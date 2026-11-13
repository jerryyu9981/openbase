# OpenBase users 模块补测方案（v1.0.0）

| 项目 | 内容 |
|---|---|
| 文档名称 | OpenBase users 模块补测方案 |
| 版本 | v1.0.0 |
| 状态 | [Review]（待人工审批后执行） |
| 文档类型 | 测试阶段专项补测方案（`doc/test`，归属 Step 4 测试阶段） |
| 编写角色 | 测试负责人 |
| 适用环境 | 开发环境（Dev）/ 测试环境（Test）通用 |
| 编写日期 | 2026-11-13 |
| 关联文档 | 批次 5 tasks.md v1.3.2（覆盖率门禁记录）、AGENTS.md（验证命令与覆盖率门禁） |
| 代码基线 | `openbase/modules/users/__init__.py`（`__version__ = 1.0.0`，152 条语句） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
| v1.0.0 | 2026-11-13 | 测试负责人 | 首次编制：覆盖率口径诊断、缺口清单（21 行）、18 条补测用例与验收标准 |

---

## 1. 背景与目标

### 1.1 背景

批次 5 全量覆盖率门禁（2026-11-13）结果为全局 `TOTAL 87%`，低于项目要求的 90%。缺口集中在历史模块，其中 users 模块为**最低覆盖模块之一**（58%，152 语句 / 64 未覆盖），是达成全局 90% 门禁的首要治理对象。

### 1.2 目标

1. 将 `openbase/modules/users/__init__.py` 的**语句覆盖率提升至 ≥90%**（目标值 ≥97%）。
2. 补齐 users 全生命周期（创建 / 列表 / 详情 / 启停 / 角色分配 / 软删除）的**异常分支与边界契约**，而非仅追指标。
3. 修正覆盖率采集口径缺陷（见 §2），使后续所有模块的覆盖率数据可信。
4. 保证全量回归零失败、`ruff check openbase tests` 零告警。

### 1.3 非目标

- 不改动 users 模块业务逻辑（本次为纯补测；如补测发现缺陷，按缺陷流程单独立项修复）。
- 不改动前端 users 相关页面与 API 封装（不属于本方案范围）。
- 不治理其他低覆盖模块（users 之外的调度/组织/存储/租户模块另行立项）。

---

## 2. 覆盖率口径诊断（P0 前置）

### 2.1 现象

| 测量方式 | 结果 | 说明 |
|---|---|---|
| 全量 `pytest tests --cov=openbase` | users **58%**（152 / 64 未覆盖） | 2026-11-13 全量门禁实测 |
| 单跑 `tests/test_users_admin.py --cov=openbase` | users **54%**（70 未覆盖） | 7 条 CRUD 用例全部通过，但 handler 主体被判定未覆盖 |
| 单跑 `tests/test_users_admin.py --cov=openbase.modules.users` | 报错 `TypeError: 'InternalTraversal' object is not callable` | 默认 ctrace 与 SQLAlchemy C 扩展在该组合下异常 |
| 单用例 `test_user_crud_flow` + `concurrency=greenlet,thread` | users **86%**（21 未覆盖） | 同等代码路径，缺失行收敛为 21 行 |

### 2.2 根因

FastAPI 异步 handler 经 `TestClient`（anyio portal + SQLAlchemy 异步引擎内部 greenlet 栈切换）执行。coverage.py 默认按线程采集（ctrace），**greenlet 栈切换后的事件丢失**，表现为：`await` 之前语句计入覆盖、`await` 之后的主体语句（如 `create_user` 的建号/落库、`list_users` 的过滤循环）被误判为未覆盖。因此当前 users 的 58% **系统性低估**，直接据此补测会产生大量冗余用例。

### 2.3 前置动作（P0，必须先做）

1. 在 `pyproject.toml` 增加统一覆盖率口径配置：

```toml
[tool.coverage.run]
concurrency = ["greenlet", "thread"]
branch = true
```

2. 以修正后口径重测 users 基线（单模块定向 + 全量各一次），把「真实缺口行」固定为本方案的补测输入。
3. 修正后全量覆盖率数字会变化，须单独提交并全量回归，避免与历史数字混用。

> 本方案 §3 的缺口清单已按修正口径（greenlet）实测得出，可直接作为补测输入。

---

## 3. 缺口清单（修正口径实测）

基线：单用例 `test_user_crud_flow` + `concurrency=greenlet,thread` → 覆盖率 86%，未覆盖 21 行。

| 序号 | 代码位置 | 函数 | 未覆盖分支 | 性质 |
|---|---|---|---|---|
| G1 | `users/__init__.py:140` | `_resolve_role` | 角色码不在受控枚举 → `PARAM_INVALID` 400 | 参数契约 |
| G2 | `users/__init__.py:142-145` | `_resolve_role` | 角色码合法但库中不存在 → `BIZ_NOT_FOUND` 404 | 数据异常 |
| G3 | `users/__init__.py:159-160` | `create_user` | 用户名重复 → `BIZ_CONFLICT` 409 | 幂等/冲突 |
| G4 | `users/__init__.py:198-199` | `list_users` | `tenant_filter_code == ""` → 返回空列表 | 租户隔离 |
| G5 | `users/__init__.py:201-203` | `list_users` | 非超管按 `tenant_code` 过滤 | 租户隔离 |
| G6 | `users/__init__.py:220-221` | `get_user` | 用户不存在 → 404 | 查询契约 |
| G7 | `users/__init__.py:235-236` | `update_user` | 用户不存在 → 404 | 更新契约 |
| G8 | `users/__init__.py:241-245` | `update_user` | `status` 写路径的状态机迁移（合法迁移 / `deactivated` 终态非法 400） | 状态机 |
| G9 | `users/__init__.py:247-251` | `update_user` | `display_name` / `email` / `phone` 部分更新 | 字段更新 |
| G10 | `users/__init__.py:256-259` | `update_user` | 启停后 `invalidate_principal_cache` 缓存失效 | 安全/一致性 |
| G11 | `users/__init__.py:271-284` | `delete_user` | 软删除全流程（`status=0` + `status_state→suspended` + 缓存失效 + 响应体） | 生命周期 |
| G12 | `users/__init__.py:296-304` | `assign_role` | 用户不存在 404；成功替换旧角色关联 | 角色管理 |

补充（不新增 users 行覆盖，但属契约完整性）：参数校验 422（`username` 字符集/长度、`password` < 6、`status` ∉ {0,1}）、未认证 401、响应不回显 `password_hash`。

---

## 4. 补测用例设计

新增用例统一写入 `tests/test_users_admin.py`（复用其模块级 SQLite 隔离 fixture，避免跨文件 DB 串扰），编号规则 `UT-USERS-xx`。

### 4.1 P0：功能分支缺口（对应 G1–G12）

| 编号 | 覆盖缺口 | 用例名称 | 前置/步骤 | 预期结果 |
|---|---|---|---|---|
| UT-USERS-01 | G1 | 创建用户-非法角色码 | admin 调 `POST /api/v1/users`，`role="superuser"` | 400，错误码 `PARAM_INVALID`，消息含 `invalid role` |
| UT-USERS-02 | G2 | 创建用户-角色未播种 | 删除（或屏蔽）`viewer` 角色行后创建 `role="viewer"` 的用户 | 404，错误码 `BIZ_NOT_FOUND`；用例结束恢复角色行 |
| UT-USERS-03 | G3 | 创建用户-用户名重复 | 连续两次创建同名用户 | 第二次 409，`BIZ_CONFLICT`，消息含 `username already exists` |
| UT-USERS-04 | G4 | 列表-无租户域非超管 | 构造无 `tenant_code` 的非超管（`org_member`）登录后 `GET /api/v1/users` | 200 且返回 `[]`（不泄露跨租户数据） |
| UT-USERS-05 | G5 | 列表-租户过滤 | 租户 A/B 各建用户，租户 A 管理员查列表 | 仅返回租户 A 用户；超管可见全部 |
| UT-USERS-06 | G6 | 详情-用户不存在 | `GET /api/v1/users/999999` | 404，`BIZ_NOT_FOUND` |
| UT-USERS-07 | G7 | 更新-用户不存在 | `PUT /api/v1/users/999999` `{"display_name":"x"}` | 404，`BIZ_NOT_FOUND` |
| UT-USERS-08 | G8 | 启停-合法状态迁移 | 用户先 `status=0`（suspended）再 `status=1` | 200；详情 `status=1`、`status_state=active` |
| UT-USERS-09 | G8 | 启停-终态不可复活 | 直接置该用户 `status_state='deactivated'` 后 `PUT status=1` | 400（非法迁移），状态保持 `deactivated` |
| UT-USERS-10 | G9 | 更新-基础字段部分更新 | `PUT` 仅传 `display_name`/`email`/`phone` 之一及组合 | 200 且仅目标字段变化，其余保持原值 |
| UT-USERS-11 | G10 | 启停-缓存失效 | `monkeypatch` 打桩 `openbase.modules.identity.verification.invalidate_principal_cache`，执行 `PUT status=0` | 断言被调用 1 次，参数含 `(user_id, username)` |
| UT-USERS-12 | G11 | 软删除-全流程 | `DELETE /api/v1/users/{id}` | 200 且体 `{code:0, user_id, status:0}`；详情 `status=0`、`status_state=suspended`；列表仍可见该行（数据保留） |
| UT-USERS-13 | G11 | 软删除-不存在 | `DELETE /api/v1/users/999999` | 404，`BIZ_NOT_FOUND` |
| UT-USERS-14 | G11 | 软删除-已 suspended 保持 | 先 `PUT status=0` 再 `DELETE` | 200；`status_state` 保持 `suspended`（不被改写/复活） |
| UT-USERS-15 | G12 | 角色分配-不存在用户 | `PUT /api/v1/users/999999/role` `{"role":"admin"}` | 404，`BIZ_NOT_FOUND` |
| UT-USERS-16 | G12 | 角色分配-替换旧角色 | 用户先为 `viewer`，再分配 `org_admin` | 200；`roles == ["org_admin"]`（旧 `viewer` 已移除） |

### 4.2 P1：契约与安全边界（不新增行覆盖，防回归）

| 编号 | 用例名称 | 断言要点 |
|---|---|---|
| UT-USERS-17 | 创建参数校验 422 | `username` 含非法字符/长度越界、`password` < 6、`status=2` 均返回 422 |
| UT-USERS-18 | 未认证 401 全覆盖 | `POST/GET/PUT/DELETE` 五个端点无 Token 均返回 401 |
| UT-USERS-19 | 越权 403 全覆盖 | `viewer` 对 `DELETE`/`PUT /role`/`PUT` 均返回 403 |
| UT-USERS-20 | 响应脱敏 | 全部响应体不含 `password_hash`；新建用户 `roles` 与入参一致 |

### 4.3 优先级与预计收益

| 优先级 | 用例 | 预计新增覆盖行 | 说明 |
|---|---|---|---|
| P0 | UT-USERS-01 ~ 16 | 21 行全量覆盖 | 直接消除 §3 缺口 |
| P1 | UT-USERS-17 ~ 20 | 0 行（契约保护） | 防止后续改动回归，满足安全验收 |
| — | 口径修正（§2.3） | 使既有覆盖真实呈现 | 可能使 users 基线从 58% 升至 80%+，需先测后补 |

**目标**：users 语句覆盖率 ≥90%（预期 ≥97%）；分支覆盖率（`branch=true` 后）≥85%。

---

## 5. 执行步骤与命令

### 5.1 步骤

1. **P0 口径修正**：`pyproject.toml` 增加 `[tool.coverage.run] concurrency/branch`（§2.3），提交后重测基线。
2. **补测实现（TDD）**：按 §4 先写用例（RED），确认失败原因与缺口一致；如用例直接通过，则说明该分支已被其他测试覆盖，标记为「对齐型用例」并保留断言。
3. **定向验证**：`tests/test_users_admin.py` 全绿 + users 模块覆盖率达标。
4. **全量回归**：全量 pytest（含覆盖率）+ ruff，确认零失败、全局覆盖率变化已在文档留痕。
5. **留痕**：测试报告/测试用例文档按 `project-document-management` 规范升版并记录修订历史。

### 5.2 命令

```bash
# 1) 定向补测 + users 单模块覆盖率（修正口径后）
python -m pytest tests/test_users_admin.py \
  --cov=openbase.modules.users --cov-report=term-missing -q

# 2) 全量回归 + 全局覆盖率（口径修正后需重新取基线）
python -m pytest tests -q \
  --cov=openbase --cov-report=term-missing \
  --junitxml=reports/pytest-users-backfill.xml

# 3) 静态检查
python -m ruff check openbase tests
```

> 注：本机 `D:\venvs\openbase` 已安装 pytest-cov 7.1.0 + coverage 7.17.3；后端全量单轮约 55–75 分钟，建议后台执行并保留 JUnit 报告。

---

## 6. 验收标准

| 维度 | 通过标准 | 验证方式 |
|---|---|---|
| 覆盖率 | users 语句覆盖率 ≥90%，且 §3 缺口 G1–G12 全部命中 | `--cov-report=term-missing` 输出中 21 行归零 |
| 用例 | UT-USERS-01 ~ 20 全部通过 | 定向 pytest 输出 `20 passed` |
| 回归 | 后端全量 0 失败 0 错误（跳过项须说明原因） | JUnit 报告 `failures=0 errors=0` |
| 静态质量 | `ruff check openbase tests` 0 错误 | 命令输出 `All checks passed` |
| 安全 | 401/403/422 契约与响应脱敏用例通过 | P1 用例断言 |
| 文档 | 本方案状态置 `[Final]`，修订历史记录执行结果 | 文档留痕 |

---

## 7. 风险与依赖

| 风险 | 影响 | 应对 |
|---|---|---|
| 覆盖率达标但用例冗余 | 维护成本上升 | 先做 §2.3 口径修正再补测，只补真实缺口 |
| `concurrency=greenlet` 影响全量覆盖率数字 | 与历史 87% 不可直接比较 | 单独提交配置变更，重取全量基线并在文档标注口径 |
| `test_users_admin.py` 模块级 DB 隔离依赖全局工厂 patch | 与全量并发顺序耦合，可能 flaky | 新用例并入同一 fixture；必要时改为独立子库 + 事务回滚 |
| 删除角色种子（UT-USERS-02）污染后续用例 | 后续创建失败 | 用例内 `try/finally` 恢复角色行，或使用独立库文件 |
| coverage ctrace + SQLAlchemy C 扩展异常（`InternalTraversal`） | 单文件测量失败 | 统一使用 `--cov=openbase` 或修正 concurrency；异常时回归验证 |
| 状态机 `deactivated` 造数需直接写库 | 与业务写路径不一致 | 明确标注为「测试专用造数」，并加注释说明来源设计草案 §4.3 |

## 8. 依赖与影响文件清单（计划）

| 文件 | 变更性质 | 说明 |
|---|---|---|
| `pyproject.toml` | 修改 | 增加 `[tool.coverage.run] concurrency/branch` |
| `tests/test_users_admin.py` | 修改（新增用例） | UT-USERS-01 ~ 20 |
| `doc/test/OpenBase-users模块补测方案-v1.0.0.md` | 新增 | 本方案 |
| `doc/test/OpenBase-测试报告-v*.md` | 按规范升版 | 回填补测执行结果与覆盖率结论 |

## 9. 附录：证据摘要

- 全量覆盖率（2026-11-13）：`TOTAL 87%`，`openbase/modules/users/__init__.py 152 64 58%`。
- 定向（默认口径，7 用例全通过）：`users 152 70 54%`，缺失 `98, 109, 134, 140, 142-145, 159-177, 182-186, 198-209, 220-223, 235-236, 241-245, 248-259, 261, 271-284, 296-304`。
- 定向（`concurrency=greenlet,thread`，单用例）：`users 152 21 86%`，缺失 `140, 144, 160, 199, 202, 221, 236, 247, 249, 251, 271-284, 297`。
- 两口径差异印证 §2.2 的 greenlet 采集缺陷；本方案缺口以修正口径为准。
