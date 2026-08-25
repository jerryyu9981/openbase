# OpenBase 用户需求说明书 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test / Pro |
| 作者 | RA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 最后更新 | 2026-08-25 |
| 关联文档 | OpenBase-开发需求文档-v1.0.0.md |

---

## 1. 用户场景

### 1.1 主场景

#### 场景 U1：四系统开发者接入公共底座

- **用户**：四系统（OpenLLM/OpenRAG/OpenMemory/DPS）开发工程师
- **目标**：以最小改动接入 OpenBase 公共底座
- **流程**：`pip install openbase` → `settings.enable_module("auth"/"tenant"/...)` → `init_app(settings)` → 挂载模块路由
- **成功条件**：既有对外接口不变，公共能力由底座提供
- **对应需求**：FR-CORE-001~005、FR-MOD-001~006

#### 场景 U2：新系统一键初始化

- **用户**：新系统开发工程师
- **目标**：一条命令创建标准工程
- **流程**：`openbase-cli create-project demo-system` → 生成标准结构 → 启用所需模块 → 运行
- **成功条件**：工程可运行，含 base models/DB/鉴权/审计等公共能力
- **对应需求**：FR-TOOL-001、FR-TOOL-003

#### 场景 U3：标准 CRUD 接口零手写

- **用户**：模块开发工程师
- **目标**：标准增删改查接口自动生成
- **流程**：定义模型 → 使用 BaseCRUDRouter 注册 → 获得分页/搜索/排序 CRUD 接口
- **成功条件**：生成接口与手写等价（延迟差 <5%）
- **对应需求**：FR-TOOL-002

### 1.2 异常场景

| 场景 | 描述 | 处理 | 对应需求 |
|------|------|------|---------|
| U4 | 模块启用冲突 | 配置驱动弱依赖，单模块禁用不影响其他模块 | FR-CORE-005、NFR-004 |
| U5 | 配置变更出错 | 配置中心版本回滚 100% 可用 | FR-MOD-006、NFR-005 |
| U6 | Token 过期 | 统一鉴权返回 401，前端/调用方重新登录 | FR-MOD-002 |
| U7 | 多租户数据越权 | 租户隔离生效，数据不串租户 | FR-MOD-003 |
| U8 | API 被刷 | 限流返回 429 | FR-MOD-001 |

### 1.3 边界场景

| 场景 | 描述 | 处理 |
|------|------|------|
| U9 | 无权限访问 | RBAC 校验返回 403 |
| U10 | 密码错误多次 | 锁定策略（auth 模块，具体策略在设计阶段细化） |
| U11 | 超大文件上传 | storage 模块限流/校验（设计阶段细化） |

## 2. 用户故事

| 故事 ID | 用户故事 | 对应需求 |
|---------|---------|---------|
| US-001 | As a 开发工程师，I want 一键安装 openbase，so that 快速获得全部公共能力 | FR-CORE、FR-MOD |
| US-002 | As a 开发工程师，I want 配置驱动启用模块，so that 按需加载最小改动 | FR-CORE-005 |
| US-003 | As a 平台管理员，I want 统一鉴权与权限矩阵，so that 用户权限集中管理 | FR-MOD-002 |
| US-004 | As a 平台管理员，I want 多租户隔离，so that 租户数据互不干扰 | FR-MOD-003 |
| US-005 | As a 运维人员，I want 可观测与审计，so that 系统状态可追踪 | FR-MOD-001/005 |
| US-006 | As a 运维人员，I want 配置热加载与回滚，so that 变更可控 | FR-MOD-006 |
| US-007 | As a 开发工程师，I want 工具经 MCP 声明注册，so that 统一暴露 | FR-MOD-004 |
| US-008 | As a 平台管理员，I want 组织/字典/任务/文件/通知统一管理，so that 通用后台能力标准化 | FR-SUP-001~005 |
| US-009 | As a 开发工程师，I want CLI 与 CRUD 生成器，so that 工程与接口快速搭建 | FR-TOOL-001/002/003 |
| US-010 | As a 开发工程师，I want pip 安装 + 文档三步启用，so that 低门槛接入 | FR-TOOL-004 |

## 3. 业务流程

### 3.1 四系统接入流程（底座视角）

```
[四系统开发工程师]
     │
     ▼
① pip install openbase
     │
     ▼
② settings.enable_module("auth"/"tenant"/"audit"/"observability"/"config"/"mcp")
     │
     ▼
③ app = init_app(settings)  +  app.include_router(module.router)
     │
     ▼
④ 既有特色路由继续挂载（编排/模型路由/回写等）
     │
     ▼
⑤ 验证：对外接口不变，公共能力生效
```

### 3.2 新系统创建流程

```
① openbase-cli create-project demo-system
     │
     ▼
② 生成标准工程结构（core/ + modules/ + settings.py + pyproject.toml）
     │
     ▼
③ 按需 enable_module
     │
     ▼
④ 初始化数据库（alembic upgrade head）
     │
     ▼
⑤ 运行验证（uvicorn 启动 + /health 检查）
```

### 3.3 模块抽取流程（本版本建设）

```
① 成熟度审计（6 模块 × 3 系统五维度评分）→ 确定最佳来源
     │
     ▼
② 来源决策（抽取范围 + 改动量：复制级/中等/改写迁移）
     │
     ▼
③ 汇聚（抽取为 openbase 模块 + 补测试与文档）
     │
     ▼
④ 验证（单模块独立启用 + 弱依赖验证 6/6）
     │
     ▼
⑤ 集成（补齐模块 + 工具链 + 整体装配）→ PyPI v1.0 发布
```

### 3.4 状态流转规则

| 流程 | 状态流转 | 说明 |
|------|---------|------|
| 用户账号 | 启用 ↔ 禁用（不可物理删除） | auth 模块 |
| 租户 | 启用 ↔ 禁用 | tenant 模块 |
| 定时任务 | 创建 → 启用 → 执行中 → 完成/失败 → 禁用 | scheduler 模块 |
| 配置版本 | 当前版 → 历史版（可回滚） | config 模块，保留 ≥10 版本 |
| 通知 | 未读 → 已读 | notify 模块 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-08-25 | RA-OpenBase-Dev | 初始创建：用户场景（主/异常/边界）、用户故事 10 条、业务流程 4 条（接入/创建/抽取/状态流转） |
