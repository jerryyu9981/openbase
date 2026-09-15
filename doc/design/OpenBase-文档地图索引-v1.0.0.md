# OpenBase-文档地图索引-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-DOCMAP-INDEX-v1.0.0 |
| 版本 | v1.0.22 |
| 状态 | [Draft]（S7-T1-5 产出；v1.0.1 S7-T8-3 增补 S7 新增条目与证据索引；v1.0.2 增补 S7 DevLogReport / 测试报告条目；v1.0.3 增补 S7 联调窗口工具脚本 L1-1/L2-1/L2-2/L3-1/L3-2 条目；v1.0.4 增补 S7 联调窗口环境检查报告与 env-check 证据条目；v1.0.5 增补人工端到端测试日志记录方案条目；v1.0.6 该方案升版 v1.0.1（补 §11 响应级观测与错误归因、D-5 红线）并同步条目描述；v1.0.7 该方案升版 v1.0.2（并入 §11.8 跨仓前提实测核实 + D-6）并同步条目描述；v1.0.8 该方案升版 v1.1.0 并置 [Approved]（决议冻结 §9.1）并同步条目描述；v1.0.9 增补 D-6 四仓 request_id 日志接线改动说明条目；v1.0.10 登记批 1 里程碑（C-1+C-6）实施记录 DevLogReport 条目并同步方案条目至 v1.1.1；v1.0.11 该 DevLogReport 升版 v1.1.0（批 1 C-1~C-9 全量落地）并同步方案条目至 v1.2.0、增补聚合脚本与人工测试证据条目；v1.0.12 登记批 2（C-10~C-12）与批 4（C-15~C-19）实施记录 DevLogReport 条目、方案条目同步至 v1.4.0、增补错误归因分析器与批 4 单测/回归证据条目；v1.0.13 该 DevLogReport 家族按版本管理流程归档旧版（v1.1.0/v1.2.0 → `doc/development/archive/`，只读）并同步条目路径；v1.0.14 增补批 5 实施记录条目并将批 4 记录标注归档（该次元信息版本字段未同步，本次一并勘正为 v1.0.15）；v1.0.15 增补人工端到端测试日志落盘 **Step 4 测试用例 / 测试报告 / 测试回溯对比审计报告** 三份条目与 `t4-*` 运行期证据（8 项）；v1.0.16 增补**联调窗口真实面执行证据**（`t4-checkall.txt`、`smoke-summary-t4{,-noollama}.json`、`s7/l1-1/t4`、`l2-2/matrix-finalize-t4.json`、`l3-1/t4`、`l3-2/smoke-result-t4.json`、`run-20260914-2146.{json,md}` 与 `-analysis.md`、`t4-manual-e2e-summary.json`、`t4-frontend-e2e.txt`）与**新增回归测试** `tests/test_log_reserved_keys.py`（缺陷 AD-20260914-02 防复发）；v1.0.17 增补 **S7-T3 主备切换演练证据**（`s7/l2-1/t4/failover-drill.json` + `drill-report.md`、`t4-l2-1-outage-drill.json`、`run-l2-1-20260914-2210-analysis.md`、`t4-checkall-after-drill.txt`）并同步执行单 P2-T3 状态；v1.0.18 增补 **S7-T2-4 purge 正例证据**（`t4-t2-4-purge.json` / `.txt`）并同步测试报告 v1.3.0、回溯审计 v1.3.0、执行单 v1.0.13；**v1.0.19 增补"全页面操作日志走查 + O-12 端点真实负载复跑"证据（6 组 `t4-all-pages-oplog-walkthrough*.json` / `t4-o12-real-payload-rerun*.json`）并同步测试报告 v1.4.0**；**v1.0.20 同步回溯审计镜像条目至内部 v1.4.0（含 §9.2#11 走查复核、观察项 O-11~O-13、边界声明）**；**v1.0.21 同步性能量化与审计落库异步化改造（TT-LOGS-056）：测试报告条目 → 内部 v1.5.0、回溯审计条目 → 内部 v1.5.0、DevLogReport 条目 → 内部 v1.6.0，并增补 §2.6 性能/异步化证据 11 项与新增回归测试条目**；随 S7 段门禁批准回写 [Approved]） |
| 日期 | 2026-09-11 |
| 作者 | AI（沙箱侧现状实测与索引编制；批 1/批 2/批 4/批 5 开发会话增补；批 6 测试阶段会话增补 Step 4 测试用例 / 测试报告 / 回溯审计条目） |
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
| v1.0.14 | 2026-09-14 | AI（S7 批 5 开发会话） | **批 5（专用代理族上游专段接线）实施记录并入 + 批 4 记录归档**：§2.5 新增一行（`doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.4.0.md`，[Review]，当前有效版本）并将 `-v1.3.0.md`（批 4）标注「已归档（只读）」；§2.6 方案条目版本由 v1.4.0 同步至 **v1.5.0**（§5.1 增列批 5 进度行与实施期补充：五族同一观测出口、SSE 头部级口径）；§2.6 增补四行（`batch5-unit-junit.xml`、`batch5-proxy-regression-junit.xml`、`batch5-full-regression-junit.xml`、`batch5-pg-flake-recheck-junit.xml`）；DOCMAP-MANIFEST 同步增补五条并同步一条归档路径，保持逐项真实存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目** |
| v1.0.15 | 2026-09-14 | AI（S7 批 6 测试阶段会话） | **「人工端到端测试日志落盘」流 Step 4 测试阶段交付物并入**：§2.5 新增三行（`doc/test/OpenBase-S7-人工端到端测试日志落盘-测试用例-v1.0.0.md`（59 条 TT-LOGS，[Review]）、`doc/test/OpenBase-S7-人工端到端测试日志落盘-测试报告-v1.0.0.md`（Step 4 报告，[Review]）、`doc/audit/verification/OpenBase-S7-人工端到端测试日志落盘-测试回溯对比审计报告-v1.0.0.md`（验证审计，[Review]））；§2.6 增补八行（`t4-stream-core-junit.xml` / `t4-audit-db-persist-junit.xml` / `t4-stream-unit-junit.xml` / `t4-proxy-regression-junit.xml` / `t4-full-regression-junit.xml` / `t4-pg-flake-recheck-junit.xml` / `t4-coverage.txt` / `t4-frontend-vitest.txt`）；§3 S7 行「并入结论」同步；**元信息版本字段自 v1.0.14 起未同步，本次一并勘正为 v1.0.15**；DOCMAP-MANIFEST 同步增补十一条并保持逐项真实存在（无游离）。**仅增补条目与清单，不改 §1 分层与既有条目；本仓未改动业务代码** |
| v1.0.16 | 2026-09-14 | AI（S7 批 7 联调窗口真实面执行会话） | **联调窗口真实面执行证据与回归测试并入**：§2.6 新增十二行（`t4-checkall.txt`（27 PASS）/ `smoke-summary-t4.json`（25/2/5，另存 noollama 对照轮）/ `t4-dps-proxy-trustchain-probe.json`（信任链口径探针）/ `s7/l1-1/t4/cascade-result.json` / `s7/l2-2/matrix-finalize-t4.json` / `s7/l3-1/t4/agent-e2e.json`（T5-4 FAIL→PASS）/ `s7/l3-2/smoke-result-t4.json` / `t4-defect-apikeys-500.json`（P1 缺陷 AD-20260914-02 复现）/ `run-20260914-2146.{json,md}` 与 `-analysis.md` / `t4-manual-e2e-summary.json`、`t4-manual-e2e.txt` / `t4-frontend-e2e.txt` / `tests/test_log_reserved_keys.py`（防复发回归 4 例））；§2.5 三份 Step 4 文档版本同步（测试报告 → v1.1.0、回溯审计 → v1.1.0）；DOCMAP-MANIFEST 同步增补两条 `.md` 证据并保持逐项真实存在（无游离）。**仅增补条目与清单；本仓代码改动（AD-20260914-02 修复 3 文件 +5/−5）已随测试报告 §13.7/§13.11 登记** |
| v1.0.17 | 2026-09-14 | AI（S7 批 8 主备切换演练会话） | **S7-T3 主备切换演练证据并入**：§2.6 新增两行（`s7/l2-1/t4/failover-drill.json` + `drill-report.md`（演练本体 T3-1~T3-4 全 PASS）、`t4-l2-1-outage-drill.json` + `run-l2-1-20260914-2210-analysis.md` + `t4-checkall-after-drill.txt`（真实上游中断注入 + 恢复后 27 PASS））；DOCMAP-MANIFEST 同步增补两条 `.md` 并保持逐项真实存在（无游离）。**仅增补条目与清单；本仓未改动代码；T3 为 S7 段断言（非 TT-LOGS 用例），其状态同步回填 `doc/planning/OpenBase-S7-沙箱外执行单-v1.0.0.md` §2.2 P2-T3** |
| v1.0.18 | 2026-09-14 | AI（S7 批 9 purge 正例关闭会话） | **S7-T2-4 purge 正例证据并入**：§2.6 新增一行（`t4-t2-4-purge.json` + `t4-t2-4-purge.txt`：签发授权码 → purge 200 / 负例 403 / 重复 400 终态 / 留痕 `purge_records` + `audit_logs(identity.purge)`）；§2.5 三份 Step 4 文档版本同步（测试报告 → v1.3.0、回溯审计 → v1.3.0、执行单 → v1.0.13）；MANIFEST 无新增 `.md`（本次证据为 `.json`/`.txt`）；元信息版本字段自 v1.0.17 同步至 **v1.0.18**。**仅增补条目与清单；本仓未改动代码** |
| v1.0.19 | 2026-09-14 | AI（S7 批 10 全页面操作日志走查会话） | **全页面操作日志走查 + O-12 复跑证据并入**：§2.6 新增两行（`t4-all-pages-oplog-walkthrough{,-2,-3}.json｜.txt`：59 项真实操作 / 24 个调后端页面 / 58 项命中 L1 `api.request`（到达网关 100% 留痕）+ 审计库双落库；`t4-o12-real-payload-rerun{,-b,-c}.json｜.txt`：5 端点按页面真实 payload 复跑 **5/5 → 200**，首跑 422 根因全为探针负载口径）；§2.5 测试报告条目版本同步至 **v1.4.0**（新增 §14）；元信息版本字段自 v1.0.18 同步至 **v1.0.19**。**仅增补条目与清单；本仓未改动代码**（走查与复跑均为只读/可回滚写，未新增或修改业务代码） |
| v1.0.20 | 2026-09-14 | AI（S7 批 11 审计同步会话） | **回溯审计镜像条目同步至内部 v1.4.0**：§2.5 该审计条目描述更新为「v1.1.0 §9 联调窗口真实面复核 + P1 缺陷闭环审计 / v1.2.0 S7-T3 演练复核 / v1.3.0 S7-T2-4 purge 正例复核 / **v1.4.0 全页面操作日志走查复核（§9.2#11）+ 观察项 O-11~O-13（O-12 已关闭）+ 边界声明**」，并在 §2.5 顶部条目列表保留其 [Review] 状态；元信息版本字段自 v1.0.19 同步至 **v1.0.20**；`doc/test/evidence/manual` 本轮 12 份新证据已由 v1.0.19 条目覆盖（无新增 `.md`，MANIFEST 不变）。**仅同步条目描述与版本字段；本仓未改动代码** |
| v1.0.21 | 2026-09-14 | AI（S7 批 12 性能整改与文档同步会话） | **性能量化与审计落库异步化改造并入（TT-LOGS-056）**：① §2.5 三份条目版本与描述同步——测试报告条目 → 内部 **v1.5.0**（新增 §15 性能与容量量化 + 异步化整改验证）、回溯审计条目 → 内部 **v1.5.0**（新增 §9.2#12、§9.4 O-14、§9.7 复核、§9.6 条件收敛）、DevLogReport 条目 → 内部 **v1.6.0**（新增 §18 审计落库异步化改造）；② §2.6 增补 **8 行**证据/测试条目（`t4-perf-tt056.{json,txt}`、`t4-perf-tt056-{A,A2,A3,B,B2,C}.txt`（6 份）、`t4-perf-micro{,-db}.{json,txt}`、`t4-perf-tt056-verdict.{json,txt}`、`t4-async-persist-verify.{json,txt}`、`t4-async-persist-full-junit{,-2}.xml`、`tests/test_audit_persist_queue.py`）；③ §3 S7 行「并入结论」追加本轮并入说明；④ 元信息版本字段自 v1.0.20 同步至 **v1.0.21**；⑤ **MANIFEST 同步增补 8 条**（1 个 `.py` 测试 + 7 份 `.json`/`.xml` 证据；无新增 `.md`），保持逐项真实存在（无游离）。**本轮代码改动（`openbase/modules/audit/__init__.py`、`openbase/demo_app.py` + 1 新测试文件 + 2 测试文件同步）由测试报告 §15 与 DevLogReport §18 登记，本索引仅做条目与清单同步** |
| v1.0.22 | 2026-09-15 | PM-OpenBase-Dev（R-384 可行性粗筛会话） | **R-384 可行性粗筛产物并入**：§2 L0-L4 清单新增 **`doc/planning/OpenBase-R384-四仓日志接入可行性粗筛与D6施工量评估-v1.0.0.md`**（含五方日志/持久化实测、D-6 施工量 ≈4.2 人天、完整链路 12~15 人天、7 项前置依赖、7 项风险）；元信息版本字段自 v1.0.21 同步至 **v1.0.22**。**⚠️ 已知待办（显式声明，非静默遗漏）**：v1.4.6 流（Step 0 四份 + Step 1 六份 + Step 2 十份，含六份设计文档、两份原型、两份审计）**尚未逐条并入本索引 §2.5/§2.6 与 MANIFEST**，计划在 **v1.4.6 Step 2 回溯重出**批次内一次性同步（届时按"逐项真实存在、无游离"口径核对）；本条仅登记本轮新增文档与版本字段。**本轮未改动任何生产代码** |

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
| doc/development/archive/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.3.0.md | v1.3.0（OB-S7-DEVLOG-LOGS-v1.3.0） | S7 增量开发记录：**批 4（C-15~C-19）落地**（C-15 网关响应观测 / C-16 上游响应专段 / C-17 错误归因分析器 / C-18 统一脱敏器 / C-19 三开关与开关审计留痕；含 §15 逐项实施、单测、覆盖率与回归证据、TDD 顺序如实说明） | **已归档（只读）** | S7 Step 2 / 方案 §5.1 |
| doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.4.0.md | v1.4.0（内部 **v1.6.0**，OB-S7-DEVLOG-LOGS-v1.4.0） | S7 增量开发记录（**当前有效版本**）：**批 5（专用代理族上游专段接线，批 4 §14#2 收尾）落地**（`publish_upstream_response` 统一出口 / 四族非流式出口接线 / SSE 头部级专段 / 缺陷 AD-20260914-01 修复；含 §16 逐项实施、单测、覆盖率与全量回归证据）；**v1.5.0 联调窗口缺陷修复（P1 AD-20260914-02 闭环，§17）**；**v1.6.0 审计落库异步化改造（TT-LOGS-056 性能整改：请求路径零 await DB + writer 协程批内单次提交；§18，新增区域覆盖率 100%）** | Review | S7 Step 2 / 方案 §5.1 |
| doc/test/OpenBase-S7-人工端到端测试日志落盘-测试用例-v1.0.0.md | v1.0.0（OB-S7-TC-LOGS-v1.0.0） | S7 增量测试用例基线：**59 条 TT-LOGS**（G1 日志链路 / G2 人工结论入口 / G3 响应级观测与归因 / G4 专用代理族接线 / G5 契约与回归门禁 / G6 沙箱外与跳过项）；逐条关联设计条目 C-x、代码落点、真实测试文件与用例名、断言级别与执行面 | Review | S7 Step 4 / 方案 §5.1 / §6 |
| doc/test/OpenBase-S7-人工端到端测试日志落盘-测试报告-v1.0.0.md | v1.0.0（内部 **v1.5.0**，OB-S7-TEST-LOGS-v1.0.0） | S7 增量测试报告（Step 4）：沙箱面（入场抽查 3/3、8 项实跑、覆盖率 96%）+ 联调窗口真实面（7 服务编排 / checkall 27 PASS / 冒烟 25/2/5 / T2·T4·T5 真实执行 / 真实人工 E2E（开关开启，归因 3/3）/ 前端 E2E 9/9）+ S7-T3 主备切换演练（含停服窗口内真实中断注入）+ S7-T2-4 purge 正例 + v1.4.0 全页面操作日志走查（78 项实测，到达网关 100% 留痕）与 O-12 关闭；含 P1 缺陷 AD-20260914-02 闭环；**v1.5.0 性能与容量量化（TT-LOGS-056：L1 0.0889ms/条、审计落库 12.865ms/请求→异步化后 0.0037ms、容量 2.47MB/日）与异步化整改验证（§15）** | Review | S7 Step 4 / 方案 §6 |
| doc/audit/verification/OpenBase-S7-人工端到端测试日志落盘-测试回溯对比审计报告-v1.0.0.md | v1.0.0（内部 **v1.5.0**，OB-S7-AUDIT-VERIFY-LOGS-v1.0.0） | S7 增量**测试回溯对比审计报告**（验证审计）：设计→用例→执行→证据逐条回溯 100%、门禁独立复算、T1→T4 层间追溯矩阵、产出物存在性验证；**v1.1.0 §9 联调窗口真实面复核 + P1 缺陷闭环审计**；**v1.2.0 S7-T3 主备切换演练复核**；**v1.3.0 S7-T2-4 purge 正例复核**；**v1.4.0 全页面操作日志走查复核（§9.2#11）+ 观察项 O-11~O-13（O-12 已关闭）+ 边界声明**；**v1.5.0 性能与容量量化复核 + 审计落库异步化改造复核（§9.2#12 / §9.7；新增观察项 O-14；条件收敛至仅余文档状态升级）**；结论「通过（有条件）」 | Review | S7 Step 4 / 方案 §9.1 |
| doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md | v1.0.0（OB-S7-TEST-v1.0.0） | S7 测试报告（34 断言矩阵 + 段门禁六项聚合结论） | Review | S7 Step 3 |
| doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md | v1.0.0（内部 v1.0.1，OB-S7-CLOSURE-v1.0.0） | S7 总收官报告（单文件形态；六项聚合 + PENDING + 会签 + 遗留） | Review | S7-T8-4 / S7-T8-5 |
| doc/planning/OpenBase-S7-联调窗口环境检查报告-v1.0.0.md | v1.0.0（OB-S7-ENVCHECK-v1.0.0） | S7 P2 联调窗口前置环境检查报告（17 项实测 + 处置建议 + 就绪度矩阵） | Draft | S7-§0.1 / S7-P2-ENV |
| doc/planning/OpenBase-R384-四仓日志接入可行性粗筛与D6施工量评估-v1.0.0.md | v1.0.0（OB-PLAN-R384-FEASIBILITY-D6-EFFORT-v1.0.0） | **R-384 四仓日志接入**可行性粗筛（Step 0 活动 0.1）：五方日志与持久化实测 + **D-6 施工量（≈4.2 人天）** + 完整链路缺口 G1~G6（8~10.5 人天，合计 **12~15 人天**） + 7 项前置依赖 + 7 项风险（P1×2） | Draft | R-384 / 候选需求池 §1.12 |

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
| doc/design/OpenBase-人工端到端测试日志记录方案-v1.0.0.md | **v1.5.0（[Approved]）** | 人工端到端测试日志记录方案（现状 4 缺口 / 三层记录通道 / 字段与事件字典（含头承载口径）/ 用例上下文贯穿 / 改造清单 C-1~C-19 / §5.1 批 1（C-1~C-9）+ 批 2（C-10~C-12）+ 批 4（C-15~C-19）+ 批 5（专用代理族接线）实施进度 / §11 响应级观测与错误归因 / §11.8 跨仓前提实测核实 / §9.1 决议记录 / 验收标准；v1.1.2 移除 C-1 的按保留期自动清理以遵循不变量 T6-1；v1.2.0 记批 1 全量落地并补 `X-Test-Run-Id` 头口径；v1.4.0 记批 4 落地并补 digest 口径差异、采集需启动期置开关、专用代理族接线范围；v1.5.0 记批 5 落地并补「五族同一观测出口」与 SSE 头部级口径） | **已批准（2026-09-13 决议冻结；v1.1.1~v1.5.0 为实施期文档对齐、修订与补充）** | 联调期人工测试留痕（补充证据；D-3 决议不参与门禁判定） |
| doc/design/OpenBase-D6四仓request_id日志接线改动说明-v1.0.0.md | v1.0.0（[Draft]） | D-6 跨仓施工说明（四仓现状实证 / 统一约定 / 逐仓改动与代码片段 / 验收标准 / 改动一览 / 风险 R-1~R-7） | 待各仓评审（跨仓依据） | D-6 = ②（四仓补齐 request_id 接线）；依据方案 v1.1.0 §11.8 |
| scripts/test_log_aggregate.py | v1.0.0（内部：批 1 C-7） | 人工测试日志聚合器（`logs/**/*.jsonl` → `doc/test/evidence/manual/<run_id>.{json,md}`；退出码 0=PASS / 1=FAIL / 2=PENDING） | 已落地（TDD 8 例 + PASS/FAIL 双路径实跑） | 方案 §5 C-7 / §3.1 L3 |
| doc/test/evidence/manual/run-20260914-0230.json｜.md、run-20260914-0225.json｜.md | 运行期证据（PASS / FAIL 各一轮） | 人工测试日志聚合证据（run → case → step + `request_id` 双证据） | 已产出（批 1 实跑回填） | 方案 §3.1 L3 / §5 C-7 |
| scripts/test_log_analyze.py | v1.0.0（内部：批 4 C-17） | 错误归因分析器（`logs/**/*.jsonl` → `doc/test/evidence/manual/<run_id>-analysis.md`；归属层矩阵 + 首现标记 + 建议动作；**不含响应明文**；退出码 0=无失败 / 1=有失败 / 2=PENDING） | 已落地（TDD 7 例 + 归因矩阵逐行核对） | 方案 §5 C-17 / §11.5 / §11.6 |
| doc/test/evidence/manual/batch4-unit-junit.xml | 运行期证据（批 4 单测） | 批 4 新增单测 JUnit 证据（C-15/C-16/C-17/C-18/C-19 用例逐项留痕） | 已产出（批 4 实跑回填） | 方案 §5 批 4 / §6 验收 |
| doc/test/evidence/manual/batch4-regression2-junit.xml | 运行期证据（批 4 定向回归，pytest 采集序） | 批 4 定向回归 JUnit 证据（审计/代理/身份/设置等受影响面按 pytest 采集序运行） | 已产出（批 4 实跑回填） | 方案 §6 验收（回归） |
| doc/test/evidence/manual/run-20260914-0230-analysis.md、run-20260914-0225-analysis.md | 运行期证据（真实轮次的归因报告） | 错误归因分析器在真实轮次上的产物（PASS 退出码 0 / FAIL 退出码 1 + 归属层） | 已产出（批 4 实跑回填） | 方案 §5 C-17 / §11.6 |
| doc/test/evidence/manual/batch5-unit-junit.xml | 运行期证据（批 5 单测） | 批 5 新增单测 JUnit 证据（`tests/test_specialized_proxy_upstream_observe.py`：**14 例 / 0 失败**） | 已产出（批 5 实跑回填） | 方案 §5 批 5 / §6 验收 |
| doc/test/evidence/manual/batch5-proxy-regression-junit.xml | 运行期证据（批 5 代理族定向回归） | 批 5 定向回归 JUnit 证据（proxy/dps/llm/rag/memory 等 9 文件：**121 例 / 0 失败**；含 `upstream_observe` 覆盖率 100%） | 已产出（批 5 实跑回填） | 方案 §6 验收（回归） |
| doc/test/evidence/manual/batch5-full-regression-junit.xml | 运行期证据（批 5 全量回归） | 批 5 全量回归 JUnit 证据（**824 例 / 4 失败 / 0 错误 / 4 跳过**；4 例为既有共享 PG 抖动，复跑 10/10 全绿，见 `batch5-pg-flake-recheck-junit.xml`） | 已产出（批 5 实跑回填） | 方案 §6 验收（回归） |
| doc/test/evidence/manual/batch5-pg-flake-recheck-junit.xml | 运行期证据（批 5 环境抖动复核） | 失败 4 例所在文件单独复跑（`test_tenant_admin.py` + `test_users_admin.py`：**10 例 / 0 失败**），判定为既有共享 PG 抖动而非代码缺陷 | 已产出（批 5 实跑回填） | 方案 §7 风险（环境） |
| doc/test/evidence/manual/t4-stream-core-junit.xml | 运行期证据（Step 4 本流核心集） | 测试阶段核心集 JUnit 证据（10 文件：**136 例 / 0 失败 / 0 错误**，32.9s；含覆盖率运行） | 已产出（批 6 测试阶段实跑回填） | 方案 §6 验收 / 测试报告 §3 |
| doc/test/evidence/manual/t4-audit-db-persist-junit.xml | 运行期证据（落库面单文件复核） | `tests/test_audit_db_persist.py` 单独运行（**7 例 / 0 失败**）——用于证伪「混合顺序 3 例失败」为夹具顺序污染而非代码缺陷 | 已产出（批 6 测试阶段实跑回填） | 测试报告 §5.1 |
| doc/test/evidence/manual/t4-stream-unit-junit.xml | 运行期证据（本流集合混合顺序） | 11 文件混合顺序（**143 例 / 3 失败**；3 例为既有 sqlite 夹具顺序污染，单文件复跑全绿） | 已产出（批 6 测试阶段实跑回填） | 测试报告 §5.1 / §7 |
| doc/test/evidence/manual/t4-proxy-regression-junit.xml | 运行期证据（Step 4 定向回归） | 代理族 9 文件定向回归（**121 例 / 0 失败**，115.4s） | 已产出（批 6 测试阶段实跑回填） | 测试报告 §3 |
| doc/test/evidence/manual/t4-full-regression-junit.xml | 运行期证据（Step 4 全量回归） | 全量回归（**824 例 / 4 失败 / 0 错误 / 4 跳过**，457.5s；4 例为既有共享 PG 抖动） | 已产出（批 6 测试阶段实跑回填） | 测试报告 §3 / §5.2 |
| doc/test/evidence/manual/t4-pg-flake-recheck-junit.xml | 运行期证据（Step 4 环境抖动复核） | 失败 4 例所在文件单独复跑（**10 例 / 0 失败**） | 已产出（批 6 测试阶段实跑回填） | 测试报告 §5.2 |
| doc/test/evidence/manual/t4-coverage.txt | 运行期证据（Step 4 覆盖率） | 覆盖率明细（合计 **96%**；`upstream_observe` 99% / `mask` 98% / `testing` 98% / `capture_switches` 100% / `logging_setup` 89%） | 已产出（批 6 测试阶段实跑回填） | 测试报告 §6 |
| doc/test/evidence/manual/t4-frontend-vitest.txt | 运行期证据（Step 4 前端 vitest） | `openbase-ui` vitest 全量（**13 文件 / 147 例 / 0 失败**，68.5s） | 已产出（批 6 测试阶段实跑回填） | 测试报告 §3 / 用例 TT-022 |
| doc/test/evidence/manual/t4-checkall.txt | 运行期证据（联调窗口全量体检） | `service-orchestrator -Action checkall` 实测输出：**27 PASS / 0 FAIL / 0 SKIP**（TT-057 关闭） | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.2 |
| doc/test/evidence/s7/smoke/smoke-summary-t4.json | 运行期证据（冒烟 S0-S6 真实 HTTP） | 32 例：**PASS 25 / FAIL 2（用例口径）/ PENDING 5**（Ollama 在线轮；`...-noollama.json` 为对照轮 21/2/9） | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.3 |
| doc/test/evidence/manual/t4-dps-proxy-trustchain-probe.json | 运行期证据（信任链口径探针） | 6 组实测：仅 JWT 200 / 身份头无来源 403 / 身份头+受信来源 200 / 非受信来源 403 / PUT 同构 → 证实冒烟 2 例 FAIL 为**用例口径缺陷** | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.3 |
| doc/test/evidence/s7/l1-1/t4/cascade-result.json | 运行期证据（T2 L1-1 级联） | S7-T2-1/2/3 PASS（DPS 阻断 / 记忆阻断+幂等 / restored 解除），T2-4 PENDING | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.4 |
| doc/test/evidence/s7/l2-2/matrix-finalize-t4.json | 运行期证据（T4 L2-2 矩阵终验） | S7-T4-1 PASS（17 行 / 缺口 0），T4-2~4 按 B 面口径 PENDING | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.5 |
| doc/test/evidence/s7/l3-1/t4/agent-e2e.json | 运行期证据（T5 L3-1 Agent 端到端） | T5-1/2 PASS；T5-3 PENDING；**T5-4 FAIL→PASS**（缺陷 AD-20260914-02 修复后复跑） | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.6 / §13.7 |
| doc/test/evidence/s7/l3-2/smoke-result-t4.json | 运行期证据（L3-2 贯通冒烟） | 骨架脚本：受信通道可达，**PENDING**（真实双签以各子系统仓脚本为准） | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.10 |
| doc/test/evidence/manual/t4-defect-apikeys-500.json、t4-defect-apikeys-junit.xml | 运行期证据（缺陷 AD-20260914-02） | 500 复现（含 `request_id`）+ TDD 回归先 RED 后 GREEN（4 例） | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.7 |
| doc/test/evidence/s7/l2-1/t4/failover-drill.json、drill-report.md | 运行期证据（S7-T3 主备切换演练本体） | 真实通道状态机驱动：**T3-1~T3-4 全 PASS**（B→A 接管 + B 写被拒 / A 断不改主 / 单主采样恒长 1 / 报告与回切审计字段齐备） | 已产出（批 8 演练会话实跑回填） | 测试报告 §13.12 |
| doc/test/evidence/manual/t4-t2-4-purge.json、t4-t2-4-purge.txt | 运行期证据（S7-T2-4 purge 正例） | 服务层签发授权码 → `POST /identity/purge` **200**（`deactivated→purged`）；负例 **403** `BIZ_PURGE_AUTH_REQUIRED`；重复 **400** `BIZ_NOT_PURGEABLE`；留痕 `purge_records=1` + `audit_logs(identity.purge)=1` | 已产出（批 9 会话实跑回填） | 测试报告 §13.13 |
| doc/test/evidence/manual/t4-all-pages-oplog-walkthrough{,-2,-3}.json｜.txt | 运行期证据（全页面操作日志走查） | 59 项真实操作（24 个调后端页面 × 各页面族）：**58 项命中 L1 `api.request`**（到达网关的请求 100% 留痕；1 例客户端连接中断）；审计库同窗 `api.request`/`proxy.outbound`/`identity.purge` 双落库 | 已产出（批 10 走查会话回填） | 测试报告 §14 |
| doc/test/evidence/manual/t4-o12-real-payload-rerun{,-b,-c}.json｜.txt | 运行期证据（O-12 端点按页面真实 payload 复跑） | 5 端点首跑 422 → 复跑 **5/5 → 200**（根因均为探针负载口径：缺 `steps[].id`/`llm_config`/`password`、`status` 误用字符串、`verdict` 应为 `result`）；19 项操作 100% 留痕 | 已产出（批 10 走查会话回填） | 测试报告 §14.4 |
| doc/test/evidence/manual/t4-l2-1-outage-drill.json、run-l2-1-20260914-2210-analysis.md、t4-checkall-after-drill.txt | 运行期证据（真实上游中断注入与恢复复验） | 已批准停服窗口内：停 OpenRAG → rag-proxy **502（可归因）**、dps/memory/llm 通道 **200 不中断**、OpenRAG 直连 ConnectionError；恢复后 `checkall` **27 PASS / 0 FAIL / 0 SKIP** | 已产出（批 8 演练会话实跑回填） | 测试报告 §13.12 |
| doc/test/evidence/manual/run-20260914-2146.json｜.md、run-20260914-2146-analysis.md | 运行期证据（真实人工 E2E 聚合与归因） | 6 步 / 5 PASS；归因 **3/3 全部定位归属层**（502→网络/上游、404+NOT_FOUND→上游子系统、401→网关鉴权）；报告不含响应明文 | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.8 |
| doc/test/evidence/manual/t4-manual-e2e-summary.json、t4-manual-e2e.txt | 运行期证据（TT-055 步骤级） | 6 步真实状态码 + L1 记录核对（6 条含 `resp_*`/`upstream_*`/摘要）+ 双证据查询 200 | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.8 |
| doc/test/evidence/manual/t4-frontend-e2e.txt、doc/test/evidence/s6/ui-e2e/results.json | 运行期证据（前端真实 E2E） | Playwright 9 关键页 **9 passed（14.2s）**（含 Q-FE-4b）；S6 基线另存 `results-s6-baseline-20260913.json` | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.9 |
| tests/test_log_reserved_keys.py | 回归测试（新增） | 缺陷 AD-20260914-02 防复发：`extra` 保留键静态扫描 + `api-keys` 端点 200 + 根因级 INFO 复现（4 例） | 已产出（批 7 联调窗口实跑回填） | 测试报告 §13.7 |
| doc/test/evidence/manual/t4-perf-tt056.json、t4-perf-tt056.txt | 运行期证据（TT-LOGS-056 端到端差分阶段） | A/B/A2/B2/A3/C 各轮延迟与体积 + **同配置重复跑噪声**（p50 波动 16.02/5.21 ms → 差分**不可判**） | 已产出（批 12 性能量化会话实跑回填） | 测试报告 §15.1 |
| doc/test/evidence/manual/t4-perf-tt056-{A,A2,A3,B,B2,C}.txt | 运行期证据（TT-056 各轮原始输出，6 份） | 各轮 `p50/p95/p99` 原始打印（可复算差分与噪声） | 已产出（批 12 性能量化会话实跑回填） | 测试报告 §15.1 |
| doc/test/evidence/manual/t4-perf-micro.json、t4-perf-micro.txt | 运行期证据（进程内直测：L1 文件日志） | 3000 条写入：mean **0.0889 ms/条** / p99 0.1702 ms / 420 B·条 → **达标**（<<5ms） | 已产出（批 12 性能量化会话实跑回填） | 测试报告 §15.2 |
| doc/test/evidence/manual/t4-perf-micro-db.json、t4-perf-micro-db.txt | 运行期证据（进程内直测：审计库） | 200 行 `INSERT+COMMIT`：mean **6.432 ms/行**（p95 8.374 / p99 10.977）；2 行/代理请求 → **12.865 ms/请求**；含 `audit_logs` 表结构 | 已产出（批 12 性能量化会话实跑回填） | 测试报告 §15.2 |
| doc/test/evidence/manual/t4-perf-tt056-verdict.json、t4-perf-tt056-verdict.txt | 运行期证据（TT-LOGS-056 判定） | 性能 / 容量 / 整改建议 / **口径与反「假达标」声明**：路径内 12.865 ms **未达标** → 登记 P2 异步化；容量 **2.47 MB/日** 达标 | 已产出（批 12 性能量化会话实跑回填） | 测试报告 §15.2 / §15.3 / §15.5 |
| doc/test/evidence/manual/t4-async-persist-verify.json、t4-async-persist-verify.txt | 运行期证据（异步化改造后验证） | 入队成本 **3.68 µs 均值**（p99 7.0 µs）；真实请求返回后**异步落库 2 行**可见（`request_id=req-05db341795cb`，等待 0.00 s） | 已产出（批 12 性能量化会话实跑回填） | 测试报告 §15.4 |
| doc/test/evidence/manual/t4-async-persist-full-junit.xml、t4-async-persist-full-junit-2.xml | 运行期证据（改造后全量回归） | 全量回归 **837 例（通过 829 / 失败 4 / 跳过 4 / 错误 0，440.1s）**；失败 4 例为既有共享 PG 抖动（单文件复跑 10/10 全绿） | 已产出（批 12 性能量化会话实跑回填） | 测试报告 §15.4 |
| tests/test_audit_persist_queue.py | 回归测试（新增） | 审计落库异步化：`submit` 零 DB / 批量单次提交 / writer 路径 / 幂等启停 / 排空在途 / 队列满丢弃 / 失败降级 / 开关关断 / 中间件改进入队 / 请求路径零等待（**16 例**，含 4 例异常边界） | 已产出（批 12 性能量化会话实跑回填；新增区域覆盖率 **100%**） | 测试报告 §15.4 / DevLogReport §18.3 |

---

## 3. S1a~S7 纵切新增文档并入核对表

> 判据：各段「立项 / 设计草案 / DevLog / 测试报告 / 台账 / 清单 / 执行模板」逐项并入本索引（§2 或本表）；**差异 0 或显式登记**，即「无游离文档」。

| 段 | 立项方案 | 设计草案 | DevLogReport | 测试报告 | 台账/清单/执行模板 | 并入结论 |
|----|---------|---------|-------------|---------|-------------------|---------|
| S1a（U1） | OpenBase-U1-统一身份收口立项方案-v1.0.0.md | OpenBase-U1-统一身份收口设计草案-v1.0.0.md | doc/development/OpenBase-U1-统一身份收口-DevLogReport-v1.0.0.md | doc/test/OpenBase-U1-统一身份收口-测试报告-v1.0.0.md | — | 已并入 |
| S1b（P2-1） | OpenBase-P2-1-统一身份协议头与信任链收口立项方案-v1.0.0.md | OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md | doc/development/OpenBase-P2-1-统一身份协议头与信任链收口-DevLogReport-v1.0.0.md | doc/test/OpenBase-P2-1-统一身份协议头与信任链收口-测试报告-v1.0.0.md | — | 已并入 |
| S1b'（P2-2 / R1） | OpenBase-P2-2-隔离与fail-open收口立项方案-v1.0.0.md | — | — | — | OpenBase-P2-2-隔离收口实施执行计划-v1.0.0.md；OpenBase-R1-隔离收口实施执行计划-v1.0.0.md | 已并入 |
| S6（前端段） | OpenBase-S6-统一前端隔离展示与段门禁收口-立项方案-v1.0.0.md | OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0.md | doc/development/OpenBase-S6-统一前端隔离展示与段门禁收口-DevLogReport-v1.0.0.md | doc/test/OpenBase-S6-统一前端隔离展示与段门禁收口-测试报告-v1.0.0.md | doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md | 已并入 |
| S7（总收官段） | OpenBase-S7-全域门禁与总收官-立项方案-v1.0.0.md | OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0.md | doc/development/OpenBase-S7-全域门禁与总收官-DevLogReport-v1.0.0.md | doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md | doc/planning/OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md；doc/design/OpenBase-K13-账号权限矩阵-v1.0.0.md；doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md；doc/test/evidence/s7/gate/gate-aggregate.json；doc/test/evidence/s7/t8/writeback-check.json；本索引 | 已并入（v1.0.2 增补 DevLog/测试报告；v1.0.3 增补联调窗口工具脚本 L1-1/L2-1/L2-2/L3-1/L3-2；v1.0.4 增补联调窗口环境检查报告与 env-check 证据；v1.0.12 增补批 2/批 4 实施记录 DevLogReport 与 C-17 错误归因分析器；v1.0.13 归档 DevLogReport 旧版并同步索引路径；v1.0.15 增补人工端到端测试日志落盘流 **Step 4 测试用例 / 测试报告 / 测试回溯对比审计报告** 及 `t4-*` 证据（8 项）；v1.0.16~v1.0.20 增补联调窗口真实面 / T3 演练 / T2-4 purge / 全页面操作日志走查 / 审计镜像同步；**v1.0.21 增补性能量化（TT-LOGS-056）与审计落库异步化改造（测试报告 §15 / 回溯审计 §9.7 / DevLogReport §18）**；S7 段交付物齐备） |

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
- doc/development/archive/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.3.0.md
- doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.4.0.md
- doc/test/OpenBase-S7-人工端到端测试日志落盘-测试用例-v1.0.0.md
- doc/test/OpenBase-S7-人工端到端测试日志落盘-测试报告-v1.0.0.md
- doc/audit/verification/OpenBase-S7-人工端到端测试日志落盘-测试回溯对比审计报告-v1.0.0.md
- doc/test/evidence/manual/batch4-unit-junit.xml
- doc/test/evidence/manual/batch4-regression2-junit.xml
- doc/test/evidence/manual/batch5-unit-junit.xml
- doc/test/evidence/manual/batch5-proxy-regression-junit.xml
- doc/test/evidence/manual/batch5-full-regression-junit.xml
- doc/test/evidence/manual/batch5-pg-flake-recheck-junit.xml
- doc/test/evidence/manual/t4-stream-core-junit.xml
- doc/test/evidence/manual/t4-audit-db-persist-junit.xml
- doc/test/evidence/manual/t4-stream-unit-junit.xml
- doc/test/evidence/manual/t4-proxy-regression-junit.xml
- doc/test/evidence/manual/t4-full-regression-junit.xml
- doc/test/evidence/manual/t4-pg-flake-recheck-junit.xml
- doc/test/evidence/manual/t4-coverage.txt
- doc/test/evidence/manual/t4-frontend-vitest.txt
- doc/test/evidence/manual/t4-perf-tt056.json
- doc/test/evidence/manual/t4-perf-tt056-verdict.json
- doc/test/evidence/manual/t4-perf-micro.json
- doc/test/evidence/manual/t4-perf-micro-db.json
- doc/test/evidence/manual/t4-async-persist-verify.json
- doc/test/evidence/manual/t4-async-persist-full-junit.xml
- doc/test/evidence/manual/t4-async-persist-full-junit-2.xml
- tests/test_audit_persist_queue.py
- doc/test/evidence/manual/run-20260914-2146.md
- doc/test/evidence/manual/run-20260914-2146-analysis.md
- doc/test/evidence/s7/l2-1/t4/drill-report.md
- doc/test/evidence/manual/run-l2-1-20260914-2210-analysis.md
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
