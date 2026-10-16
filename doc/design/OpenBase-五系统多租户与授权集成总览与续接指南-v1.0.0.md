# OpenBase-五系统多租户与授权集成总览与续接指南-v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）及四套自研后端系统（OpenLLM / OpenRAG / OpenMemory / DPS） |
| 文档编号 | OB-DESIGN-MTAUTH-OVERVIEW-v1.0.0 |
| 文档版本 | **v1.0.24**（文件名版本＝首次定稿版本；内容版本以本字段与修订历史承载） |
| 状态 | **[Review]**（本文为**汇总视图**，不引入新结论；一切结论以其上游单一事实源为准） |
| 作者 | AA/PM-OpenBase-Dev |
| 创建日期 | 2026-10-09 |
| 存放 | doc/design/ |
| 定位 | 面向「**后续迭代**」与「**新系统接入**」的总览与续接指南：一页看懂五系统的多租户与授权集成方案、契约、落地情况与未决项 |
| 上游单一事实源 | 《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》（台账，内容版本 **v1.16.33**）；《OpenBase-协议头规范-v1.1》；《OpenBase-统一身份与主备双通道贯通总体方案-v1.0.0》；《OpenBase-统一身份最小特征集与隔离模型设计-v1.0.0》；《OpenBase-四维身份透传契约-v1.1.0》；《OpenBase-R387-跨域租户码对齐设计与收口实施记录》 |
| 边界 | 本文**不改写**上游台账结论；若与上游冲突，以上游为准。台账 §9.1 为派单分发时快照，行状态请以 §5.1 / §10.3 的**回填值**为准 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.24 | 2026-10-16 | AA/PM-OpenBase-Dev | **余项处置裁定（②接受边界 / ③强制核验 / ④并入矩阵）+ D5/D15 低危闭环**：依人工裁定实施。① §10.3 生产开关清单强化为**发布强制核验**（「处置机制」第 3 条由「建议」转「**强制**」），并**并入 OpenLLM 5 组强耦合启动门禁**（本批 3 + 既有 2，不拆分）；② §10.4 遗留表同步——「各仓门禁仅装配路径生效」转 ✅ **已接受边界**（裁定②）、「OpenLLM 5 组开关强耦合」转 ✅ **已并入矩阵**（裁定④）、「OpenRAG `.devflow` projectVersion」保持登记，并新增「走查低危 D5/D15 ✅ 已修复」行；③ 跨仓落地：OpenRAG **`e2b1ddd`**（D5：`TenantScopeRequiredError` → 403 `PERM_FORBIDDEN`，v1.9.3）、DPS **`8e27614`**（D15：`TenantManager` 桩显式标注 + 反例自证，不改行为/版本）；④ 回填跨仓走查报告 **v1.4.0** §4.3/§6.7 |
| v1.0.23 | 2026-10-16 | AA/PM-OpenBase-Dev | **余下未决项裁定执行（A 挂起 / B1 / C1 / D 维持）**：依人工裁定「A 挂起、B1、C1、D 维持」执行。① **B1**（在 **OpenLLM 仓**，提交 `e451177`）：`e2e_v214_security.py` 的 **M2-004**（非管理员 API Key 模型写 403）期望由「恒定 403」改为**按强制态判定**——新增模块级 `EXPECT_WRITE_ENFORCED`（读环境变量 `OPENLLM_E2E_RBAC_ENFORCE`，默认 `0`）；强制态断言 `st == 403`，否则断言「放行（∉{401,403}）」并标注观察态。**验证**：`py_compile` OK；`ruff`（本仓 `ruff.toml`）与 HEAD 基线**逐项一致（UP009/I001/C408）→ 零新增**；运行态未实跑（脚本需 `127.0.0.1:8013` 活动服务 + 共享 PG，不在本机 pytest 面内）；DevLogReport **v1.2.11 §26**（产品版本保持 v2.17.10）。② **D（§7.1 未决项 8 DPS 自身 IAM）→ 维持规划中项，不立项**；③ **C1**：其余 444 个非 `.py` 文本 BOM **维持现状**（仅统计上报）；④ **A**：退役面（13 模块）生产强制期翻转**挂起**（待影子期观测窗口 + 运维授权）。回填《S7-冒烟缺陷分派待办单》**v1.0.28** §10.5 项 3/5/7/8/新增项 9 |
| v1.0.22 | 2026-10-16 | AA/PM-OpenBase-Dev | **退役后死定义清理 → 旧管理硬门「符号零残留」**：依人工指令「清理 auth_service 中的死定义」，在 **OpenLLM 仓**实施（提交 `f477d1e`/v2.17.9）：整段移除 `auth_service.get_current_admin_user`、`auth_service.get_admin_user_or_api_key`（phase 4~6 退役后**均无调用点**），并移除 `app/services/__init__` 对其的 import 与 `__all__` 条目。**护栏（先 RED）**：新增源码契约 `tests/unit/test_b1_d4_retired_gate_symbols_cleanup.py`（**3 例**：符号不再存在于 `auth_service` / 不再由 `app.services` 再导出（`__all__` + 属性面双查） / **全 `app/` AST 扫描**无代码级引用，注释与文档字符串不计）→ **RED 3 failed** → **GREEN 216 passed / 0 failed**（护栏 3 + phase-5 98 + phase-6 43 + providers 30 + auth 20 + users 22）；`ruff` **All checks passed**；`collect-only` 无悬挂引用。**行为零变化**（删除无调用点定义体与再导出）。**回填**：§7.1 未决项 10；《S7-冒烟缺陷分派待办单》v1.0.25 §10.5（证据 `open_items.O6`）。**登记**：`audit_service.py` 带 UTF-8 BOM（影响 `ast.parse(文本)` 类工具链）；v2.14.x 历史设计文档作快照不回溯改写 |
| v1.0.21 | 2026-10-16 | AA/PM-OpenBase-Dev | **B1 D4 phase 6：同族旧管理硬门（`get_admin_user_or_api_key`）退役 → 退役面含同族门全量清零**：依人工裁定「方案 A」，在 **OpenLLM 仓**实施（提交 `da3b834`/v2.17.8）：`providers.py`（6 处）与 `local_models.py`（6 处）共 **2 文件 / 12 处**写端点由 `Depends(get_admin_user_or_api_key)`（v2.14.0 设计的「管理员 API Key 通道」，判定链同为 `is_admin()`）改挂 `require_permission(provider:write / local_model:write)`；新增 2 权限码；`ADMIN_GATE_RETIRED_MODULES` 由 11 → **13 模块**。**语义等价性**：管理员 JWT 与**管理员所属 API Key** 均经 `is_admin()` 快路径等价放行；非管理员通道由「恒定 403」→「按权限码（强制期）」。**验证（TDD）**：新增护栏 43 例 → **RED 15 failed / 28 passed**（`git stash` 暂回退源至 HEAD）→ **GREEN 171 passed / 0 failed**；ruff 新增文件全清。**回填**：§4 注记与 §7.1 未决项 10；《S7-冒烟缺陷分派待办单》v1.0.24 §10.5（证据 `doc/test/evidence/manual/b1-phase5-retire-openllm-20261016.json`，`overall_pass=true`，`open_items.O5`）。**本次依人工裁定实施（该门为 v2.14.0 有意设计，故先请裁定再执行）** |
| v1.0.20 | 2026-10-16 | AA/PM-OpenBase-Dev | **B1 D4 phase 5：其余 12 模块旧管理硬门全量退役 → 退役面清零（§7.1 未决项 10 残量关闭）**：依人工指令「继续推进其余 12 模块的硬门改造」，在 **OpenLLM 仓**实施（提交 `f7c7073`/v2.17.3，27 文件 / +434 −96）：① `app/api/` 其余 **40 处 / 12 文件** `Depends(get_current_admin_user)` → `Depends(require_permission(<module>:<action>))`（**`app/api/` 下旧门调用点归零**）；② 新增 **10 个权限码**（audit:read / config:read / config:write / plugin:write / billing:write / routing:read / routing:write / tenant:read / tenant:write / prompt:write）；③ 生产门禁判据由「仅 user」扩展为**退役面全集**（`ADMIN_GATE_RETIRED_MODULES`，11 模块，逐项列出缺失模块）；④ 清理 3 处死导入。**验证**：新增护栏 **98 passed**（含 30 例**反例自证**强判别新旧门）；相关回归首轮 292 例 **285 passed / 7 failed**（7 项均为**退役后语义同步项**，非功能缺陷）→ 同步 6 文件后复跑 **239 passed / 0 failed**；ruff 与 HEAD 基线（`ff506e9` worktree）同文件集对比 **374 → 371（净 −3）**、**零新增**；三远程均 = `f7c7073`。**回填**：§4 注记与 §7.1 未决项 10 残量清零；《S7-冒烟缺陷分派待办单》v1.0.19 §10.5（证据 `doc/test/evidence/manual/b1-phase5-retire-openllm-20261016.json`，`overall_pass=true`）。**本项不改变 L3 闭环判定** |
| v1.0.19 | 2026-10-16 | AA/PM-OpenBase-Dev | **F-12 按方案 A 修复并复验 → L3 / B1 兼容层退役闭环（§7.1 未决项 10 关闭）**：依人工指令「按方案 A 修复 F-12，并在 main.py 启动前显式求值门禁」，在 **OpenLLM 仓**实施（提交 `ff506e9`/v2.17.2）：① 新增 `app/core/config.py::assert_startup_gates()`（**直接委托** `get_settings()`，同源同义）；② `main.py` lifespan **开头**无包裹调用（不合规即拒绝启动），「启动自检」保持原 fail-open 语义；③ 新增 `tests/unit/test_f12_startup_gate_runtime.py`（**6 例**，含「门禁异常必须穿透 lifespan」「求值不得位于 fail-open try 内」结构断言）。**验证**：TDD（先 RED 后 6 passed）；相关回归 **58 passed**；`ruff` 全清；**运行态探针复跑 `overall_pass=true`**（D1/D2 → `exit=3` 拒绝启动、`started=false`）；退役面 43 例保持 passed。**影响面**：`SECRET_KEY` / C4 入站头 / 租户隔离 A 三项门禁**一并恢复运行态效力**；非生产零变化；生产不合规将拒绝启动（上线前须确认配置齐备）；其余 12 模块 / 40 处旧门不在本批范围。OpenLLM 三远程均 = `ff506e9`；回填 S7 报告线（承 `gate-aggregate` 口径）与《S7-冒烟缺陷分派待办单》v1.0.18 §10 |
| v1.0.18 | 2026-10-16 | AA/PM-OpenBase-Dev | **L3 / B1 兼容层退役跨仓复核：退役本体已落地，但生产安全耦合未生效（新增 F-12）**：依人工指令「先处理 L3 B1 兼容层退役」实施跨仓**只读复核**。① **已落地并实证**：OpenLLM `app/api/users.py` 旧硬门（`get_current_admin_user`）已移除、改挂 `require_permission(PERM_USER_*)`；交付提交 `298fe7d`（v2.17.0）在 HEAD 祖先链；`tests/unit/{test_b1_d4_compat_gate,test_users_api,test_b1_rbac_wiring}.py` 本机复跑 **43 passed**。② **未生效（F-12，P1）**：受控端口 8056 实跑——`ENV=production` + `RBAC_PERMISSION_ENFORCE=false`（及 enforce=true 但 user 未纳入灰度）**均正常 `Application startup complete.`**，仅 `WARNING 启动自检跳过: …RBAC_PERMISSION_ENFORCE=true…`；根因＝`get_settings()` 的生产门禁唯一启动期调用点位于 fail-open 的启动自检内（`main.py` lifespan `try/except` 吞掉 `ValueError`）→ **门禁存在、单测通过，但运行态不生效**。③ **残量边界**：其余 **12 模块 / 40 处**旧门按 OpenLLM 交付记录 §17.5 属**本批范围外**（已如实登记）。④ **本次修复了本文档此前的滞后表述**（§4 原记「兼容层退役为独立后续项」→ 更正为「已交付但耦合未生效」）；§7.1 新增未决项 10。证据 `doc/test/evidence/manual/b1-compat-retire-openllm-20261016.json`（`overall_pass=false`）；详见《S7-冒烟缺陷分派待办单》v1.0.17 §10。**未改动 OpenLLM 任何文件** |
| v1.0.17 | 2026-10-16 | AA/PM-OpenBase-Dev | **RA-06 fail-closed 受控窗口故障注入完成（5 场景全 PASS）→ §10.4 遗留表 RA-06 五项真实面 5/5 全闭环**：**非破坏性注入**（仅探针实例 `POSTGRES_URL → 127.0.0.1:1` 不可达；专用端口 8055；共享 PG / 常驻服务未受影响）。**S1** production+DB 不可达 → **503 `SYS_503` / `detail.reason=db_unavailable`** + ERROR `denied (fail-closed)` / `policy_source=env_production`；**S2** development+DB 不可达 → **200 兼容放行** + WARN `reason=db_unavailable_env_allow`（留痕）；**S3** production+白名单命中 → **200 放行** + WARN `reason=db_unavailable_allowlisted`（留痕）；**S4** production+policy=allow → **拒绝启动**；**S5** production+enforce_token_version=false → **拒绝启动**。证据 `doc/test/evidence/manual/ra06-failclosed-20261016.json`（`overall_pass=true`）；回填 S7 报告 v1.0.14、`gate-aggregate.json`（§RA-06 `fail_closed` `real_face_status=PASS` + `ra06_fail_closed_real_face` 明细） |
| v1.0.16 | 2026-10-16 | AA/PM-OpenBase-Dev | **F-11 干跑核对完成并修复（夹具自洽化）**：① 逐件核对三件 PS 工具（`verify_l1_1_cascade.ps1` / `drill_l2_1_failover.ps1` / `verify_l3_1_agent.ps1`）——均为转发同名 `.py` 运行器的**薄包装**，`$PythonExe` 默认 `'python'` 为有意设计（暴露 `-PythonExe` 覆盖）；② **根因＝测试夹具非自洽**：受限环境 PATH 无解释器 → `CommandNotFoundException` 退出 1 且**运行器从未启动**（无证据落盘）；③ **契约实证**：显式传 `-PythonExe`（不依赖门控 env）→ 三件均 `exit=2 / status=PENDING / exit_code=2 / checks=4`，证据落 `-EvidenceDir`；④ 修复：`tests/test_s7_tools_skeleton.py` 夹具 PS 分支补 `-PythonExe sys.executable`（**断言零改动**）；⑤ 验证：**26 passed**、`ruff` 全清 → **F-11 关闭，段门禁预存失败（F-10/F-11）清零**；回填 S7 报告 v1.0.13、《S7-冒烟缺陷分派待办单》v1.0.16 §9.2 |
| v1.0.15 | 2026-10-16 | AA/PM-OpenBase-Dev | **F-10 修复闭环（方案 A：受管编排唯一入口）+ 冒烟受管复跑**：① `scripts/run_smoke_s0_s6.ps1` 与 `scripts/verify_mtauth_realface.ps1` 的服务生命周期全部改经 `scripts/service-orchestrator.ps1`（`-Action stop\|start\|stop -Only …`），自身不再直接终止进程；补 PATH 引导 + UTF-8 BOM；② 验证：扫描器 `disallowed=0 / exit 0`（`bypass-scan.json` 重跑 `scanned=46`）、`test_s7_t1_shr.py` **15 passed**（与 t6_gate 合计 **31 passed**）、**冒烟受管复跑 `PASS 25 / FAIL 0 / PENDING 7`**（`smoke-summary-20261016120118.json`，与第三轮逐项一致）；③ §10.4/§10.5 状态同步为「**F-10 已修复；仅余 F-11 待裁定**」；回填 S7 报告 v1.0.12、《S7-冒烟缺陷分派待办单》v1.0.15 §9.1 |
| v1.0.14 | 2026-10-16 | AA/PM-OpenBase-Dev | **F-8 / F-9 修复闭环（TDD）+ 预存门禁失败登记**：① **F-8**（`/auth/me` 对绑租户主体 500）与 **F-9**（`users` / OIDC JIT 建号未派生 `tenant_code` → 同域委托误判跨界）已按 TDD 修复——3 条 RED 用例先行，**提交 `6bf7832`**；验证：`ruff` 全清、隔离用例全绿、**仓内分组全量回归 `passed=1118 / failed=0 / skipped=4`**、**L2 探针复跑 `overall_pass=true`**（E 500→200、O 403→200）；② §10.4 遗留表与 §10.5 结论同步为「**F-8/F-9 已修复**」；③ 新增 **F-10**（SHR 受管编排唯一入口门禁：两脚本 3 处直接 `Stop-Process`）/ **F-11**（S7 工具骨架门禁 12 项）**预存登记**（经 `e2c4f25` 基线证明非本轮引入，修复方案待裁定）；④ 回填 S7 报告 v1.0.11、`gate-aggregate.json`（`aggregate_rerun_20261016.fix_verify` + `new_defects_registered` 扩至 4 项）、《S7-冒烟缺陷分派待办单》v1.0.14 |
| v1.0.13 | 2026-10-16 | AA/PM-OpenBase-Dev | **§10.5 刷新（L1 冒烟第三轮闭环 + L2 RA-06 余项探针）**：① **冒烟 S0–S6 第三轮真实执行** `total=32 / PASS 25 / FAIL 0 / PENDING 7`（首轮 17/8/7 → 8 项 FAIL 全绿），证据 `doc/test/evidence/s7/smoke/smoke-summary-20261016005540.json`，跨仓派单升 v1.0.2（§8 回执 7 项勾选）；② **RA-06 余项真实面 4/5 闭环**——委托跨界 ✅（跨域 403 `PERM_DELEGATION_CROSS_TENANT` + 同域 200 反例自证）、L3-1 agent key 面 A/D/F/G 全绿，证据 `doc/test/evidence/manual/mtauth-delegation-l31-20261016.json`；**余 fail-closed 故障注入 PENDING（需停服，待授权）**；③ 探针暴露两项 OpenBase 侧缺陷 **F-8**（`/auth/me` 对绑租户主体 500）/ **F-9**（`users` 路径未派生 `tenant_code` → 同域委托误判跨界），登记《S7-冒烟缺陷分派待办单》v1.0.13 §8（P1/阻塞用例数 0/待修复）；④ §10.4 遗留表与 §10.5 逐条同步；回填 S7 报告 v1.0.10 §4.2、`gate-aggregate.json`（§RA-06 四项 real_face_status PASS / §SMOKE-S0-S6 PASS / `aggregate_rerun_20261016`） |
| v1.0.12 | 2026-10-16 | AA/PM-OpenBase-Dev | **状态回写（消除 v1.0.3 以来的滞后）**：经逐项核对台账 v1.16.33，§4.1 批次表 B3/C1-d/C2/C3/C4/C5/D3 由「未启动/未实施/第一阶段/其余三仓未落地」回写为**已闭环**（B3 2026-10-09 锚点全覆盖；C1-d/C2 2026-10-09 `code_normalize.py`；C3 三阶段全部完成至 2026-10-13 OM 消费侧 `3f1fa5f`；C4/C5 2026-10-09 四仓覆盖；D3 2026-10-12 探针 18 PASS/0 FAIL）；§4.3 现状表与 §7.1 未决项同步刷新——**B1 强制期全 4 模块已完成灰度翻转（2026-10-13）**，§7.1 九项中 8 项已解决，仅第 8 项（DPS 自身 IAM 演进）仍为规划中项；上游台账版本引用 v1.9.4 → v1.16.33 |
| v1.0.11 | 2026-10-15 | AA/PM-OpenBase-Dev | §10.5 新增**跨仓派单指针**：《OpenBase-S7-T6-2 冒烟真实执行-跨仓派单》v1.0.0（OB-DISPATCH-S7T62-SMOKE-v1.0.0，[Draft] 待批准分发）——分仓分发表、准入判据、验收标准、逐仓回执项、已知环境适配项 |
| v1.0.10 | 2026-10-15 | AA/PM-OpenBase-Dev | **查清 OpenBase/OpenLLM「启停抖动」根因**（**非产品缺陷**）：① 包装脚本健康检查超时过短（4–5s）≪ OpenLLM `/openllm/v1/health` 首调用耗时（~11–40s，依赖三上游+Ollama 探活）→ 误判「未起」（已修为 90s）；② 多轮重叠运行的**端口残留竞争**（已加启动前清端口）；③ **沙箱在命令结束时回收子进程**，故必须「同命令内启动+探针」；④ 运行器 httpx 30s < 单次 LLM 调用 60–90s（已升 120s）+ 登录重试。**实测**：干净单命令启动 OpenLLM **11s healthy**、OpenBase 2–40s。另登记：OpenLLM→DPS 画像调用因 org 别名 `11111111-…` 未在 `OPENLLM_DPS_*_MAP` 覆盖返回 403（配置项，非缺陷）。 |
| v1.0.9 | 2026-10-15 | AA/PM-OpenBase-Dev | **S7-T6-2 冒烟 S0-S6 真实执行推进**：新增可复用运行器 `scripts/smoke_s0_s6.py`（32 例）+ 包装 `scripts/run_smoke_s0_s6.ps1`（跨仓拉起 + 加载 `.env.shared-infra`）；首轮真实执行 `total=32 / PASS 17 / FAIL 8 / PENDING 7`（证据 `doc/test/evidence/s7/smoke/smoke-summary-20261015132711.json`）；已修复环境适配项（组件嵌套/模型选择/召回解析/轮询/登录重试）；因 OpenBase/OpenLLM 启停抖动未取得干净复跑 |
| v1.0.8 | 2026-10-15 | AA/PM-OpenBase-Dev | **真实面已执行（沙箱内跑通）**：查明此前「沙箱网络阻塞」为**误判**——根因是脚本**漏注入 `POSTGRES_URL`**（OpenBase DB DSN 只从进程环境解析，`.env` 不参与），致 `db_url` 回落 `localhost:5432`。脚本加载 `.env.shared-infra` 后一条命令 **`overall_pass=true`**：A OIDC IdP ✅、**B 吊销即时性 ✅（旧 token 401）**、**C 跨租户 A 写 B 读 ✅（B 列表不含 A 集合、B 直取 A 集合 404）**、D 转发链 ✅；证据 `doc/test/evidence/manual/mtauth-realface-20261015.json`；§10.4/§10.5 状态同步 |
| v1.0.7 | 2026-10-15 | AA/PM-OpenBase-Dev | §10.5 登记**跨仓脚本执行**结果：脚本升级为 `-StartServices`（用沙箱共享解释器一键拉起六服务，**含 OpenLLM**）；A/D 复现 PASS；B/C **换解释器后仍同根因阻塞**（证明与解释器无关，为沙箱网络到共享 PG 的持连接被重置）；**SQLite 兜底不可行**（`demo_app` 初始化 SQL 为 PG 专用） |
| v1.0.6 | 2026-10-15 | AA/PM-OpenBase-Dev | §10.5 登记**二次重跑**结果（出网恢复后重试 B/C）：A/D 再次 PASS；B/C **同根因仍阻塞**（`OSError [WinError 64]` + `ConnectionResetError` + `ConnectionDoesNotExistError`，OpenBase 进程到共享 PG 的**持连接被网络重置**，DB 写入 500）。判定为**稳定环境阻塞**，停止重试 |
| v1.0.5 | 2026-10-15 | AA/PM-OpenBase-Dev | §10 补「联调窗口真实面执行单」与脚本指针；登记沙箱内已取得的部分真实面（A OIDC IdP ✅ / D 转发链 ✅；B/C/E 因共享 PG 网络重置 WinError 64 + OpenLLM 不可启动而阻塞）。沙箱内**不填 PASS、不伪造** |
| v1.0.4 | 2026-10-14 | AA/PM-OpenBase-Dev | 新增 §10「OIDC/Redis 吊销面与下游三仓数据面隔离清查（2026-10-14）」：① 清查 A（真实 IdP/Redis 面：结构面 PASS／真实面 PENDING）；② 清查 B（下游三仓数据面：D1–D20 + 4 裁定已闭环，A 写 B 读实证待授权）；③ **跨仓生产开关下发清单**（OpenMemory/DPS/OpenLLM 生产者开关 + 载体现状）；④ 处置与遗留。同步登记 OpenMemory 载体补齐提交 `934e34e`（三远程一致） |
| v1.0.3 | 2026-10-09 | AA/PM-OpenBase-Dev | 状态刷新：§4.1 批次表 C3 由「未实施」更新为「**第一阶段（契约与登记）已完成**」；§7.1 未决项 7 同步；新增契约制品 `config/identity_exemptions.json`（豁免治理单一事实源） |
| v1.0.2 | 2026-10-09 | AA/PM-OpenBase-Dev | 状态刷新：§4.1 批次表 C4/C5 由「已写入规范、未落地」更新为「**OpenLLM 已落地**」；§7.1 未决项 4/5 同步；登记 OpenLLM `daea828`（v2.16.3，23 passed） |
| v1.0.1 | 2026-10-09 | AA/PM-OpenBase-Dev | 状态刷新：§4.3 增补「强制期模块级灰度」开关行；§7.1 未决项 1 更新为「灰度机制已就位、实际翻转待运行环境」；登记 OpenLLM `6f06198`（v2.16.2，20 passed） |
| v1.0.0 | 2026-10-09 | AA/PM-OpenBase-Dev | 初始创建：五系统六维横评要点、三源模板与两段式架构、四批路线执行情况总览、接入契约清单与新系统接入 CheckList、未决项与后续迭代建议、风险与教训登记 |

---

## §1 一句话结论

集成形态定为「**中枢签发与准入 + 目标域细粒度裁决**」两段式：

> **OpenBase 作唯一身份权威与模块级准入；四仓作数据面细粒度裁决（档位 + 行控）。中间以「统一协议契约 + 统一码空间登记 + 统一错误码映射」连接。四仓不各自签发身份、不各自定义租户码语义。**

模板不选单一系统，采纳**三源模板**：

| 来源 | 贡献 | 采纳内容 |
|------|------|---------|
| **OpenMemory** | 授权与隔离维度最完整 | 授权模型主模板：RBAC + ABAC + 行控豁免治理 + 档位 + 双维行控 + 物理命名空间；**生产强制写成启动门禁** |
| **DPS** | 租户治理最完整 | 租户治理主模板：真实组织/租户表 + 存在与启停校验 + 码↔UUID 双形态规范化 + 401/403 语义 |
| **OpenBase** | 集成中枢 | 唯一身份权威 + 统一权限码体系 + 跨系统映射登记 + 唯一出站装配点 |

---

## §2 五系统现状横评（六维）

### 2.1 定位与短板（一句话）

| 系统 | 定位 | 主要短板（收口前） |
|------|------|-------------------|
| **OpenBase** | 集成与准入中枢（保留主导权） | `token_version` 吊销未强制、主体验证 DB 不可达 fail-open、入站头过渡期未退出 |
| **OpenLLM** | 欠账最多、优先收口 | **双套 RBAC 均未接线**（审计假象，P0）；主 JWT 无租户 claim；无租户标识不拒绝 |
| **OpenRAG** | 需补治理与接线 | **无租户注册表**；`RBACEngine` 未接线；无入站 JWT（靠网关） |
| **OpenMemory** | 授权主模板 | 无吊销能力；组织策略内存 + DB 双源有漂移风险 |
| **DPS** | 租户治理主模板 | `X-API-Key` 语义陷阱（非凭证）；无吊销；演示用户硬编码、无用户表 |

### 2.2 六维关键差异（浓缩）

| 维度 | 关键判读 |
|------|---------|
| **认证** | 仅 OpenBase 与 OpenMemory 具备「两种凭证叠加（AND）」与「吊销」；OpenRAG 连入站 JWT 都没有；**DPS 的 `X-API-Key` 不承担认证**（语义陷阱） |
| **受信入站** | **四仓是同构设计的多次落地**（同一白名单 + 四身份头 + 三开关），差异只在「生产是否强制」；**仅 OpenMemory 把生产强制写成启动门禁** |
| **多租户** | 事实源在 OpenBase（`tenants.code`），但**执行权威分散**；OpenRAG 无租户表；DPS 与 OpenBase 各有真表且**码空间隔离**（靠 `dps_code_map` 桥接，即 R-387 同源问题） |
| **授权** | **最大欠账 = 「存在但未接线的授权引擎」**（OpenLLM 两套、OpenRAG 一套）→ 审计误以为「有 RBAC」，实际路由仅管理员粗判（典型设计-实现偏差） |
| **失败语义** | 「过渡期 fail-open（忽略 + 标注 + WARN）」是四仓**有意过渡段**；风险在于**缺统一退出计划与生产门禁**；OpenMemory / DPS 的 fail-closed 倾向最强 |
| **数据模型与错误码** | 响应体：OpenBase / OpenMemory / DPS **三家同构**（`{code,message,detail,request_id}`）；OpenRAG / OpenLLM 各一套（短码 + 数值码）。**语义相同、字面量不同**，跨系统排障需归因矩阵 |

---

## §3 目标架构与设计原则

### 3.1 五条设计原则

| # | 原则 | 要点 |
|:-:|------|------|
| P1 | **单一身份权威** | 只有 OpenBase 签发主体；四仓只做「受信入站 + 本地档位解释」 |
| P2 | **协议契约唯一** | 四头 + 链路口 + 白名单 + 三开关为强制契约，默认值与生产强制统一 |
| P3 | **码空间登记唯一** | `tenants.code` 为唯一事实源；各目标域「可接受码 / 保留码 / 兜底码 / 映射」以**登记表**声明，**禁止散落字面量** |
| P4 | **两段式授权职责** | 网关侧做模块级准入（权限码 `module:action`）；目标侧做数据面细粒度裁决（档位 + 行控/所有权）；两侧共用同一「角色档位」语义 |
| P5 | **拒绝可观测统一** | 统一错误码命名空间 + 统一响应体 + 归因矩阵（网关码优先，上游 4xx/5xx 归上游） |

### 3.2 目标架构（四层）

```
L1 身份权威层（OpenBase 独占）
   · 凭证：本地 JWT / OIDC / ob_k_ 服务 Key / sk-agent-*
   · 主体模型：subject_type{user,agent,service,guest} + credential_type
   · 吊销：token_version（强制）+ agent key status + 生命周期状态机
   · 权限码权威：module:action + "*"；角色→权限映射（种子幂等）

L2 协议契约层（五系统共同遵守；OpenBase 为唯一出站装配点）
   · 四头 + X-Proxy-Source + X-Request-Id；白名单；strip/enforce/org-alias
   · 角色档位统一：readonly < readwrite < manage
   · 生产门禁统一：生产必须 enforce=True（照搬 OpenMemory 启动校验）

L3 码空间登记层（OpenBase 登记，目标域执行）
   · proxy_code_map{ target, source_of_truth, mappings[], accepted_codes,
                    reserved_codes, default_code }
   · 由 dps_code_map 通用化而来；R-387 的「按目标登记」并入此表

L4 数据面裁决层（各目标域自治，OpenBase 不越权）
   · 租户治理：租户注册表 + 状态（存在/启停）→ 照搬 DPS 语义
   · 数据面授权：档位守卫 + 行控 (tenant_code[, owner]) + 豁免治理
   · 目标域可保留自有 RBAC/ABAC，但【必须接线】
```

### 3.3 关键设计决策（D1~D6）

| # | 决策 | 结论 |
|:-:|------|------|
| D1 | 身份权威归属 | **OpenBase 独占**（各仓自治会导致主体语义分裂） |
| D2 | 授权职责划分 | **两段式**（网关全权会让网关须懂各域数据规则；目标域全权会缺模块级准入） |
| D3 | 租户治理模型 | **OpenBase 权威 + 目标域登记（同步）**（DPS 已真有表不能废弃；OpenRAG/OpenMemory 缺注册表需补） |
| D4 | 档位语义 | **统一档位 readonly/readwrite/manage + 登记式锚点表**（四仓已同构三档，只差统一锚点与线上接线） |
| D5 | 豁免治理 | **上升为通用机制**（票据 + 审批人 + 有效期 + 审计），与 OpenBase `k03_bypass_whitelist` 合并为一种 |
| D6 | 错误码统一 | **统一码 + 目标域短码映射表**（不改上游行为，避免跨仓破坏性变更） |

---

## §4 执行情况总览（截至 2026-10-09）

### 4.1 批次总览

| 批次 | 项 | 内容 | 状态 |
|:----:|:--:|------|:----:|
| **A** | A1 | `dps_code_map` 登记模式通用化为 `proxy_code_map`（保留码/兜底码/覆盖/校验单一入口） | ✅ 已完成 |
| **A** | A2 | R-387「按目标登记」并入 `proxy_code_map`，删除散落配置项 | ✅ 已完成 |
| **A** | A3 | 统一**角色档位锚点表**（登记式 JSON）供四仓消费 | ✅ 已完成 |
| **A** | A4 | 统一**错误码映射表**（对齐 R-384 归因矩阵） | ✅ 已完成 |
| **A** | A5 | 统一**协议契约与开关默认值**说明（含生产强制与过渡期退出计划） | ✅ 已完成 |
| **B** | B1 | **OpenLLM** 双 RBAC 收口：保留 DB RBAC 并接入路由；配置式 RBAC 显式 deprecated | ✅ 已闭环 · 已验收 |
| **B** | B1 配套 | 权限播种 + 影子期观测制品；**前置 DDL 与数据播种解耦**；播种制品**已在共享库执行完成** | ✅ 已闭环（2026-10-09） |
| **B** | B2 | **OpenRAG** `RBACEngine` 收口：**明确弃用而非接线**（消除「有引擎未用」假象） | ✅ 已闭环 |
| **B** | B3 | **四仓**统一档位锚点落地与线上接线 + 负向用例 | ✅ **已闭环（2026-10-09）**：四仓锚点全覆盖 A3 并集（admin/org_admin/user/org_member/viewer）——修复真缺陷 OpenRAG `c3a5b85` / OpenMemory `c73b5bb` 缺 `user` 码；三仓具备「readonly 写 → 403」端点级负向用例；门禁复跑 8 PASS / 0 FAIL |
| **B** | B4 | **OpenBase** `token_version` 吊销生产强制；主体验证 DB 不可达按环境门控 | ✅ 已闭环 |
| **C** | C1-a | **OpenMemory** 组织码登记（`default` / `tenant-1` / `tenant-2`），统一码空间终态切换 | ✅ 已闭环 · 已验收（12/12 PASS） |
| **C** | C1-b | **OpenRAG** 配置驱动租户注册表 + 单一校验入口（不建表） | ✅ 已闭环 |
| **C** | C1-c | **OpenLLM** 缺租户标识不再静默回退 + 主 JWT 补 `tenant_code`（向后兼容） | ✅ 已闭环 |
| **C** | C1-d | 码值规范化统一（照搬 DPS 双形态解析 + 回填） | ✅ **已闭环（2026-10-09）**：`openbase/core/code_normalize.py`（零依赖纯函数，11/11 PASS） |
| **C** | C2 | 码值规范化推广为通用能力 | ✅ **已闭环（2026-10-09）**（随 C1-d 一并收口，可被五系统共用） |
| **C** | C3 | 豁免治理统一（票据+审批人+有效期，以 OpenMemory 为模板，与 `k03_bypass_whitelist` 合并） | ✅ **已闭环（三阶段全部完成，2026-10-13）**：第一阶段契约 `config/identity_exemptions.json`（统一必填字段 + R1~R5，修复 OpenBase k03 `expires_at` 死字段）→ 第二阶段 OpenBase 收紧（`_k03_exemption_active()`）→ 第三阶段各仓对齐（OpenLLM 豁免审计 `5a9a29a`/v2.16.4；OpenMemory DB 落点 v705 迁移 + 装配 `6ecc420`/v7.1.1 + 消费侧 `3f1fa5f`/v7.1.3；三仓字段归一 target/reason） |
| **C** | C4 | 生产门禁统一（生产必须 enforce / fail-closed 写成启动校验） | ✅ **已闭环 · 四仓覆盖（2026-10-09）**：OpenLLM `daea828`/v2.16.3、OpenRAG `a9f0376`、OpenMemory 早已落地（`api/server.py:555`，参照范本）、DPS `00e4820`（`DPS_ENV` + `is_production` + `validate_identity_trust_policy()`） |
| **C** | C5 | 过渡期退出计划（设定退出条件与版本） | ✅ **已闭环 · 四仓覆盖（2026-10-09）**：各仓以 C4 生产门禁作为**机械截止手段**（生产即强制退出过渡态，规避「永久停留」） |
| **D** | D1 | 跨系统授权一致性矩阵（端点 × 主体 × 档位 × 租户 → 期望码） | ✅ 已完成 |
| **D** | D2 | 自动化门禁脚本（协议头/档位锚点/码空间/错误码映射一致性） | ✅ 已完成（复跑 0 FAIL，已纳入回归） |
| **D** | D3 | 负向用例集（匿名写/跨租户读/保留码入站/未受信带头/档位不足） | ✅ **已闭环（2026-10-12）**：六服务运行时负向探针 **18 PASS / 0 FAIL / 0 BLOCKED**，证据 `doc/test/evidence/manual/d3-runtime-negative-20261012.json` |

### 4.2 关键交付物与证据

| 项 | 交付物 / 证据 | 验证结论 |
|----|--------------|---------|
| A1/A2 | `openbase/settings.py`（内置基线 + `proxy_code_map` + 三纯函数）、`openbase/modules/protocol_headers/code_space.py`、编排器改声明 `OPENBASE_PROXY_CODE_MAP` | `ruff` 0 告警；全量回归 **1147 passed / 0 failed / 4 skipped**；行为等值（兜底值未变） |
| A3 | `config/role_tier_anchors.json`（含四仓现状与差异登记） | 被 D2 门禁静态校验 |
| A4 | `config/error_code_map.json`（11 条 + 归因规则） | 44 条字面量全部命中；首跑即抓出 6 条未核实值并修正为 `null` |
| A5 | `doc/design/OpenBase-协议头规范-v1.1.md` | 新增 §2.1 码空间登记 / §3.1 档位契约 / §4.1 生产门禁 / §4.2 过渡期退出计划 |
| B1 | OpenLLM `backend/app/identity/rbac_guard.py`（`require_permission` + 写类档位守卫 + 两段开关）、**15 个端点**接入、`edgerouter/auth/rbac.py` 弃用登记 | 端点级正负用例 **16 passed**（13 原有 + 3 通配护栏）；档位锚点与 `role_tier_anchors.json` 逐项一致 |
| B1 配套 | `doc/design/generated/rbac_seed_ddl.sql`（前置结构变更）、`rbac_seed.sql`（纯 DML）、`rbac_seed_manifest.json`；生成器 `scripts/rbac_permission_seed.py`；影子期观测 `scripts/rbac_shadow_observe.py` | 生成器 TDD 11 例 + `ruff` 全绿 + 重跑 diff=0；**已在共享库执行**：roles=5 / permissions=27 / role_permissions=34 / user_roles=0，幂等复跑新增 0 行 |
| B2 | OpenRAG `rbac_engine.py` 静态登记 `DEPRECATED` / `DEPRECATED_REASON` / `REPLACEMENT_PATH` + 类标记 `__deprecated__` | 11 例（含「请求路径零引用」护栏）；基线 failed/errors **47/40 → 47/40 零增长** |
| B4 | OpenBase 主体验证 DB 不可达**按环境门控** + `OPENBASE_PRINCIPAL_DB_DEGRADED_POLICY` + `token_version` 生产强制 | 全量 **1176 passed / 5 failed / 4 skipped**；生产误配 `allow` 拒绝启动 |
| C1-a | 编排器声明 `OPENMEMORY_RBAC__ORG_POLICIES`（**未改 OpenMemory 仓代码、未放宽其 fail-closed**）+ 本仓统一码空间终态切换 | **12/12 PASS**；受信入站 `tenant-1` 由 403 转 200；未登记码仍 403 |
| C1-b | OpenRAG 配置驱动租户注册表 + 单一校验入口 | 21 例；基线失败数零变化；保留码防护未放宽 |
| C1-c | OpenLLM 缺租户标识显式化 + 主 JWT 补 `tenant_code` | 16 例；复跑 B1 未破坏 |
| D1 | `config/auth_consistency_matrix.json`（17 格 × 6 系统 × 8 不变式） | 逐格标注 evidence 类型 |
| D2 | `scripts/cross_repo_auth_gate.py`（9 项检查） | **复跑 0 FAIL**；纳入回归 `tests/test_cross_repo_auth_gate.py`（4 例，无兄弟仓时自动跳过） |

### 4.3 生产门禁与两段推进口径（现状）

| 系统 | 影子/观察段 | 强制段开关 | 当前默认 |
|------|------------|-----------|---------|
| OpenLLM（B1） | `RBAC_PERMISSION_SHADOW`（只审计不拒绝，日志 `rbac_decision=would_deny`） | `RBAC_PERMISSION_ENFORCE` | 代码默认 SHADOW=**True** / ENFORCE=**False**；**运行侧已全模块强制（2026-10-13）** |
| OpenLLM（B1 灰度） | 未纳入灰度白名单的模块仍走影子期 | **`RBAC_PERMISSION_ENFORCE_MODULES`**（灰度白名单；空=全部模块） | 默认**空**；顺序 `user → role → knowledge_base → conversation`；**单模块可独立回滚**；**四模块已全部完成翻转（users 2026-10-12，roles/knowledge_bases/conversations 2026-10-13，回滚验证已通过）** |
| OpenBase（B4） | 非生产：allow + WARN + 留痕 | 生产：fail-closed 503 + 显式白名单 | `OPENBASE_PRINCIPAL_DB_DEGRADED_POLICY` 按环境推导 |
| 其余四仓 | 过渡期「忽略 + 标注 + WARN」 | 生产 enforce（C4 已四仓落地） | **四仓均已写成启动校验（2026-10-09，C4）** |

> **B1 强制期翻转已完成（2026-10-13）**：前置消化（影子期观测补 member 别名后消化率 100%、存量 14 真实用户绑定迁移）→ users 首翻（2026-10-12，57 例探针状态面与影子期逐项相同、结构化 403 契约完整、回滚验证通过）→ roles / knowledge_bases / conversations 三模块灰度翻转（2026-10-13，全 4 模块保持强制态）。兼容层（旧 `get_current_admin_user` 硬门）**退役已交付**（OpenLLM `298fe7d`/v2.17.0，2026-10-13，裁定方案 A 安全耦合；**退役面 = only `users` 端点**）——2026-10-16 跨仓复核曾发现其生产安全耦合实测未生效（F-12：`get_settings()` 生产门禁被 `main.py` 启动自检的 fail-open 兜底吞掉），**已按方案 A 修复并复验**（OpenLLM `ff506e9`/v2.17.2：`assert_startup_gates()` + lifespan 开头无包裹求值；运行态 D1/D2 → `exit=3` 拒绝启动）→ **该项闭环**（详见 §7.1 第 10 项与《S7-冒烟缺陷分派待办单》v1.0.18 §10）。**2026-10-16 完成 phase 5：其余 12 模块 / 40 处旧门全量退役**（OpenLLM `f7c7073`/v2.17.3；新增 10 权限码、生产门禁判据扩展为退役面全集 11 模块；护栏 98 passed、相关回归 239 passed）→ **退役面全量清零**（详见 §7.1 第 10 项与《S7-冒烟缺陷分派待办单》v1.0.19 §10.5）。**2026-10-16 完成 phase 6：同族门 `get_admin_user_or_api_key`（providers / local_models）亦退役**（OpenLLM `da3b834`/v2.17.8；退役面扩至 **13 模块**）→ **含同族门的退役面全量清零**（详见 §7.1 第 10 项与《S7-冒烟缺陷分派待办单》v1.0.24 §10.5）。

---

## §5 接入契约清单（新系统接入必须消费）

> 新系统（第五仓及以后）只要遵循本节，即可与现有五系统对齐；**禁止各自另立一套**。

### 5.1 身份与链路协议（L2）

| 类别 | 契约 |
|------|------|
| **四身份头** | `X-User-ID` / `X-Tenant-ID` / `X-Org-ID` / `X-User-Role`（可选扩展 `X-Agent-Id`） |
| **链路口** | `X-Proxy-Source`（受信来源标识）/ `X-Request-Id`（透传全链路） |
| **受信来源常量** | `openbase-{llm,rag,memory,dps}-proxy`；编排器 `openbase-orchestrator` |
| **三开关** | `strip`（剥离入站身份头）/ `enforce`（强制校验）/ `org-alias`（组织别名）——**默认均 False** |
| **非受信带头默认行为** | 忽略 + 标注（`identity_headers_ignored`）+ WARN 放行 |
| **生产要求** | 生产**必须** `enforce=True`（照搬 OpenMemory `validate_*_policy` 启动校验）；误配拒绝启动 |
| **过渡期退出** | 「忽略 + 标注 + WARN」须设定退出条件与版本（协议头规范 v1.1 §4.2：**两个版本内强制**） |

### 5.2 角色档位（L2 / L4 共用）

- 档位序：**`readonly` < `readwrite` < `manage`**（写类方法要求 ≥ `readwrite`）。
- 锚点单一事实源：`config/role_tier_anchors.json`（新系统**只消费，不另立**）。
- 现网锚点：`admin → manage`；`org_admin → readwrite`；`user` / `org_member` / `viewer → readonly`。
- **未映射角色码必须 fail-closed**（403 `ROLE_UNMAPPED`），禁止静默降级 `readonly`。

### 5.3 权限码与失败语义（L1 / L4）

| 类别 | 契约 |
|------|------|
| 权限码口径 | **`module:action`**（如 `user:read` / `role:admin` / `conversation:write`）；管理类通配 `*` |
| 通配语义 | `*` **只在权限判定（G1）中作「放行全部」**，**不参与档位校验（G3）**——`readonly` 角色持 `*` 写仍 403 |
| 服务账号/匿名写 | 必须绑定主体；白名单外 fail-closed，统一码 `PERM_SERVICE_KEY_WRITE_DENIED` |
| 统一响应体 | `{code, message, detail, request_id}` |
| 错误码命名空间 | `AUTH_*` / `PERM_*` / `BIZ_*` / `SYS_*` / `PARAM_*` / `STORAGE_*` |
| 错误码映射 | `config/error_code_map.json`（目标域短码 ↔ 统一语义码 ↔ 归因层），**不改上游行为** |

### 5.4 租户与码空间（L3 / L4）

| 类别 | 契约 |
|------|------|
| 事实源 | `tenants.code`（OpenBase 为权威）；目标域**登记同步** |
| 登记方式 | `OPENBASE_PROXY_CODE_MAP` / `proxy_code_map{target, accepted_codes, reserved_codes, default_code, mappings[]}`——**禁止散落字面量** |
| 保留码 | 各目标域声明；**保留码必须拒绝**（如强校验期 400） |
| 兜底码约束 | **兜底码不得为该目标的保留码**，且须已被目标系统登记（不变式 I7） |
| 未知租户语义 | 照搬 DPS：**401 缺标识 / 403 组织不存在或停用**（不得静默回落） |
| 逐目标示例 | memory：`{default, tenant-1, tenant-2}`；llm / rag：保留码 `{default, openrag-local}` |

### 5.5 数据落点（共享基础设施实测口径）

> **局域网内共享基础设施为唯一数据库**：`192.168.0.151:5432/nuct`（PostgreSQL 14.23）。

| 系统 | 库/schema | 权限模型要点 |
|------|-----------|-------------|
| OpenBase | `openbase` schema | `roles`/`permissions`/`user_role`/`role_permission`；关联表键类型 **bigint** |
| OpenLLM | `public` schema | `roles`/`permissions`/`role_permissions`/`user_roles`；主键 **uuid**；`permissions` 四字段并存（`code`/`resource_type`/`action`/`scope`） |
| 第三方 | `platform` schema | 权限模型与上二者**互不相同** |

**跨系统数据变更纪律**（教训登记）：变更前**必须先核实目标表结构与库落点**；本次已就此把生成期**档案校验 + 落点断言**内置到播种生成器，使「写错 schema / 键类型不符」成为**生成期硬失败**。

---

## §6 新系统接入 CheckList

> 适用：第五仓及以后的任何自研后端系统。建议按序执行，每步产出可验证证据。

### 阶段一：受信入站与身份解释（L2）

- [ ] 接入**四身份头 + 链路口**，实现 `X-Proxy-Source` 白名单校验。
- [ ] 实现**三开关**（strip / enforce / org-alias），默认 `False`，并在日志中标注「忽略 + 标注 + WARN」。
- [ ] 实现**本地档位解释**：消费 `config/role_tier_anchors.json`，**未映射角色 fail-closed**。
- [ ] 生产环境**启用启动门禁**：生产必须 `enforce=True`，否则拒绝启动。

### 阶段二：租户治理（L3 / L4）

- [ ] 接入**租户注册表**（或订阅 OpenBase 权威源），实现「存在 + 启停」校验。
- [ ] 缺租户标识/未登记租户 → **显式 401/403**，**禁止静默回落保留码**。
- [ ] 声明本目标的**保留码 / 兜底码 / 可接受码**，登记到 `proxy_code_map`（禁止散落字面量）。
- [ ] 兜底码不得为本目标保留码（不变式 I7）。

### 阶段三：授权接线（L4，**必须真实接线**）

- [ ] 选定**一套**授权引擎并**接入请求路径**（另存的一套必须显式弃用登记：`DEPRECATED` + 替代路径）。
- [ ] 路由挂载权限码判定（`module:action`），覆盖**受保护端点 100%**。
- [ ] 写类方法叠加**档位守卫**（≥ `readwrite`）。
- [ ] 服务账号/匿名写 fail-closed（`PERM_SERVICE_KEY_WRITE_DENIED`）。
- [ ] 端点级**正负用例**（有码 2xx / 缺码 403、readonly 写 403、未映射 403），断言**非软断言**。
- [ ] 两段推进开关（影子期 → 强制期），影子期输出「将被拒」结构化日志。

### 阶段四：契约对齐与门禁

- [ ] 统一响应体 `{code, message, detail, request_id}`；错误码按命名空间，并在 `config/error_code_map.json` 登记映射。
- [ ] 纳入跨仓静态门禁 `scripts/cross_repo_auth_gate.py`（协议头/档位锚点/码空间/错误码映射 9 项检查）。
- [ ] 补**负向用例集**（匿名写 / 跨租户读 / 保留码入站 / 未受信带头 / 档位不足）。
- [ ] 授权接线覆盖率写入设计评审；D1 一致性矩阵**零「未定义」格**。

---

## §7 未决项与后续迭代建议

### 7.1 未决项（按优先级；2026-10-16 经台账 v1.16.33 逐项核对刷新）

| # | 项 | 状态（2026-10-16） | 证据锚点 |
|:-:|----|--------------------|---------|
| 1 | **B1 强制期开启**（`RBAC_PERMISSION_ENFORCE` + `RBAC_PERMISSION_ENFORCE_MODULES` 灰度） | ✅ **已完成（2026-10-13）**：影子期消化率 100% 后按 `user → role → knowledge_base → conversation` 逐模块翻转，**全 4 模块保持强制态**；users 首翻 2026-10-12（57 例探针、结构化 403 契约完整、回滚验证通过），其余三模块 2026-10-13 | 台账 §10.3 B1 行；修订历史 v1.9.18/v1.16.16 |
| 2 | **B3 四仓档位锚点落地** + 负向用例 | ✅ **已闭环（2026-10-09）**：四仓锚点全覆盖 A3 并集；修复 OpenRAG `c3a5b85` / OpenMemory `c73b5bb` 缺 `user` 码；门禁复跑 8 PASS / 0 FAIL | 台账 §10.3 B3 行 |
| 3 | **D3 负向用例集**（五仓统一覆盖率） | ✅ **已闭环（2026-10-12）**：运行时负向探针 **18 PASS / 0 FAIL / 0 BLOCKED** | `doc/test/evidence/manual/d3-runtime-negative-20261012.json` |
| 4 | **C4 生产门禁落地**（各仓启动校验） | ✅ **已闭环 · 四仓覆盖（2026-10-09）**：OpenLLM `daea828`、OpenRAG `a9f0376`、OpenMemory 早已落地、DPS `00e4820` | 台账 §10.3 C4/C5 行 |
| 5 | **C5 过渡期退出**（两个版本内强制） | ✅ **已闭环 · 四仓覆盖（2026-10-09）**：各仓以 C4 生产门禁作机械截止（生产即强制退出过渡态） | 同上 |
| 6 | **C1-d / C2 码值规范化**（DPS 双形态解析推广） | ✅ **已闭环（2026-10-09）**：`openbase/core/code_normalize.py`（零依赖纯函数，11/11 PASS） | 台账 §10.3 C1-d/C2 行 |
| 7 | **C3 豁免治理统一**（票据+审批人+有效期） | ✅ **已闭环（三阶段全部完成，2026-10-13）**：契约 → OpenBase 收紧（修复 `expires_at` 死字段）→ 各仓对齐（OpenLLM 审计 `5a9a29a`；OpenMemory DB 落点 + 消费侧 `3f1fa5f`/v7.1.3；三仓字段归一） | 台账 §10.3 C3 行 |
| 8 | **DPS 自身 IAM 演进**（吊销 / 用户表 / `X-API-Key` 语义澄清） | ⬜ **仍为规划中项**（**2026-10-16 裁定 D：维持**——其版本规划排期，**不立项实施**） | 依赖 OpenBase 总线 |
| 9 | **OpenMemory 组织策略双源漂移**（内存 `_org_registry` + DB 表） | ✅ **已完成（P0~P4，2026-10-12，`68701e9`+`26dc728`）**：policy JSONB 列 → 影子读比对 → 切换读（TTL≤60s）→ 切换写 → 退役 default 兜底（fail-closed）；全量 1366 passed | 台账 §10.3 未决项 9 行 |
| 10 | **L3 / B1 兼容层退役**（`users` 端点旧管理硬门退役的生产安全耦合） | ✅ **已闭环（2026-10-16）**：退役本体已落地（OpenLLM `298fe7d`/v2.17.0；43 例护栏/接口用例通过）**+ 生产安全耦合经 F-12 修复恢复效力**（OpenLLM `ff506e9`/v2.17.2，方案 A：`assert_startup_gates()` + `main.py` lifespan 开头无包裹求值；运行态探针 `overall_pass=true`，D1/D2 → `exit=3` 拒绝启动；相关回归 58 passed）。**残量已清零**：其余 12 模块 / 40 处旧门已于 **B1 D4 phase 5 全量退役**（OpenLLM `f7c7073`/v2.17.3：`app/api/` 旧门调用点归零、新增 10 权限码、生产门禁判据扩展为退役面全集 11 模块；护栏 98 passed、相关回归 239 passed / 0 failed）。**phase 6（2026-10-16）：同族门 `get_admin_user_or_api_key` 亦退役**（OpenLLM `da3b834`/v2.17.8：`providers.py` / `local_models.py` 2 文件 / 12 处 → `require_permission(provider:write / local_model:write)`；退役面扩至 **13 模块**；护栏 43 例、合并回归 171 passed / 0 failed）→ **退役面（含同族门）全量清零**；**死定义与再导出亦已于 2026-10-16 清理**（OpenLLM `f477d1e`/v2.17.9：整段移除 `get_current_admin_user` / `get_admin_user_or_api_key` 及 `app.services` 再导出，护栏 3 例＋回归 **216 passed / 0 failed**）→ **旧管理硬门「符号零残留」** | `doc/test/evidence/manual/{b1-compat-retire-openllm-20261016.json,b1-phase5-retire-openllm-20261016.json}`（均 `overall_pass=true`，含 `open_items.O1~O6`）；《S7-冒烟缺陷分派待办单》v1.0.18 §10 + v1.0.19/v1.0.24/v1.0.25 §10.5 |

### 7.2 迭代建议

1. ~~先收口强制期，再扩面~~ **B1 强制期已全模块翻转完成（2026-10-13）**：「有 RBAC 不生效」的审计假象已消除；后续扩面动作以「新端点/新仓先过门禁」为基线。
2. **门禁先行**：任何新增仓/新增端点，先过 `cross_repo_auth_gate.py` 与 D1 矩阵，避免契约再次漂移。
3. **契约变更走登记**：凡涉及头名/档位/码空间/错误码，**必须改登记表并过门禁**，禁止仓内硬编码。
4. **过渡态必须有截止**：任何「忽略 + WARN」的兼容分支都要写退出条件与版本（C5），否则会永久停留。
5. **跨系统写操作前先探明落点**：沿用「先侦察后执行」纪律（已内置为生成期硬失败机制）。

---

## §8 证据与索引

| 主题 | 首选查阅 |
|------|---------|
| 台账（唯一事实源，内容版本 v1.9.4） | 《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》§1 结论 / §2 六维比对 / §3 模板选型 / §4 架构 / §5 差距 / §6 四批路线 / §7 裁定 / §9 派单台账 / §10 跨仓实施记录 |
| B1 派单与回执（含播种交付与执行回执） | 《OpenBase-B1派单-OpenLLM授权接线-v1.0.0》§6.2 / §6.3 |
| 播种执行前置与决策点 D1~D4 | 《OpenBase-B1-播种SQL评审与执行预检说明-v1.1.0》 |
| 生产化配套（播种 + 影子期观测） | 《OpenBase-B1-生产化配套-权限播种与影子期观测-v1.2.0》 |
| 协议契约（头/档位/门禁/退出计划） | 《OpenBase-协议头规范-v1.1》 |
| 派单件 | `doc/planning/OpenBase-C1派单-租户注册表对齐-v1.0.0.md` |
| 机械可校验制品 | `config/role_tier_anchors.json`、`config/error_code_map.json`、`config/auth_consistency_matrix.json`、`scripts/cross_repo_auth_gate.py` |
| 播种制品 | `doc/design/generated/rbac_seed_ddl.sql`、`rbac_seed.sql`、`rbac_seed_manifest.json`；目标仓镜像 `OpenLLM/backend/scripts/rbac_seed/` |

---

## §9 风险与教训登记

### 9.1 已知风险

| # | 风险 | 等级 | 缓解 |
|:-:|------|:----:|------|
| R1 | 跨仓改造工期不可控（各仓各自立项） | 高 | A/D 批本仓可独立交付；B/C 批拆到单仓最小可交付单元 |
| R2 | 强制 fail-closed 后暴露存量「无档位/无租户」调用方 | 高 | 先影子期（只审计不拒绝）→ 再强制；保留带有效期的豁免白名单 |
| R3 | 统一码空间触发数据可见性变化（R-387 已实测：`default` 桶不可达） | 中 | 逐目标登记 + 后果登记 + 一键回滚（已有先例） |
| R4 | 错误码映射表与上游实际码漂移 | 中 | D2 门禁静态校验 + 上游 `detail` 契约 |
| R5 | RBAC 收口改动既有行为 | 中 | 先补负向用例与影子观测，再切换 |

### 9.2 教训登记（可复用的工程纪律）

| # | 教训 | 规则化 |
|:-:|------|--------|
| L1 | **配置源优先级**：`.env` 优先于代码默认值，改默认值而未改 `.env` 会导致验收失败 | 凡 `Settings` 默认值变更，**必须同时检索并修改 `.env*` 同名覆盖项**；`config_default` 类变更的验收须含「有效值断言」（读实例值） |
| L2 | **跨系统数据变更前必须核实目标表结构与库落点** | 生成器内置**档案校验 + 落点断言**，使错 schema / 键类型不符成为**生成期硬失败** |
| L3 | **`pg_constraint` 不含索引型唯一约束** | 核查 `ON CONFLICT (col)` 前提时须查 `pg_indexes`（`ix_roles_code` / `ix_permissions_code` 即为索引型唯一约束），勿据 `pg_constraint` 误判为「缺失」 |
| L4 | **窄口径验证会掩盖整组失败** | 凡触及鉴权主链路的改动，验收**必须以全量回归为判据**，不得以筛选后的子集宣称通过 |
| L5 | **测试环境机制先查仓内既有约定** | 本仓 `OPENLLM_TEST_EXTRAS` 早已预留 cp313 原生扩展目录，无需外部造环境 |

---

## §10 OIDC/Redis 吊销面与下游三仓数据面隔离清查（2026-10-14）

> 依人工指令「真实 IdP（OIDC）/ Redis 吊销面隔离走查 和 下游三仓数据面租户隔离（OpenLLM/OpenRAG/OpenMemory）都需要在这里跨仓梳理并清查解决」，按「只读取证 → 统一登记 → 生产开关处置」收敛。本节为**汇总视图**，PENDING 项**不填 PASS**；一律以其上游单一事实源（S7 总收官报告 / 跨仓数据面租户隔离走查报告）为准。

### 10.1 清查 A：真实 IdP（OIDC）/ Redis 吊销面

| 维度 | 结论 | 证据 |
|------|------|------|
| 结构面（沙箱可判定） | ✅ **PASS** —— RA-06 聚合 **82 用例**：双租户隔离 19 / fail-closed 21 / **OIDC 批次 12** / 委托跨界 13 / **吊销即时性 17** | `doc/test/evidence/s7/gate/gate-aggregate.json` §RA-06；`scripts/gate_aggregate.py` |
| 真实面（联调窗口） | ⏳ **PENDING** —— 真实双租户数据面 / **真实 IdP** / **真实 Redis 吊销** 未执行 | S7 总收官报告 §4.2 |
| 关联断言 | S7-T6-1（RA-06 五项真实面）、S7-T6-2（冒烟 S0-S6 真实执行）、S7-T1-3（K13 真实授权与跨 schema 写拒绝）、S6 B3/B4（真实双租户数据面 / 真实 IdP 回调与吊销） | 同文 §4.1/§6 |
| 前置条件 | 真实 PG/Redis + **IdP** + 四仓运行态（责任方：联调窗口） | 同文 §4.2 |
| 脚本就绪度 | ✅ 已就绪（`verify_l1_1_cascade.ps1`、`verify_l3_1_agent.ps1`、`gate_aggregate.py`），**只差实跑 + 回填证据** | `scripts/` |

**判定**：OIDC/Redis 面为**验证欠账（PENDING）**，非生产阻塞；真实面须在联调窗口执行并回填证据后，方可由 [Review] 升 [Approved]。

### 10.2 清查 B：下游三仓数据面租户隔离（OpenLLM/OpenRAG/OpenMemory）

| 维度 | 结论 |
|------|------|
| 走查与修复 | ✅ **已闭环** —— D1–D20 高危 7 + 中危 10 已按仓依次修复；4 项裁定 A/B/C/D 已落地四仓（见《OpenBase-跨仓数据面租户隔离走查报告》v1.3.1 §4.4/§6.6） |
| 低危 | D5（OpenRAG 异常未映射）、D15（DPS `TenantManager` 桩实现）**保持登记**（未在指令范围） |
| 破坏性实证 | ⏳ **未执行** —— 「A 租户写 / B 租户读」需下游登记两套租户并写数据，属破坏性/需授权操作（走查报告 §5.2 登记） |
| 落地后遗留 | 见 §10.3 与走查报告 §6.6（六项，含「生产开关未下发」） |

### 10.3 跨仓生产开关下发清单

> 「生产开关未下发」= 各仓新增的**生产强制门禁开关**必须由运维在**目标环境 `.env`** 显式置真，否则该仓**生产启动被拒**（门禁 fail-closed 本意，**部署当场失败**）。`.env` 被 `.gitignore` 排除，仓库侧只需保证「**模板 + 文档**」登记到位。

| 仓 | 生产必需开关 | 仓库载体（模板/文档） | 生产值 | 载体现状 |
|----|-------------|---------------------|:-----:|:-------:|
| **OpenMemory** | `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE` | 根 `.env.example` + `deployments/docker/.env.example` + 变更记录 §8 | `true` | ✅ **已补齐（2026-10-14，`934e34e`）** |
| **DPS** | `TENANT_CONTEXT_REQUIRED`（+ `MULTI_TENANT_ENABLED`，默认 true） | `doc/operation/DPS-部署文档-v2.1.0.md` §4.2（该仓无 `.env.example`） | `true` | ✅ 已登记（v1.16.30） |
| **OpenLLM** | `TENANT_SCOPE_ENFORCE` / `TENANT_HEADER_CONSISTENCY_ENFORCE` / `QUOTA_MISSING_FAIL_CLOSED` | `.env.example`（三处）+ 运维手册 §7「生产环境启动门禁」 | `true` | ✅ 已登记（v1.16.30） |
| **OpenBase** | 无新增（B4 `token_version` 生产强制 / principal DB 降级环境门控已闭环） | — | — | — |
| **OpenLLM（既有门禁，同属启动门禁）** | `ENFORCE_INBOUND_IDENTITY_HEADERS` / `RBAC_PERMISSION_ENFORCE`（C4/B1） | 同 OpenLLM 载体 | `true` | 既有 |

> **OpenLLM 生产启动门禁（2026-10-16 裁定④：5 组强耦合，**并入本矩阵**）**：上表「本批三项」+「既有两项」= **5 组开关**；`ENV=production` 下**任一为假即拒绝启动**（有意的 fail-closed 设计，**不拆分门禁**）——发布核验须逐项确认。

**处置机制（三件套）**：
1. **载体置真**（模板 + 文档）—— 已按上表登记（本轮补齐 OpenMemory）；
2. **门禁 fail-fast**（护栏）—— 未置真 → 生产装配阶段直接拒绝启动；
3. **发布前核验（强制，2026-10-16 裁定③）**—— 发布/上线检查清单**必须**逐项核验上表「生产必需开关」（含 OpenLLM 5 组），把「拒绝启动」提前到发布门禁，避免部署当场失败。

### 10.4 处置与遗留

| 项 | 状态 | 说明 |
|----|:---:|------|
| 生产开关载体补齐（**已解决**） | ✅ 已闭环 | OpenMemory 载体补齐提交 `934e34e`（origin/backup/github 三端一致）；DPS/OpenLLM 已于 v1.16.30 登记 |
| OIDC/Redis 真实面（含 **吊销即时性**） | ✅ **已执行（2026-10-15）** | 沙箱内 `-StartServices -IncludeDataPlane` 一条命令：OIDC IdP discovery/jwks=200、吊销即时性（旧 token 401）；证据 `doc/test/evidence/manual/mtauth-realface-20261015.json` |
| 下游三仓「A 写 B 读」实证 | ✅ **已执行（2026-10-15）** | 经 rag-proxy：A 建集合=200、**B 列表不含 A 集合**、**B 直取 A 集合=404**；同上证据 |
| 委托跨界 403 真实面（RA-06） | ✅ **已执行（2026-10-16）** | 探针反例自证配对：跨域委托 **403 `PERM_DELEGATION_CROSS_TENANT`** / 同域委托 **200**；user 挂委托 403 `PERM_FORBIDDEN`；证据 `doc/test/evidence/manual/mtauth-delegation-l31-20261016.json` |
| L3-1 agent key 真实面（发放/越权/吊销） | ✅ **已执行（2026-10-16）** | `POST /identity/agents` 发放 200 + 首条 `sk-agent-*`；越权 `identity:manage` 403；吊销即时 200→401；同上证据（**读取面 `/auth/me` 曾因缺陷 F-8 返回 500，已于 `6bf7832` 修复并复验 200**） |
| fail-closed 故障注入真实面（RA-06） | ✅ **已执行（2026-10-16，受控窗口）** | 非破坏性注入（探针实例 DSN 不可达；专用端口 8055）：production → **503 `SYS_503`**（`detail.reason=db_unavailable`）+ ERROR 留痕；development → **200 兼容放行** + WARN 留痕；白名单命中 → **200 放行** + 留痕；production+`policy=allow` / production+`enforce_token_version=false` → **均拒绝启动**。证据 `doc/test/evidence/manual/ra06-failclosed-20261016.json` |
| 冒烟 S0–S6 真实执行（S7-T6-2） | ✅ **已闭环（2026-10-16，第三轮）** | `total=32 / PASS 25 / FAIL 0 / PENDING 7`；证据 `doc/test/evidence/s7/smoke/smoke-summary-20261016005540.json` |
| 各仓门禁仅装配路径生效 | ✅ **已接受边界（2026-10-16 裁定②）** | 直连装配绕过（与既有 C4/row_scope 门禁同款边界）；登记说明，不立项收口 |
| 走查低危 **D5 / D15** | ✅ **已修复（2026-10-16）** | OpenRAG `e2b1ddd`（`TenantScopeRequiredError` → 403 `PERM_FORBIDDEN`）/ DPS `8e27614`（`TenantManager` 桩显式标注 + 反例自证）；见走查报告 §4.3/§6.7 |
| OpenLLM 生产门禁强耦合 5 组开关 | ✅ **已并入生产必需开关矩阵（裁定④）** | 见 §10.3；非缺陷——矩阵化 + 发布强制核验，不拆分门禁 |
| OpenRAG `.devflow/config.json::projectVersion` | ⏳ 保持登记（待 DevFlow 侧同步） | 由 DevFlow 工具维护，手工改恐冲突 |

### 10.5 联调窗口真实面执行（指针）

- **执行单**：《[OpenBase-联调窗口真实面执行单](file:///d:/Trae%20CN/myproject/Dev/OpenBase/doc/planning/OpenBase-%E8%81%94%E8%B0%83%E7%AA%97%E5%8F%A3%E7%9C%9F%E5%AE%9E%E9%9D%A2%E6%89%A7%E8%A1%8C%E5%8D%95-v1.0.0.md) v1.0.0》（前置/步骤/验收判据/证据/风险回滚）。
- **脚本**：`scripts/verify_mtauth_realface.ps1`（覆盖 OIDC IdP / 吊销即时性 / 跨仓转发链 / 跨租户 A 写 B 读；`-StartServices` **跨仓一键拉起六服务**，统一用沙箱共享解释器 `TRAE SOLO CN\...\vm\tools\python`）。
- **沙箱内已取部分真实面（2026-10-15）**：✅ A OIDC IdP（discovery+jwks 200）、✅ D 跨仓转发链（rag/memory-proxy 200）；⏳ B/C 因**共享 PG 连接网络重置**（`OSError [WinError 64]`，两次同结果）阻塞、E 未做、OpenLLM 沙箱内不可启动 —— **PENDING 项不填 PASS**。
- **二次重跑（2026-10-15，出网恢复后）**：✅ A/D 再次 PASS；⏳ B/C **同根因仍阻塞**（`WinError 64` + `ConnectionResetError` + `ConnectionDoesNotExistError`，`/api/v1/users`、`/api/v1/tenants` 写入均 500）。**判定：稳定环境阻塞（沙箱网络到共享 PG 的持连接被重置），停止重试**，留待稳定联调环境执行。
- **跨仓脚本执行（2026-10-15）**：脚本升级为 `-StartServices` → ✅ **一键拉起六服务**（`openllm`/`openbase` 新起、余者在线的跳过）；✅ A/D 复现 PASS。
- **真实面执行完成（2026-10-15，`overall_pass=true`）**：查明此前「沙箱网络阻塞」为**误判**——根因是脚本**漏注入 `POSTGRES_URL`**（OpenBase DSN 只从进程 env 解析）致回落 `localhost:5432`。修复后 **B/C 全绿**：**吊销即时性（旧 token 401）**、**A 写 B 读（B 列表不含 A 集合 / B 直取 A 集合 404）**。证据 `doc/test/evidence/manual/mtauth-realface-20261015.json`；执行单升 v1.2.0 [Approved]。
- **S7-T6-2 冒烟 S0-S6 真实执行（2026-10-15）**：新增运行器 `scripts/smoke_s0_s6.py`（32 例）+ 包装 `scripts/run_smoke_s0_s6.ps1`；首轮真实执行 `total=32 / PASS 17 / FAIL 8 / PENDING 7`（证据 `doc/test/evidence/s7/smoke/smoke-summary-20261015132711.json`）。**启停抖动根因（已查清，非产品缺陷）**：健康检查超时过短（≪ 首健康 ~11–40s）→ 已修 90s；端口残留竞争 → 已加启动前清端口；沙箱**命令结束回收子进程** → 必须原子执行；LLM 调用 60–90s > 原 httpx 30s → 已升 120s。**实测干净启动 OpenLLM 11s healthy**。
- **跨仓派单（2026-10-15）**：《[OpenBase-S7-T6-2 冒烟真实执行-跨仓派单](file:///d:/Trae%20CN/myproject/Dev/OpenBase/doc/planning/OpenBase-S7-T6-2-%E5%86%92%E7%83%9F%E7%9C%9F%E5%AE%9E%E6%89%A7%E8%A1%8C-%E8%B7%A8%E4%BB%93%E6%B4%BE%E5%8D%95-v1.0.0.md) v1.0.0》（OB-DISPATCH-S7T62-SMOKE）——[Draft] 待批准分发；含分仓分发表（OpenBase 宿主 / OpenLLM / OpenRAG / OpenMemory / DPS / 基础设施）、准入判据（服务常驻 + Ollama 就绪 + 环境变量 + 端口空闲）、验收判据（P0 全绿 / P1 登记 / 不伪造）、逐仓回执项与已知环境适配项。
- **L2 RA-06 余项真实面探针（2026-10-16，闭环 4/5）**：原子窗口（`doc/tmp/run_l2_probe.ps1` + `doc/tmp/l2_delegation_probe.py`）真实 HTTP 验证「委托跨界 403 + agent key 面」。**反例自证配对**：B 跨域委托 **403 `PERM_DELEGATION_CROSS_TENANT`** / C 同域委托 **200**（放行）⇒ 跨界不变式真实面达成；A（user 挂 `on_behalf_of` → 403 `PERM_FORBIDDEN`）、D（agent 发放 + 首条 `sk-agent-*` → 200）、F（agent key 越权 `identity:manage` → 403）、G1/G2（吊销即时 200 → 401）全绿。证据 `doc/test/evidence/manual/mtauth-delegation-l31-20261016.json`。**同窗口暴露两项缺陷（P1、阻塞用例数 0，待修复）**：**F-8** `GET /api/v1/auth/me` 对绑租户主体（`tenant_id` 为 int，agent 通道）返回 **500**；**F-9** `POST /api/v1/users` 未派生 `tenant_code` → 同域委托被误判跨界（探针观测项 O 自证）。**余 fail-closed 故障注入 PENDING（需停服，受控窗口待授权）**。
- **S7-T6-2 冒烟第三轮真实执行（2026-10-16，闭环）**：修复包装脚本 `$Args` 自动变量冲突（首轮「服务全灭」根因）+ 新增 ready-gate + 运行器 4 处执行侧适配；**`total=32 / PASS 25 / FAIL 0 / PENDING 7`**（首轮 `17/8/7` → 8 项 FAIL 全绿）。证据 `doc/test/evidence/s7/smoke/smoke-summary-20261016005540.json`；跨仓派单升 v1.0.2（§8 逐仓回执 7 项已勾选）。
- **RA-06 fail-closed 受控窗口故障注入（2026-10-16，闭环）**：**非破坏性注入**（仅探针实例 `POSTGRES_URL → 127.0.0.1:1`；专用端口 8055；共享 PG / 常驻服务未受影响；一条命令内「起→探→停」）。**5 场景全 PASS**：S1 production+DB 不可达 → **503 `SYS_503` / `detail.reason=db_unavailable`** + ERROR `principal verify db degraded; denied (fail-closed)` / `policy_source=env_production`；S2 development+DB 不可达 → **200 兼容放行** + WARN `reason=db_unavailable_env_allow`；S3 production+白名单命中（`users.id`）→ **200 放行** + WARN `reason=db_unavailable_allowlisted`；S4 production+`principal_db_degraded_policy=allow` → **拒绝启动**；S5 production+`enforce_token_version=false` → **拒绝启动**。证据 `doc/test/evidence/manual/ra06-failclosed-20261016.json`（`overall_pass=true`）；探针 `doc/tmp/run_ra06_failclosed.ps1` + `doc/tmp/ra06_failclosed_probe.py`（doc/tmp 被 .gitignore 覆盖）。→ **RA-06 五项真实面 5/5 全闭环**。
- **结论（v1.0.17 刷新）**：真实面（A/B/C/D）**已在沙箱执行通过**；RA-06 余项中「委托跨界」「L3-1 agent key（发放/越权/吊销）」已由 2026-10-16 探针**闭环**，**冒烟 S0-S6 第三轮 `PASS 25 / FAIL 0 / PENDING 7` 闭环**，**fail-closed 故障注入已由 2026-10-16 受控窗口故障注入闭环（5 场景 PASS）→ RA-06 五项真实面 5/5 全闭环**。探针同窗口暴露 OpenBase 侧两项缺陷（**F-8** `/auth/me` 对绑租户主体 500、**F-9** `users` 路径未派生 `tenant_code`），已登记《S7-冒烟缺陷分派待办单》v1.0.13 §8（均 P1、阻塞用例数 0；**v1.0.14：已于 `6bf7832` 按 TDD 修复并验证通过，探针复跑 `overall_pass=true`**）；回填 S7 报告 §4.2（v1.0.10/v1.0.11/v1.0.14）、`gate-aggregate.json`（`aggregate_rerun_20261016`）。

- **F-8 / F-9 修复闭环（2026-10-16，TDD）**：**F-8** `me()` 出参 `tenant_id` 归一为 `str`；**F-9** `create_user` 与 OIDC JIT `_bind_or_create_user` 补齐 `tenant_code` 派生（复用 `auth.resolve_tenant_code`，与 `identity/agents` 口径一致）。**提交 `6bf7832`**；验证：`ruff` 全清、隔离用例全绿（t1 9 / users 7 / oidc 6 / tenant_admin 5 / s7_t7 20 / s7_t8 19 / s7_docs 6 / s7_t6_gate 16）、**仓内分组全量回归 `passed=1118 / failed=0 / skipped=4`**、探针 E 500→200 与 O 403→200（分界证据 `mtauth-delegation-l31-20261016-defect.json` / `-20261016.json`）。
- **预存门禁失败登记（2026-10-16，非本轮引入）**：**F-10**（SHR 受管编排唯一入口门禁：`run_smoke_s0_s6.ps1` / `verify_mtauth_realface.ps1` 3 处直接 `Stop-Process`）、**F-11**（S7 工具骨架门禁 12 项：L1-1/L2-1/L3-1 干跑退出码与证据落盘契约不符）；二者经 `e2c4f25` 基线 worktree 复跑证明改动前即失败；修复方案待裁定（详见《S7-冒烟缺陷分派待办单》v1.0.14 §9）。
- **F-10 修复闭环（2026-10-16，方案 A）**：两脚本服务生命周期全部改经**受管编排唯一入口** `scripts/service-orchestrator.ps1`（`-Action stop|start|stop -Only …`，`-HealthTimeout 240`），自身不再直接终止进程（`Stop-Process`/`Clear-Listener`/本地服务表全部移除）；补 PATH 引导（编排器以裸命令 `python` 启动服务）并转 UTF-8 with BOM。验证：`scan_orchestrator_bypass.py` → `scanned=46 / allowed=1 / disallowed=0 / exit 0`；`tests/test_s7_t1_shr.py` **15 passed**（+t6_gate 合计 31 passed）；**冒烟受管复跑 `total=32 / PASS 25 / FAIL 0 / PENDING 7`**（`smoke-summary-20261016120118.json`，与第三轮逐项一致 ⇒ 行为等价）。→ **F-10 已修复；仅余 F-11 待裁定**。
- **F-11 干跑核对与修复（2026-10-16，夹具自洽化）**：三件 PS 工具（L1-1/L2-1/L3-1）为转发同名 `.py` 运行器的薄包装，`$PythonExe` 默认 `'python'`（有意设计 + `-PythonExe` 覆盖）；**根因＝测试夹具非自洽**（受限环境 PATH 无解释器 → `CommandNotFoundException` 退出 1、运行器未启动、无证据落盘），**工具契约本身已满足**（显式传 `-PythonExe` → `exit=2 / status=PENDING / checks=4`、证据落 `-EvidenceDir`）。修复：`tests/test_s7_tools_skeleton.py` 夹具 PS 分支补 `-PythonExe sys.executable`（断言零改动）；验证 `26 passed`、`ruff` 全清。→ **F-11 关闭；段门禁预存失败清零**。
