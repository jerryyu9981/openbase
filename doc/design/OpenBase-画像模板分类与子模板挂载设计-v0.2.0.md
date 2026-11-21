# OpenBase 画像模板分类与子模板挂载设计

- 文档编号：OB-DESIGN-PORTRAIT-CATALOG-001
- 版本：v0.2.3
- 状态：[Approved]
- 适用环境：Dev / Test / Pro
- 作者：AI 编码代理
- 评审：产品/业务负责人、DPS 技术负责人、前端负责人
- 日期：2026-11-18

## 修订历史

| 版本 | 日期 | 变更摘要 | 作者 |
|---|---|---|---|
| v0.1.0 | 2026-11-18 | 首版：需求 1-6 建模、5 项决策、分类树与子模板挂载、数据模型、接口、引擎、前端、迁移与验收 | AI 编码代理 |
| v0.2.0 | 2026-11-19 | 评审通过转 [Approved]；补 §18 实施记录：P1-P5 落地证据、迁移实测结果、走查结论与遗留项 | AI 编码代理 |
| v0.2.1 | 2026-11-19 | 存量三项红灯治理完成（依赖声明判据、4 处圈复杂度拆分、profile 冻结列回填），补 §18.5 | AI 编码代理 |
| v0.2.2 | 2026-11-19 | 分类树完整性核查通过；按裁决将 `dps-correction-v1` 模板族（1 复合 + 6 子模板）迁至 `correction-business`，业务分支不再为空 | AI 编码代理 |
| v0.2.3 | 2026-11-21 | P4 前端收口：编辑页分类/类型与子模板挂载面板、标签绑定标注模板中文名提交入库；补 §18.6 验证记录 | AI 编码代理 |

---

## 1. 背景与目标

### 1.1 需求来源

| 编号 | 需求描述 | 本设计对应章节 |
|---|---|---|
| R1 | 社区矫正对象全景画像属人物画像；矫正业务画像属业务画像；二者同属数字画像总类 | §5 分类树 |
| R2 | 全景画像基础模板的六维标签体系（基础属性、行为特征、心理评估、社会关系、矫正表现、风险等级）实为六个子模板 | §5.2 复合模板与子模板 |
| R3 | 画像模板体系可选择挂载哪些子模板，且可动态维护调整 | §5.3 挂载关系、§8 引擎 |
| R4 | 所有标签项和模板都可以分类归集 | §5.1 分类、§7 数据模型 |
| R5 | 标注引擎以单模板或模板类为基础进行标注 | §8.3 标注范围 |
| R6 | 前端标签、模板、字段等能用中文名的地方默认用中文名 | §10.2 中文名规范 |

### 1.2 设计目标

1. 建立“数字画像 → 人物画像/业务画像 → 具体画像”的三级模板分类树。
2. 将六维从模板内的 `dimension_config` 升级为可复用、可独立维护的子模板。
3. 支持复合模板动态挂载/卸载子模板，并对挂载变更做版本固化。
4. 标签项与模板均可分类归集、可检索。
5. 标注引擎支持“单模板”与“模板类”两种发起范围。
6. 全链路默认展示中文名，编码退居次要位置。

### 1.3 非目标

- 不改造现有打分算法与评分白名单（`ScoringDispatcher` 仍是唯一裁决者）。
- 不引入可视化规则 DSL 编译器。
- 不做数据源接入、标签加工调度。
- 不改变画像实例的既有编码与历史数据标识。

---

## 2. 决策记录

| 编号 | 决策 | 结论 | 影响 |
|---|---|---|---|
| D1 | 子模板复用 | 允许一个子模板被多个复合模板挂载 | 挂载关系必须是多对多 |
| D2 | 版本语义 | 子模板独立版本；复合模板版本快照记录“子模板 code + 版本” | 挂载变更必须升父模板版本 |
| D3 | 模板类标注范围 | 分类下全部模板；可选“仅已挂载子模板”过滤 | 标注范围解析需支持分类继承 |
| D4 | 分类树深度 | 固定最大 3 层 | 建树与移动时强校验 |
| D5 | 中文名与编码 | 中文名必填；code 可手填，创建后不可修改 | 新增与编辑表单校验 |

以上决策为本次设计基线，实施阶段不再重复确认。

---

## 3. 术语

| 术语 | 定义 |
|---|---|
| 模板分类 | 画像模板的目录节点，三级：数字画像 / 人物画像或业务画像 / 具体画像 |
| 复合模板 | 由若干子模板挂载组成的画像模板，如“社区矫正对象全景画像” |
| 子模板 | 可独立维护、可被多个复合模板复用的模板单元，如“基础属性” |
| 挂载 | 复合模板与子模板之间的多对多组合关系，含顺序、必挂、权重覆盖 |
| 模板类 | 模板分类树上的一个节点，代表一类模板集合 |
| 标注范围 | 一次标注任务覆盖的对象，取值为单模板或模板类 |
| 标签项 | 标签分类下的标签值，以及标注产出的标签条目 |

---

## 4. 现状与差距

| 能力 | 现状 | 目标 | 差距 |
|---|---|---|---|
| 模板分类 | 模板无分类字段 | 三级分类树 | 新增分类表与模板外键 |
| 六维 | `dimension_config.dimensions` 配置块 | 六个子模板 | 需拆分与回填 |
| 模板组合 | 仅有 `extends` 单继承 | 多对多挂载 | `extends` 不能复用，需新表 |
| 挂载调整 | 无 | 动态增删、排序、权重覆盖 | 新增接口与页面 |
| 模板分类检索 | 无 | 按分类树筛选 | 列表查询改造 |
| 标签分类 | 平铺 | 支持父子层级 | `tag_category` 增加层级字段 |
| 标注范围 | 标注模板强归属一个画像模板 | 单模板 / 模板类 | 任务模型与解析器改造 |
| 中文名 | 已部分实现名称主显、编码次显 | 全链路默认中文名 | 字段/标签补 `label` 并校验 |

现状关键约束：

- `extends` 表示继承（字段与规则向下复制），与“挂载”语义不同，二者不得混用。
- 标签分类当前为内存实现（TD-3044），层级字段需随持久化一并落地。
- 标注模板当前通过 `template_code` 强归属一个画像模板，不能直接表达模板类。

---

## 5. 目标模型

### 5.1 分类树

```
数字画像（L1，总类）
├─ 人物画像（L2）
│   └─ 社区矫正对象全景画像（L3，复合模板）
└─ 业务画像（L2）
    └─ 矫正业务画像（L3，复合模板）
```

约束：

- 最大 3 层，L1 唯一根节点“数字画像”。
- 同父节点下名称唯一，code 全局唯一。
- 模板必须绑定一个 L3 分类；L1/L2 仅作目录，不直接绑定模板。
- 分类移动时同步重算子节点 `path` 与 `level`，禁止形成环。

### 5.2 复合模板与子模板

```
社区矫正对象全景画像（composite，v1.0.0）
├─ 基础属性（component，v1.0.0，weight=0.15）
├─ 行为特征（component，v1.0.0，weight=0.20）
├─ 心理评估（component，v1.0.0，weight=0.20）
├─ 社会关系（component，v1.0.0，weight=0.15）
├─ 矫正表现（component，v1.0.0，weight=0.15）
└─ 风险等级（component，v1.0.0，weight=0.15）
```

规则：

- 复合模板只能挂载 `template_kind=component` 的模板。
- 禁止自挂、禁止环，禁止 composite 嵌套 composite（避免深层树）。
- 同一子模板可被多个复合模板挂载（D1）。
- 挂载顺序即画像维度的展示与计算顺序。
- `required=true` 的子模板不可直接卸载，需先改为非必挂。

### 5.3 版本与快照

- 子模板独立升版本；复合模板挂载关系变化时父模板升版本。
- 父模板版本记录 `component_snapshot`：`[{child_code, child_version, weight_override, sort_order}]`。
- 画像实例记录“父模板 code + 父模板版本”，历史实例按快照读取，不受后续挂载调整影响（D2）。

### 5.4 标签项与标注项归集

- 标签项通过 `tag_category` 树归集，标签值必须归属于一个分类。
- 标注项不单独建分类，通过其所属标注模板的模板分类间接归集。
- 如后续需要标注项独立分组，预留 `field_schema[].group`，本期不启用。

---

## 6. 角色与使用场景

| 角色 | 场景 |
|---|---|
| 业务管理员 | 维护分类树、创建子模板、调整挂载与权重 |
| 标注管理员 | 选择单模板或模板类发起标注，查看范围预检结果 |
| 业务用户 | 在画像详情查看“中文名 + 编码”的维度与标签 |
| 审计人员 | 追溯挂载变更、版本快照与标注范围 |

---

## 7. 数据模型设计

### 7.1 关系概览

```
portrait_template_category 1 ── N portrait_template
portrait_template(parent) 1 ── N portrait_template_component N ── 1 portrait_template(child)
portrait_template 1 ── N portrait_template_version
tag_category(parent) 1 ── N tag_category(child)
tag_category 1 ── N tag_value
annotation_scope N ── 1 portrait_template_category（模板类时）
```

### 7.2 新增表：`portrait_template_category`

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | 主键 |
| code | VARCHAR(64) | UNIQUE, NOT NULL | 分类编码，创建后不可改 |
| name | VARCHAR(128) | NOT NULL | 中文名 |
| parent_id | BIGINT | FK, NULL | 根节点为空 |
| path | VARCHAR(512) | NOT NULL | 物化路径，如 `/digital/person/fullview` |
| level | SMALLINT | CHECK 1..3 | 层级 |
| sort_order | INT | NOT NULL DEFAULT 0 | 同级排序 |
| status | VARCHAR(16) | NOT NULL DEFAULT 'active' | active/disabled |
| org_id / tenant_id | VARCHAR(64) | NULL | 多租户隔离 |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL | 审计时间 |

索引：`(parent_id, sort_order)`、`(path)`、`(org_id, tenant_id)`。

### 7.3 扩展表：`portrait_template`

| 新增字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| category_id | BIGINT | FK, NOT NULL（迁移后） | 绑定 L3 分类 |
| template_kind | VARCHAR(16) | NOT NULL DEFAULT 'composite' | composite / component |
| name_source | VARCHAR(16) | NOT NULL DEFAULT 'manual' | manual / fallback（迁移回填标记） |

`code` 保持全局唯一且不可修改（D5）。

### 7.4 新增表：`portrait_template_component`

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | 主键 |
| parent_code | VARCHAR(64) | FK, NOT NULL | 复合模板 code |
| child_code | VARCHAR(64) | FK, NOT NULL | 子模板 code |
| sort_order | INT | NOT NULL DEFAULT 0 | 挂载顺序 |
| required | BOOLEAN | NOT NULL DEFAULT TRUE | 是否必挂 |
| weight_override | NUMERIC(6,4) | NULL | 覆盖子模板权重 |
| status | VARCHAR(16) | NOT NULL DEFAULT 'active' | active/disabled |
| org_id / tenant_id | VARCHAR(64) | NULL | 多租户隔离 |
| created_at | TIMESTAMPTZ | NOT NULL | 审计时间 |

唯一键：`(parent_code, child_code)`。
索引：`(parent_code, sort_order)`、`(child_code)`。

### 7.5 扩展表：`portrait_template_version`

新增 `component_snapshot JSONB`，结构：

```json
[
  {"child_code": "risk__basic", "child_version": 3, "weight_override": 0.15, "sort_order": 1},
  {"child_code": "risk__behavior", "child_version": 2, "weight_override": 0.20, "sort_order": 2}
]
```

### 7.6 扩展表：`tag_category`

新增：

| 字段 | 类型 | 约束 |
|---|---|---|
| parent_id | BIGINT | FK, NULL |
| path | VARCHAR(512) | NOT NULL |
| level | SMALLINT | CHECK 1..3 |

说明：当前为内存实现，本次随分类树一并落库；若暂不持久化，接口与校验仍按本结构提供，但需在发布说明中标注“重启丢失”。

### 7.7 标注范围

在标注任务/批次表增加：

| 字段 | 类型 | 说明 |
|---|---|---|
| scope_type | VARCHAR(16) | template / category |
| scope_code | VARCHAR(64) | 模板 code 或分类 code |
| scope_filter | JSONB | 可选，如 `{"only_mounted": true}` |

若现有任务表不宜扩展，则新增独立表 `annotation_scope`，由任务引用其 id。

### 7.8 数据约束

1. 分类最大 3 层；L3 才允许绑定模板。
2. `template_kind=component` 不得作为 `parent_code`。
3. 挂载不得自引用、不得成环。
4. 挂载变更必须写入新版本并记录快照。
5. 名称必填；同一父分类下模板名称唯一。
6. 所有查询带 `org_id/tenant_id` 过滤。

---

## 8. 迁移与回填

### 8.1 迁移步骤

1. 创建 `portrait_template_category`，写入根节点与 L2、L3 示例节点。
2. `portrait_template` 增加 `category_id`、`template_kind`、`name_source`，默认 `composite`。
3. 为每个现有模板的每个维度生成子模板：
   - `code = <parent_code>__<dimension_code>`
   - `name = dimension.name`（缺失时回退 dimension code，并标记 `name_source=fallback`）
   - `template_kind=component`
   - `category_id` 继承父模板分类
4. 写入 `portrait_template_component`，`weight_override` 取原维度权重，`sort_order` 取原维度顺序。
5. 现有模板版本补写 `component_snapshot`。
6. 标签分类补 `parent_id/path/level`，默认挂在“未分类”根下。
7. 标注模板字段补 `label`：有中文名则保留；无则回退 `key` 并标记待完善。

### 8.2 幂等与回滚

- 所有 DDL 使用 `IF NOT EXISTS`，数据回填使用 `WHERE NOT EXISTS`。
- 迁移脚本带 `migration_id`，重复执行不产生重复子模板。
- 回滚保留 `dimension_config` 原值，评分引擎可一键回退旧路径。

### 8.3 存量兼容

- 保留 `dimension_config` 至少一个发布周期，评分优先读挂载关系，空挂载时回退 `dimension_config`。
- `extends` 语义不变，仅用于继承；不得用挂载替代继承。
- 所有 `code` 不变，画像实例与历史数据无需重写。

---

## 9. 引擎设计

### 9.1 模板引擎

新增能力：

- `create_category / update_category / move_category / tree`
- `mount_component / unmount_component / reorder_components`
- `resolve_components(parent_code)`

校验顺序：

1. 父模板存在且 `template_kind=composite`。
2. 子模板存在且 `template_kind=component`。
3. 非自引用、非环、非重复挂载。
4. 必挂项不可直接卸载。
5. 变更后父模板版本 +1，写快照。

### 9.2 评分引擎

```
resolve_components(parent_code, version)
  → 按 sort_order 遍历子模板
  → 每个子模板执行自身标签绑定与规则
  → 按 weight_override（缺省用子模板权重）汇总
  → 无挂载时回退 dimension_config
```

要求：

- 同一子模板被多个父模板挂载时，按各自 `weight_override` 独立计算，互不影响。
- 快照版本与实时挂载不一致时，以实例绑定的版本快照为准。

### 9.3 标注引擎

- `scope_type=template`：沿用现有单模板标注。
- `scope_type=category`：解析该分类及其子分类下的全部模板；可选 `only_mounted` 过滤。
- 发起前预检：返回模板数、字段数、预计任务数；超过阈值（默认 50 个模板或 500 个字段）需二次确认。
- 标注产出仍写入标签条目，`target_dimension` 校验规则保持不变（见已交付的维度映射校验）。

---

## 10. 接口设计

### 10.1 分类与挂载

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/dps-proxy/portrait/template-categories/tree` | 分类树 |
| POST | `/api/v1/dps-proxy/portrait/template-categories` | 新建分类 |
| PUT | `/api/v1/dps-proxy/portrait/template-categories/{id}` | 编辑分类 |
| POST | `/api/v1/dps-proxy/portrait/template-categories/{id}/move` | 移动分类 |
| GET | `/api/v1/dps-proxy/portrait/templates/{code}/components` | 挂载清单 |
| POST | `/api/v1/dps-proxy/portrait/templates/{code}/components` | 挂载子模板 |
| DELETE | `/api/v1/dps-proxy/portrait/templates/{code}/components/{child}` | 卸载 |
| PUT | `/api/v1/dps-proxy/portrait/templates/{code}/components/order` | 排序 |

挂载请求示例：

```json
{
  "child_code": "risk__psychology",
  "sort_order": 3,
  "required": true,
  "weight_override": 0.2
}
```

错误码：

| 场景 | HTTP | message |
|---|---|---|
| 分类超过 3 层 | 400 | 分类层级不得超过 3 层 |
| 挂载 composite | 400 | 仅允许挂载子模板（component） |
| 循环挂载 | 400 | 检测到循环挂载 |
| 卸载必挂项 | 409 | 必挂子模板需先取消必挂 |
| code 重复 | 409 | 模板编码已存在 |

### 10.2 模板与标注范围

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/dps-proxy/portrait/templates?category_code=&kind=` | 按分类/类型筛选 |
| GET | `/api/v1/dps-proxy/portrait/annotation-scopes/resolve?type=category&code=` | 解析标注范围与预检统计 |

### 10.3 中文名契约

- 所有列表、详情、选择器接口必须返回 `name`（模板/分类）或 `label`（字段/标签值）。
- 前端主显 `name/label`，编码以次要样式展示。
- 缺少中文名时返回 `name_source=fallback`，前端展示“待补充中文名”标记。

---

## 11. 前端设计

### 11.1 页面改动

| 页面 | 改动 |
|---|---|
| 模板族管理 `DpsTemplateListView.vue` | 左侧分类树；右侧列表按分类筛选；显示模板类型与中文名 |
| 模板编辑 `DpsTemplateEditView.vue` | 新增“子模板挂载”页签：穿梭选择、拖拽排序、必挂开关、权重覆盖 |
| 标注模板 `DpsAnnotationTemplateView.vue` | 标注范围选择“单模板 / 模板类”；范围预检结果展示 |
| 标注工作台 `DpsAnnotationWorkbenchView.vue` | 模板下拉按分类分组，主显中文名 |
| 字段管理 `DpsAnnotationFieldView.vue` | 新增字段中文名，必填校验 |
| 标签管理 `Tags.vue` | 分类树、标签值中文名 |
| 关系视图 `RelationView.vue` | 升级为五层：分类 → 复合模板 → 子模板 → 标注项 → 画像实例 |

### 11.2 中文名规范（R6）

1. 名称优先：模板、分类、字段、标签值、维度一律主显中文名。
2. 编码次显：编码使用小号灰色文字或副标题，复用 `NameCodeLabel` 组件。
3. 必填校验：新建/编辑时中文名必填，缺失则禁止保存。
4. 回退策略：历史数据缺名时显示编码，并加“待补充中文名”标记。
5. 检索：搜索同时匹配中文名与编码。
6. 禁止前端自行拼接名称：展示值一律由接口 `name/label` 提供。

---

## 12. 非功能设计

| 维度 | 要求 |
|---|---|
| 性能 | 分类树接口 P95 ≤ 100ms；挂载清单 ≤ 50ms；范围解析 ≤ 300ms |
| 一致性 | 挂载变更与版本快照同一事务提交 |
| 审计 | 分类移动、挂载/卸载、权重调整写审计日志 |
| 权限 | 分类与挂载仅管理员可写；普通用户只读 |
| 多租户 | 分类、模板、挂载关系均按 `org_id/tenant_id` 隔离 |
| 可用性 | 分类树不可用时模板列表仍可按平铺模式展示 |

---

## 13. 验收标准

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| A1 | 分类树 | 可创建三级分类；第 4 级被拒绝；移动后 path/level 正确 |
| A2 | 子模板 | 六个维度各生成一个子模板，可独立编辑与升版本 |
| A3 | 挂载 | 全景画像可挂载 6 个子模板，顺序与权重可调整并持久化 |
| A4 | 复用 | 同一子模板可被第二个复合模板挂载，互不影响 |
| A5 | 版本 | 挂载变更后父模板版本 +1，快照含子模板版本 |
| A6 | 历史兼容 | 旧画像实例在挂载变更后仍按原快照展示 |
| A7 | 模板类标注 | 选择“人物画像”可解析出该分类下全部模板并给出预检统计 |
| A8 | 中文名 | 列表/选择器/关系视图均主显中文名；缺名有标记 |
| A9 | 回归 | 存量模板改造前后画像得分逐项一致 |
| A10 | 校验 | 挂载 composite、循环挂载、卸载必挂项均被正确拒绝 |

---

## 14. 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| 挂载与继承混淆 | 模型语义混乱 | UI/文档明确区分；接口分路径 |
| 挂载变更影响历史画像 | 结果漂移 | 版本快照 + 实例绑定版本 |
| 循环挂载 | 计算死循环 | 保存时 DFS 环检测 |
| 存量六维拆分不一致 | 得分偏差 | 迁移后逐模板对比得分 |
| 标签分类仍在内存 | 重启丢失层级 | 本次同步落库；否则发布说明标注 |
| 模板类标注范围过大 | 任务量激增 | 预检 + 阈值二次确认 |
| 中文名缺失 | 展示回退编码 | `name_source` 标记 + 待完善清单 |

---

## 15. 实施计划

| 阶段 | 内容 | 交付物 | 门禁 |
|---|---|---|---|
| P0 | 设计评审 | 本文档 | 评审通过 |
| P1 | 数据模型与迁移 | DDL、迁移脚本、回填报告、单测 | 幂等与回滚验证通过 |
| P2 | 模板引擎 | 分类树、挂载校验、版本快照、单测 | 环/深度/必挂用例通过 |
| P3 | 接口 | 分类、挂载、范围解析接口与契约测试 | 接口契约评审通过 |
| P4 | 前端 | 分类树、挂载面板、模板类标注、中文名规范 | `vue-tsc` + 浏览器走查通过 |
| P5 | 回归与切换 | 存量得分对比、关系视图五层、发布说明 | A1-A10 全部通过 |

---

## 16. 评审确认项

以下为实施默认口径，如无异议按此执行：

1. 复合模板不允许再挂载复合模板，仅允许 composite → component。
2. 标签分类树同样限制 3 层。
3. 模板类标注预检阈值默认 50 个模板 / 500 个字段，可配置。
4. 分类与挂载写权限仅限管理员角色。
5. 历史缺中文名的数据允许先以编码展示，后续批量补名。

---

## 17. 附录：需求追溯

| 需求 | 设计章节 | 验收项 |
|---|---|---|
| R1 分类归属 | §5.1 | A1 |
| R2 六维即子模板 | §5.2、§8.1 | A2 |
| R3 动态挂载 | §5.3、§9.1、§10.1 | A3、A5 |
| R4 标签与模板分类 | §5.4、§7.2、§7.6 | A1、A8 |
| R5 单模板/模板类标注 | §9.3、§10.2 | A7 |
| R6 中文名优先 | §10.3、§11.2 | A8 |

---

## 18. 实施记录（v0.2.0，2026-11-19）

### 18.1 落地清单

| 阶段 | 交付物 | 位置 |
|---|---|---|
| P1 | 新表/新列 DDL 与存量幂等演进 | `DPS/src/ddl/schema_portrait.py`、`DPS/src/database.py` |
| P1 | 迁移脚本（播种分类、拆子模板、建立挂载） | `DPS/scripts/migrate_template_catalog_v1.py` |
| P2 | 分类树与挂载引擎（3 层限制、环检测、必挂、快照） | `DPS/src/engines/template_catalog_engine.py` |
| P3 | 分类/挂载/标注范围接口 | `DPS/src/rest_api/routes/routes_template_catalog.py` |
| P3 | 模板字段持久化（category_id/template_kind/name_source） | `DPS/src/engines/template_engine.py` |
| P4 | 列表页分类/类型筛选与分类管理弹窗 | `openbase-ui/.../DpsTemplateListView.vue` |
| P4 | 编辑页分类与子模板挂载面板 | `openbase-ui/.../DpsTemplateEditView.vue`（RAW 编辑器，工作台「高级 JSON 编辑」可达） |
| P4 | 标注模板页「标注范围预检」 | `openbase-ui/.../DpsAnnotationTemplateView.vue` |
| P4 | OpenBase dps-proxy 新增 10 条代理路由 | `openbase/modules/dps_proxy/__init__.py` |
| P5 | 关系视图升级为五层 | `openbase-ui/.../RelationView.vue` |
| P2 | 单测（分类 3 层、挂载复用、必挂、排序与版本回放） | `DPS/src/tests/test_template_catalog_v1.py` |

### 18.2 迁移实测（共享 PG `platform` schema）

| 项 | 结果 |
|---|---|
| 分类播种 | 5 个（digital-profile / person-profile / business-profile / fullview-persona / correction-business） |
| 子模板生成 | 31 个（6 个复合模板 × 5~6 维 + 冒烟模板） |
| 挂载关系 | 31 条，`required=true`，权重取原维度权重 |
| 父模板版本 | 每次挂载 +1（`cor-persona-root-v1` / `dps-correction-v1` 升至 v7，`wb-smoke-v1` 升至 v2） |
| 幂等复跑 | 第二次 `--apply`：新增 0、挂载 0、跳过全部，确认幂等 |

### 18.3 走查与验证

| 项 | 结论 |
|---|---|
| DPS 目标单测 | `test_template_catalog_v1` / `test_template_engine_v2_10` / `test_v2_11_ddl_portrait` 等 87 passed |
| DPS 全量回归（v0.2.1） | 2111 passed / 3 skipped / 1 xfailed / 1 xpassed / 0 failed（22m37s） |
| 前端类型检查 | `vue-tsc --noEmit` exit 0 |
| 分类管理弹窗 | PASS：树显示 5 个分类（中文名 + 编码） |
| 分类/类型列与筛选 | PASS：列表 37 行，复合/子模板标识正确 |
| 编辑页挂载面板 | PASS：`cor-persona-root-v1` 显示 6 个子模板、权重、必挂、上移/下移/卸载 |
| 标注范围预检 | PASS：模板类 `fullview-persona` 命中 37 模板 / 8 标注模板 / 180 字段 |
| 关系视图五层 | PASS：5 分类 / 6 复合 / 31 子模板 / 180 标注项 / 18 画像实例 |
| 服务编排 | 8 个服务健康 ✅，前端 5173 可访问 |

### 18.4 遗留项与说明

1. **工作台未内置挂载面板**：主编辑页已切换为 `DpsTemplateWorkbenchView`，分类与挂载面板位于其「高级 JSON 编辑」（`/portrait/dps/templates/:code/raw`）。若要求工作台首屏可见，需单独立项。
2. **分类归属规则**：迁移脚本按模板名称/编码包含「业务/business」判定 `correction-business`，存量模板均未命中，首轮全部归入 `fullview-persona`；v0.2.2 已按裁决将 `dps-correction-v1` 及其 6 个子模板迁至 `correction-business`（L3 分布：全景画像 30 / 矫正业务 7），`wb-smoke-v1` 冒烟模板仍留在全景画像。
3. **版本噪声**：逐条挂载导致父模板版本 v1→v7；如需合并为一次变更，可增加批量挂载接口（未纳入本期）。
4. **存量测试红灯（v0.2.1 已全部治理，见 §18.5）**：原 3 个失败用例均为本次改动前既有问题，已按「不改语义、只拆结构」原则修复。

### 18.5 存量测试红灯治理（v0.2.1）

| 用例 | 根因 | 处置 |
|---|---|---|
| `test_v2_11_ci_hardening.py` | 依赖声明判据只扫描 `src/`，`scripts/p1_recompute_profiles.py` 被误判为未声明的第三方包 | `_project_modules()` 纳入 `scripts/**/*.py` 脚本名，判据语义不变 |
| `test_v2_11_complexity_guard.py` | 4 个函数圈复杂度 >15（均为历史代码） | 按职责拆分，不改变任何行为与错误文案：`conditions._evaluate_leaf` → 存在性/匹配/数值/日期 4 个子函数；`annotation_template_engine.validate_field_schema` → key/type、标签契约、tag_key、score_map、score_direction 5 个私有方法；`template_preview_validation._validate_rule_params` → 映射/布尔/区间/比率 4 个校验方法；`routes_profiles._persist_portrait_update` → SET 组装、版本冲突裁决、attributes 读回 3 个模块级函数 |
| `test_v2_11_ddl_root.py` | `portrait_profile.external_id` 为 R9 有意新增列，冻结基线未同步 | 冻结列集按实际顺序回填 `external_id` 并注明来源 |

回归结果：三个守则文件 81 passed；相关业务回归（模板试算、标注链路、画像更新、模板族、RBAC）125 passed；全量测试见 §18.3 更新。

### 18.6 P4 前端收口（v0.2.3，2026-11-21）

| 项 | 内容 |
|---|---|
| 变更文件 | `openbase-ui/src/modules/portrait/pages/DpsTemplateEditView.vue`、`openbase-ui/src/modules/portrait/templates/TagBindingTable.vue`、`openbase-ui/package.json`（1.9.2） |
| 能力 | 编辑页新增「分类与子模板挂载」卡片（分类选择、复合/子模板类型、挂载/卸载、上移/下移、必挂与权重覆盖）；标签绑定表的标注模板下拉改为 `NameCodeLabel` 中文名主显 |
| 依赖确认 | 所调用的 `listTemplateCategories` / `listTemplateComponents` / `mountTemplateComponent` / `unmountTemplateComponent` / `reorderTemplateComponents` 及 `DpsTemplateCategory` / `DpsTemplateComponent` 类型均已在 `core/api/dps.ts` 中，代理路由已由 `openbase/modules/dps_proxy/__init__.py` 提供 |
| 验证 | `npm run build`（`vue-tsc --noEmit` + `vite build`）通过；相关前端回归 6 个 spec **22 passed**（portrait-lifecycle / concept-nav / list-stale / deactivate-impact / template-filter-v180 / template-health） |
| 范围说明 | 同工作区的 OpenLLM 模块改动（`llm.ts`、`Playground.vue`）与本任务无关，未纳入本次提交 |
