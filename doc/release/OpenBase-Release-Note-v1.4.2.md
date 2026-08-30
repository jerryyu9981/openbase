# OpenBase Release Note - v1.4.2

| 项目 | 内容 |
|------|------|
| 版本号 | v1.4.2 |
| 发布日期 | 2026-08-30 |
| 版本主题 | 四维身份管理基础（租户/用户）+ OpenMemory 对接 |

## 一句话介绍

v1.4.2 落地四维身份管理基础（租户/用户 CRUD + 管理界面）并完成 OpenMemory 系统对接：统一认证签发 JWT 后经 memory-proxy 双通道真实读写记忆，前端列表/详情页替换为真实数据，全链路联调闭环。

## 为什么升级

| # | 理由 |
|---|------|
| ① | 四维身份此前仅有身份头承载（R-369）无真实管理 API/界面，租户/用户管理缺失阻塞 OpenMemory JWT 签发（VC-008） |
| ② | 用户明确"逐个系统对接，先对接 OpenMemory"（VC-010），双层认证（X-API-Key + JWT）打通后记忆功能真实可用 |
| ③ | 多模态/语音能力（图像记忆、图像嵌入、语音转写、语音记忆）补齐，指南 5.4/5.5 全部代理透传 |

## 升级了什么

| 类别 | 变更 |
|------|------|
| 租户管理 | Tenant CRUD API + 管理界面（创建/编辑/停用/配额/列表），R-374 |
| 用户管理 | User CRUD API + 管理界面（创建/启停/角色分配/列表），R-375 |
| OpenMemory 对接 | 8020 持久环境部署 + 双层认证共享 + memory-proxy 转发（remember/recall/forget/list/详情）+ 前端 2 页真实化，R-378 |
| 对接完善 | X-Tenant-ID 注入 / 错误体提取完善（error>code>detail + retry_after 透传）/ improve/sessions/decay/traces/monitor/health 端点，R-379 |
| 多模态/语音 | memories/image（上传/搜索）、multimodal/image-embed、audio/transcribe、remember-with-audio 5 端点代理，R-380 |
| 测试基座 | 回归脚本化（run_regression.py 子进程隔离 + 崩溃重试），全量 222/222、覆盖率 87%、UAT 13/13 |

## 怎么升级

1. 更新代码至 v1.4.2。
2. OpenMemory：`cd D:\Trae CN\myproject\Dev\OpenMemory && python scripts/start_openmemory.py`（8020，真实 Qdrant/PG/Redis 持久后端）。
3. OpenBase：注入 `POSTGRES_URL`/`REDIS_URL`/`OPENBASE_JWT_SECRET` 后 `uvicorn openbase.demo_app:app --port 8000`。
4. 前端：`cd openbase-ui && npm run dev`。

## 注意事项

- OpenMemory 模型下载走镜像（`HF_ENDPOINT=https://hf-mirror.com` + `HF_HUB_DISABLE_XET=1`，已固化在启动脚本）。
- torch 运行库需 VC++ 14.50（System32 旧版 14.00 会触发 c10.dll WinError 1114，修复方式见测试报告附录 C.5）。
- RBAC 经 `X-Org-ID=openbase-default` 放行（P2，后续按组织策略细化）。
- recall 结果缓存（Redis `om:result:*`）可能陈旧，数据新鲜度敏感场景清缓存。

## 遗留与规划

- v1.5+：团队/智能体管理（R-376/R-377 顺延）、服务 Key 持久化、测试基座修复、可观测性增强、四系统数据层双维度隔离、平台治理与协同集成。
- 本版本 P2 遗留：recall 缓存陈旧 / OpenMemory 软删除过滤 / RBAC 放行 / Neo4j 图检索未启用。

## 反馈

项目问题与建议提交至 PM-OpenBase-Dev。
