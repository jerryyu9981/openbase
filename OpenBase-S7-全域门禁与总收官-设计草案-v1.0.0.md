# OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-DESIGN-v1.0.0 |
| 版本 | v1.0.1（文档编号 OB-S7-DESIGN-v1.0.0 沿用） |
| 状态 | [Approved]（**2026-09-11 设计评审人工批准进入开发（S7-T1~T8）**；Q-S7-D1~D10 按本草案 §1.2/§10.2 建议定案登记） |
| 日期 | 2026-09-11 |
| 作者 | AD（跨项目分析）+ AI（沙箱侧现状实测与设计起草） |
| 版本主题 | **S7 段（总收官段）设计草案**：承接《OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md》（内部 **v1.1.0**，[Approved]，2026-09-11 立项评审批准，**34 条验收断言** + **Q-S7-1~Q-S7-8 定案**），给出 **SHR 五项收口**（verify-env 全局化 / openbase_test + run_tests.ps1 / K13 存储账号分离 / 编排唯一入口 / 文档地图）、**三原则总验证**（L1-1 级联全链核验 / L2-1 主备切换演练 + L2-2 通道矩阵终验 / L3-1 Agent 端到端）、**门禁聚合编排**（RA-06 + 冒烟 S0-S6 + 对齐清单关闭 + K07/SYS-1 终验）、**跨仓入仓核验与会签**、**24 卡/JT 台账全量回写 + 总收官报告**的逐任务设计说明、文件落点、34 条设计断言（S7-T1-1~S7-T8-5，与立项 §4 **1:1**）与验收锚点、执行面（A / A+B / B）标注 |
| 适用范围 | S7 段（总收官段）设计、开发、测试与收口；**OpenBase 主仓**（含仓根与 `doc/**` 文档、`scripts/**` 收口脚本）+ **统一前端 `openbase-ui/` 复核面** + **四个子系统仓（OpenMemory / OpenRAG / OpenLLM / DPS）入仓与会签面**。**沙箱仅允许操作 OpenBase 仓**，四仓入仓/会签与真实运行态（PG/Redis、IdP/受信通道、四仓运行态）须由用户在**沙箱外/联调窗口**执行 |
| 上游依据（需求基线） | ①《OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md》（仓根，OB-S7-v1.0.0，内部 **v1.1.0**，[Approved]，34 条验收断言 + Q-S7-1~8 定案）；②《OpenBase-多系统联调联试分阶段版本规划-子系统纵切-v1.0.0.md》（内部 v1.3.1，§3「S7 总收官段」）；③《OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md》（内部 v1.3.0）；④《OpenBase-数据隔离实现任务卡-v1.0.0.md》（内部 v1.7.0，K13 / RA-06 现状）；⑤《OpenBase-真实联调冒烟清单-v1.0.0.md》（OB-INTG-SMOKE-v1.1.0）；⑥《OpenBase-存量测试对齐任务清单-v1.0.0.md》（OB-TEST-ALIGN-v1.0.0，内部 v1.2.0）；⑦《OpenBase-U1-统一身份收口设计草案-v1.0.0.md》（§8 L1-1 事件契约 / §8.4 S7 钩子 / §9 L1-2 purge）；⑧《OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md》（§9.2 OB-9 verify-env / §9.3 OB-7 / §11.4 RA-06 终验引用）；⑨《OpenBase-多系统对接-文档体系与升级路线规划-v1.0.0.md》（内部 v1.1.0，§2.2 D-4 文档地图 / §4 R4）；⑩《OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md》（内部 v1.0.8）/《OpenBase-联调产物清点核对总清单-v1.0.0.md》（内部 v1.0.5）/ 各仓分清单；⑪配套执行件《OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md》（OB-INTG-S7-SIGNOFF-TPL-v1.0.0，commit `72db715`）；⑫《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md》（同构参照） |
| 实测基线（2026-09-11） | OpenBase 仓 HEAD `72db7150762fa64e0c9867e5ab2cd538133bcbeb`（`docs(intg): S7 跨仓入仓与会签执行模板 v1.0.0`）；工作树仅 `dogfood-output/` 噪音（7 项未跟踪，不提交）+ 两份上游文档 M（`OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md` / `OpenBase-数据隔离实现任务卡-v1.0.0.md`，非本草案改动面）；`scripts/verify-env.ps1` + `scripts/verify-env/contract.json`（6 组键）、`scripts/run_tests.ps1`（v1.4.2）、`scripts/service-orchestrator.ps1`、`doc/test/evidence/verify-env-report.json` 实测存在 |
| 设计原则 | ①需求可追溯（34 断言 → 设计条目 1:1，无游离/无新增）；②收口不改子系统语义（四仓仅入仓与 hash 回填）；③可回滚（脚本两段式 + 开关回退 + 清单可还原）；④证据可核（沙箱可判定面 A / 双面 A+B / 联调窗口必需面 B 分离，**B 面未执行一律 PENDING，禁伪造 hash 与通过**） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-11 | AD + AI（沙箱侧现状实测与设计起草） | 初始版本：S7 段（总收官段）设计草案。含 §1 设计输入与 Q 定案登记（承接立项 v1.1.0 八项定案 Q-S7-1~8 + 设计级补充定案建议 Q-S7-D1~D10）、需求覆盖矩阵（34 断言 1:1）、运行环境核实与「沙箱可判定面 vs 联调窗口必需面」清单；§2 总体改造与 5 项关键机制（SHR 收口机制、级联核验机制、主备演练机制、门禁聚合编排、会签与台账回写机制）；§3 现状代码/资产落点（2026-09-11 实测复核，含 verify-env 契约 6 组键、run_tests.ps1 v1.4.2、`grep openbase_test` 0 命中事实、任务卡 K13/RA-06 现状、冒烟清单 v1.1.0、存量对齐清单 v1.2.0、各子系统 verify-env 契约键命名现状）；§4 逐任务设计（S7-T1~T8，设计说明/文件落点/设计断言/验收锚点/执行面）+ 34 条断言汇总表；§5 证据与报告规范；§6 迁移与兼容；§7 风险；§8 边界；§9 里程碑；§10 遗留与设计级定案登记；附录 A~D（34 断言→落点→证据→执行面索引、上游文档与提交号索引、沙箱实测记录、配套执行件引用）。**本文档为新建未跟踪文档，未改动任何代码或其他文档正文** |
| v1.0.1 | 2026-09-11 | AD + AI（设计评审批准回写） | **设计评审人工批准**：状态 [Draft]→**[Approved]**，进入 S7 段开发（S7-T1~T8）；**Q-S7-D1~D10 按 §1.2/§10.2 建议定案登记**（verify-env 全局契约独立文件 + 两段式；openbase_test 独立库；K13 两类账号先落地；编排唯一入口仅约束服务生命周期；文档地图独立索引；门禁聚合 Python；L1-1 专用冒烟主体；收官报告单文件；会签汇总表置 `doc/planning/`）。§10.3 设计评审核对项 6 条通过。**本次仅回写本文档元信息与修订历史，未改动设计正文与其他文件** |

---

## 1. 设计输入与 Q 定案登记

### 1.1 Q-S7-1~Q-S7-8 定案登记（2026-09-11 立项评审批准，设计不再重议）

> **批准口径**：**2026-09-11 S7 段立项评审人工批准进入设计开发**，评审人 = 项目负责人经 AI 开发会话人工确认；**Q-S7-1~Q-S7-8 一次性定案**（口径同立项方案 §3.2 表，本表为唯一事实源；后续设计/开发/测试/收口引用本表，不得跨步反复）。立项方案 §3.2 表「定案状态」列与本表逐条一致。

| # | 事项 | 定案结论（承接立项 §3.2） | 设计落点 | 状态 |
|---|------|--------------------------|---------|------|
| **Q-S7-1** | 各仓入仓与会签闭环口径 | **沙箱外执行 + hash 回填 + 四仓勾稽 + 会签**：四仓按放行清单 v1.0.8 与各仓分清单**逐项显式 `git add`**（禁 `git add -A`/`git add .`）、分批 commit；提交后回填各仓 JT 台账与任务卡卡尾（OpenMemory v1.4.0 / OpenRAG v1.5.0 / OpenLLM v1.6.0 / DPS JT 台账 + S5 卡尾）；以清点总清单 §1.1 为基准逐仓回读 `git status --porcelain -uall` 确认**仅剩 B 类隔离 + C 类噪音 + 清单文档自身**（A 类差异=0）；OpenBase 侧汇总 hash 形成会签记录（总清单 §4.1 五步流程），总清单状态 [Review]→[Approved] | §4.7 S7-T7；§2.5；执行件模板 §2/§4/§5/§6 | ✅ 已定案 |
| **Q-S7-2** | B1~B6 非沙箱回填与验收口径 | B1（Playwright 9 关键页 PASS）/ B2（L3-2 真实受信通道双签）/ B3（真实双租户数据面）/ B4（真实 IdP 回调与吊销）/ B6（nginx `/ui/` 发布回滚）为非沙箱复核项，逐条回填证据（`doc/test/evidence/s6/**`）后关闭；**B5**（四仓 `frontend/` 物理改造与 CI 收敛）按 Q-S6-D7 由各子系统仓执行、S7 复核（需 PG-Redis / IdP / 真实通道 / nginx 就绪，属联调窗口必需） | §4.7（B5 复核）；§5 PENDING 登记；§8 边界 | ✅ 已定案 |
| **Q-S7-3** | L1-1 级联全链核验范围与证据 | 以 U1 §8 事件 schema v1（`user.provisioned/suspended/restored/deactivated`；`event_id` 幂等）与 §8.4 S7 钩子（`GET /api/v1/identity/events/{event_id}` + 阻断状态查询）为契约：真实停用主体 → **DPS 画像读阻断** + **OpenMemory 记忆数据面阻断**（跨域 403/404/空）；**Q-5=A**：数据**保留 + 全链阻断**，**purge 仅显式触发核验**（`POST /api/v1/identity/purge` 二次授权码 + 范围报告；无自动限期清除路径，静态扫描 0 自动 purge） | §4.2 S7-T2；§2.2 | ✅ 已定案 |
| **Q-S7-4** | L2-1 演练口径 | 演练窗口 = 真实联调窗口；按主备矩阵执行 **B 断→A 接管** 与 **A 断→B 维持** 双场景；**单主路径禁双写**（同一动作同一时刻仅一条主路径，禁止双主双写），主路由配置声明、切换显式触发；产出**演练报告**（场景/命令/切换前后路由/降级头/告警/回切条件/结论）；**事件通道（L1-1 身份权威同步面）不纳入 S7 主备切换演练矩阵**（原则边界①，放行清单 §6-4） | §4.3 S7-T3；§2.3 | ✅ 已定案 |
| **Q-S7-5** | L2-2 终验口径 | 以 S4-T8 产出 `matrix_rows` 通道覆盖矩阵为基座，S7 终验「**每子系统 × A/B × 头语义矩阵**」：读路径 B 主全绿 + A 备 covered、**管理面/探活 A 直连豁免行显式标注**；**写路径 A/B 等价与 K14 幂等登记 S7 终验**（Q-LL-8）；终验断言 = 矩阵行全覆盖 + 缺口 0 + 写路径等价用例绿（真实窗口） | §4.4 S7-T4；§2.3 | ✅ 已定案 |
| **Q-S7-6** | L3-1 Agent 端到端口径 | 路径 = **agent key（`sk-agent-*`）→ 四头（X-User-ID/X-Tenant-ID/X-User-Role/X-Proxy-Source）→ 各系统白名单 → 域隔离**；**未授权 403**（非白名单携带身份头 403 `PERM_UNTRUSTED_IDENTITY_HEADER`；跨域 403/404）；agent 无交互登录路径（0 可达）；M1 独立模式（本地 service key 自身认证）与 M2 受信头采纳分别断言 | §4.5 S7-T5 | ✅ 已定案 |
| **Q-S7-7** | RA-06 与冒烟 S0-S6 聚合与对齐清单关闭判定 | RA-06 聚合五项（双租户隔离回归 / fail-closed / OIDC 批次隔离（存量 T2 归档关闭）/ 委托跨界 403 / 吊销即时性）以**单命令/单批聚合**执行全绿；冒烟 S0-S6 按冒烟清单 v1.1.0 §3（P0 全绿、P1 登记）聚合；存量测试对齐清单关闭 = 状态升版 + 分批门禁复跑（OIDC 独立批次 + 主批次 0 失败）+ S6 登记的 asyncpg/PG 4 项环境性失败随 PG 就绪复跑关闭；K07/SYS-1 端点-过滤矩阵终验（缺口清零、未覆盖清零、豁免在有效期且有审批、新增端点无隔离用例不放行） | §4.6 S7-T6；§2.4 | ✅ 已定案 |
| **Q-S7-8** | 24 卡/JT 台账全量回写与收官报告形态 | 24 卡（K01-K18 + RA-01~RA-06）状态全量回写任务卡；JT 台账（七条 JT 线）状态与提交号全量回写归集文档 §3；收官报告形态 = 《S7-全域门禁与总收官报告》（含段门禁六项聚合结论、PENDING 挂起登记、跨仓会签记录、遗留事项），放置于 `doc/development/`（随段门禁批准回写） | §4.8 S7-T8；§2.5；§5 | ✅ 已定案 |

> **定案计数**：Q-S7-1~8 共 **8 项全部 ✅ 已定案**（2026-09-11 立项评审批准）；本设计不再重议，仅在 §1.2 提出设计级补充定案建议（Q-S7-D1~D10，须设计评审裁定）。

### 1.2 设计级补充定案建议（Q-S7-D1~D10，须设计评审裁定）

> 说明：下列为**设计阶段细化的落地口径建议**，均属原定案内的实现形态选择，**不改变 34 条断言口径与执行面分布**；须在设计评审当次裁定。

| # | 事项 | 建议定案 | 关联断言 |
|---|------|---------|---------|
| **Q-S7-D1** | verify-env 全局契约落地形态 | 新建**跨仓统一契约文件** `scripts/verify-env/contract.global.json`（以 OpenBase 6 组为主结构，新增 `repo_overrides` 承载 OpenLLM `identity_trust/REAL/channel/upstream`、OpenRAG/DPS `identity_trust/row_scope/identity_event/api`、OpenMemory `scripts/verify-env` 契约键），并提供**单一全局入口脚本** `scripts/verify_env_global.ps1`（参数 `-Repos` / `-ContractPath` / `-FailFast` / `-SkipNetwork` / `-SkipDb`，逐仓复用各仓 `verify-env`）；`contract.json` 保持现行 6 组不变（非破坏性扩展） | S7-T1-1 |
| **Q-S7-D2** | verify-env 收紧「两段式」时点与回退开关 | **段 1（状态校验）**：默认 WARN 非阻断（exit 0/1），真实探活按契约输出报告；**段 2（强校验）**：`-FailFast` 或 `OPENBASE_VERIFY_ENV_STRICT=1` 时 WARN→exit 1、ERROR→exit 2 阻断；发布顺序 = 先全局契约对齐 → 后强校验开启；**回退开关** = 取消 `-FailFast`/置 `STRICT=0` 即回到非阻断（脚本层可回滚） | S7-T1-1、S7-T7-4 |
| **Q-S7-D3** | openbase_test 建库与隔离形态 | **专用测试库 `openbase_test`**（PG 库/连接）独立于业务库 `openbase`；新增 `scripts/db/init_openbase_test.ps1`（建库/建账号/幂等迁移，`WHERE NOT EXISTS`/`create_all` 幂等）；测试连接由 `OPENBASE_DB_URL` 指向 `openbase_test`（隔离业务库）；`run_tests.ps1` 升为**跨仓统一回归入口**（保留 OpenBase 单仓分组子进程隔离既有能力，新增 `-Repos` 编排 + 逐仓回归命令表） | S7-T1-2 |
| **Q-S7-D4** | K13 账号矩阵文件与授权脚本落点 | 新增 `doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md`（schema×账号×权限矩阵：`openbase` 应用账号 / `platform`（DPS 等）账号 / 迁移账号 / 运行时账号）与授权脚本 `scripts/db/grant_k13_accounts.ps1`（`GRANT` 仅本 schema DML、不授 superuser、禁跨 schema 写）；复核命令 = 跨 schema 写拒绝用例 + `has_schema_privilege` 检查 | S7-T1-3 |
| **Q-S7-D5** | 受管编排唯一入口固化形态 | 以既有 `scripts/service-orchestrator.ps1` 为**唯一入口**（`start/startcheck/checkall/monitor/status/stop`），新增静态规则 `scripts/scan_orchestrator_bypass.py`：扫描仓内 `taskkill`/`Stop-Process`/`kill -9` 等**批量杀路径**（`service-orchestrator.ps1` 按记录 PID 逆拓扑 stop 为**唯一允许位**），断言「无绕过路径」= 0 命中 | S7-T1-4 |
| **Q-S7-D6** | 文档地图落点与并入核对 | 文档地图维护点 = 《OpenBase-多系统对接联调问题复盘与根治方案-v1.0.0.md》（L0-L4 全量文档清单：名称/版本/角色/状态/关联锚点），新增 **S1a~S7 纵切文档并入核对表**（`doc/design/OpenBase-文档地图索引-v1.0.0.md` 为地图正文落点）；核对判据 = 「无游离文档」（L0-L4 各层文档均在索引内） | S7-T1-5、S7-T8-3 |
| **Q-S7-D7** | 门禁聚合脚本形态 | 新增 `scripts/gate_aggregate.py`（单命令/单批）：聚合 ① RA-06 五项 ② 冒烟 S0-S6 ③ 存量对齐清单关闭 ④ K07/SYS-1 矩阵终验；输出证据 JSON `doc/test/evidence/s7/gate-aggregate.json`（含各分项结论/证据路径/提交号/执行面/PENDING），失败项不伪造、如实登记 | S7-T6-1~4 |
| **Q-S7-D8** | S7 段 evidence 目录结构 | `doc/test/evidence/s7/` 下设 `shr/`（SHR 五项：`verify-env-global/`、`openbase-test/`、`k13/`、`orchestrator/`、`doc-map/`）、`l1-1/`、`l2-1/`、`l2-2/`、`l3-1/`、`gate/`、`signoff/`，子项均含 `status`（`PASS`/`PENDING`/`FAIL`）+ `reason` + `openbase_commit`；**未执行一律 PENDING，禁伪造** | S7-T1~T8 |
| **Q-S7-D9** | S7 总收官报告形态与落点 | 报告模板 = 《OpenBase-S7-全域门禁与总收官报告-v1.0.0.md》置 `doc/development/`；含「段门禁六项聚合结论 + PENDING 挂起登记 + 跨仓会签记录 + 遗留事项」四段；结论如实（未执行项 PENDING 不阻断批准，对齐 S5/S6 范式） | S7-T8-4、S7-T8-5 |
| **Q-S7-D10** | OpenBase 侧会签汇总表形态 | 新增 `doc/planning/OpenBase-S7-跨仓入仓与会签-OpenBase汇总核对表-v1.0.0.md`，以执行件模板 §2/§4/§5/§6 为数据源，汇总四仓 commit hash + 逐仓 A 类差异回读 + 会签五步结论；放行/清点清单升版（v1.0.8/v1.0.5 → [Approved]） | S7-T7-3、S7-T7-4 |

### 1.3 需求覆盖矩阵（立项 34 条验收断言 → 设计条目 1:1）

| 断言 ID 区间 | 归属任务 | 条数 | 本文设计条目 | 执行面 |
|-------------|---------|:---:|-------------|:---:|
| S7-T1-1 ~ S7-T1-5 | S7-T1 SHR 五项收口 | 5 | §4.1 | A+B×3 / B×1 / A×1 |
| S7-T2-1 ~ S7-T2-4 | S7-T2 L1-1 级联全链核验 | 4 | §4.2 | B×3 / A+B×1 |
| S7-T3-1 ~ S7-T3-4 | S7-T3 L2-1 主备切换演练 | 4 | §4.3 | B×4 |
| S7-T4-1 ~ S7-T4-4 | S7-T4 L2-2 通道矩阵终验 | 4 | §4.4 | B×4 |
| S7-T5-1 ~ S7-T5-4 | S7-T5 L3-1 Agent 端到端 | 4 | §4.5 | B×4 |
| S7-T6-1 ~ S7-T6-4 | S7-T6 RA-06 + 冒烟聚合 + 对齐清单关闭 | 4 | §4.6 | A+B×2 / B×2 |
| S7-T7-1 ~ S7-T7-4 | S7-T7 跨仓入仓核验与会签 | 4 | §4.7 | B×2 / A+B×1 / A×1 |
| S7-T8-1 ~ S7-T8-5 | S7-T8 24 卡/JT 回写 + 文档地图 + 总收官报告 | 5 | §4.8 | A×3 / A+B×2 |
| **合计** | — | **34** | §4.1~§4.8 + §4.9 汇总 | A **5** / A+B **9** / B **20** |

**覆盖结论**：34 条验收断言 **1:1 全覆盖**（无游离断言、无新增断言，计数与立项 §4 及 §4 尾注执行面分布「A 5 / A+B 9 / B 20」完全一致）。

### 1.4 运行环境核实结论与「沙箱可判定面 vs 联调窗口必需面」

| 核实项 | 命令/方式 | 实测结论（2026-09-11） |
|--------|----------|----------------------|
| OpenBase 仓 HEAD | `git log -1 --format='%h %s'` | `72db715 docs(intg): S7 跨仓入仓与会签执行模板 v1.0.0` |
| 工作树状态 | `git status --porcelain` | 7 项 `?? dogfood-output/**`（不提交）+ 2 项 `M`（归集 / 任务卡，非本草案改动面） |
| `scripts/verify-env.ps1` | `Test-Path` / Read | 存在；WARN 非阻断雏形，exit 0/1/2，`-FailFast` / `-SkipNetwork` / `-SkipDb`；输入 `verify-env/snapshot.py`；输出 `verify-env-report.json` |
| `scripts/verify-env/contract.json` | Read | 存在；`schema_version=1`；**6 组键**：`config_single_source`(13) / `config_deprecated`(2) / `upstreams`(4) / `whitelist_matrix`(5) / `mapping_reconcile`(1) / `db_checks`(1) |
| `scripts/run_tests.ps1` | Read | 存在；**v1.4.2**（TD-新增-009）；按文件分组子进程隔离（每组 6 文件）+ `ruff`；可选 `-WithCoverage`；**单仓**（无跨仓编排） |
| `openbase_test` 独立测试库 | `grep -rn openbase_test` | **0 命中**（指独立测试库连接配置；仓内仅测试临时文件名前缀 `openbase_test_*.db`，非独立库）→ 独立库**未建立** |
| `scripts/service-orchestrator.ps1` | Read | 存在；`start/startcheck/checkall/monitor/status/stop`；单一事实源 = 端口统筹方案；stop 按**记录 PID 逆拓扑**（非批量杀） |
| 任务卡 K13 | Read（§K13） | 状态 **⏳待立项（U2）**；规则 §12.6 R-M3-1/2 → OB-7；批次 R2；改动点 = 账号分离/仅授本 schema DML/迁移与运行时账号分离/不授 superuser |
| 任务卡 RA-06 | Read（§RA-06） | 状态 **⏳**；批次 R1；前置 K01-K08 + RA-01~RA-05 全部；验收断言「R1 门禁单命令全绿；T2 OIDC 台账归档关闭」 |
| 冒烟清单 | Read（头部） | **OB-INTG-SMOKE-v1.1.0**，[Draft]，待执行（需真实服务环境）；§3 用例矩阵 S0-S6，P0/P1 语义已定义 |
| 存量对齐清单 | Read（头部） | **OB-TEST-ALIGN-v1.0.0**（内部 **v1.2.0**），状态 **[Draft]**；T1/T2/T3/T4 状态追踪（T1 `0f808e9` / T2 空库复现 / T3 `15b520a` / T4 全量回归） |
| 各子系统 verify-env 契约键命名现状 | 上游实测（立项 §2.3；沙箱仅 OpenBase，未直接读四仓文件） | OpenLLM `identity_trust/REAL/channel/upstream`；OpenRAG 与 DPS `identity_trust/row_scope/identity_event/api`；OpenMemory `scripts/verify-env/`（目录级，具体键名待仓内确认） |

**沙箱可判定面（A 面，S7 内可直接执行并作为证据，禁止伪造）**

| # | 可执行项 | 命令/方式 | 用途（断言） |
|---|---------|----------|-------------|
| A1 | verify-env 结构对账 | `scripts/verify-env.ps1 -SkipNetwork -SkipDb` + `scripts/verify_env_global.ps1 -Repos ... -SkipNetwork -SkipDb` 干跑 | S7-T1-1（结构面） |
| A2 | run_tests.ps1 脚本干跑/结构核对 | `scripts/run_tests.ps1`（沙箱内既有回归）+ 跨仓编排干跑 | S7-T1-2（结构面） |
| A3 | K13 账号矩阵文件核对 + 授权脚本结构干跑 | 矩阵文件 + `scripts/db/grant_k13_accounts.ps1`（打印模式） | S7-T1-3（结构面） |
| A4 | 编排唯一入口静态规则 | `scripts/scan_orchestrator_bypass.py`（0 命中） | S7-T1-4（静态面） |
| A5 | 文档地图核对 | `doc/design/OpenBase-文档地图索引-v1.0.0.md` + L0-L4 核对表 | S7-T1-5、S7-T8-3 |
| A6 | purge 静态扫描 | `scan_auto_purge`（无 scheduler 定时 purge）= 0 命中 | S7-T2-3（静态面） |
| A7 | 门禁聚合脚本沙箱干跑 | `scripts/gate_aggregate.py --dry-run` + 清单关闭判定 | S7-T6-1/3（结构面） |
| A8 | 会签汇总与清单升版 | OpenBase 侧汇总核对表 + 放行/清点清单 [Approved] 回写 | S7-T7-3/4 |
| A9 | 24 卡/JT 台账回写 + 报告编制 | 回写表 + 《S7-全域门禁与总收官报告》 | S7-T8-1~5（文档面） |
| A10 | 提交面纪律核对 | `git status --porcelain -uall`（仅白名单；`dogfood-output/` 不入） | 全任务提交卫生 |

**联调窗口必需面（B 面，须由用户在沙箱外/受控环境执行；S7 内只登记 PENDING，不得伪造结果）**

| # | 复核项 | 前置条件 | 阻塞断言 | 处置 |
|---|--------|---------|---------|------|
| B-1 | verify-env 真实探活（跨仓端口/上游/db） | 真实 PG/Redis + 四仓运行态 | S7-T1-1（真实面） | 结构对齐沙箱内产出；真实探活联调窗口执行并回填 |
| B-2 | openbase_test 真实建库与隔离 | 真实 PG + 建库权限 | S7-T1-2（真实面） | 脚本沙箱内产出；真实建库/隔离联调窗口执行 |
| B-3 | K13 账号矩阵授权与跨 schema 写拒绝 | 真实 PG + 账号授权权限 | S7-T1-3 | 矩阵文件/脚本沙箱内产出；授权与拒绝验证联调窗口执行 |
| B-4 | L1-1 级联真实停用与数据面阻断（DPS 画像读 / OpenMemory 记忆） | 四仓运行态 + 真实 PG/Redis | S7-T2-1/2/4 | 核验脚本沙箱内产出；真实执行联调窗口 |
| B-5 | L2-1 主备切换演练（B 断→A / A 断→B） | 可注故障的运行态 + 切换窗口 | S7-T3-1~4 | 演练脚本/报告模板沙箱内产出；演练联调窗口执行 |
| B-6 | L2-2 通道矩阵终验 + 写路径等价/K14 | 四仓运行态 + 真实通道 | S7-T4-1~4 | 终验表模板沙箱内产出；终验联调窗口执行 |
| B-7 | L3-1 Agent 端到端（四头/白名单/域隔离/403） | 四仓运行态 + 真实 agent key | S7-T5-1~4 | 用例矩阵沙箱内产出；执行联调窗口 |
| B-8 | RA-06 聚合 + 冒烟 S0-S6 + K07/SYS-1 终验 | 真实 PG/Redis/IdP/四仓 | S7-T6-2/4 | 聚合脚本沙箱内产出；执行联调窗口 |
| B-9 | 四仓入仓 / hash 回填 / 勾稽 / 会签 | 四仓 git 写权限（沙箱仅 OpenBase） | S7-T7-1/2 | 汇总核对表沙箱内产出；四仓命令沙箱外执行（执行件模板） |
| B-10 | S6 移交 B1~B6 非沙箱复核 | 真实通道 / IdP / PG-Redis / nginx | S7-T7（B5 复核）、S7-T8-4 | 逐条回填 `doc/test/evidence/s6/**` 后关闭 |

> **纪律（写入测试与收口报告口径）**：任何未在沙箱/受控环境真实执行的 B 面项，一律标注 `PENDING（未执行）` 或 `沙箱受限`，**禁止以「预期通过」代替证据，禁止编造 hash、截图、报告**（对齐立项 §7 R-1/R-5 与 Q-S7-1/S7-T7-1）。

---

## 2. 总体改造与关键机制

### 2.1 目标架构（SHR 五收口 + 三原则验证 + 门禁聚合 + 会签回写）

```
SHR 收口面（共享基础设施，S7-T1）
  verify-env 全局化（跨仓统一契约 + 单一全局入口 + 两段式 WARN→fail-fast）
  openbase_test 独立测试库 + run_tests.ps1 跨仓统一回归入口
  K13 存储账号分离（schema×账号×权限矩阵 + 授权脚本）
  受管编排唯一入口（service-orchestrator.ps1 + 禁批量杀静态规则）
  文档地图（L0-L4 索引 + S1a~S7 并入核对）

三原则验证面（真实联调窗口，S7-T2~T5）
  L1-1 级联全链：停用 → DPS 画像读阻断 / OpenMemory 记忆数据面阻断（Q-5=A 保留+阻断，purge 显式触发）
  L2-1 主备演练：B 断→A 接管 / A 断→B 维持（单主路径禁双写）
  L2-2 通道终验：每子系统 × A/B × 头语义矩阵（读 B 主 A 备 + 写路径等价 + K14 幂等）
  L3-1 Agent：agent key → 四头 → 白名单 → 域隔离（未授权 403）

门禁聚合面（单命令编排，S7-T6）
  scripts/gate_aggregate.py → gate-aggregate.json（RA-06 + 冒烟 S0-S6 + 对齐清单关闭 + K07/SYS-1）

会签与回写面（S7-T7/T8）
  四仓入仓 → hash 回填 → 四仓勾稽（A 类差异 0）→ 跨仓会签 → 清单升版
  24 卡（K01-K18 + RA-01~RA-06）+ 七线 JT 台账全量回写 → 总收官报告（doc/development/）
```

**设计不变式（Invariants）**
- INV-1：**收口不改语义**——S7 仅收口既有能力（verify-env 完整版/测试库/账号矩阵/编排入口/文档地图），不新增功能开发，不改 DPS/OpenLLM/OpenMemory/OpenRAG 功能语义与数据面实现。
- INV-2：**A/B 面分离**——任一证据项必须标明执行面（A / A+B / B）；**B 面无真实证据不得填 PASS**。
- INV-3：**禁伪造 hash**——四仓 hash 与 S7 段提交号一律真实回填；受限则登记 `PENDING`。
- INV-4：**收口可回滚**——verify-env 两段式 + 开关回退；清单升版可还原；脚本层保留上一版本。
- INV-5：**提交面纪律**——S7 提交面仅 OpenBase 仓（仓根/`doc/**`/`scripts/**`/`openbase-ui/**` 复核面 + `doc/test/evidence/s7/**`）；**不得纳入 `dogfood-output/`**；四仓命令沙箱外执行。

### 2.2 关键机制 1：SHR 收口机制（T1 核心）

**机制 1a：verify-env 全局化（统一契约 + 单一入口 + 两段式收紧）**
- **统一契约**：以 OpenBase `scripts/verify-env/contract.json` 6 组键为主结构，新建 `scripts/verify-env/contract.global.json` 新增 `repo_overrides` 节点，承载四仓契约键命名对齐（OpenLLM `identity_trust/REAL/channel/upstream`；OpenRAG/DPS `identity_trust/row_scope/identity_event/api`；OpenMemory `scripts/verify-env`）；**命名/结构对齐为静态可判定**。
- **单一全局入口**：`scripts/verify_env_global.ps1`（`-Repos` 逐仓调度各仓 `verify-env`，汇总 exit 语义 0/1/2），OpenBase 侧保留既有 `scripts/verify-env.ps1`（非破坏性）；**真实探活属联调窗口**。
- **两段式 WARN→fail-fast**（Q-S7-D2）：段 1 默认 WARN 非阻断（exit 0/1）；段 2 `-FailFast`/`STRICT=1` 时 WARN→exit 1、ERROR→exit 2 阻断；**回退开关保留**（取消开关即回退）。

**机制 1b：openbase_test 独立测试库 + run_tests.ps1 跨仓统一回归入口**
- **建库/建账号/幂等迁移**：`scripts/db/init_openbase_test.ps1`（幂等：`WHERE NOT EXISTS` / `create_all`），测试连接 `OPENBASE_DB_URL` 指向 `openbase_test`，**与业务库 `openbase` 隔离**；当前 `grep openbase_test` **0 命中**（独立库未建立）为该机制的直接缺口。
- **run_tests.ps1 升级**：保留 v1.4.2 单仓「按文件分组子进程隔离 + ruff + 可选覆盖率」能力，**新增跨仓统一回归入口**（`-Repos` 逐仓命令表编排，OpenBase 为主仓）；**真实建库与跨仓实跑属联调窗口**。

**机制 1c：K13 存储账号分离（schema×账号×权限）**
- **矩阵文件**：`doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md`（账号 = `openbase` 应用账号 / `platform`（DPS 等）账号 / 迁移账号 / 运行时账号；权限 = 各自仅授本 schema DML、不授 superuser）。
- **授权脚本**：`scripts/db/grant_k13_accounts.ps1`（`GRANT` 收敛）；**跨 schema 写 0 成功路径**由 DB 级拒绝断言（真实 PG）。
- **现状**：任务卡 K13 状态 ⏳待立项（U2）——S7 首次落地，属**联调窗口必需**。

**机制 1d：受管编排唯一入口（禁批量杀）**
- **唯一入口** = `scripts/service-orchestrator.ps1`（`start/startcheck/checkall/monitor/status/stop`，stop 按记录 PID 逆拓扑，**非批量杀**）。
- **静态规则** `scripts/scan_orchestrator_bypass.py`：扫描 `taskkill` / `Stop-Process` / `kill -9` 等批量杀路径，`service-orchestrator.ps1` 的逆拓扑 stop 为**唯一允许位**；断言「无绕过路径」= 0 命中（沙箱可判定）。

**机制 1e：文档地图（L0-L4 索引 + 并入核对）**
- **地图正文落点** = `doc/design/OpenBase-文档地图索引-v1.0.0.md`（L0-L4 全量文档：名称/版本/角色/状态/关联锚点）；**维护点** = 复盘根治方案（路线规划 §2.2 D-4）。
- **并入核对**：S1a~S7 纵切新增文档（立项/设计/DevLog/测试/台账/清单）逐项并入，判据「无游离文档」（文档面沙箱可判定）。

### 2.3 关键机制 2/3：级联核验机制（L1-1）与主备演练机制（L2-1/L2-2）

**机制 2：L1-1 级联全链核验（T2）**
```
真实停用主体（POST identity suspend/patch status）
  → 事件 outbox：user.suspended（event_id 幂等）
      → DPS 消费端：画像读阻断（403/404，数据保留）
      → OpenMemory 消费端：记忆数据面阻断（sessions/memories 拒绝，数据保留）
  → 恢复（restored）：阻断解除
  → Q-5=A：数据保留 + 全链阻断；purge 仅显式触发
      （POST /api/v1/identity/purge：非 deactivated → 400；未二次授权 → 403；
        授权后物理清除 + audit_logs action=identity.purge；无 scheduler 定时 purge）
```
- 契约 = U1 设计草案 §8 schema v1 + §8.4 S7 钩子（`GET /api/v1/identity/events/{event_id}` + 阻断状态查询）；OpenBase 事件契约端点锚点 `0713ec1`。
- **静态可判定**：无自动 purge 路径（`scan_auto_purge` 0 命中 / 无 scheduler 注册）；**真实阻断属联调窗口**。

**机制 3：L2-1 主备演练 + L2-2 通道矩阵终验（T3/T4）**
- **主备矩阵（Q-4 定案：B 主 A 备）**：单主路径状态机（S4-T7 `ChannelStateManager`）——**同一动作同一时刻仅一条主路径**，切换**显式触发**，**禁双主双写**。
- **L2-1 双场景**：`B 断 → A 接管`（降级头/告警产生，业务不中断）；`A 断 → B 维持`（B 编排维持）。
- **L2-2 终验**：以 S4-T8 `matrix_rows` 为基座 → 「每子系统 × A/B × 状态/头语义」矩阵：读路径 B 主全绿 + A 备 covered；管理面/探活 A 直连豁免行显式标注；**写路径 A/B 等价 + K14 幂等**。
- **边界**：事件通道（L1-1 身份权威同步面）**不纳入**主备切换演练矩阵（Q-S7-4）。

### 2.4 关键机制 4：门禁聚合编排（T6）

```
scripts/gate_aggregate.py   （单命令 / 单批）
  ├─ 分项 ①：RA-06 五项（双租户隔离回归 / fail-closed / OIDC 批次隔离 / 委托跨界 403 / 吊销即时性）
  ├─ 分项 ②：冒烟 S0-S6（冒烟清单 v1.1.0 §3；P0 全绿 / P1 登记）
  ├─ 分项 ③：存量测试对齐清单关闭（状态升版 + OIDC 独立批次 + 主批次 0 失败 + asyncpg/PG 4 项复跑）
  └─ 分项 ④：K07/SYS-1 端点-过滤矩阵终验（缺口清零、未覆盖清零、豁免在有效期且有审批）
       ↓
  doc/test/evidence/s7/gate/gate-aggregate.json
    { 各项 status(PASS/PENDING/FAIL) + evidence_path + openbase_commit + execution_face(A/B) + reason }
```
- **单命令/单批**：聚合脚本一次调用产出一致性证据；分项失败**不伪造**，按 PENDING/FAIL 如实登记。
- **前置**：K01-K08 + RA-01~RA-05 全部；真实 PG/Redis/IdP（真实面属联调窗口）。

### 2.5 关键机制 5：会签与台账回写机制（T7/T8）

```
四仓入仓（沙箱外，执行件模板）
  → 前置裁断（23 项待人工判定 + 7 项边界确认）
  → 分批入仓（逐项显式 git add，禁 -A；每仓回归失败即停）
  → hash 回填（各仓 JT 台账 + 任务卡卡尾）
  → 四仓勾稽（git status --porcelain -uall；A 类差异 = 0）
  → 跨仓会签（总清单 §4.1 五步流程）→ 清单升版（放行 v1.0.8 / 清点 v1.0.5 → [Approved]）
  → 24 卡（K01-K18 + RA-01~RA-06）+ 七线 JT 台账全量回写
  → 《S7-全域门禁与总收官报告》（doc/development/）：段门禁六项聚合 + PENDING + 会签 + 遗留
```
- **执行件** = `doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md`（commit `72db715`）；OpenBase 侧汇总 = Q-S7-D10 汇总核对表。
- **纪律**：hash 一律真实；未执行项 PENDING 不阻断批准（对齐 S5/S6 范式）。

---

## 3. 现状代码/资产落点（2026-09-11 实测复核）

> 复核基线：OpenBase 仓 HEAD `72db715`；以下路径均为仓内相对路径，行号/键名/计数为**当日实测**（沙箱仅可读 OpenBase 仓；四仓契约键命名取自立项 §2.3 上游实测，未直接读四仓文件，标注「上游实测」）。

### 3.1 SHR 五项现状落点

| # | SHR 项 | 实测落点 | 现状要点 | S7 设计动作 |
|---|--------|---------|---------|-----------|
| 1 | verify-env 全局化 | `scripts/verify-env.ps1`、`scripts/verify-env/contract.json`、`scripts/verify-env/snapshot.py`、`doc/test/evidence/verify-env-report.json` | 契约 **6 组键**：`config_single_source`(13 键) / `config_deprecated`(2) / `upstreams`(4) / `whitelist_matrix`(5 sources) / `mapping_reconcile`(1) / `db_checks`(1)；`schema_version=1`；WARN 非阻断雏形；exit 0/1/2；`-FailFast`/`-SkipNetwork`/`-SkipDb`；最新报告 `warnings=9 errors=0 exit_code=1`（2026-09-08） | 新建 `contract.global.json` + `verify_env_global.ps1`（机制 1a） |
| 2 | openbase_test + run_tests.ps1 | `scripts/run_tests.ps1`（**v1.4.2**） | 按文件分组子进程隔离（每组 6 文件）+ `ruff` + 可选 `-WithCoverage`；**单仓**；**`grep openbase_test` 0 命中**（独立库未建立） | 新建 `scripts/db/init_openbase_test.ps1` + run_tests.ps1 升跨仓入口（机制 1b） |
| 3 | 存储账号分离 K13 | `OpenBase-数据隔离实现任务卡-v1.0.0.md` §K13 | 状态 **⏳待立项（U2）**；规则 §12.6 R-M3-1/2 → OB-7；批次 R2；`contract.json` 的 `db_checks` 仅 1 检查位（`schema=openbase` `tenants.code` 唯一事实源对账），**无 schema×账号×权限矩阵** | 新建 K13 矩阵文件 + `grant_k13_accounts.ps1`（机制 1c） |
| 4 | 编排唯一入口 | `scripts/service-orchestrator.ps1` | 存在；`start/startcheck/checkall/monitor/status/stop`；单一事实源 = 端口统筹方案；stop 按记录 PID 逆拓扑（非批量杀） | 静态规则 `scan_orchestrator_bypass.py` + 唯一入口固化（机制 1d） |
| 5 | 文档地图 | 上游实测（路线规划 §2.2 D-4）；**本轮**新增落点 `doc/design/OpenBase-文档地图索引-v1.0.0.md` | 地图维护点已定案（L0-L4 全量清单），S1a~S7 纵切新增文档**尚未并入统一地图核对** | 地图正文落点 + S1a~S7 并入核对（机制 1e） |

### 3.2 门禁与台账现状落点

| 项 | 实测落点 | 现状要点 | S7 设计动作 |
|----|---------|---------|-----------|
| 任务卡 K13 | `OpenBase-数据隔离实现任务卡-v1.0.0.md`（内部 v1.7.0）§K13 | ⏳待立项（U2）；账号分离/仅授本 schema DML/迁移与运行时账号分离/不授 superuser | §4.1 S7-T1-3 |
| 任务卡 RA-06 | 同上 §RA-06 | **⏳**；批次 R1；前置 K01-K08 + RA-01~RA-05 全部；验收断言「R1 门禁单命令全绿；T2 OIDC 台账归档关闭」 | §4.6 S7-T6-1/3 |
| 冒烟清单 | `OpenBase-真实联调冒烟清单-v1.0.0.md` | **OB-INTG-SMOKE-v1.1.0**，[Draft]，待执行（需真实服务环境）；§3 用例矩阵 S0-S6（P0 全绿/P1 登记） | §4.6 S7-T6-2 |
| 存量对齐清单 | `OpenBase-存量测试对齐任务清单-v1.0.0.md` | **OB-TEST-ALIGN-v1.0.0**（内部 **v1.2.0**），状态 **[Draft]**；T1 `0f808e9` / T2 空库复现 / T3 `15b520a` / T4 全量回归分批门禁已落绿，**清单未关闭** | §4.6 S7-T6-3 |
| 事件契约锚点 | 立项 §10 附录 C：`0713ec1`（`GET /api/v1/identity/events` 身份事件列表契约端点） | 2026-09-09 冻结 | §4.2 S7-T2 |

### 3.3 各子系统 verify-env 契约键命名现状（上游实测，对齐目标）

| 仓 | 契约键命名（上游实测） | 对齐目标（本设计） |
|----|----------------------|-------------------|
| OpenMemory | `scripts/verify-env/`（目录级，具体键名待仓内确认） | 并入 `contract.global.json` `repo_overrides.openmemory` |
| OpenRAG | `identity_trust` / `row_scope` / `identity_event` / `api`（S3-T10） | 并入 `repo_overrides.openrag`（命名/结构对齐） |
| OpenLLM | `identity_trust` / `REAL` / `channel` / `upstream`（S4-T14） | 并入 `repo_overrides.openllm`（命名/结构对齐） |
| DPS | `identity_trust` / `row_scope` / `identity_event` / `api`（S5-T11 配套） | 并入 `repo_overrides.dps`（命名/结构对齐） |
| OpenBase（本仓） | `config_single_source` / `config_deprecated` / `upstreams` / `whitelist_matrix` / `mapping_reconcile` / `db_checks` | 作为 `contract.global.json` 主结构（6 组基线） |

> **对齐判据**：命名/结构对齐为**静态可判定**（契约文件 diff）；各仓真实探活（端口/上游/db）为**联调窗口必需**（机制 1a）。

### 3.4 scripts 资产清单（S7 收口相关，实测）

| 脚本 | 用途 | S7 关联 |
|------|------|--------|
| `scripts/verify-env.ps1` | 环境自检原型（OB-9 / P2-1 T9） | S7-T1-1（全局化基线） |
| `scripts/verify-env/contract.json` / `snapshot.py` | 契约（6 组）/ 快照采集 | S7-T1-1 |
| `scripts/run_tests.ps1`（v1.4.2） | 单仓回归（分组子进程隔离 + ruff） | S7-T1-2（升跨仓入口） |
| `scripts/service-orchestrator.ps1` | 多系统服务编排唯一入口 | S7-T1-4 |
| `scripts/k07_endpoint_matrix.py` | K07 端点-过滤矩阵 | S7-T6-4 |
| `scripts/bypass_scan.py` / `scripts/audit_dps_code_map.py` | 静态扫描/映射审计 | S7-T1-4 / S7-T2-3（参照） |
| `scripts/run_regression.py` | 回归编排 | S7-T6（参照） |
| `scripts/gen_versions.py` / `build_release.ps1` / `deploy_pro.ps1` | 版本/发布/部署 | S7-T7/T8（提交面纪律参照） |

> **新增脚本落点**（本设计建议，见 §1.2）：`scripts/verify_env_global.ps1`、`scripts/verify-env/contract.global.json`、`scripts/db/init_openbase_test.ps1`、`scripts/db/grant_k13_accounts.ps1`、`scripts/scan_orchestrator_bypass.py`、`scripts/gate_aggregate.py`。

---

## 4. 逐任务设计（S7-T1~T8）

> 每任务给：**设计说明** / **文件落点** / **设计断言**（可执行判据 + 验收锚点 + 执行面）。执行面列：**A** = 沙箱可判定（静态/脚本/文档/OpenBase 仓操作）；**B** = 联调窗口必需（真实 PG/Redis、IdP/受信通道、四仓运行态、四仓写权限）；**A+B** = 双面（结构面沙箱可判定，真实面联调窗口）。断言 ID 与立项 §4 **1:1**。

### 4.1 S7-T1 SHR 五项收口（5 断言）

**设计说明**

1. **verify-env 全局化（Q-S7-D1/D2）**：新建跨仓统一契约 `scripts/verify-env/contract.global.json`（OpenBase 6 组为主结构 + `repo_overrides` 承载四仓契约键命名对齐）与单一全局入口 `scripts/verify_env_global.ps1`（`-Repos` 逐仓调度、汇总 exit 0/1/2）；**两段式收紧**（默认 WARN 非阻断 → `-FailFast`/`STRICT=1` 强校验），**回退开关保留**；`contract.json` 非破坏性保留。
2. **openbase_test + run_tests.ps1（Q-S7-D3）**：新建 `scripts/db/init_openbase_test.ps1`（建库/建账号/幂等迁移 `WHERE NOT EXISTS`/`create_all`），测试连接 `OPENBASE_DB_URL` → `openbase_test`（隔离业务库 `openbase`）；`run_tests.ps1` 保留 v1.4.2 单仓分组子进程隔离能力，**升为跨仓统一回归入口**（`-Repos` 编排 + 逐仓命令表）。当前 `grep openbase_test` 0 命中为该机制直接缺口。
3. **K13 存储账号分离（Q-S7-D4）**：新建 `doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md`（schema×账号×权限：`openbase` 应用账号 / `platform`（DPS 等）账号 / 迁移账号 / 运行时账号；各自仅授本 schema DML、不授 superuser）与 `scripts/db/grant_k13_accounts.ps1`（`GRANT` 收敛 + 打印模式干跑）；跨 schema 写 0 成功路径由 DB 级拒绝断言（真实 PG）。
4. **编排唯一入口（Q-S7-D5）**：以 `scripts/service-orchestrator.ps1` 为唯一入口，新增 `scripts/scan_orchestrator_bypass.py` 静态规则（禁 `taskkill`/`Stop-Process`/`kill -9` 批量杀；逆拓扑 stop 为唯一允许位），断言「无绕过路径」= 0 命中。
5. **文档地图（Q-S7-D6）**：地图正文落点 `doc/design/OpenBase-文档地图索引-v1.0.0.md`（L0-L4 全量：名称/版本/角色/状态/关联锚点），S1a~S7 纵切新增文档并入核对，判据「无游离文档」。

**文件落点**

| 类型 | 路径 | 动作 |
|------|------|------|
| 脚本 | `scripts/verify-env/contract.global.json`、`scripts/verify_env_global.ps1` | 新增 |
| 脚本 | `scripts/db/init_openbase_test.ps1`、`scripts/run_tests.ps1`（升级） | 新增 / 修改 |
| 文档+脚本 | `doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md`、`scripts/db/grant_k13_accounts.ps1` | 新增 |
| 脚本 | `scripts/scan_orchestrator_bypass.py` | 新增 |
| 文档 | `doc/design/OpenBase-文档地图索引-v1.0.0.md` | 新增 |
| 证据 | `doc/test/evidence/s7/shr/{verify-env-global,openbase-test,k13,orchestrator,doc-map}/` | 新增（PENDING 登记） |

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 | 执行面 |
|----|----------------------|---------|:---:|
| **S7-T1-1** | ① 跨仓统一契约文件存在且四仓 `repo_overrides` 键命名/结构与各仓 `verify-env` 对齐（OpenBase 6 组 + OpenLLM `identity_trust/REAL/channel/upstream` + OpenRAG/DPS `identity_trust/row_scope/identity_event/api` + OpenMemory 契约键）；② 单一全局入口 `verify_env_global.ps1` 存在且 `-SkipNetwork -SkipDb` 干跑产出报告（exit 0/1/2 语义清晰）；③ 两段式收紧（默认 WARN / `-FailFast` 强校验）+ 回退开关可回退；④ 真实探活按契约输出报告（**B 面未执行 → PENDING**） | `scripts/verify-env/contract.global.json` + `scripts/verify_env_global.ps1` 干跑输出；`doc/test/evidence/s7/shr/verify-env-global/`（含 `status`） | A+B |
| **S7-T1-2** | ① `scripts/db/init_openbase_test.ps1` 建库/建账号/幂等迁移脚本存在（`WHERE NOT EXISTS`/`create_all` 幂等可重放）；② 测试连接与业务库隔离（`OPENBASE_DB_URL` → `openbase_test`；不再连接 `openbase`）；③ `run_tests.ps1` 升为跨仓统一回归入口且保留单仓分组子进程隔离能力（结构干跑）；④ 真实建库与跨仓实跑（**B 面未执行 → PENDING**） | `init_openbase_test.ps1` 幂等干跑输出；`run_tests.ps1` 跨仓编排输出；`doc/.../openbase-test/` | A+B |
| **S7-T1-3** | ① 账号矩阵文件含 schema×账号×权限（`openbase`/`platform`/迁移/运行时四类账号，各自仅本 schema DML、不授 superuser）；② 授权脚本存在且打印模式干跑通过；③ **跨 schema 写 0 成功路径**（DB 级拒绝）；④ 运行账号无法 DDL；⑤ 真实 PG 授权与拒绝验证（**B 面未执行 → PENDING**） | K13 矩阵文件 + `grant_k13_accounts.ps1`；`doc/.../k13/`（跨 schema 写拒绝证据，真实面 PENDING） | B |
| **S7-T1-4** | ① 静态规则 `scan_orchestrator_bypass.py` 存在；② 扫描仓内批量杀路径（`taskkill`/`Stop-Process`/`kill -9`）= 0 命中（`service-orchestrator.ps1` 逆拓扑 stop 为唯一允许位）；③ 断言「无绕过的直接批量操作路径」；④ 编排实跑（**B 面未执行 → PENDING**） | `scan_orchestrator_bypass.py` 输出（0 命中）；`service-orchestrator.ps1` 入口清单；`doc/.../orchestrator/` | A+B |
| **S7-T1-5** | ① 文档地图索引 `doc/design/OpenBase-文档地图索引-v1.0.0.md` 存在，含 L0-L4 全量文档（名称/版本/角色/状态/关联锚点）；② S1a~S7 纵切新增文档（立项/设计/DevLog/测试/台账/清单）逐项并入核对；③ 判据「无游离文档」（各层文档均在索引内，差异 0 或登记）；④ 与 T8-3 一致 | 文档地图索引文件 + L0-L4 并入核对表；`doc/.../doc-map/` | A |

### 4.2 S7-T2 L1-1 级联全链核验（4 断言）

**设计说明**

1. **核验脚本设计**：新增 `scripts/verify_l1_1_cascade.ps1`（或 `.py`，Node/Python 零新依赖），分步执行并在 `doc/test/evidence/s7/l1-1/` 落证据 JSON（含 `status`/`event_id`/响应码/`request_id`/`openbase_commit`）。
2. **停用 → 数据面阻断**：真实停用主体 → ① **DPS 画像读阻断**（绑定失效 → 403/404，数据保留）；② **OpenMemory 记忆数据面阻断**（`sessions`/`memories` 访问拒绝，数据保留）；③ `event_id` 幂等（重放不双写，DB 行数不变）；④ `restored` 恢复解除阻断。
3. **Q-5=A 语义**：数据**保留 + 全链访问阻断**（login 拒绝 + 数据面级联阻断）；**无自动 purge 路径**（静态扫描 `scan_auto_purge` 0 命中 / 无 scheduler 定时 purge 注册）。
4. **purge 显式触发核验**：`POST /api/v1/identity/purge` → 非 deactivated 主体 **400**；未二次授权 **403**；授权后执行 → 物理清除 + `audit_logs` 留痕（`action=identity.purge`）。
5. 契约 = U1 §8 schema v1 + §8.4 S7 钩子；OpenBase 事件契约端点锚点 `0713ec1`。

**文件落点**：`scripts/verify_l1_1_cascade.ps1`（新增）、`doc/test/evidence/s7/l1-1/{dps-block.json,openmemory-block.json,event-idempotency.json,restore.json,purge.json,scan-auto-purge.txt}`、`doc/test/OpenBase-S7-…-测试报告-v1.0.0.md`（Step 3 产出）。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 | 执行面 |
|----|----------------------|---------|:---:|
| **S7-T2-1** | 真实停用主体 → **DPS 画像读阻断**（绑定失效 → 403/404，数据保留）；证据为真实执行结果（响应码 + `request_id`） | `doc/test/evidence/s7/l1-1/dps-block.json`（真实面 PENDING） | B |
| **S7-T2-2** | 真实停用主体 → **OpenMemory 记忆数据面阻断**（`sessions`/`memories` 访问拒绝，数据保留）；`event_id` 幂等（重放不双写、DB 行数不变） | `doc/test/evidence/s7/l1-1/openmemory-block.json` + `event-idempotency.json` | B |
| **S7-T2-3** | Q-5=A 语义：deactivated 数据**保留 + 全链访问阻断**（login 拒绝 + 数据面级联阻断）；**不存在「保留期到期自动清除」代码路径**（静态扫描 0 自动 purge） | `scan-auto-purge.txt`（0 命中）；`restore.json`（沙箱可判定静态面 + 真实面 PENDING） | A+B |
| **S7-T2-4** | purge 显式触发核验：非 deactivated 主体 purge → **400**；未二次授权 → **403**；授权后执行 → 物理清除 + `audit_logs` 留痕（`action=identity.purge`）；无 scheduler 定时 purge 注册 | `doc/test/evidence/s7/l1-1/purge.json`（400/403/审计留痕） | B |

### 4.3 S7-T3 L2-1 主备切换演练（4 断言）

**设计说明**

1. **演练脚本 + 报告模板 + 故障注入方式**：新增 `scripts/drill_l2_1_failover.ps1`（故障注入 = 停 B 上游进程/阻断 B 端口）与演练报告模板 `doc/test/evidence/s7/l2-1/drill-report.md`（场景/命令/切换前后路由/降级头/告警/回切条件/结论）。
2. **双场景**：`B 断 → A 接管`（A 直连接管 + 降级头/告警，业务不中断）；`A 断 → B 维持`（B 编排维持，业务不中断）。
3. **单主路径禁双写判定**：同一动作同一时刻仅一条主路径（S4-T7 `ChannelStateManager` 单主状态机），**无双主双写证据**；主路由配置声明、切换显式触发。
4. **边界**：事件通道不纳入演练矩阵（Q-S7-4）。

**文件落点**：`scripts/drill_l2_1_failover.ps1`（新增）、`doc/test/evidence/s7/l2-1/{drill-report.md,route-before.json,route-after.json,degrade-headers.json,alerts.json}`。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 | 执行面 |
|----|----------------------|---------|:---:|
| **S7-T3-1** | **B 断 → A 接管**（B 不可用时 A 直连接管，降级头/告警产生，业务不中断） | `doc/test/evidence/s7/l2-1/drill-report.md`（场景 1）+ `route-after.json` | B |
| **S7-T3-2** | **A 断 → B 维持**（A 不可用时 B 编排维持，业务不中断） | 同上（场景 2） | B |
| **S7-T3-3** | 单主路径：同一动作同一时刻仅一条主路径，**禁双主双写**（无双写证据） | `route-before/after.json` 单主断言 | B |
| **S7-T3-4** | 演练报告：场景/命令/切换前后路由/降级头/告警/回切条件/结论齐备；切换显式触发、主路由配置声明 | `drill-report.md` 字段齐备核对 | B |

### 4.4 S7-T4 L2-2 通道矩阵终验（4 断言）

**设计说明**

1. **矩阵终验表**：以 S4-T8 `matrix_rows` 为基座，终验「每子系统 × A/B × 状态/头语义」矩阵（新增 `doc/test/evidence/s7/l2-2/matrix-finalize.json`）。
2. **读路径**：B 主全绿 + A 备 covered（同一读请求经 A/B 返回一致、四头一致）；**管理面/探活 A 直连豁免行显式标注**（与 K07 端点矩阵 A 直连豁免行对账一致）。
3. **写路径等价 + K14 幂等**：写路径 A/B 等价用例绿；K14 幂等（重放不双写、DB 行数不变）。

**文件落点**：`doc/test/evidence/s7/l2-2/{matrix-finalize.json,read-path-ab-equivalence.json,write-path-equivalence.json,k14-idempotency.json}`。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 | 执行面 |
|----|----------------------|---------|:---:|
| **S7-T4-1** | 通道覆盖矩阵（每子系统 × A/B × 状态/头语义）**行全覆盖、缺口 0** | `matrix-finalize.json`（rows/covered/gap=0） | B |
| **S7-T4-2** | 管理面/探活 **A 直连豁免行显式标注**（与 K07 端点矩阵 A 直连豁免行对账一致） | `matrix-finalize.json`（豁免行标注） | B |
| **S7-T4-3** | 读路径：**B 主全绿 + A 备 covered**（同一读请求经 A/B 返回一致、四头一致） | `read-path-ab-equivalence.json` | B |
| **S7-T4-4** | 写路径 A/B 等价用例绿 + **K14 幂等**（重放不双写、DB 行数不变）终验 | `write-path-equivalence.json` + `k14-idempotency.json` | B |

### 4.5 S7-T5 L3-1 Agent 端到端（4 断言）

**设计说明**

1. **用例矩阵 ≥3 例/系统**：新增 `scripts/verify_l3_1_agent.ps1`（或 `.py`），对 DPS / OpenLLM / OpenRAG / OpenMemory 每系统 ≥3 例（白名单放行 / 非白名单 403 / 跨域隔离）。
2. **agent key → 四头一致**：`sk-agent-*` 发放/使用 → `X-User-ID`/`X-Tenant-ID`/`X-User-Role`/`X-Proxy-Source` 齐全且与主体一致；**agent 无交互登录路径（0 可达）**。
3. **未授权 403 + M1/M2 分别断言**：非白名单携带身份头全链路 403（`PERM_UNTRUSTED_IDENTITY_HEADER`，无绕过端点）；M1 独立模式（本地 service key 自身认证）与 M2 受信头采纳分别通过。

**文件落点**：`scripts/verify_l3_1_agent.ps1`（新增）、`doc/test/evidence/s7/l3-1/{agent-key-issuance.json,system-whitelist-cases.json,domain-isolation.json,unauthorized-403.json,m1-m2.json}`。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 | 执行面 |
|----|----------------------|---------|:---:|
| **S7-T5-1** | agent key（`sk-agent-*`）发放/使用 → **四头齐全且与主体一致**；agent 无交互登录路径（0 可达） | `agent-key-issuance.json`（四头一致性 + 无登录路径） | B |
| **S7-T5-2** | **各系统白名单**放行（受信来源 + 头 = 信任；每系统 ≥3 例矩阵）；非白名单携带身份头全链路 **403**（无绕过端点） | `system-whitelist-cases.json`（≥3 例/系统） | B |
| **S7-T5-3** | **域隔离**——跨域不可见（404/403/空），跨域同名并存互不可见 | `domain-isolation.json` | B |
| **S7-T5-4** | **未授权 403**（`PERM_UNTRUSTED_IDENTITY_HEADER`）；M1 独立模式（service key 自身认证）与 M2 受信头采纳分别通过 | `unauthorized-403.json` + `m1-m2.json` | B |

### 4.6 S7-T6 RA-06 + 冒烟 S0-S6 聚合 + 存量测试对齐清单关闭（4 断言）

**设计说明**

1. **门禁聚合脚本（Q-S7-D7）**：新增 `scripts/gate_aggregate.py`（单命令/单批），聚合 ① RA-06 五项 ② 冒烟 S0-S6 ③ 对齐清单关闭 ④ K07/SYS-1 矩阵终验；输出 `doc/test/evidence/s7/gate/gate-aggregate.json`（分项 `status`/`evidence_path`/`openbase_commit`/`execution_face`/`reason`），失败项如实登记不伪造。
2. **RA-06 五项**：双租户隔离回归 / fail-closed / OIDC 批次隔离（存量 T2 归档关闭）/ 委托跨界 403 / 吊销即时性——**单命令/单批聚合全绿**，覆盖率 ≥90%。
3. **冒烟 S0-S6**：按冒烟清单 v1.1.0 §3 用例矩阵执行（P0 全绿、P1 登记）。
4. **对齐清单关闭**：存量对齐清单状态升版（[Draft]→[Approved]/[Final]）+ 分批门禁复跑（OIDC 独立批次 12 例绿 + 主批次 0 失败）+ S6 登记的 asyncpg/PG 4 项环境性失败随 PG 就绪复跑关闭。
5. **K07/SYS-1 终验**：端点-过滤矩阵缺口清零、未覆盖清零；豁免全部在有效期且有审批；新增端点无隔离用例不放行。

**文件落点**：`scripts/gate_aggregate.py`（新增）、`doc/test/evidence/s7/gate/gate-aggregate.json`、`OpenBase-存量测试对齐任务清单-v1.0.0.md`（状态升版）、`doc/test/OpenBase-S7-…-测试报告-v1.0.0.md`。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 | 执行面 |
|----|----------------------|---------|:---:|
| **S7-T6-1** | RA-06 聚合五项（双租户隔离回归 / fail-closed / OIDC 批次隔离（存量 T2 归档关闭）/ 委托跨界 403 / 吊销即时性）**单命令/单批聚合全绿**，覆盖率 ≥90% | `gate-aggregate.json`（RA-06 分项）；`scripts/gate_aggregate.py` 输出 | A+B |
| **S7-T6-2** | 冒烟 S0-S6 聚合：按冒烟清单 v1.1.0 §3 用例矩阵执行，**P0 全绿**、P1 项登记完成 | `gate-aggregate.json`（冒烟分项，真实面 PENDING） | B |
| **S7-T6-3** | 存量测试对齐清单**关闭**：状态升版（[Draft]→[Approved]/[Final]）+ 分批门禁复跑（OIDC 独立批次 12 例绿 + 主批次 0 失败）+ asyncpg/PG 4 项环境性失败随 PG 就绪复跑关闭（登记清单为空或仅剩业务缺陷项） | 对齐清单修订历史升版条目 + 复跑记录 | A+B |
| **S7-T6-4** | K07 + SYS-1 端点-过滤矩阵**终验**：矩阵缺口清零、未覆盖清零；豁免全部在有效期且有审批；新增端点无隔离用例不放行 | `gate-aggregate.json`（K07/SYS-1 分项） | B |

### 4.7 S7-T7 跨仓入仓核验与会签（4 断言）

**设计说明**

1. **以执行件模板为执行依据**：`doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md`（commit `72db715`）——前置裁断 → 分批入仓 → hash 回填 → 勾稽会签四步。
2. **OpenBase 侧汇总核对脚本/表（Q-S7-D10）**：新增 `doc/planning/OpenBase-S7-跨仓入仓与会签-OpenBase汇总核对表-v1.0.0.md`（四仓 commit hash 汇总 + 逐仓 A 类差异回读 + 会签五步结论）；沙箱内可产出结构，四仓命令沙箱外执行。
3. **清单升版**：放行清单（v1.0.8 → [Approved]）与清点总清单（v1.0.5 → [Approved]）登记，遵循文档版本管理规范。

**文件落点**：执行件模板（引用）、`doc/planning/OpenBase-S7-跨仓入仓与会签-OpenBase汇总核对表-v1.0.0.md`（新增）、放行清单 / 清点总清单（升版）、`doc/test/evidence/s7/signoff/`。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 | 执行面 |
|----|----------------------|---------|:---:|
| **S7-T7-1** | 四仓入仓完成，**实 hash 回填**各仓 JT 台账与任务卡卡尾（OpenMemory v1.4.0 / OpenRAG v1.5.0 / OpenLLM v1.6.0 / DPS JT 台账 + S5 卡尾）；**hash 一律不得伪造**（受限则如实登记 `PENDING`） | 执行件 §5 hash 回填表 + 台账/卡尾回填（真实面 PENDING） | B |
| **S7-T7-2** | 四仓清单勾稽：以清点总清单 §1.1 为基准逐仓回读 `git status --porcelain -uall`，**A 类差异 = 0**（仅剩 B 类隔离 + C 类噪音 + 清单文档自身） | 执行件 §4 勾稽核对表 + 逐仓回读记录 | B |
| **S7-T7-3** | 跨仓会签记录形成（总清单 §4.1 五步流程），四仓 hash 汇总 + 跨系统卡（K02/K07/K13）完成情况与接口一致性评审 | 汇总核对表 + 会签记录（五步结论/证据/会签人/日期） | A+B |
| **S7-T7-4** | 放行清单（v1.0.8 → [Approved]）与清点总清单（v1.0.5 → [Approved]）升版登记，遵循文档版本管理规范 | 两份清单升版后的修订历史条目 | A |

### 4.8 S7-T8 24 卡/JT 台账全量回写 + 文档地图维护 + 总收官报告（5 断言）

**设计说明**

1. **24 卡回写表**：任务卡（内部 v1.7.0）K01-K18 + RA-01~RA-06 状态全量回写（含 S0~S6 回写后当前状态与 S7 终验结论），以回写表形式登记。
2. **七线 JT 台账回写**：OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS / 前端 / SHR 七条 JT 线状态与提交号全量回写归集文档 §3。
3. **文档地图维护**：与 S7-T1-5 一致（`doc/design/OpenBase-文档地图索引-v1.0.0.md`）。
4. **总收官报告（Q-S7-D9）**：`doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md`（段门禁六项聚合结论 + PENDING 挂起登记 + 跨仓会签记录 + 遗留事项；结论如实，未执行项 PENDING）。
5. **六项聚合自检**：① RA-06 ② 冒烟 S0-S6 ③ 对齐清单关闭 ④ 三原则总验证 ⑤ 跨仓会签 ⑥ 24 卡/JT 回写——逐项登记结论与证据索引。

**文件落点**：`OpenBase-数据隔离实现任务卡-v1.0.0.md`（24 卡回写）、JT 归集文档 §3（七线回写）、`doc/design/OpenBase-文档地图索引-v1.0.0.md`、`doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md`。

**设计断言**

| ID | 设计断言（可执行判据） | 验收锚点 | 执行面 |
|----|----------------------|---------|:---:|
| **S7-T8-1** | 任务卡 **24 卡**（K01-K18 + RA-01~RA-06）状态**全量回写**（含 S0~S6 回写后当前状态与 S7 终验结论） | 任务卡回写表（24 行齐备） | A |
| **S7-T8-2** | JT 台账**七线**（OpenBase / OpenLLM / OpenRAG / OpenMemory / DPS / 前端 / SHR）状态与提交号**全量回写**归集文档 §3 | 归集文档 §3 七行齐备 + 提交号 | A |
| **S7-T8-3** | 文档地图 L0-L4 索引维护到位（与 S7-T1-5 一致） | `doc/design/OpenBase-文档地图索引-v1.0.0.md` | A |
| **S7-T8-4** | 《S7-全域门禁与总收官报告》产出：段门禁六项聚合结论、PENDING 挂起登记、跨仓会签记录、遗留事项（结论如实，未执行项 PENDING） | `doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md` | A+B |
| **S7-T8-5** | 段门禁六项聚合自检：① RA-06 ② 冒烟 S0-S6 ③ 对齐清单关闭 ④ 三原则总验证 ⑤ 跨仓会签 ⑥ 24 卡/JT 回写——逐项登记结论与证据索引 | 报告「六项聚合自检表」+ `gate-aggregate.json` 引用 | A+B |

### 4.9 断言汇总表（34 条，与立项 §4 1:1）

| 任务 | 断言 ID 区间 | 条数 | 执行面分布 | 主要落点 |
|------|-------------|:---:|:---:|---------|
| S7-T1 SHR 五项收口 | S7-T1-1 ~ S7-T1-5 | 5 | A+B×3（T1-1/2/4）、B×1（T1-3）、A×1（T1-5） | `scripts/verify-env/**`、`scripts/db/**`、`scripts/scan_orchestrator_bypass.py`、`doc/design/OpenBase-文档地图索引-v1.0.0.md` |
| S7-T2 L1-1 级联 | S7-T2-1 ~ S7-T2-4 | 4 | B×3（T2-1/2/4）、A+B×1（T2-3） | `scripts/verify_l1_1_cascade.ps1`、`doc/test/evidence/s7/l1-1/**` |
| S7-T3 L2-1 演练 | S7-T3-1 ~ S7-T3-4 | 4 | B×4 | `scripts/drill_l2_1_failover.ps1`、`doc/test/evidence/s7/l2-1/**` |
| S7-T4 L2-2 终验 | S7-T4-1 ~ S7-T4-4 | 4 | B×4 | `doc/test/evidence/s7/l2-2/**` |
| S7-T5 L3-1 Agent | S7-T5-1 ~ S7-T5-4 | 4 | B×4 | `scripts/verify_l3_1_agent.ps1`、`doc/test/evidence/s7/l3-1/**` |
| S7-T6 门禁聚合 | S7-T6-1 ~ S7-T6-4 | 4 | A+B×2（T6-1/3）、B×2（T6-2/4） | `scripts/gate_aggregate.py`、`doc/test/evidence/s7/gate/**`、存量对齐清单 |
| S7-T7 入仓会签 | S7-T7-1 ~ S7-T7-4 | 4 | B×2（T7-1/2）、A+B×1（T7-3）、A×1（T7-4） | 执行件模板、会签汇总核对表、放行/清点清单 |
| S7-T8 回写收官 | S7-T8-1 ~ S7-T8-5 | 5 | A×3（T8-1/2/3）、A+B×2（T8-4/5） | 任务卡、归集文档 §3、文档地图、总收官报告 |
| **合计** | — | **34** | **A 5 / A+B 9 / B 20** | — |

> **执行面分布核对**：A **5** 条（S7-T1-5、S7-T7-4、S7-T8-1/2/3）；A+B **9** 条（S7-T1-1/2/4、S7-T2-3、S7-T6-1/3、S7-T7-3、S7-T8-4/5）；B **20** 条（S7-T1-3、S7-T2-1/2/4、S7-T3-1~4、S7-T4-1~4、S7-T5-1~4、S7-T6-2/4、S7-T7-1/2）——与立项 §4 尾注**完全一致**。**B 面未真实执行项一律 PENDING 登记，禁伪造。**

---

## 5. 证据与报告规范

### 5.1 evidence 目录结构（`doc/test/evidence/s7/**`，Q-S7-D8）

```
doc/test/evidence/s7/
├─ shr/                        # S7-T1 SHR 五项收口
│  ├─ verify-env-global/       # contract.global.json 对账 + 全局入口干跑 + 真实探活
│  ├─ openbase-test/           # 建库/建账号/幂等迁移 + 隔离
│  ├─ k13/                     # 账号矩阵 + 跨 schema 写拒绝
│  ├─ orchestrator/            # 唯一入口 + 禁批量杀静态扫描
│  └─ doc-map/                 # L0-L4 索引 + S1a~S7 并入核对
├─ l1-1/                       # S7-T2：dps-block / openmemory-block / event-idempotency / restore / purge / scan-auto-purge
├─ l2-1/                       # S7-T3：drill-report / route-before / route-after / degrade-headers / alerts
├─ l2-2/                       # S7-T4：matrix-finalize / read-path-ab-equivalence / write-path-equivalence / k14-idempotency
├─ l3-1/                       # S7-T5：agent-key-issuance / system-whitelist-cases / domain-isolation / unauthorized-403 / m1-m2
├─ gate/                       # S7-T6：gate-aggregate.json（RA-06/冒烟/对齐清单/K07-SYS-1 分项）
└─ signoff/                    # S7-T7：四仓 hash 汇总 + 勾稽回读 + 会签记录
```

### 5.2 evidence JSON 字段规范

每个证据 JSON **至少**含：`schema_version`、`status`（`PASS`/`PENDING`/`FAIL`）、`reason`（`PENDING`/`FAIL` 必填）、`execution_face`（`A`/`A+B`/`B`）、`openbase_commit`、`checked_at`、`evidence_ref`（关联断言 ID）。未执行项写 `status=PENDING` + `reason`（前置、环境、责任方），**不写假 hash、不写假响应码**。

### 5.3 PENDING 登记规范（对齐 S5/S6 挂起口径范式）

| 项 | 规范 |
|----|------|
| 登记时机 | B 面未在沙箱/受控环境真实执行时立即登记（不推迟、不省略） |
| 必填字段 | 断言 ID / 事项 / 前置条件 / 责任方 / 环境待办 / 复核动作 |
| 影响判定 | **非阻断项**：挂起登记**不阻断**批准（对齐 S5/S6）；**阻断项**：如存在，须回溯 S7 段门禁 |
| 关闭方式 | 联调窗口执行后逐条回填证据（`status=PENDING → PASS/FAIL`），并回写证据 JSON 与测试报告 |

### 5.4 禁伪造口径（硬纪律）

1. **禁伪造通过**：未执行不得填 `PASS`；不得以「预期通过」代替证据。
2. **禁伪造 hash**：四仓 commit hash 与 S7 段提交号一律真实；沙箱受限则登记「沙箱受限未执行/未提交」。
3. **禁伪造证据**：不得编造响应码、`request_id`、截图、报告。
4. **归属可解释**：任一 PENDING/FAIL 项须可归入「B 面未执行 / 业务缺陷 / 环境待办」之一；不可解释者登记为遗留并交收口评审。

### 5.5 报告落点

| 报告 | 落点 | 产出步 |
|------|------|-------|
| DevLogReport | `doc/development/OpenBase-S7-全域门禁与总收官-DevLogReport-v1.0.0.md` | Step 2 开发 |
| 测试报告 | `doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md` | Step 3 测试 |
| 总收官报告 | `doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md` | Step 4 部署与收官 |

---

## 6. 迁移与兼容

### 6.1 verify-env 收紧的兼容面（两段式 + 回退开关）

| 项 | 现行（实测） | S7 目标 | 回滚方式 |
|----|-------------|--------|---------|
| 契约 | `contract.json`（6 组，WARN 非阻断） | 新增 `contract.global.json`（主结构 + `repo_overrides`），`contract.json` 保留 | 删除新增文件即回退（非破坏性） |
| 入口 | `verify-env.ps1`（单仓） | 新增 `verify_env_global.ps1`（跨仓调度），单仓入口保留 | 停用全局入口即回退 |
| 语义 | 默认 WARN 非阻断（exit 0/1） | **两段式**：默认 WARN 非阻断 → `-FailFast`/`STRICT=1` 强校验（WARN→1、ERROR→2） | 取消 `-FailFast`/置 `STRICT=0` 即回退非阻断 |

### 6.2 脚本回滚与兼容

- **openbase_test**：新增独立库与脚本；**测试连接隔离**（`OPENBASE_DB_URL`）对业务库零影响；回滚 = 停用独立库、连接指回（无数据迁移）。
- **K13 账号矩阵**：授权收敛为增量（账号分离/仅本 schema DML）；回滚 = 还原授权（不涉及数据迁移）。
- **编排唯一入口**：静态规则为**只读扫描**，不改编排脚本功能；回滚 = 停用规则。
- **run_tests.ps1**：保留 v1.4.2 单仓能力为基座，新增跨仓编排为增量；回滚 = 不传 `-Repos`（退化为单仓）。

### 6.3 四仓仅入仓不改语义

- 四仓**仅执行既有产物的入仓（提交）与 hash 回填**；**不改各子系统功能语义、不做新功能开发**（立项 §5）。
- **B 类须隔离、C 类排除、敏感文件（`.env*` / `data/edge_tokens.jsonl` 等）零进入提交面**；OpenRAG `repository` gitlink 禁 `git add`；OpenLLM 4 个混合文件须 `git add -p` 拆分（执行件模板 §3 红线）。
- 四仓回归失败即停止后续批次（放行清单 §0）。

---

## 7. 风险

> 承接立项 §7 R-1~R-8，并补充设计级风险 R-D1~R-D5。

| # | 风险/依赖 | 类型 | 影响 | 缓解/说明（设计层） |
|---|----------|------|------|-------------------|
| R-1 | **真实环境可用性**：真实 PG/Redis、IdP/受信通道、四仓运行态不可达 | 依赖 | S7-T2~T6 大面积断言无法在沙箱内完成 | 按挂起口径 PENDING 登记（对齐 S5/S6 范式），环境就绪后回填；**禁以「预期通过」代替证据** |
| R-2 | **演练窗口**：L2-1 主备切换演练需可注故障的运行态与切换窗口 | 依赖 | S7-T3/S7-T4 阻塞 | 受控联调窗口排期；演练脚本与矩阵基线复用 S4-T7/T8 产出 |
| R-3 | **会签时序**：四仓入仓 → hash 回填 → 勾稽 → 会签须按序完成 | 流程 | S7-T7 与段门禁 | 严格按清点总清单 §4.1 五步流程；每仓回归失败即停 |
| R-4 | **各仓入仓进度**：四仓 A 类 264 项、23 项需人工判定、7 项边界确认未裁定 | 依赖 | 入仓与勾稽延后 | 会签前完成裁断；OpenLLM 4 混合文件 `git add -p`；need-star 独立隔离批 |
| R-5 | **沙箱限制**：仅可操作 OpenBase 仓，无四仓写权限、无浏览器/PG/IdP | 约束 | B 面断言不可自动执行 | 四仓与真实面由用户在沙箱外执行，结果如实登记（S7-T7-1/S7-T8-4） |
| R-6 | **K13 与编排入口无现成基线** | 技术 | S7-T1-3/T1-4 需从零收口 | 以任务卡 K13 步骤与复盘 L7 约束为准；真实 PG 验证 |
| R-7 | **verify-env 收紧的兼容面**：WARN→fail-fast 可能阻断启动 | 技术 | 影响既有部署 | 两段式发布 + 开关回退（§6.1） |
| R-8 | **PENDING 挂起累积**：段级 10 条主挂起项集中到 S7 后段 | 进度 | 收官周期拉长 | 联调窗口一次性复核（S2~S6 双签 + S6 B1~B6）；按需分批回填，不阻断已达成项 |
| R-D1 | **跨仓契约键命名不一致**（各仓 `verify-env` 键名/结构各异） | 技术 | S7-T1-1 结构对齐可能超预期 | 以立项 §2.3 实测键名为基线；对齐仅做命名/结构映射，不改各仓语义（Q-S7-D1） |
| R-D2 | **openbase_test 首次建立**：无现成建库脚本，测试族可能隐式依赖业务库 | 技术 | S7-T1-2 建库/隔离超出预期 | 幂等迁移 + 连接隔离；先建库后切连接；隐式依赖按 TDD 逐步暴露 |
| R-D3 | **L1-1 级联真实停用影响共享环境** | 操作 | 停用真实主体可能污染联调环境 | 使用**专用冒烟主体**（`smoke_l1_1_*`）；执行后恢复（`restored`）；不触碰生产主体 |
| R-D4 | **门禁聚合脚本口径漂移**（分项与上游清单口径不一致） | 流程 | S7-T6 结论可信度 | 分项口径对齐 RA-06/冒烟 v1.1.0/对齐清单 v1.2.0；聚合 JSON 保留各分项证据路径可回溯 |
| R-D5 | **evidence 与台账回写真实性依赖人工复核** | 流程 | 可能产出无证据 PASS | evidence JSON 强制字段（§5.2）+「结论 + 证据路径 + 执行面」三列齐备；无证据不得填 PASS |

---

## 8. 边界

| 边界项 | 说明 | 归属 |
|--------|------|------|
| 各子系统功能语义 | **不改** DPS/OpenLLM/OpenMemory/OpenRAG 的功能语义与数据面实现；四仓仅执行既有产物的**入仓（提交）**与 hash 回填 | 各子系统仓 |
| 新功能开发 | S7 **不做新功能开发**；SHR/门禁聚合仅收口既有能力 | S7（SHR 面） |
| 统一身份/协议头实现 | U1/P2-1 已落地（S1a/S1b）；S7 仅**消费与终验**，不重复实现 | S1a/S1b |
| L3-2 段门禁贯通冒烟 | S2-S6 每段已完成（契约桩面绿；真实双签 PENDING）；S7 承接真实窗口复核，不重做段门禁设计 | S2-S6 |
| 事件通道主备 | 事件通道（L1-1 身份权威同步面）**不纳入** S7 主备切换演练矩阵（Q-S7-4，放行清单 §6-4） | S7（边界声明） |
| 各子系统独立前端 | 各仓 `frontend/` 已冻结；B5 物理改造与 CI 收敛由各子系统仓执行、S7 复核（Q-S6-D7） | 各子系统仓 / S7 复核 |
| 存放与提交边界 | S7 提交面仅 OpenBase 仓（仓根/`doc/**`/`scripts/**`/`openbase-ui/**` 复核面 + `doc/test/evidence/s7/**`）；**不得纳入 `dogfood-output/`**；四仓命令沙箱外执行 | S7 |

---

## 9. 里程碑（五步流程衔接）

| 步骤 | 交付物 | 与上一步对比（连续审计） | 门禁 |
|------|--------|------------------------|------|
| Step 0 / 需求 | 立项方案（内部 **v1.1.0**，[Approved]，2026-09-11 批准；Q-S7-1~8 定案） | 回溯规划 v1.3.1 S7 段定义、归集 v1.3.0 §3.8/§4-5、任务卡 v1.7.0，覆盖无遗漏 | ✅ 已批准（人工） |
| **Step 1 / 设计（本文档）** | 《S7-全域门禁与总收官-设计草案 v1.0.0》（[Draft]） | 与需求 34 条断言 1:1 对应（§1.3 覆盖矩阵）；Q-S7-1~8 定案逐条落到设计条目（§1.1） | 设计评审人工批准（本草案） |
| Step 2 / 开发 | 《S7-…-DevLogReport v1.0.0》（SHR 脚本收口 + 门禁聚合脚本 + 会签/报告文档；含源码清单与改动行号） | 与本文档逐条对应（实现一致；RED→GREEN 记录）；遵循 AGENTS.md | 静态检查（`ruff` 0 错误）/ 单测 |
| Step 3 / 测试 | 《S7-…-测试报告 v1.0.0》（34 断言逐条状态 + B 面 PENDING 登记 + 证据索引） | 回溯需求（34 断言）、设计（落点）、执行面（A/A+B/B）对比，确保覆盖 | 测试回溯对比人工批准 |
| Step 4 / 部署与收官 | 跨仓入仓核验 + 会签记录 + 24 卡/JT 台账回写 + 《S7-全域门禁与总收官报告》 | 与测试报告对比验证（结论一致）；总收官报告聚合段门禁六项 | **S7 段门禁批准**（门禁聚合六项全绿 + 无阻断遗留） |

**任务间依赖**：T1（SHR 收口）→ {T2 ∥ T3 ∥ T4 ∥ T5}（联调窗口）→ T6（门禁聚合，依赖 T2~T5 结论 + T1 收口）→ T7（会签，依赖四仓入仓 + T1~T6）→ T8（台账回写 + 报告，依赖 T1~T7）。

**S7 段门禁（收官判定）**：**门禁聚合六项全绿**——① RA-06 聚合全绿；② 冒烟 S0-S6 聚合全绿；③ 存量测试对齐清单关闭；④ 三原则总验证（L1-1 / L2-1 / L2-2 / L3-1）通过；⑤ 跨仓会签完成；⑥ 24 卡/JT 台账全量回写——并配套跨仓入仓核验（S7-T7）与总收官报告（S7-T8-4/5）。**非阻断项按挂起口径 PENDING 登记**（对齐 S5/S6 范式），遗留=无阻断项。

**交付物清单（本段）**：立项方案 v1.1.0；本设计草案 v1.0.0；DevLogReport v1.0.0；测试报告 v1.0.0；门禁聚合证据与 `doc/test/evidence/s7/**`；会签记录（执行件模板 + OpenBase 汇总核对表）；《S7-全域门禁与总收官报告》；任务卡 24 卡与 JT 台账回写；文档地图维护。

---

## 10. 遗留与设计级定案登记

### 10.1 已定案（不再重议，引用 §1.1）

| # | 结论摘要 | 状态 |
|---|---------|------|
| Q-S7-1 | 各仓入仓与会签闭环口径（沙箱外执行 + hash 回填 + 四仓勾稽 + 会签） | ✅ 已定案（2026-09-11 立项评审） |
| Q-S7-2 | B1~B6 非沙箱回填与验收口径（B5 各子系统仓执行、S7 复核） | ✅ 已定案 |
| Q-S7-3 | L1-1 级联全链核验（含 purge 显式触发、Q-5=A） | ✅ 已定案 |
| Q-S7-4 | L2-1 演练口径（双场景 + 单主禁双写 + 演练报告；事件通道不纳入矩阵） | ✅ 已定案 |
| Q-S7-5 | L2-2 终验口径（矩阵终验 + 写路径等价 + K14 幂等） | ✅ 已定案 |
| Q-S7-6 | L3-1 Agent 端到端口径（四头/白名单/域隔离/未授权 403；M1/M2 分别断言） | ✅ 已定案 |
| Q-S7-7 | RA-06 与冒烟 S0-S6 聚合与对齐清单关闭判定 | ✅ 已定案 |
| Q-S7-8 | 24 卡/JT 台账全量回写与收官报告形态（置 `doc/development/`） | ✅ 已定案 |

### 10.2 遗留待评审问题（设计级，须设计评审裁定）

> **[已裁定 2026-09-11]** 下列 Q-S7-D1~D10 于 2026-09-11 设计评审**按建议定案登记**（随状态 [Approved] 生效），不再作为待评审遗留项。

| # | 问题 | 建议 | 阻塞面 |
|---|------|------|--------|
| Q-S7-D1 | verify-env 全局契约落点：新建 `contract.global.json` 还是扩展现行 `contract.json` | 建议**新建 `contract.global.json`**（主结构 + `repo_overrides`），`contract.json` 非破坏性保留 | S7-T1-1 |
| Q-S7-D2 | verify-env 强校验默认态：`-FailFast` 是否在 S7 后段设为默认 | 建议**两段式**（默认 WARN；强校验显式开启），避免阻断既有部署 | S7-T1-1 |
| Q-S7-D3 | `openbase_test` 形态：独立 PG 库 vs 同库独立 schema | 建议**独立库 `openbase_test`**（隔离最彻底）；如环境受限，退化为独立 schema 并在报告中登记 | S7-T1-2 |
| Q-S7-D4 | K13 账号粒度：`platform` 是否按子系统再细分账号 | 建议**先按 `openbase`/`platform` 两类落地**，子系统细分列后续项（不阻塞 S7） | S7-T1-3 |
| Q-S7-D5 | 编排唯一入口：是否需将 `deploy_pro.ps1` 等亦纳入唯一入口约束 | 建议**本次仅约束服务生命周期编排**（service-orchestrator）；发布/部署脚本列后续 | S7-T1-4 |
| Q-S7-D6 | 文档地图落点：独立索引文件 vs 复盘方案内章节 | 建议**独立 `doc/design/OpenBase-文档地图索引-v1.0.0.md`** + 复盘方案引用（单一事实源，便于维护） | S7-T1-5、S7-T8-3 |
| Q-S7-D7 | 门禁聚合脚本语言：Python vs PowerShell | 建议 **Python**（`scripts/gate_aggregate.py`，便于 JSON 处理与跨平台） | S7-T6 |
| Q-S7-D8 | L1-1 核验主体命名与清理策略 | 建议**专用冒烟主体**（`smoke_l1_1_*`），执行后 `restored`，不触碰生产主体 | S7-T2（R-D3） |
| Q-S7-D9 | 收官报告是否单文件 vs 主报告 + 附录目录 | 建议**单文件主报告**（`doc/development/`）+ evidence 目录引用（避免文件膨胀） | S7-T8-4 |
| Q-S7-D10 | 会签汇总表落点：`doc/planning/` vs `doc/development/` | 建议 `doc/planning/`（与执行件模板同目录，便于成套查阅） | S7-T7-3 |

### 10.3 设计评审必须核对项（Checklist）

1. §1.3 覆盖矩阵：34 条断言是否 1:1（无新增/无遗漏，执行面分布 A 5 / A+B 9 / B 20 与立项一致）；
2. §1.1 Q-S7-1~8 定案是否与立项 v1.1.0 定案一致；§1.2 十条设计级补充定案（Q-S7-D1~D10）是否被接受；
3. §1.4「沙箱可判定面 / 联调窗口必需面」清单是否被接受为 S7 证据口径基线；
4. §5.4「禁伪造口径」与 §5.3 PENDING 登记规范是否作为硬纪律；
5. §6.1 verify-env 两段式 + 回退开关是否满足兼容与可回滚要求；
6. §10.2 十项设计级遗留是否需在设计评审当次裁定（Q-S7-D1~D10）。

---

## 附录

### 附录 A：34 条断言 → 落点 → 证据 → 执行面 索引

| 断言 | 主要落点 | 证据落点 | 执行面 |
|------|---------|---------|:---:|
| S7-T1-1 | `scripts/verify-env/contract.global.json`、`scripts/verify_env_global.ps1` | `doc/test/evidence/s7/shr/verify-env-global/` | A+B |
| S7-T1-2 | `scripts/db/init_openbase_test.ps1`、`scripts/run_tests.ps1` | `doc/test/evidence/s7/shr/openbase-test/` | A+B |
| S7-T1-3 | `doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md`、`scripts/db/grant_k13_accounts.ps1` | `doc/test/evidence/s7/shr/k13/` | B |
| S7-T1-4 | `scripts/scan_orchestrator_bypass.py`、`scripts/service-orchestrator.ps1` | `doc/test/evidence/s7/shr/orchestrator/` | A+B |
| S7-T1-5 | `doc/design/OpenBase-文档地图索引-v1.0.0.md` | `doc/test/evidence/s7/shr/doc-map/` | A |
| S7-T2-1 | `scripts/verify_l1_1_cascade.ps1` | `doc/test/evidence/s7/l1-1/dps-block.json` | B |
| S7-T2-2 | 同上 | `doc/test/evidence/s7/l1-1/{openmemory-block,event-idempotency}.json` | B |
| S7-T2-3 | 同上 + `scan_auto_purge` | `doc/test/evidence/s7/l1-1/{restore.json,scan-auto-purge.txt}` | A+B |
| S7-T2-4 | 同上（purge 端点） | `doc/test/evidence/s7/l1-1/purge.json` | B |
| S7-T3-1 | `scripts/drill_l2_1_failover.ps1` | `doc/test/evidence/s7/l2-1/drill-report.md`（场景 1） | B |
| S7-T3-2 | 同上 | 同上（场景 2） | B |
| S7-T3-3 | 同上 + `ChannelStateManager` 单主断言 | `doc/test/evidence/s7/l2-1/{route-before,route-after}.json` | B |
| S7-T3-4 | 演练报告模板 | `doc/test/evidence/s7/l2-1/drill-report.md` | B |
| S7-T4-1 | S4-T8 `matrix_rows` 基座 | `doc/test/evidence/s7/l2-2/matrix-finalize.json` | B |
| S7-T4-2 | 同上 + K07 豁免行对账 | `doc/test/evidence/s7/l2-2/matrix-finalize.json` | B |
| S7-T4-3 | 同上 | `doc/test/evidence/s7/l2-2/read-path-ab-equivalence.json` | B |
| S7-T4-4 | 同上 | `doc/test/evidence/s7/l2-2/{write-path-equivalence,k14-idempotency}.json` | B |
| S7-T5-1 | `scripts/verify_l3_1_agent.ps1` | `doc/test/evidence/s7/l3-1/agent-key-issuance.json` | B |
| S7-T5-2 | 同上 | `doc/test/evidence/s7/l3-1/system-whitelist-cases.json` | B |
| S7-T5-3 | 同上 | `doc/test/evidence/s7/l3-1/domain-isolation.json` | B |
| S7-T5-4 | 同上 | `doc/test/evidence/s7/l3-1/{unauthorized-403,m1-m2}.json` | B |
| S7-T6-1 | `scripts/gate_aggregate.py` | `doc/test/evidence/s7/gate/gate-aggregate.json`（RA-06） | A+B |
| S7-T6-2 | 同上（冒烟清单 v1.1.0） | `doc/test/evidence/s7/gate/gate-aggregate.json`（冒烟） | B |
| S7-T6-3 | 同上 + 存量对齐清单状态升版 | `doc/test/evidence/s7/gate/gate-aggregate.json`（对齐清单） | A+B |
| S7-T6-4 | 同上 + `scripts/k07_endpoint_matrix.py` | `doc/test/evidence/s7/gate/gate-aggregate.json`（K07/SYS-1） | B |
| S7-T7-1 | 执行件模板 §5 + 各仓 JT 台账/卡尾 | `doc/test/evidence/s7/signoff/`（hash 清单） | B |
| S7-T7-2 | 执行件模板 §4 + 各仓 `git status` 回读 | `doc/test/evidence/s7/signoff/`（勾稽回读） | B |
| S7-T7-3 | `doc/planning/OpenBase-S7-跨仓入仓与会签-OpenBase汇总核对表-v1.0.0.md` | `doc/test/evidence/s7/signoff/`（会签记录） | A+B |
| S7-T7-4 | 放行清单 / 清点总清单（升版） | 两份清单修订历史条目 | A |
| S7-T8-1 | `OpenBase-数据隔离实现任务卡-v1.0.0.md`（24 卡回写表） | 任务卡回写表 | A |
| S7-T8-2 | JT 归集文档 §3（七线回写） | 归集文档 §3 | A |
| S7-T8-3 | `doc/design/OpenBase-文档地图索引-v1.0.0.md` | 文档地图索引 | A |
| S7-T8-4 | `doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md` | 总收官报告 | A+B |
| S7-T8-5 | 同上（六项聚合自检表） | 报告自检表 + `gate-aggregate.json` | A+B |

### 附录 B：上游文档与提交号索引

| 类型 | 名称 / 提交号 | 说明 |
|------|--------------|------|
| 需求基线（本段） | 《OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md》（内部 **v1.1.0**，[Approved]） | 34 条验收断言 + Q-S7-1~8 定案 |
| 配套执行件 | `doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md`（commit **`72db715`**） | S7-T7 执行依据（四步：前置裁断/分批入仓/hash 回填/勾稽会签） |
| 规划 | 《多系统联调联试分阶段版本规划-子系统纵切-v1.0.0.md》（内部 v1.3.1） | §3「S7 总收官段」 |
| 归集 | 《多系统联调联试-子系统任务归集与版本规划-v1.0.0.md》（内部 v1.3.0） | §3.8 / §4-5 |
| 任务卡 | 《数据隔离实现任务卡-v1.0.0.md》（内部 v1.7.0） | K13 / RA-06 / SYS-1 / K07 现状 |
| 冒烟清单 | 《真实联调冒烟清单-v1.0.0.md》（OB-INTG-SMOKE-v1.1.0） | §3 用例矩阵 S0-S6 |
| 存量对齐清单 | 《存量测试对齐任务清单-v1.0.0.md》（OB-TEST-ALIGN-v1.0.0，内部 v1.2.0） | S7-T6-3 关闭对象 |
| 设计草案（语义依据） | 《U1-统一身份收口设计草案-v1.0.0.md》§8/§8.4/§9；《P2-1-…-设计草案-v1.0.0.md》§9.2/§9.3/§11.4 | 事件契约 / purge / verify-env / RA-06 |
| 路线/清单 | 《多系统对接-文档体系与升级路线规划-v1.0.0.md》（v1.1.0）；《跨仓提交放行清单-v1.0.0.md》（v1.0.8）；《联调产物清点核对总清单-v1.0.0.md》（v1.0.5） | 文档地图 / 放行 / 清点会签 |
| 同构参照 | 《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md》 | 设计草案结构与证据范式 |
| 事件契约锚点 | OpenBase `0713ec1` | `GET /api/v1/identity/events` 身份事件列表端点 |
| S2/S3/S4 台账回写链 | `1a6f3d4` / `a5dcd2b` / `cdfbd5b` | docs(intg) 提交 |
| S6 五提交号 | `2abe52a` / `aa6c5bd` / `72b19da` / `477eb80` / `5a1b17d` | 承载版本 `openbase-ui` 1.3.0 |
| S6 段门禁回写 | `aad9c8a` | `docs(intg): S6 段门禁批准回写（PENDING 挂起口径）` |
| U1（S1a） | `c1869bf` / `9a8dc24` / `bdbe146` / `993bc57` | U1 T1~T4 |
| P2-1（S1b） | `25b65d7` / `51c6657` / `09f28fa` / `9a0aa49` | 批次 1/2 |
| 存量对齐 | `0f808e9`（T1）/ `15b520a`（T3） | 存量测试对齐 |
| 本草案基线 HEAD | `72db715` | `docs(intg): S7 跨仓入仓与会签执行模板 v1.0.0` |

### 附录 C：沙箱实测记录（2026-09-11，可复现）

| # | 命令/方式 | 结果摘要 |
|---|----------|---------|
| 1 | `git log -1 --format='%h %s'` | `72db715 docs(intg): S7 跨仓入仓与会签执行模板 v1.0.0` |
| 2 | `git status --porcelain` | 7 项 `?? dogfood-output/**` + 2 项 `M`（归集/任务卡） |
| 3 | Read `scripts/verify-env/contract.json` | 6 组键：`config_single_source`(13)/`config_deprecated`(2)/`upstreams`(4)/`whitelist_matrix`(5)/`mapping_reconcile`(1)/`db_checks`(1) |
| 4 | Read `scripts/verify-env.ps1` | WARN 非阻断雏形；exit 0/1/2；`-FailFast`/`-SkipNetwork`/`-SkipDb` |
| 5 | Read `scripts/run_tests.ps1` | **v1.4.2**；每组 6 文件子进程隔离 + ruff；单仓 |
| 6 | `grep openbase_test` | **0 命中**（独立测试库未建立；仅测试临时文件名前缀 `openbase_test_*.db`） |
| 7 | Read `scripts/service-orchestrator.ps1` | 唯一编排入口；stop 按记录 PID 逆拓扑（非批量杀） |
| 8 | Read `OpenBase-数据隔离实现任务卡-v1.0.0.md` §K13/§RA-06 | K13 ⏳待立项（U2）；RA-06 ⏳（前置 K01-K08+RA-01~05） |
| 9 | Read 冒烟清单 / 存量对齐清单头部 | 冒烟 v1.1.0 [Draft] 待执行；对齐清单 [Draft]（内部 v1.2.0） |
| 10 | `doc/test/evidence/verify-env-report.json` | `warnings=9 errors=0 exit_code=1`（2026-09-08 快照） |

### 附录 D：配套执行件引用（S7-T7）

| 项 | 说明 |
|----|------|
| 执行件 | `doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md`（OB-INTG-S7-SIGNOFF-TPL-v1.0.0，commit `72db715`） |
| 结构 | §1 前置裁断（23 项待人工判定 + 7 项边界确认）/ §2 逐仓入仓（OpenMemory 4 批 A70 / OpenRAG 4 批 A67 / OpenLLM 6 批 A75 / DPS 4 批 A52）/ §3 入仓红线（禁 `-A`、敏感文件零进入、gitlink 禁 add、混合文件 `git add -p`）/ §4 逐仓勾稽 / §5 hash 回填 / §6 会签五步 / §7 S7-T7 断言对照 / §8 遗留与 PENDING |
| 纪律 | 该模板不代为执行四仓 git 命令；四仓命令沙箱外执行；**hash 一律真实，未执行登记 `PENDING`** |
| 与本设计关系 | S7-T7-1/2 直接以模板 §2/§4/§5 为证据形态；S7-T7-3 以模板 §6 + Q-S7-D10 汇总核对表为证据 |

---

> **文档结束**。本文档为 S7 段（总收官段）**设计（Step 1）**交付物（[Draft] v1.0.0）；断言以 §4 为准（34 条，执行面分布 A 5 / A+B 9 / B 20，与立项 §4 1:1），任务以 §4.1~§4.8 为准（S7-T1~T8），证据与 PENDING 口径以 §5 为准，段门禁以 §9 为准（门禁聚合六项全绿）。**B 面未真实执行项一律 PENDING 登记，禁伪造 hash 与通过。**


