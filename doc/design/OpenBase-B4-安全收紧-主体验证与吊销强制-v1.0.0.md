# OpenBase B4 安全收紧 - 主体验证 fail-closed 与吊销强制 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]（待评审）** |
| 主题 | B4 安全收紧：吊销强制 + 主体验证 fail-closed（含显式白名单） |
| 作者 | AA-OpenBase-Dev（安全/身份）／AU-OpenBase-Dev（复核） |
| 创建日期 | 2026-10-08 |
| 上游依据 | `AGENTS.md` §6（并发与安全）；`openbase/modules/identity/verification.py`；`openbase/settings.py`；人工裁定（2026-10-08，**选项 A：fail-closed + 显式白名单**） |
| 存放 | `doc/design/` |

---

## 1. 背景与裁定

本次收紧针对两处「鉴权可能静默失效」的窗口：

1. **吊销（token 版本）默认未强制**：`settings.enforce_token_version` 默认 `False`，
   校验落在 `verification.py` 的版本强校验段；即「过渡 fail-open」——吊销
   （`users.token_version` 递增）默认不生效。
2. **主体验证 DB 不可达时 fail-open（放行）**：`verification.py` 主体验证器在 DB
   不可达且无委托时 WARN 后放行，是当前最大的一处静默失效窗口。

**人工裁定口径（2026-10-08）**：采用 **选项 A —— fail-closed + 显式白名单**。
即 DB 不可达（无法证明主体状态）默认**拒绝**；仅显式白名单内主体可放行且必留痕；
生产环境强制启用吊销（token 版本）强校验，否则拒绝启动。

---

## 2. 变更摘要

| 项 | 变更前 | 变更后 |
|----|--------|--------|
| DB 不可达 + 无委托 + 未命中白名单 | WARN 后**放行**（fail-open） | **拒绝** 503 `SYS_SOURCE_UNAVAILABLE`（fail-closed） |
| DB 不可达 + 命中显式白名单 | （无此通道） | **放行** + 留痕（结构化日志 + 审计标注） |
| DB 不可达 + 带委托 | 403 `PERM_DELEGATION_VERIFY_UNAVAILABLE` | **不变**（fail-closed，优先级最高） |
| DB 正常（active/suspended/行缺失/墓碑） | 见 T3/T6 语义 | **零变化**（active 放行 / 非 active 401 / 行缺失无墓碑仍放行 / 墓碑 401） |
| 生产 + `enforce_token_version=False` | 允许 | **拒绝启动**（fail-fast） |
| 生产 + `enforce_token_version=True` | 允许 | 不变（通过） |
| 非生产 | 默认关 | 不变（可配置） |

---

## 3. 配置项

| 配置（环境变量） | 类型 | 默认 | 说明 |
|------------------|------|------|------|
| `OPENBASE_ENFORCE_TOKEN_VERSION`（`enforce_token_version`） | bool | `false` | token 版本（吊销）强校验开关。**生产环境必须为 `true`**，否则拒绝启动；非生产保持可配置（默认关）。 |
| `OPENBASE_PRINCIPAL_DB_DEGRADED_ALLOWLIST`（`principal_db_degraded_allowlist`） | str（逗号分隔） | **空** | **显式**主体白名单：仅 DB 不可达时允许放行的本地主体（`users.id` 的十进制字符串）。**默认空 = 不放行任何主体**。 |

**白名单取值约束（fail-closed）**：仅接受**十进制主体 id**；含通配（如 `42*`）、前缀
（如 `user:`）、非数字（如 `abc`）等项一律**丢弃**（不入集合，视同未列名 → 拒绝），
并在解析时记 `WARN` 便于运维定位。禁止模糊/前缀匹配 —— 匹配为**精确字符串相等**。

---

## 4. 拒绝错误码与理由

**DB 不可达且未命中白名单 → HTTP 503 + `SYS_SOURCE_UNAVAILABLE`（字面值 `SYS_503`）。**

理由：

- 根因是**依赖不可用**（主体存储不可达），非客户端凭据问题，属服务端临时性失败
  （可重试），`5xx` 语义更准确；若返回 `401` 会被误读为「凭据失效」，可能诱使客户端
  丢弃有效会话或触发无意义重登。
- 与既有错误码体系**单一来源一致**：`ErrorCode.SYS_SOURCE_UNAVAILABLE` 在
  `core/errors/codes.py` 已明确登记为「数据源/DB 连接失败 → 503（不静默降级为 200 +
  空集）」的 fail-closed 口径，本处复用同一语义，避免新增分叉码。
- `detail` 携带 `{"subject": <主体>, "reason": "db_unavailable"}`，便于与日志
  `request_id` 关联排障（不泄露凭据）。

带委托的 DB 不可达仍为 **403** `PERM_DELEGATION_VERIFY_UNAVAILABLE`（委托不变式不可证
即拒，保持既有语义）。

---

## 5. 白名单运维规范

### 5.1 谁可入（准入原则）

- **仅限**在 DB 短暂不可达窗口内**必须保持可用**的本地主体（通常为平台运维/应急账号）。
- 采用**最小集**原则：默认空；每次新增都应是一次**显式、可审计**的决策，且应有
  **自动移除**的到期约定（见 5.3）。
- **禁止**：通配、前缀、批量区间、非十进制值（解析层已强制丢弃，无法命中）。
- 面向 OIDC 直签/外域主体（`sub` 非数字）不需要列入 —— 该路径本就不进入 DB 主体验证。

### 5.2 如何审计（留痕）

命中白名单放行时产生**双重留痕**：

1. **结构化日志**（`logger=openbase.identity.verification`，级别 `WARN`）：
   `message="principal verify db degraded; allowlisted pass-through"`，
   字段含 `subject` / `reason="db_unavailable_allowlisted"` / `request_id` /
   `decision="allow"` / `allowlist=true`。经统一日志体系（JSON Lines）可按
   `request_id`/`subject` 检索。
2. **审计标注**：主体验证器经 `ContextVar` 承载留痕，调用方（`AuthMiddleware` /
   `get_current_user`）读取后标注到 `request.state.principal_db_degraded_allowlisted`，
   纳入既有审计链路（`{subject, reason, request_id}`）。

拒绝路径亦留痕：`logger=openbase.identity.verification`，级别 `ERROR`，
`message="principal verify db degraded; denied (fail-closed)"`，含
`subject`/`reason="db_unavailable"`/`request_id`/`decision="deny"`。

**指标对账**：`get_verdict_metrics()` 提供 `db_degraded`（DB 降级且无委托的裁定总数）、
`db_degraded_allowlisted`（白名单放行数）、`db_degraded_denied`（fail-closed 拒绝数）
供 verify-env 报告对账。

### 5.3 如何移除

- 应急窗口结束即**从 `OPENBASE_PRINCIPAL_DB_DEGRADED_ALLOWLIST` 移除对应主体 id**
  （逗号分隔列表删除该项即可），并将该配置尽量回退为空。
- 移除后，该主体在 DB 不可达时将回到 **fail-closed 拒绝**（默认安全态）。
- 建议：白名单不长期保留；如需长期保留，应登记「责任人 / 到期日 / 理由」，并按周期复核。

---

## 6. 生产门禁（吊销强制）

- **触发点**：`Settings` 模型校验器 `_validate_production_token_version_enforcement`
  （`openbase/settings.py`），随 `Settings()` 构造（即应用启动）执行，风格与既有
  「弱 JWT 密钥启动拒绝」（`_validate_jwt_secret`）一致。
- **报错文案**：
  `生产环境必须启用 OPENBASE_ENFORCE_TOKEN_VERSION=true（token 吊销强校验），否则拒绝启动（fail-closed）；非生产环境可维持默认关闭`
- **理由**：token 版本（`users.token_version` 递增）是撤销存量令牌的即时手段；生产若
  处于默认关，吊销将静默不生效，属必须前置于启动的门禁缺陷。

---

## 7. 影响面与兼容性

- **DB 正常**（当前现场可达）：行为**零变化**，`fail-closed` 分支不触发；不破坏现场可用性。
- **非生产**：默认值维持现状（`enforce_token_version=False`、白名单空）。
- **受影响既有测试**（语义同步，非行为回退）：`tests/test_verdict_k03.py`、
  `tests/test_identity_t3.py`（原 DB 不可达 fail-open 断言改为 fail-closed）；
  生产 `Settings` 相关用例补齐 `enforce_token_version=True`（`test_settings.py` /
  `test_jwt_secrets.py` / `test_capture_switches.py` / `test_specialized_proxy_upstream_observe.py`）。
- **测试会话离线主体适配**：`tests/conftest.py` 新增 autouse fixture，将**离线/演示主体**
  （内存降级用户 id=1）在测试会话内显式列入白名单（经环境变量 + 实例属性双通道），以保留
  既有「DB 未就绪 + 内存演示用户」的离线冒烟用例（`test_app` / `test_security` /
  `test_proxy_auth` / `test_ui_increments` 等）。生产默认仍为空；白名单 deny/allow 与留痕
  逻辑由 `tests/test_b4_security_hardening.py` 以独立设置对象覆盖，不受该适配影响。
- **未改动**：行缺失无墓碑（非 DB 不可达）仍保持 T3 遗留 fail-open；墓碑/purge 分支不变。

---

## 8. 验证

- 新增 TDD 用例：`tests/test_b4_security_hardening.py`（覆盖 ①~⑥，含非法白名单项 fail-closed）。
- 定向回归：`python -m pytest tests -k "identity or verification or auth or settings or jwt or lifecycle" -q`
- 静态检查：`python -m ruff check openbase tests`

---

## 修订历史

| 版本 | 日期 | 状态 | 变更摘要 | 作者 |
|------|------|------|----------|------|
| v1.0.0 | 2026-10-08 | [Review] | 初稿：记录 B4 安全收紧（主体验证 fail-closed + 显式白名单 + 吊销强制生产门禁）与白名单运维规范 | AA-OpenBase-Dev |
