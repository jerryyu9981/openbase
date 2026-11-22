# OpenBase 画像 P0 前置评估报告（人物画像与业务进度画像）

| 项 | 内容 |
|---|---|
| 文档编号 | OB-ASSESS-PORTRAIT-P0 |
| 版本 | v1.1.0 |
| 状态 | [Review] |
| 评估对象 | 《OpenBase-画像命名与数据链路一体化升级方案 v1.1.0》中的 P0 项 |
| 评估范围 | DPS 后端（数据/接口/任务/上游）、openbase-ui 画像模块 |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-22 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-22 | 首次编制：主体泛化与 PII 分级的现状盘点、方案对比、影响面、风险与实施建议 | AI 编码代理 |
| v1.1.0 | 2026-11-22 | 范围确认为「人物画像 + 业务进度画像」两类：主体泛化移出 P0；新增业务进度模型、组织数据权限、审计评估；PII 升级为最高优先 | AI 编码代理 |

## 1. 评估目的

目标系统并行建设两类画像：**① 人物画像**（基础属性、能力、履职、风险）；**② 政府组织业务人物的完成进度与情况画像**。两者主体均为 person，不做设备/内容/企业多主体。

据此，v1.1.0 的 P0 为四项：

1. **政务 PII 分级**（最高优先）：字段分级、读路径脱敏、字段级权限、保留与删除。
2. **组织数据权限**：组织树与 `data_scope`，决定谁能看谁。
3. **业务进度模型**：`business_item`、`progress_snapshot`、`profile_snapshot` 与周期计算。
4. **审计留痕**：读取、导出、删除、权限变更全审计。

主体泛化不再进入 P0，作为 P2 预案保留评估数据。本报告回答：现状差距、方案选择、影响面与实施顺序。

## 2. 评估方法

- 代码扫描：DPS `src/`、DDL、openbase-ui `src/` 的 `person_id` / `subject_type` / 脱敏相关实现。
- 数据流核对：引入 → profile → annotation → 标签 → 画像计算 → API/MCP/前端。
- 判定标准：兼容性、改造面、风险、可回滚性、合规必要性。

## 3. 结论摘要

| 事项 | 结论 | 建议 |
|---|---|---|
| 主体泛化 | 两类画像主体均为 person，**不再是 P0**；耦合数据仅作 P2 预案依据 | 本期不实施，仅保留模板 `subject_type` 兼容位 |
| PII 分级 | 现状只有「密钥/IP 脱敏」，**无字段级分级与读路径脱敏**；API 已直接返回完整 `attributes_json` | 列为**最高优先 P0**：分级清单 + 读路径脱敏 + 字段级权限 + 审计 |
| 是否阻塞 v1 | 人物画像可先行；业务进度画像需先补进度模型 | PII 与组织权限先行，进度模型与第二类画像同步 |
| 优先级 | 政务 PII > 组织权限 > 业务进度模型 > 审计 | 主体泛化移至 P2 |

## 4. 主体泛化评估（P2 预案）

> **范围说明（v1.1.0）**：目标为「人物画像 + 业务进度画像」两类，主体均为 person，因此主体泛化不再进入 P0。本节保留耦合数据，用于说明为何不做全量泛化，以及未来若扩展企业/设备主体时的改造成本。

### 4.1 现状耦合盘点

| 层 | 现状 | 耦合量 |
|---|---|---|
| 数据表 | `profile.person_id`，唯一约束 `UNIQUE(person_id, tenant_id)`；`annotation.profile_id` 外键；标签/任务表均按 person 关联 | DDL 命中 19 处 / 4 个文件 |
| 模板 | **`portrait_template.subject_type` 已存在**（默认 `person`，含 `profile_type`） | 已具备，未被 profile/接口使用 |
| 接口 | `/portrait/{person_id}/...`、`/portrait/calculate`、列表/详情/标注/标签/任务均以 person_id 为键 | `routes_profiles.py` 单文件 213 处 |
| 上游 | OpenLLM `dps_client` 以 `PUT /portrait/{person_id}` 回写；身份事件域已有 `subject_type=user/agent` 概念 | 可复用命名，需加默认值 |
| 前端 | 列表、详情、搜索、关系视图、度量、标注工作台、`dps.ts` 类型 | 171 处 / 9 个文件 |
| 任务 | `portrait_calc_task`、标注任务、引入/同步任务均按 person 建键 | 需加主体维度 |

**关键发现**：模板层已经预留 `subject_type`，说明「多主体」在模板设计上被预期；当前瓶颈集中在 profile 主表、任务表、接口路径与前端假设，而不是整个系统都要重写。

### 4.2 方案对比

| 方案 | 做法 | 兼容性 | 改造量 | 风险 | 结论 |
|---|---|---|---|---|---|
| A. 重命名 `person_id → subject_id` | 全栈一次性改字段/路径/类型 | 低（破坏旧接口与上游） | 极大（700+ 处） | 高 | 不推荐 |
| B. **加列 + 回填 + 双读**（推荐） | `profile` 加 `subject_type`（默认 person）、`subject_id`（回填 person_id）；唯一约束改三元组；旧 `person_id` 保留 | 高（旧接口不变） | 中 | 中 | **推荐** |
| C. 按主体分表 | `person_profile` / `org_profile` / `device_profile` | 低 | 极大 | 高 | 长期可选，本期不做 |

### 4.3 推荐方案要点（B）

**DDL**

```sql
ALTER TABLE profile ADD COLUMN IF NOT EXISTS subject_type VARCHAR(24) NOT NULL DEFAULT 'person';
ALTER TABLE profile ADD COLUMN IF NOT EXISTS subject_id VARCHAR(100);
UPDATE profile SET subject_id = person_id WHERE subject_id IS NULL;
-- 新唯一约束（旧约束保留一个灰度周期）
CREATE UNIQUE INDEX IF NOT EXISTS uq_profile_subject
  ON profile (tenant_id, subject_type, subject_id);
```

**任务与管线**

- `portrait_calc_task`、`annotation_task`、`ingest_task` 增加 `subject_type`，键改为 `(tenant_id, subject_type, subject_id, template_code)`。
- `ingest_pipeline` 映射增加 `subject_type`（默认 person）；标注模板绑定 `subject_type`。
- 去抖/幂等键同步升级，旧键在灰度期兼容。

**接口**

- 请求体/查询参数增加可选 `subject_type`（默认 `person`）；路径仍接受 person_id。
- 响应保留 `person_id`（当 `subject_type=person` 时等于 `subject_id`），新增 `subject_type/subject_id` 字段。
- 新增主体类型枚举接口（来源：模板 `subject_type` 去重 + 系统枚举）。

**前端**

- 画像列表/详情增加「画像类型」切换（person/org/device/content），路由 query 携带 `subject_type`。
- `dps.ts` 类型增加 `subject_type/subject_id`；展示层对非 person 主体使用「主体名称」而非「姓名」文案。

**上游**

- OpenLLM 回写 payload 增加 `subject_type`（默认 person），旧版本缺省即 person，向后兼容。
- 身份事件沿用现有 `subject_type` 命名，避免两套词汇。

### 4.4 影响面与工作量分级

| 工作项 | 级别 | 说明 |
|---|---|---|
| DDL + 回填 + 索引 | M | PG/SQLite 双形态、幂等、在线建索引 |
| 读写层适配 | L | 531+ 处 `person_id` 需逐处判断：保留/兼容/改键 |
| 接口兼容 | M | 参数、响应、错误码、文档同步 |
| 前端改造 | M | 171 处 / 9 文件 + 类型切换 |
| 上游回写 | S | 加默认字段 |
| 测试 | L | 多主体 CRUD、唯一性、导入、标注、计算、旧接口回归 |

### 4.5 风险与回滚

| 风险 | 处置 |
|---|---|
| 唯一约束切换期冲突 | 先建新索引再切读写；保留旧约束一个灰度周期 |
| 回填不完整 | 回填脚本幂等 + 校验 SQL（`subject_id IS NULL` 计数为 0） |
| 双写期数据不一致 | 以 `subject_id` 为写准，`person_id` 作为兼容列由触发器/应用层同步 |
| 旧客户端/上游不兼容 | 默认 subject_type=person；路径与响应字段保持 |
| 回滚 | 保留 `person_id` 与旧约束；关闭新键读写开关即回退 |

### 4.6 验收标准

1. 同一 tenant 下 `(subject_type, subject_id)` 唯一，跨类型可同 ID。
2. 旧接口（仅传 person_id）行为不变。
3. 企业/设备主体可完成：引入 → 标注 → 计算 → 列表/详情查询。
4. 模板 `subject_type` 与 profile 主体类型不一致时拒绝计算并给出明确错误。
5. 回填后 `subject_id IS NULL` 为 0。

## 5. P0-2 PII 分级评估

### 5.1 数据资产与 PII 分布

| 资产 | 可能含有的 PII | 现状暴露 |
|---|---|---|
| `profile`（`name/external_id/person_id/attributes_json`） | 姓名、手机、证件、邮箱、地址、行为 | `/portrait/list` **已直接返回完整 `attributes_json` 与解析后的 `attributes`** |
| `annotation.content`（TEXT） | 自由文本中的个人信息 | 标注查询/详情原样返回 |
| 标签与评分 | 通常为派生数据 | 间接可推断敏感属性 |
| 导入原始文件 / 错误行 CSV（规划中） | 整行原始数据 | 尚未实现，设计需内置脱敏 |
| 日志 / 审计 | 请求体、异常上下文 | 目前路由未记录 payload；审计仅脱敏密钥与 IP |
| API / MCP | 画像详情、模板、标注 | 无字段级脱敏 |
| OpenLLM 回写 / 记忆 | 对话抽取的事实 | 跨系统复制，需最小必要 |

### 5.2 现有控制评估

| 已有 | 证据 |
|---|---|
| 审计日志敏感键脱敏（password/token/secret/api_key/authorization） | `audit_log_engine.py:L310-L324` |
| IP 掩码（末段 → xxx） | `audit_log_engine.py:L326-L333` |
| 数据库 DSN 脱敏 | `database.py:L28` |
| 身份审计声明不读请求体 | `identity/audit_identity.py:L11` |

**缺失**：字段级分级、读路径脱敏、导出脱敏、字段级权限、画像读取审计、保留期与删除权。

### 5.3 分级框架建议

| 级别 | 定义 | 示例 | 默认策略 |
|---|---|---|---|
| L1 公开 | 可对外 | 模板名称、标签分类 | 正常展示 |
| L2 内部 | 内部可见 | 画像评分、派生标签、任务状态 | 登录可见 |
| L3 敏感 | 需授权 | 姓名、手机、邮箱、地址、行为轨迹 | 掩码 + `dps:pii:view` 才可解密 |
| L4 高敏 | 严格管控 | 证件号、生物特征、精确位置、健康/金融 | 默认不返回；单独授权 + 审计 |

### 5.4 暴露面矩阵

| 暴露面 | 现状风险 | 目标控制 |
|---|---|---|
| 画像列表/详情 API | 高（完整 attributes） | 序列化器按字段级别脱敏；L4 默认剔除 |
| 标注查询/详情 | 高（自由文本） | 按标注模板字段分级；文本命中规则脱敏 |
| 导入错误 CSV | 中（规划中） | 强制脱敏 + 导出审计 + 水印 |
| 日志/异常 | 低（当前未记录 payload） | 白名单日志字段，禁止请求体 |
| MCP 工具 | 中 | 复用同一序列化与权限 |
| OpenLLM 回写/记忆 | 中 | 最小必要字段；跨系统同级别策略 |
| 备份/导出 | 中 | 加密、访问审计、保留期 |

### 5.5 方案要点

1. **分级元数据**：新增 `field_classification(entity_type, field_path, level, mask_rule, retention_days)`；模板字段与 `attributes_json` 路径均可登记。
2. **统一序列化脱敏**：读路径统一走 `PiiSerializer`，按 `mask_rule` 输出（手机 `138****1234`、证件 `110***********1234`、姓名 `张*`）。
3. **字段级权限**：新增 `dps:pii:view`（L3 明文）、`dps:pii:high`（L4），无权限返回掩码值而非报错。
4. **导出与错误行**：导出前强制脱敏；导出动作写审计（谁、何时、多少行、字段级别）。
5. **日志纪律**：结构化白名单；禁止 payload/attributes；异常只记录字段名与错误类型。
6. **保留与删除**：按级别设置保留期；提供「按主体删除」级联（profile/annotation/attributes/tags/任务快照），删除动作审计。
7. **跨系统**：OpenLLM 回写仅传必要字段，记忆侧沿用同一分级；`subject_type` 与 PII 策略联动。

### 5.6 合规与风险

- 依据最小必要、告知同意、可删除、可审计原则（PIPL 等）。
- 主要风险：历史 `attributes_json` 已含敏感字段且无分级；一旦开放导出/错误行会放大泄露面；跨系统回写可能绕过 DPS 脱敏。
- 处置：先盘清单（字段路径 → 级别），再改读路径，最后做导出与删除；回写侧同步评审。

### 5.7 验收标准

1. 画像与标注字段分级覆盖率 100%（含 `attributes_json` 路径）。
2. L3/L4 在 API、MCP、前端、导出中均按规则脱敏；无权限不可见明文。
3. 导出与删除操作 100% 有审计记录。
4. 日志与异常中不出现 PII 明文字段（静态扫描 + 用例）。
5. 按主体删除后，关联标注/标签/任务快照不可再检索。

## 6. 范围变更后的新增 P0 评估

### 6.1 范围确认

两类画像并行：① 人物画像（基础属性、能力、履职、风险）；② 政府组织业务人物的完成进度与情况画像。主体均为 person，不做设备/内容/企业主体，以模板族区分。

结论：

- 主体泛化移出 P0，`person_id` 保持现状，仅保留模板 `subject_type` 兼容位。
- 新增三项 P0：业务进度模型、组织数据权限、审计留痕；PII 升级为最高优先。

### 6.2 P0 重排

| 优先级 | 事项 | 关键交付 | 级别 |
|---|---|---|---|
| P0-1 | 政务 PII | 分级清单、读路径脱敏、字段级权限、导出/日志纪律 | M |
| P0-2 | 组织数据权限 | 组织树、`data_scope`、跨部门授权 | M |
| P0-3 | 业务进度模型 | `business_item`、`progress_snapshot`、`profile_snapshot` | L |
| P0-4 | 审计留痕 | 读取/导出/删除/权限变更审计与留存 | S/M |
| P2 | 主体泛化 | 仅保留模板 `subject_type` 兼容位 | — |

### 6.3 业务进度模型评估

现状缺口：

- 无「业务事项」实体，无法表达事项类型、责任人、组织、时限、里程碑、状态流转。
- 无周期快照，只能看当前态，无法计算趋势、逾期、环比。
- 完成率/质量口径未定义，跨系统字段语义不一致。

建议模型：

| 表 | 关键字段 |
|---|---|
| `business_item` | `item_no`、`type`、`owner_person_id`、`org_id`、`source_system`、`deadline`、`status`、`milestones(JSON)`、`updated_at` |
| `progress_snapshot` | `person_id`、`period(day/week)`、`item_count`、`completed`、`on_time_rate`、`overdue_days`、`quality_score`、`workload` |
| `profile_snapshot` | `person_id`、`template_code`、`period`、`attributes_json`、`version`、`calculated_at` |

评估：

- **适配度**：高。与现有 `ingest_pipeline`、模板、`dps-worker` 调度天然契合。
- **工作量**：L。新实体 + 周期计算 + 口径治理。
- **主要风险**：口径不统一、源系统缺里程碑、历史数据无法回填。
- **处置**：先选 1–2 类高频事项试点；口径字典与 DQ 规则先行；历史只回填可获得的周期。

### 6.4 组织数据权限评估

现状：仅 tenant 过滤；`profile.org_id` 为单值，无组织树、无数据范围、无跨部门授权。

建议：

- 组织树（`org_code/parent_code/path`），与身份域组织编码对齐。
- `data_scope`：`self` / `org` / `org_subtree` / `all`，列表与详情统一注入。
- 跨部门专班：按事项/项目 ACL 授权，不依赖组织树。
- 前端：组织视角看板、范围切换、越权空态。

评估：

- **适配度**：高（数据量小、查询可控）。
- **工作量**：M。
- **风险**：组织调整、兼职多岗、历史数据组织归属缺失。
- **处置**：组织树版本化；人员多岗关联表；历史按最近有效组织归属并标注。

### 6.5 规模与选型

| 规模 | 建议 |
|---|---|
| 10³–10⁵ 人 | 现有 DB 任务表 + `dps-worker` 足够 |
| 10⁵–10⁶ 人 | 分区、组织树预聚合、读写分离 |
| >10⁶ 或秒级 | 再评估流式/特征存储（当前不需要） |

## 7. 综合结论与建议

### 7.1 依赖关系

```
PII 分级 ──► 读路径/导出/跨系统
组织权限 ──► 列表/详情/看板数据范围
业务进度模型 ──► 周期计算 ──► profile_snapshot ──► 趋势/预警
审计 ──► 贯穿读取/导出/删除/权限变更
```

### 7.2 建议实施顺序

1. **PII 分级与读路径脱敏**（S/M）：先封 `/portrait/list` 等直接暴露面。
2. **组织树与数据权限**（M）：决定谁能看谁。
3. **业务进度模型与周期快照**（L）：先试点 1–2 类事项。
4. **审计留痕与留存策略**（S/M）。
5. 主体泛化不实施，仅保留兼容位。

### 7.3 决策建议

| 场景 | 建议 |
|---|---|
| 两类画像都要近期上线 | P0-1/P0-2 先行，P0-3 与业务进度画像同步 |
| 先上人物画像 | P0-1/P0-2/P0-4 先做，P0-3 可延后 |
| 仅内部试用、无敏感数据 | 仍建议先做 PII 清单与日志纪律 |

### 7.4 开放问题

1. 业务事项的完成率/质量口径由哪个业务部门定义？
2. 组织树以哪个系统为主数据源，历史组织归属如何回填？
3. PII 分级由业务、法务还是平台治理角色审定？
4. L4 字段是否允许落库，还是只存引用/令牌？
5. 跨系统（OpenLLM/记忆）是否接受 DPS 的分级与脱敏策略？

## 8. 附录：证据索引

| 主题 | 路径 |
|---|---|
| profile 表与唯一约束 | `DPS/src/ddl/schema_root.py:L130-L153` |
| 模板已含 subject_type | `DPS/src/ddl/schema_portrait.py:L30-L67` |
| annotation 表（profile_id 外键、content TEXT） | `DPS/src/ddl/schema_profile_dependents.py:L205-L235` |
| 画像列表返回完整 attributes | `DPS/src/rest_api/routes/routes_profiles.py:L595-L655` |
| 审计脱敏与 IP 掩码 | `DPS/src/engines/audit_log_engine.py:L310-L333` |
| DSN 脱敏 | `DPS/src/database.py:L28` |
| 身份审计不读请求体 | `DPS/src/identity/audit_identity.py:L11` |
| OpenLLM 回写 | `OpenLLM/backend/app/api/writeback.py`、`edgerouter/adapters/dps_client.py` |
| 前端 person_id 使用 | `openbase-ui/src/modules/portrait/`（PortraitList/Detail/Search/Relation/DpsMeasureView/DpsAnnotationWorkbenchView）、`core/api/dps.ts` |
