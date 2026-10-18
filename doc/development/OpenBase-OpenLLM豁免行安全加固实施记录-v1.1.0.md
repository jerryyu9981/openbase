# OpenBase-OpenLLM 豁免行安全加固实施记录-v1.1.0

| 项目 | 内容 |
|------|------|
| 记录名称 | OpenLLM 豁免行（A 直连健康/管理面）安全加固实施记录 |
| 记录编号 | OB-SEC-EXEMPT-IMPL-v1.1.0 |
| 版本 | **v1.1.0** |
| 状态 | **[Final]**（T1~T10 已实施并验证；遗留项见 §6） |
| 实施日期 | 2026-10-18 |
| 实施方 | OpenBase 架构组（设计/验收）+ OpenLLM 开发 |
| 设计依据 | 《OpenBase-OpenLLM 豁免行安全加固方案-v1.3.0》（设计基线 v1.1.0） |
| 评审依据 | 《OpenBase-OpenLLM 豁免行安全加固方案-评审记录-v1.1.0》 |
| 风险依据 | 《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.1.0》§5（R1~R8） |
| 代码仓 | OpenLLM `feature/s4-identity-channel-b`，提交 **`dd59291` + `cff0a32`**（v2.19.0） |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：T1~T10 实施结果、代码落点、测试数据、遗留项与回滚说明 |
| v1.1.0 | 2026-10-18 | OpenBase 架构组 | 补充提交 `cff0a32`（登记表读取 60s 进程内缓存）；同步方案 v1.3.0 引用 |

---

## 1. 实施范围

对应方案 H1~H8 / T1~T10，全部在 OpenLLM 仓落地。**新增开关默认值保持现行行为**，
收紧仅由 `ENV=production` 启动门禁强制；非生产环境行为不变。

## 2. 代码与配置落点

| 任务 | 内容 | 落点 |
|:----:|------|------|
| **T1** | 豁免登记表（单一事实源） | `config/exempt_endpoints.json`（5 条，ticket/approver/expires_at 齐备） |
| **T1** | 精确匹配 + 路径规范化 | `backend/app/security/exempt_policy.py`：`EXEMPT_ROUTES`、`is_exempt_path`、`is_suspicious_path` |
| **T2** | 启动断言（路由存在性/前缀碰撞/登记表一致） | `exempt_policy.assert_exempt_routes_registered`；`main.py` lifespan 调用 |
| **T3** | 文档/Schema 生产 fail-closed | `exempt_policy.validate_production_hardening`（`DEBUG`/`OPENAPI_PUBLIC` 生产禁止） |
| **T4** | `/metrics` 鉴权（token + 可选 CIDR AND） | `app/api/metrics.py` + `metrics_access_allowed`；新增 `OPENLLM_METRICS_*` 配置 |
| **T5** | 健康明细分级 | `main.py:/health`、`openllm_gateway.py:/openllm/v1/health` + `health_detail_allowed` |
| **T6** | 豁免访问审计 + 计数 | `exempt_policy.log_exempt_access`（结构化 `exempt_path_access`，不记身份头原值）；`openllm_exempt_path_requests_total` |
| **T7** | 到期强制失效 | `active_exempt_routes`（过期条目在生产失效，非生产仅告警） |
| **T8** | 豁免路径独立限流 | `app/middleware/rate_limit.py`：`OPENLLM_EXEMPT_RATE_LIMIT_RPM`，受信来源放行 |
| **T9** | 发布门禁脚本 | `backend/scripts/verify_exempt_endpoints.py`（`RESULT: PASS|FAIL`，退出码 0/1） |
| **T10** | 单测、回归、留痕 | `backend/tests/unit/test_exempt_hardening.py`（31 例）+ 本文档 |

### 2.1 新增配置项（默认值=现行行为）

`OPENLLM_EXEMPT_MATCH_MODE=prefix`、`OPENLLM_EXEMPT_ASSERT_ON_STARTUP=false`、
`OPENLLM_EXEMPT_EXPIRY_ENFORCE=false`、`OPENLLM_EXEMPT_AUDIT_ENABLED=false`、
`OPENLLM_EXEMPT_AUDIT_IP_MODE=full`、`OPENLLM_EXEMPT_AUDIT_RETENTION_DAYS=90`、
`OPENLLM_EXEMPT_RATE_LIMIT_RPM=0`、`OPENLLM_METRICS_AUTH_MODE=none`、
`OPENLLM_METRICS_TOKEN` / `_PREVIOUS` / `_ALLOWED_SOURCES`、
`OPENLLM_HEALTH_DETAIL_MODE=all`、`OPENLLM_HEALTH_TRUSTED_SOURCES`、`OPENLLM_HEALTH_TOKEN`。

生产模板（仓库根 `.env.example`）已置为收紧值：`exact` / `ASSERT=true` / `EXPIRY=true` /
`AUDIT=true` / `RATE_LIMIT_RPM=120` / `METRICS_AUTH_MODE=token` / `HEALTH_DETAIL_MODE=trusted-only`。

## 3. 验收判据执行结果

| 判据 | 结果 | 说明 |
|:----:|:----:|------|
| AC-1 精确匹配拒绝前缀误命中 | ✅ | `test_exact_mode_rejects_prefix_collision` |
| AC-2 可疑路径不进入豁免且 400 | ✅ | `test_suspicious_path_not_exempt` + IdentityGate 400 |
| AC-3 生产误开 DEBUG/OPENAPI 拒绝启动 | ✅ | `validate_production_hardening` 用例 |
| AC-4 生产文档/Schema 关闭 | ✅（由门禁保证） | `OPENAPI_PUBLIC=false` + 生产拒绝开启 |
| AC-5 `/metrics` 四态鉴权 | ✅ | token / PREVIOUS / 错 token / CIDR AND |
| AC-6 健康明细分级 | ✅ | 非受信仅 `status`；token/回环返回完整 |
| AC-7 豁免审计字段白名单 | ✅ | 断言不含 `X-User-ID` / `Authorization` 值 |
| AC-8 登记表漂移脚本退出码 1 | ✅ | `verify_exempt_endpoints.py`（含 `--k07` 可选校验） |
| AC-9 过期豁免生产失效 | ✅ | `test_expired_route_removed_when_enforced` |
| AC-10 超限 429、受信放行 | ✅ | `TestExemptRateLimit` |
| AC-11 业务面无回归 | ✅ | 848 项相关回归全通过（见 §4） |
| AC-12 `/openllm/v1/health` 限流收紧 | ✅ | `rate_limit` 共享受信判定 |
| AC-13 网络层至少一项证据 | ⬜ 待 OPS | 发布签字前置（评审 C-1） |

## 4. 测试与静态检查

| 项 | 结果 |
|----|------|
| 新增单测 `test_exempt_hardening.py` | **31 passed** |
| 相关回归（豁免/限流/生产门禁/K07/隔离矩阵等 8 个模块） | **848 passed** |
| 全量 `tests/unit`（排除环境性导入失败模块） | **709 passed**；5 failed 均为既有 `audit_logs` 表缺失（隔离复跑同样失败，非本次改动引入）；1 collection error 为 `.pylib` OpenTelemetry 包缺文件（环境问题） |
| Ruff（本次改动文件） | **All checks passed** |
| 版本一致性 | `version.json` / `APP_VERSION` / 根 `.env.example` 均为 **2.19.0** |

## 5. 提交与推送

- OpenLLM 提交：**`dd59291`**（14 files，+1081/−32）；**`cff0a32`**（登记表 60s 缓存）
- 分支：`feature/s4-identity-channel-b`
- 三远程 HEAD 核验一致：origin / backup / github 均 **`cff0a32`**

## 6. 遗留项

| 编号 | 事项 | 状态 | 处置 |
|:----:|------|:----:|------|
| L-1 | 生产环境真实开关下发与启动验证 | ⬜ | OPS 按根 `.env.example` 下发，并在生产验证「不合规拒绝启动」 |
| L-2 | `/metrics` token 下发与抓取侧配置 | ⬜ | OPS 按评审 C-4 确定载体；轮换期 ≤7 天 |
| L-3 | 网络层控制证据（AC-13） | ⬜ | OPS 提供监听地址/安全组/NetworkPolicy 任一证据 |
| L-4 | K07 标注「受信管理面（非豁免）」 | ⬜ | 评审 C-3，实施 T1 前完成 |
| L-5 | 内网受控文档入口（`/internal/docs`） | ⏸ 未实施 | 生产直接关闭文档；如需内网查阅，另行立项（非本次验收必需） |
| L-6 | 内置 `audit_logs` 测试夹具失败 | ⏳ 既有 | 与本次改动无关，另行跟踪 |

## 7. 回滚说明

| 场景 | 回滚动作 |
|------|---------|
| Prometheus 抓取失败 | `OPENLLM_METRICS_AUTH_MODE=none` 或补来源白名单 |
| 监控读不到健康明细 | `OPENLLM_HEALTH_DETAIL_MODE=all` |
| 豁免到期导致探活失败 | 登记表续期并重启；紧急时 `OPENLLM_EXEMPT_EXPIRY_ENFORCE=false` |
| 启动断言误报 | 修复登记表/路由后重启（不建议长期关闭断言） |
| 代码级异常 | 回退至 `03d5c54`（v2.18.0） |

> 所有新增开关默认关闭，回滚只需恢复环境变量或回退版本，不涉及数据迁移。

---

**记录状态**：[Final]（代码已实施并推送；L-1~L-4 由 OPS/评审组在发布窗口闭环）
