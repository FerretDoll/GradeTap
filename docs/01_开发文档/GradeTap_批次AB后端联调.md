# 批次 A/B 本地联调

后端使用前端开工包 v0.3.0 契约。开发、回归测试和正式部署均使用腾讯云 MySQL。当前开发机的 backend/.env 已指向开发库。在项目根目录运行以下 PowerShell 命令，启动脚本会建立或复用 SSH 隧道。

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$env:GRADETAP_BACKEND_PORT = "8010"
corepack pnpm run dev
```

前端工作台地址是 http://127.0.0.1:5173 。需要单独运行迁移或测试时，可先在根目录单独执行 `node scripts/db-tunnel.mjs`，再从另一个终端进入 backend 并激活 gradetap 环境。运行 `python -m pip install -r requirements-dev.txt` 安装测试依赖。开发库已初始化；新迁移使用 `python -m alembic upgrade head`。首次创建管理员使用 `python -m app.db.create_admin` 交互输入邮箱和密码。

1. 分别用两个浏览器配置文件注册教师账号。在本地后端控制台找到对应邮箱的验证链接，通过前端的 `/verify-email?token=…` 打开。令牌有效期 30 分钟，重发后旧令牌失效。
2. 用管理员账号批准教师申请。教师可刷新工作台，各建同名课程、班级和任务，核对两边列表。批次 B 当前授课角色是 owner。
3. 归档后可用 `GET /api/tasks?include_archived=true` 查看。重建当前评分前的版本通过 `GET /api/tasks/{id}/evaluation-versions` 查询，版本详情保存当时的答案、证据、评分及师评。相同学生二次上传后重新准备学生，按最近提交轮次匹配。
4. 全部已有提交的各题成绩经教师确认后，`POST /api/tasks/{id}/releases` 返回 release_id。在 `POST /api/tasks/{id}/export-results` 中传入该 ID 下载发布时保存的 Excel。未指定 ID 时导出文件名包含 draft。
5. 从 backend 运行 `python -m pytest -q`。测试在临时库里执行真实迁移、账号审核、授课班隔离和成绩保护流程。

## 旧库与试点

迁移前备份数据库与附件，在副本执行 `python -m alembic upgrade head` 并核对记录数。0001 接管既有表及已知旧版缺列，0002 增加账号与授课外键，0003 增加轮次、历史版本和正式成绩快照。旧记录的授课归属保持待核对状态，教师工作台仅展示已绑定的数据。取得课程、班级和旧任务的真实归属清单后再进行映射。

真实发信、协作授权和多进程限流属于试点部署工作。开发验证链接仅记录在 local、development 和 test 环境的后端日志中。其他环境下 Cookie 要求 HTTPS。
