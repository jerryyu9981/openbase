# OpenBase 需求来源与干系人 - v1.1.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.1.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | RA-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 存放 | doc/requirements/ |

---

## 1. 需求来源清单

| RT-ID | 需求 | 来源通道 | 来源说明 | 负责人 |
|-------|------|---------|---------|--------|
| RT-101 | 回灌准备 | 历史技术债 | TD-001（抽取破坏稳定性） | AD-OpenBase-Dev |
| RT-102~105 | 四系统回灌 | 历史技术债 + 业务输入 | TD-001 + 路线图 S3 回灌 | AD-OpenBase-Dev |
| RT-106 | AI 规则 | 历史技术债 | TD-004（团队学习成本） | AD-OpenBase-Dev |
| RT-107 | 模块独立版本 | 历史技术债 | TD-002（模块强耦合） | AA-OpenBase-Dev |
| RT-108 | OTLP 告警 | 上版本遗留 | OPS-001（v1.0.0 发布遗留） | OE-OpenBase-Dev |
| RT-109 | 多实例 SSE | 上版本遗留 | OPS-003 | AD-OpenBase-Dev |
| RT-110 | PyPI 发布 | 业务输入 | 路线图 S4 延续 | DO-OpenBase-Dev |
| RT-111 | Pro 部署 | 上版本遗留 | OPS-002 | DO-OpenBase-Dev |
| RT-112 | 灰度验证 | 业务输入 | 路线图灰度切换三阶段 | AT-OpenBase-Test |

## 2. 干系人与用户角色

| 角色 | 职责 | 相关需求 | 审批关系 |
|------|------|---------|---------|
| 四系统开发团队（OpenLLM/OpenRAG/OpenMemory/DPS） | 回灌接入执行 | RT-101~105 | 上报 PM |
| PM-OpenBase-Dev | 版本统筹、评审批准 | 全部 | 版本门禁审批人 |
| RA-OpenBase-Dev | 需求分析与基线 | 全部 | - |
| AA/AD-OpenBase-Dev | 架构与编码实现 | RT-101~109 | - |
| AT-OpenBase-Test | 测试验收 | RT-112 + 全部 | - |
| DO/OE-OpenBase-Dev | 部署与运维 | RT-108/110/111 | - |
| AU-OpenBase-Dev | 阶段审计 | 全部 | 审计门禁 |

## 3. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | RA-OpenBase-Dev | 初始创建：17 条需求来源归档 + 干系人角色表 |
