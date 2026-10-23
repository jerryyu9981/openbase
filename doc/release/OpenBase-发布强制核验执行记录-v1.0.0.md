# OpenBase 发布强制核验执行记录（生产必需开关矩阵 · S4）

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.0.0 |
| 状态 | [Review]（待 OPS 复核签字） |
| 日期 | 2026-10-23 |
| 执行人 | 研发（AI 辅助） |
| 上游依据 | 《OpenBase-主备双通道生产上线必办事项清单-v2.2.0》S2/S4；《OpenBase-五系统多租户与授权集成总览与续接指南-v1.0.0》§10.3（裁定③④） |
| 判据 | 矩阵逐项 PASS；任一 FAIL 即禁止发布（退出码 1） |

---

## 1. 结论

| 项 | 结论 |
|----|------|
| S4 发布强制核验（仓库侧） | **已执行**：新增矩阵单一事实源 + 核验脚本 + 10 例单测；`8 项 / PASS 7 / FAIL 1` |
| 阻断项 | **OpenMemory 载体漂移**：`.env.example` 中 `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=false`，§10.3 要求载体登记生产值 `true` → 发布门禁 **FAIL** |
| S2 回滚演练 | **未执行**（需 OPS 运行态与注故障窗口；回滚方案 v1.0.0 已存在） |

> 判定：仓库侧核验能力已就绪，但**当前版本不满足发布条件**——须先闭环 OpenMemory 载体置真（登记为 XR-OPS-07）并由 OPS 完成 S2 演练。

## 2. 执行方式

```bash
# 仓库载体核验（默认，扫描同级仓）
python scripts/verify_production_switches.py --json doc/test/evidence/release/switch-matrix-20261023.json

# 实际下发文件核验（发布/上线时对目标环境执行）
python scripts/verify_production_switches.py --env-file <目标环境 .env> --repo OpenLLM
```

- 矩阵唯一事实源：`config/production_switch_matrix.json`（OpenLLM 5 组、OpenMemory 1 组、DPS 1 组、OpenBase 豁免）
- 退出码：`0` = 全部 PASS；`1` = 存在 FAIL（禁止发布）
- 证据：`doc/test/evidence/release/switch-matrix-20261023.json`

## 3. 逐项结果（2026-10-23）

| # | 仓 | 开关 | 载体 | 结果 |
|:-:|----|------|------|:----:|
| 1 | OpenLLM | `ENFORCE_INBOUND_IDENTITY_HEADERS` | `.env.example` | PASS |
| 2 | OpenLLM | `RBAC_PERMISSION_ENFORCE` | `.env.example` | PASS |
| 3 | OpenLLM | `TENANT_SCOPE_ENFORCE` | `.env.example` | PASS |
| 4 | OpenLLM | `TENANT_HEADER_CONSISTENCY_ENFORCE` | `.env.example` | PASS |
| 5 | OpenLLM | `QUOTA_MISSING_FAIL_CLOSED` | `.env.example` | PASS |
| 6 | OpenMemory | `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE` | `.env.example`（值 `false`） | **FAIL** |
| 7 | DPS | `TENANT_CONTEXT_REQUIRED` | `doc/operation/DPS-部署文档-v2.1.0.md` | PASS |
| 8 | OpenBase | —（无新增生产开关） | — | PASS（豁免） |

## 4. 阻断项详情（XR-OPS-07）

| 项 | 内容 |
|----|------|
| 现象 | OpenMemory `.env.example` 登记 `OPENMEMORY_IDENTITY_REQUIRE_TENANT_SCOPE=false` |
| 与文档差异 | 《续接指南》§10.3 记为「✅ 已补齐（2026-10-14，`934e34e`）」，生产值应为 `true` |
| 影响 | 若运维照模板下发，OpenMemory 生产门禁不生效（fail-open 风险）；发布核验直接阻断 |
| 处置 | 在 OpenMemory 仓将模板生产值改为 `true`（保留 dev 覆盖说明），回执后本记录升 v1.1.0；责任方：OpenMemory 研发 + OPS |

## 5. S2 回滚演练（待 OPS）

参照《OpenBase-主备双通道生产上线回滚方案-v1.0.0》执行，需记录：

1. 开关级回退：三 REAL 与 5 组门禁开关置假后，服务以非强制态启动且既有单租户路径不受影响；
2. 通道级回退：B 通道断开 → A 直连只读接管（写路径拒绝）；
3. 版本级回退：上一镜像回切后 `verify_release.py` 无 FAIL。

> 以上需真实运行态与注故障窗口；本环境无部署面，**不填 PASS**。

## 6. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-10-23 | 研发（AI 辅助） | 初始创建：S4 仓库侧核验执行（7 PASS / 1 FAIL），登记 OpenMemory 载体漂移为 XR-OPS-07；S2 待 OPS 窗口 |
