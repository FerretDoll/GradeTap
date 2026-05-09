# GradeTap 项目记忆

## Project Overview

GradeTap 是一个面向高校与高职教师的 AI 作业批改助手。目标不是把学生作业一次性丢给大模型批改，而是构建一条完整、可控、可追踪、可复核的批改流水线。

核心用户是教师。产品表达应优先强调教师能获得的价值：上传作业，自动拆题，统一评分，快速生成成绩表、学生反馈和班级分析报告。

关键原则：

- AI 负责初批，教师掌握最终评分权。
- 所有关键中间结果都应可查看、可修改、可重跑。
- 优先按题批量批改，保证同一道题的评分标准一致。
- 总分默认 100 分，每道题必须有明确分值和评分细则。

## Architecture Memory

推荐采用前后端分离架构。

- 前端：`Vue 3 + Element Plus + Pinia + Axios`。
- 前端包管理：当前使用 `pnpm`，通过 `corepack pnpm install` 和 `corepack pnpm run dev/build` 执行。
- 后端：`Python FastAPI`。
- 异步任务：`Celery + Redis`。
- 数据库：`PostgreSQL` 或 `MySQL`，用于结构化业务数据。
- 文件存储：MVP 可先用本地文件系统，代码结构预留 MinIO/OSS 接口。
- LLM 服务：所有模型调用统一封装在 `llm_service.py`，业务模块不要直接调用模型 API。

后端主要服务边界：

- 用户与班级管理。
- 文件管理与解析。
- 批改任务管理。
- LLM 调用服务。
- 成绩管理。
- 报告生成。

## Core Pipeline

核心批改流水线：

```text
parse_files -> set_score -> prepare_students -> extract_answers -> group_answers -> grade_by_question -> teacher_review -> summary
```

模块职责：

- `parse_files`：解析作业要求与参考答案文件，MVP 支持 `.docx`、`.pdf`、`.txt`、`.md`。
- `set_score`：调用 LLM 生成题目、分值和评分细则，并校验总分是否为 100。
- `prepare_students`：解析学生作业文件，提取学号、姓名和正文内容。
- `extract_answers`：从学生作业中按题抽取答案，规则优先，LLM 兜底。
- `group_answers`：按同一道题聚类相似答案，便于教师批量复核；不是 MVP 必需项。
- `grade_by_question`：同一道题下批量批改所有学生答案，保持评分一致。
- `teacher_review`：教师查看、修改、确认 AI 初批结果。
- `summary`：生成成绩汇总、学生反馈、班级分析和报告导出数据。

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

实现约定：

- API 层只处理请求响应和权限校验，业务逻辑放在 `services/`。
- 长任务放入 Celery，不要在 HTTP 请求中同步跑完整批改流程。
- LLM prompt 模板放在 `prompts/`，不要散落在业务代码中。
- 文档解析工具放在 `utils/`，例如 `docx_parser.py`、`pdf_parser.py`、`excel_export.py`。
- 所有需要入库的 LLM 输出必须要求合法 JSON，不输出 Markdown 或解释文字。
- JSON 解析失败时建议三步处理：正常调用、要求模型修复 JSON、仍失败则标记人工复核。
- 保存 `raw_llm_output`，便于追踪争议和调试。

## Frontend Conventions

当前前端是教师工作台，不做营销页。左侧主导航包含：

- `批改任务`：创建、编辑、删除批改任务，点击任务名称进入任务详情。
- `课程管理`：维护课程列表，课程用于归档该课程相关作业；点击课程名称进入课程明细。
- `班级管理`：维护班级列表；点击班级名称进入班级明细。

进入单个批改任务后，再展示复杂后端流水线，并包装成教师容易理解的 4 步：

1. 上传材料：作业要求、参考答案、学生作业。
2. 确认评分标准：AI 拆题和设分后，教师可修改。
3. 自动批改：抽取学生答案，并按题统一批改。
4. 查看结果：成绩表、学生反馈、班级分析和导出。

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
- 任务创建采用乐观更新：点击创建后立即显示在批改任务列表中；后端不可用时也保留本地任务。
- 当前前端任务列表使用 `localStorage` 键 `gradetap.tasks` 保存本地任务，避免刷新丢失。
- 新建批改任务时，`课程名称` 和 `班级名称` 使用下拉菜单，选项来自课程管理和班级管理。
- 新建课程只包含课程名称和课程说明，不手动填写作业数量；作业数量默认从 0 开始。
- 新建班级只包含班级名称和备注。

必须支持查看关键中间结果：

- 分值标准与评分细则。
- 学生答案抽取结果，包含 `matched`、`missing`、`ambiguous`、`manual_check` 等状态。
- 按学生和按题查看批改结果。
- 教师修改单题得分、评语和复核状态。

## Data Model Memory

主要数据表：

- `course`：课程，用于归档课程下的作业和历史批改资料。
- `class`：班级，用于组织学生和批改任务。
- `grading_task`：批改任务。
- `uploaded_file`：上传文件和解析文本。
- `question`：题目。
- `question_rubric`：评分细则。
- `student_submission`：学生提交。
- `student_answer`：按题抽取后的学生答案。
- `answer_group`：相似答案分组。
- `answer_group_member`：分组成员。
- `grading_result`：批改结果。
- `grading_deduction`：扣分明细。

前端当前临时数据约定：

- `course` 只展示课程名称、课程说明和作业数量；不展示任课教师、参考答案数、批改要求数。
- `class` 只展示班级名称、备注和学生数；不展示默认课程和学期。
- `grading_task` 展示任务名称、课程、班级、状态和操作；操作为编辑/删除图标。

任务状态建议：

```text
created
files_uploaded
parsed
score_generated
score_confirmed
students_prepared
answers_extracted
answers_grouped
grading
graded
reviewing
reviewed
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

批改状态建议：

```text
correct
partial
incorrect
missing
need_review
extract_error
```

复核状态建议：

```text
ai_generated
teacher_modified
teacher_confirmed
```

## API Memory

主要接口族以 `/api/tasks` 为中心：

- `POST /api/tasks`：创建批改任务。
- `POST /api/tasks/{task_id}/files`：上传作业要求、参考答案或学生作业。
- `POST /api/tasks/{task_id}/parse-files`：解析作业要求和参考答案。
- `POST /api/tasks/{task_id}/set-score`：生成题目、分值和评分细则。
- `GET /api/tasks/{task_id}/questions`：获取分值标准。
- `PUT /api/tasks/{task_id}/questions`：教师确认或修改分值标准。
- `POST /api/tasks/{task_id}/prepare-students`：准备学生作业。
- `POST /api/tasks/{task_id}/extract-answers`：抽取学生答案。
- `POST /api/tasks/{task_id}/group-answers`：相似答案分组。
- `POST /api/tasks/{task_id}/grade-by-question`：按题批改。
- `POST /api/tasks/{task_id}/questions/{question_id}/regrade`：重批某一道题。
- `PUT /api/tasks/{task_id}/grading-results/{result_id}`：教师修改批改结果。
- `POST /api/tasks/{task_id}/confirm-results`：教师确认最终成绩。
- `POST /api/tasks/{task_id}/summary`：生成汇总报告。
- `GET /api/tasks/{task_id}/export/excel`：导出成绩。
- `GET /api/tasks/{task_id}/export/report`：导出报告。

接口实现应和数据模型、任务状态流转保持一致。

## MVP Scope

第一阶段目标是跑通核心闭环。

必须实现：

- 课程管理：新增、编辑、删除、查看课程明细。
- 班级管理：新增、编辑、删除、查看班级明细。
- 创建批改任务。
- 批改任务列表：新增、编辑、删除、查看任务明细。
- 上传作业要求、参考答案和学生作业。
- 解析 `.docx`、`.pdf`、`.txt` 文件。
- 调用 LLM 生成题目、分值和评分细则。
- 教师确认评分标准。
- 解析学生姓名、学号和作业内容。
- 从学生作业中按题抽取答案。
- 按题批量批改所有学生答案。
- 生成学生总分表。
- 导出 Excel。

可后置到增强版本：

- 批改报告生成。
- 班级统计分析。
- 教师人工复核的高级批量能力。
- 单题重批。
- 异常答案提示。
- 学生个性化反馈。
- 相似答案分组。

可后置到专业版本：

- SQL / Python / Java 自动运行验证。
- 查重检测。
- 历史评分标准库。
- 优秀答案库。
- 课程知识点掌握分析。
- 学情画像。
- 教学改进建议。
- 课堂讲评 PPT 大纲生成。

## Risks And Rules

LLM 批改不稳定：

- 使用固定评分细则。
- 按题批改，减少评分漂移。
- 输出 JSON 并做结构校验。
- 支持重批某一道题。
- 保留原始模型输出。

学生答案抽取错位：

- 规则抽取优先，LLM 只做兜底。
- 每题输出 `confidence` 和状态。
- 前端明确标记异常与不确定项。
- 支持人工修正答案映射。

学生人数过多导致上下文过长：

- 按题批改。
- 同一道题再按学生分批，建议每批 10 到 20 人。
- 每批使用同一套评分细则。
- 异常批次单独重试或人工复核。

参考答案不完整：

- 允许教师补充批改说明。
- 允许教师编辑评分细则。
- LLM 批改时同时参考题目、参考答案和评分点。
- 对开放题可标记参考答案仅供参考。

代码类作业只靠 LLM 不可靠：

- 后续应增加 SQL、Python、Java 等自动运行验证。
- 将运行结果、错误信息和测试结果提供给 LLM 辅助评分。
- 不要仅凭自然语言描述判断代码正确性。

## Source Of Truth

本文件是给 Codex 和开发者的快速项目记忆。详细架构、SQL、Prompt 模板和页面表格仍以根目录的 `大模型自动批改作业网站_架构设计.md` 为准。
