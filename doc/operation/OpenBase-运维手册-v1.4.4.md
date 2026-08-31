# OpenBase 运维手册 - v1.4.4

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.4 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | DO-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/operation/ |

---

## 1. 服务拓扑

```
统一前端（Vue3，:5173 dev / dist 静态）→ OpenBase（FastAPI，:8000）
  ├─ auth 模块（登录/JWT）
  ├─ llm_proxy 模块（→ OpenLLM :8001，Bearer API Key 注入）
  ├─ rag_proxy 模块（→ OpenRAG :8010，无上游认证，JWT 门禁）◀── v1.4.4
  └─ memory_proxy 模块（→ OpenMemory :8020）
```

## 2. 启动命令与配置

### OpenBase 后端（:8000）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenBase'
python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000
# 数据库不可达时自动降级内存用户 admin/admin123；配置经 .env（OPENBASE_ 前缀）
```

### OpenRAG 后端（:8010，独立系统）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
$env:OPENRAG_API_PORT='8010'
# 生产环境（沙箱外）使用正式库：
$env:OPENRAG_DATABASE_URL='sqlite+aiosqlite:///D:/Trae CN/myproject/Dev/OpenRAG/openrag_test.db'
& '.\.venv3\python.exe' -m uvicorn openrag.main:app --app-dir src --host 127.0.0.1 --port 8010
# 依赖：Qdrant（localhost:6333，向量库）+ 可选 PostgreSQL/ollama
```

### OpenBase 前端（:5173 dev）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenBase\openbase-ui'
npm run dev   # vite proxy /api/v1 → 127.0.0.1:8000
# 生产：npm run build → dist 静态部署
```

## 3. 关键配置（v1.4.4 新增）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| OPENBASE_RAG_UPSTREAM_BASE | http://127.0.0.1:8010 | OpenRAG 上游基地址 |
| OPENBASE_RAG_UPSTREAM_TIMEOUT | 20.0 | 非流式请求超时（秒） |
| OPENBASE_RAG_STREAM_TIMEOUT | 120.0 | SSE 流式读超时（秒） |
| OPENRAG_API_PORT | 8000→8010 | OpenRAG 监听端口（8000 与 OpenBase 冲突时覆盖） |
| OPENRAG_DATABASE_URL | sqlite | OpenRAG 数据库（生产建议 PostgreSQL） |

> 无 rag_api_key：OpenRAG 无认证，OpenBase rag-proxy 为唯一认证入口（网络约束：OpenRAG 仅内网访问）。

## 4. 常见故障与排障

| 故障 | 排查 | 解决 |
|------|------|------|
| rag-proxy 401 | 前端未登录/JWT 过期 | 重新登录（http.ts 自动刷新） |
| rag-proxy 502（SYS_502） | OpenRAG 8010 未启动 | 启动 OpenRAG + 健康检查 /api/v1/system/health |
| 创建知识库 500 | Qdrant 未启动（DB 落库 + 向量库建集失败） | 启动 Qdrant 6333（任务书 M6） |
| 文档上传 pending/error | embedding 模型/Qdrant 依赖 | 确认 OPENRAG_EMBEDDING_MODEL + Qdrant（M6） |
| RAG 回答"未找到相关信息" | 知识库无文档或检索降级 | 上传文档 + Qdrant 就绪 |
| SSE 无流式 | 浏览器 XHR 限制（llm 侧 TD-新增-011）；rag 侧已用 fetch adapter | rag 侧正常；llm 侧后续版本修复 |
| 端口冲突 8000 | 旧进程占用 | Get-NetTCPConnection 定位后 Stop-Process |

## 5. 运维命令速查

```powershell
# 健康检查
Invoke-RestMethod http://127.0.0.1:8000/api/v1/rag-proxy/health -Headers @{Authorization="Bearer $token"}
Invoke-RestMethod http://127.0.0.1:8010/api/v1/system/health

# 登录获取 token
$r = Invoke-RestMethod http://127.0.0.1:8000/api/v1/auth/login -Method Post -ContentType application/json -Body '{"username":"admin","password":"admin123"}'
$token = $r.access_token

# 全量测试 + 静态检查
python -m pytest tests ; python -m ruff check openbase tests
```

## 6. 可观测性

| 项 | 说明 |
|----|------|
| 日志 | 结构化日志（logging + extra），模块 logger "openbase.rag_proxy"；不记录 Authorization/密钥 |
| 指标 | 复用 observability 模块（http 指标挂 path 标签，如启用） |
| 排障 | 上游不可达 WARN 日志；{detail} 归一化使前端可定位 |

## 7. 运维移交清单

| 项 | 状态 |
|----|:---:|
| 运维手册 | ✅ 本文档 |
| 联系人 | DO-OpenBase-Dev（开发）/ AU-OpenBase-Dev（审计） |
| SLA/SLO | Dev 环境无 SLA；Pro 环境随部署策略确定 |
| 遗留依赖 | Qdrant（M6）/ PostgreSQL（可选）/ embedding 模型下载（M6） |

## 8. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | DO-OpenBase-Dev | 初始创建：服务拓扑/启动命令/v1.4.4 配置/故障排障/运维命令/可观测性 |
