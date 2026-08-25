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

## v1.1.0（2026-08-25）— 四系统接入准备 + 生产就绪

**核心能力**：回灌兼容层（openbase/compat）、AI 编码规则、模块独立版本、OTLP 告警配置、多实例 SSE（Redis pub/sub 跨实例广播）、PyPI/Pro 发布工具链。

**关键交付**：
- 兼容层：字段映射/函数别名/回滚提示（四系统接入桥接）
- 模块独立版本：11 模块 `__version__` + versions.json + 模块 CHANGELOG
- OTLP 告警：alert-rules.yml 四规则（P99/登录失败/宕机/5xx）
- 多实例 SSE：真实 Redis 订阅→发布→接收闭环验证通过
- 发布工具链：build_release.ps1 / deploy_pro.ps1（蓝绿/金丝雀）
- 质量：119 测试全通过、覆盖率 90%、ruff 0 错误
- 部署：Dev 上线检查 8/8，tag v1.1.0 三处一致

**完整说明**：[版本发布说明 v1.1.0](OpenBase-版本发布说明-v1.1.0.md)

---

## 历史版本

| 版本 | 日期 | 摘要 |
|------|------|------|
| [v1.0.0](OpenBase-版本发布说明-v1.0.0.md) | 2026-08-25 | 首个可用底座（框架内核 + 11 模块 + 基础设施接入） |
| v1.1.0（当前） | 2026-08-25 | 四系统接入准备 + 生产就绪 |
