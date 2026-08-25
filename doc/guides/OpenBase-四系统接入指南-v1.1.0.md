# OpenBase 四系统接入指南 - v1.1.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.1.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 日期 | 2026-08-25 |
| 存放 | doc/guides/ |

---

## 1. 接入目标

四系统（OpenLLM / OpenRAG / OpenMemory / DPS）灰度迁移至 openbase 底座，旧实现冻结（Git 历史保留），对外接口与 MCP 工具清单不变。

## 2. 前置条件

| 项 | 要求 |
|----|------|
| openbase 版本 | v1.0.0+（pip install openbase 或源码安装） |
| Python | 3.10+ |
| 基础设施 | PG（192.168.0.151:5432）+ Redis（6380） |
| 兼容层 | `from openbase.compat import register_field_map, register_func_alias` |

## 3. 灰度接入步骤

### 3.1 准备阶段（Phase 1）

1. 安装 openbase：`pip install -e D:\Trae CN\myproject\Dev\OpenBase`
2. 注册兼容层：在各系统入口注册字段映射与函数别名
3. 确认 openbase /health 可达

### 3.2 替换阶段（按系统灰度）

| 系统 | 环境 | 替换模块 | 验证 |
|------|------|---------|------|
| OpenLLM | Dev | audit/otel | 单测 + 集成测试通过；对外接口 diff=0 |
| OpenRAG | Test | config/mcp | E2E 通过；三级配置行为一致 |
| OpenMemory | Test | tenant/observability | 多租户回归；数据同步校验 |
| DPS | Pro | errors 对齐 | 错误码格式一致；全量接入 |

### 3.3 验证阶段

- 接口对比：AI 服务接口与 MCP 工具清单 diff = 0
- 功能回归：各系统核心业务流程通过
- 监控：OTLP 指标正常、无错误率上升

## 4. 回滚预案

| 触发 | 动作 |
|------|------|
| 任一系统灰度验证失败 | `git revert` 对应 commit，旧实现从 Git 历史恢复 |
| 线上 P0 故障 | 紧急回滚（2 小时内补材料） |
| 数据异常 | openbase schema 幂等重建；各系统业务数据自有备份 |

## 5. 兼容层示例

```python
# OpenLLM 入口示例
from openbase.compat import register_field_map, register_func_alias

register_field_map("openllm", {"created_time": "created_at", "user_name": "display_name"})
register_func_alias("openllm", "audit_log_engine", openbase_audit_service.record)
```

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | AD-OpenBase-Dev | 初始创建：接入目标/前置/灰度步骤/回滚/兼容层示例 |
