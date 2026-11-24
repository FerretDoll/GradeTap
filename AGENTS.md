# GradeTap 项目记忆

## Project Overview

GradeTap 是一个面向高校与高职教师的 AI 作业批改助手。目标不是把学生作业一次性丢给大模型批改，而是构建一条完整、可控、可追踪、可复核的批改流水线。

当前升级方向：将旧版“LLM 直接批改”升级为“证据-量规驱动的多智能体批改系统”。

核心用户是教师。产品表达应优先强调教师能获得的价值：上传作业，自动拆题，生成评分量规，提取评分证据，统一评分，分流复核，快速生成成绩表、学生反馈和班级分析报告。

关键原则：

- AI 负责初批，教师掌握最终评分权。
- 不要让大模型直接从学生原文给分。
- 先结构化，再评分；先找证据，再给分；先 AI 初批，再教师复核。
- 所有关键中间结果都应可查看、可修改、可重跑、可追踪。
- 优先按题批量批改，保证同一道题的评分标准一致。
- 每个最终分数都必须能追溯到题目、评分量规、评分证据、AI 评分理由和教师复核记录。
- 总分默认 100 分，每道题必须有明确分值、评分维度、得分条件、扣分条件和证据要求。

## Architecture Memory

推荐采用前后端分离架构。

- 前端：`Vue 3 + Vue Router + Element Plus + Pinia + Axios`；本地开发通过 Vite `/api` 代理同域转发后端并启用 `withCredentials: true`（同步将 `frontend/.env.example` 改为 `VITE_API_BASE_URL=/api`，并检查本地 `.env`/`.env.local` 不覆盖为跨源绝对地址）。
- 前端包管理：当前使用 `pnpm`，通过 `corepack pnpm install` 和 `corepack pnpm run dev/build` 执行。
- 后端：`Python FastAPI`（服务端会话 Cookie + CSRF 校验 + Alembic 迁移）。
- 异步任务与智能体运行：首轮最小闭环先用数据库运行表/步骤表实现可暂停恢复循环，后续按阶段接入 `Celery + Redis`（及按需 LangGraph 检查点）。
- 数据库：开发、回归测试和正式部署统一使用腾讯云 MySQL。开发库为 gradetap_dev，回归用例使用 gtcheck 前缀的隔离临时库，正式库为 gradetap_prod。开发机通过 SSH 本地端口 13306 连接，服务端应用通过回环地址连接。库表结构由 Alembic 管理，ORM 使用通用 sqlalchemy.JSON。
- 文件存储：MVP 可先用本地文件系统，代码结构预留 MinIO/OSS 接口。
- LLM 服务：所有模型调用统一封装在 `llm_service.py`，业务模块不要直接调用模型 API。

后端主要服务边界：

- 用户与班级管理。
- 文件管理与解析。
- 批改任务管理。
- 题目分析与评分量规生成。
- 学生作业解析与答案抽取。
- 评分证据提取。
- 基于证据的按题评分。
- 反思校准与复核分流。
- 教师复核与修订记录。
- 成绩管理、报告生成和导出。
- 审计日志与原始 LLM 输出追踪。

建议明确区分以下 Service / Agent：

- `FileParseService`
- `QuestionAnalyzerService`
- `RubricBuilderService`
- `StudentPrepareService`
- `AnswerExtractorService`
- `EvidenceExtractorService`
- `AnswerGrouperService`
- `GradingService`
- `ReflectorService`
- `ReviewRouterService`
- `TeacherReviewService`
- `SummaryService`
- `ExportService`
- `LLMService`
- `AuditLogService`

## Core Pipeline

新版核心批改流水线：

```text
parse_files
  -> analyze_questions
  -> build_rubrics
  -> teacher_confirm_rubrics
  -> prepare_students
  -> extract_answers
  -> extract_evidence
  -> grade_by_question
  -> reflect_grading
  -> route_review
  -> teacher_review
  -> export_results
  -> summary
```

教师视角可以继续包装成容易理解的 4 步：

1. 上传材料：作业要求、参考答案、学生作业。
2. 确认评分量规：AI 拆题、识别题型知识点、生成评分维度后，教师可修改。
3. 自动批改：抽取学生答案，提取评分证据，并按题统一评分。
4. 查看结果：复核异常项，确认最终分数，导出成绩表、学生反馈和班级分析。

模块职责：

- `parse_files`：解析作业要求与参考答案文件，MVP 支持 `.docx`、`.pdf`、`.txt`、`.md`。
- `analyze_questions`：识别题目、题型、知识点、难度和期望答案类型。
- `build_rubrics`：为每道题生成评分量规，包括评分维度、维度分值、得分条件、扣分条件和证据要求，并校验总分是否为 100。
- `teacher_confirm_rubrics`：教师查看、修改、确认评分量规。确认前不能进入正式批改。
- `prepare_students`：解析学生作业文件，提取学号、姓名和正文内容。
- `extract_answers`：从学生作业中按题抽取答案，规则优先，LLM 兜底。
- `extract_evidence`：针对每个学生每道题，根据评分量规提取正向证据和负向证据；此步骤不评分。
- `grade_by_question`：同一道题下批量批改所有学生答案，必须主要基于结构化评分证据评分。
- `reflect_grading`：检查 AI 初始评分是否与评分量规和证据一致，发现异常并建议重批或人工复核。
- `route_review`：根据置信度、异常类型、题目权重、抽检规则等标记需要教师复核的结果。
- `teacher_review`：教师查看证据、修改得分和评语、确认最终成绩，系统保存修订记录。
- `summary`：基于最终成绩生成成绩汇总、学生反馈、班级分析和报告导出数据。

Celery pipeline 中的 `wait_for_teacher_confirm_rubrics` 和 `wait_for_teacher_review` 是等待教师操作的状态，不应作为后台任务自动跑完。

## Backend Conventions

推荐后端目录结构以领域职责划分：

```text
backend/
  app/
    api/
    services/
    tasks/
    models/
    schemas/
    prompts/
    utils/
```

建议补充的后端文件：

```text
backend/app/api/
  task_api.py
  file_api.py
  question_api.py
  rubric_api.py
  answer_api.py
  evidence_api.py
  grading_api.py
  review_api.py
  export_api.py

backend/app/services/
  file_parse_service.py
  question_analyzer_service.py
  rubric_builder_service.py
  student_prepare_service.py
  answer_extractor_service.py
  evidence_extractor_service.py
  answer_grouper_service.py
  grading_service.py
  reflector_service.py
  review_router_service.py
  teacher_review_service.py
  summary_service.py
  export_service.py
  audit_log_service.py
  llm_service.py

backend/app/prompts/
  question_analyzer_prompt.py
  rubric_builder_prompt.py
  answer_extractor_prompt.py
  evidence_extractor_prompt.py
  grade_by_question_prompt.py
  reflector_prompt.py
  summary_prompt.py
```

实现约定：

- API 层只处理请求响应和权限校验，业务逻辑放在 `services/`。
- 长任务放入 Celery，不要在 HTTP 请求中同步跑完整批改流程。
- LLM prompt 模板放在 `prompts/`，不要散落在业务代码中。
- 文档解析工具放在 `utils/`，例如 `docx_parser.py`、`pdf_parser.py`、`excel_export.py`。
- 所有需要入库的 LLM 输出必须要求合法 JSON，不输出 Markdown 或解释文字。
- JSON 解析失败时建议三步处理：正常调用、要求模型修复 JSON、仍失败则标记人工复核。
- 保存 `raw_llm_output`，便于追踪争议和调试。
- 关键操作必须写入 `audit_log`：创建任务、上传文件、解析文件、生成题目、生成量规、修改量规、抽取答案、提取证据、AI 评分、反思校准、教师修改分数、教师确认最终成绩、导出成绩。

`LLMService` 建议提供统一 JSON 调用：

```python
class LLMService:
    def chat_json(self, prompt: str, schema: dict | None = None, max_retries: int = 3) -> dict:
        pass

    def chat_text(self, prompt: str, max_retries: int = 3) -> str:
        pass
```

`LLMService` 必须支持：

- JSON 解析失败自动重试。
- 非法字段自动修复或标记人工复核。
- 保存原始 LLM 输出 `raw_llm_output`。
- 调用失败写入任务错误日志。
- 支持后续切换不同模型。

## Prompt Conventions

`question_analyzer_prompt`：

- 只分析题目结构，不评分，不批改学生答案。
- 输出题号、题目内容、题型、知识点、难度、期望答案类型、排序。
- 只输出合法 JSON。

`rubric_builder_prompt`：

- 为每道题生成评分量规。
- 每个评分维度必须包括分值、得分条件、扣分条件和证据要求。
- 每道题的评分维度分值之和必须等于该题总分。
- 只输出合法 JSON。

`evidence_extractor_prompt`：

- 只提取证据，不给分。
- 对每个评分维度输出正向证据、负向证据和置信度。
- 找不到证据时使用空数组，不要编造。
- 只输出合法 JSON。

`grade_by_question_prompt`：

- 必须主要依据 `structured_evidence` 评分。
- 每个评分维度都必须给出分数和理由。
- 维度得分不得超过维度满分，总分必须等于各维度得分之和。
- 证据不足时不能随意给高分，应降低置信度并说明原因。
- 只输出合法 JSON。

`reflector_prompt`：

- 检查评分是否与评分量规和结构化证据一致。
- 至少检查：总分求和、负向证据却给满分、无正向证据却给高分、空答案给分、超过满分、扣分理由不匹配、字段缺失或 JSON 异常。
- 输出 `reflection_status`、`issues`、`suggested_action`、`calibrated_score`、`need_human_review`。
- 只输出合法 JSON。

## Frontend Conventions

当前前端是面向多教师与管理员的后台工作台，不做营销页。左侧主导航与视图按角色展示：

- `我的授课班` / `批改任务`：按当前授权的授课班筛选、创建、编辑、删除批改任务，点击任务名称进入任务详情。
- `课程管理`：维护已授权课程及课程作业（含备课草稿转课程作业），点击课程名称进入课程明细。
- `班级管理`：维护班级与学生名单；点击班级名称进入班级明细。
- `系统管理`（仅管理员可见）：教师账号审核/驳回/停用、授课班归属管理、共用大模型配置（`/api/settings/llm`）与运行审计。

新增页面（登录、注册、邮箱验证、待审核/驳回重提、管理员后台、授课班管理等）必须通过 `vue-router` 放在 `frontend/src/views/` 独立目录中，**禁止继续往现有 9,682 行 `App.vue` 堆叠新模块**。

任务详情页应展示升级后的流程步骤：

```text
文件解析
-> 题目分析
-> 量规生成
-> 量规确认
-> 学生解析
-> 答案抽取
-> 证据提取
-> AI评分
-> 反思校准
-> 教师复核
-> 结果导出
```

界面风格应是后台工具型，而不是营销页。优先使用 Element Plus 的稳定组件：

- 文件上传：`Upload`。
- 数据表格：`Table`。
- 表单编辑：`Form`。
- 流程进度：`Steps`、`Progress`。
- 详情查看：`Dialog`、`Drawer`。
- 状态展示：`Tag`。
- 分页：`Pagination`。

当前交互约定：

- 三个主列表的名称列都可点击进入明细页。
- 明细页必须提供 `返回上一页` 按钮；顶部也可提供返回列表操作。
- 课程、班级、批改任务列表的操作列使用编辑图标和删除图标，不使用文字“管理”按钮。
- 删除课程、班级、批改任务前必须弹出确认框。
- 切换左侧边栏和进入明细页时，右侧内容有轻微的浮动淡入动效，保持克制。
- 表格右侧的数字、状态和操作列居中显示。
- **严禁跨账号本地缓存合并**：多教师改造后废除 `taskStore.js` 的 `mergeTasks` 离线合并与 `App.vue` 中的业务 `localStorage` 缓存键；切换账号或退出登录时必须彻底清空 Pinia 状态与本地业务缓存，防止跨教师数据串号。
- 新建批改任务时绑定当前授权的 `offering_id`（授课班），课程名称与班级名称由后端保存为显示快照。
- 新建课程只包含课程名称和课程说明，不手动填写作业数量；作业数量默认从 0 开始。
- 新建班级只包含班级名称和备注；授课班（`offering`）关联课程、班级与学期（`term`），允许不同教师建立同名班并通过独立 `id` 隔离。

必须支持查看关键中间结果：

- 题目分析结果：题型、知识点、难度、期望答案类型。
- 评分量规：评分维度、维度分值、得分条件、扣分条件、证据要求。
- 学生答案抽取结果，包含 `matched`、`missing`、`ambiguous`、`manual_check` 等状态。
- 评分证据：每个评分维度的正向证据、负向证据和置信度。
- 按学生和按题查看批改结果。
- Reflector 发现的问题和建议操作。
- 教师修改单题得分、评语和复核状态。

前端页面升级重点：

- 原“分值标准确认页”升级为“评分量规确认页”，支持编辑评分维度、分值、得分条件、扣分条件和证据要求。
- 原“批改结果页”增加评分证据展示：题目、学生答案、评分量规、正向证据、负向证据、各维度得分、AI 评语、Reflector 问题、教师最终评分。
- 新增“教师复核中心”：按优先级、题目、异常类型筛选；支持修改分数和评语、批量确认无异常项。
- 新增“按题批改视图”：左侧题目列表与统计，中间学生答案和分数状态，右侧评分量规、常见错误和证据统计。

## Data Model Memory

主要数据表：

- `course`：课程，用于归档课程下的作业和历史批改资料。
- `class`：班级，用于组织学生和批改任务。
- `grading_task`：批改任务。
- `uploaded_file`：上传文件和解析文本。
- `question`：题目，应包含题型、知识点、难度、期望答案类型。
- `question_rubric`：评分量规，应包含评分维度、维度说明、分值、得分条件、扣分条件和证据要求。
- `student_submission`：学生提交。
- `student_answer`：按题抽取后的学生答案。
- `answer_evidence`：每个学生每道题每个评分维度的正向证据、负向证据、置信度和原始 LLM 输出。
- `answer_group`：相似答案分组。
- `answer_group_member`：分组成员。
- `grading_result`：AI 批改结果、维度得分、置信度、复核分流信息和最终成绩。
- `grading_deduction`：扣分明细。
- `grading_reflection`：反思校准结果、异常问题、建议操作、是否需要人工复核。
- `teacher_revision`：教师修改记录。
- `adaptive_grading_rule`：从教师修改中沉淀的可复用评分规则，后置实现。
- `audit_log`：关键操作日志。

前端当前数据展示补充约定：

- `course` 展示课程名称、课程说明和作业数量；授课班（`offering`）展示课程名称、班级名称、学期（`term`）与当前教师角色。
- `class` 展示班级名称、备注和学生数。
- `grading_task` 展示任务名称、课程、班级、状态和操作；操作为编辑/删除图标。
- 现有已落地的查重表（`plagiarism_check`、`student_plagiarism_summary`、`plagiarism_match`）与课程作业表（`course_assignment` 等）须同步纳入授课班权限范围校验与数据迁移清单。

任务状态建议：

```text
created
files_uploaded
parsed
questions_analyzed
rubrics_generated
waiting_rubric_confirm
rubrics_confirmed
students_prepared
answers_extracted
evidence_extracted
grading
graded
reflecting
reflected
review_routed
waiting_teacher_review
teacher_reviewed
exported
summary_generated
failed
```

文件角色建议：

```text
requirement
reference_answer
student_submission
report
```

答案抽取状态建议：

```text
matched
missing
ambiguous
manual_check
extract_error
```

批改状态建议：

```text
correct
partial
incorrect
missing
need_review
extract_error
evidence_error
```

复核状态建议：

```text
ai_generated
teacher_confirmed
teacher_modified
system_regraded
```

Review priority 建议：

```text
low
medium
high
urgent
```

## API Memory

主要接口族以 `/api/tasks` 为中心。

基础任务与文件：

- `POST /api/tasks`：创建批改任务。
- `POST /api/tasks/{task_id}/files`：上传作业要求、参考答案或学生作业。
- `POST /api/tasks/{task_id}/parse-files`：解析作业要求和参考答案。

题目与量规：

- `POST /api/tasks/{task_id}/analyze-questions`：识别题目、题型、知识点、难度和期望答案类型。
- `POST /api/tasks/{task_id}/build-rubrics`：为每道题生成评分量规。
- `GET /api/tasks/{task_id}/questions`：获取题目和评分量规。
- `PUT /api/tasks/{task_id}/questions`：教师确认或修改题目与评分量规。

学生答案与证据：

- `POST /api/tasks/{task_id}/prepare-students`：准备学生作业。
- `POST /api/tasks/{task_id}/extract-answers`：抽取学生答案。
- `POST /api/tasks/{task_id}/extract-evidence`：提取每个评分维度的正向证据和负向证据。
- `POST /api/tasks/{task_id}/group-answers`：相似答案分组，非 MVP 必需。

评分、反思与复核：

- `POST /api/tasks/{task_id}/grade-by-question`：按题批改，内部必须读取 `student_answer`、`answer_evidence` 和 `question_rubric`，基于证据评分。
- `POST /api/tasks/{task_id}/reflect-grading`：检查评分与证据是否一致，标记异常结果。
- `POST /api/tasks/{task_id}/route-review`：标记哪些结果需要教师复核。
- `GET /api/tasks/{task_id}/review-items`：获取教师复核列表，支持按 `review_required`、`review_priority`、`question_id`、`student_id`、`grading_status` 筛选。
- `GET /api/grading-results/{result_id}/evidence`：查看某个批改结果对应的评分量规、证据、AI 理由和 Reflector 问题。
- `POST /api/tasks/{task_id}/questions/{question_id}/regrade`：重批某一道题。
- `PUT /api/tasks/{task_id}/grading-results/{result_id}/review`：教师修改最终得分、最终评语和修订原因。
- `POST /api/tasks/{task_id}/confirm-results`：教师确认最终成绩。

汇总与导出：

- `POST /api/tasks/{task_id}/summary`：生成汇总报告。
- `GET /api/tasks/{task_id}/export/excel`：导出成绩。
- `GET /api/tasks/{task_id}/export/report`：导出报告。

接口实现应和数据模型、任务状态流转保持一致。

## MVP Scope

第一阶段目标是跑通证据-量规驱动的核心闭环。

必须实现：

- 课程管理：新增、编辑、删除、查看课程明细。
- 班级管理：新增、编辑、删除、查看班级明细。
- 创建批改任务。
- 批改任务列表：新增、编辑、删除、查看任务明细。
- 上传作业要求、参考答案和学生作业。
- 解析 `.docx`、`.pdf`、`.txt` 文件。
- 题目分析：识别题目、题型、知识点、难度和期望答案类型。
- 评分量规生成：评分维度、分值、得分条件、扣分条件和证据要求。
- 教师确认或修改评分量规。
- 解析学生姓名、学号和作业内容。
- 从学生作业中按题抽取答案。
- 针对每个学生每道题提取评分证据。
- 按题批量批改所有学生答案，评分必须基于证据。
- 反思校准并标记明显不合理的 AI 评分。
- 自动分流需要教师复核的结果。
- 教师查看证据、修改最终分数和评语。
- 保存教师修改记录。
- 生成学生总分表。
- 导出 Excel，导出时优先使用 `final_score`，没有最终分数时再使用 AI 分数。

本次升级优先完成：

1. 将 `set_score` 拆成 `question_analyzer` 和 `rubric_builder`。
2. 扩展 `question` 和 `question_rubric` 表。
3. 新增 `answer_evidence` 表和 `evidence_extractor_service`。
4. 修改 `grade_by_question`，让它基于 `answer_evidence` 评分。
5. 新增 `grading_reflection` 表和 `reflector_service`。
6. 新增 `review_router_service`，并在 `grading_result` 中标记 `review_required`。
7. 新增 `teacher_revision` 表和 `teacher_review_service`。
8. 前端分值确认页升级为评分量规确认页。
9. 前端批改详情页增加评分证据展示。
10. Celery pipeline 增加 `extract_evidence`、`reflect_grading`、`route_review` 三个阶段。

可后置到增强版本：

- 批改报告生成。
- 班级统计分析。
- 教师人工复核的高级批量能力。
- 单题重批。
- 异常答案提示。
- 学生个性化反馈。
- 相似答案分组。
- 随机审计与防止形式化复核。

可后置到专业版本：

- SQL / Python / Java 自动运行验证。
- 查重检测。
- 历史评分标准库。
- 优秀答案库。
- 从教师修改中学习自适应评分规则。
- RAG 学习反馈。
- 课程知识点掌握分析。
- 学情画像。
- 教学改进建议。
- 公平性与偏见检查。
- 课堂讲评 PPT 大纲生成。

当前不要做：

- 暂时不要实现复杂 RAG。
- 暂时不要实现长期学生画像。
- 暂时不要实现代码沙箱执行（上传代码只读解析）。
- 暂时不要实现公平性检测。

注：多教师账号认证、授课班权限隔离、`/api/settings/llm` 收归管理员以及双智能体改造已纳入当前第一阶段核心范围，不再排除；且：
- `POST /api/tasks/{task_id}/export-results` 按 `release_id` 导出正式版时必须以服务端发布快照为准，忽略客户端传入的修订分数。
- 已有教师修订或已发布成绩的任务禁止物理删除（`DELETE /api/tasks/{task_id}` 返 `409`），改走 `POST /api/tasks/{task_id}/archive` 归档；任何删除操作均禁止物理清除 `AuditLog`。

## Export Memory

Excel 总表建议字段：

- 学号
- 姓名
- 各题 AI 分数
- 各题最终分数
- 总分
- 是否教师修改
- 是否需要复核
- 复核状态
- 主要扣分原因
- 总体评语

按题详细表建议字段：

- 学号
- 姓名
- 题号
- 题目分值
- AI 分数
- 最终分数
- 评分维度得分
- 正向证据
- 负向证据
- AI 评语
- 教师评语
- 复核状态

Summary 输入应优先使用 `final_score`，没有 `final_score` 时再使用 AI `score`。Summary 至少包括：

- 班级平均分、最高分、最低分。
- 各题平均分、得分率。
- 高频扣分点。
- 需要重点讲解的知识点。
- 需要复核或关注的学生。

## Risks And Rules

LLM 批改不稳定：

- 使用固定评分量规。
- 先提取证据，再基于证据评分。
- 按题批改，减少评分漂移。
- 输出 JSON 并做结构校验。
- 支持重批某一道题。
- 保留原始模型输出。

学生答案抽取错位：

- 规则抽取优先，LLM 只做兜底。
- 每题输出 `confidence` 和状态。
- 前端明确标记异常与不确定项。
- 支持人工修正答案映射。

评分证据不足或错误：

- `EvidenceExtractorService` 不允许给分，只能提取证据。
- 每个评分维度都必须有证据字段；没有证据时输出空数组。
- 证据置信度低于 0.8 时进入教师复核候选。
- 保存 `raw_llm_output` 以便追踪。

AI 评分与证据不一致：

- `ReflectorService` 必须检查总分求和、证据冲突、空答案给分、超分、理由与量规不匹配等问题。
- `ReviewRouterService` 必须将明显异常、低置信度、高权重题异常和抽检样本送入教师复核。

学生人数过多导致上下文过长：

- 按题批改。
- 同一道题再按学生分批，建议每批 10 到 20 人。
- 每批使用同一套评分量规。
- 异常批次单独重试或人工复核。

参考答案不完整：

- 允许教师补充批改说明。
- 允许教师编辑评分量规。
- LLM 批改时同时参考题目、参考答案、评分量规和结构化证据。
- 对开放题可标记参考答案仅供参考。

代码类作业只靠 LLM 不可靠：

- 后续应增加 SQL、Python、Java 等自动运行验证。
- 将运行结果、错误信息和测试结果提供给 LLM 辅助评分。
- 不要仅凭自然语言描述判断代码正确性。

教师复核规则：

- 答案抽取置信度低于 0.8，应进入复核。
- 证据提取置信度低于 0.8，应进入复核。
- Reflector 标记 `need_human_review = true`，必须进入复核。
- 学生答案为空但 Grader 给了分，必须进入复核。
- 同组答案分差异常，应进入复核。
- 高权重题得分异常，应进入复核。
- 题目分值超过 20 分且置信度不足，应进入复核。
- 系统应支持随机抽检样本。

## Acceptance Criteria

本次升级完成后，系统至少应该做到：

- 教师上传作业后，系统能识别题目、题型和知识点。
- 系统能为每道题生成评分量规，而不是只有一个总分。
- 系统能从学生答案中提取每个评分维度对应的正向证据和负向证据。
- 系统评分时必须基于证据，而不是直接黑盒评分。
- 每个学生每道题都能查看评分依据。
- 系统能发现明显不合理的 AI 评分，并标记需要教师复核。
- 教师能修改最终分数和评语。
- 教师修改记录能保存。
- 成绩导出使用最终分数。
- 所有关键中间结果都入库，便于调试、复核和后续优化。

## Server Access Memory

- 服务器运维记录保存在本机 `docs/01_开发文档/GradeTap_服务器SSH连接说明.md`。在有访问权限的开发机上处理服务器任务前，先查阅这份说明。
- 当前 Windows 开发机已配置 `ssh gradetap`，2026-11-24 已验证连通。
- 远端部署目录、运行服务和 sudo 权限尚未核验；SSH 连通不代表应用已经部署。

## Source Of Truth

本文件是给 Codex / Claude 和开发者的快速项目记忆。项目材料统一从 [docs/README.md](docs/README.md) 查阅。

当前阶段的执行口径（多教师账号、授课班隔离、双智能体与阶段化开发分工）以以下三份文档为准：
- [GradeTap_智能体改造开发方案](docs/01_开发文档/GradeTap_智能体改造开发方案.md)
- [GradeTap_第一阶段开发计划与前后端分工](docs/01_开发文档/GradeTap_第一阶段开发计划与前后端分工.md)
- [GradeTap_Claude前端开工包](docs/01_开发文档/GradeTap_Claude前端开工包.md)

基础表结构、SQL、Prompt 模板与证据-量规升级基础原则可继续查阅 [架构设计](docs/02_架构设计/大模型自动批改作业网站_架构设计.md) 与 [AI作业批改系统_旧版框架升级修改说明](docs/02_架构设计/AI作业批改系统_旧版框架升级修改说明.md)；若旧文档与上述本轮开发文档存在冲突，以本轮开发文档为准。
