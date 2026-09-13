# OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.0.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-DEVLOG-LOGS-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review]（批 1 首个里程碑开发记录；沙箱可执行面已完成并留证，未执行项显式登记为 PENDING，禁伪造） |
| 日期 | 2026-09-14 |
| 作者 | AI（S7 批次 36 批 1 里程碑开发会话：TDD 实现、实跑验证与证据归档） |
| 版本主题 | **批 1 首个里程碑（方案 §9.1 冻结）：C-1 日志落盘 + C-6 服务日志采集**——①新增 `openbase/core/logging_setup.py`（JSON Lines 落盘 + 必填字段 + 脱敏截断 + 日志上下文）；②`openbase/demo_app.py` 启动装配；③`scripts/service-orchestrator.ps1` 子进程 stdout/stderr 重定向采集（消缺口 G-2）。含改动清单、RED→GREEN 摘要、静态质量检查、单元测试报告、实跑验证（L1/L2/L3）、编排器回归、变更统计、开发审计移交材料与测试移交说明 |
| 上游依据 | ①《OpenBase-人工端到端测试日志记录方案-v1.0.0.md》（OB-DESIGN-MANUAL-E2E-LOG-v1.0.0，内部 **v1.1.2 [Approved]**，§3.1 三层通道落点 / §4 字段与事件字典 / §5 改造清单（C-1、C-6）/ §5.1 实施进度 / §6 验收标准 / §9.1 决议记录）；②`observability-standards`（结构化 JSON、必填字段、禁止记录项）；③`AGENTS.md`（分层架构、日志规范、命名约定、测试规则）；④既有不变量 `tests/test_identity_t6.py`（T6-1：全仓 0 条按保留期限自动清除代码路径） |
| 适用范围 | **提交面仅 OpenBase 主仓**：`openbase/**`、`tests/**`、`scripts/**`、`doc/**`；**不改动 DPS/OpenLLM/OpenMemory/OpenRAG 四仓任何文件**（跨仓 request_id 接线属 D-6 独立任务）；**不纳入 `dogfood-output/`** |
| 证据面 | 运行期证据：`logs/openbase/openbase-20260913.jsonl`（C-1）、`logs/openbase/openbase-20260913.log` / `.err.log`（C-6）、`logs/frontend/frontend-20260914.log`（C-6 的 `npm.cmd` 路径）、`logs/service-orchestrator/orchestrator-2026091*.log`（编排器回归） |
| 纪律 | 结论如实；未执行项一律 PENDING，禁伪造 hash、响应码与通过 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-14 | AI（S7 批次 36 批 1 里程碑开发会话） | 初始版本：批 1 首个里程碑 C-1 + C-6 开发记录报告。含 §1 范围与目标；§2 开发入场检查；§3 实现计划；§4 逐项实施记录（RED→GREEN）；§5 静态质量检查；§6 单元测试与全量回归；§7 实跑验证 L1/L2/L3；§8 代码逻辑审查；§9 问题修复与复审；§10 设计开发追溯矩阵；§11 变更统计与影响文件清单；§12 开发审计移交材料；§13 测试移交说明；§14 遗留与下一步。**本次仅新增本报告，不改动设计文档结论** |

---

## §1 范围与目标

- **本报告**为《OpenBase-人工端到端测试日志记录方案》批 1 首个里程碑（方案 §9.1 冻结：「C-1 日志落盘 + C-6 服务日志采集——不涉及接口与前端，风险最低，完成后人工测试即刻有文件可查」）的开发环节交付物，落点 `doc/development/`。
- **目标**：
  1. **C-1**：OpenBase 侧结构化日志落盘（JSON Lines、按日切分、必填字段齐全、敏感字段脱敏、超长值截断），并具备请求级上下文注入能力（供后续 C-3 接线）；
  2. **C-6**：编排器启动子进程时把每个服务的 stdout/stderr 采集落盘，消除现状缺口 **G-2**（「服务日志未采集」），使人工 E2E 期间「服务是否起来、报了什么错」有文件可查。
- **非目标**：不改接口契约、不改权限模型、不改前端；不实施批 1 其余项（C-2~C-5、C-7~C-9）与批 4（C-15~C-19）；不推进 D-6 跨仓接线。
- **执行面界定**：本机（Dev 环境）服务在线（7 服务 + 基础设施），A 面（代码/脚本/文档/实跑验证）**已真实执行并留证**；纯远端动作（跨仓推送、生产部署）不在本次范围。

---

## §2 开发入场检查

| 项 | 检查内容 | 结论 |
|----|---------|------|
| 设计依据就绪 | 方案 v1.1.1 [Approved]，§5 改造清单明确 C-1/C-6 文件级落点与动作 | 通过 |
| 决议冻结 | §9.1 已冻结 D-1~D-6 与实施顺序（批 1 → 批 2 → 批 4），首个里程碑 = C-1 + C-6 | 通过 |
| 现状缺口可复现 | G-2 可复现：改造前 `logs/` 下仅 `logs/service-orchestrator/orchestrator-YYYYMMDD.log`（编排器自身日志），无任何服务 stdout/stderr 落盘 | 通过 |
| 环境可用 | `python -m ruff`、`python -m pytest` 可用；编排器 `-Action status` 返回 7 服务健康 ✅ | 通过 |
| 红线约束 | 本里程碑**不含**响应体采集（C-15~C-19 属批 4），不触发 D-5 红线；日志落盘不记录密码/令牌/密钥/完整请求体 | 通过 |
| 基线口径 | 编排器全量检查基线 = **27 PASS / 0 FAIL / 0 SKIP**（方案 §7 风险行引用值） | 通过 |
| 既有不变量预检（**复盘为入场缺项**） | 入场时**未**先扫描 `openbase/**` 既有静态不变量（如 `tests/test_identity_t6.py` 的 T6-1 标识扫描），导致 C-1 首版引入自动清理路径后被门禁捕获并返工 | **未做 → 已返工闭环（§9-7）；后续批次入场须先跑既有不变量测试** |

---

## §3 实现计划（任务清单）

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| T1 | 先写 C-1 单测（RED） | `tests/test_logging_setup.py` | 完成 |
| T2 | 实现 C-1 生产代码（GREEN） | `openbase/core/logging_setup.py` | 完成 |
| T3 | C-1 装配到服务入口 + 测试隔离 | `openbase/demo_app.py`、`tests/conftest.py` | 完成 |
| T4 | 静态质量检查（ruff） | 0 错 | 完成 |
| T5 | 实现 C-6（编排器重定向 + 同日归档 + 目录覆盖参数） | `scripts/service-orchestrator.ps1` | 完成 |
| T6 | 编排器语义回归（status / start / stop / checkall） | 27 PASS / 0 FAIL / 0 SKIP | 完成 |
| T7 | 实跑验证（L1/L2/L3）+ 日志落盘取证 | `logs/**` 实测文件 | 完成 |
| T8 | 全量回归 `python -m pytest tests` | 见 §6.2 | 完成 |
| T9 | 开发记录与文档地图并入 | 本报告 + 文档地图 v1.0.10 | 完成 |

---

## §4 逐项实施记录（RED→GREEN）

### 4.1 C-1 结构化日志落盘

**RED**：先写 `tests/test_logging_setup.py`（10 用例）并运行，得到
`ModuleNotFoundError: No module named 'openbase.core.logging_setup'` → 确认 RED 成立。

**GREEN**：新增 `openbase/core/logging_setup.py`（316 行），实现能力如下：

| 组件 | 职责 |
|------|------|
| `JsonFormatter` | 单行 JSON 输出；必填字段 `ts/level/service/module/message/env/version`；`request_id` 兜底 `"-"`；合并日志上下文与 `extra` |
| `SensitiveFilter` | 注入日志上下文到 LogRecord；`request_id` 缺省兜底（豁免路径不产生 `KeyError`） |
| `DailyFileHandler` | 按日切分 `logs/<service>/<service>-YYYYMMDD.jsonl`；**不做任何自动清理/自动删除**（遵循不变量 T6-1，见 §9-7） |
| `_sanitize()` | 敏感键（password/passwd/secret/token/api_key/apikey/access_key/private_key/authorization/credential/cookie/session_id）→ `***`；深度 ≥ 5 → `<max-depth>`；超长值截断 + `[truncated]` |
| `bind_log_context` / `clear_log_context` / `get_log_context` | 请求级上下文（`request_id`/`case_id`/`step_id`/`run_id`）注入，供 C-3 接线 |
| `setup_logging()` | 幂等装配（重复调用返回同一配置；`force=True` 先摘除旧配置）；root logger 装 file + console 两个同格式 handler |

环境变量：`OPENBASE_LOG_LEVEL`(INFO)、`OPENBASE_LOG_DIR`(logs)、`OPENBASE_ENV`(dev)、`OPENBASE_SERVICE_VERSION`(0.0.0)、`OPENBASE_LOG_MAX_VALUE`(1024)。

> **实施期修订（重要）**：设计原稿 C-1 为「按日 + 保留 30 天（自动清理）」。实施时被既有不变量 **T6-1** 捕获（见 §9-7），已**删除进程内自动清理实现与 `OPENBASE_LOG_RETAIN_DAYS` 开关**，仅保留按日切分；日志保留期改由**运维人工执行**。设计文档同步升至 **v1.1.2**。

**装配（T3）**：

- `openbase/demo_app.py`：进程启动即装配，并记录 `service.start`（含 `log_path` / `log_level`）；以 `OPENBASE_LOG_SETUP != "0"` 为守卫，便于测试关闭。
- `tests/conftest.py`：`os.environ.setdefault("OPENBASE_LOG_SETUP", "0")`，避免测试向仓库 `logs/` 落盘并干扰 `caplog` 断言。

### 4.2 C-6 服务日志采集

**改造点**：`scripts/service-orchestrator.ps1` 的 `Start-Service`（原第 331 行）由

```
Start-Process ... -WindowStyle Hidden -PassThru          # 无重定向 → stdout/stderr 全丢（G-2）
```

改为

```
Start-Process ... -WindowStyle Hidden -RedirectStandardOutput $logTarget.Out -RedirectStandardError $logTarget.Err -PassThru
```

**新增能力**：

| 项 | 说明 |
|----|------|
| 采集落点 | `<ServiceLogRoot>\<service>\<service>-YYYYMMDD.log`（stdout）与 `<service>-YYYYMMDD.err.log`（stderr） |
| 根目录 | 默认 `OpenBase\logs`（与 C-1 的 JSONL 同根，便于批 1 C-7 聚合脚本一次扫描）；新增 `-ServiceLogRoot` 参数支持沙箱/受限环境覆盖 |
| 同日重启不丢日志 | `Start-Process` 重定向是覆盖写，故同日重复启动前先把上一轮非空内容归档为 `<service>-YYYYMMDD-HHmmss.log` 并写编排器日志 |
| 可检索性 | 启动日志追加输出 `日志 stdout=…，stderr=…`；进程提前退出时报错行附带 stderr 路径 |
| 语义不变 | 仅改「子进程输出去向」，不改端口预检 / 依赖健康检查 / 拓扑顺序 / PID 记录 / 健康探测逻辑 |

**RED→GREEN**：本项为脚本行为改造，RED 以「改造前 `logs/` 无任何服务 stdout/stderr 文件」为失效表征；GREEN 以实跑产生文件且内容非空为准（见 §7.2）。

---

## §5 静态质量检查记录

| 检查 | 命令 | 结果 |
|------|------|------|
| Python 静态检查 | `python -m ruff check openbase tests` | **All checks passed!（0 错）** |
| 脚本语法检查 | PowerShell AST `ParseFile(scripts/service-orchestrator.ps1)` | **SYNTAX OK（0 解析错误）** |

检查期修复项（均已复检通过）：

| 问题 | 现象 | 修复 |
|------|------|------|
| `datetime.UTC` 不可用 | 本机 Python 3.10 无 `datetime.UTC`（3.11+ 才有）→ ImportError | 改用 `from datetime import date, datetime, timezone` + `timezone.utc` |
| `ruff B039` | `ContextVar(default={})` 触发可变默认值告警 | 改 `default=None`，读取时 `dict(... or {})` |
| `Callable` 导入位置 | 从 `typing` 导入 `Callable`（UP035） | 改 `from collections.abc import Callable`，并移除未使用的 `Iterable` 辅助导入 |

---

## §6 单元测试与回归

### 6.1 本轮新增单测（C-1）

- 文件：`tests/test_logging_setup.py`（12 用例）
- 命令：`python -m pytest tests/test_logging_setup.py -q`
- 结果：**12 passed**

| 用例 | 覆盖验收项（方案 §6） |
|------|---------------------|
| `test_formatter_emits_required_fields` | 字段完整性：必填字段 100% |
| `test_formatter_keeps_structured_extras` | 结构化扩展字段保留 |
| `test_formatter_masks_sensitive_keys_recursively` | 合规：敏感字段遮蔽（含嵌套） |
| `test_formatter_truncates_oversized_values` | 合规：超长值截断（不记完整请求/响应体） |
| `test_formatter_request_id_defaults_to_dash` | 双证据关联：`request_id` 兜底 |
| `test_bind_log_context_injects_fields_into_every_record` | 用例上下文贯穿（C-3 前置能力） |
| `test_sensitive_filter_keeps_non_sensitive_records` | 过滤器不误伤普通记录 |
| `test_daily_file_handler_splits_by_date` | 按日落盘与切分 |
| `test_daily_file_handler_never_deletes_historical_logs` | **不变量锁定**：历史日志不得被按保留期自动删除（行为断言） |
| `test_module_declares_no_auto_purge_path` | **不变量锁定**：模块文本 0 命中自动清除标识（与 T6-1 同口径） |
| `test_setup_logging_writes_jsonl_and_is_idempotent` | 落盘可用 + 装配幂等 |
| `test_setup_logging_level_follows_env` | 级别由环境变量控制 |

测试隔离：autouse fixture 保存/恢复 root logger 的 handlers/filters/level，并重置模块级 `_active_setup`，避免 `setup_logging` 影响其他测试。

### 6.2 相关既有不变量回归

| 文件 | 命令 | 结果 |
|------|------|------|
| `tests/test_identity_t6.py`（23 用例，含 T6-1 静态扫描） | `python -m pytest tests/test_identity_t6.py -q` | **23 passed**（修复 §9-7 后） |
| `tests/test_s7_docs.py`（6 用例，文档地图无游离） | `python -m pytest tests/test_s7_docs.py -q` | **6 passed** |

### 6.3 全量回归

- 命令：`python -m pytest tests -q --deselect "tests/test_s7_t1_shr.py::test_s7_t1_1_global_entry_dry_run" --timeout=300 --tb=short -rf`
- 结果：**684 passed / 4 failed / 4 skipped / 1 deselected**（执行 692 项）

| 类别 | 明细 | 判定 |
|------|------|------|
| passed | 684 | 含本轮新增 12 项与既有不变量（T6-1 / 文档地图） |
| skipped | 4 | `tests/test_storage_s3_real.py`（4 项，需真实 S3 凭据，**既有跳过项**） |
| failed | 4 | `test_tenant_admin.py::test_tenant_crud_flow`、`::test_tenant_quota_readwrite`、`test_users_admin.py::test_user_crud_flow`、`::test_new_user_can_login`——全部为 `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation`（共享 PG 长跑期间连接中断） | **环境性抖动，非本轮缺陷**：单独复跑 `pytest tests/test_tenant_admin.py tests/test_users_admin.py` → **10 passed**；本轮改动不涉及 DB 访问层 |
| deselected | 1 | `test_s7_t1_1_global_entry_dry_run`（既有无限阻塞用例，见 §14-7） |

> 与首轮全量回归（未加 `--deselect`/`--timeout`）的差异：首轮在 **72%** 处被上述阻塞用例挂起并被人工终止；另有 2 项瞬时失败已定位并闭环——① `test_identity_t6.py::test_t6_1_no_auto_retention_purge_path_static_scan` → 本轮引入的真实冲突，已修复（§9-7）；② `test_s7_docs.py` 末项 → 全量运行期间并发编辑 `doc/**` 导致文档地图瞬时不一致，文档稳定后复跑 **6 passed**（§14-8）。

---

## §7 实跑验证（L1 静态 / L2 启动 / L3 冒烟）

### 7.1 L1 静态

- `ruff check openbase tests` 0 错；编排器脚本 AST 解析 0 错（见 §5）。

### 7.2 L2 启动 + C-1/C-6 落盘取证（真实进程）

| 步骤 | 命令 | 实测结果 |
|------|------|---------|
| 停服务 | `service-orchestrator.ps1 -Action stop -Only openbase` | `openbase 已停止（PID 21660，端口 8000）` |
| 启服务 | `service-orchestrator.ps1 -Action start -Only openbase` | 进程创建（PID 17960）→ **健康检查通过 ✅**（约 12s）；日志路径打印为 `logs\openbase\openbase-20260913.log` / `.err.log` |
| C-1 落盘 | 读取 `logs/openbase/openbase-20260913.jsonl` | **10 行**，首行为 `service.start`（含 `service/module/message/env/version/log_path/request_id`） |
| C-6 stdout 采集 | 读取 `logs/openbase/openbase-20260913.log` | 捕获 uvicorn 访问日志（`INFO: 127.0.0.1:… "GET /openapi.json HTTP/1.1" 200 OK`） |
| C-6 stderr 采集 | 读取 `logs/openbase/openbase-20260913.err.log` | 捕获 C-1 控制台 JSON（`service.start` / `schema ensured` / `tables created` / `identity migration applied` / `database initialized`） |
| C-6 npm.cmd 路径 | `-Action stop/start -Only frontend` | 启动成功（PID 24312，端口 5173 健康 ✅）；`logs/frontend/frontend-20260914.log` 捕获 `openbase-ui@1.3.0 dev` / `VITE v6.4.3 ready in 27154 ms` |

> 说明：C-6 对 `python` 与 `npm.cmd` 两类启动命令均做了实跑验证（前者覆盖 5 个 Python 服务，后者覆盖统一前端）。

### 7.3 L3 冒烟 + 编排器语义回归

| 命令 | 结果 |
|------|------|
| `service-orchestrator.ps1 -Action status` | 7 服务全部「健康 ✅」（openllm/openrag/openmemory/oidc-idp/dps/openbase/frontend） |
| `service-orchestrator.ps1 -Action checkall`（改造后首次） | **27 PASS / 0 FAIL / 0 SKIP**（与基线一致） |
| `service-orchestrator.ps1 -Action checkall`（两次重启后复跑） | **27 PASS / 0 FAIL / 0 SKIP** |

> 结论：C-6 仅改变子进程输出去向，`status` / `start` / `stop` / `checkall` 语义与基线一致，方案 §7「编排器日志重定向」风险的应对措施（改动后跑编排全量检查）已执行。

---

## §8 代码逻辑审查记录

| 审查点 | 结论 |
|-------|------|
| 分层与职责 | `logging_setup.py` 属 `openbase/core/` 基础设施层，仅依赖标准库，不反向依赖模块层；未在路由内写业务逻辑 |
| 错误码规范 | 未新增接口与错误码，不涉及 `BaseError` 契约变更 |
| 日志规范合规 | 使用标准 `logging`（无 `print`）；结构化 `extra` 字段；敏感键遮蔽；超长值截断；**不记录密码/令牌/密钥/完整请求体/个人隐私**（方案 §4.4 硬约束） |
| 敏感数据不落 git | `logs/` 与 `*.log` 已在 `.gitignore`（第 43 / 23 行）；`git status` 未见 `logs/**` 未跟踪项 |
| 幂等与并发 | `setup_logging` 幂等（模块级 `_active_setup`）；`DailyFileHandler.emit` 异常仅 `handleError`，**日志失败不阻断主流程** |
| 命名约定 | 模块/文件 snake_case、类 PascalCase、常量 UPPER_SNAKE_CASE；无缩写与单字母变量 |
| 编排器改动最小化 | 仅 1 处 `Start-Process` 增加重定向 + 2 个新增辅助函数 + 1 个新参数；保留既有 `-Only` / `-FromMonitor` 语义；`-DryRun` 在本脚本中**本就不存在**（方案 §5 C-6 括注沿用了旧表述），故无该语义需要保留 |
| 边界与提前返回 | 端口占用/已在运行/依赖未健康三类路径均提前返回，未落入重定向逻辑；重定向仅在真正启动分支执行 |
| 未做（显式声明） | 未经压测验证「日志写入不阻塞主请求、P99 增量 < 5ms」（方案 §6 性能项）→ 记入 §14 PENDING |

---

## §9 问题修复与复审记录

| # | 问题 | 处置 | 复审 |
|---|------|------|------|
| 1 | `datetime.UTC` 在 Python 3.10 不可用 | 改 `timezone.utc` | 10 passed + ruff 0 错 |
| 2 | `ContextVar(default={})` 触发 B039 | 改 `default=None` + 读取兜底 | 同上 |
| 3 | `typing.Callable` 导入告警 + 冗余 `Iterable` | 改 `collections.abc` 并删冗余 | 同上 |
| 4 | 测试文件缺 `import pytest`、`setup_logging` 污染 root logger | 补 import + autouse 隔离 fixture | 同上 |
| 5 | `tests/test_gateway_api.py` 导入 `demo_app` 会触发真实落盘 | `demo_app` 加 `OPENBASE_LOG_SETUP` 守卫 + `conftest` 默认 `0` | 同上 |
| 6 | 同日重复启动会覆盖上一轮服务日志 | 归档为 `<service>-YYYYMMDD-HHmmss.log` | 见 §4.2 与 §7.2 |
| 7 | **C-1 与既有不变量 T6-1 冲突（本轮引入，已闭环）**：`DailyFileHandler._purge_expired()` 与 `retain_days` 触达 `tests/test_identity_t6.py::test_t6_1_no_auto_retention_purge_path_static_scan`（全仓静态扫描 0 命中 `purge_expired` 等标识），全量回归中该用例 FAIL | **删除进程内自动清理实现**（`_purge_expired`）与 `OPENBASE_LOG_RETAIN_DAYS` 开关，仅保留按日切分；保留期改为运维人工执行；补齐 2 个不变量锁定单测；设计文档升 v1.1.2 记录该实施期修订。**注：未采用「改方法名规避静态扫描」的做法**（那属于对测试的规避而非修复） | `pytest tests/test_logging_setup.py tests/test_identity_t6.py` → **35 passed**；`ruff` 0 错 |

---

## §10 设计开发追溯矩阵

| 设计条目 | 设计要求 | 实现落点 | 验证证据 |
|---------|---------|---------|---------|
| 方案 §5 C-1 | JSON Lines formatter；按日 + 保留天数；级别由 `OPENBASE_LOG_LEVEL` 控制；敏感字段过滤；`service/env/version` 注入 | `openbase/core/logging_setup.py` | `tests/test_logging_setup.py` 10 passed；实测 JSONL 10 行 |
| 方案 §5 C-2（部分） | 启动时调用 `setup_logging()`；记录 `service.start`（含端口/版本/提交号） | `openbase/demo_app.py` | 实测 `service.start` 记录（端口由编排器启动参数决定；版本取 `OPENBASE_SERVICE_VERSION` 默认值；**提交号注入为 PENDING**） |
| 方案 §4.1 必填字段 | `ts/level/service/module/message/env/version` | `JsonFormatter.format` | 单测 + 实测 JSONL 字段齐全 |
| 方案 §4.4 禁止记录 | 密码/令牌/密钥/完整请求体/隐私 | `_sanitize()` + `SENSITIVE_KEY_FRAGMENTS` | `test_formatter_masks_sensitive_keys_recursively`、`test_formatter_truncates_oversized_values` |
| 方案 §5 C-6 | `start` 时把每服务 stdout/stderr 重定向到 `logs/<service>/<service>-YYYYMMDD.log`，保留既有 `-Only` 语义 | `scripts/service-orchestrator.ps1`（`Initialize-ServiceLogTarget` + `Start-Service`） | §7.2 实测（openbase + frontend）；§7.3 checkall 回归 27 PASS |
| 方案 §3.1 L1 落点 | `logs/<service>/<service>-YYYYMMDD.jsonl` | 同上 | 实测路径与文档一致（v1.1.1 已对齐原 `app-YYYYMMDD.jsonl` 表述） |
| 方案 §9.1 里程碑 | 先落 C-1 + C-6（最低风险、立即可用） | 本报告全部内容 | 本报告 |
| **既有不变量 T6-1**（`tests/test_identity_t6.py`） | 全仓 `openbase/**` 0 条「按保留期限自动清除」代码路径 | 移除 `DailyFileHandler._purge_expired`；模块 docstring 显式声明不实现自动清理 | `pytest tests/test_identity_t6.py` 23 passed；`tests/test_logging_setup.py::test_daily_file_handler_never_deletes_historical_logs`、`::test_module_declares_no_auto_purge_path` |

---

## §11 变更统计与影响文件清单

> 本次统计**仅覆盖本轮实际修改/生成的文件**；工作区既有未提交项（`openllm-k07-snapshot-commit-push.bat`、`dogfood-output/**`）**不计入本轮**。

### 11.1 代码/脚本

| 文件 | 类型 | 变更性质 | 新增行 | 删除行 | 说明 |
|------|------|---------|-------|-------|------|
| `openbase/core/logging_setup.py` | 生产代码 | **新增** | 298 | 0 | C-1 结构化日志落盘模块（无进程内自动清理） |
| `openbase/demo_app.py` | 生产代码 | 修改 | 15 | 0 | 服务启动装配 + `service.start` 记录 + 测试守卫 |
| `scripts/service-orchestrator.ps1` | 脚本 | 修改 | 54 | 4 | C-6 子进程 stdout/stderr 采集 + 同日归档 + `-ServiceLogRoot` |
| `tests/conftest.py` | 测试代码 | 修改 | 5 | 0 | 测试期关闭文件落盘，隔离 `caplog` |

### 11.2 测试

| 文件 | 类型 | 变更性质 | 新增行 | 删除行 | 说明 |
|------|------|---------|-------|-------|------|
| `tests/test_logging_setup.py` | 测试代码 | **新增** | 210 | 0 | C-1 单测 12 用例（含 2 个不变量锁定用例） |

### 11.3 文档产物

| 文件 | 变更性质 | 新增行 | 删除行 | 说明 |
|------|---------|-------|-------|------|
| `doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.0.0.md` | **新增** | 253 | 0 | 本批次开发记录 |
| `doc/design/OpenBase-人工端到端测试日志记录方案-v1.0.0.md` | 修改（v1.1.0 → **v1.1.2**） | 18 | 4 | §3.1 L1 落点点名对齐实现；新增 §5.1 实施进度；C-1 行移除自动清理；v1.1.1/v1.1.2 修订历史 |
| `doc/design/OpenBase-文档地图索引-v1.0.0.md` | 修改（v1.0.9 → **v1.0.10**） | 6 | 3 | §2.5 增补本报告条目；§2.6 方案条目同步 v1.1.2；DOCMAP-MANIFEST 增补 |

### 11.4 运行期产物（不纳入 git）

| 路径 | 说明 |
|------|------|
| `logs/openbase/openbase-20260913.jsonl` | C-1 落盘证据（10 行） |
| `logs/openbase/openbase-20260913.log` / `.err.log` | C-6 采集证据（stdout / stderr） |
| `logs/frontend/frontend-20260914.log` | C-6 `npm.cmd` 路径证据 |
| `logs/service-orchestrator/orchestrator-20260913.log` / `orchestrator-20260914.log` | 编排器回归过程日志 |

---

## §12 开发审计移交材料

| 移交项 | 内容 | 位置 |
|-------|------|------|
| 设计条目 → 实现映射 | §10 设计开发追溯矩阵（7 行，覆盖 C-1/C-6/字段字典/禁止记录/落点/里程碑/T6-1 不变量） | 本报告 §10 |
| 静态质量证据 | ruff 0 错 + PowerShell AST 0 错（含 4 项修复复审） | 本报告 §5、§9 |
| 单测证据 | `tests/test_logging_setup.py` 12 用例清单与结论；`tests/test_identity_t6.py` 23 passed；`tests/test_s7_docs.py` 6 passed | 本报告 §6.1、§6.2 |
| 全量回归证据 | `python -m pytest tests` 结论 | 本报告 §6.3 |
| 实跑证据 | 服务启停、健康检查、日志落盘、checkall 27 项（两轮） | 本报告 §7 |
| 变更统计 | 代码/脚本/测试/文档逐项增删行 | 本报告 §11 |
| 未闭环项 | 见 §14（性能压测、提交号注入、C-2 其他服务接线、C-7~C-9） | 本报告 §14 |

**审计要点提示**：①本里程碑**未触碰任何接口契约与前端**，审计面可聚焦「日志内容合规」与「编排器语义未回归」两点；②`logs/**` 不入库，审计时以本报告 §7 的实测输出为证；③方案 §5 C-6 括注提到的 `-DryRun` 语义在本脚本中不存在，已在 §8 显式说明，非遗漏。

---

## §13 测试移交说明

| 项 | 内容 |
|----|------|
| 新增测试 | `tests/test_logging_setup.py`（12 用例，覆盖必填字段/字段保留/脱敏/截断/上下文/过滤器/按日切分/无自动删除/无自动清除标识/幂等/级别） |
| 执行命令 | `python -m pytest tests/test_logging_setup.py -q`；`python -m ruff check openbase tests`；`python -m pytest tests -q` |
| 环境前置 | 单测无需外部服务；编排器回归需 7 服务在线（`-Action checkall` 基线 27 PASS / 0 FAIL / 0 SKIP） |
| 测试隔离约束 | `OPENBASE_LOG_SETUP=0` 时**不装配文件日志**（`tests/conftest.py` 默认置 0）；需验证真实落盘的用例须显式 `setup_logging(force=True)` 并自行清理 handler |
| 建议后续测试 | 批 1 C-3 起：case 头解析、审计落库降级不阻断、出站透传；批 4：响应采集「关时零采集 / 开时脱敏生效」 |
| 已知测试环境干扰 | 强制结束正在做 C 扩展调用的 Python 进程（如 pytest 中途 `Stop-Process -Force`）会产生 faulthandler 段错误转储，属终止副作用，非被测代码缺陷；测试运行请勿中途强杀 |

---

## §14 遗留与下一步

| # | 类别 | 内容 | 处置 |
|---|------|------|------|
| 1 | 本里程碑 PENDING | 「日志写入不阻塞主请求、P99 增量 < 5ms」性能验收（方案 §6）**未做压测** | 待批 1 完成后随 C-9 补测或单独压测窗口执行 |
| 2 | 本里程碑 PENDING | `service.start` 中**提交号（version）注入**当前取 `OPENBASE_SERVICE_VERSION` 默认 `0.0.0` | 由 C-2 接线时统一注入（构建/启动传参） |
| 3 | 批 1 剩余 | C-2（其他服务入口接线）、C-3（case/step 头 → `request.state` + `extra`）、C-4（审计异步落库，复用 `audit_logs`）、C-5（出站透传 `X-Test-Case-Id`）、C-7（`scripts/test_log_aggregate.py`）、C-8（`/api/v1/audit/records` 增 `case_id`/`run_id` 过滤）、C-9（补测） | 按方案 §5 批 1 继续实施 |
| 4 | 编排器既有行为（非本次引入） | 前端服务 `stop` 只杀记录的包装进程 PID，其 `node`（vite）子进程可能变成孤儿继续占用 5173，导致下次 `start` 走「端口被占用 → 跳过启动」分支 | 记入遗留；后续可在 `Stop-Service` 增加按端口回溯杀子进程（需评估与 L2-1/L2-2 演练脚本的一致性） |
| 5 | 跨仓 | D-6 四仓 `request_id` 日志接线（独立任务，不阻塞本仓） | 由各仓按《D-6 四仓改动说明》推进 |
| 6 | 工作区噪声 | `openllm-k07-snapshot-commit-push.bat`（M，无内容行差异）、`dogfood-output/**`（未跟踪）为**既有未提交项**，不属本轮改动 | 保持原状，不纳入本轮提交 |
| 7 | 测试基建（**既有**，非本轮引入） | `tests/test_s7_t1_shr.py::test_s7_t1_1_global_entry_dry_run` 在本机环境**无限阻塞**：`_run_powershell()` 使用 `subprocess.run` **未设 `timeout=`**，被调脚本 `scripts/verify_env_global.ps1 -DryRun` 不退出（该脚本本轮未被修改，已确认与本批改动无关，`git status` 无该文件）；已用 `--timeout=45 --timeout-method=thread` 单测复现超时栈（阻塞点 `subprocess.py:1515 _readerthread`）。 | 全量回归以 `--deselect` 显式排除该用例后完成（见 §6.3，排除项已在报告登记）；**建议**后续为该测试工具函数补 `timeout=` 兜底并排查被调脚本的交互式阻塞（属独立任务，不在本批范围） |
| 8 | 测试隔离观察（既有） | 全量回归期间若并发修改 `doc/**`，`tests/test_s7_docs.py`（文档地图无游离）可能瞬时失败；本轮已复跑确认 **6 passed** | 已闭环 |
