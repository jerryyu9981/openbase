# OpenBase v1.4.10 派单执行回执 — OpenLLM 侧（OB-v1.4.10-DSP-LLM-01）

| 项目 | 内容 |
|------|------|
| 派单编号 | **OB-v1.4.10-DSP-LLM-01** |
| 派单来源 | 《OpenBase-v1.4.10-跨仓改动规划与派单-v1.0.0》§2（`doc/planning/`） |
| 对应条目 | OpenBase v1.4.10：**BL-1410-12／BL-1410-13**（FR-1410-12／13、AC-15／16）／TD-新增-035／036 |
| 承接仓 | **OpenLLM** |
| 执行日期 | 2026-09-29 |
| 执行人 | AA-OpenBase-Dev / DO-OpenBase-Dev（跨仓执行） |
| 状态 | **已实施（改动入库＋tag 已推三远程）**；**实测验收待环境窗口**（见 §5） |

---

## 1. 落点确认（实施前实测）

| 证据 | 结论 |
|------|------|
| `DEBUG=True` **仅存在于** OpenLLM `backend/.env`（OpenBase 仓 `.env` 无该键） | 日志淹没根因在 OpenLLM |
| `backend/app/core/config.py:15` `DEBUG: bool = Field(default=False)` | 配置面 |
| `backend/app/db/session.py:20` 与 `:31` `echo=settings.DEBUG` | **根因确认**：DEBUG 直接驱动 SQLAlchemy echo |
| `backend/main.py:627` `@app.get("/health")`；`:88` `async def lifespan` | health 与启动路径落点 |
| `backend/app/services/health_service.py` | health 服务实现 |

---

## 2. 改动清单（5 文件，+166 −8）

| # | 文件 | 改动 |
|:-:|------|------|
| 1 | `backend/app/core/config.py` | **新增 `SQL_ECHO: bool = False`**（与 `DEBUG` 解耦，附原因注释）；`APP_VERSION` 2.14.0 → **2.14.4** |
| 2 | `backend/app/db/session.py` | **两处** `echo=settings.DEBUG` → `echo=settings.SQL_ECHO`（SQLite 与非 SQLite 分支） |
| 3 | `backend/main.py` | ① **`/health` 指标摘要**（增量 `metrics`：`uptime_seconds`／`debug`／`sql_echo`／`env`／`app_version`，**既有键不变**）；② **lifespan 启动预热**（DB 连接 ＋ `SELECT 1` 前移，**fail-open**）＋ `app.state.started_at`；③ `import time` |
| 4 | `backend/tests/unit/test_v2144_ops_hardening.py` | **新增护栏 10 例**（解耦／health 键与 metrics／预热静态契约／签名契约） |
| 5 | `.devflow/project-config.json` | `version` 2.14.3 → **2.14.4**；`lastRelease` → **v2.14.4**；`github` SSH → **HTTPS**（本机 SSH 不可用） |

### 2.1 `/health` RED 三要素评估结论（BL-1410-12 后半）

> **结论：不在 `/health` 重复实现 RED 三要素。** 理由：① Rate／Errors／Duration 需**请求级计数与耗时聚合中间件**；② 既有 `app/api/metrics.py`（Prometheus `/metrics` 端点）已承载该口径，重复实现将**产生双口径**（违背单一事实源）。**采纳的增量**为低成本运行态摘要（uptime ＋ 配置可见性），用于排障定位日志面与开关状态。**评估结论已产出 ⇒ 该项记为完成**（派单允许「采纳与否均记完成」）。

---

## 3. 交付锚点

| 项 | 值 |
|----|-----|
| 承接仓分支 | `feature/s4-identity-channel-b` |
| **提交** | **`b28fb1b`** |
| **Tag** | **`v2.14.4`**（annotated；tag 对象 `98fcc184`） |
| 推送范围 | **origin ＋ backup ＋ github 三远程**（分支与 tag 均一致） |

---

## 4. 验证结果

| 项 | 命令 | 结果 |
|----|------|------|
| 新增护栏 | `python -m pytest tests/unit/test_v2144_ops_hardening.py -v` | ✅ **10 passed** |
| 相关子集回归 | `python -m pytest tests/unit/ -k "config or session or health or main or db" -q` | **335 passed / 3 failed** |
| 失败项定性 | — | 3 项**均属 TD-新增-030 既有失败簇**：① `test_model_router_wiring::test_model_auto_no_healthy_candidate_1004`（"模型路由接线"；两次运行表现不同 —— 2001 vs 500，**环境相关 flaky**，日志显示 `组件 dps 不可用`）；②③ `test_real_contract_memory／rag::..._default_false`（"real-contract 默认值开关"，读 `.env` 环境开关，与本改动面无交集） |
| **零新增失败判据** | 逐项比对 | ✅ **成立**（3 项均为 v1.4.9 已登记既有失败，本次改动未新增任何失败） |

---

## 5. 待办（如实登记，**不静默降级**）

| # | 待办 | 原因 | 计划 |
|:-:|------|------|------|
| 1 | **日志改善实测**（结构化 JSON 占比 / 体积对比 v1.4.9 基线 4,394／27,084 行、4.17 MB） | 需启动服务并与基线日志对比 | 随 v1.4.10 测试阶段（或环境窗口）执行 |
| 2 | **首请求延迟实测**（重启后首请求 ≤ 热态 P95 量级，对比基线 2,150 ms；热态 P50 37.5 ms） | 同上 | 同上 |
| 3 | 双仓联调确认（OpenBase 侧 dps-proxy 与 OpenLLM 侧硬化互不影响） | 需 D3（DPS 可启动）就绪 | 随 P2／P3 联调 |

> **说明**：本回执**不声称已实测**；改动与单元护栏已完成并通过，**AC-15／16 的实测部分保留为待办**，在 v1.4.10 测试阶段统一取证。

---

## 6. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-09-29 | AA-OpenBase-Dev | 初始创建：**落点确认 5 项实测证据**；**改动清单 5 文件（+166 −8）**；**`/health` RED 三要素评估结论**（不在 `/health` 重复实现，避免双口径）；**交付锚点**（`b28fb1b` ＋ tag `v2.14.4`（`98fcc184`）＋ 三远程）；**验证结果**（新护栏 10 passed；相关子集 335 passed／3 failed 均属既有失败簇 ⇒ 零新增失败）；**待办 3 项如实登记**（日志改善与首请求延迟实测待环境窗口，AC-15／16 实测部分保留）。状态 [Review]。 |
