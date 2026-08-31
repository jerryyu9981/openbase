# OpenBase DevLogReport - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/development/ |

---

## 1. 版本记录与入场检查（3.0）

| 项 | 内容 |
|----|------|
| 开发范围 | FR-145-01~06（R-381 DPS 对接：服务部署/认证边界与身份头注入/dps-proxy 转发/前端画像 2 页/联调/收尾还债） |
| 入场确认 | Step 2 设计评审通过 + 需求架构对比审计通过（DT-ID 6/6）✅ |
| 基线 | v1.4.4（已发布）；本版本基于 main 开发 |
| 实现计划 | TD-ID 矩阵（doc/development/OpenBase-设计开发追溯矩阵-v1.4.5.md） |

## 2. 实现内容（3.3）

### 2.1 后端（TD-145-02/03）

| 文件 | 变更 | 说明 |
|------|------|------|
| `openbase/settings.py` | 修改 | AVAILABLE_MODULES 注册 `dps_proxy`；新增 dps_upstream_base（http://127.0.0.1:8030）/dps_upstream_timeout/dps_default_org_id/dps_default_tenant_id/dps_org_map/dps_tenant_map；无 dps_api_key |
| `openbase/demo_app.py` | 修改 | enable_module 追加 `dps_proxy` |
| `openbase/modules/dps_proxy/__init__.py` | 新建 | 8 端点（画像列表/详情/计算、标签分类、报表概览、批量任务状态、审计日志、health）；`_build_identity_headers`（四头注入 + 映射 + 兜底）/`_adapt_response`（统一响应 + {detail} str/dict/list 归一化）/`_forward`/`_jwt_payload`（解码 JWT 取 org_id/role）；无 SSE |
| `tests/test_dps_proxy.py` | 新建 | 15 用例（401×2/四头注入×2/端点×7/归一化×3/502/health） |

### 2.2 前端（TD-145-04/06）

| 文件 | 变更 | 说明 |
|------|------|------|
| `openbase-ui/src/core/api/dps.ts` | 新建 | dpsApi 8 方法（画像/标签/报表/批量/审计/health） |
| `openbase-ui/src/modules/portrait/pages/PortraitList.vue` | 改造 | mock → 真实 API（列表 + KPI + 搜索/分页 + 加载/错误态） |
| `openbase-ui/src/modules/portrait/pages/PortraitDetail.vue` | 改造 | mock → 真实 API（基本信息 + 标签 + 维度展示 + 加载/错误态） |
| `openbase-ui/src/core/api/llm.ts` | 修改 | **还债 TD-新增-011**：sendChatStream 对齐 `adapter: 'fetch'`（浏览器端真流式） |

## 3. 静态质量检查（3.4）

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 后端 Lint/静态 | `python -m ruff check openbase tests` | ✅ All checks passed（F401 已修复） |
| 后端全量测试 | `python -m pytest tests` | ✅ 全量通过（含 15 dps 用例） |
| 前端类型 + 构建 | `npm run build`（vue-tsc + vite） | ✅ built（0 error） |
| 技术债务增长率 | 新增 TODO 0；高复杂度增量 0；重复率无增量 | ✅ 阈值内 |

## 4. 实际运行验证（3.5）

### 4.1 L1 构建

| 端 | 证据 |
|----|------|
| 后端 | `python -m ruff check openbase tests` → All checks passed |
| 前端 | `npm run build` → `✓ built`（dist 产物生成） |

### 4.2 L2 启动

| 服务 | 端口 | 证据 |
|------|------|------|
| OpenBase（demo_app，含 dps_proxy） | 8000 | `Uvicorn running on http://127.0.0.1:8000`（内存降级 admin/admin123） |
| DPS | 8030 | ⚠️ 启动受阻（config.settings 缺失，任务书 M4；沙箱写限制） |

### 4.3 L3 冒烟（smoke_v145.py，11 passed / 0 failed）

| # | 场景 | 结果 |
|---|------|------|
| 1-3 | 未认证 401 + 登录 + 无效 token 401 | ✅ |
| 4-11 | 8 端点上游不可达 → 502 SYS_502 归一化 | ✅ |

## 5. 开发自测（3.6）

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 单元测试 | `python -m pytest tests/test_dps_proxy.py` | ✅ 15 passed |
| 全量回归 | `python -m pytest tests` | ✅ 全通过 |
| 冒烟 | smoke_v145.py | ✅ 11/11 |

## 6. 代码逻辑审查（3.7）

审查结论：**有条件通过**（详见 doc/development/OpenBase-代码逻辑审查记录-v1.4.5.md）。

| 发现 | 级别 | 处理 |
|------|:----:|------|
| L-145-01 DPS 侧 config.settings 缺失（第三方） | P2 | 登记任务书 M4；OpenBase 侧 502 归一化兜底 |
| L-145-02 X-User-ID 防御性兜底 | P3 | 记录，不阻塞 |
| L-145-03 日志不含四头（合规） | P3 | 记录 |

## 7. 技术债务

| 债务 ID | 级别 | 内容 | 状态 |
|---------|:----:|------|------|
| TD-新增-011 | P2 | llm.ts SSE 浏览器端假流式 | ✅ **已偿还**（fetch adapter 对齐，v1.4.5） |
| TD-新增-012 | P1 | OpenRAG 上游契约缺口 M1~M6 | 继续挂起（任务书跟踪，不在本版本范围） |

> 技术债务总表需同步 TD-新增-011 状态为已偿还（§0.0a 还债闭环）。

## 8. 设计偏差与记录

| ID | 偏差 | 依据 | 处理 |
|----|------|------|------|
| D1 | 四头注入需解码 JWT 补取 org_id/role（get_current_user 精简字段不含） | API 设计 §2 映射规则 | 实现 `_jwt_payload` 补取，符合设计意图（非偏差，实现细节） |

## 9. 已知风险与开放问题

1. DPS 侧 config 缺陷（M4）→ 真实联调留 Step 4/5（DPS 修复后补测）。
2. 组织/租户映射实际值（OQ-145-1）→ 映射逻辑单测覆盖，实际值 Step 4 联调确认。
3. DPS 沙箱写限制（__pycache__）→ 部署环境（沙箱外）验证。

## 10. 测试移交说明（3.10 前置）

| 项 | 内容 |
|----|------|
| 测试环境 | OpenBase 8000（uvicorn demo_app，含 dps_proxy）；DPS 8030（待 M4 修复）；前端 5173（vite dev） |
| 启动命令 | OpenBase 同 §4.2；DPS `$env:API_PORT='8030'; $env:SQLITE_FALLBACK='true'; python -m uvicorn rest_api.app:app --app-dir src`（需修复 config.settings） |
| 测试数据 | admin/admin123；组织/租户种子（OQ-145-1 联调确认） |
| Mock 说明 | dps_proxy 单测全部 httpx mock（tests/test_dps_proxy.py）；无其他 mock |
| 已知风险 | DPS 未就绪 → 502 归一化预期；真实联调待 M4 |
| 建议回归范围 | llm_proxy（SSE 还债改动）、rag_proxy、memory_proxy、auth（无回归，全量通过） |

## 11. 产出物存在性验证（3.10 门禁）

| 产出物 | 存在性 |
|--------|:------:|
| `openbase/modules/dps_proxy/__init__.py` | ✅ |
| `tests/test_dps_proxy.py` | ✅ |
| `openbase-ui/src/core/api/dps.ts` | ✅ |
| PortraitList.vue / PortraitDetail.vue / llm.ts | ✅ |
| doc/development/OpenBase-设计开发追溯矩阵-v1.4.5.md | ✅ |
| doc/development/OpenBase-代码逻辑审查记录-v1.4.5.md | ✅ |

## 12. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | AD-OpenBase-Dev | 初始创建：dps-proxy 8 端点 + 四头注入 + 前端 2 页 + 还债 TD-新增-011 + L3 冒烟 11/11 + 逻辑审查（有条件通过）+ DPS 启动受阻登记 M4 |
