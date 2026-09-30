# OpenBase API 接口设计文档 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档版本 | v1.4.0 |
| 状态 | **[Review]（待设计评审）** —— 含 **2026-09-30 两项实测回写** ＋ **DPS v2.9.1 跨仓修复闭环回填** |
| 版本号 | **v1.4.10**（承接型小版本：DPS 模板化能力对接深化） |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-09-29 |
| 需求基线 | **v1.4.10-REQ-BL-1.2.0**（含 D-1410-03 范围扩大） |
| **契约基线** | **DPS《API 接口设计文档-v2.11.0》v1.2.0**（§1 统一约定／§2 端点清单／§3 关键端点契约／§3.7 预检与影响面口径／§4 错误码表）—— **新增端点唯一事实源**；**既有端点**以 **DPS 实现路由**（`src/rest_api/routes/routes_profiles.py`）＋引擎代码为事实源 |
| 上游依据 | 《OpenBase-开发需求文档-v1.4.10》**v2.3.0**（FR-1410-14~18）；《OpenBase-系统架构设计文档-v1.4.10》v1.1.0；《OpenBase-需求设计追溯矩阵-v1.4.10》v1.1.0；《OpenBase-需求变更记录-v1.4.10》**v1.1.0**（D-1410-03） |
| 存放 | `doc/design/` |

> **本文档职责**：定义 **OpenBase 侧（`dps_proxy`）对 10 个新增端点的代理契约**，并逐项锁定路径、方法、参数、响应、错误码与身份口径。**不重复定义上游契约内容**（引用为准），**不臆造**。

---

## 1. 代理路径映射（前端 ↔ 本仓 ↔ 上游）

| 段 | 规则 | 示例 |
|----|------|------|
| 前端 → 本仓 | **`/api/v1/dps-proxy/{path}`**（**修正 G3**：实测 v1.4.5 口径即此前缀，`dps_proxy` router prefix ＋ 前端 `core/api/dps.ts` 全部走该前缀；**原写 `/api/v1/proxy/dps/{path}` 属臆造**） | `/api/v1/dps-proxy/scoring-types` |
| 本仓 → 上游 | `{DPS_BASE_URL}/api/v2/portrait/{path}` | `.../api/v2/portrait/scoring-types` |
| 载体 | 复用 `_forward(method, path, headers, request)`（`dps_proxy/__init__.py`） | — |

> **旁证（既有通道并存）**：另有**通用透传代理** `/api/v1/proxy/{system}/{path}`（`openbase/modules/proxy/__init__.py`），可触达四系统任意端点。**本版新增端点一律走专用 `dps_proxy` 路由**（可做权限动作映射、错误码映射与契约对齐）；通用代理**不承载**本版新增模板面端点，避免出现"路由未声明但可达"的不可审计路径。

**新增本仓路由（10 个，契约 §2）**：

| # | 本仓路由（挂载于 dps_proxy router） | 上游路径（`/api/v2/portrait/` 下） | 方法 |
|:-:|-----------------------------------|-----------------------------------|:----:|
| 1 | `/template-packages/export` | `/template-packages/export` | POST |
| 2 | `/template-packages/import` | `/template-packages/import` | POST |
| 3 | `/templates/{code}/diff` | `/templates/{code}/diff` | GET |
| 4 | `/templates/{code}/rollback` | `/templates/{code}/rollback` | POST |
| 5 | `/templates/{code}/preflight` | `/templates/{code}/preflight` | GET |
| 6 | `/lineage/tags/{tag_code}` | `/lineage/tags/{tag_code}` | GET |
| 7 | `/lineage/impact` | `/lineage/impact` | GET |
| 8 | `/measures/suggest` | `/measures/suggest` | GET |
| 9 | `/annotation-adapters/{adapter_id}/generate` | `/annotation-adapters/{adapter_id}/generate` | POST |
| 10 | `/scoring-types` | `/scoring-types` | GET |

> **路由注册顺序（强制，DT-04）**：**静态段先于动态段** —— `/template-packages/*`、`/lineage/*`、`/measures/*`、`/scoring-types`、**`/templates`（列表，无 path 参数）**、**`/annotation-templates`（列表，无 path 参数）**、**`/labels`** 必须先于 `/templates/{code}/*`、`/annotation-templates/{code}` 注册；且 DPS 侧 `/portrait/{person_id}` 在更外层。Step 3 须加**路由映射断言测试**（**22 条**逐条断言）。

### 1.1 既有端点补代理路由（12 个，D-1410-03 新增）

> **来源**：需求 §1.2（E-11~E-22）。这些端点 DPS **早已存在**（非契约 §2 的新增项），OpenBase 侧**从未代理**；本表为**逐项实测**的路径与权限动作。

| # | 本仓路由（`dps_proxy` router） | 上游路径（`/api/v2/portrait/` 下） | 方法 | 对应 E |
|:-:|--------------------------------|-----------------------------------|:----:|:------:|
| 11 | `/templates` | `/templates` | GET | E-11 |
| 12 | `/templates/{code}` | `/templates/{code}` | GET | E-12 |
| 13 | `/templates` | `/templates` | POST | E-13 |
| 14 | `/templates/{code}` | `/templates/{code}` | PUT | E-14 |
| 15 | `/templates/{code}/activate` | `/templates/{code}/activate` | POST | E-15 |
| 16 | `/templates/{code}/deactivate` | `/templates/{code}/deactivate` | POST | E-15 |
| 17 | `/annotation-templates` | `/annotation-templates` | GET | E-16 |
| 18 | `/annotation-templates/{code}` | `/annotation-templates/{code}` | GET | E-17 |
| 19 | `/annotation-templates` | `/annotation-templates` | POST | E-18 |
| 20 | `/annotation-templates/{code}` | `/annotation-templates/{code}` | PUT | E-19 |
| 21 | `/annotation-templates/{code}` | `/annotation-templates/{code}` | DELETE | E-20 |
| 22 | `/labels` | `/labels` | GET | E-21 |

> **E-22（标签分类 CRUD，4 条）**为**既有已代理**路由（`/tags/categories` GET／POST／PUT／DELETE），**本版不改行为**，仅纳入 22 端点台账（合计口径 22 ＝ 10 ＋ 12，其中 E-22 计 1 项能力）。

> **⚠ 实做提示（G2 修正）**：`dps_proxy` 现有实现为**单文件** `__init__.py`（既有 12 条路由）；新增 18 条路由（10 ＋ 8）后**体积将显著增长**（已在 ADR-01／TD-新增-039 记为观察项）。Step 3 建议按**子路由模块**拆分（如 `templates_routes.py`），**但不得改变对外路径**。

---

## 2. 统一约定（沿用契约 §1）

| 项 | 约定 | 本仓处理 |
|----|------|----------|
| 响应体 | `{"code":200,"message":"success","data":{...}}` | **保真透传**（含 `data` 内结构） |
| 错误体 | `{"code":4xx/5xx,"message":"<可读说明>","data":null}` | **语义保真**（不转 500、不改 message） |
| 鉴权 | `IdentityGate → TenantGate → PermissionGate`（**fail-closed**） | 身份由本仓注入（§4），上游裁决 |
| 权限点 | 复用 `portrait_template:*`／`annotation_template:*`，**不新增** | 映射见 §3 |
| 分页 | `?page=1&page_size=20`，响应 `{items,total,page}` | 参数透传 |
| 幂等 | 导入接受 `package_hash`，同 hash 重复导入 → `skipped` | 透传（不本仓去重） |
| 时间 | ISO8601（UTC） | 不转换 |
| 路由顺序 | 静态路由先于 `/portrait/{person_id}` | 见 §1 |

---

## 3. 端点契约明细（10 项）

### 3.1 权限动作映射（**D4 已确认，四方一致**）

| # | 端点 | 权限点 | 动作依据 |
|:-:|------|--------|----------|
| 1 | 导出 | **`portrait_template:create`** | 需求 §7 明示（**非** HTTP 方法默认 read） |
| 2 | 导入 | **`portrait_template:create`** | 同上 |
| 3 | 版本对比 | `portrait_template:read` | HTTP 方法映射（GET→read） |
| 4 | **回滚** | **`portrait_template:update`** | 需求 §7 明示；DPS 侧经**端点级动作声明** `ENDPOINT_ACTION_OVERRIDES`（`("POST","/rollback")→"update"`）落地 |
| 5 | 预检 | `portrait_template:read` | GET→read |
| 6 | 标签血缘反查 | `annotation_template:read` | GET→read |
| 7 | 影响面 | `annotation_template:read` | GET→read |
| 8 | 措施建议 | `portrait_template:read` | GET→read |
| 9 | AI 候选生成 | `annotation_template:create` | POST→create |
| 10 | 评分类型 | `portrait_template:read` | GET→read |

**D-1410-03 补代理端点权限动作映射（12 路由，E-11~E-22）—— 含 2026-09-30 实测 ＋ 跨仓修复闭环**

> **⚠ 本表已按实测回写**（证据：`doc/test/evidence/v1410/g6-permission-resolution-20260930.md`，`E-G6-20260930`）。**原 v1.2.0 表存在 3 类错误**（编号口径混用 ＋ 权限点臆断），已作废。
>
> **⚠ 2026-09-30 追加**：8 项不一致已由 **DPS v2.9.1 跨仓修复**闭环（交付回执：`doc/test/evidence/v1410/dps-v291-permission-caliber-fix-receipt-20260930.md`，`E-DPS-v291-20260930`；派单 `OB-v1.4.10-DSP-PERM-01`）。**下表保留「修复前」列作为对比基线，并列示修复后判定**。

| #（§1.1 路由号） | 能力 | 设计声明权限点 | **实测判定（修复前，2026-09-30）** | **实测判定（修复后，DPS v2.9.1）** | 一致性 |
|:-:|------|----------------|-----------------------------------|--------------------------------------|:------:|
| 11 | 画像模板列表（E-11） | `portrait_template:read` | `portrait_template` + `read` | 同左（未变） | ✅ |
| 12 | 画像模板详情（E-12） | `portrait_template:read` | `portrait_template` + `read` | 同左（未变） | ✅ |
| 13 | 画像模板创建（E-13） | `portrait_template:create` | `portrait_template` + `create` | 同左（未变） | ✅ |
| 14 | 画像模板更新（E-14） | `portrait_template:update` | `portrait_template` + `update` | 同左（未变） | ✅ |
| 15 | 画像模板**激活**（E-15） | `portrait_template:update` | `portrait_template` + `create`（⚠ G8） | **`portrait_template` + `update`** | ✅ |
| 16 | 画像模板**停用**（E-15） | `portrait_template:update` | `portrait_template` + `create`（⚠ G8） | **`portrait_template` + `update`** | ✅ |
| 17 | 标注模板列表（E-16） | `annotation_template:read` | `portrait` + `read`（⚠ G6） | **`annotation_template` + `read`** | ✅ |
| 18 | 标注模板详情（E-17） | `annotation_template:read` | `portrait` + `read`（⚠ G6） | **`annotation_template` + `read`** | ✅ |
| 19 | 标注模板创建（E-18） | `annotation_template:create` | `portrait` + `create`（⚠ G6） | **`annotation_template` + `create`** | ✅ |
| 20 | 标注模板更新／改挂（E-19） | `annotation_template:update` | `portrait` + `update`（⚠ G6） | **`annotation_template` + `update`** | ✅ |
| 21 | 标注模板删除（E-20） | `annotation_template:delete` | `portrait` + `delete`（⚠ G6） | **`annotation_template` + `delete`** | ✅ |
| 22 | 标签管理 `action=list`（E-21） | `annotation_template:read` | `portrait` + `read`（⚠ G9） | **`annotation_template` + `read`** | ✅ |
| — | 标签分类 CRUD（E-22） | 沿用既有 | 既有已代理，**本版不改** | 同左 | ✅ |

**实测一致项（核对通过）**：`templates` 读／创建／更新（#11~#14）✅；包导出 `template-packages/export`（#1）→ `portrait_template:create` ✅；版本对比（#3 面）→ `portrait_template:read` ✅；**回滚（#4 面）→ `portrait_template:update`（命中端点级声明，DPS 已修 `TD-3027`）** ✅；血缘（#6 面）→ `annotation_template:read` ✅。

> **统计**：12 路由中 **一致 12 项 ／ 不一致 0 项**（修复前为 **一致 4 项 ／ 不一致 8 项**，分属 **G6 五项、G8 两项、G9 一项**，已由 DPS v2.9.1 全部闭环）。**v1.2.0 §6 的「10/12 一致、2 项待实测」自评失真，已作废。**

> **⚠ 本仓代理层不做权限判定**（仅透传身份头，裁决权在 DPS）⇒ **本表用于「对齐判据与联调预期」，不改变运行逻辑**。差异处置见 §6.1 与《第三方集成设计文档》§8.1；**跨仓修复**见派单 `OB-v1.4.10-DSP-PERM-01`（3 子项，**已交付**）。

> **联调预期（按修复后实测）**：调用标注模板 CRUD **须持 `annotation_template:*`**（原「须持 `portrait:*`」的口径**已作废**）；调用模板启停**须持 `portrait_template:update`**（原「须持 `portrait_template:create`」**已作废**，该口径即本次修复的越权面）。**Step 3／4 用例与联调账号权限准备一律以此为准**。

> **本仓不自行做权限判定**（BR-1410-02）：仅注入身份 ＋ 透传上游 `403`。

### 3.2 请求／响应与错误（按契约 §3 摘要，**以契约为准**）

| # | 端点 | 关键请求字段 | 成功响应要点 | 错误 |
|:-:|------|-------------|-------------|------|
| 1 | 导出 | `scope{type,codes[]}`、`include_annotation_templates` | `format_version`／`package_hash`／`items[]`／`dependencies[]`／`package{}` | **400** 依赖缺失 |
| 2 | 导入 | `package{}`、`conflict_policy`（`overwrite｜skip｜rename`）、**`dry_run`** | dry_run：`would_create／would_skip／would_conflict／errors[]`；实做：`created／skipped／renamed[]／identical` | **409** 冲突未指定策略／**400** `format_version` 不支持／**422** 包结构非法 |
| 3 | 版本对比 | `{code}` 路径参数 | 差异结构 | 404 |
| 4 | 回滚 | `target_version`、`reason` | `template_code／new_version／rolled_back_to／equivalence_check` | **404** 目标版本不存在 |
| 5 | 预检 | `{code}` 路径参数 | 校验结果 ＋ **影响面三项 ＋ `basis`** | 400／404 |
| 6 | 血缘反查 | `{tag_code}` | `tag_code／sources[]{annotation_id,template_code,source,adapter_id,created_at}` | **404 无谱系** |
| 7 | 影响面 | `?template_code=` **或** `?annotation_template_code=` **或** `?tag_code=`（**三层**） | `tag_count／profile_count` ＋ `basis` | **400**（`?field_key=` **显式不支持**，D-6-6） |
| 8 | 措施建议 | `?person_id=` | `suggestions[]{tag_code,measure_code,measure_text,source_tag}` ＋ **`disclaimer`** | 400／404 |
| 9 | AI 候选生成 | `text`、`annotation_template` | `annotation{id,review_status:"pending"}`／`source:"ai_annotation"`／`adapter_id` | **403 AI 通道未启用**／**503 适配器不可用（降级非阻塞）**／**409 未复核候选进入标签·画像路径**（门禁 DT-009） |
| 10 | 评分类型 | 分页参数 | 列表 | 400（未注册评分类型） |

### 3.3 预检与影响面口径（契约 §3.7，**D-6-6／D-6-8**）

| 项 | 本仓设计 |
|----|----------|
| 影响面维度 | 三层：`template_code`／`annotation_template_code`／`tag_code` |
| `field_key` 参数 | **不支持 → 400**（不近似）；本仓**不拦截**，透传上游语义 |
| **`basis` 字段** | **必须随报告返回**（口径可复核）；**前端呈现按 A-1410-03：折叠/气泡**（默认收起，点「口径」展开；审计导出给原文） |
| 包预检同源 | 上游委托 `import_package(dry_run=True)`，影响面结论须与真实导入**逐项一致**（前端不得二次加工） |
| 谱系口径提示 | 「未联动过则为 0」—— 前端在 `tag_count=0` 时**须给出该口径提示**（避免误判为缺陷） |

### 3.4 补代理端点契约（12 项，D-1410-03 新增）

> **取证口径**：以下逐项来自 **DPS 实现路由 ＋ 引擎代码**（`routes_profiles.py`／`template_engine.py`／`annotation_template_engine.py`），非文档推断。

| # | 端点 | 请求 | 响应 `data` | 错误码（实测口径） |
|:-:|------|------|-------------|--------------------|
| 11 | `GET /templates` | `?status=&profile_type=&subject_type=`（均可选） | `{items[], total}` | 400（过滤参数非法） |
| 12 | `GET /templates/{code}` | 路径参数 `code` | 画像模板对象（`code`／`name`／`profile_type`／**`extends`**／`subject_type`／`version`／`status`／`description`／`dimension_config`／`attributes_schema`／**`tag_bindings`**／`evidence_policy`／`anomaly_rules`） | **404**（不存在） |
| 13 | `POST /templates` | body：`code`（必填唯一）／`name`／`profile_type`／`extends`／`subject_type`／`status`／`description`／`dimension_config`／`attributes_schema`／`tag_bindings`／`evidence_policy`／`anomaly_rules` | 创建后的模板对象 | **400**（校验失败，**含字段级原因**）／**409**（`code` 冲突） |
| 14 | `PUT /templates/{code}` | body：待变更字段 | 更新后对象（**`version` 递增 ＋ `portrait_template_history` 留痕**） | **404**／**400**（含 `extends` **自指／成环／深度 >2／父模板不存在**） |
| 15 | `POST /templates/{code}/activate` | 无 body | 更新后对象（`status=active`） | **404**；**幂等**（重复调用结果一致） |
| 16 | `POST /templates/{code}/deactivate` | 无 body | 更新后对象（`status=inactive`） | **404**；**幂等**；**停用后新计算与新标注被拒** |
| 17 | `GET /annotation-templates` | `?template_code=&scenario=`（均可选） | `{items[], total}` | 400 |
| 18 | `GET /annotation-templates/{code}` | 路径参数 `code` | 标注模板对象（`code`／`name`／`version`／`status`／**`template_code`（归属）**／`scenario`／**`field_schema`**） | **404** |
| 19 | `POST /annotation-templates` | body：`code`／`name`／`version`／`status`／`description`／**`template_code`（必填）**／`scenario`／**`field_schema`** | 创建后对象 | **409**（`code` 已存在）／**400**（其余校验：归属模板不存在或未 `active`、`scenario` 非法、`field_schema` 非法） |
| 20 | `PUT /annotation-templates/{code}` | body：待变更字段（**含 `template_code` 即改挂**） | 更新后对象（`version` 递增） | **404**／**400**（新归属不存在或未 `active`、`scenario` 非法、`field_schema` 非法） |
| 21 | `DELETE /annotation-templates/{code}` | 路径参数 `code` | `{code, deleted: true}` | **404**／**409**（**存在关联标注数据**，消息含条数；**引用判定列缺失 → fail-closed 拒绝**） |
| 22 | `GET /labels` | `?action=list` | 标签列表 | **400**（`action` ≠ `list`） |

**枚举与结构口径（逐项实测）**：

| 项 | 取值／结构 |
|----|-----------|
| 画像模板 `status` | `active`／`inactive`／`draft`（默认 `active`） |
| 画像模板 `profile_type`／`subject_type` | 默认 `persona`／`person` |
| **`extends` 继承约束** | **禁自指**、**禁环引用**、**深度 ≤ 2**、**父模板必须存在**、**有租户上下文时按租户过滤（不得继承他租户模板）**；维度解析「父先入 → 子覆盖同名 → 追加新维度」 |
| 标注模板 `scenario` | **仅 4 类**：`intake`／`assess`／`check`／`general`（默认 `general`） |
| **`field_schema` 元素** | `key`（必填、**同模板内唯一**）、`type`（**仅 5 类** `string`／`enum`／`number`／`date`／`list`）、`required`、`options`（`enum` **必填**）、`range`（`number`，`[low, high]`）、**`target_dimension`**（有则参与标签联动） |
| **标注值校验** | 未在模板声明的字段 → 400；必填缺失 → 400；`enum` 越界／`number` 越界／`date` 非 `YYYY-MM-DD`／`list` 非数组 → 均 400 |
| **标签联动口径** | 仅含 `target_dimension` 的字段参与；**`tag_code = "{dimension}:{key}"`**；评分：`enum` 按 `options` 顺序**逆序**线性映射（首项 100、末项 0）、`number` 裁剪 0~100、其他有值类型默认 80；**人工标注优先** |
| **审核状态机** | `pending → approved／rejected／modified`；`rejected → pending`（可重提）；`approved`／`modified` 为**终态**；非法流转 → 400 |
| **强归属三处校验** | ①创建 ②改挂（PUT）③标注提交：均要求归属画像模板**存在且 `active`**，且标注模板自身 `active`；不匹配 → **400**（消息含期望/实际 `template_code`） |
| **无"解除归属"语义** | `template_code` **非空且不可置空** ⇒ 解除只能「改挂」或「删除」；**UI 不得提供解除入口** |
| **子标签** | **不存在**：`tag_definition` 建表语句**无 `parent_tag_code` 列**（仅模型声明） ⇒ **本版不做**，转跨仓（RT-1410-28 #2） |
| `tag_bindings` | 画像模板字段，DPS 侧**仅 JSON 透传／落库，无元素结构与校验** ⇒ 本版**只做原样呈现，不做结构假设** |

---

## 4. 身份与安全（对齐架构 §4.2）

| 项 | 设计 |
|----|------|
| 出站头 | `X-User-ID`／`X-Tenant-ID`／`X-Org-ID`／`X-User-Role` ＋ `X-Proxy-Source`（`dps`）／`X-Request-Id` |
| **org 传值** | `org_value_map` 命中 → 真 org；未命中 → 回落 `= X-Tenant-ID`（OB-8 别名） |
| **强制约束** | **`enforce_org_alias` 必须为 `False`**（True 时强制 `org == tenant`，与传真 org 互斥） |
| **联调前置（P1）** | **须配 `dps_org_map`／`dps_code_map`**（当前 `.env` 未配 ⇒ org 回落 tenant 值，DPS 将 401／归属校验失败） |
| 默认角色 | `default_role="user"`（与 DPS 侧默认一致） |
| 凭据 | 前端**零密钥**；日志**零凭据** |

---

## 5. 前端调用契约（🎨 对齐，DT-13）

| 项 | 设计 |
|----|------|
| 调用入口 | `openbase-ui/src/core/api/dps.ts`（扩展 **22 个方法**：10 新增 ＋ 12 补代理） |
| 统一件 | `core/api/http.ts`（请求）＋ `core/api/error.ts`（错误） |
| 错误分支 | 400／403／404／409／422／503 **逐码呈现**；**5xx 不静默降级** |
| **页面映射（G2 修正）** | **P-01↔#11·#12·#15·#16**（原误写 `#3`，`#3` 为版本对比属 P-02）；P-02↔#3·#4；P-03↔#5·#7；P-04↔#1·#2；P-05↔#6·#7；P-06↔#8；P-07↔#10；P-08↔#9；**P-09↔#12·#13·#14**（画像模板新建／编辑＋`extends` 选择）；**P-10↔#17·#18·#19·#21**；**P-11↔#12·#18·#20**（字段体系编辑＋归属改挂）；**P-12↔#21·#22**（标签体系查看）——**映射覆盖率 100%（22 端点 ↔ 12 页面，逐项可核，不得自评）**（DT-23／AC-18） |
| 前端禁则 | 页面**不直连 DPS**；**不构造身份头**；**不做权限判定**；**不假设 `tag_bindings` 结构**（原样呈现）；**不提供"解除归属"入口**（语义上不存在） |

---

## 6. 契约对齐检查（2.9 前置）

| 检查项 | 结果 |
|--------|:----:|
| 后端 **22 端点** ↔ 前端 **12 页面**映射 | ✅ **100%（逐项可核，见 §5）** —— **原 v1.1.0 的「10 端点 ↔ 8 页面 100%」为失真自评，已作废**（见 §6.1） |
| 新增 10 端点权限点与 DPS 契约 §2 逐项一致 | ✅ **10/10** |
| **补代理 12 端点权限点与 DPS 实现口径** | ✅ **一致 12／12；不一致 0** —— **2026-09-30 实测修复前为「一致 4／12；不一致 8」**（G6 五项 ＋ G8 两项 ＋ G9 一项），**已由 DPS v2.9.1 跨仓修复闭环**（回执 `E-DPS-v291-20260930`），§3.1 按「修复前／修复后」双列回写；**原「10/12 一致、2 项待实测」自评作废** |
| **`llm_proxy` → OpenLLM 链路（2026-09-30 实测）** | ✅ **通过** —— `GET /api/v1/llm-proxy/models` **200 ＋ OpenLLM 真实注册表**；`POST /chat`（`deepseek-v4-flash`）**200 ＋ 真实推理**（含 usage／routing_trace）；匿名 **401**、裸身份头 **403** 防伪造生效（证据 `E-LLMPROXY-20260930`） |
| 错误码与契约 §4 一致（含 D-1410-01 修订后） | ✅（新增端点）；**补代理端点错误码来自实现取证**（§3.4） |
| 身份头与 `protocol_headers` 一致 | ✅（不新增头） |
| 路由顺序约束落实 | ✅（§1 强制条款，**22 条**断言） |
| 分页／幂等／时间格式 | ✅ 透传（导入 `package_hash` 幂等；模板启停幂等） |
| **代理前缀正确性** | ✅ **已修正 G3**（`/api/v1/dps-proxy/{path}`） |

### 6.1 缺陷闭环登记（G1~G5，源自 D-1410-03）

| # | 缺陷 | 级别 | 本版处置 | 状态 |
|:-:|------|:----:|----------|:----:|
| **G1** | P-01（模板族列表／详情／启停）**无端点**（E-01~E-03 不在契约 §2 且既有代理无模板族） | P0 | 新增 **§1.1 补代理路由 #11／#12／#15／#16**（E-11／E-12／E-15） | ✅ **已闭环** |
| **G2** | 页面↔端点**错映射**（P-01↔#3；前端架构表 `#1 #2 #3` 撞号）＋ §6 失真自评 | P0 | **§5 映射全量重写**；§6 自评作废并逐项重核；前端架构 §2 同步修正 | ✅ **已闭环** |
| **G3** | 代理前缀**臆造**（`/api/v1/proxy/dps/{path}`） | P1 | §1 前缀修正为 **`/api/v1/dps-proxy/{path}`**，并补「通用代理不承载本版新增端点」的通道边界声明 | ✅ **已闭环** |
| **G4** | E-01~E-03 口径偏差**未登记** | P1 | 需求 §1.1 偏差登记 2 项；本文档 §1／§1.1 分列编号段 | ✅ **已闭环**（需求侧回写见开发需求 v2.3.0） |
| **G5** | **模板本体语义整层缺失** | P0 | 新增 **§1.1（12 路由）＋ §3.1（权限）＋ §3.4（契约与枚举口径）**；页面 **P-09~P-12**（见 UI 设计文档） | ✅ **已闭环**（设计侧）；联调实测待 Step 3／4 |
| **G6** | **DPS 侧**标注模板 CRUD 权限点映射缺陷（`SUBPATH_RESOURCE_MAP` 键 `annotations` ≠ 路径 `annotation-templates`） | P1 | **已实测确认**（`E-G6-20260930`）：判定资源实测为 **`portrait`**；本仓**按实测回写 §3.1**；**跨仓派单** `OB-v1.4.10-DSP-PERM-01`（子项①）→ **DPS v2.9.1 已补键 `("portrait","annotation-templates")`，判定资源归位 `annotation_template`** | ✅ **已闭环**（回执 `E-DPS-v291-20260930`） |
| **G8** | **DPS 侧**模板**启停**端点动作映射缺陷（`ENDPOINT_ACTION_OVERRIDES` 未含 activate／deactivate ⇒ 实测动作 = **`create`**） | **P1** | **本次实测新发现**：仅持 `portrait_template:create` 者可启停（**越权面**，与已修的回滚端点 `TD-3027` 同类残留）；**本仓按实测回写 §3.1**；**跨仓派单** `OB-v1.4.10-DSP-PERM-01`（子项②）→ **DPS v2.9.1 已补声明 `("POST","/activate")→update`／`("POST","/deactivate")→update`** | ✅ **已闭环**（回执 `E-DPS-v291-20260930`） |
| **G9** | **DPS 侧** `/portrait/labels` 判定资源为 `portrait`（非 `annotation_template`） | P2 | **本次实测新发现**；**本仓按实测回写 §3.1**；**跨仓派单** `OB-v1.4.10-DSP-PERM-01`（子项③）→ **DPS v2.9.1 已补键 `("portrait","labels")→annotation_template`**（并自证读取面不收窄） | ✅ **已闭环**（回执 `E-DPS-v291-20260930`） |
| **G7** | **DPS 侧** `tag_definition.parent_tag_code` 未落库（子标签能力缺失） | P2 | **登记跨仓需求 RT-1410-28 #2**；本版**明确不做**（需求 §7 排除项） | ⏳ **跨仓待办**（派单 `OB-v1.4.10-DSP-TAG-01`；未涉及本次实测与修复） |

---

## 7. 待办与依赖

| # | 项 | 级别 | 说明 |
|:-:|----|:----:|------|
| 1 | `dps_org_map`／`dps_code_map` 配置 | **P1** | 联调前置（架构风险 #1） |
| 2 | `llm_proxy` 现状核对（AI 复核通道） | P2 | **已闭环**（A-1410-01：核实为完整 OpenLLM 通道） |
| 3 | 路由映射断言测试（**22 条**） | P0 | Step 3 交付（DT-04） |
| 4 | **补代理 12 端点权限点实测** | **P1** | ✅ **已完成（2026-09-30）** —— 见证据 `E-G6-20260930`；**实测结论（修复前）：一致 4／12，不一致 8（G6／G8／G9）**；**8 项已由 DPS v2.9.1 跨仓修复闭环（回执 `E-DPS-v291-20260930`）⇒ 当前一致 12／12**，已按「修复前／修复后」双列回写 §3.1；**Step 3／4 用例与联调账号权限一律按修复后结论准备**（标注模板 CRUD 须 `annotation_template:*`；启停须 `portrait_template:update`） |
| 5 | **DPS 侧权限点映射补丁派单** | P1 | ✅ **已交付**（跨仓 RT-1410-28 #1，**3 子项**：补 `annotation-templates` 键／补 activate·deactivate 声明／补 `labels` 键）—— **DPS v2.9.1**（提交 `ff9fd9f` ＋ 发布收尾 `de106eb`，Tag `v2.9.1` 三远程一致）；见《跨仓改动规划与派单》§3.1／§3.2 与回执 `E-DPS-v291-20260930` |
| 6 | **`parent_tag_code` 落库要求** | P2 | 跨仓（RT-1410-28 #2）；本版不做子标签 |
| 7 | **`dps_proxy` 文件拆分预案** | P3 | Step 3 建议（ADR-01／TD-新增-039），**不得改对外路径** |

---

## 8. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| **v1.4.0** | 2026-09-30 | **AA-OpenBase-Dev** | **DPS v2.9.1 跨仓修复闭环回填**（派单 `OB-v1.4.10-DSP-PERM-01` 三子项交付，回执 `E-DPS-v291-20260930` / 证据目录 `doc/test/evidence/v1410/dps-v291-permission-caliber-fix-receipt-20260930.md`）：① **§3.1** 表体改为「**修复前／修复后**」**双列**（保留实测基线，不抹去历史）+ **统计改判 一致 4／12 → 一致 12／12**；**联调预期作废并改写**（标注模板 CRUD 须 `annotation_template:*`；模板启停须 `portrait_template:update` —— 原「须 `portrait:*`／须 `create`」口径作废）；② **§6** 契约对齐检查该行 **❌ 4／12 → ✅ 12／12**；③ **§6.1** **G6／G8／G9 状态 → ✅ 已闭环**（附 DPS 侧具体落地：补 `("portrait","annotation-templates")` 键／补 activate·deactivate 动作声明／补 `("portrait","labels")` 键）；G7 仍跨仓待办并补派单号；④ **§7** #4 结论更新、#5 派单 **→ ✅ 已交付**（DPS v2.9.1，`ff9fd9f`＋`de106eb`，Tag 三远程一致）。 |
| **v1.3.0** | 2026-09-30 | **AA-OpenBase-Dev** | **2026-09-30 两项实测回写（D-1410-03 遗留「待实测」全部清零）**：① **§3.1 补代理权限映射按实测全量重写** —— 实测（`E-G6-20260930`，直接执行 DPS 判定函数）结论 **一致 4／12、不一致 8**：**G6**（标注模板 CRUD 判定资源实测 `portrait`，非 `annotation_template`，涉 5 路由）／**G8（新发现，P1）**（模板**启停**判定动作实测为 **`create`** 而非 `update` ⇒ **仅持 `create` 者可启停**，与已修回滚端点 `TD-3027` 同类残留）／**G9（新发现）**（`/labels` 判定资源实测 `portrait`）；表体改用 **§1.1 路由号** 消除编号口径混用，并新增「实测判定」列与**联调预期**说明；**原 v1.2.0 的「10/12 一致、2 项待实测」自评作废**。② **§6 契约对齐检查**：补代理权限一致性改判 **❌ 4／12**；**新增 `llm_proxy`→OpenLLM 链路行（✅ 通过）**。③ **§6.1 缺陷登记**：**G6 状态更新为「实测已完成」**，**新增 G8／G9**。④ **§7 待办**：#4 权限点实测 → **✅ 已完成**；#5 派单扩展为 **3 子项**。证据：`doc/test/evidence/v1410/g6-permission-resolution-20260930.md`、`llm-proxy-openllm-link-20260930.md`。 |
| **v1.2.0** | 2026-09-29 | **AA-OpenBase-Dev** | **D-1410-03 回写（范围扩大 10 → 22 端点）＋ G1~G4 缺陷闭环**：① **§1 前缀修正（G3）** —— 前端入口改为实测的 **`/api/v1/dps-proxy/{path}`**，并声明「通用代理 `/api/v1/proxy/{system}/{path}` 不承载本版新增端点」；② 新增 **§1.1 既有端点补代理路由 12 条**（#11~#22，E-11~E-22，含真实上游路径）；③ §1 路由顺序约束扩至 **22 条**并补列表路由（`/templates`、`/annotation-templates`、`/labels`）先于动态段；④ §3.1 新增 **补代理权限动作映射 12 项**（含**启停按 `update` 的端点级动作声明例外**）＋ **DPS 侧权限点口径异常（G6）**声明；⑤ 新增 **§3.4 补代理端点契约与枚举口径**（12 端点 × 请求／响应／错误码 ＋ `field_schema` 五类字段／`extends` ≤2 禁环／强归属三处校验／**无"解除归属"语义**／**子标签不存在**／`tag_bindings` 不假设结构），**全部来自 DPS 实现取证**；⑥ **§5 页面映射全量重写（G2）** —— P-01↔#11·12·15·16（原误写 `#3`），新增 P-09~P-12，**22 端点 ↔ 12 页面**；⑦ **§6 失真自评作废并逐项重核**，新增 **§6.1 缺陷闭环登记 G1~G7**（G1~G5 已闭环；G6／G7 跨仓待办）；⑧ §7 待办 3 → 7 项。状态 [Review]。 |
| **v1.1.0** | 2026-09-29 | **AA-OpenBase-Dev** | **D-1410-01 自我纠正落笔（双向取证）**：§3.2 端点 #9 错误码**恢复 409**（「未复核候选进入标签·画像路径」，AI 复核门禁 DT-009 —— 经 DPS **实现代码** 核对确认），与 **403／503** 并存；**复核提交路径明确**为 DPS **既有端点** `POST /portrait/annotations/{annotation_id}/review`（非 10 新增端点）；**AI 复核辅助经 `llm_proxy`→OpenLLM**（A-1410-01）。§7 待办第 2 项（`llm_proxy` 核对）**已闭环**（核实为完整 OpenLLM 通道 ⇒ AD-3 后端零新增）。详见《OpenBase-第三方集成设计文档-v1.4.10》§1／§3.1／§4 |
| v1.0.0 | 2026-09-29 | AA-OpenBase-Dev | 初始创建（v1.4.10 Step 2 §2.5a 产出）：**契约基线与职责声明**（不重复上游、不臆造）；**代理路径映射**（10 路由 ＋ **路由注册顺序强制约束**）；**统一约定 8 项**；**端点契约明细**（10 端点 × 权限动作映射〔**D4 已确认四方一致**〕／请求响应要点／错误码）；**预检与影响面口径**（三层维度、`field_key` 400、**`basis` 必返 ＋ A-1410-03 折叠呈现**、包预检同源一致性）；**身份与安全**（org 传值规则、**`enforce_org_alias` 必须 False**、**P1 联调前置**）；**前端调用契约**（`dps.ts` 扩展 ＋ **页面↔端点映射 100%**）；**契约对齐检查 6 项全通过**；**待办 3 项**。状态 [Review]。 |
