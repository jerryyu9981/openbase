# OpenBase-JWT密钥管理说明-v1.0.0

| 属性   | 值                                                                         |
| ---- | ------------------------------------------------------------------------- |
| 文档编号 | OB-AUTH-JWTKEY-v1.0.0                                                       |
| 版本   | v1.0.0                                                                    |
| 状态   | \[Review]                                                                 |
| 日期   | 2026-09-02                                                                |
| 作者   | AD-OpenBase-Dev                                                           |
| 版本主题 | 生产密钥替换：无弱默认 + 生产强校验（fail-fast）+ 双密钥轮换宽限 + 密钥生成工具 + 演示环境真实替换               |
| 适用范围 | OpenBase（8000）+ openbase-ui（5173）+ OpenMemory/OpenLLM/OpenRAG/DPS（共享密钥消费） |

> 本文档定义 OpenBase 网关 JWT 共享密钥（HS256）的生产化管理：配置约束、轮换流程与运维指引。

## 修订历史

| 版本     | 日期         | 修改人             | 修改内容                                                                           |
| ------ | ---------- | --------------- | ------------------------------------------------------------------------------ |
| v1.0.0 | 2026-09-02 | AD-OpenBase-Dev | 初始版本：密钥默认去除 + 生产强校验 + 轮换宽限 + 生成工具 + 环境替换                                          |

***

## 1. 背景与问题

网关 JWT 采用 HS256 共享密钥（OpenBase 签发 → OpenMemory/OpenLLM 等下游同密钥验签）。
旧实现存在风险：

1. `settings.jwt_secret` 内置可用弱默认（`change-me-in-production`），本地演示沿用
   `test-jwt-secret-for-v680`（25 字符），生产依赖 deploy 脚本口头校验，弱值可运行。
2. 单密钥签发/验签：轮换密钥即全体 token 失效（强制登出所有会话）。
3. 无密钥生成工具与规范流程。

## 2. 目标

- 生产环境弱/缺密钥启动即失败（fail-fast），杜绝弱默认可用。
- 支持零中断密钥轮换（新密钥签发，旧密钥宽限验签）。
- 提供生成/校验工具与运维流程文档。

## 3. 实现（v1.0.0）

### 3.1 settings（openbase/settings.py）

| 字段 | 默认 | 说明 |
| ---- | ---- | ---- |
| `env` | `development` | 运行环境：development \| production（`OPENBASE_ENV`） |
| `jwt_secret` | `""` | 无内置弱默认；本地 `.env` 提供随机密钥 |
| `jwt_secret_previous` | `""` | 轮换宽限旧密钥（仅验签） |
| `jwt_algorithm` | `HS256` | 不变 |

**启动校验器**（model\_validator after）：

- `env=production`：`jwt_secret` 必须 ≥32 字符且非已知弱值
  （`WEAK_JWT_SECRETS = {"", "change-me-in-production", "test-jwt-secret-for-v680"}`），
  否则抛 ValueError（启动失败）。
- `development`：弱值 WARN；空值 WARN（签发 fail-closed）。

### 3.2 jwt（openbase/modules/auth/jwt.py）

- 签发（access/refresh）：固定使用当前 `jwt_secret`（`_sign_secret`；未配置/过弱抛错 fail-closed）。
- 验签（`_decode_any`）：依次尝试 `[jwt_secret, jwt_secret_previous]`（跳过空）——
  轮换过渡期新旧 token 均有效；轮换完成移除 previous 后旧 token 自然失效。

### 3.3 工具（scripts/gen_jwt_secret.py）

- 默认生成 URL-safe 64 字符强随机密钥并打印配置指引。
- `--check`：校验当前 `.env` 的 `OPENBASE_JWT_SECRET` 强度（exit 0/1）。

### 3.4 演示环境（本地 .env，不入库）

- OpenBase `.env`：`OPENBASE_JWT_SECRET` 已替换为生成的强随机密钥（64 字符）。
- OpenMemory `.env`：`OPENMEMORY_GATEWAY__JWT_SECRET` 需同步为同一值
  （其目录超出当前工作区沙箱，由运维执行下方命令同步）。

## 4. 密钥轮换操作流程（零中断）

```powershell
# 1) 生成新密钥（或复用 gen_jwt_secret.py 输出）
$new = (python -c "import secrets;print(secrets.token_urlsafe(48))")

# 2) OpenBase：旧密钥保留为 previous（验签宽限），新密钥作为当前（签发切新）
#    .env
#    OPENBASE_JWT_SECRET=$new
#    OPENBASE_JWT_SECRET_PREVIOUS=<旧密钥>

# 3) 重启 OpenBase 网关 → 过渡期内新旧 token 均有效（旧会话不登出）

# 4) 同步下游共享密钥（OpenMemory 等）
#    OpenMemory .env：OPENMEMORY_GATEWAY__JWT_SECRET=$new

# 5) （可选）过渡期结束移除 previous 并重启 → 旧 token 失效
```

## 5. 验证（v1.0.0 实测）

- 单测 `tests/test_jwt_secrets.py` 11 用例：production 弱值（空/占位/演示）拒绝、
  强值放行、签发 fail-closed、轮换旧 token 宽限验签、轮换完成失效、签发恒用当前密钥。
- 回归：OIDC/auth/RBAC/用户 相关全绿；ruff 0 错误。
- E2E：新密钥下本地账号登录（签发/验签自洽 200）+ OIDC 浏览器全链路回 Dashboard 正常。
- 校验：`python scripts/gen_jwt_secret.py --check`。

## 6. 注意事项

- **密钥同步范围**：共享密钥须在 OpenBase 与 OpenMemory 等消费方保持同源；
  轮换时按 §4 顺序执行（先新当前 + 旧宽限，再同步下游，再移除旧）。
- 生产建议配合配置中心/密钥管理服务注入环境变量，不落仓库。
- HS256 内网共享为当前架构；生产长期建议网关升级 RS256 + JWKS（下游验签公钥，
  免共享密钥分发），列为后续演进。

## 7. 待办

| 待办 | 说明 |
| ---- | ---- |
| OpenMemory .env 同步 | 工作区沙箱外，运维执行：`OPENMEMORY_GATEWAY__JWT_SECRET=<新密钥>` 替换 `test-jwt-secret-for-v680` |
| RS256+JWKS（可选演进） | 网关签发 RS256 + 下发 JWKS，下游公钥验签，消除共享密钥分发 |
