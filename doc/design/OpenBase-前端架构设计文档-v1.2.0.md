# OpenBase 前端架构设计文档 - v1.2.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.2.0 |
| 文档版本 | v1.0.0 |
| 类型 | 版本设计（统一前端架构） |
| 状态 | [Review] |
| 作者 | FA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 存放 | doc/design/ |

---

## 1. 设计入场检查

| 检查项 | 输入 | 结果 |
|--------|------|------|
| 系统架构 | OpenBase-系统架构设计文档-v1.2.0.md（§5 底座/§6 动态模块/§8 OpenLLM 板块） | ✅ |
| 需求追溯 | RT-201~211 全部（前端相关） | ✅ |
| 轨道 | 前端 🎨 激活（全栈项目强制原型） | ✅ |

## 2. 技术栈（继承 ADR-12-01）

| 层 | 选型 |
|----|------|
| 框架 | Vue 3（Composition API）+ TypeScript |
| 构建 | Vite |
| 路由 | Vue Router 4（集中注册 + 动态模块路由） |
| 状态 | Pinia（分域 store） |
| UI 库 | Element Plus（统一封装业务组件） |
| 图表 | ECharts（ChartCard 封装） |
| HTTP | Axios（拦截器）+ openapi-typescript 生成客户端 |
| 测试 | Vitest + Vue Test Utils + Playwright |

## 3. 目录结构

```
openbase-ui/
├── src/
│   ├── core/                 # 公共底座
│   │   ├── layouts/          # AppLayout（侧边栏/顶栏/内容区）+ 响应式
│   │   ├── router/           # 路由注册（公共 + 模块注入）
│   │   ├── stores/           # Pinia（auth/user/moduleRegistry/ui）
│   │   ├── api/              # openapi 生成客户端 + axios 实例
│   │   ├── components/       # 业务组件（DataTable/Uploader/ChartCard/...）
│   │   ├── styles/           # 设计系统 token（色板/字体/间距/断点）
│   │   └── utils/            # 权限指令/错误映射/格式化
│   ├── modules/              # 动态模块（每个模块独立目录，懒加载）
│   │   ├── openllm/          # OpenLLM 特色模块（板块见 §5）
│   │   ├── knowledge/        # 知识库（OpenRAG）
│   │   ├── memory/           # 记忆（OpenMemory）
│   │   ├── portrait/         # 画像（DPS）
│   │   └── module-manifest.json  # 模块注册表
│   ├── pages/                # 底座公共页面（登录/仪表盘/系统管理）
│   ├── App.vue
│   └── main.ts
├── tests/                    # 单元/组件/E2E
└── vite.config.ts
```

## 4. 路由与状态设计

### 4.1 路由注册

| 类别 | 路由 | 说明 |
|------|------|------|
| 公共 | /auth/login、/dashboard、/system/* | 登录/仪表盘/系统管理（用户/角色/租户/配置/审计） |
| 动态模块 | /openllm/*、/knowledge/*、/memory/*、/portrait/* | 启动时由 ModuleRegistry 按 manifest 注入，懒加载 |

路由守卫：未登录 → /auth/login；已登录无权限 → 403 页；模块未注册 → 404。

### 4.2 Pinia 分域

| store | 职责 |
|-------|------|
| auth | token/用户信息/登录刷新 |
| user | 角色/权限标识集合 |
| moduleRegistry | 模块清单/挂载状态/动态路由注册 |
| ui | 侧边栏折叠状态/主题/断点 |
| 模块私有 store | openllm / knowledge / memory / portrait（命名空间隔离） |

## 5. OpenLLM 模块页面结构（板块重设计落地，DT-12-05）

| 板块 | 路由 | 页面 | 核心交互 | 交互状态 |
|------|------|------|---------|---------|
| 模型中心 | /openllm/models | 模型列表 | Tab 分类/搜索筛选/新增编辑弹窗/删除确认 | 空态/错误/加载/成功/提交 |
| 模型中心 | /openllm/models/:id | 模型详情 | 信息/状态/关联配置 | 同上 |
| 模型中心 | /openllm/models/local | 本地模型 | 卡片网格/启动停止删除/Ollama 拉取/GPU 占用 | 同上 |
| 模型中心 | /openllm/models/market | 开源模型市场 | 搜索/卡片/一键部署 | 同上 |
| 模型中心 | /openllm/providers | 提供商管理 | 卡片/启禁用/详情抽屉（密钥脱敏/健康） | 同上 |
| 模型中心 | /openllm/providers/register | 提供商注册向导 | 多步表单/测试连接 | 表单提交态 |
| 模型中心 | /openllm/api-keys | API 密钥 | CRUD/权限范围/过期时间 | 同上 |
| 模型中心 | /openllm/deploy | 模型部署向导 | 选模型→并发/超时/缓存→部署日志 | 表单提交态 |
| 模型中心 | /openllm/gpu | GPU 资源 | 统计卡/分配释放/10s 轮询 | 加载/空态 |
| 模型中心 | /openllm/adapters | EdgeRouter 适配器 | 卡片/健康圆点/注册注销 | 同上 |
| AI 应用 | /openllm/apps | 应用管理 | 应用 CRUD/模型绑定/Prompt/参数 | 空态/提交态 |
| AI 应用 | /openllm/apps/:id | 应用详情 | 配置/发布下架/版本 | 同上 |
| AI 应用 | /openllm/apps/calls | 调用记录 | 列表/筛选/详情 | 空态/加载 |
| AI 应用 | /openllm/playground | Playground | 对话调试/导出 | 加载（流式） |
| AI 应用 | /openllm/prompt-templates | Prompt 模板 | CRUD/变量占位符/模型关联 | 表单提交态 |
| AI 应用 | /openllm/prompt-experiments | Prompt 实验 | 变体/流量分配/评估/胜出 | 空态/提交态 |
| 对话监控 | /openllm/conversations | 对话管理 | 列表/详情/导出/批量删除 | 空态/加载 |
| 对话监控 | /openllm/monitoring | 监控仪表盘 | 指标卡/趋势图/10s 轮询 | 加载/错误 |
| 对话监控 | /openllm/monitoring/traces | 链路追踪 | Trace 搜索/Span 瀑布 | 空态/加载 |
| 对话监控 | /openllm/monitoring/costs | 成本分析 | 堆积图/明细表/导出 | 空态/加载 |
| 对话监控 | /openllm/monitoring/budgets | 预算管理 | 列表/告警阈值 80/90/100% | 同上 |
| 对话监控 | /openllm/monitoring/alerts | 告警中心 | 级别/确认/批量 | 空态 |
| 平台联动 | /openllm/routing/strategies | 路由策略 | 列表/优先级/启停 | 同上 |
| 平台联动 | /openllm/routing/circuit-breakers | 熔断器 | 环形状态卡/配置/时间线/重置 | 加载/错误 |

> 深度对接依赖四系统 API 的页面（语义/级联路由、A/B 测试、插件管理、配置中心、Webhook、计费）本版本登记 backlog，经代理 API 就绪后补挂。

## 6. 知识库模块页面结构（DT-12-06）

| 页面 | 路由 | 核心交互 |
|------|------|---------|
| 知识库列表 | /knowledge | 卡片/表格视图切换、统计条、创建/编辑、删除确认 |
| 知识库详情 | /knowledge/:id | 概览 hero、文档管理（上传/状态过滤/多选/重新索引）、分块预览、检索测试台（Agent 模式/来源追溯/评分） |
| 上传流程 | 详情内 | 拖拽/批量/进度/校验/失败重试；DocumentStatus 状态机轮询展示 |

## 7. 记忆模块页面结构（DT-12-07）

| 页面 | 路由 | 核心交互 |
|------|------|---------|
| 记忆列表 | /memory | 分页/排序/类型筛选、衰减权重列（绿/黄/红）、批量选择/删除 |
| 记忆详情 | /memory/:id | 完整内容+元数据、关联记忆跳转、WaypointTimeline（create/access/update/recall） |
| 记忆搜索 | /memory/search | 关键词+类型+时间范围、高亮、超时提示 |
| 会话管理 | /memory/sessions | 列表/终止/批量终止/30s 刷新 |
| 记忆图谱 | /memory/graph | 力导向图/搜索过滤 |
| 衰减配置 | /memory/decay | 策略/衰减因子/半衰期配置 |
| 记忆写入 | /memory/write | 写入表单（memory_type）+ 多模态上传（图像/音频） |

## 8. 画像模块页面结构（DT-12-08）

| 页面 | 路由 | 核心交互 |
|------|------|---------|
| 画像列表 | /portrait | 分页/搜索/排序、状态筛选（active/inactive/archived）与流转 |
| 画像详情 | /portrait/:id | 基本信息/标签维护（打标/移除）/数据源 |
| 画像搜索 | /portrait/search | 关键词+标签组合（AND/OR）、分数/时间范围、模糊搜索、自动补全 |
| 标签管理 | /portrait/tags | 分类 CRUD + 值 CRUD + 统计 |
| 分析报表 | /portrait/reports | 总览/维度分布/标签数量/趋势/组织分布/导出 |
| 批量任务 | /portrait/batch | 导入（上传→预检查→执行→状态/错误明细）、导出（筛选/字段/格式/加密） |

## 9. 响应式落地（RT-211）

| 策略 | 实现 |
|------|------|
| 栅格 | 12/8/4 列响应式（断点 ≥1280 / 768-1280 / <768） |
| 侧边栏 | 桌面常驻；<1280 折叠为抽屉（汉堡 ≥44px、遮罩关闭、内容滚动） |
| 表格 | DataTable 内置横向滚动（窄屏） |
| 图表 | ChartCard 内置 resize 监听与高度自适应 |
| 弹窗/抽屉 | 宽度 ≤ 屏宽-32px，最大高度可滚动 |
| E2E 断言 | Playwright 三端视口（1440/1024/375）核心路径无横向溢出 |

## 10. 质量门禁（DT-12-09）

| 门禁 | 命令 | 标准 |
|------|------|------|
| Lint | eslint + stylelint + vue-tsc | 0 错误 |
| 单测 | vitest run | 100% 通过 |
| 覆盖率 | vitest coverage | ≥80% |
| E2E | playwright test | 核心路径三端通过 |

## 11. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | FA-OpenBase-Dev | 初始创建：统一前端架构（目录/路由/状态/四模块页面结构/OpenLLM 板块落地/响应式/质量门禁） |
