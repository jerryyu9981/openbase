# OpenBase 本版本 Backlog - v1.4.2

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

## 1. Backlog 条目

### 1.1 Phase 1：四维管理基础（P1，4 项）—— R-374/R-375

| BL-ID | 需求 | R-ID | 优先级 | 价值 | 成本 |
|-------|------|------|--------|------|------|
| BL-142-01 | 租户管理 API（Tenant CRUD：create/list/get/update/停用/配额读写，SQLAlchemy 参数化 + 向后兼容既有 context/quota 端点） | R-374 | P1 | 高 | 中 |
| BL-142-02 | 租户管理界面（SystemTenants.vue 占位 mock 替换为真实 API，创建/编辑/停用/配额/列表） | R-374 | P1 | 高 | 中 |
| BL-142-03 | 用户管理 API（User CRUD：create/list/get/update/启停/角色分配，向后兼容既有 login/refresh/me 链路 + 种子数据迁移） | R-375 | P1 | 高 | 中 |
| BL-142-04 | 用户管理界面（OrgTeamsUsersView.vue 用户部分占位 mock 替换为真实 API，创建/启停/角色分配/列表） | R-375 | P1 | 高 | 中 |

### 1.2 Phase 2：OpenMemory 对接（P1，5 项）—— R-378

| BL-ID | 需求 | R-ID | 优先级 | 价值 | 成本 |
|-------|------|------|--------|------|------|
| BL-142-05 | OpenMemory 服务部署（docker-compose/进程启动，API 端口 8000→8020 避免与 OpenBase 冲突；OPENMEMORY_SERVER__API_KEY 配置；健康检查通过） | R-378 | P1 | 高 | 中 |
| BL-142-06 | OpenBase 认证适配（JWT 完整签发 sub/org_id/role，与 OpenMemory 服务端共享签名密钥配置；服务 Key 持有 X-API-Key 通道） | R-378 | P1 | 高 | 中 |
| BL-142-07 | proxy 转发适配（OpenMemory 路由代理：X-API-Key + Bearer JWT 双通道注入，统一响应 {code,message,data,timestamp} 适配，熔断/降级透传） | R-378 | P1 | 高 | 中 |
| BL-142-08 | OpenMemory 前端 2 页真实化（记忆列表/详情页 mock 替换真实 API，走 OpenBase proxy，不接触密钥） | R-378 | P1 | 中 | 中 |
| BL-142-09 | 双系统联调（OpenBase 统一认证 → OpenMemory remember/recall/forget/list 真实闭环；集成测试 + UAT 走查） | R-378 | P1 | 高 | 中 |

### 1.3 收尾与还债（1 项）

| BL-ID | 需求 | R-ID | 优先级 | 价值 | 成本 |
|-------|------|------|--------|------|------|
| BL-142-10 | 测试基座修复（TD-新增-009：全量 pytest 本机崩溃修复，回归脚本化执行；全量回归 + 覆盖率统计 + Step 4 文档） | - | P1 | 高 | 低 |

## 2. Backlog 汇总

| 项 | 值 |
|----|-----|
| 总条目 | 10（Phase 1：4 项；Phase 2：5 项；收尾：1 项） |
| P1 | 10 / 10（100%） |
| 需求覆盖 | R-374 / R-375 / R-378 全部拆解覆盖 |
| 还债容量 | BL-142-10 为还债项，1 / 10 = 10%（与 Step 4 测试阶段合并执行，实际占用 Step 4 容量 ≥15%） |

## 3. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | PM-OpenBase-Dev | 初始创建：基于单版本规划 v1.1.0（VC-008/VC-010）拆解，两 Phase 10 条目（Phase 1 四维管理基础 BL-142-01~04，Phase 2 OpenMemory 对接 BL-142-05~09，收尾还债 BL-142-10） |
