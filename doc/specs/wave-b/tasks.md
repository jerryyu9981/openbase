# 波次 B（2.19.0）任务清单

| 项 | 内容 |
|---|---|
| 文档编号 | OB-TASKS-PORTRAIT-WAVE-B |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 规格 | [spec.md](./spec.md) v1.0.0 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制：B-01~B-11 可执行任务与验证 | AI 编码代理 |

## 执行顺序

> 原则：DDL/开关先行 → 组织与范围 → PII → 引入落库 → 代理/前端 → 测试 → 留痕推送。

| ID | 任务 | 主要文件 | 验证 |
|---|---|---|---|
| [x] B-00 | 提取迁移公共工具 | `src/ddl/upgrade_utils.py`；改 `schema_v2_18_upgrade.py` | v2.18 测试通过 |
| [x] B-01 | v2.19 增量 DDL | `src/ddl/schema_v2_19_upgrade.py`；`src/database.py` | 连续执行两次幂等 |
| [x] B-01b | 组织树回填脚本 | `scripts/backfill_org_tree.py` | dry-run/apply 摘要 |
| [x] B-02 | 组织引擎 | `src/engines/org_engine.py` | 树/成员/主岗单测 |
| [x] B-02b | `/orgs/*` 路由 | `src/rest_api/routes/routes_orgs.py`；路由注册 | 路由 200 + 参数 400 |
| [x] B-03 | 数据范围引擎 | `src/security/data_scope.py` | 四范围谓词单测 |
| [x] B-03b | 查询接入 | `src/engines/query_engine.py` | 范围过滤 + 缓存键 |
| [x] B-04 | 中间件接入 | `src/middleware/permission_middleware.py` | 上下文设置/清理 |
| [x] B-05a | PII 默认 enforce + 权限位 | `src/config.py`；`pii_serializer.py`；`permission_engine.py` | 掩码/明文单测 |
| [x] B-05b | 读路径接入 | `src/rest_api/routes/routes_profiles.py` | 列表/详情/标注脱敏 |
| [x] B-06 | 引入引擎 | `src/engines/ingest_engine.py` | 预览/执行/幂等/错误行 |
| [x] B-07 | 批量与数据源落库 | `src/engines/batch_engine.py`；`datasource_engine.py` | 开关开/关行为 |
| [x] B-08 | 标注自动生成 | `ingest_engine.generate_annotation_tasks` | pending + 幂等 |
| [x] B-06b | `/ingest/*` 路由 | `src/rest_api/routes/routes_ingest.py`；路由注册 | 路由 200/404 |
| [x] B-09 | OpenBase 代理 | `openbase/modules/dps_proxy/__init__.py` | 代理单测 |
| [x] B-10 | 引入前端 | `IngestTasksView.vue`、`TaskDetailView.vue`、`MappingTable.vue` | build 通过 |
| [x] B-10b | 权限与掩码前端 | `OrgTreeSelect.vue`、`PiiMaskedField.vue`、`PortraitList.vue` | build 通过 |
| [x] B-10c | API 与路由注册 | `core/api/dps.ts`、`modules/portrait/index.ts` | 类型编译 |
| [x] B-11 | 测试与回归 | `src/tests/test_v2_19_wave_b.py` 等 | pytest/ruff/flake8 |
| [x] B-12 | 版本与留痕 | `config.py`、`__init__.py`、`constants.py`；DevLogReport；计划 v1.0.3 | 一致性检查 |
| [x] B-13 | 提交与推送 | DPS `217d0f1`、OpenBase `a777f16` | origin/backup/github 均成功 |

## 门禁

1. `python -m pytest src/tests/test_v2_19_wave_b.py -q --no-cov` 全绿。
2. 回归：`test_v2_18_wave_a.py`、`test_portrait_list_route.py`、`test_tenant_isolation.py`、`test_batch_async.py` 全绿。
3. `python -m ruff check src` 与 `flake8 src --max-line-length=120 --extend-ignore=E203,W503` 0 错误。
4. `openbase-ui` `npm run build` 通过；OpenBase 代理测试通过。
5. 两仓提交并推送 origin/backup/github 三远程。

## 风险与处置

| 风险 | 处置 |
|---|---|
| PII 默认 enforce 影响既有断言 | 仅有 PII 断言的用例才允许调整为显式权限/开关；其它失败按缺陷修复 |
| SQLite `ALTER TABLE` 限制 | 统一走 `ensure_column` 探测 |
| 组织数据缺失 | 回填脚本 + 越权空集（不报错） |
| 重复导入 | `(person_id, tenant_id)` upsert + 任务状态幂等 |
| 标注重复生成 | `ingest_batch_id + profile_id` 存在性检查 |
