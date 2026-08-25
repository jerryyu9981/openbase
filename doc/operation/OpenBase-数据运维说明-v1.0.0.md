# OpenBase 数据运维说明 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Approved] |
| 作者 | OE-OpenBase-Dev |
| 日期 | 2026-08-25 |
| 存放 | doc/operation/ |

---

## 1. 数据库运维

| 项 | 内容 |
|----|------|
| 数据库 | PostgreSQL 14.23（192.168.0.151:5432，共享库 nuct） |
| Schema | openbase（隔离，public 为其他系统） |
| 表 | 17 张（auth + 业务模型） |
| 迁移 | 幂等（metadata.create_all + 种子 WHERE NOT EXISTS），重跑安全 |
| 备份 | 依赖共享库 PG dump 策略（每日） |

## 2. 缓存运维（Redis）

| 键前缀 | 用途 | TTL | 失效策略 |
|--------|------|-----|---------|
| openbase:user:* | 用户查询缓存 | 300s | 过期 |
| openbase:dict:*:items | 字典项缓存 | 300s | 过期 + 变更 delete |
| openbase:notify:* | SSE 广播 channel | - | 消费即弃 |

Redis 不可达时自动降级（缓存禁用，直连 DB），不影响功能。

## 3. 种子数据

| 数据 | 说明 |
|------|------|
| admin 用户 | admin/admin123（bcrypt，生产必须修改） |
| admin 角色 + * 权限 | RBAC 通配（幂等） |
| user_role/role_permission | admin 关联（幂等） |
| 配置 | ConfigStore 持久化（configs + config_versions） |

## 4. 数据一致性

- 配置写入：DB 持久化 + 内存双写（失败回退内存，DB 最终一致）
- 字典缓存：写入/删除时失效键，保证读一致
- RBAC：DB 权限链优先，内存回退（降级提示日志）

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | OE-OpenBase-Dev | 初始创建：DB/缓存/种子/一致性说明 |
