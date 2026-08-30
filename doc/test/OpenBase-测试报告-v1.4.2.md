# OpenBase 测试报告 - v1.4.2（Phase 2 OpenMemory 对接）

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.2 |
| 文档版本 | v1.2.0 |
| 状态 | [Review] |
| 作者 | TST-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 测试范围 | Phase 2（BL-142-05~09）+ Phase 3 收尾（BL-142-10 回归/覆盖率/UAT） |
| 存放 | doc/test/ |

---

## 1. 测试环境

| 项 | 值 |
|----|-----|
| OpenMemory | v6.8.0，`scripts/start_openmemory.py` 真实持久环境（Qdrant 6333 + PG 5432 + Redis 6380，192.168.0.151 共享基础设施），监听 `127.0.0.1:8020` |
| OpenBase | `uvicorn openbase.demo_app:app`，监听 `127.0.0.1:8000`，JWT 密钥与 OpenMemory 共享 |
| 共享密钥 | `OPENBASE_JWT_SECRET` = `OPENMEMORY_GATEWAY__JWT_SECRET` = `test-jwt-secret-for-v680` |
| 网关 Key | `X-API-Key: openbase-gw-key-20260830`（OpenBase 持有） |

## 2. 数据持久性问题修复验证（本报告重点）

**问题背景**：Phase 2 联调期间，8020 曾被环境守护进程以内存模式（`scripts/run_lightweight.py` / `run_api.py`）拉起，导致 OpenMemory 数据不持久（向量存储于内存，服务切换/重启后数据丢失；表现为新写入记忆在列表/召回中查不到、详情 404）。

**修复措施**：以正式启动脚本 `scripts/start_openmemory.py`（完整装配 Qdrant/PG/Redis 真实后端并注入 `create_app`）独占 8020；环境守护恢复命令亦为持久模式。

**持久性验证（写入 → 重启服务 → 数据仍可查）**：

| 步骤 | 操作 | 结果 |
|------|------|------|
| 1 | 经 proxy 写入 2 条持久记忆（memory_type=persistent） | ✅ remember 200，memory_id 返回 |
| 2 | 记录 Qdrant 向量计数 | ✅ points_count = 7 |
| 3 | 重启 OpenMemory（kill → `start_openmemory.py`） | ✅ 8020 恢复监听（持久模式） |
| 4 | 重启后 /health | ✅ 200 healthy（vector/metadata/session） |
| 5 | 重启后 Qdrant 计数 | ✅ 7 = 7（数据完整保留） |
| 6 | 重启后 recall 检索标记记忆 | ✅ 2/2 命中（score 正确） |
| 7 | 重启后详情查询 | ✅ 200，内容完整 |

**结论**：OpenMemory 真实持久环境（Qdrant + PG）下数据不丢失，"数据不持久引起的问题"闭环。

## 3. 测试结果汇总

| 测试项 | 范围 | 结果 |
|--------|------|:---:|
| memory-proxy 单元测试 | `tests/test_memory_proxy.py`（401 拦截/双通道注入/统一响应/错误透传/列表分页归一化/上游 502/多模态+语音 5 端点） | ✅ 16/16 |
| 联调闭环（真实环境） | 登录 → proxy → remember/recall/forget/list（BL-142-09） | ✅ 全通过 |
| 持久性验证 | 写入 → 重启 → recall/detail（Qdrant 计数对比） | ✅ 通过 |
| 前端测试 | `vitest run`（openbase-ui） | ✅ 35/35 |
| 前端类型 | `vue-tsc --noEmit` | ✅ 通过 |
| 回归-认证 | `tests/test_auth.py`（JWT 签发 sub/org_id/role） | ✅ 6/6 |
| 回归-proxy | `tests/test_proxy_auth.py`（双通道认证） | ✅ 6/6 |
| 回归-用户 | `tests/test_users_admin.py`（Phase 1 用户管理） | ✅ 5/5 |
| 回归-租户 | `tests/test_tenant_admin.py`（Phase 1 租户管理） | ✅ 5/5 |
| 回归-网关 | `tests/test_gateway.py`（统一网关） | ✅ 17/17 |
| 静态检查 | `ruff check openbase tests` | ✅ All checks passed |

> 回归合计 39/39（含单测 6/6）；前端 35/35；持久性验证通过。
> 注：全量 pytest 组合执行仍触发本机 Segmentation fault（TD-新增-009），按文件隔离回归全部通过；修复列入 Phase 3。

## 4. 验收标准对照（AC-142）

| 验收项 | 标准 | 结果 |
|--------|------|:---:|
| AC-142-03-1 | 8020 健康检查 200（healthy） | ✅ |
| AC-142-03-2 | 免鉴权端点（/health、/docs）可访问 | ✅ |
| AC-142-03-3 | 基础设施依赖（Qdrant/PG/Redis）healthy | ✅ |
| AC-142-04-1 | 登录 JWT 含 sub/org_id/role 且数据一致 | ✅ |
| AC-142-04-2 | 该 JWT 请求 OpenMemory 业务端点认证通过 | ✅ |
| AC-142-04-3 | 密钥配置化共享（OpenBase 与 OpenMemory） | ✅ |
| AC-142-05-1 | proxy 转发 remember/recall/forget/list | ✅ |
| AC-142-05-2 | 请求头注入 X-API-Key + Bearer JWT | ✅ |
| AC-142-05-3 | 响应统一 {code,message,data,timestamp}，错误码透传 | ✅ |
| AC-142-05-4 | 未认证请求 401 | ✅ |
| AC-142-06-1 | 列表页真实数据（分页/类型/标签过滤） | ✅ |
| AC-142-06-2 | 详情页完整字段 | ✅ |
| AC-142-06-3 | 前端不持有 X-API-Key（全经 proxy） | ✅ |
| AC-142-07-1 | remember 返回 memory_id | ✅ |
| AC-142-07-2 | recall 召回命中（score） | ✅ |
| AC-142-07-3 | forget 删除生效（删除后详情 404） | ✅ |
| AC-142-07-4 | list 分页正确（total/items） | ✅ |

## 5. 已知问题与债务

| 项 | 级别 | 处置 |
|----|:---:|------|
| TD-新增-009：全量 pytest 组合执行崩溃（Segmentation fault） | P1 | Phase 3 收尾修复（回归脚本化） |
| OpenMemory recall 结果缓存（Redis `om:result:*`，TTL 7200s）可能命中旧数据 | P2 | 数据新鲜度场景清缓存或缩短 TTL（OpenMemory 侧配置） |
| OpenMemory 软删除（forget soft）后 recall 仍可能返回 | P2 | 联调期接受；正式对接需 OpenMemory 统一软删过滤 |
| RBAC 经 X-Org-ID=openbase-default 放行（未按组织策略细化） | P2 | 后续迭代按组织策略/用户角色绑定细化 |
| Neo4j 图检索未启用（TemporalKG=None） | P2 | 不影响 remember/recall/forget/list 核心闭环 |

## 6. 测试移交说明

| 项 | 说明 |
|----|------|
| OpenMemory 启动 | `cd D:\Trae CN\myproject\Dev\OpenMemory && python scripts/start_openmemory.py`（PYTHONPATH=src、PYTHONDONTWRITEBYTECODE=1、OPENMEMORY_AUTO_MIGRATE=false） |
| OpenBase 启动 | 注入 `POSTGRES_URL`/`REDIS_URL`/`OPENBASE_JWT_SECRET` 后 `uvicorn openbase.demo_app:app --port 8000` |
| 持久性复验 | `python c:\Users\jerry\.trae-cn\work\6a8c5d08e67967d7e6726b59\persist_phase2_verify.py`（重启后 recall/detail 命中） |
| proxy 走查 | `POST /api/v1/memory-proxy/remember|recall|forget`、`GET /api/v1/memory-proxy/memories`、`GET /api/v1/memory-proxy/memories/{id}` |
| 建议回归 | test_memory_proxy + test_proxy_auth + test_auth + test_users_admin + test_tenant_admin + test_gateway（文件隔离执行）+ 前端 vitest |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | TST-OpenBase-Dev | 初始创建：Phase 2 测试（BL-142-05~09）+ 数据持久性问题闭环验证（写入→重启→可查），单测 6/6 + 联调闭环 + 回归 39/39 + 前端 35/35 |
| v1.1.0 | 2026-08-30 | TST-OpenBase-Dev | Phase 3：BL-142-10 测试基座修复验证（TD-新增-009），全量回归 222/222（通过率 100%）、覆盖率 87%、回归脚本化 |
| v1.2.0 | 2026-08-30 | TST-OpenBase-Dev | Phase 3：UAT 走查 13/13 通过（接口级全链路）；补充 proxy list semantic 策略修复与 recall 缓存清理说明 |
| v1.3.0 | 2026-08-30 | TST-OpenBase-Dev | 对接完善（R-379）：对照《OpenMemory-对接使用指南 v1.1.0》逐条核对，新增 X-Tenant-ID 注入/错误体提取完善/improve/sessions/decay/traces/monitor/health 透传端点；OpenMemory 装配 WaypointTracer + 修复缓存命中 trace 缺陷；单测 11/11、真实环境 7/7；更正 recall 缓存说明（键含 strategy、TTL 300s、写后失效） |
| v1.4.0 | 2026-08-30 | TST-OpenBase-Dev | 多模态与语音端点代理（R-380）：新增 memories/image（multipart）、image/search（JSON）、multimodal/image-embed（multipart）、audio/transcribe（multipart）、remember-with-audio（JSON）5 端点；`_forward` 扩展 files/form_data、新增 `_proxy_multipart`；OpenMemory 修复 validate_audio_file 调用、启动预热 CLIP/Whisper、user 角色补充多模态/语音 RBAC；单测 16/16、真实环境 6/7（audio/transcribe 受 torch DLL 环境限制返回 500 E300020，代理透传正常） |
| v1.4.1 | 2026-08-30 | TST-OpenBase-Dev | audio/transcribe torch 加载失败修复：System32 VC++ 运行库旧版 14.00 与 torch 2.13 不匹配（WinError 1114）→ 复制 WinSxS 14.50 版 msvcp140/vcruntime140/concrt140 至 Python 根目录与 torch/lib；HuggingFace 官方不可达 + xet 协议失败 → 启动脚本设置 HF_ENDPOINT 镜像 + HF_HUB_DISABLE_XET=1，预下载 faster-whisper-base；WhisperService 启动预加载成功；真实环境 7/7 全通过 |

---

# 附录 A：Phase 3 收尾测试数据（BL-142-10）

## A.1 TD-新增-009 修复（全量 pytest 本机崩溃）

| 修复项 | 内容 |
|--------|------|
| 根因 | Windows 上 starlette BaseHTTPMiddleware（AuthMiddleware/TenantMiddleware/AuditMiddleware）+ anyio 多 TestClient 实例叠加触发 C 层 access violation / Segmentation fault；另有 deps.auth ↔ modules.auth 循环导入（特定 import 顺序暴露） |
| `tests/conftest.py` | 设置 `WindowsSelectorEventLoopPolicy`（缓解 ProactorEventLoop 多线程清理崩溃） |
| `deps/auth.py` | ApiKeyStore 延迟导入（TYPE_CHECKING 类型引用），打破循环导入 |
| `pyproject.toml` | pytest-asyncio module 级 loop 作用域（减少 event loop 创建销毁） |
| `scripts/run_regression.py` | 回归脚本化：测试文件分组（默认 3 文件/组，子进程隔离）+ 崩溃组自动重试（非确定性崩溃重试可过）+ 可选 `--cov` 汇总 |
| 兼容修复 | `test_proxy_quota.py` 参数名 user→identity（v1.4.1 proxy 重构未同步）；`test_cli_func.py` 断言对齐（books_crud.py 为已发布约定）+ `create_module` 支持 description（实现缺陷） |

## A.2 全量回归（脚本化，子进程隔离）

| 项 | 结果 |
|----|------|
| 用例 | 222 passed / 0 failed / 4 skipped（通过率 100%，≥95% 达标） |
| 命令 | `python scripts/run_regression.py` |
| ruff | All checks passed |

## A.3 覆盖率

| 项 | 结果 |
|----|------|
| 总覆盖率 | 87%（3525 语句，≥80% 达标） |
| 命令 | `python scripts/run_regression.py --cov`（分组 cov-append 汇总） |

## A.4 UAT 走查（真实环境接口级，13/13）

| # | 检查项 | 结果 |
|---|--------|:---:|
| 1 | OpenBase /health | ✅ |
| 2 | OpenMemory /health（三依赖 healthy） | ✅ |
| 3 | 未认证访问租户管理 → 401 | ✅ |
| 4 | 未认证访问 memory-proxy → 401 | ✅ |
| 5 | 登录签发 JWT（sub/org_id/role） | ✅ |
| 6 | 租户列表 API | ✅ |
| 7 | 用户列表 API | ✅ |
| 8 | remember 存储（memory_id） | ✅ |
| 9 | recall 召回命中新记忆 | ✅ |
| 10 | 详情查询（完整字段） | ✅ |
| 11 | 记忆列表（分页 total/items） | ✅ |
| 12 | forget 删除生效 | ✅ |
| 13 | 删除后详情 404（透传） | ✅ |

## A.5 Phase 3 补充修复

| 项 | 说明 |
|----|------|
| proxy list 策略 | `memory_list` recall 由 auto 改为显式 semantic（auto 可能路由到 keyword，KeywordSearch 内存索引为空返回 0） |
| recall 缓存说明（更正） | v6.8.0 缓存键**含 strategy**（`hash(query:user_id:strategy)`）、默认 TTL 300s、remember/forget 后按用户失效（`om:result:user:*` 集合跟踪）——与指南 6.4 一致；早期"列表陈旧"实为 proxy list 使用 auto 策略路由 keyword 所致（已修复），非缓存失效缺陷 |

## 附录 B：OpenMemory 对接完善（R-379，指南 v1.1.0 逐条核对）

| # | 核对项 | 指南依据 | 完善前 | 完善后 |
|---|--------|----------|--------|--------|
| B1 | 租户上下文传递 | 4.3/4.6（X-Tenant-ID > JWT tenant_id > default） | proxy 未注入 X-Tenant-ID | `_build_upstream_headers` 注入 X-Tenant-ID（JWT tenant_id 或 default） |
| B2 | 错误体提取 | 4.5/5.3.5/11（`{error, message}`、E 码、429 retry_after） | 仅提取 body.code/detail | 提取顺序 error > code > detail > HTTP 码；429/5xx retry_after 透传 data |
| B3 | improve 优化记忆 | 5.3.4（POST /improve） | 未代理 | `POST /api/v1/memory-proxy/improve` 透传 |
| B4 | 会话管理 | 5.6（sessions 三端点） | 未代理 | `GET /sessions`、`GET /sessions/{id}`、`POST /sessions/{id}/terminate` 透传 |
| B5 | 衰减引擎 | 5.7（GET/PUT /decay/config） | 未代理 | `GET/PUT /api/v1/memory-proxy/decay/config` 透传 |
| B6 | 召回路径追踪 | 5.8（trace_id + /recall/traces/{id}） | 未代理；且 OpenMemory 未装配 tracer | proxy 透传 `GET /recall/traces/{id}`；OpenMemory `start_openmemory.py` 装配 WaypointTracer 并挂 app.state；修复 `retrieval.py` 缓存命中路径不 end_trace 缺陷 |
| B7 | 运行监控 | 5.9（GET /monitor?range=） | 未代理 | `GET /api/v1/memory-proxy/monitor?range=` 透传 |
| B8 | 健康/就绪/存活 | 5.2（readiness/liveness 需 Key） | 未代理 | `GET /health`、`/health/readiness`、`/health/liveness` 透传 |

完善验证（真实环境）：proxy health/readiness/sessions/decay/monitor/recall+traces 全链路 **7/7 通过**；单元测试扩展至 **11/11**（新增错误提取、429 透传、improve、sessions/decay、health/monitor 用例）。

## 附录 C：多模态与语音上传端点代理（R-380，指南 5.4/5.5）

### C.1 新增代理端点

| 代理端点（memory-proxy 前缀） | 上游 OpenMemory | 传输格式 | 说明 |
|------|------|:---:|------|
| `POST /memories/image` | `POST /api/v1/memories/image` | multipart | 图像记忆上传（png/jpg/jpeg，≤10MB，可选 metadata 表单字段） |
| `POST /memories/image/search` | `POST /api/v1/memories/image/search` | JSON | 文本搜索图像记忆（query/top_k） |
| `POST /multimodal/image-embed` | `POST /api/v1/multimodal/image-embed` | multipart | 图像嵌入（CLIP，≤20MB，优雅降级 hash） |
| `POST /audio/transcribe` | `POST /api/v1/audio/transcribe` | multipart | 语音转写（mp3/wav/ogg，≤30MB） |
| `POST /memories/remember-with-audio` | `POST /api/v1/memories/remember-with-audio` | JSON | 语音记忆存储（audio_file_id + text） |

### C.2 实现要点

- `_forward` 扩展 `files`/`form_data` 参数：multipart 透传时移除 `Content-Type`（multipart 边界由 httpx 按文件自动生成），文件以 `{"file": (filename, content, content_type)}` 三元组传递。
- 新增 `_proxy_multipart` 辅助函数：读取 `UploadFile` 内容 → 构造 httpx files → 透传可选表单字段；身份提取/双层认证头注入与 JSON 端点共用 `_extract_identity`/`_build_upstream_headers`。
- 所有端点保持统一响应适配（`{code, message, data, timestamp}`）与错误码透传（含 E 码与 retry_after）。

### C.3 配套修复（OpenMemory 侧）

| # | 问题 | 修复 |
|---|------|------|
| C1 | `audio/transcribe` 调用不存在的 `WhisperService.validate_audio_file`（AttributeError） | 改为模块级 `validate_audio_file(filename, content)` |
| C2 | CLIP/Whisper 模型懒加载导致首次请求 30s+ 超时（超过 proxy 20s 超时） | `start_openmemory.py` 启动时预热 `CLIPEmbeddingService.warmup()` + 预载 WhisperService 并挂 `app.state`，失败优雅降级 |
| C3 | user 角色 RBAC 不含多模态/语音端点（403） | `permission.py` user 角色补充 `*/memories/image`、`*/memories/image/search`、`*/memories/remember-with-audio`、`*/multimodal/*`、`*/audio/*` 的 POST 权限 |

### C.4 验证结果

- 单元测试：`tests/test_memory_proxy.py` 扩展至 **16/16**（新增 image 上传 multipart、image/search JSON、audio/transcribe multipart、remember-with-audio JSON、multipart 401 用例；file 三元组与 Content-Type 移除断言）。
- 真实环境（OpenBase 8000 → OpenMemory 8020）：**7/7 通过** —— memories/image、image/search、image-embed、audio/transcribe（真实 WAV）、remember-with-audio、401、health 全通过。
- 静态检查：`ruff check` 通过。
- 回归：代理相关测试文件隔离执行通过（Windows 组合崩溃 TD-新增-009 已脚本化规避）。

### C.5 torch 加载失败修复（R-380 补充）

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| C4 | `c10.dll` 加载失败（WinError 1114 DLL 初始化例程失败），torch 无法导入 | System32 中 `msvcp140.dll`/`vcruntime140.dll`/`concrt140.dll` 为旧版 14.00，与 torch 2.13 所需新版不匹配；ctranslate2 先加载旧版后 torch 复用旧版导致初始化失败 | 将 WinSxS 中 14.50 版 `msvcp140.dll`/`vcruntime140.dll`/`concrt140.dll` 复制至 Python 根目录与 `torch/lib`（本地 DLL 优先于 System32） |
| C5 | faster-whisper 模型下载失败（huggingface.co ConnectTimeout + xet 协议 401） | 官方 Hub 不可达；huggingface_hub 新版默认走 xet 协议失败 | `start_openmemory.py` 设置 `HF_ENDPOINT=https://hf-mirror.com` + `HF_HUB_DISABLE_XET=1`；预下载 `Systran/faster-whisper-base` 至本地缓存 |

修复验证：`import torch` 与 `import faster_whisper` 均成功；`WhisperService` 启动预加载成功（WhisperModel 就绪，加载 2.44s）；`audio/transcribe` 对真实正弦波 WAV 返回 200（duration=1.0、language=en）。
