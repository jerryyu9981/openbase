# D3 验证证据 — DPS 服务本机启动实测（2026-09-29）

| 项目 | 内容 |
|------|------|
| 证据类型 | 环境验证（D3 关闭依据） |
| 关联 | v1.4.10 设计入场检查记录 §4.4；用户澄清「OpenBase 本身就可以修改和启动 AI 基础组件任何一个系统，包括 DPS」 |
| 执行人 | AA-OpenBase-Dev / DO-OpenBase-Dev |
| 执行日期 | 2026-09-29 |
| 结论 | ✅ **D3 已验证并关闭** —— DPS 服务在本机可成功启动，健康检查通过，鉴权链 fail-closed 行为符合契约 |

---

## 1. 启动方式（实测，含一次失败纠正）

| 尝试 | 命令 | 结果 |
|:----:|------|------|
| ① 仓根目录 | `cd DPS; python -m uvicorn src.main:app --port 8100` | ❌ `ModuleNotFoundError: No module named 'config'` —— `src/main.py` 使用**隐式导入**（`from config import settings`），需 `src` 在 `sys.path` |
| ② **正确方式** | `cd DPS\src; python -m uvicorn main:app --host 127.0.0.1 --port 8100` | ✅ **启动成功** |

> **留痕价值**：该启动方式差异在 v1.4.10 联调（P2／P3）时会直接遇到，故在此固化，避免重复排查。

---

## 2. 启动日志关键证据（原始输出摘录）

```json
{"logger": "database", "message": "数据库初始化 (v2.1.0): backend=postgresql"}
{"logger": "engines.query_engine", "message": "查询引擎初始化完成 (v2.2.0)"}
{"logger": "engines.storage_engine", "message": "存储引擎初始化完成"}
{"logger": "engines.version_manager", "message": "版本管理器初始化完成 retention_days=90"}
{"logger": "engines.ai_engine", "message": "AI 引擎初始化完成 (v2.1.0): model_url=http://localhost:8080/v1"}
{"logger": "engines.tag_engine", "message": "标签引擎初始化完成 (v2.2.0)"}
{"logger": "engines.report_engine", "message": "报表引擎初始化完成 (v2.2.0)"}
{"logger": "engines.batch_engine", "message": "批量操作引擎初始化完成 (v2.2.0)"}
{"logger": "engines.stream_engine", "message": "流处理引擎初始化完成 (v2.1.0)"}
{"logger": "rest_api.routes", "message": "路由注册完成: /api/v2, /api/v1 (兼容), /health"}
{"logger": "main", "message": "DPS v2.11.1 启动中..."}
{"logger": "engines.health_check_engine", "message": "健康检查: 启动完成标记已设置"}
```

**观察**：① 实际运行版本为 **DPS v2.11.1**（高于契约文档标题的 v2.11.0，该仓已有 `Release-Note-v2.11.1.md`）；② 后端为 **PostgreSQL**（非 `dps.db` 的 SQLite 回退）；③ 日志为**结构化 JSON**（与 OpenLLM 侧 TD-035 问题形成对照）。

---

## 3. 运行态探测结果

| 探测 | 请求 | 结果 |
|------|------|------|
| 健康检查 | `GET /health` | ✅ `{"status":"healthy","app":"DPS","version":"2.11.1"}` |
| **无身份头** | `GET /openapi.json` | **401** `{"code":401,"message":"缺少组织或租户标识","data":null}` ⇒ **验证契约 §1「缺失标识 → 401」** |
| **带身份头** | `GET /openapi.json`（`X-Org-ID: org-1`／`X-Tenant-ID: tenant-1`／`X-User-ID: u-verify`／`X-User-Role: admin`） | **403**（已禁止）⇒ **身份/租户被接受、权限门拒绝** ⇒ **验证 fail-closed 鉴权链逐级生效** |

> **双向验证结论**：401（缺标识）＋ 403（有标识但权限不足）组合，证明 **`IdentityGate → TenantGate → PermissionGate` 链路按契约 fail-closed 工作**。

---

## 4. 端点实现存在性（代码级交叉印证）

| 端点 | 代码证据 |
|------|----------|
| 5 预检 | `src/engines/template_preflight.py`；路由 `rest_api/routes/routes_profiles.py::api_template_preflight`；用例 `tests/test_template_preflight_v2_11.py`（含 `test_package_preflight_matches_real_dry_run` **逐项一致**断言） |
| 4 回滚 | `tests/test_template_version_v2_11.py::test_rollback_restores_config_and_bumps_version`／`test_rollback_writes_audit_history` |
| 8 措施建议 | `tests/test_measure_mapping_v2_11.py`（标注「路由接线：`GET /portrait/measures/suggest`（只读，DT-015/016）」） |
| 其余端点 | 契约 §2 清单 10 项 ＋ 该仓 v2.11 测试集覆盖 |

---

## 5. 已知限制（如实登记）

| # | 限制 | 影响 | 计划 |
|:-:|------|------|------|
| 1 | **有效业务用户/权限**未确认（`u-verify` 无权限）⇒ **未完成 10 端点的运行态清单枚举** | 不影响 D3 关闭（服务可启动已证）；影响联调时的账号准备 | P2／P3 联调前准备具备 `portrait_template:*`／`annotation_template:*` 的测试账号 |
| 2 | 服务已**停止**（验证完成后释放终端） | — | 联调时按 §1 方式②重启 |

---

## 6. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-09-29 | AA-OpenBase-Dev | 初始创建：**D3 实测验证** —— 启动方式 2 种（含失败纠正与正确命令固化）；**启动日志证据 12 行**（含版本 v2.11.1、PostgreSQL 后端、结构化 JSON）；**运行态探测 3 项**（`/health` healthy ＋ 无头 **401** ＋ 带头 **403** ⇒ 双向验证 fail-closed 鉴权链）；**端点实现存在性代码级印证 4 项**；**已知限制 2 项如实登记**。结论：**D3 已验证并关闭**。 |
