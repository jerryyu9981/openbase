# OpenBase-测试报告-v1.8.0

## 文档信息

| 项 | 内容 |
|---|---|
| 文档编号 | OpenBase-TEST-v1.8.0 |
| 版本 | v1.0.0 |
| 状态 | [Passed]（2026-11-21） |
| 测试对象 | DPS 2.16.0、OpenBase 1.7.0、openbase-ui 1.8.0 |
| 依据 | 《OpenBase-开发需求文档-v1.8.0》《A1/A2/A7 设计文档》 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | 测试工程师 | 首版：A1/A2/A7 新增用例＋A5/A8/A13 验证＋回归 |

## 1. 测试环境

| 项 | 值 |
|---|---|
| OS | Windows |
| Python | `D:\Python\python.exe`（pytest 串行，`-o addopts=""`） |
| 数据库 | 真实 SQLite（引擎级用例自行建库，不 mock 引擎） |
| 前端 | vitest 2.1.8 ＋ `npm run build`（vue-tsc＋vite） |

## 2. 用例执行结果

### 2.1 DPS 新增（18 条）

| 文件 | 条数 | 结果 | 覆盖 |
|---|---:|---|---|
| `tests/test_template_filter_v2_16.py` | 6 | PASS | keyword name/code、通配符转义、分类/类型、AND、空白、路由 400 |
| `tests/test_annotation_stats_v2_16.py` | 6 | PASS | 4 分组、过滤同口径、legacy 空集、路由顺序与 400 |
| `tests/test_annotation_claim_v2_16.py` | 6 | PASS | reviewer/level 过滤、领取成功/幂等/冲突/非 pending/缺失/缺列、路由 401/404/409 |

### 2.2 DPS 回归

| 文件 | 结果 |
|---|---|
| `tests/test_v2_9_1_permission_mapping.py` | PASS（含 `/claim` → update、后缀唯一性） |
| `tests/test_v2_15_annotation_detail.py` | PASS |
| `tests/test_portrait_list_route.py` | PASS |
| 合计 | 35 passed（含新增权限断言） |

### 2.3 OpenBase 代理

| 文件 | 条数 | 结果 |
|---|---:|---|
| `tests/test_dps_proxy.py` | 49 | PASS（新增 5 条：模板筛选透传、stats 路径/参数/400、claim 透传/409） |

### 2.4 前端

| 文件 | 条数 | 结果 |
|---|---:|---|
| `tests/dps-template-filter-v180.spec.ts` | 3 | PASS |
| `tests/dps-annotation-stats-v180.spec.ts` | 2 | PASS |
| `tests/dps-annotation-claim-v180.spec.ts` | 3 | PASS |
| `tests/api-dps-v1410.spec.ts` | 22 | PASS |
| `tests/dps-template-health.spec.ts` | 5 | PASS（A8） |
| `tests/r5-wiring-v195.spec.ts` | 15 | PASS（含 A5/A13 相关真实化接线） |
| `npm run build` | — | 成功 |

## 3. 需求回溯对照

| 需求 | 用例 | 结论 |
|---|---|---|
| FR-180-01 A7 | 2.1 第 1 行＋2.3 模板透传＋2.4 首行 | 通过 |
| FR-180-02 A1 | 2.1 第 2 行＋2.3 stats＋2.4 统计 | 通过 |
| FR-180-03/04 A2 | 2.1 第 3 行＋2.2 权限＋2.3 claim＋2.4 领取 | 通过 |
| FR-180-05 A5/A8/A13 | 2.4 health/r5/api-dps | 通过 |
| NFR-180-01 安全 | 转义/参数化、身份只由服务端解析 | 通过 |
| NFR-180-02 可靠性 | 缺列降级、幂等领取、KPI 静默失败 | 通过 |
| NFR-180-03 兼容性 | 未升级上游忽略未知参数；既有 44 条代理用例保持通过 | 通过 |

## 4. 缺陷与处置

| 编号 | 现象 | 处置 |
|---|---|---|
| D-180-01 | 设计稿初稿统计用例数记为 9，实际 6 | 文档已更正为 6 |
| D-180-02 | 权限映射测试原断言仅 3 项覆盖 | 同步新增 `/claim` 与后缀唯一性断言 |

无未关闭阻断缺陷。

## 5. 结论

- 新增与回归用例全部通过，构建成功。
- A1/A2/A7 达到验收标准；A5/A8/A13 验证证据齐备。
- 建议进入部署与运维阶段。
