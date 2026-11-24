import { AxiosError, AxiosHeaders } from "axios";

import { createSeedState } from "./seed";

export const mockEnabled =
  import.meta.env.DEV && (import.meta.env.MODE === "mock" || import.meta.env.VITE_API_MOCK === "true");

const STATE_KEY = "gradetap-dev-mock-state";
const LATENCY_MS = 180;

export const mockAccounts = [
  { label: "教师 A（待审核）", email: "teacher.a@example.invalid", password: "Teacher123" },
  { label: "教师 B（已启用）", email: "teacher.b@example.invalid", password: "Teacher123" },
  { label: "教师 C（已停用）", email: "teacher.c@example.invalid", password: "Teacher123" },
  { label: "试点管理员", email: "admin@example.invalid", password: "Admin12345" },
];

let state = loadState();

function loadState() {
  try {
    const saved = window.sessionStorage.getItem(STATE_KEY);
    if (saved) return JSON.parse(saved);
  } catch {
    // Fall through to a fresh seed.
  }
  return createSeedState();
}

function saveState() {
  window.sessionStorage.setItem(STATE_KEY, JSON.stringify(state));
}

export function resetMockState() {
  state = createSeedState();
  saveState();
}

class MockResponse {
  constructor(status, data) {
    this.status = status;
    this.data = data;
  }
}

function ok(data, status = 200) {
  return new MockResponse(status, data);
}

function fail(status, code, message, extra = {}) {
  return new MockResponse(status, { code, message, request_id: `mock-${Date.now()}`, ...extra });
}

function now() {
  return new Date().toISOString();
}

function nextId() {
  state.nextId += 1;
  return state.nextId;
}

function sessionUser() {
  return state.users.find((user) => user.user_id === state.sessionUserId) ?? null;
}

function toMe(user) {
  return {
    user_id: user.user_id,
    display_name: user.display_name,
    platform_role: user.platform_role,
    account_status: user.account_status,
    status_reason: user.status_reason ?? null,
  };
}

function toAdminTeacher(user) {
  return {
    user_id: user.user_id,
    display_name: user.display_name,
    email: user.email,
    account_status: user.account_status,
    status_reason: user.status_reason ?? null,
    version: user.version,
  };
}

function toOffering(offering) {
  const course = state.courses.find((item) => item.id === offering.course_id);
  const classGroup = state.classes.find((item) => item.id === offering.class_group_id);
  return {
    id: offering.id,
    course_id: offering.course_id,
    class_group_id: offering.class_group_id,
    course_name: course?.course_name ?? "",
    class_name: classGroup?.class_name ?? "",
    term: offering.term,
    teaching_role: "owner",
    allowed_actions: ["create_task", "review", "publish", "export"],
  };
}

function toTask(task) {
  const { owner_id: _ownerId, has_revision: _hasRevision, ...publicTask } = task;
  return publicTask;
}

function requireSession() {
  const user = sessionUser();
  if (!user || user.account_status === "disabled") {
    state.sessionUserId = null;
    return { error: fail(401, "session_required", "请先登录") };
  }
  return { user };
}

function requireActive() {
  const { user, error } = requireSession();
  if (error) return { error };
  if (user.account_status !== "active") {
    return { error: fail(403, "approval_required", "账号正在等待审核") };
  }
  return { user };
}

function requireAdmin() {
  const { user, error } = requireActive();
  if (error) return { error };
  if (user.platform_role !== "admin") {
    return { error: fail(403, "permission_denied", "需要管理员权限") };
  }
  return { user };
}

function emitMockMail(email, token) {
  console.info(`[GradeTap mock] 验证邮件 → ${email}: /verify-email?token=${token}`);
  window.dispatchEvent(new CustomEvent("gradetap:mock-mail", { detail: { email, token } }));
}

function issueVerificationToken(user) {
  const token = `verify-${user.user_id}-${Math.random().toString(36).slice(2, 8)}`;
  state.verificationTokens[token] = user.user_id;
  emitMockMail(user.email, token);
}

function ownedOffering(user, offeringId) {
  return state.offerings.find((item) => item.id === Number(offeringId) && item.owner_id === user.user_id);
}

function ownedTask(user, taskId) {
  return state.tasks.find((item) => item.id === Number(taskId) && item.owner_id === user.user_id);
}

const routes = [
  ["get", /^\/auth\/csrf$/, () => {
    state.csrfToken = `demo-csrf-${Math.random().toString(36).slice(2, 10)}`;
    return ok({ csrf_token: state.csrfToken });
  }],
  ["get", /^\/auth\/me$/, () => {
    const { user, error } = requireSession();
    return error ?? ok(toMe(user));
  }],
  ["post", /^\/auth\/login$/, ({ body }) => {
    const user = state.users.find((item) => item.email === String(body.email ?? "").trim().toLowerCase());
    if (!user || user.password !== body.password) return fail(401, "invalid_credentials", "邮箱或密码错误");
    if (!user.email_verified) return fail(403, "email_verification_required", "请先验证邮箱");
    if (user.account_status === "disabled") {
      return fail(403, "account_disabled", "账号已停用，请联系管理员", { status_reason: user.status_reason });
    }
    state.sessionUserId = user.user_id;
    return ok(toMe(user));
  }],
  ["post", /^\/auth\/logout$/, () => {
    state.sessionUserId = null;
    return ok(null, 204);
  }],
  ["post", /^\/auth\/register$/, ({ body }) => {
    const email = String(body.email ?? "").trim().toLowerCase();
    if (!body.display_name?.trim() || !email.includes("@") || String(body.password ?? "").length < 8) {
      return fail(422, "validation_error", "请填写姓名、有效邮箱和至少 8 位密码");
    }
    if (!state.users.some((item) => item.email === email)) {
      const user = {
        user_id: nextId(),
        display_name: body.display_name.trim(),
        email,
        password: body.password,
        platform_role: "teacher",
        account_status: "pending_verification",
        status_reason: null,
        email_verified: false,
        note: body.note ?? "",
        version: 1,
      };
      state.users.push(user);
      issueVerificationToken(user);
    }
    return ok({ message: "注册申请已提交，请查收验证邮件完成邮箱验证" }, 202);
  }],
  ["post", /^\/auth\/verify-email$/, ({ body }) => {
    const userId = state.verificationTokens[body.token];
    const user = state.users.find((item) => item.user_id === userId);
    if (!user) return fail(422, "verification_token_invalid", "验证链接无效或已过期");
    delete state.verificationTokens[body.token];
    user.email_verified = true;
    user.account_status = "pending_approval";
    user.version += 1;
    return ok({ message: "邮箱验证成功，请登录查看审核进度" });
  }],
  ["post", /^\/auth\/resend-verification$/, ({ body }) => {
    const user = state.users.find((item) => item.email === String(body.email ?? "").trim().toLowerCase());
    if (user && !user.email_verified) issueVerificationToken(user);
    return ok({ message: "如果该邮箱已注册且尚未验证，我们已重新发送验证邮件" }, 202);
  }],
  ["post", /^\/auth\/resubmit$/, ({ body }) => {
    const { user, error } = requireSession();
    if (error) return error;
    if (user.account_status !== "rejected") return fail(409, "invalid_state", "当前账号状态无需重新提交");
    if (!String(body.note ?? "").trim()) return fail(422, "validation_error", "请填写补充说明");
    if (body.display_name?.trim()) user.display_name = body.display_name.trim();
    user.note = body.note.trim();
    user.account_status = "pending_approval";
    user.status_reason = null;
    user.version += 1;
    return ok(toMe(user));
  }],
  ["get", /^\/admin\/teachers$/, ({ params }) => {
    const { error } = requireAdmin();
    if (error) return error;
    return ok(
      state.users
        .filter((item) => item.platform_role === "teacher")
        .filter((item) => !params.status || item.account_status === params.status)
        .map(toAdminTeacher),
    );
  }],
  ["post", /^\/admin\/teachers\/(\d+)\/actions$/, ({ body, match }) => {
    const { error } = requireAdmin();
    if (error) return error;
    const target = state.users.find((item) => item.user_id === Number(match[1]) && item.platform_role === "teacher");
    if (!target) return fail(404, "not_found", "教师账号不存在");
    if (body.expected_version !== target.version) return fail(409, "version_conflict", "状态已更新，请刷新列表");
    const allowed = { approve: "pending_approval", reject: "pending_approval", disable: "active" };
    if (!allowed[body.action]) return fail(422, "validation_error", "不支持的操作");
    if (target.account_status !== allowed[body.action]) return fail(409, "version_conflict", "状态已更新，请刷新列表");
    const reason = String(body.reason ?? "").trim();
    if (body.action !== "approve" && !reason) return fail(422, "validation_error", "驳回或停用必须填写原因");
    target.account_status = { approve: "active", reject: "rejected", disable: "disabled" }[body.action];
    target.status_reason = body.action === "approve" ? null : reason;
    target.version += 1;
    return ok(toAdminTeacher(target));
  }],
  ["get", /^\/offerings$/, () => {
    const { user, error } = requireActive();
    if (error) return error;
    return ok(state.offerings.filter((item) => item.owner_id === user.user_id).map(toOffering));
  }],
  ["post", /^\/offerings$/, ({ body }) => {
    const { user, error } = requireActive();
    if (error) return error;
    const hasCourseId = body.course_id != null;
    const hasCourseName = Boolean(String(body.course_name ?? "").trim());
    const hasClassId = body.class_group_id != null;
    const hasClassName = Boolean(String(body.class_name ?? "").trim());
    if (hasCourseId === hasCourseName || hasClassId === hasClassName || !String(body.term ?? "").trim()) {
      return fail(422, "validation_error", "课程与班级需分别选择已有项或填写新名称，学期必填");
    }
    let course = hasCourseId ? state.courses.find((item) => item.id === Number(body.course_id)) : null;
    if (hasCourseId && !course) return fail(404, "not_found", "课程不存在");
    if (course && course.owner_id !== user.user_id) return fail(403, "permission_denied", "无权使用该课程");
    let classGroup = hasClassId ? state.classes.find((item) => item.id === Number(body.class_group_id)) : null;
    if (hasClassId && !classGroup) return fail(404, "not_found", "班级不存在");
    if (classGroup && classGroup.owner_id !== user.user_id) return fail(403, "permission_denied", "无权使用该班级");

    const term = body.term.trim();
    const duplicate = state.offerings.some((item) => {
      if (item.owner_id !== user.user_id || item.term !== term) return false;
      const view = toOffering(item);
      const sameCourse = course ? item.course_id === course.id : view.course_name === body.course_name.trim();
      const sameClass = classGroup ? item.class_group_id === classGroup.id : view.class_name === body.class_name.trim();
      return sameCourse && sameClass;
    });
    if (duplicate) return fail(409, "offering_already_exists", "本学期已存在相同的课程与班级授课班");

    if (!course) {
      course = { id: nextId(), owner_id: user.user_id, course_name: body.course_name.trim(), description: "", assignment_count: 0 };
      state.courses.push(course);
    }
    if (!classGroup) {
      classGroup = { id: nextId(), owner_id: user.user_id, class_name: body.class_name.trim(), note: "", student_count: 0 };
      state.classes.push(classGroup);
    }
    const offering = { id: nextId(), owner_id: user.user_id, course_id: course.id, class_group_id: classGroup.id, term };
    state.offerings.push(offering);
    return ok(toOffering(offering), 201);
  }],
  ["get", /^\/tasks$/, ({ params }) => {
    const { user, error } = requireActive();
    if (error) return error;
    if (params.offering_id && !ownedOffering(user, params.offering_id)) return fail(404, "not_found", "授课班不存在或无权访问");
    const includeArchived = params.include_archived === true || params.include_archived === "true";
    return ok(
      state.tasks
        .filter((item) => item.owner_id === user.user_id)
        .filter((item) => !params.offering_id || item.offering_id === Number(params.offering_id))
        .filter((item) => includeArchived || !item.is_archived)
        .map(toTask),
    );
  }],
  ["post", /^\/tasks$/, ({ body }) => {
    const { user, error } = requireActive();
    if (error) return error;
    const offering = ownedOffering(user, body.offering_id);
    if (!offering) return fail(404, "not_found", "授课班不存在或无权访问");
    if (!String(body.task_name ?? "").trim()) return fail(422, "validation_error", "任务名称必填");
    const view = toOffering(offering);
    const timestamp = now();
    const task = {
      id: nextId(),
      owner_id: user.user_id,
      has_revision: false,
      offering_id: offering.id,
      course_id: offering.course_id,
      assignment_id: body.assignment_id ?? null,
      class_group_id: offering.class_group_id,
      task_name: body.task_name.trim(),
      course_name: view.course_name,
      assignment_name: body.assignment_name ?? "",
      class_name: view.class_name,
      status: "created",
      grading_instruction: body.grading_instruction ?? "",
      is_archived: false,
      archived_at: null,
      created_at: timestamp,
      updated_at: timestamp,
    };
    state.tasks.push(task);
    return ok(toTask(task), 201);
  }],
  ["delete", /^\/tasks\/(\d+)$/, ({ match }) => {
    const { user, error } = requireActive();
    if (error) return error;
    const task = ownedTask(user, match[1]);
    if (!task) return fail(404, "not_found", "任务不存在");
    if (task.has_revision) {
      return fail(409, "task_delete_protected", "该任务包含教师修订或已发布成绩，不可物理删除，请使用归档功能");
    }
    state.tasks = state.tasks.filter((item) => item !== task);
    return ok(null, 204);
  }],
  ["post", /^\/tasks\/(\d+)\/archive$/, ({ match }) => {
    const { user, error } = requireActive();
    if (error) return error;
    const task = ownedTask(user, match[1]);
    if (!task) return fail(404, "not_found", "任务不存在");
    task.is_archived = true;
    task.archived_at = now();
    task.updated_at = task.archived_at;
    return ok(toTask(task));
  }],
  ["get", /^\/courses$/, () => {
    const { user, error } = requireActive();
    if (error) return error;
    return ok(state.courses.filter((item) => item.owner_id === user.user_id).map(({ owner_id: _o, ...item }) => item));
  }],
  ["get", /^\/courses\/(\d+)\/assignments$/, ({ match }) => {
    const { error } = requireActive();
    if (error) return error;
    return ok(state.assignments[match[1]] ?? []);
  }],
  ["get", /^\/classes$/, () => {
    const { user, error } = requireActive();
    if (error) return error;
    return ok(state.classes.filter((item) => item.owner_id === user.user_id).map(({ owner_id: _o, ...item }) => item));
  }],
  ["get", /^\/settings\/llm$/, () => requireAdmin().error ?? ok(state.llm)],
  ["put", /^\/settings\/llm$/, ({ body }) => {
    const { error } = requireAdmin();
    if (error) return error;
    const { apiKey, ...rest } = body;
    state.llm = { ...state.llm, ...rest, hasApiKey: state.llm.hasApiKey || Boolean(apiKey) };
    return ok(state.llm);
  }],
  ["delete", /^\/settings\/llm\/api-key$/, () => {
    const { error } = requireAdmin();
    if (error) return error;
    state.llm = { ...state.llm, hasApiKey: false, enabled: false };
    return ok(state.llm);
  }],
  ["post", /^\/settings\/llm\/test$/, () => requireAdmin().error ?? ok({ status: "available", message: "模拟连接正常" })],
];

function parseBody(data) {
  if (typeof data !== "string" || !data) return {};
  try {
    return JSON.parse(data);
  } catch {
    return {};
  }
}

function readHeader(headers, name) {
  return AxiosHeaders.from(headers ?? {}).get(name);
}

function resolve(config) {
  const method = (config.method ?? "get").toLowerCase();
  const path = (config.url ?? "").replace(/^https?:\/\/[^/]+/, "").replace(/^\/api/, "").split("?")[0];

  if (!["get", "head", "options"].includes(method) && readHeader(config.headers, "X-CSRF-Token") !== state.csrfToken) {
    return fail(403, "csrf_invalid", "CSRF 校验失败，请刷新页面后重试");
  }

  for (const [routeMethod, pattern, handler] of routes) {
    if (routeMethod !== method) continue;
    const match = path.match(pattern);
    if (match) return handler({ body: parseBody(config.data), params: config.params ?? {}, match });
  }
  return fail(404, "mock_not_covered", `模拟数据源未覆盖 ${method.toUpperCase()} ${path}`);
}

export async function mockAdapter(config) {
  await new Promise((done) => window.setTimeout(done, LATENCY_MS));
  const result = resolve(config);
  saveState();
  const response = {
    data: result.data,
    status: result.status,
    statusText: String(result.status),
    headers: {},
    config,
    request: {},
  };
  if (result.status >= 400) {
    throw new AxiosError(
      `Request failed with status code ${result.status}`,
      result.status >= 500 ? AxiosError.ERR_BAD_RESPONSE : AxiosError.ERR_BAD_REQUEST,
      config,
      response.request,
      response,
    );
  }
  return response;
}
