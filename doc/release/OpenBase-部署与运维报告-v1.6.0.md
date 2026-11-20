# OpenBase-部署与运维报告-v1.6.0

| 项 | 内容 |
|---|---|
| 版本 | v1.6.0（后端 ＋ 前端） |
| 状态 | [Ready for Release] |
| 日期 | 2026-11-20 |
| 变更范围 | A4 标注详情代理 ＋ 审核收件箱接入 |
| 回滚目标 | v1.5.0 |

## 1. 制品与依赖

| 项 | 说明 |
|---|---|
| 后端 | `openbase/modules/dps_proxy/__init__.py`、`openbase/__init__.py` |
| 前端 | `openbase-ui/src/core/api/dps.ts`、`DpsAnnotationWorkbenchView.vue`、`package.json` |
| 数据库 | **无**迁移（无新表/列） |
| 依赖 | 无新增 npm/pip 依赖 |
| 配置 | 无新增环境变量（沿用 `OPENBASE_DPS_UPSTREAM_BASE`） |

## 2. 上线步骤

1. 确认 DPS v2.15.0 已上线并通过冒烟。
2. 部署 OpenBase 后端 v1.6.0；`GET /health` 200。
3. 冒烟代理（携带有效 JWT）：
   - `GET /api/v1/dps-proxy/annotations/{id}` → 200；
   - 不存在 → 404（上游语义）。
4. 发布前端制品 `openbase-ui/dist`（v1.6.0）。
5. 打开 `/portrait/dps/annotations?view=review`，选中一条记录：
   - 「审核对照」展示字段/证据；
   - 有审核人/意见时展示「审核结论」。

## 3. 构建与验证

| 检查 | 结果 |
|---|---|
| 代理定向用例 | 4 passed |
| 前端新增/回归 spec | 15 passed（`dps-backend-v160` + `dps-ui-v1410`） |
| `npm run build`（vue-tsc + vite） | 成功，dist 生成 |
| 后端全量回归 | 见《OpenBase-测试报告-v1.6.0》 |

## 4. 监控

- 代理沿用 `proxy` 上游观测与 request_id 日志。
- 关注 `/dps-proxy/annotations/{id}` 的 404 比例（可反映 DPS 未升级或数据缺失）。

## 5. 回滚

| 场景 | 操作 | 影响 |
|---|---|---|
| 前端异常 | 回退 dist 至 1.5.0 | 审核使用队列摘要，可用 |
| 后端异常 | 回退代码至 1.5.0 | 详情 404，前端回退 |
| DPS 异常 | 回退 DPS 2.14.0 | 同上 |

无数据回滚需求（全链路无写库副作用）。

## 6. 上线顺序

**DPS 2.15.0 → OpenBase 后端 1.6.0 → 前端 1.6.0**；任一层未就绪时前端自动回退，不阻断审核。
