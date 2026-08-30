# OpenBase 测试计划 - v1.4.3

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.3 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AT-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/test/ |

---

## 1. 测试目标与范围

| 项 | 内容 |
|----|------|
| 测试目标 | 验证 R-379 OpenLLM 对接：llm-proxy 12 端点功能正确、认证注入有效、SSE 透传完整、前端 2 页真实化可用、无回归 |
| 包含范围 | llm-proxy 全部端点（models/models{id}/chat/chat-stream/health/conversations 族）、OpenBase↔OpenLLM 集成链路、前端模型管理/对话管理页、全量回归 |
| 排除范围 | OpenLLM 侧 M1/M2 待完善项（会话端点 401 预期、模型写操作禁用）、四系统统一集成测试（v1.5） |
| 版本边界 | v1.4.3 增量（llm_proxy 模块 + 前端 2 页 + 配置）；不涉及 OpenMemory/OpenRAG/DPS 回归改动 |

## 2. 测试环境

| 服务 | 端口 | 版本 | 启动命令 |
|------|:---:|------|----------|
| OpenBase 后端 | 8000 | v1.4.3 | `python -m uvicorn openbase.demo_app:app`（openbase 目录） |
| OpenLLM 后端 | 8001 | v2.13.0 | `cd Dev\OpenLLM\backend && $env:PORT=8001; python -m uvicorn main:app` |
| OpenBase 前端 | 5173 | v1.4.3 | `npm run dev`（openbase-ui，UAT 走查时启动） |
| 依赖 | - | - | PostgreSQL/Redis（OpenLLM 需用；OpenBase 内存降级可用） |
| 认证配置 | - | - | OpenBase `.env`：OPENBASE_LLM_API_KEY（OpenLLM 创建的服务 Key） |

## 3. 测试矩阵（计划）

| 测试类别 | T 层 | 用例数 | 方式 | 通过标准 |
|----------|:---:|:---:|------|----------|
| API 测试（llm-proxy） | T2 | 7 | pytest + curl 实测 | P0/P1 全通过，无非预期 5xx |
| 集成测试（双系统链路） | T2 | 3 | curl 真实链路 | 登录→模型→SSE 闭环 |
| 回归测试（后端全量） | - | 231 | `python -m pytest tests` | ≥95% 通过，P0/P1 闭环 |
| 回归测试（前端） | T2 | 35 | `npx vitest run` | 全通过 |
| 覆盖率（llm_proxy 模块） | - | - | `pytest --cov` | 新代码 ≥80% |
| 合规/安全快检 | - | 3 | 检查密钥/日志/鉴权 | 无阻塞问题 |
| UAT 走查 | T4 | 2 页面 | 页面级走查 | 核心业务流通过 |

## 4. 执行顺序

```
环境验证 → API 测试（4.3a）→ 集成测试（4.4a）→ 全量回归 + 覆盖率（4.6）
→ 合规/安全快检（4.7）→ UAT 走查（4.8）→ 缺陷闭环（4.9）→ 报告（4.10）
```

## 5. 已知限制与跳过项（测试前声明）

| 跳过项 | 原因 | 影响 | 补救 |
|--------|------|------|------|
| 会话端点（conversations）业务测试 | OpenLLM M1 未实施（JWT-only），API Key 通道 401 | 对话管理页会话列表降级 | 验证 401 透传行为符合预期；M1 实施后补测 |
| 模型写操作（新增/编辑/删除） | OpenLLM M2 未实施（管理员 JWT），前端禁用 | 模型页只读 | 验证禁用提示；M2 实施后补测 |
| 对话真实回复内容 | OpenLLM 本地模型（qwen3:0.6b）未运行/无云端 Key | chat 返回 5001 | 验证错误透传；配置可用模型后补测 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | AT-OpenBase-Dev | 初始创建：测试目标/环境/矩阵/执行顺序/已知限制声明 |
