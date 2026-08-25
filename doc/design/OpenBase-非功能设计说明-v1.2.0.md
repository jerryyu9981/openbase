# OpenBase 非功能设计说明 - v1.2.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.2.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 存放 | doc/design/ |

> 本版本非功能设计以统一前端为中心，覆盖性能/兼容性/可维护性/可访问性/安全/可观测性，对齐 NFR-12-01~04 与四系统既有监控体系。

## 1. 性能设计（RT-N201）

| 指标 | 目标 | 措施 |
|------|------|------|
| 首屏加载 | <3s | 路由级懒加载、静态资源压缩（gzip）、CDN/nginx 缓存、图标按需引入 |
| 路由切换 | <500ms | 模块 chunk 预加载（hover 预取）、组件按需注册 |
| 交互响应 | <200ms | 列表虚拟滚动（大数据量）、防抖搜索、本地缓存（Pinia + sessionStorage） |
| 图表 | 趋势图加载 ≤3s（月粒度） | ECharts 按需引入、数据预聚合（对齐 OpenLLM usage_trend_data） |
| 轮询 | 监控 10s / 仪表盘 30~60s | 页面可见性感知（document.visibilitychange 暂停） |

## 2. 兼容性设计（RT-N202）

| 项 | 标准 |
|----|------|
| 浏览器 | Chrome / Edge / Firefox 最新 2 个版本 |
| 分辨率 | ≥320px；断点 ≥1280 / 768-1280 / <768 |
| 布局 | 栅格 12/8/4；表格横滚封装；图表 resize 自适应 |
| 构建 | Vite 目标 es2020（现代浏览器），不兼容 IE |

## 3. 可维护性设计（RT-N203）

| 项 | 标准 |
|----|------|
| 组件规范 | 业务组件文档化（props/events/slots/设计 token），见 UI 设计文档设计系统章节 |
| Lint | ESLint + Stylelint + vue-tsc 0 错误（CI 门禁） |
| 模块隔离 | 动态模块独立目录/store 命名空间，禁止跨模块直接引用内部状态 |
| 契约 | openapi-typescript 生成类型 + CI diff 校验，防契约漂移 |
| 命名 | 文件 snake_case / 组件 PascalCase / 变量 camelCase（遵循项目编码约定） |

## 4. 可访问性设计（RT-N204）

| 项 | 标准 |
|----|------|
| 键盘可达 | 关键操作（登录/导航/表单/弹窗关闭/表格操作）Tab 可达 + 焦点可见 |
| 对比度 | WCAG AA（正文 4.5:1、大文本 3:1） |
| 触控目标 | ≥44×44px（移动端按钮/汉堡/抽屉） |
| 语义 | 表单 label 关联、aria 标注、弹窗 role=dialog + focus trap |
| 验证 | E2E 断言 + 人工走查（Step 4 复用可访问性用例） |

## 5. 安全设计

| 项 | 设计 |
|----|------|
| 鉴权 | JWT（access + refresh），前端安全存储；401 静默刷新；登出清理 |
| 授权 | RBAC 权限标识（openllm:view 等）驱动菜单/路由/按钮三级控制 |
| 敏感数据 | API Key/密钥只在后端（config 模块），前端不落库不落日志 |
| 输入 | 前端表单校验（Pydantic 同步后端契约）+ XSS 防护（Vue 默认转义，禁用 v-html 白名单外场景） |
| 传输 | HTTPS（Pro）；Dev 同域反向代理 |
| 审计 | 关键操作（登录/导出/删除/发布）经后端 audit_logs 记录，前端展示审计入口 |

## 6. 可观测性设计

| 项 | 设计 |
|----|------|
| 前端监控 | 前端错误上报（window.onerror/unhandledrejection → 后端 /api/v1/observability/errors，可选） |
| 后端既有 | openbase 底座 OTLP 埋点（v1.0.0）+ 告警规则（v1.1.0，P99>500ms/401 率>20%） |
| 四系统联动 | 对话监控/用量统计页面直读四系统监控数据（代理透传 Prometheus 指标），不重复建设采集 |
| Dashboard | 沿用 v1.1.0 六个标准 Dashboard（Service/Resource/Dependencies/Business/Errors/Alert） |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | AA-OpenBase-Dev | 初始创建：性能/兼容/可维护/可访问/安全/可观测六域设计（对齐 NFR-12-01~04） |
