# OpenBase-P2-2-隔离收口实施执行计划-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-P22EXEC-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review]（待评审后按 Phase 顺序开工） |
| 日期 | 2026-09-06 |
| 作者 | AD（跨项目分析） |
| 版本主题 | P2-2 卡优先实施的落地执行计划：DPS fail-closed（RA-03/DP-1）→ DPS 绑定收紧（RA-04/DP-5）→ OpenMemory sessions 归属与强制过滤（RA-05/OM-1、K05/OM-2）→ R1 门禁收口；含真实文件改动点、TDD 用例、验收断言与提交策略 |
| 上游依据 | P2-2 立项方案 v1.0.0（T1-T5/Phase1-2）；隔离任务卡 v1.1.0（RA-03/RA-04/RA-05/K05）；JT 归集 v1.1.0（DPS-JT/OpenMemory-JT v1.0.0 = R1） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-06 | AD（跨项目分析） | 初始版本：Phase 0-4 执行计划（真实文件路径来自两仓代码盘点） |

---

## 0. 范围与目标

按"P2-2 卡优先"实施，仅含**已立项**的 4 张卡，分属 DPS-JT 与 OpenMemory-JT 的 v1.0.0（R1）里程碑：

| 卡 | 升级项 | 仓 | 本计划阶段 |
|----|--------|----|-----------|
| RA-03 | DP-1/OB-5（tenant/permission fail-closed） | DPS（OpenBase 同构核对） | Phase 1 |
| RA-04 | DP-5（DPS_DEMO_USER_ROLES 生产基线 + X-User-ID=1 核销） | DPS | Phase 2 |
| RA-05 | OM-1（sessions 归属显式化） | OpenMemory | Phase 3a |
| K05 | OM-2（行级归属必带 + 强制过滤骨架） | OpenMemory | Phase 3b |

OM-3（K06 复合唯一）与 OpenBase 侧 OB-5 兜底属 R1 同批次但未含于 P2-2 已立项卡 → 列入"顺带（待单独批准）"，不阻塞本计划。

## 1. Phase 0 前置盘点（先于任何改动）

- 输入文件（已完成定位）：
  - DPS：`src/config.py`（MULTI_TENANT_ENABLED、DPS_DEMO_USER_ROLES 等键现状）；`src/middleware/tenant_middleware.py`；`src/middleware/permission_middleware.py`；`src/engines/permission_engine.py`；种子 `scripts/seed-shared-infra.py`（user_roles/演示绑定段）；DPS `tests/` 目录惯例。
  - OpenMemory：`src/openmemory/api/controllers.py`（sessions 端点：list/get/terminate）；`src/openmemory/api/server.py`（中间件/身份头解析挂载）；存储层 `src/openmemory/storage/relational_store.py`、`sqlite_store.py`、`inmemory_store.py`（多实现共享 store 契约）；`tests/`（unit/contracts）。
- 盘点动作：① 记录 tenant/permission 中间件现异常分支与配置默认；② 记录 controllers 中 sessions 端点现归属/过滤行为；③ 记录 store 接口（接口统一处）现有过滤参数；④ 输出盘点结论表（现状 → 改动面 → 影响测试）。
- 退出条件：盘点表成文（本计划附件），无未知行为面。

## 2. Phase 1：DPS fail-closed 化（RA-03 / DP-1 / OB-5）

目标升级项 DP-1；依据 P2-2 Phase1、任务卡 RA-03 验收断言。

| 步骤 | 内容 | 文件/位置 |
|------|------|----------|
| 1.1（RED） | 先写失败用例：① DB 故障注入（停 DB/连接串指向坏端）→ tenant 中间件返回 503/403 不放行；② permission 引擎未初始化/异常 → 拒绝；③ 显式 `fail_open=true` 仅测试环境可用 | DPS `tests/` 新建（命名随仓惯例，如 `test_tenant_fail_closed.py`、`test_permission_fail_closed.py`） |
| 1.2（GREEN） | `src/config.py` 新增/收敛开关（如 `MULTI_TENANT_FAIL_CLOSED` 默认 true；明确 fail-open 仅测试环境变量）；tenant 中间件异常分支按开关拒绝 | `src/config.py`、`src/middleware/tenant_middleware.py` |
| 1.3 | permission 引擎初始化检查（引擎未就绪 → 503/403，不静默放行） | `src/middleware/permission_middleware.py`、`src/engines/permission_engine.py` |
| 1.4 | OpenBase 侧同构校验核对（OB-5 兜底，仅核对不改造；差异登记） | OpenBase 编排/网关文档记录 |
| 1.5（GREEN 复核） | ruff + 相关测试全绿；回归双租户 T1/T2 既有用例 | DPS 全量门禁 |

验收断言（卡 RA-03）：故障注入下无放行路径；引擎未初始化拒绝；显式 fail-open 仅测试环境可用（用例断言环境变量约束）。

## 3. Phase 2：DPS 绑定收紧（RA-04 / DP-5）

| 步骤 | 内容 | 文件/位置 |
|------|------|----------|
| 2.1（RED） | 用例：生产环境配置下演示绑定（X-User-ID=1 直绑）不可用；未绑定主体访问画像 403（无隐式降级） | DPS `tests/` 新建 |
| 2.2（GREEN） | `DPS_DEMO_USER_ROLES` 收敛为生产基线清单；演示种子与生产基线按环境开关隔离（测试/演示环境才注入 X-User-ID=1 类演示绑定） | `src/config.py`、种子 `scripts/seed-shared-infra.py` 相关段 |
| 2.3 | 未绑定主体访问画像返回 403（校验链补齐，无隐式默认放行） | permission/画像写读中间件相关 |
| 2.4 | 回归：真实契约画像读写（既有 T/冒烟画像用例）不因收紧而破坏（已绑定主体不受影响） | DPS 门禁 |

验收断言（卡 RA-04）：生产配置下无"隐式绑定放行"路径。

## 4. Phase 3：OpenMemory 归属与过滤（RA-05/OM-1、K05/OM-2）

### 4a sessions 端点归属显式化（RA-05 / OM-1）
| 步骤 | 内容 | 文件/位置 |
|------|------|----------|
| 3a.1（RED） | 用例：跨域 get/terminate → 404；list 仅本域（分页+过滤）；未带身份请求走自身认证 | OpenMemory `tests/`（unit/contracts 随仓惯例） |
| 3a.2（GREEN） | sessions list/get/terminate 端点归属参数解析与断言（owner/tenant），list 禁全量遍历（过滤+分页必需） | `src/openmemory/api/controllers.py` |
| 3a.3 | 身份上下文来源核对（server 层身份头/自身 API Key 解析，与 K02 后续白名单兼容） | `src/openmemory/api/server.py` |

### 4b 强制过滤骨架 + 行级归属必带（K05 / OM-2）
| 步骤 | 内容 | 文件/位置 |
|------|------|----------|
| 3b.1（RED） | 隔离基座用例：任何 store 方法返回集不含他域行；memories 查询跨域不可见 | OpenMemory `tests/` |
| 3b.2（GREEN） | store 接口/基类统一查询入口强制注入 `(tenant_code, owner)`（多实现：relational/sqlite/inmemory 走同一契约）；存量查询全迁骨架 | `src/openmemory/storage/relational_store.py` 及 store 契约处（多实现共用） |
| 3b.3 | 豁免清单机制 + 代码评审门禁（注释标注 ticket）；ORM/事件钩子纵深防御（若架构支持） | 同 store 层 |
| 3b.4 | 行级归属：memories/sessions 写入必带 (tenant_code, owner)，缺失拒绝 | store + controllers |
| 3b.5 | 回归：全量单测 + 双租户隔离（跨域读 404/403） | OpenMemory 门禁 |

验收断言：RA-05（sessions 三端点归属全绿、无全量遍历）；K05（双租户隔离全绿、repository 返回集不含他域行）。

## 5. Phase 4：R1 门禁收口（RA-06 前置子集 + 跨仓会签前置）

- 聚合回归：DPS（fail-closed/绑定收紧/双租户 T1/T2 模式）+ OpenMemory（sessions/骨架隔离）+ OpenBase 存量门禁（OIDC 分批不受影响）。
- 跨仓会签点（JT v1.1.0 §4-5）：K02/K07 未启动不计入本次会签，仅确认 P2-2 四卡接口一致性（身份头语义与 K02 规范预留）。
- 台账：本计划各 Phase 完成后更新任务卡状态（RA-03/04/05/K05 → ✅+提交号）与 JT 表（DPS-JT/OpenMemory-JT v1.0.0 行）。

## 6. 依赖、角色与提交策略

- 依赖：Phase 顺序 1→2→3→4；Phase1/2（DPS）与 Phase3（OpenMemory）可并行（不同仓）。
- 角色（按项目角色管理规范调用）：需求/设计评审 = 对应角色 agent；编码实施 = 开发角色 agent（TDD）；验证 = 测试角色；批准 = 人工门禁（本计划评审 → Phase 顺序执行）。
- 提交策略：DPS 仓与 OpenMemory 仓**各自独立提交**（各仓遵循各自版本与提交规范）；OpenBase 侧只做台账/文档（本计划、任务卡、JT 表）登记，不跨仓提交；OpenLLM 仓沙箱写限制与本计划无关（P2-2 不动 OpenLLM）。
- 门禁命令：DPS/OpenMemory 各自 `ruff` + `pytest` 全量；相关覆盖率 ≥90%（AGENTS.md 同源要求）。

## 7. 风险与备注

- R1：permission 引擎 fail-closed 可能影响既有合法匿名服务调用 → 盘点时确认白名单/服务账号豁免路径（S6 未落地前的过渡豁免需显式列出）。
- R2：OpenMemory 多存储实现契约统一点需先确认（store 契约层），避免各实现过滤行为不一致。
- R3：演示绑定收紧可能影响本地 demo 联调 → 以环境开关隔离，文档化两个运行模式。
- 顺带项（待批）：OM-3/K06 复合唯一（OpenMemory alembic 迁移）建议随 Phase 3 一并实施以省一次迁移窗口；OpenBase OB-5 同构兜底是否纳入本计划范围需确认。

## 8. 待评审问题

- Q-1：是否将 OM-3/K06（复合唯一）纳入本计划 Phase 3（推荐纳入，同仓同迁移窗口）？
- Q-2：DPS 过渡豁免（服务账号 S6 未落地前，fail-closed 下合法服务调用如何豁免）采用"受信来源白名单 + 显式清单"过渡方案是否认可？
- Q-3：本计划评审通过后即按 Phase 1 开工（先 DPS 后 OpenMemory 并行），是否确认？

评审通过后按 Phase 0→4 执行；每 Phase 完成即更新任务卡与 JT 台账状态。
