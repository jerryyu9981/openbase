# OpenBase-DPS降级项后端能力补齐-设计文档-v1.0.0

## 文档信息

| 项 | 内容 |
|----|------|
| 文档名称 | OpenBase-DPS 降级项后端能力补齐设计文档 |
| 文档编号 | OpenBase-DES-v1.5.0 |
| 版本 | **v1.0.0** |
| 状态 | **[Approved]**（2026-11-20 随 Spec 批准；设计评审见 §8） |
| 日期 | 2026-11-20 |
| 主题 | A11/A14 后端能力 ＋ A6/A9/A10/A12 代理与前端接入 |
| 上游依据 | 《OpenBase-开发需求文档-v1.5.0》**v2.0.0 [Approved]**；《DPS-后端能力补齐设计文档-v2.14.0》**v1.0.0 [Approved]** |
| 作者 | AA-OpenBase-Dev／AD-OpenBase-Dev／FD-OpenBase-Dev |
| 存放 | `doc/design/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-11-20 | AA-OpenBase-Dev | 首版：代理契约、CSV 导出、候选持久化模型、前端接入与回退设计 |

---

## 1. 架构与落点

```
openbase-ui
  core/api/dps.ts（新增 API 封装）
  modules/portrait/pages/*（6 处接入 + 404 回退）
        │
        ▼
OpenBase 后端 /api/v1/dps-proxy/*
  ├─ 透传：portraits / tags / audit / audit(logs)
  ├─ 本仓生成：annotations/export、portraits/export（CSV）
  └─ 本仓持久化：annotation-candidates（表 + 3 端点）
        │
        ▼
DPS /api/v2/*
  ├─ portrait/list（A6）
  ├─ tags（A9）
  ├─ audit、audit/logs（A10）
  ├─ governance/scoring-consistency（A12）
  └─ annotation-adapters/{id}/generate（A14 上游生成）
```

分层：路由只做参数校验与编排；CSV/候选存储逻辑在同模块内部函数；候选表访问集中在 `candidate_store.py`。

## 2. 代理设计

| 端点 | 参数（白名单） | 上游 | 错误 |
|---|---|---|---|
| `GET /portraits` | `page,page_size,keyword,external_id` | `/api/v2/portrait/list` | 4xx 保真；5xx/超时 502/503 |
| `GET /tags` | `keyword,category_id,page,page_size` | `/api/v2/tags` | 同上 |
| `GET /audit` | `entity_type,entity_id,page,page_size,order` | `/api/v2/audit` | 同上 |
| `GET /audit/logs` | 既有 ＋ `resource_id` | `/api/v2/audit/logs` | 同上 |

- 身份头由 `_build_identity_headers` 统一构造；
- 状态码与包络保真（上游 404 不包装为 500），供前端识别并回退；
- 参数采用显式白名单，不透传任意前端头。

## 3. CSV 导出设计（A11）

### 3.1 端点与参数

| 端点 | 参数 | 上游 |
|---|---|---|
| `GET /annotations/export` | `annotation_template,review_status,person_id` | `/api/v2/portrait/annotations` |
| `GET /portraits/export` | `keyword,external_id` | `/api/v2/portrait/list` |

> 路由注册顺序：`/portraits/export` 必须早于 `/portraits/{person_id}`，已在实现与用例中锁定。

### 3.2 生成流程

1. 预检：`page=1,page_size=1` 取 `total`，决定 `X-Export-Truncated`；
2. 逐页拉取（100/页），`page*100 >= total` 或空页停止；
3. 每行立即 `yield`，`StreamingResponse` 输出；
4. 最多 10000 行；超限截断并置 `X-Export-Truncated: true`。

### 3.3 列集

| 导出 | 列 |
|---|---|
| 标注 | `annotation_id,person_id,profile_id,annotation_template,review_status,review_level,review_levels_required,created_at,updated_at,fields_json` |
| 画像 | `person_id,name,status,person_type,region,external_id,created_at,updated_at` |

### 3.4 安全

- UTF-8 BOM；
- 单元格始终双引号包裹，内部 `"` 双写；
- `= + - @ \t \r` 开头前置 `'`；
- 空结果仅表头，HTTP 200；
- 日志只记录 `total/truncated/max_rows`，不记录行内容。

## 4. 候选持久化设计（A14）

### 4.1 模型

表 `dps_annotation_candidate`：

| 列 | 类型 | 约束 |
|---|---|---|
| `id` | String(36) | PK |
| `batch_id` | String(36) | 索引 |
| `tenant_id` | String(64) | 索引 |
| `operator` | String(128) | — |
| `adapter_id` | String(128) | — |
| `annotation_template` | String(128) | — |
| `upstream_annotation_id` | String(64) | 与 tenant 唯一 |
| `review_status` | String(32) | 默认 `pending` |
| `person_id` / `profile_id` | String | 可空 |
| `fields_json` | Text | JSON 字符串 |
| `created_at` | DateTime(tz) | UTC |

建表：随 `Base.metadata.create_all` 启动幂等创建；无存量迁移。

### 4.2 端点

| 端点 | 行为 |
|---|---|
| `POST /annotation-candidates` | 校验 `adapter_id/text` → 调 DPS 生成 → 解析候选 → 幂等落库 → `{batch_id,candidate}` |
| `GET /annotation-candidates?batch_id=` | 租户内按批次返回 `{batch_id,items,total}` |
| `GET /annotation-candidates/latest` | 可选 `adapter_id/annotation_template` 过滤，返回最近批次 |

幂等键：`(tenant_id, upstream_annotation_id)`；并发冲突由唯一约束兜底，冲突后回查既有行。

### 4.3 日志与隐私

只记录 `batch_id/adapter_id/annotation_template/tenant_id`；**禁止**记录 `fields_json` 与 `text`。

## 5. 前端接入设计

| 页面 | 变更 | 回退 |
|---|---|---|
| `DpsAnnotationAdapterView.vue` | 生成改持久化端点；`onMounted` 拉 `/latest` 恢复 | 接口异常静默保留内存态 |
| `PortraitList.vue` | 列表带 `keyword`；导出改后端 CSV | 导出失败回退本地 CSV |
| `PortraitSearch.vue` | 主关键字走服务端检索 | 404 回退全量 + 本地匹配 |
| `DpsMeasureView.vue` | 主体候选取服务端检索 | 404 回退前 100 条本地匹配 |
| `DpsTagSystemView.vue` | 关键字检索走 `/tags` | 404 回退全量 + 本地过滤 |
| `DpsAnnotationWorkbenchView.vue` | 审核留痕为空时用 `/audit`；新增导出按钮 | 404 保持空态 |

统一约定：只在捕获 `response.status === 404` 时回退；403/5xx 仍走受控错误态，避免掩盖真实故障。

## 6. 兼容与上线顺序

1. 本仓可先发布：A11/A14 独立可用；A6/A9/A10 代理在 DPS 未升级时返回上游 404，前端自动回退；
2. DPS v2.14.0 发布后四项能力自动生效，无需本仓再发版；
3. 不新增路由记录、不改导航。

## 7. 测试与证据

| 层 | 用例 |
|---|---|
| 后端 | `tests/test_dps_backend_capabilities_v150.py`（路由顺序/CSV 转义/流式分页/候选序列化） |
| 后端回归 | `python -m pytest tests -q` |
| 前端类型 | `vue-tsc --noEmit` |
| 前端回归 | vitest 相关 spec ＋ 既有 117 例 |
| 构建 | `npm run build` |

## 8. 设计评审

| 检查项 | 结果 |
|---|---|
| 两仓契约字段一致 | ✅ |
| A11 列集/编码/注入防护可验证 | ✅ |
| A14 幂等与租户隔离可验证 | ✅ |
| 前端回退边界收敛（仅 404） | ✅ |
| 分层与命名规范 | ✅ |
| 结论 | **✅ 通过（2026-11-20，随 Spec 人工批准）** |
