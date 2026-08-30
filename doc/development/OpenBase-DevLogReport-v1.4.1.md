# OpenBase DevLogReport - v1.4.1

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.1 |
| 文档版本 | v1.3.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-29 |
| 更新日期 | 2026-08-29 |
| 存放 | doc/development/ |

---

## 1. 实现范围（A 类补足 7 项 + Step 4 补充 2 项）

| 需求 | TD-ID | 实现 | 测试 |
|------|-------|------|:---:|
| R-367/368 服务 Key 认证 | TD-141-01/02 | `openbase/modules/auth/api_keys.py`（ApiKeyStore 签发/校验/吊销/scope）+ `openbase/core/deps/auth.py` require_api_key（X-API-Key/Bearer 双通道 + 路径 system scope 校验） | 15 项 |
| R-369 四维身份头 | TD-141-03 | `IdentityContext` + `get_identity_context`（4 头解析 + JWT 回退） | 含于上 |
| R-370 审计上下文 | TD-141-04 | `build_audit_record`（APICallRecord 注入 tenant_id/operator_id + team/agent extra） | 含于上 |
| R-371 openbase-cli | TD-141-05 | `openbase/cli/main.py` 增强（create-project/module/crud 5 文件骨架 + 函数导出） | 4 项 |
| R-372 BaseCRUDRouter | TD-141-06 | `openbase/core/crud.py` + `openbase/crud.py` 转发 | 6 项 |
| R-373 storage S3 | TD-141-07 | **`openbase/modules/storage/__init__.py`：`S3StorageBackend`（boto3 懒加载 + OPENBASE_STORAGE_S3_*/MINIO_* 配置驱动 + 本地回退）+ `get_backend()` 按 storage_backend 分发** | 单元 9 项 + 真实 4 项 |
| R-367 补充：服务 Key 签发 API 层 | TD-141-08 | `openbase/modules/auth/__init__.py` 新增 POST/GET/DELETE `/api/v1/auth/api-keys` 端点（ApiKeyCreate/ApiKeyOut schema + `_check_api_key_permission` admin 通配放行 + RBAC 兜底） | 4 项 |
| **R-367 补充：/proxy 双通道认证接线** | **TD-141-09** | **`AuthMiddleware` 豁免 `/api/v1/proxy` + `core/deps/auth.py` 新增 `get_proxy_identity`（JWT 优先 + X-API-Key/Bearer Key 回退）+ proxy 端点接入** | **HTTP 层 6 项** |

> Step 4 缺陷闭环记录：
> 1. BUG-141-01（P1）：R-367 AC-367-1 缺 API 层签发端点 → TD-141-08 补充后闭环。
> 2. BUG-141-02（P1）：R-373 声称完成但 `S3StorageBackend` 实现与测试均缺失 → TD-141-07 真实实现（含 `.env.shared-infra` 真实环境验证）后闭环。
> 3. BUG-141-03（P1）：UAT 走查发现 R-367 AC-367-2 "/proxy 通道 Bearer Key 认证"仅实现依赖函数（require_api_key）未接入 HTTP 层（AuthMiddleware 全局强制 JWT + proxy 端点仅 get_current_user）→ TD-141-09 修复（AuthMiddleware 豁免 `/api/v1/proxy` + `get_proxy_identity` 双通道组合依赖 + proxy 端点接入），HTTP 层验证 6/6 + UAT 14/14 后闭环。

## 2. 质量检查与验证

| 门禁 | 命令 | 结果 |
|------|------|------|
| Lint | `ruff check openbase tests` | ✅ All checks passed |
| 单测 | `pytest tests/test_api_keys.py test_api_keys_api.py test_crud_router.py test_cli.py test_storage_s3.py test_proxy_auth.py` | ✅ 44/44 |
| 真实环境 | `OPENBASE_TEST_REAL_INFRA=1 pytest tests/test_storage_s3_real.py` | ✅ 4/4（MinIO/PostgreSQL/Redis/get_backend） |
| 回归 | 核心 12 文件（含网关/认证/存储/CRUD/proxy） | ✅ 91/91 |
| UAT 走查 | 真实环境 API 序列走查（服务 Key 全生命周期 + proxy 双通道 + 越权 + 身份头） | ✅ 14/14 |
| CLI 走查 | create-project/create-module/create-crud（R-371 AC-371-1） | ✅ 3/3 |
| 覆盖率 | `--cov`（crud/api_keys/deps.auth/cli.main/modules.auth/storage） | ✅ ≥80% |
| 兼容性 | 既有 JWT 通道 + 服务 Key 双通道 + local/s3 后端共存 | ✅ 401/403 门禁用例通过 |

## 3. 已知问题与债务

| 项 | 级别 | 处置 |
|----|:---:|------|
| 服务 Key 未接数据库持久化（内存存储） | P2 | 生产接 DB 前内存可用；随测试基座批次补齐 |
| 全量 pytest 本机既有崩溃 | P2 | TD-新增-009（按文件隔离回归） |
| S3 对象存储为内存 bucket 幂等创建（未接租户隔离命名） | P2 | 多租户 bucket 命名规范随 v1.5+ 批次 |

## 4. 测试移交说明

| 项 | 说明 |
|----|------|
| 服务 Key 签发 | `POST /api/v1/auth/api-keys`（需登录 + `auth:api-keys:manage` 权限，admin 通配放行）；列表 `GET`；吊销 `DELETE /{raw_key}` |
| 认证头 | `X-API-Key: ob_k_...` 或 `Authorization: Bearer ob_k_...`（管理端点走 JWT+RBAC；`/proxy` 通道走 JWT 优先 + Key 回退双通道） |
| S3/MinIO 配置 | `storage_backend=minio`（Settings）+ `.env.shared-infra` 的 `MINIO_ENDPOINT/MINIO_ACCESS_KEY/MINIO_SECRET_KEY`；或 `OPENBASE_STORAGE_S3_*` 覆盖 |
| storage_path 引用 | `s3://{bucket}/{key}`（load/delete 直接解析） |
| 真实环境测试 | `OPENBASE_TEST_REAL_INFRA=1` 门控，依赖 192.168.0.151 共享基础设施 |
| 建议回归 | test_api_keys + test_api_keys_api + test_crud_router + test_cli + test_storage_s3 + 网关回归 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | AD-OpenBase-Dev | 初始创建：A 类 7 项实现（TD-141-01~07）+ TDD 26/26 + 回归 81/81 + 覆盖率 88% |
| v1.1.0 | 2026-08-29 | AD-OpenBase-Dev | Step 4 缺陷闭环：新增 TD-141-08 服务 Key 签发 API 层端点（R-367 AC-367-1）+ 测试 4 项 + 回归 72/72 |
| v1.2.0 | 2026-08-29 | AD-OpenBase-Dev | Step 4 缺陷闭环：TD-141-07 真实实现 S3StorageBackend（BUG-141-02）+ 单元 9 项 + `.env.shared-infra` 真实环境测试 4/4 + 回归 85/85 |
| v1.3.0 | 2026-08-29 | AD-OpenBase-Dev | UAT 走查缺陷闭环：TD-141-09 /proxy 双通道认证接线（BUG-141-03，AC-367-2 HTTP 层）+ test_proxy_auth 6 项 + 回归 91/91 + UAT 14/14 + CLI 3/3 |
