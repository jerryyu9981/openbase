# OpenBase 编排器可观测性补口 DevLogReport

## 文档元信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | OB-DEVLOG-ORCH-OBS-001 |
| 文档版本 | v1.0.0 |
| 文档状态 | [Review]（待人工批准） |
| 适用环境 | Dev（Windows ＋ PowerShell 5.1 ＋ 共享基础设施 192.168.0.151） |
| 编写角色 | 开发工程师（Dev）／测试工程师（QA）协同 |
| 创建日期 | 2026-11-07 |
| 关联文档 | 《OpenBase-基础设施子系统全生命周期走查报告-v1.4.0》§8 第 1~4 项／§9.3 |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 | 状态 |
| --- | --- | --- | --- | --- |
| v1.0.0 | 2026-11-07 | Dev／QA | 首版：闭合走查报告 §8 第 2~4 项，登记第 1 项时延基线口径；顺带修复 DSN 口令脱敏缺陷 | [Review] |

---

## 1. 背景

《OpenBase-基础设施子系统全生命周期走查报告-v1.3.0》§8 登记了 4 项编排器相关风险：

| 编号 | 风险 | 影响 |
| --- | --- | --- |
| R-1 | 共享基础设施时延未登记基线 | 无法判断代理等待预算/健康阈值是否合理 |
| R-2 | 冷启动耗时接近健康等待上限（OpenLLM 193s vs 180s） | 服务实际已就绪却被判"启动失败" |
| R-3 | 启动期环境配置易漏配 | 运行期才暴露（如 dps-proxy 自环 401） |
| R-4 | `status` 无法区分"探活超时"与"服务不可用" | 误判服务故障，干扰走查结论 |

本次在 `scripts/service-orchestrator.ps1` 内完成 R-2／R-3／R-4 的代码级闭合，并为 R-1 登记采样口径。

## 2. 变更清单

| # | 位置 | 变更 | 对应风险 |
| --- | --- | --- | --- |
| C-1 | `$services` 中 openllm 定义 | `HealthWait` 180 → **300**，注释记录实测冷启动 193s 依据 | R-2 |
| C-2 | `Test-TcpEndpoint` | 返回值新增 `Detail`（`ok`／`timeout`／`refused`／`dns`／`connect_failed`／`invalid`），失败时解析 `SocketException.SocketErrorCode` | R-4 |
| C-3 | 新增 `Test-HealthProbe` | 返回 `{Healthy, Detail, LatencyMs, Url}`；按 `WebException.Status` 区分超时／连接失败／DNS／HTTP 码 | R-4 |
| C-4 | `Test-Health` | 改为 `Test-HealthProbe(...).Healthy` 的薄封装，保持既有调用方语义不变 | R-4 |
| C-5 | 新增 `Format-HealthDetail` | 把探针细节翻译为可读原因（`健康探测超时`／`连接被拒绝`／`HTTP 503`…） | R-4 |
| C-6 | `Get-AllStatus` | 端口在监听且单次探测超时 → 按 10s 预算重试一次；命中显示"健康 ✅（重试后）"；新增"未启动（进程在，端口未监听）" | R-4 |
| C-7 | 新增 `Write-EffectiveEnvSnapshot` | `start` 前打印 10 个跨系统键的实际生效值与来源（进程环境 > `.env.shared-infra` > `OpenBase/.env`），未配置输出 WARN | R-3 |
| C-8 | `Hide-DsnSecret` | 正则由 `://([^:/@]+):[^@]*@` 改为 `://([^:@/]*):[^@]*@`，覆盖 Redis 空用户名写法 `redis://:pass@`；并兜底掩码 `password=`／`pwd=` 参数 | 安全（C-7 连带发现） |
| C-9 | `Invoke-Start` | `Assert-DbReadyOrExit` 之后调用 `Write-EffectiveEnvSnapshot` | R-3 |

> C-8 说明：C-7 首次自测时发现 `REDIS_URL=redis://:!Q1w2e3r4t5@…` 的口令未被掩码，违反「日志禁止记录密钥」。若沿用旧正则会**在启动日志中泄漏 Redis 口令**，故必须同批修复。

## 3. 验证证据

### 3.1 单测与语法门禁

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 编排器单测（含 PowerShell 语法解析守卫） | `python -m pytest tests/test_orchestrator_db_failover.py` | **22 passed / 2 skipped**（318s） |
| PowerShell AST 解析 | `[Parser]::ParseFile(...)` | **0 语法错误** |

### 3.2 `status` 实测输出（2026-11-07 12:12）

```
===== 多系统服务状态（2026-11-07 12:12:04）=====
服务          端口     说明                             状态 PID
openllm     8001   OpenLLM 大模型网关                  未启动（进程在，端口未监听） PID=-
openrag     8010   OpenRAG 知识库/检索                 运行中（不健康 ⚠️：健康探测超时） PID=32308
openmemory  8020   OpenMemory 记忆服务（complete 模式…） 未启动（进程在，端口未监听） PID=-
oidc-idp    8090   本地 OIDC IdP（标准授权码流程…）      未启动（进程在，端口未监听） PID=-
dps         8030   DPS 数据画像系统                     未启动（进程在，端口未监听） PID=-
openbase    8000   OpenBase 统一底座（JWT 门禁 + 四 proxy） 运行中（不健康 ⚠️：健康探测超时） PID=11324
frontend    5173   统一前端（vite dev，proxy → 8000）    未启动（进程在，端口未监听） PID=-
```

与改造前对比：失败原因由统一的"不健康 ⚠️"变为可区分——`8010` 明确为"健康探测超时"（端口在监听，服务实际可用），`8001/8020/8030/8090` 明确为"进程在、端口未监听"（进程已退出），不会再把两类问题混为一谈。

> 环境说明：本次采样时共享 PG 建连 4.5s、OpenBase `/health` 与登录接口分别超时（>25s／35s），OpenLLM／OpenMemory／DPS／OIDC 进程已退出。该状态属环境降载，非本次改动引入；`status` 的细分输出正是本项改造要解决的问题。为不改动用户运行环境，本次**未执行启停**。

### 3.3 环境生效值快照（函数级验证）

按 PowerShell AST 提取 C-7／C-8 函数独立执行，实际输出：

```
[INFO] 启动期环境生效值（优先级：进程环境 > .env.shared-infra > OpenBase/.env；口令已脱敏）：
[INFO]   OPENBASE_LLM_UPSTREAM_BASE = http://127.0.0.1:8001（OpenBase/.env）
[WARN]   环境未设置 OPENBASE_RAG_UPSTREAM_BASE（由服务自身 .env 或代码默认值兜底）
[WARN]   环境未设置 OPENBASE_MEMORY_UPSTREAM_BASE（由服务自身 .env 或代码默认值兜底）
[INFO]   OPENBASE_DPS_UPSTREAM_BASE = http://127.0.0.1:8030（.env.shared-infra）
[INFO]   OPENBASE_MEMORY_UPSTREAM_TIMEOUT = 180（.env.shared-infra）
[INFO]   DEFAULT_LLM_MODEL = qwen2.5:0.5b（.env.shared-infra）
[INFO]   DPS_BASE_URL = http://127.0.0.1:8030（.env.shared-infra）
[INFO]   OPENRAG_BASE_URL = http://127.0.0.1:8010（.env.shared-infra）
[INFO]   POSTGRES_URL = postgresql://nuct:***@192.168.0.151:5432/nuct（.env.shared-infra）
[INFO]   REDIS_URL = redis://:***@192.168.0.151:6380/0（.env.shared-infra）
```

脱敏用例：`redis://:!Q1w2e3r4t5@…` → `redis://:***@…`；`mysql://root:abc123@…?password=xyz` → `mysql://root:***@…?password=***`。

> `OPENBASE_RAG_UPSTREAM_BASE`／`OPENBASE_MEMORY_UPSTREAM_BASE` 未配置属**预期**：`openbase/settings.py` 对其默认值分别为 `http://127.0.0.1:8010`／`8020`，与编排端口一致。快照以 WARN 提示，便于后续排查"以为配了其实没配"。

## 4. 影响与回滚

- **影响面**：仅服务编排脚本（启停/状态展示/日志），不进入业务请求链路。
- **行为变化**：
  - `status` 输出文案更细，脚本化解析若依赖旧文案 `运行中（不健康 ⚠️）` 需同步调整（仓内检索无此依赖）。
  - `start` 日志新增 10 行环境快照（含脱敏口令）。
  - OpenLLM 冷启动等待窗口 180s → 300s，失败判定更宽松。
- **回滚**：`git revert` 本次提交即可；无数据迁移、无配置变更。

## 5. 质量门禁

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 编排器单测 | `python -m pytest tests/test_orchestrator_db_failover.py` | 22 passed / 2 skipped |
| PowerShell 语法 | AST `ParseFile` 统计 `$errors.Count` | 0 |
| Python 静态检查 | `python -m ruff check openbase tests` | **All checks passed** |

## 6. 交付清单

| 类型 | 内容 |
| --- | --- |
| 代码 | `scripts/service-orchestrator.ps1`（C-1~C-9） |
| 单测 | 复用既有 `tests/test_orchestrator_db_failover.py`（语法/结构守卫已覆盖） |
| 文档 | 本报告；走查报告升版至 v1.4.0（§1.3／§6／§8／§9.3） |
