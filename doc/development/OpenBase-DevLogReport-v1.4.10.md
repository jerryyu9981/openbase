# OpenBase 开发记录报告（DevLogReport） - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **本仓**（`openbase` 后端 ＋ `openbase-ui` 前端） |
| 版本号 | **v1.4.10**（承接型小版本「DPS 模板化能力对接深化」） |
| 文档 | 开发记录报告（Step 3 产出 1） |
| 文档版本 | v1.0.0 |
| 状态 | [Review]（Step 3 收尾，待人工批准） |
| 日期 | 2026-10-01 |
| 编制 | AD-OpenBase-Dev（后端）／FD-OpenBase-Dev（前端） |
| 上游依据 | 需求基线 **`v1.4.10-REQ-BL-1.2.0`**（含 D-1410-01／02／03）｜设计基线 **v2.0.0**（[Approved]，2026-09-30 人工批准冻结）｜追溯矩阵 **v1.0.0**（TD-1410-01~35）｜《设计基线及开发测试移交说明》v2.0.0｜《开发入场检查记录》v1.0.0 |
| 开发方式 | 批次化 TDD（RED → GREEN → 相关面回归 → 静态门 → 运行验证 → 文档同步 → 提交） |

---

## 1. 版本目标与增量范围（本版做什么／不做什么）

**版本级原则**（用户口径）：v1.4.10 为**承接型小版本**，落地「**DPS 模板化能力对接深化**」——在 **保持既有 12 条 `dps-proxy` 路由与画像 2 页行为不变**的前提下，**新增 22 个代理端点（10 新增 ＋ 12 补代理）** 并对应交付 **12 个前端页面**。

**实现范围（18 条 Backlog，《本版本Backlog-v1.4.10》v2.0.0）**：

| 段 | Backlog | 内容 | 落点 |
|:--:|:-------:|------|------|
| A | BL-1410-01／18 | dps-proxy 22 端点路由补齐 ＋ 身份注入 ＋ 错误体透传 ＋ 路由顺序 ＋ DPS 集成落地 | `openbase/modules/dps_proxy/__init__.py` |
| B | BL-1410-02~09／14~17 | 12 页面（P-01~P-12）＋ 数据层真实化 ＋ 错误 8 态 ＋ 页面↔端点映射 100% | `openbase-ui/src/**` |
| C | BL-1410-11 | 质量门禁（单测／E2E／覆盖率／隔离回归，四类全绿） | `openbase-ui/tests/**`、`tests/**` |
| D | BL-1410-10／12／13 | mock 真实化 ＋ 跨仓还债（OpenLLM `b28fb1b`／v2.14.4，**已交付**） | 本仓 ＋ 跨仓 |

**优先级分布**：P0 × 9／P1 × 6／P2 × 1／P3 × 2。

**明确排除**（需求 §7／设计冻结项，**本版不做**）：
1. 三层及以上标签层级／**子标签**（DPS `parent_tag_code` 未落库 ⇒ 不作伪功能，转跨仓派单 `OB-v1.4.10-DSP-TAG-01`）；
2. 前端直连 DPS；③ 新增隔离键；④ 改设计系统／`tokens.css`；⑤ 引入新依赖（ADR-05）；⑥ 通用代理承载本版新增端点；⑦ 既有 12 条路由与画像 2 页行为变更。

---

## 1b. 开发入场检查（Step 3 准入）

> 独立记录见《OpenBase-开发入场检查记录-v1.4.10.md》（v1.0.0）。要点摘录如下。

| # | 准入项 | 要求 | 实测结论 |
|:-:|--------|------|----------|
| 1 | 需求基线已批准 | 有现行基线标识 | ✅ 需求基线 **`v1.4.10-REQ-BL-1.2.0`**（含变更 D-1410-01／02／03） |
| 2 | 设计评审通过 | 设计评审记录结论 | ✅《设计评审记录-v1.4.10》**通过** |
| 3 | 需求架构对比审计 | 覆盖率 ≥95% | ✅ 设计层覆盖 **100%**；RT **28/28**；DT **35 无悬空**；AC **23/23** |
| 4 | **设计基线已人工批准** | 用户批准留痕 | ✅ **2026-09-30 用户以「批准」明示批准设计基线 v2.0.0** |
| 5 | 关键设计输入齐备 | 架构／API／前端／UI／集成／安全／非功能／部署 | ✅ 14 份设计交付物齐备（移交说明 §2） |
| 6 | **端点契约冻结** | 22 端点 ＝ 10 新增 ＋ 12 补代理 | ✅《API接口设计文档-v1.4.10》**v1.4.0**（§1／§1.1／§3.1／§3.4） |
| 7 | **页面 ↔ 端点映射** | 22 端点 ↔ 12 页面，100% | ✅《API接口设计文档》§5／§6 **100%**；《前端架构设计文档》§2 路由 12 条 |
| 8 | 权限口径按修复后实测 | 12/12 一致 | ✅ 补代理权限对齐 **12／12**（DPS v2.9.1 跨仓修复闭环，回执 `E-DPS-v291-20260930`） |
| 9 | 原型基线可对照 | 原型文件齐备 | ✅《UI设计文档-v1.4.10》＋ `doc/design/prototype/`（13 文件） |
| 10 | 阻断项（P0/P1） | = 0 | ✅ G1~G6／G8／G9 全部闭环；G7 明确不做 ⇒ 无 P0/P1 悬挂 |
| 11 | 产出物存在性（Step 2 移交项） | 空输出率 0% | ✅ `doc/version/releases/v1.4.10/`（4）＋`doc/requirements/`（9）＋`doc/design/`（19）＋`doc/audit/`（5）均非空 |

**准入结论**：✅ **通过**（11/11 门禁项满足）——准予进入 Step 3 编码。**遗留（不阻塞编码）**：联调前置 `dps_org_map`／`dps_code_map`／DPS 侧记录／联调账号／本仓 DB 初始化（Test 阶段前须闭合）。

---

## 2. 实现清单（逐 Phase，含「为什么」）

> 编码顺序依《设计基线及开发测试移交说明-v1.4.10》§3.1 **Phase P1~P6**。本版**后端 22 端点与前端 12 页面均已实现**；运行态/联调相关项如实标注移交 Step 4/5。

### Phase P1｜后端 `dps_proxy` 22 端点路由补齐（TD-1410-01／02／03／04／27／32／33／34）

**落点**：`openbase/modules/dps_proxy/__init__.py`（**+508 行**，见 §3）。

- **22 端点路由**（契约 §1 ＋ §1.1）：10 新增（#1~#10）＋ 12 补代理（#11~#22）；本仓路由 `/api/v1/dps-proxy/{path}` → 上游 `{dps_upstream_base}/api/v2/portrait/{path}`，统一复用既有 `_forward(...)`。
- **路由注册顺序（DT-04 强制）**：源文件物理顺序即注册顺序 —— **静态段**（`/template-packages/*`、`/lineage/impact`、`/measures/*`、`/scoring-types`）→ **列表路由**（`/templates`、`/annotation-templates`、`/labels`）→ **动态段**（`/templates/{code}/*`、`/annotation-templates/{code}`）。**理由**：否则列表路由会被同名 `:code` 动态段吞并（如 `GET /templates` 被 `GET /templates/{code}` 误匹配）。
- **身份注入**（TD-02）：沿用唯一装配点 `_build_identity_headers`（四头 ＋ `X-Proxy-Source=openbase-dps-proxy` ＋ `X-Request-Id`），**不改** `modules/protocol_headers/inject.py`；本仓**不做权限判定**（BR-1410-02：仅注入身份 ＋ 透传上游 403）。
- **错误体透传**（TD-03）：复用既有 `_adapt_response`，4xx／5xx **语义保真**（`body.code`（非 0）> `body.detail` > HTTP 状态码），**不转 500、不改 message**。
- **查询参数／请求体透传**：`_forward_query_params` 以 `dict(request.query_params)` 原样转发（含 `?field_key=` 不拦截，透传上游 400 语义）；POST／PUT body 原样转发。
- **辅助函数**：`_portrait_upstream_path(suffix)`（拼接 `/api/v2/portrait` 前缀，单一事实源）、`_forward_query_params(request)`。

### Phase P2／P3／P6｜前端 12 页面（TD-1410-05~12／28~31）

**落点**：`openbase-ui/src/modules/portrait/pages/`（**12 个新建 `Dps*View.vue`**）：

| 页面 | 组件 | 对应端点 |
|:----:|------|----------|
| P-01 模板族管理 | `DpsTemplateListView.vue` | #11·#12·#15·#16 |
| P-02 版本对比与回滚 | `DpsTemplateVersionView.vue` | #3·#4 |
| P-03 预检与影响面 | `DpsTemplatePreflightView.vue` | #5·#7 |
| P-04 包导出／导入 | `DpsTemplatePackageView.vue` | #1·#2 |
| P-05 血缘反查与影响面 | `DpsLineageView.vue` | #6·#7 |
| P-06 措施建议（只读） | `DpsMeasureView.vue` | #8 |
| P-07 评分类型（只读） | `DpsScoringTypeView.vue` | #10 |
| P-08 AI 标注候选与复核 | `DpsAnnotationAdapterView.vue` | #9 |
| P-09 画像模板新建／编辑 | `DpsTemplateEditView.vue` | #12·#13·#14 |
| P-10 标注模板管理 | `DpsAnnotationTemplateView.vue` | #17·#18·#19·#21 |
| P-11 字段体系与归属 | `DpsAnnotationFieldView.vue` | #12·#18·#20 |
| P-12 标签体系查看 | `DpsTagSystemView.vue` | #21·#22 |

**关键实现要点（对应设计冻结项／易漏点）**：
1. **错误 8 态呈现**（TD-14）：新增组合式函数 `src/core/composables/useAsyncState.ts`（加载／空态／错误归一），复用 `describeDpsError`（通用 `kind` ＋ DPS 专项 `hint`）；**不新建全局 store**（ADR-05），每次进入页面重新拉取。
2. **`basis` 口径折叠**（ADR-06／UI §4.2）：新增 `src/core/composables/useBasisTooltip.ts` —— 默认收起、维护 `aria-expanded`、**`tag_count=0` 强制展开且不可手动收起**。
3. **回滚二次确认四要素**（UI §4.1）／**导入不得默认实做**（`dry_run` 显式携带）／**5xx 不静默降级**（明确提示 ＋ 重试）／**无「解除归属」入口**（上游无此语义）。

### Phase P4｜数据层真实化 ＋ 路由（TD-1410-13／23）

- `openbase-ui/src/core/api/dps.ts`（**+398 行**）：扩展 **22 个方法**（10 新增 ＋ 12 补代理）＋ **2 个跨上游协作方法**（`assistReview` 经 `llm-proxy`→OpenLLM；`submitReview` 走 DPS 既有 `POST /portrait/annotations/{id}/review`）；既有 11 方法**不改**。
- `openbase-ui/src/core/api/error.ts`（**+40 行**）：新增 **409 `conflict`** 语义 ＋ `DPS_ERROR_HINTS`（400／403／404／409／422／503）与 5xx 兜底 `dpsErrorHint`／`describeDpsError`；**既有 `kind` 口径不变**（回归）。
- `openbase-ui/src/core/router/index.ts`（**+43 行**）：新增 **12 条设计路由** ⇒ 落为 **13 条 route record**（P-09 由 `dps/templates/new` 与 `dps/templates/:code/edit` 双路径承载同一页面组件）；**静态段先于动态段**注册。

### Phase P5｜质量门禁（TD-1410-15／18~22／24／25）

- **单测**：后端 3 文件 **95 passed**；前端 2 文件（`api-dps-v1410.spec.ts`／`dps-ui-v1410.spec.ts`）计入 vitest。
- **覆盖率门禁（TD-25）**：`openbase-ui/vite.config.ts` 已配置阈值（lines／functions／statements ≥80、branches ≥70）＋ `coverage-gate-result.json` 留痕。
- **E2E／Playwright、隔离回归、性能抽样（≥30 次/端点）**：**移交 Step 4**（见 §11）。
- **可观测性（TD-24）**：代理层结构化日志（`logger.warning`／`logger.error` 仅记 `path`／`error`／`status`，**不落凭据**）；本报告记录。

### 跨仓（TD-1410-16／17／35）｜已交付，本仓仅回填

| 项 | 交付 | 状态 |
|----|------|:----:|
| TD-16 日志硬化（`DEBUG`／echo 关闭）＋ TD-17 首请求预热（前移至 `lifespan`） | OpenLLM **`b28fb1b`／v2.14.4** | ✅ 已实施（实测待环境窗口） |
| TD-35 跨仓派单（G6 权限点映射／G8 启停动作／G9 `labels` 资源） | DPS **v2.9.1**（`ff9fd9f`＋`de106eb`） | ✅ 已交付（回执 `E-DPS-v291-20260930`） |
| TD-35 G7 子标签（`parent_tag_code` 落库） | DPS **v2.12.0** | ✅ 已交付（回执 `dps-v2120-tag-hierarchy-receipt-20260930`） |

---

## 3. 变更统计与影响文件

**本仓生产代码（4 文件：新增 0／修改 4）**：

| 文件 | 变更 |
|------|------|
| `openbase/modules/dps_proxy/__init__.py` | **+508**（22 端点 ＋ 辅助函数 ＋ 模块文档） |
| `openbase-ui/src/core/api/dps.ts` | **+398**（22 方法 ＋ 2 跨上游协作方法） |
| `openbase-ui/src/core/api/error.ts` | **+40**（409／`DPS_ERROR_HINTS`） |
| `openbase-ui/src/core/router/index.ts` | **+43**（13 条 route record） |

> `git diff --stat`（工作区实测）：**4 files changed, 983 insertions(+), 6 deletions(-)**。

**本仓新增代码／测试文件（18 个）**：

- **前端页面（12）**：`DpsTemplateListView.vue`／`DpsTemplateVersionView.vue`／`DpsTemplatePreflightView.vue`／`DpsTemplatePackageView.vue`／`DpsLineageView.vue`／`DpsMeasureView.vue`／`DpsScoringTypeView.vue`／`DpsAnnotationAdapterView.vue`／`DpsTemplateEditView.vue`／`DpsAnnotationTemplateView.vue`／`DpsAnnotationFieldView.vue`／`DpsTagSystemView.vue`
- **前端组合式函数（2）**：`core/composables/useAsyncState.ts`（73 行）／`core/composables/useBasisTooltip.ts`（46 行）
- **前端测试（2）**：`openbase-ui/tests/api-dps-v1410.spec.ts`（211 行）／`openbase-ui/tests/dps-ui-v1410.spec.ts`（228 行）
- **后端测试（2）**：`tests/test_dps_proxy_v1410_contract.py`（429 行，32 用例）／`tests/test_dps_proxy_routes_v1410.py`（182 行，43 用例）

> **后端既有回归面（1，未改动）**：`tests/test_dps_proxy.py`（既有 20 用例）本版**不改行为**，作为兼容性回归面复用（`git status` 未列为修改）。

> **工作区新增文件合计 26**：代码／测试 **18** ＋ Step 3 文档 **6**（DevLogReport／开发审计移交材料／测试移交说明／追溯矩阵／开发入场检查记录／版本控制记录）＋ 运行验证证据 **2**（`v1410_l1l2l3_smoke.py` ＋ 结果 `.txt`）。

**新增行数（按文件清单实测）**：后端 `dps_proxy` +508；前端 `dps.ts` +398／`error.ts` +40／`router` +43；12 页面合计约 **1,897 行**；组合式函数 119 行；4 个新测试文件合计约 **1,050 行**。

**文档仓（本仓 `doc/`）**：本报告（v1.0.0）／开发审计移交材料（v1.0.0）／测试移交说明（v1.0.0）／设计开发追溯矩阵（v1.0.0）／开发入场检查记录（v1.0.0）／版本控制记录（v1.0.0）／证据（`doc/test/evidence/v1410/`）。

**提交状态（重要，如实登记）**：本条改动**均在工作区，尚未提交**（`git status` 实测：**4 个 tracked 修改 ＋ 18 个新增代码／测试文件 ＋ 6 份 Step 3 文档 ＋ 2 份运行验证证据**）。**提交序列**依《版本控制记录-v1.4.10》§2.3（原子提交分组 ＋ RT-ID footer），**待人工批准后**统一提交并按三远程规则推送。

---

## 3b. 对外接口、数据与配置变更

| 类别 | 结论 | 说明 |
|------|------|------|
| **对外接口（API）** | **新增 22 个代理路由** | 本仓 `/api/v1/dps-proxy/{path}`；**既有 12 条路由路径／方法不变**；**不新增错误码**（透传上游） |
| **数据库** | **无变更** | 本仓为**代理层**，无 DDL／迁移；无新增表／字段 |
| **配置项** | **无新增** | 复用既有 `dps_upstream_base`／`dps_upstream_timeout`／`dps_health_*`／`dps_org_map`／`dps_code_map`／`enforce_org_alias`；**未新增任何配置键** |
| **依赖** | **无新增** | 前端不引入新依赖（ADR-05）；后端复用既有 `httpx`／FastAPI |

---

## 4. 静态质量检查（`code-static-quality-check`，十类 0 阻塞）

| # | 检查类 | 命令／方法 | 结果 |
|:-:|--------|-----------|:----:|
| 1 | 语法 | `python -m compileall -q openbase` | ✅ exit 0 |
| 2 | Lint（后端） | `python -m ruff check openbase tests` | ✅ **All checks passed!**（0 告警） |
| 3 | 类型／构建（前端） | `npm run build`（`vue-tsc --noEmit && vite build`） | ✅ exit 0（`✓ built in 24.45s`） |
| 4 | 符号／参数／返回值／导入导出 | `ruff`（select E,F,W,I,UP,B）＋ `vue-tsc` 类型检查 | ✅ 0 阻塞 |
| 5 | 环境配置／数据字段 | `ruff` ＋ 契约测试字段断言（22 端点） | ✅ 0 阻塞 |
| 6 | 复杂度（`C901`，附带观察） | `python -m ruff check --select C901 openbase tests` | ⚠ 11 项超默认阈值（**均为既有函数**，本版**新增函数 0**，详见 §8） |

> **说明**：`compiledall`／`ruff`／`vue-tsc`／`vite build` 四项为**本版实测**；`ruff` 采用仓库既有规则集（`pyproject.toml [tool.ruff.lint] select = ["E","F","W","I","UP","B"]`），复杂度 `C901` **不在默认选择集内**，仅在债务增长率检查中单独取样。

---

## 5. 实际运行验证（3.5，L1/L2/L3）

**证据**：`doc/test/evidence/v1410/v1410_l1l2l3_smoke.py`（可复现脚本，自定位仓库根）＋ `doc/test/evidence/v1410/v1410-l1l2l3-smoke-20261001.txt`（实测输出）。

| 层 | 判据 | 实测证据（含实际输出片段口径） | 结果 |
|:--:|------|-------------------------------|:----:|
| **L1 构建** | 构建／编译零错误、产物可导入 | `compileall exit_code=0`；`import openbase OK; __version__=1.0.0`；前端 `npm run build`（`vue-tsc --noEmit` ＋ `vite build`）`✓ built in 24.45s`，Dps*View 按页分包产出（如 `DpsTemplateVersionView` 7.94 kB／`DpsTemplateEditView` 8.45 kB） | ✅ |
| **L2 启动** | 服务装配成功、应用就绪 | `app assembled: title='OpenBase'`；`dps-proxy 路由对象总数=34; v1.4.10 新增路由对象=22`（12 既有 ＋ 22 新增）；ASGI `TestClient` 启动成功，`GET /openapi.json -> 200` | ✅ |
| **L3 冒烟** | 3~5 个核心用例全通过 | **5 例全 PASS** —— S1 认证门禁（无 token 访问新增端点 → **401**，`code=AUTH_401`）；S2 端点契约（带 token `GET /templates?status=active` → **200**，透传上游 `/api/v2/portrait/templates`，`X-Proxy-Source='openbase-dps-proxy'`）；S3 错误保真（上游 404 `{detail}` → **404**；409 网关错误体 → **409** 且 message 原文）；S4 路由顺序（静态 `impact` 先于动态 `tags/{tag_code}`；`/templates` 列表先于 `/templates/{code}`）；S5 既有 12 路由路径／方法不变 | ✅ |

**如实声明（不夸大）**：
1. L3 为**夹具级冒烟**（mock 上游，**不依赖真实 DPS**），**不能替代** Step 4 的**真实联调**与运行态统计；
2. 本环境**联调前置未闭合**（`dps_org_map`／`dps_code_map` 未配、DPS 侧记录／联调账号待准备）⇒ **写操作真实联调**移交 Step 4（见 §11）；
3. L2 日志中可见 `Duplicate Operation ID ... /api/v1/proxy/{system}/{path}` 的 FastAPI UserWarning 与 `principal verify db read failed; degrade pass-through` —— 二者均为**既有行为**（通用代理 catch-all 与 Principal 校验降级 pass-through），**非本版引入、非缺陷**，如实登记。

---

## 6. 自测（3.6，逐命令可复现）

**命令与结果同源可复现（2026-10-01 实测）**：

| # | 目的 | 命令 | 实测结果 |
|:-:|------|------|----------|
| 1 | 后端指定测试 | `python -m pytest tests/test_dps_proxy.py tests/test_dps_proxy_v1410_contract.py tests/test_dps_proxy_routes_v1410.py -q` | ✅ **95 passed**（171.90s） |
| 2 | 后端静态 | `python -m ruff check openbase tests` | ✅ **All checks passed!** |
| 3 | 前端单测 | `npx vitest run`（`openbase-ui`） | ✅ **21 test files / 239 tests passed**（第 2 次全量；见下方"抖动说明"） |
| 4 | 前端构建 | `npm run build` | ✅ exit 0 |
| 5 | 实际运行验证 | `python doc/test/evidence/v1410/v1410_l1l2l3_smoke.py` | ✅ **L1/L2/L3 全 PASS** |

**后端 95 用例构成**（按文件拆分）：
- `tests/test_dps_proxy_routes_v1410.py`（**43**）：22 条端点路由逐条断言 ＋ 路由对象数=22 ＋ 5 条顺序断言 ＋ 列表路由唯一性 ＋ 既有 12 路由回归（12 参数化）＋ 通用代理通道边界 2 条；
- `tests/test_dps_proxy_v1410_contract.py`（**32**）：22 端点契约参数化（路径／方法／参数／body／身份头逐条）＋ 上游前缀断言 ＋ 认证门禁 401 ＋ 错误保真 4 条（404／409／503／上游不可达 502）＋ `?field_key=` 不拦截 ＋ 导入 `dry_run` 透传 ＋ 既有路由回归 ＋ 模块版本常量；
- `tests/test_dps_proxy.py`（**20**）：v1.4.5 R-381 既有护栏（**回归面，不改行为**）。

**前端 vitest 抖动说明（如实登记，非产品缺陷）**：
- **第 1 次全量**：`21 files / 239 tests` → **1 failed / 238 passed**，唯一失败为 `tests/dps-ui-v1410.spec.ts > P-01 模板族列表` **5s 超时**（`Test timed out in 5000ms`）；
- **隔离复跑** `npx vitest run tests/dps-ui-v1410.spec.ts` → **14 passed**（P-01 用例 2745ms 通过）；
- **第 2 次全量** → **21 files / 239 tests 全通过**（188.79s）。
- **定性**：**并行负载下的测试时延抖动（flaky timeout）**，非功能性缺陷；已登记为测试基础设施优化项（见 §8／§9）。

---

## 7. 代码逻辑审查（`code-logic-review`，11 维）

> 审查对象：本版新增/修改的 4 个生产文件（`dps_proxy/__init__.py`、`dps.ts`、`error.ts`、`router/index.ts`）＋ 2 个组合式函数。

| # | 维度 | 结论 |
|:-:|------|------|
| 1 | **分层架构** | ✅ 合规：`dps_proxy` 属路由/代理层，**不触 DB、无 SQL**；`init_app` 装配路由；前端页面**只经 `core/api/dps.ts`** 调 `/api/v1/dps-proxy/*`，**不直连 DPS** |
| 2 | **错误处理** | ✅ 合规：4xx／5xx **语义保真**（`_adapt_response`）；上游不可达 → `SYS_UPSTREAM_ERROR`（502）；连续失败达阈值 → 503 显式降级；**不静默吞错** |
| 3 | **路由顺序（正确性关键）** | ✅ 静态段／列表路由**先于**同名动态段（源文件物理顺序）＋ **22 条断言测试**兜底 |
| 4 | **参数/请求体透传** | ✅ `_forward_query_params` 原样转发；POST／PUT body 原样；**不在本仓裁剪**（`?field_key=` 透传上游 400） |
| 5 | **身份与安全** | ✅ 唯一装配点 `_build_identity_headers`；前端**零密钥、不构造身份头、不做权限判定**；日志**不含凭据** |
| 6 | **边界/通道** | ✅ 通用代理 `/api/v1/proxy/{system}/{path}` **不承载**本版新增端点（测试断言"仅 1 条 catch-all 路由"） |
| 7 | **兼容性** | ✅ 既有 12 条路由路径／方法不变；既有 11 个 `dpsApi` 方法不变；既有 `error.ts` `kind` 口径不变（回归测试） |
| 8 | **可维护性/命名** | ✅ `snake_case` 函数、描述性命名（`dps_template_package_export` 等）；每函数单一职责 |
| 9 | **幂等/并发** | ✅ 幂等由上游裁决（导入 `package_hash`／模板启停）；`_dps_consecutive_failures` 为模块级计数器（**既有**，见观察项 O-1） |
| 10 | **类型/契约一致性** | ✅ `dps.ts` 类型与契约 §3.4 一致（`field_schema` 5 类、`extends`、强归属、无"解除归属"）；`vue-tsc` 通过 |
| 11 | **测试充分性** | ✅ 后端 95 用例逐端点；前端 35 用例（页面状态／路由／错误映射） |

**审查发现（如实登记）**：

| # | 发现 | 级别 | 处置 |
|:-:|------|:----:|------|
| O-1 | `_dps_consecutive_failures` 为**模块级可变全局**，并发失败自增**无锁**（AGENTS.md §6） | 低（P3） | **既有逻辑，本版未改动**；仅影响降级阈值启发（阈值判定不精确），不影响正确性 ⇒ 登记为后续债务候选，本版不扩大范围 |
| O-2 | `dps_proxy/__init__.py` **单文件体积增长**（+508 行，累计约 1,030 行） | 低（P3） | 已在 ADR-01／TD-新增-039 登记**拆分预案**（建议按子路由模块拆分，**不得改对外路径**）；本版不拆分以免扩大改动面 |
| O-3 | 前端 `DpsTemplateEditView` P-01 用例在**全量并行**下 5s 超时（flaky） | 低（P3） | **测试基础设施**问题（非产品缺陷）；建议后续为该用例单独提高 `testTimeout` 或降并行度（见 §8/§9） |

**结论**：**无未解决 P0/P1**；3 项观察均为 P3（既有债务／测试基础设施），本版不阻断。详细逻辑审查记录（独立文档）随 Step 3 收尾补齐。

---

## 8. 技术债务增长率检查（3.4a，本版本相对 v1.4.9）

**口径与工具（实测）**：

| 项 | 阈值 | 实测值 | 超阈值 | 方法 |
|----|:----:|:------:|:------:|------|
| 新增 TODO／FIXME／XXX／HACK | ≤5 | **0** | 否 | 正则 `(TODO\|FIXME\|XXX\|HACK)` 在**本版改动面**（`openbase/modules/dps_proxy/`、`openbase-ui/src/core/composables/`）逐行匹配，命中 0 |
| 新增高复杂度函数数 | ≤3 | **0** | 否 | `python -m ruff check --select C901`（默认阈值 10）在**全仓**检出 11 项超阈；**逐项核对后均为既有函数**（`build_outbound_headers`／`oidc_callback`／`validate_role_map`／`_adapt_response` 等，**非本版新增**）；本版新增的 22 个路由处理函数复杂度≈1~2 |
| 代码重复率增量 | ≤2% | **未实测** | — | `pylint --enable=duplicate-code` **本环境未安装** ⇒ **如实登记为"未测量"**（非 0）；移交 Step 3 收尾/Step 4 补齐 |

**结论**：前两项**均未超阈值**（0／0）；**无 P0 级超阈值**，无需申请豁免；第 3 项**如实登记为未测量**（工具缺失，不得以 0 记）。3 项观察（O-1~O-3）与池上界类项归入后续版本重构候选。

---

## 9. 偏差、语义变更与风险（如实登记）

| 项 | 说明 |
|----|------|
| 偏差 1（联调前置） | `dps_org_map`／`dps_code_map` 未配、DPS 侧 `organization`／`tenant` 记录与联调账号待准备、本仓 DB 未初始化（`F4`）⇒ **写操作真实联调未做**，L3 为**夹具级**冒烟；**已如实登记**，移交 Step 4（**不得计为"已通过"**） |
| 偏差 2（测试抖动） | 前端 vitest **第 1 次全量** 1 例（P-01）并行负载下 5s 超时；隔离复跑与第 2 次全量均通过 ⇒ 定性为**测试基础设施时延抖动**，**非产品缺陷**；已登记优化项 |
| 偏差 3（哨兵脚本自纠） | 本报告 L1/L2/L3 脚本 `v1410_l1l2l3_smoke.py` 首次运行因**把 `X-Proxy-Source` 断言写死为字面 `"dps"`**（实际常量值为 `openbase-dps-proxy`）而"假失败"⇒ 已改为**引用单一事实源常量 `PROXY_SOURCE_DPS`**；属**取证脚本缺陷（自纠）**，不入产品缺陷账 |
| 偏差 4（提交状态） | 本版代码／测试／文档**均在工作区、尚未提交**；提交序列见《版本控制记录》§2.3，**待人工批准后**原子提交 ＋ 三远程推送（红线：推送需单独确认） |
| 偏差 5（配套记录） | 《静态质量检查记录-v1.4.10》《代码逻辑审查记录-v1.4.10》**独立文档尚未产出**；本报告 §4／§7 已内嵌其结论，**待收尾补齐** |
| 语义变更 | **无对外语义变更**（仅新增路由；既有 12 路由、既有前端行为、既有错误码口径均不变） |
| 风险 1（P1） | 联调前置未闭合 ⇒ 若直接联调将出现 **401／归属校验失败**（架构风险 #1）；须按 §11 前置闭合 |
| 风险 2（P2） | `dps_proxy` 单文件体积增长（O-2）——拆分须**不改对外路径** |
| 风险 3（P3） | `_dps_consecutive_failures` 并发无锁（O-1）——既有，阈值启发不精确 |
| 风险 4（P3） | 前端 P-01 用例并行抖动（O-3）——测试基础设施 |

---

## 10. 未完成事项（移交 Step 4 / Step 5）

| 项 | 承接阶段 |
|----|----------|
| **真实联调**（写操作页面 P-02／P-04／P-08 与模板本体 P-09~P-12） | Step 4（需联调前置闭合） |
| 补代理 12 端点契约用例（#11~#22 × 各错误码；启停幂等／删除被拒 409 含条数／归属不匹配 400／`extends` 自环·成环·深度>2 400／`action≠list` 400） | Step 4 |
| 模板本体语义用例（CRUD ＋ `version` 递增／`portrait_template_history`；`field_schema` 5 类校验；改挂新归属须 `active`） | Step 4 |
| 隔离回归（跨租户／跨组织 → 空或 403，**无 500**） | Step 4 |
| 覆盖率门（`--cov`）与前端 E2E／Playwright | Step 4 |
| 性能抽样（≥30 次/端点；首请求 60 轮对比基线 2,150 ms） | Step 4 |
| 安全验收（安全设计 §7 七项） | Step 4 |
| 原型一致性验收（实现页面 ↔ `prototype/` 逐页比对，7 维） | Step 4 |
| 代码重复率增量实测（工具补齐）＋ `dps_proxy` 拆分 | Step 3 收尾／下版本 |
| 部署、灰度与回退（`dps_org_map`／DB 初始化等部署前置） | Step 5 |

---

## 11. 产出物存在性验证（3.10）

| 产出类别 | 清单 | 存在性 |
|----------|------|:------:|
| 生产代码落点 | `openbase/modules/dps_proxy/__init__.py`（+508）；`openbase-ui/src/core/api/dps.ts`（+398）／`error.ts`（+40）／`router/index.ts`（+43） | ✅ 已核（`git diff --stat`） |
| 前端页面 | 12 个 `Dps*View.vue`（P-01~P-12，合计约 1,897 行） | ✅ 已核（`Get-ChildItem` 逐文件行数） |
| 组合式函数 | `core/composables/useAsyncState.ts`（73）／`useBasisTooltip.ts`（46） | ✅ 已核 |
| 测试护栏 | 后端 `test_dps_proxy_v1410_contract.py`（429）／`test_dps_proxy_routes_v1410.py`（182）；前端 `api-dps-v1410.spec.ts`（211）／`dps-ui-v1410.spec.ts`（228） | ✅ 已核 |
| 运行验证证据 | `doc/test/evidence/v1410/v1410_l1l2l3_smoke.py` ＋ `v1410-l1l2l3-smoke-20261001.txt` | ✅ 已核（L1/L2/L3 全 PASS） |
| 设计／跨仓证据 | `doc/test/evidence/v1410/`（`E-G6-20260930`／`E-DPS-v291-20260930`／`E-LLMPROXY-20260930`／`dps-v2120-tag-hierarchy-receipt` 等，共 9 份） | ✅ 已核 |
| 开发记录 | 追溯矩阵 v1.0.0／入场检查 v1.0.0／版本控制 v1.0.0／本报告 v1.0.0／审计移交材料 v1.0.0／测试移交说明 v1.0.0 | ✅ 已核 |

**验证方式**：文件系统清点（`Get-ChildItem` 行数 ＋ `git status`／`git diff --stat`）＋ 命令实测（pytest／ruff／vitest／`npm run build`／L1-L3 冒烟）。**空输出率 0%**。

---

## 12. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-10-01 | AD-OpenBase-Dev／FD-OpenBase-Dev | 初始创建（Step 3 开发记录报告）：版本目标与 18 条 Backlog 范围（22 端点 ＋ 12 页面）；§1b 开发入场检查（11/11 通过）；§2 逐 Phase 实现清单（P1 后端 22 路由／P2·P3·P6 前端 12 页面／P4 数据层＋路由／P5 门禁）；§3 变更统计（4 文件 983 insertions／6 deletions ＋ 21 新增）；§3b 接口·数据·配置变更（新增 22 路由／无 DB／无配置／无依赖）；§4 静态质量（`ruff` All checks passed ＋ `vue-tsc`＋`vite build` 通过）；§5 实际运行验证 L1/L2/L3（**全 PASS**）；§6 自测（后端 95 passed／前端 239 passed／构建通过，含抖动如实登记）；§7 代码逻辑审查（11 维，无 P0/P1，3 项 P3 观察）；§8 债务增长率（0／0／未实测）；§9 偏差·语义·风险（5 项偏差如实登记）；§10 移交清单；§11 产出物存在性验证。状态 [Review]。 |
