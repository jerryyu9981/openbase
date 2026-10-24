# OpenBase-S2-三级回滚演练报告-v1.1.0

| 项目 | 内容 |
|------|------|
| 报告名称 | S2 三级回滚演练（开关级 / 通道级 / 版本级） |
| 报告编号 | OB-S2-DRILL-20261024 |
| 版本 | v1.1.0 |
| 状态 | **[Review]**（离线段 + 本地活实例段闭环；生产实机段待 OPS 回填） |
| 编制日期 | 2026-10-24（v1.0.0）/ 2026-10-25（v1.1.0 补录） |
| 编制人 | FA-OpenBase-Dev（AI 辅助） |
| 上游依据 | 《OpenBase-主备双通道生产上线回滚方案-v1.0.0》§3/§4/§5/§6；《OpenBase-主备双通道生产上线必办事项清单-v2.2.0》S2 |
| 演练代码基线 | v1.0.0：`648872a`（2026-10-24）；v1.1.0：`a50015b`（2026-10-25，产品 1.4.12） |
| 证据目录 | `doc/test/evidence/s2/**`；汇总 JSON：`s2-rollback-drill-20261024.json`（v1.0.0）/ `s2-rollback-drill-20261025.json`（v1.1.0，supersedes 前者） |

## 修订历史

| 版本 | 日期 | 编制人 | 修订内容 |
|------|------|--------|---------|
| v1.1.0 | 2026-10-25 | FA-OpenBase-Dev（AI 辅助） | **本地活实例补录**：L1-5 拆为 5a（生产门禁进程级双向 + 受管编排启停 + `/health`，PASS）/ 5b（生产 `.env` 与生产重启，PENDING）；L3-5 拆为 5a（活实例 `verify_release` 0 FAIL，PASS）/ 5b（生产镜像回切，PENDING）；L2-5 保持 PENDING 并补「OpenLLM 本机不可启动（psycopg 缺失）」证据；新增 D-04（编排 stop 首次因 PID 陈旧未生效）；结论 14 PASS / 3 PENDING / 0 FAIL |
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
| 宿主 | Windows 本机开发面，**无生产部署面**（初始 8000/8766/8001 等均无监听；v1.1.0 本地拉起 OpenBase 8000 后已受管停止） |
| 基础设施（v1.1.0 实测） | PG `192.168.0.151:5432` ✓ / Redis `192.168.0.151:6380` ✓ / Qdrant `192.168.0.151:6333` ✓ / Neo4j `192.168.0.151:7687` ✓；四仓服务本体均未运行 |
| 解释器 | `D:\PostgreSQL\17\pgAdmin 4\python\python.exe`（3.13），经 `doc/tmp/pyrun.py` 注入 `.venv` 依赖与源码根 |
| 受管编排 | `scripts/service-orchestrator.ps1` 以裸 `python` 启动 ⇒ 需前置 `.venv\shim` 并注入 `OPENBASE_PY_DEPS` / `OPENBASE_PY_ROOT`（否则子进程缺依赖，`No module named uvicorn`） |
| OpenLLM 测试 | 追加 `DATABASE_URL=sqlite:///:memory:`，**仅规避本机 psycopg pq 驱动缺失**，用例不触库；同一原因导致 **OpenLLM 服务本机不可启动** |
| 纪律 | 禁伪造：凡需真实运行态/注故障窗口的项一律 `PENDING` 并写明原因，不填 PASS；不裸 `Stop-Process`（v1.1.0 全程经编排入口启停） |

## 3. L1 开关级（离线判定面 + 本地进程级实测）

| # | 判据 | 方法 | 结果 |
|:-:|------|------|:----:|
| S2-L1-1 | OpenLLM 生产门禁组：任一开关回落即拒绝启动；全开通过 | `pytest tests/unit/test_production_gate_tenant_isolation.py test_c4_production_enforce_gate.py test_f12_startup_gate_runtime.py` | **PASS（15 passed）** |
| S2-L1-2 | OpenBase 生产门禁：token 版本强校验 / DB 降级 / 行缺失 / 登录租户策略 | `pytest tests/test_b4_security_hardening.py tests/test_q5_q6_decisions.py -k "production or tenant"` | **PASS（14 passed / 23 deselected）** |
| S2-L1-3 | OpenMemory 强制段：生产 M2 未开 `require_tenant_scope` 拒绝装配 | `pytest tests/unit/test_production_tenant_scope_gate.py`（`.venv3` 3.11.9） | **PASS（7 passed）** |
| S2-L1-4 | 开关值可双向核验（`--env-file` 覆盖生效） | 同一开关两侧取值比对 | **PASS**：演练 env PASS / 开发 `.env` FAIL |
| S2-L1-5a | **进程级**双向：门禁回落 → 装配拒绝退出非零；置真 → 装配成功 | 独立进程导入 `openbase.demo_app`，仅切换进程环境变量（不动仓内 `.env`） | **PASS**：负例 exit=1（`生产环境必须启用 OPENBASE_ENFORCE_TOKEN_VERSION=true…否则拒绝启动`）/ 正例 exit=0 |
| S2-L1-5b | **生产实机**：备份 `.env` → 置回 → 受管编排重启 → `/health` → 恢复 | 需生产部署面 | **PENDING（待 OPS）** |

**受管编排实测（本地开发面，非生产）**：`-Action start -Only openbase` → 冷启动 7s、`/health` 200 `{"status":"ok"}`；`-Action stop` 复核无 8000 监听。**启停全程经编排入口，未用裸 `Stop-Process`**（见 D-04）。

覆盖的 5 组门禁：`ENFORCE_INBOUND_IDENTITY_HEADERS` / `RBAC_PERMISSION_ENFORCE` / `TENANT_SCOPE_ENFORCE` / `TENANT_HEADER_CONSISTENCY_ENFORCE` / `QUOTA_MISSING_FAIL_CLOSED`。

**关键语义实证**：门禁开关「置回上线前值」不是无害动作 —— 生产环境下会直接**拒绝启动**（回滚方案 §7.1 风险 1 的具体表现）。因此 L1 回退门禁必须与「临时接受门禁缺失」的授权一并决策，不能作为无感操作。

证据：`doc/test/evidence/s2/l1-20261024/{openllm-gates,openbase-gates,openmemory-gate,prod-gate-process,managed-restart}.txt`；`doc/test/evidence/release/switch-envfile-{rehearsal,local}-20261024.json`。

## 4. L2 通道级（真实状态机驱动）

驱动面：OpenLLM `app.identity.channel.ChannelStateManager`（S4-T7 落点），经 `scripts/drill_l2_1_failover.py` 真实执行。

| # | 判据 | 结果 | 实测 |
|:-:|------|:----:|------|
| S2-L2-1 | B 断 → A 接管 | **PASS** | 连续 3 次组件降级达阈值 → `failover=true`，`route b→a`；写路径仅 A 允许、经 B 写被拒 |
| S2-L2-2 | A 断 → B 维持 | **PASS** | `route b→b`，`auto_failover=false`，备不可用不影响主 |
| S2-L2-3 | 单主路径（禁双主双写） | **PASS** | initial `['b']` / after-failover `['a']` / after-switch-back `['b']` |
| S2-L2-4 | 回切链路与报告字段齐备 | **PASS** | 审计 6 动作齐全、缺失 0；`single_primary=true` |
| S2-L2-5 | 生产运行态复位 + 写路径恢复（V2/V3） | **PENDING** | 需真实通道运行态与 `/openllm/v1/health` 快照。**本机不可达原因（v1.1.0 复核）**：OpenLLM 服务依赖 `psycopg`，本机宿主 Python 无可用 pq wrapper（S2-L2 演练日志 `ImportError: no pq wrapper available`），服务无法拉起 ⇒ 通道运行态只能在部署面获取 |

证据：`doc/test/evidence/s2/l2-1-20261024/failover-drill.json` + `drill-report.md`（统一退出码 0=PASS）。

## 5. L3 版本级

| # | 判据 | 结果 | 实测 |
|:-:|------|:----:|------|
| S2-L3-1 | 回退目标可定位 | **PASS** | 双通道批次前基线 `e2c4f25`（2026-10-15）；最近发布标签 `v1.4.10` = `2c45a32`（2026-10-02） |
| S2-L3-2 | 回退动作可执行 | **PASS** | `git worktree add --detach` 检出基线成功（1896 文件），演练后已清理 |
| S2-L3-3 | 纯代码回滚（无迁移） | **PASS** | `diff e2c4f25..HEAD` 命中 `migration` 关键字者均为证据 JSON，无迁移脚本（401 文件 / +46566 / -5894） |
| S2-L3-4 | 回退后校验能力可用 | **PASS** | `tests/test_release_verify.py` 18 passed |
| S2-L3-5a | **活实例**回滚后校验：`verify_release` 无 FAIL | 本地拉起 OpenBase 8000 后执行 `scripts/verify_release.py` | **PASS**：`PASS 7 / WARN 0 / FAIL 0 / INFO 3`，退出码 0；`info.version=1.4.12` |
| S2-L3-5b | **生产**镜像回切 + 回滚后 15 分钟内 `verify_release.py` 无 FAIL | 需生产镜像与运行面 | **PENDING（待 OPS）** |

证据：`doc/test/evidence/s2/l3-20261024/{version-rollback,verify-release-tool,verify-release-live}.txt`。

## 6. 结论与判据映射

**总判定：14 PASS / 3 PENDING / 0 FAIL → 状态 PENDING（离线段 + 本地活实例段闭环；生产实机段 3 项待 OPS）。**

| 回滚方案判据 | 本轮结论 | 说明 |
|:---:|:---:|------|
| V1 启动健康 | 部分（含本地实测） | 门禁双向（拒绝/放行）进程级实证；受管编排冷启动 7s、`/health` 200；生产实机重启待 OPS |
| V2 通道正确 | 部分（离线） | 状态机层面 `channel_report` 主通道与单主语义 PASS；运行态快照待 OPS |
| V3 写路径一致 | 部分（离线） | A 主时经 B 写被拒已断言；回写 `skipped`→正常待 OPS |
| V4 既有路径零变化 | **PASS** | 非生产分支零变化由门禁用例覆盖（默认值未翻转）；开发态实例 10 项上线验证 0 FAIL |
| V5 证据留档 | **PASS** | 本报告 + `doc/test/evidence/s2/**` 结构化留证（含原始输出与端口核对） |

## 7. 发现与处置

| 编号 | 级别 | 发现 | 处置 |
|:----:|:----:|------|------|
| D-01 | 中 | **旧基线版本号三处不统一**：回退目标 `e2c4f25` 的 `pyproject`/`openbase.__version__` = 1.0.0、`openbase-ui/package.json` = 1.3.0；三处统一始于 `1ba1445`（1.4.11） | L3 回退后须人工核对「部署镜像版本 vs 代码声明版本」，在回退记录注明；**不以版本自检不一致判定回退失败**（历史遗留，非本次引入） |
| D-02 | 低 | **L2 演练器跨仓运行时受宿主配置面影响**：OpenLLM `Settings` 以 cwd 相对路径读 `.env` 且 `extra=forbid`，在 OpenBase 仓根驱动会误读本仓 `.env` 而装配失败 | 已修复：`scripts/drill_l2_1_failover.py` 在 main 内切至 OpenLLM 仓根后驱动、`finally` 复原；OpenLLM 侧「审计记录构造先于门控」的 fail-open 契约可另行评估（本轮不改跨仓代码） |
| D-04 | **高** | **受管编排 `stop` 首次不生效**：`-Action stop` 日志称「openbase 已停止（PID 296）」，但 8000 仍监听（实际 PID 34120 为 uvicorn 真实进程，PID 文件记录为启动包装进程）；第二次 `stop` 才命中。根因：编排记录的 PID 与真实服务进程存在代际错位（两次启动尝试 + cmd shim 派生） | 回滚步骤必须**以端口核对为准**：`stop` 后执行 `Get-NetTCPConnection -LocalPort <port> -State Listen`，仍监听则重试 `stop`（**不得**裸 `Stop-Process`）；另建议编排侧改为记录真实监听 PID 并做端口兜底，登记为改进项 |
| D-05 | 低 | 本地拉起 OpenBase 需前置 `.venv\shim` + `OPENBASE_PY_DEPS/PY_ROOT`，否则编排子进程 `No module named uvicorn`（宿主 PATH 无 python） | 属本机环境限制，非服务缺陷；执行单需写明该前置（已记入 §2 与本报告 §9） |

## 8. 待 OPS 回填清单（3 项 + 1 项配置下发）

| # | 待办 | 执行依据 | 回填内容 |
|:-:|------|---------|---------|
| 1 | **L1-5b**：生产 `.env` 备份 → 开关置回 → 受管编排重启 → `/health` → 恢复（**停止后必须核对端口**，见 D-04） | 回滚方案 §4.1（`scripts/service-orchestrator.ps1`） | 开关前后值、重启时间、`/health` 快照、端口核对结果、操作人 |
| 2 | **L2-5**：按 `channel_report` 复位并验证写路径恢复（V2/V3） | 回滚方案 §4.2 | `channel_report` 前后快照、写路径状态 |
| 3 | **L3-5b**：镜像回切 + 回滚后 15 分钟内 `verify_release.py` 无 FAIL | 回滚方案 §4.3、§5 | 版本号（含 D-01 核对）、校验输出 |
| 4 | `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=true` 生产下发与 `--env-file` 核验 | 下发单 `XR-OPS-07-ENV-001` | §7 回执表 |

> 上述 4 项完成后，本报告升版 v1.2.0 并将状态由 [Review] 转 [Approved]。

## 9. 本地等效实测补录（v1.1.0）

执行时间：2026-10-25 01:02~01:12（Asia/Shanghai）；基线 `a50015b`（产品 1.4.12）。

| 步骤 | 命令 | 结果 |
|------|------|------|
| 门禁负例 | 独立进程导入 `openbase.demo_app`（`OPENBASE_ENV=production`、强 JWT、`ENFORCE_TOKEN_VERSION=false`） | 退出码 **1**，报「生产环境必须启用 OPENBASE_ENFORCE_TOKEN_VERSION=true…否则拒绝启动」 |
| 门禁正例 | 同上 + `ENFORCE_TOKEN_VERSION=true` | 退出码 **0**（装配成功） |
| 受管启动 | `service-orchestrator.ps1 -Action start -Only openbase -HealthTimeout 90`（前置 shim + `OPENBASE_PY_DEPS/PY_ROOT`） | 冷启动 **7s**，健康通过；软依赖四仓未健康（不阻断） |
| 健康核验 | `GET /health` | **200** `{"status":"ok"}` |
| 回滚后校验 | `scripts.verify_release --base-url http://127.0.0.1:8000` | **PASS 7 / WARN 0 / FAIL 0 / INFO 3**，退出码 0，`info.version=1.4.12` |
| 受管停止 | `service-orchestrator.ps1 -Action stop`（首次未生效 → 重试） | 第二次命中 PID 34120；复核 8000 无监听 |

边界：以上为**本地开发面等效实测**，证明「门禁双向机械后果 + 受管启停 + 回滚后校验链路」可执行；
生产 `.env` 置回、生产重启与镜像回切仍须 OPS 在部署面执行并回填 §8。
