# OpenBase P2 模板—标注—评分可解释性 Spec

## 文档元信息

| 项 | 内容 |
|---|---|
| 文档版本 | v1.0.1 |
| 状态 | [Implemented]（评审批准，P2 已实施并验证） |
| 适用环境 | Dev（OpenBase 8000 + DPS 8030 + 前端 5173，PostgreSQL 主库） |
| 作者 | AI 编码代理 |
| 评审人 | 需求方 / 技术负责人 |
| 创建日期 | 2026-11-17 |
| 上游依据 | 《OpenBase-画像模板-标注模板-评分项对应关系与治理方案》v1.1.1 §7 阶段三（P2） |

### 修订历史

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-17 | 首版：P2「前端可解释性」四项的接口、前端、测试与验证设计 | AI 编码代理 |
| v1.0.1 | 2026-11-17 | 评审批准并实施完成：AC-01~AC-07 全部通过，状态转 [Implemented] | AI 编码代理 |

---

## 1. 背景与目标

治理方案 §7 阶段三要求前端可解释性落地四项：

1. 模板详情页改为「族谱 / 标注模板 / 标签产出 / 评分项」四联视图；
2. 标注工作台字段旁标注「将写入 `dimension:tag_key`、计分规则、影响哪个评分项」；
3. 画像详情维度展开显示：本维度参与评分的标签、实际得分、缺值兜底；
4. 未绑定标注模板、未覆盖维度以警示标签呈现。

**验收口径**：用户可从模板配置一路下钻到某条评分项及其标签来源，无需读代码；关键缺口页面可见。

P0/P1 已完成（模板规则参与真实计算、`profile_tag` 来源隔离与读侧择优、评分项接口含维度标注来源与缺口）。P2 只做**只读解释性接口 + 前端呈现**，不改变评分算法与写路径。

---

## 2. 现状事实（已核对代码）

### 2.1 DPS 侧可复用能力

| 能力 | 位置 | 说明 |
|---|---|---|
| 模板继承解析 | `src/engines/portrait/template_registry.py` `TemplateRegistry.resolve_dimensions` | 返回 `{dim: {name, weight, rules:{key: rule}}}`；仅加载 active 模板 |
| 评分项字典 | `src/rest_api/routes/routes_profiles.py` `api_get_template_scoring_items` | 已含 `annotation_sources` / `source_gap` / `dimensions_without_annotation_source` |
| 标注来源索引 | `src/engines/p1_governance.py` `dimension_source_index` / `dimension_codes` | 维度 → 产出标签的标注模板集合 |
| 标签产出规则 | `src/engines/annotation_template_engine.py` `build_tag_sync_entries` | `tag_code = <target_dimension>:<tag_key>`，`tag_key` 缺省取 `field.key` |
| 单维度评分明细 | `src/engines/portrait/core.py` `PortraitEngine.calculate_dimension_score` | 返回 `DimensionResult.tags = {tag_code: {value, score, weight, description}}`；缺值 `value="N/A"`、`score=50` |
| 模板读取 | `src/engines/template_engine.py` `TemplateEngine.list_templates` / `get_template` | 含 draft/inactive，可构造族谱 |

**关键结构差异（必须转换）**：`resolve_dimensions()` 输出键为 `rules`，而 `calculate_dimension_score()` 读取 `active_rules[dim]["tags"]`，调用前需 `{dim: {"tags": item["rules"], "description": item["name"]}}` 转换（与既有 calculate 路由一致）。

### 2.2 OpenBase 侧

- 代理层 `openbase/modules/dps_proxy/__init__.py` 已有逐端点声明模式（如 `dps_template_scoring_items`），上游前缀 `/api/v2/portrait`。
- 前端 API 封装 `openbase-ui/src/core/api/dps.ts` 已有 `getTemplateScoringItems`。
- 页面：`DpsTemplateListView.vue`（详情抽屉）、`DpsAnnotationWorkbenchView.vue`（字段渲染）、`PortraitDetail.vue`（维度卡片与评分项弹窗）。

### 2.3 现存测试约束

`tests/test_dps_proxy_routes_v1410.py` 的 22 条计数使用 `V1410_ROUTES` 精确 `(path, method)` 配对集合计数，新增路径不计入，**不需要改该断言**；仅需新增本版路由注册断言。

---

## 3. 方案设计

### 3.1 DPS 新增 3 个只读接口（分层：route 仅校验 + 调用 engine）

#### A. `GET /api/v2/portrait/templates/{code}/lineage`

模板四联视图数据源。响应 `data`：

```json
{
  "template_code": "cor-persona-root-v1",
  "name": "社区矫正对象全景画像基础模板",
  "status": "active",
  "version": "v1",
  "lineage": [
    {"code": "cor-persona-root-v1", "name": "...", "status": "active", "depth": 0, "current": true}
  ],
  "bindings": [
    {"annotation_template": "cor-anno-basic-v1", "dimensions": ["basic", "social"],
     "exists": true, "status": "active", "owned_by": "cor-persona-intake-v1",
     "ownership_mismatch": true}
  ],
  "annotation_templates": [
    {"code": "cor-anno-basic-v1", "name": "...", "status": "active",
     "owned_by": "cor-persona-intake-v1", "bound_to_current": true,
     "bound_dimensions": ["basic"],
     "fields": [{"key": "age_stage", "label": "年龄段", "type": "enum",
                 "target_dimension": "basic", "tag_key": "age_stage",
                 "tag_code": "basic:age_stage", "score_map": {"少年": 100},
                 "score_direction": "higher_better"}],
     "tag_outputs": [{"tag_code": "basic:age_stage", "field_key": "age_stage", "tag_key": "age_stage"}],
     "scoring_hits": [{"tag_code": "basic:age_stage", "dimension": "basic",
                       "rule_key": "basic:age_stage", "weight": 0.1, "description": "年龄段"}],
     "unmatched_tag_outputs": ["basic:age_stage"]}
  ],
  "scoring": { "与 scoring-items 同构": "..." },
  "gaps": {
    "dimensions_without_annotation_source": ["social", "crime"],
    "unbound_annotation_templates": ["cor-anno-category-v1"],
    "bound_annotation_templates_missing": [],
    "ownership_mismatches": [{"annotation_template": "cor-anno-basic-v1",
                              "owned_by": "cor-persona-intake-v1",
                              "bound_by": "cor-persona-root-v1"}],
    "tag_outputs_without_scoring_rule": ["basic:age_stage"],
    "items": [{"type": "dimension_without_annotation_source", "severity": "warning",
               "code": "social", "message": "维度 social 无标注来源"}]
  }
}
```

规则：

- `lineage` 由 `TemplateEngine.list_templates()` 全量构造（含 draft/inactive），沿 `extends` 上溯，深度护栏 3；父缺失时停止并在 `gaps.items` 记 `extends_missing`。
- `scoring` 仅在模板 active（registry 可解析）时返回，否则 `null`，并追加 gap item `template_not_active`（"模板未激活，无运行时评分口径"）。
- `ownership_mismatch`：绑定的标注模板 `template_code` ≠ 当前模板 code。
- `unmatched_tag_outputs`：标签产出在 `scoring` 中无同名规则（`tag_code` 或去前缀 key 均不命中）→ 说明只写标签不影响分数。
- `annotation_templates` 包含「被当前模板绑定」与「归属当前模板」两类并集，外加全部未绑定模板（供第四联与缺口警示）。

#### B. `GET /api/v2/portrait/annotation-templates/{code}/field-mapping?portrait_template=<code>`

标注工作台逐字段提示。`portrait_template` 缺省取标注模板 `template_code`（强归属）。响应 `data`：

```json
{
  "annotation_template": "cor-anno-psych-v1",
  "owned_by": "cor-persona-assess-v1",
  "portrait_template": "cor-persona-assess-v1",
  "portrait_template_status": "active",
  "fields": [
    {"key": "crisis_level", "label": "危机等级", "type": "enum",
     "target_dimension": "psychology", "tag_key": "crisis_level",
     "tag_code": "psychology:crisis_level",
     "score_rule": {"type": "score_map", "score_direction": "higher_better",
                    "score_map": {"正常": 100, "关注": 66.67, "干预": 33.33, "紧急": 0},
                    "summary": "紧急→0 · 干预→33.33 · 关注→66.67 · 正常→100"},
     "affects_scoring": [{"dimension": "psychology", "rule_key": "psychology:crisis_level",
                          "weight": 0.25, "description": "危机等级"}],
     "scoring_status": "affects", "missing_fallback": 50.0}
  ],
  "summary": {"field_count": 22, "affects_scoring": 3, "tag_only": 2, "no_tag": 17}
}
```

`scoring_status` 枚举：`affects`（产出标签且命中评分项）/ `tag_only`（产出标签但无同名评分项）/ `no_tag`（无 `target_dimension`）。

#### C. `GET /api/v2/portrait/{person_id}/dimension-details?template_code=<code>`

画像详情维度展开。`template_code` 缺省 = 默认口径（代码常量 6 维 23 项）。响应 `data`：

```json
{
  "person_id": "tenant-1_1",
  "template_code": "cor-persona-risk-v1",
  "source": "template",
  "overall_score": 68.4,
  "missing_policy": {"score": 50.0, "note": "缺值按 50 分计入，权重照计"},
  "dimensions": [
    {"code": "basic", "name": "基础信息", "weight": 0.15, "score": 72.5,
     "confidence": 0.67, "level": "良好", "rule_count": 3,
     "present_count": 2, "missing_count": 1,
     "rules": [{"key": "basic:info_completeness", "tag_key": "info_completeness",
                "description": "信息完整度", "weight": 0.4, "score": 100.0,
                "value": "完整", "missing": false, "scoring_type": "score_map"}]}
  ]
}
```

- `missing=true` ⇔ `DimensionResult.tags[rule]["value"] == "N/A"`。
- 维度不存在于模板 → 400 PARAM（`detail: 模板无该维度`）；画像不存在 → 404。
- 每维度读一次 `profile_tag`（复用 `calculate_dimension_score`），不写库。

### 3.2 DPS 新引擎模块 `src/engines/p2_explainability.py`

纯函数（可单测）+ 异步装配函数：

| 函数 | 职责 |
|---|---|
| `build_lineage_chain(code, templates)` | 沿 `extends` 上溯构造族谱列表（含缺失/成环护栏） |
| `field_tag_contract(field)` | 归一字段契约：`tag_key`（缺省 key）、`tag_code`、`score_map`、`score_direction`、`score_rule.summary` |
| `resolve_scoring_hits(tag_code, resolved)` | 在解析维度中按 `tag_code` / 去前缀 key 命中规则，返回 `[{dimension, rule_key, weight, description}]` |
| `build_field_mappings(field_schema, resolved)` | 全字段映射 + 汇总统计 |
| `build_annotation_views(annotations, bindings, resolved, current_code)` | 标注模板视图（含 `tag_outputs` / `scoring_hits` / `unmatched_tag_outputs`） |
| `build_gap_items(...)` | 缺口清单（维度无标注来源 / 未绑定模板 / 绑定缺失 / 归属错位 / 标签无评分规则 / 模板未激活 / 继承缺失） |
| `build_template_lineage(db, registry, code)` | 异步装配：读模板 + 标注模板 + registry 解析，调用上述纯函数 |
| `build_annotation_field_mapping(db, code, portrait_template=None)` | 异步装配字段映射 |
| `build_portrait_dimension_details(db, person_id, template_code=None, engine=None)` | 异步装配维度明细（`engine` 可注入便于单测） |

约束：不修改评分算法与写路径；不新增 DDL；不改变既有接口返回。

### 3.3 DPS 路由（`src/rest_api/routes/routes_profiles.py`）

| 新路由 | 注册位置 | 说明 |
|---|---|---|
| `GET /portrait/templates/{code}/lineage` | `api_get_template_scoring_items` 之后、`GET /portrait/templates/{code}` 之前 | 静态子资源先于动态段 |
| `GET /portrait/annotation-templates/{code}/field-mapping` | `api_get_annotation_template` 之前 | 同段静态子资源 |
| `GET /portrait/{person_id}/dimension-details` | `api_get_portrait`（`/portrait/{person_id}`）之前，`/portrait/{person_id}/tasks` 附近 | 两段路径不与单段动态段冲突，仍前置于兜底 |

路由仅做参数校验与 `HTTPException` 映射，业务装配在 engine。

### 3.4 OpenBase 代理（`openbase/modules/dps_proxy/__init__.py`）

新增 3 条逐端点转发（复制 `dps_template_scoring_items` 模式，`_build_identity_headers` + `_forward`）：

- `GET /api/v1/dps-proxy/templates/{code}/lineage`
- `GET /api/v1/dps-proxy/annotation-templates/{code}/field-mapping`
- `GET /api/v1/dps-proxy/portraits/{person_id}/dimension-details`

注册顺序：`/templates/{code}/lineage` 与既有子资源同段；`/portraits/{person_id}/dimension-details` 在 `/portraits/{person_id}` 前后均可（三段路径不冲突），放在 `/portraits/tasks/{task_id}` 附近保持可读。

### 3.5 前端 API（`openbase-ui/src/core/api/dps.ts`）

新增类型：`DpsTemplateLineage`、`DpsLineageBinding`、`DpsLineageAnnotationView`、`DpsLineageGap`、`DpsAnnotationFieldMapping`、`DpsPortraitDimensionDetails`、`DpsDimensionRuleDetail`。

新增方法：`getTemplateLineage(code)`、`getAnnotationFieldMapping(code, params?)`、`getPortraitDimensionDetails(personId, params?)`。

### 3.6 前端页面改动

#### ① `DpsTemplateListView.vue` 详情抽屉 → 四联视图

- 抽屉加宽至 860px；保留下方基础 `el-descriptions`（compact）。
- `el-tabs` 四页，`data-test`：`template-lineage-tabs`、`template-tab-lineage|annotations|tags|scoring`。
- **族谱**：`lineage` 纵向链表，当前节点高亮；显示 `extends` 缺失/深层级告警。
- **标注模板**：表格列 = code / 归属 / 状态 / 绑定维度 / 标签数 / 缺口标签（`未绑定`（danger）/ `归属不一致`（warning））。
- **标签产出**：按标注模板分组，列 `dimension:tag_key` → 字段 → `评分项命中`（命中显示规则 key + 权重，未命中显示 `仅标签·不影响评分` warning tag）。
- **评分项**：复用 `DpsTemplateScoringItems` 展示（维度卡片 + 规则表），维度 `source_gap` 显示 `无标注来源` danger tag；顶部 `dimensions_without_annotation_source` 警示。
- 详情加载由 `getTemplate` + `getTemplateLineage` 并行完成；失败沿用既有 `dps-error` 展示。

#### ② `DpsAnnotationWorkbenchView.vue` 字段提示

- 选中模板后并行拉取 `getAnnotationFieldMapping(code)`（`portrait_template` = 归属模板）。
- 每个字段下方提示（`data-test="annotation-field-mapping"`）：
  - `affects`：`→ 写入 psychology:crisis_level · 计分：紧急→0 … · 影响评分项 psychology:crisis_level（权重 0.25）`
  - `tag_only`：`→ 写入 basic:age_stage · 仅生成标签，当前模板无同名评分项`
  - `no_tag`：`不生成标签（未配置目标维度）`
- 映射加载失败仅降级为原有提示，不阻断录入。

#### ③ `PortraitDetail.vue` 维度展开明细

- 维度行增加「展开明细」开关（`data-test="portrait-dimension-details-toggle"`，`@click.stop`）。
- 展开时按当前 `selectedTemplate || ''` 拉取 `getPortraitDimensionDetails(personId, { template_code })`，结果缓存于组件内（按模板 code 键）；`el-table` 列：评分项 / 权重 / 标签值 / 得分 / 缺值兜底。
- 缺值行 `data-test="portrait-dimension-missing-tag"` 显示 `缺值→50`。
- 展开区块 `data-test="portrait-dimension-details"`；维度自身无规则数据时显示空态提示。
- 保留原点击整行打开证据抽屉的行为。

#### ④ 缺口警示可见

- 上述三处已覆盖：模板详情「标注模板/评分项」页签 + 画像评分项弹窗（P1 已有）+ 维度展开。

---

## 4. 测试设计

### 4.1 DPS 单测 `src/tests/test_p2_explainability_v3.py`

纯函数 + 桩装配，覆盖：

1. `build_lineage_chain`：单层、两层、父缺失、成环护栏、当前节点标记。
2. `field_tag_contract`：`tag_key` 缺省、`score_map` 摘要、`score_direction` 缺省 `higher_better`。
3. `resolve_scoring_hits`：带前缀命中、无前缀 key 命中、无命中。
4. `build_field_mappings`：`affects` / `tag_only` / `no_tag` 三类汇总计数。
5. `build_template_lineage`：桩 DB（`fetch_all` 返回模板行）+ 假 registry；断言族谱、绑定归属错位、未绑定模板、标签无评分规则、`scoring=null`（模板未激活）。
6. `build_annotation_field_mapping`：桩 DB；`portrait_template` 缺省取归属；模板未激活标记。
7. `build_portrait_dimension_details`：注入假 engine（`calculate_dimension_score` 返回 `SimpleNamespace`），断言缺值 `missing=True` / 得分 / 权重；默认口径走常量。

目标：新增模块行覆盖 ≥90%。

### 4.2 OpenBase 单测

`tests/test_dps_proxy_routes_v1410.py` 追加 3 条路由注册断言（路径 + 方法），并追加「`/portraits/{person_id}/dimension-details` 与 `/portraits/{person_id}` 不互相遮蔽」断言。既有 22 条计数断言不变。

### 4.3 前端校验与 E2E

- `node node_modules\vue-tsc\bin\vue-tsc.js --noEmit`
- `node node_modules\eslint\bin\eslint.js src/core/api/dps.ts src/modules/portrait/pages/DpsTemplateListView.vue src/modules/portrait/pages/DpsAnnotationWorkbenchView.vue src/modules/portrait/pages/PortraitDetail.vue tests/e2e/portrait-lineage.spec.ts`
- 新增 `openbase-ui/tests/e2e/portrait-lineage.spec.ts`（headless + 固定视口 + 接口登录注入）：
  1. 模板族列表 → 详情 → 四页签可见，族谱含当前节点；
  2. 「标签产出」页签出现 `仅标签·不影响评分` 或命中评分项之一；
  3. 画像详情选模板 → 展开某维度 → 明细表出现规则行，缺值行显示 `缺值→50`；
  4. 无 pageerror / 非受控 4xx。
- 执行：`node node_modules\@playwright\test\cli.js test tests/e2e/portrait-lineage.spec.ts --reporter=list`；证据截图存 `doc/test/evidence/s6/ui-e2e/`。

### 4.4 DPS 回归

- `pytest src/tests/test_p2_explainability_v3.py src/tests/test_p0_template_scoring_v3.py src/tests/test_p1_governance_v3.py src/tests/test_template_registry_v2_10.py -q -p no:cacheprovider --no-cov`
- ruff 仅查新增/修改文件（全仓 355 条既有错误不作为门禁）。

---

## 5. 验收标准

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| AC-01 | 模板四联视图 | 模板详情抽屉可见「族谱/标注模板/标签产出/评分项」四页签，数据来自单一 lineage 接口 |
| AC-02 | 配置下钻 | 从「标签产出」可看到某标签的 `dimension:tag_key` → 命中评分项（规则 key + 权重），无需读代码 |
| AC-03 | 标注字段提示 | 工作台字段下方显示目标标签、计分摘要、影响评分项；无命中时明确提示「仅标签」 |
| AC-04 | 维度展开 | 画像详情维度可展开规则级明细（标签值/得分/缺值兜底），缺值行有 `缺值→50` 标记 |
| AC-05 | 关键缺口可见 | 未绑定标注模板、无标注来源维度、归属错位、标签无评分规则均以警示标签呈现 |
| AC-06 | 无回归 | DPS 定向回归 + OpenBase 代理测试全通过；`vue-tsc` 0 错误；新增文件 eslint 0 错误 |
| AC-07 | 运行时可复现 | E2E 用例实跑 PASS 并留证据截图 |

---

## 6. 风险与约束

| 风险 | 处置 |
|---|---|
| `TemplateRegistry` 仅缓存 active 模板，draft 无评分口径 | lineage 返回 `scoring=null` + `template_not_active` 缺口提示，不伪造数据 |
| 每维度一次 `profile_tag` 查询，6 维 6 次 | 只读、单画像场景；P2 不做批量优化，避免过度设计 |
| 大模板字段多（29 个）导致前端渲染长 | 字段提示为单行小字 + 详情页签表格分页可滚动 |
| 既有测试路由计数 | 已核对：22 条按 `V1410_ROUTES` 精确配对计数，新增路径不影响 |
| 已知基线失败 `test_portrait_update_route.py` / `test_portrait_update_persistence.py` | 非本次回归范围，不修 |

---

## 7. 交付物与留痕

1. 代码：DPS 3 接口 + 1 引擎模块 + 1 测试文件；OpenBase 3 代理路由 + 测试追加；前端 3 页面 + API 类型 + 1 E2E。
2. 文档升版：
   - 《OpenBase-画像模板-标注模板-评分项对应关系与治理方案》→ v1.2.0（§7 阶段三标 ✅、新增 §13 P2 实施与验证、修订历史）；
   - 《OpenBase-画像易用性完善-DevLogReport》→ v1.6.0。
3. 两仓提交并推送 `origin` / `backup` / `github` 三远程；排除无关改动（DPS `audit_archiver_engine.py` / `backup_engine.py` 等；OpenBase `llm.ts` / `Playground.vue` / `service-orchestrator.ps1`）。
