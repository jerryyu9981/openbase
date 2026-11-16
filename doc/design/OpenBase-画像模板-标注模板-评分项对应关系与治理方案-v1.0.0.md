# OpenBase 画像模板 / 标注模板 / 评分项对应关系梳理与治理方案

## 文档元信息

| 项 | 内容 |
|---|---|
| 文档版本 | v1.0.1 |
| 状态 | [Approved]（评审通过，P0 已实施并验证） |
| 适用环境 | Dev（OpenBase 8000 + DPS 8030 + 前端 5173，PostgreSQL 主库） |
| 作者 | AI 编码代理 |
| 评审人 | 需求方 / 技术负责人 |
| 创建日期 | 2026-11-16 |

### 修订历史

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-16 | 首次梳理画像模板父子关系、标注模板归属与绑定、字段→标签映射、评分项实际生效口径，并给出分阶段治理方案 | AI 编码代理 |
| v1.0.1 | 2026-11-16 | 评审通过；按推荐决策（D-01 A / D-02 A / D-03 A / D-04 留待 P1）实施 P0，补充 §11 实施结果与验证证据 | AI 编码代理 |

---

## 1. 结论摘要

1. **父子关系是"声明式"的**：`portrait_template.extends` 只支持单父、深度 ≤ 2，实际数据为 1 个根 + 3 个直接子模板；`TemplateRegistry.resolve_dimensions()` 的合并规则是"父维度先入、子覆盖同名、追加新维度"，但**该解析结果只用于维度清单/预览，不参与真实画像计算**。
2. **标注模板是"强归属"的**：每个 `annotation_template.template_code` 必须指向一个 **active** 画像模板；父模板的 `tag_bindings` 可以声明绑定子模板名下的标注模板，因此出现"归属 ≠ 绑定方"的交叉关系。
3. **标注 → 标签 → 评分链路当前是断的**：
   - 标注字段只有带 `target_dimension` 才产出标签，标签 code 固定为 `<dimension>:<field.key>`；
   - 真实评分仍使用代码内 6 维 23 条**硬编码规则**（key 无维度前缀，且与标注字段 key 交集为 0）；
   - 结论：**任何标注产生的标签都不会改变当前画像分数**，只会出现在标签列表/证据中。
4. **模板自身的权重与规则不生效**：`cor-persona-*` 四个模板声明的 32 条规则、维度权重仅在"模板校验/试算"中生效；真实计算只取维度 code 列表，权重取常量，`crime` / `intervention` 维度因不在常量表中被静默跳过。
5. 还发现三处数据一致性问题：`cor-persona-risk-v1.tag_bindings` 是对象而非数组（与当前校验器要求不符）；`cor-anno-eposition-v1`、`cor-anno-category-v1` 未被任何模板绑定；多个标注模板重复产出同名 `tag_code`，按 `(profile_id, tag_code)` upsert 会后写覆盖。

---

## 2. 画像模板族谱（实测数据）

数据来源：2026-11-16 通过 `GET /api/v1/dps-proxy/templates` 与 `/templates/{code}` 实测拉取，共 6 个模板。

| 模板 code | 名称 | 类型/主体 | 状态 | extends | 维度数 | 规则数 | 维度权重 |
|---|---|---|---|---|---|---|---|
| `cor-persona-root-v1` | 社区矫正对象全景画像基础模板（六维标签体系） | persona/person | active | — | 6 | 32 | basic .15 / crime .15 / psychology .20 / behavior .20 / social .15 / intervention .15 |
| `cor-persona-risk-v1` | 社区矫正对象风险评估画像模板 | risk/person | active | root | 6 | 32 | .10 / .25 / .25 / .20 / .10 / .10 |
| `cor-persona-assess-v1` | 社区矫正对象在矫考核画像模板 | persona/person | active | root | 6 | 32 | .05 / .10 / .20 / .30 / .15 / .20 |
| `cor-persona-intake-v1` | 社区矫正对象入矫接收画像模板 | persona/person | active | root | 6 | 32 | .25 / .20 / .20 / .05 / .20 / .10 |
| `dps-correction-v1` | 社区矫正画像（默认模板·等价于代码常量） | persona/person | active | — | 6 | 23 | basic .10 / behavior .20 / psychology .25 / social .15 / correction .15 / risk .15 |
| `wb-smoke-v1` | 工作台冒烟模板 | persona/person | draft | — | 1 | 1 | basic 1.0 |

### 2.1 继承解析语义

- 解析入口：`TemplateRegistry.resolve_dimensions(code)`；
- 规则：沿 `extends` 自下而上收集；**父维度先入、子同名维度整体覆盖、子新增维度追加**；深度上限 2（`MAX_EXTENDS_DEPTH`）；
- 子模板当前均为"全量重写 6 维"，因此继承在**数据上等价于覆盖全部维度**，`extends` 目前只起"族谱/删除保护/影响面提示"作用；
- 校验：`extends` 指向不存在的父模板、成环、超深会在保存时被拒绝。

### 2.2 关键结论：继承 ≠ 计算口径

`cor-persona-*` 的 32 条规则 key 为 `<dimension>:<key>`（如 `basic:age_stage`），而真实计算读取的是 `engines/portrait/__init__.py` 中的 23 条常量规则（key 无前缀，如 `age_stage` 不存在，实际为 `info_completeness`）。因此：

- 模板配置只在"校验 / 试算 / 规则总览"页面生效；
- 真实 `POST /portrait/calculate` 仅使用维度 code 列表过滤，权重和规则全部来自常量；
- `crime`、`intervention` 不在常量表 → `calculate_portrait` 打印 warning 后跳过，最终只计算 `basic / psychology / behavior / social` 四维。

---

## 3. 父模板 / 子模板 ↔ 标注模板关系

### 3.1 两种关系的定义

| 关系 | 载体 | 约束 | 是否被引擎消费 |
|---|---|---|---|
| 归属（强归属） | `annotation_template.template_code` | 必须指向 active 画像模板；更新归属时重新校验 | 仅用于模板级筛选与录入校验 |
| 绑定（声明式） | `portrait_template.tag_bindings[] = {annotation_template, dimensions[]}` | 数组、每项至少 1 个维度、同模板不得重复；**不校验标注模板是否存在/归属** | **否**：仅参与模板校验，不驱动录入、打分或 UI 过滤 |

### 3.2 实测矩阵

图例：● = 强归属；○ = 在 `tag_bindings` 中被声明绑定；— = 无关系。

| 标注模板 \ 画像模板 | root | risk | assess | intake | correction | 说明 |
|---|---|---|---|---|---|---|
| `cor-anno-basic-v1` | ○ | — | — | ● | — | 绑定维度 basic/social（字段实际只落 basic） |
| `cor-anno-psych-v1` | ○ | ○ | ● | — | — | risk 也绑定，但归属 assess |
| `cor-anno-behavior-v1` | ○ | — | ● | — | — | 字段落 behavior |
| `cor-anno-mgmt-v1` | ○ | — | ● | — | — | 字段落 behavior + intervention |
| `cor-anno-edu-v1` | ○ | — | ● | — | — | 字段落 intervention |
| `cor-anno-reward-v1` | ○ | — | ● | — | — | 字段落 behavior + psychology + intervention |
| `cor-anno-eposition-v1` | — | — | ● | — | — | **未被任何模板绑定（孤儿）** |
| `cor-anno-category-v1` | ● | — | — | — | — | **未被任何模板绑定（孤儿）** |

### 3.3 已识别关系问题

1. **归属与绑定错位**：root 绑定 6 个标注模板，其中 5 个归属 assess、1 个归属 intake；risk 绑定 psych（归属 assess）。当前没有"父模板可绑定子模板标注模板"的显式规则，属于事实约定。
2. **两个 active 标注模板无人绑定**：`cor-anno-eposition-v1`、`cor-anno-category-v1` 在录入工作台可见，但与画像模板无任何绑定声明，用户无法判断其归属场景。
3. **格式不一致**：`cor-persona-risk-v1.tag_bindings` 为对象 `{"dimensions":["psychology"],"annotation_template":"cor-anno-psych-v1"}`，其余为数组；当前校验器要求数组，说明该模板是校验器上线前的存量数据。
4. **绑定不校验存在性**：`tag_bindings` 中写错 code、或绑定到非 active 标注模板，保存阶段不会报错，运行时也无消费方，问题会被长期隐藏。

---

## 4. 标注模板 → 标签列表关系

### 4.1 标签生成规则（代码事实）

`AnnotationTemplateEngine.build_tag_sync_entries()`：

- 仅处理带 `target_dimension` 的字段；
- `tag_code = "<target_dimension>:<field.key>"`；
- `tag_name = 字段值的字符串`（如"高""良好""72"）；
- `score`：枚举按选项顺序**逆序**线性映射（首项 = 100，末项 = 0）；数值裁剪到 0~100；其他类型固定 80；
- `dimension = target_dimension`，写入 `profile_tag`（`(profile_id, tag_code)` 幂等 upsert）；
- 审核通过后同步，并写 `tag_lineage`。

### 4.2 各标注模板的标签产出

| 标注模板 | 字段数 | 产出标签数 | 目标维度分布 | 标签 code 示例 |
|---|---|---|---|---|
| `cor-anno-basic-v1` | 21 | 7 | basic ×7 | `basic:age_stage`、`basic:health_status` |
| `cor-anno-psych-v1` | 22 | 5 | psychology ×5 | `psychology:neuroticism`、`psychology:crisis_level` |
| `cor-anno-behavior-v1` | 21 | 6 | behavior ×6 | `behavior:report_compliance_rate`、`behavior:discipline_grade` |
| `cor-anno-mgmt-v1` | 27 | 5 | behavior ×3、intervention ×2 | `behavior:labor_evaluation`、`intervention:cooperation_level` |
| `cor-anno-edu-v1` | 23 | 3 | intervention ×3 | `intervention:education_effect` |
| `cor-anno-reward-v1` | 29 | 4 | behavior ×1、psychology ×2、intervention ×1 | `psychology:recidivism_relevance`、`intervention:measure_response` |
| `cor-anno-eposition-v1` | 19 | 1 | behavior ×1 | `behavior:signin_compliance_rate` |
| `cor-anno-category-v1` | 18 | 0 | — | 无 `target_dimension` 字段 |

### 4.3 已识别标签问题

1. **维度覆盖缺口**：`social`、`crime` 没有任何标注字段可产出标签；`dps-correction-v1` 依赖的 `correction` / `risk` 维度也完全没有标注来源。四维画像里 social 只能靠历史标签/接口导入。
2. **同名标签多来源**：`report_compliance_rate`、`signin_compliance_rate`、`labor_evaluation`、`discipline_grade`、`crisis_level`、`recidivism_relevance`、`measure_adaptation`、`cooperation_level` 在 2~3 个标注模板中重复出现；因 upsert 键只有 `(profile_id, tag_code)`，**最后审核通过的那条覆盖前一条**，无法区分来源模板/周期。
3. **评分方向写死**：枚举一律"首项最高分"。对 `crisis_level=紧急` 这类风险语义，最高风险得到 0 分，方向是否合理依赖下游规则，字段级无法配置。
4. **标签名是值而非名称**：`tag_name` 存的是"高/良好"，前端需结合 `tag_code` 才能读懂语义。

---

## 5. 画像模板评分项：声明 vs 实际

### 5.1 真实生效的 23 条评分项（`dps-correction-v1` 等价常量）

| 维度（权重） | 评分项 key | 权重 | 缺值 |
|---|---|---|---|
| basic（0.10） | info_completeness / identity_verified / contact_validity | .40 / .30 / .30 | 50 |
| behavior（0.20） | activity_level / compliance_score / stability_index / risk_behavior_flag | .25 / .35 / .25 / .15 | 50 |
| psychology（0.25） | emotional_stability / stress_resistance / social_adaptability / self_control | .30 / .25 / .25 / .20 | 50 |
| social（0.15） | family_support / social_connections / community_integration / influence_level | .30 / .25 / .25 / .20 | 50 |
| correction（0.15） | correction_stage / progress_score / goal_achievement / intervention_needs | .30 / .30 / .25 / .15 | 50 |
| risk（0.15） | recidivism_risk / social_risk / compliance_risk / psychological_risk | .30 / .30 / .20 / .20 | 50 |

- 维度分 = 该维度规则加权平均（缺失标签按 50 分计入，权重照计）；
- 综合分 = Σ(维度分 × 常量维度权重) / Σ(参与维度权重)，即**按实际计算到的维度重新归一化**；
- `confidence` = 有值标签数 / 维度规则数；任一维度 confidence < 1 或完整度 < 0.8 → `partial`。

### 5.2 各模板实际计算口径

| 模板 | 声明维度 | 实际计算维度 | 实际评分项 | 实际维度权重 |
|---|---|---|---|---|
| `dps-correction-v1` | 6 | 6（全覆盖） | 23 条常量项 | 常量 .10/.20/.25/.15/.15/.15 |
| `cor-persona-root-v1` | 6（basic/crime/psychology/behavior/social/intervention） | 4（crime、intervention 被跳过） | 常量中的 15 条（basic 3 + behavior 4 + psychology 4 + social 4） | 重新归一化：.10/.20/.25/.15 → 14.3%/28.6%/35.7%/21.4% |
| `cor-persona-risk-v1` | 6 | 4 | 同上 15 条 | 同上 |
| `cor-persona-assess-v1` | 6 | 4 | 同上 15 条 | 同上 |
| `cor-persona-intake-v1` | 6 | 4 | 同上 15 条 | 同上 |
| `wb-smoke-v1`（draft） | 1 | 1 | 常量 basic 的 3 条（模板里的 `basic:smoke` 不生效） | basic 100% |

> 说明：`cor-persona-*` 声明的 32 条规则（如 `crime:crime_type`、`psychology:neuroticism`）与常量 23 条规则**交集为 0**；模板权重在真实计算中完全不生效。

### 5.3 断链示意图（当前）

```
标注模板字段(带 target_dimension)
   → profile_tag: tag_code = "psychology:crisis_level", dimension = "psychology"
        ↑（写入成功，前端可见）
画像计算：
   规则 key = "emotional_stability" 等常量 key（无前缀）
   SELECT tag_code FROM profile_tag WHERE dimension = 'psychology'
   → 得到 "psychology:crisis_level"，与规则 key 永不相等
   → 该标签被忽略，分数不变
```

---

## 6. 问题清单与影响

| 编号 | 问题 | 严重度 | 影响 |
|---|---|---|---|
| G-01 | 模板 `dimension_config` 权重/规则不参与真实计算 | 高 | 配置与结果不一致，模板调权/改规则无效果 |
| G-02 | 标注标签 code 带维度前缀，评分规则 key 无前缀 | 高 | 标注数据永远无法影响评分 |
| G-03 | 标注字段 key 与评分项 key 两套命名空间（0 交集） | 高 | 即使修复前缀也无项可匹配 |
| G-04 | `crime` / `intervention` 维度不在常量表，被静默跳过 | 高 | 模板声明 6 维、实际 4 维，用户无感知 |
| G-05 | `tag_bindings` 不被消费且不校验引用 | 中 | 绑定错误长期隐藏，关系图不可信 |
| G-06 | 2 个标注模板未绑定、1 个存量格式不合规 | 中 | 录入入口与模板关系不清 |
| G-07 | 同名标签多来源、后写覆盖 | 中 | 标签值不可追溯，周期/来源丢失 |
| G-08 | `social` / `crime` 无标注来源 | 中 | 维度分长期靠 50 分兜底 |
| G-09 | 枚举评分方向写死（首项=100） | 低 | 风险类字段语义可能与业务方向相反 |
| G-10 | `evidence_policy` / `anomaly_rules` 仅校验不执行 | 中 | 三级审核、异常预警停留在配置层 |

---

## 7. 治理方案（建议分三阶段，待确认后实施）

### 阶段一（P0）：打通"标注 → 标签 → 评分"主链（✅ 已实施，见 §11）

1. **统一标签契约** ✅
   - DB 统一存 `tag_code = "<dimension>:<tag_key>"`；
   - 评分引擎按维度读取后，以 `tag_key`（去前缀）匹配规则；
   - 标注字段新增可选 `tag_key`（默认取 `field.key`），并支持 `score_map`（枚举→分值）与 `score_direction`（正向/反向）。
2. **模板规则成为唯一事实源** ✅
   - 计算入口改为 `calculate_portrait(person_id, template_code=...)`，内部用 `TemplateRegistry.resolve_dimensions()` 生成维度权重与规则；
   - `ScoringDispatcher` 按规则 `type` 分派（已支持 6 类）；
   - 未知维度改为显式错误或结果中标记 `unsupported`，不再静默跳过；
   - `dps-correction-v1` 继续等价常量，确保默认口径不变。
3. **补齐评分项可解释接口** ✅
   - 新增 `GET /portrait/templates/{code}/scoring-items`（维度/权重/规则/缺值策略/数据来源）；
   - 模板工作台和画像详情展示"本模板实际评分项"，与试算口径一致。
4. **`tag_bindings` 校验升级** ✅
   - 统一数组格式（兼容存量对象并给出迁移提示）；
   - 校验标注模板存在、active、且归属为当前模板或族谱内模板；
   - 未绑定/重复绑定给出明确 warning/error。

**验收标准**：同一人员用 `cor-persona-risk-v1` 计算，结果包含 `crime`/`intervention` 维度；修改模板权重后重算分数变化符合预期；一次标注审核通过后，对应维度分按规则变化；预置单测覆盖"前缀匹配、score_map、维度跳过改为报错"。

### 阶段二（P1）：数据治理与历史兼容

1. 迁移 8 个标注模板：补 `tag_key`、`score_map`，消除同名标签语义冲突；
2. `profile_tag` 增加 `annotation_template_code` / `source` 维度，避免后写覆盖（或改为按来源保留多行）；
3. 为 `social` / `crime` 补充标注字段或明确"无标注来源"并在 UI 提示；
4. 为存量 `cor-persona-risk-v1.tag_bindings` 做格式迁移与引用校验；
5. 提供一次性重算脚本与回滚方案（保留旧分数快照）。

**验收标准**：迁移脚本幂等；重算前后分数差异有对照报告；无标签丢失（按来源可追溯）。

### 阶段三（P2）：前端可解释性

1. 模板详情页改为"族谱 / 标注模板 / 标签产出 / 评分项"四联视图；
2. 标注工作台字段旁标注"将写入 `dimension:tag_key`、计分规则、影响哪个评分项"；
3. 画像详情维度展开显示：本维度参与评分的标签、实际得分与缺值兜底；
4. 未绑定标注模板、未覆盖维度在页面上以警示标签呈现。

**验收标准**：用户可从模板配置一路下钻到某条评分项及其标签来源，无需读代码；关键缺口在页面上可见。

---

## 8. 影响与风险

| 风险 | 说明 | 缓解 |
|---|---|---|
| 分数口径变化 | 模板规则真实生效后，历史分数会变化 | 先试算对比、保留旧值快照、灰度模板 |
| 标签 key 迁移 | 旧标签带前缀/新规则去前缀需兼容 | 读取层同时兼容两种形态，迁移后再收紧 |
| PG/SQLite 双后端 | 新增列/索引需两端一致 | 迁移幂等，补双后端测试 |
| 存量模板数据 | risk 的 tag_bindings 为对象、2 个孤儿模板 | 迁移脚本 + 校验 warning，不阻塞启动 |
| 性能 | 规则改为动态解析后每次计算需查模板 | 模板注册表已在内存缓存，按 code 取用 |

---

## 9. 待确认决策点

| 编号 | 决策 | 选项 | 结论 |
|---|---|---|---|
| D-01 | 评分事实源 | A. 模板规则为唯一事实源（推荐，默认模板等价常量） / B. 保留常量，仅做字段映射 | **采纳 A** |
| D-02 | 标签 code 形态 | A. DB 存 `dim:key`，引擎按维度+key 解析（推荐） / B. DB 改存无前缀 key | **采纳 A**（读取层兼容带/不带前缀） |
| D-03 | 标注模板归属策略 | A. 允许父模板绑定子模板标注模板（现状，需写入规则）（推荐） / B. 强制绑定方=归属方 | **采纳 A**（跨归属仅告警） |
| D-04 | 同名标签冲突 | A. 按来源隔离保留多行（推荐） / B. 后写覆盖 / C. 人工优先级 | **推迟至 P1** |

---

## 10. 附录：证据索引

- 模板父子与规则：`DPS/src/engines/portrait/template_registry.py`（`resolve_dimensions`）、`DPS/src/engines/portrait/template_preview.py`（`_validate_tag_bindings`、试算）
- 真实评分：`DPS/src/engines/portrait/__init__.py`（`_DIMENSION_RULES`、`_DIMENSION_WEIGHTS`）、`core.py:72-242`、`validation.py:25-46`
- 标注与标签：`DPS/src/engines/annotation_template_engine.py`（`build_tag_sync_entries`、`_score_for_tag`、`sync_tags_to_profile`）
- 实测数据：2026-11-16 `GET /api/v1/dps-proxy/templates?page_size=50`、`/templates/{code}`、`/annotation-templates?page_size=50`、`/annotation-templates/{code}`

---

## 11. P0 实施结果与验证证据（v1.0.1）

### 11.1 代码落点

| 仓库 | 文件 | 变更 |
|---|---|---|
| DPS | `src/engines/portrait/core.py` | `calculate_portrait` / `calculate_dimension_score` 接受 `dimension_rules`/`dimension_weights`/`dimension_names`；规则 key 带/不带维度前缀均可命中；模板维度缺规则显式报错 |
| DPS | `src/engines/portrait/validation.py` | 综合分改用传入权重；完整度按模板规则统计（支持后缀匹配） |
| DPS | `src/rest_api/routes/routes_profiles.py` | `_execute_calc` 以模板解析结果驱动计算；新增 `GET /portrait/templates/{code}/scoring-items` |
| DPS | `src/engines/annotation_template_engine.py` | 字段支持 `tag_key`/`score_map`/`score_direction`；标签 code 用 `tag_key` 生成；打分支持 score_map 优先与反向 |
| DPS | `src/engines/template_engine.py` | `tag_bindings` 归一化为数组并校验引用（不存在/未激活报错，跨归属告警） |
| DPS | `src/engines/portrait/template_preview.py` | 兼容存量对象格式 `tag_bindings`（warning 提示迁移），补维度元素类型校验 |
| DPS | `src/tests/test_p0_template_scoring_v3.py` | 新增 10 条单测（前缀命中、后缀兜底、缺规则报错、权重归一、tag_key/score_map、反向打分、字段校验、绑定归一与引用校验） |
| OpenBase | `openbase/modules/dps_proxy/__init__.py` | 新增 `GET /templates/{code}/scoring-items` 代理（身份头注入 + 上游透传） |
| OpenBase | `openbase-ui/src/core/api/dps.ts` | 新增评分项类型与 `getTemplateScoringItems` |
| OpenBase | `openbase-ui/src/modules/portrait/pages/PortraitDetail.vue` | 工具栏「查看评分项」+ 弹窗（维度权重、规则 key/标签 key/打分类型/权重/说明） |

### 11.2 运行态验证（2026-11-16，Dev）

| 项 | 方式 | 结果 |
|---|---|---|
| 模板驱动 6 维 | `POST /api/v2/portrait/calculate`（`template_code=cor-persona-intake-v1`，person 61） | 维度 = basic/crime/psychology/behavior/social/intervention；behavior 规则 key 为 `behavior:report_compliance_rate` 等模板 key；`storage.persisted=true` |
| 默认口径不变 | 同接口不传 `template_code`（person 61） | 维度 = basic/behavior/psychology/social/correction/risk（六维常量口径） |
| 评分项字典 | `GET /api/v2/portrait/templates/cor-persona-intake-v1/scoring-items` | `dimension_count=6`、`rule_count=32`、`source=template`、`extends=cor-persona-root-v1` |
| 代理透传 | `GET /api/v1/dps-proxy/templates/{code}/scoring-items`（JWT） | `code=0`，data 内 6 维/32 规则，权重与 DPS 直连一致 |
| 前端弹窗 | 浏览器登录后 `/portrait/tenant-1_1` 选择 `cor-persona-assess-v1` → 「查看评分项」 | PASS：显示「共 6 个维度 / 32 条规则；继承自 cor-persona-root-v1」，含 basic/crime/intervention 等 6 个维度区块 |
| 单测 | `python -m pytest src/tests/test_p0_template_scoring_v3.py -q` | 10 passed |

> 说明：排查中曾观察到 `cor-persona-*` 模板重算结果只有 4 维，经核对为 2026-11-15 创建的历史任务被幂等键（`sha256(tenant:person:template:data_version)`）复用；改用同步计算入口（不走幂等）后确认新代码已按模板输出 6 维，无需额外代码修复。

### 11.3 遗留（P1 起）

1. 存量标注模板批量补 `tag_key`/`score_map`，消除同名标签语义冲突（D-04 来源隔离）。
2. `social`/`crime` 标注来源补充；`cor-persona-risk-v1.tag_bindings` 对象格式迁移。
3. 一次“标注审核通过 → 标签落库 → 维度分变化”的全链路实跑样本（当前 Dev 库中已审批标注的字段未命中 `target_dimension`，无标签产出）。
