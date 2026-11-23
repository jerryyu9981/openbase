# OpenBase 画像三波次全栈端到端走查报告

| 项 | 内容 |
|---|---|
| 文档编号 | OB-TEST-PORTRAIT-WAVES-E2E |
| 版本 | v1.1.0 |
| 状态 | [Review] |
| 适用版本 | DPS 2.20.2 + OpenBase 主线 |
| 环境 | 本机全栈（OpenBase 8000 / DPS 8030 / 前端 5173），共享 PG 192.168.0.151 |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次全栈走查：API 33 项、UI 4 页；发现 5 项缺陷并修复复测 | AI 编码代理 |
| v1.1.0 | 2026-11-23 | 方案 B 接线：dps-proxy 导出补写 `log.export` 留痕；新增验证脚本，真机 10/10 通过 | AI 编码代理 |

## 1. 范围与方法

- 拉起方式：`scripts/service-orchestrator.ps1 -Action start -Only openbase,dps,frontend`（共享库主用 192.168.0.151）。
- 开关：`DPS_PROGRESS_ENABLED=true`、`DPS_INGEST_PERSIST_ENABLED=true`、`DPS_SCHEDULER_ENABLED=false`、`DPS_DATA_SCOPE_MODE=off`、PII `enforce`。
- API 链路：浏览器同源 → OpenBase JWT → dps-proxy → DPS（uvicorn 8030）→ 共享 PG `platform`。
- 受控写入：统一使用 `e2e20261123` 前缀的合成主体/事项/调度/任务；结束时按前缀清理（剩余 0 行）。
- UI：Playwright Chromium，注入真实登录 token，覆盖画像列表/总览/详情与任务中心。

## 2. 结果总览

| 面 | 结果 |
|---|---|
| API 走查 | **33/33 通过**（登录、模块、健康、画像列表/详情、模板、标注、标签、报表、组织、引入列表/预览、事项 CRUD、进度计算/趋势/事项/逾期、Cron 预览、调度列表/创建、任务列表/重试、审计、导出） |
| UI 关键页 | **3/3 通过**（画像列表 /portrait/list、画像总览 /portrait/overview、画像详情 /portrait/:id；无 console error/warn、无渲染兜底） |
| UI 任务中心 | **1/1 通过**（四页签、画像计算任务列表与刷新，无 console error/warn） |
| 审计 | 3855+ 条，覆盖 `CREATE` / `READ` / `DELETE` |
| 导出审计 | `log.export` 落 OpenBase `openbase.audit_logs`，request_id 对齐、链校验通过（验证 10/10） |
| PII | admin 持 `dps:pii:view` 见明文（设计如此）；analyst（user 2）手机号 `138****8000`、身份证剔除 |

证据：

- `doc/test/evidence/portrait-waves/e2e/api-walkthrough-20261123-185305.json`（33/33）
- `doc/test/evidence/s6/ui-e2e/artifacts/`（Playwright 通过截图/trace）

## 3. 发现与修复

| # | 缺陷 | 影响 | 修复 | 复测 |
|---|---|---|---|---|
| D1 | 存量库 `portrait_calc_task` 缺 `retry_count`，v2.20 迁移未补列 | 人工重试与失败计数在旧库直接 500 | `schema_v2_20_upgrade` 增加列迁移；新增回归用例 | 迁移幂等，重试接口 200 |
| D2 | PG 上画像删除传 ISO 字符串给 `timestamptz` 参数 | `DELETE /portrait/{id}` 500 | 改为传 `datetime` 对象 | 删除 200，审计出现 DELETE |
| D3 | 报表概览用 `PRAGMA table_info` 探测列，未区分方言 | PG 上聚合失败降级全零 | 按 `db.backend` 分支走 `information_schema` | 概览 200 且非降级 |
| D4 | `attributes_json` 为字符串时 PII 序列化不递归 | **L3/L4 明文绕过掩码**（E2E 实测泄露手机号/身份证） | `pii_serializer` 解析 `*_json` 字符串后按 `attributes.*` 路径掩码；新增单测 | analyst 详情 `138****8000`，身份证剔除 |
| D5 | 画像详情页 `el-radio-button label` 触发 Element Plus 3.0 弃用警告（40+ 条） | UI 关键页零告警门禁失败 | `label` → `value`（ProgressTrend/BusinessItemTable/ScheduleEditor/IngestTasksView） | 3 页 + 任务中心零 error/warn |
| D6 | dps-proxy 导出未调用 `record_export_audit` | 导出无业务留痕（仅 DPS list 读取） | 导出路由补写 `log.export`（actor/filters/row_count/total/truncated），失败降级不阻断 | 真机 10/10 通过，链校验 ok |

另：任务中心 `/portraits/tasks` 静态段需先于 `/portraits/{person_id}` 注册（已在 2.20.1 修复并由本轮 UI 用例验证）。

## 4. 观察项（非缺陷）

| 项 | 说明 |
|---|---|
| 导出审计 | ~~画像 CSV 由 OpenBase 侧生成，DPS `audit_logs` 无 `EXPORT` 记录~~ → **已修复（v1.1.0）**：导出补写 OpenBase `log.export`；DPS 侧仍无 EXPORT 属分工预期 |
| 导出掩码 | 导出列仅基础字段，不含 L3/L4 列，故 CSV 无掩码字符属预期 |
| 调度执行 | worker 未启动（`DPS_SCHEDULER_ENABLED=false`），本轮仅验证调度配置与 Cron 预览，未验证实际触发 |
| 数据范围 | `DPS_DATA_SCOPE_MODE=off`，本轮未做越权矩阵（B 波单测覆盖） |

## 5. 回归

| 项 | 结果 |
|---|---|
| 波次 B + C 单测 | 46 passed（含新增 retry_count 迁移、attributes_json 掩码用例） |
| 波次 A/B/C 全量 | 见提交前回归（A 38 + B 22 + C 24） |
| flake8（变更文件） | 0 error |
| 前端 build | 通过（31.38s） |
| Playwright | 画像关键页 3/3、任务中心 1/1 |
| 导出审计真机验证 | `scripts/verify_export_audit.py` 10/10 PASS（含 request_id 对齐、链校验） |

## 6. 结论与后续

- 三波次能力在**真实全栈 + 真实共享库**下主链路可用；走查发现的 6 项缺陷已修复并复测。
- 发布前仍建议补：worker 实际触发与熔断演练、并发压测、`data_scope=warn` 越权矩阵、导出审计口径确认。
- 共享库已应用 v2.18–v2.20 增量迁移（仅增表/列），合成数据已清理。
