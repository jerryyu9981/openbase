# OpenBase-DPS 前端收口验证记录 v1.0.0

| 项 | 内容 |
|---|---|
| 文档 | 前端收口验证记录（Phase 3 后 UI 收口） |
| 版本 | **v1.0.0** |
| 状态 | **[Approved]**（2026-11-20，随本轮收口批准） |
| 日期 | 2026-11-20 |
| 范围 | 标注作业台主体检索、降级文案清理、设计文档回填 |
| 上游依据 | 《OpenBase-DPS统一前端页面功能设计》v2.4.0；《OpenBase-测试报告》v1.2.0 |
| 存放 | `doc/test/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-20 | FE-OpenBase-Dev | 首版：收口项、变更文件、验证证据与结论 |

---

## 1. 收口项

| 编号 | 项 | 处置 |
|---|---|---|
| FC-01 | 标注作业台主体检索未接 A6 | 改为 `listPortraits({ keyword })` 服务端检索；仅 404 时回退「精确 ID/外部 ID + 前 100 条」旧口径 |
| FC-02 | 画像详情时间线文案称「A10 待后端」 | 按设计 AC-PT-4 标注时间线仍取标注队列创建时间；文案改为「单条审核留痕见审核收件箱（A10）」——A10 的实际落点是审核收件箱审计时间线 |
| FC-03 | 7 处过时降级文案/注释 | 更新 `PortraitList`、`PortraitSearch`、`DpsMeasureView`、`DpsTagSystemView`、`DpsAnnotationWorkbenchView`、`Overview`×2、`portraitTools.ts` 注释 |
| FC-04 | 设计文档未回填后端交付 | 设计文档升 v2.4.0：§12 风险、§14.3 API 缺口、§14.7 降级口径标注 A6/A9/A10/A11/A12/A14 已闭环；A1/A2/A3/A4/A5/A7/A8/A13 仍未排期（A4 P0） |

## 2. 变更文件

- `openbase-ui/src/modules/portrait/pages/DpsAnnotationWorkbenchView.vue`
- `openbase-ui/src/modules/portrait/pages/PortraitList.vue`
- `openbase-ui/src/modules/portrait/pages/PortraitSearch.vue`
- `openbase-ui/src/modules/portrait/pages/DpsMeasureView.vue`
- `openbase-ui/src/modules/portrait/pages/DpsTagSystemView.vue`
- `openbase-ui/src/modules/portrait/pages/Overview.vue`
- `openbase-ui/src/modules/portrait/pages/PortraitDetail.vue`
- `openbase-ui/src/modules/portrait/portrait/portraitTools.ts`
- `doc/design/OpenBase-DPS统一前端页面功能设计-v1.0.0.md`（内容版本 v2.4.0）

## 3. 验证

| 项 | 命令 | 结果 |
|---|---|---|
| 类型检查 | `vue-tsc --noEmit` | **exit 0** |
| 静态检查 | `npm run lint`（eslint ＋ vue-tsc） | **exit 0，0 errors**（29 条既有 warning，非本任务引入） |
| 前端回归 | vitest 10 个相关 spec | **10 passed／131 tests passed**（208.24s） |
| 生产构建 | `npm run build` | **成功**（`vue-tsc` 通过；vite built in 26.60s） |

证据：`doc/test/evidence/v1.5.0/openbase-vitest-frontend-closure.txt`。

## 4. 结论

FC-01～FC-04 完成；前端与设计文档口径一致，Phase 3 后的 UI 收口闭环。未排期 API 缺口（A1/A2/A3/A4/A5/A7/A8/A13）已在设计文档中显式保留。
