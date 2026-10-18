# OpenBase-P7 K07 终验报告-v1.1.0

| 项目 | 内容 |
|------|------|
| 文档名称 | 豁免行加固 P7（K07 端点过滤矩阵终验）报告 |
| 文档编号 | OB-SEC-EXEMPT-P7-v1.1.0 |
| 版本 | **v1.1.0** |
| 状态 | **[Final]** |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |
| 关联执行包 | 《OpenBase-豁免行加固生产窗口执行包-v1.0.0》§12（P7）、§15（C-5） |
| 关联审批单 | 《OpenBase-G4-T4-2-A直连豁免行双签审批单-v1.2.0》§8 |
| 执行环境 | 当前可用全栈环境 `192.168.0.157`（OpenLLM 2.19.1 / `8d20a27` → `93ac545`） |
| 证据 | `doc/test/evidence/s7/security/exempt-hardening/window-20261018/p7-k07.json` |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次发布：双口径终验（基线快照回放 + 当前代码实时导出），判定 `FAIL_DRIFT`（16 个新增端点未注册） |
| v1.1.0 | 2026-10-18 | OpenBase 架构组 | 按方案 A 完成整改：补登记 16 个端点、重生成矩阵 v1.3.0、同步基线快照并复跑；判定转 **PASS**（gaps 16→0） |

---

## 1. 结论

| 口径 | 整改前 | 整改后 |
|------|:------:|:------:|
| 基线快照回放 | PASS（gaps=0，351 操作） | PASS（gaps=0，367 操作，快照已同步） |
| 当前代码实时导出 | **FAIL（gaps=16）** | **PASS（gaps=0 / uncovered=0 / exemption_without_approval=0）** |
| 豁免登记表门禁 | PASS | PASS（5 条一致；DPS `exempt_invalid=35` 仅 WARN） |
| 受信管理面标注 | PASS | PASS（`/openllm/v1/health` = 受信管理面（非豁免）） |

**P7 判定：PASS。** K07 全量门禁已清零，矩阵与当前代码一致，P8 不再受 P7 阻塞。

## 2. 整改内容（方案 A）

| # | 动作 | 结果 |
|:-:|------|------|
| 1 | `backend/scripts/k07_isolation_registry.py` 补登记 16 个端点 | 每个端点挂 3 个用例引用（untrusted-403 / trusted-passthrough / family-suite）；新增族 `writeback`、`prompt`、`trace` |
| 2 | 重生成矩阵 v1.3.0（JSON + 填报文档） | 业务面 349→365、总行 354→370；豁免仍 5 行 |
| 3 | 同步 `backend/data/openapi-llm-snapshot.json` | 更新为 2026-10-18 导出（292 路径 / 367 操作，2,046,780 bytes） |
| 4 | `tests/unit/test_isolation_matrix_endpoints.py` | 指向 v1.3.0；计数断言 349→365 |
| 5 | 复跑门禁与测试 | `--check`：gaps=0；矩阵用例 **792 passed**；`test_s4_t11_k07_matrix.py` + `test_exempt_hardening.py` **41 passed** |

OpenLLM 提交：`93ac545 feat(k07): 补登记 16 个新增端点并重生成矩阵 v1.3.0（gaps 0）`。

## 3. 已修复的 16 项缺口

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

## 4. 漂移分析（复盘）

| 项 | 值 |
|----|----|
| 基线（2026-09-11） | 278 paths / 351 operations |
| 当前代码（2026-10-18） | 292 paths / 367 operations |
| 增量 | +14 paths / +16 operations |
| 归因 | 基线之后新增的 writeback / prompt assembly / trace export 路由未同步登记与矩阵 |
| 与豁免加固关系 | 无关；漂移由本次终验的实时导出口径发现 |
| 处置 | 已按方案 A 清零（§2） |

## 5. 执行方法（复跑命令）

运行环境：pgAdmin 精简 Python 3.13，依赖经 `doc/tmp/run_openllm_script.py` 注入，`D:\PostgreSQL\17\bin` 与 `pgAdmin 4\runtime` 前置 `PATH`（psycopg 需 libpq）。

```powershell
# 实时门禁（当前代码导出）
python -B doc/tmp/run_openllm_script.py scripts\k07_endpoint_matrix.py `
  --openapi-file doc\tmp\p7-openapi-snapshot.json --check

# 默认快照门禁（CI 同口径）
python -B doc/tmp/run_openllm_script.py scripts\k07_endpoint_matrix.py --check

# 豁免登记表门禁
python -B doc/tmp/run_openllm_script.py scripts\verify_exempt_endpoints.py `
  --k07 doc\test\evidence\s7\gate\k07-finalize.json

# 矩阵驱动隔离用例
python -B doc/tmp/run_openllm_pytest.py tests/unit/test_isolation_matrix_endpoints.py -q
```

## 6. 对 P8 的影响

P7 已闭环，P8 剩余前置：

| 项 | 状态 | 责任方 |
|----|:----:|------|
| P7 全量门禁 gaps=0 | ✅ | OpenBase 架构组 |
| 目标环境网络证据（三基础设施 + OpenLLM 无公网入口） | ⚠️ 本机已证，目标环境待补 | OPS |
| 豁免路径调用量告警配置 | ❌ 未留证 | OPS |
| 豁免到期告警配置 | ❌ 未留证 | OPS |
| 技术签字 + 发布签字 | ⏳ 待人工 | 签字人 |

审批单维持 `[待签署]`，待告警留证后由双签人签署。

## 7. 证据索引

| 文件 | 说明 |
|------|------|
| `window-20261018/p7-k07.json` | 整改前后双口径结果、16 项修复、测试与提交号 |
| OpenLLM `doc/design/OpenLLM-K07-端点过滤矩阵填报-v1.3.0.md` / `.matrix.json` | 矩阵 v1.3.0（370 行） |
| OpenLLM `backend/data/openapi-llm-snapshot.json` | 2026-10-18 导出基线（367 操作） |
| OpenLLM `backend/scripts/k07_isolation_registry.py` | 16 个新增端点注册位 |
| `s7/gate/k07-finalize.json` | 豁免字段终验（四子系统 `exempt_invalid=0`，DPS 35） |
| `s7/l2-2/matrix-finalize.json` | T4-1/3/4 PASS；T4-2 PENDING |
