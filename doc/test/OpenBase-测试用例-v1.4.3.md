# OpenBase 测试用例 - v1.4.3

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

## 1. API 测试用例（T2，llm-proxy 12 端点覆盖）

| TT-ID | 关联需求（FR） | 关联代码（TD） | 用例名称 | 测试文件/命令 | 预期结果 |
|-------|---------------|---------------|----------|---------------|----------|
| TT-143-001 | FR-143-03 | TD-143-03 | llm-proxy 无认证 401 | tests/test_llm_proxy.py | 401 + AUTH_401 |
| TT-143-002 | FR-143-03/05 | TD-143-03/05 | models 列表真实数据 | tests/test_llm_proxy.py + 实测 | 200 + code=0 + models 数组 |
| TT-143-003 | FR-143-03/05 | TD-143-03/05 | models/{id} 详情 | tests/test_llm_proxy.py + 实测 | 200 + 模型对象 |
| TT-143-004 | FR-143-03 | TD-143-03 | chat 对话（错误透传） | tests/test_llm_proxy.py + 实测 | 上游 5001 → code=5001 透传 |
| TT-143-005 | FR-143-04 | TD-143-04 | chat/stream SSE 透传 | tests/test_llm_proxy.py（3 用例）+ 实测 | routing/chunk/done 逐事件透传 |
| TT-143-006 | FR-143-03 | TD-143-03 | health 健康透传 | tests/test_llm_proxy.py + 实测 | 200 + status=healthy |
| TT-143-007 | FR-143-06 | TD-143-06 | conversations（M1 预期 401） | 实测 + 单测（转发契约） | 401 透传（符合 M1 声明） |
| TT-143-008 | FR-143-03 | TD-143-03 | conversations 端点族转发契约 | tests/test_llm_proxy.py（list/create/detail/delete/archive/messages 6 用例） | 200 + 统一响应 + 参数/body 透传 |
| TT-143-009 | FR-143-03 | TD-143-03 | models/{id} 降级（不存在/上游错误） | tests/test_llm_proxy.py（2 用例） | 2001→404 / 上游错误透传 |

## 2. 集成测试用例（T2）

| TT-ID | 关联需求 | 关联代码 | 用例名称 | 方式 | 预期结果 |
|-------|---------|---------|----------|------|----------|
| TT-143-010 | FR-143-05/07 | TD-143-07 | 登录→模型→SSE 闭环 | Python 实测（OpenBase 8000 + OpenLLM 8001） | models 200 + stream routing 事件 |
| TT-143-011 | FR-143-01/02 | TD-143-01/02 | 双系统健康 + 认证注入 | Python 实测 | OpenLLM healthy + Bearer sk-openllm- 注入 |

## 3. 回归测试

| TT-ID | 范围 | 命令 | 预期 |
|-------|------|------|------|
| TT-143-020 | 后端全量 | `python -m pytest tests`（忽略 s3_real） | 250 passed（231 既有 + 19 新增） |
| TT-143-021 | 前端全量 | `npx vitest run` | 35 passed（Step 3 已验证，本版本无前端增量改动） |
| TT-143-022 | 静态质量 | `python -m ruff check openbase tests` | All checks passed |

## 4. 覆盖率测试

| TT-ID | 范围 | 命令 | 结果 |
|-------|------|------|------|
| TT-143-030 | llm_proxy 新代码行覆盖率 | `python -m pytest tests/test_llm_proxy.py --cov=openbase.modules.llm_proxy` | 84%（≥80% 门禁通过） |

## 5. 合规/安全快检

| TT-ID | 检查项 | 方式 | 结果 |
|-------|--------|------|------|
| TT-143-040 | 密钥不落代码/前端 | Grep（sk-openllm-） | 无（仅 .env，gitignore 排除） |
| TT-143-041 | 日志不记录 Authorization | Grep（llm_proxy 代码） | 无 print/无密钥日志 |
| TT-143-042 | 鉴权覆盖 | 代码审查（12 端点全 get_current_user） | 全部 401 门禁 |

## 6. UAT 验收（T4）

| UAT-ID | 业务流 | 步骤（API 序列） | 预期 | 结果 |
|--------|--------|------------------|------|:---:|
| UAT-143-01 | 登录→模型列表 | login → GET llm-proxy/models | 200 + 11 真实模型 | ✅ |
| UAT-143-02 | 模型详情 | GET llm-proxy/models/gpt-4 | 200 + gpt-4 | ✅ |
| UAT-143-03 | 对话发起（SSE） | POST llm-proxy/chat/stream | 200 + routing 事件流 | ✅ |
| UAT-143-04 | 前端页面（组件级） | vitest module-pages（模型/对话页） | 35/35 通过（写操作禁用提示/真实数据加载） | ✅ |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | AT-OpenBase-Dev | 初始创建：API 9 类 + 集成 2 + 回归 3 + 覆盖率 1 + 合规 3 + UAT 4 |
