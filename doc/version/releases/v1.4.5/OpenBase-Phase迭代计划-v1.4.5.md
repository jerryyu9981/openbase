# OpenBase Phase 迭代计划 - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/version/releases/v1.4.5/ |

---

## 1. Phase 总览

| Phase | 主题 | 周期 | Backlog | 里程碑 | 验收重点 |
|:-----:|------|:---:|---------|--------|----------|
| 1 | DPS 服务接入 | 2 天 | BL-145-01 | DPS 8030 启动 + health 通过 | 服务就绪 + 组织/租户种子 |
| 2 | 认证边界 + proxy 转发 | 5 天 | BL-145-02/03 | 身份头注入契约 + dps-proxy 端点 | 401 门禁 + 注入正确 + 归一化 |
| 3 | 前端真实化 | 3 天 | BL-145-04 | 画像列表/详情页真实 API | 2 页走查 |
| 4 | 联调收尾 | 3 天 | BL-145-05/06 | 闭环 + 还债 + 发布 | 联调闭环 + 回归/覆盖率 + tag v1.4.5 |

## 2. Phase 详细计划

### Phase 1：DPS 服务接入（BL-145-01）

| 项 | 内容 |
|----|------|
| 任务 | DPS 以 `API_PORT=8030` 启动（`cd src; python -m uvicorn rest_api.app:app`，PYTHONPATH=src）；`/health/liveness` + `/health/readiness` 健康检查；组织/租户种子数据（platform.organization/tenant active） |
| 依赖 | DPS v2.7.1 项目 + 数据库（SQLite 降级可用） |
| 风险 | 端口 API_PORT 变量名（非 PORT）；组织/租户缺失 401/403 |
| 交付物 | 启动验证记录 + 健康检查证据 |

### Phase 2：认证边界 + proxy 转发（BL-145-02/03）

| 项 | 内容 |
|----|------|
| 任务 | 身份头注入预研（X-Org-ID/X-Tenant-ID/X-User-ID 映射规则固化到 API 契约）→ dps_proxy 模块（画像计算/查询/标签/报表/批量状态/审计日志核心端点 + 统一响应 + {detail} 归一化 + 身份头注入） |
| 依赖 | Phase 1 完成；OpenBase JWT org_id 字段 |
| 风险 | 身份映射不成立（P1）→ 预研先行 + 配置化映射兜底 |
| 交付物 | API 契约 + dps_proxy 模块 + 单测 |

### Phase 3：前端真实化（BL-145-04）

| 项 | 内容 |
|----|------|
| 任务 | 画像模块核心页（画像列表/画像详情）mock 替换真实 API（走 dps-proxy） |
| 依赖 | Phase 2 完成 |
| 交付物 | 2 页真实化 + API 层封装 |

### Phase 4：联调收尾（BL-145-05/06）

| 项 | 内容 |
|----|------|
| 任务 | 双系统联调（登录→身份头注入→画像→标签→报表闭环）；TD-新增-011 还债（llm.ts SSE fetch adapter）；全量回归 + 覆盖率 + 发布（tag v1.4.5 双远程） |
| 依赖 | Phase 1-3 完成 |
| 风险 | DPS 组织/租户校验、AI 模型服务依赖 |
| 交付物 | 联调报告 + Step 4/5 文档 + Release Note |

## 3. 资源与角色

| 角色 | 承担 |
|------|------|
| 发布负责人 PM-OpenBase-Dev | 版本规划/评审/发布 |
| 需求 RA-OpenBase-Dev | Step 1 需求 |
| 设计 SA-OpenBase-Dev | Step 2 设计（含身份头注入契约） |
| 开发 AD-OpenBase-Dev | Step 3 编码（dps_proxy + 前端） |
| 测试 AT-OpenBase-Dev | Step 4 测试 |
| 审计 AU-OpenBase-Dev | 各阶段审计 |

## 4. 高层验收目标（映射 G1~G5）

| 验收项 | 目标 ID | Phase |
|--------|:------:|:-----:|
| DPS 8030 health 通过 | G1 | 1 |
| 未认证 401 + 身份头注入正确 | G2 | 2/4 |
| dps-proxy ≥6 端点 + 归一化 | G3 | 2/4 |
| 前端 2 页真实化 | G4 | 3 |
| 联调闭环 + UAT | G5 | 4 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | PM-OpenBase-Dev | 初始创建：Phase 1-4 拆分（服务接入/认证+proxy/前端/联调收尾）+ 资源角色 + 验收映射 |
