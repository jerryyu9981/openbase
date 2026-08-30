# OpenBase 部署执行报告 - v1.4.2（M3 发布）

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.2 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | OPS-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/operation/ |

---

## 1. 部署范围

v1.4.2（四维身份管理 + OpenMemory 对接）双系统部署：

| 系统 | 端口 | 部署方式 | 依赖 |
|------|------|----------|------|
| OpenBase | 8000 | `uvicorn openbase.demo_app:app`（本地进程） | 共享基础设施 PG/Redis（192.168.0.151） |
| OpenMemory | 8020 | `scripts/start_openmemory.py`（本地进程，真实持久后端） | 共享基础设施 Qdrant/PG/Redis（192.168.0.151） |

## 2. 部署步骤与验证

### 2.1 OpenMemory（8020）

```bash
cd D:\Trae CN\myproject\Dev\OpenMemory
$env:PYTHONPATH = 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OPENMEMORY_AUTO_MIGRATE = 'false'
python scripts/start_openmemory.py
```

验证：

| 检查项 | 结果 |
|--------|:---:|
| `GET http://127.0.0.1:8020/health` | ✅ 200 healthy（vector/metadata/session） |
| `GET /docs`（免鉴权） | ✅ 200 |
| 无 X-API-Key 访问 /api/v1 | ✅ 401 |
| 有 Key 无 JWT | ✅ 401 |
| Qdrant 数据落盘（points_count） | ✅ 持久（重启后不变） |

### 2.2 OpenBase（8000）

```bash
cd D:\Trae CN\myproject\Dev\OpenBase
# 进程环境变量
$env:POSTGRES_URL = 'postgresql://nuct:nuct123456@192.168.0.151:5432/nuct'
$env:REDIS_URL = 'redis://:!Q1w2e3r4t5@192.168.0.151:6380/0'
$env:OPENBASE_JWT_SECRET = 'test-jwt-secret-for-v680'
python -m uvicorn openbase.demo_app:app --host 127.0.0.1 --port 8000
```

验证：

| 检查项 | 结果 |
|--------|:---:|
| `GET http://127.0.0.1:8000/health` | ✅ 200 ok |
| 登录 admin/admin123 签发 JWT（sub/org_id/role） | ✅ 200 |
| 租户/用户管理 API（Phase 1） | ✅ 200 |
| memory-proxy 全链路（remember/recall/detail/list/forget） | ✅ 全通过 |
| 未认证访问 401 拦截 | ✅ |

## 3. 上线验证（M3 里程碑）

| 里程碑验收 | 标准 | 结果 |
|------------|------|:---:|
| 全量回归 | ≥95% | ✅ 222/222（100%） |
| 覆盖率 | ≥80% | ✅ 87% |
| 无新增 P0/P1 | - | ✅ 无（遗留均为 P2） |
| Step 4 文档 | 测试报告齐备 | ✅ `OpenBase-测试报告-v1.4.2.md`（v1.2.0） |
| Step 5 文档 | 部署运维文档 | ✅ 本报告 |

## 4. 运维要点

| 项 | 说明 |
|----|------|
| OpenMemory 数据持久 | 由 `scripts/start_openmemory.py` 独占 8020（真实 Qdrant/PG/Redis）；环境守护曾以内存模式（run_lightweight）抢占 → 需确保守护恢复命令为持久脚本 |
| 密钥共享 | `OPENBASE_JWT_SECRET` = `OPENMEMORY_GATEWAY__JWT_SECRET` = `test-jwt-secret-for-v680`（生产轮换） |
| 网关 Key | `X-API-Key: openbase-gw-key-20260830`（OpenBase 持有，.env `OPENBASE_MEMORY_API_KEY` 可覆盖） |
| recall 缓存 | OpenMemory recall 结果缓存（Redis `om:result:*`，TTL 7200s）可能陈旧；数据新鲜度敏感场景清缓存或缩短 TTL |
| 回归执行 | `python scripts/run_regression.py [--cov]`（分组子进程隔离 + 崩溃重试） |

## 5. 回滚预案

| 场景 | 操作 |
|------|------|
| OpenBase 异常 | 停止 uvicorn 进程，回退至 v1.4.1 版本部署脚本 |
| OpenMemory 异常 | 停止 8020 进程，恢复内存模式（run_lightweight）兜底；数据不丢失（Qdrant/PG 持久） |
| 密钥泄露 | 更换 `OPENBASE_JWT_SECRET` 与 `OPENMEMORY_GATEWAY__JWT_SECRET`（双端同步） |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | OPS-OpenBase-Dev | 初始创建：v1.4.2 双系统部署执行与上线验证（M3 里程碑达成） |
