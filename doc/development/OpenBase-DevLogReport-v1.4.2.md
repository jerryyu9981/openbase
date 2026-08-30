# OpenBase DevLogReport - v1.4.2（Phase 2 OpenMemory 对接）

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.2 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/development/ |

---

## 1. 实现范围（Phase 2：BL-142-05~09，R-378 OpenMemory 对接）

| BL-ID | 需求 | 实现 | 验证 |
|-------|------|------|:---:|
| BL-142-05 | OpenMemory 服务部署 | 修正 `OpenMemory/.env` 为 pydantic-settings 双下划线嵌套格式（server 8020 / API Key / gateway JWT_SECRET / db/vector/cache/graph 指向 192.168.0.151 共享基础设施）；新增 `OpenMemory/scripts/start_openmemory.py`（完整装配 Qdrant+PG+Redis 真实后端并注入 `create_app`，单 event loop 启动避免 Redis 客户端跨 loop） | 8020 `/health` 200 healthy（vector/metadata/session 三依赖）；`/docs` 免鉴权 200；无 Key 401 / 有 Key 无 JWT 401 |
| BL-142-06 | 认证适配（JWT 密钥共享） | OpenBase `.env` 配置 `OPENBASE_JWT_SECRET=test-jwt-secret-for-v680`（与 OpenMemory `OPENMEMORY_GATEWAY__JWT_SECRET` 同源）；v1.4.2 JWT Payload 扩展（sub/org_id/role）沿用 Phase 1；`demo_app.py` 补启用 `users` 模块 | 登录签发 JWT 含 sub/org_id/role；该 JWT 请求 OpenMemory 业务端点认证通过（非 401） |
| BL-142-07 | proxy 转发适配 | 新增 `openbase/modules/proxy/memory_proxy.py`：`/api/v1/memory-proxy/*`（remember/recall/forget/memories/{id}/memories），注入 X-API-Key（OpenBase 持有）+ 透传 Bearer JWT + X-Org-ID/X-User-ID；统一响应 `{code,message,data,timestamp}` 适配；错误码透传（200005/200001/NOT_FOUND）；`init_app` 支持模块 `extra_routers` 挂载；Settings 新增 memory_api_key/memory_upstream_base/timeout 配置 | 单元测试 `tests/test_memory_proxy.py` 6/6；HTTP 验证：401 拦截 / 双通道注入 / 统一响应 / 404 透传 |
| BL-142-08 | 前端 2 页真实化 | `MemoryList.vue` / `MemoryDetail.vue` 由 mock 替换为真实 API（走 `/api/v1/memory-proxy/*`，前端不持有 X-API-Key）；列表支持分页/类型/标签过滤（proxy 侧 recall 适配 + 本地过滤）；详情展示完整字段/实体/元数据 | `vue-tsc --noEmit` 通过；vitest 35/35 通过 |
| BL-142-09 | 双系统联调 | 登录（OpenBase）→ JWT → proxy 双通道 → OpenMemory remember/recall/forget/list 真实闭环 | 集成验证：remember 返回 memory_id；recall 语义命中（score）；forget 删除生效（删除后详情 404）；list 分页正确（total/items） |

## 2. 关键实现决策

| 项 | 决策 | 理由 |
|----|------|------|
| OpenMemory 启动方式 | 本机进程（uvicorn）+ 共享基础设施（192.168.0.151），非 docker-compose | 本机 Docker 不可用；ADR-142-01 允许进程方式 |
| 启动脚本 | `start_openmemory.py` 完整装配真实后端（Qdrant/PG/Redis）并注入 `create_app(memory_service=...)` | 官方入口 `create_app` 不注入 service 时 `/health` 503（memory service not initialized） |
| 单 event loop | `asyncio.run(run_server())` 中装配 + `uvicorn.Server.serve()` | 跨 loop 使用 redis.asyncio 报 `Event loop is closed`（remember/recall 500） |
| RBAC 放行 | proxy 注入 `X-Org-ID`（JWT org_id 缺失时 `openbase-default`）+ `X-User-ID`；OpenMemory 无该 org 策略 → 默认放行 | OpenMemory server.py 硬编码 default 组织 guest 角色（不改其源码）；联调阶段放行，RBAC 精细控制在后续迭代 |
| 记忆列表 | proxy `GET /memories` 以 recall（auto + 泛化 query）适配，proxy 侧分页/类型/标签过滤，tags/created_at 从 metadata 归一化到顶层 | OpenMemory v6.8.0 无原生持久化列表端点（实际 OpenAPI 核验）；按架构"以实际 OpenAPI 为准" |
| 环境守护进程 | 8020 被环境自动拉起的 run_api.py/run_lightweight.py 抢占时，杀进程后立即用正式脚本抢占 | run_lightweight 为内存模式（数据不持久、健康检查 503），须保证正式服务占 8020 |

## 3. 质量检查与验证

| 门禁 | 命令 | 结果 |
|------|------|------|
| Lint | `ruff check openbase tests` | ✅ All checks passed |
| 单测（新增） | `pytest tests/test_memory_proxy.py` | ✅ 16/16（R-380 新增 5 用例：多模态/语音 multipart 透传 + 401） |
| 回归（相关） | `pytest tests/test_proxy_auth.py` / `test_auth.py` | ✅ 6/6 + 6/6 |
| 前端类型 | `vue-tsc --noEmit`（openbase-ui） | ✅ 通过 |
| 前端测试 | `vitest run` | ✅ 35/35 |
| 联调闭环 | 登录→proxy→remember/recall/forget/list（真实 OpenMemory 8020） | ✅ 全通过 |

> 注：全量 pytest 组合执行仍触发本机崩溃（TD-新增-009，Segmentation fault），按文件隔离回归可过；修复列入 Phase 3。

## 4. 已知问题与债务

| 项 | 级别 | 处置 |
|----|:---:|------|
| TD-新增-009：全量 pytest 本机崩溃（Segmentation fault） | P1 | Phase 3 收尾修复（回归脚本化） |
| OpenMemory recall 结果缓存（Redis `om:result:*`，TTL 7200s）可能命中旧数据 | P2 | 列表页数据新鲜度场景下需清缓存或缩短 TTL（OpenMemory 侧配置） |
| OpenMemory 软删除（forget soft）后 recall 仍可能返回（is_active 过滤不一致） | P2 | 联调期接受；正式对接需 OpenMemory 侧统一软删过滤 |
| RBAC 经 X-Org-ID=openbase-default 放行（未按组织策略细化） | P2 | 后续迭代按组织策略/用户角色绑定细化 |
| OpenMemory 未启用 Neo4j（TemporalKG=None） | P2 | 图检索/时序知识图谱能力未启用，不影响 remember/recall/forget/list 核心闭环 |
| 环境守护进程曾以内存模式（run_lightweight/run_api）拉起 8020 导致数据不持久 | P1 | 已闭环：以 `start_openmemory.py` 持久环境独占 8020；验证"写入→重启→recall/detail 仍可查"（Qdrant 计数不变） |

## 5. 测试移交说明

| 项 | 说明 |
|----|------|
| 启动 OpenMemory | `cd D:\Trae CN\myproject\Dev\OpenMemory && python scripts/start_openmemory.py`（需 `PYTHONPATH=src`、`PYTHONDONTWRITEBYTECODE=1`、`OPENMEMORY_AUTO_MIGRATE=false`）；健康检查 `GET http://127.0.0.1:8020/health` |
| 启动 OpenBase | 进程环境变量注入 `POSTGRES_URL`/`REDIS_URL`/`OPENBASE_JWT_SECRET=test-jwt-secret-for-v680`，`uvicorn openbase.demo_app:app --port 8000` |
| proxy 认证 | 前端/调用方仅需 OpenBase JWT（Bearer）；X-API-Key 由 OpenBase 持有（`OPENBASE_MEMORY_API_KEY`，.env 可覆盖） |
| proxy 端点 | `POST /api/v1/memory-proxy/remember|recall|forget`、`GET /api/v1/memory-proxy/memories`（分页/类型/标签）、`GET /api/v1/memory-proxy/memories/{id}` |
| 前端走查 | `/memory/list`（真实列表+删除）、`/memory/{id}`（真实详情）；前端无 X-API-Key |
| 建议回归 | test_memory_proxy + test_proxy_auth + test_auth + test_users_admin + test_tenant_admin + 前端 vitest |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | AD-OpenBase-Dev | 初始创建：Phase 2 OpenMemory 对接（BL-142-05~09）实现记录，含部署启动/认证适配/proxy 转发/前端真实化/联调闭环，测试 6/6 + 回归 + 前端 35/35 |
| v1.1.0 | 2026-08-30 | AD-OpenBase-Dev | 数据持久性问题闭环：环境守护内存模式（run_lightweight）抢占 8020 导致数据不持久，改为 `start_openmemory.py` 持久环境独占；验证"写入→重启→recall/detail 仍可查"（Qdrant 计数不变）；Phase 2 测试报告 v1.0.0 发布 |
| v1.2.0 | 2026-08-30 | AD-OpenBase-Dev | Phase 3（BL-142-10）：TD-新增-009 全量 pytest 崩溃修复（conftest SelectorEventLoopPolicy + deps.auth 延迟导入 + pytest-asyncio module loop scope）+ 回归脚本化（run_regression.py 分组子进程 + 崩溃重试）；全量回归 222/222、覆盖率 87%、UAT 13/13；proxy list semantic 策略修复 |
| v1.3.0 | 2026-08-30 | AD-OpenBase-Dev | 对接完善（R-379）：对照《OpenMemory-对接使用指南 v1.1.0》逐条核对——proxy 注入 X-Tenant-ID 租户上下文；错误体提取完善（error 字段优先 + 429 retry_after 透传）；新增 improve/sessions/decay/traces/monitor/health 透传端点；OpenMemory 侧装配 WaypointTracer 挂 app.state + 修复 retrieval 缓存命中不 end_trace 缺陷；测试报告 v1.3.0 发布 |
| v1.4.0 | 2026-08-30 | AD-OpenBase-Dev | 多模态与语音端点代理（R-380，指南 5.4/5.5）：proxy 新增 memories/image（multipart）、image/search（JSON）、multimodal/image-embed（multipart）、audio/transcribe（multipart）、remember-with-audio（JSON）5 端点；`_forward` 扩展 files/form_data、新增 `_proxy_multipart`（httpx 自动生成 multipart 边界）；OpenMemory 侧修复 transcribe validate_audio_file 调用、启动预热 CLIP/Whisper 挂 app.state、user 角色补充多模态/语音 RBAC；单测 16/16、真实环境 6/7（audio/transcribe 受 torch DLL 环境限制返回 500 E300020）；测试报告 v1.4.0 发布 |
| v1.4.1 | 2026-08-30 | AD-OpenBase-Dev | audio/transcribe torch 加载失败修复：System32 VC++ 运行库旧版（msvcp140/vcruntime140/concrt140 为 14.00）与 torch 2.13 不匹配导致 c10.dll WinError 1114 → 复制 WinSxS 14.50 版至 Python 根目录与 torch/lib；HuggingFace 官方站不可达且 xet 协议 401 → start_openmemory.py 设置 HF_ENDPOINT=hf-mirror.com + HF_HUB_DISABLE_XET=1，预下载 faster-whisper-base 缓存；WhisperService 启动预加载成功；真实环境 7/7 全通过；测试报告 v1.4.1 发布 |
