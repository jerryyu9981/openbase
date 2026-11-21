# OpenBase-数据画像领域模型治理-部署与运维报告-v1.0.0

| 项 | 内容 |
|---|---|
| 文档编号 | OpenBase-OPS-DM-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | **[Final]** |
| 日期 | 2026-11-21 |
| 适用版本 | DPS v2.17.0；OpenBase v1.8.0；openbase-ui v1.9.1 |
| 关联 | `doc/development/OpenBase-数据画像领域模型治理-DevLogReport-v1.0.0.md`、`doc/test/OpenBase-数据画像领域模型治理-测试报告-v1.0.0.md` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-21 | BE/FE | 首版：发布内容、配置矩阵、部署步骤、验证与回滚 |

## 1. 发布内容

- DPS 2.17.0：T-DM-01~06 六项治理能力，新增 `portrait_calc_task.retry_count`。
- OpenBase 1.8.0：`dps-proxy` 画像列表透传 `template_code`/`stale`。
- openbase-ui 1.9.1：画像结果页口径状态列/筛选；画像模板停用影响面提示。

## 2. 配置矩阵

| 变量 | 默认 | 说明 | 回滚值 |
|---|---|---|---|
| `DPS_ENFORCE_ACTIVE_PARENT` | `true` | 父画像模板停用后拒绝新标注提交 | `false` |
| `DPS_TAG_BINDING_CONSISTENCY` | `warn` | `tag_bindings` 一致性策略（off/warn/reject） | `warn`/`off` |
| `DPS_DIMENSION_VOCABULARY_CHECK` | `warn` | 维度词表跨层校验策略（off/warn/reject） | `warn`/`off` |
| `DPS_TAG_CHANGE_RECALC_ENABLED` | `true` | 标签变更自动重算 | `false` |
| `DPS_TAG_CHANGE_RECALC_DEBOUNCE_SECONDS` | `5` | 同人员+模板事件合并窗口 | 按需调大 |
| `DPS_TAG_CHANGE_RECALC_MAX_RETRIES` | `2` | 计算任务失败重试上限 | 按需调小 |

## 3. 部署步骤

1. 备份数据库（重点：`portrait_template`、`annotation_template`、`profile`、`profile_tag`、`portrait_calc_task`）。
2. 执行 DDL 幂等迁移：确保 `portrait_calc_task.retry_count` 存在（PG：`ADD COLUMN IF NOT EXISTS`；SQLite：`PRAGMA table_info` 判存后 `ALTER TABLE`）。
3. 部署 DPS 2.17.0，先以 `DPS_TAG_BINDING_CONSISTENCY=warn`、`DPS_DIMENSION_VOCABULARY_CHECK=warn` 灰度。
4. 部署 OpenBase 1.8.0 与 openbase-ui 1.9.1。
5. 冒烟：
   - 停用一个无引用画像模板 → 响应 `affected_annotation_templates=0`；
   - 停用有引用画像模板 → 响应受影响数 > 0，且对应标注模板提交返回 400；
   - 画像详情带 `template_code` → 返回 `stale` 字段；
   - 画像列表 `template_code+stale=true` → 仅返回过期画像；
   - 审核通过一条标注 → 响应 `recalc.enqueued=true`，任务最终 `succeeded`。

## 4. 发布后验证

| 项 | 通过标准 |
|---|---|
| 采集门禁 | 父模板 inactive 时新提交 400；历史标注可读 |
| stale | 模板升级后既有画像 stale=true；重算后 false |
| 一致性策略 | warn 模式保存成功且返回 warnings；reject 模式 400 |
| 自动重算 | 同人员+模板 5s 内重复事件合并为 1 个任务 |
| 前端 | 「仅看过期」请求携带 `template_code`+`stale`；停用提示受影响数 |

## 5. 监控与告警

- 日志检索：`标签变更重算任务入队`、`画像异步计算失败`、`标签联动失败明细`。
- 关注指标：`portrait_calc_task` 中 `failed` 数量、`retry_count>0` 比例、任务积压（`pending` 时长）。
- 告警阈值建议：5 分钟内 `failed` ≥ 5 或 `pending` 超 10 分钟 → 告警。

## 6. 回滚

1. 关闭自动重算：`DPS_TAG_CHANGE_RECALC_ENABLED=false`。
2. 关闭门禁：`DPS_ENFORCE_ACTIVE_PARENT=false`。
3. 一致性/词表降级：`warn` 或 `off`。
4. 代码回滚至 DPS 2.16.0 / OpenBase 1.7.0 / UI 1.9.0；`retry_count` 列可保留（有默认值，向后兼容）。
