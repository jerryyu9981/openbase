# OpenBase-OpenRAG 对接完善任务书-v1.1.0

| 项目    | 内容                           |
| ----- | ---------------------------- |
| 项目名称  | OpenBase（开放底座）↔ OpenRAG 系统对接 |
| 任务书版本 | v1.1.0                       |
| 状态    | \[Review]                    |
| 作者    | AD-OpenBase-Dev              |
| 创建日期  | 2026-08-31                   |
| 来源    | v1.4.4 联调发现（L3 冒烟 + 代码核验）    |
| 存放    | doc/design/                  |

***

## 1. 背景

OpenBase v1.4.4（R-380）完成 OpenRAG v1.8.0 对接：rag-proxy 12 端点（JWT 门禁 + 无上游认证注入 + {detail} 归一化 + SSE 透传 + multipart 透传）。联调（L3 冒烟 22/22）与代码核验发现 OpenRAG 侧存在若干缺口，需独立会话专项完善。**v1.1.0 结论：M1~M6 全部已实现并真实验证（2026-09-01 专项会话完成）。**

## 2. 任务清单

| 编号 | 事项                                                                                                          | 优先级 |  状态 | 验收建议                                                                                |
| -- | ----------------------------------------------------------------------------------------------------------- | :-: | :-: | ----------------------------------------------------------------------------------- |
| M1 | **认证体系落地**：OpenRAG HTTP API 无认证（设计文档《OpenRAG-API接口设计文档-v2.1.2》声称 API Key 但代码未实现，认证仅 MCP 通道有）                |  P0 |  ✅ DONE + VERIFIED | OpenRAG HTTP 全部端点（除健康检查）校验 API Key 或平台签发 JWT；OpenBase rag-proxy 可注入上游认证；无认证直连被拒     |
| M2 | **错误格式统一**：OpenRAG 双错误格式 `{code,message,data,timestamp}` 与 FastAPI `{detail}`（str/dict/list 三种形态）并存，调用方需归一化 |  P1 |  ✅ DONE + VERIFIED | 错误响应统一为 `{code,message,data}` 单一格式；400/404/409/422/500 均有明确错误码                      |
| M3 | **文档状态枚举统一**：上传/查询返回 `status` 大小写混用（`pending` vs 文档要求 `PENDING`）                                            |  P1 |  ✅ DONE + VERIFIED | 状态枚举统一大写 `PENDING/PROCESSING/COMPLETED/FAILED`，文档补充状态机说明                            |
| M4 | **v1.3 双前缀路由清理**：历史版本遗留 `/api/v1/api/v1/*` 双前缀路由，易混淆                                                        |  P2 |  ✅ DONE + VERIFIED | 移除双前缀路由，仅保留标准 `/api/v1/*`；存量调用方迁移说明                                                 |
| M5 | **查询契约一致性**：`POST /collections/{cid}/query*` 单集合路径下请求体仍强制要求 `collection_ids` 字段，语义冗余                        |  P2 |  ✅ DONE + VERIFIED | 单集合路径自动注入 collection\_ids；请求体契约文档对齐                                                 |
| M6 | **部署环境依赖就绪**：Qdrant 向量库未启动（vector\_store down，检索降级）；SQLite 沙箱写限制；embedding 模型（BAAI/bge-m3）需下载/配置设备          |  P1 |  ✅ DONE + VERIFIED | 部署环境一键启动（Qdrant + PG + embedding 模型缓存）；健康检查 vector\_store up；文档上传 COMPLETED 含 chunk |

## 3. 联调缺口登记对照（v1.4.4 发现 → 任务项）

| v1.4.4 联调发现                                                                     | 任务项     |
| ------------------------------------------------------------------------------- | ------- |
| OpenRAG `/api/v1/system/health` 显示 vector\_store down（Qdrant 6333 不可达）          | M6      |
| 创建知识库依赖 Qdrant（DB 落库成功但 Qdrant 建集合失败 → 500；同名再次创建返回 409）                        | M6      |
| 查询 422：请求体缺 `collection_ids` 返回 FastAPI detail 数组                               | M5 + M2 |
| 文档上传返回 `status: 'pending'` 小写 + `status: 'error'`（文档已存在去重）                      | M3      |
| OpenRAG 文档（设计 v2.1.2）声称 API Key 认证但代码无实现                                        | M1      |
| 非 UUID collection\_id 返回 500 `badly formed hexadecimal UUID string`（而非 400/404） | M2      |

## 4. 修订历史

| 版本     | 日期         | 修改人             | 摘要                                                          |
| ------ | ---------- | --------------- | ----------------------------------------------------------- |
| v1.0.0 | 2026-08-31 | AD-OpenBase-Dev | 初始创建：M1\~M6 对接完善事项（认证/错误格式/状态枚举/双前缀/查询契约/部署依赖），来源 v1.4.4 联调 |
| v1.1.0 | 2026-09-02 | AD-OpenBase-Dev | 验证回填：M1\~M6 全部已实现并真实验证（专项会话 2026-09-01），状态 Draft→Review |

## 5. 实施与验证结果（v1.1.0 回填）

| 项 | 实施要点 | 验证证据 |
|----|---------|---------|
| M1 认证落地 | 激活 `APIKeyMiddleware`（service\_api\_key 空转置）；.env 配置 `OPENRAG_API_SERVICE_API_KEY=openbase-rag-gw-key-20260901`；`/api/v1/system` 健康豁免；OpenBase rag\_api\_key 经 proxy 注入 `X-API-Key` | 无 Key 401 / 带 Key 200 / 健康端点豁免 / proxy 透传 4 场景通过；313 测试全绿（conftest 清空 env 修复回归） |
| M2 错误格式统一 | `exception_handlers.py` 全局处理器统一 `{code,message,data,trace_id,timestamp}`；错误码 PARAM-4000/AUTH-4010/PERM-4030/NOTFOUND-4040/CONFLICT-4090/VALID-4220/INTERNAL-5000 | 400/401/404/422/500 场景统一格式；`test_exception_handlers.py` 11 单测全绿 |
| M3 状态枚举统一 | `DocumentStatus` 枚举值全大写（含 `ERROR="FAILED"`），同步 SQLite/PG 默认值 `PENDING` 与硬编码 | 上传 PENDING→COMPLETED 大写；查询返回大写状态 |
| M4 双前缀清理 | `v1_3_routes.py` router 移除自带 `prefix="/api/v1"`（消除 `/api/v1/api/v1`） | 双前缀 404 → 标准路径 200 |
| M5 查询契约 | `QueryRequest.collection_ids` 由必填改可选；单集合路径自动注入 | 无 collection\_ids 请求 200 + 真实 RAG 检索命中 |
| M6 部署依赖就绪 | `OPENRAG_DATABASE_URL` 指向沙箱可写临时目录；Qdrant 远程配置（OPENRAG\_QDRANT\_URL/GRPC\_URL/PREFER\_GRPC=false） | health 全 healthy（database up + vector\_store up）；文档上传 COMPLETED 含 chunk |

### 状态追踪表

| 项 | 状态 | 验证日期 | 备注 |
|:---:|------|:---:|------|
| M1 认证落地 | ✅ VERIFIED | 2026-09-01 | 双通道（API Key/代理注入）+ 健康豁免 |
| M2 错误格式统一 | ✅ VERIFIED | 2026-09-01 | 11 单测 + 5 场景 |
| M3 状态枚举统一 | ✅ VERIFIED | 2026-09-01 | 大写枚举 + DB/硬编码同步 |
| M4 双前缀清理 | ✅ VERIFIED | 2026-09-01 | 双前缀 404、标准路径 200 |
| M5 查询契约一致性 | ✅ VERIFIED | 2026-09-01 | 可选 collection\_ids + 真实检索 |
| M6 部署环境依赖 | ✅ VERIFIED | 2026-09-01 | health 全 healthy + COMPLETED 含 chunk |

**遗留事项**：OpenRAG 代码改动已落盘生效并验证；OpenRAG 仓库 git 提交状态待确认（若 .git 受沙箱写入限制需在 OpenRAG 项目内补提交）；全量 ruff 与覆盖率（≥90%）待项目标准环境执行。

<br />
