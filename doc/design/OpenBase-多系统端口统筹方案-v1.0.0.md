# OpenBase 多系统端口统筹方案 - v1.0.0

| 项目   | 内容                                                                |
| ---- | ----------------------------------------------------------------- |
| 项目名称 | OpenBase（开放底座）                                                    |
| 文档版本 | v1.0.0                                                            |
| 状态   | \[Approved]                                                       |
| 作者   | OP-OpenBase-Dev（统筹）                                               |
| 创建日期 | 2026-09-01                                                        |
| 存放   | doc/design/                                                       |
| 适用范围 | OpenLLM / OpenRAG / OpenMemory / DPS / OpenBase / 统一前端 全系统端口与对接配置 |

***

## 1. 背景与目标

对接线（v1.4.2 OpenMemory → v1.4.3 OpenLLM → v1.4.4 OpenRAG → v1.4.5 DPS）已全部落地，五个系统 + 统一前端需要**统一端口分配，避免占用冲突**。

**核心问题**：五个系统的源码默认端口全部为 **8000**（OpenBase 固定 8000），任一系统不覆盖端口直接启动即与 OpenBase 冲突；OpenLLM 主服务与 edgerouter 默认同为 8001，存在内部冲突隐患。本方案统一端口分配 + 启动命令模板，形成单一事实源。

## 2. 端口分配总览（80xx 分段制）

|        端口       | 归属                     | 默认（源码） | 覆盖方式                    | OpenBase 对接配置               |      状态      |
| :-------------: | ---------------------- | :----: | ----------------------- | --------------------------- | :----------: |
|     **8000**    | OpenBase 后端            |  8000  | -（固定）                   | -                           |     ✅ 已定     |
|     **8001**    | OpenLLM 主服务            |  8000  | `PORT=8001`             | `llm_upstream_base=8001`    |     ✅ 已定     |
|       8002      | OpenLLM edgerouter     |  8001  | `EDGE_ROUTER_PORT=8002` | -（未接入）                      | ⚠️ 冲突源（见 §4） |
|     **8010**    | OpenRAG                |  8000  | `OPENRAG_API_PORT=8010` | `rag_upstream_base=8010`    |     ✅ 已定     |
|     **8020**    | OpenMemory             |  8000  | `--port 8020`           | `memory_upstream_base=8020` |     ✅ 已定     |
|     **8030**    | DPS                    |  8000  | `API_PORT=8030`         | `dps_upstream_base=8030`    |     ✅ 已定     |
|       8013      | DPS MCP                |  8013  | -                       | 不接入 OpenBase                |     ✅ 保留     |
|     **5173**    | 统一前端                   |  5173  | -（proxy → 8000）         | -                           |     ✅ 已定     |
|       5432      | PostgreSQL             |  5432  | -                       | 公共基础设施（本机运行中）               |       ✅      |
|       6333      | Qdrant                 |  6333  | -                       | 公共基础设施（192.168.0.151）       |       ✅      |
|       6380      | Redis                  |  6380  | -                       | 公共基础设施（192.168.0.151）       |       ✅      |
| 8002\~8004/8090 | OpenLLM mock\_services |    -   | 测试桩专用                   | 仅测试环境                       |     ⚠️ 保留    |

## 3. 启动命令模板（统一标准）

### 3.1 OpenBase（8000）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenBase'
python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000
```

### 3.2 OpenLLM 主服务（8001）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenLLM\backend'
$env:PORT = '8001'   # 覆盖默认 8000
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

> OpenLLM 对接依赖：OpenBase 侧 `llm_upstream_base=http://127.0.0.1:8001` + `llm_api_key`（已配置）。

### 3.3 OpenRAG（8010）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'
$env:OPENRAG_API_PORT = '8010'   # 覆盖默认 8000
python -m uvicorn main:app --host 127.0.0.1 --port 8010
```

> 依赖：PostgreSQL（本机 5432）/ Qdrant（6333 远端，可选，任务书 M6 跟踪）。

### 3.4 OpenMemory（8020）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenMemory'
# complete 模式：Qdrant + PostgreSQL + Redis + Neo4j 真实后端（192.168.0.151 共享基础设施）
python scripts\start_openmemory.py
```

> OpenBase 侧 `memory_upstream_base=http://127.0.0.1:8020` + `memory_api_key`（已配置）。
> 注意：首次启动约需 2~4 分钟（torch 冷加载 + faster-whisper/CLIP 模型预载），健康探针 `/health`（含 readiness/liveness）已全部放行（RBAC/Gateway/API-Key 三层豁免修复）。

### 3.5 DPS（8030）

```powershell
cd 'D:\Trae CN\myproject\Dev\DPS'
$env:API_PORT = '8030'   # 覆盖默认 8000
$env:SQLITE_FALLBACK = 'true'   # 无 PG 时降级
python -m uvicorn rest_api.app:app --app-dir src --host 127.0.0.1 --port 8030
```

> 注意：DPS 启动受阻（`src/config.py` 无 settings 实例，`from config import settings` 导入失败）→ 登记任务书 M4，DPS 侧修复后按此命令启动。

### 3.6 统一前端（5173）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenBase\openbase-ui'
npm run dev   # vite 5173，proxy → http://127.0.0.1:8000
```

## 4. 冲突分析与处置

|  #  | 冲突点                                            | 分析                                                          | 处置                                                                                                 |
| :-: | ---------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
|  C1 | **五系统默认端口全为 8000**                             | OpenBase 固定 8000；其余四系统默认 8000，不覆盖即冲突                        | 已按 §2 统一覆盖（8001/8010/8020/8030），启动模板固化                                                             |
|  C2 | **OpenLLM 主服务 vs edgerouter 均默认 8001**         | OpenLLM 主服务 PORT=8001；edgerouter EDGE\_ROUTER\_PORT 默认 8001 | ① edgerouter 未启用：8001 归主服务（现状）；② edgerouter 启用：设 `EDGE_ROUTER_PORT=8002`；主服务与 edgerouter 不同时占用同一端口 |
|  C3 | DPS 与 OpenBase 同默认 8000                        | DPS API\_PORT 默认 8000                                       | `API_PORT=8030`（已定）                                                                                |
|  C4 | OpenLLM mock\_services 占用 8002\~8004/8010/8090 | 测试桩端口与正式端口可能重叠（8010 与 OpenRAG 规划冲突）                         | 仅测试环境启用 mock\_services；正式联调禁用（8010 归 OpenRAG）                                                      |
|  C5 | 公共基础设施端口                                       | 5432（本机 PG）/ 6333/6380（远端）                                  | 保持系统默认，不纳入应用端口段                                                                                    |

## 5. 端口占用检查命令（部署前例行）

```powershell
# 部署前检查：确认目标端口空闲
$ports = 8000,8001,8010,8020,8030,5173
foreach ($p in $ports) {
  $r = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if ($r) { "端口 $p 被占用（PID $($r[0].OwningProcess)）— 启动前必须释放" }
  else { "端口 $p 空闲 ✅" }
}
```

## 6. OpenBase settings 对接配置对照（单一事实源）

| 配置                                   | 值                               | 对应系统              |
| ------------------------------------ | ------------------------------- | ----------------- |
| memory\_upstream\_base               | <http://127.0.0.1:8020>         | OpenMemory        |
| memory\_api\_key                     | openbase-gw-key-20260830        | OpenMemory 双层认证   |
| llm\_upstream\_base                  | <http://127.0.0.1:8001>         | OpenLLM           |
| llm\_api\_key                        | sk-openllm-openbase-gateway-key | OpenLLM Bearer 注入 |
| rag\_upstream\_base                  | <http://127.0.0.1:8010>         | OpenRAG（无认证注入）    |
| dps\_upstream\_base                  | <http://127.0.0.1:8030>         | DPS（身份头注入）        |
| dps\_default\_org\_id/tenant\_id/map | （按环境配置）                         | DPS 四头兜底/映射       |

## 7. 建议后续动作

|  #  | 动作                                        | 类型   | 版本               |
| :-: | ----------------------------------------- | ---- | ---------------- |
|  1  | DPS 侧修复 config.settings（任务书 M4）后按 §3.5 启动 | 第三方  | 任务书              |
|  2  | OpenLLM edgerouter 启用时端口改为 8002（C2）       | 配置约定 | 文档同步             |
|  3  | 本方案作为部署/运维手册 §端口章节引用                      | 文档   | 已引用（运维手册 v1.4.5） |
|  4  | v1.5 四系统统一集成测试按本方案启动全部服务                  | 计划   | v1.5             |

## 8. 修订历史

| 版本     | 日期         | 修改人             | 摘要                                                                              |
| ------ | ---------- | --------------- | ------------------------------------------------------------------------------- |
| v1.0.2 | 2026-09-01 | OP-OpenBase-Dev | 纠正依赖可用性误判：四个外部组件（PG/Redis/Qdrant/Neo4j）真实驱动验证全部可用，OpenMemory 恢复 complete 模式（start_openmemory.py） |
| v1.0.1 | 2026-09-01 | OP-OpenBase-Dev | OpenMemory 运行方式修订：run_api.py（恒 503）→ run_lightweight.py（lightweight 模式），健康探针三层豁免说明 |
| v1.0.0 | 2026-09-01 | OP-OpenBase-Dev | 初始创建：五系统 + 前端端口统一分配（8000/8001/8010/8020/8030/5173）+ 启动模板 + 冲突分析（C1\~C5）+ 对接配置对照 |

