# OpenBase-统一身份与主备双通道贯通总体方案-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-UNIFY-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Draft] |
| 日期 | 2026-09-06 |
| 作者 | AD（跨项目分析） |
| 版本主题 | 三条核心目标的架构定案：① 统一四维用户全生命周期管理；② OpenBase→基础功能系统直连 + 经 OpenLLM 主备双通道全面贯通；③ 前端/智能体统一经 OpenBase 与基础系统交互，全部贯通 |
| 适用范围 | OpenBase（统一入口） / OpenLLM / OpenRAG / OpenMemory / DPS / OIDC / 统一前端 / 智能体（MCP/Agent） |
| 前置事实 | 联调复盘 v1.0.0（de8c781）、治理评审 v1.6.0、任务书 v2.6.0、need_star 方案 v0.11.0、P2-2 立项方案 v1.0.0 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-06 | AD（跨项目分析） | 初始版本：三条核心目标术语定案、目标架构、现状-差距矩阵、任务分解（U1~U5）、与在途立项联动、验收 |

---

## 1. 术语定案（三条核心目标拆解）

为避免歧义，本方案对三条目标给出体系内定义（与既有文档 R-375/四头/M3/Q2/Q3 术语对齐；如与业务理解不一致，评审时以本表为修订入口）：

| 术语 | 定义 |
|------|------|
| 四维用户 | 平台用户的四维身份模型 = **User（用户身份）+ Tenant（租户/组织归属，唯一键 tenants.code）+ Org（org 头，Q2 退役为兼容别名）+ Role（角色/权限集合）**；另含外部身份维（external_user_id 承载，Q4/M3）。跨系统时各系统只消费同一 JWT/四头，不再各建身份 |
| 全生命周期 | 预置/注册 → 认证（本地/OIDC）→ 授权与角色绑定 → 数据归属（org/tenant 隔离键）→ 活跃/停用 → 注销/删除；任一状态的变更需**级联同步**到全部基础系统并全程可审计 |
| 基础功能系统 | OpenLLM（对话/模型编排）、OpenRAG（知识）、OpenMemory（记忆）、DPS（画像）；OIDC 为身份源而非功能系统 |
| 通道 A（直连） | 前端/智能体 → OpenBase → 各基础系统：现形态 llm-proxy/rag-proxy/memory-proxy/dps-proxy（JWT 门禁 + 身份头/密钥注入 + 探活降级） |
| 通道 B（经 OpenLLM） | 前端/智能体 → OpenBase(llm-proxy) → OpenLLM 编排（executor 组件 memory/rag/profile + 真实模式 REAL 开关）→ 各基础系统；OpenLLM 是汇聚编排中枢而非替代网关 |
| 主备 | 通道 A 为管理面与原子能力默认主通道；通道 B 为**对话/编排类复合能力**默认主通道（A 亦可达该子集）。"主备"= 对**同一请求语义**，A/B 均可完成且可切换（B 故障回落 A 单组件，A 故障经 B 编排补齐能力），降级不丢核心能力 |
| 统一贯通 | 前端与智能体（含 Agent/MCP）**只**面向 OpenBase（唯一认证、唯一鉴权、唯一审计入口）；基础系统不接受来自 OpenBase 之外的前端/智能体直连（服务级内部受信通道除外，如 OpenLLM 自研探活） |

## 2. 目标架构（收敛形态）

```
前端(5173) ──┐
智能体/MCP/Agent ──┼──▶ OpenBase（统一认证/鉴权/审计/路由/生命周期）
             └───────────┘
  OpenBase ──通道A(proxy 族 直连)────────▶ OpenLLM(8001) / OpenRAG(8010) / OpenMemory(8020) / DPS(8030)
  OpenBase ──通道B(llm-proxy)──▶ OpenLLM 编排(组件 memory/rag/profile, REAL 真实模式) ──▶ OpenRAG / OpenMemory / DPS
  OpenBase ◀── 身份生命周期同步总线（事件驱动：四维变更 → 各系统归属/绑定/禁用级联）── 各基础系统
  OIDC(8090) ──▶ OpenBase（外部身份源，JIT 建号）
```

- 数据面：共享 PG（openbase/platform schema）+ Redis 为共享真相；各系统本地写盘仅存非身份业务态（并受管可写路径）。
- 身份面：**OpenBase 是四维用户的唯一控制面**（CRUD/生命周期/角色/绑定），基础系统不再自建用户注册（DPS user_roles 绑定、OpenMemory 归属、画像 person 生命周期改由同步总线驱动）。

## 3. 现状-差距矩阵（基于已实证事实）

### 3.1 目标①：统一四维用户全生命周期管理

| 维度 | 现状（实证） | 差距 |
|------|-------------|------|
| 用户 CRUD | OpenBase users 模块（R-375）+ admin/viewer 种子；tenant 管理（system/tenants）；roles/permissions RBAC | 四维（user/tenant/org/role+external）无**统一身份对象**视图与生命周期状态机（草稿/启用/停用/注销） |
| 认证 | 本地密码 + OIDC（JIT 建号/绑定） | OIDC JIT 用户与本地用户体系并存、无去重与生命周期联动（停用/注销后 IdP 再登是否拒？未测） |
| 跨系统同步 | 无级联：DPS user_roles 靠种子/manual；画像 person_id 命名 `{tenant_code}_{user_ref}_{NN}` 手工维护；OpenMemory/OpenRAG 归属可选；OpenLLM 外部身份仅透传 | **身份变更不级联**：OpenBase 停用/删除用户后，DPS 绑定、会话/记忆归属、画像对象仍有效 → 越权残留 |
| 角色/权限模型 | 各系统独立：OpenBase admin/viewer/org_admin；DPS super_admin/org_admin/user；OpenMemory 自有矩阵 | 无统一角色语义与映射表（同义角色多处维护）；fail-closed 未全（P2-2 在途） |
| 外部/业务用户 | external_user_id（OpenLLM 可信源解析）；画像对象=独立 person_id | 登录用户与业务画像对象未显式分层建模（复盘根因 4.3）：无"对象注册/绑定到用户"服务 |

### 3.2 目标②：主备双通道全面贯通

| 维度 | 现状（实证） | 差距 |
|------|-------------|------|
| 通道 A | OpenBase proxy 族直连四系统：JWT 门禁、身份头/密钥注入、探活/降级（dps 探活已 real 化；DPS 画像族 10 端点 200；OpenLLM /models 200） | A 已贯通**管理面+原子面**；未开放面（DPS risk-assess/streams 等）未开放属契约清单 |
| 通道 B | OpenLLM executor 组件 memory/rag/profile；画像对话内注入 REAL 模式通（profile_source=dps）；OpenMemory/OpenRAG REAL 已实现缺省关 | B 仅覆盖 **chat/编排子集**；OpenMemory/OpenRAG REAL 未启用（OPENLLM_OPENMEMORY_REAL/OPENRAG_REAL=false）；A/B 端点能力矩阵无对账 |
| 主备切换 | llm-proxy 上游探活/降级；DPS client 组件级降级；前端路由不动 | **无显式主备策略**：B 故障回落 A 的哪个组件面、A 故障时 B 编排补齐范围、切回条件均未定义；双通道健康/降级未统一上报 |
| 身份一致性 | A：llm-proxy 注入 X-User-ID/X-Org-ID(有值才带)+X-Proxy-Source；dps-proxy 四头映射 code；B：OpenLLM external→出站 REAL_* 兜底+请求级覆盖 | A/B 出站到同一系统（如 DPS）的头值需**等价**（同一请求经 A 或经 B 到达 DPS 的 user/org/tenant 相同）——需一致性矩阵与回归用例 |

### 3.3 目标③：统一经 OpenBase 交互、全面贯通

| 维度 | 现状（实证） | 差距 |
|------|-------------|------|
| 前端 | 统一前端(5173)全部经 OpenBase(8000)；模块路由/代理收敛（UI-E2E P1/P2 已修） | 前端已达"唯一入口"；需固化防回流（新增子系统页面必须注册到统一前端，禁止直连子系统地址） |
| 智能体/Agent | OpenBase 有 mcp/ai_apps/scheduler 等；llm 对话经 llm-proxy | 智能体直连子系统的边界未审计（如 Agent 直接调 OpenLLM 8001 API key 通道做联调属服务面；业务面应收敛到 OpenBase 发布的能力/路由） |
| 鉴权/审计贯穿 | OpenBase 统一 JWT/错误 envelope/request_id；proxy 族注入来源标识（TRUSTED_PROXY_SOURCES） | request_id/身份未统一贯穿到子系统日志与 DPS/OpenMemory 审计行（局部有）；旁路（OpenLLM 直连子系统）的归属审计不完整（治理 P2-1 关联） |

## 4. 任务分解（U1~U5，含在途联动）

### U1 四维统一身份对象与生命周期状态机（OpenBase 主仓）
- 定义统一身份模型与 API：`identity/profile`（四维视图 + external + 状态机：provisioned→active→suspended→deactivated→purged），兼容既有 users/tenants/roles。
- 生命周期语义固化：active 才可认证（本地/OIDC/API Key）；suspended 即时拒签与断链；deactivated 级联清除；全程审计。
- 联动：OIDC JIT 建号接入状态机（去重、复用、停用拦截）；P1-2/P1-3（org 头退役、code 唯一键）为前置或并行。
- 验收：`identity/lifecycle` 接口单测 + 端点集成；停用用户任一入口 401/403。

### U2 跨系统身份同步总线（OpenBase 事件源 + 各系统消费）
- 发布订阅/事件：user.provisioned / role.assigned / user.suspended / user.deactivated（Redis 或 DB outbox）。
- 消费端：DPS（user_roles 绑定增删、画像 person 生命周期关联）；OpenMemory（记忆归属校验表）；OpenRAG（org 归属）；OpenLLM（external 映射缓存失效）。
- 反向收敛：各系统启动自检比对 OpenBase 身份（替换手工种子绑定；DPS seed 的 DEFAULT_USER_BINDINGS 迁移为 OpenBase 下发）。
- 验收：建号→四系统归属出现；停用→DPS 绑定失效/会话拒读；双通道同请求身份等价回归。

### U3 双通道能力矩阵与主备策略（OpenBase + OpenLLM）
- 产出能力矩阵：能力清单 × 通道 A 可达 / 通道 B 可达 / 语义等价性 / 降级映射。
- 主备策略文档化与代码钩子：对话/编排类默认 B、B 健康降级时按组件回落 A（既有 dps/rag/memory client 降级已具备）；管理/原子面默认 A。
- 启用 OpenMemory/OpenRAG REAL（OPENLLM_OPENMEMORY_REAL/OPENRAG_REAL=true 发布批次，随 U2 同步后）。
- 验收：同一画像读请求经 A（dps-proxy）与经 B（OpenLLM REAL profile 组件）返回一致、四头一致；B 故障注入回落 A 用例。

### U4 统一入口加固与全链路审计（OpenBase）
- 边界清单：前端页面注册制、智能体能力经 OpenBase 发布（禁止业务面直连子系统地址）；子系统 API 面保留服务级白名单（编排/探活）。
- 审计贯穿：统一 request_id/身份（user/org/tenant/external）透传到子系统日志与审计存储；旁路（OpenLLM 出站）归属审计补齐（P2-1 联动）。
- 验收：UI-E2E 全模块复验通过 + 旁路审计样例；未注册直连探测被拒/告警。

### U5 端到端全贯通验收（跨仓）
- 一条主链路用例：OIDC/本地建号 → 四维赋权 → 前端进入 → 对话（通道 B：画像注入+记忆沉淀）→ 画像更新（通道 A 写）→ 用户停用 → 全部系统拒访问 → 审计可追溯。
- 回归门禁：两批次测试 + 编排自检全绿。

## 5. 与在途立项联动与顺序

| 依赖 | 关系 |
|------|------|
| P1-2/P1-3（org 退役/code 化） | U1 前置/并行：身份模型以 tenants.code 为唯一键 |
| P2-2（fail-closed + sessions 归属） | U2/U4 前置：先关缺口再同步 |
| P2-1（统一身份协议头） | U4 关联：审计/头一致性大项 |
| P1 级发布批次（REAL 注入/漂移） | U3 依据：通道 B 能力已验证可用 |
| 联调复盘 S1~S6（配置源/契约收口/隔离测试/边界显式） | 全部任务落地纪律 |

建议排期：Phase 1 = P1-2/P1-3 + U1（身份模型与状态机）；Phase 2 = U2（同步总线）+ P2-2 实施；Phase 3 = U3（矩阵与主备）+ REAL 全启用；Phase 4 = U4/U5（入口加固与总验收）。每 Phase 走"需求→设计→开发→测试→部署"五步与人工门禁。

## 6. 风险与约束

- 四维用户模型与既有 users/tenants 兼容面：迁移走增量演进（W1-4 同范式：ALTER/兼容层，不重建）。
- 事件总线一致性：outbox + 幂等消费；OpenBase 停用需即时生效窗口 ≤ 可接受（秒级内）。
- 通道等价性：画像/记忆读在 A/B 的归一化格式差异需契约测试钉死（ProfileAdapter 已承担映射）。
- 智能体生态未定型：先收口 OpenBase 已发布能力，新 Agent 一律注册式接入。
- 本方案为总体定案；各 U 项立项时输出子立项方案（沿用立项方案模板与版本纪律）。

## 7. 验收与总结

以三条目标为验收主线：① 一个用户从建号到注销，四系统状态全程一致、无越权残留；② 任一对话/画像/知识/记忆能力经 A 或经 B 均可用且身份等价、故障可切换；③ 前端与智能体全部交互命中 OpenBase 审计且子系统无业务面直连。三条齐备即"全面贯通"达成；本方案经评审后按 §5 Phase 进入实施。
