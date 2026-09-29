# OpenBase API 契约对齐记录 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]（待设计评审）** |
| 版本号 | **v1.4.10**（承接型小版本） |
| 作者 | AA-OpenBase-Dev（后端）／FA-OpenBase-Dev（前端） |
| 创建日期 | 2026-09-29 |
| 依据 | `design-stage-execution` §2.9（前端＋后端轨道均激活 ⇒ **必须执行契约对齐**）；参照 `api-contract-management` |
| 存放 | `doc/design/` |

---

## 1. 对齐目标与角色

| 项 | 内容 |
|----|------|
| **目的** | 在进入 Step 3 前，确保**前端调用 ↔ 后端契约 ↔ 上游 DPS 契约**三方一致，消除字段／错误码／语义漂移 |
| 参与方 | 后端（`dps_proxy`）＋ 前端（`openbase-ui` DPS 模块） |
| 上游 | DPS 契约 v1.2.0（**唯一事实源**）＋ DPS 实现代码（**双向取证**，C1） |

---

## 2. 端点级对齐（10 条路由）

| # | 路径 | 方法 | 后端设计 | 前端调用（`dps.ts`） | 上游 | 一致 |
|:-:|------|:----:|:--------:|---------------------|------|:----:|
| 1 | `/template-packages/export` | POST | ✅ | `exportPackage()` | ✅ | ✅ |
| 2 | `/template-packages/import` | POST | ✅（含 `dry_run`） | `importPackage()` | ✅ | ✅ |
| 3 | `/templates/{code}/diff` | GET | ✅ | `diffVersions()` | ✅ | ✅ |
| 4 | `/templates/{code}/rollback` | POST | ✅（二次确认前置） | `rollbackTemplate()` | ✅ | ✅ |
| 5 | `/templates/{code}/preflight` | GET | ✅（含 `basis`） | `preflightTemplate()` | ✅ | ✅ |
| 6 | `/lineage/tags/{tag_code}` | GET | ✅ | `getTagLineage()` | ✅ | ✅ |
| 7 | `/lineage/impact` | GET | ✅（**三层维度**） | `queryImpact()` | ✅ | ✅ |
| 8 | `/measures/suggest` | GET | ✅（只读） | `suggestMeasures()` | ✅ | ✅ |
| 9 | `/annotation-adapters/{adapter_id}/generate` | POST | ✅ | `generateAnnotationCandidates()` | ✅ | ✅ |
| 10 | `/scoring-types` | GET | ✅ | `listScoringTypes()` | ✅ | ✅ |
| — | **（本仓既有）`/openllm/v1/chat`** | POST | ✅ 复用 | `assistReview()` | OpenLLM | ✅ |
| — | **（DPS 既有）`POST /portrait/annotations/{id}/review`** | POST | ✅ 复用 | `submitReview()` | ✅ | ✅ |

**结论：10＋2 条调用全部对齐 ✅**

---

## 3. 字段级对齐（关键字段抽查）

| 字段 | 后端／契约 | 前端 | 一致 |
|------|-----------|------|:----:|
| `dry_run`（导入） | 契约 §3.2 必填语义 | **模式单选（默认 dry_run）** | ✅ |
| `conflict_policy` | `overwrite｜skip｜rename` | 三选一呈现 | ✅ |
| `package_hash` | 幂等依据 | 透传（前端不生成） | ✅ |
| `target_version`（回滚） | 契约 §3.3 | 版本选择器 | ✅ |
| `basis` | 契约 §3.7 必返 | **折叠/气泡呈现（默认收起；`tag_count=0` 强制展开）** | ✅ |
| `disclaimer`（建议） | 契约 §3.5 | **原样呈现**（不改写） | ✅ |
| `review_status` | `pending` → `approved`/`rejected` | 候选列表状态位 | ✅ |
| 影响面三层维度 | `template_code`／`annotation_template_code`／`tag_code` | 三选一 | ✅ |
| `field_key` | **显式不支持 → 400** | 不提供该输入项 ＋ 400 文案兜底 | ✅ |

---

## 4. 错误码对齐

| code | 语义（契约 ＋ 实现） | 后端 | 前端呈现 | 一致 |
|:----:|---------------------|:----:|----------|:----:|
| 400 | 参数非法／`format_version` 不支持／依赖缺失／未注册评分类型／非法标签／**`field_key` 不支持** | 透传 | 语义文案 | ✅ |
| 401 | 缺身份／组织／租户标识（fail-closed） | 透传 | 「未登录/标识缺失」 | ✅ |
| 403 | 权限不足／**AI 通道未启用** | 透传 | 「无权限」／「未启用（非报错）」 | ✅ |
| 404 | 模板／版本／标注／**谱系不存在** | 透传 | 「未找到」 | ✅ |
| **409** | **code 冲突未指定策略**／非法版本流转／**未复核候选进入标签·画像路径**（实现 `routes_profiles.py:715`） | 透传 | 冲突文案（两场景区分） | ✅ |
| 422 | 包结构非法（白名单） | 透传 | 「包结构非法」 | ✅ |
| 503 | **AI 适配器不可用（降级非阻塞）** | 透传 | 「暂不可用」＋「人工路径不受影响」 | ✅ |
| 5xx／不可用 | — | 保语义 | **明确提示 ＋ 重试（不静默降级）** | ✅ |

**结论：8 类（含兜底）全部对齐 ✅**

---

## 5. 身份与安全头对齐

| 项 | 后端 | 前端 | 一致 |
|----|------|------|:----:|
| 身份头 | 四头 ＋ `X-Proxy-Source` ＋ `X-Request-Id`（**proxy 注入**） | **构造 0 个头**（不参与） | ✅ |
| 前端密钥 | — | **零密钥**（不持有） | ✅ |
| 权限判定 | 上游裁决 | **不判定**，仅呈现 403 | ✅ |
| org 传值 | `org_value_map` 命中 → 真 org；否则 = tenant | — | ✅（**P1 联调前置**） |
| **`enforce_org_alias`** | **必须 `False`** | — | ✅ |

---

## 6. 对齐结论与移交

| 项 | 结论 |
|----|------|
| 端点对齐 | ✅ 10/10 ＋ 复用 2 |
| 字段对齐 | ✅ 关键字段 9/9 |
| 错误码对齐 | ✅ 8 类全对齐 |
| 身份安全对齐 | ✅ 5/5 |
| **页面↔端点映射** | ✅ **100%**（DT-23／AC-18） |
| **阻断项** | **无** |
| **Step 3 前置待办** | ① 配 `dps_org_map`（P1）② 保持 `enforce_org_alias=False` ③ DPS 侧预置 org／tenant 记录 ④ 联调账号（R11） |

---

## 7. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-09-29 | AA-OpenBase-Dev | 初始创建（Step 2 §2.9 产出）：**端点级对齐 12 条**（10 新增 ＋ 2 复用，全部 ✅）；**字段级对齐 9 项**（含 `dry_run`／`basis`／`disclaimer`／`field_key` 等易漂移字段）；**错误码对齐 8 类**（含 **409 双语义**与 503 降级语义）；**身份与安全头对齐 5 项**（前端零头零密钥、**`enforce_org_alias` 必须 False**）；**对齐结论**（**无阻断项**；列 4 项 Step 3 前置待办）。状态 [Review]。 |
