# OpenBase-DevLogReport-v1.5.0

## 文档信息

| 项 | 内容 |
|----|------|
| 文档名称 | OpenBase 开发记录报告 |
| 版本 | **v1.0.0** |
| 状态 | **[Review]**（开发完成，待测试验证） |
| 日期 | 2026-11-20 |
| 项目版本 | **v1.5.0** |
| 主题 | DPS 降级项 A11/A14 后端能力 ＋ A6/A9/A10/A12 代理与前端接入 |
| 上游依据 | 《OpenBase-开发需求文档-v1.5.0》v2.0.0 [Approved]；《OpenBase-DPS降级项后端能力补齐-设计文档-v1.0.0》v1.0.0 [Approved] |
| 存放 | `doc/development/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-11-20 | AD-OpenBase-Dev／FD-OpenBase-Dev | 首版：代理扩展、CSV 导出、候选持久化、前端 6 处接入；含文件清单与自测结果 |

---

## 1. 交付摘要

| 需求 | 实现 | 文件 |
|---|---|---|
| FR-150-01（A6） | `GET /dps-proxy/portraits` 转发 `keyword/external_id` | `openbase/modules/dps_proxy/__init__.py` |
| FR-150-02（A9） | 新增 `GET /dps-proxy/tags` | 同上 |
| FR-150-03（A10） | 新增 `GET /dps-proxy/audit`；`/audit/logs` 转发查询参数 | 同上 |
| FR-150-04/05（A11） | 新增 `annotations/export`、`portraits/export`；CSV 流式、BOM、转义、注入防护、10000 行上限 | 同上 |
| FR-150-06（A14） | 新增候选表与 3 个端点（生成落库/按批次/最近批次） | 同上、`openbase/modules/dps_proxy/candidate_store.py`（新） |
| FR-150-07 | 前端 6 处接入：AI 候选恢复、列表/搜索/措施服务端主体检索、标签服务端检索、审核时间线、导出按钮 | `openbase-ui/src/core/api/dps.ts`、6 个页面 |
| 版本 | 后端 1.4.12 → **1.5.0**；前端 1.4.12 → **1.5.0** | `openbase/__init__.py`、`openbase-ui/package.json` |

## 2. 后端实现要点

1. **代理**：显式白名单参数，身份头由 `_build_identity_headers` 构造；上游状态码与包络保真（404 不包装），供前端回退。
2. **CSV**：`_export_response` 先取 `total` 决定 `X-Export-Truncated`，`_stream_export` 逐页（100/页）流式输出；`_csv_cell` 始终双引号包裹并防注入。
3. **候选**：`DpsAnnotationCandidate` 表按 `(tenant_id, upstream_annotation_id)` 唯一；`save_candidate` 冲突回查保证幂等；`fields_json` 仅在响应中解码，日志只记批次元数据。
4. **路由顺序**：`/portraits/export` 注册在 `/portraits/{person_id}` 之前，已由用例锁定。

## 3. 前端实现要点

| 页面 | 变更 |
|---|---|
| `DpsAnnotationAdapterView.vue` | 生成改 `generatePersistedAnnotationCandidate`；`onMounted` 拉 `/latest` 恢复并提示条数 |
| `PortraitList.vue` | 列表带 `keyword`；导出改后端 CSV，失败回退本地 CSV |
| `PortraitSearch.vue` | 主关键字走服务端检索；404 回退全量 + 本地匹配 |
| `DpsMeasureView.vue` | 主体候选取服务端检索；404 回退前 100 条 |
| `DpsTagSystemView.vue` | 关键字检索走 `/tags`；404 回退全量 + 本地过滤 |
| `DpsAnnotationWorkbenchView.vue` | 审核留痕为空时用 `/audit` 时间线；新增导出按钮 |
| `DpsScoringConsistencyView.vue` | 说明列追加 `suggestion` 修复建议 |
| `core/api/dps.ts` | 新增 8 个 API 方法、3 个类型、CSV 头解析 |

## 4. 接口清单（新增/扩展）

| 方法 | 路径 |
|---|---|
| GET | `/api/v1/dps-proxy/portraits`（扩展） |
| GET | `/api/v1/dps-proxy/tags`（新增） |
| GET | `/api/v1/dps-proxy/audit`（新增） |
| GET | `/api/v1/dps-proxy/audit/logs`（扩展） |
| GET | `/api/v1/dps-proxy/annotations/export`（新增） |
| GET | `/api/v1/dps-proxy/portraits/export`（新增） |
| POST/GET | `/api/v1/dps-proxy/annotation-candidates`（新增） |
| GET | `/api/v1/dps-proxy/annotation-candidates/latest`（新增） |

## 5. 数据与安全

- 新增 1 表 `dps_annotation_candidate`，随 `Base.metadata.create_all` 幂等创建；无存量迁移。
- 候选查询强制 `tenant_id`；导出仅当前租户。
- 导出/候选原文不落日志；CSV 注入防护与 BOM。

## 6. 自测

| 项 | 命令 | 结果 |
|---|---|---|
| 后端定向 | `python -m pytest tests/test_dps_backend_capabilities_v150.py -q` | **19 passed** |
| 后端静态 | `python -m ruff check ...` | **All checks passed** |
| 前端类型 | `vue-tsc --noEmit` | **通过** |
| 前端定向 | `vitest run tests/dps-backend-v150.spec.ts ...` | 见 Step 4 测试报告 |
| 构建 | `npm run build` | 见 Step 5 |

## 7. 测试移交

- 重点：CSV 列集/BOM/转义/截断；候选刷新恢复/幂等/租户隔离；DPS 未就绪 404 回退；既有 117 例回归。
- 证据目录：`doc/test/evidence/v1.5.0/`。
