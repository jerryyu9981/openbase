# DPS v2.12.1 补丁发布回执（跨仓：DEF-1410-T4-02／03 正式发布落点）

| 项目 | 内容 |
|------|------|
| 回执对象 | 跨仓**缺陷反馈闭环**（**非派单**）：OpenBase v1.4.10 **Step 4 真实上游集成**上报 DPS 侧 2 项上游缺陷 **`DEF-1410-T4-02`（P2）／`DEF-1410-T4-03`（P3）** |
| 回执版本 | **v1.0.0** |
| 状态 | **[Review]** |
| 日期 | 2026-10-02 |
| 来源 | DPS 仓 `main @ f065698`（**发布提交 `13f99ef`**；tag **`v2.12.1`**；**三远程一致**：origin／backup／github） |
| 交付阶段 | **补丁版已发布（Dev 环境）**；**Test／Pro 未部署** |
| 依据 | 用户 2026-10-02 决策「**另发 DPS 补丁版 `v2.12.1`**」（DPS 侧 CHG-v2121-001） |
| 编制人 | PM-OpenBase-Dev（跨仓台账） |
| 存放 | `doc/test/evidence/v1410/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-02 | PM-OpenBase-Dev | 初始版本：DPS `v2.12.1` 补丁发布事实、与本仓两项缺陷的闭环对应、验证证据、对本仓的影响与处置、可复跑判据与结论 |

---

## 1. 发布事实（可复跑）

| # | 项 | 事实 |
|:-:|----|------|
| 1 | 发布版本 | **`v2.12.1`**（Patch Release；**功能基线 `v2.12.0`**） |
| 2 | 主题 | 跨仓缺陷闭环（未知 code 资源语义 **500／422 → 404**）＋ 发布记录回填 |
| 3 | 发布提交 | **`13f99ef`**（`release(2.12.1): 版本号原子对齐 …`） |
| 4 | Tag | **`v2.12.1`**（annotated，对象 **`a67c687f`**，peel **`13f99ef`**） |
| 5 | 三远程一致性 | `main` `13f99ef` ↔ `f065698`（记录同步提交）与 tag 对象 `a67c687f`／peel `13f99ef` 在 origin／backup／github **100% 一致** |
| 6 | 既有 tag 处置 | **`v2.12.0` tag 保持不动**（对象 `2125d314`／peel `516d4dd`）——**未重打、未改写引用** |
| 7 | 版本号落点 | **5 处**统一至 `2.12.1`（`src/config.py` version／mcp_server_version ＋ 4 处 DevFlow 配置）；版本敏感断言 `tests/test_v2_9_1_permission_mapping.py` 同步 |
| 8 | 数据面 | **零结构变更**（无新增迁移步骤）⇒ 回滚为**纯代码回滚**，目标 **`v2.12.0`**（`516d4dd`） |
| 9 | 环境范围 | **Dev**（单服务 `uvicorn rest_api.app:app`，`127.0.0.1:8030`）；**Test／Pro 未部署** |

## 2. 与本仓缺陷的对应关系

| 本仓缺陷 | 级别 | 现象（本仓观测） | DPS 侧根因 | DPS 侧修复 | 状态 |
|:--------:|:----:|------------------|-----------|-----------|:----:|
| **DEF-1410-T4-02** | P2 | `GET /templates/{code}/preflight`（code 不存在）经 `dps-proxy` 透传上游 **500 INTERNAL_ERROR**，契约（API 设计 §4）预期 **404** | ① 影响面 SQL **类型不匹配**：`annotation.template_id`（text）与 `annotation_template.id`（uuid）在 **PostgreSQL** 上异型等值比较（`operator does not exist: text = uuid`；SQLite 动态类型不暴露）；② **资源存在性判定滞后** | 影响面 SQL 统一 `CAST(a.template_id AS TEXT) = CAST(t.id AS TEXT)`（双后端可移植）＋ preflight 路由**资源存在性优先** | ✅ **已闭环并正式发布** |
| **DEF-1410-T4-03** | P3 | `GET /templates/{code}/diff`（code 不存在）上游返回 **422 VALIDATION_ERROR**，与设计「**404 ＝ 资源不存在**」口径不一致 | **必填查询参数校验先于资源存在性判定**（422 遮蔽资源语义） | diff 路由**资源存在性优先**：未知 code → **404**；**模板命中但缺 `from`／`to` 仍 422**（字段级明细） | ✅ **已闭环并正式发布** |

> **共性根因**：两项同源于「**资源存在性判定未前置**」；修复统一为资源存在性优先口径，对齐 DPS《API 接口设计文档》§4 错误码表。**不影响既有 200 正常路径**，**无 DB 结构变更**。
> DPS 侧闭环记录：`doc/release/DPS-问题跟踪记录-v2.12.0.md` **§5**（根因与修复）／**§6**（补丁发布）。

## 3. 验证证据（DPS 侧，可复核）

| # | 项 | 结果 |
|:-:|----|------|
| 1 | 版本契约 ＋ 跨仓修复用例 | **101 passed / 0 failed**（`test_version_contract.py` ＋ `test_v2_9_1_permission_mapping.py` ＋ `test_template_preflight_v2_11.py` ＋ `test_v2_11_api_contract_http.py`） |
| 2 | 全量回归 | **3 failed（H 类绝对性能，环境敏感）/ 1735 passed / 3 skipped / 1 xfailed / 1 xpassed**（944.72 s） |
| 3 | 环境类失败隔离复跑 | 单跑 `TestPerformanceSmoke` ⇒ **2 failed / 3 passed**：`test_health_ready_latency` **通过**；余 2 项（登录 762.6 ms／OpenAPI 2437.5 ms）与 **v2.12.0 基线口径一致** ⇒ **相对基线不劣化** |
| 4 | 静态门禁 | `ruff`（改动文件）**All checks passed**；`compileall` **exit 0** |
| 5 | 运行态自证 | 未知 code 经运行态请求稳定 **404**（DPS《问题跟踪记录-v2.12.0》§5 验证列） |
| 6 | 缺陷守护用例 | `test_route_unknown_code_404`（preflight）／`test_nonexistent_template_404`／`test_nonexistent_template_with_only_target_version_404`（diff）＋ `test_missing_required_query_params_422`（模板命中缺参仍 422） |

## 4. 可复跑判据

| # | 目的 | 命令（工作目录 `DPS/src`） | 期望 |
|:-:|------|---------------------------|------|
| 1 | 跨仓缺陷修复面 | `python -m pytest tests/test_template_preflight_v2_11.py tests/test_v2_11_api_contract_http.py -q` | 全绿（未知 code → 404；模板命中缺参 → 422） |
| 2 | 版本契约与版本敏感断言 | `python -m pytest tests/test_version_contract.py tests/test_v2_9_1_permission_mapping.py -q` | 全绿（`settings.version == "2.12.1"`） |
| 3 | 三远程一致性 | `git ls-remote {origin,backup,github} refs/heads/main 'refs/tags/v2.12.1*'` | main ＋ tag 对象 `a67c687f` ＋ peel `13f99ef` 三组 hash 一致 |
| 4 | 版本号落点 | 读取 `src/config.py`、`.devflow/config.json`、`.devflow/project-config.json`、`.devflow/state.json`、`devflow-plugin/devflow-config.json` | 5 处均为 `2.12.1` |

## 5. 对本仓（OpenBase v1.4.10）的影响与处置

| # | 项 | 结论／处置 |
|:-:|----|-----------|
| 1 | 本仓代码改动 | **无需改动** —— 本仓 `dps_proxy` 为**保真透传**，语义修正发生在上游；本仓 `OpenBase-测试报告-v1.4.10` §6 已登记两项为 **CLOSED** |
| 2 | 消费约束 | **不变** —— 层级能力仍**非持久**（DPS `TD-3044`，重启即失）／深度 **≤2 层**／权限沿用 `tag:*`／引用键为运行态 `TagValue.parent_value_id`；本补丁**不改变**上述任何约束 |
| 3 | 本版需求 §7 排除项 | **继续有效**（本仓 v1.4.10 **未接入**子标签／层级能力） |
| 4 | 缺陷台账 | `DEF-1410-T4-02／03` 由「DPS 侧已修复（未发布）」升级为「**已修复并随 `v2.12.1` 正式发布（Dev）**」；**Pro 环境部署后**方可标注为生产可用 |
| 5 | 联调口径 | 未知 code 的资源语义以 **404** 为准（不得再以 500／422 作为契约预期）；模板命中缺参仍为 **422** |
| 6 | 派单台账回填 | 《OpenBase-v1.4.10-跨仓改动规划与派单》**§3.2 已执行交付留痕**新增本行（v1.11.0） |

## 6. 结论

| 项 | 结论 |
|----|------|
| 缺陷闭环判定 | **已闭环 ＋ 已正式发布（Dev）**：`DEF-1410-T4-02`／`03` 修复随 tag **`v2.12.1`** 出仓，三远程一致 |
| 本仓 v1.4.10 阻塞性 | **不阻塞**（本版未接入该能力；且本仓为透传方，无代码改动面） |
| 遗留动作 | ① **Test／Pro 环境部署**（DPS 侧后续人工阶段）后本收据可最终关闭；② 若本仓后续版本需消费子标签能力，须**另立版本**并重出回执 |
| 回执性质 | 本回执为**跨仓缺陷闭环的发布落点登记**，**不改变** DPS `v2.12.0` 回执（`dps-v2120-tag-hierarchy-receipt-20260930.md` v1.3.1）的任何结论 |
