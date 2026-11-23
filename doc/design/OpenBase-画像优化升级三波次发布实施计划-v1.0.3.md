# OpenBase 画像优化升级三波次发布实施计划

| 项 | 内容 |
|---|---|
| 文档编号 | OB-RELEASE-PORTRAIT-WAVES |
| 版本 | v1.0.4 |
| 状态 | [Review] |
| 上游文档 | 《画像优化升级实施方案 v1.0.3》《画像命名与数据链路一体化升级方案 v1.3.0》《画像 P0 前置评估报告 v1.1.0》《社区矫正对象画像模板与标注模板设计 v2.0.0》《社区矫正画像标签字典 v1.0.0》 |
| 发布列车 | 2.18.x（A）→ 2.19.0（B）→ 2.20.0（C） |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-22 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-22 | 首次编制：波次 A/B/C 的任务分解、门禁、发布清单、回滚与依赖 | AI 编码代理 |
| v1.0.1 | 2026-11-23 | 修正 C-03：复用现有 `profile_type='business'`，不新增 `profile_family` | AI 编码代理 |
| v1.0.2 | 2026-11-23 | 同步六维标签体系：模板种子 1 主 + 9 子、标注 8 个、标签 118 项；新增教育帮扶/心理特征标注交付 | AI 编码代理 |
| v1.0.3 | 2026-11-23 | 波次 B 交付：组织树/成员、数据范围、PII enforce、引入落库与标注自动生成、引入任务中心；补充 `sync_task.watermark` 偏差说明 | AI 编码代理 |
| v1.0.4 | 2026-11-23 | 波次 C 交付：进度模型与引擎、business 模板族、周期快照、dps-worker 调度与补偿熔断、审计 enforce、进度/任务中心前端；发布列车闭环 | AI 编码代理 |

## 1. 发布原则

1. **代码合并、发布分批**：同一分支、同一迁移序列，按 A/B/C 三个波次独立上线与验收。
2. **默认不变**：每波新增能力默认关闭或 `warn`，开关关闭时行为与当前生产一致。
3. **只增不删**：DDL 全部增量；不做破坏性重命名；`person_id` 语义保持不变。
4. **每波可回滚**：回滚以关开关为主，必要时保留旧读路径。
5. **门禁独立**：每波有完整测试矩阵与人工批准，不合并为一次大验收。

## 2. 波次总览

```
波次 A（2.18.x）基座与快赢
  ├─ 迁移框架 / 开关 / 统一序列化入口
  ├─ 命名与编码（前后端）
  └─ 任务表扩展（只加列）
        │
        ▼
波次 B（2.19.0）引入与权限
  ├─ 组织树 + org_member + data_scope
  ├─ PII enforce（脱敏/权限/导出/日志）
  ├─ ingest_engine 落库 + 标注自动生成
  └─ 引入任务中心（前端）
        │
        ▼
波次 C（2.20.0）进度与调度
  ├─ business_item / progress_snapshot / 进度引擎
  ├─ profile_history 周期快照 + 模板族
  ├─ dps-worker 调度与补偿
  └─ 审计 enforce + 进度/调度/审计前端
```

并行建议：A 内「命名前后端」可与「迁移框架/PII 骨架」并行；B 内「组织权限」与「引入落库」可并行；C 必须以 B 的引入数据与组织归属为前提。

## 3. 波次 A：基座与快赢（2.18.x）

### 3.1 目标

建立后续两波共用的迁移、开关、序列化入口；交付可独立感知的命名中文化与编码自动生成；不改变现有业务行为。

### 3.2 任务分解

| ID | 任务 | 改动/新增文件 | 产出与验收 |
|---|---|---|---|
| A-01 | 迁移框架 | 新增 `src/ddl/schema_v2_18_upgrade.py`；`src/database.py` 注册 | PG/SQLite 均可重复执行；`schema_version` 前进；失败可定位 |
| A-02 | 开关体系 | `src/config.py` | `DPS_PII_MODE=warn`、`DPS_DATA_SCOPE_MODE=off`、`DPS_PROGRESS_ENABLED=false`、`DPS_SCHEDULER_ENABLED=false`、`DPS_INGEST_PERSIST_ENABLED=false`、`DPS_AUDIT_RETENTION_DAYS=180` |
| A-03 | PII 规则骨架 | 新增 `src/security/pii.py`；DDL `field_classification` | 字段路径解析、L1–L4 定义、掩码函数单测通过 |
| A-04 | 统一序列化入口 | 新增 `src/security/pii_serializer.py`；接入 `routes_profiles.py`（list/detail/annotations）、`mcp_server/tools.py` | 默认透传；`warn` 模式记录「本应脱敏字段」日志，不改响应 |
| A-05 | 命名前端 | `components/common/NameCodeLabel.vue`、新增 `CodeField.vue`、`useCodeFromName.ts`、`portraitTerms.ts` | 中文主显；未填 code 可提交；冲突提示 |
| A-06 | 命名后端 | `routes_profiles.py`（模板创建/更新）；新增拼音依赖 | `code` 可选；`pypinyin` 生成；冲突 409 `BIZ_ENTITY_CODE_CONFLICT` |
| A-07 | 历史补名脚本 | 新增 `scripts/backfill_names.py` | `--dry-run` 输出待补清单；执行后 `name` 空值归零 |
| A-08 | 任务表扩展 | 迁移中追加 `portrait_calc_task`/`sync_task` 的 `trigger_source`、`locked_until` | 只加列，读写逻辑暂不依赖 |
| A-09 | 前端类型与术语 | `core/api/dps.ts`、画像页面文案 | 枚举中文化；类型编译通过 |
| A-10 | 回归与测试 | 迁移、命名、PII 规则、旧接口 | 全量测试通过；旧接口响应不变 |

### 3.3 门禁

| 项 | 标准 |
|---|---|
| 功能 | 命名与编码可用；未填 code 可建模板 |
| 兼容 | 所有开关默认值下，接口响应与现状一致 |
| 安全 | `warn` 日志能列出 `attributes_json` 中敏感字段路径 |
| 质量 | 迁移幂等；前端 build 通过；相关单测覆盖 |
| 文档 | 版本号、变更记录、接口说明同步 |

### 3.4 回滚

关闭 `DPS_PII_MODE`；命名改动保留（无破坏）；DDL 只增列，无需结构回滚。

## 4. 波次 B：引入与权限（2.19.0）

> **交付状态（2026-11-23）**：B-01~B-11 已实现并留痕，详见
> `DPS/doc/development/DPS-画像波次B引入与权限-DevLogReport-v1.0.0.md`。
> 默认开关：`DPS_PII_MODE=enforce`、`DPS_DATA_SCOPE_MODE=off`、
> `DPS_INGEST_PERSIST_ENABLED=false`；新增 `sync_task.watermark` 用于增量水位。

### 4.1 目标

让数据真正落库并自动生成标注任务；建立组织树与数据范围；PII 从 `warn` 切换到 `enforce`；交付引入任务中心。

### 4.2 任务分解

| ID | 任务 | 改动/新增文件 | 产出与验收 |
|---|---|---|---|
| B-01 | 组织树扩展 | `schema_root.py`（`organization` 加 `parent_code/path/level/sort_order`）；新增 `scripts/backfill_org_tree.py` | 组织树可查询；历史组织归属补齐 |
| B-02 | 成员与岗位 | 新增 `org_member` 表；新增 `/orgs/*` API | 一人多岗、主岗标记、有效期 |
| B-03 | 数据范围引擎 | 新增 `src/security/data_scope.py`；`routes_profiles.py` 列表/搜索/统计/导出 | `self/org/org_subtree/all` 生效；越权返回空集 |
| B-04 | 权限中间件接入 | `src/middleware/permission_middleware.py` | 身份 `org_code` + 角色推导范围；`warn` 只记录不拦截 |
| B-05 | PII enforce | `config.py` 默认切换；`pii_serializer.py`；导出与错误行 | L3 掩码、L4 剔除；`dps:pii:view` 才见明文；日志无 PII |
| B-06 | 引入引擎 | 新增 `src/engines/ingest_engine.py`；`import_task` 表 | 预览/执行/幂等 upsert；错误行可定位 |
| B-07 | 批量与数据源改造 | `batch_engine.py`、`datasource_engine.py`、`sync_task` | 真实落库；增量水位；失败可重试 |
| B-08 | 标注自动生成 | `annotation_template_engine.py`；`annotation` 加 `generated_by/ingest_batch_id` | 引入后按模板生成 `pending` 任务，不自动通过 |
| B-09 | 引入前端 | 新增 `IngestTasksView.vue`、`TaskDetailView.vue`、`MappingTable.vue` | 三 Tab、向导四步、错误 CSV（脱敏） |
| B-10 | 权限与掩码前端 | 新增 `OrgTreeSelect.vue`、`PiiMaskedField.vue`；`PortraitList.vue` | 范围切换、掩码展示、越权空态 |
| B-11 | 测试 | 组织矩阵、导入幂等、PII、租户隔离 | 见 §6 门禁 |

### 4.3 门禁

| 项 | 标准 |
|---|---|
| 功能 | 导入/同步落库；标注任务自动生成；组织范围生效 |
| 安全 | 敏感字段默认掩码；导出脱敏；跨租户不可见 |
| 一致 | 引入幂等（重复批次不重复写）；任务状态可追踪 |
| 兼容 | `data_scope=off` 时行为回退到现状 |
| 文档 | API 契约、错误码、权限码同步 |

### 4.4 回滚

`DPS_DATA_SCOPE_MODE=off`、`DPS_PII_MODE=warn`、`DPS_INGEST_PERSIST_ENABLED=false`；引入任务表保留但停止写入。

## 5. 波次 C：进度与调度（2.20.0）

> **交付状态（2026-11-23）**：C-01~C-10 已实现并留痕，详见
> `DPS/doc/development/DPS-画像波次C进度与调度-DevLogReport-v1.0.0.md`。
> 默认开关：`DPS_PROGRESS_ENABLED=false`、`DPS_SCHEDULER_ENABLED=false`；
> 新增 `worker_heartbeat` 与 `scripts/service-orchestrator.ps1`。
> 偏差：任务中心第三页签取「审计日志」（画像计算任务上游无列表接口，不新增未规划端点）。

### 5.1 目标

交付业务进度画像与周期快照；建立常驻调度与任务补偿；审计覆盖读取/导出/删除；完成两类画像并行的生产闭环。

### 5.2 任务分解

| ID | 任务 | 改动/新增文件 | 产出与验收 |
|---|---|---|---|
| C-01 | 进度模型 | `schema_v2_20_upgrade.py`：`business_item`、`progress_snapshot` | 事项可入库、周期键唯一 |
| C-02 | 进度引擎 | 新增 `src/engines/progress_engine.py` | 责任人映射、日/周聚合、按时率/逾期/质量/工作量 |
| C-03 | 模板族 | 复用 `portrait_template.profile_type='business'`；业务进度模板种子 | 两类画像筛选与计算互不干扰 |
| C-04 | 周期快照 | `profile_history` 加 `period_type/period_key/snapshot_type/template_code` | 每次计算写快照；趋势/对比可查 |
| C-05 | 调度 worker | 新增 `src/worker/scheduler.py`；`scripts/service-orchestrator.ps1` 注册 `dps-worker`；`datasource_schedule` 表 | advisory lock + 心跳；cron/interval 生效 |
| C-06 | 补偿与熔断 | `portrait_calc_task` 重领逻辑 | 过期任务回队；连续失败自动停用 |
| C-07 | 审计 enforce | `audit_log_engine.py`；`/audit/logs`；保留期任务 | 读取/导出/删除/范围变更全审计 |
| C-08 | 进度前端 | 新增 `ProgressTrend.vue`、`BusinessItemTable.vue`；`PortraitDetail.vue` 页签 | 趋势图、逾期、工作量可见 |
| C-09 | 任务中心与调度前端 | 新增 `TaskCenterView.vue`、`ScheduleEditor.vue`、`CronInput.vue` | 三类任务可查可重试；未来 5 次预览 |
| C-10 | 测试 | 聚合、快照、cron、重启续跑、审计完整性 | 见 §6 门禁 |

### 5.3 门禁

| 项 | 标准 |
|---|---|
| 功能 | 进度画像可算、趋势可看；定时任务按 cron 触发 |
| 可靠 | 重启后续跑；重复触发幂等；连续失败熔断可见 |
| 安全 | 审计覆盖读取/导出/删除；敏感字段仍按 B 波规则 |
| 性能 | 试点组织（1–2 类事项）计算时延可接受，压测报告留痕 |
| 文档 | 运维手册：worker 启停、心跳、熔断恢复、回滚 |

### 5.4 回滚

`DPS_PROGRESS_ENABLED=false`、`DPS_SCHEDULER_ENABLED=false`；停止 worker 不影响 API；进度表保留不删。

## 6. 门禁矩阵（每波通用）

| 维度 | 必须通过 |
|---|---|
| 功能 | 本波任务表全部完成，验收用例通过 |
| 回归 | 全量后端测试 + 前端 build + 相关 E2E |
| 安全 | 越权、脱敏、日志、导出四类用例 |
| 迁移 | PG/SQLite 重复执行；旧库升级演练 |
| 兼容 | 开关关闭时行为与上一版本一致 |
| 留痕 | 版本号、修订历史、测试报告、证据文件 |
| 推送 | origin / backup / github 三远程 |

## 7. 每波发布清单

1. 迁移在数据库副本上演练（记录耗时与锁情况）。
2. 确认默认开关值与本计划一致。
3. 部署 API 与前端，验证只读接口与登录。
4. 冒烟：列表、详情、模板、标注、任务中心。
5. 灰度 1 个租户开启本波开关，观察错误率与延迟。
6. 全量开启或保持 `warn`（按波次）。
7. 回滚演练：关开关 → 验证行为回退。
8. 更新台账：版本、变更、已知问题、回滚入口。

## 8. 依赖与并行

| 关系 | 说明 |
|---|---|
| A → B | B 复用 A 的序列化入口、开关、任务列 |
| A → C | C 复用 A 的迁移序列与任务列 |
| B → C | C 的进度依赖 B 的引入数据与组织归属 |
| A-05/A-06 并行 | 命名前后端可同时推进 |
| B-01/B-06 并行 | 组织权限与引入落库互不阻塞 |
| C-05 依赖 C-01/C-02 | 调度需有可执行任务体 |

## 9. 风险与回滚演练

| 风险 | 波次 | 处置 |
|---|---|---|
| 迁移锁表 | A/B/C | 低峰执行；先副本演练；大表加列使用轻量 DDL |
| 脱敏误伤 | B | 先 `warn` 观察一周；按字段分级逐步 `enforce` |
| 组织归属缺失 | B | 回填脚本 + 未归属清单；默认归到最近有效组织并标注 |
| 引入脏数据 | B | 校验规则 + 隔离区；`dry_run` 预览 |
| 进度口径分歧 | C | 口径字典先行；试点 1–2 类事项再推广 |
| 调度重复执行 | C | advisory lock + `locked_until` + 幂等键 |
| 审计膨胀 | C | 保留期任务 + 分区/归档 |

回滚统一原则：**先关开关，再停 worker，最后才考虑数据修复**；DDL 不回退。

## 10. 附录：与实施方案批次映射

| 实施方案批次 | 本计划波次 |
|---|---|
| 批次 0 基座与开关 | A-01 ~ A-04 |
| 批次 1 PII | A-03/A-04（骨架）+ B-05（enforce） |
| 批次 2 组织权限 | B-01 ~ B-04 |
| 批次 3 业务进度 | C-01 ~ C-04 |
| 批次 4 审计 | C-07 |
| 批次 5 命名与引入 | A-05 ~ A-07 + B-06 ~ B-09 |
| 批次 6 调度补偿 | C-05 ~ C-06 |
