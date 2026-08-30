# OpenBase 需求基线及设计移交说明 - v1.4.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | RA-OpenBase-Dev |
| 创建日期 | 2026-08-28 |
| 存放 | doc/requirements/ |

---

## 1. 需求基线（1.7）

| 项 | 内容 |
|----|------|
| 基线 ID | v1.4.0-RB1 |
| 基线版本 | 开发需求文档 v1.0.0 + 需求追溯矩阵 v1.0.0 |
| 基线范围 | 26 项功能需求（R-340~363 + R-365~366）+ 非功能/数据/权限/UI/接口 5 类 |
| 不包含 | R-364（生态工具链，VC-007 挂起）；网关阶段二（Nacos/DSL/GraphQL）；四系统后端新功能 |
| 变更规则 | 进入 Step 2 后需求变更必须记录范围、影响、审批（PM）和下游同步结果；新增需求先回写候选需求池或触发版本范围变更 |

## 2. 设计移交材料（1.10）

| # | 移交材料 | 文件 | 状态 |
|---|---------|------|:---:|
| 1 | 开发需求文档 | doc/requirements/OpenBase-开发需求文档-v1.4.0.md | ✅ |
| 2 | 需求追溯矩阵 | doc/requirements/OpenBase-需求追溯矩阵-v1.4.0.md | ✅ |
| 3 | 需求评审记录 | doc/requirements/OpenBase-需求评审记录-v1.4.0.md | ✅ |
| 4 | 需求来源与干系人 | doc/requirements/OpenBase-需求来源与干系人-v1.4.0.md | ✅ |
| 5 | 需求评估报告 | doc/audit/assessment/OpenBase-需求评估报告-v1.4.0.md | ✅ |
| 6 | 阶段审计报告 Stage1 | doc/audit/review/OpenBase-阶段审计报告-Stage1-v1.4.0.md | ✅ |

## 3. 移交要点（给 Step 2 设计）

| 维度 | 内容 |
|------|------|
| 目标优先级 | P1 24 项（RT-401~423 + RT-425~426）+ P2 1 项（RT-424）；P2 按"可用"标准验收 |
| 网关设计输入 | DiscoveryProvider 适配器接口、ServiceInstance 数据模型、`/api/v1/services` 与 `/api/v1/gateway/aggregate` 接口契约、scheduler/config 复用（见开发需求文档 RT-425~426 + 网关技术方案） |
| 前端设计输入 | 26 项页面（统一前端底座 + 网关管理页），交互沿用 v1.3.0 约定（列表/表单/二次确认/状态反馈） |
| 对接约束 | 四系统功能经代理对接既有 API；契约以独立前端为基线，缺口登记 v1.4.x 补 |
| 质量要求 | 测试 100%、覆盖率 ≥80%、Lint 0；网关向后兼容（静态表兜底） |
| 风险提示 | R-401（后端能力未开放，P1）、R-404（网关探测误判，P1）、R-405/R-406（P2）——详见单版本规划风险清单 |

## 4. 需求阶段产出物存在性验证

| # | 产出文件 | 实际存在 |
|---|---------|:---:|
| 1 | doc/requirements/OpenBase-开发需求文档-v1.4.0.md | ✅ |
| 2 | doc/requirements/OpenBase-需求来源与干系人-v1.4.0.md | ✅ |
| 3 | doc/requirements/OpenBase-需求追溯矩阵-v1.4.0.md | ✅ |
| 4 | doc/requirements/OpenBase-需求评审记录-v1.4.0.md | ✅ |
| 5 | doc/audit/assessment/OpenBase-需求评估报告-v1.4.0.md | ✅ |
| 6 | doc/audit/review/OpenBase-阶段审计报告-Stage1-v1.4.0.md | ✅ |

**产出物通过率：6/6 = 100%**（评估报告与 Stage1 审计报告由审计步骤产出后核对）

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-28 | RA-OpenBase-Dev | 初始创建：需求基线 v1.4.0-RB1 + 设计移交材料清单（6 项）+ 移交要点 + 产出物存在性验证 |