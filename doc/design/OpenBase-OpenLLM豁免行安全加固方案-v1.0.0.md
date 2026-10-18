# OpenBase-OpenLLM 豁免行安全加固方案-v1.0.0

| 项目 | 内容 |
|------|------|
| 方案名称 | OpenLLM A 直连豁免行（健康/管理面）安全加固方案 |
| 方案编号 | OB-SEC-EXEMPT-HARDENING-v1.0.0 |
| 版本 | **v1.0.0** |
| 状态 | **[Draft]**（待技术评审；评审通过后转 [Review] → [Approved]） |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |
| 适用范围 | OpenLLM 服务 `GATE_EXEMPT_PATH_PREFIXES` 命中的 5 个豁免端点：`/health`、`/metrics`、`/docs`、`/redoc`、`/openapi.json` |
| 风险来源 | 《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.1.0》§5（R1~R8） |
| 关联门禁 | 《OpenBase-主备双通道生产上线必办事项清单-v1.5.0》G4（T4-2） |
| 关联代码 | OpenLLM `app/middleware/identity_gate.py`、`app/middleware/audit.py`、`app/middleware/rate_limit.py`、`app/api/metrics.py`、`backend/main.py`、`app/core/config.py` |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：基于 R1~R8 的现状基线、四层纵深防御设计、H1~H8 逐项加固、配置/实施/验收/回滚/残余风险 |

---

## 1. 背景与目标

### 1.1 背景

OpenLLM 对健康/管理面路径采取「命中即放行」：

```python
# app/middleware/identity_gate.py L83-L86（现状）
if path.startswith(GATE_EXEMPT_PATH_PREFIXES):
    # 健康/管理面 A 直连豁免（忽略身份头，K07 对账；不裁决不剥除）
    await self.app(scope, receive, send)
    return
```

该设计保证了 A 直连与探活的可用性，但使这 5 个端点脱离 M2 身份强校验。G4-T4-2 审批单已识别
R1~R8 八项风险，本方案给出可落地的加固设计。

### 1.2 目标

| 编号 | 目标 |
|:----:|------|
| G-1 | 消除「前缀误命中」导致的未登记身份旁路（R1/R6） |
| G-2 | 生产环境不暴露 API 文档与全量 Schema（R2） |
| G-3 | 指标与健康明细仅对受信消费方可见（R3/R4） |
| G-4 | 豁免路径访问可审计、可归因到来源（R5） |
| G-5 | 豁免到期与配置漂移可机械拦截（R6/R7） |
| G-6 | 豁免路径具备独立限流，避免资源滥用（R8） |

### 1.3 非目标

- 不改变业务面端点的身份强校验语义与 403/401 行为；
- 不改变写路径与 L2-2 通道矩阵判据；
- 不引入新的外部依赖或网关组件；
- 不翻转既有默认值（新增开关默认保持现行行为，仅在生产门禁下强制收紧）。

---

## 2. 现状基线（代码事实）

| 事实 | 位置 | 含义 |
|------|------|------|
| 豁免集合为 5 个前缀，采用 `str.startswith` 匹配 | `identity_gate.py` L35-L41、L83 | 前缀匹配；`/healthfoo` 也会命中 |
| 豁免命中后不做身份裁决、不剥除身份头 | `identity_gate.py` L83-L86 | 完全绕过 M2 |
| 文档/Schema 由 `DEBUG or OPENAPI_PUBLIC` 控制 | `main.py` L447-L463 | 默认关闭；但生产若误配 `OPENAPI_PUBLIC=true` 仍会开放 |
| `/metrics` 无认证 | `metrics.py` L1-L7、L23-L29 | 任意可达来源可抓取 |
| `/health` 返回 `version` + PostgreSQL/Redis 明细 | `main.py` L675-L707 | 泄露依赖拓扑与版本 |
| `/openllm/v1/health` 返回 `components` + `channel` + `channel_report` | `openllm_gateway.py` L3704-L3749 | 泄露通道状态与组件拓扑 |
| 审计中间件将 5 个豁免路径列入排除集 | `audit.py` L46-L54 | 豁免访问**不落审计** |
| 限流中间件将 `/health`、`/metrics` 列入豁免 | `rate_limit.py` L87-L95 | 豁免路径**无限流** |

> 结论：R2 已有部分控制（默认关闭），R3/R4/R5/R8 均无应用层控制，R1/R6/R7 无机械守护。

---

## 3. 总体策略：四层纵深防御

| 层级 | 控制目标 | 主要手段 | 责任方 |
|:----:|---------|---------|--------|
| **L1 网络层** | 缩小可达面 | 内网监听、安全组/NetworkPolicy、仅 OpenBase 出口 IP 可访问 | OPS |
| **L2 应用层** | 收紧豁免语义 | 精确匹配、路径规范化、明细分级、指标鉴权、独立限流、审计留痕 | LL |
| **L3 配置与门禁** | 防漂移/防过期 | 豁免登记表单一事实源、启动断言、发布门禁脚本 | LL / OB |
| **L4 观测与响应** | 可发现可告警 | 豁免访问计数、异常调用告警、到期告警 | OPS |

> L1 是必要条件但不可单独依赖：若应用层仍按前缀放行，网络层被突破后无第二道防线。

---

## 4. 逐项加固设计

### H1（对应 R1/R6）豁免匹配改为精确匹配 + 路径规范化 + 启动断言

**设计**

1. 豁免集合由 `tuple[str, ...]` 改为显式路由表 `EXEMPT_ROUTES: frozenset[str]`，**只允许精确相等**。
2. 匹配前做路径规范化与非法形态拒绝：
   - 使用 `scope["raw_path"]` 检查是否含 `%2f`、`%2e`、`//`、`/../`、`\\`；
   - 命中上述形态直接 `400 PARAM_400`，**不进入豁免**。
3. 启动断言（生产强制）：
   - 每个豁免路径必须存在于 `app.routes` 且方法为 `GET`；
   - 不存在任何**非豁免**路由的路径以豁免路径为前缀（防止未来新增 `/health_debug` 被静默纳入）；
   - 断言失败 ⇒ 生产环境拒绝启动。

**建议实现**

```python
# app/middleware/identity_gate.py（提案）
EXEMPT_ROUTES: frozenset[str] = frozenset({
    "/health", "/metrics", "/docs", "/redoc", "/openapi.json",
})
_SUSPICIOUS_SEGMENTS = ("//", "/../", "/./", "\\")

def _is_exempt_path(raw_path: bytes, path: str) -> bool:
    if any(seg in path for seg in _SUSPICIOUS_SEGMENTS):
        return False
    lowered = raw_path.decode("latin-1").lower()
    if "%2f" in lowered or "%2e" in lowered:
        return False
    return path in EXEMPT_ROUTES

def assert_exempt_routes(app) -> None:
    """启动断言：豁免项存在且无前缀碰撞（生产失败即拒绝启动）。"""
    concrete = {r.path for r in app.routes if getattr(r, "methods", None)}
    missing = EXEMPT_ROUTES - concrete
    if missing:
        raise RuntimeError(f"豁免路由未注册: {sorted(missing)}")
    collisions = {
        p for p in concrete
        if p not in EXEMPT_ROUTES and any(p.startswith(e + "/") or p == e for e in EXEMPT_ROUTES)
    }
    if collisions:
        raise RuntimeError(f"豁免路径存在前缀碰撞: {sorted(collisions)}")
```

**兼容性**：通过 `OPENLLM_EXEMPT_MATCH_MODE=prefix|exact` 控制，默认 `prefix`（现行行为）；
生产门禁要求 `exact`。`assert_exempt_routes` 仅在生产或显式开启时执行。

---

### H2（对应 R2）文档与 Schema 生产 fail-closed

**现状**：`_openapi_public = settings.DEBUG or settings.OPENAPI_PUBLIC`，默认关闭，但生产误配即开放。

**设计**

1. 保留现有开关；
2. 新增生产启动校验：`ENV=production` 且 `DEBUG=true` 或 `OPENAPI_PUBLIC=true` ⇒ **拒绝启动**，
   错误信息明确指向 `OPENLLM_OPENAPI_PUBLIC`；
3. 若确有内网查阅需求，提供独立受控入口（不纳入豁免）：
   `INTERNAL_DOCS_ENABLED=true` 时挂载 `/internal/docs`，要求管理员 JWT + `admin` 角色；
   **禁止**复用 `/docs` 路径。

**验收**：生产 `GET /docs`、`/redoc`、`/openapi.json` 均 404；误配时启动失败并留日志。

---

### H3（对应 R3）`/metrics` 鉴权与标签脱敏

**设计**

1. 新增 `OPENLLM_METRICS_AUTH_MODE`：
   - `none`（默认，保持现行行为）
   - `token`：校验 `X-Metrics-Token`，与 `OPENLLM_METRICS_TOKEN` 做 `hmac.compare_digest`
   - `trusted-source`：校验来源 IP 属于 `OPENLLM_METRICS_ALLOWED_SOURCES`（CIDR 列表）
2. 生产门禁：`ENV=production` 时 `mode` 必须为 `token` 或 `trusted-source`，否则拒绝启动；
3. 标签审计：新增单测扫描指标 label 名，禁止出现 `tenant`、`user`、`subject`、`org`、`email` 等维度；
4. 未授权返回 `401`，不返回指标内容，错误体不含内部路径。

**说明**：Prometheus 抓取侧需同步配置 token 或来源白名单，属 OPS 交付项。

---

### H4（对应 R4）健康明细分级返回

**设计**

1. `/health` 按来源分级：
   - **受信来源**（回环/私网 + 白名单，或携带 `X-Health-Token`）：返回完整 `status` + `version` + `details`；
   - **非受信来源**：仅返回 `{"status": "healthy|degraded"}`，**不含** `version`、`details`、依赖名。
2. `/openllm/v1/health` 同理：非受信来源仅返回 `{"status"}`；`components`、`channel`、`channel_report`
   仅对受信来源返回。
3. 通道状态机的探活**不得依赖外部 HTTP 健康端点**：应直接调用进程内探针函数（现状已为
   `_probe_components` 直连依赖），避免“探活被伪造”影响 `bypass_orchestration`。
4. 新增 `OPENLLM_HEALTH_DETAIL_MODE=all|trusted-only`，默认 `all`（现行行为），生产要求 `trusted-only`。

**兼容性**：运维监控若来自非受信网段需先纳入 `OPENLLM_HEALTH_TRUSTED_SOURCES`，否则只能读到粗粒度状态。

---

### H5（对应 R5）豁免路径访问审计

**现状**：`AuditMiddleware.EXCLUDED_PATHS` 直接排除了这 5 个路径，导致完全无记录。

**设计**

1. 将 5 个路径从 `EXCLUDED_PATHS` 移出，改为**专用轻量审计**（避免记录请求体）：
   - 事件名：`exempt_path_access`
   - 字段：`request_id`、`path`、`method`、`client_ip`、`user_agent`、`source_header_present`、`trusted_source`、`decision`（allowed/rejected）
   - **禁止**记录身份头原值、Cookie、Authorization
2. 级别：正常访问 `INFO`；非受信来源访问 `/docs`、`/openapi.json`、`/metrics` 记 `WARN`。
3. 指标：`openllm_exempt_path_requests_total{path,trusted}`，用于基线与异常告警。
4. 开关 `OPENLLM_EXEMPT_AUDIT_ENABLED`，默认 `false`（保持现行“无记录”），生产要求 `true`。

> 隐私说明：`client_ip` 属网络层标识，保留期与脱敏策略由 OPS 统一规定（见 §11 Q4）。

---

### H6（对应 R1/R6）豁免登记表单一事实源 + 发布门禁

**设计**

1. 新增 `config/exempt_endpoints.json` 作为**唯一事实源**：

```json
{
  "schema_version": 1,
  "entries": [
    {
      "path": "/health",
      "method": "GET",
      "category": "health-management",
      "ticket": "T-健康直连",
      "approver": "AD-OpenLLM-Dev",
      "expires_at": "2026-12-31",
      "rationale": "A 直连探活"
    }
  ]
}
```

2. 代码启动时加载该文件，与 `EXEMPT_ROUTES` 做集合相等断言；不一致 ⇒ 生产拒绝启动；
3. 新增发布门禁脚本 `scripts/verify_exempt_endpoints.py`，三项校验：
   - 登记表 ↔ `EXEMPT_ROUTES` 集合相等；
   - 登记表 ↔ K07 矩阵豁免行（`k07-finalize.json`）逐行一致；
   - 字段完整性（`ticket/approver/expires_at` 非空）；
   - 输出 `RESULT: PASS|FAIL`，退出码 0/1；
4. 审批单 §8 的机械核对直接复用该脚本输出。

---

### H7（对应 R7）豁免到期强制失效

**设计**

1. 启动时解析 `expires_at`：
   - 已过期：**生产环境直接失效该豁免**（请求回到身份裁决链路），并记 `ERROR`；非生产仅 `WARN`；
   - 剩余 ≤30 天：`WARN` + 指标 `openllm_exempt_expiring_days`；
2. 开关 `OPENLLM_EXEMPT_EXPIRY_ENFORCE`，默认 `false`（现行行为），生产要求 `true`；
3. 定时任务（每日）检查一次，避免长进程跨过到期日仍生效。

**副作用**：到期失效后，A 直连探活将收到 401/403；这是预期的 fail-closed，需在到期前完成续期或迁移。

---

### H8（对应 R8）豁免路径独立限流

**设计**

1. 现状 `rate_limit.py` 将 `/health`、`/metrics` 列入 `EXEMPT_PATHS`，完全无限流；
2. 改为**独立限流桶**而非完全豁免：
   - `OPENLLM_EXEMPT_RATE_LIMIT_RPM`（默认 `0`＝不限，保持现行行为；生产建议 `120`）
   - 按 `client_ip + path` 计数，超限返回 `429` + `Retry-After`；
3. `trusted-source`（Prometheus 抓取源、探活源）不计数或使用更高额度；
4. 限流状态复用现有内存桶实现，不引入 Redis 依赖。

---

## 5. 新增配置项清单

| 配置 | 默认值 | 生产要求 | 作用 |
|------|--------|---------|------|
| `OPENLLM_EXEMPT_MATCH_MODE` | `prefix` | `exact` | 豁免匹配方式（H1） |
| `OPENLLM_EXEMPT_REGISTRY_PATH` | `config/exempt_endpoints.json` | 同左 | 登记表路径（H6） |
| `OPENLLM_EXEMPT_ASSERT_ON_STARTUP` | `false` | `true` | 启动断言（H1/H6） |
| `OPENLLM_EXEMPT_EXPIRY_ENFORCE` | `false` | `true` | 到期强制失效（H7） |
| `OPENLLM_EXEMPT_AUDIT_ENABLED` | `false` | `true` | 豁免访问审计（H5） |
| `OPENLLM_EXEMPT_RATE_LIMIT_RPM` | `0` | `120`（建议） | 豁免路径限流（H8） |
| `OPENLLM_METRICS_AUTH_MODE` | `none` | `token` 或 `trusted-source` | 指标鉴权（H3） |
| `OPENLLM_METRICS_TOKEN` | 空 | 由密钥管理下发 | 指标 token（H3） |
| `OPENLLM_METRICS_ALLOWED_SOURCES` | 空 | 抓取源 CIDR | 指标来源白名单（H3） |
| `OPENLLM_HEALTH_DETAIL_MODE` | `all` | `trusted-only` | 健康明细分级（H4） |
| `OPENLLM_HEALTH_TRUSTED_SOURCES` | 空 | 探活/监控 CIDR | 健康明细来源白名单（H4） |
| `OPENLLM_INTERNAL_DOCS_ENABLED` | `false` | `false` | 内网受控文档入口（H2） |

> 所有新增开关默认值均**保持现行行为**；收紧仅由生产门禁 `ENV=production` 强制。
> 生产门禁校验函数建议放在 `app/core/startup_checks.py`，由 `main.py` 在 `FastAPI(...)` 之后、
> 路由注册完成后调用，任一项不满足 ⇒ `RuntimeError` 拒绝启动。

---

## 6. 实施计划

| 任务 | 内容 | 依赖 | 交付物 |
|:----:|------|:----:|--------|
| **T1** | 豁免登记表 JSON + 加载器 + 精确匹配 + 路径规范化 | — | 代码 + 单测 |
| **T2** | 启动断言（路由存在性/前缀碰撞/登记表一致） | T1 | 代码 + 单测 + 启动日志 |
| **T3** | 文档/Schema 生产 fail-closed | — | 代码 + 单测 |
| **T4** | `/metrics` 鉴权（token / trusted-source） | — | 代码 + 单测 + 运维配置说明 |
| **T5** | `/health` 与 `/openllm/v1/health` 明细分级 | — | 代码 + 单测 |
| **T6** | 豁免访问审计 + 计数指标 | — | 代码 + 单测 + 日志样例 |
| **T7** | 到期强制失效 + 每日检查 | T1 | 代码 + 单测 |
| **T8** | 豁免路径独立限流 | — | 代码 + 单测 |
| **T9** | 发布门禁脚本 `verify_exempt_endpoints.py` | T1 | 脚本 + 输出样例 |
| **T10** | 回归、证据归档、审批单 §8 回填 | T1~T9 | 证据 JSON + 文档 |

建议按 T1→T2→T9 先打通“防漂移”主链，再并行 T3~T8，最后 T10 统一验收。

---

## 7. 验收判据

| 编号 | 判据 | 方法 |
|:----:|------|------|
| **AC-1** | `/healthz`、`/metricsx` 不再被豁免 | 请求应进入身份裁决（无身份 ⇒ 401/403，而非 200） |
| **AC-2** | 含 `..`、`//`、`%2f` 的路径不进入豁免且被拒绝 | 负向用例返回 400/404，且无豁免审计事件 |
| **AC-3** | 生产 `DEBUG=true` 或 `OPENAPI_PUBLIC=true` 时拒绝启动 | 启动命令退出码非 0，日志含明确原因 |
| **AC-4** | 生产 `/docs`、`/redoc`、`/openapi.json` 返回 404 | 真实运行态探针 |
| **AC-5** | `/metrics` 无 token/非白名单来源返回 401；授权来源 200 | 三态用例（无/错/对） |
| **AC-6** | 非受信来源 `/health` 仅返回 `status`；受信来源返回完整明细 | 两组来源对比 |
| **AC-7** | 每次豁免访问产生 `exempt_path_access` 审计事件（不含身份头） | 日志检索 + 字段白名单断言 |
| **AC-8** | 登记表与路由、K07 矩阵不一致时脚本退出码 1；生产启动失败 | 篡改登记表复跑 |
| **AC-9** | 过期豁免在生产失效（请求转为 401/403） | 注入 `expires_at` 为昨日 |
| **AC-10** | 超限返回 429；受信抓取源不受影响 | 压测豁免路径 |
| **AC-11** | 业务面 403/401 行为、L2-2 读写等价与 K14 幂等**无变化** | 全量回归 + 矩阵复跑 |

---

## 8. 测试计划

| 类型 | 范围 | 关键用例 |
|------|------|---------|
| 单元测试 | `identity_gate` | 精确匹配、路径规范化、前缀碰撞断言、登记表一致 |
| 单元测试 | `metrics` | 三种鉴权模式、错误 token、CIDR 匹配 |
| 单元测试 | `health` | 受信/非受信返回字段集合 |
| 单元测试 | `audit` | 事件字段白名单、级别（INFO/WARN） |
| 单元测试 | `expiry` | 未到期/≤30 天/已过期三态；时钟注入 |
| 单元测试 | `rate_limit` | 独立桶、429、受信源放行 |
| 集成测试 | 真实启动 | 生产门禁 12 项配置逐项缺失 → 拒绝启动 |
| 回归 | 业务面 | 既有 403/401 矩阵与 K07 隔离用例 |
| 回归 | 通道 | `dual_channel_e2e.py` 四子系统读写等价 + K14 |

> 覆盖率要求：新增代码 ≥90%（遵循项目测试规则）。

---

## 9. 灰度与回滚

**灰度顺序**

1. **Phase 1（开发/测试）**：合并代码，全部新开关保持默认，验证零行为变化；
2. **Phase 2（预发）**：开启生产门禁，逐项验证 AC-1~AC-11；
3. **Phase 3（生产窗口）**：先开审计与告警（只观测不拦截）→ 再开鉴权/分级 → 最后开到期强制与限流；
4. **Phase 4（稳定期）**：观察 7 天，确认无非预期 401/403 与抓取失败。

**回滚**

| 场景 | 动作 |
|------|------|
| Prometheus 抓取失败 | 回退 `OPENLLM_METRICS_AUTH_MODE=none`（或补白名单） |
| 监控读不到健康明细 | 回退 `OPENLLM_HEALTH_DETAIL_MODE=all`，并补 `OPENLLM_HEALTH_TRUSTED_SOURCES` |
| 豁免过期导致探活失败 | 续期登记表并重启；紧急时可临时 `OPENLLM_EXEMPT_EXPIRY_ENFORCE=false` |
| 代码级异常 | 回滚至上一版本（开关无法绕过启动断言） |

> 所有回滚动作须留操作记录，并在 24 小时内补齐根因与修复计划。

---

## 10. 影响面与兼容性

| 对象 | 影响 | 说明 |
|------|------|------|
| 业务面端点 | 无 | 不进入豁免判定分支 |
| B 通道编排 | 无 | 不依赖 HTTP 健康端点做内部决策 |
| A 直连探活 | 有 | 到期失效/明细分级后，非受信探活只能读粗粒度状态 |
| Prometheus | 有 | 需配置 token 或来源白名单 |
| 运维监控 | 有 | 需提供受信来源清单 |
| K07 矩阵 | 有 | 豁免行登记表需与矩阵、审批单三方一致 |

---

## 11. 残余风险与未决问题

| 编号 | 事项 | 处置建议 |
|:----:|------|---------|
| **Q1** | metrics token 下发方式（K8s Secret / 配置中心 / 仅 CIDR） | 由 OPS 在发布窗口前裁定；优先 CIDR + token 双因子 |
| **Q2** | `/openllm/v1/health` 当前不在 `GATE_EXEMPT_PATH_PREFIXES`，但被限流豁免 | 本方案按“受信分级”处理；是否纳入正式豁免登记需评审确认 |
| **Q3** | 网络层 ACL/NetworkPolicy 归属与落地载体 | OPS 提供；应用层加固不以其为前提 |
| **Q4** | `client_ip` 审计留存期与隐私合规 | 按组织日志规范执行，默认 90 天可配置 |
| **Q5** | 豁免到期后的替代方案（长期是否保留 A 直连探活） | 建议在下一版本评估“独立管理端口”替代路径豁免 |

---

## 12. 附件与引用

1. 《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.1.0》§5、§8
2. 《OpenBase-主备双通道生产上线必办事项清单-v1.5.0》G4
3. OpenLLM `app/middleware/identity_gate.py`
4. OpenLLM `app/middleware/audit.py`
5. OpenLLM `app/middleware/rate_limit.py`
6. OpenLLM `app/api/metrics.py`
7. OpenLLM `backend/main.py`
8. OpenLLM `app/core/config.py`
9. `doc/test/evidence/s7/gate/k07-finalize.json`
10. `doc/test/evidence/s7/l2-2/matrix-finalize.json`

---

**方案状态**：[Draft]（待技术评审；评审通过后进入实施排期，实施完成回填 §7 验收结果并升版）
