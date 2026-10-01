# DPS v2.12.0 标签层级能力交付回执（OB-v1.4.10-DSP-TAG-01）

| 项目 | 内容 |
|------|------|
| 回执对象 | 跨仓派单 **`OB-v1.4.10-DSP-TAG-01`**（DPS 侧「标签体系层级化（子标签能力落地）＋ 模型-表结构一致性治理」） |
| 回执版本 | **v1.3.0** |
| 状态 | **[Review]** |
| 日期 | 2026-10-01（v1.3.0 更新：**Step 5 发布与 Dev 部署完成**） |
| 来源 | DPS 仓 `main @ 516d4dd`（**Step 5 发布位**，tag `v2.12.0`；Step 4 定版位 `2aa6030`；Step 3 为 `5f2641d`）（**三远程一致**：origin／backup／github） |
| 交付阶段 | **Step 5 已发布并部署至 Dev**（Test/Pro 环境未部署） |
| 编制人 | PM-OpenBase-Dev（跨仓台账） |
| 存放 | `doc/test/evidence/v1410/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| **v1.3.0** | 2026-10-01 | PM-OpenBase-Dev | **Step 5 发布完成回填（Dev 范围）**：① 交付阶段 → **「Step 5 已发布并部署至 Dev」**；② §3 限制 1／2 由「尚未部署／尚未发布」改写为「**已部署 Dev／已发布（Dev 范围）**」；③ §7 移交 2／4 关闭（发布部署已完成）；④ §8.1 补 **Step 5 发布位 `516d4dd`（tag `v2.12.0`）**；⑤ **新增 §9「Step 5 发布事实与部署验证（可复跑）」**；⑥ §1 行 8 数值口径不变（Step 4 定版 110/110、2 failed/1734 passed）。**本仓消费约束不变：能力仍为非持久（TD-3044）且深度 ≤2 层。** |
| **v1.2.1** | 2026-10-01 | PM-OpenBase-Dev | **Step 4 定版数字订正同步**：① 新增代码覆盖率 → **110/110 = 100%**（分母含 DF-2120-01/02/03 方言拆分与专属 schema 修复生产行）；② 全量回归 → **2 failed（H 类）/ 1734 passed / 3 skipped / 1 xfailed / 1 xpassed**（相对基线 5 项不劣化；3 skipped 含 G12 真实 PG 守护，默认 SQLite 环境跳过）；§1 行 8 数值更新。其余结论不变：未发布、未部署 ⇒ §3 限制与 §4 对本仓约束继续有效。 |
| **v1.2.0** | 2026-10-01 | PM-OpenBase-Dev | **A2 PostgreSQL 实跑转通过回填（DF-2120-03）**：DPS 依共享基础设施 `.env.shared-infra`（192.168.0.151:5432/nuct）完成**真实 PG 实跑**，暴露并闭环 **DF-2120-03**（P1：`public.schema_migrations` 与 OpenBase 同名表冲突 → DPS 迁至专属 schema `platform.schema_migrations`）；新增 G12 真实 PG 守护用例（TC-079）；**新增用例定版 79 全绿**；交付位 `2f21fcb` → **`2aa6030`**；§1 补 Step 4 定版数值、§8 补 DF-2120-03、§8.1 交付位更新。**结论不变：未发布、未部署 ⇒ §3 限制与 §4 对本仓约束继续有效。** |
| v1.1.0 | 2026-10-01 | PM-OpenBase-Dev | **Step 4 测试完成回填**：① 交付阶段 → **「Step 4 测试已完成（Step 5 未开始；仍未部署）」**；② §1 补 Step 4 定版数值（新增用例 **78** 全绿／**新增代码覆盖率 100%（96/96）**／全量回归 **1 failed（H 类）/ 1735 passed**／集成＋E2E **54 passed**）；③ 阶段审计补 **测试回溯对比审计（通过）**；④ **新增 §8 测试阶段缺陷闭环**（DPS 侧 2 项 P1 真实后端缺陷 DF-2120-01／DF-2120-02 均已闭环）与 **§8.1 交付位**（Step 3 `5f2641d`／**Step 4 `2f21fcb`**）。**结论不变：未发布、未部署 ⇒ §3 限制与 §4 对本仓约束继续有效。** |
| v1.0.0 | 2026-09-30 | PM-OpenBase-Dev | 初始版本：DPS v2.12.0 Step 3 交付事实、交付内容与 G7 对应、限制（未发布／未部署／非持久／同毫秒 ID／≤2 层／形态差异）、对本仓影响、可复跑判据与结论 |

## 1. 交付事实（可复跑）

| # | 项 | 事实 |
|:-:|----|------|
| 1 | 提交 | DPS `main @ 5f2641d`（`feat(v2.12.0-step3): 标签层级能力(5端点)+孤儿模型废弃口径+/db/migrate schema限定; 73 新用例; 零回归(2 vs 基线5)`） |
| 2 | 远程 | origin／backup／github **三远程均已推送至 `5f2641d`** |
| 3 | 新增用例 | `test_v2_12_tag_hierarchy.py`（**56 passed**，首轮 RED 40 failed）／`test_v2_12_model_and_migration.py`（**17 passed**） |
| 4 | 全量回归 | `python -m pytest tests -q` ⇒ **2 failed / 1729 passed / 2 skipped / 1 xfailed / 1 xpassed**；失败 2 项＝H 类绝对性能（login 784ms／openapi 1080ms） |
| 5 | 基点比对 | `git stash` 撤下本次改动后同文件 **5 failed** ⇒ **相对基线不劣化**（2 ＜ 5） |
| 6 | 静态检查 | 改动文件 `ruff` 新增代码 0 错误 |
| 7 | 阶段审计 | 《DPS-阶段审计报告-Stage3-v2.12.0》⇒ **通过**（附 2 项 Step 4 条件）；**《DPS-测试回溯对比审计报告-v2.12.0》⇒ 通过**（遗留 P0／P1 = 0，允许进入 Step 5） |
| 8 | **Step 4 定版数值（v1.2.1）** | **新增用例 79 全绿**（`test_v2_12_tag_hierarchy.py` 58 ＋ `test_v2_12_model_and_migration.py` 21，含 G12 真实 PG 守护 TC-079，**真实 PostgreSQL 环境实跑** 79 passed / 0 failed）；**新增代码覆盖率 100%（110/110）**（分母含 DF-2120-01/02/03 方言拆分与专属 schema 修复生产行）；全量回归 **2 failed（H 类）/ 1734 passed / 3 skipped / 1 xfailed / 1 xpassed**（427.35 s，失败 2 项均为 H 类绝对性能，**相对基线 5 项不劣化**；3 skipped 含 G12 真实 PG 守护，默认 SQLite 环境跳过）；集成＋E2E **54 passed**；**A2 PostgreSQL 实跑通过**（共享基础设施 192.168.0.151:5432/nuct） |

## 2. 交付内容（与本仓 G7 的对应关系）

| # | 交付项 | 内容 | 对应原派单诉求 |
|:-:|--------|------|----------------|
| 1 | **层级能力（W1）** | 5 端点：`POST /api/v2/tags/categories/{category_id}/values`（体增可选 `parent_value_id`）／`PUT /api/v2/tags/values/{value_id}/parent`（改挂＝传父 ID、解除＝传 `null`）／`GET .../children`／`GET /api/v2/tags/hierarchy?category_id=`；**深度上限 ≤2 层**、禁自环、禁成环、同租户、同分类 | ✅ **原派单「`parent_tag_code` 落列 ＋ 层级端点」的替代实现**（见 §4） |
| 2 | 错误码 | `PARAM_TAG_PARENT_NOT_FOUND`／`_CROSS_CATEGORY`／`_SELF`／`PARAM_TAG_DEPTH_EXCEEDED`／`PARAM_TAG_PARENT_CYCLE`（400）；`PARAM_TAG_NOT_FOUND`（404，**跨租户同码不泄露存在性**） | 新增 |
| 3 | 权限点 | **无需新增**：沿用 `tag:read`（查询）／`tag:create`（创建）／`tag:update`（改挂与解除）；**不改映射表、无端点级声明** | ✅ 与本仓 `E-G6-20260930` 的 G8 类风险反向一致 |
| 4 | **孤儿模型清理（W2）** | 两处 `TagDefinition` 统一**废弃口径**（「未启用的历史声明」，不得用于新代码）；`tag_definition` 表定位明确；**引用面归 0**（用例自证） | ✅ 原派单「权限映射与孤儿模型清理」 |
| 5 | `/db/migrate` 修复（W3） | 迁移记账表**全路径 schema 限定**（PG：DPS 专属 **`platform.schema_migrations`**，与 OpenBase 同名表隔离〔DF-2120-03〕；SQLite：`schema_migrations`〔DF-2120-01〕）⇒ 运行态非 500，**A2 真实 PG 实跑通过** | 附加（DPS 侧 TD-3041 残余 B） |

## 3. **重要限制（消费前必读）**

| # | 限制 | 影响 |
|:-:|------|------|
| 1 | **已部署至 Dev**（2026-10-01） | DPS `v2.12.0` 已**发布并部署至 Dev 环境**（单服务 `uvicorn rest_api.app:app`，`127.0.0.1:8030`，共享 PG `platform` schema）；**该能力在 Dev 运行态可用**（`GET /api/v2/tags/hierarchy` 实测 200）。**Test/Pro 环境未部署** ⇒ 本仓**不得**据本回执假设生产态可用 |
| 2 | **已发布（Dev 范围）** | tag **`v2.12.0`**（提交 `516d4dd`）已创建并**三远程（origin／backup／github）一致**；Release Note / Changelog 已出；**无 Pro 发布、无生产放行** |
| 3 | **运行态非持久**（TD-3044，P1，本版本**不修复**） | 标签分类／标签值／**层级关系**／画像-标签关联**全部为进程内内存**，**服务重启即丢失** ⇒ 不得作为持久存储；消费方须自备种子数据 |
| 4 | **同毫秒 ID 覆盖**（TD-3045，P2，本版本**不修复**） | ID 基于毫秒时间戳（`val-{ms}`）⇒ **同一毫秒内并发创建会相互覆盖**；消费方须避免同毫秒并发创建 |
| 5 | 深度上限 **≤2 层**（DPS 侧 D2 裁定） | 仅"根 → 子"一级；**不支持三层及以上** |
| 6 | **实现形态与本仓原假设不同** | 运行态**不落 `tag_definition.parent_tag_code` 列**（该列方案已被 DPS D3 裁定否决：hollow 交付 ＋ 无租户列）；父子引用键为运行态的 **`TagValue.parent_value_id`** |

## 4. **对本仓（OpenBase v1.4.10）的影响与处置**

| # | 项 | 处置 |
|:-:|----|------|
| 1 | G7 状态变更 | 由 **「⏳ 跨仓待办」** ⇒ **「🔶 已开发交付（Step 3 完成），未发布、未部署」**（**不是**"已可用"） |
| 2 | 本版需求 §7 **排除项仍成立** | 本版**不接入**子标签／层级能力 ⇒ **用例与测试不得以"子标签可用"为前提**（原约束 ① **继续有效**） |
| 3 | 消费排期 | 若本仓需消费该能力，须**另立版本**，且**前提为 DPS Step 4／5 完成并部署**；届时以 DPS 交付契约为准 |
| 4 | 原约束 ③ 改写 | 「立项≠交付」⇒ **「已开发交付 ≠ 已发布可用」**：除交付事实外，另有两项硬约束不可越过 —— **未部署** ＋ **非持久** |
| 5 | 原约束 ④ 继续有效 | 回执须附**可复跑判据**（见 §5） |
| 6 | 派单台账回填 | 《OpenBase-v1.4.10-跨仓改动规划与派单》§3.3 状态已回填（v1.9.0） |
| 7 | 债务台账 | 本仓 `TD-新增-042`（跨仓 DPS 能力未落库）⇒ 可标注 **「DPS 侧已开发交付，待发布部署后关闭」** |

## 5. 可复跑判据（在本仓本地执行，DPS 仓路径）

| # | 目的 | 命令（工作目录 `DPS/src`） | 期望 |
|:-:|------|---------------------------|------|
| 1 | 层级能力 ＋ 反例 | `python -m pytest tests/test_v2_12_tag_hierarchy.py -q` | 58 passed |
| 2 | 孤儿模型 ＋ `/db/migrate`（真实 PG） | `$env:DATABASE_URL='postgresql://nuct:***@192.168.0.151:5432/nuct'; $env:SQLITE_FALLBACK='false'; python -m pytest tests/test_v2_12_model_and_migration.py -q` | 21 passed（含 G12 真实 PG 全路径 TC-079） |
| 3 | 全量回归 | `python -m pytest tests -q` | 仅 H 类绝对性能用例失败（**不多于基线**） |
| 4 | 端点清单核验 | `python -c "from main import app; print([p for p in app.openapi()['paths'] if p.startswith('/api/v2/tags')])"` | 含 `/api/v2/tags/hierarchy`、`/api/v2/tags/values/{value_id}/parent`、`.../children` |

## 6. 回执结论

| 项 | 结论 |
|----|------|
| 派单交付判定 | **已交付（Step 3 开发完成）**；**未发布、未部署** |
| 本仓 v1.4.10 阻塞性 | **不阻塞**（本版需求 §7 已排除） |
| 原派单诉求 | **以替代实现满足**（层级端点 ＋ 引用键落运行态；**否决"加列"方案**并有书面裁定） |
| 后续动作 | DPS 侧 Step 4→5；**DPS 发布部署后**，本仓若需消费须**另立版本**并重出回执 |

## 7. 移交

| # | 项 | 承接 |
|:-:|----|:----:|
| 1 | DPS Step 4 测试（含 H 类性能绝对数值、`/db/migrate` PostgreSQL 实跑） | DPS 侧 **✅ 已完成**（A2 真实 PG 实跑通过，DF-2120-03 闭环；H 类判据＝相对基线不劣化） |
| 2 | DPS Step 5 发布（版本号 **5 处**统一至 `2.12.0`） | DPS 侧 **✅ 已完成（Dev 范围）**：tag `v2.12.0` 三远程一致；发布提交 `516d4dd` |
| 3 | 本仓消费立项（如需） | OpenBase 后续版本（Dev 已可用，但**非持久**，须自备种子数据） |
| 4 | `TD-新增-042` 关闭时点 | DPS **已发布并部署（Dev）** ⇒ 可标注「已开发交付 ＋ 已发布部署（Dev）」；**Pro 环境部署后最终关闭** |

## 8. 测试阶段缺陷闭环（v1.1.0 新增）

| 编号 | 级别 | 描述 | 对本仓的启示 |
|:----:|:----:|------|--------------|
| **DF-2120-01** | P1 | `public.schema_migrations` 在 **SQLite** 下报 `unknown database public` ⇒ 迁移全路径在 SQLite 后端失效 | **不得**仅以替身用例取证；同类「方言差异」修复须附**真实后端**用例 |
| **DF-2120-02** | P1 | `rollback()` 先执行 `down_sql`（DROP 记账表）再 `DELETE` ⇒ 真实后端必失败 | 同左；语句顺序类缺陷在替身下**恒不暴露** |
| **DF-2120-03** | P1 | `public.schema_migrations` 在 **PostgreSQL 共享库**（192.168.0.151/nuct）中与 **OpenBase 系统既有同名表**（列集合完全不同）冲突 ⇒ `CREATE TABLE IF NOT EXISTS` 因表已存在而跳过，后续引用 `applied_at` 列直接 `UndefinedColumnError`，迁移全路径在真实环境必然失败 | **同前**；且印证本仓与 DPS 共享同一 PG 基础设施 ⇒ **跨系统表名隔离**（专属 schema）是共享库共处的基本要求 |

> 三项缺陷均由 DPS 侧 **Step 4 新增「真实后端」用例**（真实 SQLite／真实 PostgreSQL）发现并闭环（《DPS-测试报告-v2.12.0》§5／§6.2）。
> **对本仓消费的直接影响：无**（本仓 v1.4.10 未接入该能力）；但**结论是**：若本仓后续消费该能力，联调须在**真实后端**上进行。
> **附带记录（不影响本仓）**：DPS 侧 Step 4 期间发现环境限制 —— `coverage run --source=<点分模块>` 在本机会触发 `cryptography` PyO3 双初始化而收集中断（改用不加 `--source` 的等口径跑法规避），已如实登记于其测试报告 §8 注记。

### 8.1 交付位（v1.2.0 更新）

| 阶段 | 提交 | 状态 |
|------|------|------|
| Step 3 开发 | `5f2641d` | ✅ 已人工批准（2026-10-01，裁定 D4） |
| **Step 4 测试** | **`2aa6030`** | ✅ **已完成**（回溯审计通过；**A2 真实 PG 实跑通过**，DF-2120-03 闭环；待人工批准） |
| Step 5 发布／部署 | **`516d4dd`**（tag `v2.12.0`） | ✅ **已完成（Dev 范围）**：5 处版本号统一至 `2.12.0`；tag 三远程一致；Dev 部署 ＋ 上线验证 **13/13**；**零 DB 变更**（迁移 11 步幂等）；回滚目标 `v2.9.1`（纯代码回滚） |

## 9. Step 5 发布事实与部署验证（可复跑，v1.3.0 新增）

### 9.1 发布事实

| # | 项 | 事实 |
|:-:|----|------|
| 1 | 发布版本 | **`v2.12.0`**「标签体系层级化（子标签能力落地）＋ 模型-表结构一致性治理」 |
| 2 | 发布提交 | **`516d4dd`**（`release(2.12.0): 版本号原子对齐 …`） |
| 3 | Tag | **`v2.12.0`**（annotated，对象 `2125d314`，peel `516d4dd`） |
| 4 | 三远程一致性 | tag 对象 `2125d314` 在 origin／backup／github **3/3 一致**；main `516d4dd` **3/3 一致** |
| 5 | 版本号落点 | 5 处：`src/config.py`（version／mcp_server_version）＋ `.devflow/config.json` ＋ `.devflow/project-config.json` ＋ `.devflow/state.json` ＋ `devflow-plugin/devflow-config.json` ⇒ 全部 `2.12.0` |
| 6 | 应用内版本 | `/health/readiness` 与 `/openapi.json` 均返回 **`2.12.0`** |
| 7 | 结构变更 | **零**（迁移 11 步；RUN1／RUN2 均 `status=success completed=[] skipped=[1..11]`） |
| 8 | 构建与静态门禁 | `compileall` **exit 0**；改动文件 `ruff` **0 错** |
| 9 | 上线验证 | **13/13**：健康三探针 200；`GET /api/v2/tags/hierarchy` 200；`GET /api/v2/tags/categories` 200（既有链路零回归）；**无身份头 ⇒ 401（fail-closed）**；`POST /api/v2/db/migrate` **403（非 5xx，TD-3041 残余 B 闭环）** |
| 10 | 端点清单 | OpenAPI `tags|migrate` 路径 **22 条**（v1／v2 各 11），含 `/api/v2/tags/hierarchy`、`/api/v2/tags/values/{value_id}/parent`、`/api/v2/tags/values/{value_id}/children`、`/api/v2/tags/categories/{category_id}/values` |
| 11 | 回滚 | 目标 `v2.9.1`；**纯代码回滚**（零 DB 变更）；**演练本次未重跑**（已如实登记） |
| 12 | 附条件 | A1 新端点**真实写路径** Test 冒烟；A2 CI 远端 run 读数（本机无 `gh`） |

### 9.2 本仓消费影响更新

| # | 项 | 结论 |
|:-:|----|------|
| 1 | 能力可用性 | **Dev 运行态可用**（层级查询端点 200）；**生产（Pro）不可用**（未部署） |
| 2 | **消费约束（不变）** | ① **非持久**（TD-3044，重启即失，须自备种子）；② 深度 **≤2 层**；③ 权限沿用 `tag:*`（无新权限点）；④ 引用键为运行态 **`TagValue.parent_value_id`**（非 `parent_tag_code` 列） |
| 3 | 本版需求 §7 排除项 | **继续有效**（本仓 v1.4.10 未接入子标签/层级能力） |
| 4 | 若需消费 | 须**另立版本**，在联调环境按《DPS-API接口设计文档-v2.12.0》契约对接 |
| 5 | 权威发布信息 | [DPS-Release-Note-v2.12.0.md]（DPS 仓 `doc/release/`）与《DPS-运维手册-v2.12.0》 |
