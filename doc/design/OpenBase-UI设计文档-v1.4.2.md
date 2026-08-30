# OpenBase UI 设计文档 - v1.4.2

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.2 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | UI-OpenBase |
| 创建日期 | 2026-08-29 |
| 存放 | doc/design/ |
| 设计依据 | 统一前端设计体系（vue-vben-admin 风格，沿用 v1.3.0/v1.4.0 既有页面规范）；需求 FR-142-01~09 |

---

## 1. 设计范围

| 页面 | 涉及 FR | 现状态 | 目标 |
|------|---------|:------:|------|
| SystemTenants.vue（租户管理） | FR-142-01/02 | 占位 mock | 真实 API |
| OrgTeamsUsersView.vue 用户部分 | FR-142-03/04 | 占位 mock | 真实 API（团队部分仍 mock，团队管理 v1.5） |
| OpenMemory 记忆列表页 | FR-142-07/08 | mock | 真实 API（走 proxy） |
| OpenMemory 记忆详情页 | FR-142-07/08 | mock | 真实 API（走 proxy） |

## 2. 页面设计

### 2.1 租户管理页（SystemTenants.vue 重做）

| 项 | 内容 |
|----|------|
| 布局 | 标准表格页：搜索区（关键字）+ 表格 + 分页 + 新建/编辑弹窗 |
| 表格列 | 租户编码 / 名称 / 状态（active/disabled Tag）/ 配额摘要 / 创建时间 / 操作 |
| 操作 | 新建、编辑、停用/启用、配额设置 |
| 配额弹窗 | 字段：请求数上限、存储上限、并发上限（与 QuotaManager 配置对应） |
| API 绑定 | GET/POST /api/v1/tenants、PUT/DELETE /api/v1/tenants/{id}、PUT .../quota |
| 权限 | 仅 admin 可见可操作（路由守卫 + 按钮权限码） |

### 2.2 用户管理页（OrgTeamsUsersView 用户 tab 重做）

| 项 | 内容 |
|----|------|
| 布局 | 组织/团队/用户三 tab 保留；用户 tab 换真实数据（团队 tab 保留 mock 待 v1.5） |
| 表格列 | 用户名 / 角色（Tag）/ 状态 / 所属租户 / 创建时间 / 操作 |
| 操作 | 新建、编辑、启停、分配角色 |
| 角色弹窗 | 单选角色（admin/org_admin/org_member/viewer） |
| API 绑定 | GET/POST /api/v1/users、PUT/DELETE /api/v1/users/{id}、PUT .../role |
| 权限 | admin/org_admin 可操作 |

### 2.3 OpenMemory 记忆列表页（真实化）

| 项 | 内容 |
|----|------|
| 布局 | 搜索区（关键词/标签/类型过滤）+ 表格 + 分页 |
| 表格列 | 记忆内容（截断）/ 类型 / 标签 / 重要性 / 衰减权重 / 创建时间 / 操作（详情/删除） |
| 操作 | 查看详情、删除（forget） |
| API 绑定 | GET /api/v1/memory-proxy/memories、GET .../memories/{id}、POST .../forget |
| 安全 | 全部请求走 OpenBase proxy，前端不持有 X-API-Key |

### 2.4 OpenMemory 记忆详情页（真实化）

| 项 | 内容 |
|----|------|
| 布局 | 详情展示：内容全文、类型、标签、重要性、衰减权重、实体（entities）、Waypoint 召回路径（如返回）、创建时间、会话关联 |
| 操作 | 删除记忆、返回列表 |
| API 绑定 | GET /api/v1/memory-proxy/memories/{memory_id} |

## 3. 组件与交互约定

| 项 | 约定 |
|----|------|
| 表格 | 复用统一前端表格组件（分页/排序/loading 态） |
| 弹窗 | 复用统一前端表单弹窗（校验/提交 loading/错误提示 BaseError detail） |
| 状态 Tag | active=成功色、disabled=默认色 |
| 空态/错误态 | 空数据展示引导文案；接口错误展示 detail（统一响应格式） |
| 路由守卫 | 页面级权限（admin/org_admin 角色路由守卫） |

## 4. 设计验收标准（对应 AC）

| AC | 验收方法 |
|----|---------|
| AC-142-01-4 | 租户页创建/编辑/停用/配额全链路走通（界面级） |
| AC-142-02-4 | 用户页创建/启停/角色分配全链路走通（界面级） |
| AC-142-06-1~3 | 记忆列表/详情真实数据展示，前端无 Key |
| AC-142-07-5 | UAT 走查通过（页面级） |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | UI-OpenBase | 初始创建：4 页面设计（租户/用户管理重做 + OpenMemory 记忆 2 页真实化），API 绑定 + 交互约定 + 验收 |
