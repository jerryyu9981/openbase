# OpenBase UI 设计文档 - v1.4.4

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.4 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | UI-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/design/ |

---

## 1. 设计范围

| 项 | 内容 |
|----|------|
| 页面 | OpenRAG 模块知识库管理页、RAG 对话页——2 页 mock 真实化（走 OpenBase rag-proxy） |
| 设计基线 | 统一前端 Design Token + Element Plus + v1.4.3 对话管理页交互模式 |
| 不涉及 | 其他 OpenRAG 页面（保持现状）；全局布局/主题不变 |

## 2. 原型设计说明

### 2.1 知识库管理页

| 区域 | 改造后（真实） | 交互状态 |
|------|---------------|---------|
| 工具栏 | 搜索 + 新建知识库按钮 | 加载态：搜索防抖 |
| 表格 | GET /api/v1/rag-proxy/collections 真实数据（名称/描述/分块策略/状态/文档数） | 加载态：表格 loading；空态：el-empty；错误态：提示 + 重试 |
| 行操作 | 详情 / 删除（DELETE）/ 文档管理入口 | 表单提交态：删除确认 popconfirm；成功态：message |
| 新建对话框 | 名称（必填）/描述/分块策略/分块大小/重叠 | 成功态：创建成功提示；409 冲突提示 |
| 文档抽屉 | 文档上传（文件选择 → PENDING → 轮询状态展示 COMPLETED/FAILED）+ 文档列表/删除 | 加载态：上传中；轮询态：进度提示；错误态：解析失败提示 |

### 2.2 RAG 对话页

| 区域 | 改造后（真实） | 交互状态 |
|------|---------------|---------|
| 知识库选择 | 下拉选择知识库（加载 rag-proxy collections） | 加载态/空态（无知识库提示先去创建） |
| 对话区 | 提问 → POST rag-proxy/collections/{cid}/query/stream SSE 流式增量渲染（start/token/done） | 流式态：输入禁用 + 增量渲染 + 停止按钮；错误态：error 事件提示 |
| 来源引用 | done 事件完整结果 + sources（retrieve items：chunk content + score）折叠展示 | 成功态：引用列表 |

### 2.3 交互状态清单（供 Step 4 断言）

| 状态 | 说明 | 断言用途 |
|:-----|:-----|:---------|
| 空态 | 知识库无数据（el-empty「暂无知识库」） | E2E 空列表断言 |
| 错误态 | 请求失败展示（el-message 错误 + 重试按钮） | E2E 错误提示断言 |
| 加载态 | 数据加载中（表格 loading + 按钮禁用） | E2E 加载指示断言 |
| 成功态 | 新建/删除成功（message success） | E2E 成功提示断言 |
| 表单提交态 | 提交中禁用（按钮 loading） | E2E 提交状态断言 |
| 流式态 | RAG 对话中（输入禁用 + 增量渲染 + 停止按钮） | E2E 流式渲染断言 |
| 轮询态 | 文档上传 PENDING/PROCESSING 进度展示 | E2E 文档状态断言 |

## 3. 设计系统说明

| 项 | 规范 |
|----|------|
| 颜色 | 沿用 tokens.css Design Token；文档状态标签（PENDING=warning、COMPLETED=success、FAILED=danger） |
| 组件 | Element Plus：el-table/el-tag/el-dialog/el-drawer/el-input/el-select/el-upload/el-message/el-empty/el-popconfirm |
| 交互模式 | 与 v1.4.3 对话管理页一致（工具行 + 表格 + 行操作 + 二次确认 + message 反馈） |

## 4. 前端实现要点（移交 Step 3）

| # | 要点 | 说明 |
|---|------|------|
| 1 | API 层封装 | 新增 `src/core/api/rag.ts`：listCollections/createCollection/getCollection/deleteCollection/uploadDocument/listDocuments/deleteDocument/ragQuery（SSE）/ragRetrieve/getRagHealth，走 http.ts |
| 2 | SSE 扩展 | parseSseStream 复用（通用 event/data 解析），事件分发新增 start/token/done/error |
| 3 | 知识库管理页 | 数据源替换真实 API；文档上传异步轮询（setInterval 2s → status）；删除二次确认 |
| 4 | RAG 对话页 | 知识库选择 → SSE 流式渲染（token 增量）+ done 后来源引用展示 |
| 5 | 密钥隔离 | 前端零 OpenRAG 地址硬编码（全部经 rag-proxy） |

## 5. 原型（prototype/index.html）

| 项 | 内容 |
|----|------|
| 产出 | `doc/design/prototype/index.html` 追加 v1.4.4 区块（知识库管理页/RAG 对话页/交互状态/API 契约索引） |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | UI-OpenBase-Dev | 初始创建：知识库管理/RAG 对话 2 页真实化设计（原型说明/7 态交互清单/设计系统/实现要点 + SSE 扩展） |
