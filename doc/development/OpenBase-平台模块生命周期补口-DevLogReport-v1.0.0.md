# OpenBase-平台模块生命周期补口-DevLogReport-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-PLATFORM-LIFECYCLE-DEVLOG-v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review]（平台三处删除接口补口完成：TDD RED→GREEN、ruff 0、真实 Dev 环境 13 项实测通过；待人工批准） |
| 日期 | 2026-11-07 |
| 作者 | AA-OpenBase-Dev（架构视图）／AT-OpenBase-Dev（测试视图） |
| 存放 | `doc/development/` |
| 版本主题 | 平台模块生命周期补口：字典类型删除、配置键删除、agent 列表与删除 |
| 适用范围 | OpenBase 主仓（`openbase/modules/dict`、`openbase/modules/config`、`openbase/modules/identity`、`tests/test_platform_lifecycle_delete.py`） |
| 上游依据 | 《OpenBase-基础设施子系统全生命周期走查报告-v1.1.0》§7 生命周期缺口登记 GAP-01／GAP-02／GAP-03 |
| 关联文档 | 《OpenBase-API接口设计文档-v1.4.10》、《OpenBase-基础设施子系统全生命周期走查报告-v1.1.0》 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-11-07 | AA／AT-OpenBase-Dev | 初始版本：闭合走查报告 §7 登记的 GAP-01~03，新增 4 个端点（字典类型删除／配置键删除／agent 列表／agent 删除），补 6 项闭环单测并完成真实 Dev 环境实测 |

---

## 1. 缺口来源与判定口径

走查报告 v1.0.0 §7 登记三项**平台模块生命周期缺口**：模块只提供创建／读取／更新，缺少删除能力，导致走查产生的临时数据无法通过 API 清理，且"创建 → … → 删除 → 删除后不可见"链路无法闭合。

| 编号 | 模块 | 原缺口 |
|------|------|--------|
| GAP-01 | 字典 | `/api/v1/dicts` 仅 GET／POST，无**类型**删除接口 |
| GAP-02 | 配置 | `/api/v1/configs/{key}` 无 DELETE，只能改值不能删键 |
| GAP-03 | 身份 Agent | `/api/v1/identity/agents` 仅 POST，无列表／删除接口 |

**通过判据（沿用走查报告 §2.3）**：删除 2xx → 随后详情/列表不可见或状态为已删除 → 涉及下游引用时删除被拒（409）且数据保留 → 重复删除幂等。

**软删口径（对齐既有 `users` 模块）**：agent 采用软删 `status=0` ＋ `status_state=suspended`，同时级联吊销全部有效密钥并清主体缓存；不物理删除，保留审计链。

---

## 2. 新增端点契约（4 个）

| # | 方法 | 路径 | 权限 | 成功响应 | 错误 |
|:-:|------|------|------|----------|------|
| 1 | DELETE | `/api/v1/dicts/{type_code}` | 沿用字典模块既有鉴权 | `{"code": "<type_code>", "deleted": true}` | `404 BIZ_404`（类型不存在）；`409 BIZ_CONFLICT`（存在字典项，`detail={"type_code","item_count"}`） |
| 2 | DELETE | `/api/v1/configs/{key}` | 沿用配置模块既有鉴权 | `{"key": "<key>", "deleted": true, "restored_default": bool}` | `404 BIZ_404`（键不存在）；`409 BIZ_CONFIG_CONFLICT`（仅有代码默认值、无可删覆盖） |
| 3 | GET | `/api/v1/identity/agents` | `identity:view` | `list[AgentOut]`（`page` ≥1、`page_size` 1~100；非超管按 `tenant_code` 隔离） | — |
| 4 | DELETE | `/api/v1/identity/agents/{agent_id}` | `identity:manage` | `{"code": 0, "agent_id": id, "status": 0, "revoked_keys": n}` | `404`（agent 不存在或越租户） |

### 2.1 关键语义

- **字典类型删除**：先校验类型存在（否则 404），再统计字典项（>0 → 409 并回传 `item_count`），删除成功后清 Redis 缓存键。路由注册在 `DELETE /items/{item_id}` **之后**，避免 `items` 被路径变量误吞。DB 不可用时走内存回退，但**业务错误 404／409 不被回退吞掉**（`except BaseError: raise`）。
- **配置键删除**：同时删除 DB `ConfigKV` 行与 `ConfigStore` 中 system／tenant／user 三级的运行时覆盖，回退到环境变量或代码默认值；`restored_default` 标示是否回退到默认值。**版本历史保留**（`ConfigStore._versions`）供审计与回溯。仅有默认值无覆盖时返回 409，避免"删除默认配置"的语义歧义。
- **agent 删除**：`ensure_agent_subject` 做存在性与租户校验；置 `status=0`，`active`／`provisioned` 迁移为 `suspended`；`UPDATE agent_api_key SET status='revoked' WHERE agent_id=? AND status='active'`；提交后调用 `invalidate_principal_cache(row.id, row.username)`。重复调用返回 200 且 `revoked_keys=0`（幂等）。

---

## 3. 代码变更清单

| 文件 | 变更 |
|------|------|
| `openbase/modules/dict/__init__.py` | 新增 `DictService.delete_type`（DB 路径）、`DictService.delete_type_mem`（内存回退）、`DELETE /{type_code}` 路由；导入 `func`、`BaseError`、`ErrorCode`；模块版本 `__version__` 置 `1.1.0` |
| `openbase/modules/config/__init__.py` | `ConfigStore` 新增 `has_runtime`／`has_default`／`clear_runtime`；新增 `DELETE /{key}` 路由 |
| `openbase/modules/identity/__init__.py` | 新增 `AgentOut` schema、`GET /agents`（分页＋租户隔离）、`DELETE /agents/{agent_id}`（软删＋吊销密钥＋清缓存）；导入 `update`、`AgentApiKey`、`User`、`AgentKeyService` 状态常量与 `STATUS_STATE_*` |
| `tests/test_platform_lifecycle_delete.py` | 新增 6 个闭环用例（模块级 SQLite，启用 `auth/tenant/users/audit/config/identity/dict`） |

> 未改动 `dps_proxy` 与 DPS 仓代码；未改动任何既有接口行为（仅新增方法与端点）。

---

## 4. 测试与验证

### 4.1 定向单测（TDD：先写用例，RED 后实现至 GREEN）

命令：`python -m pytest tests/test_platform_lifecycle_delete.py -q` → **6 passed**。

| 用例 | 断言要点 |
|------|----------|
| `test_dict_type_delete_rejected_when_items_exist` | 建类型＋建项后删类型 → 409 且 `detail.item_count == 1`，类型仍存在 |
| `test_dict_type_delete_then_404` | 删类型 200 `deleted:true` → 再查／再删 404 |
| `test_config_delete_override_then_404` | 覆盖值删除后详情 `value` 为 null，再删 404 |
| `test_config_delete_restores_code_default_and_blocks_default_only` | `set_default(key, 42)` → 删覆盖后回 42；仅默认值再删 → 409 |
| `test_agent_list_then_delete_and_revoke_keys` | 创建 agent → 列表 `status=1` → 删除 `revoked_keys>=1` → 列表 `status=0`／`suspended` → **原密钥访问 401** → 重复删除 `revoked_keys==0` |
| `test_agent_delete_missing_returns_404` | 不存在的 agent → 404 |

> 用例首次执行暴露两处测试侧问题并已修正：dict／config 路由需 Bearer token（统一补 `_admin_headers()`）；`AgentCreated.api_key` 为 `AgentKeyOut` 对象，明文取 `body["api_key"]["raw_key"]`。

### 4.2 静态检查

`python -m ruff check openbase tests` → **All checks passed**。

### 4.3 真实 Dev 环境实测（共享 PG `192.168.0.151` ＋ Redis `:6380`，OpenBase `:8000`）

| 步骤 | 结果 |
|------|------|
| 字典：建类型 → 建字典项 | 200／200（item id=8） |
| 字典：存在字典项时删类型 | **409** `BIZ_CONFLICT`，`detail.item_count=1` |
| 字典：删字典项 → 删类型 → 再删 | 200 → 200 `deleted:true` → **404** `BIZ_404` |
| 配置：设值 → 查 → 删 → 再查 → 再删 | 200 → 200（`v1`）→ 200 `deleted:true,restored_default:false` → 200 `value:null` → **404** |
| Agent：创建 → 列表 → 删除 | 200（agent 131）→ 200 列表含该主体 → 200 `{status:0, revoked_keys:1}` |
| Agent：删除后持原密钥访问 | **401** `AUTH_API_KEY_INVALID`（`agent api key revoked`） |
| Agent：重复删除 | 200（幂等，`revoked_keys:0`） |
| 残留清理 | 走查残留 `walkthrough.key`／`wt_dict_type`／`wt_agent_01` 均删除成功（200） |

### 4.4 未覆盖项（如实登记）

- OpenBase **全量单测仍为 PENDING**：受 `tests/test_s7_t6_gate.py`（子进程门禁聚合超 180s）与 `tests/test_cross_repo_auth_gate.py`（递归扫描兄弟仓阻塞）影响，本轮以定向单测＋真实环境实测作为质量门禁，全量终验建议在完整联调机执行。证据见走查报告 v1.1.0 §6。
- 前端页面级交互（字典／配置／agent 管理页的删除按钮）未纳入本轮，本轮仅闭合**后端接口**；前端接入需在下一次前端走查中验证。

---

## 5. 兼容性与风险

| 项 | 说明 |
|----|------|
| 向后兼容 | 仅新增 HTTP 方法与端点，未修改既有请求／响应结构；既有调用方不受影响 |
| 配置删除语义 | 删除仅移除"覆盖值"，不删除代码默认值定义；版本历史保留，可由 `rollback` 回溯 |
| agent 删除不可逆性 | 软删＋吊销密钥为**不可逆**操作（无恢复端点）；生产调用需 `identity:manage` 权限 |
| 租户隔离 | agent 列表与删除均经 `_agent_tenant_scope` 过滤，防止跨租户操作 |
| 缓存一致性 | 字典删类型清 `dict:type:<code>` 缓存；agent 删除清主体验证缓存，避免旧态继续放行 |

---

## 6. 交付清单

| 类别 | 文件 |
|------|------|
| 源码 | `openbase/modules/dict/__init__.py`、`openbase/modules/config/__init__.py`、`openbase/modules/identity/__init__.py` |
| 测试 | `tests/test_platform_lifecycle_delete.py` |
| 文档 | 本报告；《OpenBase-基础设施子系统全生命周期走查报告-v1.1.0》（§6 门禁补记、§7 GAP 闭合与实测证据） |
