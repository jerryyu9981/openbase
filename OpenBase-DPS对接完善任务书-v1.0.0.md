# OpenBase-DPS对接完善任务书-v1.9.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-DPS-v1.9.0 |
| 版本 | v1.9.0 |
| 状态 | [Review] |
| 日期 | 2026-09-05 |
| 作者 | AD（跨项目分析） |
| 版本主题 | OpenBase 与 DPS 对接全量清理（P1/P2/P3.1/P3.2/P5/P6/P7 已实施；P4 对照完成且 /profile/v1 决策已定案；P8/P9 待办） |
| 适用范围 | OpenBase（8000，dps-proxy 模块）与 DPS（src/rest_api v2，默认 8000；编排 8030） |

> 本任务书为 OpenBase↔DPS 对接完善的唯一执行依据。事实锚点基于真实验证与两仓库代码核对。本文件编辑期多次遭外部进程回滚，自 v1.7.0 起以"整文件重建"为基线；v1.9.0 为当前一致快照。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-05 | AD（跨项目分析） | 初始版本：现状盘点与 P1~P9 详细方案、实施顺序、回归清单、风险登记 |
| v1.1.0 | 2026-09-05 | AD（跨项目分析） | P3 拆分子项（P3.1/P3.2/P3.3） |
| v1.2.0 | 2026-09-05 | AD（跨项目分析） | P1（0499838）/P2（aae1de7）/P3.1（1074751）实施回填 |
| v1.3.0 | 2026-09-05 | AD（跨项目分析） | P3.2 硬绑移除核对 + P7 种子实跑 |
| v1.4.0 | 2026-09-05 | AD（跨项目分析） | P5 写链真实 PG 实证 |
| v1.5.0 | 2026-09-05 | AD（跨项目分析） | P4 OpenAPI 81 路径对照 + 10 端点映射表 |
| v1.6.0 | 2026-09-05 | AD（跨项目分析） | P6 连续失败降级 503（22d369f） |
| v1.7.0 | 2026-09-05 | AD（跨项目分析） | 整文件重建汇总基线 |
| v1.8.0 | 2026-09-05 | AD（跨项目分析） | /profile/v1 映射决策定案 |
| v1.9.0 | 2026-09-05 | AD（跨项目分析） | 最终原子重建（含全部决策与状态，单一一致快照） |

---

## 1. 背景与目标

OpenBase 统一网关经 `/api/v1/dps-proxy` 聚合 DPS 画像能力（前端 portrait 页 + OpenLLM `OPENLLM_DPS_REAL`）。目标态：数据源闭环、Schema 可用、身份键同形（tenants.code 增量）、写链真实可追踪、降级可感知、冒烟全绿。

## 2. 现状总览

| 类别 | 状态 | 说明 |
|------|:---:|------|
| dps-proxy 端点面 | ✅ | 画像 list/get/calculate/update、tags/categories、reports/overview、batch/import status、audit/logs、health 共 10 端点 |
| 身份头与映射 | ✅ P3.1 | tenant_code 增量 claim + code 优先 + 映射表 code 键 |
| 运行数据源 | ✅ P1 | 编排强制共享 PG（SQLITE_FALLBACK=false）；platform schema 27 表 |
| PG 方言 | ✅ | _pg_translate（qmark→$n）落地并实证 |
| 画像读写契约 | ✅ P5 | PUT→version 递增 + profile_history 快照 + 缓存失效 |
| 可用性 | ✅ P6 | 连续失败降级 503（dps_degrade_threshold） |
| 种子 | ✅ P7 | seed-shared-infra.py 幂等（org/tenant/roles/bindings/profile） |
| 文档 | ⚠️ | 对接使用指南未成文（P8） |
| 冒烟 | ⚠️ | P9 门禁未执行 |

## 3. 实施记录与待办

### 已实施（含证据）

- **P1（0499838）**：编排共享 PG env + SQLITE_FALLBACK=false + /health/liveness；27 表实证。
- **P2（aae1de7）**：PROXY_SYSTEMS['dps'] 同源 settings.dps_upstream_base；两态取值正确；27 passed。
- **P3.1（1074751）**：auth `_resolve_tenant_code` 增量 `tenant_code` claim（login/refresh/oidc）；dps-proxy 头链 code 优先数值兜底；三态断言 + 50 passed。
- **P3.2（v2.8.1 核对）**：硬绑移除无残留；绑定显式种子（DEFAULT_USER_BINDINGS，env 覆盖）；未绑定 fail-closed 待冒烟实证。
- **P5（v2.8.1 + 实证）**：快照函数 L517+/调用 L642-646；实测 PUT 双 200、version→9、history 7 行同步。
- **P6（22d369f）**：dps_degrade_threshold（默认 3）；连续失败 503 + X-DPS-Upstream-Degraded 头；恢复归零；行为断言 + 27 passed。
- **P7（实跑）**：seed 幂等 org=1/tenant=1/roles=6/user_roles=1/profile=3，重跑 0 新增。

### P4 端点契约对照 + /profile/v1 决策（已定案）

OpenAPI 实证 81 路径；proxy 10 端点映射表（list/get/calculate/update、tags、reports/overview、batch status、audit/logs、health）。错误 envelope 由 `_adapt_response` 归一。未开放面（默认不开）：risk-assess/annotate/associate/statistics/trend/track/version/compare/search/suggestions/画像 tags/ai:* /generate/labels/reports 扩展/streams/permissions/organizations/tenants/batch export。

**/profile/v1 决策（v1.8.0 定案）**：DPS 侧无需实现 /profile/v1——OpenLLM ProfileAdapter 真实模式已承担 stub→v2 全映射（读 stub GET /profile/v1/get → real GET /api/v2/portrait/{person_id}；写 stub POST /profile/v1/update → real PUT /api/v2/portrait/{person_id}；extract_targets/dimensions 无 v2 对应 → 返回完整画像并注释忽略；错误 → ComponentUnavailableError 组件级降级）。person_id 规约：external_user_id 优先，否则 {org_id}_{user_id}。残余：真实模式端到端验证并入 P9。

### P8 待办

产出《OpenBase-DPS 对接使用指南 v1.0.0》（端点清单/身份头/错误 envelope/种子/联调/端口约定），参照 OpenMemory 指南体例。

### P9 待办（门禁）

冒烟 S4 全绿（重启存活、双租户隔离、version/history、停服降级、未绑定 fail-closed、真实模式 profile 端到端、漂移重算 P1）+ DPS/OpenBase/OpenLLM 回归 0 失败 + 编排起服健康与 DPS 表存在性断言。

## 4. 实施顺序与依赖（状态）

| 序 | 项 | 状态 |
|:---:|-----|------|
| 1 | P1 数据源闭环 | ✅（0499838） |
| 2 | P2 端口收敛 | ✅（aae1de7） |
| 3 | P6 降级 | ✅（22d369f） |
| 4 | P3 身份收敛 | 🔶 P3.1/P3.2 已实施；P3.3=治理 P1-2/P1-3 待立项 |
| 5 | P7 种子 | ✅（实证） |
| 6 | P5 写链 | ✅（实证） |
| 7 | P4 契约对照 + /profile/v1 决策 | 🔶 对照与决策完成（无待实施代码项；运行时验证归 P9） |
| 8 | P8 指南 | 待办 |
| 9 | P9 冒烟门禁 | 待办 |

## 5. 回归清单

| 命令 | 预期 |
|------|------|
| DPS pytest src/tests（子集先行） | 0 失败（沙箱写限制用例按真实环境） |
| OpenBase pytest tests | 0 失败（dps-proxy/settings/gateway/auth 子集基线通过） |
| OpenLLM profile/writeback 子集（DPS_REAL=true） | 0 失败 |
| 编排 start | 五服务健康 + DPS 表存在性断言 |
| 冒烟 S4 组（清单 v1.1.0） | 全 PASS（P1 级登记不阻塞） |

## 6. 风险与遗留

- 沙箱写限制：共享 PG 已规避（P1）。
- PG 方言：_pg_translate 实证（P5）。
- 权限：硬绑已移除；未绑定 fail-closed 待 P9 实证。
- /api/v1 写恒 403：既有契约，v2 为唯一写面。
- 文档竞争：本文件编辑期多次遭外部进程回滚，v1.9.0 起后续修改建议一次整写并立即提交校验。
- P3.3 全量 code 化 = 治理 P1-2/P1-3 立项；DPS 侧 fail-open 归治理 P2-2；dps_tenant_map code 键部署值待联调写入。

### 状态追踪表

| 项 | 状态 | 验证日期 | 备注 |
|:---:|------|:---:|------|
| P1 数据源闭环 | ✅ | 2026-09-05 | 0499838；27 表实证 |
| P2 端口收敛 | ✅ | 2026-09-05 | aae1de7 |
| P3 身份收敛 | ✅ P3.1/P3.2 | 2026-09-05 | 1074751；v2.8.1 无残留 |
| P4 契约对照与决策 | 🔶 完成 | 2026-09-05 | OpenAPI 81 路径；/profile/v1 定案 |
| P5 写链 | ✅ | 2026-09-05 | version 9 / 快照 7 行 |
| P6 降级 | ✅ | 2026-09-05 | 22d369f |
| P7 种子 | ✅ | 2026-09-05 | 幂等实跑 |
| P8 指南 | 待办 | - | - |
| P9 冒烟门禁 | 待办 | - | - |

**遗留**：P3.3、/profile/v1 运行时验证（P9）、P8、P9、DPS fail-open（治理 P2-2）、dps_tenant_map code 部署值。
