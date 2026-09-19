# OpenBase 问题跟踪记录 - v1.4.7

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.7（四仓日志接入补完 · 日志域收官 · 跨仓，承接型小版本） |
| 文档版本 | v1.3.0 |
| 状态 | [Review] |
| 作者 | AT-OpenBase-Test / AD-OpenBase-Dev |
| 创建日期 | 2026-09-19 |
| 存放 | doc/operation/ |
| 来源 | 《OpenBase-测试报告-v1.4.7》（BL-147-05 专项验收，**结论：不通过**） |

---

## 1. 缺陷清单（DEF）

| 缺陷 ID | 级别 | 来源 | 归属 | 问题描述 | 证据 | 修复状态 | 复测结果 |
|---------|:----:|------|------|---------|------|:--------:|---------|
| **DEF-BE-147-001** | **P0** | BL-147-05 / TT-147-005 | **DPS 仓（跨仓，经本仓编排器配置修复）** | 未透传网关 `X-Request-Id`：首轮 dps 族 6/6 原文未命中；DPS 采集日志仅含**本地生成** id | `bl147-05-chain-consistency.json`；《测试报告-v1.4.7》§2.1/§7 | **已修复（2026-09-19）**：本仓编排器注入 `TRUSTED_PROXY_SOURCES='openbase-dps-proxy,openbase-orchestrator'`（DPS 既有受信判定即生效，未改其代码） | **复测通过**：业务路径 7/7 命中（探活路径 3 次按契约豁免输出 `-`） |
| **DEF-BE-147-002** | **P0** | 同上 | **OpenRAG 仓（跨仓，经本仓编排器配置修复）** | ① 未透传 `X-Request-Id`（rag 族 6/6 未命中）② 请求日志**非 JSONL**（structlog 控制台渲染器，采集文件应用日志行 0） | 同上 + `bl147-05-jsonl-contract.json` | **已修复（2026-09-19）**：编排器注入 `OPENRAG_LOG_JSON='true'` + `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES='["openbase-rag-proxy"]'`（**必须 JSON 数组形态**，逗号串触发 pydantic-settings `SettingsError` 并使服务启动即崩） | **复测通过**：rag 族 10/10 命中（业务 5/5）；应用日志行 41 / 合法率 100% |
| **DEF-BE-147-003** | **P1** | 同上 | **OpenMemory 仓（经本仓编排器配置修复）** | 透传行为按路径分化：`/health` 命中、业务路径 `/api/v1/monitor` 0/5 命中（日志中为本地生成 id） | `bl147-05-chain-consistency.json` §7.2/§7.4 | **已修复（2026-09-20）**：编排器注入 `OPENMEMORY_IDENTITY_TRUSTED_PROXY_SOURCES='["openbase-memory-proxy"]'`。根因：`/health` 在 OpenMemory `IdentityTrustConfig.whitelist_paths` 内 → 身份门直接放行、不裁决 `request_id`，由 `StructuredLogMiddleware` 回退复用合规入站头（故表现为「探活命中」）；业务路径走门裁决，白名单为空 → `allow_reuse=False` → 忽略网关 id 并本地重生成 | **复测通过**：业务路径 **5/5** 命中，且全部返回 200（未触发 M2 角色/租户校验副作用） |
| **DEF-BE-147-005** | **P1** | 2026-09-19 复测（修复副作用）；**2026-09-20 已定位** | 本仓（rag-proxy 注入策略）/ OpenRAG（保留码语义） | **修复 DEF-002 时引入**：启用 OpenRAG M2 受信模式后，`rag-proxy/collections` 由 **200 → 400（响应体为空）** | **定位证据**：`doc/test/evidence/v147/def005-rag400-probe-20260920.md`（8 组消元矩阵 + 源码行号） | **根因已定位（2026-09-20）**：OpenRAG `identity_gate.py:224-239` 的「保留租户码碰撞」防护——M2 受信路径下 `X-Tenant-ID` **缺省即 `default`**，而 `default`/`openrag-local` 是 OpenRAG **本地保留租户码**（禁入受信入站）→ 400 `BIZ_RESERVED_TENANT_CODE_COLLISION`。实测「受信来源 + 任一身份头」即 400，仅带 `X-Proxy-Source`（无身份头）为 200，与角色码/头值/主体 id 形态无关 | **待裁定处置**（A 换非保留租户码／**B rag-proxy 对 OpenRAG 不注入身份头（建议）**／C OpenRAG 侧放行）；派生次级发现：拒绝响应无 body 且无日志原因（可排障性缺陷） |
| DEF-BE-147-004 | P2（工具链） | 首轮验收执行 | 本仓（验收脚本） | 新增验收脚本首轮失败：① 含中文的 `.ps1` 若无 UTF-8 BOM，Windows PowerShell 5 按 ANSI 解析 → `ParserError UnexpectedToken`；② `$ErrorActionPreference='Stop'` 下 Python 校验器的 stderr（适配器 WARN）被 PS5 视为终止性错误 → 脚本中断（校验证据缺失） | 本轮复现与修复记录；`scripts/bl147_05_e2e_check.ps1` 注释 | **已闭环** | 已复跑通过（三段证据齐备） |

**跨仓处置建议**（按《OpenBase-R384四仓施工派单》§3 核实项③「四仓受信来源判定口径对齐」）：

| 仓 | 建议动作 |
|----|---------|
| DPS | 复核 `X-Proxy-Source: openbase-dps-proxy` 是否被判为受信来源；确认 `identity.request_id` 中间件在实启路径（`rest_api.app:app`）下对**入站** `X-Request-Id` 的复用分支生效（附：其 P1 filter 落点修正尚在工作树未提交） |
| OpenRAG | ① 复核 `_is_trusted_source` 判定与 `set_request_id(rid)` 分支；② 采集/联调环境启用 `json_format=True`（或新增独立开关 `OPENRAG_LOG_JSON=true`），使请求日志输出 JSON Lines |
| OpenMemory | 定位 `/api/v1/monitor` 与 `/health` 的差异（是否存在未注入身份头的转发分支，或中间件按路径跳过 `request_id_ctx` 赋值） |

## 2. 变更请求（CR）

| CR ID | 来源 | 内容 | 影响 | 状态 |
|-------|------|------|------|:----:|
| CR-147-001 | BL-147-04 收口（2026-09-19 人工裁定） | 「采集文件抽样 100% 行为合法 JSON」判据**收窄**为四仓**应用日志行**；uvicorn 等框架自身输出行不纳入 | 联动 7 份文档升版（DevLogReport / 覆盖状态说明 / 施工派单 / Backlog / 改动包 / 分发清单 / 候选需求池 §1.15） | **已批准**（人工裁定） |
| CR-147-002 | 本轮验收（DEF-BE-147-002） | 若四仓启用 JSON Line 输出，告警口径需同步复核（OpenRAG 现为控制台文本，属**实现偏差**而非裁定范围） | 跨仓派单项 | 待分发 |
| CR-147-003 | 本轮验收（DEF-BE-147-004） | 本仓验收工具链规范补入：`.ps1` 须 UTF-8 BOM；调用 native 命令前须处理 stderr 与 `ErrorActionPreference` 的相互作用 | 本仓工具约定（已写入脚本注释） | 已实施 |

## 3. 风险归集检查

> 本章节为必填项，用于确认本版本所有 P1+ 风险/问题已归集到技术债务总表。

| 检查项 | 结果 | 说明 |
|:-------|:----:|:-----|
| 本阶段 P1+ 风险是否已归集 | ✅ | 已归集/沿用：**TD-新增-020**（R-384 四仓日志接入交付欠账，本版本偿还范围；BL-147-05 未通过 → **仍为待偿还**）；本轮 P0 缺陷 DEF-BE-147-001/002 与 P1 缺陷 DEF-BE-147-003 属**跨仓实现缺陷**，先按跨仓派单闭环，若 v1.4.7 无法闭合则升级登记为新的交付欠账条目（建议 TD-新增-021，待版本收口时定稿） |
| 未归集风险 ID 及原因 | 无（待定稿项已标注） | 建议新增条目 TD-新增-021 的登记时点为「v1.4.7 收口/发布前」，届时按 15 字段标准格式补入《技术债务总表》，避免过早登记后反复改版 |
| 归集日期 | 2026-09-19 | — |
| 技术债务总表版本 | v0.5.1（2026-09-16） | 本轮未改版；如登记 TD-新增-021 则同步升版 |

## 4. 结论（v1.2.0 更新）

- **BL-147-05 的核心判据（串联一致性）已达成**：复测 2（2026-09-20）**业务路径 22/22 = 100%**（dps 7/7、rag 5/5、memory 5/5、llm 5/5），探活/豁免路径 18/18 亦全部命中；四仓应用日志行合法率 **100%**；`repo_log` 可检索四仓覆盖 4/4 且 `request_id` 反查命中。
- **缺陷闭环**：DEF-BE-147-001（DPS）、DEF-BE-147-002（OpenRAG）、DEF-BE-147-003（OpenMemory）**均已修复并复测通过**；三处修复均为**本仓编排器 env 注入**（信任链白名单 / JSONL 开关），**未改他仓代码**。
- **剩余阻塞 1 项**：**DEF-BE-147-005（P1）** —— `rag-proxy/collections` 在 OpenRAG M2 模式下由 200 变 400（复测 2 仍复现，且响应 request_id 与网关一致，即串联正常、功能异常）。
- 版本门禁：v1.4.6 Phase 6 门禁（M10/M11）**仍未闭合**（待 DEF-005 闭环 + 测试回溯审计）；TD-新增-020 **不得**置为「已偿还」。

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-19 | AT-OpenBase-Test | 初始创建：v1.4.7 问题跟踪记录。登记 4 项缺陷（3 项 P0/P1 跨仓待修复 + 1 项 P2 工具链已闭环）、3 项变更请求（含人工裁定 CR-147-001）、**风险归集检查章节**（TD-新增-020 仍为待偿还；建议 TD-新增-021 待版本收口定稿）；结论：回退 Step 3，跨仓派单修复 |
| v1.1.0 | 2026-09-19 | AD-OpenBase-Dev | **修复与复测登记**：DEF-BE-147-001/002 由「待修复」改为「**已修复 + 复测通过**」（本仓编排器 env 注入：dps `TRUSTED_PROXY_SOURCES`；openrag `OPENRAG_LOG_JSON` + `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES`（JSON 数组形态坑））；新增 **DEF-BE-147-005（P1，M2 激活副作用）**；DEF-BE-147-003 标注「已排除本仓、差异在 OpenMemory 侧」；§4 结论更新为「阻塞面收敛为 2 项」；依据《OpenBase-测试报告-v1.4.7》§7 |
| v1.2.0 | 2026-09-20 | AD-OpenBase-Dev | **DEF-BE-147-003 闭环**：OpenMemory 由「仍开放」改为「**已修复 + 复测通过**」（编排器注入 `OPENMEMORY_IDENTITY_TRUSTED_PROXY_SOURCES=["openbase-memory-proxy"]`；根因＝`whitelist_paths` 内 `/health` 免门裁决致「探活命中假象」，业务路径受信白名单为空 → 本地重生成）；§4 结论更新为「**串联判据 100% 达成**（22/22），剩余阻塞 1 项（DEF-005）」；依据《OpenBase-测试报告-v1.4.7》§7.4 |
| v1.3.0 | 2026-09-20 | AD-OpenBase-Dev | **DEF-BE-147-005 根因定位**：抓取 400 响应体（网关与上游均为**空 body**）并做 8 组逐头消元 → 定位 OpenRAG `identity_gate.py:224-239`「保留租户码碰撞」防护（M2 下 `X-Tenant-ID` 缺省即保留码 `default` → 400 `BIZ_RESERVED_TENANT_CODE_COLLISION`）；新增证据 `doc/test/evidence/v147/def005-rag400-probe-20260920.md`；派生次级发现「拒绝响应无 body/无原因日志」；处置待人工裁定（建议方案 B） |

