# OpenBase 开发记录报告（DevLogReport） - v1.4.12

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **本仓**（`openbase` 后端 ＋ `openbase-ui` 前端） |
| 版本号 | **v1.4.12**（缺陷修复：服务 Key 身份判定回归 D-03） |
| 文档 | 开发记录报告（Step 3 产出，增量修复型） |
| 文档版本 | v1.1.1 |
| 状态 | **[Review]**（待人工批准） |
| 日期 | 2026-10-24 |
| 编制 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-长尾迭代收口审计-v1.12.0》§4.2 两项放行前置复跑；《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》§3.7 例 3 / §5.2 D-V6（服务账号主体映射与匿名服务 Key 写门禁） |
| 触发方式 | 放行前置复跑（非新需求）：`test_obk_service_account_mapped_outbound_headers`、`test_verdict_k03::test_t2_6_unregistered_service_key_write_403` |

## 修订历史

| 版本 | 日期 | 编制人 | 修订内容 |
|------|------|--------|---------|
| v1.1.1 | 2026-10-24 | 研发（AI 辅助） | 版本载体对齐：`openbase-ui/package-lock.json` 根版本 1.3.0 → 1.4.12（两处），消除与 `package.json` 的矛盾；§1.6 记录；§2 补前端全量 370 passed |
| v1.1.0 | 2026-10-24 | 研发（AI 辅助） | 同版本技术债清理：`ApiKeyStore.verify` / `require_api_key` 凭据面剔除存储内部字段 `key_hash`（TDD 2 例）；§2 增补回归；§4 遗留 1 关闭 |
| v1.0.0 | 2026-10-24 | 研发（AI 辅助） | 首次产出：D-03 根因、修复实现、断言修正、定向与全量回归证据、影响面与回滚 |

---

## 1. 缺陷 D-03：服务 Key 身份判定回归

### 1.1 现象

| 用例 | 期望 | 实际（修复前） |
|------|------|----------------|
| `test_service_agent_outbound.py::test_obk_service_account_mapped_outbound_headers` | 出站 `X-User-ID=5001`（映射主体） | `X-User-ID=<API Key 记录 id 的 uuid>` |
| `test_verdict_k03.py::test_t2_6_unregistered_service_key_write_403` | 未登记服务 Key 业务写 → `403 PERM_SERVICE_KEY_WRITE_DENIED` | 未被识别为服务 Key → 放行转发 → `502 SYS_502` |

### 1.2 根因

1. v1.9.2 为 `ApiKeyStore` 记录新增**稳定标识** `id`（uuid，用于按 id 吊销），`verify()` 直接返回整条记录；
2. `/proxy` 的服务 Key 判别沿用启发式「**无主体 id** 即服务 Key」：
   `_is_service_key_identity(identity) = "scope" in identity and "id" not in identity`；
3. 记录带 `id` 后该判据恒为 `False` ⇒ 服务 Key 被当作 JWT 主体：
   - 出站把 Key 记录 `id` 写进 `X-User-ID`（映射规则完全未生效）；
   - 匿名写门禁（K03 D-V6）不触发，业务写被直接转发。

> 两处红灯此前被归因为「共享 PG 抖动 / 本机未配置映射」，本轮复跑证伪：**同一代码根因**，与 PG、配置无关。

### 1.3 修复

| 文件 | 改动 |
|------|------|
| `openbase/core/deps/auth.py` | `require_api_key` 通过校验后返回 `{**credential, "auth_method": "service-key"}`（认证方式显式标记，取值域与 `identity_context` 一致：`jwt` / `sk-agent` / `service-key` / `trusted-orchestrator`） |
| `openbase/modules/proxy/__init__.py` | `_is_service_key_identity` 改为**标记优先**：`auth_method == "service-key"` → True；保留旧形态兼容（含 `scope` 且无 `id`） |

设计取舍：

- **不使用**「有 `key_hash` 即服务 Key」——该字段是存储内部细节，不应成为跨模块判据；
- **不删除** `id` 字段——按 id 吊销是既定能力（v1.9.2），修复的是判定方式而非数据模型；
- 兼容旧形态仅为测试/调用方显式构造凭据的场景，运行态一律走标记。

### 1.4 断言修正（同批发现的陈旧期望）

`test_obk_service_account_mapped_outbound_headers` 原断言 `X-Proxy-Source == openbase-generic-proxy`，与现行实现不符：`_TARGET_SYSTEM_BY_PROXY` 按**被代理系统**发布来源（`openrag → openbase-rag-proxy`），以便下游 `TRUSTED_PROXY_SOURCES` 采信身份头。已改为 `PROXY_SOURCE_RAG` 并注明依据，同时移除未再使用的 `PROXY_SOURCE_GENERIC` 导入。

### 1.5 同版本技术债清理：凭据面剔除 `key_hash`

**问题**：`ApiKeyStore.verify()` 直接返回存储记录（含 `key_hash`），`require_api_key` 再原样透传给 `/proxy` 身份上下文 —— 服务 Key 的哈希进入凭据面（日志/审计一旦整体序列化即外泄），且调用方持有可写引用可污染存储。

**修复**（`openbase/modules/auth/api_keys.py`）：

- 新增 `_public_record(record)`：剔除 `_INTERNAL_FIELDS = {"key_hash"}` 并返回**浅拷贝**；
- `verify()` 改为返回 `_public_record(record)`（保留 `id` / `name` / `scope` / `created` / `revoked`，按 id 吊销能力不受影响）；
- `list_keys()` 复用同一函数，消除「列表已剔除、校验未剔除」的口径分裂。

**结果**：`require_api_key` 返回 `{id, name, scope, created, revoked, auth_method}`，不含 `key_hash`；TDD 2 例（`test_api_key_store_verify_excludes_key_hash` 含副本语义、`test_require_api_key_credential_excludes_key_hash`）。

### 1.6 版本载体对齐（v1.1.1）

`openbase-ui/package-lock.json` 的根版本仍停留在 **1.3.0**（第 3 行与 `packages[""]` 第 9 行两处），与 `package.json` 的 1.4.12 矛盾——`npm install` 会静默改写并产生无关 diff。已同步为 **1.4.12**。产品版本三处锚点（`pyproject.toml` / `openbase/__init__.py` / `openbase-ui/package.json`）不变。

## 2. 验证

| 项 | 命令 | 结果 |
|---|---|---|
| 静态检查 | `ruff check openbase/core/deps/auth.py openbase/modules/proxy/__init__.py tests/test_service_agent_outbound.py` | 0 错误 |
| 技术债定向（v1.1.0） | `pytest tests/test_api_keys.py tests/test_api_keys_api.py tests/test_service_agent_outbound.py tests/test_verdict_k03.py` | **53 passed**（含新增 2 例） |
| 认证/代理面回归（v1.1.0） | `pytest`（api_keys/auth/proxy/identity/protocol 共 21 文件） | 见 §2.1 |
| 定向回归 | `pytest tests/test_service_agent_outbound.py tests/test_api_keys.py tests/test_verdict_k03.py` | **47 passed** |
| 全量（除 S7 门禁自检） | `pytest tests --ignore=tests/test_s7_t6_gate.py` | **1295 passed / 4 skipped / 6 failed** |
| 6 例失败隔离复跑 | `pytest tests/test_tenant_admin.py tests/test_users_admin.py` | **12 passed**（共享 PG 瞬态，非回归） |
| S7 门禁自检 | `pytest tests/test_s7_t6_gate.py` | **16 passed**（129s） |
| 前端全量（v1.1.1） | `npm run test`（openbase-ui） | **370 passed / 39 files**（140s） |

有效基线：**1311 passed / 4 skipped / 0 功能失败**；6 例失败全部为 `asyncpg connection was closed in the middle of operation` / `TimeoutError`，隔离复跑通过。

### 2.1 认证/代理面回归明细（v1.1.0）

`api_keys` / `auth` / `proxy` / `identity` / `protocol` 共 **21 个文件**：**225 passed / 9 failed**。9 例全部落在**身份面 DB 依赖**（日志 `agent principal verification unavailable: database degraded`、OIDC 绑定回落），与本次 `ApiKeyStore` 凭据收窄无交集；**9 例隔离复跑全部通过**（8.83s）⇒ 共享 PG 瞬态，非回归。

## 3. 影响面与回滚

- **影响面**：仅 `/proxy` 通道的服务 Key 出站身份头与 K03 写门禁判定；JWT 通道零变化（`get_current_user` 本就返回 `auth_method="jwt"`）。
- **行为变化**（符合既定设计，非新增能力）：
  1. 已登记映射的服务 Key → 出站 `X-User-ID` 为映射主体（此前误发 Key 记录 id）；
  2. 未登记映射的服务 Key 业务写 → `403 PERM_SERVICE_KEY_WRITE_DENIED`（此前误放行转发）；
  3. 未登记映射的服务 Key 读 → 仍仅来源标注，不构造伪主体头（不变）。
- **回滚**：本修复为纯代码回退（无数据结构变更），回退 `openbase/core/deps/auth.py` + `openbase/modules/proxy/__init__.py` 两文件即可；回退后上述两用例将重新红灯。

## 4. 遗留

1. ~~`require_api_key` 返回的凭据 dict 仍含 `key_hash`（存储内部字段），建议后续收窄为显式白名单字段~~ → **已闭环（v1.1.0，§1.5）**：`verify` / `list_keys` 统一经 `_public_record` 剔除 `key_hash`，TDD 2 例守门；
2. 生产发布需在 v1.4.12 镜像上回归 `/proxy` 服务 Key 链路（真实环境验证归 OPS）。
