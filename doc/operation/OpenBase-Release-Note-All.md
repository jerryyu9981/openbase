# OpenBase Release Notes（Changelog）

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档性质 | 全部版本发布说明汇总（长期维护） |
| 存放 | doc/operation/ |

---

## v1.0.0（2026-08-25）— 首个可用底座

**核心能力**：框架内核（models/db/deps/errors/settings + 统一鉴权/错误契约）、11 业务模块（auth/tenant/audit/observability/config/mcp/org/dict/scheduler/storage/notify）、工具链（cli/BaseCRUDRouter）、共享基础设施接入（PG schema 隔离 + Redis 缓存）。

**关键交付**：
- 四系统代码抽取增强（config/tenant/observability/errors/auth/audit/mcp）
- 数据库落库：17 张表（auth + 6 模块业务表）
- 安全：统一鉴权中间件（JWT）、MCP API Key、RBAC 数据库权限矩阵
- 缓存：Redis（用户/dict TTL + notify 广播，降级保护）
- 质量：105 测试全通过、覆盖率 90%、ruff 0 错误

**完整说明**：[版本发布说明 v1.0.0](OpenBase-版本发布说明-v1.0.0.md)

---

## 历史版本

（无历史版本，v1.0.0 为首个发布版本）
