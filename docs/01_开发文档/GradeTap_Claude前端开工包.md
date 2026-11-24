# GradeTap｜给 Claude 的前端开工单

**第 1–2 批（阶段 0–2）· 账号审核、授课班与任务隔离 · 接口契约 v0.3.0 · 2026-11-24**

## 可以直接给 Claude 的任务

请在 [GradeTap](https://github.com/FerretDoll/GradeTap) 的现有 `frontend/` 中完成批次 A（账号与管理员审核）及批次 B（授课班与任务隔离、归档保护）页面，沿用 Vue 3、Element Plus、Pinia 和 Axios。先实现一条完整可点击的流程：教师注册并验证邮箱 → 登录看到待审核（或被驳回查看原因后重新提交）→ 管理员批准 → 教师刷新进入自己的授课班 → 按授课班查看/新建/归档任务。请同时保留课程、班级、任务和查重的现有工作台入口（模型配置入口收归管理员后台）。页面设计与交互由你决定，身份、数据归属和可执行动作严格按下方契约读取。

本开工单按**阶段 0–2**推进（不按固定天数拆分）：前端先完成工程前置改造并用下方 JSON 样例建立可切换的开发数据源，真实接口按批次 A、批次 B 依次接通，切换时只改 API 层。模拟身份切换仅用于开发预览。每批提交附前端改动、构建结果，以及教师和管理员各一条可重现的浏览器操作路径。

## 前端工程前置要求（阶段 0 必做）

开始编写业务页面前，请先解决现有 `frontend/` 中的 4 项基线隐患：

1. **同域代理、环境示例与 Cookie 凭证**：
   - 在 `frontend/vite.config.js` 中增加 `/api` 代理转发至本地 FastAPI（默认 `http://127.0.0.1:8000`）；
   - 将 `frontend/src/api/client.js` 的默认 `baseURL` 改为 `"/api"` 并启用 `withCredentials: true`；
   - **同步将 `frontend/.env.example` 中的 `VITE_API_BASE_URL=http://127.0.0.1:8000/api` 改为 `VITE_API_BASE_URL=/api`**，并检查本机是否已有 `frontend/.env` / `frontend/.env.local` 覆盖了绝对地址，防止绕过 Vite 代理导致会话 Cookie、CSRF Cookie 与 SSE（`EventSource`）丢凭证。
2. **引入路由并隔离 9,682 行 `App.vue`**：当前 `frontend/package.json` 尚无 `vue-router`，且 `frontend/src/App.vue` 为 9,682 行单文件。请引入 `vue-router`，将新页面建在独立目录（如 `src/views/auth/`、`src/views/admin/`、`src/views/offerings/`），**禁止继续往 `App.vue` 堆叠新模块**；现有 `App.vue` 仅作为老工作台视图挂载或渐进拆分。
3. **废除跨账号 `localStorage` 合并逻辑**：现有 `src/stores/taskStore.js` 中的 `mergeTasks(readLocalTasks(), remoteTasks)` 以及 `App.vue` 内 10 余个 `LOCAL_*` 缓存键会在多教师切换时造成数据串号。请彻底停用离线缓存合并，**账号切换或退出登录时必须清空全部 Pinia store 状态和业务 `localStorage` 键**。
4. **收口模型配置入口**：`/api/settings/llm` 将改为仅管理员可访问。请从普通教师工作台移除或隐藏全局模型配置修改入口，仅在系统管理区为管理员提供入口。

## 阶段 0–2 页面清单

| 顺序 | 所属批次 | 入口 | 交付体验 |
|---|---|---|---|
| 1 | 批次 A（阶段 1） | 注册、邮箱验证、登录 | 注册后引导查看邮件（支持点击“重新发送验证邮件”）。验证页支持从 URL 读取 `token`，失效链接给出重发或返回引导。验证后登录可查看审核进度 |
| 2 | 批次 A（阶段 1） | 待审核、已驳回重提与异常状态 | 未登录回登录页。已验证待审核（`pending_approval`）显示审核进度与刷新按钮；已驳回（`rejected`）展示服务端返回的 `status_reason` 并支持补充说明重新提交；在线被停用后收到 `401` 跳回登录页，重新登录看到 `account_disabled` 原因提示 |
| 3 | 批次 A（阶段 1） | 系统管理 → 教师账号（与模型入口） | 管理员可筛选待审核/已启用/已驳回/已停用教师，执行批准、填写原因驳回或停用。操作成功后刷新列表，遇到 `409` 时提示刷新。普通教师菜单不显示系统管理，服务端返回 `403` 时页面给出明确无权提示 |
| 4 | 批次 B（阶段 2） | 教师首页、授课班管理与任务隔离 | 启用后进入自己的授课班视图并保留现有工作台入口。支持新建授课班（选择已有课程/班级或输入新名称创建，同名班以不同 `id` 区分）；任务列表按 `offering_id` 筛选，新建任务必填 `offering_id`；删除任务收到 `409 task_delete_protected` 时引导点击“归档”，并支持切换查看已归档任务。切号后彻底清空上一账号数据 |

批次 C/D（阶段 3–4）另按后续契约对接备课编辑、智能体轨迹、复核、发布快照与正式导出。

## 接口与状态约定

### 批次 A：账号、CSRF 与管理员审核
- **同域会话与 CSRF**：所有接口以 `/api` 为前缀。网页同域携带 Cookie。写操作前先调用 `GET /api/auth/csrf`：未登录时后端下发匿名 CSRF Cookie（`gradetap_csrf`）并在 JSON 中返回相同的 `csrf_token`，前端把 `csrf_token` 放入 `X-CSRF-Token` 请求头（Double-Submit Cookie 校验）；登录或退出会轮换会话，完成后前端需重新调用 `GET /api/auth/csrf`。本地非 HTTPS 开发环境后端关闭 Cookie `Secure` 标志，预发布/生产环境强制开启 `Secure`。
- **开发期邮箱验证兜底**：在阶段 5 接入真实邮件服务前，开放注册提交统一返回 `202` 与提示文案；非生产环境允许开发/联调人员从后端控制台日志或仅限非生产开启的测试回执读取一次性验证 `token` 完成联调。支持 `POST /api/auth/resend-verification` 重发验证邮件。
- **账号状态与原因闭环**：
  - 邮箱未验证时登录返回 `403` 与 `email_verification_required`。
  - 邮箱验证后登录进入受限会话，`/api/auth/me` 返回 `pending_approval`；管理员驳回后，`account_status` 变为 `rejected`，`/api/auth/me` 返回管理员填写的 `status_reason`，教师可通过 `POST /api/auth/resubmit` 补充说明重新进入 `pending_approval`。
  - 管理员批准后，同一账号再读 `/api/auth/me` 显示 `active`（`status_reason` 为 `null`）。
  - 管理员停用已启用账号时，服务端立即撤销其在线会话：该账号已有页面下次请求 `/api/auth/me` 或业务接口将收到 `401 session_required` 并退回登录页；再次登录返回 `403 account_disabled`（在 `message` 及可选 `status_reason` 中告知停用提示）。
- **管理员审核动作**：`POST /api/admin/teachers/{user_id}/actions`，请求体如 `{"action":"approve","expected_version":1}`。`reject` 与 `disable` 必须填写非空 `reason`。批准与驳回仅接受 `pending_approval`，停用仅接受 `active`。遇到 `409 version_conflict` 时刷新列表后再操作。操作者身份完全取自当前会话。

### 批次 B：授课班创建、任务绑定与删除/归档保护
- **创建授课班（`POST /api/offerings`）对象复用、新建与冲突规则**：
  - **课程维度二选一（互斥）**：传 `course_id` 表示复用当前教师已授权的课程（无权或不存在返 `403`/`404`）；传 `course_name`（不传 `course_id`）表示自动创建归属当前教师的新课程。两者不可同时传入、不可同时为空（违反返 `422`）。
  - **班级维度二选一（互斥）**：传 `class_group_id` 表示复用当前教师已授权的班级（无权或不存在返 `403`/`404`）；传 `class_name`（不传 `class_group_id`）表示自动创建归属当前教师的新班级。两者不可同时传入、不可同时为空（违反返 `422`）。
  - **命名隔离与重复冲突规则**：不同教师可以自由创建同名课程、同名班级、同名授课班（通过独立 `id` 隔离，不冲突）；同一教师在同一 `term` 下，若目标 `(course_id, class_group_id, term)` 授课班已存在（或按名称新建时该教师在同学期下已存在完全同名的课程+班级授课班），后端返回 `409 offering_already_exists`，不静默重复建班。
- **任务查询与创建（`GET/POST /api/tasks`）**：
  - `GET /api/tasks` 支持可选查询参数 `offering_id` 与 `include_archived`（默认 `false`）。未传 `offering_id` 时仅返回当前教师已授权授课班下的任务；传入无权访问的 `offering_id` 返回 `403`/`404`。
  - `POST /api/tasks` 请求体必须传 `offering_id` 与 `task_name`（可选 `assignment_id`、`assignment_name`、`grading_instruction`）；`course_name` 与 `class_name` 由后端根据 `offering_id` 自动写入显示快照，客户端不传且不可伪造。
- **任务删除限制与归档（`DELETE /api/tasks/{task_id}`、`POST /api/tasks/{task_id}/archive`）**：
  - 仅允许对**无教师修订记录且无正式发布快照**的新建/草稿任务执行 `DELETE /api/tasks/{task_id}`（且后端禁止物理删除 `AuditLog`）。
  - 若任务已有任意教师修订或已发布正式成绩，`DELETE /api/tasks/{task_id}` 返回 `409 task_delete_protected`；前端捕获后提示“已有师评或发布记录，不可删除，请改用归档”并提供一键调用 `POST /api/tasks/{task_id}/archive`。归档后原件、证据、师评、发布快照与审计日志完整保留，默认列表隐藏，可通过 `include_archived=true` 回看。
- **接口基线**：[GradeTap 96e4d35](https://github.com/FerretDoll/GradeTap/tree/96e4d351e0db65d186a85524f0e2dfe5944b60ba)。真实后端就绪时由后端负责人提供预发布地址、测试身份和对应版本。

## 联调 1（阶段 1）与联调 2（阶段 2）通过标准

1. **批次 A（联调 1）**：教师 A 自助注册、通过开发/预发布验证 token 完成邮箱验证后登录，待审期间只能查看状态；管理员驳回并填原因后，A 页面可见具体 `status_reason` 并可补充重提；管理员批准后，A 刷新进入授课班；普通教师进管理区或请求 `/api/settings/llm` 均返 `403`；停用后旧会话立返 `401` 退出，重登看到 `403 account_disabled`。
2. **批次 B（联调 2）**：教师 A 与教师 B 均通过 `POST /api/offerings` 建立“软件试点班”（A 的授课班 ID 为 12，B 为 22），同师同学期重复建同一授课班返 `409`；按 `offering_id` 创建与筛选任务彼此完全隔离；对已含师评/发布成绩的任务点击删除被 `409` 拦截并成功改走归档；切换身份或退出后彻底清空缓存，无跨账号残留。

## 前端模拟响应

```json
[
  {"name": "取得CSRF令牌", "method": "GET", "path": "/api/auth/csrf", "status": 200, "body": {"csrf_token": "demo-csrf-token-01"}},
  {"name": "未登录", "method": "GET", "path": "/api/auth/me", "status": 401, "body": {"code": "session_required", "message": "请先登录", "request_id": "demo-01"}},
  {"name": "邮箱待验证时登录", "method": "POST", "path": "/api/auth/login", "status": 403, "body": {"code": "email_verification_required", "message": "请先验证邮箱", "request_id": "demo-02"}},
  {"name": "教师A待审核", "method": "GET", "path": "/api/auth/me", "status": 200, "body": {"user_id": 101, "display_name": "教师 A", "platform_role": "teacher", "account_status": "pending_approval", "status_reason": null}},
  {"name": "教师A待审查询授课班", "method": "GET", "path": "/api/offerings", "status": 403, "body": {"code": "approval_required", "message": "账号正在等待审核", "request_id": "demo-03"}},
  {"name": "教师A被驳回查看原因", "method": "GET", "path": "/api/auth/me", "status": 200, "body": {"user_id": 101, "display_name": "教师 A", "platform_role": "teacher", "account_status": "rejected", "status_reason": "请补充所属学院与授课课程说明"}},
  {"name": "教师A补充重提", "method": "POST", "path": "/api/auth/resubmit", "status": 200, "body": {"user_id": 101, "display_name": "教师 A", "platform_role": "teacher", "account_status": "pending_approval", "status_reason": null}},
  {"name": "管理员", "method": "GET", "path": "/api/auth/me", "status": 200, "body": {"user_id": 1, "display_name": "试点管理员", "platform_role": "admin", "account_status": "active", "status_reason": null}},
  {"name": "待审核列表", "method": "GET", "path": "/api/admin/teachers?status=pending_approval", "status": 200, "body": [{"user_id": 101, "display_name": "教师 A", "email": "teacher.a@example.invalid", "account_status": "pending_approval", "status_reason": null, "version": 1}]},
  {"name": "批准A", "method": "POST", "path": "/api/admin/teachers/101/actions", "status": 200, "body": {"user_id": 101, "display_name": "教师 A", "email": "teacher.a@example.invalid", "account_status": "active", "status_reason": null, "version": 2}},
  {"name": "教师A已启用", "method": "GET", "path": "/api/auth/me", "status": 200, "body": {"user_id": 101, "display_name": "教师 A", "platform_role": "teacher", "account_status": "active", "status_reason": null}},
  {"name": "教师A的授课班", "method": "GET", "path": "/api/offerings", "status": 200, "body": [{"id": 12, "course_id": 1, "class_group_id": 1, "course_name": "Python 编程基础", "class_name": "软件试点班", "term": "2026-2027-1", "teaching_role": "owner", "allowed_actions": ["create_task", "review", "publish", "export"]}]},
  {"name": "教师A按名称新建授课班", "method": "POST", "path": "/api/offerings", "status": 201, "body": {"id": 13, "course_id": 2, "class_group_id": 2, "course_name": "程序设计基础", "class_name": "学徒制试点班", "term": "2026-2027-1", "teaching_role": "owner", "allowed_actions": ["create_task", "review", "publish", "export"]}},
  {"name": "教师A同学期重复建班冲突", "method": "POST", "path": "/api/offerings", "status": 409, "body": {"code": "offering_already_exists", "message": "本学期已存在相同的课程与班级授课班", "request_id": "demo-07"}},
  {"name": "教师B的同名授课班", "method": "GET", "path": "/api/offerings", "status": 200, "body": [{"id": 22, "course_id": 8, "class_group_id": 9, "course_name": "Python 编程基础", "class_name": "软件试点班", "term": "2026-2027-1", "teaching_role": "owner", "allowed_actions": ["create_task", "review", "publish", "export"]}]},
  {"name": "新教师尚未分班", "method": "GET", "path": "/api/offerings", "status": 200, "body": []},
  {"name": "按授课班查询任务列表", "method": "GET", "path": "/api/tasks?offering_id=12&include_archived=false", "status": 200, "body": [{"id": 43, "offering_id": 12, "course_id": 1, "assignment_id": 5, "class_group_id": 1, "task_name": "第3周-工单分类汇总", "course_name": "Python 编程基础", "assignment_name": "第3周实训作业", "class_name": "软件试点班", "status": "waiting_teacher_review", "grading_instruction": "", "is_archived": false, "archived_at": null, "created_at": "2026-11-24T08:00:00Z", "updated_at": "2026-11-24T09:10:00Z"}]},
  {"name": "在授课班下创建任务", "method": "POST", "path": "/api/tasks", "status": 201, "body": {"id": 44, "offering_id": 12, "course_id": 1, "assignment_id": 6, "class_group_id": 1, "task_name": "第4周-异常处理练习", "course_name": "Python 编程基础", "assignment_name": "第4周实训作业", "class_name": "软件试点班", "status": "created", "grading_instruction": "重点核对边界用例", "is_archived": false, "archived_at": null, "created_at": "2026-11-24T09:30:00Z", "updated_at": "2026-11-24T09:30:00Z"}},
  {"name": "删除含师评任务被拦截", "method": "DELETE", "path": "/api/tasks/43", "status": 409, "body": {"code": "task_delete_protected", "message": "该任务包含教师修订或已发布成绩，不可物理删除，请使用归档功能", "request_id": "demo-08"}},
  {"name": "归档含师评任务", "method": "POST", "path": "/api/tasks/43/archive", "status": 200, "body": {"id": 43, "offering_id": 12, "course_id": 1, "assignment_id": 5, "class_group_id": 1, "task_name": "第3周-工单分类汇总", "course_name": "Python 编程基础", "assignment_name": "第3周实训作业", "class_name": "软件试点班", "status": "waiting_teacher_review", "grading_instruction": "", "is_archived": true, "archived_at": "2026-11-24T10:00:00Z", "created_at": "2026-11-24T08:00:00Z", "updated_at": "2026-11-24T10:00:00Z"}},
  {"name": "教师无权进管理区或改模型配置", "method": "GET", "path": "/api/admin/teachers", "status": 403, "body": {"code": "permission_denied", "message": "需要管理员权限", "request_id": "demo-04"}},
  {"name": "重复审批", "method": "POST", "path": "/api/admin/teachers/101/actions", "status": 409, "body": {"code": "version_conflict", "message": "状态已更新，请刷新列表", "request_id": "demo-05"}},
  {"name": "已停用账号重新登录", "method": "POST", "path": "/api/auth/login", "status": 403, "body": {"code": "account_disabled", "message": "账号已停用，请联系管理员", "status_reason": "调岗停用", "request_id": "demo-06"}}
]
```

## 可提取的 OpenAPI 文件

下方代码块可另存为 `gradetap-batch-ab-v0.3.yaml`。覆盖批次 A（账号与审核）及批次 B（授课班、任务隔离与归档保护）全部请求体与响应模型。

```yaml
openapi: 3.1.0
info:
  title: GradeTap 批次 A/B 账号、授课班与任务隔离契约
  version: 0.3.0
servers:
- url: /api
paths:
  /auth/csrf:
    get:
      operationId: getCsrf
      summary: 下发匿名或当前会话的 CSRF Cookie 并返回对应表单令牌
      security: []
      responses:
        '200':
          description: 取得当前浏览器表单令牌（配合 gradetap_csrf Cookie 做 Double-Submit 校验）
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Csrf'
  /auth/register:
    post:
      operationId: registerTeacher
      summary: 提交教师注册申请
      security:
      - csrfCookie: []
        csrfHeader: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Register'
      responses:
        '202':
          description: 已受理注册申请并发送验证令牌
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Receipt'
        '403':
          $ref: '#/components/responses/E403'
        '422':
          $ref: '#/components/responses/E422'
        '429':
          $ref: '#/components/responses/E429'
  /auth/verify-email:
    post:
      operationId: verifyEmail
      summary: 验证邮件中的一次性令牌
      security:
      - csrfCookie: []
        csrfHeader: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/VerifyEmail'
      responses:
        '200':
          description: 邮箱验证成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Receipt'
        '403':
          $ref: '#/components/responses/E403'
        '422':
          $ref: '#/components/responses/E422'
        '429':
          $ref: '#/components/responses/E429'
  /auth/resend-verification:
    post:
      operationId: resendVerification
      summary: 重新发送邮箱验证令牌
      security:
      - csrfCookie: []
        csrfHeader: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ResendVerification'
      responses:
        '202':
          description: 已受理重发请求（避免枚举账号，统一返回提示文案）
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Receipt'
        '403':
          $ref: '#/components/responses/E403'
        '422':
          $ref: '#/components/responses/E422'
        '429':
          $ref: '#/components/responses/E429'
  /auth/login:
    post:
      operationId: login
      summary: 登录并建立服务端会话（已验证待审或被驳回账号获得受限会话）
      security:
      - csrfCookie: []
        csrfHeader: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Login'
      responses:
        '200':
          description: 登录成功并建立服务端会话
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Me'
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
        '422':
          $ref: '#/components/responses/E422'
        '429':
          $ref: '#/components/responses/E429'
  /auth/me:
    get:
      operationId: getMe
      summary: 读取当前身份、账户状态及驳回/停用原因
      security:
      - cookieSession: []
      responses:
        '200':
          description: 读取身份与账户状态
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Me'
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
  /auth/resubmit:
    post:
      operationId: resubmitApplication
      summary: 被驳回教师补充说明并重新提交审核
      security:
      - cookieSession: []
        csrfCookie: []
        csrfHeader: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Resubmit'
      responses:
        '200':
          description: 已重新进入待审核状态
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Me'
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
        '409':
          $ref: '#/components/responses/E409'
        '422':
          $ref: '#/components/responses/E422'
  /auth/logout:
    post:
      operationId: logout
      summary: 退出并撤销会话
      security:
      - cookieSession: []
        csrfCookie: []
        csrfHeader: []
      responses:
        '204':
          description: 退出并撤销会话
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
  /offerings:
    get:
      operationId: listOfferings
      summary: 列出当前教师获授权的授课班
      security:
      - cookieSession: []
      responses:
        '200':
          description: 列出当前教师获授权的授课班
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Offering'
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
    post:
      operationId: createOffering
      summary: 创建授课班（课程/班级各支持按 ID 复用或按名称新建，二选一互斥；同师同学期重复返 409）
      security:
      - cookieSession: []
        csrfCookie: []
        csrfHeader: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/OfferingCreate'
      responses:
        '201':
          description: 授课班创建成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Offering'
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
        '404':
          $ref: '#/components/responses/E404'
        '409':
          $ref: '#/components/responses/E409'
        '422':
          $ref: '#/components/responses/E422'
  /tasks:
    get:
      operationId: listTasks
      summary: 列出当前教师获授权授课班下的批改任务
      security:
      - cookieSession: []
      parameters:
      - name: offering_id
        in: query
        required: false
        description: 可选，按指定已授权授课班过滤；无权访问返 403/404
        schema:
          type: integer
          minimum: 1
      - name: include_archived
        in: query
        required: false
        description: 是否包含已归档任务，默认 false
        schema:
          type: boolean
          default: false
      responses:
        '200':
          description: 批改任务列表
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/GradingTaskRead'
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
        '404':
          $ref: '#/components/responses/E404'
        '422':
          $ref: '#/components/responses/E422'
    post:
      operationId: createTask
      summary: 在指定已授权授课班下创建批改任务（课程名/班级名由后端按 offering_id 自动回填快照）
      security:
      - cookieSession: []
        csrfCookie: []
        csrfHeader: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GradingTaskCreate'
      responses:
        '201':
          description: 批改任务创建成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GradingTaskRead'
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
        '404':
          $ref: '#/components/responses/E404'
        '422':
          $ref: '#/components/responses/E422'
  /tasks/{task_id}:
    delete:
      operationId: deleteTask
      summary: 删除未产生教师修订与正式发布快照的草稿任务（含师评/已发布返 409，且禁止删除审计日志）
      security:
      - cookieSession: []
        csrfCookie: []
        csrfHeader: []
      parameters:
      - name: task_id
        in: path
        required: true
        schema:
          type: integer
          minimum: 1
      responses:
        '204':
          description: 草稿任务已删除（审计日志保留）
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
        '404':
          $ref: '#/components/responses/E404'
        '409':
          $ref: '#/components/responses/E409'
  /tasks/{task_id}/archive:
    post:
      operationId: archiveTask
      summary: 归档批改任务（完整保留原件、证据、教师修订、发布快照与审计日志）
      security:
      - cookieSession: []
        csrfCookie: []
        csrfHeader: []
      parameters:
      - name: task_id
        in: path
        required: true
        schema:
          type: integer
          minimum: 1
      responses:
        '200':
          description: 任务已归档
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GradingTaskRead'
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
        '404':
          $ref: '#/components/responses/E404'
  /admin/teachers:
    get:
      operationId: listTeachers
      summary: 管理员查看教师账号与待审核申请
      security:
      - cookieSession: []
      parameters:
      - name: status
        in: query
        required: false
        schema:
          $ref: '#/components/schemas/AccountStatus'
      responses:
        '200':
          description: 管理员查看教师账号与待审核申请
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/AdminTeacher'
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
        '422':
          $ref: '#/components/responses/E422'
  /admin/teachers/{user_id}/actions:
    post:
      operationId: changeTeacherStatus
      summary: 管理员批准、驳回或停用教师账号
      security:
      - cookieSession: []
        csrfCookie: []
        csrfHeader: []
      parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: integer
          minimum: 1
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TeacherAction'
      responses:
        '200':
          description: 管理员批准、驳回或停用教师账号
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AdminTeacher'
        '401':
          $ref: '#/components/responses/E401'
        '403':
          $ref: '#/components/responses/E403'
        '404':
          $ref: '#/components/responses/E404'
        '409':
          $ref: '#/components/responses/E409'
        '422':
          $ref: '#/components/responses/E422'
components:
  securitySchemes:
    cookieSession:
      type: apiKey
      in: cookie
      name: gradetap_session
    csrfCookie:
      type: apiKey
      in: cookie
      name: gradetap_csrf
    csrfHeader:
      type: apiKey
      in: header
      name: X-CSRF-Token
  schemas:
    AccountStatus:
      type: string
      enum:
      - pending_verification
      - pending_approval
      - active
      - rejected
      - disabled
    PlatformRole:
      type: string
      enum:
      - teacher
      - admin
    Me:
      type: object
      additionalProperties: false
      required:
      - user_id
      - display_name
      - platform_role
      - account_status
      properties:
        user_id:
          type: integer
          minimum: 1
        display_name:
          type: string
        platform_role:
          $ref: '#/components/schemas/PlatformRole'
        account_status:
          $ref: '#/components/schemas/AccountStatus'
        status_reason:
          type:
          - string
          - 'null'
          description: 驳回或停用原因（非驳回/停用状态为 null）
    Register:
      type: object
      additionalProperties: false
      required:
      - display_name
      - email
      - password
      properties:
        display_name:
          type: string
          minLength: 1
        email:
          type: string
          format: email
        password:
          type: string
          minLength: 8
          writeOnly: true
        note:
          type: string
          description: 可选的院系或课程申请说明
    Login:
      type: object
      additionalProperties: false
      required:
      - email
      - password
      properties:
        email:
          type: string
          format: email
        password:
          type: string
          writeOnly: true
    VerifyEmail:
      type: object
      additionalProperties: false
      required:
      - token
      properties:
        token:
          type: string
          minLength: 1
    ResendVerification:
      type: object
      additionalProperties: false
      required:
      - email
      properties:
        email:
          type: string
          format: email
    Resubmit:
      type: object
      additionalProperties: false
      required:
      - note
      properties:
        display_name:
          type: string
          minLength: 1
        note:
          type: string
          minLength: 1
          description: 针对驳回原因的补充说明
    Receipt:
      type: object
      additionalProperties: false
      required:
      - message
      properties:
        message:
          type: string
    Csrf:
      type: object
      additionalProperties: false
      required:
      - csrf_token
      properties:
        csrf_token:
          type: string
    Offering:
      type: object
      additionalProperties: false
      required:
      - id
      - course_id
      - class_group_id
      - course_name
      - class_name
      - term
      - teaching_role
      - allowed_actions
      properties:
        id:
          type: integer
          minimum: 1
        course_id:
          type: integer
          minimum: 1
        class_group_id:
          type: integer
          minimum: 1
        course_name:
          type: string
        class_name:
          type: string
        term:
          type: string
        teaching_role:
          type: string
          enum:
          - owner
          - collaborator
        allowed_actions:
          type: array
          items:
            type: string
            enum:
            - create_task
            - review
            - publish
            - export
    OfferingCreate:
      type: object
      additionalProperties: false
      required:
      - term
      properties:
        course_id:
          type: integer
          minimum: 1
          description: 复用当前教师已有课程时传入，与 course_name 互斥
        course_name:
          type: string
          minLength: 1
          maxLength: 255
          description: 自动新建课程时传入，与 course_id 互斥
        class_group_id:
          type: integer
          minimum: 1
          description: 复用当前教师已有班级时传入，与 class_name 互斥
        class_name:
          type: string
          minLength: 1
          maxLength: 255
          description: 自动新建班级时传入，与 class_group_id 互斥
        term:
          type: string
          minLength: 1
          maxLength: 64
          description: 学期标识，如 2026-2027-1
      allOf:
      - oneOf:
        - required:
          - course_id
        - required:
          - course_name
      - oneOf:
        - required:
          - class_group_id
        - required:
          - class_name
    GradingTaskCreate:
      type: object
      additionalProperties: false
      required:
      - offering_id
      - task_name
      properties:
        offering_id:
          type: integer
          minimum: 1
          description: 必填，必须为当前教师获授权且具有 create_task 权限的授课班 ID
        assignment_id:
          type:
          - integer
          - 'null'
          minimum: 1
          description: 可选，关联所属课程下的课程作业 ID
        task_name:
          type: string
          minLength: 1
          maxLength: 255
        assignment_name:
          type: string
          maxLength: 255
          default: ''
        grading_instruction:
          type: string
          default: ''
    GradingTaskRead:
      type: object
      additionalProperties: false
      required:
      - id
      - offering_id
      - course_id
      - class_group_id
      - task_name
      - course_name
      - assignment_name
      - class_name
      - status
      - grading_instruction
      - is_archived
      - created_at
      - updated_at
      properties:
        id:
          type: integer
          minimum: 1
        offering_id:
          type: integer
          minimum: 1
        course_id:
          type: integer
          minimum: 1
        assignment_id:
          type:
          - integer
          - 'null'
          minimum: 1
        class_group_id:
          type: integer
          minimum: 1
        task_name:
          type: string
        course_name:
          type: string
          description: 由服务端按授课班生成的显示快照
        assignment_name:
          type: string
        class_name:
          type: string
          description: 由服务端按授课班生成的显示快照
        status:
          type: string
        grading_instruction:
          type: string
        is_archived:
          type: boolean
        archived_at:
          type:
          - string
          - 'null'
          format: date-time
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
    AdminTeacher:
      type: object
      additionalProperties: false
      required:
      - user_id
      - display_name
      - email
      - account_status
      - version
      properties:
        user_id:
          type: integer
          minimum: 1
        display_name:
          type: string
        email:
          type: string
          format: email
        account_status:
          $ref: '#/components/schemas/AccountStatus'
        status_reason:
          type:
          - string
          - 'null'
        version:
          type: integer
          minimum: 1
    TeacherAction:
      type: object
      additionalProperties: false
      required:
      - action
      - expected_version
      properties:
        action:
          type: string
          enum:
          - approve
          - reject
          - disable
        expected_version:
          type: integer
          minimum: 1
        reason:
          type: string
      allOf:
      - if:
          properties:
            action:
              enum:
              - reject
              - disable
        then:
          required:
          - reason
          properties:
            reason:
              type: string
              minLength: 1
    Error:
      type: object
      additionalProperties: false
      required:
      - code
      - message
      - request_id
      properties:
        code:
          type: string
        message:
          type: string
        status_reason:
          type:
          - string
          - 'null'
          description: 账号被驳回或停用时附带的原因说明
        request_id:
          type: string
  responses:
    E401:
      description: 没有有效会话、会话已被撤销或登录凭据无效
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    E403:
      description: 权限、账号状态或 CSRF 令牌不满足要求
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    E404:
      description: 对象不存在或不可见
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    E409:
      description: 操作依据的版本、业务状态冲突，或目标受保护不可删除
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    E422:
      description: 请求字段、互斥参数或验证令牌无效
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    E429:
      description: 请求过于频繁
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
```
