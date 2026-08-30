# OpenBase 测试用例 - v1.4.1

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.1 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AT-OpenBase-Test |
| 创建日期 | 2026-08-29 |
| 存放 | doc/test/ |

---

## 1. 用例清单总览

| 用例 ID | 对应需求 | 用例名称 | 测试文件 | 层级 | 结果 |
|---------|:-------:|---------|---------|:----:|:----:|
| TT-v1.4.1-001 | R-367 | 服务 Key 错误码定义齐全 | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-002 | R-367 | 服务 Key 错误码 HTTP 映射（401/403） | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-003 | R-367 | ApiKeyStore 签发/校验/吊销闭环 | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-004 | R-367 | 未知 Key 校验失败 | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-005 | R-367 | 列表不回显明文 Key | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-006 | R-368 | scope 校验：越系统/越租户拒绝 | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-007 | R-367 | require_api_key 有效 Key 认证通过 | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-008 | R-367 | 无效 Key → AUTH_API_KEY_INVALID(401) | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-009 | R-368 | scope 不匹配 → PERM_API_KEY_SCOPE(403) | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-010 | R-367 | 缺 Key → AUTH_API_KEY_INVALID(401) | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-011 | R-367 | Bearer 通道认证通过（ob_k_ 前缀） | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-012 | R-367 | X-API-Key 头认证通过 | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-013 | R-369 | 四维身份头解析（user/tenant/team/agent） | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-014 | R-369 | 缺省身份头返回 None 不抛异常 | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-015 | R-370 | 审计记录注入 tenant_id/operator_id | tests/test_api_keys.py | T2 | ✅ |
| TT-v1.4.1-016 | R-367 | 未登录创建服务 Key → 401 | tests/test_api_keys_api.py | T2 | ✅ |
| TT-v1.4.1-017 | R-367 | 创建（明文 ob_k_）→ 列表 → 吊销闭环 | tests/test_api_keys_api.py | T2 | ✅ |
| TT-v1.4.1-018 | R-367 | 普通用户创建服务 Key → 403 | tests/test_api_keys_api.py | T2 | ✅ |
| TT-v1.4.1-019 | R-367 | 未登录列表服务 Key → 401 | tests/test_api_keys_api.py | T2 | ✅ |
| TT-v1.4.1-020 | R-372 | BaseCRUDRouter 自动生成 5 端点 | tests/test_crud_router.py | T2 | ✅ |
| TT-v1.4.1-021 | R-372 | CRUD 创建 → out_schema 返回 | tests/test_crud_router.py | T2 | ✅ |
| TT-v1.4.1-022 | R-372 | CRUD 列表 + 单条查询 | tests/test_crud_router.py | T2 | ✅ |
| TT-v1.4.1-023 | R-372 | CRUD 更新字段生效（未传保持） | tests/test_crud_router.py | T2 | ✅ |
| TT-v1.4.1-024 | R-372 | CRUD 删除 → 再查 404 | tests/test_crud_router.py | T2 | ✅ |
| TT-v1.4.1-025 | R-372 | 创建参数校验（name 必填）→ 422 | tests/test_crud_router.py | T2 | ✅ |
| TT-v1.4.1-026 | R-371 | create-module 生成可导入模块骨架 | tests/test_cli.py | T2 | ✅ |
| TT-v1.4.1-027 | R-371 | create-crud 生成引用 BaseCRUDRouter 文件 | tests/test_cli.py | T2 | ✅ |
| TT-v1.4.1-028 | R-371 | create-project 生成标准工程（6 文件） | tests/test_cli.py | T2 | ✅ |
| TT-v1.4.1-029 | R-371 | CLI argparse 入口三命令可用 | tests/test_cli.py | T2 | ✅ |
| TT-v1.4.1-030 | R-373 | S3StorageBackend 单元级（9 项：引用/roundtrip/删除/配置解析/后端分发） | tests/test_storage_s3.py | T2 | ✅ |
| TT-v1.4.1-031 | R-367/368 | 网关代理通道回归（17 项） | tests/test_gateway.py | T3 | ✅ |
| TT-v1.4.1-032 | - | 应用装配回归（9 项） | tests/test_app.py | T3 | ✅ |
| TT-v1.4.1-033 | R-367 | 认证模块回归（6 项） | tests/test_auth.py | T3 | ✅ |
| TT-v1.4.1-034 | - | 安全/输入校验回归（5 项） | tests/test_security.py | T3 | ✅ |
| TT-v1.4.1-035 | - | RBAC 依赖回归（6 项） | tests/test_rbac_deps.py | T3 | ✅ |
| TT-v1.4.1-036 | R-367 | T4 走查：服务 Key 全生命周期 API 序列 | 人工走查清单 | T4 | ✅ |
| TT-v1.4.1-037 | R-373 | 真实 MinIO：S3StorageBackend 读写删除闭环 | tests/test_storage_s3_real.py（真实环境） | T3 | ✅ |
| TT-v1.4.1-038 | R-373 | 真实 PostgreSQL 连接（版本 + schema） | tests/test_storage_s3_real.py（真实环境） | T3 | ✅ |
| TT-v1.4.1-039 | R-373 | 真实 Redis 连接（ping + set/get/delete） | tests/test_storage_s3_real.py（真实环境） | T3 | ✅ |
| TT-v1.4.1-040 | R-373 | get_backend 配置驱动真实返回 S3 且可用 | tests/test_storage_s3_real.py（真实环境） | T3 | ✅ |
| TT-v1.4.1-041 | R-367 | proxy 无认证 → 401 | tests/test_proxy_auth.py | T2 | ✅ |
| TT-v1.4.1-042 | R-367 | proxy 无效 Key → 401（AUTH_API_KEY_INVALID） | tests/test_proxy_auth.py | T2 | ✅ |
| TT-v1.4.1-043 | R-367 | proxy 有效 Key（X-API-Key）认证通过 | tests/test_proxy_auth.py | T2 | ✅ |
| TT-v1.4.1-044 | R-367 | proxy Bearer Key 认证通过 | tests/test_proxy_auth.py | T2 | ✅ |
| TT-v1.4.1-045 | R-368 | proxy 越 scope Key → 403（PERM_API_KEY_SCOPE） | tests/test_proxy_auth.py | T2 | ✅ |
| TT-v1.4.1-046 | R-367 | proxy JWT 通道认证通过 | tests/test_proxy_auth.py | T2 | ✅ |

## 2. T2 API 三要素校验要求

所有 T2 用例均满足三要素校验：① 状态码断言；② 响应结构断言（字段名 + 类型）；③ 边界参数测试。

| 需求域 | 状态码 | 结构 | 边界 |
|--------|:------:|:----:|:----:|
| 服务 Key 认证 | 200/401/403/422 | credential/name/scope/revoked 字段 | 无效 Key/缺 Key/越 scope/未登录/越权 |
| CRUD 路由 | 200/404/422 | id/name/value 字段 | 缺必填/不存在 ID |
| CLI | exit 0 / 文件存在 | 5 文件骨架/6 文件工程 | 模块可导入 |

## 3. T4 走查清单（API 调用序列）

| 序号 | 业务流 | 步骤（API 调用序列） | 预期结果 | 实际结果 | 通过 |
|:----:|:-------|:---------------------|:---------|:---------|:----:|
| 1 | 登录 | `POST /api/v1/auth/login`（admin/admin123） | 返回 access_token | 200 + token | ✅ |
| 2 | 签发 | `POST /api/v1/auth/api-keys`（带 token + scope） | 返回明文 `ob_k_` Key | 200 + ob_k_ 前缀 | ✅ |
| 3 | 双通道认证 | `GET /api/v1/proxy/openllm/...`（X-API-Key / Bearer Key / JWT 三通道） | 服务 Key 与 JWT 均认证通过 | 三通道均通过（上游 502 包装） | ✅ |
| 4 | 越权 | `POST /api/v1/auth/api-keys`（viewer 用户） | 403 拒绝 | 403 | ✅ |
| 5 | 越 scope | `GET /api/v1/proxy/openrag/...`（openllm-scope Key） | 403 拒绝 | 403 | ✅ |
| 6 | 吊销 | `DELETE /api/v1/auth/api-keys/{raw_key}` | revoked 返回 | 200 + revoked | ✅ |
| 7 | 校验 | 吊销后使用该 Key 调 proxy | 401 拒绝 | 401 | ✅ |

## 4. 断言策略

| 项 | 说明 |
|----|------|
| 断言级别 | T2 用例全部采用 L1-硬断言（状态码 + 结构 + 边界均显式断言） |
| 软断言 | 0（无 if-else 软断言、无 try-except 吞异常、无超宽容断言） |
| 状态隔离 | ApiKeyStore 内存共享，用例使用唯一名称（uuid 后缀）隔离 |

## 5. 需求覆盖核对

| 需求 | 验收标准 | 覆盖用例 | 覆盖状态 |
|------|---------|---------|:--------:|
| R-367 | AC-367-1（签发 API 可用） | TT-v1.4.1-016~019 | FULLY_COVERED |
| R-367 | AC-367-2（双通道认证） | TT-v1.4.1-007/011/012 + **TT-041~044/046（HTTP 层）** | FULLY_COVERED |
| R-367 | AC-367-3（无效/吊销 401） | TT-v1.4.1-004/008/010 + TT-042 | FULLY_COVERED |
| R-367 | AC-367-4（scope 校验） | TT-v1.4.1-006 + TT-045 | FULLY_COVERED |
| R-368 | AC-368-1（越 scope 403） | TT-v1.4.1-009 | FULLY_COVERED |
| R-369 | AC-369-1/2（身份头解析/透传） | TT-v1.4.1-013/014 | FULLY_COVERED |
| R-370 | AC-370-1（审计绑定） | TT-v1.4.1-015 | FULLY_COVERED |
| R-371 | AC-371-1/2（三命令 + 可挂载） | TT-v1.4.1-026~029 | FULLY_COVERED |
| R-372 | AC-372-1/2（端点生成 + 鉴权统一） | TT-v1.4.1-020~025 | FULLY_COVERED |
| R-373 | AC-373（S3 接口对齐 + 真实环境） | TT-v1.4.1-030/037~040 | FULLY_COVERED | `.env.shared-infra` 真实 MinIO/PostgreSQL/Redis 闭环 |

## 6. 真实环境测试说明（.env.shared-infra）

| 项 | 内容 |
|----|------|
| 配置来源 | 项目根 `.env.shared-infra`（192.168.0.151 共享测试基础设施） |
| 执行门控 | `OPENBASE_TEST_REAL_INFRA=1`（未设置默认 skip，不影响常规回归） |
| 验证结果 | MinIO 读写删除闭环 ✅ / PostgreSQL 14.23 连接 ✅ / Redis ping+set/get/delete ✅ / get_backend 返回 S3 且真实可用 ✅ |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | AT-OpenBase-Test | 初始创建：v1.4.1 测试用例 36 项（29 专项 + 6 组回归 + 1 走查） |
| v1.1.0 | 2026-08-29 | AT-OpenBase-Test | 修正 TT-v1.4.1-030 覆盖来源；新增真实环境用例 TT-037~040；R-373 闭环 |
| v1.2.0 | 2026-08-29 | AT-OpenBase-Test | UAT 走查补充：新增 proxy 双通道用例 TT-041~046（AC-367-2 HTTP 层，BUG-141-03 闭环）；走查清单扩展至 7 步 |
