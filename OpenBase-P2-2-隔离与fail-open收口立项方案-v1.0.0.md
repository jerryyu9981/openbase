# OpenBase-P2-2-隔离与fail-open收口立项方案-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-GOV-P2-2-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 日期 | 2026-09-06 |
| 作者 | AD（跨项目分析） |
| 版本主题 | P2-2 立项：DPS fail-open 两处收口为 fail-closed + X-User-ID=1 硬绑核销 + OpenMemory /sessions 端点隔离与归属校验 |
| 适用范围 | DPS（src/rest_api v2，编排 8030）、OpenMemory（src/openmemory/api/controllers.py）、OpenBase（测试与文档基线） |

> 立项依据：《OpenBase-四件套身份治理评审-R3R5》v1.5.0 §8 路线图 P2-2（与 P1-4 同批次评估，状态待立项）。本方案承接将该行转为可执行项目，原则沿用评审 Q1/Q2/Q3 定案（tenant 唯一键、org 头退役为兼容别名、code 对外统一）与 DPS 任务书 P9 冒烟门禁口径。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-06 | AD（跨项目分析） | 初始版本：现状盘点、目标态、任务分解、决策建议、验收与风险 |

---

## 1. 背景与目标

评审 §8 P2-2 行：**OpenMemory /sessions 端点隔离与归属校验；DPS fail-open 两处与 X-User-ID=1 硬绑治理**。目标态：

1. DPS 安全核心中间件在依赖故障（DB 查询异常/权限引擎异常/未初始化）时**默认拒绝（fail-closed）**，不再静默放行；可用性降级改由显式配置与上游（OpenBase dps-proxy）感知，避免"鉴权静默失效=越权面打开"。
2. DPS `X-User-ID=1 → super_admin` 硬绑事实核销：确认代码层已移除（v2.8.1 P3），仅剩种子演示绑定需语义固化（演示数据不构成提权路径）。
3. OpenMemory `/sessions` 族端点数据级归属过滤：list 不再全量透出、get/terminate 校验归属，防跨用户/跨租户会话操作。

## 2. 现状盘点（代码证据，2026-09-06 核对）

### 2.1 DPS fail-open 两处（+1 处相关）

| # | 落点（DPS src/） | 行为 | 代码证据 |
|---|------------------|------|---------|
| FO-1 | middleware/tenant_middleware.py `_validate_context` | DB 查询异常且 `MULTI_TENANT_ENABLED=true`（config 默认 true，L95-97）→ **降级放行**（L251-257）；无 DB 连接 → 放行（L259-261，注释"仅测试模式可达"）。即运行时依赖故障默认放行 | L206-261 |
| FO-2 | middleware/permission_middleware.py `dispatch` | 权限引擎未初始化 → 放行（L65-68）；`check_permission` 异常 → 放行（L85-88） | L57-99 |
| FO-3（相关） | middleware/rate_limit_middleware.py | 限流检查失败 → 放行（L98）。属可用性优先常规策略，建议保留但补日志/指标，不纳入本次 fail-closed 改造 | L98 |

注：受管启动 `DB_FAIL_FAST=true`（config L53 默认）已挡"DB 未初始化即启动"，但**运行期 DB 故障**仍由 FO-1 放行。

### 2.2 X-User-ID=1 硬绑核销

- main.py:179 / rest_api/app.py:137 注释：v2.8.1 P3 已移除"X-User-ID=1 → super_admin"启动硬绑；绑定改由 `platform.user_roles` 显式（种子 `DEFAULT_USER_BINDINGS="1:super_admin"`，env `DPS_DEMO_USER_ROLES` 可覆盖）。
- 权限引擎 super_admin 全权来自**角色预设**（engines/permission_engine.py L30/L282），非用户 id 特判。
- 核销结论：**代码层硬绑已移除**；残余为演示种子绑定（1:super_admin）与本次 P1 联调补的画像对象绑定，属种子数据。治理动作=在 DPS 部署/种子文档固化"生产环境须以 DPS_DEMO_USER_ROLES 显式收紧，不得沿用默认 1:super_admin 绑定"。
- 现行 user_roles（共享 PG）含：uid 1→super_admin（seed）、uid 2→41、uid dps-tenant-001_admin1_001→super_admin（P1 联调补种）。

### 2.3 OpenMemory /sessions 隔离缺口

- `src/openmemory/api/controllers.py`：
  - `GET /sessions`（L1077-1102）：遍历 `session_store._session_index` **全量**返回，无 user/org 过滤。
  - `GET /sessions/{session_id}`（L1105-1126）：按 id 直查 `service.get_session_memories`，无归属校验。
  - `POST /sessions/{session_id}/terminate`（L1129-1149）：按 id 直接 `clear_session`，无归属校验。
- RBAC 权限矩阵（auth/permission.py L81-82 `"*/sessions"`/`"*/sessions/*"`）为端点级粗粒度，无数据级归属；鉴权开启时任意已认证用户可读/清任意会话。
- 会话存储当前为进程内 `_session_index`/session_store（InMemory 形态），多实例部署下天然非共享——归属校验需先在存储层补充 session 归属字段（user/org 元数据）。

## 3. 任务分解（T1~T5）

### T1 DPS：tenant 中间件 DB 故障 fail-closed 化（FO-1）

- 落点：`middleware/tenant_middleware.py` `_validate_context` 异常分支。
- 改动：DB 查询异常统一返回 403 `验证服务暂时不可用`（与 DB_FAIL_FAST=false 排障态一致），**移除 multi_tenant_enabled 条件放行**；新增配置键 `TENANT_VALIDATE_FAIL_OPEN`（默认 false）供显式调试/降级放行（默认 fail-closed，决策 D1）。
- 连带：缓存读失败不再静默继续（保持现状语义即可，不扩大）。
- 测试：更新 `tests/test_v280_coverage_gap2.py` L609/L643 族断言（DB 异常→fail-closed）；新增 fail-open 配置分支用例。

### T2 DPS：permission 中间件 fail-closed 化（FO-2）

- 落点：`middleware/permission_middleware.py`。
- 改动：权限引擎未初始化与 `check_permission` 异常由"放行"改 **403 拒绝**（`无权限/验证不可用`）；新增配置键 `PERMISSION_FAIL_OPEN`（默认 false）。
- 测试：`test_v280_coverage_gap2.py` L311/L362 族断言翻转 + 配置分支用例。

### T3 OpenMemory：sessions 归属过滤与校验

- 前置：session 记录补归属元数据（user_id/org_id，创建/复用时写入；session_store 索引升级）。
- 改动：list_sessions 按当前身份（X-User-ID/X-Org-ID 或 Bearer 身份，与 auth/middleware 对齐）过滤；get/terminate 校验归属，非归属返回 404（不泄露存在性）。
- 依赖：与治理 Q2/Q3（tenant 唯一键、code 形态）及 P0-2 M3 身份头（OpenBase 注入 X-User-ID）一致——OpenBase→OpenMemory 直连带身份头场景为第一优先级。
- 测试：归属内/跨归属读 404、跨归属 terminate 404、未认证 401 矩阵（对齐 v7.1 E2E 10/10 基线风格）。

### T4 DPS：硬绑核销与种子语义固化

- 动作：以本方案 §2.2 为据，在 DPS 种子脚本注释与《DPS-OpenBase 对接使用指南》中固化"默认 1:super_admin 仅为演示，生产以 DPS_DEMO_USER_ROLES 显式收紧 + fail-closed 验证"；登记现状 user_roles 至文档（含 P1 联调补种行）。
- 验收：文档化完成；无代码改动（硬绑已移除，核销留档）。

### T5 回归与门禁

- DPS：`pytest src/tests`（受管 SQLITE_FALLBACK=false 真实 PG 子集 + fail-open/fail-closed 分支）0 失败；ruff 0 错误。
- OpenMemory：`pytest`（sessions 相关 + v7.1 E2E 基线）0 失败。
- 联调：编排重启后 dps-proxy 画像族仍 200（fail-closed 不影响正常路径）；OpenBase 全量 `pytest tests` 绿（基线）。
- 冒烟联动：DPS 任务书 P9 门禁项与治理 P2-2 验收互证。

## 4. 决策建议（评审用）

| # | 决策点 | 建议 | 理由 |
|---|--------|------|------|
| D1 | tenant 中间件 DB 故障语义 | **默认 fail-closed**（403），`TENANT_VALIDATE_FAIL_OPEN=false` 显式开启放行 | FO-1 当前默认放行=鉴权静默失效；DB 故障属"不可用"而非"可放行"，上游 dps-proxy 已有健康探活/降级感知，不依赖 DPS 内放行 |
| D2 | permission 中间件异常语义 | **默认 fail-closed**（403），`PERMISSION_FAIL_OPEN=false` | 权限校验失败放行即越权；异常须显式（日志+403）暴露，勿吞 |
| D3 | rate_limit fail-open 去留 | 保留放行但补 WARN 日志与指标 | 限流降级属可用性保护，非授权面；保持不阻塞业务 |
| D4 | OpenMemory sessions 归属键 | 以 `(org_id, user_id)` 复合归属（tenant 唯一键语义，Q2/Q3） | 与治理统一；user-only 在租户共享场景不足 |

## 5. 验收标准

| 项 | 验收 |
|----|------|
| T1 | DPS 注入 DB 故障（stop 共享 PG 或 mock 抛错）：tenant 中间件返回 403 非放行；`TENANT_VALIDATE_FAIL_OPEN=true` 时恢复放行（联调排障用） |
| T2 | 注入权限引擎异常/未初始化：403 拒绝；`PERMISSION_FAIL_OPEN=true` 显式放行 |
| T3 | sessions list 仅含归属内会话；跨归属 get/terminate 404；正常归属内 200 |
| T4 | 指南/种子注释固化生产绑定收紧要求 |
| T5 | 三仓测试全绿 + 正常链路 dps-proxy 200 回归 |

## 6. 风险与依赖

- 依赖：Q2/Q3（tenant 唯一键/code）若先行，T3 归属键直接用 tenants.code；DPS 侧 org/tenant 校验与 P1-2/P1-3 同源改造，避免返工。
- 风险 1：T3 前置存储归属元数据涉及会话索引结构变更，影响面需 OpenMemory 单测基线护航。
- 风险 2：DPS fail-closed 上线前须确认编排期 DB 抖动不会造成误拒（建议结合 dps-proxy 探活与启动 DB_FAIL_FAST 双保险，故障窗口由探活感知）。
- 联动：评审 §8 P1-2/P1-3（code 化）与 P2-1（统一身份头）立项后与本项按序排期。

## 7. 排期与产出

| 阶段 | 内容 | 产出 |
|------|------|------|
| Phase 1 | DPS T1+T2（fail-closed + 配置分支 + 测试） | DPS 仓改动与回归 |
| Phase 2 | OpenMemory T3（归属元数据 + 过滤/校验 + 测试） | OpenMemory 仓改动与回归 |
| Phase 3 | T4 文档固化 + T5 联调门禁 | 指南更新、评审记录、冒烟互证 |

> 状态约定：本方案经评审批准后进入实施；任务书/评审 §8 P2-2 状态由"待立项"更新为"已立项/实施中/已完成"。
