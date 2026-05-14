# GradeTap

GradeTap 是一个面向高校与高职教师的 AI 作业批改助手。项目目标是把批改拆成可控、可追踪、可复核的流水线：解析、设分、抽题、分组、批改、复核、汇总。

## 当前框架

- `backend/`：FastAPI 后端基础骨架。
- `frontend/`：Vue 3 + Element Plus 前端基础骨架。
- `AGENTS.md`：项目记忆与开发约定。
- `大模型自动批改作业网站_架构设计.md`：完整架构设计文档。

## 后端启动

推荐使用 conda 管理环境（**Python 3.10+**，与 `requirements.txt` 中 `uvicorn>=0.30` 等依赖一致）：

```powershell
cd backend
conda create -n gradetap python=3.12
conda activate gradetap
pip install -r requirements.txt
uvicorn app.main:app --reload
```

默认服务地址：`http://127.0.0.1:8000`。

## 前端启动

```powershell
cd frontend
corepack pnpm install
corepack pnpm run dev
```

默认服务地址：`http://127.0.0.1:5173`。

## MVP 开发优先级

1. 创建批改任务。
2. 上传作业要求、参考答案和学生作业。
3. 解析 `.docx`、`.pdf`、`.txt` 文件。
4. 生成并确认评分标准。
5. 抽取学生答案。
6. 按题批量批改。
7. 生成成绩表并导出 Excel。
