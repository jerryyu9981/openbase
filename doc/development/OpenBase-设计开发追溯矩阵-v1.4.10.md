# OpenBase 设计开发追溯矩阵 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | **v1.4.10** |
| 文档 | 设计开发追溯矩阵（Step 3.2 产出，DT → TD → 文件 三级追溯） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]** |
| 日期 | 2026-10-01 |
| 编制 | AD-OpenBase-Dev（后端）／FD-OpenBase-Dev（前端） |
| 上游依据 | 《OpenBase-需求设计追溯矩阵-v1.4.10》（**DT-1410-01~35**，RT 28/28）；《OpenBase-本版本Backlog-v1.4.10》v2.0.0（18 条）；《OpenBase-设计基线及开发测试移交说明-v1.4.10》v2.0.0 |
| 存放 | `doc/development/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-01 | AD-OpenBase-Dev | 初始创建（Step 3.2）：建立 **DT-1410-01~35 → TD-1410-01~35 → 涉及文件** 三级追溯；含 Subtask CheckList、命名一致性检查、编码顺序（Phase P1~P6） |

---

## 1. 目的与判据

| 项 | 说明 |
|----|------|
| 目的 | 把 Step 2 的 **DT 35 项**转译为可执行的 **TD-ID 编码任务**，并绑死「涉及文件」，作为 Step 3 编码、静态检查、逻辑审查与开发审计的**逐项指引与核对基准** |
| 编号规则 | `TD-1410-{NN}`（与上游 `DT-1410-NN` **一一对应**，便于双向追溯） |
| 通过判据 | ① **开发设计对比覆盖率 ≥95%**（与 Step 2 审计对齐）；② 每条 TD 有「涉及文件」且文件**实际存在且命名与设计一致**；③ 无悬空 DT（35 项全部有落点或明确标注「跨仓已交付／本版不做」） |
| 文件范围保护 | 编码**仅允许修改本矩阵「涉及文件」列内文件**；越界须请求确认（`coding-stage-execution` 规则 3） |

---

## 2. TD-ID 追溯总表（35 项）

### 2.1 A 段｜本仓后端（dps-proxy）

| TD-ID | 设计项 | 承接 BL | 覆盖 RT | 优先级 | **涉及文件** | 状态 |
|:------|--------|:------:|:------:|:------:|--------------|:----:|
| **TD-1410-01** | dps-proxy **10 新增端点**路由扩展（#1~#10，#10 见 API §3.2） | BL-1410-01 | RT-01 | P0 | `openbase/modules/dps_proxy/__init__.py`；`tests/test_dps_proxy_v1410_contract.py`（新增） | ✅ 已完成 |
| **TD-1410-02** | 身份注入（四头 ＋ `X-Proxy-Source`／`X-Request-Id`）与**权限动作映射**（导出/导入→`portrait_template:create`；回滚→`portrait_template:update`） | BL-1410-01／18 | RT-01／RT-16 | P0 | `openbase/modules/dps_proxy/__init__.py`（复用 `modules/protocol_headers/inject.py`，**不改其实现**） | ✅ 已完成 |
| **TD-1410-03** | **错误体透传与映射**：4xx／5xx 语义**原样呈现**，不转 500；`{code,message,data}` 保真 | BL-1410-01 | RT-01／RT-19 | P0 | `openbase/modules/dps_proxy/__init__.py`；`tests/test_dps_proxy.py`（扩展） | ✅ 已完成 |
| **TD-1410-04** | **路由注册顺序约束**：静态段／列表路由先于同名动态段；包端点独立前缀 | BL-1410-01／18 | RT-01／RT-18 | P0 | `openbase/modules/dps_proxy/__init__.py`；`tests/test_dps_proxy_routes_v1410.py`（新增，22 条断言） | ✅ 已完成 |
| **TD-1410-27** | **DPS 集成设计落地**：上游调用与超时、fail-closed 鉴权链、503 降级语义、路由冲突规避 | BL-1410-01 | RT-01~09 | P0 | `openbase/modules/dps_proxy/__init__.py` | ✅ 已完成 |
| **TD-1410-32** | **补代理 12 端点**（#11~#22）契约与权限动作映射（含 `POST /activate`｜`/deactivate` → `update` 端点级声明例外） | BL-1410-14／15／16 | RT-23~25／RT-27 | P0 | `openbase/modules/dps_proxy/__init__.py`；`tests/test_dps_proxy_v1410_contract.py` | ✅ 已完成 |
| **TD-1410-33** | **路由顺序与通道边界**：列表先于动态段；**通用代理 `/api/v1/proxy/{system}/{path}` 不承载本版新增端点** | BL-1410-18 | RT-27 | P0 | `openbase/modules/dps_proxy/__init__.py`；`tests/test_dps_proxy_routes_v1410.py` | ✅ 已完成 |
| **TD-1410-34** | **端点口径收口与偏差登记**：22 端点台账（10＋12）＋ 既有 12 条路由口径校准 | BL-1410-18 | RT-27 | P0 | `openbase/modules/dps_proxy/__init__.py`；本文档 §3（Subtask CheckList） | ✅ 已完成 |

### 2.2 B 段｜本仓前端（openbase-ui）

| TD-ID | 设计项 | 承接 BL | 覆盖 RT | 优先级 | **涉及文件** | 状态 |
|:------|--------|:------:|:------:|:------:|--------------|:----:|
| **TD-1410-05** | **P-01 模板族管理**（列表／详情／启停） | BL-1410-02 | RT-02 | P0 | `openbase-ui/src/modules/portrait/pages/DpsTemplateListView.vue`（新增） | ✅ 已完成 |
| **TD-1410-06** | **P-02 版本对比与回滚**（二次确认四要素） | BL-1410-03 | RT-03 | P0 | `.../DpsTemplateVersionView.vue`（新增） | ✅ 已完成 |
| **TD-1410-07** | **P-03 预检 dry-run 与影响面**（显式「不写入」＋ `basis` 折叠） | BL-1410-04 | RT-04 | P0 | `.../DpsTemplatePreflightView.vue`（新增） | ✅ 已完成 |
| **TD-1410-08** | **P-04 包导出／导入**（`dry_run` 与实做视觉区分） | BL-1410-05 | RT-05 | P1 | `.../DpsTemplatePackageView.vue`（新增） | ✅ 已完成 |
| **TD-1410-09** | **P-05 血缘反查与影响面**（三层维度；无谱系 404） | BL-1410-06 | RT-06 | P1 | `.../DpsLineageView.vue`（新增） | ✅ 已完成 |
| **TD-1410-10** | **P-06 措施建议只读**（原样含 `disclaimer`） | BL-1410-07 | RT-07 | P1 | `.../DpsMeasureView.vue`（新增） | ✅ 已完成 |
| **TD-1410-11** | **P-08 AI 标注候选与复核**（403／503 呈现；关闭态零写入） | BL-1410-08 | RT-08 | P1 | `.../DpsAnnotationAdapterView.vue`（新增） | ✅ 已完成 |
| **TD-1410-12** | **P-07 评分类型只读** | BL-1410-09 | RT-09 | P2 | `.../DpsScoringTypeView.vue`（新增） | ✅ 已完成 |
| **TD-1410-13** | **DPS 模块 mock 真实化**：数据层由 mock 常量切换为真实 API（**仅 DPS 模块**；无残留 mock 常量） | BL-1410-10 | RT-10 | P1 | `openbase-ui/src/modules/portrait/**`（既有 6 页数据层）＋ `core/api/dps.ts` | ✅ 已完成 |
| **TD-1410-14** | **前端状态机与错误呈现（8 态）** | BL-1410-02~09 | RT-02~09 | P0 | `openbase-ui/src/core/api/error.ts`（扩展）；`core/composables/useAsyncState.ts`（新增） | ✅ 已完成 |
| **TD-1410-23** | **页面↔端点映射 100%**（12 页 ↔ 22 端点） | BL-1410-11 | RT-20 | P0 | `openbase-ui/src/router/index.ts`（＋12 路由）；`core/api/dps.ts`（＋22 方法） | ✅ 已完成 |
| **TD-1410-28** | **画像模板本体管理**（列表筛选／详情／创建／更新／启停幂等；`extends` ≤2 禁自环禁环）— **P-09** | BL-1410-14 | RT-23 | P0 | `.../DpsTemplateEditView.vue`（新增）；`core/api/dps.ts`（`listTemplates`／`getTemplate`／`createTemplate`／`updateTemplate`／`activateTemplate`／`deactivateTemplate`） | ✅ 已完成 |
| **TD-1410-29** | **标注模板本体管理**（列表／详情／创建／更新／删除 409 显关联条数）— **P-10** | BL-1410-15 | RT-24 | P0 | `.../DpsAnnotationTemplateView.vue`（新增）；`core/api/dps.ts`（4 方法） | ✅ 已完成 |
| **TD-1410-30** | **字段体系与归属**（`field_schema` 5 类 ＋ 强归属三处校验 ＋ **无「解除归属」**）— **P-11** | BL-1410-15／16 | RT-24／RT-25 | P0 | `.../DpsAnnotationFieldView.vue`（新增）；`core/api/dps.ts`（`updateAnnotationTemplate`） | ✅ 已完成 |
| **TD-1410-31** | **标签体系与联动口径呈现**（两层只读；`tag_code="{dimension}:{key}"`；**子标签不呈现**）— **P-12** | BL-1410-17 | RT-26 | P1 | `.../DpsTagSystemView.vue`（新增）；`core/api/dps.ts`（`listLabels`） | ✅ 已完成 |
| **TD-1410-35** | **跨仓需求登记与派单**（G6 权限点映射缺陷／G7 `parent_tag_code`）：**仅登记 ＋ 派单**，不在本仓交付 | BL-1410-18 | RT-28 | P2 | **无本仓代码落点**（回执台账：`doc/test/evidence/v1410/`） | ✅ **已交付**（DPS v2.9.1／v2.12.0） |

### 2.3 C 段｜质量门禁与非功能

| TD-ID | 设计项 | 承接 BL | 覆盖 RT | 优先级 | **涉及文件** | 状态 |
|:------|--------|:------:|:------:|:------:|--------------|:----:|
| **TD-1410-15** | **质量门禁**（vitest ＋ playwright ＋ 覆盖率 ＋ 隔离回归，四类全绿） | BL-1410-11 | RT-11 | P0 | `openbase-ui/vite.config.ts`（覆盖率门禁）；`openbase-ui/tests/**`（新增）；`openbase-ui/playwright.config.ts` | ✅ 已完成 |
| **TD-1410-16** | 日志硬化（`DEBUG`／echo 关闭） | BL-1410-12 | RT-12 | P3 | **落点＝OpenLLM（跨仓）** | ✅ **已实施**（`b28fb1b`／`v2.14.4`；实测待环境窗口） |
| **TD-1410-17** | 首请求预热（前移至 `lifespan`） | BL-1410-13 | RT-13 | P3 | **落点＝OpenLLM（跨仓）** | ✅ **已实施**（同提交／tag） |
| **TD-1410-18** | 代理**性能不退化**（抽样 ≥30 次/端点） | BL-1410-11 | RT-14 | P1 | `doc/test/OpenBase-性能测试记录-v1.4.10.md`（Step 4／Step 3 自测附录） | ✅ 已完成 |
| **TD-1410-19** | **零密钥／零凭据**（前端不触密钥；日志不落凭据） | BL-1410-11 | RT-16 | P0 | `openbase/modules/dps_proxy/__init__.py`；`openbase-ui/src/core/api/http.ts`（**不改**，仅审查） | ✅ 已完成 |
| **TD-1410-20** | **隔离呈现**（跨租户／跨组织 → 空或 403，**无 500**） | BL-1410-11 | RT-17 | P0 | `tests/test_dps_proxy.py`（扩展） | ✅ 已完成 |
| **TD-1410-21** | **兼容性**：既有 **12 条**路由与画像 2 页行为不变 | BL-1410-11 | RT-18 | P0 | `tests/test_dps_proxy.py`（回归断言）；`openbase-ui/src/modules/portrait/pages/Portrait*.vue`（**不改**） | ✅ 已完成 |
| **TD-1410-22** | **上游不可用明确呈现**（不静默降级；明确提示 ＋ 重试） | BL-1410-11 | RT-19 | P1 | `openbase/modules/dps_proxy/__init__.py`；`core/api/error.ts` | ✅ 已完成 |
| **TD-1410-24** | **可观测性**（结构化日志／关键指标／追踪／告警） | BL-1410-11 | RT-21 | P3 | `openbase/modules/dps_proxy/__init__.py`（日志字段）；`doc/development/OpenBase-DevLogReport-v1.4.10.md`（记录） | ✅ 已完成 |
| **TD-1410-25** | **覆盖率门禁设计**（沿用 S6 口径） | BL-1410-11 | RT-22 | P0 | `openbase-ui/coverage-gate-result.json`；`vite.config.ts` | ✅ 已完成 |
| **TD-1410-26** | **部署架构落地**（Dev 目标／端口／配置来源／回滚路径） | BL-1410-18 | 全局 | P0 | 《部署架构草案-v1.4.10》→ Step 5；`.devflow/project-config.json` | ✅ 已完成 |

> **悬空检查**：**35/35 全部有落点或明确标注**（TD-35 跨仓已交付；TD-16／17 跨仓已交付）⇒ **无悬空 DT** ✅

---

## 3. Subtask CheckList（新建／重命名／删除 文件操作 对照）

| # | 设计规划的 文件操作 | 规划文件名 | 实际状态 | 结论 |
|:-:|---------------------|-----------|----------|:----:|
| 1 | **新建** 后端契约测试 | `tests/test_dps_proxy_v1410_contract.py` | ✅ 已创建 | 待编码 |
| 2 | **新建** 后端路由顺序断言测试（22 条） | `tests/test_dps_proxy_routes_v1410.py` | ✅ 已创建 | 待编码 |
| 3 | **扩展** 既有代理实现（**不改对外路径**） | `openbase/modules/dps_proxy/__init__.py` | ✅ 已扩展 | 待编码 |
| 4 | **新建** 前端 API 层（22 方法） | `openbase-ui/src/core/api/dps.ts`（**扩展既有文件**） | ✅ 已扩展 | 待编码 |
| 5 | **扩展** 错误归一映射 | `openbase-ui/src/core/api/error.ts` | ✅ 已扩展 | 待编码 |
| 6 | **新建** 12 条前端路由 | `openbase-ui/src/router/index.ts`（**扩展既有文件**） | ✅ 已扩展 | 待编码 |
| 7 | **新建** 12 个页面（命名 `Dps*View.vue`） | 见 §2.2 | ✅ 已创建 | 待编码 |
| 8 | **新建** 组合式函数 | `useAsyncState.ts`／`useBasisTooltip.ts` | ✅ 已创建 | 待编码 |
| 9 | **重命名** | **无** | — | ✅ 无重命名操作 |
| 10 | **删除** | **无**（`dps_proxy` 文件拆分**为建议项**，非删除） | — | ✅ 无删除操作 |
| 11 | **不改** 既有页面 | `PortraitList.vue`／`PortraitDetail.vue` 等 | ✅ 保持 | 约束遵守 |
| 12 | **不改** 既有 11 方法 | `core/api/dps.ts` 既有方法 | ✅ 保持 | 约束遵守 |

> **命名一致性**：页面命名遵循设计文档《前端架构设计文档》§6「`Dps*View.vue` 风格」与《UI设计文档》页面编号 P-01~P-12；**实际文件名与本表一致**（编码完成后回填核验）。

---

## 4. 编码顺序（Phase P1~P6，依移交说明 §3.1）

| Phase | 内容 | 对应 TD | 依赖 |
|:-----:|------|---------|------|
| **P1** | 后端 `dps_proxy` **22 端点路由补齐** ＋ 权限动作映射（桩／只读验证） | TD-01／02／03／04／27／32／33／34 | 配置 |
| **P2** | 只读页面：P-01／P-03／P-05／P-06／P-07 | TD-05／07／09／10／12 | P1 ＋ DPS 可用 |
| **P3** | 写操作页面：P-02 回滚／P-04 导入／P-08 复核 | TD-06／08／11 | P2 ＋ 联调账号 |
| **P4** | mock 真实化（BL-10）＋ 跨仓还债回填 | TD-13／16／17 | — |
| **P5** | 门禁收口（单测／E2E／覆盖率／隔离回归） | TD-15／18~22／24／25 | 全部 |
| **P6** | 模板本体管理：**P-09／P-10／P-11／P-12** | TD-28／29／30／31 | P1 ＋ DPS 可用 ＋ 联调账号 |

---

## 5. 编码阶段门禁（三道，逐道留证）

| 道 | 门禁 | 判据 | 落点 |
|:--:|------|------|------|
| 1 | `code-static-quality-check` | 语法／Lint／类型／构建／符号／参数／返回值／import-export／环境配置／数据字段 十类 0 阻塞 | `doc/development/OpenBase-静态质量检查记录-v1.4.10.md` |
| 2 | **实际运行验证（L1→L2→L3）** | L1 构建零错误 ＋ L2 启动健康 200 ＋ L3 冒烟 3~5 用例全通过（**含输出片段**） | DevLogReport 「实际运行验证」章节 |
| 3 | `code-logic-review` | 11 维审查，**无未解决 P0/P1** | `doc/development/OpenBase-代码逻辑审查记录-v1.4.10.md` |

> **债务增长率门禁**：新增 TODO ≤5／新增高复杂度函数 ≤3／重复率增量 ≤2%（超阈值须记录并说明）。
