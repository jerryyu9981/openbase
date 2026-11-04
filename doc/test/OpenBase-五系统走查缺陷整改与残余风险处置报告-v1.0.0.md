# OpenBase 五系统走查缺陷整改与残余风险处置报告 - v1.1.0

## 文档元信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | TEST-WALK-FIX-001 |
| 文档版本 | v1.1.0 |
| 文档状态 | [Review] |
| 适用环境 | 本机 Windows 原生进程（无 Docker）；共享设施 `192.168.0.151`（PG 5432 / Redis 6380 / Qdrant 6333） |
| 编制日期 | 2026-11-04 |
| 编制 | FA-OpenBase-Dev（AI 辅助）/ 待人工复核 |
| 处置范围 | ① 走查缺陷 D-1~D-9；② 执行单 v1.0.5 §13 残余风险 R-13-1~R-13-3；③ 生产硬门禁 G-1~G-7 本地可核查部分；④ 数据库死锁/长事务防护方案；⑤ 五系统测试基线清零（OpenRAG 全量单测 19 项既有失败、OpenMemory 顺序污染与收集中断） |
| 上游依据 | `OpenBase-五系统全栈走查报告-v1.0.1.md` §6；`OpenBase-四系统APIKey优化生产窗口执行单与回滚方案-v1.0.5.md` §13；`OpenBase-生产侧硬门禁待办清单与回执-XR-OPS-08-v1.0.1.md` §1~§8 |
| 判定口径 | 代码/配置缺陷以「根因修复 + 回归验证」判闭合；生产环境依赖项以「本地可核查结论 + 明确交接对象」判阶段性闭合，不替代生产验收 |

> 本报告仅记录**本机测试实例**的整改与验证结果，不作为生产验收证据（对齐 R-13-3）。

---

## 1. 处置口径

| 分类 | 判定规则 |
| --- | --- |
| 已修复 | 根因修改 + 单元/回归验证通过 + 证据落盘 |
| 复测通过 | 无需改码，warm 态复测满足判据；记录原判定为环境抖动的依据 |
| 正确降级 | 环境不具备能力（如无 GPU），系统按设计返回明确错误，不做无效依赖安装 |
| 生产阻塞 | 依赖生产参数/授权/真实拓扑，本机无法闭合；转 OPS/DBA/IdP 交接 |

---

## 2. 走查缺陷 D-1~D-9 处置台账

| 编号 | 级别 | 根因 | 处置动作 | 验证证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| D-1 | P1 | OpenMemory `search()` 直接调用被 qdrant-client 1.20 移除的 `AsyncQdrantClient.search`，语义检索固定 500 | `storage/vector_store.py` 与 `multitenancy/adapters/qdrant_adapter.py` 增加 `query_points`/`search` 双路径适配；补回落单测 | `xr08-postfix-probe-20261104-022751.json`（`/api/v1/recall`、`memory-proxy/recall` 均 200）；OpenMemory 单测 75 项通过 | 已修复 |
| D-2 | P2 | 前端深链在模块路由注册表就绪前安装路由器，`router.resolve` 告警 `No match found` | `openbase-ui/src/main.ts` 深链引导预算由 2.5s 提升至 12s（根入口仍 2.5s） | `xr08-ui-e2e-openllm-fix-20261104.json`（openllm 11/11 PASS、0 warning） | 已修复 |
| D-3 | P2 | OpenMemory 文档页白名单未覆盖 `/redoc` | `gateway/gateway.py` 白名单新增 `/redoc` | 复测 `/docs`、`/redoc`、`/openapi.json` 均 200 | 已修复 |
| D-4 | P2 | 冷启动后上游首次调用慢，proxy 默认 10s 阈值偏紧 | 维持 10s 常规 / 30s 慢路径超时；warm 态复测确认 | `xr08-postfix-probe-20261104-022751.json` 全 200，`gateway/ping` 22.6s→1.02s | 复测通过 |
| D-5 | P3 | 启动后瞬时资源竞争 | 不修改 | 复测 `/api/v1/auth/me` 0.1s 200 | 观察项 |
| D-6 | P2 | OpenBase Token 与 OpenLLM 签发/校验口径未统一 | 代码侧无本机可闭合项；依赖 G-2 网关与 G-3 IdP 参数对齐 | — | 生产阻塞 |
| D-7 | P3 | 无 NVIDIA GPU 且未安装 `pynvml` | 不安装无效依赖；确认 503 + 明确提示为设计降级 | `nvidia-smi` 不存在、`pynvml` 未安装；接口 503 提示明确 | 正确降级 |
| D-8 | P3 | OpenRAG 健康路由仅挂在 `/api/v1` 前缀 | `openrag/main.py` 新增根 `/health` 轻量探针（不触碰 DB/向量库） | 根 `/health` 200 且 `/api/v1/system/health` 仍 200 | 已修复 |
| D-9 | P3 | 本机空闲内存约 1.1GB，CLIP/向量组件加载慢 | 不修改；编排器已提供 300s 门限 | 冷启动 136~280s，服务最终健康 | 观察项（转运维内存配额） |

---

## 3. 残余风险 R-13-1~R-13-3 处置台账

| 编号 | 原风险 | 核查结论 | 处置 | 状态 |
| --- | --- | --- | --- | --- |
| R-13-1 | `pymupdf4llm 2.0` 与降级后的 `pymupdf` 不兼容 | 全仓检索 `pymupdf4llm` 无运行时代码引用（OpenRAG 仅使用 `fitz`/`pymupdf 1.24.14`）；该包未安装 | 不引入该依赖；保持 `fitz` 解析链路 | 不构成阻断（保留为启用前置） |
| R-13-2 | `qdrant-client 1.20.0` 与 Qdrant Server `1.7.4` 主/次版本不匹配 | 实测共享 venv `qdrant-client 1.20.0`、OpenMemory venv `1.7.3`、服务端 `1.7.4`；已定位 **OpenMemory** 与 **OpenRAG** 两处 `search` 调用在 1.20 下不存在 | 两仓均落地 `query_points`/`search`（OpenRAG 另含 `query_batch_points`/`search_batch`、稀疏 `using="sparse"`）双路径适配，并补回落单测 | 已缓解（读写路径均可运行）；生产仍按 G-4 复核 |
| R-13-3 | 本机为共享测试实例，非生产拓扑 | 本机结果仅作整改验证，不替代生产验收 | 报告显式标注；生产验证仍由 G-1~G-7 闭合后执行 | 生产阻塞 |

> 补充发现（本轮新增）：OpenRAG `storage/qdrant.py` 的 `search`/`batch_search`/`search_sparse` 与 `storage/sqlite.py`、`storage/postgres.py` 的 `list_documents` 状态过滤存在同类缺陷——前者在 qdrant-client 1.20 下必失败，后者对大小写敏感导致小写状态静默过滤为空。均已随本轮修复。

---

## 4. 生产硬门禁 G-1~G-7 逐项核查

| 编号 | 门禁 | 本地可核查部分与结论 | 仍需生产闭合 | 阶段结论 |
| --- | --- | --- | --- | --- |
| G-1 | PEM `0600` 只读挂载 | G-1.5 日志抽样扫描：本地日志目录 `BEGIN PRIVATE KEY` / `BEGIN RSA PRIVATE KEY` 命中 **0** | 私钥下发、`install -m 600` 落盘、非服务账号 `EACCES`、移走 PEM 拒启 | 本地部分通过；主体生产阻塞 |
| G-2 | 网关地址与路由参数 | **已修正本单口径**：G-2.3 与 §4.1 端口统一为 OpenBase 8000 / OpenLLM 8001 / OpenRAG 8010 / OpenMemory 8020 / DPS 8030（与 `scripts/service-orchestrator.ps1` 一致）；本机五仓直连可达 | 生产 base URL、JWKS/吊销端点、网关超时 ≥3.0s、可信代理网段、TLS/CA | 文档口径已闭合；取值生产阻塞 |
| G-3 | IdP 生产参数与 issuer 判重 | 本机 OIDC-IdP 8090 `/health`、discovery、`/jwks` 均 200，`/authorize` 缺参 422、`/userinfo` 无令牌 401（门禁生效） | `issuer`、端点集合、`client_id/secret`、`redirect_uri`、scopes、back-channel 判重 | 本机链路通过；取值生产阻塞 |
| G-4 | DBA 会话与生产 PG 基线 | 测试实例基线 `verdict=BASELINE_CAPTURED`、列数 15、`missing_required_columns=[]`；**死锁防护已落地并验证**（见 §5） | 变更单、DBA 会话、生产实例幂等 DDL、生产基线重跑与归档 | 参数/代码侧闭合；生产执行阻塞 |
| G-5 | DPS `.env` 18 键 | 本机未做生产填值（按本单禁止以测试值冒充生产） | 18 键逐项 `present=18/commented=0/duplicate=0`，重启探活 | 生产阻塞 |
| G-6 | 四仓 58 键 | 同上；本机仅核对键名口径 | OpenBase 9 / OpenLLM 15 / OpenRAG 17 / OpenMemory 17 逐键转有效值 | 生产阻塞 |
| G-7 | 统一复核与回执 | 回执模板齐备（§9） | 五仓键存在性复核全绿 + 三方签署 | 生产阻塞 |

---

## 5. 数据库死锁与长事务防护

### 5.1 方案

| 项 | 取值 | 落地位置 |
| --- | --- | --- |
| `lock_timeout` | `3000ms` | `openbase/core/db/session.py` 连接级 `asyncpg server_settings`（PG 直接下发，等待锁 3s 失败 `55P03`） |
| `statement_timeout` | `30000ms` | 同上，限制单条语句 30s |
| 可配置开关 | `OPENBASE_DB_LOCK_TIMEOUT_MS` / `OPENBASE_DB_STATEMENT_TIMEOUT_MS` | `openbase/settings.py`（默认 3000 / 30000） |
| 会话参数权威 | 执行单 §13、门禁单 §6.1.4 | — |
| 禁止项 | 不得在连接上执行 `Base.metadata.create_all` | 迁移仍走幂等 DDL |

### 5.2 锁顺序核查

| 检查点 | 结论 |
| --- | --- |
| 审计链 advisory 锁 | `before_flush` 中 `pg_advisory_xact_lock` 在本事务 DML 之前获取 |
| 行锁 | 全仓检索无 `with_for_update`，不存在「先行锁后 advisory」的反转路径 |
| 结论 | 「advisory → 行锁」单一顺序成立，无锁反转条件 |

### 5.3 验证证据

| 证据 | 结论 |
| --- | --- |
| `xr08-db-guard-verify-20261104-020331.json` | 建连后 `SHOW lock_timeout=3s`、`statement_timeout=30s`；`instance_deadlocks_total=0` |
| `xr08-db-deadlock-probe-20261104-014115.json` | `pg_stat_database.deadlocks=0`；无阻塞会话、无 >60s 长事务、无未授予锁 |
| `tests/test_settings.py`（新增用例） | 默认值 3000/30000 与环境变量覆盖生效 |

### 5.4 回滚

移除两项 `server_settings` 即恢复 PG 默认（0 = 不限制）；该改动为连接参数，不涉及 schema，重启生效。

---

## 6. 回归验证记录

| 对象 | 命令/方式 | 结果 |
| --- | --- | --- |
| OpenMemory 单测 | `pytest tests --ignore=tests/e2e --ignore=tests/performance --ignore=tests/benchmark` | 1751 项通过 / 41 跳过 / 0 失败（`pytest 8.4.2` + `pytest-asyncio 0.24.0`，符合 `pyproject.toml` 约束） |
| OpenRAG 全量单测 | `pytest tests/unit` | **2936 项通过 / 1 跳过 / 0 失败**（19 项既有失败已清零） |
| OpenRAG 存储+检索单测 | `pytest tests/unit/storage tests/unit/retrieval` | 403 项通过（含新增 `query_points` 双路径与回落用例） |
| 修复后定向探针 | `tmp/xr08/postfix_probe.py` | 16 项端点全部 200，`failures=0` |
| 前端 openllm 模块 E2E | `ui_e2e_all_services.mjs` | 11/11 PASS、0 warning |
| OpenBase 静态检查 | `python -m ruff check openbase tests` | 结果见 §6.1 |
| OpenBase 全量单测 | `python -m pytest tests` | 结果见 §6.1 |
| 前端生产构建 | `npm run build` | 结果见 §6.1 |

### 6.1 本次执行结果（2026-11-04）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| OpenBase 静态检查 | `ruff check openbase tests` | **All checks passed!**（exit=0） |
| OpenBase 全量单测 | `pytest tests` | **全量通过**（exit=0） |
| 前端生产构建 | `npm run build` | **成功**，`✓ built in 47.51s`（`dist/` 产出正常） |
| OpenMemory 单测 | `pytest tests --ignore=tests/e2e --ignore=tests/performance --ignore=tests/benchmark` | 1751 通过 / 41 跳过 / 0 失败 |
| OpenRAG 全量单测 | `pytest tests/unit -q` | 2936 通过 / 1 跳过 / 0 失败 |
| OpenRAG 存储+检索 | `pytest tests/unit/storage tests/unit/retrieval` | 403 项通过 |
| 修复后定向探针 | `postfix_probe.py` | 16/16 端点 200，`failures=0` |
| 前端 openllm E2E | `ui_e2e_all_services.mjs` | 11/11 PASS、0 warning |

### 6.2 全量回归中伴随发现并修复的既有问题

| # | 现象 | 根因 | 处置 |
| --- | --- | --- | --- |
| 1 | `test_identity_t2/t3` 3 项失败，身份门禁聚合 FAIL | 测试桩 `_FakeOidcClient` 缺 `profile` 属性，而 `oidc.py` 已按 profile 分支 | 两处测试桩补 `profile="generic"` |
| 2 | `test_log_reserved_keys` 失败 | `abac_policy_store` 以保留键 `name` 写入日志 `extra` | 改为 `policy_name` |
| 3 | 源码编码契约测试失败 | `tmp/xr08/` 临时 PowerShell 脚本缺 BOM（非仓库产物） | 删除临时脚本 |
| 4 | `test_storage_s3` 3 项失败 | `.venv-test` 缺 S3 可选依赖 `boto3` | 安装 `boto3==1.43.83`（与既有 `security-pip-list` 证据一致） |
| 5 | 生产配置用例 13 项失败 | 用例未随「生产禁止内置默认 MCP 静态 Key」门禁更新 | 用例显式提供 `mcp_api_keys=""` + 虚拟摘要 |
| 6 | OpenRAG 全量单测 19 项失败（回退基线 20 项） | ① 7 项测试期望未随产品契约更新（状态枚举大写、`APP_VERSION` 事实源优先级、嵌套 `BaseSettings` 读 `.env`）；② 12 项为 `test_compaction.py` 仅恢复部分 `openrag*` `sys.modules` 键，残留 `openrag.core.exceptions` 副本导致异常类重复，`isinstance`/异常映射失配 | 测试隔离改为「全量快照 + 整体回填」；状态断言与 `tenant_code` 签名对齐；`APP_VERSION` 回退用例按事实源优先级重写；回归 **2936 通过 / 1 跳过 / 0 失败**，详见 OpenRAG `DevLogReport-v1.0.0` |
| 7 | OpenMemory 全量单测顺序执行 278 项失败 + 默认收集 `INTERNALERROR(SystemExit)` | `asyncio.run()` 结束时清空线程当前事件循环；`tests/e2e/test_full_e2e_v660.py` 模块级直接执行并 `sys.exit` | `conftest.py` 增加事件循环兜底/清理夹具；e2e 脚本改为 `__main__` 保护；回归 **1751 通过 / 41 跳过 / 0 失败** |

---

## 7. 证据清单

| 证据 | 路径 |
| --- | --- |
| 修复后定向探针 | `doc/audit/verification/evidence/xr-ops-08/xr08-postfix-probe-20261104-022751.json` |
| 死锁/长事务探针 | `doc/audit/verification/evidence/xr-ops-08/xr08-db-deadlock-probe-20261104-014115.json` |
| 连接级超时验证 | `doc/audit/verification/evidence/xr-ops-08/xr08-db-guard-verify-20261104-020331.json` |
| 前端 E2E（openllm 修复） | `doc/audit/verification/evidence/xr-ops-08/xr08-ui-e2e-openllm-fix-20261104.json` |
| 基线（测试实例） | `doc/audit/verification/evidence/xr-ops-08/xr08-p01-baseline-20261103-post-migration.json` |
| OpenRAG 单测修复留痕 | `OpenRAG/doc/development/OpenRAG-全量单测19项失败根因修复-DevLogReport-v1.0.0.md` |
| OpenMemory 单测修复留痕 | `OpenMemory/doc/development/OpenMemory-全量单测事件循环污染修复-DevLogReport-v1.0.0.md` |

---

## 8. 未闭合项与交接

| 项 | 原因 | 交接对象 | 前置 |
| --- | --- | --- | --- |
| G-1 PEM 权限与负向验证 | 需生产密钥管理与挂载授权 | OPS + 安全 | 变更单 |
| G-2 网关生产取值 | 需生产网关配置 | 网络 / OPS | G-4 变更单 |
| G-3 IdP 生产参数 | 需 IdP 管理员登记与判重 | IdP 管理员 / OPS | G-2 |
| G-4 生产 DBA 会话与基线 | 需生产实例授权 | 生产 DBA | 变更单 |
| G-5 / G-6 键填值 | 禁止以测试值冒充生产 | OPS + 研发 | G-2 / G-3 |
| D-6 跨系统 JWT 打通 | 依赖 G-2/G-3 口径 | OPS | G-2 / G-3 |
| D-9 OpenMemory 冷启动 | 本机内存配额 | 运维 | — |

---

## 9. 风险、假设与约束

- 本机验证覆盖读路径与单元回归；写路径（创建/删除集合、向量 upsert）仍须在生产复核（对齐 R-13-2 原口径）。
- 双路径适配以「客户端方法是否存在」判定，不绑定具体版本号；两仓均保留回落分支与单测。
- 生产硬门禁结论以 OPS/DBA 回执为准，本报告不替代 §9 统一回执。

---

## 10. 修订历史

| 版本 | 日期 | 修订人 | 修订摘要 | 状态 |
| --- | --- | --- | --- | --- |
| v1.0.0 | 2026-11-04 | FA-OpenBase-Dev（AI 辅助） | 首次记录：D-1~D-9 处置台账、R-13-1~R-13-3 处置、G-1~G-7 本地核查、死锁防护方案与验证、回归结果与交接清单 | [Review] |
| v1.1.0 | 2026-11-04 | FA-OpenBase-Dev（AI 辅助） | 新增 §6.2 第 7 项并闭合第 6 项：OpenRAG 全量单测 19 项既有失败清零（2936 通过）、OpenMemory 顺序污染与收集中断修复（1751 通过）；§6/§6.1 回归数据同步更新 | [Review] |
