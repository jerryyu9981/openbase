# OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.1.0

## 文档元信息

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-S7-DEVLOG-LOGS-v1.1.0 |
| 版本 | v1.1.0 |
| 状态 | [Review]（批 1（C-1~C-9）全量落地开发记录；沙箱可执行面已完成并留证，未执行项显式登记为 PENDING，禁伪造） |
| 日期 | 2026-09-14 |
| 作者 | AI（S7 批次 36~37 批 1 开发会话：TDD 实现、实跑验证与证据归档） |
| 版本主题 | **批 1 日志链路全量落地（C-1~C-9）**——①C-1 结构化日志落盘；②C-2 服务入口接线 + 提交号注入；③C-3 用例上下文头 → L1 请求级 JSON 日志；④C-4 审计记录 best-effort 落 `audit_logs`（复用 JSON `detail`，零迁移）；⑤C-5 出站透传 `X-Test-Case-Id`；⑥C-6 服务 stdout/stderr 采集；⑦C-7 聚合脚本产出证据；⑧C-8 审计查询过滤；⑨C-9 单测补齐。含逐项改动清单、RED→GREEN 摘要、静态质量检查、单测报告、实跑验证（L1/L2/L3）、编排器回归、变更统计、开发审计移交材料与测试移交说明 |
| 上游依据 | ①《OpenBase-人工端到端测试日志记录方案-v1.0.0.md》（OB-DESIGN-MANUAL-E2E-LOG-v1.0.0，内部 **v1.2.0 [Approved]**，§3.1 三层通道落点 / §4 字段与事件字典（含头承载口径）/ §5 改造清单（C-1~C-9）/ §5.1 实施进度 / §6 验收标准 / §9.1 决议记录）；②`observability-standards`（结构化 JSON、必填字段、禁止记录项）；③`AGENTS.md`（分层架构、日志规范、命名约定、测试规则）；④既有不变量 `tests/test_identity_t6.py`（T6-1：全仓 0 条按保留期限自动清除代码路径） |
| 适用范围 | **提交面仅 OpenBase 主仓**：`openbase/**`、`tests/**`、`scripts/**`、`doc/**`；**不改动 DPS/OpenLLM/OpenMemory/OpenRAG 四仓任何文件**（跨仓 request_id 接线属 D-6 独立任务）；**不纳入 `dogfood-output/`** |
| 证据面 | 运行期证据：`logs/openbase/openbase-2026091*.jsonl`（C-1/C-3/C-5 的 L1 记录）、`logs/openbase/*.log｜.err.log`、`logs/frontend/frontend-*.log`、`logs/oidc-idp/oidc-idp-20260914.jsonl`（C-2/C-6）；聚合证据：`doc/test/evidence/manual/run-20260914-0225.{json,md}`（含 FAIL 步骤）与 `run-20260914-0230.{json,md}`（PASS）；DB 证据：真实 PG `audit_logs` id=390/391（C-4） |
| 纪律 | 结论如实；未执行项一律 PENDING，禁伪造 hash、响应码与通过 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-14 | AI（S7 批次 36 批 1 里程碑开发会话） | 初始版本：批 1 首个里程碑 C-1 + C-6 开发记录报告（含 §9-7 与不变量 T6-1 冲突的处置闭环）。归档于 `doc/development/archive/`。 |
| v1.1.0 | 2026-09-14 | AI（S7 批次 37 批 1 全量落地会话） | **批 1（C-1~C-9）全量落地**：新增 §15 批 1 续做实施记录（C-2 提交号注入与 IdP 入口接线 / C-3 用例上下文头与 L1 日志 / C-4 审计落库与降级 / C-5 出站透传与头注入防护 / C-7 聚合脚本与退出码 / C-8 查询过滤 / C-9 单测补齐），同步更新 §1 目标、§3 任务清单、§6 测试结论、§10 追溯矩阵、§11 变更统计、§12/§13 移交材料与 §14 遗留。设计依据升至方案 v1.2.0。 |

---

## §1 范围与目标

- **本报告**为《OpenBase-人工端到端测试日志记录方案》**批 1（C-1~C-9）**的开发环节交付物（v1.0.0 记录首个里程碑 C-1+C-6；v1.1.0 追加 C-2~C-5/C-7~C-9，见 §15），落点 `doc/development/`，状态 [Review]。
- **目标**：
  1. **C-1**：OpenBase 侧结构化日志落盘（JSON Lines、按日切分、必填字段齐全、敏感字段脱敏、超长值截断），并具备请求级上下文注入能力（供 C-3 接线）；
  2. **C-6**：编排器启动子进程时把每个服务的 stdout/stderr 采集落盘，消除现状缺口 **G-2**（「服务日志未采集」），使人工 E2E 期间「服务是否起来、报了什么错」有文件可查；
  3. **C-2~C-5、C-7~C-9（v1.1.0 追加，批 1 全量）**：服务入口接线与提交号注入 → 用例上下文贯穿（头 → L1 日志 → 出站透传 → 落库 → 查询过滤）→ 一键聚合证据，形成「人工测试结果可按 run/case/step 检索 + 与客观响应按 `request_id` 关联」的闭环。
- **非目标**：不改接口契约（仅新增只读查询参数）、不改权限模型、不改前端；批 2（C-10~C-12 受权 API 与前端面板）与批 4（C-15~C-19 响应级观测）不在本批；不推进 D-6 跨仓接线。
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
| 既有不变量预检（**复盘为入场缺项**） | v1.0.0 入场时**未**先扫描 `openbase/**` 既有静态不变量（如 `tests/test_identity_t6.py` 的 T6-1 标识扫描），导致 C-1 首版引入自动清理路径后被门禁捕获并返工；**v1.1.0 已改进**：续做前后均先运行 T6-1 等相关不变量用例 | v1.0.0 已返工闭环（§9-7）；v1.1.0 前置预检通过（T6-1 23 passed） |

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
| T10 | C-2 提交号注入 + 仓内第二服务入口（oidc-idp）接线 | `logging_setup._resolve_version`、`scripts/oidc-idp/idp_server.py` | 完成（§15.1） |
| T11 | C-3 用例上下文头解析 + `request.state` + L1 请求级 JSON 日志 | `audit/__init__.py`、`protocol_headers/constants.py` | 完成（§15.2） |
| T12 | C-4 审计记录 best-effort 落库 + 跨重启按 case 查询 | `audit/__init__.py` | 完成（§15.3） |
| T13 | C-5 出站透传 `X-Test-Case-Id`/`X-Test-Step-Id` + 头注入防护 | `protocol_headers/inject.py` | 完成（§15.4） |
| T14 | C-7 聚合脚本（分组 + 双证据 + 退出码 0/1/2） | `scripts/test_log_aggregate.py` | 完成（§15.5） |
| T15 | C-8 `/api/v1/audit/records` 增 `case_id`/`run_id` 过滤 | `audit/__init__.py` | 完成（§15.6） |
| T16 | C-9 单测补齐（合计 46 例） | `tests/test_test_case_context.py` 等 4 文件 | 完成（§15.7） |

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
| Python 静态检查 | `python -m ruff check openbase tests scripts/test_log_aggregate.py scripts/oidc-idp/idp_server.py` | **All checks passed!（0 错）** |
| 脚本语法检查 | PowerShell AST `ParseFile(scripts/service-orchestrator.ps1)`；`python -m py_compile scripts/test_log_aggregate.py` | **SYNTAX OK（0 解析错误）** |

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
- 结果：**716 passed / 6 failed / 4 skipped / 1 deselected**（执行 726 项；较 v1.0.0 那轮 692 项增加 34 项 = 本轮新增/扩充单测）

| 类别 | 明细 | 判定 |
|------|------|------|
| passed | 716 | 含本轮新增/扩充 46 例（其中 34 例为新增用例）与既有不变量（T6-1 / 文档地图 / SHR） |
| skipped | 4 | `tests/test_storage_s3_real.py`（4 项，需真实 S3 凭据，**既有跳过项**） |
| failed | 6 | ①`test_tenant_admin.py`（2）+ `test_users_admin.py`（2）：全部为 `asyncpg.exceptions.ConnectionDoesNotExistError`（共享 PG 抖动）；②`test_s7_docs.py::test_doc_map_index_includes_new_docs` + `test_s7_t1_shr.py::test_s7_t1_5_manifest_entries_exist`：文档地图 MANIFEST 指向已被升版的旧 DevLogReport 路径（**运行期间并发编辑文档导致的自伤项**） | **均已闭环**：①单独复跑 `test_tenant_admin.py tests/users_admin.py` → 通过；②文档地图更新完成后两项复跑 → 通过（见下方复跑证据） |
| deselected | 1 | `test_s7_t1_1_global_entry_dry_run`（既有无限阻塞用例，见 §14-7） |

**失败项复跑证据**（本次）：`python -m pytest tests/test_s7_docs.py tests/test_s7_t1_shr.py tests/test_tenant_admin.py tests/test_users_admin.py tests/test_test_case_context.py tests/test_audit_db_persist.py tests/test_test_log_aggregate.py tests/test_logging_setup.py -q --deselect "<hang case>"` → **EXIT=0，0 FAILED**。

> 与 v1.0.0 那轮的差异：那轮 684 passed / 4 failed（PG 抖动）/ 4 skipped / 1 deselected；本轮新增 34 项单测全部通过，失败项性质同前（PG 抖动）＋两项文档并发自伤（已闭环）。
> 教训（再次印证 v1.0.0 §14-8）：**全量回归期间不得并发修改 `doc/**`**——文档地图一致性用例会瞬时失败。建议后续将「文档编辑」与「全量回归」串行执行。

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

### 7.4 L2/L3 续做验证（C-2~C-9，v1.1.0 追加）

| 步骤 | 实测结果 | 证据位置 |
|------|---------|---------|
| 重启 `oidc-idp` + `openbase`（加载新代码） | 两者健康检查通过（PID 25380 / 22664），7 服务全部健康 ✅ | `logs/service-orchestrator/orchestrator-20260914.log` |
| 带用例头打真实请求（4 步：服务列表 / 审计查询 / DPS 画像 / DPS 画像计算） | 3×200 + 1×404（后者为上游业务响应） | §15.2 / §15.4 |
| L1 结构化日志 | 记录含 `case_id/step_id/run_id/channel` + `version="966745b"` | §15.2 JSON 片段 |
| 审计落库（C-4） | 真实 PG `audit_logs` 命中 2 行、字段齐全 | §15.3 |
| 聚合证据（C-7） | `run-20260914-0230`（PASS，退出码 0）、`run-20260914-0225`（FAIL，退出码 1） | `doc/test/evidence/manual/` |
| 编排器全量检查（L3 域检查） | **27 PASS / 0 FAIL / 0 SKIP**（重启后复跑） | 本节 §7.3 同口径 |

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
| C-3 审查（v1.1.0） | 用例上下文解析放在 `dispatch` 起始、`_record` 与 L1 日志共用同一 `_test_context_fields()`，避免双份取值逻辑漂移；缺省不产生任何字段（**未启用测试模式即零影响**）；非身份头常量带「禁止加入裁剪集」注释并有单测锁定 |
| C-4 审查（v1.1.0） | 落库为 **best-effort**：`try/except` 包住、失败仅 `warning` + `rollback`、**绝不 re-raise**；开关默认开但可关；`user_id` 非数字时置 None（避免类型转换异常）；`resource`/`user_agent` 按列长度截断；查询走 SQLAlchemy 表达式（**参数化，零字符串拼接**） |
| C-5 审查（v1.1.0） | 非身份头**不做 fail-closed**（非法值丢弃而非 400），避免测试头错误影响业务；值与 `X-Request-Id` 同源策略一致；放在身份解析之前，使匿名/服务级出站也可按 case 聚合 |
| C-7 审查（v1.1.0） | 只读 `*.jsonl`；非法行计入 `skipped_lines` 不崩溃；无记录时不产出空报告（避免证据污染）并返回 PENDING(2)；退出码与项目统一口径（0/1/2）一致；Markdown 明示「人工判定为准、不参与门禁」（D-3） |
| C-2 审查（v1.1.0） | 提交号获取 `lru_cache` 化（进程内仅一次子进程调用、5s 超时、失败静默）；IdP 入口导入失败回落 `basicConfig`，**日志装配不得阻断服务启动** |

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
| 方案 §5 C-2（v1.1.0） | 服务入口装配 + `service.start`（含版本/提交号） | `demo_app.py`、`scripts/oidc-idp/idp_server.py`、`logging_setup._resolve_version` | 实测 `version="966745b"`；单测 5 例 |
| 方案 §5 C-3（v1.1.0） | ①读 `X-Test-Case-Id`/`X-Test-Step-Id` → `request.state`；②`extra` 增 `case_id/step_id/run_id/channel`；③JSON 日志落盘（复用同一 formatter） | `audit/__init__.py`（`_extract_test_context`/`_emit_request_log`）、`protocol_headers/constants.py` | 实测 L1 记录含全部用例字段；单测 14 例 |
| 方案 §5 C-4（v1.1.0） | 审计记录异步落 DB（`audit_logs`，best-effort，失败仅 WARN 不阻断）；内存缓冲保留；按 `case_id` 查询 | `audit/__init__.py`（`_persist_audit_record`/`query_audit_logs_by_case`） | 真实 PG 命中 2 行（id=390/391）；单测 7 例 |
| 方案 §5 C-5（v1.1.0） | 出站头增可选 `X-Test-Case-Id` 透传（与 `X-Request-Id` 同源策略） | `protocol_headers/inject.py` | 实测带三头代理 200（非 403）；单测 4 例 |
| 方案 §5 C-7（v1.1.0） | 按 `run_id`/`case_id` 聚合 `logs/**/*.jsonl` → `doc/test/evidence/manual/<run_id>.json` + `.md`；退出码 0/1/2 | `scripts/test_log_aggregate.py` | 实测 PASS（run-20260914-0230）与 FAIL（run-20260914-0225）两路径；单测 8 例 |
| 方案 §5 C-8（v1.1.0） | 既有 `/api/v1/audit/records` 增 `case_id`/`run_id` 过滤（只读） | `audit/__init__.py` | 实测 `?case_id=` 命中当步记录；单测 2 例 |
| 方案 §7 风险行「自定义头被误加入身份集合」 | 显式标注「非身份头，禁止加入裁剪集」 | `protocol_headers/constants.py` 注释 + 单测断言 `not in IDENTITY_HEADERS/INBOUND_IDENTITY_HEADERS` | `test_test_case_headers_are_not_identity_headers` |

---

## §11 变更统计与影响文件清单

> 本次统计**仅覆盖本轮实际修改/生成的文件**；工作区既有未提交项（`openllm-k07-snapshot-commit-push.bat`、`dogfood-output/**`）**不计入本轮**。

### 11.1 本批（v1.1.0）代码/脚本变更

| 文件 | 类型 | 变更性质 | 新增行 | 删除行 | 说明 |
|------|------|---------|-------|-------|------|
| `openbase/modules/audit/__init__.py` | 生产代码 | 修改 | 288 | 24 | C-3 用例上下文与 L1 日志 + C-4 落库与查询 + C-8 过滤（总 523 行） |
| `openbase/modules/protocol_headers/inject.py` | 生产代码 | 修改 | 45 | 1 | C-5 出站透传 + 头注入防护（总 208 行） |
| `openbase/modules/protocol_headers/constants.py` | 生产代码 | 修改 | 18 | 0 | 三头常量 + 非身份头约束注释（总 120 行） |
| `openbase/core/logging_setup.py` | 生产代码 | 修改 | 47 | 4 | C-2 提交号注入（总 335 行） |
| `scripts/oidc-idp/idp_server.py` | 脚本 | 修改 | 13 | 1 | C-2 服务入口接线 + 兜底（总 313 行） |
| `scripts/test_log_aggregate.py` | 脚本 | **新增** | 268 | 0 | C-7 聚合器 |
| `tests/conftest.py` | 测试代码 | 修改 | 4 | 0 | C-4 落库开关测试隔离 |

### 11.2 本批测试变更

| 文件 | 变更性质 | 新增行 | 删除行 | 说明 |
|------|---------|-------|-------|------|
| `tests/test_test_case_context.py` | **新增** | 227 | 0 | C-3/C-5/C-8 单测 14 例 |
| `tests/test_audit_db_persist.py` | **新增** | 213 | 0 | C-4 单测 7 例 |
| `tests/test_test_log_aggregate.py` | **新增** | 199 | 0 | C-7 单测 8 例 |
| `tests/test_logging_setup.py` | 修改 | 57 | 0 | C-2 版本解析 4 例 + IdP 接线 1 例（总 248 行 / 17 例） |

### 11.3 本批文档与证据

| 文件 | 变更性质 | 行数/大小 | 说明 |
|------|---------|----------|------|
| `doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.1.0.md` | **新增（v1.0.0 升版）** | 358 行 | 本报告（含 §15） |
| `doc/development/archive/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.0.0.md` | **归档（只读）** | 341 行 | v1.0.0 基线归档 |
| `doc/design/OpenBase-人工端到端测试日志记录方案-v1.0.0.md` | 修改（v1.1.2 → **v1.2.0**） | +20 / -10 | §4.2 头承载口径、§5.1 全量实施进度、修订历史 |
| `doc/design/OpenBase-文档地图索引-v1.0.0.md` | 修改（v1.0.10 → **v1.0.11**） | +13 / -5 | DevLogReport 升版 + 聚合脚本与证据条目 + MANIFEST |
| `doc/test/evidence/manual/run-20260914-0230.json｜.md` | **新增（证据）** | 1456B / 1510B | L3 冒烟 PASS 轮次聚合证据 |
| `doc/test/evidence/manual/run-20260914-0225.json｜.md` | **新增（证据）** | 1739B / 1619B | FAIL 路径实测证据 |

### 11.4 v1.0.0 里程碑回顾（已随 `966745b` 提交）

| 文件 | 变更性质 | 新增行 | 删除行 |
|------|---------|-------|-------|
| `openbase/core/logging_setup.py` | 新增（该轮） | 298 | 0 |
| `openbase/demo_app.py` | 修改 | 15 | 0 |
| `scripts/service-orchestrator.ps1` | 修改 | 54 | 4 |
| `tests/conftest.py` | 修改 | 5 | 0 |
| `tests/test_logging_setup.py` | 新增（该轮） | 210 | 0 |
| `doc/development/OpenBase-S7-人工端到端测试日志落盘-DevLogReport-v1.0.0.md` | 新增（该轮） | 253 | 0 |
| `doc/design/OpenBase-人工端到端测试日志记录方案-v1.0.0.md` | 修改 | 18 | 4 |
| `doc/design/OpenBase-文档地图索引-v1.0.0.md` | 修改 | 6 | 3 |

> 该轮提交：`966745b`（8 files changed, +1067 / -11）。

### 11.5 运行期产物（不纳入 git）

| 路径 | 说明 |
|------|------|
| `logs/openbase/openbase-20260913.jsonl` | C-1 落盘证据 |
| `logs/openbase/openbase-20260914.jsonl` | C-3/C-5 的 L1 记录（含用例字段、`version`） |
| `logs/openbase/openbase-2026091*.log` / `.err.log` | C-6 采集证据（stdout / stderr） |
| `logs/frontend/frontend-20260914.log` | C-6 `npm.cmd` 路径证据 |
| `logs/oidc-idp/oidc-idp-20260914.jsonl` | C-2 IdP 结构化日志证据 |
| `logs/service-orchestrator/orchestrator-2026091*.log` | 编排器回归过程日志 |

---

## §12 开发审计移交材料

| 移交项 | 内容 | 位置 |
|-------|------|------|
| 设计条目 → 实现映射 | §10 设计开发追溯矩阵（14 行，覆盖 C-1~C-8、字段字典、禁止记录、落点、里程碑、T6-1 不变量、非身份头风险） | 本报告 §10 |
| 静态质量证据 | ruff 0 错 + PowerShell AST 0 错（含 4 项修复复审） | 本报告 §5、§9 |
| 单测证据 | 批 1 合计 46 例：`tests/test_logging_setup.py` 17 / `tests/test_test_case_context.py` 14 / `tests/test_audit_db_persist.py` 7 / `tests/test_test_log_aggregate.py` 8；相关既有不变量回归 T6-1 23 passed、文档地图 6 passed | 本报告 §6.1、§6.2、§15.7 |
| 全量回归证据 | `python -m pytest tests` 结论 | 本报告 §6.3 |
| 实跑证据 | L1 JSONL（含用例字段）/ DB `audit_logs` 两行 / 聚合证据两份（PASS+FAIL）/ `checkall` 27 PASS | 本报告 §7、§15 |
| 变更统计 | 代码/脚本/测试/文档逐项增删行 | 本报告 §11 |
| 未闭环项 | 见 §14（性能压测、上游确认、既有测试基建与污染、环境抖动） | 本报告 §14 |

**审计要点提示**：①本批**未触碰既有接口契约语义**（仅新增只读查询参数 `case_id`/`run_id`）与前端；②`logs/**` 为运行期产物不入库（`gitignore` 覆盖），而聚合证据 `doc/test/evidence/manual/**` **随本批入库**、与方案 §5 C-7 落点一致，审计可直接核对；③方案 §5 C-6 括注提到的 `-DryRun` 语义在本脚本中不存在（已在 v1.0.0 §8 显式说明）；④§15.8 三项实施期设计补充需评审追认。

---

## §13 测试移交说明

| 项 | 内容 |
|----|------|
| 新增测试 | ①`tests/test_logging_setup.py`（17 例：必填字段/字段保留/脱敏/截断/上下文/过滤器/按日切分/无自动删除/无自动清除标识/幂等/级别 + 版本解析 4 例 + IdP 接线 1 例）；②`tests/test_test_case_context.py`（14 例：C-3 头解析与 L1 日志 7 例 / C-5 出站透传 4 例 / C-8 过滤 2 例 / 非身份头约束 1 例）；③`tests/test_audit_db_persist.py`（7 例：落库字段/开关/降级/dispatch/SQLite 查询 3 例）；④`tests/test_test_log_aggregate.py`（8 例：分组/过滤/健壮性/输出/退出码/Markdown 列） |
| 执行命令 | `python -m pytest tests/test_logging_setup.py tests/test_test_case_context.py tests/test_audit_db_persist.py tests/test_test_log_aggregate.py -q`；`python -m ruff check openbase tests scripts/test_log_aggregate.py scripts/oidc-idp/idp_server.py`；`python -m pytest tests -q` |
| 环境前置 | 单测无需外部服务（C-4 用假会话/内存 SQLite）；编排器回归需 7 服务在线（`-Action checkall` 基线 27 PASS / 0 FAIL / 0 SKIP）；聚合脚本可脱机运行（只读 `logs/**`） |
| 测试隔离约束 | ①`OPENBASE_LOG_SETUP=0` 时不装配文件日志；②`OPENBASE_AUDIT_DB_PERSIST=0` 时不做请求期落库（`tests/conftest.py` 默认置 0，避免全量测试逐请求连库）；需验证落库/降级的用例显式置 1 并注入假会话工厂 |
| 建议后续测试 | 批 2：受权 API 权限矩阵（`test:record`）、前端测试模式开关零影响、面板改判留痕；批 4：响应采集「默认关闭时 0 条 / 开启时脱敏生效 / ≤2KB」 |
| 已知测试环境干扰 | ①强制结束正在做 C 扩展调用的 Python 进程会产生 faulthandler 段错误转储（终止副作用，非缺陷）；②共享 PG 抖动会造成 `test_tenant_admin`/`test_users_admin` 偶发失败（复跑即绿，见 §14-10）；③自选子集顺序会触发既有跨文件污染（见 §14-9），建议以全量顺序运行 |

---

## §14 遗留与下一步

| # | 类别 | 内容 | 处置 |
|---|------|------|------|
| 1 | 本批 PENDING | 「日志写入不阻塞主请求、P99 增量 < 5ms」性能验收（方案 §6）**未做压测**；C-4 落库在请求尾增加一次 DB 往返（awaited best-effort），其耗时增量同样未量化 | 建议随批 4 或独立压测窗口执行；如需先降风险，可将 `OPENBASE_AUDIT_DB_PERSIST=0` 关闭落库 |
| 2 | 已闭环（v1.1.0） | 提交号注入：改为 `_resolve_version()`（显式 > `OPENBASE_SERVICE_VERSION` > git 短提交号 > `0.0.0`） | 实测日志 `version="966745b"`（§15.1） |
| 3 | 已闭环（v1.1.0） | 批 1 剩余项 C-2~C-5、C-7~C-9 **全部落地**（§15） | 下一步为批 2（C-10~C-12：受权 API + 前端测试模式与面板） |
| 4 | 编排器既有行为（非本次引入） | 前端服务 `stop` 只杀记录的包装进程 PID，其 `node`（vite）子进程可能变成孤儿继续占用 5173，导致下次 `start` 走「端口被占用 → 跳过启动」分支 | 记入遗留；后续可在 `Stop-Service` 增加按端口回溯杀子进程（需评估与 L2-1/L2-2 演练脚本的一致性） |
| 5 | 跨仓 | D-6 四仓 `request_id` 日志接线（独立任务，不阻塞本仓） | 由各仓按《D-6 四仓改动说明》推进 |
| 6 | 工作区噪声 | `openllm-k07-snapshot-commit-push.bat`（M，无内容行差异）、`dogfood-output/**`（未跟踪）为**既有未提交项**，不属本轮改动 | 保持原状，不纳入本轮提交 |
| 7 | 测试基建（**既有**，非本轮引入） | `tests/test_s7_t1_shr.py::test_s7_t1_1_global_entry_dry_run` 在本机环境**无限阻塞**：`_run_powershell()` 使用 `subprocess.run` **未设 `timeout=`**，被调脚本 `scripts/verify_env_global.ps1 -DryRun` 不退出（该脚本本轮未被修改，已确认与本批改动无关，`git status` 无该文件）；已用 `--timeout=45 --timeout-method=thread` 单测复现超时栈（阻塞点 `subprocess.py:1515 _readerthread`）。 | 全量回归以 `--deselect` 显式排除该用例后完成（见 §6.3，排除项已在报告登记）；**建议**后续为该测试工具函数补 `timeout=` 兜底并排查被调脚本的交互式阻塞（属独立任务，不在本批范围） |
| 8 | 测试隔离观察（既有） | 全量回归期间若并发修改 `doc/**`，`tests/test_s7_docs.py`（文档地图无游离）可能瞬时失败；本轮已复跑确认 **6 passed** | 已闭环 |
| 9 | 测试污染观察（既有，**非本轮引入**） | 以「自选文件子集 + 特定顺序」运行时会触发既有跨文件顺序污染：`tests/test_gateway.py` 等前置文件之后运行 `tests/test_identity_t6.py` 的 purge 族用例会报 `sqlite3.OperationalError: no such table: openbase.agent_api_keys/roles`（共享 sqlite 会话/全局 engine 残留）。**验证方式**：去掉了本轮全部新增测试文件后以同一子集复跑，仍复现同样 13 条失败 → 与本批改动无关；全量顺序（字母序）运行无此现象。 | 记入遗留；建议后续为测试加统一的 DB 单例/会话隔离 fixture（属测试基建独立任务） |
| 10 | 共享基础设施抖动（环境） | 本轮实跑与全量回归期间多次出现 `asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation`（共享 PG `192.168.0.151:5432`），表现为 `test_tenant_admin`/`test_users_admin` 偶发失败（单独复跑即绿）与独立查询脚本首跑失败 | 属环境性抖动；本轮全部相关结论均以「单独复跑通过」为闭环证据；影响登记为环境风险，不改代码 |
| 11 | 跨仓确认 PENDING | C-5 的「上游子系统是否确实收到 `X-Test-Case-Id`」无法在本仓侧证实（子系统当前不记录该头），依赖 D-6 四仓 request_id/case 日志接线 | 本批结论限定为「本仓装配正确 + 不破坏信任链」；跨仓确认随 D-6 推进 |

---

## §15 批 1 续做实施记录（C-2~C-9，批 1 全量落地）

> 本节记录 v1.1.0 新增部分（C-2/C-3/C-4/C-5/C-7/C-8/C-9）。执行纪律同前：**TDD（RED→GREEN）**、证据真实、未执行项 PENDING。

### 15.1 C-2 服务入口接线 + 提交号注入

**改动**：

| 文件 | 改动 |
|------|------|
| `openbase/core/logging_setup.py` | 新增 `_git_short_commit()`（`lru_cache`，best-effort 调 `git rev-parse --short HEAD`，失败返回 None）与 `_resolve_version()`（显式入参 > `OPENBASE_SERVICE_VERSION` > git 短提交号 > `"0.0.0"`）；`setup_logging(..., version=None)` |
| `scripts/oidc-idp/idp_server.py` | 仓内第二个常驻服务入口接线：`setup_logging(service="oidc-idp")`；无法导入 `openbase`（独立运行）时回落原 `basicConfig`；`OPENBASE_LOG_SETUP=0` 可关闭 |

**RED→GREEN**：新增 5 个单测（`test_resolve_version_prefers_explicit_then_env` / `_falls_back_to_git_commit` / `_defaults_when_git_unavailable` / `test_setup_logging_version_flows_into_records` / `test_oidc_idp_entry_wires_structured_logging`）→ 初始 RED（`_resolve_version` 不存在、`version` 参数不存在）→ 实现后全绿。

**实跑证据**：重启后服务日志 `version` 字段为 **`966745b`**（当前 git 短提交号，证明注入生效）；`logs/oidc-idp/oidc-idp-20260914.jsonl` 253B（IdP 结构化落盘生效），同服务 stdout/stderr 由 C-6 采集。

### 15.2 C-3 用例上下文贯穿（头解析 + L1 请求级日志）

**改动**：

| 文件 | 改动 |
|------|------|
| `openbase/modules/protocol_headers/constants.py` | 新增 `HEADER_TEST_CASE_ID`/`HEADER_TEST_STEP_ID`/`HEADER_TEST_RUN_ID` 与 `TEST_CONTEXT_HEADERS`；**注释显式声明「非身份头，禁止加入身份头/入站裁剪集」**（方案 §7 风险应对项落地） |
| `openbase/modules/audit/__init__.py` | `_extract_test_context()`（读三头；`step_id` 数字归一 int；`run_id` 缺省回退 `OPENBASE_TEST_RUN_ID`）→ `dispatch` 写入 `request.state`；`_test_context_fields()` 渲染记录字段；`_record` 的 `extra` 增 `case_id/step_id/run_id/channel`；新增 `_emit_request_log()` 输出 L1 JSON 日志（`message="api.request"`） |

**RED→GREEN**：`tests/test_test_case_context.py` 14 例（含「非身份头常量约束」「头解析/归一化」「run_id 环境回退」「dispatch 写 state」「extra 字段」「L1 日志字段」「缺省零影响」）先 RED 后 GREEN。

**实跑证据**（真实请求，`logs/openbase/openbase-20260914.jsonl`）：

```json
{"ts":"2026-09-13T18:22:47.059+00:00","level":"INFO","service":"openbase","module":"openbase.audit",
 "message":"api.request","env":"dev","version":"966745b","request_id":"req-ff86834ff7ff",
 "method":"GET","path":"/api/v1/services","status_code":200,"duration_ms":113,
 "case_id":"AD-HOC-20260914-01","channel":"B","step_id":1,"run_id":"run-20260914-0225"}
```

### 15.3 C-4 审计记录 best-effort 落库

**改动**（`openbase/modules/audit/__init__.py`）：

- 新增 `ENV_AUDIT_DB_PERSIST`（默认 `1` 开）与 `ACTION_API_REQUEST="api.request"`；
- `_record` 改为返回 `APICallRecord | None`；`dispatch` 在响应后（含异常路径）调用 `_persist_audit_record()`；
- `_persist_audit_record()`：复用 `audit_logs`（`detail` JSON 扩展，**零迁移**，对应 D-2=①），写入 `status_code/duration_ms/method/path/channel/case_id/step_id/run_id`（非空键）+ `identity`（有主体时）+ `error`（有错误时）；失败仅 **WARN + rollback**，绝不阻断请求；
- 新增 `query_audit_logs_by_case()`：SQLAlchemy JSON 路径表达式（PG `->>'case_id'`）参数化过滤，提供**跨重启**检索口。

**RED→GREEN + 实跑证据**：`tests/test_audit_db_persist.py` 7 例（落库字段 / 开关关闭零访问 / 失败降级 WARN+rollback / dispatch 接线 / SQLite 真表查询 3 例）全绿；真实 PG 复核：

```text
命中 2 行（case_id=AD-HOC-20260914-01）
  id=391 request_id=req-d36499062a22 step=2 run=run-20260914-0225 status=200 path=/api/v1/audit/records
  id=390 request_id=req-ff86834ff7ff step=1 run=run-20260914-0225 status=200 path=/api/v1/services
缺失字段: 无
```

**设计取舍记录**：采用「awaited best-effort」而非 `asyncio.create_task` 后台任务——避免无人管理的任务在关机/测试中泄漏；代价是请求尾部多一次 DB 往返（性能验收仍为 §14-1 PENDING）。

### 15.4 C-5 出站透传与头注入防护

**改动**（`openbase/modules/protocol_headers/inject.py`）：`build_outbound_headers(..., test_case_id=None, test_step_id=None)`；取值口径与 `X-Request-Id` 同源（显式入参 > `request.state` > 不注入）；`_test_context_value()` 对非身份头**不做 fail-closed 校验**——空值/超长（>64）/含 CR-LF 一律**丢弃**（防头注入，且不因测试头非法而 400 影响业务）。

**RED→GREEN + 实跑证据**：单测 4 例（state 取值 / 缺省不注入 / 显式优先 / 注入防护）；真实链路：带三头请求 `GET /api/v1/dps-proxy/portraits` → **200**（若被误判为身份头将为 `403 PERM_UNTRUSTED_IDENTITY_HEADER`，即方案 §3.3 关键设计成立）；另一路径返回的是**上游 DPS 业务响应**（`404 画像不存在`），证明出站链路与上游交互正常。

> 上游侧「是否确实收到 `X-Test-Case-Id`」的确认依赖 D-6（四仓 request_id/case 日志接线），属独立跨仓任务；本批结论限定为「本仓装配正确 + 不破坏信任链」。

### 15.5 C-7 日志聚合脚本

**新增** `scripts/test_log_aggregate.py`（聚合 `logs/**/*.jsonl` → `doc/test/evidence/manual/<run_id>.json｜.md`）：

- 分组：`run_id → case_id`；步骤排序稳定；无用例上下文的记录归入 `<unlabeled>`（仅计总数）；
- 字段：`schema_version/tool/openbase_commit/checked_at/logs_root/run_id/status/totals{records,cases,failed_steps}/cases[{case_id,run_id,status,records,failed_steps,steps[{step_id,request_id,method,path,status_code,duration_ms}]}]/sources/skipped_lines`；
- 失败口径：步骤 `status_code ≥ 400` 或含 `error`；
- 退出码：**0=PASS / 1=FAIL / 2=PENDING（无记录，且不产出空报告）**；
- 只读取 `*.jsonl`（C-6 的纯文本 `.log` 不参与），非法行计入 `skipped_lines` 而非崩溃。

**RED→GREEN + 实跑证据**：`tests/test_test_log_aggregate.py` 8 例全绿；真实聚合两次：

| 轮次 | 结果 | 退出码 | 说明 |
|------|------|--------|------|
| `run-20260914-0225` | FAIL（4 记录 / 1 用例 / 1 失败步骤） | 1 | 含一次探针路径 404 → **FAIL 路径实测** |
| `run-20260914-0230` | PASS（3 记录 / 1 用例 / 0 失败步骤） | 0 | 三步全 200 → **PASS 路径实测** |

### 15.6 C-8 审计查询过滤

**改动**：`AuditService.records(limit, case_id=None, run_id=None)` 返回记录新增 `case_id/step_id/run_id/channel` 并支持双维过滤；`GET /api/v1/audit/records` 暴露 `case_id`/`run_id` 查询参数（只读）。

**RED→GREEN + 实跑证据**：单测 2 例（服务层过滤矩阵 / HTTP 端点参数）；真实服务实测 `GET /api/v1/audit/records?case_id=AD-HOC-20260914-01` → 200，返回体中命中同一 `request_id` 的当步记录。

### 15.7 C-9 单测补齐（合计）

| 文件 | 用例数 | 覆盖 |
|------|-------|------|
| `tests/test_logging_setup.py`（扩充） | 17 | C-1 formatter/脱敏/截断/上下文/按日切分/无自动删除/无自动清除标识/幂等/级别 + C-2 版本解析 4 例 + IdP 接线 1 例 |
| `tests/test_test_case_context.py`（新增） | 14 | C-3 头解析与 L1 日志、C-5 出站透传、C-8 过滤、非身份头约束 |
| `tests/test_audit_db_persist.py`（新增） | 7 | C-4 落库/降级/开关/dispatch/SQLite 查询 |
| `tests/test_test_log_aggregate.py`（新增） | 8 | C-7 分组/过滤/健壮性/输出/退出码/Markdown 列 |
| **合计** | **46** | 批 1 全部改造项 |

### 15.8 实施期设计补充（需评审追认）

| 补充项 | 原因 | 影响面 |
|-------|------|-------|
| 新增 `X-Test-Run-Id` 头（缺省回退 `OPENBASE_TEST_RUN_ID`） | 原设计 §4.2 定义 `run_id` 字段，但 §3.2 仅给出 case/step 头 → C-7/C-8 的 run 维度聚合无来源 | 非身份头；不注入时不产生任何字段（零影响）；已同步方案 §4.2 头承载口径与 v1.2.0 修订历史 |
| 新增 `OPENBASE_AUDIT_DB_PERSIST` 开关（默认开，测试环境关） | 每请求落库会拖慢测试并受共享 PG 抖动影响（本轮实测已见 PG 连接抖动） | 生产可关闭；测试隔离在 `tests/conftest.py` 显式登记 |
| `_persist_audit_record` 采用 awaited best-effort（非后台任务） | 避免无管理的 asyncio 任务在关机/测试中泄漏；保证可测试性 | 请求尾多一次 DB 往返（性能验收 PENDING，见 §14-1） |
