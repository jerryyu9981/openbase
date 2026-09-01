# OpenBase-OpenRAG 对接完善任务书

| 项目    | 内容                           |
| ----- | ---------------------------- |
| 项目名称  | OpenBase（开放底座）↔ OpenRAG 系统对接 |
| 任务书版本 | v1.0.2                       |
| 状态    | [Draft]                       |
| 作者    | AD-OpenBase-Dev              |
| 创建日期  | 2026-08-31                   |
| 来源    | v1.4.4 联调发现（L3 冒烟 + 代码核验）    |
| 存放    | doc/design/                  |

***

## 1. 背景

OpenBase v1.4.4（R-380）完成 OpenRAG v1.8.0 对接：rag-proxy 12 端点（JWT 门禁 + 上游认证注入 + {detail} 归一化 + SSE 透传 + multipart 透传）。联调（L3 冒烟 22/22）与代码核验发现 OpenRAG 侧存在若干缺口，需独立会话专项完善。

## 2. 任务清单

| 编号 | 事项                                                                                                          | 优先级 |  状态 | 验收建议                                                                                |
| -- | ----------------------------------------------------------------------------------------------------------- | :-: | :-: | ----------------------------------------------------------------------------------- |
| M1 | **认证体系落地**：OpenRAG HTTP API 无认证（设计文档《OpenRAG-API接口设计文档-v2.1.2》声称 API Key 但代码未实现，认证仅 MCP 通道有）                |  P0 |  ✅ 完成（v1.0.1） | OpenRAG HTTP 全部端点（除健康检查）校验 API Key 或平台签发 JWT；OpenBase rag-proxy 可注入上游认证；无认证直连被拒     |
| M2 | **错误格式统一**：OpenRAG 双错误格式 `{code,message,data,timestamp}` 与 FastAPI `{detail}`（str/dict/list 三种形态）并存，调用方需归一化 |  P1 |  ✅ 完成（v1.0.2） | 错误响应统一为 `{code,message,data}` 单一格式；400/404/409/422/500 均有明确错误码                      |
| M3 | **文档状态枚举统一**：上传/查询返回 `status` 大小写混用（`pending` vs 文档要求 `PENDING`）                                            |  P1 |  待办 | 状态枚举统一大写 `PENDING/PROCESSING/COMPLETED/FAILED`，文档补充状态机说明                            |
| M4 | **v1.3 双前缀路由清理**：历史版本遗留 `/api/v1/api/v1/*` 双前缀路由，易混淆                                                        |  P2 |  待办 | 移除双前缀路由，仅保留标准 `/api/v1/*`；存量调用方迁移说明                                                 |
| M5 | **查询契约一致性**：`POST /collections/{cid}/query*` 单集合路径下请求体仍强制要求 `collection_ids` 字段，语义冗余                        |  P2 |  待办 | 单集合路径自动注入 collection_ids；请求体契约文档对齐                                                 |
| M6 | **部署环境依赖就绪**：Qdrant 向量库未启动（vector_store down，检索降级）；SQLite 沙箱写限制；embedding 模型（BAAI/bge-m3）需下载/配置设备          |  P1 |  待办 | 部署环境一键启动（Qdrant + PG + embedding 模型缓存）；健康检查 vector_store up；文档上传 COMPLETED 含 chunk |

## 3. 联调缺口登记对照（v1.4.4 发现 → 任务项）

| v1.4.4 联调发现                                                                     | 任务项     |
| ------------------------------------------------------------------------------- | ------- |
| OpenRAG `/api/v1/system/health` 显示 vector_store down（Qdrant 6333 不可达）          | M6      |
| 创建知识库依赖 Qdrant（DB 落库成功但 Qdrant 建集合失败 → 500；同名再次创建返回 409）                        | M6      |
| 查询 422：请求体缺 `collection_ids` 返回 FastAPI detail 数组                               | M5 + M2 |
| 文档上传返回 `status: 'pending'` 小写 + `status: 'error'`（文档已存在去重）                      | M3      |
| OpenRAG 文档（设计 v2.1.2）声称 API Key 认证但代码无实现                                        | M1      |
| 非 UUID collection_id 返回 500 `badly formed hexadecimal UUID string`（而非 400/404） | M2      |

## 4. 修订历史

| 版本     | 日期         | 修改人             | 摘要                                                          |
| ------ | ---------- | --------------- | ----------------------------------------------------------- |
| v1.0.2 | 2026-09-01 | OP-OpenBase-Dev | M2 错误格式统一完成：新增全局异常处理器（HTTPException/RequestValidationError/兜底 500 → {code,message,data,trace_id,timestamp}）；错误码 PARAM-4000/AUTH-4010/PERM-4030/NOTFOUND-4040/CONFLICT-4090/VALID-4220/INTERNAL-5000；真实服务 4 场景验证 + 11 单测；顺带修复 M1 引入的测试环境 API Key 回归（conftest 清空） |
| v1.0.1 | 2026-09-01 | OP-OpenBase-Dev | M1 认证落地完成：OpenRAG 启用 APIKeyMiddleware（OPENRAG_API_SERVICE_API_KEY + bypass 增 /api/v1/system）；OpenBase rag-proxy 注入 X-API-Key（settings.rag_api_key）；验证：无 key 401 / 带 key 200 / 健康豁免 / rag-proxy 透传 |
| v1.0.0 | 2026-08-31 | AD-OpenBase-Dev | 初始创建：M1~M6 对接完善事项（认证/错误格式/状态枚举/双前缀/查询契约/部署依赖），来源 v1.4.4 联调 |
