# OpenBase-多系统对接联调问题复盘与根治方案-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-POSTMORTEM-v1.0.0 |
| 版本 | v1.1.0 |
| 状态 | [Review]（§8 问题-方案-批次承接总表已并入；身份域承接见身份域文档族） |
| 日期 | 2026-09-06 |
| 作者 | AD（跨项目分析） |
| 版本主题 | 六系统（OpenBase/OpenLLM/OpenRAG/OpenMemory/DPS/OIDC+统一前端）对接联调全部问题复盘：现象、根因、彻底根治方案与账本 |
| 适用范围 | 五仓库 + 统一前端 + 共享基础设施（PG/Redis/Ollama）运维与开发 |

> 事实来源：2026-09-04~06 治理 P0 批次、真实契约落地（Phase A~D）、真实联调冒烟（S0~S6）、P9 门禁、UI-E2E 与 P1/P2 登记项处理的全部实证记录（含提交号）。本复盘为唯一结论载体，配套文档：治理评审 v1.6.0、任务书 v2.6.0、冒烟清单 v1.2.0、测试对齐清单 v1.2.0、P2-2 立项方案 v1.0.0、文档体系与升级路线规划 v1.0.0。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-06 | AD（跨项目分析） | 初始版本：问题分层盘点、根因分析与根治方案、闭环/剩余账本 |
| v1.1.0 | 2026-09-06 | AD（跨项目分析） | 新增 §8 问题-方案-批次承接总表：五大根因 × S1-S6 × R1-R4 批次映射；剩余登记逐项排期；闭环项基线引用（配套文档体系与升级路线规划 v1.0.0） |

---

## 1. 摘要

联调以"真实契约、真实数据、真实链路"为目标，先后暴露 20+ 个问题。**根因可收敛为五类**：

1. **配置即代码缺位**：默认值、映射、部署值散落在各仓库 `.env`（gitignored）且互相不一致，环境可达性改变行为（约占 40% 故障，如 dps 403 组织不存在、探活打错端点、OIDC 断言漂移）。
2. **契约双轨未收敛**：stub（/profile/v1、/openmemory/v1、/openrag/v1 与真实 v2/v1 并存），探活、断言、健康检查按错轨执行（DPS 探活 401 误报、权限动作错位）。
3. **身份键语义多义**：同一字段（external_user_id / X-User-ID / person_id / org_id / tenant_id）在不同层承担不同语义（平台登录用户 vs 被画像对象），未分层建模（画像读 403、双租户错位、映射表双向混淆）。
4. **测试/运行环境同库同进程**：全量测试与真实服务共用共享 PG 与进程内全局单例（engine/settings），历史行污染与路径漂移制造假失败（OIDC '3'/'4'、注入依赖用例）。
5. **平台沙箱写限制与外部并发编辑**：掩盖真实故障（DPS 500 假象、OpenLLM 非流式 disk I/O error）、阻断提交（OpenLLM `.git`）、反复回滚文档（任务书），干扰根因定位与交付闭环。

**根治原则**：配置单一来源 + 启动契约自检；stub 显式废弃、探活与断言统一真实面；身份按"平台用户 / 组织租户 / 业务对象"三层建模；测试与运行完全隔离（分批/独立库）；沙箱边界显式声明（可写路径白名单）并纳入受管编排。

## 2. 系统拓扑与联调目标

```
统一前端(5173,vite) ──> OpenBase 网关(8000, JWT 门禁 + llm-proxy/rag-proxy/memory-proxy/dps-proxy)
OpenBase ──> OpenLLM(8001) ──> Ollama LAN(192.168.0.4:11434, llama3.2:1b)
OpenBase ──> OpenRAG(8010) / OpenMemory(8020)
OpenBase ──> DPS(8030 受管; src 默认 8000; MCP 8013) ──> 共享 PG platform schema
OpenLLM ProfileAdapter/Writeback ──> DPS /api/v2/portrait（真实契约）
OIDC IdP(8090) ── OpenBase 授权码登录
共享基础设施：PG(192.168.0.151:5432, schema: openbase/platform) / Redis(6380) / Ollama
```

目标态（各阶段验收）：P0 门禁与身份收敛 → 真实契约落地（读写两端真实）→ 冒烟全链路（S0~S6）→ P9 双租户/重启存活/隔离 → UI-E2E 全模块可用 → P2 治理收口（fail-open/sessions 隔离）。

## 3. 问题全量与分层

状态图例：✅已闭环（含提交）/ 🔄已缓解待收口 / 📋登记项。

### L1 端口与拓扑
| 问题 | 现象与根因 | 状态 |
|------|-----------|------|
| DPS 端口三态错位 | 源码默认 8000 vs 编排 8030 vs MCP 8013；OpenBase 默认 8000，早期未覆盖致自循环（dps-proxy 打到自身 401） | ✅ aae1de7/0ee504b/P0-3 + 编排显式 8030 |
| DPS stub 与 OpenRAG 端口冲突 | .env.shared-infra 曾指向 8010（被 OpenRAG 占用） | ✅ 真实 DPS 8030 落地 |
| 编排 openapi 检查期望错误 | DPS `/openapi.json` 期望 200 实 401（门禁生效属正常） | ✅ 0ee504b 期望改 401 |

### L2 身份与鉴权
| 问题 | 现象与根因 | 状态 |
|------|-----------|------|
| 空凭据默认放行 | OpenRAG/OpenMemory allow_empty_service_key/api_key 默认放行 | ✅ P0-1a 门禁 + fail-fast |
| 出站凭据形态不一 | OpenLLM Bearer vs OpenRAG X-API-Key；bypass 伪凭据 | ✅ P0-1b/P1-1 统一 X-API-Key |
| dps-proxy 403「组织不存在」 | OpenBase 默认 org-1/tenant-1（旧种子语义）未映射至 DPS 现库 dps-org-001/dps-tenant-001 | ✅ P1-1（def7ed8）映射部署值双落点 |
| OpenLLM 画像读 403（无权限 create） | external_user_id（画像 person_id）同时充当 DPS 平台用户，无 RBAC 绑定 | ✅ 补画像对象 super_admin 绑定（P1 级发布批次） |
| OpenMemory 密钥不匹配 | 进程注入 key 与 .env 不一致 → 401 | ✅ S2 换钥复跑（文档化部署注入） |
| OIDC 用户名 '3'/'4' | 测试与运行同库：固定 sub 命中历史 OidcIdentity 复用旧用户 | ✅ T2 隔离修复（23c0b79） |
| X-User-ID=1 硬绑 | 代码层已移除（v2.8.1），种子默认演示绑定未固化 | 🔄 P2-2 立项（f7dd3f0）固化收紧 |
| DPS fail-open | tenant 中间件 DB 故障按 MULTI_TENANT_ENABLED 默认放行；permission 引擎未初始化/异常放行 | 📋 P2-2 Phase1 默认 fail-closed |
| OpenMemory /sessions 无归属 | list 全量遍历、get/terminate 无归属校验 | 📋 P2-2 Phase2 归属过滤 |

### L3 契约与端点
| 问题 | 现象与根因 | 状态 |
|------|-----------|------|
| stub/real 双轨 | DPS /profile/v1（stub）vs /api/v2（真实）；健康探活无条件打 stub → real 下 401 误报 | ✅ OpenLLM 探活契约分叉（待提交 OpenLLM 仓） |
| DPS 画像 403（UI-E2E P1-1） | 见 L2 dps-proxy 映射缺失 | ✅ def7ed8 + UI 复验 |
| calculate 权限动作错位 | 读链路 POST calculate 被当作 create 权限门槛，画像对象身份未分层 | ✅ 绑定修复 + 文档 |
| llm-proxy /models 500 | 上游 OpenLLM 未就绪瞬态（非代码缺陷） | ✅ 复验 200 |
| /profile/v1 决策 | DPS 无需实现，由 ProfileAdapter 真实模式全映射 | ✅ P4 定案（任务书） |
| OpenRAG/OpenMemory stub 契约 | 真实契约未落（W4） | ✅ Phase A~D（立项方案 v1.2.0） |

### L4 数据与运行环境
| 问题 | 现象与根因 | 状态 |
|------|-----------|------|
| DPS 500 假象（L-1） | 误判 PG qmark 方言 → 实为沙箱只读致 sqlite dps.db 无法 attach | ✅ 共享 PG 化（_pg_translate 仍保留为 PG 兼容） |
| OpenLLM 非流式 500 disk I/O | 沙箱对 backend/data 只读，trace/写库失败 | ✅ 临时 env 指可写路径（根治见 §4） |
| OpenLLM .git 写受限 | 沙箱拦 index.lock | 🔄 待放行后提交 |
| PowerShell 中文乱码 | Invoke-WebRequest 非 UTF-8 | ✅ 文档化改用 Python/UTF-8 客户端 |
| 沙箱 pyc 写拦截 | 测试写 pgAdmin/site-packages 被拒 | ✅ PYTHONPYCACHEPREFIX/DONTWRITEBYTECODE 约定 |

### L5 前端与路由
| 问题 | 现象与根因 | 状态 |
|------|-----------|------|
| /openllm/recommend、reports-trend 菜单指向未注册路由 | 视图文件已建未入路由表 → 点击回 /dashboard | ✅ 8bb6dc7 补注册 |
| 模块路由父名告警（5 条） | router.addRoute('', ...) 空父名 | ✅ 8bb6dc7 改 addRoute(record) |
| 画像模块数据 403 | 同 L2 | ✅ |
| 对话管理模型下拉默认值 | 静态模板项（gpt-4o/qwen2.5-7b）易误读为动态失败 | ✅ 文档澄清 |

### L6 测试与门禁
| 问题 | 现象与根因 | 状态 |
|------|-----------|------|
| 存量 8 例断言过期 | 网关 envelope/OIDC 种子/proxy 网关化后未同步 | ✅ T1/T3（0f808e9/15b520a） |
| OIDC 空库复现 | 固定 sub 历史行污染 + 全局 engine 单例绕过 env 隔离 | ✅ T2（23c0b79）+ 分批门禁 |
| refresh NameError | P3.1 调用未定义 _resolve_tenant_code | ✅ 23c0b79 补实现（业务缺陷修复） |
| 环境注入改变行为 | POSTGRES_URL 使 demo_app/tenant 等用例路径漂移 | ✅ 分批/独立库门禁（清单 v1.2.0） |
| modules 注册表计数断言 | 模块演进 4→5 未同步 | ✅ 08f60b5 |

### L7 过程与治理
| 问题 | 现象与根因 | 状态 |
|------|-----------|------|
| 任务书外部回滚 | 并发编辑器反复反转 v1.x | ✅ 原子整文件重建基线（v2.x） |
| 文档版本记录缺失 | 修订行被覆盖 | ✅ 重填 + 即时提交 |
| 误杀服务 | 按 python 名批量杀进程波及全家 | 🔄 受管编排化（编排是唯一启动入口） |

## 4. 根因分析（详细）

### 4.1 配置即代码缺位：默认值不设防、部署值无单一来源
- **深层证据**：dps-proxy 403 的链条是 `login 无 tenant claim → dps_default_org_id=org-1（.env 旧值）→ DPS 现库无 org-1 → 403`。OpenLLM DPS real 未生效同理：`DPS_ENABLED=false` 缺省、`.env.shared-infra` 模板不自动加载、`.env` 无键。三者都是"默认值/示例值没有与真实种子数据对账"的产物。
- **机理**：Pydantic env 优先级（env > .env > 默认）与 gitignore（.env 不入库）组合，使"部署即真相"无法被代码/测试/文档单一约束；同一键在不同仓取值不同（如 DPS 端口 8000/8010/8030 三态、TRUSTED_PROXY_SOURCES=llm-proxy 与 openbase-llm-proxy 两写法），探活与断言按各自假设执行。
- **影响面**：P1-1、S4/S5 阻塞、探活误报、联调批次来回调试，占故障数最多。

### 4.2 契约双轨未收敛：stub 与真实面并存，次级系统按错轨执行
- 真实契约落地（Phase A~D）后，代码保留了 stub 兼容分支（正确），但**所有"探测性/默认性"路径仍按 stub 轨写死**：OpenLLM 网关健康探活无条件 `get_profile → /profile/v1/get`，real 模式下打真实 DPS 得到 401 → 误报 unavailable；测试断言、UI 默认项同样按旧轨假设。
- 这是"迁移只做了一半"的典型：数据面转真实，控制面（health/断言/默认值）未随契约轨切换。

### 4.3 身份键语义多义：登录用户 / 租户 / 业务对象未分层
- `X-User-ID` 在 OpenBase=JWT sub（登录用户），在 DPS=RBAC 平台用户，在 OpenLLM ProfileAdapter 又被 external_user_id 承载并**优先充当 DPS person_id（画像对象）**。画像对象（dps-tenant-001_admin1_001）与登录用户（admin id=1）本是两个实体，同字段导致：读画像 403（对象无 create 权限）、种子 person_id 命名规则与内部 user_id 形态不一致、映射表（org_1↔tenant）双向语义混淆。
- **本质**：缺少"平台身份（user/org/tenant）→ 业务对象（person_id）"的显式映射层与命名约定；external_* 字段在 P0-2/M3 只做透传，没有按消费端建模。

### 4.4 测试与运行同库同进程：状态污染与路径漂移
- OpenBase 全量 pytest 与真实服务共用共享 PG `openbase` schema、共用进程内全局单例（async engine/settings）；OIDC 用例断言前提是"DB 不可达（降级直签）"，与其他需要真实 DB 的用例在同一进程冲突：DB 可达→绑定路径→固定 sub 命中历史行→'3'/'4'；加 env 强制不可达又被已创建的全局 engine 绕过。
- **本质**：测试没有进程/库级隔离设计，断言隐含环境假设（哪条 DB 路径生效取决于进程 env 注入顺序），导致同一用例在不同批次红绿漂移。

### 4.5 平台沙箱写限制 + 外部并发编辑：掩盖故障、阻断闭环
- 沙箱对部分目录只读（DPS data 的 sqlite attach、OpenLLM backend/data、OpenLLM .git、pgAdmin site-packages），制造了"业务 500/提交失败"的表象，根因却与业务代码无关；期间一次按进程名批量清理还误杀全家服务。
- 文档被外部编辑器并发回滚（任务书 v1.1~v1.7 反复跳版）——变更没有单一写者与原子提交护栏。
- **本质**：运行边界（可写/可执行/可提交清单）未显式声明与检查；文档与代码变更管理脆弱。

## 5. 根治方案

### S1 配置单一来源与启动自检（对应 4.1）
1. 各仓维护 `config 契约清单`（真实种子值/端口/URL 以种子脚本为源），`.env.example` 同步真实部署值，禁止魔法默认（旧种子语义）长期驻留：`dps_default_*`/映射/REAL 开关值全部以共享 PG 种子（seed-shared-infra.py）为基准对账，用 `scripts/verify-env.ps1`（新建）在编排 start 时比对并 fail-fast。
2. OpenBase/OpenLLM 编排 Env 作为唯一受管注入源（含 dps 映射、OPENLLM_DPS_REAL、四头 code 兜底、WRITEBACK/SEMANTIC 可写路径），与 `.env` 双写同步改为**受管优先**。
3. 探活与降级：所有上游健康检查按当前契约轨执行（real→真实端点 ping；stub→原语义），并纳入启动自检输出。

### S2 契约双轨显式收口（对应 4.2）
1. stub 端点标注 Deprecated 并在真实模式日志 WARN（禁止静默双轨）；OpenLLM DPSClient/ProfileAdapter 增加"契约轨"字段暴露，供 health/断言/UI 默认值统一读取，杜绝再按旧轨写死。
2. 已修复范式推广：探活分叉（client.ping）、测试缺省断言改字段级默认、UI 动态源替代静态默认项。

### S3 身份三层建模（对应 4.3）
1. 明确三层：**平台登录用户**（OpenBase JWT sub / DPS X-User-ID，RBAC 校验对象）、**组织租户**（tenants.code，Q2/Q3 唯一键）、**业务画像对象**（DPS person_id，形如 `{tenant_code}_{user_ref}_{NN}`）。
2. 约定：`X-User-ID` 恒为平台用户；画像对象由 ProfileAdapter 的显式 person_id 参数/`external` 前缀规约承担，禁止用 external_user_id 一值双义；读链 DPS calculate 的权限动作映射为 read 语义（或按对象绑定校验），写链 PUT 按对象归属。
3. DPS 绑定种子语义固化：`DPS_DEMO_USER_ROLES` 显式收紧为生产基线；P2-2 立项已含该固化（T4）。

### S4 测试与运行彻底隔离（对应 4.4）
1. 测试门禁分批（已落地）：OIDC E2E 独立进程（fixture 强制 DB 不可达），其余主批次独立进程；固化到 `scripts/run_tests.ps1` 与 CI，禁止单进程全量混合。
2. 测试基建：移除对进程内全局单例的隐式依赖（engine/settings 由 fixture 显式重建/复原）；需真实 DB 的用例指向专用测试库（`openbase_test` schema），跑前清库种子，杜绝历史行污染。
3. 断言写"契约意图"而非环境值（如 OIDC 断言降级直签语义=环境无关前提；DB 可用路径另设绑定单测 mock 校验）。

### S5 运行边界显式化与受管化（对应 4.5）
1. 沙箱/运行边界清单：声明可写路径（服务 data 目录、WRITEBACK/SEMANTIC 路径）、可执行范围、git 可提交仓库；服务统一由 `service-orchestrator.ps1` 启停（禁止按进程名批量杀）。
2. 数据落盘统一走共享 PG/Redis（真实面）或显式白名单本地路径；OpenLLM 本地 sqlite（writeback/semantic cache）由受管 env 指向可写路径。
3. 提交护栏：关键仓库提交仅走单一受管通道；文档版本记录随改随提 + 原子整文件重建基线，杜绝并发回滚。

### S6 剩余登记与路线（实施顺序）
| 序 | 事项 | 承载 |
|----|------|------|
| 1 | OpenLLM 探活分叉提交（放行 .git 后） | OpenLLM 仓 |
| 2 | P2-2 Phase1：DPS tenant/permission fail-closed 化 + 配置开关 | P2-2 立项方案 |
| 3 | P2-2 Phase2：OpenMemory sessions 归属与校验 | P2-2 立项方案 |
| 4 | 配置契约清单 + verify-env 自检脚本 | 本方案 S1 |
| 5 | 测试基建（openbase_test 库 + run_tests.ps1 分批固化） | 本方案 S4 |
| 6 | stub 废弃标注与契约轨字段（S2） | 与 P2-1 统一身份协议头联动 |
| 7 | P1-2/P1-3 code 化、P2-1 统一身份头（评审待立项） | 治理评审 |

## 6. 账本：已闭环与剩余

**已闭环（本轮战役）**：治理 P0 批次、真实契约 Phase A~D、冒烟 S0~S6、P9 全部实证（含双租户/重启存活）、UI-E2E P1/P2 项、存量测试对齐 T1~T4、P2-2 立项。主要提交：`0499838/aae1de7/1074751/22d369f/0ee504b/08f60b5/0f808e9/15b520a/3763b66/def7ed8/8bb6dc7/f658fa1/23c0b79/f7dd3f0`（OpenBase）；DPS/OpenRAG/OpenMemory 侧 P0/Phase 提交见各自仓；OpenLLM 探活分叉代码就绪待提交。

**剩余**：
- OpenLLM 仓 4 文件提交（沙箱放行后）。
- P2-2 实施（fail-closed + sessions 归属 + 绑定固化）——已立项未实施。
- P1-2/P1-3（code 化）、P2-1（统一身份头）、治理 fail-open 复核（P0-3 遗留 PROXY_SYSTEMS dps 8030 通用通道）。
- 配置契约清单与 verify-env、openbase_test 测试库基建（S1/S4）。
- 画像对话内注入的"模型层质量验证"（llama3.2:1b 能力边界，不阻塞链路）。

## 7. 结论

联调绝大多数问题不是"代码不会写"，而是**默认值/契约轨/身份语义/隔离边界四类系统性假设不一致**造成的连锁表象。根治方向已明确并部分落地（分批测试、契约探活、映射部署值、fail-closed 立项）。建议按 §5 顺序以"单一配置源 + 真实面自检 + 身份分层 + 隔离测试 + 显式运行边界"五条主线持续收口，使后续联调以"自检即真相、失败即红线"方式收敛，避免同类问题在新系统接入时复发。

## 8. 问题-方案-批次承接总表（v1.1.0）

> 本文档为 L0 治理根；批次（R1-R4）定义与子系统升级清单见《OpenBase-多系统对接-文档体系与升级路线规划 v1.0.0》。**身份域（根因 4.3/S3 及 U1-U5）承接于身份域文档族**（统一总体方案 v1.0.0 → 身份最小集 v1.3.0 → P2-2 立项方案），不在此重复；本表安排"其他问题"。

### 8.1 根因 × 方案 × 批次矩阵（非身份域）

| 根因 | 方案 | 承接（升级项/文档） | 批次 | 状态 |
|------|------|---------------------|------|------|
| 4.1 配置即代码缺位 | S1 配置单一来源 + 启动自检 | OB-9 verify-env 自检 + config 契约清单（种子为源）+ .env.example 同步真实部署值 + 受管 Env 优先 | R3（探活契约轨部分随 R2 前置） | 🔄 受管 Env 已实施；自检/清单待建 |
| 4.2 契约双轨未收敛 | S2 显式收口 | LL-2 REAL 全启用 + stub Deprecated 标注 + 契约轨字段统一供 health/断言/UI 读取；探活分叉（已就绪） | R2 | 🔄 探活分叉待提交（立即项） |
| 4.3 身份键语义多义 | S3 三层建模 | 身份域文档族（总体方案/最小集/立项），R1/R2 承接 | R1/R2 | ✅ 设计定案（最小集 v1.3.0） |
| 4.4 测试同库同进程 | S4 分批/独立库 | 分批门禁（已落地 T2）；openbase_test 专用库 + run_tests.ps1 固化（待建） | R3 | 🔄 分批已落地，基建待建 |
| 4.5 沙箱写限制与外部并发 | S5 运行边界显式化 | 编排受管（已部分）+ 沙箱可写/可提交清单 + 提交护栏 + "误杀服务"固化（编排唯一入口） | R3 | 🔄 |

### 8.2 剩余登记逐项安排（含 §5 S6 与 §6 剩余）

| 序 | 事项 | 承载 | 批次/时点 |
|----|------|------|----------|
| 1 | OpenLLM 探活分叉 4 文件提交（沙箱外 git add/commit，命令已备） | OpenLLM 仓 | 立即（R2 前置） |
| 2 | P2-2 Phase1：DPS tenant/permission fail-closed 化 + 绑定固化 | P2-2 立项方案 | R1 |
| 3 | P2-2 Phase2：OpenMemory sessions 归属 + 行级归属必带 + 复合唯一 | P2-2 立项方案 | R1 |
| 4 | 配置契约清单 + verify-env 自检脚本（S1） | 本方案 S1 | R3 |
| 5 | 测试基建：openbase_test 库 + run_tests.ps1 分批固化（S4） | 本方案 S4 | R3 |
| 6 | stub 废弃标注与契约轨字段（S2）；REAL_* 兜底限期移除（R-L1-1） | 与 P2-1 联动 | R2 |
| 7 | P1-2/P1-3 code 化、P2-1 统一身份头（评审待立项） | 治理评审 → OB-8 | R1（P2-1）/R2（code 化） |
| 8 | 画像对话内注入"模型层质量验证"（llama3.2:1b 边界，不阻塞链路） | 任务书 P9 | R2 发布批次 |
| 9 | L7 误杀服务收口：受管编排为唯一启停入口并固化文档 | service-orchestrator.ps1 | R3 |
| 10 | UI-E2E P3 体验项（模块导航壳等） | 前端 | R4 |

### 8.3 闭环项基线引用（不再重复安排，回归由既有门禁覆盖）

L1-L7 中 ✅ 项（端口拓扑、P0 门禁、映射双落点 def7ed8、路由修复 8bb6dc7、T1-T4 对齐、沙箱 pyc 约定等）构成当前基线；回归由《存量测试对齐任务清单 v1.2.0》与《真实联调冒烟清单 v1.2.0》持续覆盖；本表不再列实施动作。

### 8.4 新增待办（本表确认后并入 R3）

- config 契约清单文档（键名/真实种子值/端口/URL 单一来源表）；
- verify-env.ps1（编排 start 时比对并 fail-fast，覆盖配置/映射/契约轨）；
- openbase_test 专用测试库与 run_tests.ps1 分批固化；
- 沙箱可写/可提交路径清单 + 提交护栏（单一受管提交通道）；
- 受管编排唯一入口声明（禁按进程名批量杀）。
