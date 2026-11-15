# OpenBase 画像模板可视化 DevLogReport

- 版本：v1.0.0
- 状态：[Approved]
- 适用环境：Dev / Test / Pro
- 作者：AI 编码代理
- 日期：2026-11-15
- 关联设计：[OpenBase-画像模板与标注模板可视化设计 v1.2.0](../design/OpenBase-画像模板与标注模板可视化设计-v1.0.0.md)

## 修订历史

| 版本 | 日期 | 变更摘要 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-15 | 首版：P0 可视化模板工作台 + P1 校验/试算接口与 `when` 求值交付记录 | AI 编码代理 |

---

## 1. 交付范围

按设计 §10 交付 **P0 + P1**：

- P0：画像模板可视化工作台（6 段模板项 + 6 类评分规则 + 条件组构建器），写回契约不变；
- P1：DPS 只读接口 `meta/schema`、`templates/{code}/validate`、`templates/{code}/preview`，试运行抽屉，以及打分前 `when` 条件求值；
- 画像 360 视图按决策留待后续期。

## 2. 变更清单

### 2.1 前端（openbase-ui）

| 文件 | 说明 |
|---|---|
| `src/modules/portrait/templates/model.ts` | 草稿模型、`toDraft/fromDraft`（未知键透传）、前端校验、条件表达式预览、规则/维度工厂 |
| `src/modules/portrait/templates/ConditionGroupBuilder.vue` | AND/OR 嵌套条件组（≤3 层）、算子按操作类型动态呈现、只读表达式 |
| `src/modules/portrait/templates/RuleCardForm.vue` | 6 类规则表单（mapping/boolean/interval/ratio）、`when` 开关、只读 JSON |
| `src/modules/portrait/templates/DimensionEditor.vue` | 维度 code/名称/权重 + 规则列表（增删复制） |
| `src/modules/portrait/templates/AttributeFieldTable.vue` | `attributes_schema` 分组 → 字段 key 维护与跨组重复提示 |
| `src/modules/portrait/templates/TagBindingTable.vue` | 标注模板 → 维度绑定，冲突提示，扩展键保留 |
| `src/modules/portrait/templates/EvidencePolicyForm.vue` | 证据策略表单 + 证据示例卡 + 未识别键提示 |
| `src/modules/portrait/templates/AnomalyRuleList.vue` | 异常规则（条件/动作/级别）+ 3 个内置模板 |
| `src/modules/portrait/templates/DryRunDrawer.vue` | 样例生成/编辑、逐规则状态表、维度与总分 |
| `src/modules/portrait/pages/DpsTemplateWorkbenchView.vue` | 工作台页面：左侧分区导航、问题清单定位、权重合计、服务端校验、保存、JSON 视图、未保存拦截 |
| `src/modules/portrait/index.ts` | 新增 `new`/`edit`（工作台）与 `raw`（原 JSON 编辑器）路由 |
| `src/modules/portrait/pages/DpsTemplateListView.vue` | 列表新增「工作台」入口，详情抽屉区分「工作台 / JSON 编辑」 |
| `src/core/api/dps.ts` | 新增元数据/校验/试算接口封装与类型 |

### 2.2 后端（DPS）

| 文件 | 说明 |
|---|---|
| `src/engines/portrait/conditions.py` | 18 个条件算子、`all/any` 嵌套求值（超深/非法算子报错，缺字段 fail-closed）、`should_apply`、结构校验 |
| `src/engines/portrait/template_preview.py` | `META_SCHEMA`、字段级校验（`{path, code, message, severity}`）、样例试算（`scored/missing/skipped/error` + 维度加权） |
| `src/engines/portrait/core.py` | 打分前 `_rule_applies`：`when` 不成立跳过规则；无 `when` 行为不变 |
| `src/rest_api/routes/routes_profiles.py` | 三个只读接口（置于 `/portrait/{person_id}` 之前）；顺带修复既有 `List` 未导入（F821） |
| `src/tests/test_template_preview_v2_12.py` | 18 个用例：条件组、校验、试算四态、加权归一、旧模板回归、元数据 |

### 2.3 OpenBase 代理层

| 文件 | 说明 |
|---|---|
| `openbase/modules/dps_proxy/__init__.py` | 新增 `/meta/schema`、`/templates/{code}/validate`、`/templates/{code}/preview` 转发（JWT + 身份头） |

## 3. 接口契约（新增，只读）

| 方法 | 代理路径 | DPS 路径 | 说明 |
|---|---|---|---|
| GET | `/api/v1/dps-proxy/meta/schema` | `/api/v2/portrait/meta/schema` | 字段类型、18 算子、6 类规则参数模式、权重容差 |
| POST | `/api/v1/dps-proxy/templates/{code}/validate` | `/api/v2/portrait/templates/{code}/validate` | 入参 `{template?}`；返回 `{valid, errors[], weight_sum}`，失败仍 200 |
| POST | `/api/v1/dps-proxy/templates/{code}/preview` | `/api/v2/portrait/templates/{code}/preview` | 入参 `{template?, sample}`；返回逐规则状态、维度得分、总分、耗时 |

试算状态语义：

| 状态 | 含义 | 是否计入维度加权 |
|---|---|---|
| `scored` | 样例值评分成功 | 是 |
| `missing` | 样例缺该 key，按 50 分 | 是 |
| `skipped` | `when` 条件不成立 | 否 |
| `error` | 取值/类型错误（附原因） | 否 |

## 4. 验证证据

| 验证项 | 命令/方式 | 结果 |
|---|---|---|
| DPS 单测（新增） | `python -m pytest src/tests/test_template_preview_v2_12.py -q --no-cov` | 18 passed |
| DPS 回归 | preview + preflight + scoring 三文件 | 59 passed |
| DPS 静态检查 | `ruff check` 新增文件 | All checks passed |
| 前端类型 | `vue-tsc --noEmit` | 0 错误 |
| 前端规范 | `eslint`（新增/改动文件） | 0 错误 0 警告 |
| 接口联调 | 代理层 `meta/validate/preview` | 6 类规则/18 算子；存量模板 valid=true；示例总分 49.7 |
| 浏览器走查 | 工作台 `/portrait/dps/templates/cor-persona-root-v1/edit` | 6 分区、权重 1.00、问题清单、试运行总分 61.45（32 条全 scored） |
| 新建闭环 | 工作台 `/portrait/dps/templates/new` | `wb-smoke-v1` 保存成功（v1），刷新后维度/规则持久 |

> 说明：`wb-smoke-v1` 为走查产生的草稿模板（status=draft），仅存在于 Dev 库，不影响激活模板列表。

## 5. 兼容性与风险

- **兼容**：写回仍是既有 JSONB 键位，未新增数据库列；未识别键深拷贝透传；旧模板无 `when` 打分行为不变（有回归用例对照 `ScoringDispatcher`）。
- **降级**：服务端接口不可用时，前端仍有本地即时校验；试运行抽屉报错不影响编辑与保存。
- **已知边界**：维度级条件、画像 360 视图、标注模板设计器增强（字段分组联动）留待后续期；权重合计 ≠ 1.00 仅提示不阻断。

## 6. 回滚

- 前端：将 `new`/`edit` 路由指回 `DpsTemplateEditView` 即可（`/raw` 已保留）；新增组件无副作用。
- 后端：三个接口只读，下线路由即可；`when` 求值对无 `when` 规则零影响。
