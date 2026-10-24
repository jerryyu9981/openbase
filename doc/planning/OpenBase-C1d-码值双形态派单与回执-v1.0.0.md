# OpenBase C1-d 码值双形态派单与回执 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）跨仓治理 |
| 文档版本 | v1.0.0 |
| 状态 | **[Approved]**（已按派单执行并回执） |
| 派单编号 | XR-GOV-01 / C1-d |
| 发出方 | OpenBase（统一前端 / 平台域） |
| 接收方 | OpenLLM、OpenRAG、OpenMemory |
| 创建日期 | 2026-10-24 |
| 上游依据 | 《OpenBase-长尾事项产品裁定-v1.0.0》§XR-GOV-01；《OpenBase-剩余事项统一清查与小版本迭代计划-v1.0.0》v1.12.0 D 批 |
| 能力源 | `openbase/core/code_normalize.py`（纯函数 + 11 例，禁止跨仓包依赖） |

---

## 1. 能力契约（三仓同源）

三仓各自**复制**同一份零依赖纯函数（标准库 `re`/`uuid`），实现「码 ↔ UUID」双形态解析：

| 函数 | 语义 |
|------|------|
| `is_uuid_like(value)` | 正则判定 UUID 形态；空值/非 UUID → `False` |
| `pick_lookup_column(value)` | UUID 形态 → `id`；其余 → `code` |
| `canonical_uuid(value)` | UUID → 标准小写连字符形式；非 UUID → `None` |
| `normalize_code_or_id(value, resolver)` | 按形态选列查询并回填 canonical UUID；`resolver` 未命中 → `None`（fail-closed） |

**禁则**：不得以 Python 包方式依赖 OpenBase；三份副本以 OpenBase 为语义源，后续变更须同步。

---

## 2. 分仓派单

| 仓 | 接入点 | 交付要求 | 状态 |
|----|--------|----------|------|
| OpenLLM | `GET /api/v1/tenants/{tenant_id}` | 路径参数接受租户码或 UUID；UUID 形态规范化后按主键查询；不存在 → 404 | ✅ 已回执 |
| OpenRAG | `identity/tenant_registry.resolve_tenant_code`（单一校验入口） | UUID 形态规范化后进入保留码/登记集合判定；未登记 → `unknown`（fail-closed） | ✅ 已回执 |
| OpenMemory | `identity/inbound_gate`（`identity_scope` / `trusted_tenant_code` 单一域解析入口） | UUID 形态统一 canonical 小写；码形态去空白透传；D8 默认兜底不变 | ✅ 已回执 |

**共性验收**：纯函数单测（码→UUID / UUID 规范化 / 未命中 fail-closed）＋ 接入点单测 ＋ 既有相关用例回归。

---

## 3. 回执

### 3.1 OpenLLM

| 项 | 内容 |
|----|------|
| 副本模块 | `backend/app/identity/code_normalize.py` |
| 接入点 | `backend/app/api/tenants.py`：新增 `_find_tenant(db, identifier)`；`GET /tenants/{tenant_id}` 参数类型 `UUID → str`，先解析后鉴权（统一用库内 UUID 比较） |
| 行为 | 租户码 → UUID 解析；大写/带空白的 UUID → canonical 后命中；未登记码值 → 404 `租户不存在` |
| 测试 | `backend/tests/unit/test_r13_code_normalize_v1120.py` **7 passed**；`backend/tests/unit/test_tenants_api.py` **38 passed**（含新增 3 例：按码命中 / 大写 UUID / 未知码 404） |
| 提交 | `de4c7e5` |

**边界**：仅读明细路径支持双形态；`PUT /tenants/{id}`、`/quota`、`/teams` 等写路径保持 UUID-only，避免写面语义扩大。

### 3.2 OpenRAG

| 项 | 内容 |
|----|------|
| 副本模块 | `src/openrag/identity/code_normalize.py` |
| 接入点 | `src/openrag/identity/tenant_registry.py::resolve_tenant_code`：UUID 形态先 `canonical_uuid` 再进入四态裁定 |
| 行为 | 登记集合含 UUID 别名（含大写入参）→ `registered` 且回填小写；未登记 UUID → `unknown`；保留码 `default`/`openrag-local` 仍 `reserved`；租户码行为不变 |
| 测试 | `tests/unit/test_r13_code_normalize.py` **10 passed**；`tests/unit/test_c1b_tenant_registry.py` **21 passed**；`test_c4_production_gate.py` + `test_cross_repo_tenant_isolation_fix.py` **17 passed** |
| 提交 | `d5ea6a8` |

### 3.3 OpenMemory

| 项 | 内容 |
|----|------|
| 副本模块 | `src/openmemory/identity/code_normalize.py` |
| 接入点 | `src/openmemory/identity/inbound_gate.py`：新增单一入口 `normalize_tenant_code`，`identity_scope` / `trusted_tenant_code` 统一调用 |
| 行为 | UUID 形态（含大写/空白）→ canonical 小写；码形态去空白透传；空值 → D8 既有 `default` 兜底（不翻转默认） |
| 测试 | `tests/unit/test_r13_code_normalize.py` **12 passed**；`tests/unit/test_default_tenant_fallback_d8.py` **7 passed**；`tests/unit/test_s2_t9_audit_identity.py` **16 passed** |
| 提交 | `9920e70` |

---

## 4. 未闭环项与解冻条件

| # | 事项 | 现状 | 解冻条件 |
|:-:|------|------|----------|
| 1 | OpenRAG 码 → UUID（真实主键） | 本仓无租户主数据，登记集合仅承载「码或 UUID 别名」；当前实现为 UUID 形态规范化 + 未登记 fail-closed | OpenBase 租户主数据实时对账或本地缓存接入（`tenant_registry` 已预留替换点） |
| 2 | OpenMemory 码 → UUID（真实主键） | 同上：`tenant_code` 为自由域键，无 UUID 映射表 | 引入租户主数据/注册表后，由 `normalize_tenant_code` 注入 resolver |
| 3 | 三仓副本同步 | 按裁定禁止跨仓包依赖，存在三份副本 | 任一副本语义变更时，以 OpenBase `code_normalize.py` 为源同步并各自回归 |

---

## 5. 验证命令

| 仓 | 命令 | 运行环境 |
|----|------|----------|
| OpenLLM | `python -S -B doc/tmp/run_openllm_pytest.py tests/unit/test_r13_code_normalize_v1120.py -q --confcutdir=tests/unit` 与 `... tests/unit/test_tenants_api.py` | pgAdmin CPython 3.13（`-S` 规避本机 site 初始化挂起）+ `DATABASE_URL=sqlite:///:memory:` |
| OpenRAG | `python doc/tmp/run_openrag_pytest.py tests/unit/test_r13_code_normalize.py tests/unit/test_c1b_tenant_registry.py -q --no-cov` | OpenRAG `.venv3`（CPython 3.11.9） |
| OpenMemory | `python doc/tmp/run_openmemory_pytest.py tests/unit/test_r13_code_normalize.py tests/unit/test_default_tenant_fallback_d8.py -q --no-cov` | OpenRAG `.venv3`（CPython 3.11.9） |

---

## 6. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-10-24 | 研发（AI 辅助） | 初始创建：C1-d 能力契约、三仓派单与回执（OpenLLM 10 例新增 / OpenRAG 10 例新增 / OpenMemory 12 例新增，相关回归全通过），登记 3 项未闭环与解冻条件 |
