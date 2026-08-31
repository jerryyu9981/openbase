# OpenBase 部署架构草案 - v1.4.4

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.4 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | SA-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/design/ |

---

## 1. 部署拓扑（Dev 环境）

```
┌─────────────────────────────────────────────────────────────┐
│ 本机（Windows，Dev 环境）                                    │
│                                                             │
│  OpenBase 后端   :8000  uvicorn openbase.demo_app:app       │
│  OpenBase 前端   :5173  vite dev（或构建产物 nginx）          │
│  OpenRAG 后端    :8010  openrag（OPENRAG_API_PORT=8010 覆盖默认 8000）│
│                                                             │
│  基础设施：                                                  │
│    PostgreSQL :5432（openbase + openrag）或 SQLite（openrag 降级）│
│    Qdrant     :6333（OpenRAG 向量库）                        │
│    Redis      :6380（可选）                                  │
└─────────────────────────────────────────────────────────────┘
```

| 服务 | 端口 | 启动方式 | 说明 |
|------|:---:|----------|------|
| OpenBase 后端 | 8000 | `uvicorn openbase.demo_app:app` | 新增 rag_proxy 模块启用 |
| OpenBase 前端 | 5173 | `npm run dev` | 2 页改造走 rag-proxy |
| OpenRAG 后端 | 8010 | `OPENRAG_API_PORT=8010` + `openrag`（或 uvicorn openrag.main:app） | 默认 8000 被覆盖，与 OpenBase 错开 |
| PostgreSQL | 5432 | 共享 | OpenRAG 默认 PG；本机可 SQLite 降级 |
| Qdrant | 6333 | 独立 | OpenRAG 向量库（必启） |

## 2. 环境变量设计

| 环境变量 | 值 | 归属 |
|----------|-----|------|
| `OPENRAG_API_PORT=8010` | OpenRAG 启动端口（注意前缀 OPENRAG_） | OpenRAG .env |
| `OPENRAG_DATABASE_URL` | PG 或 SQLite（本机降级） | OpenRAG .env |
| `OPENRAG_QDRANT_URL` | http://localhost:6333 | OpenRAG .env |
| `rag_upstream_base` | `http://127.0.0.1:8010` | OpenBase .env（OPENBASE_ 前缀） |
| `rag_upstream_timeout` / `rag_stream_timeout` | 20.0 / 120.0 | OpenBase .env |

## 3. 部署步骤（草案）

```
1. 启动基础设施（PG/Qdrant；OpenRAG 依赖）
2. 启动 OpenRAG：cd Dev\OpenRAG && $env:OPENRAG_API_PORT=8010; openrag
   → 验证 GET /api/v1/system/health（status=healthy 或 degraded 核心可用）
   → 验证 GET /docs（openapi 契约核验）
3. 配置 OpenBase .env：OPENBASE_RAG_UPSTREAM_BASE=http://127.0.0.1:8010
4. 启动 OpenBase 后端：uvicorn openbase.demo_app:app（rag_proxy 模块已启用）
   → 验证 GET /api/v1/rag-proxy/health（OpenBase JWT）
5. 启动 OpenBase 前端：npm run dev
   → 走查知识库管理/RAG 对话
```

## 4. 端口冲突治理

| 冲突场景 | 处理 |
|----------|------|
| OpenRAG 默认 8000 与 OpenBase 冲突 | `OPENRAG_API_PORT=8010` 覆盖（OpenRAG settings.api.port 读 OPENRAG_API_PORT env） |
| 8010 被其他进程占用 | 启动前 netstat 检测；确认占用后换端口或释放 |
| 部署脚本 | 启动脚本封装端口检测 + 健康检查等待（联调收尾 BL-144-01 落地） |

## 5. 回滚与风险

| 项 | 内容 |
|----|------|
| 回滚 | rag_proxy 模块禁用（demo_app enable_module 移除）即回退至 mock 前端；无数据迁移（无新增表），回滚零成本 |
| 依赖风险 | OpenRAG 依赖重（PG/Qdrant），8010 启动失败 → 健康检查先行 + SQLite 降级 |
| 发布验证 | Step 5 部署执行报告按本草案 + 上线检查报告执行 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | SA-OpenBase-Dev | 初始创建：Dev 部署拓扑（OpenBase 8000 + OpenRAG 8010 + PG/Qdrant）、环境变量（OPENRAG_ 前缀）、部署步骤、端口治理、回滚方案 |
