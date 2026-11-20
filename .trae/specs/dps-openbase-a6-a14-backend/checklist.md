# Checklist：DPS 降级项后端能力补齐（A6/A9/A10/A11/A12/A14）

## 需求与设计

- [x] 两仓需求文档、追溯矩阵、评审记录均为 [Approved] v2.0.0
- [x] 两仓设计文档 [Approved]，覆盖 A6/A9/A10/A11/A12/A14 契约与降级口径
- [x] 版本号冻结：DPS 2.14.0；OpenBase 后端/前端 1.5.0

## DPS 实现（A6/A9/A10/A12）

- [x] `GET /api/v2/portrait/list` 支持 `keyword` 与 `external_id`，无参行为与 v2.13.0 一致
- [x] `GET /api/v2/tags` 返回扁平标签值并带分类元数据，支持关键字/分类/分页，`page_size>100` 返回 422
- [x] `GET /api/v2/audit` 按实体返回时间线，支持 `order=asc|desc`，未知实体 200 空集合
- [x] `GET /api/v2/audit/logs` 新增 `resource_id` 且旧参数不变
- [x] 口径报告每条 issue 含非空 `suggestion` 与 `fix_target`，7 类问题码全覆盖
- [x] 新增定向用例 `src/tests/test_v2_14_requirements.py`（6 例）全部通过
- [x] DPS 全量回归无本任务新增失败（唯一失败为既有用例自命中）

## OpenBase 后端实现（A11/A14）

- [x] `/dps-proxy/portraits` 转发 `keyword`/`external_id`，上游状态码与包络保真
- [x] 新增 `/dps-proxy/tags`、`/dps-proxy/audit`；`/audit/logs` 转发 `resource_id`
- [x] `annotations/export`、`portraits/export` 为流式 CSV，含 UTF-8 BOM、RFC4180 转义、注入前缀、10000 行截断与 `X-Export-Truncated`
- [x] 候选表 `dps_annotation_candidate` 幂等建表，唯一键 `(tenant_id, upstream_annotation_id)`
- [x] 候选 3 个端点（生成/按批次/最近批次）按租户隔离且幂等
- [x] 新增后端用例 `tests/test_dps_backend_capabilities_v150.py`（19 例）全部通过

## OpenBase 前端实现

- [x] `core/api/dps.ts` 新增代理与导出、候选 API 封装（含 8 方法、3 类型）
- [x] AI 候选页改持久化接口，刷新后按 `/latest` 恢复
- [x] 画像列表/搜索/措施主体、标签体系、审核时间线接入服务端检索
- [x] 导出按钮改调后端 CSV
- [x] 仅上游 404 时回退本地降级；403/5xx 呈现受控错误态

## 测试与部署

- [x] 后端定向、ruff、`vue-tsc`、`npm run build` 均通过
- [x] 前端相关 spec 全部通过（含 `dps-backend-v150` 6 例）
- [x] 产出两仓测试报告并登记基线/环境类残余失败
- [x] 产出两仓部署与运维报告
- [x] 提交并推送两仓 `main` 三远程（T1.3 统一留痕）
