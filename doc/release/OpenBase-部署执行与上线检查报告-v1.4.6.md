# OpenBase 部署执行与上线检查报告 - v1.4.6

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.6 |
| 文档版本 | v1.0.1 |
| 状态 | [Approved] |
| 执行 | OP-OpenBase-Ops |
| 日期 | 2026-09-16 |
| 存放 | doc/release/ |

## 1. 部署执行记录

| 步骤 | 命令 | 结果 |
|------|------|------|
| 后端启动 | `python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000` | ✅ 监听 127.0.0.1:8000（PID 8988），`GET /health` → **200 {"status":"ok"}** |
| 前端（Dev） | `npm run dev`（openbase-ui，Vite 6.4.3） | ✅ 监听 localhost:5173（PID 11164） |
| 前端构建产物 | `npm run build` → `openbase-ui/dist/` | ✅ dist 产物存在（vue-tsc 类型校验 + vite build） |
| 前端（生产预览） | `npx vite preview --port 5173` 或 Nginx 托管 dist/ | ✅ dist 就绪，可由 preview/Nginx 托管 |
| 数据库 | PostgreSQL 5432 监听中 | ✅（连接波动 PG-ENV 已登记，内存降级兜底） |
| Redis | 6379 | ⚠️ 不可达（缓存降级，conftest 容忍，非阻塞） |

## 2. 上线验证（关联 TT-ID）

| # | 验证项 | 关联 TT-ID | 命令/方式 | 实际结果 | 结论 |
|:-:|--------|-----------|-----------|---------|:---:|
| 1 | 后端健康检查 | TT-146-004 | GET /health | **200** {"status":"ok"} | ✅ |
| 2 | 前端可访问 | TT-146-027 | GET localhost:5173/ | **200**（页面渲染） | ✅ |
| 3 | 登录端点 | TT-146-005 | POST /api/v1/auth/login | 400（空请求体，符合校验契约 PARAM_400） | ✅ |
| 4 | 日志中心检索 | TT-146-022 | GET /api/v1/logs/search（log:read） | Step 4 实环境 **200**（四源，repo_log 4937 条） | ✅ |
| 5 | 日志中心页面 | UAT-146-08 | 前端 /system/logs 走查 | 20 行/共 4977 条，无错误提示 | ✅ |
| 6 | IA 三分导航 + 四域 | UAT-146-10~15 | 前端顶层导航走查 | 仪表盘/业务模块/平台管理三分 + 四域归并 | ✅ |
| 7 | 旧路径兼容重定向 | TT-146-029 | 旧路由访问 | 无 404，重定向至新位置 | ✅ |
| 8 | 权限门禁 | TT-146-主体 | 无 `log:read`/`module:manage` 访问 | 403`PERM_403` / 404`PARAM_404` 统一契约 | ✅ |
| 9 | 导出留痕 | TT-146-030 | GET /api/v1/logs/export | CSV/JSON 导出 + `log.export` 留痕（Step 4 验证） | ✅ |
| 10 | T3a 全页面巡检 | TT-146-031 | Playwright 遍历 110 路由 | **110/110** 无错误（Step 4 证据） | ✅ |

**上线验证：10/10 通过**（6 项实环境现场核验 + 4 项以 Step 4 证据复验）

## 3. 监控/日志/告警检查（5.6）

| 项 | 结果 |
|----|------|
| 日志 | ✅ 结构化日志（uvicorn + 业务日志带 request_id）；日志中心服务端脱敏（Bearer/sk-*/AKIA* 等凭据不落日志） |
| 指标 | ⚠️ Dev 环境内存降级模式无外部监控面板；Pro 环境按 observability-standards 配置 |
| 告警 | ⚠️ Dev 环境未配置告警通道；Pro 环境按标准（P0 15min 电话/P1 1h IM） |
| 可观测性 | ✅ 四仓日志 JSONL 结构化契约就绪（R-384，本仓 adapter 接入） |

## 4. 性能/安全检查（5.7）

| 项 | 结果 |
|----|------|
| 性能 | ✅ Step 4 巡检无阻塞退化；facets 性能 7.3~14.6s 已登记（TD-新增-018 同族性能治理，不阻塞上线） |
| 安全 | ✅ 密钥不落日志/不落配置；`audit_db` 不可用显式 503 `SYS_503`；参数校验 400`PARAM_400`；日志脱敏覆盖 `summary.message`/`raw.line`；响应采集默认关闭+强制脱敏 |

## 5. 发布制品与标签证据

| 项 | 值 | 验证 |
|----|----|------|
| 发布分支 | main | ✅ |
| 发布 commit | `bfc0572e63e7b0bb99855f195e9e2cf84ee15b5e` | ✅ 与本地 HEAD 一致 |
| 注释标签 | `v1.4.6` → `6e86d7d7679222e655ef202622cf7e547ba031db`（指向 bfc0572） | ✅ |
| origin 推送 | `refs/heads/main` = bfc0572（`4b95f02..bfc0572` 快进）；`refs/tags/v1.4.6` = 6e86d7d7 | ✅ |
| backup 推送 | `refs/heads/main` = bfc0572（`4b95f02..bfc0572` 快进）；`refs/tags/v1.4.6` = 6e86d7d7 | ✅ |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-16 | OP-OpenBase-Ops | 初始创建：部署执行 + 上线验证 10/10 + 监控/性能/安全检查 |
| v1.0.1 | 2026-09-16 | OP-OpenBase-Ops | 回填发布制品与标签证据（commit bfc0572 + tag v1.4.6 双远程推送）；状态置 [Approved] |