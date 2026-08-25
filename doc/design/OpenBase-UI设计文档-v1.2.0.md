# OpenBase UI 设计文档 - v1.2.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.2.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | UI-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 存放 | doc/design/ |

---

## 1. 设计入场检查

| 检查项 | 输入 | 结果 |
|--------|------|------|
| 前端架构 | OpenBase-前端架构设计文档-v1.2.0.md（页面结构/路由） | ✅ |
| 需求 | FR-12-02（风格体系）、FR-12-11（响应式）、NFR-12-04（可访问性） | ✅ |
| 原型 | doc/design/prototype/index.html（设计总览首页） | ✅ |

## 2. 设计系统说明（DT-12-02）

### 2.1 设计 Token（对齐四系统抽取后统一）

| Token | 值 | 用途 |
|-------|-----|------|
| color-primary | #2563EB | 主色（按钮/链接/激活态） |
| color-success / warning / danger / info | #16A34A / #D97706 / #DC2626 / #64748B | 功能色 |
| color-bg / surface / border | #F8FAFC / #FFFFFF / #E2E8F0 | 背景层级 |
| text-primary / secondary / disabled | #0F172A / #475569 / #94A3B8 | 文本层级 |
| font-family | 系统字体栈（-apple-system, Segoe UI, Roboto, PingFang SC, Microsoft YaHei） | 中文优先 |
| spacing | 8px 基准栅格（8/12/16/24/32） | 间距 |
| radius | 4/8/12 | 圆角 |
| shadow | sm/md/lg 三档 | 层级 |
| breakpoint | 1280 / 768 | 三端断点 |

### 2.2 组件规范

| 业务组件 | 说明 | 交互状态覆盖 |
|---------|------|-------------|
| AppLayout | 侧边栏+顶栏+内容区；响应式折叠 | 折叠/抽屉/遮罩 |
| DataTable | 筛选/分页/多选/排序/横向滚动/导出 | 空态/加载/错误 |
| Uploader | 拖拽/批量/进度/校验/失败重试 | 上传中/失败重试/成功 |
| ChartCard | ECharts 封装（趋势/分布/堆积），resize 自适应 | 加载/空数据 |
| StatusTag | 状态着色（在线/离线/进行中/错误/active/archived…） | - |
| ConfirmModal | 删除/危险操作二次确认 | 提交态 |
| EmptyState | 空数据引导 | - |
| WaypointTimeline | 记忆召回路径时间线（create/access/update/recall） | 空态 |
| ProviderRegisterWizard | 提供商注册多步向导 | 每步校验/测试连接 |

### 2.3 视觉一致性

统一设计 token（不引入多色板）；四系统抽取组件仅保留结构，样式全部 token 化重构；字体栈中文优先。

## 3. 原型设计说明

### 3.1 设计总览首页

`doc/design/prototype/index.html`：file:// 协议直接打开，列出全部设计页面卡片（按模块分组），支持检索与状态说明。

### 3.2 页面清单（RT-ID 映射）

| 模块 | 页面 | RT-ID |
|------|------|-------|
| 底座 | 登录/仪表盘/系统管理（用户/角色/租户/配置/审计） | RT-202/204 |
| OpenLLM | 模型中心 10 页/AI 应用 6 页/对话监控 7 页/平台联动 2 页（见前端架构文档 §5） | RT-205 |
| 知识库 | 列表/详情/上传/检索测试台 | RT-206 |
| 记忆 | 列表/详情/搜索/会话/图谱/衰减配置/写入 | RT-207 |
| 画像 | 列表/详情/搜索/标签/报表/批量 | RT-208 |

### 3.3 交互状态清单（模板）

| 状态 | 说明 | E2E 断言用途 |
|------|------|-------------|
| 空态 | 无数据展示（EmptyState 引导） | E2E 空列表断言 |
| 错误态 | 请求失败展示（ErrorResponse 映射提示） | E2E 错误提示断言 |
| 加载态 | 数据加载中（骨架屏/loading） | E2E 加载指示断言 |
| 成功态 | 操作成功反馈（message/跳转） | E2E 成功提示断言 |
| 表单提交态 | 提交中禁用+进度 | E2E 提交状态断言 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | UI-OpenBase-Dev | 初始创建：设计系统 token/组件规范/原型说明/交互状态清单 |
