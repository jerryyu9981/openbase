# OpenBase 运维手册 - v1.4.3

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.3 |
| 文档版本 | v1.0.0 |
| 状态 | [Final] |
| 作者 | DO-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/operation/ |

---

## 1. 服务清单

| 服务 | 端口 | 启动命令 | 健康检查 |
|------|:---:|----------|----------|
| OpenBase 后端 | 8000 | `python -m uvicorn openbase.demo_app:app`（项目根） | /openapi.json 或 llm-proxy/health（登录后） |
| OpenLLM 后端 | 8001 | `cd Dev\OpenLLM\backend && $env:PORT=8001; python -m uvicorn main:app` | GET /openllm/v1/health（免鉴权） |
| OpenBase 前端 | 5173 | `npm run dev`（openbase-ui） | 首页可达 |

## 2. 运维移交清单

| 项 | 内容 |
|----|------|
| 关键配置 | OpenBase `.env`：OPENBASE_LLM_API_KEY（OpenLLM 服务 Key）/ OPENBASE_LLM_UPSTREAM_BASE（http://127.0.0.1:8001）/ OPENBASE_LLM_UPSTREAM_TIMEOUT |
| 密钥管理 | OpenLLM API Key 在 OpenLLM 侧创建（POST /api/v1/auth/api-keys，任意登录用户可建，一次性返回）；轮换时 OpenLLM 重建 + 更新 OpenBase .env + 重启 |
| 常见故障 1：模型列表 401 | 上游 Key 失效 → OpenLLM 重建 Key → 更新 .env → 重启 OpenBase |
| 常见故障 2：模型列表 502 | OpenLLM 8001 未启动 → 启动 OpenLLM → 验证 /openllm/v1/health |
| 常见故障 3：对话 5001 | 模型不可用（本地 Ollama 未运行 / 云端 Key 无效）→ 配置可用模型 |
| 常见故障 4：会话页 401 | OpenLLM M1 未实施（JWT-only）→ 已知限制，任务书登记 |
| 排障命令 | `netstat -ano | findstr 8000/8001`（端口占用）；`Get-Content .env`（配置核对，注意密钥脱敏展示） |
| SLA/SLO | Dev 环境无 SLA；llm-proxy 转发 P95 ≤ 500ms；SSE 首包 ≤1s |

## 3. 日志与监控

| 项 | 说明 |
|----|------|
| 日志位置 | OpenBase 控制台（uvicorn 输出）；llm_proxy 模块 WARN 记录上游异常（path/status） |
| 关键日志 | `llm-proxy upstream unreachable`（8001 不可达）；`llm-proxy sse upstream error`（流式上游错误） |
| 监控入口 | 网关服务视图（/gateway/services 含 openllm 实例健康） |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | DO-OpenBase-Dev | 初始创建：服务清单/移交清单/故障排障/日志监控 |
