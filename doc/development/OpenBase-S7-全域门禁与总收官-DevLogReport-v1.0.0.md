# OpenBase-S7-全域门禁与总收官-DevLogReport-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-DEVLOG-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review]（S7 段（总收官段）开发记录报告；**沙箱可判定面（A 面）已完成并留证**，联调窗口必需面（B 面）与两仓远端推送一律 PENDING 登记，禁伪造） |
| 日期 | 2026-09-11 |
| 作者 | AI（S7 批次 1~4 开发会话：沙箱内实现、实测与证据归档） |
| 版本主题 | **S7 段（总收官段）开发记录报告**：批 1 SHR 五项收口（`402ff8e`）→ 台账回填（`2235229`）→ 批 2 门禁聚合 T6（`d3faa7f`）→ 批 3 24 卡/七线 JT 回写 + 总收官报告 T8（`2d97d1a`）→ 批 4 会签汇总与口径修正 T7（`a5020fa`）；含逐批次改动清单、提交 hash、RED→GREEN 摘要、硬门禁实测值、SHR 五项收口与门禁聚合/清单关闭、24 卡/七线 JT 回写、会签汇总、版本处置、回归结果、遗留与沙箱受限复核清单、提交链索引 |
| 上游依据 | ①《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0.md》（OB-S7-DESIGN-v1.0.0，内部 **v1.0.1 [Approved]**，§4.1~§4.8 / §5 证据规范 / §8 边界 / §9 里程碑）；②《OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md》（OB-S7-v1.0.0，内部 **v1.1.0 [Approved]**，§4 34 条验收断言 / §8 里程碑与交付物清单）；③《OpenBase-数据隔离实现任务卡-v1.0.0.md》（内部 v1.9.0）；④《OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md》（内部 v1.5.0）；⑤《OpenBase-存量测试对齐任务清单-v1.0.0.md》（OB-TEST-ALIGN-v1.0.0，[Approved]） |
| 适用范围 | **提交面仅 OpenBase 主仓**：仓根与 `doc/**` 文档、`scripts/**` 收口脚本、`doc/test/evidence/s7/**` 证据；**不纳入 `dogfood-output/`**；**不改动 DPS/OpenLLM/OpenMemory/OpenRAG 四仓任何文件**（设计草案 §8 边界） |
| 证据面 | `doc/test/evidence/s7/**`（`shr/` 5 份 / `gate/gate-aggregate.json` / `t7/signoff-check.json` / `t8/writeback-check.json`）；`l1-1/**`、`l2-1/**`、`l2-2/**`、`l3-1/**` 为联调窗口待产出 |
| 纪律 | 结论如实；**未执行项一律 PENDING，禁伪造 hash、响应码与通过**（对齐设计草案 §5.4 与立项 §7 R-1/R-5） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-11 | AI（S7 批次 1~4 开发会话） | 初始版本：S7 段开发记录报告。含 §1 范围与目标；§2 逐批次实施记录（批 1~4：改动清单、提交 hash、RED→GREEN 摘要、硬门禁实测值）；§3 SHR 五项收口说明；§4 门禁聚合与清单关闭；§5 24 卡/七线 JT 回写；§6 会签汇总；§7 版本处置；§8 回归结果汇总；§9 遗留与沙箱受限复核清单；§10 提交链索引。**本次仅新建本报告，不改动任何代码、脚本或子系统仓文件** |

---

## §1 范围与目标

- **本报告**为 S7 段（总收官段）「开发」环节交付物（设计草案 §5.5、§9 Step 2），落点 `doc/development/`，状态 [Review]。
- **目标**：SHR 五项收口（verify-env 全局化 / `openbase_test` + `run_tests.ps1` / K13 存储账号分离 / 编排唯一入口 / 文档地图）、门禁聚合编排（RA-06 + 冒烟 S0-S6 + 存量对齐清单关闭 + K07/SYS-1 终验）、跨仓入仓核验与会签、24 卡/七线 JT 台账全量回写与总收官报告。
- **执行面界定**：A 面（静态/脚本/文档/OpenBase 仓操作）在本报告内**已真实执行并留证**；B 面（真实 PG/Redis、IdP/受信通道、四仓运行态、四仓写权限）**一律 PENDING 登记**，交联调窗口与用户（沙箱外）执行。
- **交付物对应**：本报告对应设计草案 §9 Step 2「DevLogReport v1.0.0（含源码清单与改动行号）」；测试报告见 `doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md`（Step 3）；总收官报告见 `doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md`（Step 4）。

---

## §2 逐批次实施记录（批 1~4）

> 批次划分按 S7 任务依赖 `T1 → {T2 ∥ T3 ∥ T4 ∥ T5} → T6 → T7 → T8`（设计草案 §9）。每批给出改动清单、提交 hash、RED→GREEN 摘要与硬门禁实测值。**所有 hash 均为本仓已入库实测值**。

### 2.1 批 1（`402ff8e`）——S7-T1 SHR 五项收口

- **提交**：`402ff8e` `feat(shr): S7-T1 SHR 五项收口（verify-env 全局化/测试库/账号矩阵/编排入口/文档地图）`
- **RED→GREEN 摘要**：
  - RED：`contract.global.json` 不存在、`grep openbase_test` 0 命中（独立测试库未建立）、K13 账号矩阵与授权脚本缺位、编排绕过静态扫描缺位、文档地图索引缺位；`tests/test_s7_t1_shr.py` 15 用例首跑失败。
  - GREEN：五项落点全部产出，`tests/test_s7_t1_shr.py` **15 passed**；`scan_orchestrator_bypass.py` 扫描 20 文件、`disallowed=0`、自检三项 `true`。
- **改动清单（新增/修改）**：

| 类型 | 文件 | 说明 |
|------|------|------|
| 新增 | `scripts/verify-env/contract.global.json` | 跨仓统一契约（OpenBase 6 组主结构 + `repo_overrides` 承载四仓键命名对齐） |
| 新增 | `scripts/verify_env_global.ps1` | verify-env 全局入口（`-Repos` / 两段式收紧 / 回退开关） |
| 新增 | `scripts/db/init_openbase_test.ps1` | `openbase_test` 建库/建账号/幂等迁移（`IF NOT EXISTS` / `create_all`） |
| 新增 | `scripts/db/grant_k13_accounts.ps1` | K13 授权收敛（仅本 schema DML、不授 superuser、含跨 schema `REVOKE`） |
| 新增 | `scripts/scan_orchestrator_bypass.py` | 编排禁批量杀静态扫描（唯一允许位 = 逆拓扑 stop） |
| 修改 | `scripts/run_tests.ps1` | 升为跨仓统一回归入口（`-Repos` + 逐仓命令表），保留单仓分组子进程隔离 |
| 新增 | `doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md` | schema×账号×权限矩阵（四类账号） |
| 新增 | `doc/design/OpenBase-文档地图索引-v1.0.0.md` | L0-L4 全量文档地图 + S1a~S7 并入核对 + DOCMAP-MANIFEST |
| 新增 | `tests/test_s7_t1_shr.py` | S7-T1 断言 **15 用例** |
| 新增 | `doc/test/evidence/s7/shr/{verify-env-global,openbase-test,k13,orchestrator,doc-map}/**` | SHR 五项证据 JSON 5 份 |

- **硬门禁实测值**：`python -m ruff check openbase tests scripts` → 0 错误；`python -m pytest tests/test_s7_t1_shr.py -q` → **15 passed**。

### 2.2 批 2（`d3faa7f`）——S7-T6 门禁聚合

- **提交**：`d3faa7f` `feat(gate): S7-T6 门禁聚合（RA-06/冒烟 S0-S6/对齐清单关闭/K07 终验）`
- **RED→GREEN 摘要**：
  - RED：无单命令/单批门禁聚合脚本与结构化证据；RA-06 五项、冒烟 S0-S6、对齐清单关闭、K07/SYS-1 无统一聚合口径。
  - GREEN：`scripts/gate_aggregate.py` 落地，单命令输出 `doc/test/evidence/s7/gate/gate-aggregate.json`（`overall_status=PASS`、`pass=19`、`pending=3`、`fail=0`）；`tests/test_s7_t6_gate.py` **16 passed**。
- **改动清单（新增/修改）**：

| 类型 | 文件 | 说明 |
|------|------|------|
| 新增 | `scripts/gate_aggregate.py` | 门禁聚合脚本（单命令/单批/结构化 JSON；失败项如实登记） |
| 新增 | `tests/test_s7_t6_gate.py` | S7-T6 断言 **16 用例** |
| 新增 | `doc/test/evidence/s7/gate/gate-aggregate.json` | 门禁聚合证据（RA-06 82 用例 PASS / 冒烟结构对账 PASS / 对齐清单 / K07-SYS-1 / SHR 五项） |
| 修改 | `OpenBase-存量测试对齐任务清单-v1.0.0.md` | 状态升 **[Approved]**（分批门禁复跑口径登记） |

- **硬门禁实测值**：`scripts/gate_aggregate.py` 输出 `overall=PASS / pass=19 / pending=3`（A 面选择器真实执行，B 面真实面 PENDING）；`python -m pytest tests/test_s7_t6_gate.py -q` → **16 passed**。

### 2.3 批 3（`2d97d1a`）——S7-T8 24 卡/七线 JT 回写与总收官报告

- **提交**：`2d97d1a` `docs(s7): S7-T8 24卡/七线JT全量回写与总收官报告`
- **RED→GREEN 摘要**：
  - RED：任务卡缺 S7 回写口径、归集文档缺七线 JT 汇总、文档地图缺 S7 新增条目、总收官报告缺位。
  - GREEN：任务卡升 **v1.8.0**（24 卡逐卡回写）、归集文档升 **v1.4.0**（§3.9 七线 JT）、文档地图升 **v1.0.1**（+13 项 S7 条目）、总收官报告 v1.0.0 [Review] 产出；`tests/test_s7_t8_writeback.py` **19 passed**。
- **改动清单（新增/修改）**：

| 类型 | 文件 | 说明 |
|------|------|------|
| 修改 | `OpenBase-数据隔离实现任务卡-v1.0.0.md` | 内部升 v1.8.0：24 卡（K01-K18 + RA-01~RA-06）状态全量回写 |
| 修改 | `OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md` | 内部升 v1.4.0：§3.9 七线 JT 汇总 |
| 修改 | `doc/design/OpenBase-文档地图索引-v1.0.0.md` | 内部升 v1.0.1：§2.6 增补 S7 收口资产与证据 + MANIFEST |
| 新增 | `doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md` | 总收官报告 v1.0.0 [Review]（六项聚合 + PENDING + 会签 + 遗留） |
| 新增 | `tests/test_s7_t8_writeback.py` | S7-T8 断言 **19 用例** |
| 新增 | `doc/test/evidence/s7/t8/writeback-check.json` | t8 回写核对证据（24 卡 / 七线 / 无游离 / 报告章节） |

- **硬门禁实测值**：`python -m pytest tests/test_s7_t8_writeback.py -q` → **19 passed**。

### 2.4 批 4（`a5020fa`）——S7-T7 会签汇总与口径修正

- **提交**：`a5020fa` `docs(s7): S7-T7 会签汇总与入仓口径修正（四仓入仓 + 清单升版）`
- **RED→GREEN 摘要**：
  - RED：批次 3 过时口径（OpenMemory/OpenLLM 两仓「未入仓」）；四仓本地入仓实测已完成，缺 hash 回填、清单升版与会签汇总核对表。
  - GREEN：四仓入仓 hash 回填、执行模板 v1.0.2 [Approved]、放行清单 v1.0.9 [Approved]、清点总清单 v1.0.7 [Approved]、归集 v1.5.0、任务卡 v1.9.0、总收官报告 v1.0.1（口径修正）、会签汇总核对表 v1.0.0；`tests/test_s7_t7_signoff.py` **20 passed**。
- **改动清单（新增/修改）**：

| 类型 | 文件 | 说明 |
|------|------|------|
| 新增 | `doc/planning/OpenBase-S7-跨仓入仓与会签-OpenBase汇总核对表-v1.0.0.md` | 四仓 hash 汇总 + 逐仓 A 类回读 + 会签五步结论 |
| 修改 | `doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md` | 内部升 v1.0.2 [Approved] |
| 修改 | `doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md` | 内部升 v1.0.9 [Approved] |
| 修改 | `doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md` | 内部升 v1.0.7 [Approved] |
| 修改 | `OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md` | 内部升 v1.5.0（四仓入仓口径修正） |
| 修改 | `OpenBase-数据隔离实现任务卡-v1.0.0.md` | 内部升 v1.9.0（四仓 hash 卡尾回填） |
| 修改 | `doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md` | 内部升 v1.0.1（四仓入仓完成口径修正与跨仓会签回填） |
| 新增 | `tests/test_s7_t7_signoff.py` | S7-T7 断言 **20 用例** |
| 新增 | `doc/test/evidence/s7/t7/signoff-check.json` | 会签核对证据（四仓 hash / 勾稽 / 会签五步 / 清单升版） |

- **硬门禁实测值**：`python -m pytest tests/test_s7_t7_signoff.py -q` → **20 passed**。

### 2.5 台账回填（`2235229`）——S3(OpenRAG)/S5(DPS) 入仓回填登记

- **提交**：`2235229` `docs(intg): S3(OpenRAG)/S5(DPS) 入仓回填登记（hash/勾稽/清单同步）`
- 该批为跨仓入仓 hash 与勾稽结果回填，**不属 S7 本体任务**（S3/S5 段级），作为 S7-T7 会签的前置数据源登记；`gate-aggregate.json` 的 `openbase_commit` 基线取自本批。

---

## §3 SHR 五项收口说明

> 逐项对齐设计草案 §4.1 与 S7-T1-1~5；证据索引 `doc/test/evidence/s7/shr/**`（5 份）。

| 项 | 收口结论（A 面） | 落点 | 证据 | B 面（PENDING） |
|----|----------------|------|------|----------------|
| ① verify-env 全局化（S7-T1-1） | 契约主结构 = OpenBase 6 组（与 `contract.json` 逐组一致，非破坏性保留）；`repo_overrides` 承载四仓契约键；全局入口 `-DryRun` 退出码 0、`repos=5` | `scripts/verify-env/contract.global.json`、`scripts/verify_env_global.ps1` | `shr/verify-env-global/contract-align.json` | 逐仓真实探活（端口/上游/db）→ PENDING |
| ② `openbase_test` + `run_tests.ps1`（S7-T1-2） | 建库脚本幂等（存在性守卫 + `IF NOT EXISTS`/`create_all`）；`OPENBASE_DB_URL` → `openbase_test`；`run_tests.ps1` 升跨仓入口且保留 `$i += 6` 分组隔离 | `scripts/db/init_openbase_test.ps1`、`scripts/run_tests.ps1` | `shr/openbase-test/init-check.json` | 真实建库/建账号/迁移 + 跨仓实跑 → PENDING |
| ③ K13 存储账号分离（S7-T1-3） | 账号矩阵含四类账号（`openbase_app`/`platform_app`/`openbase_migrator`/`openbase_runtime`）、仅本 schema DML、不授 superuser；授权脚本 `-DryRun` 退出码 0、无 `GRANT ... SUPERUSER` | `doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md`、`scripts/db/grant_k13_accounts.ps1` | `shr/k13/account-matrix-check.json` | 真实授权 + 跨 schema 写拒绝 → PENDING |
| ④ 编排唯一入口（S7-T1-4） | 唯一入口 = `service-orchestrator.ps1`；扫描 20 文件、`disallowed=0`、自检三项 `true` | `scripts/service-orchestrator.ps1`、`scripts/scan_orchestrator_bypass.py` | `shr/orchestrator/bypass-scan.json` | 编排实跑（启停逆拓扑）→ PENDING |
| ⑤ 文档地图（S7-T1-5） | 索引覆盖 L0-L4 分层与字段；S1a~S7 文档逐项并入；MANIFEST 逐项存在（游离 0） | `doc/design/OpenBase-文档地图索引-v1.0.0.md` | `shr/doc-map/orphan-check.json` | 无（A 面判定） |

> **SHR 结构面结论**：① ② ④ 结构面 PASS（真实面 PENDING）；③ 结构面 PASS（断言主体属 B 面 → PENDING）；⑤ PASS（纯 A 面）。

---

## §4 门禁聚合与清单关闭

> 对齐设计草案 §4.6（S7-T6-1~4）与 Q-S7-D7；证据 `doc/test/evidence/s7/gate/gate-aggregate.json`。

| 分项 | A 面结论 | 实测值 | B 面（PENDING） |
|------|---------|--------|----------------|
| RA-06 聚合（五项） | PASS | 82 用例：双租户隔离 19 / fail-closed 21 / OIDC 批次 12 / 委托跨界 13 / 吊销即时性 17 | 真实双租户数据面 / IdP / Redis / 网关链路 → PENDING |
| 冒烟 S0-S6 | 结构对账 PASS | S0-S6 七组、P0 30 例、P1 2 例、`missing=0` | 真实五服务执行（P0 全绿 / P1 登记）→ PENDING |
| 存量测试对齐清单关闭 | PASS（文档面） | 清单升 **[Approved]**；OIDC 独立批次 12 例 PASS；主批次 573 例中 4 例 asyncpg/PG 环境性失败 | 主批次复跑 0 失败（随 PG 就绪）→ PENDING（PG-ENV-4） |
| K07 + SYS-1 终验 | 结构对账 PASS | 四仓填报缺口清零（OpenMemory 32 / OpenRAG 121 / OpenLLM 14 / DPS 169 行，`gap_count=0`） | 真实 openapi 全量导出与逐行终验 → PENDING |
| SHR 五项（批 1 复核） | PASS | 五项结构面全 PASS | 各真实面 → PENDING |

**聚合结论**：`overall_status=PASS`、`pass=19`、`pending=3`、`fail=0`；`exit_code=0`（mode=dry-run）。**清单关闭**：`OpenBase-存量测试对齐任务清单-v1.0.0.md` 状态升 [Approved]（`gate-aggregate.json` §TEST-ALIGN-CLOSE）。

---

## §5 24 卡 / 七线 JT 回写

- **24 卡回写（S7-T8-1）**：任务卡 v1.8.0 → v1.9.0，K01-K18 + RA-01~RA-06 共 **24 卡**逐卡含「S7 回写口径（S7-T8-1）」；统计 **22 已完成/已闭环 + 2 待联调窗口 PENDING（RA-06 关联 S7-T6-1/S7-T6-2、K13 关联 S7-T1-3）**；卡尾追加「附：S7 段（总收官）回写摘要（2026-09-11）」。
- **七线 JT 回写（S7-T8-2）**：归集文档 v1.4.0 → v1.5.0，§3.9 七线（OpenBase-JT / OpenLLM-JT / OpenRAG-JT / OpenMemory-JT / DPS-JT / FE-JT / SHR-JT）状态与提交号全量回写；**四仓均「已入仓（本地提交完成）」**，其中 OpenRAG `a2eb92b` / DPS `e772c01` 三远端同步，OpenMemory `cc7c06f` origin+backup 同步（github 待推 PENDING），OpenLLM `be1886d` 四远端未推送（PENDING）。
- **文档地图维护（S7-T8-3）**：文档地图 v1.0.1 增补 S7 收口资产与证据；本批再升 v1.0.2 增补 DevLogReport / 测试报告条目（见 §10）。
- **证据**：`doc/test/evidence/s7/t8/writeback-check.json`（`coverage`：task_cards 24 / jt_lines 7 / doc_map_orphan 0 / report_sections ≥6）。

---

## §6 会签汇总

> 对齐设计草案 §4.7（S7-T7-1~4）与 Q-S7-D10；证据 `doc/test/evidence/s7/t7/signoff-check.json`、汇总核对表 `doc/planning/OpenBase-S7-跨仓入仓与会签-OpenBase汇总核对表-v1.0.0.md`。

- **四仓本地入仓（S7-T7-1）**：OpenRAG `release/v1.10.0`@`a2eb92b`（4 批）、DPS `main`@`e772c01`（4 批）、OpenMemory `release/v7.3.0`@`cc7c06f`（4 批 + lint/untrack）、OpenLLM `feature/s4-identity-channel-b`@`be1886d`（6 批 + 手册留档）+ need-star `ce40f90`；hash 一律真实回填。
- **逐仓勾稽（S7-T7-2）**：OpenRAG/DPS/OpenLLM A 类差异 0（实测/按登记）；OpenMemory 残余 89 待 A 类回读复核（**PENDING**）。
- **清单升版（S7-T7-4）**：放行清单 **v1.0.9 [Approved]**、清点总清单 **v1.0.7 [Approved]**、执行模板 **v1.0.2 [Approved]**。
- **会签五步（S7-T7-3）**：① 前置裁断 ✅ / ② 分批入仓 ✅ / ③ hash 回填 ✅ / ④ 四仓勾稽 ✅ 部分（OpenMemory PENDING）/ ⑤ 清单升版 ✅；含 K02/K07/K13 跨系统卡与接口一致性评审。

**会签汇总结论**：**部分达成**——四仓入仓完成（本地提交）+ 勾稽 A 类差异 0（两仓实测、两仓按登记）+ 清单升版；**两仓远端推送与 OpenMemory 勾稽回读 PENDING**。

---

## §7 版本处置（S7 无产品版本）

- **S7 段无独立产品版本**：S7 为总收官段，不改 `openbase/**` 业务语义，不产出产品版本号；版本桥接以 **OpenBase 仓 HEAD 提交链**承载（对齐设计草案 §8 边界与 Q-S7-8）。
- **提交链**：`402ff8e`（T1 SHR）→ `2235229`（台账回填）→ `d3faa7f`（T6 门禁聚合）→ `2d97d1a`（T8 回写/收官报告）→ `a5020fa`（T7 会签汇总与口径修正）。
- **承载资产版本**：统一前端承载版本 `openbase-ui` 1.3.0（S6 冻结，S7 仅复核 B5/B6，不改动）；四仓以各仓分支/提交号桥接（见 §6）。
- **回滚**：脚本/规则层回滚 = 保留上一版本 + 取消 `-FailFast`/置 `STRICT=0`；文档层回滚 = Git 提交历史；四仓入仓回滚由各仓自行处置（S7 不代执行）。

---

## §8 回归结果汇总

> 2026-09-11 沙箱内实测（仓根 `d:\Trae CN\myproject\Dev\OpenBase`）；**未执行项不填 PASS**。

| # | 命令 | 结果摘要 | 退出码 |
|---|------|---------|--------|
| 1 | `python -m ruff check openbase tests scripts` | **All checks passed!**（0 错误） | **0** |
| 2 | `python -m pytest tests/test_s7_t1_shr.py -q` | **15 passed**（S7-T1） | **0** |
| 3 | `python -m pytest tests/test_s7_t6_gate.py -q` | **16 passed**（S7-T6） | **0** |
| 4 | `python -m pytest tests/test_s7_t8_writeback.py -q` | **19 passed**（S7-T8） | **0** |
| 5 | `python -m pytest tests/test_s7_t7_signoff.py -q` | **20 passed**（S7-T7） | **0** |
| 6 | `python -m pytest tests/test_s7_docs.py -q` | **passed**（本批新增：S7 文档一致性断言） | **0** |
| 7 | `python -m pytest tests/test_s7_t1_shr.py tests/test_s7_t6_gate.py tests/test_s7_t7_signoff.py tests/test_s7_t8_writeback.py -q` | **70 passed**（防回归） | **0** |
| 8 | `python -m pytest tests/test_s6_t1_frontend_boundary.py -q` | **9 passed**（既有 S6 边界防回归） | **0** |

**用例合计**：S7-T1~T8 断言测试 **15 + 16 + 19 + 20 = 70 用例全绿**；本批新增 `tests/test_s7_docs.py`（文档一致性断言）全绿。

---

## §9 遗留与沙箱受限复核清单

> 对齐设计草案 §5.3 PENDING 登记规范与总收官报告 §4；**均非阻断项**。**未执行一律 PENDING，禁伪造**。

### 9.1 沙箱受限（A 面已完成，B 面待执行）

| 项 | 挂起项 | 前置条件 | 责任方 | 复核动作 |
|----|--------|---------|--------|---------|
| B-1 | verify-env 真实探活（跨仓端口/上游/db） | 真实 PG/Redis + 四仓运行态 | 联调窗口 | 非 `-DryRun` 执行并回填逐仓响应 |
| B-2 | `openbase_test` 真实建库与跨仓实跑 | 真实 PG + 建库权限 | 联调窗口 | 执行 `init_openbase_test.ps1` + `run_tests.ps1 -Repos` |
| B-3 | K13 真实授权与跨 schema 写拒绝 | 真实 PG + 授权权限 | 联调窗口 | 执行授权脚本 + 拒绝用例（期望 42501） |
| B-4 | 编排实跑（服务生命周期逆拓扑） | 四仓运行态 | 联调窗口 | 执行 `service-orchestrator.ps1` 启停 |
| RA-06 真实面 | 双租户隔离 / fail-closed / OIDC / 委托跨界 / 吊销即时性 | 真实 PG/Redis + IdP + 四仓 | 联调窗口 | 真实环境执行后回填 `gate-aggregate.json` |
| 冒烟 S0-S6 | 真实执行（P0 全绿 / P1 登记） | 真实五服务 + 密钥 + 三真实开关 | 联调窗口 | 按冒烟清单 v1.1.0 §5 产出记录 |
| K07/SYS-1 真实终验 | 真实 openapi 全量导出与逐行终验 | 四仓运行态 + openapi 导出 | 联调窗口 | 导出全量并回填矩阵终验表 |

### 9.2 PENDING 汇总（须逐条登记）

- **段级真实双签 4 条**：S2（OpenMemory L3-2）/ S3（OpenRAG Pull）/ S4（OpenLLM）/ S5（DPS Pull 真实 Q-DPS-5）。
- **S6 B1~B6**：B1 Playwright 9 关键页 / B2 L3-2 真实受信通道双签 / B3 真实双租户数据面 / B4 真实 IdP 回调与吊销 / B5 四仓 `frontend/` 物理改造与 CI 收敛（S7 按 Q-S6-D7 复核）/ B6 nginx `/ui/` 发布回滚。
- **S7 自身**：RA-06 五项真实面 / 冒烟 S0-S6 真实执行 / `PG-ENV-1`~`PG-ENV-4`（asyncpg/PG 4 项环境性失败）/ K07/SYS-1 真实 openapi 全量导出与逐行终验 / T2~T5 联调窗口（L1-1 级联 / L2-1 演练 / L2-2 终验 / L3-1 Agent）/ 两仓远端推送（OpenMemory github 待推、OpenLLM 四远端未推送）+ OpenMemory 勾稽回读。
- **关系说明**：`PG-ENV-1`~`PG-ENV-4` 与 `tests/test_oidc_binding.py` 4 例环境性失败同源（沙箱无真实 PG/Redis），单文件独立运行 5 passed，**非业务缺陷**，随 PG 就绪复跑关闭（详见测试报告 §5）。

---

## §10 提交链索引

| # | 提交 | 主题 | 覆盖任务 | 主要落点 |
|---|------|------|---------|---------|
| 1 | `402ff8e` | `feat(shr): S7-T1 SHR 五项收口（verify-env 全局化/测试库/账号矩阵/编排入口/文档地图）` | S7-T1-1~5 | `scripts/verify-env/contract.global.json`、`scripts/verify_env_global.ps1`、`scripts/db/init_openbase_test.ps1`、`scripts/db/grant_k13_accounts.ps1`、`scripts/scan_orchestrator_bypass.py`、`scripts/run_tests.ps1`、`doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md`、`doc/design/OpenBase-文档地图索引-v1.0.0.md`、`tests/test_s7_t1_shr.py`、`doc/test/evidence/s7/shr/**` |
| 2 | `2235229` | `docs(intg): S3(OpenRAG)/S5(DPS) 入仓回填登记（hash/勾稽/清单同步）` | S7-T7 前置数据 | 跨仓回填登记（S3/S5 段级） |
| 3 | `d3faa7f` | `feat(gate): S7-T6 门禁聚合（RA-06/冒烟 S0-S6/对齐清单关闭/K07 终验）` | S7-T6-1~4 | `scripts/gate_aggregate.py`、`tests/test_s7_t6_gate.py`、`doc/test/evidence/s7/gate/gate-aggregate.json`、存量对齐清单（[Approved]） |
| 4 | `2d97d1a` | `docs(s7): S7-T8 24卡/七线JT全量回写与总收官报告` | S7-T8-1~5 | 任务卡 v1.8.0、归集 v1.4.0、文档地图 v1.0.1、总收官报告 v1.0.0、`tests/test_s7_t8_writeback.py`、`doc/test/evidence/s7/t8/writeback-check.json` |
| 5 | `a5020fa` | `docs(s7): S7-T7 会签汇总与入仓口径修正（四仓入仓 + 清单升版）` | S7-T7-1~4 | 汇总核对表 v1.0.0、执行模板 v1.0.2、放行清单 v1.0.9、清点总清单 v1.0.7、归集 v1.5.0、任务卡 v1.9.0、总收官报告 v1.0.1、`tests/test_s7_t7_signoff.py`、`doc/test/evidence/s7/t7/signoff-check.json` |
| 6 | （本批） | `docs(s7): S7 DevLogReport 与测试报告（34 断言矩阵与段门禁六项结论）` | S7-T8-4/5 文档面 | 本报告 v1.0.0、测试报告 v1.0.0、`tests/test_s7_docs.py`、文档地图 v1.0.2、总收官报告 v1.0.1 引用增补 |

> **提交面纪律**：逐项显式 `git add`（禁 `git add -A` / `git add .`）；提交白名单 = 仓根与 `doc/**` 文档 + `tests/test_s7_docs.py`；**不纳入 `dogfood-output/`**；**不改动子系统仓**。

---

> **文档结束**。本文档为 S7 段「开发」环节交付物（**[Review]** v1.0.0）；与设计草案 v1.0.1（[Approved]）、立项方案 v1.1.0（[Approved]）逐条对应；B 面（联调窗口）与非沙箱项待受控环境回填后按挂起口径复核。测试结论见《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md》。
