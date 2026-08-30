# OpenBase 部署架构草案 - v1.4.3

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.3 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | SA-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/design/ |

---

## 1. 部署拓扑（Dev 环境）

```
┌─────────────────────────────────────────────────────────┐
│ 本机（Windows，Dev 环境）                                 │
│                                                         │
│  OpenBase 后端   :8000  uvicorn openbase.demo_app:app   │
│  OpenBase 前端   :5173  vite dev（或构建产物 nginx）      │
│  OpenLLM 后端    :8001  uvicorn backend.main:app（PORT=8001 覆盖默认 8000）│
│                                                         │
│  共享基础设施（.env.shared-infra）：                     │
│    PostgreSQL :5432（openbase + openllm 双 schema）      │
│    Redis      :6380                                      │
└─────────────────────────────────────────────────────────┘
```

| 服务 | 端口 | 启动方式 | 说明 |
|------|:---:|----------|------|
| OpenBase 后端 | 8000 | `uvicorn openbase.demo_app:app` | 新增 llm_proxy 模块启用 |
| OpenBase 前端 | 5173 | `npm run dev` | 2 页改造走 llm-proxy |
| OpenLLM 后端 | 8001 | 环境变量 `PORT=8001` + `uvicorn main:app`（OpenLLM 项目 backend 目录） | 默认 8000 被覆盖，与 OpenBase 错开 |
| PostgreSQL | 5432 | 共享 | OpenLLM 需自身库（openllm schema/库） |
| Redis | 6380 | 共享 | OpenLLM 认证/缓存依赖 |
| ClickHouse | 8123 | OpenLLM 自持（可选） | 用量统计，缺失时 OpenLLM 降级 |

## 2. 环境变量设计

| 环境变量 | 值 | 归属 |
|----------|-----|------|
| `PORT=8001` | OpenLLM 启动端口 | OpenLLM .env |
| `llm_api_key` | sk-openllm-xxx（OpenLLM 创建） | OpenBase .env（settings 读取） |
| `llm_upstream_base` | `http://127.0.0.1:8001` | OpenBase .env |
| `llm_upstream_timeout` | `20.0` | OpenBase .env（默认） |
| `llm_stream_timeout` | `120.0` | OpenBase .env（SSE 流读） |
| OpenLLM SECRET_KEY / PG / Redis | OpenLLM .env | 沿用 OpenLLM 既有配置 |

## 3. 部署步骤（草案）

```
1. 启动共享基础设施（.env.shared-infra：PG/Redis）
2. 启动 OpenLLM：cd D:\Trae CN\myproject\Dev\OpenLLM\backend && set PORT=8001 && uvicorn main:app
   → 验证 GET /health（healthy）与 GET /openllm/v1/health（code=0）
3. 创建/确认 OpenLLM 服务 API Key（POST /api/v1/auth/api-keys）→ 配置 OpenBase .env llm_api_key
4. 启动 OpenBase 后端：uvicorn openbase.demo_app:app（llm_proxy 模块已启用）
   → 验证 GET /api/v1/llm-proxy/health（OpenBase JWT）
5. 启动 OpenBase 前端：npm run dev
   → 走查 /openllm/models、/openllm/conversations
```

## 4. 端口冲突治理

| 冲突场景 | 处理 |
|----------|------|
| OpenLLM 默认 8000 与 OpenBase 冲突 | `PORT=8001` 覆盖（OpenLLM settings.PORT 读取 env） |
| 8001 被其他进程占用 | 启动前 `netstat -ano | findstr 8001` 检测；确认占用进程后换端口或释放 |
| 部署脚本 | 启动脚本封装端口检测 + 健康检查等待（联调收尾 BL-143-01 落地） |

## 5. 回滚与风险

| 项 | 内容 |
|----|------|
| 回滚 | llm_proxy 模块禁用（demo_app enable_module 移除）即回退至 mock 前端；无数据迁移（无新增表），回滚零成本 |
| 依赖风险 | OpenLLM 依赖重（PG/Redis/ClickHouse），8001 启动失败 → 健康检查先行 + 依赖降级（详见单版本规划风险清单） |
| 发布验证 | Step 5 部署执行报告按本草案 + 上线检查报告执行 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | SA-OpenBase-Dev | 初始创建：Dev 部署拓扑（OpenBase 8000 + OpenLLM 8001 + 共享基础设施）、环境变量、部署步骤草案、端口冲突治理、回滚方案 |
