# 波次 B（2.19.0）验收清单

| 项 | 内容 |
|---|---|
| 文档编号 | OB-CHECKLIST-PORTRAIT-WAVE-B |
| 版本 | v1.0.0 |
| 状态 | [Approved] |
| 关联规格 | [spec.md](./spec.md) v1.0.0 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制并完成逐项核验 | AI 编码代理 |

## 功能门禁

- [x] 组织树可查询（`GET /orgs/tree`），历史组织路径可回填（`scripts/backfill_org_tree.py`，默认 dry-run）
- [x] 成员一人多岗、主岗唯一（`org_member`，`PUT /orgs/{code}/members`）
- [x] 数据范围四种口径可用；`enforce` 缺定位信息返回空集；`off` 不附加条件
- [x] 查询统计缓存键纳入范围指纹，避免跨范围串读
- [x] 引入预览脱敏、执行真实 upsert、重复执行幂等、错误行可定位
- [x] 引入成功后按模板生成 `pending` 标注，不自动通过；重复执行不重复生成
- [x] 前端引入任务中心三 Tab、详情、错误 CSV（脱敏）、重试

## 安全门禁

- [x] PII 默认 `enforce`：L3 掩码、L4 剔除
- [x] `dps:pii:view` 见 L3 明文，`dps:pii:high` 见 L4；无权限返回掩码
- [x] 画像列表/详情/标注队列读路径接入统一序列化
- [x] 错误行落库强制脱敏，错误 CSV 无明文
- [x] 日志不记录字段值；数据范围 WARN 只记 scope/org_code
- [x] 新增表/读写带 `tenant_id` 谓词

## 兼容与回滚门禁

- [x] `DPS_DATA_SCOPE_MODE=off` 时行为与 2.18.x 一致
- [x] `DPS_INGEST_PERSIST_ENABLED=false` 时 `BatchEngine` 保持模拟路径
- [x] `DPS_PII_MODE=warn` 为回滚入口（只留痕不改响应）
- [x] DDL 只增不删，迁移连续执行两次幂等
- [x] 回滚顺序：数据范围 off → PII warn → 引入持久化 false，不做 DDL 回退

## 质量与留痕门禁

- [x] `python -m pytest src/tests/test_v2_19_wave_b.py -q --no-cov`：21 passed
- [x] 回归 `test_v2_18_wave_a.py`：38 passed
- [x] 回归 `test_portrait_list_route.py`：2 passed
- [x] 回归 `test_tenant_isolation.py` + `test_batch_async.py`：29 passed / 1 skipped
- [x] 变更文件 `flake8 --max-line-length=120 --extend-ignore=E203,W503`：0 error
- [x] `openbase-ui npm run build`：通过
- [x] OpenBase 代理测试 `tests/test_dps_proxy_wave_b.py`：通过
- [x] 版本升 2.19.0（`config.py` / `src/__init__.py` / `mcp_server/constants.py`）
- [x] DevLogReport v1.0.0 与实施计划 v1.0.3 留痕
- [x] 两仓提交并推送 origin/backup/github（DPS `217d0f1`、OpenBase `a777f16`）
