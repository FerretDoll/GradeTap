import logging
import os
import re
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url

from app.api.auth_api import hasher
from app.core.config import settings
from app.db.models import Account, AnswerEvidence, AuditLog, GradingResult, Question, QuestionRubric, StudentAnswer, StudentSubmission
from app.db.session import SessionLocal
from app.main import app


@pytest.fixture()
def test_engine():
    if not settings.test_database_url:
        pytest.fail("请在本地 backend/.env 配置 GRADETAP_TEST_DATABASE_URL")
    test_url = make_url(settings.test_database_url)
    if test_url.get_backend_name() != "mysql" or test_url.username != "gradetap_test":
        pytest.fail("回归测试须使用独立的 gradetap_test MySQL 账号")
    control = create_engine(test_url)
    database = "gtcheck" + uuid4().hex
    url = test_url.set(database=database)
    engine = create_engine(url)
    backend = Path(__file__).resolve().parents[1]
    try:
        with control.connect() as connection:
            connection.exec_driver_sql(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4")
            try:
                subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend,
                               env={**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False)}, check=True)
                yield engine
            finally:
                engine.dispose()
                connection.exec_driver_sql(f"DROP DATABASE `{database}`")
    finally:
        control.dispose()


@pytest.fixture()
def clients(tmp_path, monkeypatch, test_engine):
    old = SessionLocal.kw["bind"]
    SessionLocal.configure(bind=test_engine)
    monkeypatch.setattr(settings, "app_env", "test")
    monkeypatch.setattr(settings, "local_storage_root", str(tmp_path / "uploads"))
    try:
        accounts = {}
        password_hash = hasher.hash("LocalTest123")
        for name in ("admin", "alpha", "beta"):
            with SessionLocal() as db:
                db.add(Account(email=f"{name}@example.org", display_name=name, password_hash=password_hash,
                               platform_role="admin" if name == "admin" else "teacher", account_status="active"))
                db.commit()
            accounts[name] = TestClient(app)
            login(accounts[name], name)
        yield accounts
    finally:
        SessionLocal.configure(bind=old)


def token(client):
    client.headers["X-CSRF-Token"] = client.get("/api/auth/csrf").json()["csrf_token"]


def login(client, name):
    token(client)
    result = client.post("/api/auth/login", json={"email": f"{name}@example.org", "password": "LocalTest123"})
    assert result.status_code == 200, result.text
    token(client)


def offering(client):
    body = {"term": "Fall", "course_name": "Python", "class_name": "同名班"}
    result = client.post("/api/offerings", json=body)
    assert result.status_code == 201, result.text
    assert client.post("/api/offerings", json=body).status_code == 409
    return result.json()


def task(client, o):
    result = client.post("/api/tasks", json={"offering_id": o["id"], "task_name": "Python"})
    assert result.status_code == 201, result.text
    return result.json()["id"]


def test_account_lifecycle(clients, caplog):
    admin = clients["admin"]
    new = TestClient(app)
    body = {"email": "new@example.org", "display_name": "New", "password": "LocalTest123"}
    assert new.post("/api/auth/register", json=body).status_code == 403
    token(new)
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        assert new.post("/api/auth/register", json=body).status_code == 202
        first = re.findall(r"token=([\w-]+)", caplog.text)[-1]
        assert new.post("/api/auth/resend-verification", json=body).status_code == 202
        current = re.findall(r"token=([\w-]+)", caplog.text)[-1]
    assert new.post("/api/auth/login", json=body).json()["code"] == "email_verification_required"
    assert new.post("/api/auth/verify-email", json={"token": first}).status_code == 422
    assert new.post("/api/auth/verify-email", json={"token": current}).status_code == 200
    login(new, "new")
    assert new.get("/api/tasks").status_code == 403
    who = admin.get("/api/admin/teachers?status=pending_approval").json()[0]
    actions = f"/api/admin/teachers/{who['user_id']}/actions"
    def action(name, version):
        return admin.post(actions, json={"action": name, "reason": "test", "expected_version": version})
    assert action("reject", who["version"]).status_code == 200
    assert new.get("/api/auth/me").json()["status_reason"] == "test"
    assert new.post("/api/auth/resubmit", json={"note": "补充"}).status_code == 200
    assert action("approve", who["version"]).status_code == 409
    who = admin.get("/api/admin/teachers?status=pending_approval").json()[0]
    approved = action("approve", who["version"]).json()
    assert new.get("/api/tasks").status_code == 200
    assert new.get("/api/settings/llm").status_code == 403
    assert new.get("/api/admin/teachers").status_code == 403
    assert action("disable", approved["version"]).status_code == 200
    assert new.get("/api/auth/me").json()["code"] == "session_required"
    assert new.post("/api/auth/login", json=body).json()["code"] == "account_disabled"


def test_all_workspace_routes_enforce_scope(clients):
    alpha, beta = clients["alpha"], clients["beta"]
    a, b = offering(alpha), offering(beta)
    tid = task(alpha, a)
    assert beta.get("/api/tasks").json() == []
    assert beta.get(f"/api/tasks?offering_id={a['id']}").status_code == 404
    assert beta.post("/api/tasks", json={"offering_id": a["id"], "task_name": "x"}).status_code == 404
    assert [c["id"] for c in beta.get("/api/classes").json()] == [b["class_group_id"]]
    assert [c["id"] for c in beta.get("/api/courses").json()] == [b["course_id"]]
    ids = {"task_id": tid, "course_id": a["course_id"], "class_group_id": a["class_group_id"]}
    for path, methods in app.openapi()["paths"].items():
        if not any("{"+key+"}" in path for key in ids):
            continue
        url = re.sub(r"\{(\w+)\}", lambda match: str(ids.get(match[1], 1)), path)
        for method in methods:
            response = beta.request(method, url)
            assert response.status_code == 404, (method, url, response.text)
            assert response.json()["request_id"]
    assert alpha.delete(f"/api/tasks/{tid}").status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.target_id == tid, AuditLog.action == "create_task"))


def test_review_release_and_second_submission(clients):
    client = clients["alpha"]
    o = offering(client)
    tid = task(client, o)
    path = f"/api/tasks/{tid}"
    student = client.post(f"/api/classes/{o['class_group_id']}/students",
                          json={"student_name": "Alpha", "student_no": "123"})
    assert student.status_code == 201, student.text
    def submit(content):
        upload = client.post(path+"/files?file_role=student_submission", files={"file": ("Alpha123.txt", content)})
        assert upload.status_code == 201, upload.text
        prepared = client.post(path+"/prepare-students")
        assert prepared.status_code == 200, prepared.text
    submit("first")
    with SessionLocal() as db:
        submission = db.scalar(select(StudentSubmission).where(StudentSubmission.task_id == tid))
        q = Question(task_id=tid, question_number="1", content="test", question_type="short_answer",
                     difficulty="medium", total_score=100)
        db.add(q)
        db.flush()
        answer = StudentAnswer(task_id=tid, question_id=q.id, student_submission_id=submission.id,
                               answer_text="first", extraction_status="matched")
        db.add(answer)
        db.flush()
        rubric = QuestionRubric(question_id=q.id, dimension_name="logic", max_score=100,
                                scoring_criteria="correct", deduction_criteria="missing", evidence_requirement="answer")
        db.add(rubric)
        db.flush()
        db.add(AnswerEvidence(task_id=tid, question_id=q.id, rubric_id=rubric.id, student_answer_id=answer.id,
                              positive_evidence=["first"], negative_evidence=[], confidence=1))
        result = GradingResult(task_id=tid, student_answer_id=answer.id, student_submission_id=submission.id,
                               question_id=q.id, score=70, confidence=1, grading_status="partial", review_status="ai_generated", review_priority="low")
        db.add(result)
        db.commit()
        rid = result.id
    assert client.post(path+"/releases").status_code == 409
    reviewed = client.put(path+f"/grading-results/{rid}/review", json={
        "teacher_id": 999, "final_score": 85, "final_comment": "corrected", "revision_reason": "review"})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["teacher_id"] != 999
    assert client.delete(path).json()["code"] == "task_delete_protected"
    release = client.post(path+"/releases")
    assert release.status_code == 201, release.text
    export = {"release_id": release.json()["release_id"]}
    workbook = client.post(path+"/export-results", json=export).content
    assert 85 in [cell.value for row in load_workbook(BytesIO(workbook)).active for cell in row]
    submit("second")
    with SessionLocal() as db:
        assert db.scalar(select(StudentSubmission.content).where(StudentSubmission.task_id == tid)) == "second"
    assert client.get(path).json()["submission_round"] == 2
    versions = client.get(path+"/evaluation-versions").json()
    snapshot = client.get(path+f"/evaluation-versions/{versions[0]['id']}").json()["snapshot"]
    assert snapshot["answer_evidence"][0]["positive_evidence"] == ["first"]
    assert snapshot["teacher_revision"][0]["final_score"] == 85
    assert snapshot["student_submission"][0]["content"] == "first"
    assert Path(snapshot["uploaded_file"][0]["storage_path"]).exists()
    assert client.post(path+"/export-results", json={**export, "teacher_revisions": [
        {"grading_result_id": rid, "final_score": 1}]}).content == workbook
    assert client.delete(path).status_code == 409
    assert client.post(path+"/archive").json()["is_archived"]
    assert client.get("/api/tasks").json() == []
    assert client.get("/api/tasks?include_archived=true").json()[0]["id"] == tid
