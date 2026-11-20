# Spec：DPS 降级项 A6/A9/A10/A11/A12/A14 后端能力

| 项 | 值 |
|---|---|
| 状态 | **[Review] 待人工批准** |
| 日期 | 2026-11-20 |
| 目标版本 | DPS **v2.14.0** ／ OpenBase **v1.5.0** |
| 形式化需求 | `DPS/doc/requirements/DPS-开发需求文档-v2.14.0.md`；`OpenBase/doc/requirements/OpenBase-开发需求文档-v1.5.0.md` |
| 追溯 | 两仓 `*-需求追溯矩阵-v*.md` |
| 门禁 | 需求批准后方可进入 Step 2 设计；设计批准后方可编码 |

## 1. 问题

统一前端 Phase 1～3 有 6 项能力因上游缺接口而降级：A6 主体检索、A9 标签检索/分页、A10 审计时间线、A11 标注/画像导出、A12 口径修复建议、A14 AI 候选持久化。目标是把它们落为真实后端能力并接入前端，同时保持 DPS 未升级时的优雅回退。

## 2. 决策（已确认）

| # | 决策 |
|:-:|---|
| D1 | 两仓协同：DPS 做 A6/A9/A10/A12；OpenBase 做 A11/A14＋代理＋前端接入 |
| D2 | 六项一次交付，五步流程从需求起，每步人工门禁 |
| D3 | DPS 版本 v2.14.0（v2.13.0 已被评分口径统一占用）；OpenBase v1.5.0 |
| D4 | A9 返回扁平标签值＋分类元数据；A10 新增 `/audit` 且 `/audit/logs` 加 `resource_id`；A6 复用 `search_portraits_advanced` |
| D5 | A11 同步流式 CSV，10000 行上限；A14 候选批次落 OpenBase 库 |

## 3. 契约（decision-complete）

### 3.1 DPS

| 端点 | 参数 | 行为 |
|---|---|---|
| `GET /api/v2/portrait/list` | `page,page_size,keyword?,external_id?` | keyword 模糊匹配 person_id/姓名/external_id；external_id 精确；缺省行为不变；total 为过滤后总数 |
| `GET /api/v2/tags` | `page,page_size,keyword?,category_id?` | 扁平标签值＋分类元数据＋`parent_value_id`；total 准确；空 200 |
| `GET /api/v2/audit` | `entity_type,entity_id,page,page_size,order?` | 映射 resource_type/resource_id；asc/desc；未知实体 200 空；回显实体键 |
| `GET /api/v2/audit/logs` | 既有 ＋ `resource_id?` | 旧行为不变 |
| `GET /api/v2/portrait/governance/scoring-consistency` | 既有 | issue 增 `suggestion`、`fix_target{portrait_template,annotation_template,field_key,tag_code}` |

### 3.2 OpenBase

| 端点 | 行为 |
|---|---|
| `GET /api/v1/dps-proxy/portraits` | 转发 `page,page_size,keyword,external_id`；状态码保真 |
| `GET /api/v1/dps-proxy/tags` | 转发 `keyword,category_id,page,page_size` → DPS `/api/v2/tags` |
| `GET /api/v1/dps-proxy/audit` | 转发 `entity_type,entity_id,page,page_size,order` → DPS `/api/v2/audit` |
| `GET /api/v1/dps-proxy/audit/logs` | 增加 `resource_id` 透传 |
| `GET /api/v1/dps-proxy/annotations/export` | CSV：列集固定；UTF-8 BOM；RFC4180 转义；`= + - @` 前缀 `'`；文件名 `annotations-<ts>.csv`；≤10000 行；`X-Export-Truncated` |
| `GET /api/v1/dps-proxy/portraits/export` | 同上，画像列集；支持 `keyword,external_id` |
| `POST /api/v1/dps-proxy/annotation-candidates` | 调 DPS 生成 → 落库 `dps_annotation_candidate` → `{batch_id,candidate}`；幂等键 `(tenant_id,upstream_annotation_id)` |
| `GET /api/v1/dps-proxy/annotation-candidates?batch_id=` | 按批次返回 `{batch_id,items,total}` |
| `GET /api/v1/dps-proxy/annotation-candidates/latest` | 最近批次；空 200 |

### 3.3 前端

`DpsAnnotationAdapterView.vue`（持久化生成＋恢复）、`PortraitList.vue`／`PortraitSearch.vue`／`DpsMeasureView.vue`（服务端主体检索）、`DpsTagSystemView.vue`（服务端标签检索）、`DpsAnnotationWorkbenchView.vue`（审计时间线）、导出按钮（后端 CSV）。所有接入在捕获上游 404 时回退既有本地降级路径。

## 4. 文件级改动

### DPS
- `src/rest_api/routes/routes_profiles.py`：`api_list_portraits` 加参并调用 `search_portraits_advanced`。
- `src/rest_api/routes/routes_tags.py`：新增 `GET /tags`。
- `src/rest_api/routes/routes_admin.py`：新增 `GET /audit`；`api_audit_logs` 加 `resource_id`。
- `src/engines/audit_log_engine.py`：`query` 加 `resource_id`。
- `src/engines/scoring_consistency.py`：`_issue` 增 `suggestion`／`fix_target`，补 7 类问题码文案。
- `src/tests/`：新增 `test_v2_14_requirements.py`（或等价命名）。

### OpenBase（后端）
- `openbase/modules/dps_proxy/__init__.py`：代理参数转发、`/tags`、`/audit`、两个 CSV 导出、三个候选端点。
- `openbase/modules/dps_proxy/candidate_store.py`（新）：SQLAlchemy 模型＋存储函数。
- `openbase/modules/logs/router.py`：复用/抽取 CSV 工具（不改变既有导出行为）。
- `tests/`：新增代理、导出、候选存储测试。

### OpenBase（前端）
- `openbase-ui/src/core/api/dps.ts`：新增 API 封装。
- 6 个页面组件按 §3.3 接入。
- 前端测试：新增/扩展 spec。

## 5. 验证

```powershell
# DPS
cd "D:\Trae CN\myproject\Dev\DPS"
python -m ruff check src
python -m pytest src/tests -q

# OpenBase 后端
cd "d:\Trae CN\myproject\Dev\OpenBase"
python -m ruff check openbase tests
python -m pytest tests -q

# OpenBase 前端
cd "d:\Trae CN\myproject\Dev\OpenBase\openbase-ui"
node node_modules/vue-tsc/bin/vue-tsc.js --noEmit
node node_modules/vitest/vitest.mjs run <新增/相关 spec>
npm run build
```

必须通过：DPS 全量回归零新增失败；OpenBase 后端/前端测试全通过；类型与 lint 0 错误；导出/候选/租户隔离用例有证据。

## 6. 非目标

- 不做权限模型变更、不做 DPS 表结构变更、不做异步导出任务、不做页面视觉重设计。
- 不把候选或导出内容写入日志。

## 7. 批准

用户明确批准两仓需求文档后：状态改 [Approved]，进入 Step 2 设计；未批准前不得编码。
