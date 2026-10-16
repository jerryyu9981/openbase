# OpenBase-S7-冒烟缺陷分派待办单-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-FAULT-DISPATCH-v1.0.0 |
| 版本 | v1.0.28 |
| 状态 | [Draft] |
| 日期 | 2026-09-12 |
| 作者 | AI（S7 批次 9 冒烟缺陷分派会话；证据与各仓配置只读核对 2026-09-11；S7 批次 10 OpenLLM K07 补填回填会话修订 v1.0.1；S7 批次 11 OpenMemory K07 缺口补填回填会话修订 v1.0.2；S7 批次 12 F-2/F-3 修复与冒烟重跑会话修订 v1.0.3；S7 批次 13 F-1 环境配置与主链路修复会话修订 v1.0.4；S7 批次 14 DPS 探活口径修复会话修订 v1.0.5；S7 批次 15 冒烟 v4 重跑与回填会话修订 v1.0.6；S7 批次 16 跨仓提交状态同步回填会话修订 v1.0.7；S7 批次 17 K07 门禁收口与聚合复跑会话修订 v1.0.8；S7 批次 18 K07 收口提交与脚本路径回填会话修订 v1.0.9；S7 批次 19 DPS 豁免续期入库回填会话修订 v1.0.10；S7 批次 20 OpenLLM 快照落仓脚本登记会话修订 v1.0.11） |
| 用途 | **冒烟缺陷分派与闭环回填**：将 S7-T6-2 全量冒烟 S0~S6 实测暴露的三项功能缺陷（F-1/F-2/F-3），逐条落笔为「现象与证据 → 根因判定 → 修复动作 → 验证方式 → 回填位置 → 风险与边界」，供责任方按单修复、重跑指定用例、回填台账，并由 OpenBase 侧复核收口 |
| 上游依据 | ①`doc/test/evidence/s7/smoke/smoke-summary.json`、`doc/test/evidence/s7/smoke/s0-s6-cases.json`（P0 30 例：PASS 14 / FAIL 9 / BLOCKED 7；P1 2 例 BLOCKED）；②`doc/test/evidence/s7/env/env-check.json`（READY 14 / UNREACHABLE 2 / BLOCKED 1）；③《OpenBase-S7-联调窗口环境检查报告-v1.0.0.md》（`doc/planning/`，内部 **v1.0.2**，§2.6 四项功能缺陷）；④《OpenBase-真实联调冒烟清单-v1.0.0.md》（仓根，内部 **v1.1.0**，§3 用例定义）；⑤各仓实际配置文件（只读定位）；⑥《OpenBase-S7-沙箱外执行单-v1.0.0.md》（`doc/planning/`，内部 **v1.0.5**，§2/§3 结构与回填位）；⑦《OpenBase-数据隔离实现任务卡-v1.0.0.md》（K02/K07/K09/K10/K15，七线 JT 口径回填位） |
| 关联证据 | `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}`；`doc/test/evidence/s7/env/env-check.json`；`doc/test/evidence/s7/gate/gate-aggregate.json`；**（v1.0.13）** `doc/test/evidence/manual/{mtauth-realface-20261015.json,mtauth-delegation-l31-20261016.json}`；`doc/test/evidence/s7/smoke/smoke-summary-20261016005540.json`；**（v1.0.14）** `doc/test/evidence/manual/mtauth-delegation-l31-20261016-defect.json`（F-8/F-9 修复前 RED 证据）；**（v1.0.15）** `doc/test/evidence/s7/shr/orchestrator/bypass-scan.json`（F-10 修复后重跑：`scanned=46 / allowed=1 / disallowed=0`）、`doc/test/evidence/s7/smoke/smoke-summary-20261016120118.json`（受管编排复跑冒烟）；**（v1.0.17）** `doc/test/evidence/manual/{ra06-failclosed-20261016.json,b1-compat-retire-openllm-20261016.json}`（RA-06 fail-closed 受控窗口注入；L3/B1 兼容层退役跨仓复核）；**（v1.0.19）** `doc/test/evidence/manual/b1-phase5-retire-openllm-20261016.json`（B1 D4 phase 5 退役面全量清零交付复核，`overall_pass=true`） |
| 使用说明（闭环四步） | **① 责任方按单修复**（§2~§4「修复动作」）→ **② 重跑指定用例**（各缺陷「验证方式」用例 ID 清单 + 命令模板）→ **③ 回填三处**（执行单 §2/§3、测试报告 §2.2、`smoke-summary.json`）→ **④ 通知 OpenBase 侧复核**（§7 复核动作） |
| 脱敏口径 | 本单**不输出任何明文密钥 / 口令**；数据库 / Redis 连接串仅记 host 与库名，键值以「已配置 / 脱敏」表述；`.env` 只引用键名，值以「当前值 / 目标值」呈现（密钥类不落值） |
| 适用范围 | S7 段冒烟 S0~S6 暴露的 **F-1 / F-2 / F-3**；**不含** F-4（统一前端路由告警，v1.0.2 已修复，E2E 9/9 PASS）与 S5-6（禁停服务降级，归受控窗口 / T3 纪律）；**v1.0.1 新增 F-5**（OpenLLM K07 端点过滤矩阵全量补填：工作树完成/待提交，非冒烟阻塞项）；**v1.0.2 新增 F-6**（OpenMemory K07 端点过滤矩阵 8 条缺口已补填：工作树完成/待提交，非冒烟阻塞项）；**v1.0.13 新增 F-8 / F-9**（L2 真实面探针 `doc/test/evidence/manual/mtauth-delegation-l31-20261016.json` 暴露的 OpenBase 侧两项缺陷：`/auth/me` 500、`users` 路径未派生 `tenant_code`；均 P1、阻塞用例数 0，见 §8）；**v1.0.14：F-8 / F-9 已按 TDD 修复并验证通过**（提交 `6bf7832`；探针复跑 `overall_pass=true`），并**新增 F-10 / F-11 预存门禁失败登记**（全量回归暴露、经 `e2c4f25` 基线证明非本轮引入，见 §9）；**v1.0.15：F-10 已按方案 A 修复并验证通过**（两个脚本的服务生命周期改经受管编排 `service-orchestrator.ps1`，自身不再直接终止进程；扫描器 `disallowed=0`、`test_s7_t1_shr.py` 15 passed、冒烟经受管编排复跑 `PASS 25 / FAIL 0 / PENDING 7`）；**v1.0.16：F-11 干跑核对完成并修复**（根因＝**测试夹具非自洽**：三件 PS 工具以裸 `python` 为默认解释器，受限环境 PATH 无解释器 → `CommandNotFoundException` 退出 1 且不落证据，掩盖干跑契约判定；**工具契约本身已满足**——显式传 `-PythonExe` 时三件均 `exit=2 / status=PENDING / exit_code=2 / checks=4` 且证据落 `-EvidenceDir`）→ 修夹具（显式传 `sys.executable`），`tests/test_s7_tools_skeleton.py` **26 passed**）；**v1.0.17：新增 F-12（OpenLLM 仓）**——**L3 / B1 D4 phase 4「兼容层退役」跨仓复核**发现：退役本体已落地（`users.py` 旧硬门已移除、43 例护栏/接口用例通过），但其**生产安全耦合（生产拒绝启动）实测未生效**（`get_settings()` 生产门禁被 `main.py` 启动自检的 fail-open 兜底吞掉 → 生产带 `RBAC_PERMISSION_ENFORCE=false` 仍能启动）；详见 §10；**v1.0.18：F-12 已按方案 A 修复并复验通过**（OpenLLM `ff506e9`/v2.17.2：新增 `assert_startup_gates()` + `main.py` lifespan 开头无包裹求值 + 6 例新用例；运行态探针 `overall_pass=true`，D1/D2 → **exit=3 拒绝启动**；相关回归 **58 passed**、ruff 全清）→ **L3 项闭环**；**v1.0.19：B1 D4 phase 5「其余 12 模块旧管理硬门退役」交付并复核通过**（OpenLLM `f7c7073`/v2.17.3：`app/api/` 40 处 / 12 文件旧门全量清零，新增 10 权限码，生产门禁判据扩展为退役面全集；护栏 **98 passed**、相关回归 **239 passed / 0 failed**、ruff 零新增）→ **§10.4 第 3 项关闭（退役面全量清零）**，详见 §10.5 |

### 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-11 | AI（S7 批次 9 冒烟缺陷分派会话） | 初始版本：基于 `smoke-summary.json` / `s0-s6-cases.json` / `env-check.json` 与各仓只读配置核对，形成 §1 分派总表、§2~§4 逐缺陷详单（现象与证据 / 根因判定 / 修复动作 / 验证方式 / 回填位置 / 风险与边界）、§5 闭环检查清单、§6 执行纪律、§7 OpenBase 侧复核动作、附录（用例→缺陷→责任方映射 + 冒烟快照）。**仅新建本单，未改动任何代码、未对四仓执行 git 写操作、未将 `dogfood-output/` 纳入提交面** |
| v1.0.1 | 2026-09-11 | AI（S7 批次 10 OpenLLM K07 补填回填会话） | **新增 F-5 条目（OpenLLM K07 全量补填：工作树完成/待提交）**：§1 分派总表增补 **F-5**（责任方 OpenLLM 仓；优先级 P0；阻塞用例数 **0**（非冒烟阻塞项，属 K07 矩阵治理）；关联断言 **S7-T6-4**；状态 **已修复待提交**）；新增 **§5.4 F-5 闭环检查清单**；§7 增补 F-5 OpenBase 侧复核动作。**要点**：OpenLLM 仓已在其工作树完成 K07 端点过滤矩阵全量补填（5 文件；矩阵 354 行 / 覆盖 349 / 豁免 5；**缺口 344→0**；隔离用例新增 759 条 → **767 passed**；门禁复跑 `total=351 covered=349 exempt=2 / gaps=0 uncovered=0 exemption_without_approval=0`，exit 0；ruff All checks passed），**因沙箱拒写 `.git/objects` 未能 commit（无 hash，禁伪造），工作树保留，待可写环境提交**（建议 message：`docs(k07): OpenLLM 端点过滤矩阵全量补填与隔离用例注册（351 端点/缺口归零）`）。回填位：`k07-finalize.json` `per_system[openllm]`（rows=354/covered=349/exempt=5/gap=0/status=FILLED(worktree,uncommitted)）+ `gate-aggregate.json` §K07-SYS-1（`status=PARTIAL`）。**保留 F-1~F-3 条目不变**；未改动任何子系统仓文件 |
| v1.0.2 | 2026-09-12 | AI（S7 批次 11 OpenMemory K07 缺口补填回填会话） | **新增 F-6 条目（OpenMemory K07 8 条缺口已补填：工作树完成/待提交）**：§1 分派总表增补 **F-6**（责任方 OpenMemory 仓；优先级 P0；阻塞用例数 **0**（非冒烟阻塞项，属 K07 矩阵治理）；关联断言 **S7-T6-4**；状态 **已修复待提交（工作树）**）；新增 **§5.5 F-6 闭环检查清单**；§7 增补 F-6 OpenBase 侧复核动作。**要点**：OpenMemory 仓已在其工作树完成 K07 端点过滤矩阵 8 条缺口补填（4 文件；矩阵 32→**40 行** / 覆盖 25→31 / 豁免 7→9；**缺口 8→0**；新增隔离用例 `IS-OM-R26~R31`，`pytest tests/unit/test_isolation_matrix_endpoints.py` → **81 passed**；门禁复跑 `missing_rows=0`，exit 0；K07/identity 组 **372 passed**；ruff 0 错误），**因沙箱拒写 `.git/objects` 未能 commit（无 hash，禁伪造），工作树保留，待可写环境提交**（建议 message：`docs(k07): OpenMemory 端点过滤矩阵 8 条缺口补填与隔离用例注册（缺口归零）`）。回填位：`k07-finalize.json` `per_system[openmemory]`（rows=40/covered=31/exempt=9/gap=0/status=FILLED(worktree,uncommitted)）+ `gate-aggregate.json` §K07-SYS-1。**保留 F-1~F-3/F-5 条目不变**；未改动任何子系统仓功能语义代码 |
| v1.0.3 | 2026-09-12 | AI（S7 批次 12 F-2/F-3 修复与冒烟重跑会话） | **F-2 / F-3 修复关闭 + 冒烟重跑（v3）回填**：① **F-2 已修复**——根因＝S3-T2 补列迁移**仅实现 SQLite 版**（PG 侧只有回滚/索引计划，无正向补列），OpenRAG 仓本批补齐 PG 幂等迁移实现（`src/openrag/storage/migrations.py` 新增 6 个 PG 函数；新增执行器 `scripts/migrate_tenant_columns_pg.py`（支持 `--dry-run`）；新增单测 `tests/unit/test_s3_t2_tenant_columns_pg.py` 7 条）并对共享库 `nuct` 执行：`collections/documents/chunks` 三表 `tenant_code`（`NOT NULL DEFAULT 'default'`）+ `idx_*_tenant` 3 索引 + `uq_collections_tenant_name` 复合唯一 + 迁移标记 `s3_tenant_columns` + 对账 **0 孤儿**；实测 `POST /api/v1/collections` **500→200**（创建/列表/文本入库/幂等/检索通过；无密钥 401）；ruff All checks passed、相关单测 **23 passed**；**沙箱拒写 `.git/objects` 未 commit（无 hash，禁伪造），工作树保留，已生成一键提交脚本**（`f2-commit-push.bat` / `scripts/f2_commit_push.ps1`，建议 message：`fix(f2): 补齐 PG 租户列幂等迁移（补列+回填+复合唯一）并对共享库执行`）；② **F-3 已修复**——`OpenLLM backend/.env` 由 `llm-proxy` 改为 `openbase-llm-proxy`，经 `service-orchestrator.ps1 -Action stop/start -Only openllm` 仅重启 OpenLLM（`/health` 200）；实测受信源 `openbase-llm-proxy` + 四头 → 审计 `external_user_id/external_org_id` 非空（采纳），非受信伪造仍不落库；③ **冒烟 S0~S6 重跑（v3）**：**P0 21 PASS / 2 FAIL / 7 BLOCKED、P1 2 BLOCKED**（v2→v3：**7 例 FAIL→PASS、零回归**——S0-4/S5-3 归 F-3，S1-1/S3-1/S3-2/S3-3/S6-1 归 F-2）；④ §1 分派总表 F-2/F-3 状态由「待修复」改为 **「已修复关闭（v1.0.3）」**；**F-1 仍登记**（环境侧：三真实开关未全开 + Ollama 上游不可达/选路模型未注册）；⑤ 证据：`doc/test/evidence/s7/smoke/smoke-summary-v3.json` + 五份 `smoke-<sys>.json`；测试报告同步升 **v1.0.7**。**未改动任何子系统仓功能语义代码以外的文件** |
| v1.0.4 | 2026-09-12 | AI（S7 批次 13 F-1 环境配置与主链路修复会话） | **F-1 修复关闭（环境配置 + 代码修复）**：① 环境侧——三上游地址对齐（OpenRAG→8010 / OpenMemory→8020 / DPS→8030）、补齐 REAL/ENABLED 开关、`DEFAULT_LLM_MODEL=qwen3:0.6b`、`ollama-lan` provider 指向本机、本机 Ollama 启动（v0.32.15，`qwen3:0.6b`/`llama3.2:1b`，CPU）、内部直连密钥经 `OpenBase/.env.shared-infra` 注入；② 代码侧（提交 **`f258022`**，7 文件 / +902 −18，三远端同步）——语义缓存新增 **Redis 后端（可配置切换，默认 sqlite 不变）** + writeback 队列**降级加固**（不缓存失败态、可重试）；③ 复验——openmemory/openrag 探活 **ok**、流式（直连/网关）**200**、非流式（直连）**200**（cache_hit）；④ §1 分派总表 F-1 状态由「待修复」改为 **「已修复（v1.0.4）」**；⑤ 遗留：DPS 探活 401（未带 org/tenant 头，待复核）、冒烟 v4 待重跑。**未改动任何子系统仓文件（OpenLLM 侧代码修复由本批会话实施并已提交）** |
| v1.0.5 | 2026-09-12 | AI（S7 批次 14 DPS 探活口径修复会话） | **新增 F-7（DPS 组件探活恒 401 → 已修复）**：根因＝real 模式探活打业务只读面 `/api/v2/portrait/list`（需组织/租户身份头），探活上下文无身份 → 恒 401，导致 `/openllm/v1/health` 的 dps 恒 unavailable；修复＝`dps_client.liveness()`（`GET /health/liveness`）+ 网关探活分支改调，新增单测 5 例（**5 passed**，ruff 通过）；实测 `/openllm/v1/health` **三上游全 ok**（openmemory/openrag/dps）。§1 分派总表新增 **F-7** 行（待提交，脚本就绪）；**F-1 行维持「已修复（v1.0.4）」**。未改动其它子系统仓文件 |
| v1.0.6 | 2026-09-12 | AI（S7 批次 15 冒烟 v4 重跑与回填会话） | **冒烟 v4 快照回填 + F-7 状态更新**：① 冒烟 v4（32 例：30 P0 + 2 P1）= **26 PASS / 0 FAIL / 6 BLOCKED**（v3 21/2/9；新增 5 PASS、FAIL 清零、零回归）；② **F-7 状态由「已修复待提交（脚本就绪）」更新为「已提交（`f1d187b`，三远端同步）」**（`fix(dps): 组件探活改走运维端点 /health/liveness`）；③ **新增环境受限登记（非缺陷，不作为分派缺陷）**：`writeback.db` SQLite WAL 写入在本执行环境被拒 → 回写队列不可用（S2-4 / S3-4 / S5-4 / S4-4 写侧沉淀受阻；主链路已由降级保护正常）；④ 新增特性缺口登记：routing 未输出 `need_profile/profile_source`、未接入 `evaluate_session` 钩子（need-star v0.6.0 分支特性）；⑤ S3-3 命中抖动登记重试策略（+3s）。冒烟快照基线由 v3 更新为 v4。未改动任何子系统仓文件 |
| v1.0.7 | 2026-09-12 | AI（S7 批次 16 跨仓提交状态同步回填会话） | **F-2 / F-5 / F-6 状态由「已修复待提交」同步为「已提交（三远端同步）」**：F-2 → OpenRAG `ada7a97`（`fix(f2): 补齐 PG 租户列幂等迁移（补列+回填+复合唯一）并对共享库执行`）；F-5 → OpenLLM `41af780`（`docs(k07): OpenLLM 端点过滤矩阵全量补填与隔离用例注册`）；F-6 → OpenMemory `0a6f351`（`docs(k07): OpenMemory 端点过滤矩阵 8 条缺口补填与隔离用例注册`）。三仓 `git status` 目标文件均无残留改动，`ls-remote` 三端与本地 HEAD 一致。**F-1（`f258022`）/ F-7（`f1d187b`）此前已登记为已提交**。**分派缺陷清单至此全部闭环（F-1~F-7：已提交/已修复；F-4 早前已修复）**。未改动任何子系统仓文件 |
| v1.0.8 | 2026-09-12 | AI（S7 批次 17 K07 门禁收口与聚合复跑会话） | **K07 挂起项全部闭环 + 门禁收口**：① **DPS 35 条豁免续期**——DPS 填报矩阵 35 条豁免行「到期/复核」由 2026-09-10 更新为 **续期至 2026-12-31（续期日 2026-09-12）**，复跑 DPS 门禁 `scripts/k07_endpoint_matrix.py --check` → `total=169 covered=134 exempt=35 / gaps=0 uncovered=0 exemption_without_approval=0`（exit 0）；② **F-5/F-6 提交状态确认**——OpenLLM `41af780`、OpenMemory `0a6f351` 均已入库且三远端同步（§5.4/§5.5 「待提交」行转 ☑）；③ **K07/SYS-1 门禁 verdict 由 PARTIAL 升 PASS**（缺口 0 / 未覆盖 0 / 豁免 59 全有效）；④ **门禁聚合复跑（本批实跑）**：`python scripts/gate_aggregate.py` → `overall=PASS exit=0 pass=20 fail=0 pending=2`；⑤ 新增 **§5.6 K07 端到端闭环检查清单**、§7 增补第 8 项 OpenBase 侧复核。**F-1~F-7 缺陷与 K07 挂起项至此全部闭环**；未改动任何子系统仓文件（DPS 侧改动保留工作树，提交脚本就绪） |
| v1.0.9 | 2026-09-12 | AI（S7 批次 18 K07 收口提交与脚本路径回填会话） | **收口提交入库 + 一键提交脚本路径登记**：① OpenBase 侧 K07 收口回填提交 **`1affff5`**（10 文件 = 证据 2 + 文档 4 + S7 断言测试 2 + 一键提交脚本 2），`origin` / `backup` 双远端 `ls-remote` 实测与本地 HEAD 一致；② **DPS 仓一键提交脚本就绪**——`DPS/dps-k07-commit-push.bat`（包装 `DPS/scripts/dps_k07_exempt_commit_push.ps1`，支持 `-DryRun`），`-DryRun` 通过（续期自检：旧复核日残留 0 / `续期至 2026-12-31` 出现 35 次），实跑在本执行环境因 `.git/index.lock: Permission denied` 中止（环境写入受限，禁伪造）→ **待可写环境执行**；③ §5.6 与 §7 第 8 项同步登记脚本路径与实跑结论。**F-1~F-7 与全部 K07 挂起项闭环状态不变**；未改动任何子系统仓文件 |
| v1.0.10 | 2026-09-13 | AI（S7 批次 19 DPS 豁免续期入库回填会话） | **DPS 侧 K07 豁免续期入库（`b5f5c06`）+ 包装脚本修复**：① 一键提交包装 `dps-k07-commit-push.bat` 行尾由 LF 更正为 CRLF（cmd 对 LF-only 批处理逐行解析失败，实测误报 `"\cmd.exe"` / `->` / `doc` 等命令），并改用 `%SystemRoot%` 解析 powershell/chcp；② DPS 侧已于 2026-09-13 执行提交 **`b5f5c06`**（3 文件 = `doc/design/DPS-K07-端点过滤矩阵填报-v1.0.0.md` + `scripts/dps_k07_exempt_commit_push.ps1` + `dps-k07-commit-push.bat`），**origin/backup/github 三远端 `ls-remote` 与本地 HEAD 一致**；③ hash 已回填 §1/§5.6/§7 与 `k07-finalize.json`（新增 `dps_exemption_commit`）及 `gate-aggregate.json` `k07_backfill.dps` → **本单待提交项清零（F-1~F-7 + 全部 K07 挂起项闭环）**。未改动任何子系统仓文件 |
| v1.0.11 | 2026-09-13 | AI（S7 批次 20 OpenLLM 快照落仓脚本登记会话） | **F-5 遗留项（OpenLLM `backend\data\openapi-llm-snapshot.json` 落仓）收口为可执行形态**：生成一键脚本 `openllm-k07-snapshot-commit-push.bat` + `scripts/openllm_k07_snapshot_commit_push.ps1`（宿主仓库＝OpenBase），源快照取 K07 证据导出 `k07-openapi/openllm.openapi.json`（278 路径 / **351 操作**，与终验台账一致）；脚本含 351 操作校验 + 提交面守卫（仅 1 文件）+ 三远端 `ls-remote` 校验，`-DryRun` 通过；提交分支与 **OpenLLM `backend/data/**` 与 `.git` 在本沙箱被拦截（全仓只读，实测无残留）** → 待沙箱外执行并回填 hash。**F-1~F-7 全部闭环状态不变；本项仅影响 K07 无参 CI 离线校验能力，非冒烟阻塞项（阻塞用例数 0）。** |
| v1.0.13 | 2026-10-16 | AA/PM-OpenBase-Dev | **新增 F-8 / F-9（L2 真实面探针暴露的 OpenBase 侧缺陷，P1，阻塞用例数 0）**：按「更宽口径遗留问题」推进 L2（RA-06 余项真实面），以原子窗口探针（`doc/tmp/run_l2_probe.ps1` + `doc/tmp/l2_delegation_probe.py`）在运行态验证「委托跨界 403 + agent key 面」，取得 **反例自证配对**：B 跨域委托 **403 `PERM_DELEGATION_CROSS_TENANT`** / C 同域委托 **200**（放行）→ 委托跨界不变式**真实面达成**；A（user 挂委托 → 403 `PERM_FORBIDDEN`）、D（agent 发放 200）、F（agent key 越权 403）、G1/G2（吊销即时 200→401）全部 PASS。**同窗口暴露两项缺陷**：① **F-8** `GET /api/v1/auth/me` 在主体 `tenant_id` 为整数（agent 绑定租户）时 **500**——`MeResponse.tenant_id: str \| None` 与 `resolve_agent_principal` 返回的 int 冲突（pydantic `string_type` 校验失败）；② **F-9** `POST /api/v1/users` **不派生 `tenant_code`**（agent 路径经 `_resolve_tenant_code` 派生），致该路径建的同域账号作委托目标时「目标行域为空 → 同域被误判 `PERM_DELEGATION_CROSS_TENANT`」（探针观测项 O 自证：期望同域放行 200，实测 403）。证据 `doc/test/evidence/manual/mtauth-delegation-l31-20261016.json`（`overall_pass=false`，仅 F-8 对应项 E 不通过；`O` 为如实观测项不入门禁）。新增 §8 详单与 §5.7/§5.8 闭环清单、§7 第 9 项复核动作。**未改动任何功能语义代码**（缺陷按单登记，待裁定修复窗口） |
| v1.0.14 | 2026-10-16 | AA/PM-OpenBase-Dev | **F-8 / F-9 修复闭环（TDD）+ F-10 / F-11 预存失败登记**：① 依人工指令「按 TDD 修复 F-8 和 F-9」实施——先写 3 条 RED 用例（`tests/test_identity_t1.py::test_t1_3b_agent_bound_to_tenant_me_returns_200`、`tests/test_users_admin.py::test_create_user_derives_tenant_code`、`tests/test_oidc_binding.py::test_jit_create_derives_tenant_code`，均先失败）→ 再修复：**F-8** `me()` 出参口径统一为 `str`；**F-9** `create_user` 与 OIDC JIT `_bind_or_create_user` 补齐 `tenant_code` 派生（复用 `auth.resolve_tenant_code`）。**提交 `6bf7832`**（8 文件 / +178 −6）。② **验证**：`ruff` 全清；三新用例 + 相关模块隔离全绿（t1 9 / users 7 / oidc 6 / tenant_admin 5 / s7_t7 20 / s7_t8 19 / s7_docs 6 / s7_t6_gate 16）；**仓内分组全量回归 `passed=1118 / failed=0 / skipped=4`**；**L2 探针复跑 `overall_pass=true`**（E 由 500→**200**、观测项 O 由 403→**200**，修复前原始证据留档 `mtauth-delegation-l31-20261016-defect.json`）。③ §1 F-8/F-9 状态转「已修复（`6bf7832`）」、§5.7/§5.8 逐项勾选、§7 第 9 项复核落笔、§8 追加修复与验证记录。④ **新增 F-10 / F-11 预存门禁失败登记**（全量回归暴露；已用 `e2c4f25` 基线 worktree 证明非本轮引入，见 §9）。**仅改动 OpenBase 仓源码/测试/文档** |
| v1.0.15 | 2026-10-16 | AA/PM-OpenBase-Dev | **F-10 按方案 A 修复闭环（受管编排唯一入口）+ 冒烟受管复跑验证**：依人工指令「按方案 A 修复 F-10 并重新跑冒烟验证」实施——① **`scripts/run_smoke_s0_s6.ps1`**：删除本地 `Start-Svc`/`Clear-Listener`/收尾 `Stop-Process`，服务生命周期改由 `& scripts/service-orchestrator.ps1 -Action stop|start|stop -Only openbase,openllm -HealthTimeout 240` 驱动（含 `.env.shared-infra` 环境等价、就绪门保留）；② **`scripts/verify_mtauth_realface.ps1`**：`-StartServices` 分支删除本地进程表与 `Start-Process`/收尾 `Stop-Process`，改经同一编排入口对六服务 `stop`→`start`→（末尾）`stop`；③ 两脚本均补 **PATH 引导**（编排器以裸命令 `python` 启动服务，沙箱 PATH 无解释器 → 前置解释器目录）并转 **UTF-8 with BOM**（解析 0 错误）。**验证**：`python scripts/scan_orchestrator_bypass.py` → `disallowed=0 / allowed=1 / exit 0`（证据 `bypass-scan.json` 重跑 `scanned=46`）；`pytest tests/test_s7_t1_shr.py tests/test_s7_t6_gate.py` → **31 passed**；**冒烟经受管编排复跑 `total=32 / PASS 25 / FAIL 0 / PENDING 7`**（证据 `smoke-summary-20261016120118.json`，与第三轮结果一致 → 行为等价）。§1 F-10 状态转「已修复」、§9.1 追加修复与验证记录、§9.3 表更新。**仅改动 OpenBase 仓脚本/文档** |
| v1.0.16 | 2026-10-16 | AA/PM-OpenBase-Dev | **F-11 干跑核对完成并修复（夹具自洽化）**：依人工指令「先处理 F-11 的干跑核对」实施——① **逐件核对**：三件 PS 工具（`verify_l1_1_cascade.ps1` / `drill_l2_1_failover.ps1` / `verify_l3_1_agent.ps1`）为**薄包装**（参数转发至同名 `.py` 运行器），其 `$PythonExe` 默认值 `'python'` 为**有意设计**（假定宿主 PATH 有解释器，并暴露 `-PythonExe` 供覆盖）；② **实测复现**：受限环境 PATH 无 `python.exe` 时，`& $PythonExe` 抛 `CommandNotFoundException` → 脚本以 **exit 1** 终止且**不落证据**（与 F-11 现象逐项吻合，非工具契约缺失）；③ **契约实证**：显式传 `-PythonExe <解释器>`（且不依赖门控 env）时三件工具均满足契约——`exit=2（PENDING）`、证据落 `-EvidenceDir/<name>`、`status=PENDING / exit_code=2 / mode=dry-run / checks=4`；④ **修复**：`tests/test_s7_tools_skeleton.py` 夹具**自洽化**（PS 分支显式传 `-PythonExe sys.executable`，与 .py 分支既有的 `sys.executable` 口径一致），**未改动任何断言**（退出码约定、必需字段、`checks` 映射、禁伪造自证全部保留）；⑤ **验证**：`pytest tests/test_s7_tools_skeleton.py -q` → **26 passed**（原 12 failed / 14 passed）；`ruff` 全清。§1 F-11 状态转「已修复」、§9.2 追加根因定论与修复验证记录、§9.3 表更新。**仅改动 OpenBase 仓测试/文档** |
| v1.0.18 | 2026-10-16 | AA/PM-OpenBase-Dev | **F-12 按方案 A 修复并复验（跨仓：OpenLLM `ff506e9`/v2.17.2）→ L3 / B1 兼容层退役闭环**：依人工指令「按方案 A 修复 F-12，并在 main.py 启动前显式求值门禁」实施。① **OpenLLM 侧改动**（5 文件 / +168 −6）：新增 `app/core/config.py::assert_startup_gates()`（**直接委托** `get_settings()`，同源同义）+ `main.py` lifespan **开头**无包裹调用（不合规即拒绝启动；「启动自检」保持原 fail-open 语义）+ 新增 `tests/unit/test_f12_startup_gate_runtime.py`（**6 例**：辅助函数正/负向、dev 不门禁、**门禁异常必须穿透 lifespan**、**求值不得位于 fail-open try 内**（哨兵穿透法）、与 `get_settings()` 同义）+ 版本 `v2.17.1 → v2.17.2`（`version.json` 与 `APP_VERSION` 对齐）+ DevLogReport **v1.2.1 §18**（背景/根因/实施/验证/影响边界/回滚）。② **TDD**：先写 6 例 → RED（`assert_startup_gates` 未实现，收集失败）→ 实现 → **6 passed**。③ **验证**：相关回归（新用例 + B1 D4 门禁 + users API + B1 接线 + C4 门禁 + 租户隔离门禁）**58 passed**；`ruff` **All checks passed**；**运行态探针复跑 `overall_pass=true`**（D1 production 缺 enforce / D2 user 未纳入灰度 → **均 `exit=3` 拒绝启动、`started=false`**；D3 接线自证：自检 fail-open 保留 + 门禁在自检之前且未被 try 包裹；D4 对照不触发；C1 退役面 43 例保持 passed）。④ **推送**：OpenLLM 分支 `feature/s4-identity-channel-b` 三远程（origin/backup/github）均 = `ff506e9`。⑤ **影响与边界**：同类门禁（`SECRET_KEY` / C4 入站头 / 租户隔离 A 三项）**一并恢复运行态效力**；非生产零变化；生产不合规将拒绝启动（既定机械截止语义，上线前需确认配置齐备）；**其余 12 模块 / 40 处旧门不在本批范围**（§17.5）；**回滚** = 移除 lifespan 开头一行调用。**§10 追加修复与验证记录、§10.3 L3 判定转「已闭环」** |
| v1.0.17 | 2026-10-16 | AA/PM-OpenBase-Dev | **新增 F-12（OpenLLM 仓，P1）—— L3 / B1 D4 phase 4 兼容层退役跨仓复核发现（生产安全耦合未生效）**：依人工指令「先处理 L3 B1 兼容层退役」实施**跨仓只读复核**（探针 `doc/tmp/b1_compat_retire_probe.py`，不修改 OpenLLM 任何文件）。① **退役本体已落地（实证）**：`app/api/users.py` 已无 `get_current_admin_user` 导入/依赖，改挂 `require_permission(PERM_USER_READ/WRITE/DELETE)`；交付提交 `298fe7d`（v2.17.0）在 HEAD 祖先链上且分支跟踪 origin；`tests/unit/{test_b1_d4_compat_gate,test_users_api,test_b1_rbac_wiring}.py` 本机复跑 **43 passed**。② **安全耦合未生效（F-12）**：受控端口 8056 实跑三场景——`ENV=production` + `RBAC_PERMISSION_ENFORCE=false`、以及 enforce=true 但 `MODULES=["role"]`（user 未纳入）——**两次均 `Application startup complete.` 正常启动**，仅打印 `WARNING 启动自检跳过: 生产环境必须开启 RBAC_PERMISSION_ENFORCE=true…`；根因＝`get_settings()` 的生产门禁在 app 内**唯一**启动期调用点位于 `app/core/startup_alignment.py:128`，而 `main.py` 的 lifespan 以 `try/except Exception: logger.warning("启动自检跳过: …")` **fail-open** 包裹该自检 → `ValueError` 被吞。③ **残量边界（如实登记，未在本批范围）**：`get_current_admin_user` 在 `app/` 下仍有 **40 处调用点 / 12 个模块**（auth_service 定义 + config/audit_logs/tenants/roles/plugins/billing/cascade_routing/semantic_routing/circuit_breakers/tenant_management/prompt_assembly/config_import_export），与 OpenLLM 交付记录 §17.5「退役面 = only users 端点」一致。证据 `doc/test/evidence/manual/b1-compat-retire-openllm-20261016.json`（`overall_pass=false`，D1/D2 即为 F-12 客观取证）。**未改动 OpenLLM 任何文件；修复需 OpenLLM 侧授权** |
| v1.0.19 | 2026-10-16 | AA/PM-OpenBase-Dev | **B1 D4 phase 5：其余 12 模块旧管理硬门退役（退役面全量清零）——OpenLLM 交付跨仓复核通过 → §10.4 第 3 项关闭**：依人工指令「继续推进其余 12 模块的硬门改造」实施。① **OpenLLM 侧交付**（`f7c7073` / v2.17.3，27 文件 / +434 −96）：`app/api/` 其余 **40 处 / 12 文件** `Depends(get_current_admin_user)` → `Depends(require_permission(<module>:<action>))`（`app/api/` 下旧门调用点**归零**）；新增 10 个权限码（audit:read / config:read / config:write / plugin:write / billing:write / routing:read / routing:write / tenant:read / tenant:write / prompt:write）；生产门禁判据由「仅 user」扩展为**退役面全集**（`ADMIN_GATE_RETIRED_MODULES`，11 模块，逐项列出缺失模块）；清理 3 处死导入（workspaces / ab_tests / usage）；DevLogReport **v1.2.2 §19**。② **验证（实测）**：新增护栏 `test_b1_d4_phase5_admin_gate_retire.py` **98 passed**（含 30 例**反例自证**强判别新旧门：强制期 + 模块未纳入灰度 → 放行，旧硬门存在时必失败）；相关回归首轮 292 例 **285 passed / 7 failed**（7 项均为**退役后语义同步项**：6 个既有文件以旧硬门语义编码「非管理员→403」、1 例门禁用例以 phase 4「仅 user」判据编码）→ 同步 6 文件后复跑 **239 passed / 0 failed**；ruff 与 HEAD 基线（`ff506e9` worktree）同文件集对比 **374 → 371（净 −3）**、**零新增**；三远程（origin/backup/github）**均 = `f7c7073`**。③ **复核证据** `doc/test/evidence/manual/b1-phase5-retire-openllm-20261016.json`（`overall_pass=true`）；**新增 §10.5**，§10.4 第 3 项由「不在本批范围」转 **✅ 已退役**。④ **未决（如实登记）**：`tenant_management.py` 未被挂载（疑似遗留文件，去留待裁定）；`circuit_breakers.py` 的 `current_user: dict` 注解不一致（改动前既有）；**生产强制期实际翻转**（`RBAC_PERMISSION_ENFORCE=true` + 模块灰度）未在本批执行（需影子期观测窗口 + 运维授权）。**本项不改变 L3 闭环判定**（§10.3） |
| v1.0.20 | 2026-10-16 | AA/PM-OpenBase-Dev | **`tenant_management.py` 去留裁定「删除」并执行（OpenLLM `0d87bf1`/v2.17.4）**：依人工指令「先裁定 tenant_management.py 的去留」实施**取证 + 执行 + 留痕**。**四条件取证**：① 未被任何入口挂载（`main.py` / `tests/conftest.py` / 全仓均无 import 或 `include_router`；`tenant_management` 引用仅存于文档、历史报告与测试运行日志）；② 功能由 `tenants.py` **严格超集**承载（其 5 端点 `GET /tenants`、`GET /{id}`、`PUT /{id}/quota`、`GET /{id}/usage`、`GET /{id}/gpu-allocation` 全部已迁入，且额外具备 POST/PUT/DELETE 与 teams 系列）；③ **最新 API 设计文档 v2.14.3 该文件 0 次提及**（仅遗留 v1.9.0 文档列其为「模块 6」）；④ **历史已立项**——v1.8.0 即裁定「合并 `tenant_management` 到 `tenants.py` 并删除」（ISSUE-003 / BUG-ROUTE-003 / GAP-03 / TD-003 均闭合；部署指南与修复验证审计报告均记「已删除」），但 `git log --follow` 显示该文件自 `73c375d initial commit` 起**从未进入删除记录** → 属**已裁定未执行的清理**。**执行**：OpenLLM 删除该文件（`0d87bf1`，4 文件 / +19 −319，`delete mode` 记录在案），`app/api/` 旧管理硬门退役面由 12 文件收窄为 **11 文件**；**验证** `test_tenant_management_api + test_tenants_api` → **27 passed**（应用构建与租户端点不受影响）；版本 `v2.17.3 → v2.17.4`；DevLogReport **v1.2.3 §19.6/§19.7**。**登记（另行裁定，本批不动）**：`tests/unit/test_tenant_management_api.py` 名义覆盖该模块，实则仅打 `/api/v1/tenants/stats` 与 `/api/v1/tenants/config`（两文件皆无此端点、断言 `!= 404` 恒真）→ 与被删文件**零耦合**。回填本文档 §10.5 未决项 1 + 证据 JSON `open_items.O1`。三远程均 = `0d87bf1` |
| v1.0.21 | 2026-10-16 | AA/PM-OpenBase-Dev | **`test_tenant_management_api.py` 去留裁定「删除」并执行（OpenLLM `4993f43`/v2.17.5）**：依人工指令「先裁定 test_tenant_management_api.py 的去留」实施**取证 + 执行 + 留痕**。**三条件取证**：① **断言恒真（虚假覆盖）**——4 条断言全部打在**不存在**的端点（`GET /api/v1/tenants/stats`、`GET/PUT /api/v1/tenants/config`；在 `tenants.py` 全部 13 路由与任何 `app/` 模块中均不存在），请求被 `GET /{tenant_id}` 的 UUID 校验挡为 **422**，故 `!= 404` **因错误原因通过**；未认证用例的 `== 401` 亦属通用鉴权行为；② **零依赖**——全仓（含测试与门禁契约）对该文件名无任何引用；③ **命名指向已删模块**——`tenant_management.py` 已于 v1.0.20 裁定删除，保留即等于保留虚假覆盖。**执行**：OpenLLM 删除该文件（`4993f43`，4 文件 / +19 −64，`delete mode` 记录在案）；**验证** `pytest tests/unit --collect-only` → **3871 tests collected / exit 0**（无悬挂引用）；版本 `v2.17.4 → v2.17.5`；DevLogReport **v1.2.4 §19.6/§19.7**。**登记待补（本批不实施）**：`tenants.py` 的 `PUT /{tenant_id}/quota`、`GET /{tenant_id}/usage`、`GET /{tenant_id}/gpu-allocation` **功能覆盖为零**，建议独立补测（跨租户 403 / 未认证 401 反例自证），归属 `tests/unit/test_tenants_api.py`。回填本文档 §10.5 未决项 4 + 证据 JSON `open_items.O4`。**推送**：三远程（origin / backup / github）均 = `4993f43`（github 首推遇 `Connection was reset` 网络瞬断，**重试后成功**） |
| v1.0.22 | 2026-10-16 | AA/PM-OpenBase-Dev | **tenant_management 三端点补测完成（闭合 v1.0.21 登记的覆盖缺口，OpenLLM `4a87cc0`/v2.17.6）**：依人工指令「先补测 tenants.py 的三个端点」实施。① **归属文件** `tests/unit/test_tenants_api.py` 新增 `TestTenantQuotaUsageGpuAPI`（**12 例**）——`PUT /{id}/quota`：**落库断言**（`TenantQuota` 行 + 值 + `reset_period`）、同 `resource_type` 二次更新**命中既有行**（行数 1、值 10→99）、不存在租户 404、未认证 401；`GET /{id}/usage`：**聚合数值逐项等于种子**（`total_requests=2` / `prompt=300` / `completion=60` / `cost≈0.03` / `avg_latency≈150.0` / `model_breakdown[0].tokens=360`）、同租户成员放行（含**空聚合分支**）、**跨租户 403 反例自证**、401；`GET /{id}/gpu-allocation`：字段逐项校验、空列表、**跨租户 403 反例自证**、401。与已删的「`!= 404` 恒真空断言」相对，本组**每个断言均校验具体值或具体错误文案**。② **验证**：单跑 **12 passed**（23 deselected）；合并回归（`test_tenants_api` 35 + phase-5 护栏 98）→ **133 passed / 0 failed**；`ruff` 该文件 40 项告警**全部位于改动前既有区域**（本批新增区间命中 0）。③ **留痕**：版本 `v2.17.5 → v2.17.6`；DevLogReport **v1.2.5 §20**；回填本文档 §10.5 未决项 4 + 证据 JSON `open_items.O4`（`follow_up → resolution`）。④ **推送**：三远程均 = `4a87cc0` |
| v1.0.23 | 2026-10-16 | AA/PM-OpenBase-Dev | **`circuit_breakers.py` 注解不一致修复（实为真实缺陷：3 管理端点 500 + 审计事件静默丢失，OpenLLM `2263ba4`/v2.17.7）**：依人工指令「先处理 circuit_breakers.py 的注解不一致问题」按 **TDD** 实施。① **取证**：8 端点标注 `current_user: dict` 但依赖实际返回 **`User`**（`auth_service.get_current_user` / `require_permission._guard`）；3 个管理端点函数体沿用 dict 语义 `current_user.get("id")` → 运行态 `AttributeError`：审计事件被内层 try **静默吞掉（不落库）**、外层 logger 再次抛出 → 兜底 **500**。② **掩盖机制**：既有用例 `test_reset_circuit_breaker_success` 为 `test_admin` **动态补 `get` 方法**（把 `User` 伪装成 dict）以迁就实现 → **测试通过而运行态 500**（与 v1.0.21 §19.6 的「空断言」同类：绿灯不成立于产品语义）。③ **RED→GREEN**：先删迁就代码并按真实语义断言（含审计事件落库 + `details["reset_by"\|"updated_by"] == str(admin.id)`）→ **RED 3 例均 `assert 500 == 200`** → 修复（注解 `dict`→`User` 8 处、`.get("id")` → `.id`、JSONB 域 `str(...)`、新增 `User` 导入）→ **GREEN**。④ **验证**：`test_circuit_breakers_api` **9 passed**；合并回归（含 phase-5 护栏 98）→ **107 passed / 0 failed**；`ruff` 两文件告警均在未触碰行 → **零新增**。⑤ **留痕**：版本 `v2.17.6 → v2.17.7`；DevLogReport **v1.2.6 §21**；回填本文档 §10.5 未决项 2 + 证据 JSON `open_items.O2`。⑥ **推送**：三远程均 = `2263ba4` |
| v1.0.24 | 2026-10-16 | AA/PM-OpenBase-Dev | **B1 D4 phase 6：providers / local_models 同族旧管理硬门退役（`get_admin_user_or_api_key`，OpenLLM `da3b834`/v2.17.8）**：依人工指令「按方案 A 执行」实施。① **背景（同族残留）**：phase 5 已清零 `get_current_admin_user`，但 `get_admin_user_or_api_key`（v2.14.0 设计的「管理员 API Key 通道」，判定链同为 `is_admin()`）仍在 2 文件 / **12 处**写端点，且该 2 模块写端点**未接 RBAC** → B1「授权唯一由权限码承担」在此仍被绕过；经**人工裁定方案 A**（同 phase 5 方法退役，不作为设计例外保留）。② **实施**：`providers.py` 6 处 → `require_permission(provider:write)`；`local_models.py` 6 处 → `require_permission(local_model:write)`；新增 2 权限码；`ADMIN_GATE_RETIRED_MODULES` 11 → **13 模块**（生产门禁同步扩展）。③ **语义等价性**：管理员 JWT / **管理员所属 API Key** 均经 `is_admin()` 快路径等价放行；非管理员通道由「恒定 403」→「按权限码（强制期）」。④ **验证（TDD）**：新增护栏 **43 例** → **RED 15 failed / 28 passed**（`git stash` 暂回退 4 个源文件至 HEAD；12 例反例自证 `403 != 403` + 门禁覆盖 2 例）→ **GREEN 171 passed / 0 failed**（含同步后的 `test_providers_api` 与 phase-5 护栏）；ruff **新增文件 All checks passed**、改动文件**零新增**。⑤ **登记（本批不实施）**：`get_admin_user_or_api_key` 退役后无调用点（定义保留，待裁定清理）；`e2e_v214_security.py`（M2-004 非管理员 API Key 模型写 403）等 e2e 脚本期望需按强制期配置复核。⑥ **留痕**：版本 `v2.17.7 → v2.17.8`；DevLogReport **v1.2.7 §22**；回填本文档 §10.5 新增项 5 + 证据 JSON `open_items.O5`。⑦ **推送**：三远程均 = `da3b834` |
| v1.0.25 | 2026-10-16 | AA/PM-OpenBase-Dev | **auth_service 退役后死定义清理（`get_current_admin_user` / `get_admin_user_or_api_key` + `app.services` 再导出，OpenLLM `f477d1e`/v2.17.9）**：依人工指令「清理 auth_service 中的死定义」按 **TDD** 实施。① **背景**：phase 4~6 已清零旧管理硬门**调用点**（§10.5 第 1~5 项），两处**定义体**按「调用点先退役、定义与再导出另裁」纪律保留至今 → 本批为**死定义收尾**。② **护栏先行（RED）**：新增源码契约 `tests/unit/test_b1_d4_retired_gate_symbols_cleanup.py`（**3 例**）→ **RED 3 failed**（①② 报符号与再导出仍在；③ 初版以 `utf-8` 读源码在 `app/services/audit_service.py` 触发 `SyntaxError: invalid non-printable character U+FEFF` → 改用 `utf-8-sig` 后精确报出 `services/__init__.py` 的再导出引用）。③ **修复**：整段移除两个函数定义 + 移除 `services/__init__` 的 import 与 `__all__` 条目。④ **验证**：**GREEN 216 passed / 0 failed**（护栏 3 + phase-5 98 + phase-6 43 + providers 30 + auth 20 + users 22）；`ruff` 改动/新增文件 **All checks passed**；`pytest tests/unit --collect-only` **无悬挂引用**。⑤ **行为零变化**：删除的是无调用点定义体与再导出（运行路径未动）；全仓仅在注释/文档字符串提及该两符号，跨仓为 HTTP 无导入面。⑥ **登记**：`audit_service.py` 的 UTF-8 BOM 影响 `ast.parse(文本)` 类工具链；v2.14.x 历史设计文档作为快照不回溯改写，后续版本设计文档需按 phase 5/6/死定义清理同步。⑦ **留痕**：版本 `v2.17.8 → v2.17.9`；DevLogReport **v1.2.8 §23**；回填本文档 §10.5 新增项 6 + 证据 JSON `open_items.O6`。⑧ **推送**：三远程均 = `f477d1e` |
| v1.0.26 | 2026-10-16 | AA/PM-OpenBase-Dev | **源码编码统一：清理 Python 源码 UTF-8 BOM（7 文件 / 3 仓）**：依人工指令「先统一清理 audit_service.py 的 UTF-8 BOM」按 **TDD** 实施（承 §10.5 项 6 登记的独立清理项）。① **跨仓字节级只读扫描**（判据＝首 3 字节 `EF BB BF`；5 仓 / 扩展名 11 类；排除 `.git`/`node_modules`/`.venv*`/`extras`/`.pylib`/缓存）：**8908** 文件命中 **497** → `.py` **7**（OpenBase 2 / OpenLLM 4 / OpenMemory 1）、`.ps1` **46**（有意保留）、其它 **444**（`.md` 236 / `.json` 29 / 其余 179，**待裁定**）。② **护栏先行（RED）**：在 §10.5 项 6 的源码契约文件内追加第 4 条 `test_python_sources_have_no_utf8_bom`（扫描 `backend/**/*.py`），并将第 3 条 AST 扫描由 `utf-8-sig` 兜底**回归 `utf-8`** → **RED 2 failed / 2 passed**。③ **字节级剥离**（三重校验：首 3 字节为 BOM / 正文严格 UTF-8 解码 / 剥离前后解码内容一致；仅删 3 字节、不重编码不改行尾）：7 文件均 `−3 bytes`、`bom_now=False`。④ **验证**：OpenLLM **GREEN 183 passed / 0 failed**；OpenBase（被剥离者为核心模型 `models/base.py`、`models/business.py`）经 `doc/tmp/pyrun.py` 复跑 `test_models`/`test_db_init`/`test_three_modules` **全通过**。⑤ **留痕**：OpenLLM 版本 `v2.17.9 → v2.17.10`（`825b804`，DevLogReport **v1.2.9 §24**）；OpenBase **`5309a10`**；OpenMemory **`453c967`**（分支 `release/v7.3.0`）；新增证据 `doc/test/evidence/manual/source-bom-cleanup-20261016.json`；回填本文档 §10.5 新增项 7。⑥ **登记（待裁定）**：其余 **444** 个非 `.py` 文本文件是否统一清理（涉文档版本管理规范与各工具链兼容性）；各仓「源码编码契约」尚未统一建立（本批仅在 OpenLLM 落地） |
| v1.0.27 | 2026-10-16 | AA/PM-OpenBase-Dev | **跨仓源码编码契约建立 + `.ps1` GBK 误解码风险修复（12 文件 / 3 仓）**：依人工指令「按这个方案统一建立跨仓源码编码契约」按 **TDD** 实施（承 §10.5 项 7 的 S2 登记）。① **单一事实源工具**：新增 `scripts/scan_source_encoding.py`（跨仓扫描器，零第三方依赖；硬判据「`.py` 不得带 BOM」「含非 ASCII 的 `.ps1` 必须带 BOM」；其余扩展名仅统计；排除第三方/缓存/构建目录与 `doc/tmp`；CLI `--check`/`--json --out`/`--strip-py`）。② **回归（护栏先行）**：新增 `tests/test_source_encoding_contract.py`（**5 例**，含 `.py` 带 BOM 正控、`.ps1` 带 BOM 负控、非 ASCII `.ps1` 无 BOM 正控）→ **RED 4 failed（扫描器缺失）→ GREEN 5 passed**。③ **落地即修复真实缺陷**：命中 **12 个含非 ASCII 却无 BOM 的 `.ps1`**，其中 **9 个在 GBK 默认代码页下确实解析失败**（共 **37** 个解析错误；`deploy.ps1` 18、`install-ollama.ps1` 9）→ 逐文件**前置 3 字节 BOM** → 全部 **0 解析错误**；契约面复跑 **8857 文件 / 违规 0 / PASS**。④ **证据**：`doc/test/evidence/manual/source-encoding-contract-20261016.json`（机器生成）+ `source-encoding-ps1-remediation-20261016.json`（前后对照）。⑤ **留痕/推送**：OpenLLM **`b0cea58`**（10 文件 + DevLogReport **v1.2.10 §25**，产品版本不变 v2.17.10）、OpenRAG **`fcec166`**、OpenMemory **`f30d361`**、OpenBase **`0fe52fc`**（均三远程）；回填本文档 §10.5 新增项 8；`source-bom-cleanup-…json` 的 `open_items.S2` 转 ✅。⑥ **登记（待裁定）**：其余 **444** 个非 `.py` 文本文件（`.md` 236 / `.json` 23 / `.txt` 178 等）的 BOM 处置 |
| v1.0.28 | 2026-10-16 | AA/PM-OpenBase-Dev | **余下未决项裁定执行（A 挂起 / B1 / C1 / D 维持）**：依人工裁定「A 挂起、B1、C1、D 维持」执行。① **A（生产强制期实际翻转）→ 挂起**：待影子期观测窗口 + 运维授权，本机不翻转；退役面实际保护由生产启动门禁兜底（不合规即拒绝启动）。② **B1（`e2e_v214_security.py` M2-004 期望复核）→ 已执行**：脚本改为**按强制态判定**（新增 `EXPECT_WRITE_ENFORCED` 读环境变量 `OPENLLM_E2E_RBAC_ENFORCE`，默认 `0`；env=1 断言 `403`，否则断言「放行（∉{401,403}）」），OpenLLM 提交 **`e451177`**（2 文件 / +55 −3，三远程）；`py_compile` OK、`ruff`（本仓 `ruff.toml`）与 HEAD 基线**逐项一致（UP009/I001/C408）→ 零新增**；运行态未实跑（需 `127.0.0.1:8013` 活动服务 + 共享 PG，不在本机 pytest 面内）；DevLogReport **v1.2.11 §26**（产品版本保持 v2.17.10）。③ **C1（其余 444 个非 `.py` 文本 BOM 处置）→ 维持现状**：契约中仅统计上报、不计失败（不统一剥离）。④ **D（DPS 自身 IAM 演进立项）→ 维持**：仍为版本规划中的规划项，不立项实施。⑤ 回填 §10.5 项 3/5/7（含项 8 ⑥）/新增项 9 + 续接指南 §7.1 项 8。 |

---

## §1 分派总表

> 口径：**阻塞用例数** = 该缺陷直接导致 FAIL / BLOCKED 的 **P0** 用例条数；三缺陷合计 **15** 条。关联断言与关联卡取自《OpenBase-S7-沙箱外执行单-v1.0.5》§2/§3 与《OpenBase-数据隔离实现任务卡-v1.0.0》。

| 编号 | 标题 | 责任方 | 优先级 | 阻塞用例数 | 关联 S7 断言 | 关联卡（七线 JT） | 状态 |
|:---:|------|--------|:---:|:---:|-----------|------------------|:---:|
| **F-1** | OpenLLM 上游 Ollama 不可达（`192.168.0.4:11434` / `localhost:11434` 连接被拒）+ 三真实开关未全开（`open_memory`/`open_rag` client 未注入；`dps` client 已注入但探活 401） | **OpenLLM 仓 + 环境侧**（联调窗口：启动上游 / 改上游地址 / 置开关） | P0 | **8** | S7-T6-2（冒烟 S0~S6） | K15（REAL_* 兜底收口）、K02(LL) | **已修复（v1.0.4）** |
| **F-2** | OpenRAG 共享库 `collections` 表缺 `tenant_code` 列 → `GET /api/v1/collections`（带 X-API-Key）500、集合创建 / 列表、文本入库（`/documents/text`）、检索、以及经网关的 `rag-proxy query` 500 | **OpenRAG 仓** | P0 | **5** | S7-T6-2、S7-T4-1~4（L2-2 通道矩阵）、S7-T6-4（K07/SYS-1 真实终验） | K10（OpenRAG 强制过滤骨架）、K02(RG) | **已提交（`ada7a97`，三远端同步）** |
| **F-3** | OpenLLM `TRUSTED_PROXY_SOURCES=llm-proxy` 与 OpenBase 注入的 `openbase-llm-proxy` 不一致 → M3 可信源不生效（`identity.proxy_source=null`、审计外部身份未采纳） | **OpenLLM 仓**（白名单取值对齐）；OpenBase 提供协议头单一事实源对标 | P0 | **2** | S7-T6-2、S7-T6-1（RA-06 M3 五项真实面） | K09（编排出站身份透传）、K02(LL) | **已修复关闭（v1.0.3）** |
| **F-5** | OpenLLM K07 端点-过滤矩阵全量缺填（真实底单 351 操作中 344 未登记 + 无隔离用例） | **OpenLLM 仓**（工作树全量补填已完成/待提交） | P0 | **0**（非冒烟阻塞项，属 K07 矩阵治理） | S7-T6-4（K07/SYS-1） | K07（端点-过滤矩阵填报）、K02(LL) | **已提交（`41af780`，三远端同步）** |
| **F-6** | OpenMemory K07 端点-过滤矩阵 8 条缺口（真实底单 36 操作中 8 条未登记 + 无隔离用例） | **OpenMemory 仓**（工作树 8 条缺口补填已完成/待提交） | P0 | **0**（非冒烟阻塞项，属 K07 矩阵治理） | S7-T6-4（K07/SYS-1） | K07（端点-过滤矩阵填报）、K02(OM) | **已提交（`0a6f351`，三远端同步）** |
| **F-7** | OpenLLM DPS 组件探活恒 401（real 模式探活打业务只读面 `/api/v2/portrait/list`，要求组织/租户身份头，而探活上下文无身份）→ `/openllm/v1/health` 的 dps 恒 unavailable，掩盖真实可用性 | **OpenLLM 仓**（探活改走运维端点 `/health/liveness`） | P0 | **0**（非冒烟阻塞项，属健康探活口径） | S7-T6-1（RA-06 真实面）、S7-T6-2 | K09（编排出站身份透传）、K02(LL) | **已提交（`f1d187b`，三远端同步）** |
| **F-8** | `GET /api/v1/auth/me` 在主体 `tenant_id` 为整数（agent 绑定租户）时返回 **500** —— `MeResponse.tenant_id: str \| None` 与 `resolve_agent_principal` 返回的 int 冲突（pydantic `string_type` 校验失败）；主体未绑租户（int=None）时不触发 | **OpenBase 仓**（响应模型 / 端点序列化口径对齐） | P1 | **0**（非冒烟 S0~S6 阻塞项；属 L3-1 agent key 面读取端点） | S7-T5-1~4（L3-1 Agent 端到端）、S7-T6-1（RA-06 真实面） | — | **已修复（`6bf7832`，v1.0.14）** |
| **F-9** | `POST /api/v1/users` **不派生 `tenant_code`**（agent 路径经 `_resolve_tenant_code` 派生），致该路径建的同域账号作委托目标时「目标行域为空 → 同域委托被误判 `PERM_DELEGATION_CROSS_TENANT` 403」（探针观测项 O 自证：期望同域放行 200，实测 403）；**同根因旁路**：OIDC JIT `_bind_or_create_user` 同样只落 `tenant_id` | **OpenBase 仓**（`users` 创建路径 + OIDC JIT 建号补 `tenant_code` 派生，与 `identity/agents` 口径统一） | P1 | **0**（非冒烟 S0~S6 阻塞项；属委托域不变式的目标装配口径） | S7-T6-1（RA-06 委托跨界真实面）、S7-T5-1~4 | — | **已修复（`6bf7832`，v1.0.14）** |
| **F-10** | **SHR 门禁 T1-4 失败**：`scripts/scan_orchestrator_bypass.py` 命中 3 处批量杀路径——`scripts/run_smoke_s0_s6.ps1`（L59 端口残留清理、L123 收尾停服）与 `scripts/verify_mtauth_realface.ps1`（L237 收尾停服）均直接使用 `Stop-Process`，违反「服务生命周期编排唯一入口」纪律 | **OpenBase 仓**（改为经受管编排 `service-orchestrator.ps1 -Action start/stop -Only ...`，或在扫描器加**带票据/审批人/有效期**的豁免位） | P1 | **0**（门禁项，非冒烟用例阻塞项） | S7-T1-4（SHR 受管编排唯一入口） | — | **已修复（方案 A，v1.0.15）** |
| **F-11** | **S7 工具骨架门禁失败 12 项**：`tests/test_s7_tools_skeleton.py` 期望 `verify_l1_1_cascade.ps1` / `drill_l2_1_failover.ps1` / `verify_l3_1_agent.ps1` 干跑退出码 = 2（PENDING）实测为 1，且 `l1_1/l2_1/l3_1` 证据 JSON 未在临时目录产出（`FileNotFoundError`） | **OpenBase 仓**（核对 l1_1/l2_1/l3_1 工具干跑退出码契约与 `-EvidenceDir` 参数，或同步测试期望） | P2 | **0**（门禁项，非冒烟用例阻塞项） | S7-T2-1 / S7-T3-1 / S7-T5-1（三原则总验证工具面） | — | **已修复（夹具自洽化，v1.0.16）** |
| **F-12** | **（OpenLLM，跨仓复核发现）** L3 / B1 D4 phase 4「兼容层退役」的**生产安全耦合未生效**：`APP/core/config.py::get_settings()` 中「生产必须 `RBAC_PERMISSION_ENFORCE=true` 且 user 纳入灰度」门禁，在 app 内唯一启动期调用点被 `main.py` 启动自检的 **fail-open 兜底吞掉** → 生产带 `RBAC_PERMISSION_ENFORCE=false` 仍能启动（实测 `Application startup complete.`），users 端点将处于无保护状态（该门禁本为退役后的机械截止手段） | **OpenLLM 仓**（把启动门禁置于 fail-open 自检之外，或令门禁 `ValueError` 不被吞） | P1 | **0**（不影响 S7 冒烟用例；属生产启动门禁有效性） | L3 / B1 D4 phase 4（S7-T1-4 同源纪律：门禁必须真实生效） | — | **已修复（方案 A，`ff506e9`/v2.17.2，v1.0.18）** |
| — | **合计** | — | — | **15**（F-1~F-3 冒烟阻塞 15；F-5~F-12 各计 0） | — | — | — |

> **冒烟快照**（`smoke-summary.json`，`generated_at=2026-09-11T18:57:56+08:00`，`openbase_commit=0595bcde788bd19d3a2e21ffc647b827eaa3fded` / 短号 `0595bcd`）：**P0 30 例 PASS 14 / FAIL 9 / BLOCKED 7；P1 2 例 BLOCKED**（`entry_criteria_met=false`）。9 条 FAIL **全部**由 F-1/F-2/F-3 覆盖（F-1 2 条：S0-1、S1-2；F-2 5 条：S1-1、S3-1、S3-2、S3-3、S6-1；F-3 2 条：S0-4、S5-3）；7 条 BLOCKED 中 6 条由 F-1 覆盖（S2-4、S3-4、S5-1、S5-2、S5-4、S5-5），余 1 条 **S5-6** 为禁停服务约束（归受控窗口，不在本单）。
> **v1.0.8 收口（2026-09-12）**：K07 挂起项全部闭环——**F-5**（OpenLLM `41af780`）、**F-6**（OpenMemory `0a6f351`）均已入库并三远端同步；**DPS 35 条豁免已续期至 2026-12-31**（续期日 2026-09-12，门禁复跑 exit 0）→ K07/SYS-1 门禁 verdict 由 `PARTIAL` 升 **PASS**（缺口 0 / 未覆盖 0 / 豁免 59 全有效）；门禁聚合复跑 `overall=PASS exit=0 pass=20 fail=0 pending=2`。**F-1~F-7 与全部 K07 挂起项至此闭环**（余环境侧写限制与特性缺口登记，非缺陷）。

---

## §2 F-1 详单（OpenLLM 上游 Ollama 不可达 + 三真实开关未全开）

### 2.1 现象与证据

证据文件：`doc/test/evidence/s7/smoke/smoke-summary.json` 与 `s0-s6-cases.json`（同源）；`doc/test/evidence/s7/env/env-check.json`。逐条引用如下：

| 用例 ID | 请求（脱敏） | 状态 | 判定 | 证据摘要（脱敏） |
|:---:|------|:---:|:---:|------|
| S0-1 | `GET http://127.0.0.1:8001/openllm/v1/health`（Authorization 已使用） | 200 | **FAIL** | `{"openmemory": "组件 open_memory 不可用: client 未注入", "openrag": "client_not_injected", "dps": "组件 dps 不可用: HTTP 401: 缺少组织或租户标识 (status=401)"}` |
| S1-2 | `GET http://127.0.0.1:8001/openllm/v1/health`（三上游探活） | 200 | **FAIL** | 同上（openmemory/openrag client 未注入 → 上游不可达） |
| S2-4 | `POST http://127.0.0.1:8000/api/v1/llm-proxy/chat`（主通道非流式） | 500 | **BLOCKED** | `{"code":5001,"message":"内部错误，请稍后再试","data":null,"timestamp":"2026-09-11T10:57:55.055096+00:00"}` |
| S3-4 | `POST http://127.0.0.1:8000/api/v1/llm-proxy/chat`（rag） | 500 | **BLOCKED** | `{"code":5001,...}`（Ollama 不可达 + rag client 未注入） |
| S5-1 | `POST http://127.0.0.1:8000/api/v1/llm-proxy/chat`（非流式 /chat） | 500 | **BLOCKED** | `{"code":5001,...}` |
| S5-2 | `POST http://127.0.0.1:8000/api/v1/llm-proxy/chat/stream`（SSE） | 200 | **BLOCKED** | `event: routing` → `{"components":{"need_memory":false,"need_rag":false,"reason":"explicit","rag_source":"skipped"},"model":{"selected":"gpt-4o-mini","reason":"cost"},"parallel":false}`（受上游不可达阻塞） |
| S5-4 | 流式收尾 `EvaluateSession`（依赖 S5-2 流式成功） | — | **BLOCKED** | `—`（依赖 S5-2；受 Ollama 上游不可达阻塞） |
| S5-5 | `POST http://127.0.0.1:8000/api/v1/llm-proxy/chat`（llm-only explicit 语义） | 500 | **BLOCKED** | `{"code":5001,...}` |

> 环境侧佐证 `env-check.json` → `checks[name=openllm_runtime]` 功能注记：`/openllm/v1/health` 显示 openmemory/openrag 组件 client 未注入、dps client 已注入；LLM 推理上游 Ollama（`192.168.0.4:11434` 与 `localhost:11434`）连接被拒 → `/openllm/v1/chat` 5001。对应 `pending_items[id=ENV-OPENLLM-UPSTREAM]`（owner=联调窗口）。

### 2.2 根因判定

1. **上游地址不可达**：OpenLLM 运行态读取的上游为局域网 Ollama。实测配置（只读）：
   - `D:\Trae CN\myproject\Dev\OpenLLM\backend\.env` **L24** `OLLAMA_HOST=http://192.168.0.4:11434`、**L25** `OLLAMA_BASE_URL=http://192.168.0.4:11434/v1`；
   - `D:\Trae CN\myproject\Dev\OpenLLM\.env.shared-infra` **L36** `OLLAMA_HOST=http://192.168.0.4:11434`、**L37** `OLLAMA_BASE_URL=http://192.168.0.4:11434/v1`；
   - 代码默认（`backend\app\core\config.py` **L152~L153**）为 `OLLAMA_BASE_URL=http://localhost:11434/v1` / `OLLAMA_HOST=None`。
   实测 `192.168.0.4:11434` 与 `localhost:11434` **连接被拒**（All connection attempts failed）→ `/openllm/v1/chat` 返回 5001。
2. **三真实开关未全开**：`backend\.env` 中**未出现** `OPENLLM_OPENMEMORY_REAL` / `OPENLLM_OPENRAG_REAL` 两键 → 生效值为代码默认 `False`（`config.py` **L247~L250** `OPENLLM_OPENMEMORY_REAL` default `False`；**L218~L221** `OPENLLM_OPENRAG_REAL` default `False`；模板 `backend\.env.example` **L40/L41** 亦为 `false`）→ `open_memory` / `open_rag` **client 未注入**。
3. **dps 侧另一情形**：`backend\.env` **L51** `OPENLLM_DPS_REAL=true`（真实契约已开，且 **L52~L55** 四头 ORG/TENANT/USER/ROLE 已配）→ dps client **已注入**，但探活因**缺少组织 / 租户头**返回 HTTP 401（`/openllm/v1/health` 探活口径，非本次分派阻塞项）。

> **判定结论**：F-1 = 「上游 Ollama 不可达」+「`OPENLLM_OPENMEMORY_REAL` / `OPENLLM_OPENRAG_REAL` 未开启」双因素叠加；属**环境待办 + 开关未置**（`env-check.json` 明确标注「环境待办」），非用例设计缺陷。

### 2.3 修复动作

> 责任方：**OpenLLM 仓 + 环境侧（联调窗口）**。以下键名均自实际文件只读核对。

**步骤 A — 启动 Ollama（或改上游地址为可用实例）**

| 文件 | 行号 | 键名 | 当前值 | 目标值 |
|------|:---:|------|--------|--------|
| `OpenLLM\backend\.env` | L24 | `OLLAMA_HOST` | `http://192.168.0.4:11434` | 可达实例地址（如已启动的 Ollama） |
| `OpenLLM\backend\.env` | L25 | `OLLAMA_BASE_URL` | `http://192.168.0.4:11434/v1` | 可达实例 `<base>/v1` |
| `OpenLLM\.env.shared-infra` | L36/L37 | `OLLAMA_HOST` / `OLLAMA_BASE_URL` | `http://192.168.0.4:11434` / `.../v1` | 与上保持一致 |

**步骤 B — 置三真实开关（逐键当前值 / 目标值）**

| 文件 | 行号 | 键名 | 当前值 | 目标值 |
|------|:---:|------|--------|--------|
| `OpenLLM\backend\.env` | —（缺省） | `OPENLLM_OPENMEMORY_REAL` | 未配置 → 生效 `False`（config.py L247~L250 默认） | `true` |
| `OpenLLM\backend\.env` | —（缺省） | `OPENLLM_OPENRAG_REAL` | 未配置 → 生效 `False`（config.py L218~L221 默认） | `true` |
| `OpenLLM\backend\.env` | L51 | `OPENLLM_DPS_REAL` | `true` | 保持 `true`（已注入） |
| `OpenLLM\backend\.env` | L52~L55 | `OPENLLM_DPS_REAL_ORG` / `_TENANT` / `_USER` / `_ROLE` | `dps-org-001` / `dps-tenant-001` / `1` / `super_admin` | 保持（与 DPS 预置实体一致） |

**步骤 C — 核对起服日志 `contract=real`（S0-1 判据）**：OpenLLM 起服日志须出现三注入点契约生效标记（`open_memory` / `open_rag` / `dps`），对齐冒烟清单 §3「S0-1 三真实开关生效：起服日志出现 `contract=real`」。

**注意事项**：
- 上游地址 / 开关属**本机环境配置**，`.env*` 已被 `.gitignore` 排除，**不得入库**；
- **密钥 / 口令零进入提交面**；不得为「过测试」放宽断言或屏蔽 5001；
- 开关可临时置 `true` 冒烟、失败即回退 `False`（冒烟清单 §2.2 / §4 口径）。

### 2.4 验证方式

- **重跑用例 ID（8 例，期望 PASS）**：`S0-1`、`S1-2`、`S2-4`、`S3-4`、`S5-1`、`S5-2`、`S5-4`、`S5-5`。
- **期望结果**：
  - `S0-1` / `S1-2`：`/openllm/v1/health` 三组件均可用（无 `client 未注入` / `client_not_injected`）；
  - `S2-4` / `S3-4` / `S5-1` / `S5-5`：主通道非流式 / rag / llm-only 均 `2xx`，无 `code=5001`；
  - `S5-2`：SSE 事件 `routing→chunk→done` 正常；
  - `S5-4`：流式收尾触发 `EvaluateSession` 并在真实 OpenMemory 出现该轮记忆。
- **命令模板**（PowerShell；尖括号占位替换为真实值）：
  ```powershell
  # 探活（S0-1 / S1-2）
  curl.exe -s -H "Authorization: Bearer <JWT>" 'http://127.0.0.1:8001/openllm/v1/health'

  # 主通道（S2-4 / S3-4 / S5-1 / S5-5）
  curl.exe -s -X POST -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" `
    -d '{\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"stream\":false}' `
    'http://127.0.0.1:8000/api/v1/llm-proxy/chat'

  # 结果归档 + 聚合（真实面）
  python 'D:\Trae CN\myproject\Dev\OpenBase\scripts\gate_aggregate.py' --face real --only SMOKE-S0-S6 --out 'D:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\s7\gate\gate-aggregate.json'
  ```
  逐例结果归档至 `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}`。

### 2.5 回填位置

| 回填位 | 具体位置 |
|--------|---------|
| 各仓 JT 台账 / 任务卡 | OpenLLM 仓 JT 台账；`OpenBase-数据隔离实现任务卡-v1.0.0.md` **K15（REAL_* 兜底收口）** / K02(LL) 行状态 |
| 执行单 §2/§3 | 《OpenBase-S7-沙箱外执行单-v1.0.5》**§2.5**（P2 执行结果回填）/ **§3.5**（T6 真实面执行结果） |
| 测试报告 §2.2 | 《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0》**§2.2 联调窗口实跑结论更新**（S7-T6-2 行） |
| 冒烟证据 | `doc/test/evidence/s7/smoke/smoke-summary.json`（`cases[].verdict` / `pending_or_failed[]`）与 `s0-s6-cases.json` |
| 环境检查报告 | 《OpenBase-S7-联调窗口环境检查报告-v1.0.0》（内部 v1.0.2）**§2.6 F-1** 行状态、`env-check.json` `pending_items[ENV-OPENLLM-UPSTREAM]` |

### 2.6 风险与边界

- **仅环境 / 开关调整**，不得为过测试改动 OpenLLM 业务代码或放宽健康 / 对话断言；
- 上游地址变更须保证 DPS / Redis 等其余依赖不受影响；改后须保留起服日志作为 S0-1 判据；
- **不得停止或重启服务**（冒烟期）；Ollama 启动属新增进程，须与受管编排一致；
- **S5-6（OpenRAG 停服降级）不在本单**：其 BLOCKED 缘于「任务约束禁止停止 / 重启服务」，归 T3 / 受控窗口，不得以 F-1 修复名义启停服务；
- 密钥 / 口令不入库、不入报告明文；**回归失败即停**。

---

## §3 F-2 详单（OpenRAG 共享库 `collections` 表缺 `tenant_code` 列）

### 3.1 现象与证据

证据文件：`doc/test/evidence/s7/smoke/smoke-summary.json` 与 `s0-s6-cases.json`；`env-check.json`。

| 用例 ID | 请求（脱敏） | 状态 | 判定 | 证据摘要（脱敏） |
|:---:|------|:---:|:---:|------|
| S1-1 | OpenRAG / OpenMemory 鉴权（`X-API-Key` 已使用） | 500 | **FAIL** | `RAG no-key=401, key=500; MEM no-key=401, key=200` |
| S3-1 | `POST/GET http://127.0.0.1:8010/api/v1/collections`（X-API-Key） | 500 | **FAIL** | `{"code":"INTERNAL-5000","message":"创建知识库失败: ... asyncpg.exceptions.UndefinedColumnError: column collections.tenant_code does not exist ... [SQL: SELECT collections.id, collections.name, col...]"}` |
| S3-2 | `POST http://127.0.0.1:8010/api/v1/collections/{cid}/documents/text` | 500 | **FAIL** | `{"code":"INTERNAL-5000","message":"文本入库失败: ... column collections.tenant_code does not exist ..."}`（无法进入 PENDING→COMPLETED 轮询） |
| S3-3 | `POST http://127.0.0.1:8010/api/v1/collections/{cid}/query/retrieve` | 500 | **FAIL** | `{"code":"INTERNAL-5000","message":"检索失败: ... column collections.tenant_code does not exist ..."}` |
| S6-1 | `POST http://127.0.0.1:8000/api/v1/rag-proxy/collections/{cid}/query/retrieve`（经网关） | 500 | **FAIL** | `{"code":"INTERNAL-5000","message":"检索失败: ... column collections.tenant_code does not exist ..."}` |

> 环境侧佐证 `env-check.json` → `checks[name=openrag_runtime]`：`collections 相关端点因 DB 列 collections.tenant_code 缺失返回 INTERNAL-5000`；`impact` 明确「**真实缺陷，非环境待办**」。对应 `pending_items[id=ENV-OPENRAG-SCHEMA]`（owner=OpenRAG 子系统仓）。

### 3.2 根因判定

1. **运行态数据库为共享 PG**：`D:\Trae CN\myproject\Dev\OpenRAG\.env` **L9** `OPENRAG_DATABASE_URL=postgresql+asyncpg://<user>@192.168.0.151:5432/nuct`（共享库 `nuct`，口令已配置、脱敏）。共享库内 `collections` 为**早期建立的既有表，缺 `tenant_code` 列**。
2. **ORM 已声明列、但既有表不会被自动 ALTER**：`D:\Trae CN\myproject\Dev\OpenRAG\src\openrag\storage\postgres.py` **L60~L89** `CollectionTable` 已声明 `tenant_code = Column(String(64), nullable=False, default="default", server_default="default")`（**L76**）及索引 `idx_collections_name` / `idx_collections_tenant` / `uq_collections_tenant_name`（**L86~L88**）；但 `PostgresStore.initialize()`（**L279~L306**）仅执行 `Base.metadata.create_all`（**L300~L301**）——**`create_all` 对既有表不会 `ALTER TABLE ADD COLUMN`**。
3. **PG 侧缺正向落列迁移**：`D:\Trae CN\myproject\Dev\OpenRAG\src\openrag\storage\migrations.py` 模块 docstring 明示「**本仓无 alembic → create_all/DDL 幂等迁移器**」（**L1**）；`s3_tenant_columns` 迁移项（**L4**）的**可执行入口为 SQLite**（`ensure_tenant_columns_sqlite` **L109**、`run_tenant_column_migration_sqlite` **L251**）；**PG 侧仅有 `plan_rollback_postgres_tenant_columns()`（L311，回滚）与 `plan_composite_unique_postgres()`（L432，复合唯一）两个计划函数，缺「PG 正向 `ADD COLUMN tenant_code` + 存量回填 + 索引」的执行体，且未在启动 / 部署链路中执行**。
4. **部署脚本显式不支持 PG**：`D:\Trae CN\myproject\Dev\OpenRAG\scripts\tenant_backfill_report.py` **L47~L49** 对 `postgresql*` 直接 `SystemExit("PG 后端对账请在 S3 联调环境执行（R-4）；本机以 SQLite 验证")`。
5. **列名完全吻合报错**：报错 `column collections.tenant_code does not exist` 与缺失迁移的列名一致，且 `SELECT collections.id, collections.name, ...` 为 ORM 默认列清单查询，佐证「表结构落后于 ORM 模型」。

> **判定结论**：F-2 = **共享 PG `collections` 历史表缺 `tenant_code` 列 + OpenRAG 缺 PG 正向幂等迁移执行路径**；属**真实代码 / 迁移缺陷**（责任在 OpenRAG 仓）。

### 3.3 修复动作

> 责任方：**OpenRAG 仓**。须在 OpenRAG **既有迁移机制内**（`migrations.py` 幂等迁移器，非引入 alembic）以**正式迁移**落地。

1. **新增 PG 正向迁移执行体**（建议置于 `src\openrag\storage\migrations.py`，与 SQLite 入口同构、幂等可重放）：
   - 落列：`ALTER TABLE collections ADD COLUMN IF NOT EXISTS tenant_code VARCHAR(64) NOT NULL DEFAULT 'default';`（`documents` / `chunks` 同构，对齐 ORM `postgres.py` L76 / L112 / L148）；
   - 存量回填：`collections` 按 `metadata` 推导（复用 `_derive_tenant_from_metadata`，键集 `METADATA_TENANT_KEYS`），不可推导行落 `BACKFILL_RESERVED_TENANT_CODE`（对齐 SQLite 口径 `migrations.py` L149~L192）；`documents` / `chunks` 从所属 `collections` 继承；
   - 索引：`CREATE INDEX IF NOT EXISTS idx_collections_tenant ON collections (tenant_code);`（`idx_documents_tenant` / `idx_chunks_tenant` 同构，对齐 L86~L88 / L124 / L159）；
   - 复合唯一：复用 `plan_composite_unique_postgres()`（**L432~L443**）——`DROP INDEX IF EXISTS uq_collections_tenant_name` + `CREATE UNIQUE INDEX IF NOT EXISTS uq_collections_tenant_name ON collections (tenant_code, name);`（**与 K10 / B2 定案口径一致**：collection 唯一升级为 `(tenant_code, name)` 复合唯一）。
2. **接入执行链路（关键，否则仍不落列）**：在 `PostgresStore.initialize()`（`postgres.py` **L279~L306**）`create_all` 之后调用该 PG 迁移；或以迁移标记位（对齐 SQLite 的 `storage_migration_log` 语义，L24~L25 / L79~L106）保证幂等；另可在 `scripts\tenant_backfill_report.py` 放开 PG 分支（现 L47~L49 直接拒绝 PG）。
3. **注意事项**：
   - 迁移**幂等**（`IF NOT EXISTS` / 标记位），可重放；**仅限 `collections` / `documents` / `chunks` 三表**的租户列迁移，**不得对共享 PG 做其他破坏性变更**；
   - 迁移前建议先跑同名冲突预检 `report_duplicate_name_conflicts_sqlite`（PG 侧对应检出）避免建唯一索引失败；
   - 口令 / 密钥不入库、不入报告；迁移命令走参数化 / 幂等 DDL。

### 3.4 验证方式

- **重跑用例 ID（5 例，期望 PASS）**：`S1-1`、`S3-1`、`S3-2`、`S3-3`、`S6-1`。
- **期望结果**：
  - `S1-1`：OpenRAG 无 key → 401；正确 `X-API-Key`（键名 `OPENRAG_API_SERVICE_API_KEY`，值脱敏）→ 200；
  - `S3-1`：集合创建 / 列表 `2xx`（id 与 name 关联），检索命中（score / 元数据正确）；
  - `S3-2`：文本入库 → `status=PENDING` → 轮询 `GET documents/{id}` → `COMPLETED`；
  - `S3-3`：入库 `COMPLETED` 后 retrieve 命中新文本片段；
  - `S6-1`：经网关 `rag-proxy .../query/retrieve` `2xx`（含 `X-API-Key` 与**域过滤**生效）。
- **命令模板**（PowerShell）：
  ```powershell
  # OpenRAG 迁移落地后，跑既有回归（OpenRAG 仓内）
  python -m pytest tests -q

  # 重跑 collections 全链（S3-1/S3-2/S3-3）
  curl.exe -s -H "X-API-Key: <OPENRAG_API_SERVICE_API_KEY>" -H "Content-Type: application/json" `
    'http://127.0.0.1:8010/api/v1/collections'

  # 经网关（S6-1）
  curl.exe -s -X POST -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" `
    -d '{\"query\":\"ping\",\"top_k\":5}' `
    'http://127.0.0.1:8000/api/v1/rag-proxy/collections/<cid>/query/retrieve'
  ```
  结果归档至 `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}`；OpenRAG 侧回归留证于 OpenRAG 仓证据目录。

### 3.5 回填位置

| 回填位 | 具体位置 |
|--------|---------|
| 各仓 JT 台账 / 任务卡 | OpenRAG 仓 JT 台账；`OpenBase-数据隔离实现任务卡-v1.0.0.md` **K10（OpenRAG 强制过滤骨架）** / K02(RG) 行状态 |
| 执行单 §2/§3 | 《OpenBase-S7-沙箱外执行单-v1.0.5》**§2.5** / **§3.5** |
| 测试报告 §2.2 | 《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0》**§2.2**（S7-T6-2 行；并关联 S7-T4 / S7-T6-4 真实面） |
| 冒烟证据 | `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}` |
| 环境检查报告 | 《OpenBase-S7-联调窗口环境检查报告-v1.0.0》（内部 v1.0.2）**§2.6 F-2** 行、`env-check.json` `pending_items[ENV-OPENRAG-SCHEMA]` |

### 3.6 风险与边界

- **仅允许** `collections` / `documents` / `chunks` 的 `tenant_code` 列迁移；**禁止对公共 PG 库做其他破坏性变更**（不得删表 / 改主键 / 全表重写三表以外对象）；
- 迁移须在 **OpenRAG 仓内以正式迁移落地**（迁移器 + 启动 / 部署接入），不得由 OpenBase 侧直连改库绕过；
- **OpenRAG 仓禁 `git add repository`**（禁把 `repository/` 目录纳入提交面）；
- 迁移前做同名冲突预检，迁移后须全量回归（`python -m pytest tests`）；**回归失败即停**；
- 与 K10 / B2 定案口径一致：`(tenant_code, name)` 复合唯一、域过滤 fail-closed；不得为过测试弱化域过滤断言。

---

## §4 F-3 详单（`TRUSTED_PROXY_SOURCES` 取值 `llm-proxy` 与 OpenBase 注入 `openbase-llm-proxy` 不一致）

### 4.1 现象与证据

证据文件：`doc/test/evidence/s7/smoke/smoke-summary.json` 与 `s0-s6-cases.json`。

| 用例 ID | 请求（脱敏） | 状态 | 判定 | 证据摘要（脱敏） |
|:---:|------|:---:|:---:|------|
| S0-4 | `POST http://127.0.0.1:8001/openllm/v1/chat`，头 `X-Proxy-Source: openbase-llm-proxy` | `null` | **FAIL** | 实测对比：`"openbase-llm-proxy": {"delegated":null,"effective":null,"principal":null,"request_id":"req-5e06b84c1cd3","proxy_chain":[],"proxy_source":null}`；`"llm-proxy": {"effective":{"role":"admin","subject_id":"smoke_ext_user","tenant_code":"smoke-ext-tenant","subject_type":"user"},"principal":{...,"auth_method":"***MASKED..."}}` |
| S5-3 | `GET http://127.0.0.1:8001/api/v1/audit-logs` | 200 | **FAIL** | 同上：`openbase-llm-proxy` → `identity.principal=null` / `proxy_source=null`；仅 `llm-proxy` 取值被采纳。伪造头在非受信源下 `principal=null`（不落库） |

> `reason`（原文口径）：OpenLLM `TRUSTED_PROXY_SOURCES=llm-proxy`，不含 OpenBase 注入值 `openbase-llm-proxy`（行为实测：前者 `proxy_source=null`，后者采纳）。对应 `env-check.json` `pending_items[id=ENV-OPENLLM-TRUSTED-SOURCE]`（owner=OpenLLM 子系统仓）。

### 4.2 根因判定

**两侧取值不一致**，实测证据与只读配置逐项对照：

| 侧 | 位置 | 键 / 常量 | 实际取值 |
|----|------|-----------|----------|
| **OpenLLM（运行态）** | `D:\Trae CN\myproject\Dev\OpenLLM\backend\.env` **L28** | `TRUSTED_PROXY_SOURCES` | `llm-proxy`（**实测生效值**，与 OpenBase 注入值不一致） |
| OpenLLM（代码默认） | `backend\app\core\config.py` **L43~L46** | `TRUSTED_PROXY_SOURCES` default | `openbase-llm-proxy` |
| OpenLLM（模板） | `backend\.env.example` **L29** | `TRUSTED_PROXY_SOURCES` | `openbase-llm-proxy` |
| **OpenBase（注入方）** | `openbase\modules\protocol_headers\constants.py` **L88** | `PROXY_SOURCE_LLM` | `openbase-llm-proxy` |
| OpenBase（llm-proxy 出口） | `openbase\modules\llm_proxy\__init__.py` **L67~L68** | 读出站头 | 注入 `X-Proxy-Source: openbase-llm-proxy` |
| 规范（单一事实源） | `doc\design\OpenBase-协议头规范-v1.0.md` **§8 L147~L152** | `PROXY_SOURCE_LLM` | `openbase-llm-proxy`（「值不变，下游白名单零迁移」） |

> **判定结论**：F-3 = **运行态 `.env` 将白名单覆盖为 `llm-proxy`，与规范 / 代码默认 / OpenBase 注入值 `openbase-llm-proxy` 不一致** → OpenLLM 判定 `openbase-llm-proxy` 为非受信来源 → `identity.proxy_source=null`、审计外部身份不采纳（M3 不成立）。

### 4.3 修复动作

> 责任方：**OpenLLM 仓**（白名单取值对齐）；OpenBase 提供协议头单一事实源对标（无需改注入值）。

1. 将 `D:\Trae CN\myproject\Dev\OpenLLM\backend\.env` **L28** `TRUSTED_PROXY_SOURCES` 由 `llm-proxy` 修改为 **`openbase-llm-proxy`**（对齐 `config.py` L43~L46 代码默认、`.env.example` L29、协议头规范 v1.0 §8）。
   - 若需保留既有来源可**逗号分隔追加**：`TRUSTED_PROXY_SOURCES=openbase-llm-proxy,<其他来源>`（对齐白名单「可覆盖追加来源」语义，`config.py` L45）。
2. **统一来源常量口径**：以《OpenBase-协议头规范-v1.0》§8 来源标识常量表为准（`protocol_headers/constants.py` 为单一发布面），两侧不得各自定义同义异值。
3. **回归 OpenLLM 既有用例**：K09 / K15（`OpenBase-数据隔离实现任务卡-v1.0.0.md` **K09 L173**「编排出站身份透传」、**K15 L225**「REAL_* 兜底收口」；对应 OpenLLM 单测 `backend\tests\unit\test_external_identity.py`、`test_s4_t2_identity_base.py`、`test_s4_t3_outbound_headers.py`、`test_s4_t7_channel_preference.py`）。
4. **注意事项**：
   - 仅**白名单取值对齐**，**不得改动身份透传业务逻辑，不得放宽伪造头拦截**（非受信来源 `principal` 仍应 `null`）；
   - `.env` 不入库；密钥 / 口令零进入提交面。

### 4.4 验证方式

- **重跑用例 ID（2 例，期望 PASS）**：`S0-4`、`S5-3`。
- **期望结果**：
  - `S0-4`：带 `X-Proxy-Source: openbase-llm-proxy`（+ 四维身份头）时，`identity.proxy_source=openbase-llm-proxy`、`identity.principal/effective` 非空（采纳）；
  - `S5-3`：`GET /api/v1/audit-logs` 审计 `detail.identity` **六键**（`subject_id` / `subject_type` / `tenant_code` / `role` / `auth_method` / `proxy_source`）齐备，且 `external_user_id` / `external_org_id` 非空；伪造 JWT / 非受信来源头**不落库**。
- **命令模板**（PowerShell）：
  ```powershell
  # S0-4 可信源生效初探（expected: proxy_source=openbase-llm-proxy）
  curl.exe -s -X POST -H "X-Proxy-Source: openbase-llm-proxy" -H "X-User-ID: <uid>" `
    -H "X-Tenant-ID: <tenant>" -H "Content-Type: application/json" `
    -d '{\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}' `
    'http://127.0.0.1:8001/openllm/v1/chat'

  # S5-3 审计核对
  curl.exe -s 'http://127.0.0.1:8001/api/v1/audit-logs'

  # OpenLLM 既有 K09/K15 回归
  python -m pytest tests/unit/test_external_identity.py tests/unit/test_s4_t2_identity_base.py tests/unit/test_s4_t3_outbound_headers.py -q
  ```
  结果归档至 `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}`。

### 4.5 回填位置

| 回填位 | 具体位置 |
|--------|---------|
| 各仓 JT 台账 / 任务卡 | OpenLLM 仓 JT 台账；`OpenBase-数据隔离实现任务卡-v1.0.0.md` **K09** / K15 / K02(LL) 行状态 |
| 执行单 §2/§3 | 《OpenBase-S7-沙箱外执行单-v1.0.5》**§2.5** / **§3.5** |
| 测试报告 §2.2 | 《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0》**§2.2**（S7-T6-2 行；并关联 S7-T6-1 RA-06 M3） |
| 冒烟证据 | `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}` |
| 环境检查报告 | 《OpenBase-S7-联调窗口环境检查报告-v1.0.0》（内部 v1.0.2）**§2.6 F-3** 行、`env-check.json` `pending_items[ENV-OPENLLM-TRUSTED-SOURCE]` |

### 4.6 风险与边界

- 仅**白名单取值对齐**；不得降低 M3 信任校验强度，不得使非受信来源身份头落库；
- 若选择「统一两侧取值」而非改白名单，须以协议头规范 v1.0 §8 单一事实源为准，并同步评估 OpenBase 其余出口常量一致性；
- 回归 K09 / K15 若失败即停，不得绕过；
- 密钥 / 口令零进入提交面。

---

## §5 闭环检查清单

> 责任方逐缺陷填写；`已修复` / `已重跑` / `已回填` / `OpenBase 复核` 四栏以 `☐` → `☑` 勾选并附责任人 / 日期。**任一栏未完成不得判定缺陷关闭**。

### 5.1 F-1（OpenLLM 上游 Ollama + 三真实开关）

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已修复（启动上游 / 改地址 + 置 `OPENLLM_OPENMEMORY_REAL=true` / `OPENLLM_OPENRAG_REAL=true`，日志 `contract=real`） | ☐ | | | |
| 已重跑（S0-1/S1-2/S2-4/S3-4/S5-1/S5-2/S5-4/S5-5 全 PASS） | ☐ | | | |
| 已回填（执行单 §2.5/§3.5、测试报告 §2.2、`smoke-summary.json`） | ☐ | | | |
| OpenBase 复核（§7） | ☐ | | | |

### 5.2 F-2（OpenRAG `collections.tenant_code` 迁移）

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已修复（OpenRAG 仓内 PG 正向幂等迁移 + 启动 / 部署接入 + 既有回归） | ☐ | | | |
| 已重跑（S1-1/S3-1/S3-2/S3-3/S6-1 全 PASS，含 X-API-Key 与域过滤） | ☐ | | | |
| 已回填（执行单 §2.5/§3.5、测试报告 §2.2、`smoke-summary.json`） | ☐ | | | |
| OpenBase 复核（§7） | ☐ | | | |

### 5.3 F-3（`TRUSTED_PROXY_SOURCES` 白名单对齐）

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已修复（`backend\.env` L28 改为 `openbase-llm-proxy`；K09/K15 回归） | ☐ | | | |
| 已重跑（S0-4/S5-3 全 PASS，`proxy_source=openbase-llm-proxy` 且审计六键 + external 身份） | ☐ | | | |
| 已回填（执行单 §2.5/§3.5、测试报告 §2.2、`smoke-summary.json`） | ☐ | | | |
| OpenBase 复核（§7） | ☐ | | | |

### 5.4 F-5（OpenLLM K07 端点-过滤矩阵全量补填：工作树完成/待提交）

> 说明：F-5 非冒烟 S0~S6 阻塞项（阻塞用例数 0），属 **K07 矩阵治理**（S7-T6-4）；此处按同口径登记闭环状态。**已修复（工作树）→ 待提交**。

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已修复（OpenLLM 仓工作树全量补填 5 文件：`backend\scripts\k07_endpoint_matrix.py`、`backend\scripts\k07_isolation_registry.py`（354 键）、`backend\tests\unit\test_isolation_matrix_endpoints.py`（新增 759 条）、`doc\design\OpenLLM-K07-端点过滤矩阵填报-v1.1.0.md`（354 行主表）、`...v1.1.0.matrix.json`） | ☑ | OpenLLM 仓（工作树） | 2026-09-11 | 矩阵 354 行 = 真实底单 351 操作 + 文档面合成 3；业务面覆盖 349 + A 直连豁免 5；**缺口 344→0** |
| 已重跑（门禁 `--check`：`total=351 covered=349 exempt=2 / gaps=0 uncovered=0 exemption_without_approval=0`，**exit 0**；隔离用例 `pytest tests\unit\test_isolation_matrix_endpoints.py tests\unit\test_s4_t11_k07_matrix.py ...` → **767 passed**；ruff（改动 3 个 py）All checks passed） | ☑ | OpenLLM 仓（工作树） | 2026-09-11 | 独立复核复跑一致（OpenBase 侧脚本解析 + 命令复跑） |
| 已回填（`k07-finalize.json` `per_system[openllm]`：rows=354/covered=349/exempt=5/gap=0/uncovered=0/exemption_valid=5/status=FILLED(worktree,uncommitted)、`K07-GAP-OPENLLM`→RESOLVED；`gate-aggregate.json` §K07-SYS-1 `status=PARTIAL`（保留历史字段）；测试报告 §2/§3/§7、总收官报告 §2/§3/§5.3/§6/§7、执行单 §3.4/§3.5/§6） | ☑ | OpenBase 侧 | 2026-09-11 | 子系统仓文件只读（未改动）；仅回填 OpenBase 侧证据与文档 |
| **已提交**（OpenLLM 仓 5 文件 commit + push 完成，三远端同步） | ☑ | OpenLLM 仓 | 2026-09-12 | 提交 **`41af780`**（`docs(k07): OpenLLM 端点过滤矩阵全量补填与隔离用例注册（351 端点/缺口归零）`）；**遗留收口（2026-09-13）**：已生成一键落仓脚本 `openllm-k07-snapshot-commit-push.bat`（包装 `scripts/openllm_k07_snapshot_commit_push.ps1`；源取 K07 证据导出 `doc/test/evidence/s7/gate/k07-openapi/openllm.openapi.json`——`openapi=3.1.0` / `paths=278` / `operations=351`，与 K07 台账一致；脚本含 **351 操作校验 + 提交面守卫（仅 1 文件）+ 三远端 `ls-remote` 校验**，`-DryRun` 实跑通过）。**受限沙箱内 OpenLLM 仓全仓只读**（`backend/data/**` 与 `.git` 均被拦截，实测无残留：目标文件未生成、`index.lock` 未产生、暂存区为空）→ **已于 2026-09-13 完成落仓并三远端同步**（提交 **`e2683ce`**（`chore(k07): 落仓 OpenLLM /openapi.json 快照（351 操作，K07 无参 CI 依赖）`）；sha256 `2CE7DF70EF22B94B` **三方一致**（HEAD blob = 工作树 = 源快照，888760 bytes）；origin / backup / github `ls-remote` 均 = `e2683ce`；重跑落仓脚本会因「暂存面为空」被提交面守卫拦下（exit 2）= **无东西可提交时的正确行为**）。 |
| OpenBase 复核（§7 第 6 项） | ☑ | OpenBase 侧 | 2026-09-11 | 独立复核通过（见批量回填记录） |

### 5.5 F-6（OpenMemory K07 端点-过滤矩阵 8 条缺口补填：工作树完成/待提交）

> 说明：F-6 非冒烟 S0~S6 阻塞项（阻塞用例数 0），属 **K07 矩阵治理**（S7-T6-4）；此处按同口径登记闭环状态。**已修复（工作树）→ 待提交**。

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已修复（OpenMemory 仓工作树 4 文件：`doc\design\OpenMemory-K07-端点过滤矩阵填报-v1.0.0.md`（内部 v1.1.0，40 行主表）、`scripts\api_baseline.json`（32→40）、`scripts\k07_endpoint_matrix.py`（豁免判定对齐 `/health*` 前缀）、`tests\unit\test_isolation_matrix_endpoints.py`（新增，隔离注册 IS-OM-R26~R31）） | ☑ | OpenMemory 仓（工作树） | 2026-09-12 | 矩阵 32→40 行 = 真实底单 36 操作 + 文档面合成 4；覆盖 25→31 + A 直连豁免 7→9；**缺口 8→0**；2 健康探针豁免（ticket=T-健康直连 / 审批人=S2-PMO / 复核 2026-09-11 / 到期 2026-12-31），6 业务面挂隔离用例 |
| 已重跑（门禁 `--verify --openapi <真实导出>`：`missing_rows=[] uncovered_business=[] exemption_errors=[] isolation_missing=[] total_rows=40 business_rows=31 exempt_rows=9`，**exit 0**；隔离用例 `pytest tests\unit\test_isolation_matrix_endpoints.py` → **81 passed**；K07/identity 组 25 文件 → **372 passed**；ruff `scripts tests src` → All checks passed） | ☑ | OpenMemory 仓（工作树） | 2026-09-12 | 独立复核复跑一致（OpenBase 侧脚本解析 + 命令复跑） |
| 已回填（`k07-finalize.json` `per_system[openmemory]`：rows=40/covered=31/exempt=9/gap=0/uncovered=0/exemption_valid=9/status=FILLED(worktree,uncommitted)、`summary.gap_total 8→0`、`K07-GAP-OPENMEMORY`→RESOLVED；`gate-aggregate.json` §K07-SYS-1 同步；测试报告 §2/§3、总收官报告 §2/§3/§5.3/§6/§7、执行单 §3.4/§3.5/§6） | ☑ | OpenBase 侧 | 2026-09-12 | 子系统仓文件只读（未改动功能语义代码）；仅回填 OpenBase 侧证据与文档 |
| **已提交**（OpenMemory 仓 4 文件 commit + push 完成，三远端同步） | ☑ | OpenMemory 仓 | 2026-09-12 | 提交 **`0a6f351`**（`docs(k07): OpenMemory 端点过滤矩阵 8 条缺口补填与隔离用例注册（缺口归零）`）；敏感文件零进入（`.env*` / `scripts/evidence_v680_*.txt` / `storage/images/**` / `doc/test/_temp_test.txt` 不提交） |
| OpenBase 复核（§7 第 7 项） | ☑ | OpenBase 侧 | 2026-09-12 | 独立复核通过（见 §7 第 7 项） |
### 5.6 K07/SYS-1 端到端闭环（v1.0.8：F-5/F-6/DPS 豁免续期三项）

> 说明：本节为 K07 矩阵治理项（S7-T6-4）的端到端闭环清单，与 F-1~F-3 冒烟阻塞项同口径登记。

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已修复（OpenLLM 全量补填 / OpenMemory 8 条补填 / DPS 35 条豁免续期） | ☑ | OpenLLM / OpenMemory / DPS 仓 | 2026-09-12 | OpenLLM 矩阵 354 行（覆盖 349 / 豁免 5）；OpenMemory 矩阵 40 行（覆盖 31 / 豁免 9）；DPS 169 行（覆盖 134 / 豁免 35 续期至 2026-12-31） |
| 已重跑（三仓 K07 门禁 exit 0 + 隔离用例 767 / 81 passed + DPS 门禁复跑 exit 0） | ☑ | 各子系统仓 | 2026-09-12 | OpenLLM `--check` gaps=0/uncovered=0 exit 0；OpenMemory `--verify --openapi` missing_rows=0 exit 0；DPS `--check` gaps=0 exit 0 |
| 已回填（`k07-finalize.json` `status=PARTIAL→PASS`、断言 `S7-T6-4-c` FAIL→PASS、挂起项 DONE；`gate-aggregate.json` §K07-SYS-1 `status=PASS`、`overall=PASS / pass=20 / fail=0 / pending=2`；测试报告 v1.0.12 / 总收官报告 v1.0.8 / 执行单 §3.4/§3.5 同步） | ☑ | OpenBase 侧 | 2026-09-12 | 缺口 0 / 未覆盖 0 / 豁免 59 全有效 |
| OpenBase 复核（§7 第 8 项） | ☑ | OpenBase 侧 | 2026-09-12 | 独立复核复跑一致（`gate_aggregate.py` 实跑 + 各仓门禁复跑 + 证据 JSON 解析） |
> **一键提交脚本（v1.0.9 登记）**：`DPS/dps-k07-commit-push.bat`（包装 `DPS/scripts/dps_k07_exempt_commit_push.ps1`，支持 `-DryRun`）。实跑结论：本执行环境因 `fatal: Unable to create 'D:/Trae CN/myproject/Dev/DPS/.git/index.lock': Permission denied` 中止（`git add` 未成功，无 hash，禁伪造）→ **待可写环境执行**；执行后请将 DPS 提交 hash 回填本单 §1/§5.6 与 `k07-finalize.json`。**v1.0.10 收口（2026-09-13）**：包装 bat 行尾 LF→CRLF 修复后 `-DryRun` 实跑通过；DPS 侧已执行提交 **`b5f5c06`**（3 文件），三远端 `ls-remote` 与本地 HEAD 一致 → hash 已回填本单与 `k07-finalize.json` / `gate-aggregate.json`；**本单待提交项清零**。

### 5.7 F-8（`GET /api/v1/auth/me` 对绑租户主体 500：`MeResponse.tenant_id` 形态不一致）—— v1.0.13 新增

> 说明：F-8 非冒烟 S0~S6 阻塞项（阻塞用例数 0），属 **L3-1 agent key 面读取端点**；由 L2 真实面探针暴露。**已修复（`6bf7832`）**。

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已登记（现象 / 根因 / 证据） | ☑ | OpenBase 侧 | 2026-10-16 | 证据 `doc/test/evidence/manual/mtauth-delegation-l31-20261016-defect.json`（项 E：500）+ 服务日志 pydantic `string_type` |
| 已修复（`me()` 出参归一化为 str；**TDD 先行**：`test_t1_3b_agent_bound_to_tenant_me_returns_200` 先 RED） | ☑ | OpenBase 仓 | 2026-10-16 | 提交 **`6bf7832`**（选项 A，§8.1） |
| 已重跑（探针项 E → **200** 且 `me_id == agent_id`；`tests/test_identity_t1.py` 9 passed） | ☑ | OpenBase 仓 | 2026-10-16 | 证据 `mtauth-delegation-l31-20261016.json`（`overall_pass=true`，E observed=200） |
| 已回填（本单 §1/§5.7/§8.1；`mtauth-delegation-l31-20261016*.json`；`gate-aggregate.json` §RA-06；S7 报告 §4.2） | ☑ | OpenBase 侧 | 2026-10-16 | 见本单 v1.0.14 修订历史 |
| OpenBase 复核（§7 第 9 项） | ☑ | OpenBase 侧 | 2026-10-16 | 独立复跑一致（探针 + 隔离用例 + 分组全量回归） |

### 5.8 F-9（`POST /api/v1/users` 未派生 `tenant_code`：同域委托被误判跨界）—— v1.0.13 新增

> 说明：F-9 非冒烟 S0~S6 阻塞项（阻塞用例数 0），属 **委托域不变式的目标装配口径**；由 L2 真实面探针暴露。**已修复（`6bf7832`）**。

| 检查项 | 是否完成 | 责任人 | 日期 | 备注 |
|--------|:---:|--------|------|------|
| 已登记（现象 / 根因 / 证据） | ☑ | OpenBase 侧 | 2026-10-16 | 探针观测项 O（修复前）：同域用户作目标 → 403 `PERM_DELEGATION_CROSS_TENANT`（对照项 C 同域 agent 目标 → 200）；留档 `mtauth-delegation-l31-20261016-defect.json` |
| 已修复（`create_user` + OIDC JIT `_bind_or_create_user` 补 `tenant_code` 派生；**TDD 先行**：`test_create_user_derives_tenant_code`、`test_jit_create_derives_tenant_code` 先 RED） | ☑ | OpenBase 仓 | 2026-10-16 | 提交 **`6bf7832`**；连带核查：`PUT /users/{id}` 无 `tenant_id` 字段（不可改租户 → 无失同步路径）、`UserOut` 不加字段（契约不变）、存量未派生行**本轮不批量回填**（需幂等脚本 + 证据，另立任务） |
| 已重跑（探针项 O → **200**，探针 `overall_pass=true`；`tests/test_users_admin.py` 7 passed / `tests/test_oidc_binding.py` 6 passed） | ☑ | OpenBase 仓 | 2026-10-16 | 证据 `mtauth-delegation-l31-20261016.json`（O observed.status=200） |
| 已回填（本单 §1/§5.8/§8.2；`mtauth-delegation-l31-20261016*.json`；`gate-aggregate.json` §RA-06；S7 报告 §4.2；派单 §9） | ☑ | OpenBase 侧 | 2026-10-16 | 见本单 v1.0.14 修订历史 |
| OpenBase 复核（§7 第 9 项） | ☑ | OpenBase 侧 | 2026-10-16 | 独立复跑一致（探针 + 隔离用例 + 分组全量回归） |

---

## §6 执行纪律（硬约束）

1. **禁伪造结果**：不得填写假 `PASS` / 假响应码 / 假 `request_id` / 假 hash；未执行项一律保持 `PENDING` 并附 `reason`。
2. **不得停止或重启服务**：全程不得停止 / 重启五服务；`S5-6`（OpenRAG 停服降级）与 T3 主备切换归**受控窗口**，不在本单执行。
3. **不得改公共 PG 结构**：**除 F-2 的 `collections` / `documents` / `chunks` 租户列迁移**外，禁止对共享 PG 做任何破坏性变更；F-2 迁移须在 **OpenRAG 仓内以正式迁移落地**（迁移器 + 启动 / 部署接入），不得由 OpenBase 侧直连改库绕过。
4. **OpenRAG 仓禁 `git add repository`**：`repository/` 目录不得纳入提交面。
5. **敏感文件零进入提交面**：`.env*` / 密钥 / 口令 / 令牌不得入库、不得入报告明文（本单已按脱敏口径处理）。
6. **逐项显式 `git add`，禁 `git add -A`**：提交面须显式指定文件；**`dogfood-output/` 不纳入任何提交面**（对齐设计草案 §5.3/§5.4、放行清单 §0 红线）。
7. **不得改动子系统仓**：本单仅在 OpenBase 仓新建；四仓修复由责任方在各自仓内按单执行，须遵循各仓提交纪律。
8. **回归失败即停**：任一回归失败，停止后续步骤并回溯（不掩盖、不带病通过）。

---

## §7 完成后的 OpenBase 侧复核动作

责任方三缺陷修复并回填后，由 OpenBase 侧按序执行复核（复核通过方可关闭缺陷）：

1. **重跑 S0~S6 相关段**：按《OpenBase-真实联调冒烟清单-v1.1.0》§3 逐条真实 HTTP，重点覆盖 F-1（S0-1/S1-2/S2-4/S3-4/S5-1/S5-2/S5-4/S5-5）、F-2（S1-1/S3-1/S3-2/S3-3/S6-1）、F-3（S0-4/S5-3）；结果归档 `doc/test/evidence/s7/smoke/{smoke-summary.json,s0-s6-cases.json}`。
2. **门禁聚合复跑**：`python 'D:\Trae CN\myproject\Dev\OpenBase\scripts\gate_aggregate.py'`（含 `--face real --only SMOKE-S0-S6`），更新 `doc/test/evidence/s7/gate/gate-aggregate.json`。
3. **更新测试报告断言状态**：《OpenBase-S7-全域门禁与总收官-测试报告-v1.0.0》**§2.2** 逐行由 `PENDING` → `PASS` / `FAIL`（S7-T6-2 行及关联 S7-T4 / S7-T6-1 / S7-T6-4），并同步 §3 段门禁六项。
4. **段门禁六项复评**：① RA-06 ② 冒烟 S0-S6 ③ 对齐清单关闭 ④ 三原则总验证 ⑤ 跨仓会签 ⑥ 24 卡 / JT 回写——逐项复核结论，回填总收官报告 §2 六项聚合自检表。
5. **回填下游文档**：更新《OpenBase-S7-联调窗口环境检查报告-v1.0.0》§2.6 三缺陷行状态、`env-check.json` `pending_items` 对应项；按文档版本管理规范同步版本与修订历史。
6. **F-5（OpenLLM K07 全量补填）复核（v1.0.1 新增）**：OpenBase 侧已独立复核 OpenLLM 工作树补填——解析真实底单 openapi（278 路径 / 351 操作）、解析 `...v1.1.0.matrix.json`（354 行 / 覆盖 349 / 豁免 5）、差集缺口 0（额外 3 为文档面合成）、豁免到期 2026-12-31 有效、复跑门禁 `--check`（exit 0）、隔离用例 767 passed、ruff 通过；回填 `k07-finalize.json`（`per_system[openllm]` + `gate_verdict=PARTIAL`）与 `gate-aggregate.json` §K07-SYS-1。**待提交项**：OpenLLM 仓须在可写环境提交 5 文件（沙箱拒写 `.git/objects`，无 hash，禁伪造）；提交后核对 `git log -1 --stat` 与门禁复跑结果。
7. **F-6（OpenMemory K07 8 条缺口补填）复核（v1.0.2 新增）**：OpenBase 侧已独立复核 OpenMemory 工作树补填——解析真实底单 openapi（30 路径 / 36 操作）、解析 `scripts/api_baseline.json`（40 条，排序保持）、解析矩阵主表（40 行 / 覆盖 31 / 豁免 9）、差集缺口 0（额外 4 为文档面合成 `/docs`、`/docs/oauth2-redirect`、`/openapi.json`、`/redoc`）、9 条豁免到期 2026-12-31 有效且有审批、复跑门禁 `--verify --openapi`（`missing_rows=0`，exit 0）、隔离用例 81 passed（K07/identity 组 372 passed）、ruff 通过；回填 `k07-finalize.json`（`per_system[openmemory]` + `summary.gap_total 8→0` + `K07-GAP-OPENMEMORY`→RESOLVED）与 `gate-aggregate.json` §K07-SYS-1。**待提交项**：OpenMemory 仓须在可写环境提交 4 文件（沙箱拒写 `.git/objects`，无 hash，禁伪造）；提交后核对 `git log -1 --stat` 与门禁复跑结果。
8. **K07 门禁收口复核（v1.0.8 新增）**：OpenBase 侧已独立复核——① 门禁聚合实跑 `python scripts/gate_aggregate.py` → `overall=PASS exit=0 pass=20 fail=0 pending=2`；② K07 真实终验 `k07-finalize.json` 三项判定全部满足（缺口 0 / 未覆盖 0 / 豁免 59 全有效）→ `gate_verdict=PASS`；③ 两仓补填提交 hash 实证（OpenLLM `41af780` / OpenMemory `0a6f351`，三远端同步）；④ DPS 35 条豁免续期至 2026-12-31 且门禁复跑 exit 0；⑤ 回填 `k07-finalize.json`（`status=PASS`、断言 `S7-T6-4-c` FAIL→PASS、挂起项 DONE）与 `gate-aggregate.json` §K07-SYS-1（`status=PASS`）；⑥ 下游文档同步（测试报告 v1.0.12 / 总收官报告 v1.0.8 / 本单 v1.0.8 / 执行单 §3.4/§3.5）。**待提交项**：DPS 仓 K07 填报文档改动（一键提交脚本 `DPS/dps-k07-commit-push.bat`（包装 `DPS/scripts/dps_k07_exempt_commit_push.ps1`，支持 `-DryRun`） 已就绪（`-DryRun` 通过），实跑因环境写入受限中止，待可写环境执行并回填 DPS hash）。**收口（2026-09-13）**：DPS 侧已执行提交 **`b5f5c06`**（3 文件，三远端同步）→ **待提交项：无**。

9. **L2 真实面探针缺陷复核（v1.0.13 新增，F-8 / F-9）**：责任方修复后由 OpenBase 侧按下述口径复核——① **F-8**：以绑租户（`tenant_id` 非空）的 agent 密钥调 `GET /api/v1/auth/me` → 期望 **200** 且 `id == agent_id`（当前实测 **500**，pydantic `string_type`）；② **F-9**：以 `POST /api/v1/users` 建同域账号作委托目标，agent 同域委托 → 期望 **200**（当前实测 **403 `PERM_DELEGATION_CROSS_TENANT`**）；③ 两项修复后重跑探针（`doc/tmp/run_l2_probe.ps1`）→ 期望 `overall_pass=true`（`O_user_target_same_domain_observed.status=200`）；④ 回归 `tests/test_identity_t4.py`（委托域不变式）+ `tests/test_users_admin.py` / `tests/test_identity_t3.py`（`me` 端点与吊销面）全绿；⑤ 回填证据 `doc/test/evidence/manual/mtauth-delegation-l31-<日期>.json`、本单 §1/§5.7/§5.8、`gate-aggregate.json` §RA-06、S7 报告 §4.2。

> **复核结论（2026-10-16，v1.0.14）**：**F-8 / F-9 复核通过**。① **F-8**：`tests/test_identity_t1.py::test_t1_3b_agent_bound_to_tenant_me_returns_200`（9 passed）隔离全绿，探针项 E 由 500 → **200**（`me_id == agent_id`）；② **F-9**：`tests/test_users_admin.py::test_create_user_derives_tenant_code`（7 passed）与 `tests/test_oidc_binding.py::test_jit_create_derives_tenant_code`（6 passed）隔离全绿，探针项 O 由 403 → **200**，探针 `overall_pass=true`；③ 回归：`ruff` 全清、**仓内分组全量回归 `passed=1118 / failed=0 / skipped=4`**（余 F-10/F-11 预存项见 §9，非本轮引入）；④ 证据留档：修复前 `mtauth-delegation-l31-20261016-defect.json` / 修复后 `mtauth-delegation-l31-20261016.json`。判定：**F-8 / F-9 关闭**（提交 `6bf7832`，本单待提交项清零）。

---

## §8 新增缺陷详单（F-8 / F-9，L2 真实面探针，2026-10-16 登记）

> **来源**：L2「RA-06 余项真实面」原子窗口探针（`doc/tmp/run_l2_probe.ps1` + `doc/tmp/l2_delegation_probe.py`）；证据 `doc/test/evidence/manual/mtauth-delegation-l31-20261016.json`。
> **同窗口已达成的正向结论（不受本两项缺陷影响）**：委托跨界不变式**真实面达成**——B 跨域委托 **403 `PERM_DELEGATION_CROSS_TENANT`** / C 同域委托 **200**（反例自证配对）；A user 挂委托 → **403 `PERM_FORBIDDEN`**；D agent 发放 **200**；F agent key 越权 → **403**；G1/G2 吊销即时 **200 → 401**。

### 8.1 F-8 详单（`GET /api/v1/auth/me` 对「绑租户的主体」返回 500）

**现象与证据**

| 用例 | 请求 | 状态 | 判定 | 证据摘要 |
|:---:|------|:---:|:---:|------|
| E | `GET http://127.0.0.1:8000/api/v1/auth/me`（`Authorization: Bearer sk-agent-*`，该 agent `tenant_id=1`） | **500** | **FAIL** | 服务日志：`pydantic_core._pydantic_core.ValidationError: 1 validation error for MeResponse / tenant_id / Input should be a valid string [type=string_type, input_value=1, input_type=int]`（`openbase/modules/auth/__init__.py:421` `return MeResponse(`） |
| 对照（首轮探针，agent 未绑租户 `tenant_id=None`） | 同上 | 200 | PASS | `me_id=115 == agent_id`（未绑租户时不触发，反向印证根因） |

**根因判定**

1. `MeResponse.tenant_id` 声明为 `str | None`（`openbase/modules/auth/__init__.py:78`）。
2. `get_current_user` 的两条主体通道取值形态不一致：JWT 通道 `user_context["tenant_id"] = payload.get("tenant_id")`（签发时以 **str** 写入，`create_access_token(... tenant_id=str(...))`）→ 与模型一致；**agent 密钥通道** `resolve_agent_principal` 返回 `"tenant_id": user.tenant_id`（**DB 的 int**，`openbase/modules/identity/agent_keys.py:171`）→ 与模型**不一致** → `me()` 构造 `MeResponse` 时 pydantic v2 拒绝 int→str 隐式转换 → 未捕获 → **500**。
3. 触发条件精确：**主体绑租户（`tenant_id` 非空）** 且经 agent 密钥通道访问 `/auth/me`；未绑租户（`None`）不触发。

**修复动作（建议，待裁定批准后实施）**

- **选项 A（最小改动，推荐）**：`me()` 端点归一化为字符串——`tenant_id=str(user.get("tenant_id")) if user.get("tenant_id") is not None else None`（单一出参口径，不触碰模型）。
- **选项 B**：`MeResponse.tenant_id` 放宽为 `int | str | None`（沿用 `MeResponse.id` 已有的 `int | str` 先例，`openbase/modules/auth/__init__.py:76`）。
- **不采纳**：改动 agent 通道返回 int（会与 JWT 通道口径背离，且影响面更大）。
- 纪律：**TDD 先行**（新增/复用「绑租户 agent 调 `/auth/me` → 200」用例，RED → GREEN）；新增代码覆盖率 ≥90%；`ruff` 0 错误。

**验证方式**

- 重跑探针项 **E** → 期望 **200** 且 `me_id == agent_id`；
- 定向回归：`python -m pytest tests/test_identity_t3.py tests/test_users_admin.py -q`（`me` 端点与主体面）+ 全量回归不劣于基线。

**回填位置**：本单 §1/§5.7；`doc/test/evidence/manual/mtauth-delegation-l31-<日期>.json`；`gate-aggregate.json` §RA-06（`delegation_cross_tenant_403` 附注）；S7 报告 §4.2。

**风险与边界**：仅端点出参口径对齐，**不得**放宽 `get_current_user` 的主体验证/吊销语义；不得改动 `MeResponse.id` 既有行为。

### 8.2 F-9 详单（`POST /api/v1/users` 未派生 `tenant_code` → 同域委托被误判跨界）

**现象与证据**

| 用例 | 请求 | 状态 | 判定 | 证据摘要 |
|:---:|------|:---:|:---:|------|
| O（如实观测项，不入门禁） | `POST /api/v1/users`（`tenant_id=1`）建同域账号 → 以其为委托目标，agent **同域**委托 | **403** | **观测**（期望同域放行 200） | `{"status":403,"code":"PERM_DELEGATION_CROSS_TENANT"}` |
| C（对照，目标为同域 **agent**） | 同域委托目标改用 agent（该路径**会**派生 `tenant_code`） | **200** | PASS | 反例自证：同域放行成立 ⇒ O 的 403 源于目标行域为空 |

**根因判定**

1. 委托域不变式（`openbase/modules/identity/delegation.py:310`）：`if (target.tenant_code or "") != delegated_tenant:` → 目标行 `tenant_code` 必须等于 claim 域；否则判 `PERM_DELEGATION_CROSS_TENANT`。
2. `create_agent_subject` 显式派生：`tenant_code = await _resolve_tenant_code(session, tenant_id)`（`openbase/modules/identity/agents.py:67`）。
3. `create_user` **未派生**：`User(... tenant_id=payload.tenant_id)`，**无 `tenant_code` 赋值**（`openbase/modules/users/__init__.py:176-184`）→ 该类账号 `tenant_code` 为空 → 作委托目标时域比对必失败 → **合法同域委托被误判跨界（fail-closed 方向的假阳性）**。

**修复动作（建议，待裁定批准后实施）**

- 在 `create_user` 中补 `tenant_code` 派生，与 agents 路径口径统一：`tenant_code = await resolve_tenant_code(payload.tenant_id, session)`（`openbase/modules/auth.resolve_tenant_code` 为共享函数，agents 路径即复用该函数）。
- **连带核查**：`PUT /api/v1/users/{id}`（`tenant_id` 变更时是否需同步 `tenant_code`）、`UserOut` 是否需回显 `tenant_code`、存量未派生行是否需一次性回填（建议以幂等脚本 + 证据登记，避免直连改库）。
- 纪律：**TDD 先行**（新增「users 路径建的账号，同域委托 → 200」用例，RED → GREEN）；覆盖率 ≥90%；`ruff` 0 错误。

**验证方式**

- 重跑探针项 **O** → 期望 **200**（探针 `overall_pass=true`）；
- 定向回归：`python -m pytest tests/test_identity_t4.py tests/test_users_admin.py -q`（委托域不变式 + users 面）+ 全量回归不劣于基线。

**回填位置**：本单 §1/§5.8；`doc/test/evidence/manual/mtauth-delegation-l31-<日期>.json`；`gate-aggregate.json` §RA-06（`delegation_cross_tenant_403` 附注）；S7 报告 §4.2；《S7-T6-2 冒烟真实执行-跨仓派单》§9 已知环境适配项（同条）。

**风险与边界**：**不得**放宽委托域不变式（跨界必须继续 403）；修复仅补齐「目标行域装配」口径，**不得**改为「目标域为空时放行」（那会打开跨界旁路）；存量数据回填须幂等且留证。

### 8.3 修复与验证记录（v1.0.14，2026-10-16）

| 项 | 内容 |
|----|------|
| 指令 | 人工指令「按 TDD 修复 F-8 和 F-9」 |
| TDD（RED） | 先加 3 条用例并确认**先失败**：`test_t1_3b_agent_bound_to_tenant_me_returns_200`（pydantic `string_type` 500）、`test_create_user_derives_tenant_code`（users 行无 tenant_code）、`test_jit_create_derives_tenant_code`（OIDC JIT 行无 tenant_code） |
| 实现（GREEN） | ① `openbase/modules/auth/__init__.py::me()` 出参 `tenant_id` 归一为 `str`；② `openbase/modules/users/__init__.py::create_user` 补 `resolve_tenant_code` 派生；③ `openbase/modules/auth/oidc.py::_bind_or_create_user` 补 `tenant_code=tenant.code` |
| 提交 | **`6bf7832`**（8 文件 / +178 −6；含 2 个因本轮文档升版而同步的版本锚点用例 `tests/test_s7_t7_signoff.py` / `tests/test_s7_t8_writeback.py`） |
| 静态检查 | `python -m ruff check openbase tests` → **All checks passed** |
| 定向验证 | 隔离复跑：t1 **9 passed** / users **7 passed** / oidc **6 passed** / tenant_admin **5 passed** / s7_t7 **20 passed** / s7_t8 **19 passed** / s7_docs **6 passed** / s7_t6_gate **16 passed** |
| 全量回归 | `python scripts/run_regression.py`（仓内既定分组子进程隔离）→ **`passed=1118 / failed=0 / skipped=4`**；异常分组仅 F-10/F-11 预存项（见 §9） |
| 真实面复验 | 探针复跑 `doc/tmp/run_l2_probe.ps1` → **`overall_pass=true`**：E（agent key `/auth/me`）**500 → 200**、O（users 路径同域目标委托）**403 → 200**；保存分界证据 `mtauth-delegation-l31-20261016-defect.json`（修复前）/ `mtauth-delegation-l31-20261016.json`（修复后） |
| 连带核查 | `PUT /api/v1/users/{id}` 无 `tenant_id` 字段（不可改租户 → 无 `tenant_code` 失同步路径）；`UserOut` 不加字段（响应契约不变）；**存量未派生行不批量回填**（需幂等脚本 + 证据，另立任务登记） |

---

## §9 预存门禁失败登记（v1.0.14 新增，非本轮引入）

> 来源：2026-10-16 全量回归暴露；已用 **`e2c4f25` 基线 worktree** 复跑同项对比，证明二者**在改动前即失败**。二者均为门禁项（阻塞用例数 0），不阻断业务链路，但**须在段门禁最终通过前关闭**。

### 9.1 F-10 详单（受管编排唯一入口门禁：3 处直接 `Stop-Process`）

**现象与证据**

| 项 | 内容 |
|----|------|
| 门禁 | `tests/test_s7_t1_shr.py::test_s7_t1_4_bypass_scan_zero_hits_and_not_vacuous` |
| 结果 | **1 failed / 14 passed**（隔离复跑一致） |
| 命中 | `scripts/run_smoke_s0_s6.ps1:59`（端口残留清理）、`:123`（收尾停服）；`scripts/verify_mtauth_realface.ps1:237`（收尾停服）——token=`stop-process`、`allowed=false` |
| 基线 | `e2c4f25` worktree 复跑**同样失败** → **预存**（两脚本的 `Stop-Process` 分别由 `7ca4ed9`/`876f50d` 与 `2aafbaa` 引入） |
| 复核命令 | `python scripts/scan_orchestrator_bypass.py`（命中 3 项，exit 1） |

**根因判定**：扫描器 `scripts/scan_orchestrator_bypass.py` 的唯一允许位限定于 `scripts/service-orchestrator.ps1`（且仅 `Stop-Process -Id <pid>` 形态，见 `_is_allowed_hit()`）；上述两脚本在自身进程内直接终止所启子进程（按 PID，非按名/通配）→ 仍计为绕过。

**修复动作（建议，二选一，待裁定）**

- **A（推荐，口径正确）**：两脚本的服务启停改为经受管编排入口——`scripts/service-orchestrator.ps1 -Action start|stop -Only openbase,openllm`（该入口已注入 `.env.shared-infra` 与 DPS/代理映射，具备环境等价性；可用 `-HealthTimeout` 覆盖首健康等待）；自持 PID 的收尾停服随之删除。
- **B**：在扫描器内为「启动方自持 PID 的收尾停服」增设**带票据/审批人/有效期**的豁免位（对齐 `config/identity_exemptions.json` 治理口径），并保留非空化自检以防豁免滥用。

**验证方式**：`python -m pytest tests/test_s7_t1_shr.py -q` → 期望 **15 passed**；`python scripts/scan_orchestrator_bypass.py` → `disallowed=0` / exit 0。

**回填位置**：本单 §1/§9.1；`doc/test/evidence/s7/shr/orchestrator/bypass-scan.json`（重跑刷新）。

**风险与边界**：不得放宽「批量杀」拦截（`-Name` / `/IM` / 通配仍须命中）；改造后必须保持沙箱「同一命令内启动 + 探针」的原子性，避免服务随命令结束被回收。

**修复与验证记录（v1.0.15，2026-10-16，方案 A 采纳）**

| 项 | 内容 |
|----|------|
| 指令 | 人工指令「按方案 A 修复 F-10 并重新跑冒烟验证」 |
| 改动① | `scripts/run_smoke_s0_s6.ps1`：移除本地 `Start-Svc` / `Clear-Listener` / 收尾 `Stop-Process`；生命周期改由 `& scripts/service-orchestrator.ps1 -Action stop|start|stop -Only openbase,openllm -HealthTimeout 240` 驱动；`.env.shared-infra` 仍由脚本前置加载（与编排器注入等价）；ready-gate 保留 |
| 改动② | `scripts/verify_mtauth_realface.ps1`：`-StartServices` 分支移除本地服务表 + `Start-Process` + 收尾 `Stop-Process`；改经同一编排入口对六服务（openbase/openllm/openrag/openmemory/oidc-idp/dps）`stop`→`start`→（末尾）`stop`；移除随之失效的 `$obEnv`/`$DevRoot`/`$started` |
| 改动③ | 两脚本补 **PATH 引导**：编排器以裸命令 `python` 启动服务（`Command='python'`），而沙箱 PATH 无解释器 → 脚本在调用编排器前把已解析解释器目录前置到 `$env:PATH`（首轮实测报错 `The system cannot find the file specified.`，修复后编排器成功创建进程） |
| 改动④ | 两脚本转 **UTF-8 with BOM**，`Parser::ParseFile` 解析错误 **0** |
| 门禁验证① | `python scripts/scan_orchestrator_bypass.py` → `scanned=46 / allowed=1（编排器自身按 PID 停止）/ disallowed=0`，`exit 0`；证据 `doc/test/evidence/s7/shr/orchestrator/bypass-scan.json`（重跑刷新） |
| 门禁验证② | `python -m pytest tests/test_s7_t1_shr.py tests/test_s7_t6_gate.py -q` → **31 passed**（t1_shr 15 + t6_gate 16），`exit 0` |
| 端到端验证 | `.\scripts\run_smoke_s0_s6.ps1`（受管编排启停）→ `total=32 / PASS 25 / FAIL 0 / PENDING 7`（`ready-gate: ready=True (5s)`，`model=qwen2.5:0.5b`），收尾编排日志 `openllm 已停止（PID …）` + `停止完成`，端口 8000/8001 释放；证据 `doc/test/evidence/s7/smoke/smoke-summary-20261016120118.json` |
| 等价性判定 | 与第三轮（`smoke-summary-20261016005540.json`）**逐项一致**（25/0/7），证明方案 A 改造未改变用例语义 |
| 残留说明 | 冒烟证据 `openbase_commit` 记录为 `e131c23`（脚本改动为本轮工作树，提交后随文档一并入库）；F-10「预存」判定不变（`e2c4f25` 基线同样失败） |

### 9.2 F-11 详单（S7 工具骨架门禁 12 项）

**现象与证据**

| 项 | 内容 |
|----|------|
| 门禁 | `tests/test_s7_tools_skeleton.py` |
| 结果 | **12 failed / 14 passed**（隔离复跑一致） |
| 失败族① | 干跑退出码：`verify_l1_1_cascade.ps1` / `drill_l2_1_failover.ps1` / `verify_l3_1_agent.ps1` **期望 2（PENDING）实测 1** |
| 失败族② | 证据文件缺失：`l1_1/cascade-result.json`、`l2_1/failover-drill.json`、`l3_1/agent-e2e.json` → `FileNotFoundError`（经 `test_evidence_schema_valid` / `test_checks_mapped_to_assertions` / `test_no_fake_pass_without_real_environment` 三组参数化各 3 项） |
| 基线 | `e2c4f25` worktree 复跑**同样 12 failed / 14 passed** → **预存** |

**根因判定（已定论，2026-10-16）**：三件 PS 工具为**薄包装**，真实逻辑在同名 `.py` 运行器；包装脚本 `$PythonExe` 默认 `'python'`（有意设计：假定宿主 PATH 有解释器，并暴露 `-PythonExe` 覆盖）。**受限环境 PATH 无 `python.exe`** 时，`& $PythonExe @runnerArgs` 抛 `CommandNotFoundException` → 脚本 `exit 1` 且**运行器从未启动** → 证据 JSON 未产出。故：**工具契约本身已满足**（显式传解释器即 `exit=2 / status=PENDING / 证据落 -EvidenceDir`），缺陷在**测试夹具非自洽**（依赖环境 PATH）。

**修复动作（已实施）**：`tests/test_s7_tools_skeleton.py::_build_dry_run_command` 的 PowerShell 分支显式传 `-PythonExe sys.executable`（与 .py 分支既有口径一致），使夹具自洽、不再依赖宿主 PATH；**未改动任何断言**。

**验证方式**：`python -m pytest tests/test_s7_tools_skeleton.py -q` → 期望 **26 passed**（实测 **26 passed**）。

**回填位置**：本单 §1/§9.2；S7 报告 §4.2（T2~T5 工具面）。

**风险与边界**：修复须保留「干跑禁伪造 PASS」的可证伪性（`test_no_fake_pass_without_real_environment` 不得弱化）。

**修复与验证记录（v1.0.16，2026-10-16）**

| 项 | 内容 |
|----|------|
| 指令 | 人工指令「先处理 F-11 的干跑核对」 |
| 逐件核对① | 三件 PS 工具均为薄包装：`& $PythonExe @runnerArgs`（`--dry-run --evidence-dir … --repo-root … --tool-name …`），无自身判定逻辑 |
| 逐件核对② | 实测（当前 PATH 无 `python`）：`verify_l1_1_cascade.ps1 -DryRun …` → `The term 'python' is not recognized…`（`CommandNotFoundException`）、**exit=1**、`-EvidenceDir` 下 **0 个文件** |
| 逐件核对③ | 实测（显式 `-PythonExe <解释器>`，且**不设**门控 env）：l1_1 / l2_1 / l3_1 三件均 **exit=2**、证据 `cascade-result.json` / `failover-drill.json` / `agent-e2e.json` 落至 `-EvidenceDir`；l1_1 证据内容 `tool=verify_l1_1_cascade.ps1 / mode=dry-run / status=PENDING / exit_code=2 / checks=4` |
| 结论 | 工具契约**已满足**；缺陷在**测试夹具非自洽**（未传 `-PythonExe`，依赖宿主 PATH） |
| 修复 | `_build_dry_run_command` PS 分支补 `"-PythonExe", sys.executable`（1 处 3 行 + 注释）；**断言零改动** |
| 验证 | `pytest tests/test_s7_tools_skeleton.py -q` → **26 passed**（原 12 failed / 14 passed）；`ruff check openbase tests` → **All checks passed**；全仓范围仅该测试文件裸调这三件工具（已复核） |
| 残留说明 | 工具默认值 `'python'` **保持不变**（有意的宿主约定 + `-PythonExe` 覆盖）；仓内 PATH 级答案为 `.venv\shim\python.cmd`（其解释器依赖门控 env，故不作为夹具默认） |

### 9.3 预存项与同进程串扰的归因汇总（2026-10-16）

| ID | 门禁/用例 | 隔离结果 | 基线（`e2c4f25`） | 本轮引入 |
|:--:|-----------|---------|------------------|:-------:|
| F-10 | `tests/test_s7_t1_shr.py` | 修复前 1 failed / 14 passed → **修复后 15 passed** | 同样失败 | ❌ 否（**已修复，方案 A，v1.0.15**） |
| F-11 | `tests/test_s7_tools_skeleton.py` | 修复前 12 failed / 14 passed → **修复后 26 passed** | 同样失败 | ❌ 否（**已修复，夹具自洽化，v1.0.16**） |

> **同进程串扰说明**：单进程全量跑另出现 6 例 `asyncpg.exceptions.ConnectionDoesNotExistError`（`test_tenant_admin.py` / `test_users_admin.py`），经**逐文件隔离复跑全部通过**（t_users 7 / t_tenant 5），且仓内既定分组回归（`scripts/run_regression.py`，3 文件/组子进程隔离）**未复现** → 判定为「全局 engine 单例 + 共享 PG 连接」在多文件同进程场景的**环境性串扰**，非业务缺陷（与既有登记口径一致）。

---

## §10 跨仓复核发现（L3 / B1 兼容层退役，2026-10-16 登记）

> **来源**：依人工指令「先处理 L3 B1 兼容层退役」实施**跨仓只读复核**（`doc/tmp/b1_compat_retire_probe.py`）；证据 `doc/test/evidence/manual/b1-compat-retire-openllm-20261016.json`（`overall_pass=false`）。**未改动 OpenLLM 任何文件**。

### 10.1 复核结论

| 面 | 结论 |
|----|------|
| 退役本体（`users` 端点旧管理硬门） | ✅ **已落地且实证**：`app/api/users.py` 无 `get_current_admin_user` 导入/依赖，改挂 `require_permission(PERM_USER_READ/WRITE/DELETE)`；交付提交 `298fe7d`（v2.17.0，2026-10-13）在 HEAD 祖先链上，分支 `feature/s4-identity-channel-b` 跟踪 origin；`tests/unit/{test_b1_d4_compat_gate,test_users_api,test_b1_rbac_wiring}.py` 本机复跑 **43 passed** |
| 安全耦合（生产拒绝启动） | ❌ **未生效 → F-12**（详见 §10.2） |
| 残量边界 | ⬜ **如实登记**：`get_current_admin_user` 在 `app/` 下仍有 **40 处调用点 / 12 个模块**（`auth_service` 定义 + config / audit_logs / tenants / roles / plugins / billing / cascade_routing / semantic_routing / circuit_breakers / tenant_management / prompt_assembly / config_import_export）；与 OpenLLM 交付记录 §17.5「退役面 = only `users` 端点，其余由各自路由既有语义承担」一致 —— **未在本批范围**，如需退役其余模块需按其各自「模块纳入强制期」逐一耦合（与 users 同款方案 A 纪律） |

### 10.2 F-12 详单（生产启动门禁被 fail-open 兜底吞掉）

**现象与证据**（受控端口 8056，不影响常驻 8001/8000）

| 场景 | 配置 | 期望 | 实测 |
|:----:|------|------|------|
| D1 | `ENV=production` + `RBAC_PERMISSION_ENFORCE=false` | 拒绝启动（exit≠0） | **`Application startup complete.` 正常启动**（exit 未发生）；仅 `WARNING 启动自检跳过: 生产环境必须开启 RBAC_PERMISSION_ENFORCE=true…` |
| D2 | `ENV=production` + `enforce=true` + `MODULES=["role"]`（user 未纳入） | 拒绝启动（exit≠0） | **同上**（正常启动 + 同条 WARNING） |
| D3（机制自证） | 静态：`main.py` 以 `try/except Exception: logger.warning("启动自检跳过: …")` 包裹 `run_startup_alignment_checks`，而 `get_settings()` 的**唯一**启动期调用点在该自检内（`app/core/startup_alignment.py:128`） | 成立 | 成立（`ValueError` 被吞） |
| D4（对照） | 两项前置满足（`enforce=true` + `MODULES=[]`） | 该门禁文案不出现 | 不出现 ✓（区分「门禁拒绝」与「其它启动失败」） |

**根因判定**：B1 D4 phase 4 的「安全耦合」把生产截止实现为 `get_settings()` 内的 `ValueError`（见 `app/core/config.py`「B1 D4 phase 4 兼容层退役安全耦合」段），但该函数在应用启动路径上的**唯一调用点**（`startup_alignment.py::run_startup_alignment_checks`）被 `main.py` lifespan 的**启动自检 fail-open 兜底**包裹 → 门禁异常被降级为 WARNING，应用继续启动。即：**门禁存在、单测通过，但运行态不生效**。同根因还波及同一函数内的其它生产门禁（`SECRET_KEY` / C4 `ENFORCE_INBOUND_IDENTITY_HEADERS` / 租户隔离 A 三项），见 §10.4 待裁定。

**修复建议（待 OpenLLM 侧授权；二选一）**

- **方案 A（推荐，语义正确）**：在 `main.py` lifespan **开头**（fail-open 自检之前）显式求值一次启动门禁——例如 `get_settings()`（或抽出 `assert_startup_gates()`）——使其 `ValueError` **不被任何 fail-open 包裹**；启动自检（版本口径/默认模型漂移）保持原 fail-open 语义不变。
- **方案 B**：收窄自检的 `except`（如仅捕获漂移类异常，或对门禁类 `ValueError` 重新抛出）。
- 配套：新增**启动级**回归用例（在 `ENV=production` 且门禁不满足时，应用启动应失败），避免再次出现「单测绿而运行态 fail-open」。

**验证方式**：`python doc/tmp/b1_compat_retire_probe.py` → 期望 **D1/D2 转为 `exit!=0`**（探针 `overall_pass=true`）；同时 `pytest tests/unit/test_b1_d4_compat_gate.py tests/unit/test_users_api.py tests/unit/test_b1_rbac_wiring.py` 保持 **43 passed**。

**回填位置**：本单 §1/§10；`doc/test/evidence/manual/b1-compat-retire-openllm-<日期>.json`（重跑刷新）；《五系统多租户与授权集成总览与续接指南》§7.1（新增未决项）。

**风险与边界**：**不得**以「放开门禁」或「改单测期望」消除该差异；修复后**生产若配置不合规将拒绝启动**（这正是既定机械截止语义，但**属运行影响面变化**，需 OpenLLM 侧确认其生产环境配置已满足全部门禁再实施）；退役其余 12 个模块的旧门**须逐个耦合其模块强制期**，禁止一次性批量移除。

**修复与验证记录（v1.0.18，2026-10-16，方案 A 实施于 OpenLLM 仓）**

| 项 | 内容 |
|----|------|
| 授权 | 人工指令「按方案 A 修复 F-12，并在 main.py 启动前显式求值门禁」 |
| ① 门禁显式化 | `app/core/config.py` 新增 `assert_startup_gates()`：**直接委托** `get_settings()`（同源同义，禁止两处漂移）；docstring 明示「调用方必须在 fail-open 兜底之外调用」 |
| ② 启动期求值 | `main.py` lifespan **开头**调用 `assert_startup_gates()`（**无 try/except 包裹**）→ 不合规即抛 `ValueError` 拒绝启动；「启动自检」（版本口径 / 默认模型注册漂移）**fail-open 语义保持不变** |
| ③ 回归护栏 | 新增 `tests/unit/test_f12_startup_gate_runtime.py`（6 例）：辅助函数正/负向、dev 不门禁、**门禁异常必须穿透 lifespan**、**门禁求值不得位于 fail-open `try` 内**（哨兵异常穿透法）、辅助函数与 `get_settings()` 同义 |
| ④ TDD | 先写 6 例 → **RED**（`assert_startup_gates` 未实现，`ERROR ... collection`）→ 实现 → **6 passed**（1.67s） |
| ⑤ 相关回归 | 新用例 + `test_b1_d4_compat_gate` + `test_users_api` + `test_b1_rbac_wiring` + `test_c4_production_enforce_gate` + `test_production_gate_tenant_isolation` → **58 passed** |
| ⑥ 静态检查 | `ruff check app/core/config.py main.py tests/unit/test_f12_startup_gate_runtime.py` → **All checks passed**（首轮 3 处 `SIM117`/`N818` 已修） |
| ⑦ 运行态复验 | 探针复跑 **`overall_pass=true`**：**D1/D2 → `exit=3` 拒绝启动、`started=false`**；D3 接线自证（自检 fail-open 保留 + 门禁在自检之前且未被 try 包裹）；D4 对照不触发；**C1 退役面 43 例保持 passed**；证据 `doc/test/evidence/manual/b1-compat-retire-openllm-20261016.json`（已刷新） |
| ⑧ 版本与留痕 | OpenLLM `v2.17.1 → v2.17.2`（`version.json` + `APP_VERSION` 对齐）；DevLogReport **v1.2.1 §18**（背景/根因/实施/验证/影响边界/回滚） |
| ⑨ 提交与推送 | OpenLLM 提交 **`ff506e9`**（5 文件 / +168 −6，仅精确圈定文件，未触碰其仓内既有改动）；分支 `feature/s4-identity-channel-b` **三远程（origin/backup/github）均 = `ff506e9`** |
| 影响面（一并恢复） | 同一调用点内的 `SECRET_KEY` / C4 `ENFORCE_INBOUND_IDENTITY_HEADERS` / 租户隔离 A 三项门禁**同时恢复运行态效力**（此前同样被 fail-open 吞掉） |
| 回滚 | 移除 `main.py` lifespan 开头的 `assert_startup_gates()` 一行（门禁实现与自检均未改） |

### 10.3 与 L3 项闭环状态的关系

**L3 / B1 兼容层退役：✅ 已闭环（v1.0.18）**。退役本体已落地（§10.1 第 1 行）+ 其验收判据「生产安全耦合生效」经 **F-12 修复（`ff506e9`/v2.17.2，方案 A）并运行态复验通过**（探针 `overall_pass=true`，D1/D2 `exit=3` 拒绝启动）→ 两项判据齐备。

### 10.4 裁定结果与后续（v1.0.18 落定）

| # | 事项 | 裁定/结论 |
|:-:|------|-----------|
| 1 | 是否实施方案 A | ✅ **已实施**（人工指令授权；OpenLLM `ff506e9`） |
| 2 | 同根因影响面（`SECRET_KEY` / C4 / 租户隔离 A） | ✅ **一并恢复运行态效力**（同处 `get_settings()`、同一调用点）；历史交付声明（C4 `daea828`、租户隔离 A `4f11c48`）**运行态效力随本次修复生效**；建议后续小版本补充「修复后运行态取证」于各自 DevLog（已在本单登记为可选项，不阻塞） |
| 3 | 其余 12 模块 / 40 处旧门是否退役 | ✅ **已退役（v1.0.19）**：OpenLLM `f7c7073`/v2.17.3 **全量清零**（40 处 / 12 文件），并**逐模块耦合其强制期**（生产门禁判据扩展为退役面全集 11 模块）；护栏 98 passed、相关回归 239 passed；详见 §10.5 |

### 10.5 B1 D4 phase 5：其余 12 模块旧管理硬门退役（v1.0.19 落定，2026-10-16）

> **来源**：依人工指令「继续推进其余 12 模块的硬门改造」实施（跨仓：OpenLLM 仓交付）；证据 `doc/test/evidence/manual/b1-phase5-retire-openllm-20261016.json`（`overall_pass=true`）。

**交付内容（OpenLLM 仓 `f7c7073` / v2.17.3；27 文件 / +434 −96）**

| # | 项 | 内容 |
|:-:|----|------|
| ① | 退役面 | `app/api/` 其余 **40 处 / 12 文件** `Depends(get_current_admin_user)` → `Depends(require_permission(<module>:<action>))`；**`app/api/` 下旧门调用点归零**（仅余 `auth_service` 定义本体 + `get_admin_user_or_api_key` 内部复用 + `services/__init__` 再导出） |
| ② | 新增权限码 | **10 个**：`audit:read` / `config:read` / `config:write` / `plugin:write` / `billing:write` / `routing:read` / `routing:write` / `tenant:read` / `tenant:write` / `prompt:write` |
| ③ | 门禁扩展 | `ADMIN_GATE_RETIRED_MODULES`（**11 模块** = phase 4 四模块 ∪ phase 5 七模块）；生产门禁判据由「仅 user」扩展为**退役面全集**，白名单（空=全部）未覆盖即拒绝启动并**逐项列出缺失模块** |
| ④ | 护栏 | 新增 `tests/unit/test_b1_d4_phase5_admin_gate_retire.py`（**98 passed**，含 30 例**反例自证**「强制期 + 模块未纳入灰度 → 放行」以**强判别新旧门**）；同步 6 个既有用例文件至强制期语义 + 1 处夹具改覆盖点（`get_current_active_user_or_api_key`） |
| ⑤ | 死导入清理 | `workspaces.py` / `ab_tests.py` / `usage.py` 三处未使用 `get_current_admin_user` 导入 |

**验证（实测）**

| 项 | 结果 |
|----|------|
| phase-5 护栏 | **98 passed**（30 非管理员 403 + 30 反例自证 + 30 管理员不受影响 + 3 影子期 + 5 门禁） |
| 相关回归（首轮 17 文件 292 例） | **285 passed / 7 failed**——7 项均为**退役后语义同步项**（6 个既有文件以旧硬门语义编码「非管理员 → 403」；1 例门禁用例以 phase 4「仅 user」判据编码），**非功能缺陷** |
| 相关回归（同步 6 文件后复跑 239 例） | **239 passed / 0 failed**（exit 0） |
| 静态检查 | ruff 与 HEAD 基线（`ff506e9` worktree）同文件集对比 **374 → 371（净 −3）**、**零新增**（差额即移除的 3 处死导入） |
| 推送 | 分支 `feature/s4-identity-channel-b` 三远程（origin/backup/github）**均 = `f7c7073`** |

**边界与未决（如实登记，不阻塞）**

| # | 事项 | 状态 |
|:-:|------|------|
| 1 | `app/api/tenant_management.py` 未被任何入口挂载（疑似遗留文件） | ✅ **已裁定并执行：删除（v1.0.20，OpenLLM `0d87bf1`/v2.17.4）**。四条件取证——① 未被任何入口挂载（全仓无 import / `include_router`）；② 功能由 `tenants.py` **严格超集**承载（5 端点全覆盖 + teams 等）；③ 最新 API 设计文档 v2.14.3 **0 次提及**；④ v1.8.0 已裁定「合并到 `tenants.py` 并删除」（ISSUE-003 / BUG-ROUTE-003 / GAP-03 / TD-003 闭合），但 `git log --follow` 显示自 `73c375d` 起**从未进入删除记录** → 属已裁定未执行的清理。退役面随之收窄为 11 文件；相关回归 `test_tenant_management_api + test_tenants_api` **27 passed** |
| 2 | `app/api/circuit_breakers.py` 注解 `current_user: dict` 与实际返回 `User` 不一致（**实为真实缺陷**） | ✅ **已修复（v1.0.23，OpenLLM `2263ba4`/v2.17.7，TDD）**。三管理端点（`POST /{id}/reset`、`PUT /{id}/config`、`POST /global-config`）函数体沿用 dict 语义 `current_user.get("id")` → 运行态 `AttributeError`：① 审计事件 `CircuitBreakerEvent` 被内层 try **静默吞掉（不落库）**；② 外层 logger 再次抛出 → 兜底转 **HTTP 500**。**掩盖机制**：既有用例为 `test_admin` **动态补 `get` 方法**（把 `User` 伪装成 dict）以迁就实现 → **测试通过而运行态 500**。**修复**：注解 `dict` → `User`（8 处）、取值改 `.id`（JSONB 值域 `str(...)`）、新增 `from app.models.user import User`。**验证**：RED 3 例均 `assert 500 == 200` → GREEN `test_circuit_breakers_api` **9 passed**、合并回归（含 phase-5 护栏 98）**107 passed / 0 failed**；ruff 零新增。版本 `v2.17.6 → v2.17.7`；DevLogReport **v1.2.6 §21** |
| 3 | 生产**强制期实际翻转**（`RBAC_PERMISSION_ENFORCE=true` + 模块灰度） | ⬜ **挂起（2026-10-16 裁定 A）**：待影子期观测窗口 + 运维授权，本机不翻转；退役面（13 模块）的实际保护仍由生产启动门禁兜底（未满足即拒绝启动） |
| 4 | `tests/unit/test_tenant_management_api.py`（名义覆盖已删模块的空断言文件） | ✅ **已裁定并执行：删除（v1.0.21，OpenLLM `4993f43`/v2.17.5）**。三条件取证——① **断言恒真**：4 条断言全部打在**不存在**的端点（`GET /api/v1/tenants/stats`、`GET/PUT /api/v1/tenants/config`，在 `tenants.py` 全 13 路由及任何 `app/` 模块中均无），请求被 `GET /{tenant_id}` 的 UUID 校验挡为 **422**，断言 `!= 404` **因错误原因通过**；② 全仓（含门禁契约）对该文件名**零引用**；③ 命名指向已于 v1.0.20 删除的模块。删除后 `pytest tests/unit --collect-only` → **3871 tests collected / exit 0**（无悬挂引用）。**覆盖缺口已于 v1.0.22 补测闭合**：被删模块原有三端点（`PUT /{tenant_id}/quota`、`GET /{tenant_id}/usage`、`GET /{tenant_id}/gpu-allocation`）已在归属文件 `tests/unit/test_tenants_api.py` 新增 `TestTenantQuotaUsageGpuAPI`（**12 例**，OpenLLM `4a87cc0`/v2.17.6）：正向**落库 / 聚合数值逐项断言** + 空态 + **跨租户 403 / 未认证 401 反例自证**；单跑 12 passed、合并回归 **133 passed / 0 failed** |

| 5 | `providers.py` / `local_models.py` 的 `get_admin_user_or_api_key`（v2.14.0「管理员 API Key 通道」；判定链同为 `is_admin()`，与 phase 4/5 退役门**同族**） | ✅ **已按方案 A 退役（v1.0.24，OpenLLM `da3b834`/v2.17.8，TDD）**：**2 文件 / 12 处**写端点 → `require_permission(provider:write / local_model:write)`；`ADMIN_GATE_RETIRED_MODULES` 由 11 → **13 模块**（生产启动门禁同步扩展）。**语义等价性**：管理员 JWT 与**管理员所属 API Key** 均经 `is_admin()` 快路径**等价放行**；非管理员通道由「恒定 403」→「按权限码（强制期）」。**验证**：新增护栏 `test_b1_d4_phase6_admin_gate_retire.py` **43 例**（含 12 例**反例自证**）；**RED 15 failed / 28 passed**（`git stash` 暂回退源至 HEAD 基线）→ **GREEN 171 passed / 0 failed**；`test_providers_api` 6 例同步至强制期语义；ruff **新增文件全清、改动零新增**。**登记处置（2026-10-16）**：① `get_admin_user_or_api_key` 退役后**无调用点的定义体**已随项 6 一并清理（v1.0.25，OpenLLM `f477d1e`）→ ✅ 关闭；② `e2e_v214_security.py`（M2-004）期望**已按强制态复核并改造**（裁定 **B1**：OpenLLM `e451177`，见项 9）→ ✅ 关闭 |

| 6 | `auth_service` 退役后**死定义**（`get_current_admin_user` / `get_admin_user_or_api_key`）及 `app.services` 对前者的再导出 | ✅ **已清理（v1.0.25，OpenLLM `f477d1e`/v2.17.9，TDD）**：phase 4~6 已清零**调用点**，本批整段移除两个**无调用点**定义体 + 移除 `services/__init__` 的 import 与 `__all__` 条目。**护栏（先 RED）**：新增源码契约 `tests/unit/test_b1_d4_retired_gate_symbols_cleanup.py`（**3 例**：① 符号不再存在于 `app.services.auth_service`；② 不再由 `app.services` 再导出（`__all__` + 属性面双查）；③ **全 `app/` 源码 AST 扫描**无**代码级**引用——注释与文档字符串中的历史说明不计）→ **RED 3 failed**（并暴露 `app/services/audit_service.py` 带 **UTF-8 BOM**）→ **GREEN 216 passed / 0 failed**（护栏 3 + phase-5 98 + phase-6 43 + providers 30 + auth 20 + users 22）；`ruff` **All checks passed**；`pytest tests/unit --collect-only` **无悬挂引用**。**顺带发现（登记）**：`audit_service.py` 的 BOM 会影响以 `ast.parse(文本)` 做源码扫描的工具链，是否统一去 BOM 属独立清理项 |

| 7 | 源码编码：Python 源码带 **UTF-8 BOM**（会使 `ast.parse(文本)` 类源码扫描工具报 `SyntaxError: invalid non-printable character`） | ✅ **已统一清理（v1.0.26，7 文件 / 3 仓，TDD）**：跨仓字节级扫描（5 仓 / **8908** 文件）命中 **497**——`.py` **7**（本批剥离：OpenBase 2 = `openbase/core/models/{base,business}.py`；OpenLLM 4 = `app/services/audit_service.py` + 3 个测试文件；OpenMemory 1 = `tests/test_v700_smoke.py`）、`.ps1` **46**（**有意保留**：PowerShell 5.1 对无 BOM 的 UTF-8 按 GBK 误解码，本项目既定做法）、其它 **444**（`.md` 236 / `.json` 29 / `.sql`·`.vue`·`.ts`·`.js`·`.yml`·`.txt` 179 → **裁定 C1：维持（仅统计上报）**）。**护栏（先 RED）**：在本节项 6 的源码契约文件追加第 4 条 `test_python_sources_have_no_utf8_bom`（扫描 `backend/**/*.py`，排除第三方/缓存），并把第 3 条 AST 扫描由 `utf-8-sig` 兜底**回归 `utf-8`** → **RED 2 failed / 2 passed**（第 3 条 `SyntaxError: U+FEFF`；第 4 条列出 4 个 `.py`）→ **字节级剥离**（逐文件三重校验：首 3 字节为 BOM / 正文经 `throwOnInvalidBytes` 严格解码 / 剥离前后**解码内容完全一致**；仅删 3 字节，**不重编码、不改行尾**）→ **GREEN 183 passed / 0 failed**；OpenBase 侧（被剥离者为核心模型）`test_models`/`test_db_init`/`test_three_modules` **全通过**。证据 `doc/test/evidence/manual/source-bom-cleanup-20261016.json`（`overall_pass=true`，`open_items.S1` 其余 444 待裁定 / `S2` 各仓编码契约待统一） |

| 8 | 跨仓**源码编码契约未统一建立**（上一批仅 OpenLLM 有仓内护栏，OpenRAG / OpenMemory / DPS 无同款检查） | ✅ **已建立并落地（v1.0.27，2026-10-16，TDD）**：① **工具（单一事实源）**：`scripts/scan_source_encoding.py`——跨仓扫描器、**零第三方依赖**；硬判据 `REQUIRED_NO_BOM`＝`.py` 不得带 BOM、`REQUIRED_BOM_IF_NON_ASCII`＝含非 ASCII 的 `.ps1` 必须带 BOM（PowerShell 5.1 对无 BOM 的 UTF-8 按 GBK 解码）；其余扩展名仅统计；排除第三方/缓存/构建目录与 `doc/tmp`。CLI：`--check`（违规即 exit 1）/ `--json --out` / `--strip-py`（字节级三重校验剥离）。② **回归**：`tests/test_source_encoding_contract.py`（**5 例**：工具自检 / 跨仓契约主体 / `.py` 带 BOM **正控** / `.ps1` 带 BOM **负控** / 非 ASCII `.ps1` 无 BOM **正控**）→ **RED 4 failed（扫描器缺失）→ GREEN 5 passed**。③ **契约落地即发现并修复真实缺陷**：命中 **12 个含非 ASCII 却无 BOM 的 `.ps1`（OpenLLM 10 / OpenRAG 1 / OpenMemory 1）**，其中 **9 个在 GBK 默认代码页下确实解析失败**（共 **37** 个解析错误，单文件最多 `scripts/deploy.ps1` **18** 个、`install-ollama.ps1` 9 个）→ 逐文件**前置 3 字节 BOM**（不改正文、不重编码、不改行尾）→ 全部 **0 解析错误**；契约面复跑 **8857 文件 / 违规 0 / PASS**（`.ps1` 带 BOM 46 → **58**）。④ **证据**：`doc/test/evidence/manual/source-encoding-contract-20261016.json`（机器生成 PASS 报告）+ `source-encoding-ps1-remediation-20261016.json`（12 文件前后对照因果证据）。⑤ **提交**：OpenBase **`0fe52fc`**、OpenLLM **`b0cea58`**（10 个 `.ps1` + DevLogReport v1.2.10 §25）、OpenRAG **`fcec166`**、OpenMemory **`f30d361`**。⑥ **裁定（C1，2026-10-16）**：其余 **444** 个非 `.py` 文本文件（`.md` 236 / `.json` 23 / `.txt` 178 等）的 BOM **维持现状**——契约中仅统计上报、不计失败（不统一剥离） |

| 9 | `e2e_v214_security.py`（v2.14.0 安全专项）**M2-004 期望**（非管理员 API Key 模型写 403）在 phase 6 退役后需按强制态复核 | ✅ **已复核并改造（v1.0.28，裁定 B1；OpenLLM `e451177`）**：脚本 M2-004 由「恒定 403」改为**按强制态判定**——新增模块级 `EXPECT_WRITE_ENFORCED`（读环境变量 `OPENLLM_E2E_RBAC_ENFORCE`，默认 `0`）；强制态断言 `st == 403`，否则断言「放行（∉{401,403}）」并标注观察态。**边界**：脚本需 `127.0.0.1:8013` 活动服务 + 共享 PG，**不在本机 pytest 面内 → 运行态未实跑**；`py_compile` OK、`ruff`（本仓 `ruff.toml`）与 HEAD 基线**逐项一致（UP009/I001/C408）→ 零新增**。DevLogReport **v1.2.11 §26**；产品版本保持 v2.17.10 |

**与 L3 闭环判定（§10.3）的关系**：L3（B1 兼容层退役）此前已判「已闭环」（phase 4 本体 + F-12 安全耦合）；§10.5 为**同一退役主题的收尾**（phase 5 清 `get_current_admin_user` 调用点、phase 6 清同族 `get_admin_user_or_api_key`、项 6 清**死定义与再导出**、项 7 清**源码 BOM**、项 8 建**跨仓编码契约**并清 `.ps1` GBK 风险、项 9 复核 **e2e M2-004 期望**）→ 退役面 **13 模块**且**符号零残留**，**不改变 L3 闭环判定**。§10.4 第 3 项与 §10.5 第 1~9 项至此收敛（仅余第 3 项「生产强制期实际翻转」**按裁定 A 挂起**，待影子期观测窗口 + 运维授权；其余 444 个非 `.py` 文本 BOM 按裁定 C1 **维持现状**）。

---

## 附录

### 附录 A 用例 → 缺陷 → 责任方映射表

| 用例 ID | 段 | 判定 | 归属缺陷 | 责任方 | 关联断言 |
|:---:|:---:|:---:|:---:|--------|---------|
| S0-1 | S0 | FAIL | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S0-4 | S0 | FAIL | **F-3** | OpenLLM（+ OpenBase 协议头对标） | S7-T6-2 / S7-T6-1 |
| S1-1 | S1 | FAIL | **F-2** | OpenRAG | S7-T6-2 |
| S1-2 | S1 | FAIL | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S2-4 | S2 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S3-1 | S3 | FAIL | **F-2** | OpenRAG | S7-T6-2 / S7-T4-1~4 |
| S3-2 | S3 | FAIL | **F-2** | OpenRAG | S7-T6-2 / S7-T4-1~4 |
| S3-3 | S3 | FAIL | **F-2** | OpenRAG | S7-T6-2 / S7-T4-1~4 |
| S3-4 | S3 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S5-1 | S5 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S5-2 | S5 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S5-3 | S5 | FAIL | **F-3** | OpenLLM（+ OpenBase 协议头对标） | S7-T6-2 / S7-T6-1 |
| S5-4 | S5 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S5-5 | S5 | BLOCKED | **F-1** | OpenLLM + 环境侧 | S7-T6-2 |
| S6-1 | S6 | FAIL | **F-2** | OpenRAG | S7-T6-2 / S7-T6-4 |
| S5-6 | S5 | BLOCKED | **不受控（禁停服务）** | 受控窗口 / T3 | S7-T6-2（挂起登记，不在本单） |

### 附录 B 当前冒烟结果快照

来源：`doc/test/evidence/s7/smoke/smoke-summary.json`（`generated_at=2026-09-11T18:57:56+08:00`，`mode=real`，`openbase_commit=0595bcde788bd19d3a2e21ffc647b827eaa3fded`）。

| 维度 | 值 |
|------|-----|
| P0 总数 | 30 |
| P0 PASS | 14（S0-2/S0-3/S0-5/S2-1/S2-2/S2-3/S2-5/S2-6/S4-0/S4-1/S4-2/S4-3/S6-2/S6-4） |
| P0 FAIL | 9（S0-1/S0-4/S1-1/S1-2/S3-1/S3-2/S3-3/S5-3/S6-1） |
| P0 BLOCKED | 7（S2-4/S3-4/S5-1/S5-2/S5-4/S5-5/S5-6） |
| P1 总数 | 2（S4-4、S6-3，均 BLOCKED） |
| 入口准则 | `entry_criteria_met=false`（五服务 `/health` 通过；但三真实开关未全开且 OpenLLM 上游不可达） |
| 缺陷归属 | FAIL 9 = F-1(2) + F-2(5) + F-3(2)；BLOCKED 7 = F-1(6) + 禁停约束(1，S5-6) |

来源：`doc/test/evidence/s7/env/env-check.json`（`rechecked_at=2026-09-11T20:45:00+08:00`）。

| 状态 | 数量 | 说明 |
|------|:---:|------|
| READY | 14 | 真实 PG（含业务 schema）/ `openbase_test` / Redis / 本地 IdP 8090 / 四仓运行态 / 网关 8000 / 前端 5173 / Playwright 等 |
| NOT_READY | 0 | `openbase_test` 建库闭环后归零 |
| UNREACHABLE | 2 | Keycloak 8080、nginx `/ui/` |
| BLOCKED | 1 | OpenLLM `jerry.yu` 远端（受限挂起，不阻断段门禁） |

---

> **文档结束**。本单为 S7 段冒烟缺陷（F-1/F-2/F-3）**分派与闭环回填待办**（[Draft] v1.0.2）；**v1.0.1 新增 F-5（OpenLLM K07 端点过滤矩阵全量补填：工作树完成/待提交，非冒烟阻塞项）**；**v1.0.2 新增 F-6（OpenMemory K07 端点过滤矩阵 8 条缺口已补填：工作树完成/待提交，非冒烟阻塞项）**；所有键名 / 文件路径 / 行号均自实际仓内只读核对得出，每缺陷的验证用例 ID 与 `smoke` 证据逐条对应；**不输出明文密钥 / 口令**；未改动任何功能语义代码、未将 `dogfood-output/` 纳入提交面。**v1.0.8 收口**：K07 挂起项（F-5 / F-6 / DPS 35 条豁免续期）全部闭环，K07/SYS-1 门禁 verdict 由 `PARTIAL` 升 **PASS**；四仓改动与提交由各仓在可写环境执行（本单只登记不代改），DPS 侧改动已生成一键提交脚本待执行。**v1.0.13；**v1.0.13 新增**：**F-8 / F-9**（L2 真实面探针暴露的 OpenBase 侧两项缺陷，均 P1、阻塞用例数 0，见 §8；同窗口已达成「委托跨界 403 + 同域放行 200」反例自证配对与 agent key 面 A/D/F/G 全绿）；两项**仅登记、未改代码**，修复窗口待裁定。**v1.0.14 收口**：**F-8 / F-9 已按 TDD 修复并验证通过**（提交 `6bf7832`；探针复跑 `overall_pass=true`；仓内分组全量回归 `passed=1118 / failed=0 / skipped=4`），**本单待提交项清零**；同时**新增 F-10 / F-11 预存门禁失败登记**（§9，经 `e2c4f25` 基线证明非本轮引入，修复方案待裁定）。**v1.0.15 收口**：**F-10 已按方案 A 修复并验证通过**（两脚本服务生命周期改经 `service-orchestrator.ps1`，自身不再直接终止进程；扫描器 `disallowed=0`、`test_s7_t1_shr.py` 15 passed、冒烟受管复跑 `PASS 25 / FAIL 0 / PENDING 7`，证据 `smoke-summary-20261016120118.json`）；**F-11 仍待裁定**。**v1.0.16 收口**：**F-11 干跑核对完成并修复**（根因＝测试夹具非自洽：工具默认解释器为裸 `python`，受限环境 PATH 无解释器 → 退出 1 且不落证据；**工具契约本身已满足**——显式传 `-PythonExe` 即 `exit=2 / PENDING / 证据落 -EvidenceDir`）→ 夹具补 `-PythonExe sys.executable`（断言零改动），`tests/test_s7_tools_skeleton.py` **26 passed**。**F-1~F-11 至此全部闭环**（本单待办清零）。**v1.0.17 新增 F-12（OpenLLM 仓，P1，跨仓复核发现）**：L3 / B1 D4 phase 4「兼容层退役」**退役本体已落地并实证**（`298fe7d` / 43 passed），但其**生产安全耦合实测未生效**（启动门禁被 `main.py` 启动自检 fail-open 兜底吞掉 → 生产带 `RBAC_PERMISSION_ENFORCE=false` 仍可启动）→ **L3 项未闭环**（详见 §10，待 OpenLLM 侧授权修复）；其余 12 模块 40 处旧门按交付记录**本批范围外**（已如实登记）。**v1.0.18 收口**：**F-12 已按方案 A 修复并复验通过**（OpenLLM `ff506e9`/v2.17.2：新增 `assert_startup_gates()` + `main.py` lifespan 开头无包裹求值 + 6 例新用例；运行态探针 `overall_pass=true`，D1/D2 → `exit=3` 拒绝启动；相关回归 58 passed；ruff 全清；三远端已同步）→ **L3 / B1 兼容层退役闭环**。**F-1~F-12 至此全部闭环**。
