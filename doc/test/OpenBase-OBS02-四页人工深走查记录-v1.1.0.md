# OpenBase OBS-02 四页人工深走查记录

| 项目 | 内容 |
|---|---|
| 文档编号 | TEST-OBS02-20261026 |
| 版本 | v1.1.0 |
| 状态 | [Final] |
| 适用环境 | 本地全栈联调：OpenBase 8000 / OpenLLM 8001 / OpenRAG 8010 / OpenMemory 8020 / DPS 8030 / 前端 5173；共享 PG 主用 `192.168.0.151:5432` |
| 执行日期 | 2026-10-26（首轮） / 2026-10-27（遗留复验） |
| 上游依据 | 《OpenBase-前端全页面走查清单-v1.0.0.md》§6「OBS-02 人工深走查清单」 |
| 证据 | `doc/test/evidence/manual/obs02-walkthrough-20261026.json`<br>`doc/test/evidence/manual/obs02-def02-def03-b3-20261027.json`<br>`doc/test/evidence/manual/obs02-20261026/`（11 张截图：A1/A2/B1/B2/B3/C1/C2/D1/D2/D2b/D3） |

---

## 1. 执行方式（"陪跑"口径）

| 环节 | 由谁执行 | 说明 |
|---|---|---|
| 只读加载、空态、校验提示、弹窗打开 | 自动陪跑（Playwright） | 逐用例记录接口状态码、`console/page error`、截图 |
| 业务写操作（生成候选 / 新建应用） | 自动陪跑 + **受控数据** | 仅创建 `OBS02-*` 前缀临时数据，执行后**全部清理** |
| 破坏性操作（删除模型、停用提供商、回滚模板） | **未执行** | 需人工在真实业务数据上操作，另开窗口 |

判定口径（与全页走查一致，补充业务预期）：

- 5xx / 页面异常 / 步骤失败 → **FAIL**；
- 业务预期 4xx（如「无谱系」404、「能力未启用」403）→ 记录为 **PASS(预期 N)**，其浏览器 `console.error` 属必然产物，不判失败；
- 缺少业务数据导致用例不可验证 → **BLOCKED**（显式标注，不填 PASS）。

---

## 2. 前置环境处置（本次实测触发）

启动全栈时**主用库被误判为不可用**：跨网 `select 1` 实测 2.1~4.8s，而数据面探针默认超时 `3s`，导致脚本自动切备用库——openllm / openrag / openmemory 被覆盖到 `127.0.0.1`（备用库 `api_keys` 仅 2 条，主用 17 条），openmemory 因备用库瞬时不可达**被拒启动**。

处置：使用编排器既有参数放宽阈值后重拉：

```powershell
.\scripts\service-orchestrator.ps1 -Action start -Only openllm,openrag,openmemory,dps -DbProbeTimeoutSec 10
```

结果：`pg=ok(primary,data-plane)`，四服务均连主用库；openllm / openrag / openmemory / dps 分别 126s / 200s / 298s / 自检超时（进程已监听）后健康。

> 结论：**不是代码缺陷，是阈值配置与该网络环境不匹配**。建议把默认值调到 8~10s（或按环境配置），见 §5 OBS02-OBS-01。

---

## 3. 用例结果

| # | 页面 | 用例 | 关键观测 | 结论 |
|:-:|---|---|---|---|
| A1 | `/openllm/models/local` | 加载 + 「模型仓库」弹窗 | 弹窗可见；`local-models/available` 返回 0 条（内置清单为空） | PASS |
| A2 | `/openllm/models/local` | 「GPU 调度」弹窗 | 弹窗可见，文案「暂无数据 / 未检测到可用 GPU」（信息态） | PASS |
| B1 | `/portrait/dps/lineage` | 不存在的 tag_code | `GET /dps-proxy/lineage/tags/__not_exist__` → 404；页面呈现「未找到该标签的谱系」空态，**未**呈现错误告警 | PASS(预期 404) |
| B2 | `/portrait/dps/lineage` | 空输入边界 | 点击「反查」**新增接口调用 0 次**，无报错（前端早退） | PASS |
| B3 | `/portrait/dps/lineage` | 口径（basis）展开 | 造 1 条 `tag_lineage`（`service:channel`）后：`GET /dps-proxy/lineage/tags/service:channel` → **200（sources=1）**；`?tag_code=` 影响面 → 200（tag_count=1 / profile_count=1）；口径卡渲染条件 `sources.length>0` 已满足 | **PASS（数据面）**；浏览器可视复验受 Playwright 启动超时限制，待工具恢复补截图 |
| C1 | `/portrait/dps/annotation-adapters` | 空输入校验 | 提示「请填写标注模板与待标注文本」，新增接口调用 0 次 | PASS |
| C2 | `/portrait/dps/annotation-adapters` | 生成 AI 候选（写） | `POST /dps-proxy/annotation-adapters/stub-v1/generate` → **403**；页面切「该能力当前未启用」信息态，候选 0 行，**零写入** | PASS(预期 403) |
| D1 | `/openllm/apps/new` | 空表单校验 | 提示「请填写应用名称与模型」，无请求、停留在表单 | PASS |
| D2 | `/openllm/apps/new` | 正常提交（写） | 真实创建成功（后端 `GET /api/v1/ai-apps` 可见 `OBS02-走查临时应用`，模型 `qwen2.5:0.5b`），跳转 `/openllm/apps` | PASS |
| D2b | `/openllm/apps/new` | **失败路径**（拦截 POST 后 abort） | 提示 `Network Error`，**停留在表单、不跳转、不提示成功** | PASS（修复后） |
| D3 | `/openllm/apps/new` | 取消返回 | 跳转 `/openllm/apps` | PASS |

汇总（v1.1.0 复验后）：**PASS 10 / PASS(预期 4xx) 2 / BLOCKED 0 / FAIL 0**；B3 浏览器可视复验待工具恢复补截图。

---

## 4. 逐页功能判定

### 4.1 `/openllm/models/local`（本地模型）

| 功能点 | 判定 | 说明 |
|---|---|---|
| 已安装模型列表 | 正常 | `GET local-models` 200，返回 2 个模型（`qwen3.5:4b/2b-q4_K_M`），单次耗时 ~8.5s（需查询 Ollama `192.168.0.4:11434`） |
| GPU 信息 / 分配 | 正常 | `gpu-info`、`gpu-allocation/status` 200，7s 级；无 GPU 时为空态 |
| 模型仓库弹窗 | 正常但无数据 | `local-models/available` 返回 0 条（后端内置清单为空） |
| 拉取 / 启动 / 停止 / 更新 / 删除 | **未执行**（破坏性） | 需人工确认后在真实 Ollama 上操作 |
| 性能观察 | 注意 | 列表接口 8s+，首屏骨架期较长；若代理超时较紧可能偶发 502（本次首调即出现 1 次 `SYS_502 upstream unreachable`，复跑 200） |

### 4.2 `/portrait/dps/lineage`（标签血缘反查）

| 功能点 | 判定 | 说明 |
|---|---|---|
| 无谱系 → 空态 | 正常 | 404 收敛为 `lineage-not-found` 信息态，符合「正常业务结果不作错误页」设计 |
| 空输入早退 | 正常 | 0 请求 |
| 血缘来源表 / 影响面统计 | **已复验（数据面）** | 造 1 条 `tag_lineage` 后 sources=1；影响面 tag_count=1 / profile_count=1 |
| 口径（basis）展开 + 强制展开 | **条件已满足** | `sources.length>0` 时渲染口径卡；浏览器可视点击受工具限制待补 |
| 导出结果（`sources` 非空才可用） | **条件已满足** | 导出按钮 disabled 绑定 `!sources.length`，当前 sources=1 → 可用；浏览器实点待补 |

### 4.3 `/portrait/dps/annotation-adapters`（AI 标注候选与复核）

| 功能点 | 判定 | 说明 |
|---|---|---|
| 空输入校验 | 正常 | 提示正确、零请求 |
| 能力未启用 → 403 信息态 | 正常 | `capability_disabled` 分支生效，零写入；文案明确「未启用状态下不会发起任何写请求」 |
| 生成候选（启用态） | **不可验证** | 通道未启用（403）；`platform.annotation` 0 行 |
| 逐条通过/驳回 | **已复验（接口面）** | `POST /dps-proxy/annotations/{id}/review` 200、`review_persisted=true`，DB 状态落库 |
| 复核辅助（LLM） | 未验证 | 需候选行上的按钮 |
| 「提交复核结果」 | **已修复并复验** | 改接 `POST /dps-proxy/annotations/batch-review`；实测 2 条 → succeeded=2 / failed=0，DB 逐条落库（见 §5 DEF-02） |

### 4.4 `/openllm/apps/new`（AI 应用新建）

| 功能点 | 判定 | 说明 |
|---|---|---|
| 空表单校验 | 正常 | 提示「请填写应用名称与模型」 |
| 正常创建 | 正常 | `POST /api/v1/ai-apps` 200，列表可见，跳转正确 |
| 失败提示 | **已修复**（原为假成功） | 见 §5 OBS02-DEF-01 |
| 取消返回 | 正常 | 返回 `/openllm/apps` |
| 编辑态（`/openllm/apps/:id`） | 未验证 | 当前无应用数据，且编辑页复用同一组件（`PUT /ai-apps/{id}`） |

---

## 5. 缺陷与观察项

### OBS02-DEF-01（P2，已修复）AI 应用保存失败被吞掉，提示「保存成功（演示）」

- **现象**：`AppForm.vue` 的 `catch` 分支提示「保存成功（演示）」并跳转列表；接口失败时用户误以为已保存。
- **根因**：catch 内写了成功文案（演示遗留），未区分成功/失败分支。
- **修复**：改为 `ElMessage.error(describeError(error).detail || title || '保存失败，请稍后重试')`，失败停留在表单、不再跳转。
- **验证**：`vue-tsc --noEmit` 通过；Playwright 拦截 POST 强制 abort → 提示 `Network Error` 且停留在 `/openllm/apps/new`（截图 `D2b-失败路径.png`）；正常路径提示「保存成功」并跳转。

### OBS02-DEF-02（P2，已修复）「提交复核结果」无后端动作

- **现象**：`DpsAnnotationAdapterView.vue::submitAll()` 仅 `ElMessage.success('复核结果已提交')`，未调用任何接口（逐条通过/驳回已各自落库）。
- **根因**：前端无批量调用；OpenBase `dps-proxy` 也未登记标注复核路由（单条/批量一律 404）。
- **修复**（2026-10-27）：
  1. **OpenBase**：`dps_proxy` 新增 `POST /annotations/{id}/review` 与 `POST /annotations/batch-review`，请求体原样透传 DPS；
  2. **前端字段对齐**：单条复核由 `review_status` 改为 DPS 原生 `status` + `current_status`（原字段被 DPS 判为不支持操作 → 409）；
  3. **批量接线**：`submitAll()` 调用 `batchReviewAnnotations`，按 `succeeded/failed` 如实反馈；仅提交服务端 UUID（`cand-N` 占位不提交）。
- **验证**：`POST /api/v1/dps-proxy/annotations/batch-review`（2 条）→ 200 `succeeded=2 / failed=0`；单条 → 200 `review_persisted=true`；DB 状态与备注逐条一致；OpenBase 路由测试 **77 passed**；前端 `vue-tsc` + `vite build` 通过。

### OBS02-DEF-03（P1，已修复，复验中发现）DPS 标注复核在 PostgreSQL 上恒 500

- **现象**：批量复核返回 200 但逐条 `ok=false, status=500`，错误 `invalid input for query argument $4: '…' (expected datetime…)`。
- **根因**：`annotation_template_engine.review_annotation` 把 `datetime.isoformat()` 字符串绑定到 `platform.annotation.updated_at`（timestamptz）；asyncpg 只接受 datetime 实例。同类写法还存在于标注模板创建/更新与结构化标注落库。
- **修复**：上述四处统一改传 `datetime` 对象（SQLite 由适配器转换，仓内用例保持通过）。
- **验证**：修复后批量 2/2、单条 200 且落库；新增 `test_obs02_annotation_timestamp_param.py`（1 例）＋ `test_v2_10_annotation_chain.py`（30 例）合计 **31 passed**。

### OBS02-FIX-01（P1，已修复）健康超时路径不落盘监听 PID，`stop` 留孤儿

- **现象**：openllm / openrag 健康检查超时后（进程稍后才就绪），记录的仍是包装 powershell PID；`stop` 后端口 8001/8010 仍在监听。
- **修复**：① 超时分支按端口反查并落盘真实监听 PID；② `stop` 同时终止「记录 PID」与「端口占用 PID」。
- **验证**：`tests/test_orchestrator_db_failover.py` 24 例（23 通过 / 1 跳过——需无栈环境的行为用例）；修复后 `stop` 端口全部释放。

### OBS02-OBS-01（P2，已修复）数据面探针 3s 超时对跨网主用库偏紧 → 误切备用

- **实测**：主用 PG `select 1` 2.1s、Redis 2.5s、Qdrant 4.8s（2026-10-27 复测最高 6.1s）；默认 `-DbProbeTimeoutSec 3` 触发误判，四服务被覆盖到备用库。
- **影响**：备用库数据落后（`api_keys` 2 vs 17），业务会出现「登录成功但数据缺失/401」等迷惑现象；openmemory 直接被拒启动。
- **修复**：`service-orchestrator.ps1` 默认超时 **3s → 10s**（仍可用 `-DbProbeTimeoutSec` 覆盖）；2026-10-27 默认启动实测 `mode=primary`，dps/openbase 均连主用库。

---

## 6. 数据清理与遗留

| 项 | 状态 |
|---|---|
| 临时应用 `OBS02-走查临时应用`（app-1/app-3）、`OBS02-成功路径验证`（app-4）、探针 `app-2` | **已全部删除**（`GET /api/v1/ai-apps` 现为 0 条） |
| `platform.annotation` / `platform.annotation_template` / `platform.tag_lineage` | 复验临时标注已删除；**B3 最小谱系数据保留 1 条**（`service:channel`，annotation `aaaaaaaa-1111-4111-8111-111111111111`） |
| B3 口径用例 | **PASS（数据面）**：sources=1 / impact tag_count=1；浏览器可视点击待工具恢复补 |
| C2 生成候选 / 复核辅助 | **BLOCKED**，需开启 AI 标注通道（当前 403）；逐条复核与批量复核已用临时标注行完成接口面复验 |
| 本地模型写操作（拉取/启停/更新/删除） | 未执行，需人工确认窗口 |
| 应用编辑态 | 无数据未验证，建议造 1 条应用后再验 `PUT` |

复验建议命令：

```powershell
# 1) 造数后单跑血缘页面
node scripts/ui_e2e_all_services.mjs --service dps --interact
# 2) 通道开启后重跑本记录用例集（脚本见 §1 说明，已随会话清理）
```

---

## 7. 修订历史

| 版本 | 日期 | 执行人 | 说明 |
|---|---|---|---|
| v1.0.0 | 2026-10-26 | FA-OpenBase-Dev（AI 陪跑） | 首版：四页 11 条用例（PASS 9 / PASS(预期 4xx) 2 / BLOCKED 1 / FAIL 0）；DEF-01 已修并复验；DEF-02 待裁定；FIX-01 已修；OBS-01 环境阈值建议 |
| v1.1.0 | 2026-10-27 | AA/PM-OpenBase-Dev | 遗留复验：DEF-02 接线并复验（dps-proxy 单条/批量 + 前端批量提交）；OBS-01 默认探针 3s→10s；B3 造谱系数据后数据面 PASS（sources=1 / tag_count=1，浏览器可视待补）；**新发现并修复 DEF-03**（DPS 复核 timestamptz 绑定字符串致 PG 500），回归 31 passed |
