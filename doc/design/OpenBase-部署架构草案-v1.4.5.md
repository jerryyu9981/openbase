# OpenBase 部署架构草案 - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | SA-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/design/ |

---

## 1. 部署拓扑

```
OpenBase 前端（Vue3）:5173 dev / dist 静态
  → OpenBase 后端（FastAPI）:8000
      ├─ llm-proxy → OpenLLM :8001
      ├─ rag-proxy → OpenRAG :8010
      └─ dps-proxy → DPS :8030（v1.4.5 新增）
DPS 依赖：PostgreSQL（或 SQLite 降级）/ Redis（可选）/ AI 模型服务（可选，OQ-145-2）
```

## 2. 端口规划

| 服务 | 端口 | 环境变量 | 说明 |
|------|:---:|----------|------|
| OpenBase | 8000 | - | 既有 |
| OpenLLM | 8001 | PORT | 既有（v1.4.3） |
| OpenRAG | 8010 | OPENRAG_API_PORT | 既有（v1.4.4） |
| DPS | 8030 | **API_PORT** | v1.4.5 新增（注意变量名非 PORT） |
| 前端 dev | 5173 | - | 既有 |

## 3. DPS 启动配置

```powershell
cd 'D:\Trae CN\myproject\Dev\DPS'
$env:API_PORT = '8030'          # 覆盖默认 8000（与 OpenBase 错开）
$env:SQLITE_FALLBACK = 'true'   # 数据库降级（无 PG 时）
# 入口：src/rest_api/app.py，需 PYTHONPATH=src
& '.\.venv\python.exe' -m uvicorn rest_api.app:app --host 127.0.0.1 --port 8030
# 依赖确认：/health/liveness 健康检查；组织/租户种子数据（身份头校验前提）
```

## 4. 部署步骤

| 步骤 | 操作 |
|------|------|
| 1 | 启动 DPS（API_PORT=8030）+ 种子组织/租户数据 |
| 2 | OpenBase settings 配置 dps_upstream_base=http://127.0.0.1:8030 |
| 3 | 启动 OpenBase 8000（demo_app 含 dps_proxy） |
| 4 | 启动前端 5173（或 build 静态部署） |
| 5 | 上线验证（health/画像列表/详情） |

## 5. 回滚策略

| 项 | 内容 |
|----|------|
| 代码回滚 | git tag v1.4.4 一键回滚（无 DB 变更） |
| 配置回滚 | 移除 dps_* 配置 + disable dps_proxy 模块 |
| 数据回滚 | 无（DPS 数据为上游系统，不落 OpenBase 库） |

## 6. 环境差异

| 环境 | 差异 |
|------|------|
| Dev | SQLite 降级 + 沙箱写限制（联调用临时库） |
| Test/Pro | PostgreSQL + Redis + 组织/租户正式种子；Qdrant/AI 模型服务按需 |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | SA-OpenBase-Dev | 初始创建：部署拓扑（DPS 8030）/端口规划/启动配置/部署步骤/回滚策略/环境差异 |
