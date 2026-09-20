# OpenBase 静态质量检查记录 - v1.4.7

> 本记录为 **v1.4.7 Step 3（开发）门禁材料之一**，按 `code-static-quality-check` 技能的 12 类检查矩阵执行与登记，作为 `code-logic-review`（代码逻辑审查）与 Stage 3 阶段审计的输入。**本记录不判定 Step 3 是否完成**，Step 3 完成与否由《OpenBase-DevLogReport-v1.4.7》与《OpenBase-阶段审计报告-Stage3-v1.4.7》统一判定。

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.7（四仓日志接入补完 · 日志域收官 · 跨仓，承接型小版本） |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 检查日期 | 2026-09-20 |
| 存放 | doc/development/ |
| 检查依据 | `code-static-quality-check`（12 类检查矩阵 + 圈复杂度/重复率/架构合规门禁）；`coding-stage-execution` §3.4a（静态质量 + 技术债务增长率 + 可观测性 + 编码约定）；仓库根 `AGENTS.md` §7/§8；`doc/development/OpenBase-设计开发追溯矩阵-v1.4.7.md`（TD-147-01~04） |

---

## 1. 检查范围与依据

### 1.1 检查对象（版本级，含两个增量）

| 增量 | 内容 | 关联 TD / 缺陷 |
|------|------|----------------|
| 增量 1 | BL-147-04 本仓采集命名对齐 + 归档命名缺陷修复 + 命名实测 | TD-147-01/02/03 |
| 增量 2 | DEF-BE-147-005（P1）修复：rag-proxy 身份头注入策略显式开关 | TD-147-04（偏差项，见追溯矩阵 §2） |

### 1.2 变更/新增文件清单（行数为 2026-09-20 文件系统实测，非 git diff）

> **口径声明**：本轮受环境约束**未执行 `git diff --numstat` / `git` 类命令**，故不给出逐文件 `+n/−m` 精确增量；下表「总行数」为文件当前总行数实测，「变更点位」为源码逐行回读确认的位置。

| 文件 | 变更 | 总行数（实测） | 变更点位（回读确认） | 增量 |
|------|------|:-------------:|---------------------|:----:|
| `scripts/service-orchestrator.ps1` | 修改 | 806 | L259 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS = 'false'`（含 L253–L258 根因/证据/回退注释）；增量 1 的命名单点与 `-Action namecheck` 见 DevLogReport §3.3 | 1 + 2 |
| `openbase/modules/logs/repository.py` | 修改 | 919 | 公开常量 `REPO_LOG_NAME_RE` + `__all__` 导出 + 命名契约注释（**正则本体零变更**） | 1 |
| `scripts/verify_repo_log_naming.py` | 新建 | 231 | 命名白名单校验工具（CLI 退出码 0/1/2） | 1 |
| `tests/test_r384_repo_log_naming.py` | 新建 | 240 | 13 例（四仓命名/归档 + 反例 + 在盘扫描 + CLI + 编排器结构护栏） | 1 |
| `tests/test_logs_service.py` | 修改 | 434 | 3 处 fixture 由硬编码日期改回 `f"openbase-{TODAY}.jsonl"` | 1 |
| `openbase/settings.py` | 修改 | 409 | L179–L187 注释 + `rag_inject_identity_headers: bool = True` | 2 |
| `openbase/modules/rag_proxy/__init__.py` | 修改 | 585 | L106–L108 docstring 增补；L118 `effective_user = user if settings.rag_inject_identity_headers else None` | 2 |
| `tests/test_rag_proxy_identity_policy.py` | 新建 | 106 | 3 例（默认注入 / 关闭不注入 / 关闭仍携带 `X-Request-Id`） | 2 |
| `tests/test_bl147_trust_env_wiring.py` | 修改 | 101 | L85–L101 新增 1 例（openbase 块须声明 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS='false'`）；该文件现 **5 例** | 2 |

**文件总数：9 个**（增量 1 五个 + 增量 2 四个，`service-orchestrator.ps1` 两增量共用，去重后 9 个）。

### 1.3 工具链（项目既有，未引入新工具）

| 项 | 值 | 来源 |
|----|----|------|
| Lint/静态检查器 | `ruff`（`select = ["E","F","W","I","UP","B"]`，`line-length=100`，`target-version=py310`） | `pyproject.toml` §[tool.ruff] / §[tool.ruff.lint] |
| 类型检查器 | **无**（dev 依赖仅 `pytest` / `pytest-asyncio` / `pytest-cov` / `ruff` / `httpx` / `aiosqlite`） | `pyproject.toml` §[project.optional-dependencies].dev |
| 测试器 | `pytest`（`testpaths=tests`，`addopts=-q`）；脚本化回归 `scripts/run_regression.py` | `pyproject.toml` §[tool.pytest.ini_options] |
| 复杂度/重复率工具 | **未配置**（无 `radon` / `lizard` / `jscpd` / `pylint`） | 同上 |
| 环境 | Windows PowerShell 5 / Python 3.10 | 全量回归日志 `logs/v147-def005-regression.txt` |

---

## 2. 十二类检查项逐项结论

| # | 检查类别 | 结论 | 依据（本轮实测命令与结果 / 不适用原因） |
|:-:|---------|:----:|--------------------------------------|
| 1 | 语法检查 | **通过（本轮实测）** | `python -m ruff check openbase tests scripts` → `All checks passed!`（0 错误）。ruff 的 `E`/`F`/`W` 规则集含语法解析（E9 类）与未定义名（F821），解析失败会直接报错。脚本化回归首段亦独立执行同一命令并输出 `=== 1/3 ruff ===` / `[OK] ruff`（`logs/v147-def005-regression.txt` L1–L3）。 |
| 2 | Lint 检查 | **通过（本轮实测）** | 同 #1：0 错误。本轮 9 个文件均在检查路径内（`openbase` / `tests` / `scripts`）。增量 1 首轮暴露的存量 Lint 类问题（W292/I001/UP037/F401 同族）此前已清零，本轮无新增违例。 |
| 3 | 类型检查 | **不适用（原因）** | 项目**未配置** `mypy` / `pyright`（`pyproject.toml` dev 依赖与配置节均无类型检查器），仓库无类型门禁约定；`AGENTS.md` §8 验证命令仅含 `ruff` 与 `pytest`。故本项不适用，**不以推测替代实测**。 |
| 4 | 构建检查 | **不适用（原因）+ 部分替代实测** | 本仓为 Python 源码项目（`pyproject.toml` 的 `[build-system]` 为 setuptools 元数据，无编译产物步骤），**L1 无独立构建动作**；按 DevLogReport §4.5 口径以 `ruff` 0 错误代替。`scripts/service-orchestrator.ps1` 为 PowerShell 脚本，**本轮未单独执行 PS 语法解析命令**（未实测），其行为由既有实跑证据间接覆盖（`-Action namecheck` 三段实测与 L2/L3 启动冒烟，见 DevLogReport §4.2/§4.5）。 |
| 5 | 符号一致性 | **通过（本轮实测）** | 只读全仓检索（Grep）`rag_inject_identity_headers` 命中 16 处，逐条回读确认口径一致：**定义** `openbase/settings.py:187`；**消费** `openbase/modules/rag_proxy/__init__.py:118`（另有 L106 注释）；**环境变量映射** `scripts/service-orchestrator.ps1:259`（`OPENBASE_RAG_INJECT_IDENTITY_HEADERS`）与 `tests/test_bl147_trust_env_wiring.py:98`（护栏断言）；其余命中为文档/证据/状态文件记录。无未定义符号、无拼写漂移、无死引用（`_build_upstream_headers` 仍被 `openbase/modules/rag_proxy/__init__.py` 内路由调用，测试 3 例直接导入）。 |
| 6 | 参数一致性 | **通过（本轮实测）** | `_build_upstream_headers(request, user)` 签名**未变更**（`__init__.py:93-95`），调用方无需改动；策略以**函数内部**决定入参有效值（L118），不新增/删除形参。定向回归 `python -m pytest tests/test_rag_proxy_identity_policy.py tests/test_bl147_trust_env_wiring.py tests/test_proxy_outbound_matrix.py tests/test_rag_proxy.py -q` → **41 passed**（用例数构成实测：3 + 5 + 11 + 22 = 41，四文件互调参数口径一致）。 |
| 7 | 返回值一致性 | **通过（本轮实测）** | 开关关闭时仍走**同一装配点** `build_outbound_headers(...)` 并返回同一 `dict[str, str]` 结构（含 `X-Proxy-Source` + `X-Request-Id`），返回类型与字段集合无漂移；由 3 例单测断言（`tests/test_rag_proxy_identity_policy.py:74/88/100`）与网关层实测共同锁定：经网关 `GET /api/v1/rag-proxy/collections` 返回 **200** 且 `data.items=12`（`doc/test/evidence/v147/def005-gateway-retest-20260920.json`）。 |
| 8 | import/export | **通过（本轮实测）** | 新增测试文件导入 `openbase.modules.protocol_headers.constants`（6 个符号）、`openbase.modules.rag_proxy._build_upstream_headers`、`openbase.settings.get_settings`，全部可解析（3 passed 即证）；ruff 的 `F401`（未使用导入）/`F821`（未定义名）0 命中。无循环依赖引入（仅测试侧引用，生产侧未新增导入）。 |
| 9 | API 字段映射 | **通过（本轮实测）** | 无接口契约变更（DevLogReport §1「无接口契约变更」声明）。运行时取证：`GET /api/v1/rag-proxy/collections` → **200**，`envelope_code=0`、`items_count=12`、`total=12`、`body_bytes=5305`；同网关 `page=0` → **400** 且 body 为 **190 字节完整 envelope**（`code=PARAM_400` + `message` + `detail[field=page,min=1]` + `request_id`）→ 字段命名、错误结构与既有设计一致，**无破坏性漂移**（依据 `def005-gateway-retest-20260920.json`）。 |
| 10 | 环境和配置 | **通过（本轮实测）** | 环境变量名与 settings 字段映射一致：`OPENBASE_RAG_INJECT_IDENTITY_HEADERS`（前缀 `OPENBASE_` + 字段名大写）↔ `rag_inject_identity_headers`；取值 `'false'` 为布尔字面量、**非密钥**，无真实密钥泄露（`settings.rag_api_key` 为既有字段，本轮未改动）。护栏用例 `tests/test_bl147_trust_env_wiring.py:98` 以正则锁定声明形态，防口径被无意改回。 |
| 11 | 数据字段 | **不适用（原因）** | 本轮**无 DTO / Schema / 数据库字段 / 迁移变更**（DevLogReport §1「无 DB schema 变更」、§3.5「无 DB schema / 接口契约 / 依赖变更」）。无字段可对，故不适用。 |
| 12 | 状态与枚举 | **通过（本轮实测，适用面有限）** | 本轮新增的状态面为**布尔策略开关**（`True`/`False` 二态），两态均有独立用例覆盖：`True` → 注入四头（L74 例），`False` → 不注入四头（L88 例）且仍携带 `X-Request-Id`（L100 例）；非法/缺省态由默认值 `True` 兜底。**无业务状态枚举新增或修改**（既有状态机与错误码未动）。 |

**十二类合计**：**本轮实测通过 9 项**（#1 语法、#2 Lint、#5 符号一致、#6 参数、#7 返回值、#8 import/export、#9 API 字段、#10 环境配置、#12 状态枚举）；**不适用 3 项**（#3 类型检查、#4 构建检查、#11 数据字段，均给出原因，其中 #4 有部分替代证据）；**失败 0 项**。

---

## 3. 补充门禁项（圈复杂度 / 重复率 / 架构合规）

| 门禁项 | 阈值 | 本轮结论 | 依据与口径说明 |
|--------|:----:|:--------:|----------------|
| 圈复杂度（单函数 ≤15，>15 阻断） | >15 = P0 | **未超阈值（未实测工具扫描）** | 本轮**未运行** `radon cc` / `lizard`（项目未配置，且本机存在长任务在跑、环境受限），标注**未实测**。以变更面核定：增量 2 可执行逻辑仅新增 **1 行条件表达式**（`__init__.py:118`）+ **4 个测试函数**（策略 3 例 + 编排器护栏 1 例），无新增分支簇；无函数因本轮改动跨过 15 复杂度门槛的迹象。 |
| 代码重复率（新代码 ≤3%，>3% 阻断） | >3% = P0 | **未超阈值（未实测工具扫描）** | 本轮**未运行** `jscpd` / `pylint --duplicate-code`（项目未配置），标注**未实测**。以变更面核定：新增生产代码为 1 行策略选择 + 注释，新增测试为独立桩（`StubRequest` + `_user_ctx`）与独立断言，未见复制粘贴式新实现。 |
| 架构合规（禁止跨层依赖） | 违规阻断 | **合规（本轮实测，源码回读）** | 改动落点：`settings.py`（配置层）→ `modules/rag_proxy/__init__.py`（模块路由/出站装配层）。rag-proxy **不新增 Repository 直调**，未出现「Controller→Repository」跨层；未新增模块、未新增依赖（`AGENTS.md` §1「禁止跨层调用」满足）。 |

---

## 4. 技术债务增长率检查（本版本相对上一版本 v1.4.6）

| 指标 | 阈值 | 本轮值 | 是否超阈值 | 依据与统计口径 |
|------|:----:|:------:|:----------:|----------------|
| 新增 TODO 数 | ≤5 | **0** | 否 | **实测（只读检索）**。口径：正则 `(TODO\|FIXME\|XXX\|HACK)` 在 §1.2 的 **9 个文件**内逐行匹配。**命中 1 处伪阳性已人工回读剔除**：`openbase/modules/rag_proxy/__init__.py:137` 注释示例文本 `如 "知识库不存在: xxx"`（大小写不敏感的 `Select-String` 会命中，大小写敏感的 ripgrep 不命中）——经逐条回读确认**非待办标记**。剔除后 **新增 TODO = 0**。 |
| 新增高复杂度函数数 | ≤3 | **0** | 否 | **未实测（工具扫描）**，按变更面核定：本轮修改的函数 1 个（`_build_upstream_headers`，仅 +1 行有效逻辑）、新增测试函数 4 个（均为线性断言），无圈复杂度 >15 者。标注「未实测」以免与工具实测混淆。 |
| 代码重复率增量 | ≤2% | **0（未实测）** | 否 | **未实测（工具扫描）**；以变更面核定无重复实现（见 §3）。标注「未实测」。 |

**结论**：三项均未超阈值，**无 P0 级超阈值**（三项全超或任一项超 2 倍均未发生），**无需申请豁免**。其中仅「新增 TODO 数」为工具可复算的实测项，其余两项明确标注「未实测」而非以推测充数。

---

## 5. 可观测性合规检查（参考 `observability-standards`）

| 检查点 | 结论 | 依据 |
|--------|:----:|------|
| 关键失败路径可定位（错误上下文/追踪信息完整） | **通过** | 策略关闭后**仍注入 `X-Request-Id`**（`tests/test_rag_proxy_identity_policy.py:100-106` 锁定「串联契约不可回退」）；网关实测响应头 `X-Request-Id = req-2ebfcfc04552` 与 OpenRAG 应用日志三行（`request_started` / `api_key_authed` / `request_completed(status_code=200)`）`request_id` **完全一致**（`def005-gateway-retest-20260920.json` §collections.openrag_log_hits）。 |
| 溯源标识（`X-Proxy-Source`）未被策略关闭波及 | **通过** | 关闭时以 `user_ctx=None` 走**同一装配点**，`X-Proxy-Source = openbase-rag-proxy` 仍产出（单测断言 `HEADER_PROXY_SOURCE == PROXY_SOURCE_RAG`）。 |
| 非 2xx 可排障性（错误 envelope 完整） | **通过（并纠错 1 项）** | 网关 4xx 实测 **190 字节完整 envelope**（`PARAM_400` + `detail` + `request_id`）；上游 400 实测 **385 字节完整 envelope**。原「400 响应体为空」经原始 socket + httpx 双口径复核判定为 **PS 5.1 测量假阳性**并已撤回（CR-147-005，证据文档升 v1.1.0）。 |
| 日志级别规范（DEBUG/INFO/WARN/ERROR）与本轮改动一致性 | **通过** | 本轮未新增日志调用（仅策略选择），未引入 `print`、未新增降级静默路径；关闭策略属**显式声明**（编排器注释 + 护栏用例），非静默降级。 |
| 敏感信息不落日志 | **通过** | 新增开关为布尔值；未记录令牌/密钥/完整请求体（`AGENTS.md` §3）。 |
| 拒绝路径结构化日志（可观测性余项） | **未闭环（跨仓，非本仓）** | OpenRAG `request_completed` 仅记 `status_code`、未记拒绝原因 → 已登记为跨仓/设计议题 **CR-147-006**（建议人工确认后入候选需求池 + 跨仓派单），**不阻塞本仓 Step 3**。 |

---

## 6. 编码约定审查（依据仓库根 `AGENTS.md`）

| 约定项（AGENTS.md 条款） | 结论 | 证据 |
|--------------------------|:----:|------|
| §1 分层架构：Controller 只做校验+调 Service、禁止跨层、禁止路由拼 SQL | **合规** | 本轮改动不涉及路由层业务逻辑；`rag_proxy/__init__.py` 的 `_build_upstream_headers` 为**出站头装配单点**（既有分层落点），策略判断在模块内完成，未跨层调用；无 SQL 变更。 |
| §2 错误码规范：`{code, message, detail, request_id}` + 前缀 AUTH/PERM/PARAM/BIZ/SYS/STORAGE | **合规** | 本轮**未新增错误码**；实测 4xx envelope 字段完整且前缀为 `PARAM_400`（网关侧参数校验），结构符合 §2；上游 `BIZ_RESERVED_TENANT_CODE_COLLISION` 属 OpenRAG 侧透传（既有约定：上游错误码不映射为 OpenBase 错误码表）。 |
| §3 日志规范：结构化日志、禁止 `print`、不记录敏感信息 | **合规** | 本轮未新增日志语句；9 个文件全文检索无 `print` 新增（变更面为配置/策略/测试）；敏感数据未落盘。 |
| §4 命名约定：模块 snake_case / 类 PascalCase / 常量 UPPER_SNAKE_CASE、禁止无意义缩写 | **合规** | `rag_inject_identity_headers`（snake_case 字段）、`OPENBASE_RAG_INJECT_IDENTITY_HEADERS`（UPPER_SNAKE_CASE 环境变量）、`StubRequest` / `_user_ctx` / `_set_policy`（测试内 PascalCase 类 + 描述性函数名）均符合；无单字母变量。 |
| §5 数据库操作：参数化查询、禁 `SELECT *`、迁移幂等、多租户过滤 | **不适用** | 本轮无 DB 访问与迁移变更。 |
| §6 并发与安全：共享可变状态加锁、关键操作幂等、输入校验、敏感数据不落 git | **合规（有限适用面）** | `settings` 单例读取为**只读**消费，无共享可变状态写入（测试中的属性注入经 `monkeypatch` 自动回滚）；新增开关为**声明式配置**、幂等；无输入面扩展（无新增外部输入）。 |
| §7 测试规则：TDD 先 RED 后 GREEN、覆盖率 ≥90%、命令 `pytest`/`ruff` | **合规** | 增量 2 按 TDD 执行：先 RED（**3 failed**，报错 `Settings object has no field "rag_inject_identity_headers"`）→ 实现 → GREEN（**3 passed**）；护栏用例 1 例同步 RED→GREEN。新增/受影响用例 **41 passed**，全量回归 **996 passed / 0 failed**（`logs/v147-def005-regression.txt` L63–L65）。逐模块覆盖率本轮**未单独实测**（未运行 `--cov`）。 |
| §8 验证命令（ruff 0 错误 / pytest 全通过 / 覆盖率 ≥90%） | **部分满足** | `ruff` 0 错误 ✅；`pytest` 全通过 ✅（996/0/4 skip）；覆盖率 ≥90% **本轮未实测**（未运行 `pytest --cov=openbase`）→ 见 §7 未实测项。 |

---

## 7. 检查结论

**结论：通过（允许进入 `code-logic-review`）**

| 项 | 结论 |
|----|------|
| 十二类检查 | 实测 9 项**全部通过**；不适用 3 项（#3 类型检查无工具、#4 构建无步骤、#11 无数据字段），均给出原因 |
| 补充门禁（复杂度/重复率/架构合规） | 架构合规合规；复杂度与重复率**未超阈值但标注未实测**（无工具 + 环境受限） |
| 技术债务增长率 | 新增 TODO **0**（实测，含 1 处伪阳性剔除留痕）；高复杂度函数 **0**、重复率增量 **0**（未实测，变更面核定）——三项均远低于阈值（≤5 / ≤3 / ≤2%） |
| 可观测性合规 | 通过（1 项跨仓余项已登记 CR-147-006） |
| 编码约定审查（AGENTS.md） | 合规（DB 项不适用；覆盖率项未实测） |
| 失败项 | **0 项**，无 P0/P1 静态质量问题待修 |
| **是否允许进入 `code-logic-review`** | **是** |

**如实登记的未实测项（不以后续推测替代）**：

| # | 未实测内容 | 原因 | 处置 |
|:-:|-----------|------|------|
| 1 | 类型检查（`mypy` / `pyright`） | 项目未配置类型检查器 | 记为「不适用」；如需引入须走工具链变更评审 |
| 2 | 圈复杂度工具扫描（`radon cc` / `lizard`） | 项目未配置；本轮环境受限（本机有长任务在跑，禁止启停服务/运行 pytest） | 以变更面核定 0；建议后续版本把 `radon cc` 纳入脚本化回归 |
| 3 | 重复率工具扫描（`jscpd` / `pylint --duplicate-code`） | 同上 | 同上 |
| 4 | PowerShell 脚本单独语法解析 | 本轮未执行 PS 解析命令 | 行为由实跑证据间接覆盖（namecheck / L2 / L3） |
| 5 | 逐模块覆盖率（`pytest --cov=openbase`，AGENTS.md §7 ≥90%） | 本轮未执行覆盖率命令 | 记为未实测；测试阶段（Step 4）建议全量 `--cov` 补齐 |

---

## 8. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-20 | AD-OpenBase-Dev | 初始创建：v1.4.7 Step 3 静态质量门禁记录（**补齐本版本此前缺失的门禁材料**）。含检查范围与依据（9 个变更文件 + 工具链实测）、12 类检查项逐项结论（实测 9 / 不适用 3 / 失败 0）、圈复杂度与重复率与架构合规补充门禁（明确标注「未实测工具扫描」）、技术债务增长率检查（新增 TODO 实测 0，含 1 处伪阳性剔除留痕；阈值 ≤5/≤3/≤2%）、可观测性合规检查（1 项跨仓余项 CR-147-006）、编码约定审查（引用 `AGENTS.md` §1~§8）、结论「通过（允许进入 code-logic-review）」与 5 项未实测留痕 |
