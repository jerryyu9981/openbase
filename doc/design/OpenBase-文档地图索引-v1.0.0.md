# OpenBase-文档地图索引-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-DOCMAP-INDEX-v1.0.0 |
| 版本 | v1.0.13 |
| 状态 | [Draft]（S7-T1-5 产出；v1.0.1 S7-T8-3 增补 S7 新增条目与证据索引；v1.0.2 增补 S7 DevLogReport / 测试报告条目；v1.0.3 增补 S7 联调窗口工具脚本 L1-1/L2-1/L2-2/L3-1/L3-2 条目；v1.0.4 增补 S7 联调窗口环境检查报告与 env-check 证据条目；v1.0.5 增补人工端到端测试日志记录方案条目；v1.0.6 该方案升版 v1.0.1（补 §11 响应级观测与错误归因、D-5 红线）并同步条目描述；v1.0.7 该方案升版 v1.0.2（并入 §11.8 跨仓前提实测核实 + D-6）并同步条目描述；v1.0.8 该方案升版 v1.1.0 并置 [Approved]（决议冻结 §9.1）并同步条目描述；v1.0.9 增补 D-6 四仓 request_id 日志接线改动说明条目；v1.0.10 登记批 1 里程碑（C-1+C-6）实施记录 DevLogReport 条目并同步方案条目至 v1.1.1；v1.0.11 该 DevLogReport 升版 v1.1.0（批 1 C-1~C-9 全量落地）并同步方案条目至 v1.2.0、增补聚合脚本与人工测试证据条目；v1.0.12 登记批 2（C-10~C-12）与批 4（C-15~C-19）实施记录 DevLogReport 条目、方案条目同步至 v1.4.0、增补错误归因分析器与批 4 单测/回归证据条目；v1.0.13 该 DevLogReport 家族按版本管理流程归档旧版（v1.1.0/v1.2.0 → `doc/development/archive/`，只读）并同步条目路径；随 S7 段门禁批准回写 [Approved]） |
| 日期 | 2026-09-11 |
| 作者 | AI（沙箱侧现状实测与索引编制；批 1/批 2/批 4 开发会话增补） |
| 用途 | **L0-L4 全量文档地图（唯一入口表）**：逐层登记文档「名称 / 版本 / 角色 / 状态 / 关联锚点」，并承载 **S1a~S7 纵切新增文档并入核对**；判据「**无游离文档**」（各层文档均在索引内，差异 0 或显式登记） |
| 上游依据 | ①《OpenBase-多系统对接-文档体系与升级路线规划-v1.0.0.md》§2（L0-L4 分层定案 C + §2.2 D-4「复盘根治方案维护文档地图」）；②《OpenBase-多系统对接联调问题复盘与根治方案-v1.0.0.md》（L0 治理根 / 文档地图维护点）；③《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0.md》§2.2 / §4.1（Q-S7-D6：独立索引文件为地图正文落点） |
| 适用范围 | OpenBase 主仓全部项目文档（`doc/**` + 仓根治理/立项/设计/台账文档）；各子系统仓文档不在本索引范围（见 §5 边界） |

### 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-11 | AI（沙箱侧现状实测与索引编制） | 初始版本：S7-T1-5 文档地图正文落点。含 §1 分层模型、§2 L0-L4 全量文档清单、§3 S1a~S7 纵切并入核对表、§4 无游离核对判据 + 机器可核对清单、§5 维护与边界。**本次仅新建本索引一个文档，未改动其他正文** |
| v1.0.1 | 2026-09-11 | AI（S7 批次 3 开发会话） | **S7-T8-3 文档地图维护**：新增 §2.6「S7 新增收口资产与证据」（SHR 五项脚本与契约 / K13 矩阵 / 门禁聚合脚本与证据 / S7 总收官报告 + t8 回写核对证据）并入索引；§3 S7 行「并入结论」更新；DOCMAP-MANIFEST 机器清单同步增补上述条目并保持逐项真实存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目** |
| v1.0.2 | 2026-09-11 | AI（S7 批次 5 开发会话） | **S7 段 Step 2/3 交付物并入**：新增 §2.5 L4 两份交付物行（`doc/development/OpenBase-S7-全域门禁与总收官-DevLogReport-v1.0.0.md`、`doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md`）；§3 S7 行 DevLogReport / 测试报告由「待产出」更正为实际路径；DOCMAP-MANIFEST 同步增补两条并保持逐项存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目** |
| v1.0.3 | 2026-09-11 | AI（S7 联调窗口工具脚本骨架批次） | **S7 联调窗口工具脚本并入**：新增 §2.6 五行（`scripts/verify_l1_1_cascade.ps1`、`scripts/drill_l2_1_failover.ps1`、`scripts/finalize_l2_2_matrix.py`、`scripts/verify_l3_1_agent.ps1`、`scripts/smoke_l3_2.py`，均为「骨架 + 干跑」形态）；DOCMAP-MANIFEST 同步增补五条并保持逐项真实存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目** |
| v1.0.4 | 2026-09-11 | AI（P2 联调窗口环境只读探测会话） | **S7 联调窗口环境检查报告与证据并入**：§2.5 新增一行（`doc/planning/OpenBase-S7-联调窗口环境检查报告-v1.0.0.md`）；§2.6 新增一行（`doc/test/evidence/s7/env/env-check.json`，schema_version=1 / tool=env-check / mode=run）；§3 S7 行「并入结论」更新；DOCMAP-MANIFEST 同步增补两条并保持逐项真实存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目** |
| v1.0.5 | 2026-09-13 | AI（S7 批次 31 人工测试日志方案会话） | **人工端到端测试日志记录方案并入**：§2.6 新增一行（`doc/design/OpenBase-人工端到端测试日志记录方案-v1.0.0.md`，状态 [Draft] 待评审）；DOCMAP-MANIFEST 同步增补一条并保持逐项真实存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目** |
| v1.0.6 | 2026-09-13 | AI（S7 批次 32 响应级观测方案会话） | **人工测试日志方案升版 v1.0.1 并同步条目**：该方案新增 §11（响应级观测与错误归因：实证原方案观测不到响应数据、D-5 红线硬约束、三开关、脱敏规则、错误归因矩阵、分析器输出）与 §5 批 4（C-15~C-19），待决策增至 D-1~D-5（**D-5 响应采集红线已确认：默认关闭 + 开启强制脱敏**）；§2.6 条目描述与状态同步更新。**仅更新既有条目描述，不新增/不删除条目** |
| v1.0.7 | 2026-09-13 | AI（S7 批次 33 跨仓前提核实会话） | **人工测试日志方案升版 v1.0.2 并同步条目**：该方案新增 §11.8（跨仓前提实测核实：前提 1 四仓 PASS 无需改动、前提 2 四仓均未打通需各自最小改动、并登记 OpenRAG 请求日志中间件未注册与 OpenMemory 启动路径两处既有缺口）与 §9 D-6（是否推动四仓补接线），待决策增至 D-1~D-6；§2.6 条目描述与状态同步更新。**仅更新既有条目描述，不新增/不删除条目** |
| v1.0.8 | 2026-09-13 | AI（S7 批次 34 决议冻结会话） | **人工测试日志方案定稿 v1.1.0 并置 [Approved]**：D-1~D-6 全部决议冻结（D-1=②/D-2=①/D-3=①/D-4=①/D-5=①/D-6=②，详见该方案 §9.1），冻结实施顺序（批 1 → 批 2 → 批 4）与首个里程碑（C-1 + C-6）；§2.6 条目版本与状态（[Draft] → [Approved]）同步更新。**仅更新既有条目描述与状态，不新增/不删除条目；本仓未改动业务代码** |
| v1.0.9 | 2026-09-13 | AI（S7 批次 35 跨仓施工说明会话） | **D-6 四仓改动说明并入**：§2.6 新增一行（`doc/design/OpenBase-D6四仓request_id日志接线改动说明-v1.0.0.md`，[Draft]，跨仓施工依据）；DOCMAP-MANIFEST 同步增补一条并保持逐项真实存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目；本仓未改动业务代码** |
| v1.0.10 | 2026-09-14 | AI（S7 批次 36 批 1 里程碑开发会话） | **批 1 里程碑（C-1 日志落盘 + C-6 服务日志采集）实施记录并入**：§2.5 新增一行（`doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.0.0.md`，[Review]，S7 Step 2 增量开发记录）；§2.6 方案条目版本由 v1.1.0 同步至 **v1.1.2**（§3.1 L1 落点文件名对齐实现、新增 §5.1 实施进度、移除 C-1 按保留期自动清理以遵循不变量 T6-1）；DOCMAP-MANIFEST 同步增补一条并保持逐项真实存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目** |
| v1.0.11 | 2026-09-14 | AI（S7 批次 37 批 1 全量落地会话） | **批 1（C-1~C-9）全量落地并入**：§2.5 该 DevLogReport 升版 **v1.1.0**（新增 §15 C-2~C-9 实施记录）并同步 §2.6 方案条目至 **v1.2.0**（含 `X-Test-Run-Id` 头承载口径与 C-1~C-9 实施进度表）；§2.6 增补两行（`scripts/test_log_aggregate.py`、`doc/test/evidence/manual/run-20260914-*.{json,md}`）；DOCMAP-MANIFEST 同步增补三条并保持逐项真实存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目** |
| v1.0.12 | 2026-09-14 | AI（S7 批 4 开发会话） | **批 2 / 批 4 实施记录并入**：§2.5 增补两行（`doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.2.0.md`（批 2 C-10~C-12）、`...-v1.3.0.md`（批 4 C-15~C-19））；§2.6 方案条目版本由 v1.2.0 同步至 **v1.4.0**（§5.1 增列批 4 C-15~C-19 进度行与实施期补充：digest 口径差异、采集需启动期置开关、专用代理族接线范围）；§2.6 增补三行（`scripts/test_log_analyze.py` 错误归因分析器、`doc/test/evidence/manual/batch4-unit-junit.xml`、`.../batch4-regression2-junit.xml`）；DOCMAP-MANIFEST 同步增补五条并保持逐项真实存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目** |
| v1.0.13 | 2026-09-14 | AI（S7 批 4 开发会话，人工确认后执行） | **DevLogReport 家族旧版归档（版本管理流程落地）**：按 `project-document-management` §6「工作目录仅保留当前最新版本」将 `doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.1.0.md`（批 1）与 `-v1.2.0.md`（批 2）移入 `doc/development/archive/`（**只读**，内容零改动），工作目录仅保留最新 `-v1.3.0.md`（批 4）；§2.5 两条条目路径同步为归档路径并标注「已归档（只读）」，DOCMAP-MANIFEST 两条路径同步更新（保持逐项真实存在、无失效引用、无游离）。**仅归档与路径同步，不改文档内容与 §1 分层** |

---

## 1. 分层模型（L0-L4）

> 承接《OpenBase-多系统对接-文档体系与升级路线规划-v1.0.0.md》§2 定案 C（不物理合并，按 L0-L4 分层 + 索引 + 强引用纪律）。

| 层 | 定位 | 职责 |
|----|------|------|
| **L0** | 治理根 | 问题全景 + 对策总纲 + 文档地图维护点（单一事实源） |
| **L1** | 域根（专项目标态） | 身份与主备双通道等专项的目标架构与任务定义 |
| **L2** | 设计基线 | 数据模型基线 + 隔离实现细则（R-H/M/L 规则） |
| **L3** | 立项 / 计划 | 各专项实施计划（任务 / 决策 / 验收） |
| **L4** | 台账 / 验证 | 决策记录、运行指南、验证记录、门禁台账、段级交付物 |

段级交付物（立项方案 / 设计草案 / DevLogReport / 测试报告 / 清单 / 执行模板）按其角色归入对应层，段号（S1a~S7）作为关联锚点登记。

---

## 2. L0-L4 全量文档清单

### 2.1 L0 治理根

| 名称 | 版本 | 角色 | 状态 | 关联锚点 |
|------|------|------|------|---------|
| OpenBase-多系统对接联调问题复盘与根治方案-v1.0.0.md | v1.0.0 | 治理根 / 文档地图维护点 | Final（演进中） | §8 承接总表；路线规划 §2.2 D-4 |
| OpenBase-多系统对接-文档体系与升级路线规划-v1.0.0.md | v1.0.0（内部 v1.1.0） | 文档体系与升级路线 | Review | §2 分层定案 C；§2.2 D-4 |
| OpenBase-多系统联调联试分阶段版本规划-子系统纵切-v1.0.0.md | v1.0.0（内部 v1.3.1） | 纵向阶段规划（S1a~S7） | Review | §3「S7 总收官段」 |
| OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md | v1.0.0（内部 v1.3.0） | 任务归集与版本规划 | Review | §3.8 / §4-5 |

### 2.2 L1 域根（专项目标态）

| 名称 | 版本 | 角色 | 状态 | 关联锚点 |
|------|------|------|------|---------|
| OpenBase-统一身份与主备双通道贯通总体方案-v1.0.0.md | v1.0.0 | 身份与通道目标架构 | Review | U1-U5 任务定义；L2-1/L2-2 |

### 2.3 L2 设计基线

| 名称 | 版本 | 角色 | 状态 | 关联锚点 |
|------|------|------|------|---------|
| OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0.md | v1.0.0（内部 v1.3.0） | 数据模型基线 + 隔离细则 | Review | §12 隔离实现细则（R-H/M/L） |
| doc/design/OpenBase-文档地图索引-v1.0.0.md | v1.0.0 | 文档地图（本索引） | Draft | S7-T1-5 / S7-T8-3 |
| doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md | v1.0.0 | K13 schema×账号×权限矩阵 | Draft | S7-T1-3 / 任务卡 K13 |

### 2.4 L3 立项 / 计划

| 名称 | 版本 | 角色 | 状态 | 关联锚点 |
|------|------|------|------|---------|
| OpenBase-P2-2-隔离与fail-open收口立项方案-v1.0.0.md | v1.0.0 | 隔离与 fail-open 立项 | Review | P2-2 |
| OpenBase-P2-2-隔离收口实施执行计划-v1.0.0.md | v1.0.0 | 隔离收口执行计划 | Review | P2-2 Phase1/2 |
| OpenBase-R1-隔离收口实施执行计划-v1.0.0.md | v1.0.0 | R1 隔离收口执行计划 | Review | R1 批次 |
| OpenBase-U1-统一身份收口立项方案-v1.0.0.md | v1.0.0 | U1 立项（S1a） | Approved | U1 T1~T4 |
| OpenBase-U1-统一身份收口设计草案-v1.0.0.md | v1.0.0 | U1 设计（S1a） | Approved | §8 事件契约 / §8.4 S7 钩子 |
| OpenBase-P2-1-统一身份协议头与信任链收口立项方案-v1.0.0.md | v1.0.0 | P2-1 立项（S1b） | Approved | P2-1 T1~T10 |
| OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md | v1.0.0 | P2-1 设计（S1b） | Approved | §9.2 OB-9 / §9.3 OB-7 / §11.4 RA-06 |
| OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0.md | v1.0.0（内部 v1.1.0） | S6 立项 | Approved | 22 断言 |
| OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md | v1.0.0 | S6 设计 | Approved | §4.6 / §9 |
| OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md | v1.0.0（内部 v1.1.0） | S7 立项（总收官） | Approved | 34 断言 + Q-S7-1~8 |
| OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0.md | v1.0.0（内部 v1.0.1） | S7 设计 | Approved | §4.1~§4.8 / §5 |
| OpenBase-DPS对接完善任务书-v1.0.0.md | v1.0.0 | DPS 对接任务书 | Review | L3 |
| OpenLLM-真实契约落地与沉淀收敛立项方案-v1.0.0.md | v1.0.0 | OpenLLM 立项 | Review | L3 |
| OpenLLM-need-star-统一编排实现方案-v0.1.0.md | v0.1.0 | OpenLLM 编排方案 | Review | L3 |

### 2.5 L4 台账 / 验证 / 段级交付物

| 名称 | 版本 | 角色 | 状态 | 关联锚点 |
|------|------|------|------|---------|
| OpenBase-四件套身份治理评审-R3R5-v1.0.0.md | v1.0.0 | 决策账 | Final | R3/R5 决策 |
| OpenBase-DPS对接使用指南-v1.0.0.md | v1.0.0 | 运行指南 | Final | DPS 对接 |
| OpenBase-数据隔离实现任务卡-v1.0.0.md | v1.0.0（内部 v1.7.0） | 24 卡台账（K01-K18 + RA-01~RA-06） | 演进中 | K13 / RA-06 / K07 / SYS-1 |
| OpenBase-真实联调冒烟清单-v1.0.0.md | v1.0.0（OB-INTG-SMOKE-v1.1.0） | 冒烟台账（S0-S6） | Draft | §3 用例矩阵 |
| OpenBase-存量测试对齐任务清单-v1.0.0.md | v1.0.0（内部 v1.2.0） | 存量测试对齐台账 | Draft | T1/T2/T3/T4 |
| doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md | v1.0.0（内部 v1.0.5） | 清点总清单 / 会签五步 | Review | §1.1 / §4.1 |
| doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md | v1.0.0（内部 v1.0.8） | 跨仓提交放行清单 | Review | §0 通用红线 / §1-§5 |
| doc/development/OpenBase-U1-统一身份收口-DevLogReport-v1.0.0.md | v1.0.0 | U1 开发记录 | Final | S1a |
| doc/test/OpenBase-U1-统一身份收口-测试报告-v1.0.0.md | v1.0.0 | U1 测试报告 | Final | S1a |
| doc/development/OpenBase-P2-1-统一身份协议头与信任链收口-DevLogReport-v1.0.0.md | v1.0.0 | P2-1 开发记录 | Final | S1b |
| doc/test/OpenBase-P2-1-统一身份协议头与信任链收口-测试报告-v1.0.0.md | v1.0.0 | P2-1 测试报告 | Final | S1b |
| doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md | v1.0.0 | S6 冻结口径登记 | Final | S6-T1 |
| doc/development/OpenBase-S6-统一前端隔离展示与段门禁收口-DevLogReport-v1.0.0.md | v1.0.0 | S6 开发记录 | Final | S6 |
| doc/test/OpenBase-S6-统一前端隔离展示与段门禁收口-测试报告-v1.0.0.md | v1.0.0 | S6 测试报告 | Final | S6 |
| doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md | v1.0.0（OB-INTG-S7-SIGNOFF-TPL-v1.0.0） | S7 执行模板 | Draft | S7-T7 |
| doc/development/OpenBase-S7-全域门禁与总收官-DevLogReport-v1.0.0.md | v1.0.0（OB-S7-DEVLOG-v1.0.0） | S7 开发记录报告（批 1~4 / SHR 收口 / 门禁聚合 / 台账回写 / 会签） | Review | S7 Step 2 |
| doc/development/archive/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.1.0.md | v1.1.0（OB-S7-DEVLOG-LOGS-v1.1.0） | S7 增量开发记录：**批 1（C-1~C-9）全量落地**（C-1 日志落盘 / C-2 入口接线与提交号注入 / C-3 用例上下文与 L1 日志 / C-4 审计落库 / C-5 出站透传 / C-6 服务日志采集 / C-7 聚合脚本 / C-8 查询过滤 / C-9 单测；含 §15 逐项 RED→GREEN、实跑证据、变更统计） | **已归档（只读）** | S7 Step 2 / 方案 §5.1 |
| doc/development/archive/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.2.0.md | v1.2.0（OB-S7-DEVLOG-LOGS-v1.2.0） | S7 增量开发记录：**批 2（C-10~C-12）落地**（C-10 受权 `test:record` 端点族 + best-effort 落 `audit_logs` / C-11 前端测试模式注入三测试头 / C-12 `/system/test-records` 面板；含 §15 逐项实施、23 例后端单测 + 147 例前端、覆盖率 98%） | **已归档（只读）** | S7 Step 2 / 方案 §5.1 |
| doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.3.0.md | v1.3.0（OB-S7-DEVLOG-LOGS-v1.3.0） | S7 增量开发记录（**当前有效版本**）：**批 4（C-15~C-19）落地**（C-15 网关响应观测 / C-16 上游响应专段 / C-17 错误归因分析器 / C-18 统一脱敏器 / C-19 三开关与开关审计留痕；含 §15 逐项实施、单测、覆盖率与回归证据、TDD 顺序如实说明） | Review | S7 Step 2 / 方案 §5.1 |
| doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md | v1.0.0（OB-S7-TEST-v1.0.0） | S7 测试报告（34 断言矩阵 + 段门禁六项聚合结论） | Review | S7 Step 3 |
| doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md | v1.0.0（内部 v1.0.1，OB-S7-CLOSURE-v1.0.0） | S7 总收官报告（单文件形态；六项聚合 + PENDING + 会签 + 遗留） | Review | S7-T8-4 / S7-T8-5 |
| doc/planning/OpenBase-S7-联调窗口环境检查报告-v1.0.0.md | v1.0.0（OB-S7-ENVCHECK-v1.0.0） | S7 P2 联调窗口前置环境检查报告（17 项实测 + 处置建议 + 就绪度矩阵） | Draft | S7-§0.1 / S7-P2-ENV |

### 2.6 S7 新增收口资产与证据（脚本 / 契约 / 证据）

> 承接 S7-T1（SHR 五项收口）、S7-T2~T5（联调窗口工具脚本 L1-1/L2-1/L2-2/L3-1/L3-2）与 S7-T6/T8（门禁聚合与回写）；脚本与证据亦纳入机器可核对清单（§4），保持「无游离」。

| 名称 | 版本 | 角色 | 状态 | 关联锚点 |
|------|------|------|------|---------|
| scripts/verify-env/contract.global.json | schema_version=1 | 跨仓统一 verify-env 契约（主结构 + repo_overrides） | 已产出（S7 批 1） | S7-T1-1 |
| scripts/verify_env_global.ps1 | v1.0.0 | verify-env 全局入口（-Repos / 两段式收紧） | 已产出（S7 批 1） | S7-T1-1 |
| scripts/db/init_openbase_test.ps1 | v1.0.0 | openbase_test 建库/建账号/幂等迁移脚本 | 已产出（S7 批 1） | S7-T1-2 |
| scripts/db/grant_k13_accounts.ps1 | v1.0.0 | K13 授权收敛脚本（不授 superuser） | 已产出（S7 批 1） | S7-T1-3 |
| scripts/scan_orchestrator_bypass.py | v1.0.0 | 编排禁批量杀静态扫描（0 绕过命中） | 已产出（S7 批 1） | S7-T1-4 |
| scripts/gate_aggregate.py | v1.0.0 | 门禁聚合脚本（单命令 / 单批 / 结构化 JSON） | 已产出（S7 批 2） | S7-T6-1~4 |
| doc/test/evidence/s7/gate/gate-aggregate.json | schema_version=1 | 门禁聚合证据（RA-06 / 冒烟 / 对齐清单 / K07-SYS-1 / SHR） | 已产出（S7 批 2） | S7-T6 / S7-T8-5 |
| doc/test/evidence/s7/t8/writeback-check.json | schema_version=1 | S7-T8 回写核对证据（24 卡 / 七线 / 无游离 / 报告章节） | 已产出（S7 批 3） | S7-T8-1~5 |
| scripts/verify_l1_1_cascade.ps1 | v1.0.0（骨架 + 干跑） | S7-T2 L1-1 级联全链核验（DPS/OpenMemory 阻断 / 幂等 / purge；真实执行 PENDING） | 骨架已就绪（干跑 PENDING） | S7-T2-1~4 |
| scripts/drill_l2_1_failover.ps1 | v1.0.0（骨架 + 干跑） | S7-T3 L2-1 主备切换演练（双场景 + 演练报告模板；真实执行 PENDING） | 骨架已就绪（干跑 PENDING） | S7-T3-1~4 |
| scripts/finalize_l2_2_matrix.py | v1.0.0（骨架 + 干跑） | S7-T4 L2-2 通道矩阵终验（复用 S4-T8 matrix_rows 语义 + K07 豁免对账） | 骨架已就绪（干跑 PENDING） | S7-T4-1~4 |
| scripts/verify_l3_1_agent.ps1 | v1.0.0（骨架 + 干跑） | S7-T5 L3-1 Agent 端到端（四头 / 白名单 / 域隔离 / 403 + M1-M2） | 骨架已就绪（干跑 PENDING） | S7-T5-1~4 |
| scripts/smoke_l3_2.py | v1.0.0（骨架 + 干跑） | L3-2 贯通冒烟（OpenBase 侧缺失项；受信通道端到端关键路径） | 骨架已就绪（干跑 PENDING） | S7-T6-2 / S7-T7-3 |
| doc/test/evidence/s7/env/env-check.json | schema_version=1 | S7 P2 联调窗口环境检查证据（真实 PG/openbase_test / Redis / IdP / 四仓运行态 / 网关与前端 / Playwright / 四仓远端写权限） | 已产出（P2 环境只读探测） | S7-§0.1 / S7-P2-ENV |
| doc/design/OpenBase-人工端到端测试日志记录方案-v1.0.0.md | **v1.4.0（[Approved]）** | 人工端到端测试日志记录方案（现状 4 缺口 / 三层记录通道 / 字段与事件字典（含头承载口径）/ 用例上下文贯穿 / 改造清单 C-1~C-19 / §5.1 批 1（C-1~C-9）+ 批 2（C-10~C-12）+ 批 4（C-15~C-19）实施进度 / §11 响应级观测与错误归因 / §11.8 跨仓前提实测核实 / §9.1 决议记录 / 验收标准；v1.1.2 移除 C-1 的按保留期自动清理以遵循不变量 T6-1；v1.2.0 记批 1 全量落地并补 `X-Test-Run-Id` 头口径；v1.4.0 记批 4 落地并补 digest 口径差异、采集需启动期置开关、专用代理族接线范围） | **已批准（2026-09-13 决议冻结；v1.1.1~v1.4.0 为实施期文档对齐、修订与补充）** | 联调期人工测试留痕（补充证据；D-3 决议不参与门禁判定） |
| doc/design/OpenBase-D6四仓request_id日志接线改动说明-v1.0.0.md | v1.0.0（[Draft]） | D-6 跨仓施工说明（四仓现状实证 / 统一约定 / 逐仓改动与代码片段 / 验收标准 / 改动一览 / 风险 R-1~R-7） | 待各仓评审（跨仓依据） | D-6 = ②（四仓补齐 request_id 接线）；依据方案 v1.1.0 §11.8 |
| scripts/test_log_aggregate.py | v1.0.0（内部：批 1 C-7） | 人工测试日志聚合器（`logs/**/*.jsonl` → `doc/test/evidence/manual/<run_id>.{json,md}`；退出码 0=PASS / 1=FAIL / 2=PENDING） | 已落地（TDD 8 例 + PASS/FAIL 双路径实跑） | 方案 §5 C-7 / §3.1 L3 |
| doc/test/evidence/manual/run-20260914-0230.json｜.md、run-20260914-0225.json｜.md | 运行期证据（PASS / FAIL 各一轮） | 人工测试日志聚合证据（run → case → step + `request_id` 双证据） | 已产出（批 1 实跑回填） | 方案 §3.1 L3 / §5 C-7 |
| scripts/test_log_analyze.py | v1.0.0（内部：批 4 C-17） | 错误归因分析器（`logs/**/*.jsonl` → `doc/test/evidence/manual/<run_id>-analysis.md`；归属层矩阵 + 首现标记 + 建议动作；**不含响应明文**；退出码 0=无失败 / 1=有失败 / 2=PENDING） | 已落地（TDD 7 例 + 归因矩阵逐行核对） | 方案 §5 C-17 / §11.5 / §11.6 |
| doc/test/evidence/manual/batch4-unit-junit.xml | 运行期证据（批 4 单测） | 批 4 新增单测 JUnit 证据（C-15/C-16/C-17/C-18/C-19 用例逐项留痕） | 已产出（批 4 实跑回填） | 方案 §5 批 4 / §6 验收 |
| doc/test/evidence/manual/batch4-regression2-junit.xml | 运行期证据（批 4 定向回归，pytest 采集序） | 批 4 定向回归 JUnit 证据（审计/代理/身份/设置等受影响面按 pytest 采集序运行） | 已产出（批 4 实跑回填） | 方案 §6 验收（回归） |
| doc/test/evidence/manual/run-20260914-0230-analysis.md、run-20260914-0225-analysis.md | 运行期证据（真实轮次的归因报告） | 错误归因分析器在真实轮次上的产物（PASS 退出码 0 / FAIL 退出码 1 + 归属层） | 已产出（批 4 实跑回填） | 方案 §5 C-17 / §11.6 |

---

## 3. S1a~S7 纵切新增文档并入核对表

> 判据：各段「立项 / 设计草案 / DevLog / 测试报告 / 台账 / 清单 / 执行模板」逐项并入本索引（§2 或本表）；**差异 0 或显式登记**，即「无游离文档」。

| 段 | 立项方案 | 设计草案 | DevLogReport | 测试报告 | 台账/清单/执行模板 | 并入结论 |
|----|---------|---------|-------------|---------|-------------------|---------|
| S1a（U1） | OpenBase-U1-统一身份收口立项方案-v1.0.0.md | OpenBase-U1-统一身份收口设计草案-v1.0.0.md | doc/development/OpenBase-U1-统一身份收口-DevLogReport-v1.0.0.md | doc/test/OpenBase-U1-统一身份收口-测试报告-v1.0.0.md | — | 已并入 |
| S1b（P2-1） | OpenBase-P2-1-统一身份协议头与信任链收口立项方案-v1.0.0.md | OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md | doc/development/OpenBase-P2-1-统一身份协议头与信任链收口-DevLogReport-v1.0.0.md | doc/test/OpenBase-P2-1-统一身份协议头与信任链收口-测试报告-v1.0.0.md | — | 已并入 |
| S1b'（P2-2 / R1） | OpenBase-P2-2-隔离与fail-open收口立项方案-v1.0.0.md | — | — | — | OpenBase-P2-2-隔离收口实施执行计划-v1.0.0.md；OpenBase-R1-隔离收口实施执行计划-v1.0.0.md | 已并入 |
| S6（前端段） | OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0.md | OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md | doc/development/OpenBase-S6-统一前端隔离展示与段门禁收口-DevLogReport-v1.0.0.md | doc/test/OpenBase-S6-统一前端隔离展示与段门禁收口-测试报告-v1.0.0.md | doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md | 已并入 |
| S7（总收官段） | OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md | OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0.md | doc/development/OpenBase-S7-全域门禁与总收官-DevLogReport-v1.0.0.md | doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md | doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md；doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md；doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md；doc/test/evidence/s7/gate/gate-aggregate.json；doc/test/evidence/s7/t8/writeback-check.json；本索引 | 已并入（v1.0.2 增补 DevLog/测试报告；v1.0.3 增补联调窗口工具脚本 L1-1/L2-1/L2-2/L3-1/L3-2；v1.0.4 增补联调窗口环境检查报告与 env-check 证据；v1.0.12 增补批 2/批 4 实施记录 DevLogReport 与 C-17 错误归因分析器；v1.0.13 归档 DevLogReport 旧版并同步索引路径；S7 段交付物齐备） |

**台账/清单（跨段）**：OpenBase-数据隔离实现任务卡-v1.0.0.md、OpenBase-真实联调冒烟清单-v1.0.0.md、OpenBase-存量测试对齐任务清单-v1.0.0.md、doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md、doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md —— 均已并入 §2.5。

---

## 4. 无游离核对判据与机器可核对清单

**核对判据**：
1. 本索引 §2 + §3 覆盖 L0-L4 全量文档；任一新增段级文档须同步并入（差异 0 或显式登记「待产出」）；
2. 下列「机器可核对清单」逐项均在仓内真实存在（无失效引用 / 无游离文档）；
3. 反向核对：S1a~S7 纵切新增文档均可在本索引命中（`tests/test_s7_t1_shr.py::test_s7_t1_5_s1a_s7_documents_merged`）。

<!-- DOCMAP-MANIFEST:BEGIN -->
- OpenBase-多系统对接联调问题复盘与根治方案-v1.0.0.md
- OpenBase-多系统对接-文档体系与升级路线规划-v1.0.0.md
- OpenBase-多系统联调联试分阶段版本规划-子系统纵切-v1.0.0.md
- OpenBase-多系统联调联试-子系统任务归集与版本规划-v1.0.0.md
- OpenBase-统一身份与主备双通道贯通总体方案-v1.0.0.md
- OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0.md
- doc/design/OpenBase-文档地图索引-v1.0.0.md
- doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md
- OpenBase-P2-2-隔离与fail-open收口立项方案-v1.0.0.md
- OpenBase-P2-2-隔离收口实施执行计划-v1.0.0.md
- OpenBase-R1-隔离收口实施执行计划-v1.0.0.md
- OpenBase-U1-统一身份收口立项方案-v1.0.0.md
- OpenBase-U1-统一身份收口设计草案-v1.0.0.md
- OpenBase-P2-1-统一身份协议头与信任链收口立项方案-v1.0.0.md
- OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md
- OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0.md
- OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md
- OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md
- OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0.md
- OpenBase-DPS对接完善任务书-v1.0.0.md
- OpenLLM-真实契约落地与沉淀收敛立项方案-v1.0.0.md
- OpenLLM-need-star-统一编排实现方案-v0.1.0.md
- OpenBase-四件套身份治理评审-R3R5-v1.0.0.md
- OpenBase-DPS对接使用指南-v1.0.0.md
- OpenBase-数据隔离实现任务卡-v1.0.0.md
- OpenBase-真实联调冒烟清单-v1.0.0.md
- OpenBase-存量测试对齐任务清单-v1.0.0.md
- doc/planning/OpenBase-联调产物清点核对总清单-v1.0.0.md
- doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md
- doc/development/OpenBase-U1-统一身份收口-DevLogReport-v1.0.0.md
- doc/test/OpenBase-U1-统一身份收口-测试报告-v1.0.0.md
- doc/development/OpenBase-P2-1-统一身份协议头与信任链收口-DevLogReport-v1.0.0.md
- doc/test/OpenBase-P2-1-统一身份协议头与信任链收口-测试报告-v1.0.0.md
- doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md
- doc/development/OpenBase-S6-统一前端隔离展示与段门禁收口-DevLogReport-v1.0.0.md
- doc/test/OpenBase-S6-统一前端隔离展示与段门禁收口-测试报告-v1.0.0.md
- doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md
- doc/development/OpenBase-S7-全域门禁与总收官-DevLogReport-v1.0.0.md
- doc/development/archive/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.1.0.md
- doc/development/archive/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.2.0.md
- scripts/test_log_aggregate.py
- scripts/test_log_analyze.py
- doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.3.0.md
- doc/test/evidence/manual/batch4-unit-junit.xml
- doc/test/evidence/manual/batch4-regression2-junit.xml
- doc/test/evidence/manual/run-20260914-0230-analysis.md
- doc/test/evidence/manual/run-20260914-0225-analysis.md
- doc/test/evidence/manual/run-20260914-0230.json
- doc/test/evidence/manual/run-20260914-0230.md
- doc/test/evidence/manual/run-20260914-0225.json
- doc/test/evidence/manual/run-20260914-0225.md
- doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md
- doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md
- doc/planning/OpenBase-S7-联调窗口环境检查报告-v1.0.0.md
- doc/test/evidence/s7/gate/gate-aggregate.json
- doc/test/evidence/s7/t8/writeback-check.json
- doc/test/evidence/s7/env/env-check.json
- scripts/verify-env/contract.global.json
- scripts/verify_env_global.ps1
- scripts/db/init_openbase_test.ps1
- scripts/db/grant_k13_accounts.ps1
- scripts/scan_orchestrator_bypass.py
- scripts/gate_aggregate.py
- scripts/verify_l1_1_cascade.ps1
- scripts/drill_l2_1_failover.ps1
- scripts/finalize_l2_2_matrix.py
- scripts/verify_l3_1_agent.ps1
- scripts/smoke_l3_2.py
- doc/design/OpenBase-人工端到端测试日志记录方案-v1.0.0.md
- doc/design/OpenBase-D6四仓request_id日志接线改动说明-v1.0.0.md
<!-- DOCMAP-MANIFEST:END -->

---

## 5. 维护与边界

| 项 | 说明 |
|----|------|
| 维护点 | 本索引为地图正文落点（路线规划 §2.2 D-4）；S7-T8-3 与 S7-T1-5 共用同一事实源 |
| 更新纪律 | 新增 L0-L4 文档或段级交付物时，须同步并入本索引并递增版本（主/次/修订号）与修订历史 |
| 边界 | 各子系统仓（OpenMemory / OpenRAG / OpenLLM / DPS）仓内文档不在本索引范围，由各仓各自索引维护；跨仓契约以执行模板与清点总清单承载 |
| 回滚 | 本索引为新增只读维护点，停止维护/删除即回退（不影响其他文档正文） |
