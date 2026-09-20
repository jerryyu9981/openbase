# OpenBase 部署执行与上线检查报告 - v1.4.7

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.7 |
| 文档版本 | v1.0.1 |
| 状态 | **[Approved]**（上线发布批准：2026-09-20） |
| 执行 | DO-OpenBase-Ops / OE-OpenBase-Pro |
| 日期 | 2026-09-20 |
| 存放 | doc/release/ |

---

## 1. 部署执行记录（5.4）

| 步骤 | 命令 | 实际结果 |
|------|------|---------|
| 依赖端口核验 | `TcpClient` 直连 127.0.0.1:5432 / 6379 / 8000（超时 2s） | **5432 = OPEN**（PostgreSQL）；**6379 = CLOSED**（Redis 不可达，缓存降级容忍，非阻塞）；**8000 = CLOSED**（无既有 OpenBase 实例，符合发布前状态） |
| 后端启动 | `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8010` | ✅ 启动成功（PID 5416），`GET /health` → **200** `{"status":"ok"}`，**10s 内就绪** |
| 后端实例回收 | `proc.terminate()` | ✅ 已终止（returncode=1，端口释放，无残留进程） |
| 前端构建 | `npm run build`（`vue-tsc --noEmit && vite build`） | ✅ **退出码 0**，`✓ built in 1m 41s`；`dist/` 产物 **157 个文件 / 3,061,080 B**（最大：`echarts` 1,036,306 B、`element-plus` 1,034,658 B、`index.css` 362,235 B、`index.js` 104,001 B；`LogsView` 15.81 kB / gzip 5.44 kB） |
| 构建环境 | `node -v` / `npm -v` | node **v22.16.0** / npm **10.9.4** |
| 制品形态 | — | 源码交付（Python 后端 + Vue3 前端静态产物）；**无镜像构建**（沿用项目现行交付形态） |
| 数据库迁移 | — | **本版本无 DB schema 变更**（无新增/修改 migration），迁移步骤不适用，依据见《OpenBase-数据运维说明-v1.4.7》 |

**证据文件**

| 文件 | 内容 |
|------|------|
| `doc/test/evidence/v147/deploy-verify-v1.4.7.txt` | 端口可达性 + 启动 + 端点探测 + 回收，全流程原文 |
| `doc/test/evidence/v147/deploy-uvicorn-8010.log` | 后端实例运行日志（含 startup 信息） |
| `doc/test/evidence/v147/ui-build-release-v1.4.7.txt` | 前端构建全量输出（含产物清单与体积） |

## 2. 上线验证（关联 TT-ID）（5.5）

| # | 验证项 | 关联 TT-ID | 命令 / 方式 | 实际结果 | 结论 |
|:-:|--------|:----------:|------------|---------|:---:|
| 1 | 后端健康检查 | TT-147-001 | `GET /health` | **200** `{"status":"ok"}` | ✅ 现场 |
| 2 | 鉴权门禁（模块列表未带 token） | TT-147-001 | `GET /api/v1/modules` | **401** `AUTH_401`「missing bearer token」+ `request_id` | ✅ 现场 |
| 3 | 日志检索鉴权门禁 | TT-147-004 | `GET /api/v1/logs/search?limit=1` | **401** `AUTH_401` + `request_id` | ✅ 现场 |
| 4 | 参数校验契约 | TT-147-002 | `POST /api/v1/auth/login`（空体 `{}`） | **400** `PARAM_400` + 字段级 `detail`（username/password required） | ✅ 现场 |
| 5 | API 文档可达 | TT-147-001 | `GET /docs` | **200**（Swagger UI 页面） | ✅ 现场 |
| 6 | 四仓日志可检索 | TT-147-006 | BL-147-05 集成用例（实环境四源检索） | 四仓 **4/4** 命中 | ✅ 复验 Step 4 证据 |
| 7 | 业务路径串联一致性 | TT-147-005 | 判据 1（`-PerFamily 10` 抽样） | 业务路径 **22/22** 命中、命中率 **1.0**、40/40 带回 `X-Request-Id` | ✅ 复验 Step 4 证据 |
| 8 | JSONL 契约一致性 | TT-147-004 / 007 | 判据 3（四仓 JSONL 契约） | 合法率 **100%**、`status_code` 非数字计数 **0** | ✅ 复验 Step 4 证据 |
| 9 | 四仓专项单测复跑 | TT-147-009 | 逐仓 pytest（DPS/OpenLLM/OpenMemory/OpenRAG） | **36/36 passed**（10/7/12/7） | ✅ 复验 Step 4 补跑证据 |
| 10 | 本仓全量回归 | TT-147-008 / 010 | `python scripts/run_regression.py --cov` | **`passed=1008 / failed=0 / skipped=4`**（85 文件 / 29 组，退出码 0） | ✅ 现场（本发布批次内复跑） |
| 11 | 日志命名规范脚本 | TT-147-002 | `tests/test_r384_repo_log_naming.py`（13 例） | 全通过（Step 4 出证） | ✅ 复验 Step 4 证据 |
| 12 | 前端构建与可托管 | TT-147-008 | `npm run build` | 退出码 0，`dist/` 157 文件可托管 | ✅ 现场 |

**上线验证：12/12 通过**（**5 项为本次实环境现场核验**：健康、鉴权 401、参数 400、/docs、前端构建与全量回归；**7 项以 Step 4 已留证证据复验**：四仓 E2E 与判据 1/3 需五方服务与四仓运行态日志，Dev 单机窗口不具备重放条件，故按同版本证据复验，符合「不得用部署成功替代上线验证」的留证要求）。

## 3. 监控 / 日志 / 告警检查（5.6）

| 项 | 结果 |
|----|------|
| 日志 | ✅ 结构化日志 + `request_id` 串联（现场探测返回体均含 `request_id`，如 `req-f6933f891df8`）；应用日志 JSONL 契约由判据 3 保障（四仓合法率 100%） |
| 日志脱敏 | ✅ 沿用 v1.4.6 基线（Bearer / `sk-*` / AKIA 等凭据不落日志；响应采集默认关闭 + 强制脱敏，生产永久关闭红线 4 由本次新增的 `capture_*_enabled` 护栏用例守护） |
| 指标 | ⚠️ Dev 环境无外部监控面板（内存降级模式）；**Pro 环境按 `observability-standards` 配置 RED 指标**（Rate/Errors/Duration），未在本窗口执行 |
| 告警 | ⚠️ Dev 环境未配置告警通道；**Pro 环境按标准配置**（P0 15min 电话 / P1 1h IM / P2 24h IM / P3 邮件），责任人与演练要求见《OpenBase-回滚方案与运维手册-v1.4.7》 |
| Tracing | ⚠️ `otel_enabled` / `langfuse_enabled` 默认关闭（Dev 未启用，属既有设计）；Pro 启用时机由运维窗口决定 |
| 可观测性就绪度 | ✅ 四仓日志 JSONL 契约 + 串联一致性证据齐备（R-384 收官），关键路径可观测 |

## 4. 性能 / 安全上线检查（5.7）

| 项 | 结果 |
|----|------|
| 性能 | ✅ 本版本无业务逻辑新增（开关 + 策略分支 + 脚本），全量回归 **1008 passed / 0 failed / skipped 4** 无退化；前端构建产物体积与 v1.4.6 基线一致量级（主包 `index.js` 104 kB / gzip 39.66 kB）。**Chunk 体积提示**：`element-plus` 1,034.66 kB（gzip 337.05 kB）、`echarts` 1,036.31 kB（gzip 343.41 kB）分块偏大 → 属既有基线（非本版本引入），已列为观察项，不阻塞上线 |
| 安全（密钥） | ✅ 无密钥落库/落日志/落文档：`.env*` 排除；`OPENBASE_JWT_SECRET` 无内置弱默认（production 强制 ≥32 字符，弱值启动即拒绝，由本次新增 3 例护栏守护）；`deploy_pro.ps1` 对弱密钥直接抛错 |
| 安全（鉴权/权限） | ✅ 现场实测：无 token 访问受保护接口 → **401 `AUTH_401`**；参数非法 → **400 `PARAM_400`**，错误体统一契约 `{code, message, detail, request_id}` |
| 安全（采集红线） | ✅ `capture_response` / `capture_upstream` 在 `production` 永久关闭（`env != "production"` 才生效，护栏用例覆盖） |
| 依赖风险 | ✅ 本版本无新增第三方依赖（后端无新增；前端 `package-lock.json` 未变更）；Critical 依赖告警沿用既有基线 |
| TLS / CORS | ⚠️ Dev 环境直连 `127.0.0.1` 无 TLS；Pro 环境按部署架构草案由网关终结 TLS，CORS 白名单在 Pro 配置中显式声明（未在本窗口执行） |

## 5. 发布制品与标签证据（已回填）

| 项 | 值 | 验证 |
|----|----|------|
| 发布分支 | `main` | ✅ `git rev-parse HEAD` = `8d22302c29801131ec981a76a1b868d8b4c192d1` |
| 发布 commit | **`8d22302`**（`docs(v1.4.7): 运维审计输入清单 v1.0.1（后端日志未入库如实更正）`，2026-09-20 21:59:16） | ✅ 与本地 HEAD 一致 |
| 注释标签 | **`v1.4.7`** → tag object `b29ae9e6a1fc74cfd9806f1a8fbeb84cf9a638c7`，peel 至 `8d22302`（`git cat-file -t` = `tag`） | ✅ `git rev-parse v1.4.7` / `'v1.4.7^{commit}'` |
| origin 推送 | `738472e..8d22302  main -> main`；`* [new tag] v1.4.7 -> v1.4.7` | ✅ `git ls-remote origin`：`refs/heads/main = 8d22302`、`refs/tags/v1.4.7 = b29ae9e6` |
| backup 推送 | `738472e..8d22302  main -> main`；`* [new tag] v1.4.7 -> v1.4.7` | ✅ `git ls-remote backup`：`refs/heads/main = 8d22302`、`refs/tags/v1.4.7 = b29ae9e6` |
| github 推送 | **N/A** | 本项目**无 `github` 远程**（`git remote -v` 仅 origin + backup；`remote.github` 为空串配置）→ 维持豁免，见《发布复盘与问题跟踪记录》R5/I5 |
| 备份动作偏差 | 未执行 `git push --mirror`；改以非破坏式 `push main + tag` 完成归档 | backup 仓含 `refs/remotes/*`，mirror 会删除远端 ref（破坏性）——依据登记于《回滚方案与运维手册》§4 T5 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-20 | DO-OpenBase-Ops | 初始创建：部署执行记录（依赖端口 5432 OPEN / 6379 CLOSED / 8000 CLOSED、后端 8010 健康 200 并回收、前端构建退出码 0 与 dist 明细）+ 上线验证 **12/12**（5 项现场 + 7 项 Step 4 证据复验，关联 TT-147-001~010）+ 监控/日志/告警检查 + 性能/安全上线检查；标签证据待发布时回填 |
| v1.0.1 | 2026-09-20 | DO-OpenBase-Ops | **标签证据回填**：§5 由「待回填」改为实测值——发布 commit `8d22302`、附注标签 `v1.4.7`（`b29ae9e6` → `8d22302`）、origin/backup 推送输出原文与 `ls-remote` 双远程 hash 一致（`main=8d22302`、`tag=b29ae9e6`）；`github` 项标注 **N/A**（无该远程，维持豁免）；备份动作偏差（未执行 mirror）附依据；状态置 **[Approved]**；文档版本 v1.0.0 → **v1.0.1** |
