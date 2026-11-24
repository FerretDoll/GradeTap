# AI作业批改系统：旧版基础框架升级修改说明

> 适用场景：你已经根据旧版开发指南完成了一个基础框架，现在需要在原有项目基础上升级为“证据—量规驱动的多智能体批改系统”。\
> 本文档不是重写整个系统，而是告诉 Codex：**在现有框架上需要新增、修改、重构哪些部分**。

---

## 0. 本次升级目标

旧版系统主要是线性流水线：

```text
parse_files
  → set_score
  → prepare_students
  → extract_answers
  → grade_by_question
  → summary
```

本次升级目标是将其改造为：

```text
文件解析
  → 题目理解
  → 评分量规生成
  → 学生作业解析
  → 学生答案抽取
  → 评分证据提取
  → 按题批改
  → 反思校准
  → 教师复核分流
  → 结果导出与学情分析
```

核心变化：

```text
不要让大模型直接从学生原文给分。
必须先抽取评分证据，再基于评分证据进行评分。
```

系统升级后的核心原则：

```text
先结构化，再评分；
先找证据，再给分；
先AI初批，再教师复核；
先保证可信，再追求自动化。
```

---

## 1. 总体架构需要调整

### 1.1 旧版架构的问题

旧版架构中，LLM 的主要作用是：

```text
1. 根据作业要求设置分值
2. 从学生作业中抽取答案
3. 根据题目、参考答案和学生答案直接评分
4. 生成汇总报告
```

这个模式存在问题：

1. 大模型直接评分，过程偏黑盒。
2. 教师很难知道扣分依据。
3. 学生申诉时缺少可追溯证据。
4. 同类答案可能出现分数不一致。
5. 异常样本不能自动进入人工复核。

---

### 1.2 新版架构

新版架构要改为：

```text
Parse
  → Question Analyze
  → Rubric Build
  → Student Prepare
  → Answer Extract
  → Evidence Extract
  → Grade
  → Reflect
  → Review Route
  → Teacher Review
  → Export / Summary
```

建议在代码中明确区分以下 Agent / Service：

```text
FileParseService
QuestionAnalyzerService
RubricBuilderService
StudentPrepareService
AnswerExtractorService
EvidenceExtractorService
AnswerGrouperService
GradingService
ReflectorService
ReviewRouterService
TeacherReviewService
SummaryService
ExportService
LLMService
AuditLogService
```

---

## 2. 原有模块修改清单

| 旧模块 | 处理方式 | 新模块 / 新职责 |
|---|---|---|
| parse_files | 保留并增强 | FileParseService |
| set_score | 拆分重构 | QuestionAnalyzerService + RubricBuilderService |
| prepare_students | 保留并增强 | StudentPrepareService |
| extract_answers | 保留并增强 | AnswerExtractorService |
| grade_by_question | 重大重构 | EvidenceExtractorService + GradingService + ReflectorService |
| summary | 延后增强 | SummaryService + TeachingAnalysis |
| 无 | 新增 | ReviewRouterService |
| 无 | 新增 | TeacherReviewService |
| 无 | 新增 | AuditLogService |
| 无 | 可选新增 | AnswerGrouperService |
| 无 | 可选新增 | AdaptiveRuleService |

---

## 3. 目录结构修改建议

如果旧项目已经有类似目录，请在原结构基础上补充以下文件。

```text
backend/
├── app/
│   ├── api/
│   │   ├── task_api.py
│   │   ├── file_api.py
│   │   ├── question_api.py
│   │   ├── rubric_api.py
│   │   ├── answer_api.py
│   │   ├── evidence_api.py
│   │   ├── grading_api.py
│   │   ├── review_api.py
│   │   └── export_api.py
│   │
│   ├── services/
│   │   ├── file_parse_service.py
│   │   ├── question_analyzer_service.py
│   │   ├── rubric_builder_service.py
│   │   ├── student_prepare_service.py
│   │   ├── answer_extractor_service.py
│   │   ├── evidence_extractor_service.py
│   │   ├── answer_grouper_service.py
│   │   ├── grading_service.py
│   │   ├── reflector_service.py
│   │   ├── review_router_service.py
│   │   ├── teacher_review_service.py
│   │   ├── summary_service.py
│   │   ├── export_service.py
│   │   ├── audit_log_service.py
│   │   └── llm_service.py
│   │
│   ├── models/
│   │   ├── task.py
│   │   ├── file.py
│   │   ├── question.py
│   │   ├── rubric.py
│   │   ├── student_submission.py
│   │   ├── student_answer.py
│   │   ├── answer_evidence.py
│   │   ├── answer_group.py
│   │   ├── grading_result.py
│   │   ├── grading_reflection.py
│   │   ├── teacher_revision.py
│   │   ├── adaptive_grading_rule.py
│   │   └── audit_log.py
│   │
│   ├── prompts/
│   │   ├── question_analyzer_prompt.py
│   │   ├── rubric_builder_prompt.py
│   │   ├── answer_extractor_prompt.py
│   │   ├── evidence_extractor_prompt.py
│   │   ├── grade_by_question_prompt.py
│   │   ├── reflector_prompt.py
│   │   └── summary_prompt.py
│   │
│   └── tasks/
│       ├── grading_pipeline.py
│       └── celery_tasks.py
```

---

## 4. set_score 需要拆成两个模块

旧版：

```text
set_score
输入：作业要求文本、批改说明
输出：分值标准列表
```

新版不要只做 set_score，而是拆成：

```text
question_analyzer
rubric_builder
```

---

### 4.1 新增 question_analyzer

#### 功能

识别作业中的题目、题型、知识点和难度。

#### 输入

```json
{
  "task_id": 1,
  "requirement_text": "作业要求全文",
  "reference_text": "参考答案全文",
  "grading_instruction": "教师补充批改说明"
}
```

#### 输出

```json
{
  "questions": [
    {
      "question_no": "1",
      "question_type": "SQL编程题",
      "question_content": "查询年龄大于18岁的学生信息",
      "knowledge_points": ["SELECT查询", "WHERE条件", "字段选择"],
      "difficulty": "中等",
      "expected_answer_type": "SQL代码",
      "sort_order": 1
    }
  ]
}
```

#### 数据库修改

如果原有 `question` 表没有以下字段，请补充：

```sql
ALTER TABLE question ADD COLUMN question_type VARCHAR(100);
ALTER TABLE question ADD COLUMN knowledge_points JSON;
ALTER TABLE question ADD COLUMN difficulty VARCHAR(50);
ALTER TABLE question ADD COLUMN expected_answer_type VARCHAR(100);
```

---

### 4.2 新增 rubric_builder

#### 功能

为每道题生成评分量规，而不是只生成总分。

#### 输入

```json
{
  "question": {},
  "reference_answer": "...",
  "grading_instruction": "..."
}
```

#### 输出

```json
{
  "question_no": "1",
  "total_score": 20,
  "rubrics": [
    {
      "rubric_id": "R1",
      "dimension": "语法正确性",
      "description": "SQL语句结构正确，可以正常执行",
      "score": 5,
      "positive_condition": "包含完整 SELECT ... FROM ... 结构，无明显语法错误",
      "negative_condition": "SQL结构缺失，存在明显语法错误",
      "evidence_required": "是否存在完整SQL结构，是否存在语法错误"
    }
  ]
}
```

#### 数据库修改

旧版如果已有 `question_rubric` 表，需要增加以下字段：

```sql
ALTER TABLE question_rubric ADD COLUMN dimension VARCHAR(255);
ALTER TABLE question_rubric ADD COLUMN description TEXT;
ALTER TABLE question_rubric ADD COLUMN positive_condition TEXT;
ALTER TABLE question_rubric ADD COLUMN negative_condition TEXT;
ALTER TABLE question_rubric ADD COLUMN evidence_required TEXT;
```

如果没有该表，则创建：

```sql
CREATE TABLE question_rubric (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    question_id BIGINT NOT NULL,
    dimension VARCHAR(255),
    description TEXT,
    rubric_item TEXT,
    score DECIMAL(5,2),
    positive_condition TEXT,
    negative_condition TEXT,
    evidence_required TEXT,
    sort_order INT,
    created_at DATETIME
);
```

---

## 5. grade_by_question 需要重构为三步

旧版：

```text
grade_by_question:
题目 + 参考答案 + 评分标准 + 学生答案 → LLM直接给分
```

新版：

```text
evidence_extractor:
题目 + 评分量规 + 学生答案 → 结构化评分证据

grading_service:
题目 + 评分量规 + 结构化证据 → 初始分数

reflector_service:
初始分数 + 结构化证据 + 评分量规 → 反思校准 / 标记异常
```

---

## 6. 新增 evidence_extractor

这是本次升级最关键的模块。

### 6.1 功能

不评分，只提取证据。

也就是说，它不回答：

```text
这个学生得多少分？
```

只回答：

```text
这个学生答案中有哪些内容支持或不支持每个评分点？
```

---

### 6.2 输入

```json
{
  "task_id": 1,
  "question": {
    "id": 1,
    "question_no": "1",
    "question_content": "查询年龄大于18岁的学生信息"
  },
  "rubrics": [
    {
      "rubric_id": 1,
      "dimension": "查询逻辑",
      "score": 8,
      "positive_condition": "包含正确 WHERE 条件",
      "negative_condition": "缺少核心筛选条件或条件错误",
      "evidence_required": "是否包含符合题意的 WHERE 条件"
    }
  ],
  "student_answer": {
    "id": 1001,
    "student_no": "20240101",
    "student_name": "张三",
    "answer_text": "SELECT * FROM student WHERE age > 18;"
  }
}
```

---

### 6.3 输出

```json
{
  "student_answer_id": 1001,
  "question_no": "1",
  "evidence": [
    {
      "rubric_id": 1,
      "dimension": "查询逻辑",
      "positive_evidence": [
        "答案包含 WHERE age > 18 条件"
      ],
      "negative_evidence": [],
      "evidence_confidence": 0.95
    }
  ]
}
```

---

### 6.4 新增数据库表

```sql
CREATE TABLE answer_evidence (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL,
    student_answer_id BIGINT NOT NULL,
    rubric_id BIGINT NOT NULL,
    positive_evidence TEXT,
    negative_evidence TEXT,
    confidence DECIMAL(5,4),
    raw_llm_output LONGTEXT,
    created_at DATETIME
);
```

说明：

- `positive_evidence` 可以存 JSON 字符串。
- `negative_evidence` 可以存 JSON 字符串。
- 必须保留 `raw_llm_output`，方便调试。

---

## 7. grading_service 需要改为基于证据评分

旧版评分输入里可以直接包含学生答案，但新版必须优先使用 `answer_evidence`。

### 7.1 新版输入

```json
{
  "question": {},
  "rubrics": [],
  "student_answer": {},
  "structured_evidence": []
}
```

### 7.2 新版输出

```json
{
  "student_no": "20240101",
  "question_no": "1",
  "score": 16,
  "max_score": 20,
  "rubric_scores": [
    {
      "rubric_id": 1,
      "dimension": "语法正确性",
      "score": 5,
      "max_score": 5,
      "reason": "SQL语句结构完整，无明显语法错误"
    },
    {
      "rubric_id": 2,
      "dimension": "查询逻辑",
      "score": 6,
      "max_score": 8,
      "reason": "包含主要筛选条件，但未限定专业字段"
    }
  ],
  "comment": "整体语法正确，但查询条件不够完整。"
}
```

### 7.3 grading_result 表修改

如果旧版表中没有以下字段，请增加：

```sql
ALTER TABLE grading_result ADD COLUMN evidence_based BOOLEAN DEFAULT TRUE;
ALTER TABLE grading_result ADD COLUMN rubric_scores JSON;
ALTER TABLE grading_result ADD COLUMN grading_confidence DECIMAL(5,4);
ALTER TABLE grading_result ADD COLUMN grading_status VARCHAR(50);
```

`grading_status` 建议取值：

```text
correct
partial
incorrect
missing
need_review
extract_error
evidence_error
```

---

## 8. 新增 reflector_service

### 8.1 功能

检查 AI 初始评分是否与证据一致。

### 8.2 检查规则

Reflector 至少检查：

```text
1. 总分是否等于各评分点得分之和
2. 是否存在负向证据但该评分点给了满分
3. 是否没有正向证据却给了高分
4. 是否答案为空但给了分
5. 是否同一相似答案组内分差过大
6. 是否扣分理由和评分量规不匹配
7. 是否超过该题满分
8. 是否出现 JSON 格式异常或字段缺失
```

---

### 8.3 输入

```json
{
  "grading_result": {},
  "rubrics": [],
  "structured_evidence": [],
  "student_answer": {}
}
```

---

### 8.4 输出

```json
{
  "reflection_status": "warning",
  "issues": [
    {
      "type": "score_evidence_mismatch",
      "message": "查询逻辑维度存在负向证据，但该维度给了满分"
    }
  ],
  "suggested_action": "human_review",
  "calibrated_score": 14,
  "need_human_review": true
}
```

---

### 8.5 新增数据库表

```sql
CREATE TABLE grading_reflection (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL,
    grading_result_id BIGINT NOT NULL,
    reflection_status VARCHAR(50),
    issues JSON,
    suggested_action VARCHAR(100),
    calibrated_score DECIMAL(5,2),
    need_human_review BOOLEAN,
    raw_llm_output LONGTEXT,
    created_at DATETIME
);
```

---

## 9. 新增 review_router_service

### 9.1 功能

决定哪些批改结果需要教师复核。

旧版可能是全部结果都让教师看，或者全部自动通过。新版要做“智能分流”。

### 9.2 必须进入教师复核的情况

```text
1. 答案抽取置信度低于 0.8
2. 证据提取置信度低于 0.8
3. Reflector 标记 need_human_review = true
4. 学生答案为空但 Grader 给了分
5. 同组答案分差异常
6. 高权重题得分异常
7. 题目分值超过 20 分且置信度不足
8. 系统随机抽检样本
```

---

### 9.3 输出

```json
{
  "grading_result_id": 123,
  "review_required": true,
  "review_priority": "high",
  "review_reason": [
    "证据置信度低",
    "评分与负向证据不一致"
  ]
}
```

### 9.4 grading_result 表补充字段

```sql
ALTER TABLE grading_result ADD COLUMN review_required BOOLEAN DEFAULT FALSE;
ALTER TABLE grading_result ADD COLUMN review_priority VARCHAR(50);
ALTER TABLE grading_result ADD COLUMN review_reason JSON;
```

---

## 10. 新增 teacher_review_service

### 10.1 功能

教师可以对 AI 结果进行最终确认和修改。

### 10.2 必须支持的操作

```text
1. 修改某个学生某道题得分
2. 修改某个学生某道题评语
3. 查看该分数对应的评分证据
4. 查看 Reflector 发现的问题
5. 确认 AI 分数
6. 批量确认无异常结果
7. 重批某一道题
8. 导出最终成绩
```

---

### 10.3 新增教师修订表

```sql
CREATE TABLE teacher_revision (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL,
    grading_result_id BIGINT NOT NULL,
    old_score DECIMAL(5,2),
    new_score DECIMAL(5,2),
    old_comment TEXT,
    new_comment TEXT,
    revision_reason TEXT,
    teacher_id BIGINT,
    created_at DATETIME
);
```

---

### 10.4 grading_result 表补充字段

```sql
ALTER TABLE grading_result ADD COLUMN final_score DECIMAL(5,2);
ALTER TABLE grading_result ADD COLUMN final_comment TEXT;
ALTER TABLE grading_result ADD COLUMN review_status VARCHAR(50);
```

`review_status` 建议取值：

```text
ai_generated
teacher_confirmed
teacher_modified
system_regraded
```

---

## 11. 新增 audit_log_service

### 11.1 功能

记录关键操作日志，保证批改过程可追溯。

### 11.2 需要记录的操作

```text
1. 创建任务
2. 上传文件
3. 解析文件
4. 生成题目
5. 生成评分量规
6. 修改评分量规
7. 抽取学生答案
8. 提取评分证据
9. AI评分
10. 反思校准
11. 教师修改分数
12. 教师确认最终成绩
13. 导出成绩
```

---

### 11.3 新增数据库表

```sql
CREATE TABLE audit_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT,
    user_id BIGINT,
    action_type VARCHAR(100),
    target_type VARCHAR(100),
    target_id BIGINT,
    detail JSON,
    created_at DATETIME
);
```

---

## 12. 可选新增 answer_grouper_service

这个模块可以第二阶段实现，但建议预留接口和表结构。

### 12.1 功能

将同一道题下的相似答案自动分组。

### 12.2 输入

```json
{
  "question_id": 1,
  "student_answers": []
}
```

### 12.3 输出

```json
{
  "question_no": "1",
  "groups": [
    {
      "group_name": "基本正确",
      "summary": "答案完整，逻辑正确，仅有少量格式问题",
      "suggested_score_range": "18-20",
      "student_answer_ids": [1, 5, 7]
    }
  ]
}
```

---

### 12.4 新增数据库表

```sql
CREATE TABLE answer_group (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT,
    question_id BIGINT,
    group_name VARCHAR(255),
    group_summary TEXT,
    suggested_score_range VARCHAR(50),
    created_at DATETIME
);

CREATE TABLE answer_group_member (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    group_id BIGINT,
    student_answer_id BIGINT,
    created_at DATETIME
);
```

---

## 13. 可选新增 adaptive_grading_rule

这个模块可以第三阶段实现，但建议预留表结构。

### 13.1 功能

根据教师修改记录，总结可复用的评分规则。

例如：

```text
如果 SQL 查询题缺少核心 WHERE 条件，即使语法正确，查询逻辑维度最高只能得 50%。
```

---

### 13.2 新增数据库表

```sql
CREATE TABLE adaptive_grading_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_name VARCHAR(255),
    question_type VARCHAR(100),
    rule_text TEXT,
    source_type VARCHAR(50),
    confidence DECIMAL(5,4),
    usage_count INT DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME
);
```

---

## 14. API 需要新增或调整

### 14.1 新增题目分析接口

```http
POST /api/tasks/{task_id}/analyze-questions
```

功能：

```text
从作业要求和参考答案中识别题目、题型、知识点、难度。
```

---

### 14.2 新增评分量规生成接口

```http
POST /api/tasks/{task_id}/build-rubrics
```

功能：

```text
为每道题生成评分量规。
```

---

### 14.3 新增评分证据提取接口

```http
POST /api/tasks/{task_id}/extract-evidence
```

功能：

```text
针对每个学生每道题，提取评分点对应的正向证据和负向证据。
```

---

### 14.4 调整按题批改接口

旧接口：

```http
POST /api/tasks/{task_id}/grade-by-question
```

保留路径，但内部逻辑修改为：

```text
读取 student_answer
读取 answer_evidence
读取 question_rubric
基于证据进行评分
写入 grading_result
```

---

### 14.5 新增反思校准接口

```http
POST /api/tasks/{task_id}/reflect-grading
```

功能：

```text
检查评分与证据是否一致，标记异常结果。
```

---

### 14.6 新增教师复核分流接口

```http
POST /api/tasks/{task_id}/route-review
```

功能：

```text
标记哪些结果需要教师复核。
```

---

### 14.7 新增教师复核列表接口

```http
GET /api/tasks/{task_id}/review-items
```

支持筛选：

```text
review_required
review_priority
question_id
student_id
grading_status
```

---

### 14.8 新增教师修改评分接口

```http
PUT /api/tasks/{task_id}/grading-results/{result_id}/review
```

请求：

```json
{
  "final_score": 16,
  "final_comment": "查询条件基本正确，但字段选择不完整。",
  "revision_reason": "教师复核后调整查询逻辑维度得分"
}
```

---

### 14.9 新增查看评分证据接口

```http
GET /api/grading-results/{result_id}/evidence
```

返回：

```text
该学生该题的评分量规、正向证据、负向证据、AI评分理由、Reflector检查结果。
```

---

## 15. 前端页面需要修改

### 15.1 原“分值标准确认页”改为“评分量规确认页”

旧页面字段：

```text
题号
题目内容
分值
评分细则
```

新版页面字段：

```text
题号
题型
知识点
题目内容
总分
评分维度
维度分值
得分条件
扣分条件
证据要求
操作
```

教师可以编辑：

```text
评分维度
分值
得分条件
扣分条件
证据要求
```

---

### 15.2 原“批改结果页”增加“评分证据”

每个学生每道题详情中必须展示：

```text
题目
学生答案
评分量规
AI提取的正向证据
AI提取的负向证据
各维度得分
AI评语
Reflector发现的问题
教师最终评分
```

---

### 15.3 新增“教师复核中心”

功能：

```text
1. 查看所有需要复核的批改结果
2. 按优先级筛选
3. 按题目筛选
4. 按异常类型筛选
5. 修改分数和评语
6. 批量确认无异常项
```

复核列表建议字段：

| 学生 | 题号 | AI分数 | 置信度 | 异常原因 | 优先级 | 操作 |
|---|---|---:|---:|---|---|---|

---

### 15.4 批改流程步骤条需要调整

旧版：

```text
文件解析 → 分值设定 → 学生作业解析 → 答案抽取 → 按题批改 → 汇总报告
```

新版：

```text
文件解析
→ 题目分析
→ 量规生成
→ 量规确认
→ 学生解析
→ 答案抽取
→ 证据提取
→ AI评分
→ 反思校准
→ 教师复核
→ 结果导出
```

---

### 15.5 新增“按题批改视图”

左侧：

```text
题目列表
平均分
需要复核人数
异常人数
```

中间：

```text
该题所有学生答案
AI分数
最终分数
状态
```

右侧：

```text
评分量规
常见错误
证据统计
```

---

## 16. Celery Pipeline 需要调整

旧版 pipeline 可能是：

```python
parse_files()
set_score()
prepare_students()
extract_answers()
grade_by_question()
summary()
```

新版建议改为：

```python
parse_files()
analyze_questions()
build_rubrics()
wait_for_teacher_confirm_rubrics()
prepare_students()
extract_answers()
extract_evidence()
grade_by_question()
reflect_grading()
route_review()
wait_for_teacher_review()
export_results()
```

注意：

```text
wait_for_teacher_confirm_rubrics
wait_for_teacher_review
```

这两步不是 Celery 自动跑完，而是任务状态进入等待教师操作。

---

## 17. 任务状态需要增加

旧版任务状态可能包括：

```text
created
files_uploaded
parsed
score_generated
score_confirmed
students_prepared
answers_extracted
grading
graded
summary_generated
failed
```

新版建议改为：

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

---

## 18. LLMService 需要统一 JSON 调用

请检查旧版是否有业务模块直接调用 LLM API。

如果有，需要改成统一通过：

```python
llm_service.chat_json()
```

建议接口：

```python
class LLMService:
    def chat_json(self, prompt: str, schema: dict | None = None, max_retries: int = 3) -> dict:
        pass

    def chat_text(self, prompt: str, max_retries: int = 3) -> str:
        pass
```

### 必须实现

```text
1. JSON解析失败自动重试
2. 非法字段自动修复
3. 保存原始LLM输出 raw_llm_output
4. 调用失败要写入任务错误日志
5. 支持后续切换不同模型
```

---

## 19. Prompt 需要新增和替换

### 19.1 question_analyzer_prompt

```text
你是一名课程作业题目分析专家。

请根据作业要求、参考答案和教师批改说明，识别作业中的所有题目。
你需要输出题号、题目内容、题型、知识点、难度和期望答案类型。

要求：
1. 不要评分。
2. 不要批改学生答案。
3. 只分析题目结构。
4. 请只输出合法 JSON，不要输出 Markdown，不要输出解释文字。

输出格式：
{
  "questions": [
    {
      "question_no": "1",
      "question_type": "SQL编程题",
      "question_content": "...",
      "knowledge_points": ["SELECT查询", "WHERE条件"],
      "difficulty": "中等",
      "expected_answer_type": "SQL代码",
      "sort_order": 1
    }
  ]
}

作业要求：
{{requirement_text}}

参考答案：
{{reference_text}}

教师批改说明：
{{grading_instruction}}
```

---

### 19.2 rubric_builder_prompt

```text
你是一名课程评分量规设计专家。

请根据题目、参考答案和教师批改说明，为该题生成评分量规。
评分量规必须包括评分维度、分值、得分条件、扣分条件和证据要求。

要求：
1. 每道题的评分维度分值之和必须等于该题总分。
2. 评分维度要具体、可判断、可解释。
3. 每个评分维度都必须说明需要从学生答案中提取什么证据。
4. 请只输出合法 JSON，不要输出 Markdown，不要输出解释文字。

输出格式：
{
  "question_no": "1",
  "total_score": 20,
  "rubrics": [
    {
      "dimension": "语法正确性",
      "description": "SQL语句结构正确，可以正常执行",
      "score": 5,
      "positive_condition": "包含完整 SELECT ... FROM ... 结构，无明显语法错误",
      "negative_condition": "SQL结构缺失，存在明显语法错误",
      "evidence_required": "是否存在完整SQL结构，是否存在语法错误"
    }
  ]
}

题目：
{{question}}

参考答案：
{{reference_answer}}

教师批改说明：
{{grading_instruction}}
```

---

### 19.3 evidence_extractor_prompt

```text
你是一名评分证据提取助手。

你的任务不是评分，而是根据评分量规，从学生答案中提取每个评分维度对应的正向证据和负向证据。

要求：
1. 不要给分。
2. 不要评价总分。
3. 每个评分维度都必须输出证据。
4. 如果没有找到正向证据，positive_evidence 为空数组。
5. 如果没有找到负向证据，negative_evidence 为空数组。
6. confidence 是 0 到 1 之间的小数。
7. 请只输出合法 JSON，不要输出 Markdown，不要输出解释文字。

输出格式：
{
  "student_answer_id": 1001,
  "question_no": "1",
  "evidence": [
    {
      "rubric_id": 1,
      "dimension": "查询逻辑",
      "positive_evidence": ["答案包含 WHERE age > 18 条件"],
      "negative_evidence": [],
      "evidence_confidence": 0.95
    }
  ]
}

题目：
{{question}}

评分量规：
{{rubrics}}

学生答案：
{{student_answer}}
```

---

### 19.4 grade_by_question_prompt 需要替换

旧版 prompt 如果是直接根据学生答案打分，需要改为：

```text
你是一名严格、公正、稳定的课程作业批改教师。

现在只批改同一道题。
请根据题目、评分量规和已经提取出的结构化评分证据，为学生答案评分。

重要要求：
1. 你必须主要依据 structured_evidence 评分。
2. 不得忽略评分量规。
3. 每个评分维度都必须给出分数。
4. 每个维度得分不得超过该维度满分。
5. 总分必须等于各维度得分之和。
6. 如果证据不足，不能随意给高分，应降低置信度并说明原因。
7. 请只输出合法 JSON，不要输出 Markdown，不要输出解释文字。

输出格式：
{
  "student_no": "20240101",
  "student_name": "张三",
  "question_no": "1",
  "score": 16,
  "max_score": 20,
  "rubric_scores": [
    {
      "rubric_id": 1,
      "dimension": "语法正确性",
      "score": 5,
      "max_score": 5,
      "reason": "SQL语句结构完整，无明显语法错误"
    }
  ],
  "comment": "整体语法正确，但查询条件不够完整。",
  "grading_confidence": 0.91
}

题目：
{{question}}

评分量规：
{{rubrics}}

结构化评分证据：
{{structured_evidence}}

学生原始答案：
{{student_answer}}
```

---

### 19.5 reflector_prompt

```text
你是一名AI批改结果审查员。

你的任务是检查 AI 初始评分是否与评分量规和结构化证据一致。
你不需要重新完整批改，但需要发现明显不合理的评分。

请检查：
1. 总分是否等于各评分维度得分之和。
2. 是否存在负向证据但该维度给了满分。
3. 是否没有正向证据却给了高分。
4. 是否答案为空但给了分。
5. 是否超过题目满分或维度满分。
6. 扣分理由是否与评分量规匹配。
7. 是否需要教师复核。

请只输出合法 JSON，不要输出 Markdown，不要输出解释文字。

输出格式：
{
  "reflection_status": "pass | warning | failed",
  "issues": [
    {
      "type": "score_evidence_mismatch",
      "message": "查询逻辑维度存在负向证据，但该维度给了满分"
    }
  ],
  "suggested_action": "pass | regrade | human_review",
  "calibrated_score": 14,
  "need_human_review": true
}

评分结果：
{{grading_result}}

评分量规：
{{rubrics}}

结构化评分证据：
{{structured_evidence}}

学生答案：
{{student_answer}}
```

---

## 20. 导出 Excel 需要增加字段

旧版 Excel 可能只导出：

```text
学号
姓名
各题得分
总分
评语
```

新版建议增加：

```text
学号
姓名
各题AI分数
各题最终分数
总分
是否教师修改
是否需要复核
复核状态
主要扣分原因
总体评语
```

如果按题导出详细表，则包括：

```text
学号
姓名
题号
题目分值
AI分数
最终分数
评分维度得分
正向证据
负向证据
AI评语
教师评语
复核状态
```

---

## 21. summary 暂时不必复杂化

如果旧版已经有 summary，可以保留。

但建议 summary 的输入改为使用最终成绩：

```text
final_score 优先
如果没有 final_score，再使用 AI score
```

summary 输出至少包括：

```text
班级平均分
最高分
最低分
各题平均分
各题得分率
高频扣分点
需要重点讲解的知识点
需要复核或关注的学生
```

---

## 22. 当前阶段建议 Codex 优先完成的修改

请优先修改以下 10 项：

```text
1. 将 set_score 拆成 question_analyzer 和 rubric_builder。
2. 扩展 question 和 question_rubric 表。
3. 新增 answer_evidence 表和 evidence_extractor_service。
4. 修改 grade_by_question，让它基于 answer_evidence 评分。
5. 新增 grading_reflection 表和 reflector_service。
6. 新增 review_router_service，并在 grading_result 中标记 review_required。
7. 新增 teacher_revision 表和 teacher_review_service。
8. 前端分值确认页升级为评分量规确认页。
9. 前端批改详情页增加评分证据展示。
10. Celery pipeline 增加 evidence_extractor、reflector、review_router 三个阶段。
```

---

## 23. 可以暂缓的功能

以下功能不是本次必须完成，可以先预留接口和表结构：

```text
1. answer_grouper：相似答案分组。
2. adaptive_grading_rule：从教师修改中学习规则。
3. code_runner：代码运行测试。
4. sql_executor：SQL沙箱执行。
5. rag_feedback：基于课程资料生成学习反馈。
6. random_audit：随机审计与防止形式化复核。
7. fairness_checker：公平性与偏见检查。
8. student_learning_profile：学生长期学习画像。
```

---

## 24. 修改后的核心验收标准

本次升级完成后，系统至少应该做到：

```text
1. 教师上传作业后，系统能识别题目、题型和知识点。
2. 系统能为每道题生成评分量规，而不是只有一个总分。
3. 系统能从学生答案中提取每个评分维度对应的正向证据和负向证据。
4. 系统评分时必须基于证据，而不是直接黑盒评分。
5. 每个学生每道题都能查看评分依据。
6. 系统能发现明显不合理的 AI 评分，并标记需要教师复核。
7. 教师能修改最终分数和评语。
8. 教师修改记录能保存。
9. 成绩导出使用最终分数。
10. 所有关键中间结果都入库，便于调试、复核和后续优化。
```

---

## 25. 给 Codex 的直接修改指令

可以把下面这段直接发给 Codex：

```text
我已经有一个基于旧版指南开发的 AI 作业批改系统基础框架。
现在请不要推翻重写，而是在现有项目基础上做增量升级。

升级目标：
将系统从“LLM直接批改”改为“证据—量规驱动的多智能体批改系统”。

核心要求：
1. 不要让 LLM 直接从学生原文给分。
2. 先通过 question_analyzer 识别题目、题型、知识点。
3. 再通过 rubric_builder 生成评分量规，包括评分维度、分值、得分条件、扣分条件和证据要求。
4. 通过 answer_extractor 从学生作业中抽取每题答案。
5. 新增 evidence_extractor，从学生答案中为每个评分维度提取正向证据和负向证据。
6. 修改 grade_by_question，使其必须基于 evidence_extractor 的结构化证据进行评分。
7. 新增 reflector，检查评分是否与证据一致。
8. 新增 review_router，自动标记需要教师复核的结果。
9. 新增 teacher_review，允许教师修改分数和评语，并保存修改记录。
10. 前端增加评分证据展示和教师复核中心。

请优先完成：
- 后端 service 拆分和新增
- 数据库表结构修改
- API 接口新增
- Celery pipeline 调整
- 前端评分量规确认页
- 前端评分证据详情页
- 前端教师复核中心

不要做的事情：
- 暂时不要实现复杂的 RAG
- 暂时不要实现长期学生画像
- 暂时不要实现代码沙箱执行
- 暂时不要实现公平性检测
- 暂时不要大改登录权限系统

开发完成后，请确保：
1. 所有 LLM 输出都是 JSON。
2. 所有中间结果都入库。
3. 每个最终分数都能追溯到评分量规和评分证据。
4. 教师修改过的分数优先作为最终成绩。
5. 系统状态流转完整。
```

---

## 26. 总结

本次修改不是简单增加几个接口，而是改变批改系统的底层逻辑。

旧逻辑：

```text
学生答案 → LLM → 分数
```

新逻辑：

```text
学生答案
  → 答案抽取
  → 证据提取
  → 基于量规评分
  → 反思校准
  → 教师复核
  → 最终成绩
```

最终目标：

```text
让系统从“会批改”升级为“批得有依据、能解释、可复核、可追踪”。
```
