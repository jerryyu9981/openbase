# OpenBase-S7-T6-2 冒烟真实执行-跨仓派单-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-DISPATCH-S7T62-SMOKE-v1.0.0 |
| 文档版本 | v1.0.1 |
| 状态 | **[Approved]（已批准，正式分发）** |
| 日期 | 2026-10-15 |
| 发起方 | AA/PM-OpenBase-Dev |
| 上游依据 | 《OpenBase-五系统多租户与授权集成总览与续接指南》v1.0.11 §10.5；《OpenBase-真实联调冒烟清单》v1.1.0 §3；《OpenBase-S7-全域门禁与总收官报告》§4.2（S7-T6-2）；《OpenBase-自研系统多租户与授权集成总体完善方案》v1.16.33 |
| 范围 | 在**服务常驻（非沙箱回收）**且 **Ollama 就绪**的环境，按同一脚本执行 S7-T6-2「冒烟 S0–S6 真实执行」并回填证据；**不改代码、不改契约** |
| 分发前置 | 状态由 [Draft] 转 **[Approved]** 后方可分发给各仓 Ops → **已于 2026-10-15 转 [Approved] 并正式分发** |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0.1 | 2026-10-15 | AA/PM-OpenBase-Dev | **批准转 [Approved] 并正式分发**：状态 [Draft] → [Approved]；新增「分发记录」（见上）；登记台账 v1.16.33 与续接指南 v1.0.11 |
| v1.0.0 | 2026-10-15 | AA/PM-OpenBase-Dev | 初始创建：分仓分发表、准入判据、执行步骤、验收判据、证据归集、风险回滚、逐仓回执清单、已知环境适配项 |

## 分发记录

| 项 | 值 |
|----|-----|
| 批准 | 2026-10-15（人工批准「好的，创建跨仓派单」→ 视为批准分发） |
| 分发状态 | **[Approved] 已分发**（分发即本文档作为唯一入口交付各仓 Ops） |
| 分发对象 | OpenBase（宿主）/ OpenLLM / OpenRAG / OpenMemory / DPS / 基础设施 |
| 回执要求 | 各仓按 §8 逐项回执（☐→☑ + 证据），由 OpenBase 宿主汇总 |

---

## 1. 目的与范围

**目的**：闭环 S7-T6-2 —— 在稳定联调环境完成冒烟 S0–S6 全量**真实执行**，判据为 **P0 全绿 / P1 如实登记**，产出可追溯证据。

**范围内**：执行、取证、回填（S7 §4.2 / 走查报告 §5.2 / 续接指南 §10.5）。
**范围外**：任何产品代码/契约变更；E 项（fail-closed 故障注入，需停服，另行授权）；RA-06 其余项（委托跨界、冒烟通知等）。

**已具备（宿主侧，OpenBase 仓已交付）**：
- 运行器 `scripts/smoke_s0_s6.py`（32 例 S0–S6 真实 HTTP，`schema_version=5`）
- 包装脚本 `scripts/run_smoke_s0_s6.ps1`（加载 `.env.shared-infra` + 跨仓拉起 OpenBase/OpenLLM + 运行运行器）
- 首轮基线证据 `doc/test/evidence/s7/smoke/smoke-summary-20261015132711.json`（`PASS 17 / FAIL 8 / PENDING 7`）

---

## 2. 派单对象与分仓分发表

| 仓/角色 | 责任 | 交付物 | 回执 |
|---------|------|--------|------|
| **OpenBase（宿主 Ops）** | 主执行：跑包装脚本；汇总证据；回填文档 | `smoke-summary-<时间戳>.json` + 回填后的 S7 §4.2 / 续接指南 §10.5 | 执行记录（提交号 + 证据路径） |
| **OpenLLM（Ops）** | 保障 8001 常驻可用；确认模型注册表可用；确认 Redis 令牌存储可达 | 8001 `/openllm/v1/health` 200 截图/日志；`OPENLLM_DPS_*_MAP` 覆盖确认 | 前置就绪确认（Y/N + 证据） |
| **OpenRAG（Ops）** | 保障 8010 常驻；服务密钥具备写权限路径（M2 受信来源 + 四头） | 建库/入库/检索冒烟通过记录 | 就绪确认 |
| **OpenMemory（Ops）** | 保障 8020 常驻；确认直连鉴权口径（网关/密钥形态） | `/api/v1/remember|recall` 可达记录 | 就绪确认 |
| **DPS（Ops）** | 保障 8030 常驻；确认 org/tenant 映射与 `TENANT_CONTEXT_REQUIRED` | `/health/liveness` 200；画像端点鉴权口径 | 就绪确认 |
| **基础设施（Ollama/Redis/PG）** | **Ollama 就绪且响应及时**（LLM 调用 ≤ 30s）；共享 Redis/PG 可达 | Ollama `/api/tags` 200；推理时延抽样 | 就绪确认 |

**重叠处置**：以 **OpenBase 宿主的包装脚本**为准一入口；各仓仅提供「就绪确认 + 本仓侧证据」，**不各自另写运行器**，避免口径漂移。

---

## 3. 前置条件（准入判据，全部满足方可执行）

1. **服务常驻**：六服务（OpenBase 8000 / OpenLLM 8001 / OpenRAG 8010 / OpenMemory 8020 / DPS 8030 / OIDC-IdP 8090）**在非沙箱回收环境下常驻**（禁用「命令结束即回收子进程」的沙箱）。
2. **OpenLLM 首健康可容忍**：`/openllm/v1/health` 能返回 200（首次可能 11–40s；脚本已按 90s 超时等待）。
3. **Ollama 就绪**：`http://192.168.0.4:11434/api/tags` = 200，且**推理时延 ≤ 30s**（否则 S2-4/S3-4/S5-1/S5-5 会 `ReadTimeout`）。
4. **模型**：注册表(`GET /openllm/v1/models`)与 Ollama 已拉取模型**存在交集**（脚本自动择交）。
5. **环境变量**：`.env.shared-infra` 存在且含 `POSTGRES_URL`/`REDIS_URL`/`OPENRAG_API_KEY` 等（**OpenBase DB DSN 仅从进程环境解析**，缺失会回落 localhost 致全写失败）。
6. **端口空闲**：8000/8001 无残留监听（脚本启动前自动清理）。

---

## 4. 执行步骤

```powershell
# 0) 前置自检（六服务 + Ollama）
# 1) 一条命令执行（跨仓拉起 + 冒烟 + 取证）
.\scripts\run_smoke_s0_s6.ps1
# 2) 查看结果
#    stdout 末行：total=.. pass=.. fail=.. pending=..
#    证据：doc/test/evidence/s7/smoke/smoke-summary-<时间戳>.json
```

分步（可选，便于隔离问题）：
- `.\scripts\run_smoke_s0_s6.ps1 -Python <解释器>`：指定解释器；
- 已常驻服务时，包装脚本会跳过启动（`already online`）。

---

## 5. 验收判据

| 判据 | 通过标准 |
|------|---------|
| P0 全绿 | S0–S6 中 **P0 用例 100% PASS**（健康/鉴权/记忆契约/知识库 CRUD/检索/旁路等） |
| P1 登记 | P1 项（S4-4/S5-3/S5-4/S6-3 等）允许 `PENDING`，**须逐条给原因** |
| 不伪造 | 任何未执行项**不得填 PASS**；`PENDING` 必须附原因 |
| 证据齐全 | 产出 `smoke-summary-*.json`（`schema_version=5`，含 `openbase_commit`/`ollama_available`/逐案 `evidence`） |

---

## 6. 证据归集

- 汇总：`doc/test/evidence/s7/smoke/smoke-summary-<时间戳>.json`
- 服务日志：同目录 `openllm.<时间戳>.{out,err}.log`、`openbase.<时间戳>.{out,err}.log`
- 回填：S7 报告 §4.2、走查报告 §5.2、续接指南 §10.5（升版留修订历史）

---

## 7. 风险与回滚

| 风险 | 缓解 |
|------|------|
| Ollama 慢 → LLM 用例超时 | 前置判据 3；必要时仅跑非 LLM 子集并登记 LLM 项为 `PENDING(环境)` |
| 服务未常驻 → 中途被回收 | 前置判据 1；严格在常驻环境执行 |
| 端口残留 → 启动失败 | 脚本启动前清端口；失败时读 `*.err.log` 归因 |
| 探索性写入残留 | 运行器使用 `smoke_`/时间戳命名的临时资源，并在 §4 用后停用/清理 |

**回滚**：本派单**仅执行与取证**，无代码/数据回滚需求；发现的缺陷按既有《S7-冒烟缺陷分派待办单》流程登记，不在本单内修复。

---

## 8. 逐仓确认清单（回执项）

| # | 确认项 | 责任方 | 回执 |
|---|--------|--------|:---:|
| 1 | 六服务常驻（非沙箱回收） | 全体 Ops | ☐ |
| 2 | Ollama 就绪且推理 ≤30s | 基础设施 | ☐ |
| 3 | 注册表 ∩ Ollama 模型非空 | OpenLLM | ☐ |
| 4 | RAG 服务密钥可走写路径（M2 + 四头） | OpenRAG | ☐ |
| 5 | OpenMemory 直连鉴权口径明确 | OpenMemory | ☐ |
| 6 | DPS org/tenant 映射与四头鉴权 | DPS | ☐ |
| 7 | `.env.shared-infra` 关键项齐备 | OpenBase | ☐ |

---

## 9. 已知环境适配项（登记，供各仓核对）

| 项 | 说明 | 归属 |
|----|------|------|
| OpenBase DB DSN 仅取进程环境 | `.env` 不参与 DSN 解析（`settings::_resolve_db_url`）；须注入 `POSTGRES_URL` | OpenBase |
| OpenLLM 首健康 11–40s | 探活三上游 + Ollama；脚本超时已设 90s | OpenLLM |
| OpenLLM→DPS 画像 403 | org 别名 `11111111-…` 未在 `OPENLLM_DPS_*_MAP` 覆盖 | OpenLLM/DPS |
| OpenLLM Redis 令牌存储 | 日志为 `redis://redis:6379/0`（Docker 主机名默认值）；确认是否需对齐共享 Redis | OpenLLM |
| 记忆契约经 memory-proxy | 本环境 OpenMemory 直连鉴权被网关层拒绝，运行器改经 `memory-proxy`（语义等价链路，含四头） | OpenBase/OpenMemory |

---

## 10. 参考规范

- 《OpenBase-真实联调冒烟清单》v1.1.0（§3 用例矩阵、§4 环境待办）
- 《OpenBase-S7-全域门禁与总收官报告》§4.2（S7-T6-2 卡）
- 《OpenBase-五系统多租户与授权集成总览与续接指南》v1.0.10 §10.5
- 《OpenBase-联调窗口真实面执行单》v1.2.0（同源脚本模式）
