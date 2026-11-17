# OpenBase 画像模板 / 标注模板 / 评分项对应关系梳理与治理方案

## 文档元信息

| 项 | 内容 |
|---|---|
| 文档版本 | v1.4.0 |
| 状态 | [Approved]（评审通过；P0、P1、P2、P3、P4 均已实施并验证） |
| 适用环境 | Dev（OpenBase 8000 + DPS 8030 + 前端 5173，PostgreSQL 主库） |
| 作者 | AI 编码代理 |
| 评审人 | 需求方 / 技术负责人 |
| 创建日期 | 2026-11-16 |

### 修订历史

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-16 | 首次梳理画像模板父子关系、标注模板归属与绑定、字段→标签映射、评分项实际生效口径，并给出分阶段治理方案 | AI 编码代理 |
| v1.0.1 | 2026-11-16 | 评审通过；按推荐决策（D-01 A / D-02 A / D-03 A / D-04 留待 P1）实施 P0，补充 §11 实施结果与验证证据 | AI 编码代理 |
| v1.1.0 | 2026-11-16 | 实施 P1（D-04 采纳 A：来源隔离保留多行）：标注模板字段治理、`profile_tag` 来源列与读侧择优、维度标注来源缺口提示、`tag_bindings` 迁移、重算/回滚脚本；补 §12 实施结果与验证证据 | AI 编码代理 |
| v1.1.1 | 2026-11-17 | 修复前端走查环境阻塞：新增 Playwright headless 走查用例（固定视口），前端评分项弹窗验证由 BLOCKED 转 PASS，补证据截图与执行方式 | AI 编码代理 |
| v1.2.0 | 2026-11-17 | 实施 P2「前端可解释性」：DPS 新增模板 lineage / 标注字段映射 / 画像维度明细三个只读接口，OpenBase 三代理路由，前端四联视图与维度展开；补 §13 实施结果与验证证据 | AI 编码代理 |
| v1.3.0 | 2026-11-17 | 实施 P3「策略执行与孤儿治理」：证据来源落库与审核门禁、异常规则求值、孤儿标注模板治理报告；DPS 2 只读接口 + OpenBase 2 代理 + 前端证据录入/异常预警/策略摘要 + 20 条单测 + 3 条 E2E；补 §14 实施结果与验收对照 | AI 编码代理 |
| v1.4.0 | 2026-11-17 | 实施 P4「多级审核」：逐级状态机（非末级通过保持 pending）、应审级数快照、审核留痕表与只读接口、前端进度与终审按钮/留痕弹窗；顺带修复 P3 遗漏的 DDL 契约冻结列；补 §15 实施结果与验收对照 | AI 编码代理 |

---

## 1. 结论摘要

> 下列 1~5 为**治理前（2026-11-16）实测结论**，用于说明问题成因；P0/P1/P2 实施后的现行口径见 §11、§12、§13。

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

### 阶段二（P1）：数据治理与历史兼容（✅ 已实施，见 §12）

1. 迁移 8 个标注模板：补 `tag_key`、`score_map`，消除同名标签语义冲突；
2. `profile_tag` 增加 `annotation_template_code` / `source` 维度，避免后写覆盖（或改为按来源保留多行）；
3. 为 `social` / `crime` 补充标注字段或明确"无标注来源"并在 UI 提示；
4. 为存量 `cor-persona-risk-v1.tag_bindings` 做格式迁移与引用校验；
5. 提供一次性重算脚本与回滚方案（保留旧分数快照）。

**验收标准**：迁移脚本幂等；重算前后分数差异有对照报告；无标签丢失（按来源可追溯）。

### 阶段三（P2）：前端可解释性（✅ 已实施，见 §13）

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
| D-04 | 同名标签冲突 | A. 按来源隔离保留多行（推荐） / B. 后写覆盖 / C. 人工优先级 | **采纳 A**（P1 实施：`profile_tag` 来源列 + 读侧择优） |

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

1. ~~存量标注模板批量补 `tag_key`/`score_map`，消除同名标签语义冲突（D-04 来源隔离）。~~（P1 完成，见 §12）
2. ~~`social`/`crime` 标注来源补充；`cor-persona-risk-v1.tag_bindings` 对象格式迁移。~~（P1 完成，见 §12）
3. 一次“标注审核通过 → 标签落库 → 维度分变化”的全链路实跑样本（当前 Dev 库中已审批标注的字段未命中 `target_dimension`，无标签产出）。

---

## 12. P1 实施结果与验证证据（v1.1.0）

**决策落地**：D-04 采纳 A —— 同一 `tag_code` 按来源保留多行；评分读取按"来源优先级 → 最新"确定性择优。

### 12.1 代码落点

| 仓库 | 文件 | 变更 |
|---|---|---|
| DPS | `src/ddl/schema_profile_dependents.py` | `profile_tag` 双方言新增 `source` / `annotation_template_code`（NOT NULL DEFAULT `''`）；PG 退役 `UNIQUE(profile_id, tag_code)`；新增演进常量 `PROFILE_TAG_SOURCE_COLUMNS` / `PROFILE_TAG_SOURCE_EVOLUTION_PG` / `_SQLITE`（DDL 单一来源） |
| DPS | `src/database.py` | 新增 `_ensure_profile_tag_source_columns()`：启动期幂等补齐来源列；PG 建 `uq_profile_tag_source(profile_id, tag_code, source, annotation_template_code)`；存量行标 `source='legacy'` |
| DPS | `src/engines/annotation_template_engine.py` | 标签写入按来源隔离 upsert（冲突键含 `source` + `annotation_template_code`）；列探测降级保留旧列集兼容 |
| DPS | `src/engines/portrait/crud.py` | 新增 `pick_preferred_tags()`（`manual_annotation` > 其他 > `legacy`，同优先级取最新）；标签读取优先带来源列，缺列自动回退 |
| DPS | `src/engines/portrait/risk.py` | 风险维度标签读取复用择优口径，消除重复 SQL |
| DPS | `src/engines/p1_governance.py` | 新增：`govern_field_schema`（补 `tag_key`/`score_map`，幂等）、`normalize_tag_bindings`（对象→数组）、`dimension_source_index`/`audit_annotation_sources`（来源缺口）、`migrate_annotation_templates` / `migrate_tag_bindings` / `run_migration` |
| DPS | `scripts/p1_governance_migration.py` | 迁移 CLI：默认 dry-run，`--apply` 写库，输出 JSON 报告（幂等可重跑） |
| DPS | `scripts/p1_recompute_profiles.py` | 重算 CLI：旧分快照 → 重算 → 前后对照报告 → `--rollback` 回滚 |
| DPS | `src/rest_api/routes/routes_profiles.py` | `scoring-items` 增加 `annotation_sources` / `source_gap` 与 `dimensions_without_annotation_source` |
| DPS | `src/tests/test_p1_governance_v3.py` | 新增 20 条单测（字段治理幂等、绑定归一、来源索引、择优、SQLite 来源隔离写读、迁移幂等、重算对照） |
| DPS | `src/tests/test_v2_11_ddl_profile_dependents.py` | 冻结列集随 P1 增量更新（PG 21 / SQLite 8 列，非对称 13 列不变）；新增"来源隔离索引位于演进清单"契约断言 |
| OpenBase | `openbase-ui/src/core/api/dps.ts` | 评分项类型补 `annotation_sources` / `source_gap` / `dimensions_without_annotation_source` |
| OpenBase | `openbase-ui/src/modules/portrait/pages/PortraitDetail.vue` | 评分项弹窗：维度标注来源标签 + 「无标注来源」警示 + 顶部缺口汇总 |

### 12.2 迁移内容（Dev 实跑）

| 项 | 结果 |
|---|---|
| 标注模板字段 | 8 个模板扫描；7 个变更（v1→v2）、`cor-anno-category-v1` 无维度字段保持不变；枚举字段落 `score_map`（线性映射，与旧默认算法等价，**分数口径不变**）；全部字段落 `tag_key` |
| 二次执行 | `changed=0`，幂等成立 |
| `profile_tag` 结构 | 新增 `source` / `annotation_template_code`；旧唯一约束已删除；`uq_profile_tag_source` 已建；存量 1 行标 `source=legacy`（无标签丢失） |
| `tag_bindings` | 存量已为数组；对象格式迁移逻辑对老环境生效（引用校验复用 P0，不通过仅记 issue 不阻断） |
| 来源缺口 | `dimension_gaps = {cor-persona-root/risk/assess/intake: ["crime","social"]}`；孤儿标注模板 = `cor-anno-category-v1`（无维度字段） |

### 12.3 重算与回滚验证（Dev）

| 项 | 方式 | 结果 |
|---|---|---|
| 对照报告（dry-run） | `python scripts/p1_recompute_profiles.py --limit 5` | 5 人全部 ok；示例：`dps-tenant-001_admin1_003` 综合 81.2 → 50.0（六维 40/45/50/42/48/15 → 50），差异逐维记录 |
| 写库 | `--apply --person-id dps-tenant-001_admin1_003` | `storage.persisted=true target=profile_six_dimension_columns`，六维列更新为 50 |
| 回滚 | `--rollback <snapshot>` | `restored=1`；六维列恢复 40/45/50/42/48/15、综合 81.2（与快照一致） |

> 说明：`after` 全为 50 是因为该批画像当前无标签命中（缺值兜底 50），属预期；重算脚本的价值在于"旧分快照 + 逐人逐维对照"，而非制造分数变化。

### 12.4 接口与前端

| 项 | 方式 | 结果 |
|---|---|---|
| DPS 评分项 | `GET /api/v2/portrait/templates/cor-persona-risk-v1/scoring-items` | `dimensions_without_annotation_source=["crime","social"]`；basic 来源 `cor-anno-basic-v1`，psychology 来源 `cor-anno-psych-v1`+`cor-anno-reward-v1`，behavior 4 来源，intervention 3 来源 |
| OpenBase 代理 | `GET /api/v1/dps-proxy/templates/{code}/scoring-items`（JWT） | 与直连一致（gap 与来源列表逐项相同） |
| 前端 | `vue-tsc --noEmit` / `eslint`（2 文件） | 0 错误 |
| 前端走查 | Playwright headless：`node node_modules/@playwright/test/cli.js test tests/e2e/portrait-scoring-sources.spec.ts --reporter=list` | **PASS**：6 个维度区块、≥1 个「标注来源」标签、crime/social 缺口警示 2 个、页面零 `pageerror`/`console.error`；证据截图 `doc/test/evidence/s6/ui-e2e/p1-scoring-sources-dialog.png` |

### 12.5 测试

| 项 | 命令 | 结果 |
|---|---|---|
| P1 新增单测 | `pytest src/tests/test_p1_governance_v3.py` | 20 passed |
| DDL 契约 | `pytest src/tests/test_v2_11_ddl_profile_dependents.py` | 19 passed（含新增来源索引契约） |
| 相关回归 | 标注/评分/租户/命名空间 8 个文件 | 135 passed, 1 skipped |
| 静态检查 | `ruff check`（P1 新增/重写 5 文件） | All checks passed |
| 既有基线 | `pytest test_portrait_update_route.py::...whitelist` | 2 条失败为**既有基线**（响应自 96d8e83 起含 `version`，用例未同步），与 P1 无关 |

### 12.6 运维手册（P1 产物的使用方式）

```bash
# 1) 配置侧治理（幂等；建议先 dry-run 看报告）
python scripts/p1_governance_migration.py
python scripts/p1_governance_migration.py --apply
# 2) 一次性重算（默认只出报告；快照始终落盘）
python scripts/p1_recompute_profiles.py --limit 50
python scripts/p1_recompute_profiles.py --apply
python scripts/p1_recompute_profiles.py --apply --template-code cor-persona-risk-v1
# 3) 回滚（按快照恢复六维列与 attributes_json）
python scripts/p1_recompute_profiles.py --rollback reports/p1_recompute_snapshot_<ts>.json
```

> 回滚边界：仅恢复 `profile` 六维列 / `overall_score` / `attributes_json`；不恢复 `profile_history` 与标注/标签表（这两类为追加型数据，回滚会造成证据缺失）。

### 12.7 遗留（P2 起）

1. `social` / `crime` 维度仍无标注字段来源（当前以 UI 缺口提示替代，需业务确认是否补字段）。
2. 同名 `tag_code` 跨模板的**语义歧义**（如 `crisis_level` 选项集合不同）已通过来源隔离与显式 `score_map` 缓解，但业务侧仍需确认优先级策略。
3. 前端可视化走查已改为 Playwright headless 可重复执行（不再依赖 IDE 内置浏览器）；新增页面仍需补对应 spec。

---

## 13. P2 实施结果与验证证据（v1.2.0）

### 13.1 交付物清单

| 仓库 | 交付物 | 说明 |
|---|---|---|
| DPS | `src/engines/p2_explainability.py` | 纯函数（族谱/字段契约/评分项命中/缺口）+ 三个异步装配函数 |
| DPS | `src/rest_api/routes/routes_profiles.py` | 新增 3 条只读路由；`scoring-items` 改为复用 `build_scoring_payload`（口径单源） |
| DPS | `src/tests/test_p2_explainability_v3.py` | 15 条单测；新增模块行覆盖率 94% |
| OpenBase | `openbase/modules/dps_proxy/__init__.py` | 3 条逐端点代理（身份头注入 + 错误体保真） |
| OpenBase | `tests/test_dps_proxy_routes_v1410.py` | 追加 3 条注册断言 + 动态段不遮蔽断言 |
| 前端 | `src/core/api/dps.ts` | 7 个类型 + 3 个方法 |
| 前端 | `DpsTemplateListView.vue` / `DpsAnnotationWorkbenchView.vue` / `PortraitDetail.vue` | 四联视图 / 字段提示 / 维度展开 |
| 前端 | `tests/e2e/portrait-lineage.spec.ts` | 2 条 headless 走查用例 |

### 13.2 新增接口契约

| 接口 | 用途 | 关键返回 | 错误语义 |
|---|---|---|---|
| `GET /api/v2/portrait/templates/{code}/lineage` | 四联视图单一数据源 | `lineage[]`、`bindings[]`、`annotation_templates[]`、`scoring`、`gaps` | 模板不存在 404；模板未激活时 `scoring=null` + `template_not_active` |
| `GET /api/v2/portrait/annotation-templates/{code}/field-mapping?portrait_template=` | 字段 → 标签 → 评分项 | `fields[]`（`tag_code`/`score_rule`/`affects_scoring`/`scoring_status`）、`summary` | 标注模板不存在 404 |
| `GET /api/v2/portrait/{person_id}/dimension-details?template_code=&dimension=` | 维度规则级明细 | `dimensions[].rules[]`（`value`/`score`/`missing`）、`missing_policy` | 画像/模板不存在 404；模板无该维度 400 |

约定：`scoring_status` = `affects`（命中评分项）/ `tag_only`（仅写标签）/ `no_tag`（无目标维度）；缺值 `missing=true` 且按 50 分计入。

### 13.3 前端四项落地

| 治理要求 | 呈现位置 | 关键标识 |
|---|---|---|
| 四联视图 | 模板族详情抽屉 `el-tabs`：族谱 / 标注模板 / 标签产出 / 评分项 | `template-lineage-tabs`、`template-lineage-node`、`template-tag-only-tag`、`template-dimension-gap-tag` |
| 字段旁提示 | 标注工作台每个字段下方：写入 `dimension:tag_key` · 计分摘要 · 影响评分项 | `annotation-field-mapping` |
| 维度展开 | 画像详情维度行「展开明细」：评分项 / 标签值 / 权重 / 得分 / 缺值兜底 | `portrait-dimension-details-toggle`、`portrait-dimension-details`、`portrait-dimension-missing-tag` |
| 缺口警示 | 抽屉顶部缺口汇总 + 标注模板「未绑定/归属不一致」+ 评分项「无标注来源」 | `template-lineage-gaps`、`template-unbound-tag`、`template-ownership-mismatch-tag`、`template-scoring-gap` |

### 13.4 验证证据

| 项目 | 命令 | 结果 |
|---|---|---|
| DPS 新增单测 | `pytest src/tests/test_p2_explainability_v3.py` | 15 passed |
| DPS 定向回归 | P2 + P0 scoring + P1 governance + template registry | 55 passed |
| DPS 覆盖率 | `--cov=engines.p2_explainability` | 94% |
| DPS 静态检查 | `ruff check`（新增文件） | All checks passed |
| OpenBase 代理测试 | `pytest tests/test_dps_proxy_routes_v1410.py -q` | 47 passed |
| 前端类型检查 | `vue-tsc --noEmit` | 0 错误 |
| 前端静态检查 | `eslint`（4 个改动文件） | 0 错误 |
| 前端 E2E | `portrait-lineage.spec.ts` + `portrait-scoring-sources.spec.ts`（headless 1440×900） | 3 passed |
| 运行时冒烟 | 经 OpenBase 代理直调 3 接口 | 全部 200，数据见 §13.5 |

证据截图：

- `doc/test/evidence/s6/ui-e2e/p2-template-lineage.png`（四联视图）
- `doc/test/evidence/s6/ui-e2e/p2-dimension-details.png`（维度展开 + 缺值兜底）

### 13.5 实测下钻样例（2026-11-17，Dev）

| 调用 | 结果摘要 |
|---|---|
| `templates/cor-persona-root-v1/lineage` | 族谱 1 节点；绑定 6 个标注模板；标注模板视图 8 个；6 维 32 条规则；缺口 10 项 = 2 个无标注来源维度 + 2 个未绑定标注模板 + 6 个归属错位 |
| `annotation-templates/cor-anno-psych-v1/field-mapping` | 归属 `cor-persona-assess-v1`（active）；22 字段中 5 个命中评分项（`affects`），其余 17 个不产出标签 |
| `portraits/tenant-1_1/dimension-details?template_code=cor-persona-root-v1` | 6 维；`basic` 7 条规则全部缺值 → 每行显示「缺值→50」，维度分 50（兜底） |

### 13.6 只读边界与遗留

1. P2 **不改变**评分算法、写路径与既有接口返回；`scoring-items` 仅做实现复用，响应结构保持不变。
2. 维度明细每维度查询一次 `profile_tag`（单画像 6 次读），当前场景可接受；批量画像下钻如需性能优化另行评审。
3. §12.7 的两项业务遗留（`social`/`crime` 无标注字段、同名标签语义歧义）仍由业务确认；P2 已使这两类缺口在页面可见。

---

## 14. P3 实施结果与验证证据（v1.3.0）

依据 §6 的 G-10（`evidence_policy` / `anomaly_rules` 仅校验不执行）与 §12.7 / §13.6 遗留实施。P3 让模板上**已声明但从未执行**的两类策略真正生效，并补孤儿标注模板治理入口；**不改变评分算法与默认行为**。

### 14.1 交付物清单

| 仓库 | 交付物 | 说明 |
|---|---|---|
| DPS | `src/ddl/schema_profile_dependents.py` | `annotation.evidence_source` 建表列（PG `VARCHAR(200)` / SQLite `TEXT`）+ ALTER 常量（DDL 单一来源） |
| DPS | `src/database.py` | `_ensure_annotation_evidence_source()`：PG `ADD COLUMN IF NOT EXISTS`；SQLite `PRAGMA table_info` 探测后 ALTER；接入启动装配链 |
| DPS | `src/engines/p3_policies.py`（新增） | 规则上下文双键、异常规则求值、证据策略校验、孤儿模板识别、画像预警聚合、策略装载 |
| DPS | `src/engines/annotation_template_engine.py` | 创建/读取标注时按实际列集合动态写入 `evidence_source`；列缺失降级且如实标注 `evidence_source_persisted=false` |
| DPS | `src/rest_api/routes/routes_profiles.py` | 创建标注接受 `evidence_source`（≤200）；审核通过前证据门禁（409）；通过后求值异常规则；新增 2 条只读路由 |
| DPS | `src/tests/test_p3_policies_v3.py`（新增） | 20 条单测（含写路径落库、审核门禁 409、审核响应装配） |
| OpenBase | `openbase/modules/dps_proxy/__init__.py` | 2 条代理路由（静态段注册在动态段之前） |
| OpenBase | `tests/test_dps_proxy_routes_v1410.py` | 2 条注册断言 + `governance` 静态段不被 `/portraits/{person_id}` 遮蔽断言 |
| 前端 | `src/core/api/dps.ts` | 5 个类型 + `getPortraitAnomalyAlerts` / `getOrphanAnnotationTemplates`；创建标注载荷补 `evidence_source` |
| 前端 | `DpsAnnotationWorkbenchView.vue` | 「证据来源（文书编号）」输入 + 按模板策略动态必填提示 + 409 文案展示 |
| 前端 | `PortraitDetail.vue` | 「异常预警」区块：规则/动作/来源标注时间 + 未执行规则警示 |
| 前端 | `DpsTemplateListView.vue` | 评分项页签策略摘要（证据来源 / 审核级数 / 异常规则）+ 多级审核未支持警示 |
| 前端 | `tests/e2e/portrait-policies.spec.ts`（新增） | 3 条 headless 走查用例（策略摘要 / 证据来源 / 异常预警） |

### 14.2 数据模型与幂等演进

| 对象 | 变更 | 幂等策略 |
|---|---|---|
| `annotation.evidence_source` | 新增可空列（不建索引、不回填） | PG `ADD COLUMN IF NOT EXISTS`；SQLite PRAGMA 探测后 ALTER |
| 启动装配 | `_ensure_annotation_evidence_source()` | 与既有 `_ensure_*` 同链执行，重复启动无副作用 |

存量行 `evidence_source=NULL`；模板未声明 `require_source` 时不受影响。

### 14.3 策略执行语义

1. **证据策略**：`require_source=true` 且来源为空 → 审核通过被拒（409，状态不变更）；证据列未迁移时**降级放行**并 `logger.warning`，响应标注 `persisted=false / enforced=false`。
2. **异常规则**：仅结构化条件（`{all|any: [{field,op,value}]}`）可执行，复用 `engines/portrait/conditions.py`；字符串表达式返回 `evaluable=false` 且**不执行**；求值异常被捕获，不影响审核成功。
3. **多级审核**：`review_levels>1` 仅告警（响应 `review_levels_supported=false` + 页面警示），当前审核状态机仍为单级 `pending → approved/rejected/modified`。
4. **默认行为不变**：策略为空时创建/审核语义与 P2 一致，仅新增可选字段。

### 14.4 新增接口契约

| 接口 | 用途 | 关键返回 | 错误语义 |
|---|---|---|---|
| `GET /api/v2/portrait/{person_id}/anomaly-alerts?template_code=&limit=` | 画像异常预警聚合（只读） | `person_id` / `template_code` / `scanned` / `alerts[]`（`rule`/`action`/`matched`/`evaluable`/`reason`/`annotation_id`/`created_at`）/ `unevaluated_rules[]` | 画像不存在 404 |
| `GET /api/v2/portrait/governance/orphan-annotation-templates` | 孤儿标注模板治理报告（只读，给建议不改数据） | `items[]`（`code`/`name`/`status`/`owned_by`/`suggested_action`/`reason`）/ `total` | — |

审核响应新增 `evidence`（`required`/`provided`/`satisfied`/`review_levels`/`review_levels_supported`/`persisted`/`enforced`）与 `anomaly_alerts[]`；创建标注响应新增 `evidence_source` / `evidence_source_persisted`。

### 14.5 前端落地

| 能力 | 呈现位置 | 关键标识 |
|---|---|---|
| 证据来源录入 | 标注工作台表单「证据来源（文书编号）」，必填态随归属模板策略变化 | `annotation-evidence-source` |
| 异常预警 | 画像详情维度卡片下方：规则 + 动作 + 标注时间；未执行规则警示 | `portrait-anomaly-alerts`、`portrait-anomaly-alert`、`portrait-anomaly-unevaluated` |
| 策略摘要 | 模板详情「评分项」页签顶部：证据来源 / 审核级数 / 异常规则条数 | `template-policy-summary`、`template-evidence-policy`、`template-review-levels`、`template-anomaly-rule-count` |
| 多级审核警示 | 同上，`review_levels>1` 时显示 | `template-review-levels-warning` |

### 14.6 验证证据

| 项目 | 命令 | 结果 |
|---|---|---|
| DPS P3 单测 | `pytest src/tests/test_p3_policies_v3.py` | 20 passed；`engines.p3_policies` 行覆盖率 99% |
| DPS 定向回归 | P3 + P2 + P1 + P0 + annotation chain | 95 passed |
| DPS 静态检查 | `ruff check`（新增/改动文件） | All checks passed |
| OpenBase 代理测试 | `pytest tests/test_dps_proxy_routes_v1410.py -q` | 50 passed |
| OpenBase 静态检查 | `ruff check` | All checks passed |
| 前端类型检查 | `vue-tsc --noEmit` | 0 错误 |
| 前端静态检查 | `eslint`（改动 4 文件 + 新 E2E） | 0 错误 |
| 前端 E2E | `portrait-policies.spec.ts`（headless 1440×900） | 3 passed |
| E2E 回归 | `portrait-lineage.spec.ts` + `portrait-scoring-sources.spec.ts` | 3 passed |
| 运行时冒烟（经 OpenBase 代理） | 孤儿报告 / 画像预警 | 孤儿 `total=2`（`cor-anno-eposition-v1` → `cor-persona-assess-v1`；`cor-anno-category-v1` → `cor-persona-root-v1`）；`anomaly-alerts` 200（样例画像暂无已审核标注，`scanned=0`） |

证据截图：

- `doc/test/evidence/s6/ui-e2e/p3-evidence-source.png`（证据来源录入）
- `doc/test/evidence/s6/ui-e2e/p3-anomaly-alerts.png`（异常预警区块）
- `doc/test/evidence/s6/ui-e2e/p3-template-policy.png`（评分项策略摘要）

### 14.7 验收标准对照

| 编号 | 验收项 | 结论 | 证据 |
|---|---|---|---|
| AC-P3-01 | 证据来源可写入 | ✅ | 单测 `test_create_structured_annotation_persists_evidence_source`（INSERT 含列且参数含来源、响应回显）；E2E 工作台可录入 |
| AC-P3-02 | 证据门禁生效 | ✅ | 单测 `test_review_blocks_approval_without_evidence_source`（409 + 明确文案）；`test_review_returns_evidence_and_anomaly_alerts`（有来源放行） |
| AC-P3-03 | 异常规则可执行 | ✅ | 单测同上：结构化条件 `matched=true`；字符串条件 `evaluable=false` 且审核成功 |
| AC-P3-04 | 画像预警可见 | ✅ | E2E「画像详情展示异常预警区块」PASS + 截图 `p3-anomaly-alerts.png` |
| AC-P3-05 | 孤儿治理可见 | ✅ | 运行时冒烟 `total=2`，含建议动作 `bind_to_owner` 与归属模板 |
| AC-P3-06 | 默认行为不变 | ✅ | 空策略走 `load_policy_bundle` 默认空策略分支；审核响应仅新增可选字段；DPS 95 条定向回归全通过 |
| AC-P3-07 | 无回归 | ✅ | DPS 95 passed；OpenBase 50 passed；`vue-tsc`/`eslint` 0 错误；3 条新 E2E + 3 条回归 E2E 全 PASS |

### 14.8 边界与遗留

1. **多级审核未支持**：需重做审核状态机与审核 UI，P3 仅显式告警，登记为后续需求（建议 P4）。
2. **字符串条件不求值**：避免任意表达式执行风险，页面与响应均标注 `evaluable=false` 并提示改为结构化条件。
3. **孤儿模板只给建议**：治理报告不自动改数据（G-05/G-06 的最终处置需业务裁定归属或停用）。
4. **G-08 仍在业务侧**：`social` / `crime` 无标注来源字段，P1/P2 已页面提示，P3 未扩围。

---

## 15. P4 实施结果与验证证据（v1.4.0）

依据 §14.8「多级审核未支持，建议 P4」实施：让 `evidence_policy.review_levels` 真正生效，标注逐级通过后才终审并联动标签；**默认单级行为不变**。

### 15.1 交付物清单

| 仓库 | 交付物 | 说明 |
|---|---|---|
| DPS | `src/ddl/schema_profile_dependents.py` | `annotation.review_level`（默认 0）、`review_levels_required`（默认 1）列；`annotation_review_log` 建表/索引（PG/SQLite 单一来源） |
| DPS | `src/database.py` | `_ensure_annotation_review_progress()`：PG `ADD COLUMN IF NOT EXISTS` + 建表；SQLite PRAGMA 探测后 ALTER + 建表 |
| DPS | `src/engines/annotation_template_engine.py` | `resolve_review_outcome` 逐级状态机、`review_annotation` 进度持久化、`record_review_log` / `query_review_logs`、队列与详情读取进度列、创建时快照应审级数 |
| DPS | `src/engines/p3_policies.py` | 级数解析/归一（1~5）；`review_levels_supported` 改为按上限判定 |
| DPS | `src/rest_api/routes/routes_profiles.py` | 审核响应新增 `review{level,required,finalized}` 与 `review_log_persisted`；仅终审联动标签/求值异常规则；新增 `GET /portrait/annotations/{id}/review-log` |
| DPS | `src/tests/test_p4_multi_level_review.py`（新增） | 35 条单测（状态机/解析/DDL/写路径/持久化/留痕/编排/只读接口） |
| DPS | `src/tests/test_v2_11_ddl_profile_dependents.py` | 修正 `annotation` 冻结列（补 P3 `evidence_source` 与 P4 两列），修复 P3 遗漏的 DDL 契约失败 |
| OpenBase | `openbase/modules/dps_proxy/__init__.py` | `GET /annotations/{annotation_id}/review-log` 代理 |
| OpenBase | `tests/test_dps_proxy_routes_v1410.py` | 注册断言 + 不与 `GET /annotations`/`POST .../review` 遮蔽断言 |
| 前端 | `src/core/api/dps.ts` | 队列行补进度字段；新增 `DpsAnnotationReviewProgress` / `DpsAnnotationReviewLogItem` / `DpsAnnotationReviewLog` 与 `getAnnotationReviewLog` |
| 前端 | `DpsAnnotationWorkbenchView.vue` | 「审核进度」列、`通过本级（N/M）` / `终审通过` 按钮、分级提示、审核记录弹窗 |
| 前端 | `DpsTemplateListView.vue` | 移除「当前仅支持单级审核」警示，保留级数摘要 |
| 前端 | `tests/e2e/portrait-multilevel-review.spec.ts`（新增） | 2 条 headless 用例（进度+按钮文案 / 留痕弹窗） |

### 15.2 数据模型与不变式

| 对象 | 变更 | 幂等/兼容 |
|---|---|---|
| `annotation.review_level` | 已通过级数（0 = 未通过） | 默认 0；存量行按 0 处理 |
| `annotation.review_levels_required` | 创建时快照的应审级数（1~5） | 默认 1 → 存量 `pending` 行按单级收口，不追溯补审 |
| `annotation_review_log` | 只追加留痕（`annotation_id/review_level/action/reviewer/comment/created_at`） | `CREATE TABLE/INDEX IF NOT EXISTS`；写失败仅 WARN |

### 15.3 逐级审核语义

| 动作 | 条件 | 新状态 | 级数 | 终审 |
|---|---|---|---|---|
| `approved` | `level + 1 < required` | `pending` | `level + 1` | 否（不联动标签、不求值异常规则） |
| `approved` | `level + 1 >= required` | `approved` | `required` | 是（联动标签 + 求值异常规则） |
| `rejected` | 任意级 | `rejected` | 不变 | 是（终态） |
| `modified` | 任意级 | `modified` | 不变 | 是（终态） |

补充：证据门禁在**任一级通过前**执行（来源缺失且列已持久化 → 409，状态与级数不变）；留痕记录“本次审核所处级数”；不强制不同审核人（无分级角色模型）。

### 15.4 接口契约

| 接口 | 变更 | 关键字段 |
|---|---|---|
| `POST /api/v2/portrait/annotations/{id}/review` | 扩展 | `review{level,required,finalized}`、`review_log_persisted`；非末级通过时 `status=pending` |
| `POST /api/v2/portrait/annotations/batch-review` | 继承 | 每条结果含 `review` 块，单条失败不影响其余 |
| `GET /api/v2/portrait/annotations` | 扩展 | 行内 `review_level` / `review_levels_required` |
| `GET /api/v2/portrait/annotations/{id}/review-log` | 新增（只读） | `{annotation_id, items[], total}`；不存在 404；表未迁移返回空列表 |

### 15.5 前端落地

| 能力 | 呈现 | 关键标识 |
|---|---|---|
| 审核进度 | 队列列：`第 N/M 级`，终审后 `已完成` | `annotation-review-progress-text` |
| 分级按钮 | `通过本级（N/M）` / `终审通过` / 单级 `通过` | `annotation-approve` |
| 分级提示 | 非末级「已通过第 N 级，待第 N+1 级审核」；末级「终审通过，标签联动已执行」 | — |
| 审核记录 | 行内「记录」打开弹窗，按级升序展示动作/审核人/意见/时间 | `annotation-review-log`、`annotation-review-log-dialog` |
| 策略摘要 | 模板评分项页签保留「审核级数：N 级」，移除单级限制警示 | `template-review-levels` |

### 15.6 验证证据

| 项目 | 命令/方式 | 结果 |
|---|---|---|
| DPS P4 单测 | `pytest src/tests/test_p4_multi_level_review.py` | 35 passed |
| DPS 定向回归 | P4 + P3 + P2 + P1 + P0 + annotation chain + DDL 契约 | 173 passed |
| DPS 静态检查 | `ruff check`（新测/策略文件） + `--select F,E9`（存量改动文件） | 0 错误 |
| OpenBase 路由测试 | `pytest tests/test_dps_proxy_routes_v1410.py -q` | 52 passed |
| OpenBase 静态检查 | `ruff check` | All checks passed |
| 前端类型/静态检查 | `vue-tsc --noEmit`；`eslint`（3 文件 + 新 E2E） | 0 错误 |
| 前端 E2E | `portrait-multilevel-review.spec.ts` | 2 passed（截图 `p4-review-progress.png`、`p4-review-log.png`） |
| E2E 回归 | `portrait-policies.spec.ts`、`portrait-lineage.spec.ts` | 3 + 2 passed（需 `--trace=off` 规避 trace 对大响应的 8s 超时影响） |
| 真实链路冒烟（经 OpenBase 代理） | 创建多级标注 → 第 1 级通过 → 查留痕 | `required=2`、`created.progress_persisted=true`、`status=pending`、`review={level:1,required:2,finalized:false}`、留痕 `total=1` |

说明：E2E 标注页用例通过 `page.route` 固定模板/队列/留痕响应（本机 tracing + 大响应对前端 8s 预算的影响），UI 断言为强断言；真实链路由上述冒烟与 DPS 单测覆盖。

### 15.7 验收标准对照

| 编号 | 验收项 | 结论 | 证据 |
|---|---|---|---|
| AC-P4-01 | 多级逐级生效 | ✅ | 单测三组推进（1→2 pending，2→3 approved）；真实冒烟 1/2 级 pending |
| AC-P4-02 | 终审才联动 | ✅ | 编排单测：非末级 `tag_sync=null`、`sync_calls=0`；末级调用 1 次并求值 |
| AC-P4-03 | 审核留痕 | ✅ | 单测追加/降级/查询；真实冒烟 `total=1`；E2E 弹窗显示 `一级通过` |
| AC-P4-04 | 证据门禁保持 | ✅ | 缺来源任一级 409（P3 用例保持通过） |
| AC-P4-05 | 进度可见 | ✅ | 队列/审核响应含进度；E2E 断言 `第 1/2 级`、`第 0/1 级`、`终审通过`/`通过` |
| AC-P4-06 | 默认行为不变 | ✅ | `required=1` 即时终审、存量行默认 1；173 条定向回归通过 |
| AC-P4-07 | 无回归 | ✅ | 上述测试/E2E 全绿；修复 P3 遗留 DDL 契约测试 |

### 15.8 边界与遗留

1. **未强制不同审核人**：DPS 无分级角色模型，P4 仅留痕；按角色路由审核任务需 IAM 配套，另立需求。
2. **审核超时/催办/转交**未实现，需任务调度与通知通道。
3. **存量 `pending` 行不追溯补审**：按 `required=1` 单级收口，避免改变既有语义。
4. **测试环境提示**：Playwright trace + DPS 大响应会触发前端 8s 超时，回归命令建议附 `--trace=off`（非功能缺陷，已在本章记录）。


