# OpenBase Release Note - v1.4.1

| 项目 | 内容 |
|------|------|
| 版本号 | v1.4.1 |
| 发布日期 | 2026-08-29 |
| 版本主题 | 完整方案 A 类补足（认证汇聚点闭环 + 开发工具链 + 存储适配） |

## 一句话介绍

v1.4.1 补齐服务级 API Key 认证闭环、四维身份头承载、审计上下文、开发工具链（openbase-cli/BaseCRUDRouter）与 MinIO/S3 存储适配，并完成 proxy 通道 JWT + Key 双通道认证接线。

## 为什么升级

| # | 理由 |
|---|------|
| ① | 外部系统接入需服务级 API Key（签发/认证/吊销），此前仅内部实现无 API 层 |
| ② | 四维身份头（X-User-Id/X-Tenant-Id/X-Team-Id/X-Agent-Id）承载后，网关/审计可携带完整身份上下文 |
| ③ | 文件存储支持 MinIO/S3（真实环境验证通过），本地后端可选切换 |
| ④ | 开发工具链（CLI 脚手架 + CRUD 路由自动生成）提升后续版本开发效率 |

## 升级了什么

| 类别 | 变更 |
|------|------|
| 认证 | 服务级 API Key 签发/列表/吊销 API（`/api/v1/auth/api-keys`）+ proxy 通道 JWT 优先/Key 回退双通道认证 |
| 身份 | 四维身份头解析（IdentityContext）+ 审计上下文注入（tenant_id/operator_id） |
| 工具链 | openbase-cli（create-project/create-module/create-crud）+ BaseCRUDRouter 通用 CRUD 路由 |
| 存储 | S3StorageBackend（boto3 懒加载 + 配置驱动 + 本地回退），真实 MinIO 验证通过 |
| 安全 | 越权 403 / 越 scope 403 / 无效 Key 401 全链路门禁 |

## 怎么升级

1. 更新代码至 v1.4.1。
2. 复制 `.env.shared-infra` 配置（或按需设置 `OPENBASE_*` 变量）。
3. 启动后端：`uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000`。
4. 启动前端：`cd openbase-ui && npm run dev`。

## 注意事项

- 服务 Key 为内存存储，进程重启后需重新签发（P2，v1.5+ 接 DB）。
- S3/MinIO 需 `storage_backend=minio` + `MINIO_ENDPOINT` 配置启用，默认本地存储。
- 四系统（OpenLLM/OpenRAG/OpenMemory/DPS）对接挂起，proxy 上游返回 502 为预期。

## 遗留与规划

- v1.4.2：四维身份管理（租户/用户/团队/智能体 CRUD + 管理界面，R-374~377）。
- v1.5+：服务 Key 持久化、测试基座修复、可观测性增强、四系统数据层双维度隔离。

## 反馈

项目问题与建议提交至 PM-OpenBase-Dev。
