# OpenBase Phase 迭代计划 - v1.4.2

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.2 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-08-29 |
| 存放 | doc/version/releases/v1.4.2/ |

---

## 1. Phase 拆分

| Phase | 时间 | 内容 | BL 项 | 里程碑 | 验收重点 |
|-------|------|------|-------|--------|---------|
| Phase 1 | 第 1-1.5 周 | 四维管理基础：租户管理（API + 界面）+ 用户管理（API + 界面） | BL-142-01~04 | M1 四维管理可用 | 租户/用户 CRUD 全链路可用、数据落库；JWT 完整签发（sub/org_id/role）就绪；既有登录链路无回归 |
| Phase 2 | 第 1.5-2.5 周 | OpenMemory 对接：服务部署 + 认证适配 + proxy 转发 + 前端 2 页真实化 + 联调 | BL-142-05~09 | M2 OpenMemory 对接闭环 | OpenMemory 8020 健康检查通过；双层认证打通；remember/recall/forget/list 真实闭环；前端 2 页真实数据 |
| Phase 3 | 第 2.5-3 周 | 收尾：测试基座修复（TD-新增-009）+ 全量回归 + 覆盖率 + UAT 走查 + 部署发布 | BL-142-10（+ 全量） | M3 v1.4.2 发布 | 全量回归 ≥95%；覆盖率 ≥80%；无新增 P0/P1；Step 4/5 文档齐备 |

## 2. 里程碑与依赖

| 里程碑 | 依赖 | 前置 |
|--------|------|------|
| M1 四维管理可用（JWT 签发前提） | BL-142-01~04 | v1.4.1（已发布） |
| M2 OpenMemory 对接闭环 | BL-142-05~09 | M1（JWT 签发依赖租户/用户体系） |
| M3 v1.4.2 发布 | BL-142-01~10（全量） | M2 |

## 3. 关键交付物与接口契约

| 交付物 | 说明 |
|--------|------|
| 租户 API | `/api/v1/tenants` CRUD（create/list/get/update/deactivate/quota），向后兼容 context/quota |
| 用户 API | `/api/v1/users` CRUD（create/list/get/update/启停/角色分配），向后兼容 login/refresh/me |
| JWT 完整签发 | Payload 含 sub(user_id)/org_id(tenant_id)/role，签名密钥与 OpenMemory 服务端一致（环境变量共享） |
| OpenMemory proxy | OpenBase 侧代理路由（X-API-Key + Bearer JWT 双通道注入），统一响应适配 {code,message,data,timestamp} |
| OpenMemory 前端 | 记忆列表/详情 2 页 mock 替换真实 API（走 proxy，前端不接触密钥） |

## 4. 版本成功指标

| 指标 | 目标 |
|------|------|
| 四维管理 API | 租户/用户 CRUD 100% 可用（P0/P1 验收 100%） |
| 前端 mock 替换 | SystemTenants / OrgTeamsUsers 占位页 100% 替换；OpenMemory 前端 2 页替换 |
| OpenMemory 闭环 | 双层认证打通，remember/recall/forget/list 真实读写成功 |
| 回归质量 | 全量回归通过率 ≥95%，覆盖率 ≥80%，无新增 P0/P1 |
| 还债 | TD-新增-009（全量 pytest 崩溃）修复，回归脚本化 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | PM-OpenBase-Dev | 初始创建：两 Phase + 收尾 3 段迭代计划（Phase 1 四维管理基础 → Phase 2 OpenMemory 对接 → Phase 3 收尾发布），基于单版本规划 v1.1.0（VC-008/VC-010） |
