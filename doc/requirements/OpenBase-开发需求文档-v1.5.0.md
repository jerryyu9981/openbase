# OpenBase-开发需求文档-v1.5.0

## 文档信息

| 项 | 内容 |
|----|------|
| 文档名称 | OpenBase 开发需求文档 |
| 文档编号 | OpenBase-REQ-v1.5.0 |
| 版本 | **v2.0.0** |
| 状态 | **[Approved]**（2026-11-20 用户批准 Spec，需求基线冻结为 `v1.5.0-REQ-Baseline-v1.0.0`，准予进入 Step 2 设计） |
| 日期 | 2026-11-20 |
| 主题 | **DPS 降级项 A11/A14 后端能力落地 ＋ A6/A9/A10/A12 代理与前端接入** |
| 编制人 | BA-OpenBase-Dev（需求分析岗） |
| 复核 | PM／AA／AD／AT／AU（OpenBase 角色组） |
| 上游依据 | 《OpenBase-DPS 统一前端页面功能设计》**v2.3.0 [Implemented]** §9／§12／§14；用户 2026-11-20 指令；同轮《DPS-开发需求文档-v2.14.0》**v2.0.0 [Approved]**；源码事实核对（2026-11-20） |
| 需求总数 | **FR 8 条 ＋ NFR 7 条 ＋ 接口与集成 4 条 ＋ 数据需求 2 条 ＋ 权限与安全 3 条 ＋ 约束与排除 1 条 ＝ 25 条**（对应 `RT-150-001~025`） |
| 存放 | `doc/requirements/` |
| 版本基线说明 | 当前包版本 `openbase/__init__.py` 与 `openbase-ui/package.json` 均为 `1.4.12`；本轮新增后端能力与前端接入，按 Minor 升为 **v1.5.0** |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-11-20 | BA-OpenBase-Dev | 首版：承接 A11（标注/画像 CSV 导出）与 A14（AI 标注候选持久化），并补齐 A6/A9/A10/A12 代理与前端接入；给出 8 条 FR、7 条 NFR、25 条可追溯需求与 14 条验收标准；明确与 DPS v2.14.0 的交付边界与降级兼容策略 |
| **v2.0.0** | 2026-11-20 | BA-OpenBase-Dev | **人工批准留痕**：用户批准 Spec（覆盖五步连续推进）⇒ 状态 [Review] → **[Approved]**，需求基线冻结为 `v1.5.0-REQ-Baseline-v1.0.0`；FR／NFR／AC 内容未变 |

---

## 1. 背景、目标与范围

### 1.1 背景

统一前端 Phase 1～3 交付时，A6/A9/A10/A11/A12/A14 六项因后端能力缺失按「明示降级、不造假数据」实现（设计 §12）。DPS v2.14.0 承接 A6/A9/A10/A12 数据能力后，本仓需要：

1. 把新增/扩展接口**代理**给前端（含查询参数与错误语义保真）；
2. 独立落地 **A11 导出**（不由 DPS 承接）；
3. 独立落地 **A14 候选持久化**（刷新不丢）；
4. 前端从降级路径切换到服务端路径，同时保留 DPS 未就绪时的**优雅回退**。

### 1.2 目标（可衡量）

| 编号 | 目标 | 可衡量判据 |
|:----:|------|------------|
| B1 | 四项能力**代理可用** | 代理参数透传与错误保真用例通过（AC-150-01/03/04） |
| B2 | 导出**服务端生成** | 标注/画像 CSV 可下载，列集稳定、转义正确（AC-150-05/06/07/08） |
| B3 | AI 候选**刷新不丢** | 生成后按 `batch_id`／`latest` 可重查（AC-150-09/10/11） |
| B4 | **优雅回退** | DPS 未就绪（上游 404/503）时前端仍可用既有降级路径（AC-150-02） |
| B5 | **零回归** | 既有代理路径与 117 例前端回归全通过（AC-150-13/14） |

### 1.3 源码事实（2026-11-20 核对）

| # | 事实 | 位置 |
|:-:|------|------|
| F1 | DPS 代理为透传层，画像列表端点未显式转发 `keyword`/`external_id` | `openbase/modules/dps_proxy/__init__.py` L347-362 |
| F2 | 已有标签分类代理，但无统一标签检索代理 | 同上 L598-653 |
| F3 | 已有 `/audit/logs` 代理，未转发 `resource_id`；无 `/audit` 时间线代理 | 同上 L686-693 |
| F4 | 已有标注队列/审核/生成代理，但 AI 候选响应无持久化落点 | 同上 L1596-1750 |
| F5 | 本仓已有 CSV 导出参考实现（流式响应、文件名、转义） | `openbase/modules/logs/router.py`（`/api/v1/logs/export`） |
| F6 | 前端 AI 候选页候选仅组件内存态 | `openbase-ui/src/modules/portrait/pages/DpsAnnotationAdapterView.vue` |
| F7 | 前端画像列表/搜索/措施/标签/审核页均存在本地降级路径 | `PortraitList.vue`、`PortraitSearch.vue`、`DpsMeasureView.vue`、`DpsTagSystemView.vue`、`DpsAnnotationWorkbenchView.vue` |

### 1.4 范围

| 范围内 | 范围外 |
|---|---|
| 代理扩展（A6/A9/A10）与 A12 字段透传 | DPS 上游 A6/A9/A10/A12 实现（DPS v2.14.0） |
| A11 标注/画像 CSV 导出（本仓生成） | Excel/PDF 导出、邮件订阅 |
| A14 候选批次持久化（本仓库表） | DPS 侧候选表结构变更 |
| 前端 6 处接入与回退 | 页面视觉重设计、路由增删 |
| 单元/组件/回归测试 | 性能压测环境搭建 |

### 1.5 排除项

1. 不新增对外路由记录（沿用既有 `/api/v1/dps-proxy/*` 与新增同前缀子路径）。
2. 不做权限模型变更；前端仍不做权限判定。
3. 不把导出结果写入磁盘或对象存储（流式返回）。
4. 不持久化导出任务（同步导出，超限截断并标记）。
5. 不改变 AI 候选「强制 pending + 人工复核门禁」语义。

---

## 2. 干系人与用户角色

| 角色 | 本版本相关操作 | 权限要点 |
|------|----------------|----------|
| 标注员 | AI 候选生成、刷新恢复、提交复核 | 沿用既有标注域权限 |
| 审核员 | 审核时间线、导出待审清单 | 沿用审计/标注读权限 |
| 业务查看者 | 画像检索、导出画像 CSV | 画像读权限 |
| 模板治理者 | 口径问题「去修复」跳转 | 只读 |
| 运维 | 候选表留存与排障 | 不接触明文候选字段日志 |

---

## 3. 业务流程

### 3.1 A6/A9/A10 代理透传

```
前端请求 /api/v1/dps-proxy/{能力}
   ↓
① 鉴权（沿用 get_current_user）＋组装身份头
② 原样转发查询参数（page/page_size/keyword/external_id/category_id/entity_*/order）
③ 上游响应状态码与包络保真返回
   ↓
④ 上游 404（DPS 未升级） → 前端捕获并回退本地降级路径
⑤ 上游 5xx/超时 → 502/503，前端展示受控错误态
```

### 3.2 A11 CSV 导出（本仓生成）

```
用户点击「导出」
   ↓
① 校验筛选参数（page_size 固定 100，最大 10000 行）
② 循环调用 DPS 列表接口分页拉取（标注 / 画像）
③ 逐行序列化为 CSV（UTF-8 BOM；转义；注入前缀防护）
   ↓
④ 流式返回 text/csv + Content-Disposition 文件名
⑤ 超限 → 截断并在响应头标记 X-Export-Truncated=true
⑥ 空结果 → 仅表头，HTTP 200
```

### 3.3 A14 候选持久化

```
用户生成 AI 候选
   ↓
① 前端调用 POST /dps-proxy/annotation-candidates（可带 batch_id）
② 后端调用 DPS 生成端点 → 得到 upstream_annotation_id/fields/review_status
③ 落库 dps_annotation_candidate（tenant/operator/batch/adapter/template/fields_json）
   ↓
④ 返回 {batch_id, candidate}；同 upstream_annotation_id 幂等（不重复落库）
   ↓
⑤ 刷新页面 → GET ...?batch_id= 或 /latest → 恢复候选列表
```

---

## 4. 功能需求（FR）

| 编号 | 需求 | 优先级 | 来源 | 验收 |
|------|------|:------:|------|------|
| **FR-150-01** | `GET /api/v1/dps-proxy/portraits` 转发 `page`、`page_size`、`keyword`、`external_id`；响应包络与状态码保真 | P0 | A6 | AC-150-01/02 |
| **FR-150-02** | 新增 `GET /api/v1/dps-proxy/tags`，转发 `keyword`、`category_id`、`page`、`page_size`，对应 DPS `GET /api/v2/tags` | P0 | A9 | AC-150-03 |
| **FR-150-03** | 新增 `GET /api/v1/dps-proxy/audit`，转发 `entity_type`、`entity_id`、`page`、`page_size`、`order`；`/audit/logs` 增加 `resource_id` 透传 | P0 | A10 | AC-150-04 |
| **FR-150-04** | 新增 `GET /api/v1/dps-proxy/annotations/export`：按 `annotation_template`、`review_status`、`person_id` 过滤，CSV 流式导出（UTF-8 BOM、转义、注入防护、文件名、最多 10000 行） | P0 | A11 | AC-150-05/07/08 |
| **FR-150-05** | 新增 `GET /api/v1/dps-proxy/portraits/export`：按 `keyword`、`external_id` 过滤，CSV 流式导出，规则同 FR-150-04 | P0 | A11 | AC-150-06/07/08 |
| **FR-150-06** | A14 持久化：`POST /api/v1/dps-proxy/annotation-candidates`（生成并落库）、`GET .../annotation-candidates?batch_id=`、`GET .../annotation-candidates/latest`；同租户同 `upstream_annotation_id` 幂等 | P0 | A14 | AC-150-09/10 |
| **FR-150-07** | 前端接入：AI 候选页改持久化接口并在挂载时恢复；画像列表/搜索/措施主体选择器改用服务端检索；标签页改用 `/tags`；审核时间线改用 `/audit`；导出按钮改调后端 CSV；**全部保留上游 404 时本地降级** | P0 | A6/A9/A10/A11/A14 | AC-150-11/02 |
| **FR-150-08** | 错误与降级：上游 404 原样透传（不包装为 500）；超时/连接失败映射 502/503；前端按受控错误态呈现，不白屏 | P1 | 通用 | AC-150-02/12 |

### 4.1 A11 导出契约

| 项 | 规定 |
|---|---|
| 路径 | `GET /api/v1/dps-proxy/annotations/export`、`GET /api/v1/dps-proxy/portraits/export` |
| 鉴权 | `get_current_user`，沿用既有 JWT |
| 参数 | annotations：`annotation_template`、`review_status`、`person_id`；portraits：`keyword`、`external_id` |
| 媒体类型 | `text/csv; charset=utf-8` |
| 文件名 | `annotations-YYYYMMDDHHmmss.csv` / `portraits-YYYYMMDDHHmmss.csv` |
| 编码 | UTF-8 with BOM（Excel 兼容） |
| 行上限 | 10000 行；截断时响应头 `X-Export-Truncated: true`，否则 `false` |
| 空结果 | 仅表头，HTTP 200 |
| 列集（标注） | `annotation_id,person_id,profile_id,annotation_template,review_status,review_level,review_levels_required,created_at,updated_at,fields_json` |
| 列集（画像） | `person_id,name,status,person_type,region,external_id,created_at,updated_at` |
| 安全 | 以 `= + - @`／制表符／回车开头的单元格前置 `'`；字段含逗号/引号/换行时按 RFC4180 加引号并双写引号 |

### 4.2 A14 持久化契约

| 项 | 规定 |
|---|---|
| 表 | `dps_annotation_candidate`（SQLAlchemy 模型，幂等 `create_all`） |
| 主键 | `id`（UUID 字符串） |
| 关键列 | `batch_id`、`tenant_id`、`operator`、`adapter_id`、`annotation_template`、`upstream_annotation_id`、`review_status`、`person_id`、`profile_id`、`fields_json`、`created_at` |
| 唯一约束 | `(tenant_id, upstream_annotation_id)` |
| 生成请求 | `{adapter_id, text, annotation_template, person_id?, profile_id?, batch_id?}`；缺 `batch_id` 时服务端生成 UUID |
| 生成响应 | `{batch_id, candidate:{id, upstream_annotation_id, fields, review_status, adapter_id}}` |
| 查询 | `GET ...?batch_id=` 返回 `{batch_id, items, total}`；`GET .../latest?adapter_id=&annotation_template=` 返回最近批次（无数据返回 `items=[]`，200） |
| 幂等 | 同租户同 `upstream_annotation_id` 重复生成 → 返回既有记录，不新增行 |
| 日志 | **禁止**记录 `fields_json`／`text` 原文 |

---

## 5. 非功能需求（NFR）

| 编号 | 类别 | 要求 | 验收 |
|------|------|------|------|
| NFR-150-01 | 性能 | 导出 1000 行 P95 ≤ 3s（Dev 内网）；代理请求额外开销 ≤ 50ms | 基准记录 |
| NFR-150-02 | 流式 | 导出使用流式响应，不在内存拼接完整文件 | 代码审查 |
| NFR-150-03 | 安全 | CSV 注入防护 + BOM；导出内容与候选字段不落日志 | 用例＋日志抽查 |
| NFR-150-04 | 租户隔离 | 候选表按 `tenant_id` 过滤；禁止跨租户读取 | 双租户用例 |
| NFR-150-05 | 兼容 | 既有 `/dps-proxy/*` 路径与响应不变；新增参数全可选 | 全量回归 |
| NFR-150-06 | 可观测 | 结构化日志记录导出条数、截断标记、候选批次号；不含敏感内容 | 日志抽查 |
| NFR-150-07 | 可维护 | 新增模块遵循分层：路由→服务→存储；禁止路由内拼 SQL | 静态检查 |

---

## 6. 接口与集成需求

| 编号 | 要求 |
|------|------|
| INT-150-01 | DPS 契约以《DPS-开发需求文档-v2.14.0》§4.1 为准；本仓不自定义字段名 |
| INT-150-02 | 代理查询参数采用白名单转发，不转发身份头以外的前端头 |
| INT-150-03 | 上游不可达时错误码：连接失败/超时 → 503；上游 5xx → 502；上游 4xx → 保真 |
| INT-150-04 | 前端 API 封装集中在 `src/core/api/dps.ts`，页面不直连 axios |

---

## 7. 数据需求

| 编号 | 要求 |
|------|------|
| DATA-150-01 | 新增 1 张表 `dps_annotation_candidate`；建表幂等（`create_all` / `WHERE NOT EXISTS` 口径） |
| DATA-150-02 | 无存量数据迁移；表为空时查询返回空集合；不修改既有表结构 |

---

## 8. 权限与安全需求

| 编号 | 要求 |
|------|------|
| SEC-150-01 | 全部新增端点要求登录态；不新增权限资源类型，沿用既有域权限 |
| SEC-150-02 | 候选落库字段可能含个人信息；接口响应按租户隔离，日志脱敏 |
| SEC-150-03 | 导出接口只允许当前租户数据；文件名不含租户/用户标识 |

---

## 9. 约束与排除

| 编号 | 内容 |
|------|------|
| CON-150-01 | 必须与 DPS v2.14.0 契约一致；DPS 未部署时前端回退既有降级路径，不得白屏 |
| CON-150-02 | 不新增 npm/pip 依赖 |
| CON-150-03 | 不改变既有路由记录与导航结构 |
| CON-150-04 | 排除 DPS 上游实现、权限模型变更、导出任务异步化 |
| CON-150-05 | 所有新增代码须附测试；覆盖率不低于项目基线 |

---

## 10. 验收标准（AC）

| 编号 | 验收标准 | 关联 FR |
|------|----------|---------|
| **AC-150-01** | `/dps-proxy/portraits?keyword=&external_id=` 参数完整转发，上游 200 包络原样返回 | FR-150-01 |
| **AC-150-02** | 上游 404/503 时前端回退本地降级路径，页面可用、无白屏、错误态受控 | FR-150-01/08 |
| **AC-150-03** | `/dps-proxy/tags` 转发关键字/分类/分页，返回 `items/total/page/page_size` | FR-150-02 |
| **AC-150-04** | `/dps-proxy/audit` 转发实体与排序参数；`/audit/logs?resource_id=` 生效且旧参数不变 | FR-150-03 |
| **AC-150-05** | 标注 CSV 含规定列集、UTF-8 BOM、正确转义与注入前缀；文件名符合规范 | FR-150-04 |
| **AC-150-06** | 画像 CSV 支持 `keyword`/`external_id` 过滤，导出结果与列表一致 | FR-150-05 |
| **AC-150-07** | 空结果导出仅表头、HTTP 200 | FR-150-04/05 |
| **AC-150-08** | 超过 10000 行时截断且 `X-Export-Truncated=true` | FR-150-04/05 |
| **AC-150-09** | 生成候选后按 `batch_id` 与 `latest` 均可重查；刷新恢复列表 | FR-150-06/07 |
| **AC-150-10** | 同租户重复生成幂等；跨租户不可见；无敏感字段日志 | FR-150-06 |
| **AC-150-11** | 前端 6 处接入完成：AI 候选、画像列表、画像搜索、措施建议、标签体系、审核时间线 | FR-150-07 |
| **AC-150-12** | 上游超时/连接失败映射 502/503，前端呈现受控错误 | FR-150-08 |
| **AC-150-13** | 既有 117 例前端回归全通过；新增后端单测全通过 | FR-150-01~08 |
| **AC-150-14** | `vue-tsc --noEmit`、`eslint`、`ruff` 均 0 错误；`npm run build` 通过 | FR-150-01~08 |

---

## 11. 交付边界（与 DPS v2.14.0）

| 能力 | DPS v2.14.0 | OpenBase v1.5.0 |
|---|---|---|
| A6 | `keyword`/`external_id` 服务端检索 | 代理透传；前端列表/搜索/措施接入 |
| A9 | `GET /tags` | 代理；标签体系页接入 |
| A10 | `GET /audit`、`/audit/logs?resource_id=` | 代理；审核时间线接入 |
| A12 | issue 补 `suggestion`/`fix_target` | 字段透传；「去修复」消费 |
| A11 | — | CSV 导出 ＋ 前端按钮 |
| A14 | — | 候选持久化 ＋ 前端恢复 |

**上线顺序**：OpenBase 可先发布（A11/A14 独立可用；A6/A9/A10 代理自动回退）；DPS v2.14.0 发布后四项能力自动生效，无需 OpenBase 再发版。

---

## 12. 追溯

需求 → 设计 → 测试的追溯见《OpenBase-需求追溯矩阵-v1.5.0》；评审与门禁见《OpenBase-需求评审记录-v1.5.0》。
