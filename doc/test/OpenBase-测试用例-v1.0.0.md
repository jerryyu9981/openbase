# OpenBase 测试用例 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 适用环境 | Dev / Test |
| 作者 | AT-OpenBase-Test |
| 创建日期 | 2026-08-25 |
| 最后更新 | 2026-08-25 |
| 存放 | doc/test/ |

---

## 1. 测试范围与策略

| 项 | 说明 |
|----|------|
| 项目类型 | 纯后端项目（v1.0.0 无前端页面，前端轨道 v1.2.0 激活） |
| T 层级 | T1 契约层 + T2 接口层 + T3b 深度用例（纯后端模式）+ T4 核心业务流走查 |
| T3a 声明 | 不适用（单服务纯 API，无前端页面、无服务间集成链路），见测试报告"测试跳过项说明" |
| 关联需求 | 开发需求文档 v1.0.0（FR-CORE/FR-MOD/FR-SUP/FR-TOOL + SR-001~009） |
| 关联代码 | TD-01~TD-26（设计开发追溯矩阵） |
| 执行环境 | Python 3.10.11 + pytest 9.1.1 + 真实 PG（192.168.0.151:5432）+ Redis（6380） |

## 2. 测试用例清单

### 2.1 T1 契约层（openapi.json）

| TT-ID | 用例名称 | 关联需求 | 关联代码 | 命令/方式 | 预期结果 | 结果 |
|-------|---------|---------|---------|-----------|---------|------|
| TT-v1.0.0-001 | OpenAPI schema 可解析 | FR-CORE-001 | TD-01-01 | GET /openapi.json | 200，JSON 可解析 | ✅ |
| TT-v1.0.0-002 | 关键路径契约齐备 | FR-CORE-002 | TD-01-01 | 遍历 paths | 31 路径，含 /health/login/refresh/dicts/org/configs | ✅ |
| TT-v1.0.0-003 | login 契约字段完整 | FR-MOD-001 | TD-02-03 | 解析 LoginRequest $ref | 含 username/password | ✅ |
| TT-v1.0.0-004 | 错误响应运行时格式 | FR-CORE-004 | TD-01-06 | 触发 401/422 | {code,message,detail,request_id} | ✅（契约声明缺口登记 BUG-003） |

### 2.2 T2 接口层（API 测试，pytest tests）

| TT-ID | 用例名称 | 关联需求 | 关联代码 | 命令/方式 | 预期结果 | 结果 |
|-------|---------|---------|---------|-----------|---------|------|
| TT-v1.0.0-101 | health 健康检查 | FR-CORE-001 | TD-01-01 | GET /health | 200 {"status":"ok"} | ✅ |
| TT-v1.0.0-102 | 登录成功（admin/admin123） | FR-MOD-001 | TD-02-03, TD-26-12 | POST /api/v1/auth/login | 200 access/refresh token | ✅ |
| TT-v1.0.0-103 | 登录失败（错误密码） | FR-MOD-001 | TD-02-03 | POST login wrong | 401 AUTH_401 | ✅ |
| TT-v1.0.0-104 | 刷新令牌 | FR-MOD-001 | TD-02-03 | POST /auth/refresh | 200 新 access_token | ✅ |
| TT-v1.0.0-105 | JWT 签发/解码 | FR-MOD-002 | TD-02-01 | 单测 test_auth.py | 签名/载荷/过期正确 | ✅ |
| TT-v1.0.0-106 | RBAC 权限检查 | FR-MOD-002 | TD-02-02, TD-26-06 | test_three_modules.py | 放行/拒绝正确 | ✅ |
| TT-v1.0.0-107 | 租户上下文解析 | FR-MOD-003 | TD-03-01, TD-26-02 | test_extracted.py | Header/Path/Query 解析正确 | ✅ |
| TT-v1.0.0-108 | 审计记录查询 | FR-MOD-004 | TD-04-01, TD-26-07 | test_three_modules.py | 记录/查询/脱敏正确 | ✅ |
| TT-v1.0.0-109 | 配置三级合并/回滚 | FR-MOD-006 | TD-06-01, TD-26-01 | test_extracted.py | 合并优先级/版本回滚正确 | ✅ |
| TT-v1.0.0-110 | MCP 工具注册/调用 | FR-MOD-007 | TD-07-01, TD-26-08 | test_obs_mcp.py | 工具列表/调用正确 | ✅ |
| TT-v1.0.0-111 | dict CRUD 流程 | FR-SUP-002 | TD-09-01 | test_app.py | 创建/列表/联动正确 | ✅ |
| TT-v1.0.0-112 | org 部门树 | FR-SUP-001 | TD-08-01 | test_app.py | 创建/路径/tree 正确 | ✅ |
| TT-v1.0.0-113 | scheduler 启停 | FR-SUP-003 | TD-10-01 | test_extra.py | 创建/启停/日志正确 | ✅ |
| TT-v1.0.0-114 | storage 文件上传 | FR-SUP-004 | TD-11-01 | test_app.py | 上传/元数据/下载正确 | ✅ |
| TT-v1.0.0-115 | notify 通知 | FR-SUP-005 | TD-12-01 | test_extra.py | 创建/已读/read-all 正确 | ✅ |
| TT-v1.0.0-116 | BaseCRUDRouter | FR-TOOL-002 | TD-14-01 | test_crud.py | 通用 CRUD 生成正确 | ✅ |
| TT-v1.0.0-117 | openbase-cli | FR-TOOL-001 | TD-13-01 | test_cli.py | create-project/module/crud 正确 | ✅ |
| TT-v1.0.0-118 | 数据模型建表 | FR-CORE-003 | TD-25-01 | test_models.py | 表结构/关系正确 | ✅ |
| TT-v1.0.0-119 | 统一错误处理 | FR-CORE-004 | TD-01-06 | test_auth.py | 403/401 统一格式 | ✅ |
| TT-v1.0.0-120 | demo_app 降级回退 | FR-CORE-001 | TD-16-01 | test_demo_app.py | DB 不可达降级内存用户，应用可装配 | ✅ |
| TT-v1.0.0-121 | 初始化种子 SQL 构造 | FR-CORE-003 | TD-26-11 | test_db_init.py | schema 前缀 + 幂等（WHERE NOT EXISTS） | ✅ |

### 2.3 安全专项（4.7a，tests/test_security.py + 契约脚本）

| TT-ID | 用例名称 | 关联需求 | 关联代码 | 命令/方式 | 预期结果 | 结果 |
|-------|---------|---------|---------|-----------|---------|------|
| TT-v1.0.0-201 | 匿名访问业务接口 | SR-001 | TD-02-04 | GET /api/v1/dicts 无 token | 401 AUTH_401 | ✅ |
| TT-v1.0.0-202 | 匿名访问 configs/audit | SR-001 | TD-02-04 | GET configs/{key}、audit/records | 401 | ✅ |
| TT-v1.0.0-203 | 伪造 token | SR-001 | TD-02-04 | Bearer fake.token | 401 | ✅ |
| TT-v1.0.0-204 | 有效 token 访问 | SR-001 | TD-02-04 | 登录后访问 | 200 | ✅ |
| TT-v1.0.0-205 | 白名单公开路径 | SR-001 | TD-02-04 | health/docs/openapi 匿名 | 200 | ✅ |
| TT-v1.0.0-206 | SQL 注入尝试 | SR-002 | TD-02-03 | username=' OR '1'='1 | 401（不绕过） | ✅ |
| TT-v1.0.0-207 | XSS 输入处理 | SR-002 | TD-09-01 | dict 名称含 <script> | 存储原样（无执行） | ✅ |
| TT-v1.0.0-208 | 敏感信息不泄露 | SR-004 | TD-02-03 | 401 响应体检查 | 不含密码/hash | ✅ |
| TT-v1.0.0-209 | 超长/异常输入 | SR-002 | TD-02-03 | 5000 字符/非字符串 | 4xx 统一错误 | ✅ |

### 2.4 集成测试（真实 PG，it_pg_integration.py）

| TT-ID | 用例名称 | 关联需求 | 关联代码 | 命令/方式 | 预期结果 | 结果 |
|-------|---------|---------|---------|-----------|---------|------|
| TT-v1.0.0-301 | 启动数据库初始化 | FR-CORE-001 | TD-26-11 | import demo_app | DB_READY=True | ✅ |
| TT-v1.0.0-302 | openbase schema 建表 | FR-CORE-003 | TD-26-10 | 查询 pg_tables | 8 张表齐全 | ✅ |
| TT-v1.0.0-303 | admin 用户落库 | FR-MOD-001 | TD-26-12 | SELECT openbase.users | admin 存在 | ✅ |
| TT-v1.0.0-304 | 数据库路径登录 | FR-MOD-001 | TD-26-12 | POST login | 200 token | ✅ |
| TT-v1.0.0-305 | 错误密码拒绝 | FR-MOD-001 | TD-26-12 | POST login wrong | 401 | ✅ |
| TT-v1.0.0-306 | refresh 数据库路径 | FR-MOD-001 | TD-26-12 | POST refresh | 200 | ✅ |
| TT-v1.0.0-307 | public 无污染 | FR-CORE-003 | TD-26-10 | 查 public 特有表 | 无 OpenBase 特有表 | ✅ |
| TT-v1.0.0-308 | public.users 非本表 | FR-CORE-003 | TD-26-10 | 列结构对比 | 结构不同 | ✅ |

### 2.5 性能测试（4.7b）

| TT-ID | 用例名称 | 关联需求 | 关联代码 | 命令/方式 | 预期结果 | 结果 |
|-------|---------|---------|---------|-----------|---------|------|
| TT-v1.0.0-401 | /health 并发压测 | NFR-001~003 | TD-01-01 | 100 请求/并发 10 | P50 48.6ms / P99 111.3ms ✅ | ✅ |
| TT-v1.0.0-402 | login 并发压测 | NFR-001~003 | TD-02-05 | 40 请求/并发 8 | P50 753ms（BUG-002 修复后）✅ | ✅ |

### 2.6 UAT 核心业务流走查（T4，纯后端模式）

| TT-ID | 业务流 | 步骤（API 调用序列） | 预期结果 | 实际结果 | 通过 |
|-------|--------|----------------------|---------|---------|------|
| UAT-001 | 健康检查 | GET /health | 200 ok | 200 ok | ✅ |
| UAT-002 | 登录→鉴权访问 | POST /auth/login → GET /api/v1/dicts（带 token） | 登录成功，业务接口可访问 | 200 + 200 | ✅ |
| UAT-003 | 登录→未授权拦截 | POST /auth/login → 匿名 GET /api/v1/configs/{key} | 匿名被 401 拦截 | 401 统一格式 | ✅ |
| UAT-004 | 配置闭环 | 登录 → POST /configs → POST 更新 → GET versions → POST rollback | 写入/版本/回滚闭环 | 全链路通过 | ✅ |
| UAT-005 | 字典闭环 | 登录 → POST /dicts → POST items → GET items | 创建/列表联动 | 通过 | ✅ |
| UAT-006 | 组织闭环 | 登录 → POST departments → 子部门 → GET tree | 树形结构正确 | 通过 | ✅ |
| UAT-007 | 数据库闭环 | 服务启动 → admin 落库 → 数据库登录 → health | 真实 PG 全链路 | 通过 | ✅ |

## 3. 断言策略

| 类别 | 策略 |
|------|------|
| 关键交互（登录/创建/删除） | L1 硬断言（状态码 + 响应结构 + token 非空） |
| 边界/异常输入 | L1 硬断言（4xx + 统一错误格式） |
| 可选功能 | L2 条件断言（存在则验证，不存在 skip） |
| 软断言 | 0（grep 检查通过） |

## 4. 测试追溯说明

- 所有 TT-ID 可追溯至 RT-ID（需求追溯矩阵）与 TD-ID（设计开发追溯矩阵）
- P0/P1 需求全部有测试覆盖（覆盖率 82%，用例覆盖率 100%）
- 层间追溯：T1 契约路径 → T2 API 用例 → T3b 集成 → T4 UAT，见测试回溯对比审计报告

## 5. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-08-25 | AT-OpenBase-Test | 初始创建：T1 契约 4 例 + T2 接口 19 例 + 安全 9 例 + 集成 8 例 + 性能 2 例 + UAT 7 项，共 49 项，全部通过 |
