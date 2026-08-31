# OpenBase Release Note - v1.4.5

| 项目 | 内容 |
|------|------|
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Final] |
| 发布人 | OP-OpenBase-Dev |
| 发布日期 | 2026-09-01 |
| 存放 | doc/release/ |

---

## 1. 版本概述

**DPS 对接（对接线第 3 站）**：OpenBase 与 DPS（数据画像系统）完成对接，新增 dps-proxy 代理模块（8 端点 + 身份头注入），前端画像列表/详情 2 页真实化。DPS Header 身份认证形态：OpenBase JWT 唯一认证入口 + 四头注入（X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role），映射表 + default 兜底。

## 2. 变更清单

| 类别 | 变更 | 关联 |
|------|------|------|
| 新增 | dps-proxy 模块（画像列表/详情/计算、标签分类、报表概览、批量任务状态、审计日志、健康透传） | R-381，FR-145-01~06 |
| 新增 | 身份头注入：X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role（JWT → 四头，映射 + 兜底） | AC-145-02-2 |
| 新增 | settings 配置 dps_* 6 项（dps_upstream_base=8030/timeout/default_*/map） | TD-145-02 |
| 新增 | 前端 dps.ts API 层 + 画像列表/详情 2 页真实化（KPI/搜索/分页/错误态） | TD-145-04 |
| 还债 | llm.ts sendChatStream 对齐 fetch adapter（浏览器端真流式） | TD-新增-011 已偿还 |
| 排除 | 四维身份专项（挂起后续处理）；DPS 侧 config 缺陷（登记任务书 M4）；无 SSE（DPS 无流式） | 规划声明 |

## 3. 兼容性说明

| 项 | 说明 |
|----|------|
| 既有端点 | llm_proxy/rag_proxy/memory_proxy/gateway 无破坏性变更（全量回归通过） |
| 前端 | 不直连 DPS（走 OpenBase dps-proxy）；http.ts 统一响应兼容 |
| 配置 | 新增 dps_* 可选配置（不配置则默认 8030）；无新增必填项 |
| 数据库 | 无 DB 变更（DPS 数据为上游系统） |

## 4. 测试与验证结论

| 项 | 结果 |
|----|------|
| 后端测试 | pytest 15/15（dps-proxy）+ 全量回归 100% |
| 覆盖率 | 86%（dps_proxy ≥80% 门禁） |
| L3 冒烟 | 11/11（门禁 + 8 端点 502 归一化） |
| T3a/E2E/UAT | 画像 2 页渲染 + 错误态符合设计 |
| 环境遗留 | DPS 8030 未就绪（config 缺陷 M4）→ 502 归一化已验证，真实联调留 DPS 修复后 |

## 5. 部署目标

| 环境 | 端口 | 说明 |
|------|:---:|------|
| OpenBase 后端 | 8000 | uvicorn demo_app（含 dps_proxy） |
| DPS 后端 | 8030 | API_PORT=8030（待 M4 修复） |
| OpenBase 前端 | 5173 / dist | vite dev / build 静态 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-01 | OP-OpenBase-Dev | 初始创建：v1.4.5 DPS 对接发布说明（8 端点 + 四头注入 + 还债 TD-新增-011 + 环境遗留 M4 声明） |
