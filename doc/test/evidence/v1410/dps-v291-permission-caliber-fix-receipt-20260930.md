# DPS v2.9.1 跨仓修复交付回执（2026-09-30）

| 项 | 内容 |
|----|------|
| **回执编号** | `E-DPS-v291-20260930` |
| **对应派单** | `OB-v1.4.10-DSP-PERM-01`（**3 子项**；来源 OpenBase 侧实测 `E-G6-20260930` 的 **G6／G8／G9**） |
| **落点仓** | **DPS**（`src/`） |
| **交付版本** | **v2.9.1**（**GA 线 patch 位**最小版本化；基线 **v2.9.0**） |
| **制品提交** | `ff9fd9ff2dfa329a5e37393402ccd7635e207d1b`（口径修正） |
| **发布收尾提交** | `de106ebd15bd8a23c1a1c9ebb4869f617713bebd`（版本号原子对齐 ＋ Release Note ＋ DevFlow 记录同步；**即 Tag 指向提交**） |
| **Tag** | **`v2.9.1`**（annotated）＝ 对象 `a95f2bd3798809df25507fd905b367cb12746eb9`，peel `de106ebd15bd8a23c1a1c9ebb4869f617713bebd` |
| **远端** | **origin ＋ backup ＋ github 三仓一致**（`ls-remote` 实测：`main`／tag 对象／tag peel **三组哈希三仓相同**） |
| **执行人** | DO-OpenBase-Dev（跨仓实施） |
| **结论** | ✅ **已修复并验证**（TDD 先 RED 后 GREEN；定向回归 0 failed；**两处影响面自证**；三仓哈希一致） |

---

## 1. 版本落点裁定（为什么是 v2.9.1，而不是 v2.11.2）

> 本项为**须留痕的裁定动作**：落地前核对仓内**自身版本事实**，避免"按上一个 tag 顺延"造成版本口径错误。

| 项 | 核实结果（来源） |
|----|------------------|
| 本仓**当前版本** | **v2.9.0**（GA 线；2026-09-30 Dev 环境发布成功）—— 来源：《DPS-版本迭代路线图》§当前版本、`DPS-Release-Note-All.md` 版本总表、`.devflow/project-config.json`（`version`／`lastRelease`）、`devflow-plugin/devflow-config.json` |
| 功能线状态 | v2.10.0／v2.11.0／**v2.11.1 均已归档**；后续功能迭代号由 **v2.12.0** 承续（CHG-v290-001） |
| 变更性质 | 判定口径修正（非新功能、非破坏性）⇒ 属《DPS-版本发布策略总则》「**Patch 按需（缺陷／配置／文档）**」 |
| **裁定** | **落 GA 线 patch 位 `v2.9.1`** —— 若按"上一个 tag 顺延"发 `v2.11.2`，则等于**对已归档的功能线补丁**，且改动实际施加在 HEAD（GA 线）之上 ⇒ **版本与制品错配** |
| 附带订正 | `.devflow/config.json` 的 `projectVersion` 原为**过期的 `2.11.1`**（v2.9.0 发布时未同步）⇒ 本次一并统一为 `2.9.1`，**四处版本字段口径一致**；`.devflow/state.json` 的 `versionHistory` **补登缺失的 `v2.9.0`** |

---

## 2. 修复内容（3 子项，全部为实现侧判定口径）

判定函数：`src/middleware/permission_middleware.py` 的 `PermissionMiddleware._resolve_resource_type()`／`_resolve_action()`（**直接执行判定函数取证**，非文档声明、非人工阅读代码 —— 遵循判据纪律 **C5**）。

| 子项 | 修复前（2026-09-30 实测） | 修复后 | 落地改动 | 影响 |
|:----:|---------------------------|--------|----------|------|
| **G6** | `/api/v2/portrait/annotation-templates[/{code}]` → 判定资源 **`portrait`** | **`annotation_template`** | `SUBPATH_RESOURCE_MAP` **补键** `("portrait", "annotation-templates") → "annotation_template"` | **`annotation_template:create/update/delete` 恢复可达**（原键为 `("portrait","annotations")`，与路径第二段 `annotation-templates` **精确元组匹配不命中** ⇒ 回落 `portrait`） |
| **G8** | `POST /api/v2/portrait/templates/{code}/activate`｜`/deactivate` → 判定动作 **`create`** | **`update`** | `ENDPOINT_ACTION_OVERRIDES` **补声明** `("POST","/activate") → "update"`、`("POST","/deactivate") → "update"` | **关闭越权面**：原「仅持 `portrait_template:create` 者可启停，而仅持 `update` 者被拒」—— 与已修的回滚端点 `TD-3027` **同类残留**；审计侧动作标签**同源**（`AuditMiddleware` 一并判 `UPDATE`） |
| **G9** | `/api/v2/portrait/labels` → 判定资源 **`portrait`** | **`annotation_template`** | `SUBPATH_RESOURCE_MAP` **补键** `("portrait", "labels") → "annotation_template"` | 按 API 设计归**标注域**；**读取面不收窄**（见 §4.2） |

### 2.1 未改动项（防"顺手扩大"）

| 项 | 说明 |
|----|------|
| **方法映射主逻辑** | `POST→create / GET→read / PUT,PATCH→update / DELETE→delete` **保持不变**；仅以端点级声明作为**显式例外**承接启停（与回滚同一先例） |
| **权限点集合** | **未新增／未删除任何权限点**（沿用 `portrait_template:*`／`annotation_template:*`） |
| **既有映射** | 7 项既有 `SUBPATH_RESOURCE_MAP` 键（`templates`／`annotations`／`template-packages`／`measures`／`scoring-types`／`lineage`／`annotation-adapters`）**逐项断言未变** |

---

## 3. 交付物清单

| # | 文件 | 变更 |
|:-:|------|------|
| 1 | `src/middleware/permission_middleware.py` | `SUBPATH_RESOURCE_MAP` **+2 键**；`ENDPOINT_ACTION_OVERRIDES` **+2 声明**（含影响面自证注释） |
| 2 | `src/tests/test_v2_9_1_permission_mapping.py` | **新增守护测试**（G6／G8／G9 三组 ＋ 非回归 ＋ 访问影响自证 ＋ 版本口径） |
| 3 | `src/tests/test_v2_11_route_mapping.py` | 既有基线断言 `test_declaration_table_is_minimal_and_explicit` 由「仅 1 项」→ **显式列出 3 项**（**未**放宽为子集匹配） |
| 4 | `src/config.py` | `version`／`mcp_server_version` → **`2.9.1`** |
| 5 | `.devflow/config.json`／`.devflow/project-config.json`／`.devflow/state.json`／`devflow-plugin/devflow-config.json` | 版本号对齐 `2.9.1`；project-config 新增 `release_v291_actual` 发布记录块；state 补登 `v2.9.0`／`v2.9.1` |
| 6 | `doc/release/DPS-Release-Note-v2.9.1.md` | **新增**（版本落点裁定／三项修复／验证摘要／已知问题／升级回滚） |
| 7 | `doc/release/DPS-Release-Note-All.md`／`doc/version/global/DPS-版本迭代路线图.md` | 版本总表与总目录新增 v2.9.1；路线图 **v1.4.0 → v1.5.0**，当前版本 → v2.9.1 |

---

## 4. 验证证据

### 4.1 测试与静态检查

| 项 | 结果 |
|----|------|
| **TDD** | 新守护测试先跑 **RED：14 failed ／ 14 passed** ⇒ 补齐实现后 **GREEN** |
| **定向回归** | **21 个权限相关测试文件 ＋ 版本契约用例：503 passed ／ 1 skipped ／ 0 failed**（覆盖：权限资源类型覆盖、保留端点 RBAC、组合矩阵、身份门禁、租户隔离、审计与权限动作同源、端到端与种子集成） |
| **静态检查** | `ruff check`（本次改动 4 个文件）→ **All checks passed!** |
| **版本契约** | 升版后版本敏感用例（`test_version_contract`／`test_s5_t4_version_conflict`）**全绿**；应用内版本自证断言 `settings.version == "2.9.1"` |

### 4.2 两处「影响面自证」（本补丁的原则性要求）

> **修正不得以"静默收窄既有访问面"为代价** —— 故两项修正均附**可失败的断言**，而非口头声明。

| # | 自证内容 | 断言位置 | 结果 |
|:-:|----------|----------|:----:|
| 1 | **后缀型动作声明的影响面**：全仓以 `/activate`｜`/deactivate` 结尾的路由**仅**画像模板启停的 v2 端点及其 **v1 兼容别名**（同一语义端点）⇒ 后缀匹配不存在对其他业务面的误伤 | `test_activate_suffix_is_used_only_by_portrait_templates`（读 `app.openapi()` 全量路由） | ✅ |
| 2 | **资源修正不窄化读取面**：预设角色中凡持 `portrait:read` 者**均**持 `annotation_template:read` | `test_read_access_preserved_for_preset_roles`（读 `engines/permission_engine.py::PRESET_ROLES`） | ✅ |

> 断言设计意图：若未来出现**同后缀的其他端点**或**新增只持 `portrait:read` 的角色**，对应断言会**失败**，强制改为「带前缀的精确匹配」或补权限点 —— **而不是让问题静默通过**。

### 4.3 三仓推送核验（`git ls-remote` 实测）

| 远端 | `refs/heads/main` | `refs/tags/v2.9.1`（对象） | `refs/tags/v2.9.1^{}`（peel） |
|------|-------------------|---------------------------|-------------------------------|
| origin | `de106ebd15bd8a23c1a1c9ebb4869f617713bebd` | `a95f2bd3798809df25507fd905b367cb12746eb9` | `de106ebd15bd8a23c1a1c9ebb4869f617713bebd` |
| backup | `de106ebd15bd8a23c1a1c9ebb4869f617713bebd` | `a95f2bd3798809df25507fd905b367cb12746eb9` | `de106ebd15bd8a23c1a1c9ebb4869f617713bebd` |
| github | `de106ebd15bd8a23c1a1c9ebb4869f617713bebd` | `a95f2bd3798809df25507fd905b367cb12746eb9` | `de106ebd15bd8a23c1a1c9ebb4869f617713bebd` |

**三仓三组哈希全部一致** ⇒ 满足 `code-version-backup-management` §5.0「任一远程遗漏视为发布不完整」。

---

## 5. 未纳入本次修复（如实登记）

| # | 项 | 说明 | 处置 |
|:-:|----|------|------|
| 1 | **子标签能力**（`tag_definition.parent_tag_code` 未落库 ＋ 无层级端点） | 属**新能力**（非口径修正），需 DPS 独立版本；且本版需求 §7 已**明确排除**子标签 | 保持派单 **`OB-v1.4.10-DSP-TAG-01`**（P2，不阻塞）；对应 G7 **仍为跨仓待办** |
| 2 | **性能冒烟断言环境敏感（H 类）** | `test_v280_specialty.py::TestPerformanceSmoke` 2 项（`test_openapi_spec_latency`／`test_login_latency`）在本机超 500ms 基线。**取证**：**改动前（`stash` 回基线）隔离复跑亦超基线**（OpenAPI 最快 1311.5ms；样本 [2233.2, 1537.6, 1311.5]）⇒ **非本补丁引入**，与 v2.9.0 已登记的「1 failed（H 类环境敏感）」同源 | **保留原断言不删**（依项目既有「不得删断言换绿」纪律）；正式性能结论由专用环境 **PC-2** 承载（NFR-01~03／TD-3039） |
| 3 | **仓库级 ruff 存量** | 全仓 `ruff check .` 存量 **81 项**（分属多个既有引擎／测试文件）；**本次改动 4 个文件 0 项** | 不由本补丁承接（建议单独立项）；已在《DPS-Release-Note-v2.9.1》§5 登记 |
| 4 | **全量回归未复跑** | 补丁范围仅限权限判定映射 ＋ 版本号，已以定向回归（21 文件）＋ 版本契约覆盖其全部影响面 | 如需版本级全量回归记录，建议随 v2.12.0 功能版本常规全量一并留证（已在 Release Note §3 如实标注） |

---

## 6. 对 OpenBase v1.4.10 的影响（回填清单）

| # | OpenBase 侧文档 | 变化 |
|:-:|------------------|------|
| 1 | 《OpenBase-API接口设计文档-v1.4.10》**v1.3.0 → v1.4.0** | §3.1 改「修复前／修复后」**双列**、统计 **4／12 → 12／12**；§6 该行 **❌ → ✅**；§6.1 **G6／G8／G9 → ✅ 已闭环**（G7 补派单号）；§7 #4 结论更新、#5 **→ ✅ 已交付**；**联调预期改写** |
| 2 | 联调账号与用例口径（**强制**） | **标注模板 CRUD 须持 `annotation_template:*`**（原「须持 `portrait:*`」**作废**）；**模板启停须持 `portrait_template:update`**（原「须持 `portrait_template:create`」**作废** —— 该口径即本次修复的越权面）。Step 3／4 用例与联调账号权限准备**一律以此为准** |
| 3 | 《OpenBase-v1.4.10-跨仓改动规划与派单》 | §3.1 派单状态更新；**§3.2 回执台账新增 DPS v2.9.1 行** |
| 4 | 《OpenBase-第三方集成设计文档-v1.4.10》 | §8.1 相应条目 → ✅ 已修复 |
| 5 | 《OpenBase-技术债务总表》 | TD-新增-**041／044／045** 相应条目 **→ 已偿还**（G6／G8／G9 闭环） |
| 6 | 设计覆盖／评审／审计／移交材料 | 相应「待实测／跨仓待办」结论更新 |

> **⚠ 判据纪律留痕（C5）**：本次修复的**验收判据**为「**执行 DPS 判定函数的实测结果**」，而非 DPS 侧文档声明或人工阅读代码 —— 与 G2／G8 同类问题（**以推断代替取证**）的根因整改保持一致。
