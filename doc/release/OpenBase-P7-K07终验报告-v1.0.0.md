# OpenBase-P7 K07 终验报告-v1.0.0

| 项目 | 内容 |
|------|------|
| 文档名称 | 豁免行加固 P7（K07 端点过滤矩阵终验）报告 |
| 文档编号 | OB-SEC-EXEMPT-P7-v1.0.0 |
| 版本 | **v1.0.0** |
| 状态 | **[Final]** |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |
| 关联执行包 | 《OpenBase-豁免行加固生产窗口执行包-v1.0.0》§12（P7）、§15（C-5） |
| 关联审批单 | 《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.1.0》§8 |
| 执行环境 | 当前可用全栈环境 `192.168.0.157`（OpenLLM 2.19.1 / `8d20a27`） |
| 证据 | `doc/test/evidence/s7/security/exempt-hardening/window-20261018/p7-k07.json` |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次发布：P7 双口径终验（基线快照回放 + 当前代码实时导出）、缺口清单、漂移分析与 P8 处置选项 |

---

## 1. 结论

| 口径 | 结果 | 说明 |
|------|:----:|------|
| 基线快照回放（`backend/data/openapi-llm-snapshot.json`，2026-09-11） | **PASS** | `total=351 / gaps=0 / uncovered=0 / exemption_without_approval=0` |
| 当前代码实时导出（`main.app.openapi()`） | **FAIL** | `total=367 / gaps=16 / uncovered=0 / exemption_without_approval=0` |
| 豁免登记表门禁（`verify_exempt_endpoints.py --k07`） | **PASS** | 5 条登记一致；DPS `exempt_invalid=35` 仅 WARN |
| 受信管理面标注 | **PASS** | `/openllm/v1/health` = 「受信管理面（非豁免）」 |

**P7 判定：`FAIL_DRIFT`。** 豁免面判据全部满足；但当前代码相比 2026-09-11 基线新增 **16 个未注册隔离用例的业务端点**，K07 全量门禁拒绝（AC-T12-2）。该漂移与本次豁免行加固无关，但构成 P8 双签前置不成立。

## 2. 执行方法

运行环境：pgAdmin 精简 Python 3.13（`python313._pth`），依赖经 `doc/tmp/run_openllm_script.py` 注入（backend → `.venv-libs` → OpenBase `.venv`），并将 `D:\PostgreSQL\17\bin` 与 `pgAdmin 4\runtime` 前置于 `PATH`（psycopg 需 libpq）。

```powershell
# 1) 从当前代码实时导出 OpenAPI（2,046,780 bytes / 292 paths / 367 operations）
python -B doc/tmp/run_openllm_script.py scripts\k07_endpoint_matrix.py `
  --export-openapi doc\tmp\p7-openapi-snapshot.json

# 2) 实时门禁
python -B doc/tmp/run_openllm_script.py scripts\k07_endpoint_matrix.py `
  --openapi-file doc\tmp\p7-openapi-snapshot.json --check

# 3) 基线回放（对照）
python -B doc/tmp/run_openllm_script.py scripts\k07_endpoint_matrix.py `
  --openapi-file backend\data\openapi-llm-snapshot.json --check

# 4) 豁免登记表门禁
python -B doc/tmp/run_openllm_script.py scripts\verify_exempt_endpoints.py `
  --k07 doc\test\evidence\s7\gate\k07-finalize.json
```

## 3. 缺口清单（16 项，全部为业务面）

| 族 | 端点 | 方法 | 类别 |
|----|------|:----:|------|
| trace | `/openllm/v1/trace/metrics/export` | GET | 列表分页/集合读 |
| trace | `/openllm/v1/trace/fidelity/export` | GET | 列表分页/集合读 |
| writeback | `/openllm/v1/writeback/receipts` | GET | 列表分页/集合读 |
| writeback | `/openllm/v1/writeback/stats` | GET | 列表分页/集合读 |
| writeback | `/openllm/v1/writeback/dead-letter` | GET | 列表分页/集合读 |
| writeback | `/openllm/v1/writeback/dead-letter/replay` | POST | 批量/异步写回 |
| prompt | `/openllm/v1/prompt/assembly/template` | GET | 列表分页/集合读 |
| prompt | `/openllm/v1/prompt/assembly/template` | PUT | CRUD（集合写） |
| prompt | `/openllm/v1/prompt/assembly/preview` | POST | 批量/创建（集合写） |
| prompt | `/openllm/v1/prompt/assembly/compare` | GET | 列表分页/集合读 |
| prompt | `/openllm/v1/prompt/assembly/compare/records` | GET | 列表分页/集合读 |
| prompt（api 别名） | `/api/v1/prompt/assembly/template` | GET | 列表分页/集合读 |
| prompt（api 别名） | `/api/v1/prompt/assembly/template` | PUT | CRUD（集合写） |
| prompt（api 别名） | `/api/v1/prompt/assembly/preview` | POST | 批量/创建（集合写） |
| prompt（api 别名） | `/api/v1/prompt/assembly/compare` | GET | 列表分页/集合读 |
| prompt（api 别名） | `/api/v1/prompt/assembly/compare/records` | GET | 列表分页/集合读 |

> 均无 `A 直连豁免` 命中，`exemption_without_approval=0`；不涉及 `/health`、`/metrics`、`/docs`、`/redoc`、`/openapi.json`。

## 4. 漂移分析

| 项 | 值 |
|----|----|
| 基线（2026-09-11） | 278 paths / 351 operations |
| 当前代码（2026-10-18） | 292 paths / 367 operations |
| 增量 | +14 paths / +16 operations |
| 归因 | 2026-09-11 之后新增的 writeback / prompt assembly / trace export 路由，未同步登记 `k07_isolation_registry.py` 与矩阵 v1.2.0 |
| 与本次豁免加固关系 | 无关（本次改动仅涉及 IdentityGate 豁免判定、`/metrics` 鉴权、健康分级、审计、限流与登记表） |
| 影响 | 下一次 CI 执行 K07 门禁会拒绝（AC-T12-2）；不影响豁免行本身 |

## 5. 豁免面判据（全部满足）

| 判据 | 结果 | 证据 |
|------|:----:|------|
| `EXEMPT_ROUTES` ↔ `config/exempt_endpoints.json` 集合一致（5 条） | PASS | `verify_exempt_endpoints.py` 输出 |
| 登记表字段完整（ticket/approver/category/expires_at） | PASS | 同上 |
| OpenLLM / OpenRAG / OpenMemory `exempt_invalid=0` | PASS | `k07-finalize.json`（5/5、10/10、9/9） |
| DPS `exempt_invalid=35` 仅 WARN | PASS | 同上（K07-DPS-AUTH 独立项） |
| `/openllm/v1/health` 为「受信管理面（非豁免）」 | PASS | 实时矩阵行 |
| A 直连豁免行 = `/health`、`/metrics` | PASS | 实时矩阵 `exempt_rows=2`（文档面生产关闭后不入 openapi） |

## 6. 对 P8 的影响

P8 双签的前置项「K07 全量门禁 gaps=0」不成立，且审批单 §8 另有两项待 OPS 留证（豁免路径调用量告警、到期告警）。因此本次**不具备签署条件**，审批单维持 `[待签署]`。

处置选项：

| 方案 | 内容 | 影响 | 建议 |
|:----:|------|------|------|
| **A** | 为 16 个新端点补登记 `k07_isolation_registry.py`，重生成矩阵 v1.3.0 与填报文档，复跑 `--check` 至 `gaps=0` 后重做 P7 | 需改动 OpenLLM 注册表/矩阵/测试常量并跑全量隔离用例；周期较长 | **推荐**（彻底清零，符合 AC-T12-2） |
| B | 由审批人将「K07-NEW-ENDPOINTS」列为独立整改项，书面豁免本次双签，整改单列跟踪 | 可立即完成 P8 文书，但门禁仍红，G4 关闭带条件 | 仅在发版窗口紧张时采用 |

## 7. 证据索引

| 文件 | 说明 |
|------|------|
| `window-20261018/p7-k07.json` | 双口径结果、16 项缺口、漂移分析、豁免面判据 |
| `doc/tmp/p7-openapi-snapshot.json` | 当前代码实时导出（SHA256 `DC2679B3…9B381F`，不入库） |
| `doc/tmp/p7-matrix-report.json` | 实时矩阵行（367 行） |
| `s7/gate/k07-finalize.json` | 豁免字段终验（四子系统 `exempt_invalid=0`，DPS 35） |
| `s7/l2-2/matrix-finalize.json` | T4-1/3/4 PASS；T4-2 PENDING |
