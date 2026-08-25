# OpenBase

四系统（OpenLLM / OpenRAG / OpenMemory / DPS）及未来类似系统的统一基础设施公共底座框架。

## 快速开始

```bash
pip install openbase
```

```python
from openbase import init_app, settings

settings.enable_module("auth")
settings.enable_module("tenant")
settings.enable_module("audit")
settings.enable_module("config")

app = init_app(settings)
```

## 模块

| 模块 | 说明 | 启用 |
|------|------|------|
| auth | 鉴权认证（JWT/RBAC） | `enable_module("auth")` |
| tenant | 多租户隔离 | `enable_module("tenant")` |
| audit | 审计日志 + API 服务框架 | `enable_module("audit")` |
| observability | 可观测（OTel/Langfuse） | `enable_module("observability")` |
| config | 配置中心（版本回滚） | `enable_module("config")` |
| mcp | MCP 工具封装 | `enable_module("mcp")` |
| org | 组织架构 | `enable_module("org")` |
| dict | 数据字典 | `enable_module("dict")` |
| scheduler | 定时任务 | `enable_module("scheduler")` |
| storage | 统一文件存储 | `enable_module("storage")` |
| notify | 通知中心（SSE） | `enable_module("notify")` |

## 开发

```bash
pip install -e ".[dev]"
pytest
ruff check .
```
