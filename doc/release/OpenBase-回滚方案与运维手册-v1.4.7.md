# OpenBase 回滚方案与运维手册 - v1.4.7

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.7 |
| 文档版本 | v1.0.1 |
| 状态 | **[Approved]**（随 v1.4.7 Dev 发布完成） |
| 作者 | DO-OpenBase-Ops / OE-OpenBase-Pro |
| 日期 | 2026-09-20 |
| 存放 | doc/release/ |

---

## 1. 回滚方案（5.8）

### 1.1 回滚基线与目标版本

| 项 | 值 | 实测依据 |
|----|----|---------|
| 回滚目标版本（上一发布） | **tag `v1.4.6` → commit `bfc0572`**（2026-09-16 `chore(v1.4.6): 版本配置与路线图同步`） | `git rev-parse --short 'v1.4.6^{commit}'` → `bfc0572` |
| 当前本地 HEAD（待发布起点） | **`ac3a5b2`** | `git rev-parse --short HEAD` |
| 远端基线（origin / backup 的 `main`） | **`738472e`**（本地领先 **9** 个提交、**0** 落后，无分叉） | `git ls-remote origin refs/heads/main` / `backup refs/heads/main` 均为 `738472e…`；`git merge-base --is-ancestor origin/main main` → 0 |
| 待发布 tag | **`v1.4.7`（尚未创建）** | `git tag -l 'v1.4*'` → v1.4.2~v1.4.6（无 v1.4.7） |
| 单文件回滚可用性 | ✅ 可用 | `git cat-file -e 'v1.4.6:openbase/settings.py'` / `'v1.4.6:openbase/modules/rag_proxy/__init__.py'` → exit 0 |

### 1.2 部署策略与对应回滚路径

| 环境 | 部署策略 | 回滚路径 | 预期耗时 |
|------|---------|---------|:--------:|
| Dev | **直接部署**（`uvicorn` 起停 + 源码切换） | 停实例 → `git checkout v1.4.6`（或 `git revert`）→ 重启 → 健康检查 | 2~5 分钟 |
| Test | 直接部署 | 同 Dev（含回归复测） | 5~10 分钟 |
| Pro | **蓝绿**（`scripts/deploy_pro.ps1 -Env pro -Strategy bluegreen`：Green 端口 = `Port+1`，健康检查最多 60s，登录验证后由 LB 切流） | **LB 流量切回 Blue（<30s）** → 停 Green 实例；必要时 `git checkout v1.4.6` 重建 | **<5 分钟** |
| Pro（备选） | 金丝雀（`-Strategy canary`） | 阶段 1/2：立即把流量降回旧版本（<30s）；阶段 3：同蓝绿 | <5 分钟 |

> 本版本为 **Dev 发布**；Pro 路径为方案留存，未在本窗口执行（Pro 发布须另行批准，见 §1.5）。

### 1.3 回滚触发条件

| 类型 | 条件 | 处置 |
|------|------|------|
| 自动 | `/health` 或 `/ready` 非 200（连续 3 次，间隔 10s） | 蓝绿/金丝雀场景自动回滚；直接部署场景人工确认 |
| 自动 | 5xx 错误率 > 1%（5 分钟滑窗，或环比 +500%） | 自动回滚 |
| 自动 | 发布后 10 分钟内核心功能冒烟失败 | 自动回滚 |
| 半自动 | P99 延迟 > 基线 +50%；CPU/内存持续 >90% | 告警 → 人工确认 |
| 手动 | 发现 P0/P1 缺陷、数据异常（脏数据）、安全/合规要求、性能显著退化 | 按审批流程回滚 |

### 1.4 回滚命令（按对象）

| 对象 | 命令 | 说明 |
|------|------|------|
| 代码（推荐，保留历史） | `git revert <hash>` | 生成反向提交，共享分支安全 |
| 代码（整版回退） | `git checkout v1.4.6` / `git reset --hard v1.4.6`（**仅本地**） | 禁止在共享分支使用 `reset --hard` 后强推 |
| 单文件恢复 | `git checkout v1.4.6 -- openbase/modules/rag_proxy/__init__.py` | 已实测该路径在 v1.4.6 存在 |
| 配置（本版本关键开关） | 将 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS` 置为 `true`（默认值）或删除该 env | **回到 v1.4.6 语义（注入身份头）**；改动为编排器 env 一处，无需改代码 |
| 服务（Dev） | `Stop-Process -Id <PID>` → 重启 `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000` | 现场已演练启停与端口释放 |
| 服务（Pro 蓝绿） | LB 切流回 Blue → 停 Green | 由运维执行，<30s |
| 数据回滚 | **不适用** | 本版本**无 DB schema 变更、无 migration、无数据写入逻辑变更**（依据见《OpenBase-数据运维说明-v1.4.7》§2） |
| 缓存/消息 | 无缓存 key 结构变更；Redis 在当前 Dev 环境不可达（降级容忍） | 如需清缓存：`redis-cli DEL <prefix>*`（Pro 环境谨慎执行） |
| 跨仓回滚 | 四仓各仓独立回滚：DPS（`0954b9a` P1 修正 / `145d858`）、OpenLLM（`0c44c26`）、OpenMemory（`6d18e49`）、OpenRAG（`390f5dd`） | 各仓按自身流程 `git revert`，OpenBase 不代回滚他仓 |

### 1.5 审批与权限

| 环境 | 回滚类型 | 审批要求 |
|------|---------|---------|
| Dev | 代码/配置/服务 | 开发者自决（记录于问题跟踪记录） |
| Test | 全部 | 审查者审批 |
| Pro | 代码/服务 | **发布负责人 + PM 双签** |
| Pro | 数据回滚 | **发布负责人 + DBA + PM 三签** |
| Pro | 配置回滚 | 发布负责人 + 运维双签 |
| Pro | **P0 紧急回滚** | 可由发布负责人/运维管理员一键触发，**2 小时内补录审批材料 + 24 小时内输出 RCA** |

> 发布负责人：`DO-OpenBase-Ops`；Pro 审批人：`OE-OpenBase-Pro` + `PM-OpenBase-Dev`（用户）；审计：`AU-OpenBase-Ops`。

### 1.6 回滚后验证（强制）

| 验证项 | 方法 | 通过标准 | 时限 |
|--------|------|---------|:----:|
| 服务健康 | `GET /health` | 200 `{"status":"ok"}` | 回滚后 15 分钟内 |
| 核心接口 | 冒烟：鉴权门禁 401 / 参数契约 400 / 受保护接口可达 | 契约与回滚前一致 | 同上 |
| 错误率 / 延迟 | 监控面板（Pro） | 5xx <0.1%、P99 回到基线 | 同上 |
| 数据一致性 | 无 DB 变更 → 无需数据校验（如发生数据回滚则必须二次备份后校验） | — | — |

> **未在 15 分钟内完成验证视为回滚失败，必须升级 P0 处理**；回滚原因与影响须在 5 分钟内记录到《OpenBase-问题跟踪记录》。

## 2. 回滚演练记录（5.8）

| # | 演练项 | 方式 | 结果 |
|:-:|--------|------|------|
| 1 | 回滚基线可解析 | `git rev-parse 'v1.4.6^{commit}'` | ✅ `bfc0572`（2026-09-16） |
| 2 | 单文件回滚可用性 | `git cat-file -e 'v1.4.6:openbase/settings.py'`、`…rag_proxy/__init__.py` | ✅ 两者均 exit 0（路径在 v1.4.6 存在） |
| 3 | 服务启停与端口释放 | 启动 8010 实例 → 健康 200 → `terminate()` | ✅ 启动 10s 就绪、终止后无残留进程（`deploy-verify-v1.4.7.txt`） |
| 4 | 配置回滚等价性 | 开关 `rag_inject_identity_headers` 默认 `true` = v1.4.6 语义 → 不改代码即可回退行为 | ✅ 由 `tests/test_rag_proxy_identity_policy.py` / `test_bl147_trust_env_wiring.py` 护栏保证（7 例） |
| 5 | 数据回滚演练 | — | **不适用**（无 DB 变更；已在 §1.4 给出依据） |
| 6 | 蓝绿自动切回演练 | — | **不适用**（Dev 无 LB/Blue-Green 环境；Pro 演练须在 Pro 窗口执行，已列入 §4 移交项） |
| 7 | 远端 hash 与本地关系核对 | `git ls-remote` + `merge-base --is-ancestor` | ✅ origin/backup = `738472e` 为本地祖先，**无分叉**，回滚/推送均为快进安全操作 |

**演练结论：本地可执行项 5/5 通过；数据回滚与蓝绿自动切回因环境不具备而标记不适用（依据已给出），Pro 侧演练列入运维移交待办。**

## 3. 运维手册（5.9）

### 3.1 服务清单与端口

| 服务 | 端口 | 启动命令 | 健康检查 |
|------|:----:|---------|---------|
| OpenBase 后端 | 8000（Dev 主）/ 8010（核验实例） | `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000` | `GET /health` → 200 `{"status":"ok"}` |
| OpenBase 前端（Dev） | 5173 | `npm run dev`（`openbase-ui/`） | 浏览器访问 `/` |
| OpenBase 前端（静态产物） | 由 Nginx/preview 托管 | `npm run build` → `dist/`（157 文件 / 2.92 MB） | `npx vite preview --port 5173` |
| PostgreSQL | 5432 | 外部依赖（当前可达） | `TcpClient 127.0.0.1:5432` |
| Redis | 6379 | 外部依赖（**当前不可达，缓存降级容忍**） | `TcpClient 127.0.0.1:6379` |
| 四仓（DPS/OpenLLM/OpenMemory/OpenRAG） | 各仓自管 | 各仓自有启动方式（不属本仓运维范围） | 各仓 `/health` |

### 3.2 常见故障与处置

| 现象 | 可能原因 | 处置 |
|------|---------|------|
| 启动即失败（production） | `OPENBASE_JWT_SECRET` 缺失/弱值 | 生成强密钥：`python scripts/gen_jwt_secret.py`；≥32 字符且非占位值 |
| 401 `AUTH_401`（业务侧） | 缺少/过期 Bearer token | 检查 `Authorization` 头与 token 有效期（`OPENBASE_JWT_EXPIRE_SECONDS`） |
| 400 `PARAM_400` | 请求体字段缺失/类型不符 | 按 `detail` 字段级提示修正 |
| `/api/v1/logs/*` 返回 401/403 | 缺少 `log:read` 权限 | 授予对应权限码 |
| Redis 连接失败 | 6379 不可达 | 缓存降级（容忍）；Pro 环境检查 `OPENBASE_REDIS_URL` |
| rag-proxy 调 OpenRAG 返回 400 | 保留租户码碰撞（DEF-BE-147-005 根因） | 联调保持 `OPENBASE_RAG_INJECT_IDENTITY_HEADERS='false'`（方案 B）；**根因消解由 R-387 落地**（见候选需求池 §1.16） |
| 前端页面空白 / 路由告警 | 模块注册表未预热 | 检查冷启动预热链路（S6-T2-1(B) 护栏覆盖） |

### 3.3 排障命令速查

```powershell
# 健康与契约
Invoke-RestMethod http://127.0.0.1:8000/health
# 端口占用
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
# 依赖端口
(New-Object System.Net.Sockets.TcpClient).Connect('127.0.0.1', 5432)
# 环境校验（项目脚本）
python scripts/verify_repo_log_naming.py --help
# 全量回归
python scripts/run_regression.py --cov
# 版本/标签
git tag -l 'v1.4*'; git ls-remote origin refs/tags/v1.4.7
```

### 3.4 SLO / SLA 与可观测性

| 项 | 目标 | 现状 |
|----|------|------|
| 可用性 SLO | Pro ≥99.9%（月） | Pro 未在本次窗口部署；Dev 已就绪 |
| 延迟 SLO | P99 < 基线 +50% | 本版本无业务逻辑新增，回归无退化 |
| 错误率 SLO | 5xx <0.1%（生产） | 由监控面板（Pro）保障 |
| 观测量 | 结构化 JSONL 日志 + `request_id` 全链路串联 | ✅ 四仓 JSONL 契约收官（判据 3 合法率 100%） |
| 告警 | P0 15min 电话 / P1 1h IM / P2 24h IM / P3 邮件 | ⚠️ Dev 未配置；Pro 待配置（移交项 T3） |

### 3.5 联系人

| 角色 | 代号 | 职责 |
|------|------|------|
| 发布负责人 | `DO-OpenBase-Ops` | 发布执行、回滚决策发起 |
| Pro 运维 | `OE-OpenBase-Pro` | 生产运维、告警响应、蓝绿切流 |
| 审计 | `AU-OpenBase-Ops` | 运维审计、证据复验 |
| 决策/批准 | 用户（PM） | 上线发布批准、Pro 回滚双签 |

## 4. 运维移交清单（5.9）

| # | 移交项 | 状态 | 备注 |
|:-:|--------|:----:|------|
| T1 | 部署执行与上线检查报告 | ✅ | 本批交付（含实环境核验证据） |
| T2 | 回滚方案 + 演练记录 | ✅ | 本地项 5/5；数据/蓝绿演练不适用说明在案 |
| T3 | Pro 环境监控/告警配置 | ⚠️ 待执行 | 按 `observability-standards`（RED 指标 + 四级告警）；责任人 `OE-OpenBase-Pro` |
| T4 | Pro 蓝绿部署与自动切回演练 | ⚠️ 待执行 | `scripts/deploy_pro.ps1 -Env pro -Strategy bluegreen`；须先满足弱密钥校验与 DB 注入 |
| T5 | 备份远程同步核验 | ✅ 已完成 | origin + backup 的 `main` 与 tag `v1.4.7` 均已同步（`main = 8d22302`、`tag = b29ae9e6`，`git ls-remote` 三处 hash 一致）；**本项目未配置 `github` 远程**（`remote.github` 为空串）→ 三远程模板中 github 项 **N/A**（维持豁免，登记 F1/R5）。备份动作采用**非破坏式** `push main + tag`；**未执行 `git push --mirror`**（backup 仓含 `refs/remotes/*`，mirror 语义会删除远端 ref，属破坏性操作） |
| T6 | 运维手册与排障命令 | ✅ | 本章 §3 |
| T7 | 数据运维说明 | ✅ | 独立文档（无 DB 变更声明 + 依据） |
| T8 | 发布复盘报告 | ✅ | 独立文档（含风险归集检查） |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-20 | DO-OpenBase-Ops | 初始创建：回滚基线与路径（含 `v1.4.6=bfc0572`、本地 `ac3a5b2`、远端 `738472e` 快进关系）+ 触发条件 + 审批矩阵 + 演练记录（5/5 通过、2 项不适用说明）+ 运维手册（服务/故障/排障/SLO/联系人）+ 移交清单（T3/T4 待执行、T5 github N/A） |
| v1.0.1 | 2026-09-20 | DO-OpenBase-Ops | **发布后同步**：§4 **T5 升级为「已完成」**——登记 origin + backup 的 `main`/tag 同步实测（`main=8d22302`、`tag=b29ae9e6`）与**非破坏式备份决策**（未执行 `--mirror`，理由：backup 仓含 `refs/remotes/*` 会被删除）；状态置 **[Approved]**；文档版本 v1.0.0 → **v1.0.1** |
