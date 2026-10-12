# OpenBase-B4-row_missing收紧-DevLogReport-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-B4-RM-DEVLOG-v1.0.0 |
| 版本 | v1.0.1 |
| 状态 | [Review]（B4 遗留项 row_missing 收紧开发完成：TDD RED→GREEN、ruff 0、全量回归已附（局域网共享 PG）；待人工批准与台账回填登记） |
| 日期 | 2026-10-12 |
| 作者 | AA-OpenBase-Dev（架构视图）/ AT-OpenBase-Dev（测试视图）/ PM-OpenBase-Dev |
| 存放 | doc/development/ |
| 版本主题 | B4 遗留收紧：主体验证「行缺失（无墓碑）」fail-open → 环境门控（生产 fail-closed 401 / 非生产 allow+WARN+留痕 / 显式白名单），对齐 `principal_db_degraded` 口径 |
| 适用范围 | OpenBase 主仓（openbase/settings.py、openbase/modules/identity/verification.py、tests/） |
| 上游依据 | 《OpenBase-自研系统多租户与授权集成总体完善方案》v1.15.0（§7 B4 行：**遗留**：`row_missing` 仍 fail-open（未收紧，另批））；B4 已落地 `principal_db_degraded` 门控口径（settings.py 字段/校验器/属性 + verification.py DB 降级分支） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-12 | AA/AT/PM-OpenBase-Dev | 初始版本：B4 遗留 `row_missing` 环境门控收紧——RED 12 失败 → GREEN 全绿、ruff 0、改动文件清单、留痕与台账登记说明 |
| v1.0.1 | 2026-10-12 | AA/AT/PM-OpenBase-Dev | 补记「局域网共享 PG（`openbase_test`）」下的全量回归结果与 29 项非通过归因（§4），状态行同步 |

---

## 1. 背景与裁定口径

- **遗留登记**：台账 v1.15.0 §7 B4 行「**遗留**：`row_missing` 仍 fail-open（未收紧，另批）」——
  `verify_principal` 在「DB 正常 + 主体行缺失 + 无 purge 墓碑 + 无委托」时无条件放行（WARN 计数），
  该路径覆盖 OIDC 直签 / 降级内存用户形态，生产环境同样放行 → 与 B4 「无法确认主体状态即拒绝」安全口径不一致。
- **收紧口径（对齐 B4 已落地 `principal_db_degraded` 环境门控）**：
  - 显式白名单 `principal_row_missing_allowlist`（十进制主体 id，通配/非数字一律不作为命中）→ 放行 + 留痕，优先于拒绝；
  - 有效策略为 reject（生产默认推导 / 显式 `principal_row_missing_policy=reject`）→ **fail-closed 401 `AUTH_PRINCIPAL_DISABLED`**；
  - 有效策略为 allow（非生产默认推导 / 显式 `policy=allow`）→ 兼容放行，**必 WARN + 审计留痕**（不得静默）；
  - 生产误配 `allow` → Settings 构造（启动）fail-fast 拒绝；非法取值 → 拒绝启动；
  - 委托分支（行缺失 + `on_behalf_of` → 403）与 purge 墓碑分支（→ 401）行为不变，优先级最高。
- 指标拆分（不变式）：`row_missing == row_missing_allowlisted + row_missing_policy_allow + row_missing_denied`。

## 2. TDD（RED → GREEN）

| 阶段 | 证据 |
|------|------|
| RED | `tests/test_b4_security_hardening.py` 新增 ⑧ 组 10 例 + 改造 `test_b4_3`（b4_13~b4_22）+ `tests/test_verdict_k03.py` 改造 `test_t2_2`——运行 **12 failed**（`Settings` 缺 `principal_row_missing_*` 属性 / 新指标计数为 0 / 生产未拒绝），全部为预期缺口 |
| GREEN | 实现落位后重跑 **42 passed**（`tests/test_b4_security_hardening.py` + `tests/test_verdict_k03.py`），含既有 B4 12 例与 K03 全量无回归 |

## 3. 实现内容与改动文件

- `openbase/settings.py`：
  - 新增字段 `principal_row_missing_allowlist: str = ""`、`principal_row_missing_policy: str = ""`（对齐 db_degraded 字段语义注释）；
  - 新增 `@model_validator _validate_principal_row_missing_policy`（取值白名单 + 生产禁 `allow` 启动 fail-fast）；
  - 新增属性 `principal_row_missing_allowlist_set`（仅十进制 id，非法项 WARN 忽略）/ `principal_row_missing_policy_source`（explicit/env 推导）/ `principal_row_missing_reject`。
- `openbase/modules/identity/verification.py`：
  - 模块 docstring 与 `verify_principal` docstring（Returns/Raises）同步收紧语义；
  - `_VERDICT_METRICS` 新增 `row_missing_allowlisted` / `row_missing_policy_allow` / `row_missing_denied`（不变式注释）；
  - 新增 `_row_missing_allowlisted` 助手；
  - `_record_degraded_verify_trace` reason 枚举扩展（row_missing_allowlisted / policy_allow / env_allow）；
  - `snapshot is None` 无墓碑分支：白名单 → 放行留痕；reject → 401 `AUTH_PRINCIPAL_DISABLED`；allow → WARN + 留痕（`request_id`/`policy_source`/`env` 结构化）。
- 测试：`tests/test_b4_security_hardening.py`（⑧ 组 b4_13~b4_22 共 10 例新增 + `test_b4_3` 改造）、`tests/test_verdict_k03.py`（`test_t2_2` 改造 + 指标 fixture 同步）。

## 4. 验证结论

| 项 | 结果 |
|----|------|
| ruff | **0 错误**（`openbase/modules/identity/verification.py` + `openbase/settings.py` + 两测试文件，ruff 0.17.0） |
| 定向测试 | **42 passed**（B4 22 例 + verdict K03 全量）；含 PG 用例（`test_tenant_admin`/`test_users_admin`）的 4 文件隔离批次 **52 passed** |
| 全量回归 | **1183 passed / 19 failed / 10 errors / 4 skipped**（tests=1216；局域网共享 PG `openbase_test`，`OPENBASE_DB_URL` 注入；JUnit XML 计数） |
| 环境性已知 | 上述 29 项非通过**全部为环境/配置/用例隔离固有**（详见 §4.1），与本改动无因果 |

### 4.1 全量回归非通过项归因（29 项，均与本改动无因果）

| 归类 | 数量 | 用例 | 归因 |
|------|------|------|------|
| 沙箱无 `python` PATH + 隔离模式导入 | 10 errors | `test_s7_t6_gate.py`（门禁聚合） | 门禁脚本子进程裸调 `python -m pytest`，本执行环境无 PATH `python` / isolated 模式导入 `openbase` 失败 → exit=2；编写环境（commit `3ae1aea`，2026-09-12）基线证据为 PASS |
| 同上（脚本 `python` 不可识别）+ 缺真实联调证据 | 12 failures | `test_s7_tools_skeleton.py` | `verify_l1_1_cascade.ps1`/`drill_l2_1_failover.ps1`/`verify_l3_1_agent.ps1` 报 `python` 非可识别命令；证据文件属真实联调窗口产物 |
| Py3.13 + SQLAlchemy 2.1.4 子进程兼容 | 2 failures | `test_org_alias_code.py::test_t7_7_*` | 子进程 `import sqlalchemy` 崩溃：`SQLCoreOperations ... directly inherits TypingOnly but has additional attributes {'__firstlineno__','__static_attributes__'}`（既有环境固有，台账既有口径登记） |
| 单进程全量并发下 asyncpg 连接占用 | 4 failures | `test_tenant_admin.py`(2)、`test_users_admin.py`(2) | `asyncpg.InterfaceError: another operation is in progress`；**同文件隔离复跑全绿**（本批 52 passed 已证），属测试隔离/单进程并发固有 |
| 注入 `OPENBASE_DB_URL` 后模块级状态 | 1 failure | `test_demo_app.py::test_demo_app_starts_and_falls_back` | 用例前置为「无库回退」（`_DB_READY is False`），链接局域网 PG 后 `demo_app` 模块级 `_DB_READY` 因导入序置 True，与前置冲突；属环境/用例隔离固有 |

> B4 改动仅触及 `openbase/settings.py` 的 Settings 字段/校验器/属性与 `openbase/modules/identity/verification.py` 的行缺失分支，上述 29 项失败用例均不覆盖该路径（应检 42 例 + 含 PG 用例的 52 例隔离批次全绿）。

## 5. 留痕与入仓

- 台账《OpenBase-自研系统多租户与授权集成总体完善方案》修订历史 **v1.15.0 → v1.16.0（B4 收紧）→ v1.16.1（全量回归补记）** 回写 + 状态行/§7 B4 行更新；
- 本报告随代码同仓提交；提交信息记版本主题；
- 三远程（origin / backup / github）推送，哈希齐平。

## 6. 遗留登记

- 无新增遗留；`row_missing` 收紧后 B4 遗留清零。
