# OpenBase 模块 CHANGELOG

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.1.0 |
| 说明 | 模块独立 CHANGELOG（TD-11-01，BL-107）；各模块独立版本演进 |

---

## auth（v1.1.0）
- 模块独立版本声明（__version__）
- 前置：登录 bcrypt 异步化、RBAC 数据库权限矩阵、Redis 用户缓存（v1.0.0~1.0.6 继承）

## tenant（v1.1.0）
- 模块独立版本声明
- 前置：EdgeRouter 上下文解析 + 配额（v1.0.0 继承）

## audit（v1.1.0）
- 模块独立版本声明
- 前置：审计中间件全功能（v1.0.0 继承）

## observability（v1.1.0）
- 模块独立版本声明
- 新增：OTLP 告警规则配置（config/alerting/alert-rules.yml）
- 前置：OTel + Langfuse 配置（v1.0.0 继承）

## config（v1.1.0）
- 模块独立版本声明
- 前置：三级合并 + 版本回滚 + DB 持久化（v1.0.0 继承）

## mcp（v1.1.0）
- 模块独立版本声明
- 前置：服务级 API Key 鉴权（v1.0.0 继承）

## org / dict / scheduler / storage / notify（v1.1.0）
- 模块独立版本声明
- notify 新增：多实例 SSE 订阅接收（Redis pub/sub，TD-11-04）
- 前置：数据库落库 + Redis 缓存（v1.0.0 继承）

---

## 版本说明

- 模块版本独立演进：模块升级不影响内核与其他模块（内核 API 冻结）
- 版本生成：`python scripts/gen_versions.py`（自动扫描 __version__ 生成 versions.json）
- 本文件随模块变更持续更新
