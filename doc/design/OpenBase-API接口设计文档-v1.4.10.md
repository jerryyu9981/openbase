# OpenBase API 接口设计文档 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]（待设计评审）** |
| 版本号 | **v1.4.10**（承接型小版本：DPS 模板化能力对接深化） |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-09-29 |
| **契约基线** | **DPS《API 接口设计文档-v2.11.0》v1.2.0**（§1 统一约定／§2 端点清单／§3 关键端点契约／§3.7 预检与影响面口径／§4 错误码表）—— **唯一事实源** |
| 上游依据 | 《OpenBase-系统架构设计文档-v1.4.10》v1.0.0；《OpenBase-需求设计追溯矩阵-v1.4.10》v1.0.0（DT-01／DT-03／DT-27） |
| 存放 | `doc/design/` |

> **本文档职责**：定义 **OpenBase 侧（`dps_proxy`）对 10 个新增端点的代理契约**，并逐项锁定路径、方法、参数、响应、错误码与身份口径。**不重复定义上游契约内容**（引用为准），**不臆造**。

---

## 1. 代理路径映射（前端 ↔ 本仓 ↔ 上游）

| 段 | 规则 | 示例 |
|----|------|------|
| 前端 → 本仓 | `/api/v1/proxy/dps/{path}`（沿用 v1.4.5 口径） | `/api/v1/proxy/dps/scoring-types` |
| 本仓 → 上游 | `{DPS_BASE_URL}/api/v2/portrait/{path}` | `.../api/v2/portrait/scoring-types` |
| 载体 | 复用 `_forward(method, path, headers, request)`（`dps_proxy/__init__.py:253`） | — |

**新增本仓路由（10 个）**：

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

> **路由注册顺序（强制，DT-04）**：**静态段先于动态段** —— `/template-packages/*`、`/lineage/*`、`/measures/*`、`/scoring-types` 必须先于 `/templates/{code}/*` 注册；且 DPS 侧 `/portrait/{person_id}` 在更外层。Step 3 须加**路由映射断言测试**。

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
| 9 | AI 候选生成 | `text`、`annotation_template` | `annotation{id,review_status:"pending"}`／`source:"ai_annotation"`／`adapter_id` | **403 AI 通道未启用**／**503 适配器不可用（降级非阻塞）** |
| 10 | 评分类型 | 分页参数 | 列表 | 400（未注册评分类型） |

### 3.3 预检与影响面口径（契约 §3.7，**D-6-6／D-6-8**）

| 项 | 本仓设计 |
|----|----------|
| 影响面维度 | 三层：`template_code`／`annotation_template_code`／`tag_code` |
| `field_key` 参数 | **不支持 → 400**（不近似）；本仓**不拦截**，透传上游语义 |
| **`basis` 字段** | **必须随报告返回**（口径可复核）；**前端呈现按 A-1410-03：折叠/气泡**（默认收起，点「口径」展开；审计导出给原文） |
| 包预检同源 | 上游委托 `import_package(dry_run=True)`，影响面结论须与真实导入**逐项一致**（前端不得二次加工） |
| 谱系口径提示 | 「未联动过则为 0」—— 前端在 `tag_count=0` 时**须给出该口径提示**（避免误判为缺陷） |

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
| 调用入口 | `openbase-ui/src/core/api/dps.ts`（扩展 10 个方法） |
| 统一件 | `core/api/http.ts`（请求）＋ `core/api/error.ts`（错误） |
| 错误分支 | 400／403／404／409／422／503 **逐码呈现**；**5xx 不静默降级** |
| 页面映射 | P-01↔#3／P-02↔#3·#4／P-03↔#5·#7／P-04↔#1·#2／P-05↔#6·#7／P-06↔#8／P-07↔#10／P-08↔#9（**映射覆盖率 100%**，DT-23／AC-18） |

---

## 6. 契约对齐检查（2.9 前置）

| 检查项 | 结果 |
|--------|:----:|
| 后端 10 端点 ↔ 前端 8 页面映射 | ✅ **100%**（§5） |
| 权限点与 DPS 契约 §2 逐项一致 | ✅ **10/10** |
| 错误码与契约 §4 一致（含 D-1410-01 修订后） | ✅ |
| 身份头与 `protocol_headers` 一致 | ✅（不新增头） |
| 路由顺序约束落实 | ✅（§1 强制条款） |
| 分页／幂等／时间格式 | ✅ 透传 |

---

## 7. 待办与依赖

| # | 项 | 级别 | 说明 |
|:-:|----|:----:|------|
| 1 | `dps_org_map`／`dps_code_map` 配置 | **P1** | 联调前置（架构风险 #1） |
| 2 | `llm_proxy` 现状核对（AI 复核通道） | P2 | AD-3 落地前提 |
| 3 | 路由映射断言测试 | P0 | Step 3 交付（DT-04） |

---

## 8. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-09-29 | AA-OpenBase-Dev | 初始创建（v1.4.10 Step 2 §2.5a 产出）：**契约基线与职责声明**（不重复上游、不臆造）；**代理路径映射**（10 路由 ＋ **路由注册顺序强制约束**）；**统一约定 8 项**；**端点契约明细**（10 端点 × 权限动作映射〔**D4 已确认四方一致**〕／请求响应要点／错误码）；**预检与影响面口径**（三层维度、`field_key` 400、**`basis` 必返 ＋ A-1410-03 折叠呈现**、包预检同源一致性）；**身份与安全**（org 传值规则、**`enforce_org_alias` 必须 False**、**P1 联调前置**）；**前端调用契约**（`dps.ts` 扩展 ＋ **页面↔端点映射 100%**）；**契约对齐检查 6 项全通过**；**待办 3 项**。状态 [Review]。 |
