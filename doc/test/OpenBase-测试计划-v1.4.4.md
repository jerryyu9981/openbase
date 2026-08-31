# OpenBase 测试计划 - v1.4.4

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

## 1. 测试目标与范围

| 项 | 内容 |
|----|------|
| 测试目标 | 验证 R-380 OpenRAG 对接：rag-proxy 12 端点功能正确、JWT 门禁有效、{detail} 归一化完整、SSE 透传正确、前端 2 页真实化可用、无回归 |
| 包含范围 | rag-proxy 全部端点（collections 4 + documents 4 + query 3 + health 1）、OpenBase↔OpenRAG 集成链路、前端知识库管理页/RAG 对话页、全量回归 + 覆盖率 |
| 排除范围 | OpenRAG 侧 M1~M6 待完善项（认证/错误格式/状态枚举/双前缀/查询契约/部署依赖，见任务书）、四系统统一集成测试（v1.5） |
| 版本边界 | v1.4.4 增量（rag_proxy 模块 + 前端 2 页 + 配置）；不涉及 OpenMemory/OpenLLM/DPS 回归改动 |

## 2. 测试环境

| 服务 | 端口 | 版本 | 启动命令 | 状态 |
|------|:---:|------|----------|:----:|
| OpenBase 后端 | 8000 | v1.4.4 | `python -m uvicorn openbase.demo_app:app` | ✅ 运行中 |
| OpenRAG 后端 | 8010 | v1.8.0 | `$env:OPENRAG_API_PORT='8010'; & .venv3\python.exe -m uvicorn openrag.main:app --app-dir src` | ✅ 运行中（health: database up / vector_store down） |
| OpenBase 前端 | 5173 | v1.4.4 | `npm run dev`（openbase-ui） | ✅ 运行中 |
| 认证配置 | - | - | OpenBase admin/admin123（内存降级）；OpenRAG 无认证（OpenBase 唯一入口） |
| 环境遗留 | - | - | Qdrant 6333 未启动（vector_store down，检索降级）；SQLite 沙箱写限制（联调用临时库） |

## 3. 测试矩阵（计划）

| 测试类别 | T 层 | 用例数 | 方式 | 通过标准 |
|----------|:---:|:---:|------|----------|
| API 测试（rag-proxy） | T1+T2 | 22（pytest）+ 12 端点三要素 | pytest + 真实链路 curl | P0/P1 全通过，无非预期 5xx |
| 集成测试（双系统链路） | T2 | 4 | 真实链路（登录→知识库→文档→查询/SSE） | 关键链路有效执行 |
| T3a 全页面巡检 | T3a | 2 页（知识库管理/RAG 对话）+ 相关页 | 浏览器巡检（HTTP/console/渲染） | 无代码类 HTTP≥500 / requestfailed / console error |
| E2E 测试 | T3b | 4 | 核心流程（列表/详情/上传/SSE 对话） | 通过率 ≥95% |
| 回归测试（后端全量） | - | 全量 | `python -m pytest tests` | ≥95% 通过，P0/P1 闭环 |
| 覆盖率（rag_proxy 模块） | - | - | `python -m pytest --cov=openbase` | 新代码 ≥80% |
| 合规/安全快检 | - | 4 | 鉴权 401/越权/日志脱敏/密钥 | 无阻塞问题 |
| 性能快检 | - | 2 | rag-proxy 转发响应时间 | P95 ≤ 500ms（不含上游处理） |
| UAT 走查 | T4 | 2 页面 | 页面级走查（知识库管理 + RAG 对话） | 核心业务流通过 |

## 4. 执行顺序

```
环境验证 → 自测证据抽查 → API 测试（4.3a）→ 集成测试（4.4a）→ T3a 巡检（4.3b'）
→ E2E（4.5）→ 全量回归 + 覆盖率（4.6）→ 安全/性能快检（4.7）→ UAT（4.8）
→ 缺陷闭环（4.9）→ 报告（4.10）→ 测试回溯审计（4.11）
```

## 5. 已知限制与跳过项（测试前声明）

| 跳过项 | 原因 | 影响 | 补救 |
|--------|------|------|------|
| RAG 真实检索命中（retrieve 返回命中 items） | Qdrant 6333 未启动（vector_store down），检索链路降级 | query 返回降级 answer（如"未找到相关信息"） | 验证降级行为符合预期；M6（Qdrant 就绪）后补测真实检索 |
| 创建知识库 200 成功链路 | 沙箱写限制 + Qdrant down → 上游 500/409 归一化 | 创建成功路径无法真实落库验证 | 验证 500/409 归一化透传符合契约；Step 5 部署环境补测 |
| 文档上传 COMPLETED 终态 | embedding 模型 + Qdrant 依赖（M6） | 上传返回 pending/error（去重） | 验证状态机响应；M6 后补测 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | AT-OpenBase-Dev | 初始创建：测试目标/环境/矩阵/执行顺序/已知限制声明 |
