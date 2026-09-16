# OpenBase v1.4.6 · T3a/T3b 前端轨道环境就绪记录（Step 4 测试 · 前端）

| 项目 | 内容 |
|------|------|
| 文档编号 | OB-TEST-EVIDENCE-ENV-FRONTEND-v1.4.6 |
| 版本号 | v1.4.6 |
| 状态 | [Draft]（证据文件，测试执行中产出） |
| 执行角色 | AT-OpenBase-Test（测试工程师） |
| 执行日期 | 2026-09-15 |
| 适用环境 | 本机沙箱（Windows / Node 22.16.0 / Python 3.10.11） |
| 仓库根 | `d:/Trae CN/myproject/Dev/OpenBase` |
| 前端工程 | `openbase-ui/`（Vue 3 + Vite + Vitest + Playwright） |
| 约束 | 未修改仓库源码与测试文件；临时脚本落 `work/` 工作目录；令牌仅内存使用，不落盘不打印 |

## 1. 进程与端口清单（实测）

| 服务 | 命令 | PID | 端口 | 探活结果 |
|------|------|-----|------|----------|
| 后端（任务指定端口） | `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8011` | 2756 | 8011 | `GET /health` → **200** `{"status":"ok"}` |
| 后端（preview 既有代理目标） | `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000` | 2460 | 8000 | `GET /health` → **200** `{"status":"ok"}` |
| 后端（根因验证用第三方实例） | 同上，`--port 8012` | 9576 | 8012 | `GET /health` → 200（另有 1 次 10048 端口占用失败记录，见 §4） |
| 前端静态服务 | `npm run build` + `npx vite preview --port 4173 --host 127.0.0.1` | 18584（cmd 包装）/ 2060（监听进程） | 4173 | `GET /` → **200**（475 字节 index.html） |
| PostgreSQL | 系统 `postgres`（PID 5024） | 5024 | 5432 | TCP 可连；**应用侧连接被重置**，见 §4 |
| Redis | 未启动 | — | 6379 | 未监听（环境现状已声明） |
| 上游 OpenLLM / OpenRAG / OpenMemory / DPS | 未启动 | — | 8001 / 8002 / 8020 等 | 未监听（环境现状已声明） |

### 1.1 启动日志摘要

**后端（8011 / 8000）** — 启动成功、`/health` 200，日志中持续出现（每 1s 一条）：
```
{"level":"WARNING","module":"openbase.identity.dispatcher","message":"outbox dispatcher loop iteration failed",
 "error":"connection was closed in the middle of operation","request_id":"-"}
{"level":"WARNING","module":"openbase.audit","message":"audit db persist failed (degraded)", ...}
```
即：进程可服务，但 outbox 投递循环与审计落库因 DB 连接异常持续降级重试。

**前端（vite preview）**：
```
> npx vite preview --port 4173 --host 127.0.0.1
  ➜  Local:   http://127.0.0.1:4173/
```
`vite.config.ts` **未做任何改动**：其 `preview.proxy['/api']` 目标为 `http://127.0.0.1:8000`，故额外在 8000 启动同一 `demo_app` 实例以复用既有代理配置（不修改源码的等价做法）。

### 1.2 生产构建（用于静态服务）

```
> npm run build          # vue-tsc --noEmit && vite build
✓ built in 30.99s
EXIT_CODE=0
```
产物：`openbase-ui/dist`（157 个文件，3,061,075 字节 ≈ **2.92 MB**）；最大 chunk：`echarts-*.js` 1012 KB、`element-plus-*.js` 1010 KB。
构建期告警（非阻断）：`src/core/router/index.ts` 同时被静态与动态导入，Vite 提示 `dynamic import will not move module into another chunk`。

## 2. 页面巡检链路（T3a）验证

| 项 | 结果 |
|----|------|
| 静态服务可达 | `http://127.0.0.1:4173/` → 200 |
| 同源代理可达 | `POST /api/v1/auth/login`（经 preview 代理）→ 200，登录成功取得登录态 |
| 登录态注入 | 通过 Playwright `context.addInitScript` 注入 `localStorage.ob_access_token`（仅内存传递，未打印/落盘） |
| `/auth/me` | 200，`username=admin`，`permissions=["*"]` |
| 浏览器 | Playwright 1.63.0（`chromium_headless_shell-1228` 本地已安装） |

## 3. 环境阻塞与处置（如实登记）

| 编号 | 现象（实测） | 归因 | 处置 / 替代验证 |
|------|--------------|------|------------------|
| ENV-FE-01 | 涉 DB 接口异常：`GET /api/v1/tenants` → 500 `SYS_500`；`GET /api/v1/users` → 连接被重置（ECONNRESET）；页面侧表现为请求长时间挂起（测量时仍 pending） | 应用连接串 `db_url = postgresql+asyncpg://<credentials>@localhost:5432/openbase`（凭据已屏蔽）。**raw asyncpg 直连该地址 2/2 次报 `ConnectionDoesNotExistError: connection was closed in the middle of operation`**；同一脚本直连共享库 `192.168.0.151:5432/nuct` 2/2 次成功（`PostgreSQL 14.23`） | 登记为环境阻塞（H 类），不计入 L4 违规；端点为 DB 依赖页（`/platform/identity/tenants`、`/platform/identity/org`、`/platform/identity/users` 等）；替代验证：受控桩（`page.route`）覆盖三态与交互 |
| ENV-FE-02 | `GET /api/v1/logs/search`、`/logs/facets`、`/logs/export` → 403 `AUTH_403 "missing permission: log:read"`（admin 亦如此） | RBAC 路径 2（user→role→permission）需查库；DB 异常 → `PermissionService.permissions_for_with_fallback` 回退内存 `PermissionStore`（空）→ 403；而 `/auth/me` 对 `username=admin` 有 `*` 注入兜底（`openbase/modules/auth/__init__.py:419`）→ 造成「菜单可见 / 接口 403」口径割裂 | 登记为环境阻塞（H 类）；T3b 以受控桩覆盖检索/分页/详情/导出/三态，并对 403 分支做真实硬断言（见 t3b-deep-cases.json） |
| ENV-FE-03 | 上游四服务未启动 | 环境现状 | `/api/v1/{llm,rag,memory}-proxy/*` → 502 `SYS_502 "... upstream unreachable: All connection attempts failed"`；模块页数据态以受控桩验证 |
| ENV-FE-04 | Redis 未启动 | 环境现状 | 无 Redis 依赖页面可正常渲染（未观察到额外失败）；后端 outbox 投递退避重试，事件不丢 |

## 4. 环境阻塞根因证据（可复核）

`work/probe-db-compare.py`（临时脚本，只读仓库配置，屏蔽凭据）实测输出摘要：

```
.env.shared-infra:POSTGRES_URL -> postgresql://<credentials>@192.168.0.151:5432/nuct
--- tcp probe 192.168.0.151:5432 ---  tcp connect: OK
--- asyncpg direct query (3 rounds) --- round1/2/3: connect OK, select 1 -> 1

--- settings.db_url(localhost): postgresql://<credentials>@localhost:5432/openbase ---
  round1: FAIL ConnectionDoesNotExistError: connection was closed in the middle of operation
  round2: FAIL ConnectionDoesNotExistError: connection was closed in the middle of operation
--- shared-infra(192.168.0.151) ---
  round1: OK current_database=nuct   version=PostgreSQL 14.23 ...
  round2: OK current_database=nuct
settings.db_schema=openbase
```

结论：**PostgreSQL 服务端可用**，故障点在 `localhost:5432/openbase` 这条应用连接（TCP 可连、握手后被立即重置），属环境/配置问题，非本次前端改动引入。

## 5. 替代验证与证据索引

| 证据 | 路径 |
|------|------|
| T3a 全页面巡检原始数据 | `doc/test/evidence/v146/t3a-page-scan.json` |
| T3a 汇总与分类统计 | `doc/test/evidence/v146/t3a-page-scan.md` |
| 逐页截图（110 张，含 4 条参数化路由样本） | `doc/test/evidence/v146/screenshots/` |
| T3b 深度用例结果 | `doc/test/evidence/v146/t3b-deep-cases.json` / `.md` |
| 本次前端轨道结构化摘要 | `doc/test/evidence/v146/t3-frontend-summary.md` |

## 6. 修订历史

| 版本 | 日期 | 修订人 | 说明 |
|------|------|--------|------|
| v1.4.6 | 2026-09-15 | AT-OpenBase-Test | 首版：环境就绪、端口/进程、启动日志摘要、环境阻塞与根因证据登记 |
