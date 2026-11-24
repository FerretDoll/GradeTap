import { createServer } from "vite";

const memoryStorage = () => {
  const map = new Map();
  return {
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => map.set(key, String(value)),
    removeItem: (key) => map.delete(key),
    clear: () => map.clear(),
  };
};
globalThis.window = {
  sessionStorage: memoryStorage(),
  localStorage: memoryStorage(),
  setTimeout,
  clearTimeout,
  dispatchEvent: (event) => {
    globalThis.lastMail = event.detail;
  },
};
globalThis.CustomEvent = class {
  constructor(type, init) {
    this.type = type;
    this.detail = init?.detail;
  }
};
console.info = () => {};

process.env.VITE_API_MOCK = "true";
const server = await createServer({ mode: "development", server: { middlewareMode: true }, logLevel: "error" });
const auth = await server.ssrLoadModule("/src/api/auth.js");
const admin = await server.ssrLoadModule("/src/api/admin.js");
const offerings = await server.ssrLoadModule("/src/api/offerings.js");
const tasks = await server.ssrLoadModule("/src/api/tasks.js");
const settings = await server.ssrLoadModule("/src/api/settings.js");

let failures = 0;
function check(label, condition, detail = "") {
  console.log(`${condition ? "PASS" : "FAIL"}  ${label}${detail ? `  (${detail})` : ""}`);
  if (!condition) failures += 1;
}
async function expectError(label, promise, status, code) {
  try {
    await promise;
    check(label, false, "expected error");
  } catch (error) {
    const got = `${error.response?.status} ${error.response?.data?.code}`;
    check(label, error.response?.status === status && (!code || error.response?.data?.code === code), got);
    return error;
  }
}
const login = (email, password = "Teacher123") => auth.login({ email, password });
const A = "teacher.a@example.invalid";
const B = "teacher.b@example.invalid";
const ADMIN = ["admin@example.invalid", "Admin12345"];

// Batch A
await expectError("anonymous /auth/me -> 401", auth.getMe(), 401, "session_required");
await auth.register({ display_name: "新教师", email: "new@example.invalid", password: "Password1" });
await expectError("unverified login -> 403", login("new@example.invalid", "Password1"), 403, "email_verification_required");
await auth.verifyEmail(globalThis.lastMail.token);
check("verified login -> pending_approval", (await login("new@example.invalid", "Password1")).account_status === "pending_approval");
await expectError("pending teacher /offerings -> 403", offerings.listOfferings(), 403, "approval_required");
await auth.logout();

check("teacher A pending", (await login(A)).account_status === "pending_approval");
await expectError("teacher /admin/teachers -> 403", admin.listTeachers(), 403);
await expectError("teacher /settings/llm -> 403", settings.getLlmSettings(), 403);
await auth.logout();

await login(...ADMIN);
let pending = await admin.listTeachers("pending_approval");
let teacherA = pending.find((item) => item.user_id === 101);
await expectError("reject without reason -> 422", admin.changeTeacherStatus(101, { action: "reject", expected_version: teacherA.version }), 422);
teacherA = await admin.changeTeacherStatus(101, { action: "reject", expected_version: teacherA.version, reason: "请补充所属学院与授课课程说明" });
await auth.logout();

let me = await login(A);
check("rejected A sees status_reason", me.account_status === "rejected" && me.status_reason === "请补充所属学院与授课课程说明");
me = await auth.resubmitApplication({ note: "信息学院，Python 编程基础" });
check("resubmit -> pending_approval", me.account_status === "pending_approval" && me.status_reason === null);
await auth.logout();

await login(...ADMIN);
teacherA = (await admin.listTeachers("pending_approval")).find((item) => item.user_id === 101);
await expectError("stale version -> 409", admin.changeTeacherStatus(101, { action: "approve", expected_version: teacherA.version - 1 }), 409, "version_conflict");
await admin.changeTeacherStatus(101, { action: "approve", expected_version: teacherA.version });
await expectError("approve twice -> 409", admin.changeTeacherStatus(101, { action: "approve", expected_version: teacherA.version + 1 }), 409);
check("admin can read /settings/llm", Boolean(await settings.getLlmSettings()));
await auth.logout();

me = await login(A);
check("approved A -> active", me.account_status === "active" && me.status_reason === null);

// Batch B
let listA = await offerings.listOfferings();
check("A sees offering 12", listA.length === 1 && listA[0].id === 12);
await expectError(
  "duplicate offering same term -> 409",
  offerings.createOffering({ course_id: 1, class_group_id: 1, term: "2026-2027-1" }),
  409,
  "offering_already_exists",
);
await expectError("course_id + course_name -> 422", offerings.createOffering({ course_id: 1, course_name: "x", class_name: "y", term: "t" }), 422);
const created = await offerings.createOffering({ course_name: "程序设计基础", class_name: "学徒制试点班", term: "2026-2027-1" });
check("create offering by name -> 201", created.course_name === "程序设计基础" && created.class_name === "学徒制试点班");
const task = await tasks.createTask({ offering_id: 12, task_name: "第4周-异常处理练习", assignment_id: 6, assignment_name: "第4周实训作业" });
check("task snapshot names from offering", task.course_name === "Python 编程基础" && task.class_name === "软件试点班");
check("list by offering 12", (await tasks.listTasks({ offeringId: 12 })).length === 2);
check("list by new offering is empty", (await tasks.listTasks({ offeringId: created.id })).length === 0);
await expectError("A cannot read B's offering 22", tasks.listTasks({ offeringId: 22 }), 404);
await expectError("delete reviewed task 43 -> 409", tasks.deleteTask(43), 409, "task_delete_protected");
check("archive task 43", (await tasks.archiveTask(43)).is_archived === true);
check("archived hidden by default", !(await tasks.listTasks({ offeringId: 12 })).some((item) => item.id === 43));
check("include_archived shows 43", (await tasks.listTasks({ offeringId: 12, includeArchived: true })).some((item) => item.id === 43));
await tasks.deleteTask(task.id);
check("draft task deleted", !(await tasks.listTasks({ offeringId: 12 })).some((item) => item.id === task.id));
await auth.logout();

await login(B);
listA = await offerings.listOfferings();
check("B sees only offering 22 with same names", listA.length === 1 && listA[0].id === 22 && listA[0].class_name === "软件试点班");
check("B tasks isolated", (await tasks.listTasks({ includeArchived: true })).every((item) => item.offering_id === 22));
await auth.logout();

// Disable flow
await login(...ADMIN);
const teacherB = (await admin.listTeachers("active")).find((item) => item.user_id === 102);
await admin.changeTeacherStatus(102, { action: "disable", expected_version: teacherB.version, reason: "调岗停用" });
await auth.logout();
const disabled = await expectError("disabled login -> 403", login(B), 403, "account_disabled");
check("disabled login carries status_reason", disabled?.response?.data?.status_reason === "调岗停用");

await server.close();
console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
process.exit(failures ? 1 : 0);
