# OpenBase 前端全页面走查报告 - 画像模块 500 修复复验

| 文档版本 | 状态 | 适用环境 | 作者 | 日期 |
|---|---|---|---|---|
| v1.1.0 | [Final] | Dev（本地五件套联调环境） | AD-OpenBase-Dev | 2026-09-03 |

## 修订历史

| 版本 | 日期 | 修订说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-09-03 | 前端全页面清单走查首版：73 页 71 可用，画像数据层 ISSUE-001/002 记录 | AD-OpenBase-Dev |
| v1.1.0 | 2026-09-03 | ISSUE-001 修复后画像模块复验：overview/list/reports/batch 数据恢复可用，ISSUE-001 关闭 | AD-OpenBase-Dev |

## 1. 复验结论摘要

ISSUE-001（画像数据总览/列表接口 500）已由 DPS 侧修复并复验通过，画像模块受影响 4 页（数据总览/画像列表/分析报表/批量任务）恢复真实数据展示，错误提示消失。ISSUE-002（画像列表页错误静默、无错误态）属前端缺陷，不在本次范围，保持开启。

| 页面 | v1.0.0 | v1.1.0 复验 | 结论 |
|---|---|---|---|
| /portrait/overview | ISSUE-001：数据总览加载失败 500 | KPI/风险分布/最新画像全部加载（画像总数 40、平均综合分 65.53、活跃画像率 97.5%） | ✅ 通过 |
| /portrait/list | 数据为空（ISSUE-002 同源） | 40 条分页列表 + 上游健康度 healthy（DPS v2.8.1），搜索/刷新可用 | ✅ 通过 |
| /portrait/reports | 数据为空（同源） | 复用列表数据源，数据正常展示 | ✅ 通过 |
| /portrait/batch | 数据为空（同源） | 复用列表数据源，数据正常展示 | ✅ 通过 |

## 2. 根因与修复（DPS 侧）

- 现象复现链路：网关 `GET /api/v1/dps-proxy/portraits?page=1&page_size=5`（带 JWT）→ 500；直连 DPS `GET http://127.0.0.1:8030/api/v2/portrait/list` → 500。
- 根因：DPS `/portrait/list` 处理器曾错误调用 `query_engine.get_portraits(page=, page_size=)`，与引擎方法签名 `get_portraits(person_ids, force_refresh)` 关键字不匹配 → TypeError → 500。v2.8.0 已将处理器改调 `query_engine.search_portraits(filters=None, pagination=Pagination(page, page_size))`（真实挂载模块 `rest_api/routes/routes_profiles.py`）。
- 运行环境侧：线上 DPS 进程为旧代码（启动时间早于修复提交），重启加载新代码后 500 消除；数据库沙箱路径不可写导致 SQLite 降级，改为可写路径后演示种子 40 条正常入库。
- 代码卫生：删除被 `rest_api/routes/` 包遮蔽、从不被导入且含同源旧 bug 的遗留单文件 `src/rest_api/routes.py`。

## 3. 复验证据

### 3.1 接口层（网关，带登录 JWT）

| 接口 | 结果 |
|---|---|
| GET /api/v1/dps-proxy/portraits?page=1&page_size=5 | 200，total=40，page_size=5，total_pages=8，items 含真实画像 |
| GET /api/v1/dps-proxy/reports/overview | 200，total_profiles=40，风险分布/趋势真实聚合 |
| GET /api/v1/dps-proxy/tags/categories | 200 |
| GET /api/v1/dps-proxy/health | 200，status=healthy，version=2.8.1 |
| GET /api/v1/dps-proxy/audit/logs | 200（含本次复验 READ 审计流水） |

### 3.2 DPS 侧自动化回归

新增 `DPS/src/tests/test_portrait_list_route.py`：mock 真实挂载模块 `routes_profiles.query_engine` 断言 200/分页结构/Pagination 透传/不再误调 `get_portraits`；真实引擎（SQLite 回退）空库 200。执行结果 **2 passed / 2 collected**。

### 3.3 页面层（浏览器实走，admin 登录态）

- /portrait/overview：KPI 卡片（画像总数 40、今日新增 6、高风险 8、活跃画像率 97.5%）+ 最新画像表 5 行，无错误提示。
- /portrait/list：表头 KPI + 40 条分页（每页 20）+ "共 40 条"，姓名/ID/风险等级/更新时间齐全。
- /portrait/reports、/portrait/batch：数据源同列表，正常展示。

## 4. 遗留项

- ISSUE-002（low）：画像列表页对接口异常静默吞错、无错误态与重试入口，属前端体验缺陷，待前端迭代处理。
- DPS 运行依赖 SQLite 落盘路径：沙箱内需以可写路径（如 `%TEMP%`）指定 `SQLITE_PATH`，正式环境建议固定持久化路径。
- DPS 仓库代码提交因沙箱对 `.git/objects` 的写限制未在本次会话内完成，工作区改动（新增回归测试、删除遗留文件、CHANGELOG 记录）已就绪，待沙箱外/放宽规则后提交。

## 5. 参考资料

- v1.0.0 走查报告（ISSUE-001/002 原始记录）
- DPS CHANGELOG v2.8.1 FIX-281-06 / Release Note
