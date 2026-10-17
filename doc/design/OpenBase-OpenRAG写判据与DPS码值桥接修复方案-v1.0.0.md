# OpenBase — OpenRAG 写判据修复与 DPS 码值桥接打通方案

| 项目 | 内容 |
| --- | --- |
| 文档版本 | v1.0.0 |
| 文档状态 | [Draft] |
| 适用环境 | Dev / Test（联调态）；生产需另行编排窗口 |
| 编制日期 | 2026-10-17 |
| 编制人 | OpenBase 架构组 |
| 关联文档 | 《OpenBase-主备双通道生产上线必办事项清单-v1.0.0》《OpenBase-跨仓数据面租户隔离走查报告-v1.0.0》（v1.4.0） |
| 关联问题 | G5（回写链路真实面）、G6（profile 路由真实化）；本轮 B 通道实测 `degraded=["rag"]`、回写 profile 403 |

---

## 1. 背景与问题实证

2026-10-17 全栈七服务联调实跑（OpenBase 8000 / OpenLLM 8001 / OpenRAG 8010 / OpenMemory 8020 / DPS 8030 / OIDC 8090 / 前端 5173）暴露两处真实阻断：

| 序号 | 实测现象 | 证据 |
| --- | --- | --- |
| E1 | 显式三路 pipeline（memory+rag+llm）返回 200，但 `executed=["memory","llm"]`、`degraded=["rag"]` | `doc/tmp/e2e_explicit_response.json` |
| E2 | OpenLLM → OpenRAG 检索 403 `PERM_SERVICE_KEY_WRITE_DENIED`（PERM-4035），`reason=subject_required_for_write_under_m2` | OpenLLM 错误日志 `HTTP Request: POST http://127.0.0.1:8010/api/v1/collections/{id}/query/retrieve "HTTP/1.1 403 Forbidden"` |
| E3 | 回写 profile 连续 3 次失败，DPS 返回 403「租户不存在或不属于该组织」 | OpenLLM `WritebackQueue` 日志 `target=profile seq=125/2 err=组件 dps 不可用: HTTP 403` |

补充实测（本轮新增，用于定位边界）：

| 探测 | 请求头 | 结果 | 解读 |
| --- | --- | --- | --- |
| D1 | `X-Org-ID=dps-org-001`、`X-Tenant-ID=dps-tenant-001` | **403「无权限执行 create 操作于 portrait」** | **租户校验已通过**，阻塞点下移到 DPS RBAC |
| D2 | `X-Org-ID=org-1`、`X-Tenant-ID=tenant-1` | 403「组织不存在」 | 码值未桥接时的典型表现 |
| D3 | 不带租户头 | 401「缺少组织或租户标识」 | DPS 对缺头 fail-closed，无默认兜底 |
| D4 | 直接查共享 PG `platform.organization / tenant` | `dps-org-001 → dps-tenant-001`（均 active） | **目标码值在库中真实存在且归属正确** |

结论先行：**能力已具备，缺的是「只读语义判据」与「跨系统主体/码值对齐」两处连接件**，不是底层功能缺失。

---

## 2. 根因分析

### 2.1 问题一：OpenRAG 把「检索」判成「写」

代码路径 [role_gate.py](file:///D:/Trae%20CN/myproject/Dev/OpenRAG/src/openrag/api/middleware/role_gate.py#L107-L127)：

```python
# M2 匿名（仅 key 无主体域）：业务写拒绝（D-V6）
if subject_type not in _SUBJECT_TYPES:
    if method in WRITE_METHODS:      # WRITE_METHODS = {POST, PUT, PATCH, DELETE}
        return self._reject(..., code=PERM_SERVICE_KEY_WRITE_DENIED, ...)
    return await call_next(request)
```

判据是**纯 HTTP 方法**（[role_map.py](file:///D:/Trae%20CN/myproject/Dev/OpenRAG/src/openrag/identity/role_map.py#L59)）。而 OpenRAG 的纯检索端点只有 `POST /collections/{collection_id}/query/retrieve`（[query.py](file:///D:/Trae%20CN/myproject/Dev/OpenRAG/src/openrag/api/routes/query.py#L164-L187)），**没有 GET 等价端点**。

因此：检索语义 → POST → 被判写 → 匿名主体直接 403。这是**语义与方法不匹配**，不是权限配置错误。

> 注：手工带 `X-Proxy-Source=openbase-rag-proxy` + `X-User-ID` + `X-Tenant-ID` 时创建集合可成功，说明受信主体通道本身正常；问题只发生在「只有服务密钥、无主体」的编排匿名形态。

### 2.2 问题二：DPS 码值与主体双缺口

链路：`OpenBase JWT → llm-proxy 出站头 → OpenLLM 编排 → profile adapter → DPS`

| 层 | 现状 | 缺口 |
| --- | --- | --- |
| 码值层 | OpenBase 有 `dps_code_map`（登记式，优先）+ 旧 `dps_org_map/dps_tenant_map`（[dps_code_map.py](file:///D:/Trae%20CN/myproject/Dev/OpenBase/openbase/modules/protocol_headers/dps_code_map.py#L229-L234)、[dps_proxy](file:///D:/Trae%20CN/myproject/Dev/OpenBase/openbase/modules/dps_proxy/__init__.py#L82-L110)）；OpenLLM 有 `DPS_ORG_CODE_MAP/DPS_TENANT_CODE_MAP`（[profile.py](file:///D:/Trae%20CN/myproject/Dev/OpenLLM/backend/app/edgerouter/adapters/profile.py#L63-L93)） | 两处映射**键空间不统一**，且未覆盖 UUID / 兜底码形态；未知码**静默原样透传**（映射 miss 无告警） |
| 主体层 | DPS `platform.users` 有 `admin(id=1)`，`platform.user_roles` 有 `'1' → super_admin`、`'probe-user' → super_admin(subject_source=openbase)` 等 | **不存在 `admin` 这一 user_id 键**。DPS 权限引擎按 `X-User-ID` 原值查 `user_roles`（[permission_middleware.py](file:///D:/Trae%20CN/myproject/Dev/DPS/src/middleware/permission_middleware.py#L320-L339)）→ 查不到 → 403「无权限执行 create」 |
| 配置层 | `.env.shared-infra` 已置三 REAL 与映射；`.env*` 不入库 | 需运维人工同步多环境；编排器为长驻进程，Env 启动即固化（改脚本须重启） |

主体层是**当前最关键的新发现**：即使码值桥接正确（D1 已验证租户通过），仍会被 DPS RBAC 拒绝。

---

## 3. 方案总览

| 编号 | 方案 | 仓库 | 目标 | 优先级 |
| --- | --- | --- | --- | --- |
| A1 | 只读语义路径判据 | OpenRAG | 检索类 POST 不再被判写 | P0 |
| A2 | 映射完整性守卫 | OpenLLM | 未知码不再静默透传 | P1 |
| B1 | 统一码值事实源 | OpenBase + OpenLLM | 两仓映射同源、可校验 | P0 |
| B2 | DPS 外部主体映射播种 | DPS（+ OpenBase 出站键） | 让 `X-User-ID` 命中 DPS 角色 | P0 |
| B3 | 配置一致性门禁 | 三仓 | 启动期自检 + 显式失败 | P1 |

实施顺序：**B1 → B2 → A1 → A2 → B3**（B2 是当前最硬阻断，A1 独立可并行）。

---

## 4. 方案 A1：OpenRAG 只读语义路径判据

### 4.1 设计原则

- **不放宽写保护**：只对「语义上是读、只是因为协议用了 POST」的端点做语义覆盖；
- **精确匹配**：只接受路径后缀精确模式，禁止裸前缀通配（避免 `POST /collections` 被误放）；
- **可配置**：默认内置最小集合，允许部署侧覆盖；
- **可审计**：每次覆盖必须留结构化日志，字段可检索；
- **反例自证**：真正的写端点必须仍然 403。

### 4.2 配置项（OpenRAG）

在 `openrag/config/settings.py` 的 `IdentityTrustConfig` 增加：

```python
m2_readonly_post_paths: list[str] = Field(
    default_factory=lambda: [
        "*/query/retrieve",     # 纯检索（S3-T3）
        "*/query/search",       # 检索别名（若启用）
        "*/retrieve/federated", # 联邦检索
    ],
    description="M2 下按读语义处理的 POST 路径模式（精确后缀，禁止前缀通配）",
)
```

环境变量：`OPENRAG_M2_READONLY_POST_PATHS`（JSON 数组，与其他 `list[str]` 字段一致）。

### 4.3 判定改造（`role_gate.py`）

新增纯函数，便于单测：

```python
def is_readonly_semantic(method: str, path: str, patterns: Sequence[str]) -> bool:
    """POST 类方法命中只读语义模式时返回 True（仅用于匿名/角色档位判定）。"""
    if method.upper() not in WRITE_METHODS:
        return False
    return any(path.endswith(p) for p in patterns if p.startswith("*") and len(p) > 1)
```

`dispatch` 中匿名分支调整为：

```python
if subject_type not in _SUBJECT_TYPES:
    if method in WRITE_METHODS and not is_readonly_semantic(
        method, path, self._config.m2_readonly_post_paths
    ):
        ... 原 403 ...
    if is_readonly_semantic(method, path, self._config.m2_readonly_post_paths):
        logger.info("m2_readonly_semantic_override", path=path, method=method)
    return await call_next(request)
```

受信主体分支同样先把 `min_tier_for_method(method)` 降为 `readonly`（若命中只读语义），避免只读账号被挡。

### 4.4 改动清单

| 文件 | 改动 |
| --- | --- |
| `src/openrag/config/settings.py` | 新增 `m2_readonly_post_paths` 字段 |
| `src/openrag/api/middleware/role_gate.py` | 新增 `is_readonly_semantic`；匿名/受信两分支判定接入；新增结构化日志 |
| `tests/unit/test_m2_readonly_semantic.py` | 新增 4 例（见 4.5） |
| `docs/design/**`（OpenRAG 侧） | 契约说明补「只读语义覆盖」段落 |

### 4.5 TDD 用例（先 RED 后 GREEN）

| 编号 | 场景 | 期望 |
| --- | --- | --- |
| A1-T1 | 匿名 key + `POST .../query/retrieve` | 放行（非 403） |
| A1-T2 | 匿名 key + `POST /api/v1/collections`（真写） | **403 PERM_SERVICE_KEY_WRITE_DENIED**（反例自证） |
| A1-T3 | 受信主体 readonly 角色 + 检索 POST | 放行 |
| A1-T4 | 受信主体 readonly 角色 + 写 POST | **403 PERM_FORBIDDEN（tier_insufficient）** |
| A1-T5 | 自定义 `OPENRAG_M2_READONLY_POST_PATHS=[]` | 回到严格方法判据（零破坏回滚） |

### 4.6 风险与回滚

- 风险：模式写宽导致误放写端点。缓解：仅后缀精确匹配 + 反例自证用例 + 默认集合最小化。
- 回滚：配置置空数组即回到原行为（无需回滚代码）。

---

## 5. 方案 B：DPS 码值桥接打通

### 5.1 B1 统一码值事实源

**事实源**：`openbase.tenants.code`（唯一）；DPS 目标空间为 `dps-org-001 / dps-tenant-001`（库中已 active）。

OpenBase 侧：

- 以登记式 `dps_code_map` 为**唯一入口**（旧 `dps_org_map/dps_tenant_map` 仅兼容读取）；
- 登记内容需覆盖三种入站形态：`tenant-1`、`org-1`、OpenBase 内部 UUID。

示意（`OPENBASE_DPS_CODE_MAP`）：

```json
{
  "schema_version": 1,
  "entries": [
    {"tenant_code": "tenant-1", "org_code": "org-1", "dps_org_code": "dps-org-001", "dps_tenant_code": "dps-tenant-001"},
    {"tenant_code": "tenant-2", "org_code": "org-1", "dps_org_code": "dps-org-001", "dps_tenant_code": "dps-tenant-002"}
  ]
}
```

OpenLLM 侧：`DPS_ORG_CODE_MAP / DPS_TENANT_CODE_MAP` 由同一份登记表**生成**（脚本产出，禁止手抄），并在启动期做一致性校验（见 B3）。

> 现状缺口：OpenLLM 映射键为 `org-1/tenant-1`，但实际入站可能是 UUID 或空值 → 映射 miss 后原样透传。B1 要求把 UUID 键一并登记。

### 5.2 B2 DPS 外部主体映射（当前最硬阻断）

**问题**：DPS 按 `X-User-ID` 原值查 `platform.user_roles.user_id`；OpenBase 传 `admin`，而库中键为 `1`。

**方案（推荐）**：在 DPS 侧建立「外部主体 → 本地用户」映射，沿用既有 `subject_source='openbase'` 形态（库中已有 `probe-user` 先例），不改权限引擎逻辑。

幂等播种（示意，主键/唯一约束按实际执行前核对）：

```sql
-- 1) 确认本地用户
--    platform.users: id=1, username='admin'
-- 2) 建立外部主体绑定（示例：OpenBase 用户 admin + 租户 tenant-1）
INSERT INTO platform.user_roles (user_id, role_id, active, subject_source)
VALUES ('tenant-1_admin', 1, 1, 'openbase')          -- 1 = super_admin
ON CONFLICT (user_id, role_id)
DO UPDATE SET active = 1, subject_source = 'openbase';
```

OpenBase/OpenLLM 侧配合：出站 `X-User-ID` 统一为**受信主体键**（建议 `{tenant_code}_{username}` 或直接 OpenBase 数字 ID，二选一后全链路固定），并在协议头规范中登记该键格式。

**备选（不推荐）**：把 DPS 的 `user_roles.user_id` 直接补一条 `'admin'`——会与「外部主体键空间」混用，后续多租户同名用户冲突。

### 5.3 B3 配置一致性门禁

| 检查 | 位置 | 失败行为 |
| --- | --- | --- |
| `dps_code_map` entries 与 `DPS_*_CODE_MAP` 逐项一致 | OpenLLM 启动期自检 | 非生产 WARN；生产拒绝启动（可配置） |
| 映射 miss（入站码未登记） | OpenLLM `apply_dps_code_map` | WARN + 审计字段 `code_map_miss`，**不静默透传** |
| DPS 主体查不到绑定 | DPS permission middleware | 保持 403，但 detail 增加 `subject_bound=false`（便于定位，不改变判定） |

### 5.4 改动清单

| 仓库 | 文件 | 改动 |
| --- | --- | --- |
| OpenBase | `openbase/modules/protocol_headers/dps_code_map.py` | 增加 UUID 键解析与 miss 告警（不改优先级） |
| OpenBase | `openbase/settings.py` | `dps_code_map` 校验增强（entries 必填字段） |
| OpenLLM | `app/edgerouter/adapters/profile.py` | `apply_dps_code_map` 增加 miss 日志与 `code_map_miss` 审计字段 |
| OpenLLM | `app/core/startup_alignment.py` | 新增映射一致性自检（与既有模型注册表自检同范式） |
| DPS | `scripts/seed-*.py`（幂等播种脚本） | 新增外部主体绑定播种 |
| DPS | `src/middleware/permission_middleware.py` | 403 detail 增加 `subject_bound`（仅可观测性） |
| 三仓 | `docs/**` | 协议头规范补充「外部主体键格式」与码值登记规则 |

### 5.5 验证判据（可复现）

| 编号 | 请求头 | 期望 |
| --- | --- | --- |
| B-T1 | `X-Org-ID=org-1` + `X-Tenant-ID=tenant-1` | 桥接后 **不再出现「组织不存在」** |
| B-T2 | `X-Org-ID=dps-org-001` + `X-Tenant-ID=dps-tenant-001` + 已绑定主体 | `POST /api/v2/portrait/calculate` **非 403 权限错误**（200 或业务 4xx） |
| B-T3 | 未登记码（如 `org-9`） | 明确告警 `code_map_miss`，不静默透传 |
| B-T4 | 未绑定主体 | 403 且 detail 含 `subject_bound=false` |
| B-T5 | 端到端：OpenBase → OpenLLM 显式三路 | `executed=["memory","rag","profile","llm"]`、`degraded=[]` |

> 说明：B-T5 的 `profile` 段取决于编排是否启用写回触发；至少要求回写队列无 `target=profile` 失败记录。

---

## 6. 实施顺序与依赖

```text
B1（码值同源 + 生成脚本）
  └─> B2（DPS 主体绑定播种）  ──> B-T2 通过
        └─> A1（OpenRAG 只读语义）──> E1/E2 消除
              └─> A2（映射 miss 守卫）
                    └─> B3（配置一致性门禁）
                          └─> B-T5 端到端复测 ──> 提交 L2-2 终验
```

- A1 与 B1/B2 无代码依赖，可并行开发；
- 所有改动遵循 TDD（先 RED）；
- 每仓改动需独立提交并推送三远程，提交信息引用本方案编号。

---

## 7. 验收标准

| 编号 | 验收项 | 判定方法 |
| --- | --- | --- |
| AC-1 | 检索不再被判写 | 匿名 key `POST .../query/retrieve` 返回非 403；同时 `POST /collections` 仍 403 |
| AC-2 | 租户码值桥接生效 | B-T1 无「组织不存在」 |
| AC-3 | DPS 主体可达 | B-T2 非 403 权限错误 |
| AC-4 | 映射 miss 可见 | B-T3 日志含 `code_map_miss` |
| AC-5 | 端到端三路 | B-T5 达成，回写无 profile 失败 |
| AC-6 | 回归不劣化 | 三仓既有全量用例通过；新增用例覆盖率 ≥90%（OpenBase 标准） |

---

## 8. 回归范围与回滚

**回归范围**

- OpenRAG：identity 中间件全部用例、collections/query 路由契约用例；
- OpenLLM：profile adapter、writeback queue、identity outbound 用例；
- DPS：tenant middleware、permission middleware 用例；
- OpenBase：dps_code_map、dps_proxy、protocol_headers 用例。

**回滚**

| 层 | 回滚动作 | 影响 |
| --- | --- | --- |
| A1 | `OPENRAG_M2_READONLY_POST_PATHS=[]` | 回到严格方法判据 |
| B1 | 恢复上一版 `dps_code_map` 配置 | 码值映射回到旧口径 |
| B2 | `UPDATE user_roles SET active=0 WHERE subject_source='openbase' AND user_id=...` | 撤销外部主体绑定 |
| B3 | 关闭一致性自检开关（非生产） | 仅告警不回退功能 |

---

## 9. 未决事项与需裁定项

| 编号 | 事项 | 需谁裁定 | 建议 |
| --- | --- | --- | --- |
| Q1 | 外部主体键格式：`{tenant}_{username}` 还是 OpenBase 数字 `user_id` | 架构组 | 推荐 `{tenant_code}_{user_id}`，避免同名冲突且可直接关联 `tenants.code` |
| Q2 | 只读语义白名单是否允许部署侧追加 | 安全负责人 | 允许，但生产变更需走变更单 |
| Q3 | B3 一致性自检在生产的失败行为 | 运维 + 架构 | 生产拒绝启动（与既有 5 组门禁同范式） |
| Q4 | OpenRAG 是否长期提供 GET 检索等价端点 | OpenRAG 负责人 | 建议后续版本提供，A1 作为过渡 |

---

## 10. 修订历史

| 版本 | 日期 | 修订人 | 说明 |
| --- | --- | --- | --- |
| v1.0.0 | 2026-10-17 | OpenBase 架构组 | 首版：基于 2026-10-17 全栈实跑证据（E1~E3、D1~D4）编制，覆盖 A1/A2/B1/B2/B3 五项改造与验收判据 |
