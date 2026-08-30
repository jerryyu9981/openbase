# OpenBase 需求基线及设计移交说明 - v1.4.3

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.3 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | RA-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/requirements/ |

---

## 1. 需求基线（1.7）

| 项 | 内容 |
|----|------|
| 基线 ID | v1.4.3-RB1 |
| 基线版本 | 开发需求文档 v1.0.0 + 需求追溯矩阵 v1.0.0 |
| 基线范围 | 9 项功能需求（FR-143-01~09，对应 R-379 拆解 BL-143-01~06 + 还债 BL-143-07）+ 非功能/数据/权限/UI/接口 5 类需求 |
| 不包含 | OpenRAG/DPS 对接（v1.4.4/v1.4.5）；四系统统一集成测试（v1.5）；R-376/R-377（v1.5）；OpenLLM 功能补全（R-301~R-312 等历史条目）；JWT 共享签发方案落地（P2 评估） |
| 变更规则 | 进入 Step 2 后需求变更必须记录范围、影响、审批（PM）和下游同步结果；新增需求先回写候选需求池或触发版本范围变更记录（VC-XXX） |

## 2. 设计移交材料（1.10）

| # | 移交材料 | 文件 | 状态 |
|---|---------|------|:---:|
| 1 | 开发需求文档 | doc/requirements/OpenBase-开发需求文档-v1.4.3.md | ✅ |
| 2 | 需求追溯矩阵 | doc/requirements/OpenBase-需求追溯矩阵-v1.4.3.md | ✅ |
| 3 | 需求评审记录 | doc/requirements/OpenBase-需求评审记录-v1.4.3.md | ✅ |
| 4 | 需求来源与干系人 | doc/requirements/OpenBase-需求来源与干系人-v1.4.3.md | ✅ |
| 5 | 需求评估报告 | doc/audit/assessment/OpenBase-需求评估报告-v1.4.3.md | ✅ |
| 6 | 阶段审计报告 Stage1 | doc/audit/review/OpenBase-阶段审计报告-Stage1-v1.4.3.md | ✅（随本步骤产出） |

## 3. 移交要点（给 Step 2 设计）

| 维度 | 内容 |
|------|------|
| 目标优先级 | P1 8 项（FR-143-01~05、07、09）+ P2 1 项（FR-143-08）；P1 必须全部满足验收标准 |
| 对接设计输入 | OpenLLM v2.13.0 认证契约（JWT `/api/v1/auth/login` HS256/SECRET_KEY + API Key `sk-openllm-` 仅 Bearer）、统一网关 `/openllm/v1/*`（双通道鉴权、统一响应 {code,message,data}、错误码 1001/1003/1004/2001/5001）、SSE 事件 routing→chunk→done、会话 API `/api/v1/conversations`（JWT、标准 REST、Pydantic 直出） |
| 复用设计输入 | v1.4.2 memory_proxy.py 模式（认证注入/转发/响应适配三函数拆分、_forward/_forward_raw/_proxy_json/_proxy_multipart 复用骨架）；网关服务发现骨架（openllm 循环探测）已具备 |
| 配置设计输入 | settings 新增 llm_api_key / llm_upstream_base=http://127.0.0.1:8001 / llm_upstream_timeout（.env 可覆盖，对标 memory_* 配置） |
| 前端设计输入 | 模型管理页（Models.vue）/对话管理页（Conversations.vue）mock 替换真实 API（走 proxy）；沿用统一前端 Design Token 与 v1.4.2 记忆管理页交互模式（加载态/错误态/重试） |
| 质量要求 | 全量回归 ≥95%、覆盖率 ≥80%、Lint 0（ruff）；无新增 P0/P1 缺陷 |
| 风险提示 | 认证契约差异（P1，Phase 2 前置对齐）；8001 启动失败/依赖重（P2）；SSE 兼容（P2，降级非流式）；OpenLLM 侧占位（P2，任务书登记）；OQ-143-1（JWT 用户映射）、OQ-143-2（模型写操作能力）待联调闭环 |

## 4. 需求阶段产出物存在性验证（1.9b 变更一致性自检）

| # | 产出文件 | 实际存在 |
|---|---------|:---:|
| 1 | doc/requirements/OpenBase-开发需求文档-v1.4.3.md | ✅ |
| 2 | doc/requirements/OpenBase-需求来源与干系人-v1.4.3.md | ✅ |
| 3 | doc/requirements/OpenBase-需求追溯矩阵-v1.4.3.md | ✅ |
| 4 | doc/requirements/OpenBase-需求评审记录-v1.4.3.md | ✅ |
| 5 | doc/audit/assessment/OpenBase-需求评估报告-v1.4.3.md | ✅ |
| 6 | doc/audit/review/OpenBase-阶段审计报告-Stage1-v1.4.3.md | ✅ |

### 4.1 版本号一致性自检

| 文档 | 文件头版本 | 修订历史底部版本 | 一致 |
|------|:---:|:---:|:---:|
| 开发需求文档 | v1.0.0 | v1.0.0 | ✅ |
| 需求来源与干系人 | v1.0.0 | v1.0.0 | ✅ |
| 需求追溯矩阵 | v1.0.0 | v1.0.0 | ✅ |
| 需求评审记录 | v1.0.0 | v1.0.0 | ✅ |
| 需求评估报告 | v1.0.0 | v1.0.0 | ✅ |
| 阶段审计报告 Stage1 | v1.0.0 | v1.0.0 | ✅ |

### 4.2 命名与路径规范自检

| 检查项 | 结果 | 说明 |
|--------|:---:|------|
| 文件名格式 {项目名}-{文档类型}-v{版本号}.md | ✅ | 全部匹配（OpenBase-XXX-v1.4.3.md） |
| 需求文档存放 doc/requirements/ | ✅ | 5 份（开发需求/来源干系人/追溯矩阵/评审记录/基线移交） |
| 审计文档存放 doc/audit/assessment/ | ✅ | 需求评估报告 1 份 |
| 阶段审计报告存放 doc/audit/review/ | ✅ | Stage1 报告 1 份 |

### 4.3 追溯编号自检

| 检查项 | 结果 | 说明 |
|--------|:---:|------|
| FR 编号数 = 需求总数 | ✅ | 9（FR-143-01~09）= 开发需求文档 §3 功能需求 3.1~3.7 拆解 9 项 |
| BL 覆盖 | ✅ | BL-143-01~07 全映射（7/7 = 100%） |
| AC 覆盖 | ✅ | AC-143-01~07 全对应，无遗漏 |

**产出物通过率：6/6 = 100%**（评估报告与 Stage1 审计报告由审计步骤产出后核对）

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | RA-OpenBase-Dev | 初始创建：需求基线 v1.4.3-RB1 + 设计移交材料清单（6 项）+ 移交要点 + 产出物存在性验证与 1.9b 自检记录 |
