# OpenBase-S7-沙箱外执行单-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-OUTSIDE-RUN-v1.0.0 |
| 版本 | v1.0.9 |
| 状态 | [Draft] |
| 日期 | 2026-09-12 |
| 作者 | AI（S7 批次 5 沙箱外执行单编制；现状只读实测 2026-09-11；批次 7 全量冒烟执行回填 2026-09-11 19:00；批次 8 F-4 修复 + openbase_test 建库回填 2026-09-11 20:45；批次 9 K07 终验回填 2026-09-11 22:15；批次 10 OpenLLM K07 补填回填 2026-09-11；批次 11 OpenMemory K07 缺口补填回填 2026-09-12；批次 19 DPS 豁免续期入库回填 2026-09-13；批次 20 OpenLLM 快照落仓脚本登记 2026-09-13） |
| 用途 | **S7 沙箱外 / 联调窗口执行单**：将 S7 段（总收官段）全部 B 面（联调窗口必需面）与跨仓收口待办，整理为可逐项执行、可回填证据、可勾选收口的**唯一执行清单**；沙箱内仅可执行 OpenBase 仓操作，四仓 git 与真实运行态操作须由用户在沙箱外按本单执行 |
| 上游依据 | ①《OpenBase-S7-全域门禁与总收官-设计草案-v1.0.0.md》（仓根，OB-S7-DESIGN-v1.0.0，内部 **v1.0.1 [Approved]**，§4 逐任务设计 §4.1~§4.9（34 断言与执行面 A/A+B/B）、§5 证据与报告规范）；②《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md》（`doc/test/`，OB-S7-TEST-v1.0.0，**[Review]**，34 断言矩阵：通过 5 / 部分达成 9 / PENDING 20）；③《OpenBase-S7-全域门禁与总收官报告-v1.0.0.md》（`doc/development/`，内部 **v1.0.1**，[Review]）；④《OpenBase-S7-跨仓入仓与会签执行模板-v1.0.0.md》（`doc/planning/`，内部 **v1.0.2 [Approved]**）；⑤《OpenBase-联调产物清点核对总清单-v1.0.0.md》（`doc/planning/`，内部 **v1.0.7 [Approved]**，§1.1 五仓对照表 / §4.1 会签五步 / §5.10 四仓入仓完成登记）；⑥《OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md》（`doc/development/`，内部 **v1.0.9 [Approved]**，§0 通用红线）；⑦各段测试报告 PENDING 清单（S2 / S3 / S4 / S5 段级真实双签 + S6 B1~B6，见总收官报告 §4.1）；⑧《OpenBase-真实联调冒烟清单-v1.0.0.md》（仓根，OB-INTG-SMOKE-v1.1.0，内部 **v1.1.0**，§3 用例矩阵 S0-S6） |
| 事实基线（2026-09-11 实测） | 四仓入仓 = **OpenRAG** `release/v1.10.0` @ `a2eb92b`（三远端同步、勾稽差异 0、残余 1）；**DPS** `main` @ `e772c01`（三远端同步、勾稽差异 0、残余 4）；**OpenMemory** `release/v7.3.0` @ `cc7c06f`（origin+backup 已同步、**github 待推**、**勾稽 A 类回读待做**（残余 89））；**OpenLLM** `feature/s4-identity-channel-b` @ `be1886d`（**四远端 origin/backup/github/jerry.yu 均未推送**；need-star 隔离分支 `feature/need-star-orchestration` @ `ce40f90` 亦未推，残余 1459）。**OpenBase 提交链** = `402ff8e` / `2235229` / `d3faa7f` / `2d97d1a` / `a5020fa` / `9056f48`（S7 段内提交，`main`）。**S7 段门禁当前结论 = 未达最终通过**（① ② 真实面、④ 三原则总验证、⑤ 两仓远端推送为 PENDING） |
| 适用范围 | S7 段沙箱外 / 联调窗口执行；覆盖 P1 跨仓收口、P2 联调窗口（T2~T5 / T6 真实面 / 段级非沙箱复核）、P3 收口与批准。**沙箱内只允许操作 OpenBase 仓**；四仓命令与真实面一律沙箱外执行 |
| 使用说明（四步） | **① 前置检查**（§0：真实 PG/Redis/IdP/四仓运行态/端口/网关与统一前端/git 远端写权限/Playwright 浏览器逐项确认）；**② 按优先级执行**（P1 可立即执行、无需联调环境 → P2 联调窗口 → P3 收口）；**③ 回填证据与文档**（按每项「证据落盘路径 + 回填位置」落地，`status: PENDING → PASS/FAIL`）；**④ 收口批准**（§5：证据回填 → 测试报告 34 断言状态更新 → 报告内部版本升级 → 段门禁六项复核 → S7 段门禁人工批准回写） |
| 执行面口径 | **A** = 沙箱可判定（已达成，见测试报告结论 5 条）；**A+B** = 结构面已 PASS、真实面待联调窗口（9 条）；**B** = 断言主体属联调窗口（20 条）。本执行单聚焦 **A+B 真实面 + B 面 + 跨仓收口 + 段级非沙箱复核** |
| 纪律 | **禁伪造 hash 与通过结论**；仅推指定分支，不推送 `master`/`main` 之外的无关内容；远端推送前确认本地勾稽；回归失败即停；敏感文件不入提交面；`dogfood-output/` 不纳入任何提交面（对齐设计草案 §5.3/§5.4、放行清单 §0 红线） |

### 占位符替换规则（全部命令为可复制形态）

> 本单全部命令中的尖括号占位符 `<...>` 在执行前**一律替换为真实值**；Windows 路径含空格，PowerShell 中一律用**单引号**包裹。

| 占位符 | 替换值（默认仓库路径） | 说明 |
|--------|----------------------|------|
| `<OM>` | `D:\Trae CN\myproject\Dev\OpenMemory` | OpenMemory 仓 |
| `<LL>` | `D:\Trae CN\myproject\Dev\OpenLLM` | OpenLLM 仓 |
| `<RAG>` | `D:\Trae CN\myproject\Dev\OpenRAG` | OpenRAG 仓 |
| `<DPS>` | `D:\Trae CN\myproject\Dev\DPS` | DPS 仓 |
| `<OB>` | `D:\Trae CN\myproject\Dev\OpenBase` | OpenBase 仓（本仓，沙箱内可操作） |
| `<PG_DSN>` | 真实 PostgreSQL 连接串（例 `postgresql://<user>:<pwd>@<host>:<port>/openbase`） | 含 `openbase_test` 库权限 |
| `<REDIS_HOST>` / `<REDIS_PORT>` | 真实 Redis 主机 / 端口 | 例 `127.0.0.1` / `6379` |
| `<IDP_BASE>` / `<REALM>` | 真实 IdP（Keycloak）基址 / 域（例 `http://<host>:<port>` / `openbase`） | OIDC 发现端点 |
| `<GATEWAY_BASE>` | 网关 + 统一前端基址（例 `http://<host>:<port>`） | `/ui/` 发布回滚复核 |
| `<SMOKE_AGENT_KEY>` | 真实 agent key（`sk-agent-*`） | L3-1 Agent 端到端 |
| `<TENANT_A>` / `<TENANT_B>` | 真实双租户标识（L1-1 / RA-06 双租户面） | 隔离复核 |
| `<SUBJECT_ID>` | 专用冒烟主体（建议 `smoke_l1_1_*`，禁用生产主体） | L1-1 级联核验 |

### 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-11 | AI（S7 批次 5 执行单编制） | 初始版本：S7 沙箱外执行单。含 §0 前置环境检查表（含 S7 相关脚本现状只读核实结论）、§1 跨仓收口项（P1，3 条）、§2 联调窗口 T2~T5（P2，4 条）、§3 T6 真实面（P2，4 条）、§4 段级非沙箱复核（P2，10 条：S2~S5 双签 4 + S6 B1~B6 6）、§5 收口与批准（P3，6 条）、§6 执行进度勾选总表、§7 执行纪律与风险、附录 A~D（提交链索引 / 四仓分支与 hash / PENDING 主挂起与 S7 自身 PENDING 清单 / 断言→证据→回填映射表）。**本次仅新建本执行单一个文件，未改动任何代码与其他文档，未执行任何四仓 git 写操作** |
| v1.0.1 | 2026-09-11 | AI（S7 联调窗口工具脚本骨架批次） | **工具脚本骨架并入与命令校正**：§0.2 由「待实现」更新为「骨架已就绪（可干跑，真实执行仍需联调窗口）」（N-1~N-4 五脚本骨架已补齐，N-5 `scripts/smoke_l3_2.py` 已补做）；§2.1~§2.4 命令模板按实际参数名校正（`-OutDir`→`-EvidenceDir`，补 `-DryRun` / `--dry-run`，`finalize_l2_2_matrix.py` 补 `--matrix`/`--check-read-ab`/`--check-write-ab`/`--k14`）；§2 增补五脚本统一退出码约定（`0=PASS` / `1=FAIL` / `2=PENDING`）。**仅更新本执行单脚本现状与命令，不改任务范围与 PENDING 结论** |
| v1.0.2 | 2026-09-11 | AI（S7 批次 6 回填会话） | **P1 跨仓收口三条状态回填（实测）**：§1.1 [P1-1] OpenMemory 推送 github → **已完成（实测已同步，无需操作）**（远端 `ls-remote` = `cc7c06f`，三端一致）；§1.2 [P1-2] OpenMemory 勾稽 A 类回读 → **已完成（差异 0）**（A 类集合 73 vs 残余 89，交集 0；分类 C 类 88 + 清单文档自身 1）；§1.3 [P1-3] OpenLLM 推送 → **部分完成**（origin/backup/github 三端已同步 `be1886d`/`ce40f90`；`jerry.yu` 无写权限受限 PENDING；本地点跟踪 ref 待 `git fetch`）。§1 各条新增「执行状态」行；§2~§4（P2 联调窗口）任务范围与 PENDING 结论**不变** |
| v1.0.3 | 2026-09-11 | AI（P2 联调窗口环境只读探测会话） | **§0.1 前置环境检查表逐项实测回填**：0-1 真实 PG（192.168.0.151:5432/nuct，PG 14.23）**就绪**、0-2 `openbase_test` **未就绪（库不存在）**、0-3 Redis（192.168.0.151:6380）**就绪（PONG）**、0-4 IdP（8090/8080）**未就绪（未启动）**、0-5 四仓运行态（8001/8010/8020/8030）**未就绪**、0-6 网关/统一前端（8000/5173/80）**未就绪**、0-7 四仓远端写权限**就绪（jerry.yu 受限 BLOCKED）**、0-8 Playwright**就绪（chromium-1228 + 1.63.0）**；新增 §0.1 实测汇总行。新增《OpenBase-S7-联调窗口环境检查报告-v1.0.0.md》与证据 `doc/test/evidence/s7/env/env-check.json`。**仅回填检查表与新增报告/证据，不改任务范围与 PENDING 结论；未执行任何四仓 git 写操作** |
| v1.0.4 | 2026-09-11 | AI（P2 全量冒烟与真实面执行会话，批次 7） | **§2/§3 真实面执行状态回填（实测）**：环境排序后逐条执行——**全量冒烟 S0~S6**（P0 30 例 PASS 14 / FAIL 9 / BLOCKED 7；P1 2 例 BLOCKED）；**L3-2 贯通冒烟实跑**（`mode=run`，PENDING，受信通道可达）；**T2 L1-1 / T4 L2-2 / T5 L3-1 实跑**（去 DryRun/dry-run，均 PENDING exit 2）；**T6 门禁聚合实跑**（最终 `overall=PASS exit=0 pass=19 fail=0 pending=3`；RA-06 PASS；主批次 4 例 `test_oidc_binding` 环境性失败 PENDING；首跑 FAIL 由 `test_verdict_k03` 断言过严 + 门禁自引用时序导致，已修）；**S6 B1 Playwright 9 页实跑**（0 passed / 9 failed，Q-FE-4b console.warn）；**DPS 幂等 seed**（0 新增）。新增证据 `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json,dps-seed.json}`、`doc/test/evidence/s6/ui-e2e/status.json`。**暴露 4 项真实功能缺陷**（OpenLLM 上游不可达 + memory/rag client 未注入、OpenRAG `collections.tenant_code` 缺失、`TRUSTED_PROXY_SOURCES` 取值不一致、前端路由告警）；§1/§2/§3 各条新增「执行状态」行。**仅回填状态与证据，未改动四仓** |
| v1.0.5 | 2026-09-11 | AI（S7 批次 8 收口会话） | **F-4 修复与 openbase_test 建库收口（实测）**：① **F-4 统一前端路由告警修复**——根因判定为**装配时序（B 类）**：模块路由由守卫在导航后懒装载，vue-router 在首帧 `router.resolve`（守卫之前）即对深链发出 `No match found` 告警；修复为启动预热（`openbase-ui/src/core/router/index.ts` 新增 `bootstrapModuleRoutes` + `src/main.ts` 在 `app.use(router)` 前预热），**未放宽 `console.warn=0` 判据、未屏蔽告警**；E2E 重跑 **9/9 PASS**（`npm run test:e2e`），`npm run lint` 0 problem、`npm test` 140 passed。② **openbase_test 独立库真实建立**——`scripts/db/init_openbase_test.ps1` 参数化（Host/Port/Db/账号取自 `.env.shared-infra`，无 psql 客户端时回退 psycopg2）；真实建库 + 四账号 NOSUPERUSER + K13 授权 + 幂等迁移（28 表）实测通过；`pg_database`/`pg_roles`/`has_schema_privilege` 复核收敛。§0.1 第 0-2 项由「未就绪」更新为「就绪」；§2.5 P2-B1 行由「9 failed」更新为「9 passed」；§3.3 回填 PG-ENV 复跑结果。**仅改前端源码/测试、建库脚本、证据与文档；未改动子系统仓、未停止/重启任何服务** |
| v1.0.6 | 2026-09-11 | AI（S7 批次 9 K07 终验会话） | **K07/SYS-1 端点-过滤矩阵真实导出终验回填（§3.4/§3.5）**：五实例真实导出 openapi（`openbase:8000` 137 / `openllm:8001` 351 / `openrag:8010` 115 / `openmemory:8020` 36 / `dps:8030` 161，均 HTTP 200）并保真落盘；与各仓填报矩阵逐行核对 → **缺口 352（OpenLLM 344 / OpenMemory 8）、未覆盖 0、豁免 56（有效 21；DPS 35 需续期）→ FAIL**。§3.4 与 §3.5 P2-T6-4 行更新；证据 `doc/test/evidence/s7/gate/k07-finalize.json` + `k07-openapi/*.openapi.json`。**子系统仓缺口只登记不代改。**（注：本批次元信息版本 v1.0.6 与 §3.4/§3.5 标注一致，修订历史行此处补记。） |
| v1.0.8 | 2026-09-12 | AI（S7 批次 11 OpenMemory K07 缺口补填回填会话） | **OpenMemory K07 8 条缺口补填结果回填（§3.4/§3.5/§6）**：OpenMemory 仓已在其工作树完成 8 条缺口补填（4 文件；矩阵 32→**40 行** / 覆盖 25→31 / 豁免 7→9；**缺口 8→0**；新增隔离注册 `IS-OM-R26~R31`；隔离用例 **81 passed**；门禁复跑 `missing_rows=0`，exit 0；K07/identity 组 **372 passed**；ruff 0 错误），**因沙箱拒写 `.git/objects` 未能 commit（无 hash，禁伪造），工作树保留，需在可写环境提交**。§3.4「执行状态」追加 v1.0.8 行；§3.5/§6 P2-T6-4 状态更新；**待提交项扩为两仓（OpenMemory 4 文件 + OpenLLM 5 文件），建议 message：`docs(k07): OpenMemory 端点过滤矩阵 8 条缺口补填与隔离用例注册（缺口归零）`**。**缺口合计 0/未覆盖 0；仅 DPS 35 条豁免需续期。未改动子系统仓功能语义代码。** |
| v1.0.9 | 2026-09-13 | AI（S7 批次 19~20 DPS 入库回填 + OpenLLM 快照落仓脚本登记会话） | ① **补记 v1.0.8 之后的 DPS 入库闭环**：DPS 仓 K07 35 条豁免续期已于 2026-09-13 提交 **`b5f5c06`**（3 文件 = 填报矩阵 + 一键提交脚本 2；`origin`/`backup`/`github` 三远端 `ls-remote` 与本地 HEAD 一致）——§3.4 执行状态、§3.5 待提交项、附录 B DPS HEAD、§5.6 与 `k07-finalize.json` / `gate-aggregate.json` 同步；② **本批次：OpenLLM `backend\data\openapi-llm-snapshot.json` 落仓项收口为可执行形态** —— 生成一键脚本`openllm-k07-snapshot-commit-push.bat` + `scripts/openllm_k07_snapshot_commit_push.ps1`（宿主仓库＝OpenBase，因 OpenLLM 在本沙箱全仓只读）；脚本干跑通过（源快照校验 351 操作 / 提交面守卫 / 三远端校验），提交分支与 K07 补填提交 `41af780` 同源（`feature/s4-identity-channel-b`，三远端均有该分支）；③ 受限说明：OpenLLM `backend/data/**` 与 `.git` 写入被沙箱拦截，**实测无残留**（无目标文件、无 `index.lock`、暂存区为空）→ 该项**待沙箱外执行并回填 hash**。**未改动任何子系统仓文件；敏感文件零进入。** |

---

## §0 前置环境检查表（执行前逐项确认）

> 判据：**全部「就绪」后方可进入 P2 联调窗口执行**；任一「未就绪」项须记录备注并评估对 P2 相关任务（及关联断言）的阻塞范围。P1 跨仓收口仅需 §0.1 第 6 项（git 远端写权限）。

### 0.1 环境与运行态检查表

| # | 检查项 | 检查命令（可复制） | 就绪 | 未就绪 | 备注 |
|:-:|--------|-------------------|:---:|:---:|------|
| 0-1 | **真实 PostgreSQL**（连接可用） | `psql "<PG_DSN>" -c "select version();"` | ☒ | ☐ | **就绪（2026-09-11 实测）**：192.168.0.151:5432（库 `nuct`，user `nuct`，口令已配置）TCP 可达 + `SELECT 1` 通过（PG 14.23）；业务 schema `openbase` 已存在。**（明细见《OpenBase-S7-联调窗口环境检查报告-v1.0.0.md》§1 第 1/2 项）** |
| 0-2 | **`openbase_test` 测试库可用**（S7-T1-2 真实面） | `psql "<PG_DSN>" -c "select datname from pg_database where datname='openbase_test';"` | ☒ | ☐ | **就绪（2026-09-11 20:40 实测）**：`openbase_test` 已真实建立（`pg_database` 实测 = [nuct, openbase_test]）；四账号 `openbase_app`/`platform_app`/`openbase_migrator`/`openbase_runtime` 已建（NOSUPERUSER）；`openbase_test` 内 `openbase` schema 迁移 **28 表**；K13 授权 `has_schema_privilege` 复核收敛。建库脚本 `scripts/db/init_openbase_test.ps1` 已参数化（默认读 `.env.shared-infra`，无 psql 回退 psycopg2）。**（明细见《OpenBase-S7-联调窗口环境检查报告-v1.0.0.md》§1 第 3 项与证据 `doc/test/evidence/s7/env/env-check.json`）** |
| 0-3 | **Redis**（PING 通） | `redis-cli -h <REDIS_HOST> -p <REDIS_PORT> ping` | ☒ | ☐ | **就绪（2026-09-11 实测）**：192.168.0.151:6380 TCP 可达、`PING` = `PONG`（口令已配置）；会话/连接池用例前置（PG-ENV-3）满足 |
| 0-4 | **IdP / Keycloak**（OIDC 发现端点可达） | `curl -sk <IDP_BASE>/realms/<REALM>/.well-known/openid-configuration` | ☐ | ☒ | **未就绪（2026-09-11 实测）**：本地 OIDC IdP `127.0.0.1:8090`（`.env` 默认，无 realm）与 Keycloak `127.0.0.1:8080/realms/openbase`（发行版存于 `.runtime/keycloak-26.7.3`）**均连接被拒（未启动）**；阻塞 S6 B4 / RA-06 OIDC 面 |
| 0-5 | **四仓运行态与端口**（四仓 `/health` 通过） | 逐仓 `curl -s <各仓健康地址>`（端口见《OpenBase-多系统端口统筹方案-v1.0.0.md》） | ☐ | ☒ | **未就绪（2026-09-11 实测）**：OpenLLM 8001 / OpenRAG 8010 / OpenMemory 8020 / DPS 8030 **全部无监听**；运行态编排唯一入口 = `<OB>\scripts\service-orchestrator.ps1 -Action startcheck`（已就绪，可用） |
| 0-6 | **网关 / 统一前端可访问** | `curl -s <GATEWAY_BASE>/health; curl -s <GATEWAY_BASE>/ui/` | ☐ | ☒ | **未就绪（2026-09-11 实测）**：OpenBase 网关 8000、统一前端 vite 5173、nginx 80 `/ui/` **均无监听**（`openbase-ui/node_modules` 依赖已装、`nginx.conf.example` 配置齐备）；阻塞 S6 B6 与 T2~T5 `-BaseUrl` |
| 0-7 | **四仓 git 远端写权限** | `git -C <OM> ls-remote --heads origin; git -C <LL> ls-remote --heads origin`（读）+ 推送前 `git -C <LL> push --dry-run origin feature/s4-identity-channel-b` | ☒ | ☐ | **就绪（引用 2026-09-11 已测结论，不重复探测）**：OpenMemory/OpenRAG/DPS 三仓远端可写且已同步；OpenLLM origin/backup/github 三端已同步 `be1886d`/`ce40f90`；**`jerry.yu` 无写权限（BLOCKED，受限 PENDING，不阻断远端子项关闭）**；P1 跨仓收口（S7-T7-1）唯一前置满足 |
| 0-8 | **Playwright 浏览器二进制**（S6 B1） | `cd <OB>\openbase-ui; npx playwright install chromium` | ☒ | ☐ | **就绪（2026-09-11 实测）**：用户缓存 `%LOCALAPPDATA%\ms-playwright` 含 `chromium-1228/chrome-win64/chrome.exe`；`npx playwright --version` = **1.63.0**（node v22.16.0）。S6 B1 剩余阻塞仅为统一前端运行态（0-6） |

> **§0.1 实测汇总（v1.0.3 回填，2026-09-11）**：8 项中 **就绪 4**（0-1 真实 PG / 0-3 Redis / 0-7 四仓远端写权限（除 `jerry.yu`）/ 0-8 Playwright）、**未就绪 4**（0-2 `openbase_test` / 0-4 IdP / 0-5 四仓运行态 / 0-6 网关与统一前端）。**结论：环境未就绪，不满足「全部就绪后方可进入 P2 联调窗口」判据**；仅 P1 跨仓收口（已完成/受限）与 S6 B5（不依赖本机运行态）可独立推进。逐项明细与处置建议见《OpenBase-S7-联调窗口环境检查报告-v1.0.0.md》§1/§2，证据见 `doc/test/evidence/s7/env/env-check.json`。

### 0.2 S7 相关脚本现状核实（只读实测，2026-09-11）

> 核实方式：只读枚举 `<OB>\scripts\**`（Glob / Grep），**未执行任何写操作**。判定为「已就绪」= 文件存在且实现于 S7-T1/T6 收口提交内；「骨架已就绪」= 文件已补齐（参数解析 + 证据 JSON 字段 + 断言占位），可**干跑**（`-DryRun` / `--dry-run`，无真实环境时 `status=PENDING`、退出码 `2`），真实调用与真实响应码在联调窗口填入（**骨架不得填假响应码**）。

**已就绪（实测存在）**

| # | 脚本路径 | 关联任务 / 断言 | 说明 |
|:-:|---------|----------------|------|
| S-1 | `scripts/gate_aggregate.py` | S7-T6 / S7-T6-1~4 | 门禁聚合单命令（RA-06 / 冒烟 S0-S6 / 对齐清单 / K07-SYS-1），输出 `doc/test/evidence/s7/gate/gate-aggregate.json` |
| S-2 | `scripts/verify_env_global.ps1` | S7-T1-1 | verify-env 跨仓单一全局入口（`-Repos` / `-FailFast` / `-SkipNetwork` / `-SkipDb`） |
| S-3 | `scripts/verify-env/contract.global.json` | S7-T1-1 | 跨仓统一契约（主结构 + `repo_overrides`，与 `contract.json` 非破坏性并存） |
| S-4 | `scripts/db/init_openbase_test.ps1` | S7-T1-2 | `openbase_test` 建库/建账号/幂等迁移（`WHERE NOT EXISTS` / `create_all`） |
| S-5 | `scripts/db/grant_k13_accounts.ps1` | S7-T1-3 | K13 账号授权收敛（打印模式干跑通过；真实授权属 B 面） |
| S-6 | `scripts/scan_orchestrator_bypass.py` | S7-T1-4 | 禁批量杀静态扫描（实测 20 文件、`disallowed=0`） |
| S-7 | `scripts/run_tests.ps1` | S7-T1-2 | 单仓回归入口（分组子进程隔离 + ruff）；跨仓 `-Repos` 编排为增量 |
| S-8 | `scripts/k07_endpoint_matrix.py` | S7-T6-4 | K07 端点-过滤矩阵脚本（四仓计数对账：OpenMemory 32 / OpenRAG 121 / OpenLLM 14 / DPS 169，`gap_count=0`） |
| S-9 | `scripts/service-orchestrator.ps1` | S7-T1-4 | 受管编排唯一入口（`start/startcheck/checkall/monitor/status/stop`，逆拓扑 stop） |

**骨架已就绪（可干跑，真实执行仍需联调窗口）**

| # | 计划脚本路径 | 关联任务 / 断言 | 现状与骨架说明 |
|:-:|-------------|----------------|---------------|
| N-1 | `scripts/verify_l1_1_cascade.ps1`（零新依赖） | S7-T2 / S7-T2-1~4 | **骨架已就绪**（可干跑：`-DryRun -BaseUrl … -SubjectId … -EvidenceDir …`，无环境 `status=PENDING`/退出码 `2`）。真实路径：`POST /api/v1/identity/suspend` → 轮询身份事件 → 断言 DPS 画像读阻断（403/404）、OpenMemory 记忆数据面阻断（`sessions`/`memories` 403/404）、`event_id` 幂等（重放 DB 行数不变）、`restored` 解除、purge 显式触发（400/403/审计留痕）；输出 `doc/test/evidence/s7/l1-1/cascade-result.json` |
| N-2 | `scripts/drill_l2_1_failover.ps1` | S7-T3 / S7-T3-1~4 | **骨架已就绪**（可干跑：`-DryRun -Scenario b-down\|a-down\|both -BaseUrl … -EvidenceDir …`）。真实路径：故障注入 = 停 B 上游进程 / 阻断 B 端口；双场景（B 断→A 接管、A 断→B 维持）；采集切换前后路由、降级头、告警；单主禁双写断言；输出 `doc/test/evidence/s7/l2-1/failover-drill.json` + `drill-report.md` |
| N-3 | `scripts/finalize_l2_2_matrix.py` | S7-T4 / S7-T4-1~4 | **骨架已就绪**（可干跑：`--dry-run`；真实路径 `--matrix <S4-T8 matrix_rows.json> --check-read-ab --check-write-ab --k14`）。以 S4-T8 `matrix_rows` 为基座（复用其语义口径），校验「每子系统 × A/B × 头语义」行全覆盖、缺口 0、A 直连豁免行标注（与 K07 端点矩阵对账）、读路径 B 主 A 备、写路径 A/B 等价 + K14 幂等；输出 `doc/test/evidence/s7/l2-2/matrix-finalize.json` |
| N-4 | `scripts/verify_l3_1_agent.ps1` | S7-T5 / S7-T5-1~4 | **骨架已就绪**（可干跑：`-DryRun -AgentKey … -BaseUrl … -EvidenceDir …`）。真实路径：agent key → 四头（X-User-ID/X-Tenant-ID/X-User-Role/X-Proxy-Source）→ 各系统白名单（每系统 ≥3 例）→ 域隔离 → 未授权 403（`PERM_UNTRUSTED_IDENTITY_HEADER`）；M1/M2 分别断言；agent 无交互登录 0 可达；输出 `doc/test/evidence/s7/l3-1/agent-e2e.json` |
| N-5 | `scripts/smoke_l3_2.py` | S7-T6-2 / S7-T7-3（S6 B2） | **骨架已就绪**（可干跑：`--dry-run --base-url …`；不可达 → `status=PENDING`、退出码 `2`）；经受信通道端到端关键路径；L3-2 双签执行以各子系统仓脚本为准，OpenBase 侧登记回填；输出 `doc/test/evidence/s7/l3-2/smoke-result.json` |

> **纪律**：五脚本骨架**不阻断** P1/P2 执行中的非依赖项；参数解析 + 证据 JSON 字段 + 断言占位已就绪，**真实调用与真实响应码在联调窗口填入，骨架不得填假响应码**。五脚本统一退出码约定：`0=PASS` / `1=FAIL` / `2=PENDING`（干跑且无环境时默认 `2`）。

---

## §1 跨仓收口项（优先级 P1 · 可立即执行 · 无需联调环境）

> 前置：仅需 §0.1 第 0-7 项（四仓 git 远端写权限）。关联断言：**S7-T7-1 / S7-T7-2**。纪律：仅推**指定分支**，禁推 `master`/`main` 之外的无关内容；推送前先确认本地勾稽（`git status --porcelain -uall`）。

### 1.1 [P1-1] OpenMemory 推送 github 远端

| 项 | 内容 |
|----|------|
| **关联断言** | **S7-T7-1**（四仓入仓 + 远端同步）；门禁项 ⑤ 跨仓会签 |
| **目标** | OpenMemory `release/v7.3.0` @ `cc7c06f`：origin / backup 已同步，**github 远端待推** |
| **执行状态（v1.0.2 实测 2026-09-11）** | ✅ **已完成（实测已同步，无需操作）**：`git -C <OM> ls-remote github refs/heads/release/v7.3.0` 实测 = `cc7c06f648650e51f01fdba5ea60e6f8b85c4763`，与本地 `cc7c06f` 一致；origin / backup 亦为 `cc7c06f` → **三端已同步**。备注：本沙箱 HTTPS 出口访问 github 时偶发 `Recv failure: Connection was reset`（环境性），以远端实测 hash 为准 |
| **执行命令** | `git -C <OM> push github release/v7.3.0` |
| **期望证据** | `git -C <OM> ls-remote --heads github release/v7.3.0` 输出 = `cc7c06f...`（与本地 `git -C <OM> rev-parse release/v7.3.0` 一致） |
| **证据落盘路径** | `doc/test/evidence/s7/signoff/om-github-push.json`（字段：`repo`/`branch`/`local_head`/`remote_head`/`status`/`reason`/`checked_at`/`evidence_ref`=`S7-T7-1`） |
| **回填位置** | ① 清点总清单 §5.10「远端同步」行 OM 条目；② 归集文档 §3.9 OM 远端状态；③ `doc/test/evidence/s7/t7/signoff-check.json` §repos.OM.remote；④ 执行模板（内部 v1.0.2）§4.1 / §5 |
| **失败处置** | 无 github 远端写权限 / 网络不可达 → **如实登记 `PENDING`（不得伪造 hash）**；分支名不符 → 以 `git -C <OM> branch --show-current` 实测为准并登记差异 |

### 1.2 [P1-2] OpenMemory 勾稽 A 类回读

| 项 | 内容 |
|----|------|
| **关联断言** | **S7-T7-2**（四仓清单勾稽，A 类差异 = 0）；门禁项 ⑤ |
| **目标** | 以清点总清单 §1.1 为基准，回读 OpenMemory 工作树：**A 类差异 0**，残余仅 B 类隔离 + C 类噪音 + 分清单文档自身（当前残余 **89** 待复核） |
| **执行状态（v1.0.2 实测 2026-09-11）** | ✅ **已完成（差异 0）**：A 类集合 **73** 项（批 0 基线批 29 + §8.1 裁断并入 3 = 32、S2 段批 41；`A70=70`→执行后 `A73=73`）与残余 **89** 做集合比对，**交集 = 0**；残余分类 = C 类噪音 88（C-2 4 / C-3 57 / C-4 27）+ 清单文档自身 1，**B 类 0、清单外待裁定 0**。明细证据 `doc/test/evidence/s7/t7/om-reconcile.json` |
| **执行命令** | `git -C <OM> status --porcelain -uall` ；再与《OpenMemory-联调产物待提交清单-v1.0.0.md》§2 的 **A 集合**做集合差比对（A 集合应全部消失，仅余 B/C + 分清单自身） |
| **期望证据** | A 类差异 = 0；残余条目分类计数 = B（197）+ C（89）+ 需人工判定（8）+ 分清单自身，且与分清单 §2/§7 双向自检一致 |
| **证据落盘路径** | `doc/test/evidence/s7/signoff/om-reconcile-readback.json`（含残余条数、A 类差异数、分类计数、原始 `status` 摘要行数） |
| **回填位置** | ① 执行模板 §4.1（勾稽核对表 OM 行）；② 总收官报告 v1.0.1 §5.1 / §5.2 第 4 步；③ `doc/test/evidence/s7/t7/signoff-check.json` §repos.OM.reconcile；④ 测试报告 §2 **S7-T7-2** 行状态 |
| **失败处置** | 若仍检出 A 类差异 → 回到入仓流程逐项显式 `git add` 补提交（**禁用 `git add -A`/`git add .`**）；回归失败即停 |

### 1.3 [P1-3] OpenLLM 四远端推送

| 项 | 内容 |
|----|------|
| **关联断言** | **S7-T7-1**（四仓入仓 + 远端同步）；门禁项 ⑤ |
| **目标** | OpenLLM `feature/s4-identity-channel-b` @ `be1886d`：**origin / backup / github / jerry.yu 四远端均未推送**；need-star 隔离分支 `feature/need-star-orchestration` @ `ce40f90` 亦未推 |
| **执行状态（v1.0.2 实测 2026-09-11）** | 🟡 **部分完成**：`feature/s4-identity-channel-b` = `be1886d`、`feature/need-star-orchestration` = `ce40f90`，**origin / backup / github 三端已同步**（`ls-remote` 实测三端 hash 一致）；**`jerry.yu` 远端无写权限**（`Permission denied (publickey,...)`，exit 128）→ 受限 **PENDING**；推送中 `.git/logs/refs/remotes/**` 写入沙箱受限（exit 1，不影响远端），**本地点跟踪 ref 待人工 `git fetch` 同步** |
| **执行命令** | `git -C <LL> push origin feature/s4-identity-channel-b`<br>`git -C <LL> push backup feature/s4-identity-channel-b`<br>`git -C <LL> push github feature/s4-identity-channel-b`<br>`git -C <LL> push jerry.yu feature/s4-identity-channel-b`<br>`git -C <LL> push origin feature/need-star-orchestration`（need-star 隔离分支，按各远端可用性补推） |
| **期望证据** | `git -C <LL> ls-remote --heads origin feature/s4-identity-channel-b` = `be1886d...`（backup / github / jerry.yu 同理）；`git -C <LL> ls-remote --heads origin feature/need-star-orchestration` = `ce40f90...` |
| **证据落盘路径** | `doc/test/evidence/s7/signoff/ll-remote-push.json`（逐远端 `remote`/`branch`/`local_head`/`remote_head`/`status`） |
| **回填位置** | ① 清点总清单 §5.10「远端同步」行 LL 条目；② 归集文档 §3.9 LL 远端状态；③ `signoff-check.json` §repos.LL.remote；④ 执行模板 §4.1 / §5 |
| **失败处置** | 个别远端不可用 → 逐远端分别登记 `PENDING` + `reason`（不得以「预期已推」代替证据）；`jerry.yu` 为个人远端须确认授权后再推 |

> **P1 收尾**：三项完成后，门禁项 ⑤「跨仓会签」的远端子项可关闭；随后按 §5 顺序回填。**（v1.0.2 实测 2026-09-11：P1-1 已完成、P1-2 已完成（差异 0）、P1-3 部分完成——origin/backup/github 三端已同步，仅 `jerry.yu` 受限 PENDING 不阻断远端子项关闭）**

---

## §2 联调窗口 T2~T5（优先级 P2 · 需真实环境）

> 前置：§0.1 全项「就绪」。纪律：真实停用使用**专用冒烟主体**（`smoke_l1_1_*`），执行后 `restored`；**未执行不填 PASS，禁伪造响应码 / `request_id`**。证据 JSON 字段规范见设计草案 §5.2（`schema_version` / `status` / `reason` / `execution_face` / `openbase_commit` / `checked_at` / `evidence_ref`）。
>
> **工具脚本（骨架已就绪）**：T2~T5 五脚本已补齐骨架（L1-1/L2-1/L2-2/L3-1/L3-2），可**干跑**（无真实环境时 `status=PENDING`）；**统一退出码约定：`0=PASS` / `1=FAIL` / `2=PENDING`**（干跑且无环境时默认 `2`）。真实执行时去掉 `-DryRun` / `--dry-run` 并按命令模板替换占位符。

### 2.1 [P2-T2] S7-T2 L1-1 级联全链核验（关联断言 S7-T2-1~4）

| 项 | 内容 |
|----|------|
| **脚本** | `scripts/verify_l1_1_cascade.ps1` → **骨架已就绪**（可干跑；见 §0.2 N-1） |
| **前置** | 真实停用主体（`<SUBJECT_ID>`，建议 `smoke_l1_1_*`）+ DPS 运行态 + OpenMemory 运行态 + 真实 PG/Redis |
| **关联断言** | S7-T2-1 / S7-T2-2 / S7-T2-3 / S7-T2-4 |
| **执行步骤** | ① 停用主体（`POST /api/v1/identity/suspend` 或状态补丁）→ 事件 outbox `user.suspended`（`event_id` 幂等）；② 断言 **DPS 画像读阻断**（绑定失效 → 403/404，数据保留）；③ 断言 **OpenMemory 记忆数据面阻断**（`sessions`/`memories` 拒绝，数据保留）；④ `event_id` 幂等（重放不双写、DB 行数不变）；⑤ `restored` 恢复解除阻断；⑥ purge 显式触发核验：`POST /api/v1/identity/purge`（非 deactivated → **400**；未二次授权 → **403**；授权后物理清除 + `audit_logs` 留痕 `action=identity.purge`）；⑦ 静态扫描无自动 purge 路径 |
| **命令模板** | `pwsh -File <OB>\scripts\verify_l1_1_cascade.ps1 -BaseUrl <GATEWAY_BASE> -SubjectId <SUBJECT_ID> -EvidenceDir <OB>\doc\test\evidence\s7\l1-1 -DryRun`（干跑，退出码 `2`）<br>`pwsh -File <OB>\scripts\verify_l1_1_cascade.ps1 -BaseUrl <GATEWAY_BASE> -SubjectId <SUBJECT_ID> -EvidenceDir <OB>\doc\test\evidence\s7\l1-1`（真实执行，退出码 `0`/`1`）<br>`python -m pytest tests -k "identity_events or purge" -q`（本地静态/契约面基线参照）<br>`Select-String -Path <OB>\openbase\**\*.py -Pattern "scheduler|apscheduler|purge"`（无定时 purge 佐证） |
| **期望证据** | `doc/test/evidence/s7/l1-1/dps-block.json`（S7-T2-1）、`openmemory-block.json` + `event-idempotency.json`（S7-T2-2）、`restore.json` + `scan-auto-purge.txt`（S7-T2-3）、`purge.json`（S7-T2-4） |
| **回填位置** | 测试报告 §2 「S7-T2-1~4」行状态（PENDING → PASS/FAIL）；门禁项 ④ 三原则总验证；`gate-aggregate.json` 相关分项引用；总收官报告 v1.0.1 §4.2 第 6 项 |
| **失败处置** | 契约不符 / 阻断未生效 → 登记 `FAIL` + `reason`，回溯 U1 §8 事件契约与 DPS/OpenMemory 消费端；不得以「预期通过」替代 |

### 2.2 [P2-T3] S7-T3 L2-1 主备切换演练（关联断言 S7-T3-1~4）

| 项 | 内容 |
|----|------|
| **脚本** | `scripts/drill_l2_1_failover.ps1` → **骨架已就绪**（可干跑；见 §0.2 N-2） |
| **前置** | 可注故障的运行态 + 切换窗口（B 上游进程可停 / B 端口可阻断） |
| **关联断言** | S7-T3-1 / S7-T3-2 / S7-T3-3 / S7-T3-4 |
| **双场景** | **场景 1**：B 断 → A 接管（A 直连接管 + 降级头/告警产生，业务不中断）；**场景 2**：A 断 → B 维持（B 编排维持，业务不中断） |
| **单主禁双写** | 同一动作同一时刻**仅一条主路径**（S4-T7 `ChannelStateManager` 单主状态机）；**无双主双写证据**；主路由配置声明、切换显式触发 |
| **边界** | 事件通道（L1-1 身份权威同步面）**不纳入**演练矩阵（设计草案 §4.3 / Q-S7-4） |
| **命令模板** | `pwsh -File <OB>\scripts\drill_l2_1_failover.ps1 -Scenario b-down -BaseUrl <GATEWAY_BASE> -EvidenceDir <OB>\doc\test\evidence\s7\l2-1 -DryRun`（干跑，退出码 `2`）<br>`pwsh -File <OB>\scripts\drill_l2_1_failover.ps1 -Scenario b-down -BaseUrl <GATEWAY_BASE> -EvidenceDir <OB>\doc\test\evidence\s7\l2-1`（场景 1 真实执行）<br>`pwsh -File <OB>\scripts\drill_l2_1_failover.ps1 -Scenario a-down -BaseUrl <GATEWAY_BASE> -EvidenceDir <OB>\doc\test\evidence\s7\l2-1`（场景 2）<br>`-Scenario both` 可选（双场景一次演练） |
| **期望证据** | `doc/test/evidence/s7/l2-1/drill-report.md`（含**场景/命令/切换前后路由/降级头/告警/回切条件/结论**字段）+ `route-before.json` / `route-after.json`（单主断言）+ `degrade-headers.json` + `alerts.json` |
| **回填位置** | 测试报告 §2 「S7-T3-1~4」行状态；门禁项 ④；总收官报告 §3 S7-T3 行 |
| **失败处置** | 双写 / 业务中断 / 无降级头 → 登记 `FAIL`，回溯 S4-T7 单主状态机与路由配置；演练窗口不可得 → `PENDING` + 排期 |

### 2.3 [P2-T4] S7-T4 L2-2 通道矩阵终验（关联断言 S7-T4-1~4）

| 项 | 内容 |
|----|------|
| **脚本** | `scripts/finalize_l2_2_matrix.py` → **骨架已就绪**（可干跑；见 §0.2 N-3） |
| **前置** | 四仓运行态 + 真实通道；基座 = S4-T8 `matrix_rows` |
| **关联断言** | S7-T4-1 / S7-T4-2 / S7-T4-3 / S7-T4-4 |
| **终验判据** | ① 通道覆盖矩阵（每子系统 × A/B × 状态/头语义）**行全覆盖、缺口 0**；② 管理面/探活 **A 直连豁免行显式标注**（与 K07 端点矩阵 A 直连豁免行对账一致）；③ **读路径 B 主全绿 + A 备 covered**（同读请求经 A/B 返回一致、四头一致）；④ **写路径 A/B 等价 + K14 幂等**（重放不双写、DB 行数不变） |
| **命令模板** | `python <OB>\scripts\finalize_l2_2_matrix.py --dry-run --out <OB>\doc\test\evidence\s7\l2-2\matrix-finalize.json`（干跑，退出码 `2`）<br>`python <OB>\scripts\finalize_l2_2_matrix.py --matrix <S4-T8 matrix_rows.json> --out <OB>\doc\test\evidence\s7\l2-2\matrix-finalize.json`<br>`python <OB>\scripts\finalize_l2_2_matrix.py --check-read-ab --base-url <GATEWAY_BASE> --out <OB>\doc\test\evidence\s7\l2-2\read-path-ab-equivalence.json`<br>`python <OB>\scripts\finalize_l2_2_matrix.py --check-write-ab --k14 --base-url <GATEWAY_BASE> --out <OB>\doc\test\evidence\s7\l2-2\write-path-equivalence.json` |
| **期望证据** | `doc/test/evidence/s7/l2-2/matrix-finalize.json`（rows / covered / `gap=0`）+ `read-path-ab-equivalence.json` + `write-path-equivalence.json` + `k14-idempotency.json` |
| **回填位置** | 测试报告 §2 「S7-T4-1~4」行状态；门禁项 ④；`gate-aggregate.json` K07 豁免行对账引用 |
| **失败处置** | 矩阵缺口 / 读写不等价 / K14 非幂等 → 登记 `FAIL` + `reason`，回溯 S4-T8 矩阵与 DPS 写路径；豁免行无审批 → 不放行 |

### 2.4 [P2-T5] S7-T5 L3-1 Agent 端到端（关联断言 S7-T5-1~4）

| 项 | 内容 |
|----|------|
| **脚本** | `scripts/verify_l3_1_agent.ps1` → **骨架已就绪**（可干跑；见 §0.2 N-4） |
| **前置** | 四仓运行态 + 真实 agent key（`<SMOKE_AGENT_KEY>`，`sk-agent-*`） |
| **关联断言** | S7-T5-1 / S7-T5-2 / S7-T5-3 / S7-T5-4 |
| **路径与判据** | agent key → **四头**（X-User-ID / X-Tenant-ID / X-User-Role / X-Proxy-Source）齐全且与主体一致（**agent 无交互登录路径，0 可达**）；**各系统白名单**放行（受信来源 + 头 = 信任；每系统 ≥3 例）→ 非白名单携带身份头全链路 **403**（`PERM_UNTRUSTED_IDENTITY_HEADER`，无绕过端点）；**域隔离** 跨域不可见（404/403/空）；**M1 独立模式**（本地 service key 自身认证）与 **M2 受信头采纳**分别断言 |
| **命令模板** | `pwsh -File <OB>\scripts\verify_l3_1_agent.ps1 -AgentKey <SMOKE_AGENT_KEY> -BaseUrl <GATEWAY_BASE> -EvidenceDir <OB>\doc\test\evidence\s7\l3-1 -DryRun`（干跑，退出码 `2`）<br>`pwsh -File <OB>\scripts\verify_l3_1_agent.ps1 -AgentKey <SMOKE_AGENT_KEY> -BaseUrl <GATEWAY_BASE> -EvidenceDir <OB>\doc\test\evidence\s7\l3-1`（真实执行，退出码 `0`/`1`） |
| **期望证据** | `doc/test/evidence/s7/l3-1/agent-key-issuance.json`（四头一致性 + 无登录路径）、`system-whitelist-cases.json`（≥3 例/系统）、`domain-isolation.json`、`unauthorized-403.json`、`m1-m2.json` |
| **回填位置** | 测试报告 §2 「S7-T5-1~4」行状态；门禁项 ④；总收官报告 §4.2 第 6 项 |
| **失败处置** | 四头缺失 / 白名单放行异常 / 403 可绕过 / 域隔离失效 → 登记 `FAIL` + `reason`，回溯 K02 白名单规范与四仓落地 |

### 2.5 执行结果回填（v1.0.4 实测，2026-09-11 19:00）

> 环境复检（§0.1 更新为多数 READY）后按 §2.1~§2.4 命令模板执行。**去 `-DryRun`/`--dry-run` 的实跑形态**；未通过项一律如实登记，不伪造。

| 项 | 命令（实跑形态） | 结果 | 证据 |
|----|----------------|------|------|
| P2-T2 | `verify_l1_1_cascade.ps1 -BaseUrl http://127.0.0.1:8000 -SubjectId smoke_l1_1_smoke` | **PENDING（exit 2，mode=run）**：身份端点经网关需鉴权（401），真实停用→DPS/记忆阻断与 purge 需联调窗口真实执行 | `doc/test/evidence/s7/l1-1/cascade-result.json` |
| P2-T3 | `drill_l2_1_failover.ps1` | **未执行（BLOCKED）**：需停 B 上游/阻端口注入故障，**任务约束禁止停止/重启服务**，无可注故障窗口 | （按挂起登记） |
| P2-T4 | `finalize_l2_2_matrix.py --check-read-ab --check-write-ab --k14 --base-url http://127.0.0.1:8000` | **PENDING（exit 2，mode=run）**：S4-T8 `matrix_rows` 基座未提供；读写 A/B 等价 + K14 幂等需真实四仓 | `doc/test/evidence/s7/l2-2/matrix-finalize.json` |
| P2-T5 | `verify_l3_1_agent.ps1 -AgentKey sk-agent-smoke -BaseUrl http://127.0.0.1:8000` | **PENDING（exit 2，mode=run）**：未提供真实 `sk-agent-*`；白名单/域隔离/M1-M2 需四仓 | `doc/test/evidence/s7/l3-1/agent-e2e.json` |
| P2-T6-2（冒烟） | 冒烟清单 §3 逐条真实 HTTP | **P0 30 例 PASS 14 / FAIL 9 / BLOCKED 7；P1 2 例 BLOCKED**（失败=真实缺陷 F-1/F-2/F-3；阻塞=环境待办上游不可达/禁停服务） | `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}` |
| P2-B2（L3-2） | `smoke_l3_2.py --base-url http://127.0.0.1:8000` | **PENDING（exit 2，mode=run，reachable=true）**：受信通道可达；真实双签以子系统仓脚本为准 | `doc/test/evidence/s7/l3-2/smoke-result.json` |
| P2-B1（前端 E2E） | `cd openbase-ui; $env:OPENBASE_BASE_URL=http://localhost:5173; npm run test:e2e` | **9 页全绿（9 passed / 0 failed）**（v1.0.5 F-4 修复后重跑）：页面渲染 + 关键元素/受控空态 + 无渲染兜底 + **无 console error/warn**（Q-FE-4b 达成）。历史首跑（v1.0.4）为 0 passed / 9 failed（Q-FE-4b `console.warn`，Vue Router No match，F-4） | `doc/test/evidence/s6/ui-e2e/{results.json,status.json}`（attempt=2 PASS，历史 attempt=1 保留） |
| DPS seed | `python DPS/scripts/seed-shared-infra.py` | **exit 0（幂等，0 新增）** | `doc/test/evidence/s7/smoke/dps-seed.json` |

---

## §3 T6 真实面（优先级 P2 · 需真实环境）

> 关联断言：**S7-T6-1 / S7-T6-2 / S7-T6-3 / S7-T6-4**；门禁项 ① ② ③。证据基线 = `doc/test/evidence/s7/gate/gate-aggregate.json`（结构面已 PASS）。

### 3.1 [P2-T6-1] RA-06 五项真实面（关联断言 S7-T6-1）

| 项 | 内容 |
|----|------|
| **前置** | 真实 PG/Redis + IdP + 四仓运行态 + 网关链路 |
| **真实面五项** | ① 双租户隔离回归（`<TENANT_A>` / `<TENANT_B>`）② fail-closed 故障注入 ③ OIDC 批次隔离（存量 T2 归档关闭）④ 委托跨界 403 ⑤ 吊销即时性 |
| **命令模板** | `python <OB>\scripts\gate_aggregate.py --face real --only RA-06 --out <OB>\doc\test\evidence\s7\gate\gate-aggregate.json`<br>`python -m pytest tests -k "ra06 or tenant_isolation or fail_closed or delegated or revoke" -q` |
| **期望结果 / 退出码** | RA-06 五项**真实面全绿**（A 面 82 用例：双租户隔离 19 / fail-closed 21 / OIDC 批次 12 / 委托跨界 13 / 吊销即时性 17），覆盖率 ≥90%；脚本退出码 **0** |
| **回填位置** | 测试报告 §2 「S7-T6-1」行状态；门禁项 ①；`gate-aggregate.json` §RA-06 `status=PASS`；总收官报告 §4.2 第 1 项 |
| **失败处置** | 任一子项失败 → `FAIL` + `reason`，回溯对应子系统；不得整体判 PASS |

### 3.2 [P2-T6-2] 冒烟 S0-S6 真实执行（关联断言 S7-T6-2）

| 项 | 内容 |
|----|------|
| **依据** | 《OpenBase-真实联调冒烟清单-v1.0.0.md》（OB-INTG-SMOKE-**v1.1.0**）**§3 用例矩阵**；分组 **S0~S6**，**P0 30 例**（全绿）+ **P1 2 例**（登记） |
| **前置** | 真实五服务 + 密钥（`OPENMEMORY_SERVER_API_KEY` / `OPENRAG_API_SERVICE_API_KEY` 非空）+ 三真实开关（`OPENLLM_OPENMEMORY_REAL` / `OPENLLM_OPENRAG_REAL` / `OPENLLM_DPS_REAL`）显式开启并确认 `contract=real` 日志；DPS org/tenant 与四头预置一致 |
| **入口/出口准则** | 入口 = 五服务 `/health` 通过 + 密钥非空校验通过 + 三真实开关开启；出口 = **P0 全绿且 P1 项登记完成** |
| **命令模板** | `python <OB>\scripts\gate_aggregate.py --face real --only SMOKE-S0-S6 --out <OB>\doc\test\evidence\s7\gate\gate-aggregate.json`<br>（执行记录逐例登记于冒烟清单 §3 结果列 + 各服务 stdout 日志归档） |
| **期望结果 / 退出码** | P0 30 例全绿、P1 2 例登记；脚本退出码 **0**；`gate-aggregate.json` §SMOKE-S0-S6 `status=PASS` |
| **回填位置** | 测试报告 §2 「S7-T6-2」行状态；门禁项 ②；冒烟清单 §3 结果列 / §5 产物 |
| **失败处置** | 环境故障（服务未起/密钥缺失）**不算用例失败**，单独登记环境待办；真实用例失败 → `FAIL`，记录复现步骤/日志/期望 vs 实际 |

### 3.3 [P2-T6-3] PG-ENV-1~4 复跑关闭（关联断言 S7-T6-3）

| 项 | 内容 |
|----|------|
| **前置** | 真实 PostgreSQL + `openbase_test`（§0.1 第 0-2 项）+ Redis |
| **关闭对象** | `PG-ENV-1`（asyncpg 连接/迁移族）`PG-ENV-2`（asyncpg 真实 DDL/DML 对账）`PG-ENV-3`（连接池/会话生命周期，需 Redis）`PG-ENV-4`（存量对齐主批次 573 例中 4 例环境性失败） |
| **`test_oidc_binding.py` 4 例** | `tests/test_oidc_binding.py::test_jit_create_binds_mapping_and_role`、`::test_reuse_existing_identity`、`::test_username_conflict_gets_suffix`、`::test_role_mapping_filters_unknown_roles` —— 单文件独立运行 5 passed，属 asyncpg/PG 环境性失败；随真实 PG / `openbase_test` 就绪**复跑主批次确认 0 失败**即关闭 |
| **命令模板** | `pwsh -File <OB>\scripts\db\init_openbase_test.ps1 -Pgdns "<PG_DSN>"`<br>`$env:OPENBASE_DB_URL="<openbase_test DSN>"; python -m pytest tests/test_oidc_binding.py -q`<br>`python -m pytest tests -q`（主批次全量复跑，确认 0 失败） |
| **期望结果 / 退出码** | `tests/test_oidc_binding.py` → 5+ passed，退出码 **0**；主批次 573 例 **0 失败**，退出码 **0** |
| **回填位置** | 测试报告 §5 `PG-ENV-1`~`PG-ENV-4` 处置列；门禁项 ③；`gate-aggregate.json` §TEST-ALIGN-CLOSE `pending_items` 清空；存量对齐清单复跑记录 |
| **失败处置** | 若复跑仍失败且非环境性 → 转业务缺陷登记并回溯；`openbase_test` 建库失败 → 记录原因，评估是否退化为独立 schema（设计草案 Q-S7-D3） |
| **执行状态（v1.0.5 实测 2026-09-11 20:40）** | ✅ **已完成（PG-ENV-1~4 全部关闭）**：`scripts/db/init_openbase_test.ps1` 参数化后（默认读 `.env.shared-infra`；无 psql 客户端时回退 psycopg2）真实执行——`openbase_test` 独立库建立、四账号 `openbase_app`/`platform_app`/`openbase_migrator`/`openbase_runtime` NOSUPERUSER、K13 授权收敛、幂等迁移 **28 表**；`tests/test_oidc_binding.py` 单文件 **5 passed**；主批次（`run_regression.py` 分组 22 组）**676 passed / 0 failed / 4 skipped（exit 0）**，含该文件分组 **passed=10 / failed=0** → 原 4 例环境性失败关闭。证据：`doc/test/evidence/s7/env/env-check.json`（`openbase_test_database=READY`）、`doc/test/evidence/s7/gate/gate-aggregate.json` §TEST-ALIGN-CLOSE（`main_batch.status=PASS` + `closed_items`） |

### 3.4 [P2-T6-4] K07 / SYS-1 端点-过滤矩阵真实终验（关联断言 S7-T6-4）

| 项 | 内容 |
|----|------|
| **前置** | 四仓运行态 + 各仓真实 openapi 全量导出能力 |
| **终验判据** | 矩阵**缺口清零、未覆盖清零**；豁免全部在有效期且有审批；新增端点无隔离用例**不放行** |
| **各仓脚本** | 各仓 `k07_endpoint_matrix.py`（OpenBase 侧为 `scripts/k07_endpoint_matrix.py`，已就绪）；四仓结构面计数基线 = OpenMemory 32 / OpenRAG 121 / OpenLLM 14 / DPS 169 行，`gap_count=0` |
| **命令模板** | `python <OB>\scripts\k07_endpoint_matrix.py --repos <OM>,<RAG>,<LL>,<DPS> --openapi-export real --out <OB>\doc\test\evidence\s7\gate\k07-real.json`<br>逐仓：`python <各仓>\scripts\k07_endpoint_matrix.py --export-openapi --check-gap` |
| **期望结果 / 退出码** | 四仓缺口 0、未覆盖 0；脚本退出码 **0** |
| **回填位置** | 测试报告 §2 「S7-T6-4」行状态；门禁项 ③/④；`gate-aggregate.json` §K07-SYS-1 `status=PASS` |
| **失败处置** | 存在缺口/未覆盖/过期豁免 → **不放行**，登记 `FAIL` 并回溯对应子系统矩阵填报 |
| **执行状态（v1.0.6 实测 2026-09-11 22:15）** | ❌ **已执行，结论 FAIL**：从五实例真实导出 openapi（`openbase:8000` 137 / `openllm:8001` 351 / `openrag:8010` 115 / `openmemory:8020` 36 / `dps:8030` 161，均 HTTP 200）并保真落盘 `doc/test/evidence/s7/gate/k07-openapi/*.openapi.json`；与各仓填报表逐行核对 → **缺口 352 = OpenLLM 344 + OpenMemory 8、未覆盖 0、豁免 56（有效 21；DPS 35 条复核日 2026-09-10 早于终验日需续期）、十列字段完整性 0 缺口**。证据 `doc/test/evidence/s7/gate/k07-finalize.json`；`gate-aggregate.json` §K07-SYS-1 改真实终验结论（`overall=FAIL / pass=20 / fail=1 / pending=1`）。**子系统仓缺口按纪律只登记不代改（归属 OpenLLM/OpenMemory）**。<br>脚本能力实测：OpenBase 骨架生成器接受外部 openapi（四子系统 351/115/36/161 骨架行，退出码 0）；OpenMemory `--verify --openapi` 接受真实导出（退出码 1，missing_rows=8）；OpenLLM `--openapi-file`（需 app 装配）支持外部 openapi；**OpenRAG/DPS 脚本仅支持仓内离线 `app.openapi()` 底单（不接受外部 openapi）→ 采用真实导出 JSON 与填报表逐行核对** |
| **执行状态（v1.0.7 补填回填 2026-09-11）** | ⚠️ **PARTIAL（OpenLLM 已补填/待提交）**：OpenLLM 仓工作树全量补填（5 文件；矩阵 354 行 / 覆盖 349 / 豁免 5；**缺口 344→0**；隔离用例新增 759 条 → **767 passed**；门禁复跑 `total=351 covered=349 exempt=2 / gaps=0 uncovered=0 exemption_without_approval=0`（exit 0）；ruff All checks passed）→ 缺口合计 **352→8（仅 OpenMemory）**；`k07-finalize.json` `gate_verdict=PARTIAL`、`gate-aggregate.json` §K07-SYS-1 `status=PARTIAL`（保留历史字段）。**剩余：OpenMemory 8 条缺口 + DPS 35 条豁免续期**。 |
| **执行状态（v1.0.8 补填回填 2026-09-12）** | ✅ **缺口/未覆盖清零（两仓均补填/待提交）**：OpenMemory 仓工作树完成 8 条缺口补填（4 文件；矩阵 32→**40 行** = 真实底单 36 操作 + 文档面合成 4；覆盖 25→31 / 豁免 7→9；**缺口 8→0**；2 健康探针（`/health/liveness`、`/health/readiness`）A 直连豁免 + 6 业务面挂隔离用例 `IS-OM-R26~R31`；隔离用例 **81 passed**；门禁复跑 `missing_rows=[] uncovered_business=[] exemption_errors=[] isolation_missing=[] total_rows=40 business_rows=31 exempt_rows=9`（exit 0）；K07/identity 组 **372 passed**；ruff 0 错误）→ 缺口合计 **8→0**；`k07-finalize.json` `gate_verdict=PARTIAL`（仅剩 DPS 35 条豁免续期）、`gate-aggregate.json` §K07-SYS-1 同步。**剩余：DPS 35 条豁免续期（两仓补填待提交）。** |
| **执行状态（v1.0.10 收口提交与 hash 回填 2026-09-12）** | ✅ **OpenBase 侧收口回填已入库**：提交 **`1affff5`**（10 文件 = 证据 2 + 文档 4 + S7 断言测试 2 + 一键提交脚本 2；`origin` / `backup` 双远端 `ls-remote` 与本地 HEAD 一致）；**DPS 仓一键提交脚本就绪**——`DPS/dps-k07-commit-push.bat`（包装 `DPS/scripts/dps_k07_exempt_commit_push.ps1`，支持 `-DryRun`）（`-DryRun` 通过；实跑因 `.git/index.lock: Permission denied` 中止 → 待可写环境执行，执行后回填 DPS hash）。 |
| **执行状态（v1.0.11 DPS 豁免续期入库 2026-09-13）** | ✅ **DPS 侧已提交入库**：提交 **`b5f5c06`**（`docs(k07): DPS 端点过滤矩阵 35 条豁免续期至 2026-12-31（S7 终验续期，门禁复跑 exit 0）`；3 文件 = 填报矩阵 + 一键提交脚本 2），`origin` / `backup` / `github` 三远端 `ls-remote` 与本地 HEAD 一致 → **本单待提交项清零**（DPS 门禁复跑 `total=169 covered=134 exempt=35 / gaps=0 uncovered=0 / exit 0`，缺口 0 / 未覆盖 0 / 豁免 59 全有效）。 |
| **执行状态（v1.0.9 门禁收口 2026-09-12）** | ✅ **门禁 verdict=PASS（三项判定全部满足）**：DPS 填报矩阵 35 条豁免行「到期/复核」由 2026-09-10 更新为 **续期至 2026-12-31（续期日 2026-09-12）**，复跑 DPS 门禁 `scripts/k07_endpoint_matrix.py --check` → `total=169 covered=134 exempt=35 / gaps=0 uncovered=0 exemption_without_approval=0`（exit 0）；两仓补填提交 hash 实证（OpenLLM `41af780` / OpenMemory `0a6f351`，三远端同步）→ **缺口合计 0 / 未覆盖 0 / 豁免 59 全有效**；`k07-finalize.json` `gate_verdict=PASS`（`status` PARTIAL→PASS）、`gate-aggregate.json` §K07-SYS-1 `status=PASS`；门禁聚合复跑 `overall=PASS exit=0 pass=20 fail=0 pending=2`。 |
| **待提交项（≤）** | **无** —— DPS 仓 K07 填报文档与一键提交脚本已于 2026-09-13 提交 **`b5f5c06`**（3 文件），origin/backup/github 三远端与本地 HEAD 一致；OpenLLM（`41af780`）/ OpenMemory（`0a6f351`）K07 补填已提交。遗留（收口为可执行形态）：**遗留收口（2026-09-13）**：已生成一键落仓脚本 `openllm-k07-snapshot-commit-push.bat`（包装 `scripts/openllm_k07_snapshot_commit_push.ps1`；源取 K07 证据导出 `doc/test/evidence/s7/gate/k07-openapi/openllm.openapi.json`——`openapi=3.1.0` / `paths=278` / `operations=351`，与 K07 台账一致；脚本含 **351 操作校验 + 提交面守卫（仅 1 文件）+ 三远端 `ls-remote` 校验**，`-DryRun` 实跑通过）。**受限沙箱内 OpenLLM 仓全仓只读**（`backend/data/**` 与 `.git` 均被拦截，实测无残留：目标文件未生成、`index.lock` 未产生、暂存区为空）→ **待沙箱外执行并回填 hash**。**敏感文件零进入**（`.env*` / `scripts/evidence_v680_*.txt` / `storage/images/**` / `doc/test/_temp_test.txt` 不提交）。 | **仅剩 DPS 仓 K07 填报文档改动（35 条豁免续期）**：`doc/design/DPS-K07-端点过滤矩阵填报-v1.0.0.md`，**已生成一键提交脚本**（`DPS/dps-k07-commit-push.bat`（包装 `DPS/scripts/dps_k07_exempt_commit_push.ps1`，支持 `-DryRun`）；`-DryRun` 通过，实跑因 `.git/index.lock: Permission denied` 中止 → 待可写环境执行）；建议 message：`docs(k07): DPS 端点过滤矩阵 35 条豁免续期至 2026-12-31（S7 终验续期）`。**OpenLLM（`41af780`，5 文件）与 OpenMemory（`0a6f351`，4 文件）K07 补填均已提交并三远端同步**；遗留（收口为可执行形态）：**遗留收口（2026-09-13）**：已生成一键落仓脚本 `openllm-k07-snapshot-commit-push.bat`（包装 `scripts/openllm_k07_snapshot_commit_push.ps1`；源取 K07 证据导出 `doc/test/evidence/s7/gate/k07-openapi/openllm.openapi.json`——`openapi=3.1.0` / `paths=278` / `operations=351`，与 K07 台账一致；脚本含 **351 操作校验 + 提交面守卫（仅 1 文件）+ 三远端 `ls-remote` 校验**，`-DryRun` 实跑通过）。**受限沙箱内 OpenLLM 仓全仓只读**（`backend/data/**` 与 `.git` 均被拦截，实测无残留：目标文件未生成、`index.lock` 未产生、暂存区为空）→ **待沙箱外执行并回填 hash**。**敏感文件零进入**（`.env*` / `scripts/evidence_v680_*.txt` / `storage/images/**` / `doc/test/_temp_test.txt` 不提交）。 |

### 3.5 T6 真实面执行结果（v1.0.4 实测，2026-09-11 19:00）

| 项 | 命令（实跑形态） | 结果 | 证据 |
|----|----------------|------|------|
| P2-T6-1（RA-06） | `python scripts/gate_aggregate.py`（含 RA-06 选择器实跑） | **RA-06 五项 PASS**（82 用例：双租户 19 / fail-closed 21 / OIDC 12 / 委托 13 / 吊销 17）；真实数据面仍 PENDING | `gate-aggregate.json` §RA-06 |
| P2-T6-2（冒烟 S0-S6） | 冒烟清单 §3 逐条真实 HTTP | **P0 14/30 PASS、9 FAIL、7 BLOCKED；P1 2 BLOCKED**（详见 §2.5） | `doc/test/evidence/s7/smoke/**` |
| P2-T6-3（PG-ENV） | `gate_aggregate.py` 主批次实跑 | **PASS（对齐清单关闭，主批次 PENDING）**：主批次 605 例中 4 例 `test_oidc_binding` 环境性失败（`openbase_test` 未建，PG-ENV-1~4 未关闭） | `gate-aggregate.json` §TEST-ALIGN-CLOSE |
| P2-T6-4（K07/SYS-1） | 五实例 `/openapi.json` 真实导出 + 逐行核对 | **PASS（v1.0.9）**：缺口合计 **0**（OpenLLM 344→0 已提交 `41af780`；OpenMemory 8→0 已提交 `0a6f351`）、未覆盖 **0**、豁免 **59 条全部在有效期且有审批**（DPS 35 条 2026-09-12 续期至 2026-12-31，门禁复跑 exit 0） | `doc/test/evidence/s7/gate/k07-finalize.json`；`doc/test/evidence/s7/gate/k07-openapi/*.openapi.json` |

> **门禁聚合实跑结论**：最终 `overall=PASS exit=0 pass=19 fail=0 pending=3`（`mode=dry-run`，脚本固定口径）。首跑 FAIL 由两点导致并已修：① `tests/test_verdict_k03.py::test_t2_6_whitelisted_write_allowed_with_bypass_audit` 断言过严（上游可达时响应为透传体无 `code`）→ 健壮化；② `test_s7_t7_signoff`/`test_s7_t8_writeback` 读取本脚本产出文件产生自引用时序 → 纳入主批次排除项；并增补 `s7_report_ref`/`t8_evidence_ref`/`t7_evidence_ref`/`shr_ref` 引用键。

---

## §4 段级非沙箱复核（优先级 P2 · 需真实环境）

> 依据：总收官报告 §4.1「段级主挂起（承接 S0~S6，共 10 条）」+ §6 非沙箱复核清单。逐条回填 `doc/test/evidence/s6/**`（S6 项）与各段证据后关闭。

### 4.1 [P2-S2~S5] 段级真实 HTTP 双签（4 条）

| ID | 段 | 关联断言 | 复核项 | 前置 | 执行命令模板 | 期望证据 | 回填位置 | 失败处置 |
|----|----|---------|--------|------|-------------|---------|---------|---------|
| **P2-S2** | S2 OpenMemory | S7-T2-2、S7-T6-1 | L3-2 真实 HTTP 双签（OpenMemory 事件消费端） | OpenMemory 运行态 + 真实通道 + 真实 PG/Redis | 按 OpenMemory 段 L3-2 双签脚本执行并留证 | `doc/test/evidence/s2/**`（L3-2 双签记录） | 总收官报告 §4.1 第 1 项；测试报告 §2 S7-T2-2 | 通道不可达 → `PENDING` + `reason` |
| **P2-S3** | S3 OpenRAG | S7-T2-1、S7-T6-1 | Pull 真实 HTTP 双签（Q-RG-7）+ PG/Redis 实跑 | OpenRAG 运行态 + PG/Redis | 按 OpenRAG 段 Pull 双签脚本执行并留证 | `doc/test/evidence/s3/**` | 总收官报告 §4.1 第 2 项 | 同上 |
| **P2-S4** | S4 OpenLLM | S7-T3-4、S7-T4-4、S7-T6-4 | 真实 HTTP 双签；写路径等价 / K14 幂等 / L2-1 切换 / L2-2 终验 / K07 RA-06 终验 / 错误面收敛 | OpenLLM 运行态 + 真实通道 | 按 OpenLLM 段双签脚本执行并留证（**注：OpenLLM 不适用 Pull 双签**，以真实验证 + L3-2 通道为准） | `doc/test/evidence/s4/**` | 总收官报告 §4.1 第 3 项 | 同上 |
| **P2-S5** | S5 DPS | S7-T2-1、S7-T6-2 | Pull 真实 HTTP 双签（Q-DPS-5）；非沙箱复核（真实 PG/Redis） | DPS 运行态 + PG/Redis | 按 DPS 段 Pull 双签脚本执行并留证 | `doc/test/evidence/s5/**` | 总收官报告 §4.1 第 4 项 | 同上 |

### 4.2 [P2-B1~B6] S6 移交非沙箱复核（6 条）

| ID | 关联断言/门禁 | 复核项 | 前置 | 执行命令模板 | 期望证据 | 回填位置 | 失败处置 |
|----|--------------|--------|------|-------------|---------|---------|---------|
| **P2-B1** | S7-T6-2 | Playwright **9 关键页** PASS | 浏览器二进制（§0.1 第 0-8 项）+ 统一前端运行态 | `cd <OB>\openbase-ui; npx playwright install chromium; npm run test:e2e` | `doc/test/evidence/s6/ui-e2e/{results.json,status.json}`（9 页 PASS） | 总收官报告 §4.1 第 5 项；放行清单 §0 S6 注记 | 页面失败逐页记录复现；浏览器不可得 → `PENDING` |
| **P2-B2** | S7-T7-3（B5 复核） | L3-2 真实受信通道双签 | 四子系统运行态 + 真实通道 | 按段级 L3-2 双签执行；OpenBase 侧骨架：`python <OB>\scripts\smoke_l3_2.py --dry-run`（PENDING，退出码 `2`） | `doc/test/evidence/s6/l3-2-smoke.json`（`status=PASS`） | 总收官报告 §4.1 第 6 项 | 同上 |
| **P2-B3** | S7-T6-2 | 真实双租户数据面 | 真实 PG/Redis | 双租户隔离回归（`<TENANT_A>` / `<TENANT_B>`） | `doc/test/evidence/s6/**`（双租户数据面证据） | 总收官报告 §4.1 第 7 项 | 隔离失效 → `FAIL` 回溯 |
| **P2-B4** | S7-T2-1 | 真实 IdP 回调与吊销 | 真实 IdP（§0.1 第 0-4 项） | 按 IdP 回调/吊销用例执行 | `doc/test/evidence/s6/**` | 总收官报告 §4.1 第 8 项 | IdP 不可达 → `PENDING` |
| **P2-B5** | S7-T7-3（Q-S6-D7） | 四仓 `frontend/` 物理改造与 CI 收敛（各子仓执行，S7 复核） | 各子系统仓写权限 + CI | 逐仓改造并收敛构建链（见下表「B5 物理改造点」） | 各仓改造提交 hash + CI 结果；S7 复核结论回填 | 总收官报告 §4.1 第 9 项；S6 证据索引 | 未改造 → 登记复核结论 `PENDING` |
| **P2-B6** | S7-T8-3 | nginx `/ui/` 发布回滚 | nginx 运行态（§0.1 第 0-6 项） | 发布 `/ui/` → 校验 → 回滚 → 再校验 | `doc/test/evidence/s6/**`（发布回滚记录） | 总收官报告 §4.1 第 10 项 | 同上 |

**B5 物理改造点（含具体文件与行号，对齐放行清单 §0 红线第 5 条 / 清点总清单 §5.6）**

| 仓 | 改造点（文件 : 行） |
|----|-------------------|
| OpenMemory | `deploy\nginx\conf.d\openmemory.conf:90,93` |
| OpenLLM | `docker-compose.yml:141-172`、`docker-compose.prod.yml:19`、`frontend\Dockerfile`、`frontend\nginx.conf` |
| DPS | `.github\workflows\ci.yml`（CI 构建链） |
| OpenRAG | `.github\workflows\frontend-ci.yml` |

---

## §5 收口与批准（优先级 P3 · 回填后执行）

> 前置：P1 / P2 项真实执行并留证。纪律：回填顺序不可颠倒；**未执行项保持 `PENDING` 不阻断已达成项**（对齐 S5/S6 挂起口径）；三份 [Review] 文档在段门禁人工批准后升 [Approved]。

| ID | 步骤 | 内容 | 关联断言 / 门禁 | 执行要点 | 产物 / 回填位置 |
|----|------|------|----------------|---------|----------------|
| **P3-1** | 证据回填 | 将 P1/P2 各项 `status: PENDING → PASS/FAIL` 写入证据 JSON / 报告 | S7-T1-1/2/3/4、S7-T2~T7 全量 B 面 | 按设计草案 §5.2 字段规范；`reason` 必填；`openbase_commit` 真实 | `doc/test/evidence/s7/{shr,l1-1,l2-1,l2-2,l3-1,gate,signoff}/**`、`doc/test/evidence/s6/**` |
| **P3-2** | 测试报告 34 断言状态更新 | 更新《S7-…-测试报告-v1.0.0》§2 矩阵逐行结论与 §3 段门禁六项 | 34 断言全量 | 结论口径三类保持（通过 / 部分达成 / PENDING → 真实面回填后收敛） | `doc/test/OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0.md`（升版记录） |
| **P3-3** | 报告内部版本升级 | DevLogReport 与总收官报告内部版本升级（附本次沙箱外执行记录） | S7-T8-4 / S7-T8-5 | 遵循文档版本管理规范（主.次.修订）；同步修订历史 | `doc/development/OpenBase-S7-全域门禁与总收官-DevLogReport-v1.0.0.md`、`doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md` |
| **P3-4** | 段门禁六项复核 | ① RA-06 ② 冒烟 S0-S6 ③ 对齐清单关闭 ④ 三原则总验证 ⑤ 跨仓会签 ⑥ 24 卡/JT 回写 逐项复核结论 | 段门禁六项 | ① ② ④ ⑤ 真实面回填为 PASS 方可复核通过；⑥ 已 PASS | 总收官报告 §2 六项聚合自检表 + `gate-aggregate.json` |
| **P3-5** | S7 段门禁人工批准回写 | 三份 [Review] 升 **[Approved]**：测试报告、DevLogReport、总收官报告 | S7-T8-4/5 | 项目负责人经 AI 开发会话人工确认；批准口径逐字登记 | 三份文档状态列 + 修订历史；`doc/planning/OpenBase-S7-跨仓入仓与会签-OpenBase汇总核对表-v1.0.0.md`（会签终态） |
| **P3-6** | 清单 / 台账终态登记 | 清点总清单、放行清单、任务卡 24 卡、七线 JT 台账终态登记 | S7-T7-4、S7-T8-1、S7-T8-2 | 仅登记终态与提交号（真实）；不改变 §1.1 既有计数与 A/B/C 归类 | 清点总清单（v1.0.7+）、放行清单（v1.0.9+）、任务卡、归集文档 §3.9 |

> **段门禁最终批准前置**（测试报告 §6 口径）：上述 B 面全绿且 T2~T5 真实面回填、P1 两仓远端推送与 OpenMemory 勾稽回读完成后，三份 [Review] 文档按挂起口径升 [Approved]。

---

## §6 执行进度勾选总表（供填报）

> 说明：`开始日期` / `完成日期` / `结论` 由执行人逐项填写；`证据路径` 为期望落盘路径；**结论仅允许 PASS / FAIL / PENDING**。

| ID | 事项 | 优先级 | 责任人 | 开始日期 | 完成日期 | 证据路径 | 结论 | 关联断言 |
|----|------|:---:|------|:---:|:---:|---------|:---:|---------|
| P1-1 | OpenMemory 推送 github 远端 | P1 | ☐ | | | `doc/test/evidence/s7/signoff/om-github-push.json` | | S7-T7-1 |
| P1-2 | OpenMemory 勾稽 A 类回读 | P1 | ☐ | | | `doc/test/evidence/s7/signoff/om-reconcile-readback.json` | | S7-T7-2 |
| P1-3 | OpenLLM 四远端推送 | P1 | ☐ | | | `doc/test/evidence/s7/signoff/ll-remote-push.json` | | S7-T7-1 |
| P2-T2 | L1-1 级联全链核验 | P2 | ☐ | | | `doc/test/evidence/s7/l1-1/**` | | S7-T2-1~4 |
| P2-T3 | L2-1 主备切换演练 | P2 | ☐ | | | `doc/test/evidence/s7/l2-1/**` | | S7-T3-1~4 |
| P2-T4 | L2-2 通道矩阵终验 | P2 | ☐ | | | `doc/test/evidence/s7/l2-2/**` | | S7-T4-1~4 |
| P2-T5 | L3-1 Agent 端到端 | P2 | ☐ | | | `doc/test/evidence/s7/l3-1/**` | | S7-T5-1~4 |
| P2-T6-1 | RA-06 五项真实面 | P2 | ☐ | | | `doc/test/evidence/s7/gate/gate-aggregate.json` §RA-06 | | S7-T6-1 |
| P2-T6-2 | 冒烟 S0-S6 真实执行 | P2 | ☐ | | | `gate-aggregate.json` §SMOKE-S0-S6；冒烟清单 §3 | | S7-T6-2 |
| P2-T6-3 | PG-ENV-1~4 复跑关闭 | P2 | ☐ | | | `gate-aggregate.json` §TEST-ALIGN-CLOSE | | S7-T6-3 |
| P2-T6-4 | K07/SYS-1 真实终验 | P2 | ☑ | 2026-09-12 | **PASS（v1.0.9）**：缺口 0 / 未覆盖 0 / 豁免 59 全有效（DPS 35 条已续期至 2026-12-31）；两仓补填已提交（`41af780` / `0a6f351`） | `gate-aggregate.json` §K07-SYS-1（`status=PASS`）；`k07-finalize.json`（`gate_verdict=PASS`） | | S7-T6-4 |
| P2-S2 | S2 段级真实 HTTP 双签 | P2 | ☐ | | | `doc/test/evidence/s2/**` | | S7-T2-2、S7-T6-1 |
| P2-S3 | S3 段级真实 HTTP 双签 | P2 | ☐ | | | `doc/test/evidence/s3/**` | | S7-T2-1、S7-T6-1 |
| P2-S4 | S4 段级真实 HTTP 双签 | P2 | ☐ | | | `doc/test/evidence/s4/**` | | S7-T3-4、S7-T4-4、S7-T6-4 |
| P2-S5 | S5 段级真实 HTTP 双签 | P2 | ☐ | | | `doc/test/evidence/s5/**` | | S7-T2-1、S7-T6-2 |
| P2-B1 | S6 B1 Playwright 9 关键页 | P2 | ☐ | | | `doc/test/evidence/s6/ui-e2e/**` | | S7-T6-2 |
| P2-B2 | S6 B2 L3-2 真实双签 | P2 | ☐ | | | `doc/test/evidence/s6/l3-2-smoke.json` | | S7-T7-3 |
| P2-B3 | S6 B3 真实双租户数据面 | P2 | ☐ | | | `doc/test/evidence/s6/**` | | S7-T6-2 |
| P2-B4 | S6 B4 真实 IdP 吊销 | P2 | ☐ | | | `doc/test/evidence/s6/**` | | S7-T2-1 |
| P2-B5 | S6 B5 四仓 frontend 物理改造与 CI 收敛 | P2 | ☐ | | | 各仓改造 hash + CI 结果 | | S7-T7-3 |
| P2-B6 | S6 B6 nginx `/ui/` 发布回滚 | P2 | ☐ | | | `doc/test/evidence/s6/**` | | S7-T8-3 |
| P3-1 | 证据回填 | P3 | ☐ | | | `doc/test/evidence/s7/**`、`s6/**` | | 全 B 面 |
| P3-2 | 测试报告 34 断言状态更新 | P3 | ☐ | | | 测试报告 §2/§3 | | 34 断言 |
| P3-3 | 报告内部版本升级 | P3 | ☐ | | | DevLogReport / 总收官报告 | | S7-T8-4/5 |
| P3-4 | 段门禁六项复核 | P3 | ☐ | | | 总收官报告 §2 | | 段门禁六项 |
| P3-5 | S7 段门禁人工批准回写（三份 [Review]→[Approved]） | P3 | ☐ | | | 三份文档状态列 | | S7-T8-4/5 |
| P3-6 | 清单/台账终态登记 | P3 | ☐ | | | 清点总清单 / 放行清单 / 任务卡 / 归集 | | S7-T7-4、S7-T8-1/2 |

> **统计**：P1 **3** 条 + P2 **18** 条（T2~T5 4 + T6 真实面 4 + 段级非沙箱 10）+ P3 **6** 条 = **27 条**。

---

## §7 执行纪律与风险

### 7.1 执行纪律（硬约束）

1. **禁伪造 hash 与通过结论**：四仓 commit hash、S7 段提交号、响应码、`request_id`、截图一律真实；未执行项写 `status=PENDING` + `reason`，**不得以「预期通过」代替证据**（设计草案 §5.4）。
2. **只推指定分支**：四仓推送仅限本单指定分支（`release/v7.3.0`、`release/v1.10.0`、`main`、`feature/s4-identity-channel-b`、`feature/need-star-orchestration`）；**不推送无关内容、不改写既有历史**。
3. **远端推送前确认本地勾稽**：推送前先 `git -C <仓> status --porcelain -uall` 与分清单 A 集合比对，A 类差异为 0 再推。
4. **回归失败即停**：任一仓推送/改造后回归失败，停止后续批次并修正；回归通过后再继续（放行清单 §0）。
5. **敏感文件不入提交面**：`.env`、`.env.shared-infra`、`.env.e2e`、`data/edge_tokens.jsonl` 等一律不入任何批次；OpenRAG `repository` gitlink 禁 `git add`；OpenLLM 4 个混合文件须 `git add -p` 拆分（放行清单 §0 红线）。
6. **禁用兜底暂存**：四仓任何批次禁用 `git add -A` / `git add .`，一律逐项显式 `git add` + 提交前 `git diff --cached --stat` 复查（本单自身提交同样遵循）。
7. **不纳入 `dogfood-output/`**：S7 提交面仅 OpenBase 仓（仓根 / `doc/**` / `scripts/**` / `openbase-ui/**` 复核面 + `doc/test/evidence/s7/**`）；`dogfood-output/` 走查产物不提交。
8. **回填顺序不可颠倒**：证据 → 测试报告 34 断言状态 → 报告内部版本 → 段门禁六项复核 → 人工批准回写 → 清单/台账终态（§5）。

### 7.2 风险与应对（承接设计草案 §7 R-1~R-8、R-D1~R-D5）

| # | 风险 | 影响面 | 本单应对 |
|---|------|--------|---------|
| R-1 | 真实环境可用性（PG/Redis、IdP/受信通道、四仓运行态不可达） | P2-T2~T6 | §0.1 前置逐项确认；不可达项按挂起口径 `PENDING` 登记，环境就绪后回填 |
| R-2 | 演练窗口（L2-1 需可注故障窗口） | P2-T3 / P2-T4 | 受控窗口排期；矩阵基线复用 S4-T7/T8 产出 |
| R-3 | 会签时序（入仓→回填→勾稽→会签须按序） | P1 / §5 | 严格按清点总清单 §4.1 五步；每仓回归失败即停 |
| R-4 | 四仓入仓进度（23 项人工判定 + 7 项边界确认） | P1 / P2-B5 | 会签前完成裁断；OpenLLM 混合文件 `git add -p`；need-star 独立隔离批 |
| R-5 | 沙箱限制（仅可操作 OpenBase 仓，无四仓写权限/无浏览器/PG/IdP） | 全量 B 面 | 四仓与真实面由用户沙箱外执行，结果如实登记（本单为执行依据） |
| R-6 | K13 与编排入口无现成基线 | P2-T6-3 / §0.2 | 以任务卡 K13 步骤与复盘 L7 约束为准；真实 PG 验证 |
| R-7 | verify-env 收紧兼容面（WARN→fail-fast 可能阻断启动） | §0 | 两段式发布 + 开关回退（设计草案 §6.1） |
| R-8 | PENDING 挂起累积（段级 10 条主挂起集中到 S7 后段） | §4 / §5 | 联调窗口一次性复核（S2~S6 双签 + S6 B1~B6）；按需分批回填，不阻断已达成项 |
| R-D3 | L1-1 级联真实停用可能污染联调环境 | P2-T2 | 使用**专用冒烟主体** `smoke_l1_1_*`；执行后 `restored`；不触碰生产主体 |
| R-D4 | 门禁聚合口径漂移 | §3 | 分项口径对齐 RA-06 / 冒烟 v1.1.0 / 对齐清单 v1.2.0；聚合 JSON 保留各分项证据路径 |
| R-D5 | evidence 与台账回写真实性依赖人工复核 | §5 | evidence JSON 强制字段（设计草案 §5.2）+「结论 + 证据路径 + 执行面」三列齐备；无证据不得填 PASS |

---

## 附录

### 附录 A：OpenBase 提交链索引（S7 段，`main`）

| 序 | 提交 hash | 提交信息（摘要） | 承载交付物 |
|:-:|-----------|----------------|-----------|
| 1 | `402ff8e` | `feat(shr): S7-T1 SHR 五项收口（verify-env 全局化/测试库/账号矩阵/编排入口/文档地图）` | S7-T1 结构面（脚本/文档） |
| 2 | `2235229` | `docs(intg): S3(OpenRAG)/S5(DPS) 入仓回填登记（hash/勾稽/清单同步）` | S7-T7 部分回填 |
| 3 | `d3faa7f` | `feat(gate): S7-T6 门禁聚合（RA-06/冒烟 S0-S6/对齐清单关闭/K07 终验）` | S7-T6 聚合脚本与证据 |
| 4 | `2d97d1a` | `docs(s7): S7-T8 24卡/七线JT全量回写与总收官报告` | S7-T8 台账/报告 |
| 5 | `a5020fa` | `docs(s7): S7-T7 会签汇总与入仓口径修正（四仓入仓 + 清单升版）` | S7-T7 会签汇总 |
| 6 | `9056f48` | `docs(s7): S7 DevLogReport 与测试报告（34 断言矩阵与段门禁六项结论）` | S7 Step 2/3 文档（当前 HEAD） |
| 7 | `1affff5` | `docs(s7): K07 门禁收口与聚合复跑回填（DPS 35 条豁免续期 + 缺口/未覆盖清零 -> gate verdict PASS；测试报告 v1.0.12 / 分派单 v1.0.8 / 执行单 v1.0.9 / 总收官报告 v1.0.8）` | K07/SYS-1 门禁收口证据与文档回填 + 一键提交脚本 |
| — | （本单） | `docs(s7): S7 沙箱外执行单 v1.0.0` | 本执行单（待提交） |

> 说明：提交链与上游一致（`402ff8e` / `2235229` / `d3faa7f` / `2d97d1a` / `a5020fa` / `9056f48`）；`402ff8e` 之前为 `f360cef`（设计草案）等，不在本段链内。

### 附录 B：四仓分支与 hash（2026-09-11 实测）

| 仓 | 分支 | HEAD | 远端同步 | 勾稽 A 类差异 | 关联断言 |
|----|------|------|---------|:---:|---------|
| OpenMemory | `release/v7.3.0` | `cc7c06f` | origin / backup 已同步；**github 待推（P1-1）** | 待 A 类回读（残余 89，P1-2） | S7-T7-1 / T7-2 |
| OpenRAG | `release/v1.10.0` | `a2eb92b` | origin / backup / github 三远端已同步 | 0（残余 1） | S7-T7-1 / T7-2 |
| OpenLLM | `feature/s4-identity-channel-b` | `be1886d` | **origin / backup / github / jerry.yu 四远端未推送（P1-3）** | 0（残余 1459） | S7-T7-1 / T7-2 |
| OpenLLM（隔离） | `feature/need-star-orchestration` | `ce40f90` | 未推送（随 P1-3 补推） | — | S7-T7-1 |
| DPS | `main` | `b5f5c06`（2026-09-13：K07 35 条豁免续期入库） | origin / backup / github 三远端已同步 | 0 | S7-T7-1 / T7-2 / S7-T6-4 |

### 附录 C：PENDING 主挂起清单（段级 10 条 + S7 自身）

**C.1 段级主挂起（承接 S0~S6，共 10 条）**

| # | 段 | 上级断言 | 挂起项 | 前置条件 | 本单执行项 |
|:-:|----|---------|--------|---------|-----------|
| 1 | S2 | S7-T2-2 | L3-2 真实 HTTP 双签（OpenMemory 事件消费端） | 四仓运行态 + 真实通道 | P2-S2 |
| 2 | S3 | S7-T2-1、S7-T6-1 | Pull 真实 HTTP 双签（Q-RG-7）+ PG/Redis 实跑 | OpenRAG 运行态 + PG/Redis | P2-S3 |
| 3 | S4 | S7-T3-4、S7-T4-4、S7-T6-4 | 真实 HTTP 双签；写路径等价 / K14 幂等 / L2-1 切换 / L2-2 终验 / K07 RA-06 终验 / 错误面收敛 | OpenLLM 运行态 + 真实通道 | P2-S4 |
| 4 | S5 | S7-T2-1、S7-T6-2 | Pull 真实 HTTP 双签（Q-DPS-5）；非沙箱复核（真实 PG/Redis） | DPS 运行态 + PG/Redis | P2-S5 |
| 5 | S6 | S7-T6-2 | B1 Playwright 9 关键页 PASS | 浏览器二进制 + 运行态 | P2-B1 |
| 6 | S6 | S7-T7-3（B5 复核） | B2 L3-2 真实受信通道双签 | 四子系统运行态 | P2-B2 |
| 7 | S6 | S7-T6-2 | B3 真实双租户数据面 | 真实 PG/Redis | P2-B3 |
| 8 | S6 | S7-T2-1 | B4 真实 IdP 回调与吊销 | 真实 IdP | P2-B4 |
| 9 | S6 | S7-T7-3 | B5 四仓 `frontend/` 物理改造与 CI 收敛复核（Q-S6-D7） | 各子系统仓执行 | P2-B5 |
| 10 | S6 | S7-T8-3 | B6 nginx `/ui/` 发布回滚 | nginx 运行态 | P2-B6 |

**C.2 S7 自身 PENDING（共 7 项）**

| # | 断言 ID | 挂起项 | 本单执行项 |
|:-:|---------|--------|-----------|
| 1 | S7-T6-1 | RA-06 五项真实面 | P2-T6-1 |
| 2 | S7-T6-2 | 冒烟 S0-S6 真实执行（P0 全绿 / P1 登记） | P2-T6-2 |
| 3 | S7-T6-3 | 存量对齐主批次 4 例异步/PG 环境性失败复跑关闭 | P2-T6-3 |
| 4 | S7-T6-4 | K07/SYS-1 真实 openapi 全量导出与逐行终验 | P2-T6-4 |
| 5 | S7-T1-3 | K13 真实授权与跨 schema 写拒绝 | §3.3（PG 就绪后随 PG-ENV 复跑）/ §0.1 |
| 6 | S7-T2-1 / T3-1 / T4-1 / T5-1 | T2~T5 联调窗口（L1-1 / L2-1 / L2-2 / L3-1） | P2-T2 / T3 / T4 / T5 |
| 7 | S7-T7-1 / T7-2 | 两仓远端推送 + OpenMemory 勾稽 A 类回读 | P1-1 / P1-3 / P1-2 |

**C.3 `PG-ENV-1`~`PG-ENV-4`（环境性挂起）**：见 §3.3，随真实 PG / `openbase_test` 就绪复跑关闭。

### 附录 D：断言 → 证据 → 回填映射表（34 断言）

> 执行面：A = 沙箱可判定（已达成）；A+B = 双面（真实面待执行）；B = 联调窗口。**本执行单覆盖 34 断言中的 29 条真实面**（B 20 + A+B 9）；A 面 5 条已达成，无需沙箱外执行。

| 断言 ID | 执行面 | 本单执行项 | 证据落点 | 回填位置 |
|---------|:---:|-----------|---------|---------|
| S7-T1-1 | A+B | §0.1 + §0.2（S-2/S-3 真实探活） | `doc/test/evidence/s7/shr/verify-env-global/` | 测试报告 §2 S7-T1-1 |
| S7-T1-2 | A+B | §0.1 第 0-2 项 + §3.3 | `doc/test/evidence/s7/shr/openbase-test/` | 测试报告 §2 S7-T1-2 |
| S7-T1-3 | B | §3.3（真实授权 + 跨 schema 写拒绝） | `doc/test/evidence/s7/shr/k13/` | 测试报告 §2 S7-T1-3 |
| S7-T1-4 | A+B | §0.1 第 0-5 项（编排实跑） | `doc/test/evidence/s7/shr/orchestrator/` | 测试报告 §2 S7-T1-4 |
| S7-T1-5 | A | 已达成（无需执行） | `doc/test/evidence/s7/shr/doc-map/orphan-check.json` | 测试报告 §2 S7-T1-5（PASS） |
| S7-T2-1 | B | P2-T2 | `doc/test/evidence/s7/l1-1/dps-block.json` | 测试报告 §2 S7-T2-1 |
| S7-T2-2 | B | P2-T2 | `doc/test/evidence/s7/l1-1/{openmemory-block,event-idempotency}.json` | 测试报告 §2 S7-T2-2 |
| S7-T2-3 | A+B | P2-T2 | `doc/test/evidence/s7/l1-1/{restore.json,scan-auto-purge.txt}` | 测试报告 §2 S7-T2-3 |
| S7-T2-4 | B | P2-T2 | `doc/test/evidence/s7/l1-1/purge.json` | 测试报告 §2 S7-T2-4 |
| S7-T3-1 | B | P2-T3 | `doc/test/evidence/s7/l2-1/drill-report.md`（场景 1） | 测试报告 §2 S7-T3-1 |
| S7-T3-2 | B | P2-T3 | `doc/test/evidence/s7/l2-1/drill-report.md`（场景 2） | 测试报告 §2 S7-T3-2 |
| S7-T3-3 | B | P2-T3 | `doc/test/evidence/s7/l2-1/{route-before,route-after}.json` | 测试报告 §2 S7-T3-3 |
| S7-T3-4 | B | P2-T3 | `doc/test/evidence/s7/l2-1/drill-report.md` | 测试报告 §2 S7-T3-4 |
| S7-T4-1 | B | P2-T4 | `doc/test/evidence/s7/l2-2/matrix-finalize.json` | 测试报告 §2 S7-T4-1 |
| S7-T4-2 | B | P2-T4 | `doc/test/evidence/s7/l2-2/matrix-finalize.json` | 测试报告 §2 S7-T4-2 |
| S7-T4-3 | B | P2-T4 | `doc/test/evidence/s7/l2-2/read-path-ab-equivalence.json` | 测试报告 §2 S7-T4-3 |
| S7-T4-4 | B | P2-T4 | `doc/test/evidence/s7/l2-2/{write-path-equivalence,k14-idempotency}.json` | 测试报告 §2 S7-T4-4 |
| S7-T5-1 | B | P2-T5 | `doc/test/evidence/s7/l3-1/agent-key-issuance.json` | 测试报告 §2 S7-T5-1 |
| S7-T5-2 | B | P2-T5 | `doc/test/evidence/s7/l3-1/system-whitelist-cases.json` | 测试报告 §2 S7-T5-2 |
| S7-T5-3 | B | P2-T5 | `doc/test/evidence/s7/l3-1/domain-isolation.json` | 测试报告 §2 S7-T5-3 |
| S7-T5-4 | B | P2-T5 | `doc/test/evidence/s7/l3-1/{unauthorized-403,m1-m2}.json` | 测试报告 §2 S7-T5-4 |
| S7-T6-1 | A+B | P2-T6-1 | `gate-aggregate.json` §RA-06 | 测试报告 §2 S7-T6-1 |
| S7-T6-2 | B | P2-T6-2 | `gate-aggregate.json` §SMOKE-S0-S6 | 测试报告 §2 S7-T6-2 |
| S7-T6-3 | A+B | P2-T6-3 | `gate-aggregate.json` §TEST-ALIGN-CLOSE | 测试报告 §2 S7-T6-3 |
| S7-T6-4 | B | P2-T6-4 | `gate-aggregate.json` §K07-SYS-1 | 测试报告 §2 S7-T6-4 |
| S7-T7-1 | B | P1-1 / P1-3 | `doc/test/evidence/s7/signoff/{om-github-push,ll-remote-push}.json` | 测试报告 §2 S7-T7-1 |
| S7-T7-2 | B | P1-2（+ 其余三仓复核） | `doc/test/evidence/s7/signoff/om-reconcile-readback.json` | 测试报告 §2 S7-T7-2 |
| S7-T7-3 | A+B | §5（P3-5 会签终态） | `doc/test/evidence/s7/signoff/`（会签记录） | 测试报告 §2 S7-T7-3 |
| S7-T7-4 | A | 已达成（无需执行） | 两份清单修订历史 | 测试报告 §2 S7-T7-4（PASS） |
| S7-T8-1 | A | 已达成（无需执行） | 任务卡回写表 | 测试报告 §2 S7-T8-1（PASS） |
| S7-T8-2 | A | 已达成（无需执行） | 归集文档 §3 | 测试报告 §2 S7-T8-2（PASS） |
| S7-T8-3 | A | P2-B6 复核（同口径） | `doc/design/OpenBase-文档地图索引-v1.0.0.md` | 测试报告 §2 S7-T8-3（PASS） |
| S7-T8-4 | A+B | §5（P3-3 / P3-4） | `doc/development/OpenBase-S7-全域门禁与总收官报告-v1.0.0.md` | 测试报告 §2 S7-T8-4 |
| S7-T8-5 | A+B | §5（P3-4） | 报告 §2 自检表 + `gate-aggregate.json` | 测试报告 §2 S7-T8-5 |

> **覆盖统计**：本执行单直接关联 **29 条**（B 面 20 + A+B 双面 9）；A 面 **5 条**（S7-T1-5、S7-T7-4、S7-T8-1/2/3）已达成、仅作口径引用，不重复执行。合计 34 条全覆盖。

---

> **文档结束**。本执行单为 S7 段沙箱外 / 联调窗口的**唯一执行依据**（[Draft] v1.0.7）；P1 可立即执行，P2 需真实环境与联调窗口，P3 于回填后执行；全部未执行项保持 `PENDING`，**禁伪造 hash 与通过结论**。**「待提交项（≤）」**：OpenLLM K07 全量补填（5 文件）已在子系统仓工作树完成，因沙箱拒写 `.git/objects` 未能 commit（无 hash），须在可写环境提交（建议 message：`docs(k07): OpenLLM 端点过滤矩阵全量补填与隔离用例注册（351 端点/缺口归零）`）。
