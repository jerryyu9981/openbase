# OpenBase-S2-三级回滚演练报告-v1.0.0

| 项目 | 内容 |
|------|------|
| 报告名称 | S2 三级回滚演练（开关级 / 通道级 / 版本级） |
| 报告编号 | OB-S2-DRILL-20261024 |
| 版本 | v1.0.0 |
| 状态 | **[Review]**（离线段闭环；生产实机段待 OPS 回填） |
| 编制日期 | 2026-10-24 |
| 编制人 | FA-OpenBase-Dev（AI 辅助） |
| 上游依据 | 《OpenBase-主备双通道生产上线回滚方案-v1.0.0》§3/§4/§5/§6；《OpenBase-主备双通道生产上线必办事项清单-v2.2.0》S2 |
| 演练代码基线 | `648872afeef3e5f47f73bbcb2647b9df6f071130`（2026-10-24 17:32 +0800） |
| 证据目录 | `doc/test/evidence/s2/**`；汇总 JSON `doc/test/evidence/s2/s2-rollback-drill-20261024.json` |

## 修订历史

| 版本 | 日期 | 编制人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-24 | FA-OpenBase-Dev（AI 辅助） | 首次产出：L1/L2/L3 三级演练执行与证据归档；11 项 PASS、3 项 PENDING（生产实机段）、0 FAIL；登记 D-01/D-02 |

---

## 1. 目的与范围

- **目的**：验证回滚方案 §4 的三级动作在**可执行层面**成立，并区分「本机可判定面」与「必须生产运行态」的部分，避免以离线结论冒充生产演练。
- **范围**：
  - **L1 开关级**：生产门禁组与租户强制段开关的「置回 → 拒绝启动 / 置真 → 可装配」双向语义；
  - **L2 通道级**：真实通道状态机 `ChannelStateManager` 的 B→A 接管、A 断维持、单主路径、回切与审计留痕；
  - **L3 版本级**：回退目标定位、检出可执行性、纯代码回滚判定、回退后校验工具可用性。
- **不在范围**：事件通道（L1-1，Q-S7-4）；数据面结构回退（本批无迁移）。

## 2. 执行环境与限制

| 项 | 内容 |
|----|------|
| 宿主 | Windows 本机开发面，**无生产部署面**（8010/8011/8012/8013/8000/8766/5173 均无监听） |
| 解释器 | `D:\PostgreSQL\17\pgAdmin 4\python\python.exe`（3.13），经 `doc/tmp/pyrun.py` 注入 `.venv` 依赖与源码根 |
| OpenLLM 测试 | 追加 `DATABASE_URL=sqlite:///:memory:`，**仅规避本机 psycopg pq 驱动缺失**，用例不触库 |
| 纪律 | 禁伪造：凡需真实运行态/注故障窗口的项一律 `PENDING` 并写明原因，不填 PASS；不裸 `Stop-Process` |

## 3. L1 开关级（离线可判定面）

| # | 判据 | 方法 | 结果 |
|:-:|------|------|:----:|
| S2-L1-1 | OpenLLM 生产门禁组：任一开关回落即拒绝启动；全开通过 | `pytest tests/unit/test_production_gate_tenant_isolation.py test_c4_production_enforce_gate.py test_f12_startup_gate_runtime.py` | **PASS（15 passed）** |
| S2-L1-2 | OpenBase 生产门禁：token 版本强校验 / DB 降级 / 行缺失 / 登录租户策略 | `pytest tests/test_b4_security_hardening.py tests/test_q5_q6_decisions.py -k "production or tenant"` | **PASS（14 passed / 23 deselected）** |
| S2-L1-3 | OpenMemory 强制段：生产 M2 未开 `require_tenant_scope` 拒绝装配 | `pytest tests/unit/test_production_tenant_scope_gate.py`（`.venv3` 3.11.9） | **PASS（7 passed）** |
| S2-L1-4 | 开关值可双向核验（`--env-file` 覆盖生效） | 同一开关两侧取值比对 | **PASS**：演练 env PASS / 开发 `.env` FAIL |
| S2-L1-5 | 生产实机：备份 `.env` → 置回 → 受管编排重启 → `/health` → 恢复 | 需生产面 | **PENDING（待 OPS）** |

覆盖的 5 组门禁：`ENFORCE_INBOUND_IDENTITY_HEADERS` / `RBAC_PERMISSION_ENFORCE` / `TENANT_SCOPE_ENFORCE` / `TENANT_HEADER_CONSISTENCY_ENFORCE` / `QUOTA_MISSING_FAIL_CLOSED`。

**关键语义实证**：门禁开关「置回上线前值」不是无害动作 —— 生产环境下会直接**拒绝启动**（回滚方案 §7.1 风险 1 的具体表现）。因此 L1 回退门禁必须与「临时接受门禁缺失」的授权一并决策，不能作为无感操作。

证据：`doc/test/evidence/s2/l1-20261024/{openllm-gates,openbase-gates,openmemory-gate}.txt`；`doc/test/evidence/release/switch-envfile-{rehearsal,local}-20261024.json`。

## 4. L2 通道级（真实状态机驱动）

驱动面：OpenLLM `app.identity.channel.ChannelStateManager`（S4-T7 落点），经 `scripts/drill_l2_1_failover.py` 真实执行。

| # | 判据 | 结果 | 实测 |
|:-:|------|:----:|------|
| S2-L2-1 | B 断 → A 接管 | **PASS** | 连续 3 次组件降级达阈值 → `failover=true`，`route b→a`；写路径仅 A 允许、经 B 写被拒 |
| S2-L2-2 | A 断 → B 维持 | **PASS** | `route b→b`，`auto_failover=false`，备不可用不影响主 |
| S2-L2-3 | 单主路径（禁双主双写） | **PASS** | initial `['b']` / after-failover `['a']` / after-switch-back `['b']` |
| S2-L2-4 | 回切链路与报告字段齐备 | **PASS** | 审计 6 动作齐全、缺失 0；`single_primary=true` |
| S2-L2-5 | 生产运行态复位 + 写路径恢复（V2/V3） | **PENDING** | 需真实通道运行态与 `/openllm/v1/health` 快照 |

证据：`doc/test/evidence/s2/l2-1-20261024/failover-drill.json` + `drill-report.md`（统一退出码 0=PASS）。

## 5. L3 版本级

| # | 判据 | 结果 | 实测 |
|:-:|------|:----:|------|
| S2-L3-1 | 回退目标可定位 | **PASS** | 双通道批次前基线 `e2c4f25`（2026-10-15）；最近发布标签 `v1.4.10` = `2c45a32`（2026-10-02） |
| S2-L3-2 | 回退动作可执行 | **PASS** | `git worktree add --detach` 检出基线成功（1896 文件），演练后已清理 |
| S2-L3-3 | 纯代码回滚（无迁移） | **PASS** | `diff e2c4f25..HEAD` 命中 `migration` 关键字者均为证据 JSON，无迁移脚本（401 文件 / +46566 / -5894） |
| S2-L3-4 | 回退后校验能力可用 | **PASS** | `tests/test_release_verify.py` 18 passed |
| S2-L3-5 | 生产镜像回切 + 回滚后 15 分钟内 `verify_release.py` 无 FAIL | **PENDING** | 需生产镜像与运行面 |

证据：`doc/test/evidence/s2/l3-20261024/version-rollback.txt` + `verify-release-tool.txt`。

## 6. 结论与判据映射

**总判定：11 PASS / 3 PENDING / 0 FAIL → 状态 PENDING（离线可判定面闭环，生产实机段待 OPS）。**

| 回滚方案判据 | 本轮结论 | 说明 |
|:---:|:---:|------|
| V1 启动健康 | 部分（离线） | 「门禁全开可装配 / 任一回落实例化即拒绝」已实证；生产实机启动与 `/health` 待 OPS |
| V2 通道正确 | 部分（离线） | 状态机层面 `channel_report` 主通道与单主语义 PASS；运行态快照待 OPS |
| V3 写路径一致 | 部分（离线） | A 主时经 B 写被拒已断言；回写 `skipped`→正常待 OPS |
| V4 既有路径零变化 | **PASS（离线）** | 非生产分支零变化由门禁用例覆盖（默认值未翻转） |
| V5 证据留档 | **PASS** | 本报告 + `doc/test/evidence/s2/**` 结构化留证 |

## 7. 发现与处置

| 编号 | 级别 | 发现 | 处置 |
|:----:|:----:|------|------|
| D-01 | 中 | **旧基线版本号三处不统一**：回退目标 `e2c4f25` 的 `pyproject`/`openbase.__version__` = 1.0.0、`openbase-ui/package.json` = 1.3.0；三处统一始于 `1ba1445`（1.4.11） | L3 回退后须人工核对「部署镜像版本 vs 代码声明版本」，在回退记录注明；**不以版本自检不一致判定回退失败**（历史遗留，非本次引入） |
| D-02 | 低 | **L2 演练器跨仓运行时受宿主配置面影响**：OpenLLM `Settings` 以 cwd 相对路径读 `.env` 且 `extra=forbid`，在 OpenBase 仓根驱动会误读本仓 `.env` 而装配失败 | 已修复：`scripts/drill_l2_1_failover.py` 在 main 内切至 OpenLLM 仓根后驱动、`finally` 复原；OpenLLM 侧「审计记录构造先于门控」的 fail-open 契约可另行评估（本轮不改跨仓代码） |

## 8. 待 OPS 回填清单

| # | 待办 | 执行依据 | 回填内容 |
|:-:|------|---------|---------|
| 1 | L1：生产 `.env` 备份 → 开关置回 → 受管编排重启 → `/health` → 恢复 | 回滚方案 §4.1（`scripts/service-orchestrator.ps1`） | 开关前后值、重启时间、`/health` 快照、操作人 |
| 2 | L1：`OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true` 生产下发与 `--env-file` 核验 | 下发单 `XR-OPS-07-ENV-001` | §7 回执表 |
| 3 | L2：按 `channel_report` 复位并验证写路径恢复（V2/V3） | 回滚方案 §4.2 | `channel_report` 前后快照、写路径状态 |
| 4 | L3：镜像回切 + 回滚后 15 分钟内 `verify_release.py` 无 FAIL | 回滚方案 §4.3、§5 | 版本号（含 D-01 核对）、校验输出 |

> 上述 4 项完成后，本报告升版 v1.1.0 并将状态由 [Review] 转 [Approved]。
