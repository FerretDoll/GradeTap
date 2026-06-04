from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

SUPPORTED_PARSE_SUFFIXES = {".docx", ".pdf", ".txt", ".md"}

STUDENT_ID_PATTERN = r"\d{5,}"
STUDENT_NAME_PATTERNS = (
    re.compile(rf"^(?P<name>.+?)[_\-\s]+(?P<no>{STUDENT_ID_PATTERN})$"),
    re.compile(rf"^(?P<no>{STUDENT_ID_PATTERN})[_\-\s]+(?P<name>.+?)$"),
)
SKIP_DIR_NAMES = {"__macosx"}
SKIP_FILE_NAMES = {".ds_store"}


@dataclass(frozen=True)
class ExtractedStudentSubmission:
    folder_name: str
    student_name: str
    student_no: str
    source_files: tuple[str, ...]
    parsed_text: str


def extract_student_submissions_from_zip(zip_path: Path, extract_root: Path) -> list[ExtractedStudentSubmission]:
    if not zip_path.exists():
        raise ValueError("ZIP 文件不存在")
    if zip_path.suffix.lower() != ".zip":
        raise ValueError("仅支持 .zip 压缩包")

    extract_dir = extract_root / f"extracted-{uuid4().hex}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    try:
        _extract_zip(zip_path, extract_dir)
        submissions = _collect_submissions(extract_dir)
        if not submissions:
            raise ValueError(
                "ZIP 中未找到可解析的学生作业文件。支持：姓名_学号/作业文件、学号_姓名/作业文件、"
                "姓名-学号.docx、学号-姓名.pdf，以及 .txt/.md/.docx/.pdf 文件。",
            )
        return submissions
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)


def _extract_zip(zip_path: Path, extract_dir: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            member_name = _decode_zip_member_name(info.filename)
            relative_path = Path(member_name)
            if _should_skip_path(relative_path):
                continue
            if relative_path.is_absolute() or ".." in relative_path.parts:
                continue
            target_path = extract_dir / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)


def _decode_zip_member_name(filename: str) -> str:
    if not filename:
        return filename
    try:
        return filename.encode("cp437").decode("gbk")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return filename


def _should_skip_path(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    if any(part in SKIP_DIR_NAMES for part in parts):
        return True
    return path.name.lower() in SKIP_FILE_NAMES


def _normalize_extract_root(extract_dir: Path) -> Path:
    current = extract_dir
    while True:
        entries = [entry for entry in current.iterdir() if not _should_skip_path(entry.relative_to(extract_dir))]
        dirs = [entry for entry in entries if entry.is_dir()]
        files = [entry for entry in entries if entry.is_file()]
        if files:
            return current
        if len(dirs) == 1:
            current = dirs[0]
            continue
        return current


def _find_student_directories(extract_dir: Path) -> list[Path]:
    root = _normalize_extract_root(extract_dir)
    direct_matches = [
        path
        for path in root.iterdir()
        if path.is_dir() and not _should_skip_path(path.relative_to(extract_dir)) and _is_student_folder(path.name)
    ]
    if direct_matches:
        return direct_matches

    nested_matches: list[Path] = []
    for child in root.iterdir():
        if not child.is_dir() or _should_skip_path(child.relative_to(extract_dir)):
            continue
        nested_matches.extend(
            path
            for path in child.iterdir()
            if path.is_dir() and not _should_skip_path(path.relative_to(extract_dir)) and _is_student_folder(path.name)
        )
    if nested_matches:
        return nested_matches

    return [
        path
        for path in extract_dir.rglob("*")
        if path.is_dir() and not _should_skip_path(path.relative_to(extract_dir)) and _is_student_folder(path.name)
    ]


def _is_student_folder(folder_name: str) -> bool:
    return _parse_student_identity(folder_name)[1] != ""


def _parse_student_folder_name(folder_name: str) -> tuple[str, str]:
    return _parse_student_identity(folder_name)


def _parse_student_identity(value: str) -> tuple[str, str]:
    normalized = re.sub(r"\s+", " ", value).strip()
    for pattern in STUDENT_NAME_PATTERNS:
        match = pattern.match(normalized)
        if match is not None:
            return match.group("name").strip(" _-"), match.group("no").strip()
    return normalized, ""


def _collect_submissions(extract_dir: Path) -> list[ExtractedStudentSubmission]:
    submissions = _collect_directory_submissions(extract_dir, require_student_name=True)
    if submissions:
        return submissions

    submissions = _collect_file_submissions(extract_dir)
    if submissions:
        return submissions

    return _collect_directory_submissions(extract_dir, require_student_name=False)


def _collect_directory_submissions(
    extract_dir: Path,
    *,
    require_student_name: bool,
) -> list[ExtractedStudentSubmission]:
    student_dirs = _find_student_directories(extract_dir) if require_student_name else _find_loose_submission_dirs(extract_dir)
    submissions: list[ExtractedStudentSubmission] = []
    for student_dir in sorted(student_dirs, key=lambda path: str(path.relative_to(extract_dir)).lower()):
        parsed_name, parsed_no = _parse_student_folder_name(student_dir.name)
        source_files, parsed_text = _collect_submission_text(student_dir)
        if not parsed_text.strip():
            continue
        submissions.append(
            ExtractedStudentSubmission(
                folder_name=student_dir.name,
                student_name=parsed_name,
                student_no=parsed_no,
                source_files=tuple(source_files),
                parsed_text=parsed_text,
            ),
        )
    return submissions


def _find_loose_submission_dirs(extract_dir: Path) -> list[Path]:
    root = _normalize_extract_root(extract_dir)
    candidate_dirs = [
        path
        for path in root.iterdir()
        if path.is_dir()
        and not _should_skip_path(path.relative_to(extract_dir))
        and any(child.is_file() and child.suffix.lower() in SUPPORTED_PARSE_SUFFIXES for child in path.rglob("*"))
    ]
    if len(candidate_dirs) > 1:
        return candidate_dirs
    return []


def _collect_file_submissions(extract_dir: Path) -> list[ExtractedStudentSubmission]:
    root = _normalize_extract_root(extract_dir)
    files = sorted(
        [
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in SUPPORTED_PARSE_SUFFIXES
            and not _should_skip_path(path.relative_to(extract_dir))
        ],
        key=lambda path: str(path.relative_to(root)).lower(),
    )

    submissions: list[ExtractedStudentSubmission] = []
    for file_path in files:
        source_files, parsed_text = _collect_submission_file_text(file_path)
        if not parsed_text.strip():
            continue
        parsed_name, parsed_no = _parse_student_identity(file_path.stem)
        submissions.append(
            ExtractedStudentSubmission(
                folder_name=file_path.stem,
                student_name=parsed_name,
                student_no=parsed_no,
                source_files=tuple(source_files),
                parsed_text=parsed_text,
            ),
        )
    return submissions


def _collect_submission_text(student_dir: Path) -> tuple[list[str], str]:
    files = sorted(
        [
            path
            for path in student_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_PARSE_SUFFIXES
        ],
        key=lambda path: path.name.lower(),
    )
    if not files:
        return [], ""

    chunks: list[str] = []
    source_names: list[str] = []
    for file_path in files:
        source_names.append(file_path.name)
        try:
            from app.services.file_parse_service import parse_document_text

            content = parse_document_text(file_path).strip()
        except ValueError:
            content = ""
        if not content:
            continue
        if len(files) == 1:
            chunks.append(content)
        else:
            chunks.append(f"=== {file_path.name} ===\n{content}")
    return source_names, "\n\n".join(chunks)


def _collect_submission_file_text(file_path: Path) -> tuple[list[str], str]:
    try:
        from app.services.file_parse_service import parse_document_text

        return [file_path.name], parse_document_text(file_path).strip()
    except ValueError:
        return [file_path.name], ""
