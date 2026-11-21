# OpenBase-部署与运维报告-v1.8.0

## 文档信息

| 项 | 内容 |
|---|---|
| 文档编号 | OpenBase-OPS-v1.8.0 |
| 版本 | v1.0.0 |
| 状态 | [Ready]（2026-11-21） |
| 发布组件 | DPS 2.16.0、OpenBase 1.7.0、openbase-ui 1.8.0 |
| 依据 | 《OpenBase-测试报告-v1.8.0》 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | 运维工程师 | 首版：发布内容、顺序、验证与回滚 |

## 1. 发布内容

| 组件 | 变更 |
|---|---|
| DPS 2.16.0 | 模板筛选参数、标注统计端点、审核人/级数过滤、领取端点、权限动作覆盖 |
| OpenBase 1.7.0 | 代理新增 `GET /annotations/stats`、`POST /annotations/{id}/claim`；模板列表参数透传 |
| openbase-ui 1.8.0 | 模板中心服务端筛选、工作台 KPI、只看我的/级数/归属列/领取 |

## 2. 发布顺序（必须）

1. **DPS 2.16.0** 先上线（新端点与新参数依赖）。
2. **OpenBase 1.7.0** 上线（代理转发新端点）。
3. **openbase-ui 1.8.0** 发布静态资源。
4. 反向回滚时顺序相反：前端 → OpenBase → DPS。

> 混部兼容：旧 DPS 会忽略未知参数，前端降级为全量（不报错）；但 `/annotations/stats` 与 `/claim` 在旧 DPS 会 404，前端已做 KPI 静默与按钮错误提示。

## 3. 配置与依赖

| 项 | 说明 |
|---|---|
| 数据库迁移 | **无**（复用既有 `annotation.reviewer_id/review_level` 列） |
| 新增环境变量 | 无 |
| 权限点 | 无新增；`/claim` 复用 `annotation_template:update` |
| 代理上游 | `OPENBASE_DPS_UPSTREAM_BASE` 指向 DPS 2.16.0 |

## 4. 部署后验证

| 检查 | 命令/操作 | 期望 |
|---|---|---|
| DPS 健康 | `GET /health` | 200 |
| 模板筛选 | `GET /api/v2/portrait/templates?keyword=风险&template_kind=composite` | 仅命中匹配项；非法 kind → 400 |
| 统计 | `GET /api/v2/portrait/annotations/stats?group_by=status` | `{group_by,total,items}` |
| 领取 | `POST /api/v2/portrait/annotations/{id}/claim` | 200；重复 200 `already=true`；他人已领 409 |
| 代理 | 同路径替换前缀 `/api/v1/dps-proxy` | 结构 `{code,message,data,timestamp}` |
| 前端 | 模板中心筛选、审核收件箱「只看我的」与领取 | 结果与 URL 参数一致；KPI 正常 |

## 5. 监控与告警

- 关注 `dps_proxy` 5xx/502 比例与上游超时；新端点错误沿用既有归一化。
- 领取 409 属业务冲突，不告警；401/404 峰值需排查身份注入与租户映射。
- 统计端点失败仅影响 KPI 展示，不触发业务告警。

## 6. 回滚方案

| 层级 | 操作 | 影响 |
|---|---|---|
| 前端 | 回退至 1.7.0 静态资源 | 恢复本地过滤与无 KPI/领取入口 |
| OpenBase | 回退至 1.6.0 | 新端点 404；既有代理不变 |
| DPS | 回退至 2.15.0 | 未知参数被忽略；新端点不可用 |

数据层无需回滚（仅写既有 `reviewer_id` 列）。

## 7. 结论

测试报告全部通过，发布顺序与混部降级明确，具备上线条件。
