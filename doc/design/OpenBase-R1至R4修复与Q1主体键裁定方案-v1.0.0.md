# OpenBase — R1~R4 修复方案与 Q1 主体键裁定建议

| 项目 | 内容 |
| --- | --- |
| 文档版本 | v1.0.0 |
| 文档状态 | [Draft]（Q1 为待裁定项） |
| 适用环境 | Dev / Test；生产需另行编排窗口 |
| 编制日期 | 2026-10-17 |
| 编制人 | OpenBase 架构组 |
| 关联文档 | 《OpenBase-OpenRAG写判据与DPS码值桥接修复方案-v1.1.0》§10.5 未闭环项 |
| 前置结论 | A1/A2/B1/B2 已实施完毕：检索 403 与 DPS 码值/权限 403 均已消除 |

---

## 1. 问题清单与实测证据

| 编号 | 问题 | 实测证据（2026-10-17） |
| --- | --- | --- |
| R1 | 经 OpenBase 的 B 通道 rag 仍降级（404） | OpenLLM 出站 `POST /api/v1/collections/{id}/query/retrieve → 404`；同请求直连 OpenLLM（`X-Tenant-ID=tenant-1`）时 `executed=rag,llm`、`degraded` 为空 |
| R2 | 回写 profile 404「人员不存在」 | `PUT /api/v2/portrait/admin → 404`；`platform.profile` 共 18 条，`person_id` 为 `'tenant-1_179fc89c-…'`、`'49'`、`'50'` 等，**无 `admin`** |
| R3 | 生产配置未下发 | `.env.shared-infra` 被 `.gitignore`（`.env.*`）排除；`OPENBASE_DPS_CODE_MAP` / UUID 别名 / 两仓互译表仅存在于本机 |
| R4 | OpenRAG 本地回归 1 例失败 | `test_s3_t9_5_role_gate_inactive_under_m1` 失败；根因为本地 `.env` 含 `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES=["openbase-rag-proxy"]`，使 M1 基线用例进入 M2 分支 |

关键数据事实：

- `openbase.users`：`admin(id=1)`、`viewer(4)`、`oidc-admin(5)` 等，**`tenant_id` 全部为 NULL**；
- `openbase.tenants`：`tenant-1(id=1)`、`tenant-2(id=2)` 均 active；
- `openbase.users` **无 UUID 列**（主键为 BIGINT 自增）；
- `platform.user_roles` 既有键：`'1'`（本地）、`'dps-tenant-001_admin1_001'`、`'tenant-1_<uuid>'`、`'probe-user'`；
- `platform.profile` 既有 `person_id`：`'tenant-1_<uuid>'`、`'49'`、`'50'` …（**复合键形态已有先例**）。

---

## 2. R1：登录主体租户绑定

### 2.1 根因

登录签发链路（[auth/__init__.py](file:///D:/Trae%20CN/myproject/Dev/OpenBase/openbase/modules/auth/__init__.py#L259-L282)）：

```text
users.tenant_id (NULL)
  → resolve_tenant_code(None) → tenant_code=None
  → JWT.org_id=None
  → llm-proxy 出站缺 X-Tenant-ID
  → OpenLLM 按保留码 default 处理
  → OpenRAG 集合在 tenant-1 域 → 404（域不匹配）
```

即：**不是检索链路故障，而是主体缺少租户声明**。

### 2.2 修复设计（数据 + 代码加固）

**步骤 1（必做，数据层）**：为需要参与 B 通道的账号绑定租户。

```sql
-- 幂等：仅当未绑定且用户启用
UPDATE openbase.users
   SET tenant_id = (SELECT id FROM openbase.tenants WHERE code = 'tenant-1')
 WHERE username = 'admin'
   AND tenant_id IS NULL
   AND status = 1;
```

**步骤 2（建议，代码层）**：登录期租户兜底/门禁二选一，由配置控制。

在 `openbase/settings.py` 新增：

```python
default_tenant_code: str = ""          # 空 = 不启用兜底
require_tenant_on_login: bool = False  # 生产建议 True（fail-closed）
```

在登录签发前（`auth/__init__.py` 的 `resolve_tenant_code` 之后）插入：

```text
if tenant_code 为空:
    if settings.default_tenant_code:
        使用 default_tenant_code，留痕 WARN（tenant_fallback=default_config）
    elif settings.require_tenant_on_login and env == production:
        拒绝登录（AUTH_FORBIDDEN，detail.reason=tenant_unbound）
```

- 非生产：默认 `require_tenant_on_login=false`，只留痕不阻断（保护既有联调）；
- 生产：建议置真，避免「静默落到保留码」导致跨域 404/403。

### 2.3 影响面与风险

| 项 | 说明 |
| --- | --- |
| 已签发 Token | 旧 JWT 的 `org_id=null`，需重新登录或等待过期（无刷新即失效） |
| 缓存 | `invalidate_principal_cache` 需在租户变更后调用（用户更新接口已有调用） |
| OpenMemory | 出站租户码变为 `tenant-1`（已登记组织策略，见编排器 `OPENMEMORY_RBAC__ORG_POLICIES`） |
| 风险 | 兜底配置若误置，会把未分配用户静默归入默认租户 → 生产必须 fail-closed |

### 2.4 验收判据

| 编号 | 判据 |
| --- | --- |
| R1-T1 | 登录响应 JWT 解出 `org_id=tenant-1` |
| R1-T2 | 经 OpenBase 显式 `memory+rag+llm`：`executed=memory,rag,llm`、`degraded=[]` |
| R1-T3 | 未绑定用户 + 生产 `require_tenant_on_login=true` → 登录 403 且 `reason=tenant_unbound` |
| R1-T4 | 未绑定用户 + 非生产 → 登录成功并留痕 `tenant_fallback` |

---

## 3. R2：DPS 画像初始化与 404 语义

### 3.1 根因

- DPS **没有**「创建 profile」的公网端点（仅 `POST /portrait/calculate`、`PUT /portrait/{person_id}`、`POST /batch/import`）；
- `PUT /portrait/{person_id}` 要求记录已存在（[storage_engine.py](file:///D:/Trae%20CN/myproject/Dev/DPS/src/engines/storage_engine.py#L173-L185)）；
- OpenLLM 的 `person_id` 规约（[profile.py](file:///D:/Trae%20CN/myproject/Dev/OpenLLM/backend/app/edgerouter/adapters/profile.py#L287-L302)）优先取 `external_user_id`（即 `X-User-ID=admin`）；
- 库中无 `person_id='admin'` → 404 → 回写队列重试 3 次后失败。

### 3.2 修复设计（播种 + 语义收敛，不新增 DPS 写端点）

**步骤 1（必做，数据层）**：幂等播种 profile。

```sql
INSERT INTO platform.profile
  (id, person_id, org_id, tenant_id, name, status, version, created_at, updated_at)
VALUES
  (gen_random_uuid(),
   :person_id,                                  -- 与 Q1 裁定键一致（见 §7）
   '10000000-0000-0000-0000-000000000001',      -- dps-org-001
   '20000000-0000-0000-0000-000000000001',      -- dps-tenant-001
   'admin', 'active', 1, now(), now())
ON CONFLICT (person_id, tenant_id) DO NOTHING;   -- 以实际唯一约束为准
```

**步骤 2（必做，代码层）**：区分「人员不存在」与「链路故障」。

在 OpenLLM `profile.py` 的写路径对 404 单独处理：

```text
if 上游 404 且 detail 含「人员不存在」:
    记 WARN（profile_absent, person_id, tenant）
    返回 skipped=True（不进入重试队列）
else:
    维持既有重试/降级语义
```

同步调整 `WritebackQueue`：`skipped=True` 不计入失败、不触发指数退避。

**步骤 3（可选，运维层）**：账号开通联动。
在 OpenBase 创建用户/分配租户后，调用 DPS 播种（或由同步任务批量补齐），确保「有账号即有画像占位」。

### 3.3 影响面与风险

| 项 | 说明 |
| --- | --- |
| 优点 | 不新增 DPS 公网写端点（攻击面不变）；播种幂等可重放 |
| 风险 | 若 Q1 未裁定，`person_id` 可能与最终主体键不一致 → 建议 R2 在 Q1 裁定后落地 |
| 观测 | 新增 `profile_absent` 指标可区分「数据缺失」与「服务故障」 |

### 3.4 验收判据

| 编号 | 判据 |
| --- | --- |
| R2-T1 | 播种后 `PUT /api/v2/portrait/{person_id}` 返回 200 |
| R2-T2 | 未播种 person 的回写日志出现 `profile_absent`，且**不再重试 3 次** |
| R2-T3 | `routing_trace.segment_tokens.profile > 0`（画像段有内容注入） |

---

## 4. R3：生产配置下发与校验门禁

### 4.1 配置清单（三处必须一致）

| 配置项 | 归属 | 取值来源 | 落点 |
| --- | --- | --- | --- |
| `OPENBASE_DPS_CODE_MAP` | OpenBase | DPS `platform.organization/tenant` UUID | 生产 `.env`（不入库） |
| `OPENBASE_DPS_ORG_MAP` / `_TENANT_MAP` | OpenBase | UUID 别名（内部 org UUID → DPS UUID） | 生产 `.env` |
| `DPS_ORG_CODE_MAP` / `DPS_TENANT_CODE_MAP` | OpenLLM | 由 `scripts/gen_dps_code_map.py` **生成** | 生产 `.env` |
| `SUBJECT_USERNAME_RESOLVE_ENABLED` | DPS | 过渡期 `true`；Q1 落地并完成主体键迁移后置 `false` | 生产 `.env` |
| `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES` | OpenRAG | 含 `openbase-orchestrator` | 生产 `.env` |

### 4.2 校验脚本（新增）

`scripts/verify_dps_code_map.py`，三项校验，任一失败返回非 0：

1. **结构**：登记式 JSON 可解析、entries 必填字段齐全、无同码冲突；
2. **一致性**：`OPENBASE_DPS_CODE_MAP` 生成的映射 == OpenLLM `DPS_*_CODE_MAP`（逐键比对）；
3. **存在性**：连接共享 PG 校验每个 `dps_org_id/dps_tenant_id` 在 `platform.organization/tenant` 中 active 且归属正确。

接入方式：

- 发布前：`python scripts/verify_dps_code_map.py --strict`
- 启动期：OpenLLM 已有 `detect_dps_code_map_alerts`（B3）做结构/键集合告警，**生产建议升级为 fail-fast**（可配置）。

### 4.3 发布检查单增补

在《主备双通道生产上线必办事项清单》G1/G2 项下补充：

- [ ] 生产 `.env` 已下发 §4.1 五项配置（运维签字）
- [ ] `verify_dps_code_map.py --strict` 通过（附输出）
- [ ] OpenLLM 启动日志无 `启动自检｜DPS` 告警
- [ ] 抽样一次 `POST /openllm/v1/chat`（explicit rag）确认 `degraded` 为空

### 4.4 验收判据

| 编号 | 判据 |
| --- | --- |
| R3-T1 | 校验脚本在缺失/错配配置时返回非 0 并指出具体键 |
| R3-T2 | 配置齐全时脚本返回 0，且 OpenLLM 启动无 DPS 告警 |
| R3-T3 | 发布检查单四项全部勾选并留存输出 |

---

## 5. R4：OpenRAG 测试基线环境隔离

### 5.1 根因

`tests/conftest.py` 已用同一范式隔离 `OPENRAG_API_SERVICE_API_KEY`（[conftest.py](file:///D:/Trae%20CN/myproject/Dev/OpenRAG/tests/conftest.py#L21-L24)），但未隔离 `OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES`：

- `.env` 中的该值使 `IdentityTrustConfig()` 读到 M2 配置；
- `test_s3_t9_5_role_gate_inactive_under_m1` 期望 M1 放行 → 实际走 M2 匿名写拒绝。

### 5.2 修复设计

在 `tests/conftest.py` 的既有隔离段追加：

```python
# 身份信任基线隔离：M2 用例经 _m2_config() 显式构造，不依赖环境；
# 此处清空可保证 M1 基线用例（RoleGate 不激活）稳定。
os.environ["OPENRAG_IDENTITY_TRUSTED_PROXY_SOURCES"] = ""
```

> 语义确认：该清空只影响**测试进程**；所有 M2 用例均通过 `IdentityTrustConfig(trusted_proxy_sources=[...])` 显式传参（已实测 53 例中 M2 用例全部通过）。

### 5.3 验收判据

| 编号 | 判据 |
| --- | --- |
| R4-T1 | 在含 `.env` 的本机环境跑 `test_s3_t9_role_mapping.py` 全通过 |
| R4-T2 | M2 相关用例（`test_s3_t10`、`test_s3_b2`）仍全通过 |
| R4-T3 | 新增 1 条基线断言：`IdentityTrustConfig().trust_mode == "m1"`（防回归） |

---

## 6. 实施顺序与依赖

```text
Q1 裁定（主体键格式）
  ├─> R2（profile 播种键依赖 Q1）
  └─> R1（租户绑定，独立可先行）
        └─> R3（配置下发 + 校验门禁）
              └─> R4（测试基线，独立可并行）
```

- R1 / R4 与 Q1 无关，可立即实施；
- R2 建议在 Q1 裁定后落地，避免 `person_id` 二次迁移；
- R3 依赖 R1/R2 的最终配置形态。

---

## 7. Q1 裁定建议：外部主体键格式

### 7.1 候选对比

| 方案 | 格式 | 优点 | 缺点 | 迁移影响 |
| --- | --- | --- | --- | --- |
| **A（推荐）** | `{tenant_code}_{user_id}`，如 `tenant-1_1`，经**专用头 `X-Subject-ID`** 传输 | 稳定（id 不可变）；自带租户；与 DPS 既有 `tenant-1_<uuid>` 同构；不改 `X-User-ID`，OpenMemory/OpenRAG 零迁移 | 需新增一个协议头（三仓各 1 处装配/解析） | 无（缺省回退） |
| B | `{tenant_code}_{username}`，如 `tenant-1_admin` | 可读 | username 可改、可重名 → 不适合做主键 | 需迁移历史绑定 |
| C | 纯 `user_id`（`1`） | 最简 | 无租户语义；与 DPS 现有数字 `person_id`（49/50…）冲突 | 高风险 |
| D | 直接覆盖 `X-User-ID` 为复合键 | 不新增头 | OpenMemory 记忆按 user_id 归属 → 历史记忆不可见，需数据迁移 | 高 |

### 7.2 推荐：方案 A

**裁定建议：外部主体键 = `{tenant_code}_{user_id}`，经 `X-Subject-ID` 传输；`X-User-ID` 保持 username 语义不变。**

理由（按优先级）：

1. **稳定性**：`users.id` 不可变，`username` 可改；键一旦写入 DPS 绑定与画像，就不可轻易变更；
2. **租户隔离**：键自带租户码，与 OpenBase 唯一事实源 `tenants.code` 直接对齐；
3. **既有形态兼容**：DPS 库中 `user_roles.user_id` 与 `profile.person_id` 已存在 `tenant-1_<uuid>`，方案 A 仅把 UUID 换成数字 id，属同构演进；
4. **零迁移**：不改变 `X-User-ID`，OpenMemory 的记忆归属与 OpenRAG 的审计主体不受影响；
5. **可灰度**：未提供 `X-Subject-ID` 时，DPS 复用已实现的 username 回退（B2），旧客户端零感知；
6. **可退役**：过渡期结束后将 `SUBJECT_USERNAME_RESOLVE_ENABLED` 置 `false`，收敛为单一路径。

### 7.3 落地要点（若采纳 A）

| 层 | 改动 | 说明 |
| --- | --- | --- |
| 协议头规范 | 新增 `X-Subject-ID`（受信来源下生效，长度 ≤128） | 与四头同批次校验 |
| OpenBase | `protocol_headers/constants.py` + `inject.build_outbound_headers` 装配 `{tenant_code}_{user_id}` | 仅受信出站注入 |
| OpenLLM | `identity/outbound.py` 透传；`profile._resolve_real_person_id` 优先取 `X-Subject-ID` | 与 `external_user_id` 并存，前者优先 |
| DPS | `permission_middleware` 主体解析优先 `X-Subject-ID` | 已有 username 回退保留为兜底 |
| 数据 | `user_roles.user_id` / `profile.person_id` 统一为复合键（幂等迁移脚本） | 支持双写过渡 |

### 7.4 若裁定不采纳 A

- 选 B：需先冻结 username 不可修改，并在用户改名流程中禁止（不推荐）；
- 选 C/D：需对 OpenMemory 记忆与 DPS 画像做数据迁移，且多租户隔离语义弱化（不建议）。

---

## 8. 回滚方案

| 项 | 回滚动作 | 影响 |
| --- | --- | --- |
| R1 数据 | `UPDATE openbase.users SET tenant_id=NULL WHERE username='admin'` | 回到无租户（rag 404 复现） |
| R1 代码 | `require_tenant_on_login=false` + `default_tenant_code=""` | 回到只留痕 |
| R2 播种 | `DELETE FROM platform.profile WHERE person_id=:key AND tenant_id=:tid` | 回写恢复 404（不重试语义保留） |
| R3 脚本 | 不影响运行态（纯校验） | 无 |
| R4 | 删除 conftest 新增行 | 恢复环境依赖（仅测试） |
| Q1 | `SUBJECT_USERNAME_RESOLVE_ENABLED=true` 并停止注入 `X-Subject-ID` | 回到 username 回退路径 |

---

## 9. 验收汇总

| 编号 | 验收项 | 判据 |
| --- | --- | --- |
| AC-R1 | 租户链路贯通 | R1-T1~T4 |
| AC-R2 | 画像可写 | R2-T1~T3 |
| AC-R3 | 配置可核验 | R3-T1~T3 |
| AC-R4 | 测试基线稳定 | R4-T1~T3 |
| AC-Q1 | 主体键唯一且可回退 | 同一用户跨系统键一致；关闭注入后回退路径可用 |

---

## 10. 需裁定事项

| 编号 | 事项 | 建议 | 影响 |
| --- | --- | --- | --- |
| **Q1** | 外部主体键格式与传输方式 | **方案 A：`{tenant_code}_{user_id}` + `X-Subject-ID`** | 决定 R2 `person_id` 与 DPS 绑定键 |
| Q5 | 生产是否强制 `require_tenant_on_login=true` | 建议是（fail-closed） | 未绑定用户将被拒绝登录 |
| Q6 | `X-Subject-ID` 是否纳入受信头强校验集合 | 建议是（与四头同规则） | 影响协议头规范版本 |
| Q7 | username 回退的退役时限 | 建议 2 个版本内 | 影响 Q1 收敛节奏 |

---

## 11. 修订历史

| 版本 | 日期 | 修订人 | 说明 |
| --- | --- | --- | --- |
| v1.0.0 | 2026-10-17 | OpenBase 架构组 | 首版：基于 A1/A2/B1/B2 实施后的实测证据（R1~R4）编制；Q1 给出四方案对比与推荐（A：`{tenant_code}_{user_id}` + `X-Subject-ID`） |
