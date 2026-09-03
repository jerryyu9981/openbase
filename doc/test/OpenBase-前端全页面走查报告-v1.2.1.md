# OpenBase 前端全页面走查报告 - ISSUE-002 画像列表错误态修复复验

| 文档版本 | 状态 | 适用环境 | 作者 | 日期 |
|---|---|---|---|---|
| v1.2.1 | [Final] | Dev（本地五件套联调环境） | AD-OpenBase-Dev | 2026-09-03 |

## 修订历史

| 版本 | 日期 | 修订说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-09-03 | 前端全页面清单走查首版：ISSUE-001（画像接口 500）/ ISSUE-002（列表页错误静默）记录 | AD-OpenBase-Dev |
| v1.1.0 | 2026-09-03 | ISSUE-001 修复复验：overview/list/reports/batch 数据恢复，ISSUE-001 关闭 | AD-OpenBase-Dev |
| v1.2.0 | 2026-09-03 | ISSUE-002 修复复验：画像列表页错误提示 + 重试入口 + 错误态空文案，故障注入与恢复链路验证通过 | AD-OpenBase-Dev |
| v1.2.1 | 2026-09-03 | 补充 ISSUE-002 自动化回归测试 `tests/portrait-list-error.spec.ts`（3 例），vitest 全量 42/42 通过 | AD-OpenBase-Dev |

## 1. 复验结论摘要

ISSUE-002（画像列表页静默吞错，数据失败无提示与重试入口）已关闭。

画像列表页 `PortraitList.vue`（`/portrait/list`，及复用同一组件的 `/portrait/reports`、`/portrait/batch`）现具备完整错误态：

1. 数据请求失败时顶部展示 `el-alert` 错误条（文案：画像列表加载失败：{原因}）并内置「点击重试」按钮；
2. 表体空态随错误状态切换为引导文案（加载失败，请点击上方提示条「点击重试」），不再误导性显示"暂无数据"；
3. KPI 卡片与上游健康度独立降级（显示 `-` / `不可达`），不阻断页面渲染；
4. 重试成功后错误条自动消失并恢复数据。

## 2. 修复内容（openbase-ui）

| 文件 | 修复 |
|---|---|
| `src/modules/portrait/pages/PortraitList.vue` | 错误条已含（加载失败文案 + 点击重试 + closable）；本次补充：表体 `#empty` 插槽随 `errorMessage` 显示错误引导文案，移除冗余独立 `el-empty`，消除错误态下"暂无数据"误导 |
| `tests/portrait-list-error.spec.ts` | ISSUE-002 自动化回归 3 例：① 接口失败展示错误条与错误引导空态（不再误显"暂无画像数据"）；② 点击「点击重试」恢复后错误条消失并渲染数据；③ KPI/上游健康度独立降级展示 |
| 画像模块其他数据页（Overview/Tags/Rules/PortraitSearch） | 同源错误模式（el-alert + errorMessage + 重试/关闭）已在工作区统一，与列表页一致 |

## 3. 复验证据（故障注入 + 恢复）

执行方式：浏览器以 admin 登录态访问 `/portrait/list`；停掉上游 DPS（8030）使网关代理返回 502，模拟数据源故障；随后重启 DPS 并点击「点击重试」验证恢复。

| 场景 | 页面表现 | 结论 |
|---|---|---|
| 上游 DPS 停止（502） | 错误条：画像列表加载失败：Request failed with status code 502；按钮：点击重试；表体：加载失败，请点击上方提示条「点击重试」；KPI：- / 不可达；分页：共 0 条禁用 | ✅ 错误可见、可重试 |
| DPS 恢复后点击「点击重试」 | 错误条消失；KPI：画像总数 40 / 高风险 8 / healthy（DPS v2.8.1）；列表 40 条分页正常 | ✅ 一键恢复 |

浏览器控制台无 SFC 编译错误（仅模块注册期 Vue Router 预置 warn，与本次改动无关）。

### 3.1 自动化回归（v1.2.1 补充）

`tests/portrait-list-error.spec.ts`（@vue/test-utils 挂载 `PortraitList.vue` + mock `dpsApi`）锁定 ISSUE-002 四条验收点，防止回归：

| 用例 | 断言 | 结果 |
|---|---|---|
| 接口失败 → 错误可见 | 错误条含「画像列表加载失败 / 点击重试」；表体空态含「加载失败，请点击上方提示条『点击重试』」且不含「暂无画像数据」 | ✅ |
| 重试恢复 | 首调 reject、二调 resolve：点击重试后错误条消失、列表渲染数据 | ✅ |
| KPI 独立降级 | 列表失败时 KPI/健康度仍正常展示（40 / healthy），不静默空白 | ✅ |

验证命令：`npx vitest run`（全量 42/42 passed，7 个测试文件）；`npx vue-tsc --noEmit`、`npx eslint` 均 0 错误。

## 4. 遗留项

- ISSUE-001/ISSUE-002 均已关闭。画像详情页（`/portrait/:id`）、搜索等依赖真实数据/接口的页面建议在后续回归中补充错误态走查。
- ISSUE-002 修复（`PortraitList.vue` + 回归测试 + 本报告）已随修复提交落地；画像模块其余联调遗留改动（Overview/Tags/Rules/PortraitSearch/`dps.ts`/`index.ts` 等）仍在工作区，建议随画像模块联调整体评审后统一提交。

## 5. 参考资料

- v1.0.0 / v1.1.0 / v1.2.0 走查报告
- ISSUE-001 修复：DPS `/api/v2/portrait/list` 500（见 DPS CHANGELOG v2.8.1）
