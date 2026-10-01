# OpenBase 测试移交说明 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **本仓**（`openbase` 后端 ＋ `openbase-ui` 前端） |
| 版本号 | **v1.4.10**（承接型小版本「DPS 模板化能力对接深化」） |
| 文档 | 测试移交说明（Step 3 产出 6，`coding-stage-execution` §3.10／`project-document-management` 阶段 3 产物） |
| 文档版本 | v1.0.0 |
| 状态 | [Review]（待人工批准后进入 Step 4） |
| 编制 | AD-OpenBase-Dev（后端）／FD-OpenBase-Dev（前端） |
| 移交对象 | 测试负责人／测试工程师（Step 4 测试阶段） |
| 创建日期 | 2026-10-01 |
| 存放 | `doc/development/` |
| 上游依据 | 《开发审计移交材料-v1.4.10》v1.0.0；《DevLogReport-v1.4.10》v1.0.0；《设计开发追溯矩阵-v1.4.10》v1.0.0；《设计基线及开发测试移交说明-v1.4.10》v2.0.0；《API接口设计文档-v1.4.10》v1.4.0 |

---

## 1. 移交范围

| 项 | 内容 |
|----|------|
| 交付代码 | 本仓：后端 `openbase/modules/dps_proxy/__init__.py`（+508，22 端点）；前端 `openbase-ui/src/core/api/dps.ts`（+398）／`error.ts`（+40）／`core/router/index.ts`（+43）＋ **12 个 `Dps*View.vue`** ＋ 2 组合式函数；`git diff --stat`：**4 files changed, 983 insertions(+), 6 deletions(-)** ＋ **18 个新增代码／测试文件**（另 6 份 Step 3 文档 ＋ 2 份运行验证证据） |
| 交付形态 | **均在工作区，尚未提交、未推送**（提交序列见《版本控制记录-v1.4.10》§2.3，待人工批准后原子提交 ＋ 三远程推送） |
| 本版增量 | dps-proxy **22 端点**（10 新增 #1~#10 ＋ 12 补代理 #11~#22）；前端 **12 页面**（P-01~P-12）＋ 数据层 22 方法 ＋ 错误 8 态 ＋ 13 条 route record（P-09 双路径） |
| 不在本次测试范围 | Step 5 部署与灰度、发布验证；DPS 仓自身版本测试；跨仓（OpenLLM `b28fb1b`／v2.14.4、DPS v2.9.1／v2.12.0）自身测试（**已交付，本仓仅消费**）；**子标签**（本版明确不做） |

---

## 2. 测试环境与入口

| 项 | 值 |
|----|-----|
| 后端入口 | 仓库根：`uvicorn openbase.demo_app:app --host 127.0.0.1 --port <端口>`（`openbase/demo_app.py` 装配全部模块，含 `dps_proxy`） |
| 后端环境变量来源 | 仓库既有 `.env` ＋ `.env.shared-infra`（**密钥不落盘、不打印**）；`OPENBASE_LOG_SETUP=0` 可关闭日志落盘（测试隔离） |
| 后端健康 | `GET /openapi.json` → 200（应用就绪）；`GET /api/v1/dps-proxy/health` → 透传 DPS `/health/liveness` |
| 登录 | `POST /api/v1/auth/login`（demo 降级内存用户：`admin` / `admin123`；**生产禁用降级**） |
| 前端入口 | `openbase-ui/`：`npm run dev`（Vite `5173`，`/api` 代理至 `127.0.0.1:8000`） |
| 前端测试入口 | `npm run test`（vitest）／`npm run test:coverage`（v8 覆盖率）／`npm run test:e2e`（Playwright）／`npm run build`（`vue-tsc --noEmit && vite build`） |
| 主要取证面 | 后端：`/api/v1/dps-proxy/*` 22 端点（本仓 → 上游 `/api/v2/portrait/*`）；前端：12 个 `dps/*` 路由页面 |
| 请求要点 | 身份头由**本仓代理注入**（前端不可伪造）；上游裁决权限；`model`／分页等参数**原样透传**；上游错误体 4xx／5xx **语义保真** |

---

## 3. 开关矩阵（测试必须区分「出厂默认」与「工作区生效值」）

| 开关 | 出厂默认 | 作用与测试要点 |
|------|:--------:|----------------|
| `enforce_org_alias` | **False** | **必须为 False**；`True` 时强制 `org == tenant`，与传真 org 互斥（ADR-04）。**红线**：误开将导致归属口径错乱 |
| `dps_health_check_enabled` | True | 上游 `/health` 探活；**测试断言"恰一次转发"时须置 False**（避免探活请求插入请求序列） |
| `dps_health_interval` | 30.0 | 探活节流间隔 |
| `dps_upstream_base` | `http://...:8000` | 上游地址；契约测试以 monkeypatch 覆盖并替换 `httpx.AsyncClient` |
| `dps_org_map`／`dps_code_map` | 空 | **联调前置**（P1）：未配 ⇒ 出站 `X-Org-ID` 回落 tenant 值 ⇒ DPS 侧 **401／归属校验失败** |
| `dps_degrade_threshold` | 既有 | 连续失败达阈值 → **503 显式降级**（`X-DPS-Upstream-Degraded: true`） |

> **红线**：① `enforce_org_alias` 必须为 `False`；② **不新增隔离键**（`tenant_code` 单键）；③ 前端**零密钥、不构造身份头**；④ 本版**未新增任何配置键**（与 v1.4.9 不同，无需关注"死开关"）。

---

## 4. 判据复现命令（口径与 Step 3 证据同源）

| 目的 | 命令（在仓库根执行） | 期望（2026-10-01 实测） |
|------|----------------------|------------------------|
| 后端指定测试（契约 ＋ 路由 ＋ 回归） | `python -m pytest tests/test_dps_proxy.py tests/test_dps_proxy_v1410_contract.py tests/test_dps_proxy_routes_v1410.py -q` | **95 passed** |
| 后端静态检查 | `python -m ruff check openbase tests` | **All checks passed!** |
| 复杂度取样（可选） | `python -m ruff check --select C901 openbase tests` | 11 项超阈（**均为既有函数**，本版新增 0） |
| 前端单测 | `cd openbase-ui` → `npx vitest run` | **21 files / 239 tests passed**（全量） |
| 前端指定测试 | `npx vitest run tests/api-dps-v1410.spec.ts tests/dps-ui-v1410.spec.ts` | 全通过（v1410 专项 **35 用例**） |
| 前端构建／类型 | `npm run build` | exit 0（`✓ built in ≈24s`） |
| 实际运行验证（L1/L2/L3） | `python doc/test/evidence/v1410/v1410_l1l2l3_smoke.py` | **L1/L2/L3 全 PASS**（夹具级，任意 cwd 可跑） |

> **说明**：前端 `npx vitest run` 首次全量在**并行负载**下曾出现 1 例（`dps-ui-v1410.spec.ts` P-01）5s 超时；**隔离复跑与第二次全量均通过**（239/239）⇒ 属**测试时延抖动**，重跑即可确认，**不应据此判为功能缺陷**。

---

## 5. 建议的测试重点（按风险排序）

| # | 重点 | 说明与判据 |
|:-:|------|-----------|
| 1 | **写操作真实联调**（P-02 回滚／P-04 导入／P-08 复核／P-09~P-12 模板本体） | 需**联调前置闭合**（`dps_org_map`／`dps_code_map`／DPS 侧记录／联调账号权限按**修复后**口径：标注模板 CRUD 须 `annotation_template:*`；模板启停须 `portrait_template:update`）；含二次确认四要素、`dry_run` 与实做视觉区分、关闭态零写入 |
| 2 | **22 端点契约覆盖率 100%** | 逐端点：路径映射（本仓 → `/api/v2/portrait/*`）／方法保真／查询参数与 body 透传／身份头（四头 ＋ `X-Proxy-Source`／`X-Request-Id`）；判据 AC-18（22 ↔ 12 页面） |
| 3 | **错误语义保真（不转 500）** | 上游 400／403／404／409／422／503 逐码原样呈现；**409 双语义区分**（`code` 冲突 vs 未复核候选门禁）；上游不可达 → **502**，连续失败达阈值 → **503**（不静默） |
| 4 | **权限口径按修复后实测** | 标注模板 CRUD 须 `annotation_template:*`；模板启停须 `portrait_template:update`（**不得沿用修复前旧口径，不得按语义推断**）；本仓**仅透传**，裁决在上游 |
| 5 | **路由顺序与通道边界** | 静态段／列表路由先于同名动态段（22 条断言）；通用代理 `/api/v1/proxy/{system}/{path}` **不承载**本版新增端点 |
| 6 | **兼容性（红线）** | 既有 **12 条** `dps-proxy` 路由路径／方法不变；画像 `PortraitList.vue`／`PortraitDetail.vue` 行为不变；既有 `dpsApi` 11 方法不变；既有 `error.ts` `kind` 口径不变 |
| 7 | **隔离回归** | 跨租户／跨组织 → **空或 403，无 500**（AC 兼容既有口径） |
| 8 | **无敏感落痕（安全）** | 回执／日志不含令牌、密钥、完整请求体、个人隐私；前端**零密钥**（`http.ts` 仅审查、不改） |
| 9 | **前端错误 8 态与空态呈现** | 404 无谱系 → 空态（非错误页）；403 未启用 → 信息态且**零写入**；`tag_count=0` 强制展开 `basis`；5xx **不静默降级**（明确提示 ＋ 重试） |
| 10 | **门禁四类 ＋ 原型一致性** | 单测／E2E（Playwright）／覆盖率（v8，阈值 lines·functions·statements ≥80、branches ≥70）／隔离回归；实现页面 ↔ `prototype/` 逐页比对（7 维）；性能抽样 ≥30 次/端点、首请求 60 轮（对比基线 2,150 ms） |

---

## 6. 已知受限项与未覆盖项（**不得计为「已通过」**）

| 类别 | 项 | 说明 |
|------|----|------|
| 受限（**前置未闭合**） | 真实联调（写操作 ＋ 模板本体） | `dps_org_map`／`dps_code_map` 未配、DPS 侧记录／联调账号待准备、本仓 DB 未初始化（`F4`）⇒ 本版仅**夹具级**冒烟 |
| 受限（**明确不做**） | 三层及以上标签／**子标签** | DPS `parent_tag_code` 未落库 ⇒ 不作伪功能；跨仓派单 `OB-v1.4.10-DSP-TAG-01`（DPS v2.12.0 已交付，**非本版交付**） |
| 遗留（测量缺口） | **代码重复率增量未实测** | `pylint` 未安装；**不得以 0 记**，移交收尾/Step 4 |
| 遗留（低） | `dps_proxy` 单文件体积增长（+508，累计约 1,030 行） | 拆分预案（ADR-01／TD-039），**不得改对外路径** |
| 遗留（低） | `_dps_consecutive_failures` 模块级全局并发无锁 | **既有逻辑**，本版未改动；阈值启发不精确 |
| 环境性 | 前端 vitest 首轮并行抖动（P-01 5s 超时） | **测试基础设施**问题，隔离／重跑通过；**非产品缺陷** |
| 既有行为（非本版） | FastAPI `Duplicate Operation ID /api/v1/proxy/{system}/{path}` 警告；`principal verify db read failed; degrade pass-through` | 既有通用代理 catch-all 与 Principal 校验降级，**非本版引入** |

---

## 7. 环境使用提示（避免误判为缺陷）

1. **联调前置未闭合会表现为 401／归属校验失败**：如实属 `dps_org_map`／`dps_code_map` 未配，属**环境前置**问题，**非代码缺陷**；请先闭合前置再联调。
2. **上游不可达 ≠ 代码缺陷**：上游连接异常 → **502**；连续失败达阈值 → **503 显式降级**（`X-DPS-Upstream-Degraded: true`）＋ ERROR 日志（可观测，非缺陷）。
3. **组件可用性波动**：DPS 组件在会话间可用性会变化 ⇒ 降级属**设计内行为**，但必须**如实留痕**（错误日志／状态码），**不得静默**；测试应区分「环境不可用」与「代码缺陷」。
4. **不要把夹具结论当运行态结论**：本版 L1/L2/L3 为 **mock 上游**的夹具级冒烟；运行态结论须用**真实 DPS**（如 DPS 本地实例）并在报告中标注样本量。
5. **前端并行测试抖动**：全量 vitest 偶发超时属并行负载时延，**隔离复跑或重跑**确认；不据此判缺陷。

---

## 8. 准入／准出建议

| 项 | 建议 |
|----|------|
| 准入（进入 Step 4） | Stage3 审计通过 ＋ 本文档与《开发审计移交材料》齐备 ＋ **联调前置闭合**（`dps_org_map`／`dps_code_map`／DPS 侧记录／联调账号权限按修复后口径／本仓 DB 初始化） |
| 必测门禁 | 接口／集成／E2E／回归／**覆盖率**（`--cov`／`test:coverage`）／合规／UAT —— 覆盖率门与 E2E 为**本阶段首次执行**（Step 3 未做，已如实登记） |
| 准出（进入 Step 5）建议 | 无未闭环 P0/P1；§6 受限项**如实标注**且不计入通过；22 端点契约覆盖率、隔离回归（无 500）、错误码逐码呈现必须给出结论与证据；测试跳过项须写明原因／影响／补测计划 |
| 移交物 | 测试计划／测试用例／测试报告（含跳过项说明与 E2E 证据）／测试回溯对比审计报告（`doc/audit/verification/`） |

---

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-10-01 | AD-OpenBase-Dev／FD-OpenBase-Dev | 初始创建（补齐 `coding-stage-execution` §3.10 要求的**测试移交说明**，与《开发审计移交材料-v1.4.10》配套）：移交范围与上限（22 端点 ＋ 12 页面；**0 提交，均在工作区**）；测试环境与入口（后端 `uvicorn openbase.demo_app:app`／前端 Vite＋vitest＋Playwright）；**开关矩阵**（`enforce_org_alias` 红线／探活开关／联调前置）；判据复现命令（后端 95 passed／`ruff` 通过／前端 239 passed／L1-L3 PASS／构建通过）；**10 项测试重点**（按风险排序，含写操作真实联调与权限修复后口径）；受限与未覆盖项 7 类（含联调前置未闭合、子标签不做、重复率未实测、并行抖动）；环境使用提示 5 条；准入准出建议。状态 [Review]。 |
