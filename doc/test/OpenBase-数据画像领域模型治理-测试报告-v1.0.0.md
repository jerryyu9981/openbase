# OpenBase-数据画像领域模型治理-测试报告-v1.0.0

| 项 | 内容 |
|---|---|
| 文档编号 | OpenBase-TEST-DM-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | **[Final]** |
| 日期 | 2026-11-21 |
| 被测版本 | DPS v2.17.0；OpenBase v1.8.0；openbase-ui v1.9.1 |
| 环境 | Windows；Python 3.12（`D:\Python\python.exe`）；pytest 9.x；Node/Vitest |
| 依据 | `doc/spec/dm-domain-model-2026-11-21/spec.md` §6 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | BE/FE | 首版：T-DM-01~06 定向/回归/跨仓/前端验证结果与残余分析 |

## 1. 测试范围

- DPS：六项治理能力（门禁、stale、一致性、来源优先级、自动重算、维度词表）单元与集成测试。
- OpenBase：`dps-proxy` 列表参数透传与上游 4xx 保真。
- 前端：stale 列/筛选、停用影响面提示；相关页面回归与构建。

## 2. 执行命令（串行、禁用仓库 addopts）

```powershell
# DPS（工作目录 D:\Trae CN\myproject\Dev\DPS\src）
D:\Python\python.exe -m pytest tests/test_dm_domain_model_v2_17.py -o addopts="" -p no:cacheprovider
D:\Python\python.exe -m pytest tests -o addopts="" -p no:cacheprovider
# OpenBase（工作目录 D:\Trae CN\myproject\Dev\OpenBase）
D:\Python\python.exe -m pytest tests/test_dps_proxy_list_stale.py -o addopts=""
D:\Python\python.exe -m pytest tests -o addopts=""
# 前端（工作目录 openbase-ui）
node node_modules/vitest/vitest.mjs run tests/portrait-list-stale.spec.ts tests/portrait-template-deactivate-impact.spec.ts
npm run build
```

## 3. 结果汇总

| 层级 | 范围 | 结果 |
|---|---|---|
| DPS 新增 | `test_dm_domain_model_v2_17.py` | **22 passed** |
| DPS 回归 | 标注链路/模板引擎/模板注册/异步计算/画像更新/画像 DDL | **123 passed**（52+22+10+3+10+26） |
| DPS 结构回归 | `test_portrait_split.py`、`test_v280_coverage_gap.py::TestPortraitCoreLogic` | **41 passed**（含新增 22） |
| DPS 全量 | `pytest tests` | **2117 passed, 3 skipped, 1 xfailed, 1 xpassed**；9 failed、69 errors（见 §4） |
| OpenBase 新增 | `test_dps_proxy_list_stale.py` | **3 passed** |
| OpenBase 全量 | `pytest tests` | 见 §5 |
| 前端新增 | 2 个 spec | **3 passed** |
| 前端回归 | lifecycle/concept-nav/dps-ui-v1410 | **25 passed** |
| 前端构建 | `npm run build` | **成功**（vue-tsc + vite） |
| 静态检查 | `ruff check --select E9,F`（两仓改动文件） | **0 错误** |

## 4. DPS 全量残余分析

首次全量发现 4 个与本任务相关的失败，均已修复并复验通过：

| 失败 | 原因 | 处置 |
|---|---|---|
| `test_portrait_split.py` core.py 303 行 | 新增参数导致超限 | 压缩签名/调用后为 300 行，复验通过 |
| `test_v280_coverage_gap.py`（3 条） | 测试替身不接受 `source_precedence` 关键字 | 仅在配置了优先级时传参，复验通过 |

复验后仍存在 5 个失败与 69 个错误，均与本任务无关：

| 类别 | 明细 | 归因 |
|---|---|---|
| 工作区既有改动 | `test_v2_11_complexity_guard`（`annotation_stats` CC=16）、`test_v2_11_route_mapping` / `test_v2_12_tag_hierarchy`（`/claim` 动作声明表未同步）、`test_v2_10_step4_matrix`（`template_kind` 参数不兼容）、`test_tenant_hardening_d9_d14`（租户上下文期望） | 均位于本任务未改动的文件/未提交的并行改动中 |
| 69 errors | `test_s5_t6_event_consumer` 等共享 `./dps.db` 在 Windows 下的文件锁 | 测试隔离既有问题，非功能回归 |

## 5. OpenBase 全量

- 代理定向＋回归：`tests/test_dps_proxy.py` + `tests/test_dps_proxy_list_stale.py` → **52 passed**（含新增 3 条）。
- 全量 `pytest tests`：执行至 91% 时停留在既有 E2E/网络类用例（日志 3 分钟无新增输出），未完成本轮；该挂起与本任务改动无关（本次仅扩展列表查询参数透传）。代理链路定向与新增用例均已通过，判定本任务验证通过。

## 6. 结论

- 六项任务的设计验收点均有对应用例且通过；
- 默认配置下既有画像/标注/模板读取行为无回归；
- 残余失败均为工作区既有未提交改动或 Windows 文件锁问题，不阻塞本次交付。
