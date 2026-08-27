# OpenBase API 接口设计文档 - v1.3.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.3.0 |
| 文档版本 | v1.0.0 |
| 类型 | 版本设计（继承 v1.2.0 API 契约约定，记录本版本增量） |
| 状态 | [Review] |
| 作者 | AA-OpenBase-Dev |
| 创建日期 | 2026-08-27 |
| 存放 | doc/design/ |

> 本文档定义 v1.3.0 的 API 增量：①代理层 402 错误码（DT-13-28）；②代理契约核对基准（DT-13-27）；③基座调试 API 对齐清单。四系统业务 API 对接挂起（VC-005），契约以独立前端实际调用为基线登记，分批对接时核对。

## 1. 错误码增量：402 模型余额不足（DT-13-28）

| 字段 | 内容 |
|------|------|
| 错误码 | `BIZ_MODEL_QUOTA` |
| HTTP 状态 | 402（Payment Required） |
| 场景 | 模型提供商返回 402（Insufficient Balance）经代理层透传时 |
| 响应体 | `{"code": "BIZ_MODEL_QUOTA", "message": "模型服务余额不足，请联系管理员充值", "detail": "<request_id 关联信息>", "request_id": "<uuid>"}` |
| 代理层实现 | 上游 HTTP 402 → 包装统一 ErrorResponse（code=BIZ_MODEL_QUOTA，HTTP 保持 402）；不记录上游原始响应体/密钥 |
| 前端实现 | 请求层拦截 HTTP 402 → 全局 ElMessage 友好提示；不展示原始错误 |
| 注册位置 | `openbase/core/errors/codes.py` 错误码表 + OpenAPI schema（ErrorResponse） |

## 2. 代理契约核对基准（DT-13-27）

> 四系统对接挂起，前端按契约 mock；下列契约清单为分批对接时的核对基准（以独立前端实际调用为基线）。

| 系统 | 代理路径前缀 | 契约来源 | 核对时机 |
|------|------------|---------|---------|
| OpenLLM | `/api/v1/proxy/openllm/*` | OpenLLM `frontend/src/api/*.ts`（33 模块） | 对接批次启动时 |
| OpenRAG | `/api/v1/proxy/openrag/*` | OpenRAG `src/services/api.ts`（API_MODE 映射） | 对接批次启动时 |
| OpenMemory | `/api/v1/proxy/openmemory/*` | OpenMemory `src/api/*.ts`（动态 baseURL + X-API-Key） | 对接批次启动时 |
| DPS | `/api/v1/proxy/dps/*` | DPS API 服务（画像/标签/报表/限流/权限/审计） | 对接批次启动时 |

**mock 契约要求（AC-327-5）**：前端 mock 数据结构必须与上述契约字段一致（DTO 类型对齐），对接时仅切换请求基址即可无缝替换。

## 3. 基座调试 API 对齐清单（本次必须调试完整）

| API | 方法 | 用途 | 验证点 |
|-----|------|------|--------|
| `/api/v1/auth/login` | POST | 登录 | 成功/失败提示 |
| `/api/v1/auth/refresh` | POST | Token 刷新 | 过期自动刷新 |
| `/api/v1/auth/logout` | POST | 登出 | 清理本地状态 |
| `/api/v1/users` | GET/POST/PUT | 用户管理（公共页面） | RBAC 权限 |
| `/api/v1/roles` | GET | 角色列表 | 权限过滤 |
| `/api/v1/services` | GET | 动态模块发现 | 模块显隐 |
| `/api/v1/proxy/{system}/health` | GET | 代理连通性 | 502 包装验证 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-27 | AA-OpenBase-Dev | 初始创建：402 错误码设计（BIZ_MODEL_QUOTA）、代理契约核对基准、基座调试 API 对齐清单 |
