# OpenBase 开发记录报告（DevLogReport） - v1.4.12

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座）／落点仓 **本仓**（`openbase` 后端 ＋ `openbase-ui` 前端） |
| 版本号 | **v1.4.12**（缺陷修复：服务 Key 身份判定回归 D-03） |
| 文档 | 开发记录报告（Step 3 产出，增量修复型） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]**（待人工批准） |
| 日期 | 2026-10-24 |
| 编制 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-长尾迭代收口审计-v1.12.0》§4.2 两项放行前置复跑；《OpenBase-自研系统多租户与授权集成总体完善方案-v1.0.0》§3.7 例 3 / §5.2 D-V6（服务账号主体映射与匿名服务 Key 写门禁） |
| 触发方式 | 放行前置复跑（非新需求）：`test_obk_service_account_mapped_outbound_headers`、`test_verdict_k03::test_t2_6_unregistered_service_key_write_403` |

## 修订历史

| 版本 | 日期 | 编制人 | 修订内容 |
|------|------|--------|---------|
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

## 2. 验证

| 项 | 命令 | 结果 |
|---|---|---|
| 静态检查 | `ruff check openbase/core/deps/auth.py openbase/modules/proxy/__init__.py tests/test_service_agent_outbound.py` | 0 错误 |
| 定向回归 | `pytest tests/test_service_agent_outbound.py tests/test_api_keys.py tests/test_verdict_k03.py` | **47 passed** |
| 全量（除 S7 门禁自检） | `pytest tests --ignore=tests/test_s7_t6_gate.py` | **1295 passed / 4 skipped / 6 failed** |
| 6 例失败隔离复跑 | `pytest tests/test_tenant_admin.py tests/test_users_admin.py` | **12 passed**（共享 PG 瞬态，非回归） |
| S7 门禁自检 | `pytest tests/test_s7_t6_gate.py` | **16 passed**（129s） |

有效基线：**1311 passed / 4 skipped / 0 功能失败**；6 例失败全部为 `asyncpg connection was closed in the middle of operation` / `TimeoutError`，隔离复跑通过。

## 3. 影响面与回滚

- **影响面**：仅 `/proxy` 通道的服务 Key 出站身份头与 K03 写门禁判定；JWT 通道零变化（`get_current_user` 本就返回 `auth_method="jwt"`）。
- **行为变化**（符合既定设计，非新增能力）：
  1. 已登记映射的服务 Key → 出站 `X-User-ID` 为映射主体（此前误发 Key 记录 id）；
  2. 未登记映射的服务 Key 业务写 → `403 PERM_SERVICE_KEY_WRITE_DENIED`（此前误放行转发）；
  3. 未登记映射的服务 Key 读 → 仍仅来源标注，不构造伪主体头（不变）。
- **回滚**：本修复为纯代码回退（无数据结构变更），回退 `openbase/core/deps/auth.py` + `openbase/modules/proxy/__init__.py` 两文件即可；回退后上述两用例将重新红灯。

## 4. 遗留

1. `require_api_key` 返回的凭据 dict 仍含 `key_hash`（存储内部字段），建议后续收窄为显式白名单字段（本次不动，避免扩大改动面）；
2. 生产发布需在 v1.4.12 镜像上回归 `/proxy` 服务 Key 链路（真实环境验证归 OPS）。
