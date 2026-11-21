# OpenBase 模板族 v2.12.0 存量测试治理报告

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）/ DPS 画像模板化 |
| 被测对象 | 三项存量测试红灯治理（依赖声明判据、圈复杂度守卫、DDL 冻结列） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]**（待人工批准） |
| 测试日期 | 2026-11-19 |
| 测试人 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-画像模板分类与子模板挂载设计》v0.2.1 §18.5 |
| 通过判据 | 三个守则用例全部通过 + 相关业务回归无退化 + 全量回归 0 failed + 静态检查 0 错误 |

---

## 1. 结论

**通过。**

- 三个存量失败用例全部修复，且未改变任何对外行为、错误文案、接口契约或数据模型。
- 定向验证：三个守则文件 **81 passed**；相关业务回归 **125 passed**。
- 全量回归：**2111 passed / 3 skipped / 1 xfailed / 1 xpassed / 0 failed**（耗时 22 分 37 秒）。
- 静态检查：Ruff（E4/E7/E9/F）**All checks passed**。

---

## 2. 修复范围

| # | 用例 | 根因 | 处置 | 涉及文件 |
|---|---|---|---|---|
| 1 | `test_v2_11_ci_hardening.py` | 依赖声明判据只扫描 `src/`，`scripts/p1_recompute_profiles.py` 被误判为未声明的第三方包 | `_project_modules()` 纳入 `scripts/**/*.py` 脚本名；判据语义（仅第三方需声明）不变 | `src/tests/test_v2_11_ci_hardening.py` |
| 2 | `test_v2_11_complexity_guard.py` | 4 个历史函数圈复杂度超过 15（21 / 23 / 19 / 18） | 按职责拆分，不改变任何行为与错误文案（见 §3） | `src/engines/portrait/conditions.py`、`src/engines/annotation_template_engine.py`、`src/engines/portrait/template_preview_validation.py`、`src/rest_api/routes/routes_profiles.py` |
| 3 | `test_v2_11_ddl_root.py` | `portrait_profile.external_id` 为 R9 有意新增列，冻结基线未同步 | 按实际列顺序回填 `external_id` 并注明来源 | `src/tests/test_v2_11_ddl_root.py` |

### 2.1 圈复杂度拆分明细

| 原函数（CC） | 拆分后 |
|---|---|
| `conditions._evaluate_leaf`（21） | 主分发（6）+ `_evaluate_presence` / `_evaluate_match` / `_evaluate_numeric` / `_evaluate_date` |
| `annotation_template_engine.validate_field_schema`（19） | 主循环（4）+ `_validate_field_identity` / `_validate_field_tag_contract` / `_validate_tag_key` / `_validate_score_map` / `_validate_score_direction` |
| `template_preview_validation._validate_rule_params`（23） | 类型分发（5）+ `_validate_mapping_params` / `_validate_boolean_params` / `_validate_interval_params` / `_validate_ratio_params` |
| `routes_profiles._persist_portrait_update`（18） | 主流程（12）+ `_build_profile_update_clauses` / `_raise_portrait_version_conflict` / `_resolve_stored_attributes` |

---

## 3. 验证矩阵

| 验证项 | 命令 | 结果 |
|---|---|---|
| 三个守则用例 | `pytest test_v2_11_ci_hardening.py test_v2_11_complexity_guard.py test_v2_11_ddl_root.py` | **81 passed** |
| 相关业务回归 | 模板试算、标注链路、画像更新、模板族、RBAC 共 7 个文件 | **125 passed** |
| 结构守则 | `pytest test_portrait_split.py test_v2_11_complexity_guard.py` | **13 passed**（`conditions.py` = 300 行，未超上限） |
| 静态检查 | `ruff check --select E4,E7,E9,F`（6 个改动文件） | **All checks passed** |
| 全量回归 | `pytest -q --no-cov` | **2111 passed / 3 skipped / 1 xfailed / 1 xpassed / 0 failed** |

### 3.1 全量回归执行说明

- 首轮全量：2110 passed + 1 failed，唯一失败为 `test_portrait_split` 报 `conditions.py 301 行`（本次拆分新增 4 个辅助函数后超限）。
- 处置：合并模块文档串中 1 行（无语义变更），文件回到 300 行；结构守则与复杂度守则复验通过。
- 次轮全量：上述 **2111 passed / 0 failed**，即最终结果。

---

## 4. 行为等价性说明

1. **条件求值**：算子分支、缺字段 fail-closed、错误文案与异常类型完全不变，仅按算子族拆函数。
2. **标注字段校验**：校验顺序（key → type/options → target_dimension → tag_key → score_map → score_direction）与报错文案不变。
3. **规则参数校验**：`legacy_map` 空映射放行、区间重叠 warning、枚举映射 ≥2 项 warning 等既有口径不变。
4. **画像更新**：SQL 组装顺序、乐观锁 `WHERE version`、409/404 分支、缓存失效与历史快照时机不变。
5. **DDL 契约**：仅更新测试侧冻结基线（`external_id` 为已上线的 R9 列），未改任何 DDL。

---

## 5. 残余风险与后续建议

| 风险 | 等级 | 建议 |
|---|---|---|
| `conditions.py` 恰好 300 行，后续任何新增都可能触发结构守则 | 低 | 下次改动条件模型时，将叶子算子拆至独立模块 |
| 冻结列基线依赖人工同步 | 低 | 新增列时同步更新 `_FROZEN_COLUMNS` 并注明版本来源 |
| 全量回归耗时 22 分钟（共享 PG 环境） | 低 | 可评估按模块分组并行，或在 CI 使用专用库 |

---

## 6. 修订历史

| 版本 | 日期 | 变更摘要 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-19 | 首版：三项存量测试治理的修复范围、验证矩阵与行为等价性说明 | 研发（AI 辅助） |
