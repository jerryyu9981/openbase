# OpenBase Phase 迭代计划 - v1.1.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.1.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 存放 | doc/version/releases/v1.1.0/ |

---

## 1. Phase 总览

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
回灌准备      OpenLLM       OpenRAG+       DPS +        PyPI + Pro
+工具链        回灌          OpenMemory     告警/SSE      部署 + 验证
1 周          1 周          回灌 1 周       1 周          1 周
```

**总周期**：约 5 周（2026-10-13 ~ 2026-11-09，弹性 ±1 周）

## 2. Phase 明细

### Phase 1 — 回灌准备 + 工具链（约 1 周）

| 项 | 内容 |
|----|------|
| Backlog | BL-101（部分）、BL-106、BL-107 |
| 交付物 | 四系统接入指南、兼容层框架、回滚预案、AI 规则（.cursor/rules + AGENTS.md）、模块独立版本机制 |
| 验收重点 | 接入指南可执行；AI 规则可生成 OpenBase 规范代码；模块 version 独立可查 |

### Phase 2 — OpenLLM 回灌（约 1 周）

| 项 | 内容 |
|----|------|
| Backlog | BL-102 |
| 交付物 | OpenLLM 灰度接入（Dev：audit/otel 替换）+ 回灌验证记录 |
| 验收重点 | OpenLLM 单测 + 集成测试通过；对外接口不变（diff=0） |

### Phase 3 — OpenRAG + OpenMemory 回灌（约 1 周）

| 项 | 内容 |
|----|------|
| Backlog | BL-103、BL-104 |
| 交付物 | OpenRAG 接入（config/mcp）+ OpenMemory 接入（tenant/observability）（Test：auth/tenant/config/mcp 替换） |
| 验收重点 | E2E + 多租户回归；数据同步验证 |

### Phase 4 — DPS 回灌 + 运维完善（约 1 周）

| 项 | 内容 |
|----|------|
| Backlog | BL-105、BL-108、BL-109 |
| 交付物 | DPS 接入（errors 对齐 + 全量）+ OTLP 告警通道 + 多实例 SSE 订阅 |
| 验收重点 | 四系统全量接入 Pro 灰度准备；告警触发可达；SSE 跨实例推送 |

### Phase 5 — PyPI + Pro 部署 + 验证（约 1 周）

| 项 | 内容 |
|----|------|
| Backlog | BL-110、BL-111、BL-112 |
| 交付物 | PyPI 发布、Pro 蓝绿/金丝雀部署、灰度三阶段验证、上线检查、发布复盘 |
| 验收重点 | pip install openbase 成功；Pro 上线检查通过；灰度切换 3/3 阶段验证通过 |

## 3. 里程碑

| 里程碑 | Phase | 日期（约） | 验证 |
|--------|-------|-----------|------|
| M1 回灌就绪 | Phase 1 | 第 1 周末 | 指南/规则/模块版本可用 |
| M2 OpenLLM 接入 | Phase 2 | 第 2 周末 | OpenLLM 回归通过 |
| M3 三系统接入 | Phase 3 | 第 3 周末 | OpenRAG/OpenMemory 回归通过 |
| M4 全量接入 | Phase 4 | 第 4 周末 | 四系统接入 + 运维完善 |
| M5 发布完成 | Phase 5 | 第 5 周末 | PyPI + Pro + 灰度验证通过 |

## 4. 依赖与资源

| 项 | 说明 |
|----|------|
| 人力 | PM/RA/AA/AD/AU/DO（DevFlow 角色矩阵） |
| 外部依赖 | 四系统 Dev 环境可启动；OTLP Collector/Langfuse（预研确认）；PyPI 账号 |
| 风险 | R-101（回灌破坏）→ 灰度 + 回滚；R-103（OTLP 未就绪）→ 预研/推迟 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | PM-OpenBase-Dev | 初始创建：5 Phase 拆分（回灌准备→OpenLLM→OpenRAG/OpenMemory→DPS/运维→PyPI/Pro），里程碑与资源风险明确 |
