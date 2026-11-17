# OpenBase 前端全站走查报告

## 文档元信息

| 项 | 内容 |
|---|---|
| 文档版本 | v1.1.0 |
| 状态 | [Approved]（本次全栈走查完成） |
| 适用环境 | Dev（OpenBase 8000 / DPS / OpenLLM / OpenRAG / OpenMemory / 前端 5173） |
| 作者 | AI 编码代理 |
| 创建日期 | 2026-11-18 |
| 走查范围 | 前端全部静态路由 89 个 + 8 组关键业务流程 + A/B 双通道 |

### 修订历史

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-18 | 首次全栈拉起与全站页面/关键流程走查，记录问题、修复 RAG SSE 终止缺陷并留存证据 | AI 编码代理 |
| v1.1.0 | 2026-11-18 | 回填 P-01/P-02 修复：编排器启动预热（6 端点）+ DPS 模板注册表进程内预热；图投影 worker 纳入编排（单实例 advisory lock + 心跳，积压 2860→0） | AI 编码代理 |

## 1. 环境与启动

- 启动方式：`scripts/service-orchestrator.ps1 -Action start`（全栈 7 服务 + 前端）。
- 启动结果：OpenBase 8000、DPS 8030、OpenLLM、OpenRAG、OpenMemory、OIDC、前端 5173 全部监听，`-Action status` 全部健康。
- 登录入口：`admin / admin123`，JWT 登录与前端路由守卫正常。

## 2. 走查方法

1. **全路由渲染扫描**：注入登录态后逐页访问 89 个路由，采集 `pageerror`、`console.error`、API `>=400`、布局兜底标记与正文长度。
2. **关键流程交互**：登录→仪表盘、画像列表搜索/计算弹窗、画像详情、DPS 模板与标注工作台、OpenLLM 模型/Playground（A 直连 + B 自动编排）、知识库列表与 RAG 对话、记忆列表/写入校验/图谱、平台用户/角色/租户/监控/日志。
3. **结果复核**：首轮正文过短的页面延长等待复测，排除懒加载时序误判。
4. **证据**：截图与 Playwright 产物位于 `%TEMP%\ob-walk\` 与 `doc/test/evidence/s6/ui-e2e/artifacts/`。

## 3. 全站结果

- 89 个路由全部可达，无白屏、无路由兜底页、无 JS 运行时错误。
- 扫描期间 **0 条** `console.error`、**0 条** API `4xx/5xx`。
- 首轮 31 个页面正文不足 20 字符，延长等待后全部正常渲染，属懒加载/冷启动时序，不是页面故障。

### 3.1 关键流程结果

| 流程 | 结果 | 观测 |
|---|---|---|
| 登录 → 仪表盘 | PASS | 登录成功、令牌落库、KPI 延迟约 10s 后显示（5 / 115 / 99 / $0.00） |
| 画像列表 + 搜索 + 计算弹窗 | PASS | 18 行；不存在关键字过滤为 0；计算弹窗正常打开 |
| 画像详情（tenant-1_1） | PASS | 6 维正常；标签区按维度分组；同名标签已按 D-04 去重 |
| DPS 模板族 | PASS | 6 个模板全部列出，状态/操作列正常 |
| DPS 标注工作台 | PASS | 录入卡与队列卡渲染；未选模板/人员时提交按钮禁用 |
| OpenLLM 模型中心 | PASS | 模型列表正常；`qwen2.5:0.5b` 可选 |
| Playground（A 直连） | PASS | HTTP 200，流式 21.3s 完成，发送按钮复位 |
| Playground（B 自动编排） | PASS | 提示「由 OpenLLM 判断是否装配 画像/记忆/知识库」，HTTP 200，9.3s 完成 |
| 知识库列表 / RAG 对话 | PASS | 9 个知识库；RAG 回答完整，SSE 3.5s 内关闭，停止态消失、可继续提问 |
| 记忆列表 / 搜索 / 写入 | PASS | 10 行；关键字过滤生效；空提交提示「请输入记忆内容」 |
| 记忆图谱 | PASS | P-02 已修复：worker 纳入编排常驻，`outbox_pending` 2860→0、死信 0，5 节点/3 边正常渲染 |
| 平台用户/角色/租户/监控/日志 | PASS | 用户 115 行、角色 5 行、租户 8 行；监控与日志页正常渲染 |

## 4. 问题清单

| 编号 | 级别 | 问题 | 处置 |
|---|---|---|---|
| P-01 | 中 | DPS/仪表盘页面冷启动首屏数据 3~12s，期间仅显示骨架屏；前端 15s 超时虽可兜底，但余量偏小 | **已修复**（v1.1.0）：编排器 `Invoke-StackWarmup` 预热 6 个首屏端点（实测 281~723ms）+ DPS 启动加载模板注册表；见 §5、`doc/test/evidence/ops/startup-warmup-20261118-025109.json` |
| P-02 | 中 | `service-orchestrator.ps1` 未拉起 OpenMemory 图投影 worker，导致记忆图谱页长期 `outbox_pending=3057`、节点为 0 | **已修复**（v1.1.0）：新增 `openmemory-graph-worker`（`Kind=worker`、心跳 + PG advisory lock 单实例）；积压 2860→0、死信 0；见 §5、`doc/test/evidence/ops/p01-p02-verify-20261118.json` |
| P-03 | 低 | RAG 代理 SSE 依赖上游主动断连；若上游在 `done` 后保持连接，下游会等到超时 | 已修复（防御性终止），见 §5 |

## 5. 修复记录（P-01 / P-02 / P-03）

### 5.1 P-03：RAG SSE 防御性终止

**文件**：`openbase/modules/rag_proxy/__init__.py` `_forward_sse`

- 识别 `event: done` / `event: error` 为终止事件；转发完该事件块（下一个空行）后主动 `return` 结束下游流，不再等待上游断开。
- 保留既有事件透传与观测逻辑，不改变事件内容。

### 5.2 P-01：首屏冷启动预热

**文件**：`scripts/service-orchestrator.ps1`、`DPS/src/rest_api/app.py`

- 编排器新增 `Invoke-StackWarmup`：全服务健康后以 `admin` 身份登录并串行请求首屏 6 端点（用户数、Dashboard KPI、模板、画像、知识库、记忆），单端点 30s 超时、失败不阻断启动，证据落 `doc/test/evidence/ops/startup-warmup-*.json`；可用 `-SkipWarmup` 关闭。
- DPS 新增 `_warmup_template_registry`：启动即执行 `SELECT 1` 并加载 `TemplateRegistry`（复用 `routes_profiles` 单例），日志 `画像模板注册表预热完成: {'loaded': 5, ...}`；失败仅告警，请求路径 `is_loaded()` 兜底。
- 实测：6 端点全部 200，281~723ms；DPS 首访模板/画像接口 68.95ms / 48.06ms。

### 5.3 P-02：图投影 worker 纳入编排

**文件**：`scripts/service-orchestrator.ps1`、`OpenMemory/scripts/graph_projection_worker.py`、`OpenMemory/src/openmemory/storage/relational_store.py`

- 编排器新增 `Kind='worker'` 服务类型与 `openmemory-graph-worker`（依赖 openmemory），`Start/Stop/Status/Monitor/CheckAll` 均按心跳判定，不依赖监听端口。
- worker 新增 PG 会话级 advisory lock 单实例互斥（`openmemory.graph_projection_worker`）与原子心跳文件；`--once` 不取锁、不写心跳。
- 实测：积压 2860→0、死信 0；重复启动第二实例记录 `holds lock` 后退出码 0；`stop` 后无残留进程。

**测试**：`tests/test_specialized_proxy_upstream_observe.py`

- 新增 `test_sse_closes_downstream_after_done_even_if_upstream_stays_open`：上游发送 `done` 后永久阻塞，断言代理 2s 内结束。
- 修复前 RED（`TimeoutError`），修复后 GREEN；`tests/test_rag_proxy.py` 定向回归 28 passed。
- 实测：RAG 对话 HTTP 200、流 3.5s 关闭、停止态消失、重新输入后可再次发送。

## 6. 残余风险与建议

1. **冷启动延迟**：DPS 模板/画像首查仍可能 7~12s，建议后续增加启动预热或缓存，前端继续保留 15s 超时。
2. **图投影 worker**：建议在编排脚本中增加 `openmemory-graph-worker` 常驻服务，并在 `-Action status` 中暴露其存活状态。
3. **本轮未做破坏性写入**：标注创建、模板保存、模型删除等写操作仅验证到表单/按钮态，未实际提交，避免污染 Dev 数据。

## 7. 结论

全栈服务可稳定拉起，前端 89 个路由与 8 组关键流程均可用；A/B 双通道（直连 / 自动编排）与 RAG 流式对话验证通过。本轮仅有一处代码修复（SSE 终止加固），其余为冷启动与运维编排层面的改进项。
