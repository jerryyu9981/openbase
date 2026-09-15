# Dogfood 探索报告：OpenBase 统一前端（openbase-ui）

| 项 | 值 |
|---|---|
| 目标 | http://localhost:5173 |
| 会话 | obui（agent-browser 0.27.0） |
| 日期 | 2026-09-05 |
| 环境 | 五件套+前端运行中（openllm 8001 / openrag 8010 / openmemory 8020 / oidc 8090 / dps 8030 / openbase 8000 / vite 5173） |
| 账号 | admin / admin123（本地登录，JWT 门禁） |
| 范围 | 登录 → Dashboard → 模块入口初探（自动化受模块内导航限制，未覆盖全页面；API 层功能已在冒烟 S4/P9 实证） |

## 执行记录

- 登录页结构正常（用户名/密码/OIDC 统一登录按钮均渲染）；本地登录成功进入 Dashboard。
- Dashboard 导航含：仪表盘、租户管理、OpenLLM、知识库、记忆、画像、统一网关。
- 逐页截图（screenshots/）：01 登录态、02 Dashboard、03 OpenLLM、04-07 模块入口、08 统一网关内部（模型中心/AI 应用/对话监控/平台联动 + 搜索模型）。
- 浏览器控制台：所覆盖页面**无 JS 错误/4xx/5xx**。
- API 数据层（P9 冒烟，2026-09-05 实证）：画像读写/双租户隔离/重启存活/真实模式 E2E/对话链路均通过。

## 发现

- 无已确认应用缺陷。
- 待复验项：
  1. 模块内导航为独立侧栏/菜单结构，进入"统一网关"后外层入口被替换，以文本"画像"等点击无法从模块内回到顶层模块（疑为 UI 信息架构设计使然或布局 bug，需人工/Playwright 细验）。
  2. agent-browser 该版本 fill/click 需裸 ref（`e4`）而非 `@e4`，属工具用法差异，不影响应用。
- 建议：由独立会话用 webapp-testing/Playwright 对 7 个模块（仪表盘/租户管理/OpenLLM/知识库/记忆/画像/统一网关及其子页）做完整遍历与交互回归，补充截图/视频证据。

## 收尾

- 会话已截图 8 张存档（dogfood-output/screenshots/）。
- 服务与前端保持运行，未改动任何代码。
