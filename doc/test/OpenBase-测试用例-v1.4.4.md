# OpenBase 测试用例 - v1.4.4

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.4 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AT-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/test/ |

---

## 1. 用例索引（TT-ID → RT-ID → TD-ID）

| TT-ID | 用例名称 | T 层 | 关联需求 | 关联代码 | 断言级别 |
|-------|---------|:---:|----------|----------|:--------:|
| TT-144-001 | rag-proxy 未认证 401 + AUTH_401 | T2 | AC-144-02-1/03-5 | TD-144-02/03 | L1 |
| TT-144-002 | 知识库列表统一响应 + 分页透传 + 无密钥注入 | T2 | AC-144-03-1/2 | TD-144-03 | L1 |
| TT-144-003 | 知识库创建（200/409 归一化） | T2 | AC-144-03-2/05-1 | TD-144-03 | L1 |
| TT-144-004 | 知识库详情/删除 | T2 | AC-144-03-1 | TD-144-03 | L1 |
| TT-144-005 | {detail} 归一化（str/dict/list + 网关码） | T2 | AC-144-03-3 | TD-144-06 | L1 |
| TT-144-006 | 文档上传 multipart + 文档详情轮询 + 列表/删除 | T2 | AC-144-03-1/05-2 | TD-144-04 | L1 |
| TT-144-007 | RAG 查询/检索（含 collection_ids 透传） | T2 | AC-144-03-1/05-3 | TD-144-05 | L1 |
| TT-144-008 | SSE 流式透传（start/token/done/error/中断） | T2 | AC-144-03-4/05-4 | TD-144-05 | L1 |
| TT-144-009 | health 透传 + 上游不可达 502 | T2 | AC-144-01-1/03-6 | TD-144-06 | L1 |
| TT-144-010 | 双系统集成链路（登录→知识库→查询→SSE） | T2 | AC-144-05-1~4 | TD-144-10 | L1 |
| TT-144-011 | T3a 巡检：知识库管理页/RAG 对话页网络层 | T3a | AC-144-04-1/2/4 | TD-144-08/09 | L1+L4 |
| TT-144-012 | E2E：登录→知识库列表→详情→上传→SSE 对话 | T3b | AC-144-04-1/2/05-4 | TD-144-07~10 | L1+L4 |
| TT-144-013 | 安全：鉴权 401 全覆盖 + 日志脱敏 + 无上游密钥 | T2 | AC-144-02-1/03-5 | TD-144-02 | L1 |
| TT-144-014 | 性能：rag-proxy 转发响应时间（P95） | - | 非功能 §6 | TD-144-03~06 | L1 |
| TT-144-015 | 回归：全量 pytest（既有 + 新增无回归） | - | AC-144-07-1 | TD-144-12 | L1 |
| TT-144-016 | 覆盖率：rag_proxy 新代码行覆盖率 | - | AC-144-07-2 | TD-144-12 | L1 |
| TT-144-017 | UAT：知识库管理页走查（真实数据/CRUD/错误态） | T4 | AC-144-04-1/4 | TD-144-08 | L1 |
| TT-144-018 | UAT：RAG 对话页走查（选择/流式/中止/错误提示） | T4 | AC-144-04-2/4 | TD-144-09 | L1 |

## 2. 用例详述（关键用例）

### TT-144-001 rag-proxy 未认证 401

| 项 | 内容 |
|----|------|
| 前置条件 | OpenBase 8000 运行；rag_proxy 已启用 |
| 测试步骤 | 1) GET /api/v1/rag-proxy/collections（无 Authorization 头）；2) POST /api/v1/rag-proxy/collections/{cid}/query/stream（无认证） |
| 预期结果 | 两者均返回 401，响应 code=AUTH_401 |
| 三要素 | 状态码 401 + 结构 {code,message,detail,request_id} + 边界（POST/GET 均拦截） |
| 证据 | pytest test_rag_proxy.py::test_rag_proxy_no_token_returns_401 + test_rag_proxy_sse_requires_auth |

### TT-144-002 知识库列表统一响应

| 项 | 内容 |
|----|------|
| 前置条件 | 登录获取 token；OpenRAG 8010 运行 |
| 测试步骤 | 1) GET /api/v1/rag-proxy/collections?page=1&page_size=20（带 token） |
| 预期结果 | 200；响应 {code:0, message:"success", data:{items,total,...}, timestamp}；上游无 Authorization/X-API-Key 注入 |
| 三要素 | 状态码 200 + 结构统一 + 边界（分页参数透传） |
| 证据 | pytest test_rag_proxy_collections_list_success + L3 冒烟 |

### TT-144-003 知识库创建

| 项 | 内容 |
|----|------|
| 前置条件 | 登录获取 token |
| 测试步骤 | 1) POST /api/v1/rag-proxy/collections {name:"...", chunk_size:512, chunk_overlap:50}；2) 同名再次创建 |
| 预期结果 | 1) 200（上游 Qdrant 就绪时）或 500/409 归一化（Qdrant down）；2) 409 {code:409, message 含"已存在"} 透传 |
| 三要素 | 状态码（200/409）+ 结构统一 + 边界（必填 name / 重复名称） |
| 证据 | pytest test_rag_proxy_collection_create_success + L3 冒烟 409 |

### TT-144-005 {detail} 归一化

| 项 | 内容 |
|----|------|
| 前置条件 | 登录获取 token |
| 测试步骤 | 1) 404 {detail:"知识库不存在: xxx"}；2) 409 {detail:{error,code,message}}；3) 422 {detail:[{msg},...]}；4) 500 {code:5000,message} |
| 预期结果 | 统一 {code,message,data:null,timestamp}；提取顺序 body.code > detail(str/dict/list) > error.code > HTTP 状态码 |
| 三要素 | 状态码透传 + 结构统一 + 边界（4 种错误形态） |
| 证据 | pytest 4 个归一化用例 + L3 冒烟 |

### TT-144-008 SSE 流式透传

| 项 | 内容 |
|----|------|
| 前置条件 | 登录获取 token；OpenRAG 8010 运行 |
| 测试步骤 | 1) POST /collections/{cid}/query/stream {query, collection_ids, stream:true}；2) 上游 4xx；3) 上游中断 |
| 预期结果 | 1) 200 + text/event-stream + start/token/done 事件；2) error 事件透传；3) error 事件 + 连接关闭 |
| 三要素 | 状态码 200 + Content-Type + 事件保序 |
| 证据 | pytest 3 个 SSE 用例 + L3 冒烟 + 浏览器流式渲染 |

### TT-144-012 E2E 核心流程

| 项 | 内容 |
|----|------|
| 前置条件 | 三服务运行；admin/admin123 |
| 测试步骤 | 1) 登录 → 2) 知识库管理页真实列表 → 3) 详情 → 4) 文档上传（PENDING→轮询）→ 5) RAG 对话页提问 → SSE 流式回答 |
| 预期结果 | 全流程无阻塞；页面无代码类 HTTP≥500 / requestfailed / console error |
| 断言 | L1（关键交互 wait_for+assert）+ L4（网络层断言 assert_network_clean） |
| 证据 | L3 冒烟 + 浏览器走查（Step 3 已执行，Step 4 复测） |

## 3. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | AT-OpenBase-Dev | 初始创建：18 用例（TT-144-001~018）关联 RT-ID/TD-ID，覆盖 API/集成/T3a/E2E/安全/性能/回归/覆盖率/UAT |
