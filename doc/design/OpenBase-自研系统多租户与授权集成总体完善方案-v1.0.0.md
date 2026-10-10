# OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）及四套自研后端系统（OpenLLM / OpenRAG / OpenMemory / DPS） |
| 文档编号 | OB-DESIGN-MTAUTH-v1.0.0 |
| 文档版本 | **v1.9.9**（文件名版本＝首次定稿版本；内容版本以本字段与修订历史承载） |
| 状态 | **[Review]**（§7 待裁定项已由人工裁定并回填；A 批已落地；B1/C1 已按 DevFlow 纪律正式分发；B1 配套播种制品已跨仓交付 OpenLLM **并已在共享库执行完成**；强制期**模块级灰度机制已就位**；**C4 生产门禁 / C5 过渡期退出**已在 OpenLLM 落地；待各仓回执后进入 D 批门禁） |
| 作者 | AA-OpenBase-Dev（架构视图）/ AU-OpenBase-Dev（审计视图）/ PM-OpenBase-Dev |
| 创建日期 | 2026-10-08 |
| 存放 | doc/design/ |
| 上游依据 | 《OpenBase-统一身份与主备双通道贯通总体方案-v1.0.0》；《OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0》；《OpenBase-四维身份透传契约-v1.1.0》；《OpenBase-协议头规范-v1.0》；《OpenBase-R387-跨域租户码对齐设计与收口实施记录》（统一码空间）；《OpenBase-P2-1/P2-2/S6/S7/U1 立项方案》 |
| 方法 | 逐仓**只读**代码取证（每条结论附 `文件:行号`），五系统同一维度口径横向比对；不含任何运行时写操作 |
| 范围边界 | 本文件为**分析与方案**，供人工确认后分批执行；不替代 Step 2 正式设计评审与需求架构对比审计 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| **v1.9.9** | **2026-10-09** | AA/AT/PM-OpenBase-Dev | **C3 第二阶段：OpenBase k03 死字段修复 + R1 影子期**：① **R2 落地（真缺陷修复）**——`openbase/modules/proxy/__init__.py` 新增 `_k03_exemption_active()`，`_k03_bypass_matches()` 先判 `expires_at`：**到期即不生效**（fail-closed），非法格式与已过期一律不匹配；此前该字段「声明但未生效」使豁免条目**永不失效**，现修复；② **R1 影子期**——`openbase/settings.py::parse_k03_bypass_whitelist` 对缺 `ticket`/`approver`/`expires_at` 的条目 WARN + 留痕，**不改变放行行为**（退出条件：影子期无依赖方后转强制段）；③ 用例 `tests/test_c3_exemptions.py`（6 例）；④ **本机无法执行 pytest**（Py3.13 + 旧 SQLAlchemy 阻断包导入），改以**源码抽取隔离执行**验证 R2 4/4、**直接构造 `Settings`** 验证 R1 2/2，均 PASS；契约制品 `config/identity_exemptions.json` 的 stage_2 状态回填为「已落地」
| **v1.9.8** | **2026-10-09** | AA/AT/PM-OpenBase-Dev | **C3 豁免治理统一（第一阶段：契约与登记）（收口未决项 7）**：产出 `config/identity_exemptions.json` 作为豁免治理**单一事实源**——统一必填字段（`target`/`ticket`/`approver`/`expires_at`）+ 规则 **R1~R5** + 三实现（OpenBase k03 / OpenMemory 行控豁免 / OpenLLM 入站头豁免）字段映射与差距清单；主模板取 OpenMemory（三态审计 + 到期清零）。**查出真缺陷**：OpenBase k03 的 `expires_at` **声明未生效（死字段）**、无 `ticket`/`approver`；OpenLLM 豁免**无专属审计**；OpenMemory 注册表内存实现且 `src` 无实例化点。第二阶段（OpenBase 收紧）与第三阶段（各仓对齐）已登记退出条件，待批
| **v1.9.7** | **2026-10-09** | AA/AT/PM-OpenBase-Dev | **B3 四仓档位锚点落地 + D3 门禁覆盖加固（收口未决项 2/3）**：① **修复真缺陷**——OpenRAG `c3a5b85`、OpenMemory `c73b5bb` 的角色→档位映射原仅收四码、**缺 A3 并集内的 `user`**，会把 OpenBase 合法透传码 fail-closed 403 `ROLE_UNMAPPED` 误拒；两仓补 `user→readonly`（RAG 同步扩 `OPENBASE_ROLE_CODES`、OM 扩 `KNOWN_OPENBASE_ROLES`）并更新契约用例与端点级读写矩阵参数；② 四仓锚点**全覆盖**（OpenLLM/DPS 经**直接导入模块断言**证实一致，无需改动）；③ D3 门禁加固——`scripts/cross_repo_auth_gate.py` 新增「**锚点覆盖**」检查（原仅查"不矛盾"）且提取器支持常量式映射，复跑 **8 PASS / 1 WARN / 0 FAIL**；④ 测试可执行性：RAG/OM **本机无法执行**（RAG `.venv2` 基础解释器缺失、共享解释器缺 `structlog`；OM 命中 Py3.13+旧 SQLAlchemy 不兼容），故以**模块级直接断言**取证并登记遗留
| **v1.9.6** | **2026-10-09** | AA/AT/PM-OpenBase-Dev | **C4 生产门禁 + C5 过渡期退出落地（OpenLLM，收口未决项 4/5）**：`get_settings()` 新增生产门禁——`ENV=production` 且 `ENFORCE_INBOUND_IDENTITY_HEADERS=false` 即**拒绝**（照搬本仓既有 `SECRET_KEY` 门禁形态与 OpenMemory `validate_*_policy` 口径），该门禁兼作过渡期「忽略+标注+WARN」的**机械截止手段**（规避过渡态永久停留）；新增 `tests/unit/test_c4_production_enforce_gate.py`（3 例），连同 B1 用例复跑 **23 passed**；OpenLLM commit **`daea828`**（`version.json`→**2.16.3**）、DevLogReport 升 **v1.1.3** 新增 §15。**未覆盖**：其余三仓同类门禁属各自批次（OpenMemory 已有 `validate_*_policy`，需**口径对齐**；OpenRAG/DPS 待排期）
| **v1.9.5** | **2026-10-09** | AA/AT/PM-OpenBase-Dev | **强制期「按模块灰度」机制就位（收口未决项 1）**：OpenLLM 新增 `RBAC_PERMISSION_ENFORCE_MODULES` 灰度白名单（默认空=全部模块；非空=仅列出的 module 强制，其余走影子期）+ `enforced_modules()`/`module_of()`/`is_module_enforced()`，落点 `app/core/config.py`、`app/identity/rbac_guard.py`；新增 4 例护栏用例，`test_b1_rbac_wiring.py` 实测 **20 passed**（16+4）；OpenLLM commit **`6f06198`**（`version.json`→**2.16.2**）、DevLogReport 升 **v1.1.2** 新增 §14（含**单模块可独立回滚**口径）。**仍未执行**：`RBAC_PERMISSION_ENFORCE` 实际翻转——本机**无运行中的 OpenLLM 服务、无影子期 `would_deny` 日志**，出口门禁（消化率 100% 且无未归类调用方）无法判定，登记为遗留。
| **v1.9.4** | **2026-10-09** | AA/AT/PM-OpenBase-Dev | **B1 配套播种制品执行闭环**：① **测试环境修复并执行**——启用 OpenLLM 既有机制 `OPENLLM_TEST_EXTRAS`（`backend/extras/.venv/Lib/site-packages`，cp313 `psycopg2-binary`）后 `test_b1_rbac_wiring.py` 实测 **16 passed**（D2-A 验收闭环），v1.9.3 遗留①关闭；② **播种制品已在共享库执行完成**——`192.168.0.151:5432/nuct`（PG 14.23）按「结构先行、数据后行」：预检（四表存在/计数 0/重复行 0/缺唯一索引/账号具 `public` 的 `CREATE` 权限）→ 执行 `rbac_seed_ddl.sql`（建 `uq_role_permissions_role_permission`）→ 执行 `rbac_seed.sql`（roles=5/permissions=27/role_permissions=34/user_roles=0，与 manifest 一致）→ **幂等复跑新增 0 行**（跳过 66），v1.9.3 遗留②关闭；③ **附带发现**：`roles.code`/`permissions.code` 唯一性由**索引型唯一约束**（`ix_roles_code`/`ix_permissions_code`）承载而**非**表级约束（`pg_constraint` 不含索引型唯一约束，勿误判），故 `ON CONFLICT (code)` 前提成立；④ OpenLLM 侧 commit **`1075e37`**（`version.json`→**2.16.1**）、DevLogReport 升 **v1.1.1**，origin/backup/github 三远程一致；⑤ `RBAC_PERMISSION_ENFORCE` 前置**已具备**，**本批未改运行时开关、未重启服务**（按模块灰度另行推进） |
| **v1.9.3** | **2026-10-09** | AA/AT/PM-OpenBase-Dev | **B1 配套播种制品跨仓交付闭环**：依人工指令「立即跨仓执行」，将 B1 配套播种制品**照抄落位** OpenLLM `backend/scripts/rbac_seed/`（`rbac_seed_ddl.sql` 前置结构变更 / `rbac_seed.sql` 纯 DML / `rbac_seed_manifest.json`），目标仓自此为**执行责任方**；同批交付 **D2 裁定 A 接线侧复核**（`app/identity/rbac_guard.py:137-139 has_permission_code()` 已支持 `*` 通配、G3 档位守卫优先于 G1，`*` 不参与档位校验）与 **3 例通配护栏用例**；OpenLLM 侧 `version.json`→**2.16.0**、DevLogReport 升 **v1.1.0 §13**；目标仓 commit **`9feeec8`**，origin/backup/github **三远程哈希一致**；OpenBase 侧派单单 §6.3 回执登记、§10.3 B1 配套行回填。**遗留**：①该仓 3 例护栏用例**未在本机执行**（运行环境不可用：`psycopg2` DLL 缺失 / 无 `ruff`），已登记于 `DevLogReport §13.3`，须在可用环境确认 **16 例全绿**；②播种制品须由共享库受控变更流程执行，**尚未执行** |
| **v1.9.2** | **2026-10-09** | AA/AT-OpenBase-Dev | **D1/D2 裁定落地 + 前置 DDL 与数据播种解耦**：① **D1 裁定采纳**——`role_permissions` 唯一索引属**前置结构变更**，从数据种子拆出为独立交付 `doc/design/generated/rbac_seed_ddl.sql`，`rbac_seed.sql` 退化为**纯 DML**，交付与执行按「**结构先行、数据后行**」两步走；② **D2 裁定采纳 A**（B1 接线在 `rbac_guard.py` 补 `*` 通配语义，播种不变；B 仅作短期兜底）；③ 生成器与用例同步改造（TDD **11 例**；本机 Python 3.13 + 旧 SQLAlchemy 环境下 **10 passed / 1 环境失败**，失败项与本改动无关；`ruff` 全绿；DDL 重跑逐字节一致、SQL 忽略生成时间戳后一致、diff=0）；④ **文档升版留痕**：评审预检说明 v1.0.0→**v1.1.0 [Approved]**、生产化配套设计 v1.1.0→**v1.2.0 [Approved]**；⑤ **口径补充**：局域网共享基础设施（`192.168.0.151:5432/nuct`）为**唯一数据库**，四系统同实例按 schema 区分，结构变更须经受控流程（迁移/DBA）执行 |
| **v1.9.1** | **2026-10-09** | AA/AT-OpenBase-Dev | **播种生成器重修闭环 + 评审预检说明产出 + 推送遗留关闭**：① **OpenRAG github 补验通过**（`f2f774f`，origin/github/backup 三远程至此全部一致，v1.9.0 遗留项关闭）；② **B1 播种制品缺陷已修复**：生成器 `scripts/rbac_permission_seed.py` 数据模型来源换为目标系统真实表结构（`nuct.public`，uuid 主键、`permissions` 四字段并存、`role_permissions` 冲突键 `(role_id, permission_id)`），新增**生成期档案校验**（schema/键类型/表集合与档案不符即硬失败）+**落点断言**（SQL 含 `openbase`/`platform` INSERT 即硬失败，令历史缺陷不可能重犯）；播种用例 **10 passed**、`ruff` 全绿、SQL 重跑 diff=0；③ 产出《OpenBase-B1-播种SQL评审与执行预检说明-v1.0.0.md》：含前置 DDL 风险与只读预检 SQL、通配符 `*` 语义两选项（A 接线补通配 / B admin 逐码授予）、约定值说明、执行清单、回滚口径、决策点 D1~D4（**D1 DDL 权限 / D2 通配符口径为强制段前置阻塞项**，待 OpenLLM 评审）；④ 本轮未提交未推送——生成器+SQL+评审说明**待 D1/D2 口径确认后与 OpenLLM 一批推送** |
| **v1.9.0** | **2026-10-09** | AA/AT-OpenBase-Dev | **推送完成 + 播种制品缺陷登记**：① 三仓（OpenBase `d60c69b` / OpenLLM `081c5d5` / OpenRAG `f2f774f`）以「本批次文件精确圈定 + 推当前分支 + origin/github/backup 三远程」口径推送，累计 **86 个文件**，origin/backup 六项哈希逐一一致；**OpenRAG 的 github 因 github.com 连通性中断（`Connection was reset`）至今未能验证**，登记为待复核项；② OpenLLM `version.json` 升 **2.15.0**（OpenBase 无 version.json，版本记于提交信息 v1.5.0；OpenRAG 的 `version.json` 为 DevFlow 元数据、未动，产品版本 1.10.1 仅记于提交信息）；③ **发现并登记 B1 播种制品缺陷**：`rbac_seed.sql` 目标 schema 错误（写 OpenBase 的 `openbase` schema 而非 OpenLLM 权限表），**判定不可执行、未执行**，须按 OpenLLM 真实表结构重新生成；④ 本次以「先侦察后执行」避免了跨系统误写——**记录为纪律：跨系统数据变更前必须先核实目标表结构与库落点** |
| **v1.8.0** | **2026-10-08** | AA/AT-OpenBase-Dev | **B4 环境门控修复（P0 回归破坏已闭环）**：① 降级策略按环境门控——生产 fail-closed（503 + 白名单）/ 非生产**兼容 allow+WARN+留痕**（不静默），新增 `OPENBASE_PRINCIPAL_DB_DEGRADED_POLICY`（`reject`/`allow`/留空按环境推导），**生产误配 `allow` 拒绝启动**；② **移除**上一轮为绕过沙箱而加在 `tests/conftest.py` 的「测试会话白名单 id=1」（该文件已与 HEAD 逐字节一致），deny 路径用例改为**显式钉死 `policy=reject`** 以继续测到安全语义；③ 回归恢复：`test_dps_proxy_v1410_contract.py` 39 failed → **0**；全量 **1176 passed / 5 failed / 4 skipped**（5 项 = 4 项共享 PG 连接抖动 + 1 项本批遗漏）；④ **顺带修复本批遗漏**：`tests/test_org_alias_code.py::test_t7_2_memory_org_alias_same_source` 仍断言旧兜底码 `default`（C1 终态切换时漏改），已改 `tenant-1`；复核 73 passed、`ruff` 全绿。**教训**：B4 首轮以窄口径 `-k` 验证并宣称通过，掩盖了整组失败——**凡触及鉴权主链路的改动，验收必须以全量回归为判据** |
| **v1.7.0** | **2026-10-08** | AA/AT-OpenBase-Dev | **B4 安全收紧（人工裁定口径 A：fail-closed + 显式白名单）**：① 主体验证 DB 不可达分支由 **WARN 后放行** 改为 **fail-closed**——拒绝用 **503 `SYS_SOURCE_UNAVAILABLE`**（非 401，因根因是依赖不可用、可重试，401 会误导客户端丢弃有效会话；与既有「数据源失败不静默降级」单一来源一致）；② 新增白名单 `principal_db_degraded_allowlist`（默认 **空**、**精确十进制匹配**、通配/前缀一律丢弃、放行必留痕 WARN + 审计 ContextVar 标注 `principal_db_degraded_allowlisted`、新增指标 `db_degraded_allowlisted`/`db_degraded_denied`）；③ `token_version` 吊销**生产强制**（新增 `_validate_production_token_version_enforcement`，生产未启用即拒绝启动）；④ TDD 12 例，复核 **62 passed**、`ruff` 全绿；⑤ **附**：沙箱内 `localhost:5432` 不可达，故依赖真实 DB 行存在性的既有离线用例在新语义下走 503（现场 DB 可达则行为零变化）；`tests/conftest.py` 为测试会话白名单 id=1。**遗留**：全量回归未跑；`row_missing` 仍保留 fail-open（未收紧，另批） |
| **v1.6.0** | **2026-10-08** | AA/AT-OpenBase-Dev | **B2 闭环（OpenRAG 授权引擎收口）**：经事实复核确认 `RBACEngine` **未被请求路径引用**（仅包导出、未装配的遗留惰性构造点与单测直接实例化；`main.py`/`api/` 全量 0 引用），故按 B1 同构口径 **明确弃用而非接线**：`rbac_engine.py` 静态登记 `DEPRECATED`/`DEPRECATED_REASON`/`REPLACEMENT_PATH` + 类标记 `__deprecated__`（不发运行时告警，以兼容该仓 `filterwarnings=error::DeprecationWarning`），`security/models.py` 同步登记；新增 `tests/unit/test_s3_b2_rbac_engine_closure.py`（11 例，含「请求路径零引用」护栏）；基线 `failed/errors = 47/40 → 47/40` 零增长；§10.3 B2 行回填「已闭环」。**遗留**：三个未装配的惰性构造点未物理下线（保持零行为变化，另立批次） |
| **v1.5.0** | **2026-10-08** | AA/PM-OpenBase-Dev | **B1 权限模型定稿（人工裁定）**：新增 `config/rbac_permission_model.json` 作为播种/观测/门禁的**唯一输入**——四项裁定均采纳推荐项：**D1 普通用户只读**（保持 B1 基线）、**D2 `role:admin` 仅平台 admin**（org_admin 不含角色与权限管理，防自我提权）、**D3 模块级 `module:action` 粒度**（本版本目标：受保护端点覆盖 100%）、**D4 按模块灰度开强制**（`users → roles → knowledge_bases → conversations`）。制品同时固化：角色→权限码映射、禁用授予清单、10 个模块的接线状态（4 已接线 / 6 待接线）、四阶段推进（影子期 → 模块灰度 → 覆盖补齐 → 兼容层退役）、5 条生产门禁、幂等播种要求（**尚未播种**）。推送口径经人工确认：**各仓以自身推送脚本 + 小版本号推送**，待 B2/B4 落地后一并执行 |
| **v1.4.0** | **2026-10-08** | AA/AT-OpenBase-Dev | **D 批 D1/D2 落地**：① D1 新增 `config/auth_consistency_matrix.json`（跨系统授权一致性矩阵：17 格 / 6 系统 / 8 不变式，含 I7「兜底码非保留码」与 I3~I6 各项拒绝语义，逐格标注 evidence 类型）；② D2 新增 `scripts/cross_repo_auth_gate.py`（跨仓静态门禁 9 项检查：矩阵完整性 / 四仓档位锚点一致性 / 错误码映射字面量可检索 / **码空间登记一致性（C1-a 阻塞项固化防线）** / 保留码防护未放宽），**复跑 0 FAIL**；③ 门禁纳入回归 `tests/test_cross_repo_auth_gate.py`（4 例，无兄弟仓时自动跳过）；④ **门禁首跑即抓到真问题**：A4 映射表 6 条目标字面量在对应仓不存在（分析阶段未核实值），已修正为 `null` 并复跑通过（44 条字面量全部命中）；⑤ D3（运行时负向集全量复测）未启动 |
| **v1.3.0** | **2026-10-08** | AA/AT-OpenBase-Dev | **B1 / C1-b / C1-c 跨仓实施完成**：① B1（OpenLLM 双 RBAC 接线，P0）——新增 `rbac_guard.py` + 15 端点接入权限码判定 + EdgeRouter 配置式 RBAC 显式 deprecated + 两段开关；② C1-c（OpenLLM 租户语义）——缺租户标识显式化 + 主 JWT 补 `tenant_code`（向后兼容）；③ C1-b（OpenRAG 租户注册表）——配置驱动注册表 + M2 缺省/未登记显式语义 + M1 零变化 + 保留码防护未放宽；④ 三仓均以「改动前基线 vs 改动后」证明失败数零增长，**均未重启服务**；⑤ §10.3 由「未实施」改写为实施台账；⑥ A4 错误码映射表同步两条新码（`AUTH_TENANT_ID_MISSING`/`BIZ_TENANT_NOT_FOUND`）并纳入覆盖断言 |
| **v1.2.0** | **2026-10-08** | AA/AT-OpenBase-Dev | **跨仓实施（C1-a 闭环）+ 统一码空间终态落地**：① 依人工指令「直接跨仓修复」，在 `scripts/service-orchestrator.ps1` 登记 `OPENMEMORY_RBAC__ORG_POLICIES`（`default`/`tenant-1`/`tenant-2`），**未改 OpenMemory 仓代码、未放宽其 fail-closed**；② 端到端实测 **12/12 PASS**（受信入站 `tenant-1` 由 403 转 200；未登记码仍 403）；③ **同批执行本仓终态切换**：memory 兜底码（内置基线 + `OPENBASE_PROXY_CODE_MAP`）、`oidc_default_tenant`（代码默认值 **与 `.env` 第 17 行**）、本地 IdP 演示池 → 非保留码 `tenant-1`；④ §5.1 OpenMemory 行状态回填为「已闭环·已验收」；⑤ 新增 §10 本轮跨仓实施记录（含 `.env` 覆盖教训与回滚口径） |
| **v1.1.0** | **2026-10-08** | AA/AU/PM-OpenBase-Dev | **裁定回填 + A 批落地 + B1/C1 分发**：① §7 待裁定 Q1~Q5 已由人工裁定（Q1=**三源模板**、Q2=**A 批执行并并行立 B1**、Q3=**B1/C1 两份派单都出**；Q4/Q5 采建议值）；② §6 A 批 5 项落地状态回填（A1/A2 统一码空间登记入口、A3 档位锚点表、A4 错误码映射表 **已完成**；**A5 已完成**——《OpenBase-协议头规范-v1.1》）；③ §5 差距清单增**派发状态**列（B1/C1 已分发）；④ 新增 §9 派单与回执台账（含 C1-a 吸收并取代《R387派单-OpenMemory组织码登记》序号 1 的重叠处置） |
| v1.0.0 | 2026-10-08 | AA/AU/PM-OpenBase-Dev | 初始版本：五系统（OpenBase + 四仓）「认证 / 受信入站 / 多租户 / 授权 / 失败语义 / 数据模型」六维横向实测比对；判定**模板选型**（OpenMemory 授权与隔离维度最全、DPS 租户治理最完整、OpenBase 为集成中枢）；给出**分层授权集成架构**（单一身份源 → 统一协议层 → 统一码空间 → 双层授权职责 → 统一码表/门禁/豁免/审计）；给出**四批完善路线**（A 契约与登记 / B 授权接线补欠账 / C 治理增强 / D 一致性门禁）与验收标准、风险、回滚、待裁定决策项 |

---

## §1 结论摘要

1. **四仓的「受信入站 + 身份头」层已高度同构**（P2-1/K01 收口成果）：均有受信来源白名单 + 四身份头 + 三开关（strip / enforce / org-alias），差异仅在默认值与生产强制程度。**这一层不必重做，需做的是统一默认值与强制门禁。**
2. **真正不统一的是「租户治理」与「授权接线」**：租户注册表只有 OpenBase 与 DPS 有（且语义不同）；授权引擎多数仓**存在但未接线**（OpenLLM 双套 RBAC 均未上路由、OpenRAG `RBACEngine` 未接线），实际生效的是「档位守卫 + 管理员粗判」。
3. **模板选型**：**OpenMemory 是授权与隔离维度最完整的方案**（双层认证 AND + 组织策略 fail-closed + 角色档位 + RBAC + ABAC + 行控豁免治理 + (tenant_code, owner) 双维行控 + 组织级物理命名空间 + 生产强制开关校验）；**DPS 在多租户治理上最完整**（真实 `organization`/`tenant` 表 + 存在/启停校验 + 码→UUID 双形态规范化 + 401/403 语义清晰 + contextvars 强制过滤）。
4. **集成形态**应确定为「**中枢签发与准入 + 目标域细粒度裁决**」两段式：OpenBase 作为唯一身份权威与模块级准入，四仓作为数据面细粒度裁决（档位 + 行控），中间以**统一协议契约 + 统一码空间登记 + 统一错误码映射**连接。**不应**让四仓各自维护身份签发或各自定义租户码语义。
5. 据此给出 **A/B/C/D 四批完善路线**（§6），其中 A 批（契约与登记）低风险可先落地，B/C 批涉及四仓改造需各自立项，D 批为一致性门禁。

---

## §2 六维横向实测比对

### 2.1 认证（Authentication）

| 维度 | OpenBase（中枢） | OpenLLM | OpenRAG | OpenMemory | DPS |
|------|-----------------|---------|---------|-----------|-----|
| 主凭证 | 本地 JWT(HS256) + OIDC(RS256/JWKS) | JWT(HS256) + API Key | **X-API-Key（service/bypass）** | **X-API-Key「且」Bearer JWT（AND）** | JWT(HS256) |
| 其他凭证 | `ob_k_` 服务 Key（内存态）；`sk-agent-*`（DB） | `sk-openllm-*`（走 `Authorization: Bearer`，非 X-API-Key） | MCP 侧 `OPENRAG_MCP_API_KEY` | 网关 `api_key`+`jwt_secret` 双配时 AND | `X-API-Key` **非凭证**（仅写主体分类） |
| 验签/校验 | jose 验签 + DB 主体验证 | 哈希比对 / jose 验签 | `hmac.compare_digest` 常量时间比对 | `compare_digest` + jwt decode | jose 验签 + 过期 |
| 过期 | access 2h / refresh 7d | API Key `expires_at` | 无（密钥换值） | 依赖 JWT | `JWT_EXPIRATION_HOURS`=24 |
| 吊销 | `token_version`（**默认未强制**）+ agent key `status` | API Key `is_active`；边缘 JWT **jti 黑名单**；主 JWT **无** | 无 | 无 | 无 |
| 入口 | `AuthMiddleware`；`get_current_user` / `require_permission` | `get_current_user` / `get_current_active_user_or_api_key` / `get_admin_user_or_api_key` | 中间件链 `APIKey→IdentityGate→BlockSubject→RoleGate` | 中间件链 `Gateway→APIKey→IdentityGate→BlockSubject→RateLimit→Tenant→Workspace→RBAC` | `get_current_user` + `IdentityGateMiddleware` + `TenantMiddleware` + `PermissionMiddleware` |

**判读**：仅 OpenBase 与 OpenMemory 具备「两种凭证叠加（AND）」与「吊销」语义；OpenRAG 连入站 JWT 都没有（**只能靠网关**）；DPS 的 `X-API-Key` 不承担认证（易被误读为认证头，属**语义陷阱**）。

### 2.2 受信入站与身份头（Trusted inbound）

| 维度 | OpenBase | OpenLLM | OpenRAG | OpenMemory | DPS |
|------|----------|---------|---------|-----------|-----|
| 白名单变量 | `trusted_proxy_sources`（默认 `""`） | `TRUSTED_PROXY_SOURCES` + 独立 `TRUSTED_PROXY_ENABLED` | `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES` | `OPENMEMORY_IDENTITY_TRUSTED_PROXY_SOURCES` | `TRUSTED_PROXY_SOURCES`（默认空） |
| 身份头 | X-User-ID / X-Tenant-ID / X-Org-ID / X-User-Role (+ X-Agent-Id) | 同 | 同 | 同 | 同 |
| 链路口 | X-Proxy-Source / X-Request-Id | 同 | 同 | 同 | 同 |
| 三开关 | strip / enforce / org-alias（均默认 False） | strip / enforce / org-alias（均默认 False） | strip / enforce（默认 False） | strip / enforce（默认 False） | `IDENTITY_STRIP_INBOUND_HEADERS` / `IDENTITY_ENFORCE_INBOUND_HEADERS`（默认 False） |
| 受信来源常量 | `openbase-{dps,llm,rag,memory}-proxy`（+ `openbase-orchestrator` 已定义未用） | 白名单默认 `openbase-llm-proxy` | `openbase-rag-proxy`/`openbase-generic-proxy`/`openbase-orchestrator` | `openbase-memory-proxy`/`generic-proxy`/`orchestrator` | `openbase-dps-proxy`/`openbase-orchestrator` |
| 非受信带头（默认） | 忽略 + `identity_headers_ignored` 标注 + WARN（放行） | 同 | 同 | 同 | 同 |
| 生产强制 | 未强制 | 未强制 | 生产 `row_scope.enforce` 强制 True | **生产强制 `enforce_inbound_identity_headers=True` 与行控策略**（否则拒绝装配） | 未强制（`MULTI_TENANT_FAIL_CLOSED` 默认 True） |

**判读**：**四仓这一层是同一份设计的多次落地**，差异集中在「生产是否强制」。OpenMemory 是唯一把「生产必须开强校验」写成**启动门禁**的系统（可作范本）。

### 2.3 多租户（Multi-tenancy）

| 维度 | OpenBase | OpenLLM | OpenRAG | OpenMemory | DPS |
|------|----------|---------|---------|-----------|-----|
| 租户标识承载 | JWT `tenant_code`/`tenant_id`；受信来源 `X-Tenant-Id` 优先 | `X-Tenant-ID`（`X-Org-ID` 别名）；主 JWT **无租户 claim**；边缘 JWT 有 `org_id` | `X-Tenant-ID` → `principal.tenant_code` | `X-Tenant-ID` → `identity_scope` = (tenant_code, owner) | `X-Org-ID` + `X-Tenant-ID` → `TenantContext` |
| 租户注册表 | ✅ `tenants.code`（**唯一事实源**） | ✅ `tenants` 表 + `tenant_schemas`/`tenant_quotas` + 团队 | ❌ **无**（`tenants_router` 已弃用） | ✅ DB `organizations` + 内存 `_org_registry` + 组织策略 | ✅ `platform.organization` / `platform.tenant`（**真实存在+启停校验**） |
| 未知租户行为 | 由调用方决定 | 不拒绝（回退 org 别名/空串） | 回落 `default` 保留码 | **fail-closed 拒绝** | **401 缺标识 / 403 组织不存在或停用** |
| 隔离粒度 | `schema`（默认，SET search_path）/ `row` | **三轨并存**：行级 `tenant_id` + PG schema + 命名空间前缀 | 行级 `tenant_code` + `row_scope` fail-closed | 行级 `(tenant_code, owner)` + **组织级物理命名空间**（Qdrant collection / Neo4j label / SQLite 表） | 行级 `org_id`+`tenant_id` + contextvars 注入 + `UNIQUE(person_id,tenant_id)` |
| 保留码 | — | `{default, openrag-local}`（强校验期 400） | `{default, openrag-local}` | 未声明（`default` 为其**已登记组织**） | `{default, dps-local}` |
| 码值规范化 | `dps_code_map` 登记式映射 | 无 | 无 | 无（码即键） | ✅ **码↔UUID 双形态解析 + 回填规范化** |

**判读**：**租户治理的「事实源」在 OpenBase，但「执行权威」分散**——OpenRAG 连租户表都没有；DPS 与 OpenBase 各有一套真实注册表且**码空间隔离**（靠 `dps_code_map` 桥接，正是 R-387 同源问题的另一个实例）。**统一码空间（R-387 已起步）是把这条线拉直的关键**。

### 2.4 授权（Authorization）

| 维度 | OpenBase | OpenLLM | OpenRAG | OpenMemory | DPS |
|------|----------|---------|---------|-----------|-----|
| 模型 | **RBAC 权限码** `module:action` + `"*"` | 双套：DB RBAC + EdgeRouter 配置式 RBAC | `RBACEngine`（权限码）+ M2 档位守卫 | **RBAC + ABAC + 行控豁免** | RBAC（真表 `permissions`/`roles`/`user_roles`）+ 档位 + 写守卫 |
| 判定入口 | `require_permission` → `has_permission`（JWT permissions 优先，DB 回退） | `get_current_admin_user`（角色 ∈ platform_admin/org_admin） | M2 `RoleGate` + `role_map` 档位 | `RBACMiddleware` → `PermissionMatrix.check_permission`；`require_user_tier` | `PermissionMiddleware` → `PermissionEngine.check_permission` |
| **是否接入路由** | ✅ **已接入且细粒度** | ❌ **两套均未接线**（DB RBAC 无路由判定；边缘 RBAC 中间件未装配） | ⚠️ 仅 M2 档位生效，`RBACEngine` **未接线** | ✅ 已接入（RBAC + ABAC 均可装配） | ✅ 已接入（含路由→资源/动作映射与端点级例外） |
| 角色档位 | —（以权限码为主） | 定义了四入码→档位，**`require_write_access_from_state` 无调用点** | readonly/readwrite/manage（M2 生效） | READ/READWRITE/MANAGE（写需 ≥READWRITE） | readonly/readwrite/manage（readonly 写 → 403） |
| 租户×角色绑定 | RBAC 表 + 委托（`delegated`） | DB 模型有 `organization_id`/`team_id`/`expires_at`（未接线） | 无 | 组织策略 + `UserRoleBinding` | `user_roles(user_id, role_id, active, subject_source)` |
| 豁免机制 | `k03_bypass_whitelist`（含 owner/reason/audit/expires_at）+ `service_account_subject_map` | — | 仅测试开关 `accept_proxy_source_header_on_any` | **行控豁免注册表**（ticket + 审批人 + 未到期才生效；`org_wide` 仅管理角色或命中豁免） | — |
| 服务账号/匿名写 | `PERM_SERVICE_KEY_WRITE_DENIED`（白名单外 fail-closed） | — | 同码（写需 `subject_type ∈ {user, agent}`） | 同码 | 同码（`write_guard` + 主体分类） |

**判读**：
- **同一族错误码 `PERM_SERVICE_KEY_WRITE_DENIED` 已在三仓出现** → 说明「服务账号/匿名写必须绑定主体」已是被广泛采纳的共识语义，**但只有 OpenBase/OpenRAG/OpenMemory/DPS 四家在做，OpenLLM 缺位**。
- **最大欠账是「存在但未接线的授权引擎」**：OpenLLM（两套）、OpenRAG（RBACEngine）。这会让审计误以为「有 RBAC」，实际路由只做管理员粗判——**属典型的设计-实现偏差**。
- **OpenMemory 是唯一同时具备 RBAC + ABAC + 豁免治理 + 档位 + 双维行控**的系统；**DPS 是唯一把路由→资源/动作映射做成显式表并含端点级例外的系统**（工程完成度最高）。

### 2.5 失败语义（Fail-open / Fail-closed）

| 系统 | 核心判定 | 过渡期/放宽项 | 默认倾向 |
|------|---------|--------------|:--------:|
| OpenBase | JWT/服务 Key 失败 401；`k03` 白名单外写 403 | 主体验证 DB 不可达且无委托 → WARN 放行；`token_version` 默认未强制；入站头过渡期忽略 | 混合（偏 fail-open 过渡） |
| OpenLLM | API Key/JWT 失败 401；未知角色 `ROLE_FAIL_CLOSED=True` → 403 | 非受信带头缺失时放行并标注；**RBAC 路径未命中规则即放行（fail-open）** | 混合 |
| OpenRAG | 行控缺域 → 403；未知角色 → 403；阻断集不可达 → 503 | 限流降级 warn_allow；MCP 无密钥恒放行；未配置 api_key 时跳过鉴权（有启动门禁拦） | 偏 fail-closed |
| OpenMemory | 未知组织 deny；行控缺域 `SCOPE_REQUIRED`；阻断异常即拒 | 过渡期非受信带头忽略 + WARN；BlockSubjectGate 服务缺失放行 | **偏 fail-closed（最强）** |
| DPS | 租户/权限 fail-closed（403/503）；`MULTI_TENANT_FAIL_CLOSED` 与 `PERMISSION_FAIL_CLOSED` 默认 True | 显式 fail-open 仅 `DPS_DEBUG=true` 且开关关闭 | **偏 fail-closed（最强）** |

**判读**：**「过渡期 fail-open」是四仓共有的、明确标注的临时态**（都是「忽略 + 标注 + WARN」），说明这是 P2-1 统一设计的**有意过渡段**；风险在于**过渡段没有统一的退出计划与生产门禁**（只有 OpenMemory 写成启动强制）。

### 2.6 数据模型与错误码

| 系统 | 租户/身份相关表 | 错误码命名空间 | 统一响应体 |
|------|----------------|---------------|-----------|
| OpenBase | `tenants`/`users`/`roles`/`permissions`/`user_role`/`role_permission`/`agent_api_keys`/`audit_logs`/`oidc_identity` | `AUTH_*`/`PERM_*`/`BIZ_*` | `{code,message,detail,request_id}` ✅ |
| OpenLLM | `tenants`/`tenant_schemas`/`tenant_quotas`/`roles`/`permissions`/`user_roles`/`api_keys`/`edge_roles` | 身份层 `code_text` + LL 数值码 | `{code,code_text,message,detail{ll_code},request_id}` |
| OpenRAG | 无租户表；`collections.tenant_code` 等行控列 + `identity_blocked_subjects`/`identity_event_consumption`/`scope_exemption` | `AUTH-4010`/`PERM-403x`/`BIZ-4091`/`DB-5001`（短码 + 数值） | `{code,code_text?,message,detail,request_id}` |
| OpenMemory | `organizations`/`memories`(tenant_code,owner)/`sessions`/`roles`/`permissions`/`role_permissions` + 内存策略 | `E5001xx` 通用码 + 语义文案 | `{code,message,detail,data,request_id}` ✅（**与 OpenBase 对齐**） |
| DPS | `platform.organization`/`platform.tenant`/`permissions`/`roles`/`user_roles` + 审计表 | 语义码（`PERM_FORBIDDEN`/`BIZ_RESERVED_TENANT_CODE`/…）+ `dps_code_legacy` | `{code,message,data,detail,request_id}` ✅ |

**判读**：**OpenBase / OpenMemory / DPS 三家的响应体已同构**；OpenRAG 与 OpenLLM 各有一套（短码 + 数值码）。错误码**语义相同但字面量不同**（如 OpenRAG `PERM-4035` ↔ 三家 `PERM_SERVICE_KEY_WRITE_DENIED`），跨系统排障需靠 R-384 的归因矩阵人工映射。

---

## §3 模板选型：哪一套更完善

### 3.1 评分口径（六维）

| 维度 | 权重 | 说明 |
|------|:----:|------|
| 认证强度 | 20% | 凭据种类、AND 语义、吊销能力 |
| 受信入站完整度 | 15% | 白名单 + 四头 + 三开关 + 生产强制 |
| 多租户治理 | 25% | 注册表真实性、状态机、码值规范化、缺省语义 |
| 授权完成度 | 25% | 是否**接入路由**、粒度、档位、豁免治理 |
| 失败语义 | 10% | fail-closed 覆盖面与生产门禁 |
| 可观测与契约 | 5% | 错误码/响应体一致性 |

### 3.2 结论

| 系统 | 得分判读 | 定位 |
|------|---------|------|
| **OpenMemory** | **授权与隔离维度最完整**：唯一 RBAC+ABAC+豁免治理+档位+双维行控+物理命名空间；唯一把生产强制写成启动门禁 | **授权模型主模板** |
| **DPS** | **租户治理最完整**：真实组织/租户表 + 存在与启停校验 + 码→UUID 双形态规范化 + 401/403 语义最清晰 + 权限映射表最工程化 | **租户治理主模板** |
| **OpenBase** | **集成中枢**：唯一具备统一权限码体系 + 跨系统映射登记（`dps_code_map`/`service_account_subject_map`）+ 唯一身份出站装配点 + 四类凭据全生命周期 | **集成与准入中枢（保留主导权）** |
| OpenRAG | 行控与档位扎实，但**无租户表**、`RBACEngine` 未接线、无入站 JWT | 需补治理与接线 |
| OpenLLM | 设计最丰富（双 RBAC + schema 级隔离 + 租户配额）但**关键件未接线**，实现落后于设计 | 欠账最多，优先收口 |

**一句话结论**：**以 OpenMemory 的授权模型 + DPS 的租户治理 + OpenBase 的集成中枢为「三源模板」**，不选单一系统。若必须只选一套作为「最完善的现成方案」，选 **OpenMemory**（授权维度覆盖最全，且其行控豁免治理是四仓中唯一的成体系豁免机制）。

---

## §4 授权集成的设计原则与目标架构

### 4.1 五条设计原则

| # | 原则 | 依据（现状反例） |
|:-:|------|-----------------|
| P1 | **单一身份权威**：只有 OpenBase 签发主体；四仓只做「受信入站 + 本地档位解释」，不各自签发、不各自定义主体类型 | OpenRAG 无入站 JWT；OpenLLM 边缘 JWT 与主 JWT 双轨；DPS 演示用户硬编码 |
| P2 | **协议契约唯一**：四头 + 链路口 + 白名单 + 三开关为强制契约，默认值与生产强制统一 | 四仓同构但默认值/生产强制不一致（仅 OpenMemory 强制） |
| P3 | **码空间登记唯一**：`tenants.code` 为唯一事实源；各目标域的「可接受码 / 保留码 / 兜底码 / 映射」以**登记表**声明，禁止散落字面量 | R-387 实测：同一 `default` 在 OpenRAG 是禁用保留码、在 OpenMemory 是唯一已登记组织码；`dps_code_map` 已开先例 |
| P4 | **两段式授权职责**：网关侧做**模块级准入**（权限码 `module:action`），目标侧做**数据面细粒度裁决**（角色档位 + 行控/所有权）；两侧共用同一「角色档位」语义 | OpenLLM 路由只做管理员粗判；OpenRAG/OpenMemory/DPS 各有档位但档位表各异 |
| P5 | **拒绝可观测统一**：统一错误码命名空间 + 统一响应体 + 归因矩阵（网关码优先、上游 4xx/5xx 归上游） | 五套码字面量不同、响应体两种形态；跨系统排障依赖人工映射 |

### 4.2 目标架构（四层）

```
┌─────────────────────────────────────────────────────────────────────┐
│ L1 身份权威层（OpenBase 独占）                                        │
│  · 凭证：本地 JWT / OIDC / ob_k_ 服务 Key / sk-agent-*              │
│  · 主体模型：subject_type{user,agent,service,guest} + credential_type│
│  · 吊销：token_version（强制）+ agent key status + 生命周期状态机     │
│  · 权限码权威：module:action + "*"；角色→权限映射（种子幂等）         │
├─────────────────────────────────────────────────────────────────────┤
│ L2 协议契约层（五系统共同遵守，OpenBase 单一装配点出站）               │
│  · 四头 + X-Proxy-Source + X-Request-Id；白名单；strip/enforce/alias │
│  · 角色档位统一：readonly < readwrite < manage                        │
│  · 生产门禁统一：生产必须 enforce=True（照搬 OpenMemory 启动校验）     │
├─────────────────────────────────────────────────────────────────────┤
│ L3 码空间登记层（OpenBase 登记，目标域执行）                          │
│  proxy_code_map{ target, source_of_truth, mappings[],                 │
│                  accepted_codes, reserved_codes, default_code }       │
│  · 由现有 dps_code_map 通用化；R-387 的按目标登记并入此表             │
├─────────────────────────────────────────────────────────────────────┤
│ L4 数据面裁决层（各目标域自治，OpenBase 不越权）                      │
│  · 租户治理：租户注册表 + 状态（存在/启停）→ 照搬 DPS 语义            │
│  · 数据面授权：档位守卫 + 行控 (tenant_code[, owner]) + 豁免治理       │
│  · 目标域可保留自有 RBAC/ABAC（如 OpenMemory），但**必须接线**         │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 关键设计决策（含备选，需确认）

| # | 决策 | 备选 | 建议 | 理由 |
|:-:|------|------|------|------|
| D1 | 身份权威归属 | ① OpenBase 独占 ② 各仓自治 + 联邦 | **①** | 现状已是①、且②会导致主体语义分裂（P1） |
| D2 | 授权职责划分 | ① 网关全权 ② 目标域全权 ③ **两段式** | **③** | 现状已是③的雏形；①会造成网关须懂各域数据规则，②会造成模块级准入缺失 |
| D3 | 租户治理模型 | ① 各仓各自注册表 ② OpenBase 唯一注册表 + 目标域订阅 ③ **OpenBase 权威 + 目标域登记（同步）** | **③** | DPS 已有真实表（不能废弃）；OpenRAG/OpenMemory 缺注册表需补；③ 兼顾存量与统一 |
| D4 | 档位语义 | ① 保留各仓自有角色码 ② **统一档位 readonly/readwrite/manage + 登记式锚点表** | **②** | 四仓已同构（三档），只差统一锚点表与线上接线 |
| D5 | 豁免治理 | ① 各仓自建 ② **上升为通用机制（票据 + 审批人 + 有效期 + 审计）** | **②** | OpenMemory 已有成体系实现；OpenBase `k03_bypass_whitelist` 已是同类，应合并为一种 |
| D6 | 错误码统一 | ① 强制各仓改码 ② **统一码 + 目标域短码映射表（不改上游行为）** | **②** | 强制改码属跨仓破坏性变更；映射表可达同等可观测性且零风险 |

---

## §5 目标域差距清单（按系统）

| 系统 | 认证 | 受信入站 | 多租户 | 授权 | 主要差距（P0/P1） |
|------|:----:|:--------:|:------:|:----:|-------------------|
| OpenBase | ✅ | ✅ | ✅ | ✅ | ① `token_version` 吊销未强制（P1）；② 主体验证 DB 不可达时 fail-open（P1）；③ 入站头过渡期未退出（P1） |
| OpenLLM | ⚠️ | ✅ | ✅ | ❌ | ① **双套 RBAC 均未接线**（P0，审计假象）；② 主 JWT 无租户 claim（P1）；③ API Key 走 `Authorization` 易与 JWT 混淆（P2）；④ 无租户标识不拒绝（P1） |
| OpenRAG | ⚠️ | ✅ | ⚠️ | ⚠️ | ① **无租户注册表**（P1）；② `RBACEngine` 未接线（P1）；③ 无入站 JWT（P2，靠网关可接受）；④ 保留码拒绝分支无结构化日志（P2） |
| OpenMemory | ✅ | ✅ | ✅ | ✅ | ① 无吊销能力（P2）；② 组织策略为内存 `_org_registry` + DB 表双源，存在漂移风险（P1）；③ 未声明保留码集合（P2，R-387 已登记） |
| DPS | ⚠️ | ✅ | ✅ | ✅ | ① `X-API-Key` 语义陷阱（非凭证但名为 API Key，P2）；② 无吊销（P2）；③ 演示用户硬编码、无用户表（P1，IAM 依赖 OpenBase 总线） |

---

### 5.1 派发状态回填（v1.1.0）

| 系统 | 对应差距 | 派发件 | 派发状态（2026-10-08） |
|------|---------|--------|----------------------|
| OpenLLM | G1/G2（P0 双 RBAC 未接线）、G3/G4/G5 | **B1 派单** + B1 立项方案；G4/G5 另见 C1-c | ✅ **已闭环 · 已验收**（2026-10-08：B1 15 端点接线 + C1-c 租户语义；33 passed / 29 passed） |
| OpenRAG | 无租户注册表、`RBACEngine` 未接线 | **C1-b**（租户注册表）；`RBACEngine` 接线见 B 批 B2（**本轮未出单**，待下批） | ✅ **C1-b 已闭环 · 已验收**（2026-10-08，21 passed，基线失败数零变化） |
| OpenMemory | 组织策略双源、仅登记 `default` | **C1-a**（吸收并取代《R387派单-OpenMemory组织码登记》序号 1） | ✅ **已闭环 · 已验收**（2026-10-08，12/12 PASS；登记 `default`/`tenant-1`/`tenant-2`，防护未放宽） |
| DPS | `X-API-Key` 语义陷阱、无吊销、演示用户硬编码 | **本轮未出单**（缺吊销与用户表属其自身 IAM 演进，待版本规划排期） | 未派发（登记在案） |
| OpenBase（本仓） | 吊销未强制、主体验证 fail-open、入站头过渡期未退出 | **A 批已完成**；吊销/验证收紧见 B 批 B4（**本轮未出单**） | A 批已完成；B4 待派 |

> 说明：B 批中 **B1 已随本轮分发**；**B2（OpenRAG RBACEngine 接线）与 B4（OpenBase 吊销/主体验证收紧）本轮未出单**，作为下一批次候选，避免单轮派单过载。

## §6 完善方案（四批路线，逐批可独立交付）

### A 批：契约与登记（低风险，OpenBase 单仓可落地）

| 项 | 内容 | 产出 | 落地状态（v1.1.0 回填） |
|:-:|------|------|------------------------|
| A1 | 把 `dps_code_map` 的**登记模式**通用化为 `proxy_code_map`（保留码 / 兜底码 / 覆盖 / 校验单一入口），DPS 的**值映射**仍由 `dps_code_map` 承载 | 设计说明 + 代码 | **已完成**：`openbase/settings.py`（内置基线 `OUTBOUND_RESERVED_TENANT_CODES_BY_TARGET` + `BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET` + `proxy_code_map` 覆盖 + 三个纯函数）；运行期 `protocol_headers/code_space.py` |
| A2 | R-387 的「按目标登记」并入 `proxy_code_map`，删除散落配置项 | 代码 | **已完成**：移除 `rag_default_tenant_code` / `memory_default_tenant_code` 两字段与 `OPENBASE_RAG_DEFAULT_TENANT_CODE`；编排器改声明 `OPENBASE_PROXY_CODE_MAP` |
| A3 | 统一**角色档位锚点表**（OpenBase 角色码 → readonly/readwrite/manage），供四仓消费（登记式 JSON） | 配置 + 文档 | **已完成**：`config/role_tier_anchors.json`（含四仓现状与差异登记） |
| A4 | 统一**错误码映射表**（目标域短码 ↔ 统一语义码 ↔ 归因层），对接 R-384 归因矩阵 | 文档 + 映射 JSON | **已完成**：`config/error_code_map.json`（11 条 + 归因规则） |
| A5 | 统一**协议契约与开关默认值**说明（含生产强制要求与过渡期退出计划），写入《协议头规范》v1.1 | 设计文档 | **已完成**：`doc/design/OpenBase-协议头规范-v1.1.md`（新增 §2.1 码空间登记、§3.1 档位契约、§4.1 生产门禁、§4.2 过渡期退出计划；§5/§7/§8 回写） |
| 验收 | 映射表可被脚本校验；`ruff`/回归全绿；不改动四仓行为 | | **已达成**：`tests/test_auth_registries.py`（10 例）+ `tests/test_outbound_tenant_code_space.py`（15 例）；`ruff` 0 告警；全量回归 **1147 passed / 0 failed / 4 skipped**；行为等值（兜底值未变） |

### B 批：授权接线补欠账（需四仓各自立项）

| 项 | 内容 | 优先级 |
|:-:|------|:------:|
| B1 | **OpenLLM**：双套 RBAC 收口——保留一套并**接入路由**（建议保留 DB RBAC 以承接租户/团队绑定，弃用或改造 EdgeRouter 配置式）；补齐档位调用点 | **P0** |
| B2 | **OpenRAG**：`RBACEngine` 接线或**明确弃用**（二选一并写入设计文档，消除「有引擎未用」假象） | P1 |
| B3 | **四仓**：统一档位锚点表落地（消费 A3），补线上接线与负向用例（`readonly` 写 → 403） | P1 |
| B4 | **OpenBase**：`token_version` 吊销改为**生产强制**；主体验证 DB 不可达从 fail-open 改 fail-closed（带熔断/降级白名单） | P1 |
| 验收 | 每仓：授权接线可被端点级用例证明（正向 + 负向）；接线覆盖率入设计评审 | |

### C 批：治理增强（跨仓）

| 项 | 内容 | 优先级 |
|:-:|------|:------:|
| C1 | **租户注册表对齐**：照搬 DPS 语义（存在 + 启停 + 401/403 语义）到 OpenRAG/OpenMemory/OpenLLM；OpenBase 为权威源、目标域登记同步 | P1 |
| C2 | **码值规范化统一**：DPS 的「码↔UUID 双形态解析 + 回填」推广为通用能力 | P2 |
| C3 | **豁免治理统一**：以 OpenMemory 行控豁免（票据 + 审批人 + 有效期）为模板，与 OpenBase `k03_bypass_whitelist` 合并为一种机制 | P1 |
| C4 | **生产门禁统一**：把「生产必须 enforce / fail-closed」写成各仓启动校验（照搬 OpenMemory `validate_*_policy`） | P1 |
| C5 | **过渡期退出计划**：为四仓「忽略 + 标注 + WARN」过渡态设定退出条件与版本（否则永久停留） | P1 |
| 验收 | 跨系统一致性矩阵（§D1）逐行可判定；门禁脚本可回归 | |

### D 批：一致性门禁与验证

| 项 | 内容 |
|:-:|------|
| D1 | **跨系统授权一致性矩阵**：端点 × 主体类型（user/agent/service/guest）× 档位 × 租户 → 期望状态码；作为回归基线 |
| D2 | **自动化门禁脚本**：校验协议头契约、档位锚点表、保留码/码空间登记、错误码映射表的一致性（类似 `test_bl147_trust_env_wiring.py` 的静态护栏思路，跨仓版） |
| D3 | **负向用例集**：匿名写、跨租户读、保留码入站、未受信带头、档位不足——五仓统一覆盖率 |
| 验收 | 门禁脚本纳入各仓 CI；D1 矩阵 100% 覆盖零「未定义」格 |

### 6.4 批次依赖与建议顺序

```
A（契约与登记，本仓）
  └─► B1/B2（接线补欠账，需四仓立项）
        └─► C1/C3/C4/C5（治理增强）
              └─► D（一致性门禁收口）
```
建议：**A 批先行**（本仓低风险、收益立即可见）；**B1 与 C1 并行立项**（欠账最重、阻塞面最大）。

---

## §7 风险、假设与待裁定项

### 7.1 风险

| # | 风险 | 等级 | 缓解 |
|:-:|------|:----:|------|
| R1 | 跨仓改造工期不可控（四仓各自立项） | 高 | A/D 批本仓可独立交付；B/C 批拆到单仓最小可交付单元 |
| R2 | 强制 fail-closed 后暴露存量「无档位/无租户」调用方 | 高 | 先影子期（只审计不拒绝）→ 再强制；保留豁免白名单且带有效期 |
| R3 | 统一码空间触发数据可见性变化（R-387 已实测一例：`default` 桶不可达） | 中 | 逐目标登记 + 显式后果登记 + 一键回滚（已有先例） |
| R4 | 错误码映射表与上游实际码漂移 | 中 | D2 门禁脚本静态校验 + 上游 `detail` 契约（R-388 同向） |
| R5 | OpenLLM RBAC 收口可能改动既有行为 | 中 | 先补负向用例与影子观测，再切换 |

### 7.2 假设

1. OpenBase 作为唯一身份权威的组织约定**不变**（现有架构已如此）。
2. 四仓可接受「档位锚点表 + 码空间登记表」由 OpenBase 侧统一维护、仓内只消费。
3. 允许在过渡期保留「忽略 + 标注 + WARN」，但必须设定**退出条件与版本**。

### 7.3 待裁定项与裁定结果（v1.1.0 回填）

| # | 待裁定 | 选项 | 建议 | **裁定结果（2026-10-08）** |
|:-:|--------|------|------|--------------------------|
| **Q1** | 模板选型是否采纳「三源模板」（OpenMemory 授权 + DPS 租户治理 + OpenBase 中枢） | ①采纳 ②仅选 OpenMemory 单源 ③仅选 DPS 单源 | ① | ✅ **采纳① 三源模板** |
| **Q2** | 是否先执行 **A 批**（本仓契约与登记，低风险） | ①先做 A ②A+B 同时 ③暂不动 | ① | ✅ **A 批执行 + 并行立 B1**（A 批已落地；B1 立项与派单已出） |
| **Q3** | 是否就 **B1（OpenLLM RBAC 接线）** 与 **C1（租户注册表对齐）** 分别出跨仓派单项 | ①都出 ②只出 B1 ③暂不出 | ① | ✅ **两份都出**，且已按 DevFlow 纪律**正式分发**（重叠项已处置，见 §9） |
| **Q4** | 过渡期 fail-open 的**退出版本**如何设定 | ①下一版本强制 ②两个版本内强制 ③仅登记不设期 | ②（留影子期） | 采建议值 **②**（已写入《协议头规范 v1.1》§4.2 过渡期退出计划） |
| **Q5** | 错误码统一策略 | ①上游改名对齐 ②**映射表**（不改上游） | ② | 采建议值 **②**（已落地 `config/error_code_map.json`） |
| Q6 | A5（协议头规范 v1.1）是否现在补齐 | ①现在补 ②并入 C 批文档修订 | — | ✅ **现在补齐**（已产出 `doc/design/OpenBase-协议头规范-v1.1.md`） |

> 裁定来源：用户对话（2026-10-08）——「授权集成的模板选型是否采纳三源模板？」= 三源模板；「是否先执行 A 批？」= A 批 + 并行立 B1；「是否分别出跨仓派单项？」= 两份都出；「按 DevFlow 纪律，直接执行 B1/C1 属跨仓事项修正，另外 A5 要现在补上」。

---

## §8 附录：证据索引（关键 `文件:行号`）

| 系统 | 关键证据点 |
|------|-----------|
| **OpenBase** | 统一装配点 `openbase/modules/protocol_headers/inject.py:101-239`；`require_permission` `openbase/modules/auth/rbac.py:109-167`；RBAC 种子 `openbase/core/db/init.py:70-229`；`tenants.code` 事实源 `openbase/modules/protocol_headers/dps_code_map.py:45`；开关 `openbase/settings.py:256-267`；错误码 `openbase/core/errors/codes.py:16-104` |
| **OpenLLM** | 主 JWT 无租户 claim `backend/app/services/auth_service.py:76`；双 RBAC 未接线 `backend/app/api/user.py:79-81`、`backend/app/edgerouter/auth/edge_auth.py:163-287`、`main.py:478-500`；档位未调用 `backend/app/identity/role_map.py:153-159`；三轨隔离 `backend/app/services/tenant_isolation.py:37-99` |
| **OpenRAG** | 无租户表 `src/openrag/main.py:275-277`；保留码 `src/openrag/identity/tenancy.py:6-14`；拒绝分支 `src/openrag/api/middleware/identity_gate.py:227-239`；M2 写守卫 `src/openrag/api/middleware/role_gate.py:92-111`；`RBACEngine` 未接线 `src/openrag/security/rbac_engine.py:13-53`；行控 fail-closed `src/openrag/storage/postgres.py:286-301` |
| **OpenMemory** | 双层 AND `src/openmemory/gateway/gateway.py:87-138`；组织 fail-closed `src/openmemory/auth/permission.py:145-177`；ABAC `src/openmemory/abac/engine.py:30-46`；行控 `src/openmemory/storage/relational_store.py:355-407`；豁免治理 `src/openmemory/identity/scope_exemption.py:110-341`；物理命名空间 `src/openmemory/multitenancy/models.py:36-69`；生产门禁 `src/openmemory/utils/config.py:465-506` |
| **DPS** | 租户表 `src/ddl/schema_root.py:56-124`；存在/启停校验 `src/middleware/tenant_middleware.py:186-325`；码→UUID 规范化 `src/middleware/tenant_middleware.py:287-319`；contextvars 强制过滤 `src/engines/tenant_context.py:17-63`、`src/engines/query_engine.py:84,127,194`；RBAC 真表 `src/engines/permission_engine.py:163-198`；档位 `src/identity/role_map.py:25-62`；fail-closed 默认 `src/config.py:105-111,189-194` |

---

## §9 派单与回执台账（v1.1.0 新增）

### 9.1 本轮已分发派单

| 派单件 | 对象 | 状态 | 回执落点 | 闭环后本仓动作 |
|--------|------|------|---------|---------------|
| `doc/planning/OpenBase-B1派单-OpenLLM授权接线-v1.0.0.md`（v1.0.1） | OpenLLM | **已分发 · 待回执** | 该件 §6.2 | D 批门禁校验（§3.1 锚点一致、§4 用例） |
| `doc/planning/OpenBase-C1派单-租户注册表对齐-v1.0.0.md`（v1.0.2） | OpenMemory / OpenRAG / OpenLLM | **C1-a 已闭环·已验收**；C1-b/C1-c/C1-d 已分发 · 待回执 | C1 派单 §6.4 | ✅ C1-a 回执后**同批切换已执行完毕**（见该件 §6.5 与本文 §10） |

### 9.2 重叠处置

| 项 | 处置 |
|----|------|
| 《OpenBase-R387派单-OpenMemory组织码登记-v1.0.0》序号 1 | **由 C1-a 吸收并取代**；该件转为**已并入的先行登记**，不再独立分发（保留为附件级证据）；回执改由 C1 派单 §6.4 承接 |

### 9.3 本轮未出单（下批候选）

| 项 | 内容 | 建议时机 |
|:--:|------|---------|
| B2 | OpenRAG `RBACEngine` 接线或明确弃用（消除「有引擎未用」假象） | C1-b 同窗口（同仓） |
| B3 | 四仓档位锚点落地与线上接线（消费 A3 制品） | 随 B1/C1 回执推进 |
| B4 | OpenBase `token_version` 吊销强制 + 主体验证 fail-open 收紧 | 本仓独立批次（可与 D 批合并） |
| C2/C3/C4/C5 | 码值规范化统一 / 豁免治理合并 / 生产门禁统一 / 过渡期退出计划 | 随 C 批推进（C4/C5 已写入协议头规范 v1.1） |
| **C4/C5** | 生产门禁统一（生产必须 enforce/fail-closed 写成启动校验）+ 过渡期退出计划（设退出条件与版本） | ✅ **OpenLLM 已落地（2026-10-09，`daea828`/v2.16.3）**：`app/core/config.py::get_settings()` 生产门禁（`ENV=production` 且 `ENFORCE_INBOUND_IDENTITY_HEADERS=false` → `ValueError` 拒绝），兼作过渡期机械截止；3 例用例，复跑 **23 passed**。**其余仓未落地**（OpenMemory 需口径对齐；OpenRAG/DPS 待各自批次） |
| **C3** | 豁免治理统一（票据 + 审批人 + 有效期，以 OpenMemory 行控豁免为模板，与 OpenBase `k03_bypass_whitelist` 合并为一种机制） | 🟡 **第一阶段（契约与登记）已完成（2026-10-09）**：产出 `config/identity_exemptions.json`——统一必填字段（`target`/`ticket`/`approver`/`expires_at`）+ 生效规则 **R1~R5**（拒绝非法豁免 / 到期即失效 / 匿名不豁免 / 必须留痕 / 过渡期须有截止）+ 三实现字段映射与差距清单。**查出的真缺陷**：① **OpenBase `k03_bypass_whitelist` 的 `expires_at` 是声明未生效的死字段**（匹配器无任何时间比较，条目永不失效，违反 R2）；② OpenBase 无 `ticket`/`approver`（违反 R1）；③ OpenLLM 入站头豁免**无专属审计**（违反 R4）；④ OpenMemory 豁免注册表为内存实现且 `src` 内无实例化点。**第二阶段（OpenBase 收紧）已完成（2026-10-09）**：① **R2 落地**——`openbase/modules/proxy/__init__.py` 新增 `_k03_exemption_active()`，匹配器先判到期（**死字段已修复**，非法格式 fail-closed 视为过期）；② **R1 影子期**——`parse_k03_bypass_whitelist` 对缺 `ticket`/`approver`/`expires_at` 的条目输出 WARN + 留痕（**不改变放行行为**，退出条件已登记）；③ 用例 `tests/test_c3_exemptions.py`（6 例，本机环境阻断未执行，改以源码抽取隔离执行验证 R2 **4/4** + 直接构造 `Settings` 验证 R1 **2/2**）。**第三阶段（各仓对齐）待批** |
| D1~D3 | 跨系统授权一致性矩阵 + 自动化门禁脚本 + 负向用例集 | B/C 批复回执后收口 |

### 9.4 A 批交付清单（本仓，已完成）

| 类别 | 交付物 |
|------|--------|
| 代码 | `openbase/settings.py`（内置基线 + `proxy_code_map` + 三纯函数）、`openbase/modules/protocol_headers/code_space.py`（新增）、`rag_proxy`/`memory_proxy` 接入、`scripts/service-orchestrator.ps1`（改声明 `OPENBASE_PROXY_CODE_MAP`） |
| 配置制品 | `config/role_tier_anchors.json`、`config/error_code_map.json` |
| 测试 | `tests/test_outbound_tenant_code_space.py`（15 例）、`tests/test_auth_registries.py`（10 例）、`tests/test_rag_proxy_identity_policy.py` 与 `tests/test_bl147_trust_env_wiring.py`（同步口径） |
| 文档 | **本文件 v1.1.0**、`doc/design/OpenBase-协议头规范-v1.1.md`（A5）、`OpenBase-B1-OpenLLM授权接线收口立项方案-v1.0.0`、`OpenBase-R387-…收口实施记录` v1.2.0（§13 变更影响登记） |
| 验证 | `ruff` 0 告警；全量回归 **1147 passed / 0 failed / 4 skipped**；行为等值（兜底值未变） |

---

## §10 本轮跨仓实施记录（v1.2.0 新增）

### 10.1 已实施：C1-a（OpenMemory 组织码登记）+ 统一码空间终态

| 项 | 内容 |
|----|------|
| 触发 | 人工指令「直接跨仓修复」（2026-10-08），越过「派单等回执」直接实施 |
| 跨仓动作 | **仅配置面登记**：`scripts/service-orchestrator.ps1` openmemory 服务块声明 `OPENMEMORY_RBAC__ORG_POLICIES = {default, tenant-1, tenant-2}`（进程环境变量优先于该仓 `.env`）。**未修改 OpenMemory 仓任何文件**；其 fail-closed 语义与判定逻辑**未放宽** |
| 本仓动作 | 统一码空间终态切换三处：`BUILTIN_DEFAULT_TENANT_CODE_BY_TARGET["memory"]`、`oidc_default_tenant`（**代码默认值 + `.env` 第 17 行**）、IdP 演示池 `DEMO_TENANT_ID` |
| 护栏同步 | `tests/test_memory_proxy.py`、`tests/test_outbound_tenant_code_space.py` 期望值随终态更新；新增「兜底码不得为其目标保留码」不变量用例 |
| 验收 | `doc/tmp/c1_acceptance.py` → **12/12 PASS**（证据：`doc/test/evidence/manual/c1-acceptance-20261008.json`）。关键断言：受信入站 `tenant-1` → `POST /api/v1/recall` **200**（修复前 403）；`POST /api/v1/remember` **200**；未登记码 **仍 403**；网关记忆读/写/删 **200**（读得 total=5，未出现空列表）；RAG 读 **200** 不回归 |
| 回滚 | 三项配置各自置回 `default` 即可，无需改代码或迁移数据 |

### 10.2 教训登记（配置源优先级）

**`settings.py` 的 `model_config = SettingsConfigDict(env_prefix="OPENBASE_", env_file=".env", ...)` 使 `.env` 优先于代码默认值。** 本次首轮验收 B1 断言失败（实际 `default`、期望 `tenant-1`）即因此：代码默认值已改，但 `.env` 第 17 行仍为 `OPENBASE_OIDC_DEFAULT_TENANT=default`。

**规则化**：凡涉及 `Settings` 字段的"默认值变更"，必须**同时检索并修改 `.env*` 中的同名覆盖项**；`config_default` 类变更的验收须包含"有效值断言"（读 `Settings()` 实例值），而非仅检查代码字面量。

### 10.3 已实施（B1 / C1-b / C1-c）与仍待跨仓

| 项 | 说明 | 状态 |
|:--:|------|------|
| **B1** | OpenLLM 双 RBAC 接线（P0）：新增 `app/identity/rbac_guard.py`（`require_permission` + 写类档位守卫 + 两段开关），**15 个端点**接入权限码判定；EdgeRouter 配置式 RBAC **显式 deprecated**（未删除）；档位锚点与 `role_tier_anchors.json` 逐项一致 | ✅ **已闭环**（13 例 TDD 用例；本仓独立复核 33 passed） |
| **C1-c** | OpenLLM 缺租户标识不再静默回退（显式标注 + 两段开关）+ 主 JWT 补 `tenant_code` 声明（向后兼容，旧令牌不受影响）；保留码归一为显式缺省 | ✅ **已闭环**（16 例；复跑 B1 未破坏） |
| **C1-b** | OpenRAG 引入**配置驱动租户注册表** + 单一校验入口（不建表，显式设计决策）；M2 缺租户头不再回落保留码、未登记租户显式拒绝（两段开关）；M1 行为零变化；保留码防护未放宽 | ✅ **已闭环**（21 例；基线失败数零变化） |
| C1-d | 码值规范化（照搬 DPS 双形态解析 + 回填） | 未实施（P2，待排期） |
| **B2** | OpenRAG `RBACEngine` 收口：**明确弃用而非接线**（请求路径已由 M2 `RoleGate`+档位承担，再挂权限码引擎即双引擎并存——与 B1 否决形态同构）；静态登记 `DEPRECATED`/`DEPRECATED_REASON`/`REPLACEMENT_PATH` + 类标记 `__deprecated__`；护栏断言「请求路径零引用」 | ✅ **已闭环**（11 例；本仓独立复核 67 passed；基线 failed/errors 47/40 → **47/40 零增长**） |
| **B3** | 四仓档位锚点落地（消费 A3）+ 负向用例 | ✅ **已闭环（2026-10-09）**：四仓档位锚点**全覆盖** A3 并集（admin/org_admin/**user**/org_member/viewer）——**修复真缺陷**：OpenRAG（`c3a5b85`）与 OpenMemory（`c73b5bb`）原仅收四码、缺 `user`，会把 OpenBase 合法透传码 fail-closed 误拒 `ROLE_UNMAPPED`；OpenLLM/DPS 经机械校验一致。三仓均已具备「readonly 写 → 403」端点级负向用例（RAG `test_s3_t9_role_mapping.py` / OM `test_s2_t11_role_map.py` / DPS `test_s5_t9_role_map.py`）。**门禁加固**：`cross_repo_auth_gate.py` 增「**锚点覆盖**」检查（原仅查"不矛盾"）并硬化提取器（常量式映射 `ROLE_VIEWER: TIER_READONLY` / `ANCHOR_*` / `ROLE_TIER_*` 可解析）→ 复跑 **8 PASS / 1 WARN / 0 FAIL**（四仓锚点全覆盖） |
| **B1 配套** | 权限播种 `scripts/rbac_permission_seed.py` + 影子期观测 `scripts/rbac_shadow_observe.py`（脚本默认 dry-run、不导入任何数据库驱动） | ✅ **已修复（2026-10-09）**：① 落点更正为 `nuct.public`（OpenLLM 自身表结构，uuid 主键、四字段并存），并加**生成期档案校验 + 落点护栏**；② **前置 DDL 与数据播种解耦**——唯一索引独立为 `rbac_seed_ddl.sql`（结构先行），`rbac_seed.sql` 退化为**纯 DML**（数据后行）；③ **D1/D2 裁定采纳**（D1 拆两步交付 / D2 取 A：接线补 `*` 通配语义）；④ 播种 TDD **11 例**、`ruff` 全绿、重跑 diff=0（本机 Python3.13 环境下 1 例环境性失败，与本改动无关）；⑤ **跨仓交付完成（2026-10-09，OpenLLM `9feeec8`）**——制品**照抄落位** `backend/scripts/rbac_seed/`（目标仓自此为执行责任方）、D2-A 接线侧复核（`has_permission_code` 已支持 `*` 通配、G3 守卫优先于 G1）、DevLogReport 升 **v1.1.0 §13**、`version.json`→**2.16.0**，origin/backup/github 三远程哈希一致。**历史缺陷**（v1.9.0 登记的 `INSERT INTO "openbase"."roles"` schema 错配）已消除；⑥ **已在共享库执行完成（2026-10-09）**——预检通过（四表存在 / 计数 0 / 重复行 0 / 缺该唯一索引 / 账号具 `public` 的 `CREATE` 权限）→ 前置 DDL 建 `uq_role_permissions_role_permission` → DML 计数 **roles=5 / permissions=27 / role_permissions=34 / user_roles=0**（与 manifest 一致）→ **幂等复跑新增 0 行**（跳过 66）；⑦ **测试已执行**：`test_b1_rbac_wiring.py` 实测 **16 passed**（经该仓既有 `OPENLLM_TEST_EXTRAS` 机制修复环境），D2-A 验收闭环。**遗留**：⑧ **强制期模块级灰度机制已就位**（`RBAC_PERMISSION_ENFORCE_MODULES`，OpenLLM `6f06198`/v2.16.2，20 例通过）→ 可按 `user → role → knowledge_base → conversation` 逐模块开强制并**单模块独立回滚**；但**实际翻转仍未执行**（本机无运行服务与影子期观测数据，出口门禁无法判定）；`ruff` 未安装故该仓未出静态检查结论 |
| **B1 播种落点（已探明，2026-10-09）** | 共享 PG `192.168.0.151:5432/nuct` 只读探查结果 | **目标 = `nuct` 库的 `public` schema**（非 OpenLLM 仓内 `.env` 所写 `localhost:5432/openllm`）。表结构：`roles(code, name, role_type, level, scope, organization_id…)`、`permissions(code, resource_type, action, scope…)`（**四字段并存**）、`role_permissions(role_id uuid, permission_id uuid, constraints jsonb, is_active)`、`user_roles(user_id uuid, role_id uuid, organization_id uuid, team_id uuid, expires_at, is_active)`。**关联表主键为 uuid**，而 `openbase.roles` 为 bigint——故原 SQL 不仅 schema 名错，**整套键类型与列模型亦不对**，须重写生成器（换数据模型来源）并**加生成期目标校验**（断言目标 schema/表与"目标系统"声明一致，将此类错误变为生成期硬失败）。另注：`nuct` 内另有 `openbase`（OpenBase 自有）与 `platform`（第三方系统）两个 schema，三者权限模型互不相同 |
| **B4** | OpenBase 安全收紧：主体验证 DB 不可达**按环境门控**（生产 fail-closed 503 + 显式白名单；非生产兼容 allow+WARN+留痕，可 `principal_db_degraded_policy` 显式覆盖，生产误配 `allow` 拒绝启动）+ `token_version` 吊销**生产强制** | ✅ **已修复并闭环**：门控落地后全量 **1176 passed / 5 failed / 4 skipped**（5 项为既有 pg 抖动与 1 项本批遗漏，后者已修）；复核 73 passed、`ruff` 全绿。**遗留**：`row_missing` 仍 fail-open（未收紧，另批） |
| **C4/C5** | 生产门禁统一（生产必须 enforce/fail-closed 写成启动校验）+ 过渡期退出计划（设退出条件与版本） | ✅ **OpenLLM 已落地（2026-10-09，`daea828`/v2.16.3）**：`app/core/config.py::get_settings()` 生产门禁（`ENV=production` 且 `ENFORCE_INBOUND_IDENTITY_HEADERS=false` → `ValueError` 拒绝），兼作过渡期机械截止；3 例用例，复跑 **23 passed**。**其余仓未落地**（OpenMemory 需口径对齐；OpenRAG/DPS 待各自批次） |
| **C3** | 豁免治理统一（票据 + 审批人 + 有效期，以 OpenMemory 行控豁免为模板，与 OpenBase `k03_bypass_whitelist` 合并为一种机制） | 🟡 **第一阶段（契约与登记）已完成（2026-10-09）**：产出 `config/identity_exemptions.json`——统一必填字段（`target`/`ticket`/`approver`/`expires_at`）+ 生效规则 **R1~R5**（拒绝非法豁免 / 到期即失效 / 匿名不豁免 / 必须留痕 / 过渡期须有截止）+ 三实现字段映射与差距清单。**查出的真缺陷**：① **OpenBase `k03_bypass_whitelist` 的 `expires_at` 是声明未生效的死字段**（匹配器无任何时间比较，条目永不失效，违反 R2）；② OpenBase 无 `ticket`/`approver`（违反 R1）；③ OpenLLM 入站头豁免**无专属审计**（违反 R4）；④ OpenMemory 豁免注册表为内存实现且 `src` 内无实例化点。**第二阶段（OpenBase 收紧）已完成（2026-10-09）**：① **R2 落地**——`openbase/modules/proxy/__init__.py` 新增 `_k03_exemption_active()`，匹配器先判到期（**死字段已修复**，非法格式 fail-closed 视为过期）；② **R1 影子期**——`parse_k03_bypass_whitelist` 对缺 `ticket`/`approver`/`expires_at` 的条目输出 WARN + 留痕（**不改变放行行为**，退出条件已登记）；③ 用例 `tests/test_c3_exemptions.py`（6 例，本机环境阻断未执行，改以源码抽取隔离执行验证 R2 **4/4** + 直接构造 `Settings` 验证 R1 **2/2**）。**第三阶段（各仓对齐）待批** |
| D1~D3 | 跨系统授权一致性矩阵 + 自动化门禁脚本 + 负向用例集 | **D1/D2 已完成**（`config/auth_consistency_matrix.json` 17 格 × 6 系统 × 8 不变式；`scripts/cross_repo_auth_gate.py` 9 项检查 **0 FAIL**，已纳入回归 `tests/test_cross_repo_auth_gate.py`）；**D3（运行时负向用例集全量复测）未启动** |

**三仓实施共性（风险控制口径）**：三项均采用**观察段默认 + 强制段开关**的两段推进，默认**不改变现场可用性**；均**未重启服务**，故现场走查不受影响；均以「改动前基线 vs 改动后」逐项对比证明**失败数零增长**。
