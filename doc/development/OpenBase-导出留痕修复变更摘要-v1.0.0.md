# OpenBase 导出留痕修复变更摘要

| 项 | 内容 |
|---|---|
| 文档编号 | OB-CHANGE-EXPORT-AUDIT |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 关联缺陷 | D6：dps-proxy 导出未写业务留痕（E2E 走查发现） |
| 影响组件 | OpenBase 后端（dps-proxy、logs）、测试、运维脚本 |
| 提交 | `a6a7a70`（origin / backup / github 已推送） |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制：背景、改动清单、契约、验证结果、兼容与回滚 | AI 编码代理 |

## 1. 背景与问题

画像/标注 CSV 导出由 OpenBase 代理生成：`_export_response` 分页调用 DPS 列表接口后在本地拼装 CSV。DPS 侧只能观察到 `READ(list)`，不存在 `EXPORT` 动作。

OpenBase 已有业务留痕函数 `record_export_audit`（写入 `audit_logs(action="log.export")` 并接入链式哈希），但仅被 OpenBase 自有日志导出路由调用，dps-proxy 的导出路由未接线。结果是：**导出行为没有业务留痕**（谁、按什么条件、导出了多少行均无法追溯）。

## 2. 变更范围

| 文件 | 变更 |
|---|---|
| `openbase/modules/dps_proxy/__init__.py` | 导出前补写 `log.export`；新增 `_export_actor`；`_fetch_upstream_json` 改用 `client.request` 便于测试；删除重复注册的 `/audit/logs` 路由 |
| `openbase/modules/logs/service.py` | `record_export_audit` 新增可选 `extra` 参数，合并进 `detail` |
| `tests/test_dps_proxy_wave_c.py` | 新增导出留痕用例；修正 1 处无占位符 f-string |
| `scripts/verify_export_audit.py` | 新增真机验证脚本（10 项检查 + 证据落盘 + 失败退出码） |
| `doc/test/...走查报告`、`doc/release/...Runbook`、计划、核对单 | 同步 D6 结论、冒烟 S11、版本与证据 |

## 3. 实现要点

| 项 | 实现 |
|---|---|
| 触发点 | `_export_response` 预检拿到 `total` 后、返回 `StreamingResponse` 前 |
| 动作码 | `log.export` |
| 来源 | `dps_proxy.portraits.export` / `dps_proxy.annotations.export` |
| 操作者 | JWT `sub`，缺失回退 `user_id` / `username` |
| 过滤条件 | 原样传入，由 `mask_sensitive` 脱敏后落库 |
| 行数 | `row_count = min(total, 10000)`，`extra` 同时记录 `total`、`exported_rows`、`truncated` |
| 链路 | `request.state.request_id`（缺失时生成 `req-<uuid12>`），与响应头一致 |
| 失败语义 | 留痕失败仅 WARN，**不阻断导出**（ADR-146-04） |

落库位置：`openbase` schema 的 `audit_logs`，`detail` 示例：

```json
{
  "actor": "admin",
  "source": "dps_proxy.portraits.export",
  "filters": {},
  "row_count": 18,
  "format": "csv",
  "total": 18,
  "exported_rows": 18,
  "truncated": false
}
```

## 4. 接口与兼容性

| 项 | 结论 |
|---|---|
| 对外 API | 无变化（导出路径、响应头、CSV 内容不变） |
| 函数签名 | `record_export_audit` 仅新增可选参数，既有调用不受影响 |
| DPS 侧 | 无改动；DPS `audit_logs` 仍无 `EXPORT`，属架构分工（CSV 非 DPS 生成） |
| 性能 | 每次导出多 1 次审计写入；行数统计复用已有预检请求，不额外调用 DPS |
| 数据安全 | `filters` 脱敏；日志不记录令牌与敏感值 |

## 5. 验证结果

| 项 | 结果 |
|---|---|
| 单元/接口测试 | `test_dps_proxy.py`、`test_dps_proxy_wave_c.py`（含新增留痕用例）、`test_logs_endpoints_api.py` 全部通过 |
| 静态检查 | 变更文件 flake8 0 error（E203/W503 除外） |
| 真机验证 | `scripts/verify_export_audit.py` **10/10 PASS**：request_id 对齐、字段完整、链校验 `ok=True` |
| 证据 | `doc/test/evidence/portrait-waves/export-audit/export-audit-20261123-214958.json` |

## 6. 回滚方案

1. 回退提交 `a6a7a70`（或仅回退 `dps_proxy/__init__.py` 中的留痕调用）；
2. 无 DDL、无数据迁移，回滚不影响导出功能；
3. 已产生的 `log.export` 记录保留，可按 `source`/时间清理，清理需双人复核；
4. 回滚后导出恢复为"仅 DPS READ 记录"状态，需在验收单标注该已知缺口。

## 7. 风险与后续

| 项 | 说明 |
|---|---|
| 审计写库故障 | 已降级为 WARN，不阻断导出；若合规要求 fail-closed，可切换 `OPENBASE_AUDIT_DB_PERSIST=0` 策略 |
| 截断场景 | `total > 10000` 时 `truncated=true`，导出行数与总量均可追溯 |
| 统一台账诉求 | 若要求"只查 DPS 一张表"，需另做 DPS 内部审计写入端点（方案 B Option 2），当前未实施 |
| 保留期 | 遵循 OpenBase 审计保留策略，与 DPS `DPS_AUDIT_RETENTION_DAYS` 独立 |

## 8. 关联文档

| 文档 | 位置 |
|---|---|
| 全栈 E2E 走查报告 v1.1.0 | `doc/test/OpenBase-画像三波次全栈端到端走查报告-v1.0.0.md` |
| 发布与回滚 Runbook（冒烟 S11） | `doc/release/OpenBase-画像优化升级三波次发布与回滚Runbook-v1.0.0.md` |
| 波次 C 验收核对单 v1.0.6 | `doc/specs/wave-c/checklist.md` |
| 验证脚本 | `scripts/verify_export_audit.py` |
