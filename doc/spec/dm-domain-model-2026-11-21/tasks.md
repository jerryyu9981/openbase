# Tasks：后端 T-DM-01~06 实施任务清单

| 项 | 内容 |
|---|---|
| 文档编号 | OpenBase-TASKS-DM-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | **[Approved] 执行中** |
| 依据 | `doc/spec/dm-domain-model-2026-11-21/spec.md` |
| 执行纪律 | 顺序执行；每项先写失败用例（RED）再实现（GREEN）；单轮连续推进至全量验证与提交推送 |

## 阶段 A：测试与开关基线

- [x] A1 新增 `DPS/src/tests/test_dm_domain_model_v2_17.py`，先写 T-DM-01~06 全部失败用例
- [x] A2 `DPS/src/config.py` 增加 6 个配置项，版本升 2.17.0
- [x] A3 运行新增用例确认 RED

## 阶段 B：T-DM-01 采集门禁

- [x] B1 `validate_annotation_submission` 增加父模板 active 校验（受开关控制）
- [x] B2 `TemplateEngine.count_active_annotation_templates` 新增
- [x] B3 `_set_portrait_template_status` 停用响应追加 `affected_annotation_templates`、`parent_gate_enforced`
- [x] B4 用例转 GREEN：父模板 inactive 提交 400；开关关闭放行；停用返回引用数

## 阶段 C：T-DM-03 绑定单一事实源

- [x] C1 `check_binding_rule_alignment` 与 `collect_binding_alignment`
- [x] C2 create/update 接入 warn/reject 策略，返回 `warnings`
- [x] C3 预检追加 `binding_rule_alignment`
- [x] C4 用例转 GREEN：一致通过、不一致 warn、reject 400

## 阶段 D：T-DM-06 维度词表校验

- [x] D1 `collect_dimension_vocabulary_gaps` 新增
- [x] D2 create/update 接入 `off|warn|reject`
- [x] D3 预检追加 `dimension_vocabulary_gaps`
- [x] D4 用例转 GREEN：命中通过、缺口 warn、reject 400、词表为空不阻断

## 阶段 E：T-DM-02 版本对齐与 stale

- [x] E1 命名空间写入 `template_version`
- [x] E2 新增 `_mark_namespace_stale`
- [x] E3 详情/外部 ID 查询返回 stale 三元组
- [x] E4 列表支持 `template_code` + `stale`（缺 template_code 时 400）
- [x] E5 用例转 GREEN：版本不一致 stale=true、缺版本/缺模板分支

## 阶段 F：T-DM-04 来源优先级

- [x] F1 `pick_preferred_tags` 支持 `precedence`
- [x] F2 `_get_existing_tags` / `_get_tags_by_dimension` / `calculate_portrait` 透传
- [x] F3 `_execute_calc` 读取并校验 `dimension_config.source_precedence`，payload 回显
- [x] F4 用例转 GREEN：自定义顺序生效；未配置行为与现状一致

## 阶段 G：T-DM-05 自动重算

- [x] G1 `portrait_calc_task` 新增 `retry_count`（PG/SQLite）
- [x] G2 新增 `enqueue_tag_change_recalc`
- [x] G3 `_run_calc_task` 失败重试上限与 ERROR 告警
- [x] G4 `_apply_annotation_review` 接入触发与响应 `recalc`；单条/批量端点透传 `BackgroundTasks`
- [x] G5 用例转 GREEN：同桶合并、开关关闭不入队、审核联动入队

## 阶段 H：跨仓与前端

- [x] H1 `dps_proxy` 列表代理透传 `template_code` / `stale`
- [x] H2 新增 `OpenBase/tests/test_dps_proxy_list_stale.py`（3 passed）
- [x] H3 `PortraitList.vue` stale 列与「仅看过期」筛选
- [x] H4 `DpsTemplateListView.vue` 停用影响面提示
- [x] H5 前端两个新 spec 通过（3 passed）、相关回归 25 passed、`npm run build` 通过

## 阶段 I：全量验证

- [x] I1 DPS 定向用例通过（22 passed）
- [x] I2 DPS 全量：2117 passed；9 failed / 69 errors 均来自工作区既有未提交改动与 Windows `./dps.db` 文件锁（与本任务无关，详见测试报告）
- [x] I3 OpenBase 代理定向＋回归通过（52 passed；全量在既有 E2E 用例处挂起，与本任务无关）
- [x] I4 前端 vitest 相关用例通过＋build 通过
- [x] I5 静态检查（`ruff --select E9,F`）0 错误

## 阶段 J：文档与交付

- [x] J1 设计文档升版 v1.1.1，T-DM-01~06 标「已实施」并补修订历史
- [x] J2 产出开发记录、测试报告、部署报告
- [x] J3 DPS 提交：按人工裁定**暂缓**（工作区存在并行「模板目录 v1」约 800 行未提交改动，与本任务交织，避免混提）
- [x] J4 OpenBase 提交：`e98e027 feat(dps-proxy|portrait): 数据画像领域模型治理跨仓适配 (v1.8.0)`
- [x] J5 OpenBase 已推送 origin/backup/github 三远程；DPS 按裁定暂缓推送

## 完成判据

- 六项任务对应用例全部通过，默认配置下存量行为无回归；
- 所有开关可按 spec §7 回滚；
- 文档、版本、提交与三远程推送一致。
