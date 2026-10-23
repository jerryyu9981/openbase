# OpenBase 长尾事项产品裁定（v1.11.0）

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.0.0 |
| 状态 | [Review]（待人工批准；批准后「建设」项进入下一版本排期） |
| 日期 | 2026-10-23 |
| 编制 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-剩余事项统一清查与小版本迭代计划-v1.0.0》v1.5.0 §4 v1.11.0（范围 14 项） |
| 裁定口径 | **建设**＝有明确数据源与验收，进入下一版本；**冻结**＝保留现状不投入（附原因与解冻条件）；**不建设**＝产品不采纳；**已闭环**＝上游已交付，仅台账滞后 |

---

## 1. 结论汇总

| 裁定 | 数量 | 事项 |
|------|:----:|------|
| 已闭环 | 1 | XR-MEM-01 |
| 建设（进入下一版本） | 7 | OB-03、OB-04、XR-LLM-03（报表趋势部分）、XR-LLM-06、XR-DPS-03（只读部分）、XR-DPS-04、XR-DPS-05、XR-GOV-01 |
| 冻结 | 5 | XR-LLM-03（推荐部分）、XR-LLM-04、XR-LLM-05、XR-LLM-08、XR-DPS-02、XR-DPS-03（写部分） |
| 不建设 | 1 | OB-05 |

> 注：XR-LLM-03 与 XR-DPS-03 按子项拆分裁定，故两类合计存在重叠计数。

---

## 2. 本仓事项（OB）

### OB-03 应用调用记录全局聚合 —— 建设

| 项 | 内容 |
|----|------|
| 现状证据 | OpenBase 已有 `GET /api/v1/ai-apps/{app_id}/calls`（`openbase/modules/ai_apps/__init__.py:250`），**无跨应用全局视图**；`ai_app_calls` 表已建模（`core/models/business.py:231`） |
| 裁定 | **建设**（OpenBase 自建，不依赖 OpenLLM） |
| 端点清单 | `GET /api/v1/ai-apps/calls?app_id=&status=&start=&end=&page=&page_size=` → `{items,total,page,page_size}`；权限码复用 `ai_apps:read`（沿用模块既有） |
| 数据模型 | 复用 `ai_app_calls`（app_id / user_id / status / latency_ms / created_at），不新增列 |
| 验收 | 全局分页可筛选；与单应用视图口径一致；单测 ≥4（分页/筛选/空态/越权） |

### OB-04 知识库 API 控制台真实化 —— 建设

| 项 | 内容 |
|----|------|
| 现状证据 | OpenRAG 已有 `POST /retrieve/federated`、`GET /cache/stats`、`GET/PUT /config`（`src/openrag/api/v1_3_routes.py:25,63,137`） |
| 裁定 | **建设**（复用既有端点，OpenRAG 不新增接口） |
| 端点清单 | 前端经 `rag-proxy` 接 `/retrieve/federated`（调试检索）、`/cache/stats`（缓存命中）；如需清缓存走 `DELETE /cache`（写操作需二次确认） |
| 验收 | 控制台展示真实检索结果与耗时；0 mock；错误态覆盖 401/403/503 |

### OB-05 注册 / 找回密码 —— 不建设

| 项 | 内容 |
|----|------|
| 现状证据 | 统一前端仅保留登录；用户由平台管理员开户（`/api/v1/users`） |
| 裁定 | **不建设**：本系统为企业内平台，开户与密码重置由管理员/IT 流程承担；自助注册需邀请码、邮箱验证、风控与 SMTP 通道，当前无对应基础设施，投入产出不成立 |
| 解冻条件 | 若转为 SaaS 多租户自助开通（需邮件服务 + 图形验证 + 防滥用），重新立项 |

### OB-06 文档中心 —— 保留维护（不在本期范围）

无需后端，维持内容型页面现状。

---

## 3. 跨仓事项（OpenLLM / DPS / OpenMemory / OpenRAG）

### XR-LLM-03 模型对比推荐 / 报表趋势 —— 拆分裁定

| 子项 | 现状证据 | 裁定 | 说明 |
|------|----------|------|------|
| 模型对比推荐 | 无推荐端点；无标注/偏好数据 | **冻结** | 推荐需评分样本与算法选型（协同过滤/LLM 打分），当前无数据基础；解冻条件：积累 ≥1 万条调用与人工标注 |
| 报表趋势 | 可复用 `GET /usage/trends`、`GET /monitoring/dashboard`（成本趋势/延迟曲线） | **建设** | 前端新建「报表趋势」页，组合 usage 趋势 + 成本趋势 + 延迟 P50/P95，**不新增端点**；验收：0 mock、三源失败独立降级 |

### XR-LLM-04 成本优化建议「应用」 —— 冻结

| 项 | 内容 |
|----|------|
| 现状证据 | 建议为启发式文本（高成本模型/高错误率/低利用率/高延迟），无「建议 ID」与可执行配置变更（`app/services/monitoring_service.py::get_optimization_suggestions`） |
| 冻结原因 | 「应用」需定义对路由/模型配置的真实变更与回滚，且建议无唯一标识；直接接线会产生不可逆副作用 |
| 解冻条件 | 建议结构化为 `{suggestion_id, action_type, target, before, after}` 并提供幂等执行 + 回滚端点 |

### XR-LLM-05 单条工具调用取消 —— 冻结

| 项 | 内容 |
|----|------|
| 现状证据 | 仅有链级取消 `POST /tool-calls/chains/{chain_id}/cancel`（`app/api/tool_calls.py:237`），无单调用取消 |
| 冻结原因 | 单调用中止需执行器中断协议与幂等审计，且运行中调用多为短时任务；链级取消已覆盖主要场景 |
| 解冻条件 | 引入长任务执行器（可中断）后再评估 |

### XR-LLM-06 工作空间按用户名邀请 —— 建设

| 项 | 内容 |
|----|------|
| 现状证据 | `POST /workspaces/{id}/members` 仅接受 `user_id: UUID`（`app/api/workspaces.py:192-216`） |
| 裁定 | **建设**（OpenLLM 小改动） |
| 端点清单 | 沿用 `POST /workspaces/{workspace_id}/members`，请求体新增可选 `username`；二选一必填 |
| 规则 | `username` 精确匹配 `users.username`；不存在 → 404 `BIZ_NOT_FOUND`；`user_id` 与 `username` 同时给且不一致 → 400 `PARAM_INVALID` |
| 验收 | 用户名邀请成功、重名不存在有明确错误、单测 ≥4 |

### XR-LLM-08 插件与工具清单不一致 —— 冻结（口径说明）

| 项 | 内容 |
|----|------|
| 根因证据 | `GET /plugins` 仅查 DB `plugin` 表（`app/api/plugins.py:49`）；`GET /plugins/tools` 合并**运行时注册表**（`plugin_registry.get_all_tools()`，含内建 `hello-world`）与 DB 插件工具（同文件 74-90 行） |
| 裁定 | **冻结**：非缺陷，是「持久化插件」与「运行时工具」两种口径；不改 OpenLLM 数据结构 |
| 落地 | 前端工具表增加「运行期内建」标签与说明文案（下一版本随页面迭代，无后端改动） |
| 解冻条件 | 若需统一口径，OpenLLM 补 `source=runtime|db` 字段 |

### XR-DPS-02 画像规则引擎端点 —— 冻结

| 项 | 内容 |
|----|------|
| 现状证据 | DPS 仅有告警规则引擎（`AlertRuleEngine`）；`/alerts/rules` 写方法已按 ADR-290-01 收口为 410，迁移目标为平台域 |
| 冻结原因 | 「画像规则引擎」无需求定义与数据模型，且在 DPS 重开写面与既有收口裁定冲突 |
| 落地 | 统一前端移除规则引擎 mock，保留只读告警规则视图（与 XR-DPS-03 只读接线同批） |

### XR-DPS-03 数据权限 / 接口限流 / API 管理 —— 只读建设、写面冻结

| 子项 | 现状证据 | 裁定 |
|------|----------|------|
| 接口限流 | `GET /rate-limits/status`（只读，含 `source` 标注） | **建设（只读接线）** |
| API 管理 | `GET /api-registry`、`GET /error-codes` | **建设（只读接线）** |
| 数据权限 | `POST /permissions/check`（判定）、`GET /permissions/roles`（只读）；角色写面已 410 | **只读建设，写冻结** |
| 验收（只读） | 三页 0 mock、只读可见；写操作不提供入口并标注「治理端点已收口」 |

### XR-DPS-04 DPS 运行态指标端点 —— 建设（排下一版本）

| 项 | 内容 |
|----|------|
| 现状证据 | DPS 无 `GET /metrics`；无 `psutil`/`prometheus_client` 运行依赖；权限资源需注册（`PATH_RESOURCE_MAP` + `PRESET_PERMISSIONS`） |
| 裁定 | **建设**，但须在 DPS 可运行测试环境交付（本机无 venv/runner，无法出具真实回归） |
| 端点清单 | `GET /api/v2/metrics` → `{qps_1m, cpu_percent, memory_mb, memory_percent, uptime_seconds, requests_total, collected_at}`；QPS 取 60s 滑动窗口 |
| 依赖与注册 | 新增权限资源 `runtime_metric`（`runtime_metric:read`）；`PATH_RESOURCE_MAP["metrics"]="runtime_metric"`；`PRESET_PERMISSIONS` 注册 + 类级守门用例同步 |
| 验收 | 端点 200、`super_admin` 200 / 无权限 403 / 匿名 401；DPS 全量回归不劣于基线 |

### XR-DPS-05 OpenBase 代理扩权 + 画像监控页接线 —— 建设

| 项 | 内容 |
|----|------|
| 现状证据 | `dps-proxy` 仅映射 `/api/v2/portrait/*`（`openbase/modules/dps_proxy/__init__.py:24`） |
| 裁定 | **建设**（依赖 XR-DPS-04） |
| 端点清单 | 代理允许清单新增只读：`GET /api/v2/metrics`、`GET /api/v2/rate-limits/status`、`GET /api/v2/alerts/rules`；禁止透传写方法 |
| 验收 | 画像监控页 0 mock；指标 + 规则只读可见；写入口不提供；代理单测 ≥4 |

### XR-GOV-01 C1-d 码值双形态（三仓） —— 建设（派单）

| 项 | 内容 |
|----|------|
| 现状证据 | OpenBase 已有 `openbase/core/code_normalize.py`（纯函数 + 11 例）；OpenLLM / OpenRAG / OpenMemory 全仓检索 `code_normalize` **零命中** |
| 裁定 | **建设**：按 OpenLLM → OpenRAG → OpenMemory 顺序派单，各仓复制纯函数并接入租户解析入口，禁止跨仓包依赖 |
| 验收 | 三仓回执 + 各自单测（码→UUID / UUID 规范化 / 不存在 fail-closed）+ 回归 |

### XR-MEM-01 OpenMemory `default` 兜底退役 —— 已闭环（台账滞后）

| 项 | 内容 |
|----|------|
| 证据 | OpenMemory 未决项 9 P1~P4 已交付（2026-10-12，`68701e9`+`26dc728`）：P4 以空策略矩阵 fail-closed 启动，不再自动创建 `{"default":{"enabled":true}}`；`OpenMemory-未决项9-…-DevLogReport-v1.0.0.md` §4.4；全量 1366 passed |
| 裁定 | **已闭环**，台账更新状态即可，无需再排期 |

---

## 4. 下一版本建议范围（v1.12.0）

| 批次 | 事项 | 依赖 |
|------|------|------|
| A（本仓，低风险） | OB-03 全局调用聚合、OB-04 知识库控制台接线、XR-LLM-03 报表趋势页、XR-DPS-05 代理扩权（待 04） | 无 |
| B（跨仓小改） | XR-LLM-06 用户名邀请 | OpenLLM 派单 |
| C（跨仓交付） | XR-DPS-04 指标端点（含权限点注册）→ XR-DPS-05 接线 | DPS 可运行测试环境 |
| D（跨仓派单） | XR-GOV-01 三仓码值规范化 | 三仓回执 |
| E（前端文案） | XR-LLM-08「运行期内建」标注、XR-DPS-02/03 只读视图 | 无 |

---

## 5. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-10-23 | 研发（AI 辅助） | 初始创建：14 项逐条裁定（建设 7 / 冻结 5 / 不建设 1 / 已闭环 1，含 2 项子项拆分），附端点清单、数据模型、解冻条件与下一版本分批建议 |
