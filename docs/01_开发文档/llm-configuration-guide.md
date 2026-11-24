# 大模型配置功能开发说明

本文档用于指导其他 AI 或开发者在类似系统中实现“大模型配置”功能。它以 GradeTap 当前实现为参考，目标是让教师或管理员可以在前端配置模型供应商、API 地址、模型名称和 API Key，后端统一保存配置并通过统一的 `LLMService` 发起模型调用。

## 设计目标

大模型配置不应该散落在各个业务模块中。系统应提供一个独立的配置入口，由前端负责收集配置，由后端负责保存、脱敏返回、连通性测试和运行时读取，所有业务模型调用统一经过 `LLMService`。

核心原则：

- 前端可以录入 API Key，但不能在读取配置时拿到明文 API Key。
- 后端保存完整配置，返回给前端时只返回 `hasApiKey` 和 `apiKeyMask`。
- 业务服务不得直接请求模型供应商接口，只能调用 `llm_service.py`。
- 配置必须支持 OpenAI-compatible `/chat/completions` 接口，方便切换 DeepSeek、OpenAI、通义千问、豆包等供应商。
- 连通性测试应独立于业务流程，避免教师在批改时才发现密钥不可用。
- JSON 型业务输出必须通过统一 JSON 调用方法处理，包含重试和 JSON 修复机制。

## 功能范围

建议实现以下能力：

- 获取当前模型配置。
- 保存模型配置。
- 清除 API Key。
- 测试模型连接。
- 前端本地兜底缓存。
- 后端运行时读取配置。
- 统一文本调用和 JSON 调用。
- 支持流式输出进度，供长任务展示模型生成过程。

## 配置字段

前端表单和后端配置建议使用同一组字段，前端使用 camelCase，后端内部可转为 snake_case。

| 字段 | 类型 | 示例 | 说明 |
| --- | --- | --- | --- |
| `enabled` | boolean | `true` | 是否启用大模型能力。关闭时业务流程应提示先启用模型。 |
| `provider` | string | `deepseek` | 供应商标识，用于前端预设和后续扩展。 |
| `baseUrl` | string | `https://api.deepseek.com` | OpenAI-compatible API 根地址，不要带末尾 `/`。 |
| `model` | string | `deepseek-v4-pro` | 默认模型名称。 |
| `apiKey` | string | `sk-...` | 仅保存或替换时提交；读取配置时不返回明文。 |
| `temperature` | number | `0.2` | 默认温度。批改类任务建议低温。 |
| `maxRetries` | number | `3` | JSON 修复或请求失败时的最大重试次数。 |
| `hasApiKey` | boolean | `true` | 后端返回，表示是否已保存密钥。 |
| `apiKeyMask` | string | `已保存 API Key` | 后端返回，前端显示用。 |

推荐默认值：

```json
{
  "enabled": false,
  "provider": "deepseek",
  "baseUrl": "https://api.deepseek.com",
  "model": "deepseek-v4-pro",
  "temperature": 0.2,
  "maxRetries": 3
}
```

## 供应商预设

前端可以维护一个供应商预设列表。切换供应商时自动填充 `baseUrl` 和默认模型，仍允许用户手动编辑。

```js
const llmProviders = [
  {
    label: "DeepSeek",
    value: "deepseek",
    baseUrl: "https://api.deepseek.com",
    models: ["deepseek-v4-pro", "deepseek-v4-flash"],
  },
  {
    label: "OpenAI Compatible",
    value: "openai-compatible",
    baseUrl: "https://api.openai.com/v1",
    models: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
  },
  {
    label: "通义千问",
    value: "qwen",
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    models: ["qwen-plus", "qwen-turbo", "qwen-max"],
  },
  {
    label: "豆包",
    value: "doubao",
    baseUrl: "https://ark.cn-beijing.volces.com/api/v3",
    models: ["doubao-1-5-pro-32k", "doubao-1-5-lite-32k"],
  },
  {
    label: "自定义",
    value: "custom",
    baseUrl: "",
    models: [],
  },
];
```

## 后端接口设计

建议接口统一放在 `/api/settings/llm` 下。

### 获取配置

```http
GET /api/settings/llm
```

返回示例：

```json
{
  "enabled": true,
  "provider": "deepseek",
  "baseUrl": "https://api.deepseek.com",
  "model": "deepseek-v4-pro",
  "temperature": 0.2,
  "maxRetries": 3,
  "apiKey": "",
  "hasApiKey": true,
  "apiKeyMask": "已保存 API Key"
}
```

注意：`apiKey` 永远返回空字符串。

### 保存配置

```http
PUT /api/settings/llm
Content-Type: application/json
```

请求示例：

```json
{
  "enabled": true,
  "provider": "deepseek",
  "baseUrl": "https://api.deepseek.com",
  "model": "deepseek-v4-pro",
  "temperature": 0.2,
  "maxRetries": 3,
  "apiKey": "sk-..."
}
```

处理规则：

- `baseUrl` 保存前去掉末尾 `/`。
- `model` 和 `provider` 保存前去除首尾空格。
- 如果请求没有携带 `apiKey`，保留旧密钥。
- 如果请求携带非空 `apiKey`，替换旧密钥。
- 保存后返回脱敏配置。

### 清除密钥

```http
DELETE /api/settings/llm/api-key
```

处理规则：

- 将 `api_key` 清空。
- 建议同时把 `enabled` 设为 `false`，避免后续业务误调用。
- 返回脱敏配置。

### 测试连接

```http
POST /api/settings/llm/test
```

返回示例：

```json
{
  "status": "available",
  "message": "密钥可用，模型连接正常",
  "provider": "deepseek",
  "model": "deepseek-v4-pro"
}
```

建议状态值：

| 状态 | 说明 |
| --- | --- |
| `disabled` | 大模型未启用。 |
| `missing_key` | 未配置 API Key。 |
| `unconfigured` | Base URL 或模型名称缺失。 |
| `available` | 连接成功。 |
| `unavailable` | 请求失败、鉴权失败、网络失败或返回异常。 |

连通性测试请求建议调用：

```text
POST {baseUrl}/chat/completions
```

请求体示例：

```json
{
  "model": "deepseek-v4-pro",
  "messages": [
    { "role": "system", "content": "只回复 OK。" },
    { "role": "user", "content": "ping" }
  ],
  "temperature": 0,
  "max_tokens": 16
}
```

只要供应商返回 `choices` 或 `usage`，即可视为配置基本可用。

## 数据库存储

MVP 可以用通用系统设置表保存配置：

```sql
CREATE TABLE system_setting (
  id INT PRIMARY KEY AUTO_INCREMENT,
  setting_key VARCHAR(128) NOT NULL UNIQUE,
  setting_value JSON NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
```

保存时使用固定 key：

```text
llm_settings
```

`setting_value` 示例：

```json
{
  "enabled": true,
  "provider": "deepseek",
  "api_key": "sk-...",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-v4-pro",
  "temperature": 0.2,
  "max_retries": 3
}
```

生产环境建议增强：

- API Key 字段加密后入库。
- 记录最后测试时间和最后测试状态。
- 保存修改人、修改时间和审计日志。
- 多租户系统应按学校、组织或用户隔离配置。

## 后端服务分层

推荐分成两层：

```text
settings_service.py  # 保存、读取、脱敏、测试连接
llm_service.py       # 业务运行时统一模型调用
```

`settings_service.py` 负责：

- 合并默认配置和数据库配置。
- 读取配置时隐藏明文 API Key。
- 保存配置时保留旧 API Key 或替换新 API Key。
- 清除 API Key。
- 连通性测试。

`llm_service.py` 负责：

- 每次调用前读取最新配置。
- 校验模型是否启用、API Key 是否存在、Base URL 和模型名是否完整。
- 调用 OpenAI-compatible `/chat/completions`。
- 提供 `chat_text`、`chat_json` 和可选的 `chat_json_stream`。
- 解析返回内容。
- JSON 输出失败时自动发起修复请求。

## 统一调用接口

建议业务模块只使用以下接口：

```python
class LLMService:
    def chat_json(
        self,
        prompt: str,
        schema: dict | None = None,
        max_retries: int | None = None,
    ) -> dict:
        pass

    def chat_text(self, prompt: str, max_retries: int | None = None) -> str:
        pass
```

批改、题目分析、量规生成、证据提取等结构化任务必须使用 `chat_json`。普通总结或说明类任务可以使用 `chat_text`。

JSON 调用建议流程：

1. 业务 prompt 明确要求只输出合法 JSON。
2. 如有 schema，将 schema 附加到 prompt。
3. 请求模型时添加 `response_format: {"type": "json_object"}`。
4. 解析 JSON。
5. 解析失败时，把原始输出交给模型修复 JSON。
6. 多次失败后抛出异常，由业务服务标记人工复核或任务失败。

## 前端交互建议

模型配置页面建议包含：

- 启用开关。
- 供应商下拉框。
- Base URL 输入框。
- 模型下拉框或输入框。
- API Key 密码输入框。
- 温度滑块或数字输入。
- 最大重试次数数字输入。
- 保存按钮。
- 清除密钥按钮。
- 连通性测试按钮。
- 当前状态提示。

前端校验规则：

- 启用模型时，必须存在 API Key 或后端已保存 API Key。
- 启用模型时，`baseUrl` 不能为空。
- 启用模型时，`model` 不能为空。
- API Key 输入框只在用户主动编辑时提交新值。
- 后端不可用时可以暂存到 `localStorage`，但只能作为开发环境兜底；正式模型调用仍必须以后端配置为准。

当前 GradeTap 使用的本地缓存 key：

```text
gradetap.llmSettings
```

本地缓存只保存：

```json
{
  "enabled": true,
  "provider": "deepseek",
  "baseUrl": "https://api.deepseek.com",
  "model": "deepseek-v4-pro",
  "temperature": 0.2,
  "maxRetries": 3,
  "hasApiKey": true,
  "apiKeyMask": "已保存 API Key"
}
```

不要把明文 API Key 长期写入 `localStorage`。如果开发阶段需要临时兜底，也应尽快切回后端保存。

## 接入新模型供应商

优先选择 OpenAI-compatible 接口的供应商，这样只需要新增前端预设：

1. 在 `llmProviders` 中新增供应商。
2. 填写供应商 `baseUrl`。
3. 填写常用模型名列表。
4. 使用 `/api/settings/llm/test` 验证。
5. 如果供应商返回格式兼容 `choices[0].message.content`，不需要修改 `LLMService`。

如果供应商不兼容 OpenAI 格式，需要在 `LLMService` 中增加 provider adapter：

```text
LLMService
  -> DeepSeek/OpenAI adapter
  -> Qwen compatible adapter
  -> Custom provider adapter
```

但业务服务仍然只调用 `llm_service.chat_json()` 或 `llm_service.chat_text()`。

## 错误处理

建议统一处理以下错误：

- 大模型未启用：提示用户进入模型设置启用。
- 未配置 API Key：提示用户填写密钥。
- Base URL 或模型为空：提示配置不完整。
- HTTP 401/403：提示密钥无效或权限不足。
- HTTP 404：提示 Base URL 或模型名称可能错误。
- HTTP 429：提示额度、限流或并发过高。
- HTTP 5xx：提示供应商服务异常，稍后重试。
- JSON 解析失败：自动修复，仍失败则标记人工复核。
- 流式输出中断：关闭事件流，保留已有状态并提示重试。

## 安全规则

- 不要把 API Key 写死在前端代码、后端代码或文档示例中。
- 不要把真实 API Key 提交到 Git。
- 后端读取配置时不要返回明文 API Key。
- 日志中不要打印请求头 `Authorization`。
- 连通性测试失败时不要把完整供应商响应直接展示给普通用户，避免泄露敏感信息。
- 生产环境建议对数据库中的 API Key 加密保存。
- 多租户环境必须隔离不同学校、组织或用户的密钥。

## 给其他 AI 的实现提示词

可以把下面这段交给其他 AI，让它在类似项目中实现大模型配置功能：

```text
请为当前项目实现“大模型配置”功能。

要求：
1. 前端提供模型配置页面，字段包括 enabled、provider、baseUrl、model、apiKey、temperature、maxRetries。
2. 前端支持供应商预设：DeepSeek、OpenAI Compatible、通义千问、豆包、自定义。
3. 后端提供 GET /api/settings/llm、PUT /api/settings/llm、DELETE /api/settings/llm/api-key、POST /api/settings/llm/test。
4. API Key 只允许保存或替换，不允许通过 GET 接口返回明文；GET 只返回 hasApiKey 和 apiKeyMask。
5. 配置保存在数据库 system_setting 表中，setting_key 使用 llm_settings，setting_value 使用 JSON。
6. 所有业务模型调用必须统一经过 services/llm_service.py，不允许业务模块直接请求模型供应商。
7. LLMService 至少提供 chat_json(prompt, schema=None, max_retries=None) 和 chat_text(prompt, max_retries=None)。
8. chat_json 必须要求模型输出合法 JSON，并在 JSON 解析失败时自动请求模型修复 JSON。
9. 连通性测试调用 {baseUrl}/chat/completions，使用 Bearer API Key，请求一个 ping 消息。
10. 实现时注意密钥脱敏、错误提示、HTTP 异常处理、Base URL 去除末尾斜杠，以及生产环境密钥加密的扩展点。
```

## 验收清单

实现完成后至少验证：

- 打开配置页面能看到默认配置。
- 保存配置后刷新页面，配置仍存在。
- GET 配置接口不返回明文 API Key。
- 清除密钥后 `hasApiKey=false` 且模型自动停用。
- 连通性测试能正确区分未启用、缺少密钥、配置缺失、连接成功和连接失败。
- 业务服务调用模型时只依赖 `LLMService`。
- 切换供应商会自动更新 Base URL 和默认模型。
- JSON 型模型任务在非法 JSON 时会触发修复流程。
- 日志、页面和错误信息中不会泄露完整 API Key。
