# OpenBase 设计开发追溯矩阵 TD-ID - v1.4.3

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.3 |
| 文档版本 | v1.0.0 |
| 状态 | [Draft] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/development/ |

---

## 1. 追溯矩阵（DT → TD → 文件）

| DT-ID（设计项） | TD-ID（开发项） | BL-ID | 涉及文件 | 状态 |
|----------------|-----------------|-------|----------|:----:|
| DT-143-01 服务接入 | TD-143-01 OpenLLM 8001 启动 + 健康检查 + 端口治理 | BL-143-01 | OpenLLM 项目（backend/main.py，PORT=8001）；启动验证 | ✅ 完成（/health healthy v2.13.0） |
| DT-143-02 认证适配 | TD-143-02 settings llm_* 配置 + Bearer 注入 | BL-143-02 | `openbase/settings.py`（llm_api_key/llm_upstream_base/llm_upstream_timeout/llm_stream_timeout）；`.env`（OPENBASE_LLM_API_KEY） | ✅ 完成（真实 Key 联调通过） |
| DT-143-03 proxy 转发 | TD-143-03 llm_proxy 模块（models/chat/health + 统一响应 + 错误透传） | BL-143-03 | `openbase/modules/llm_proxy/__init__.py`（新建）；`openbase/demo_app.py`（enable_module）；`tests/test_llm_proxy.py`（新建） | ✅ 完成（真实 11 模型） |
| DT-143-04 SSE 透传 | TD-143-04 chat/stream SSE 逐事件透传 | BL-143-03 | `openbase/modules/llm_proxy/__init__.py`（_forward_sse） | ✅ 完成（routing/error 事件透传验证） |
| DT-143-05 模型页真实化 | TD-143-05 Models.vue 数据源真实化 + llm.ts API 层 | BL-143-04 | `openbase-ui/src/core/api/llm.ts`（新建）；`openbase-ui/src/modules/openllm/pages/Models.vue`（改造） | ✅ 完成（真实 API + 写操作禁用） |
| DT-143-06 对话页真实化 | TD-143-06 Conversations.vue 真实化 + parseSSEStream + 聊天视图 | BL-143-04 | `openbase-ui/src/core/api/llm.ts`（SSE 封装）；`openbase-ui/src/modules/openllm/pages/Conversations.vue`（改造） | ✅ 完成（真实 API + SSE 流式） |
| DT-143-07 双系统联调 | TD-143-07 联调闭环（登录→模型→对话） | BL-143-05 | 联调验证（真实链路冒烟） | ⚠️ 部分完成（模型/SSE 闭环✅；对话回复需 OpenLLM 可用模型，登记任务书） |
| DT-143-08 任务书 | TD-143-08 对接完善任务书 | BL-143-06 | `doc/design/OpenBase-OpenLLM对接完善任务书-v1.0.0.md` | ✅ 已完成（v1.0.0） |
| DT-143-09 收尾还债 | TD-143-09 回归/覆盖率/发布 | BL-143-07 | 测试基座复用（全量回归 231 通过） | ✅ 完成（回归 ✅；覆盖率随 Step 4） |

## 2. Subtask CheckList（子任务状态表）

| 子任务 | 设计规划文件操作 | 实际状态 | 偏差 |
|--------|------------------|:--------:|------|
| TD-143-02 配置 | settings.py 新增 llm_* 4 项 | ✅ 完成（settings + .env） | 无（.env 需 OPENBASE_ 前缀，已修正） |
| TD-143-03 模块 | 新建 openbase/modules/llm_proxy/__init__.py | ✅ 完成（12 端点 + __version__） | 无 |
| TD-143-03 挂载 | demo_app.py enable_module + "llm_proxy" | ✅ 完成 | 无 |
| TD-143-03 测试 | 新建 tests/test_llm_proxy.py | ✅ 完成（7 用例） | 无 |
| TD-143-05 API 层 | 新建 openbase-ui/src/core/api/llm.ts | ✅ 完成（9 方法 + parseSseStream） | 无 |
| TD-143-05 页面 | Models.vue 改造 | ✅ 完成 | 写操作禁用（M2 登记） |
| TD-143-06 页面 | Conversations.vue 改造 | ✅ 完成 | 会话端点 401（M1 登记） |

## 3. 版本控制记录（分支策略 + commit 约定）

| 项 | 内容 |
|----|------|
| 分支策略 | git-flow（沿用项目既有约定）：本次开发在 `feature/v1.4.3-openllm` 分支，完成后合并 develop |
| commit 格式 | `type(scope): subject`，footer 引用 TD-ID（如 `refs TD-143-03`） |
| TDD 合规 | feat/fix 提交必须包含对应测试文件变更；测试先于生产代码提交 |
| 备份 | 提交前 .devflow hooks（post-push）自动备份；重要节点打标 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | AD-OpenBase-Dev | 初始创建：DT→TD 追溯矩阵（9 项）、Subtask CheckList、版本控制记录 |
