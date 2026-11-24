# GradeTap 智能批改系统

GradeTap 是面向高校与高职教师的 AI 作业批改助手，重点服务软件技术、数据库应用、程序设计、Web 前端开发等编码类课程的过程性评价。

项目不追求把学生作业直接交给大模型“黑盒打分”，而是把教师日常批改拆解为可查看、可修改、可追踪、可复核的流水线：先解析材料和题目，再生成评分量规；先抽取学生答案和评分证据，再按题统一评分；AI 完成初批，教师掌握最终评分权。

## 核心理念

- 先结构化，再评分。
- 先找证据，再给分。
- AI 负责初批，教师负责确认和修订。
- 同一道题按统一量规批量评分，减少评分漂移。
- 每个最终分数都应能追溯到题目、量规、证据、AI 理由和教师复核记录。

## 适用场景

GradeTap 主要用于编码类、实验类和文档类作业批改，尤其适合需要关注学习过程的课程评价。

教师可以要求学生提交最终代码之外的过程材料，例如代码初稿、错误提示、调试记录、修改说明、实验报告和最终代码。系统将这些材料纳入解析、证据提取和评分流程，帮助教师从重复性核对转向评分把关、证据分析和课堂讲评。

## 可复用开发路径

本项目的开发方法来自《开发与应用报告》中总结的实践流程，可复用于类似 AI 教育工具或智能业务系统：

1. AI 调研  
   围绕业务场景、评价方法、风险边界和同类产品进行调研，明确系统不只是自动生成结果，而要提供可解释依据和人工复核机制。

2. 知识沉淀  
   将项目定位、架构约定、数据模型、提示词规范、风险规则和验收标准整理到 `AGENTS.md`，作为后续 AI 辅助开发的项目记忆。

3. 辅助编程  
   使用 AI 编程工具按模块推进，优先搭建可运行闭环，再逐步补充数据模型、服务边界、前端视图和异常处理。

4. 提示词设计  
   将大模型任务拆分为题目分析、量规生成、答案抽取、证据提取、按题评分、反思校准、结果汇总等独立环节。每个环节只做自己的事，并要求输出合法 JSON。

5. 功能验证  
   使用真实或模拟作业材料验证“上传材料 -> 生成量规 -> 抽取答案 -> 提取证据 -> AI 评分 -> 教师复核 -> 导出结果”的完整链条。

## 教师使用流程

前端面向教师工作台，推荐把复杂后台流水线包装成 4 个易理解步骤：

1. 上传材料  
   上传作业要求、参考答案和学生作业文件。

2. 确认评分量规  
   系统自动拆题，识别题型、知识点、难度和期望答案类型，并生成每道题的评分维度、分值、得分条件、扣分条件和证据要求。教师可修改后确认。

3. 自动批改  
   系统解析学生信息，按题抽取答案，提取正向证据、负向证据和置信度，并基于结构化证据按题统一评分。

4. 查看结果  
   教师查看学生答案、评分证据、AI 评分理由和异常标记，确认或修改最终成绩，最后导出 Excel 成绩表。

## 核心批改流水线

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

其中 `teacher_confirm_rubrics` 和 `teacher_review` 是等待教师操作的状态，不应作为后台任务自动跑完。

## 功能模块

- 基础数据管理：维护课程、班级、学生等基础信息。
- 批改任务管理：创建任务，上传作业材料，查看任务状态和处理进度。
- 智能批改流程：完成文件解析、题目分析、量规生成、学生解析、答案抽取、证据提取、AI 评分和反思校准。
- 教师复核中心：按异常类型、题目、优先级筛选复核项，查看证据并修改最终分数和评语。
- 结果导出：导出 Excel 成绩表，导出时优先使用教师确认后的 `final_score`。
- 模型配置：配置大模型 API 地址、模型名称和密钥，并进行连通性测试。

## 技术栈

```text
frontend: Vue 3 + Vite + Element Plus + Pinia + Axios
backend:  Python FastAPI + SQLAlchemy + Pydantic
tasks:    Celery + Redis
database: MySQL
files:    MVP 使用本地文件系统，后续可替换为 MinIO / OSS
llm:      统一通过 LLMService 调用，可接入 DeepSeek 等模型服务
export:   pandas + openpyxl
parse:    python-docx + PyMuPDF + pdfplumber
```

## 项目结构

```text
GradeTap/
  backend/
    app/
      api/          # FastAPI 路由
      core/         # 配置
      db/           # 数据库会话与初始化
      models/       # 业务模型
      prompts/      # 大模型提示词模板
      schemas/      # Pydantic 请求与响应结构
      services/     # 业务服务与智能体服务
      tasks/        # Celery 流水线任务
      utils/        # 文件解析、导出等工具
    requirements.txt
  frontend/
    src/
      api/          # Axios API 封装
      stores/       # Pinia 状态
      views/        # 教师工作台页面
      components/   # 可复用组件
    package.json
  AGENTS.md         # 项目记忆与开发约定
  docs/
    README.md       # 文档导航
    01_开发文档/
    02_架构设计/
    03_项目申报/
    04_案例与演示/
    05_图件/
```

## 一键启动（推荐）

首次使用前，请先完成依赖安装：

```bash
# 后端
cd backend
conda create -n gradetap python=3.12
conda activate gradetap
pip install -r requirements.txt

# 前端
cd ../frontend
corepack pnpm install
```

开发与正式部署使用腾讯云 MySQL。开发机通过 SSH 别名 `gradetap` 访问独立开发库，连接参数从未提交的 `backend/.env` 读取。根目录启动脚本会建立或复用本地 13306 隧道。详见[数据库与联调配置](docs/01_开发文档/GradeTap_批次AB后端联调.md)。

之后在项目根目录执行以下任一命令，即可同时启动前后端：

```bash
# 方式 1：根目录 npm script
corepack pnpm run dev

# 方式 2：脚本（macOS / Linux）
./scripts/start-dev.sh

# 方式 3：脚本（Windows PowerShell）
.\scripts\start-dev.ps1
```

启动后默认地址：

```text
前端: http://127.0.0.1:5173
后端: http://127.0.0.1:8000
```

按 `Ctrl+C` 会同时停止前后端服务。

Python 环境查找顺序：

1. 环境变量 `GRADETAP_PYTHON`（手动指定 Python 路径）
2. 当前已激活的 conda 环境（`CONDA_PREFIX`）
3. 项目根目录 `.conda/` 本地环境
4. `environment.yml` 中声明的 conda 环境（默认 `gradetap`）
5. 系统 `python3`（Windows 为 `python`）

也可通过 `GRADETAP_CONDA_ENV=其他环境名` 指定 conda 环境名。

## 分别启动

如需单独调试，也可以分开启动。

后端（建议使用 Python 3.10+）：

```powershell
cd backend
conda activate gradetap
uvicorn app.main:app --reload
```

前端：

```powershell
cd frontend
corepack pnpm run dev
```

## DeepSeek API Key 获取与配置

GradeTap 默认支持通过 DeepSeek Open Platform 调用大模型。官方 API 文档入口为 [DeepSeek API Docs](https://api-docs.deepseek.com/zh-cn/)，API 平台入口为 [DeepSeek Platform](https://platform.deepseek.com/)。

获取 API Key 的流程：

1. 打开 `https://platform.deepseek.com/`。
2. 注册或登录 DeepSeek 账号。
3. 进入 API Keys / API 密钥页面。
4. 点击创建 API Key，按页面提示生成新密钥。
5. 复制密钥并妥善保存。平台通常只在创建时完整展示一次，后续无法再次查看明文。
6. 如平台要求，先完成充值或开通额度，再进行接口调用测试。

在 GradeTap 中配置：

1. 启动前后端服务。
2. 打开前端教师工作台。
3. 进入模型配置页面。
4. 填写以下信息：

```text
Provider: deepseek
Base URL: https://api.deepseek.com
Model: deepseek-v4-pro
API Key: 从 DeepSeek Platform 创建的密钥
```

5. 点击连通性测试，看到“密钥可用，模型连接正常”后再启用智能批改流程。

安全注意事项：

- 不要把 API Key 写入前端代码。
- 不要把真实 API Key 提交到 Git。
- 不要在截图、演示视频或日志中暴露 API Key。
- 如果怀疑密钥泄露，应立即在 DeepSeek Platform 删除旧密钥并创建新密钥。
- 生产环境建议通过后端配置、数据库加密字段或密钥管理服务保存密钥。

## 开发约定

- API 层只处理请求响应和权限校验，业务逻辑放在 `services/`。
- 长任务放入 Celery，不要在 HTTP 请求中同步跑完整批改流程。
- 业务模块不要直接调用模型 API，统一通过 `services/llm_service.py`。
- Prompt 模板统一放在 `backend/app/prompts/`。
- 所有需要入库的 LLM 输出必须要求合法 JSON。
- JSON 解析失败时，按“正常调用 -> 要求模型修复 JSON -> 标记人工复核”的方式处理。
- 保存 `raw_llm_output`，便于争议追踪和调试。
- 关键操作写入审计日志，包括上传文件、解析文件、生成题目、生成量规、提取证据、AI 评分、教师修改分数和导出成绩。

## 提示词拆分原则

- `question_analyzer_prompt`：只分析题目结构，不评分。
- `rubric_builder_prompt`：生成评分量规，每个维度包含分值、得分条件、扣分条件和证据要求。
- `answer_extractor_prompt`：按题抽取学生答案，输出匹配状态和置信度。
- `evidence_extractor_prompt`：只提取正向证据、负向证据和置信度，不给分。
- `grade_by_question_prompt`：基于结构化证据和评分量规给分，不直接依赖学生原文黑盒评分。
- `reflector_prompt`：检查总分求和、空答案给分、超分、证据冲突、理由不匹配等异常。
- `summary_prompt`：基于最终成绩生成班级汇总、共性问题和反馈建议。

## 复核规则

以下情况应进入教师复核候选：

- 答案抽取置信度低于 0.8。
- 证据提取置信度低于 0.8。
- Reflector 标记 `need_human_review = true`。
- 学生答案为空但 AI 给了分。
- 维度得分超过维度满分或总分求和异常。
- 负向证据明显存在但 AI 给高分。
- 高权重题得分异常。
- 随机抽检样本。

## 当前重点

第一阶段优先跑通证据-量规驱动的核心闭环：

1. 课程、班级和批改任务管理。
2. 上传作业要求、参考答案和学生作业。
3. 解析 `.docx`、`.pdf`、`.txt` 文件。
4. 题目分析和评分量规生成。
5. 教师确认或修改评分量规。
6. 学生解析和答案抽取。
7. 评分证据提取。
8. 按题批量评分。
9. 反思校准和复核分流。
10. 教师复核、保存修订记录、导出 Excel。

## 后续规划

- 增加代码沙箱运行验证，支持 SQL、Python、Java 等代码类作业自动测试。
- 增加 OCR 和多模态解析，处理截图、运行界面和复杂实验报告。
- 完善相似答案分组、共性错误分析、课堂讲评建议和学生反馈报告。
- 从教师修改记录中沉淀可复用评分规则。
- 逐步形成适用于编码类课程的智能评价与教学改进平台。

## 许可证

本项目采用 MIT License。你可以自由使用、复制、修改和分发本项目代码，但需要保留原始版权声明和许可证文本。详见 [LICENSE](LICENSE)。

## 参考文档

- [项目文档目录](docs/README.md)：开发文档、架构设计、项目申报、案例与演示、图件的统一入口。
- [AGENTS.md](AGENTS.md)：项目记忆、架构约定、数据模型、API 设计和验收标准。
- [架构设计](docs/02_架构设计/大模型自动批改作业网站_架构设计.md)：详细架构设计。
- [旧版框架升级修改说明](docs/02_架构设计/AI作业批改系统_旧版框架升级修改说明.md)：证据-量规驱动的升级要求。
