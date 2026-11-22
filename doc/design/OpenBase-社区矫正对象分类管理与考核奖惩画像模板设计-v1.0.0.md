# OpenBase 社区矫正对象分类管理与考核奖惩画像模板设计

| 项 | 内容 |
|---|---|
| 文档编号 | OB-TPL-SQJZ-001 |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 依据文件 | 《广东省司法厅关于社区矫正对象分类管理及考核奖惩规定》（粤司办〔2022〕97 号，2022-03-25） |
| 上游设计 | 《画像命名与数据链路一体化升级方案 v1.1.0》《画像优化升级实施方案 v1.0.1》 |
| 适用范围 | 社区矫正对象的人物画像与业务进度画像；DPS 模板/标注/标签种子数据 |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 依据 5 章 33 条抽取：1 个复合模板、8 个子模板、6 个标注模板、63 个标签、判定规则与追溯矩阵 | AI 编码代理 |

## 1. 设计说明

1. 本设计**只做条款结构化**，不新增或解释政策；规则冲突时以原文为准。
2. 评分权重、等级阈值为**系统建议值**，需业务部门确认后固化。
3. 姓名、身份证、联系方式、保证人等按 PII 分级处理（L3 掩码、L4 剔除）。
4. 模板与标签全部进入 DPS 现有模型，不新建模板体系：
   - `portrait_template`：`profile_type='business'`，`subject_type='person'`；
   - `template_kind='composite'` 为主模板，`component` 为子模板；
   - `portrait_template_component` 挂载子模板与权重；
   - `annotation_template.field_schema` 定义标注字段；
   - `tag_definition` / `tag_value` 定义标签；
   - `portrait_extension` 存事项、周期、证据等子数据。

## 2. 业务对象与画像目标

| 项 | 内容 |
|---|---|
| 画像对象 | 社区矫正对象（person） |
| 管理主体 | 县级社区矫正机构（组织实施）、受委托司法所（日常工作） |
| 核心问题 | 对象处于什么管理类别、考核是否合格、有无奖惩、风险如何、教育帮扶是否到位、矫正成效如何 |
| 画像用途 | 分类调整、考核奖惩、矫正方案调整、风险预警、期满评估 |
| 更新频率 | 事件触发（入矫/分类/奖惩/考核）+ 每日同步 + 每考核周期（3 个月）结算 |

## 3. 模板体系总览

| 层级 | 模板编码 | 中文名 | template_kind | 权重 | 说明 |
|---|---|---|---|---|---|
| 主模板 | `sqjz_object_composite` | 社区矫正对象综合画像 | composite | 100 | 汇总 8 个子模板，输出总分与等级 |
| 子模板 | `sqjz_basic` | 基础信息 | component | 0（必挂） | 身份、矫正类型、期限、执行地 |
| 子模板 | `sqjz_compliance` | 遵规报告 | component | 20 | 报告、核查、外出、变更报告 |
| 子模板 | `sqjz_assessment` | 考核 | component | 25 | 周期扣分、结论、审批 |
| 子模板 | `sqjz_reward_punish` | 奖惩 | component | 20 | 训诫、警告、治安、表扬、撤销 |
| 子模板 | `sqjz_education` | 教育帮扶 | component | 15 | 思想汇报、个别/集体教育、公益 |
| 子模板 | `sqjz_risk` | 风险管控 | component | 10 | 风险等级、特殊管理、脱管 |
| 子模板 | `sqjz_outcome` | 矫正成效 | component | 10 | 悔改表现、趋势、期满评估 |
| 子模板 | `sqjz_classification` | 分类管理 | component | 0（派生） | 管理类别与措施，作为画像结论输出 |

## 4. 主模板设计

### 4.1 维度与权重

| 维度 | 来源子模板 | 权重 | 评分口径 |
|---|---|---|---|
| 遵规报告 | `sqjz_compliance` | 20 | 报告/核查/外出/变更合规率 |
| 考核结果 | `sqjz_assessment` | 25 | 周期扣分与结论 |
| 奖惩情况 | `sqjz_reward_punish` | 20 | 训诫/警告/治安/表扬 |
| 教育帮扶 | `sqjz_education` | 15 | 教育完成率与公益时长 |
| 风险管控 | `sqjz_risk` | 10 | 风险等级与特殊管理 |
| 矫正成效 | `sqjz_outcome` | 10 | 悔改表现、连续周期表现、趋势 |

### 4.2 评分规则（建议值，可配置）

| 维度 | 规则 |
|---|---|
| 遵规报告 | 基础 100；每类违规按扣分档 -5/-10/-15；外出违规 -20；下限 0 |
| 考核结果 | 合格 100；不合格 40；特殊管理考核仅记录不计分 |
| 奖惩情况 | 基础 100；每次训诫 -15、警告 -30、治安处罚 -50；每次表扬 +10；上限 120，按 100 归一 |
| 教育帮扶 | 完成率 ×100；当月教育与公益合计 ≥12 小时 +10；未达标按比例扣减 |
| 风险管控 | 低 100；中 70；高 40；特殊管理 30 |
| 矫正成效 | 连续两周期无扣分 100；单周期良好 80；有反复 60；不合格周期 40 |

综合分 = Σ（维度分 × 权重）/100；等级：A ≥85、B 70–84、C 55–69、D <55。

### 4.3 主模板输出字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `overall_score` | number | 综合分 |
| `grade` | enum A/B/C/D | 画像等级 |
| `management_category` | enum 普通/严格/特殊 | 当前管理类别 |
| `cycle_result` | enum 合格/不合格 | 最近考核结论 |
| `deduction_total` | number | 最近周期累计扣分 |
| `admonition_count` / `warning_count` | number | 训诫/警告次数 |
| `commendation_count` | number | 表扬次数 |
| `risk_level` | enum 高/中/低 | 风险等级 |
| `education_completion` | number | 教育完成率 |
| `trend` | enum 上升/持平/下降 | 近三周期趋势 |

`attributes_schema` 与 `tag_bindings` 直接引用第 8 节标签编码。

## 5. 子模板字段设计

### 5.1 基础信息 `sqjz_basic`

| 字段 | 类型 | 必填 | 说明 | 条款 |
|---|---|---|---|---|
| `name` | string(PII) | 是 | 姓名 | — |
| `id_card` | string(PII L4) | 是 | 身份证号 | — |
| `gender` / `birth_date` | enum/date | 是 | 性别/出生日期 | — |
| `household` / `residence` | string | 是 | 户籍地/居住地 | 十七(一) |
| `contact` | string(PII) | 是 | 联系方式 | 十七(七) |
| `crime_type` | string | 是 | 犯罪类型 | 二 |
| `sentence` | string | 是 | 原判刑罚 | 二十六 |
| `correction_type` | enum | 是 | 管制/缓刑/假释/暂予监外执行 | 二十六 |
| `registration_date` | date | 是 | 登记接收日期 | 十六 |
| `correction_start` / `correction_end` | date | 是 | 矫正起止 | — |
| `execution_location` | string | 是 | 执行地 | 十九 |
| `guarantor` / `guardian` | string(PII) | 否 | 保证人/监护人 | 十四 |
| `is_minor` | bool | 是 | 是否未成年 | 二十八 |
| `special_group` | multi-enum | 否 | 年老/体弱/残疾/疾病/怀孕/就读 | 十四 |

### 5.2 遵规报告 `sqjz_compliance`

| 字段 | 类型 | 说明 | 条款 |
|---|---|---|---|
| `report_phone_freq` | enum | 每周1/每周2/每日1 | 八(一)/九(一)/十(一) |
| `report_inperson_freq` | enum | 每月1/每月2/每周1 | 八(二)/九(二)/十(二) |
| `thought_report_count` | number | 周期内书面思想汇报次数 | 八(三) |
| `info_verification` | bool/enum | 是否接受信息化核查及频次 | 八(七)/十二 |
| `outing_approval` | enum | 允许/从严/不批准 | 八(八)/九(八)/十(八) |
| `change_reports` | array | 联系方式/居所/工作/家庭变故/外出返回 | 十七(七)-(十一) |
| `violation_items` | array | 违规项与次数 | 十七 |
| `compliance_rate` | number | 合规率（系统计算） | — |

### 5.3 考核 `sqjz_assessment`

| 字段 | 类型 | 说明 | 条款 |
|---|---|---|---|
| `cycle_key` | string | 考核周期（3 个月） | 十六 |
| `cycle_start` / `cycle_end` | date | 首周期起止规则 | 十六 |
| `deduction_total` | number | 周期累计扣分（不跨周期） | 十六/十七 |
| `deduction_items` | array | 扣分项、分值、日期、证据 | 十七 |
| `deduction_authority` | enum | 1 分：工作人员；2–3 分：司法所长 | 十八 |
| `assessment_date` | date | 周期结束后 5 个工作日内 | 十六 |
| `cycle_result` | enum | 合格/不合格 | 二十 |
| `unqualify_reason` | multi-enum | 扣分≥10/训诫≥2/警告/治安处罚 | 二十 |
| `cross_cycle_carry` | bool | 是否跨周期累计（应为 false） | 十六 |
| `outside_transfer` | bool | 是否省外转入；原奖惩累计 | 十九 |

### 5.4 奖惩 `sqjz_reward_punish`

| 字段 | 类型 | 说明 | 条款 |
|---|---|---|---|
| `admonition_count` | number | 训诫次数 | 二十一/二十四 |
| `warning_count` | number | 警告次数 | 二十二/二十五 |
| `public_security_count` | number | 治安管理处罚次数 | 二十六 |
| `commendation_count` | number | 表扬次数 | 二十三 |
| `commendation_basis` | enum | 六个月条件/突出表现/表现突出 | 二十三 |
| `outstanding` | bool | 连续两周期无扣分且每月教育+公益≥12h | 二十三 |
| `direct_legal_handling` | bool | 达到直接处理情形，不再扣分 | 二十一 |
| `revoked` / `revoke_reason` | bool/enum | 撤销及原因 | 三十 |
| `objection_status` | enum | 无/待处理/已处理/检察院 | 二十七 |
| `public_notice` | string | 公示 5 日；未成年不公示 | 五/二十八 |
| `commutation_basis` | bool | 表扬作为减刑建议依据 | 二十三 |

### 5.5 教育帮扶 `sqjz_education`

| 字段 | 类型 | 说明 | 条款 |
|---|---|---|---|
| `individual_education_count` | number | 个别教育次数（按类别） | 八(四)/九(四)/十(四) |
| `collective_education_count` | number | 集体教育次数（每月≥1） | 八(六) |
| `public_welfare_hours` | number | 公益活动时长 | 十三/十五 |
| `education_completion` | number | 教育完成率 | 八(六) |
| `adjustment` | bool/enum | 报告/教育调整方式 | 十四 |
| `adjustment_approved` | bool | 本人申请+证明+审批 | 十四 |
| `external_counted` | bool | 外部教育/公益活动计入 | 十五 |

### 5.6 风险管控 `sqjz_risk`

| 字段 | 类型 | 说明 | 条款 |
|---|---|---|---|
| `risk_level` | enum | 高/中/低 | 二/十 |
| `risk_type` | multi-enum | 国家安全/公共秩序/社会稳定/脱管/再犯 | 十 |
| `special_reason` | enum | 特殊管理情形 | 十 |
| `special_deadline` | date | 批准确定的时限 | 十 |
| `escape_days` | number | 脱管天数（<10/10–20/20–30/>30） | 二十四/二十五/二十六 |
| `risk_review_date` | date | 复核日期 | — |

### 5.7 矫正成效 `sqjz_outcome`

| 字段 | 类型 | 说明 | 条款 |
|---|---|---|---|
| `repentance` | enum | 认罪悔罪表现 | 二十三 |
| `stage` | enum | 入矫/中期/期满 | — |
| `consecutive_good_cycles` | number | 连续良好周期数 | 二十三 |
| `commendation_ready` | bool | 是否满足表扬条件 | 二十三 |
| `exit_assessment` | enum | 期满评估结论 | — |
| `trend` | enum | 上升/持平/下降 | — |

### 5.8 分类管理 `sqjz_classification`

| 字段 | 类型 | 说明 | 条款 |
|---|---|---|---|
| `management_category` | enum | 普通/严格/特殊 | 七 |
| `approval_level` | enum | 县级审批/市级备案 | 七 |
| `approval_date` | date | 批准日期 | 七 |
| `basis` | multi-enum | 首周期/不合格/风险情形/调整 | 八/九/十 |
| `measures` | object | 八项措施的具体频次 | 八/九/十 |
| `adjustment_reason` | string | 调整原因 | 十一/二十九 |
| `effective_from` | date | 生效日期 | 七 |

## 6. 标注模板设计

| 模板编码 | 名称 | 绑定模板 | 触发 | 复核 |
|---|---|---|---|---|
| `ann_sqjz_classification` | 分类管理标注 | `sqjz_classification` | 入矫、考核结论、风险情形、调整审批 | 县级审批（必复核） |
| `ann_sqjz_assessment` | 考核标注 | `sqjz_assessment` | 周期结束后 5 个工作日 | 司法所长（2–3 分必复核） |
| `ann_sqjz_reward_punish` | 奖惩标注 | `sqjz_reward_punish` | 训诫/警告/表扬/治安/撤销决定 | 县级审批（必复核） |
| `ann_sqjz_risk` | 风险标注 | `sqjz_risk` | 入矫评估、风险变化、特殊管理 | 县级复核 |
| `ann_sqjz_education` | 教育帮扶标注 | `sqjz_education` | 月度教育数据、调整申请 | 司法所复核 |
| `ann_sqjz_minor` | 未成年专项标注 | `sqjz_basic`/`sqjz_assessment` | 入矫识别为未成年 | 分开考核、不公示 |

### 6.1 分类管理标注字段

| key | 标签 | 类型 | 选项/规则 | 条款 |
|---|---|---|---|---|
| `category` | 管理类别 | enum | 普通/严格/特殊 | 七 |
| `basis` | 认定依据 | multi | 首周期/不合格/风险情形/调整 | 八/九/十 |
| `approval_level` | 审批层级 | enum | 县级/市级备案 | 七 |
| `special_reason` | 特殊情形 | multi | 国家安全/公共秩序/社会稳定 | 十 |
| `special_deadline` | 特殊期限 | date | 批准时限 | 十 |
| `measures` | 措施清单 | object | 报告/当面/思想汇报/个别教育/查访/集体教育/核查/外出 | 八/九/十 |
| `evidence` | 证据材料 | file[] | 审批表/决定书 | — |

### 6.2 考核标注字段

| key | 标签 | 类型 | 选项/规则 | 条款 |
|---|---|---|---|---|
| `cycle_key` | 考核周期 | string | 3 个月周期 | 十六 |
| `deduction_items` | 扣分项 | array | 19 项，分值 1–3 | 十七 |
| `deduction_total` | 累计扣分 | number | ≤周期上限，不跨周期 | 十六 |
| `authority` | 扣分审批 | enum | 工作人员(1分)/司法所长(2–3分) | 十八 |
| `result` | 周期结论 | enum | 合格/不合格 | 二十 |
| `unqualify_reason` | 不合格原因 | multi | 扣分≥10/训诫≥2/警告/治安 | 二十 |
| `assessment_date` | 考核日期 | date | 周期后 5 个工作日内 | 十六 |

### 6.3 奖惩标注字段

| key | 标签 | 类型 | 选项/规则 | 条款 |
|---|---|---|---|---|
| `type` | 奖惩类型 | enum | 训诫/警告/治安处罚/表扬/撤销 | 二十一–二十六/三十 |
| `trigger` | 触发条件 | multi | 扣4分/两次训诫后扣3分/脱管天数/突出表现 | 二十一/二十二/二十四–二十六 |
| `count` | 次数 | number | 周期/累计 | — |
| `decision_org` | 决定机关 | string | 县级社区矫正机构 | 二十四–二十六 |
| `decision_date` | 决定日期 | date | — | — |
| `public_notice` | 公示 | string | 5 日；未成年不公示 | 五/二十八 |
| `objection` | 异议 | enum | 无/待处理/已处理/检察院 | 二十七 |
| `revoke_reason` | 撤销原因 | enum | 条件不符/程序违规/材料不符 | 三十 |

### 6.4 风险标注字段

| key | 标签 | 类型 | 选项/规则 | 条款 |
|---|---|---|---|---|
| `risk_level` | 风险等级 | enum | 高/中/低 | 二 |
| `risk_type` | 风险类型 | multi | 国家安全/公共秩序/社会稳定/脱管/再犯 | 十 |
| `special_management` | 特殊管理 | bool | 批准时限内 | 十 |
| `escape_days` | 脱管天数 | number | <10/10–20/20–30/>30 | 二十四–二十六 |
| `basis` | 认定依据 | text | 事实与证据 | — |

### 6.5 教育帮扶标注字段

| key | 标签 | 类型 | 选项/规则 | 条款 |
|---|---|---|---|---|
| `individual_count` | 个别教育次数 | number | 按管理类别 | 八/九/十 |
| `collective_count` | 集体教育次数 | number | 每月≥1 | 八(六) |
| `public_welfare_hours` | 公益时长 | number | 计入规则 | 十三/十五 |
| `completion` | 完成率 | number | 0–100% | 八(六) |
| `adjustment` | 调整 | bool/enum | 申请+证明+审批 | 十四 |

### 6.6 未成年专项标注字段

| key | 标签 | 类型 | 规则 | 条款 |
|---|---|---|---|---|
| `is_minor` | 是否未成年 | bool | 入矫识别 | 二十八 |
| `separate_assessment` | 分开考核 | bool | 与成年人分别进行 | 二十八 |
| `no_public_notice` | 不公示 | bool | 考核结果不予公示 | 二十八 |

## 7. 判定规则矩阵

### 7.1 分类管理

| 条件 | 结论 | 条款 |
|---|---|---|
| 入矫第一个考核周期 | 严格管理 | 九 |
| 周期考核不合格 | 严格管理（立即） | 二十 |
| 周期考核合格且非首周期 | 可实施普通管理 | 八 |
| 可能危害国家安全/严重扰乱公共秩序/重大社会稳定影响 | 特殊管理（批准时限内，市备案） | 七/十 |
| 特殊管理对象 | 应考核，但不作为分类依据 | 二十 |
| 调整 | 司法所意见 → 县级审批；县级可直接调整 | 二十九 |

### 7.2 考核结论

| 条件 | 结论 | 条款 |
|---|---|---|
| 累计扣分 <10 且训诫 <2 次 | 合格 | 二十 |
| 累计扣分 ≥10，或训诫 ≥2 次，或警告/治安处罚 | 不合格 | 二十 |
| 扣分跨周期累计 | 不允许 | 十六 |

### 7.3 奖惩触发

| 情形 | 处置 | 条款 |
|---|---|---|
| 周期累计扣分达 4 分 | 训诫 | 二十一 |
| 训诫后再次累计达 4 分 | 再次训诫 | 二十一 |
| 2 次训诫后累计扣分 ≥3 分 | 警告 | 二十二 |
| 接受矫正 ≥6 个月且符合四项条件 | 可给予表扬 | 二十三 |
| 见义勇为/抢险救灾/帮助他人/服务社会突出 | 可表扬、调整类别 | 二十三 |
| 连续两周期无扣分且每月教育+公益 ≥12h | 表现突出，应表扬 | 二十三 |
| 脱管 <10 日/情节轻微 | 训诫 | 二十四 |
| 脱管 >10 日/情节较重 | 警告 | 二十五 |
| 脱管 >20 日未满 30 日/扰乱秩序/威胁报复 | 提请治安管理处罚 | 二十六 |
| 达到直接处理情形 | 依法处理，不再扣分 | 二十一 |
| 条件不符/程序违规/材料不符 | 撤销奖惩 | 三十 |

### 7.4 程序与时限

| 事项 | 规则 | 条款 |
|---|---|---|
| 考核周期 | 3 个月；周期后 5 个工作日内考核 | 十六 |
| 首周期 | 登记接收之日起，至次月起第三个月月底 | 十六 |
| 扣分审批 | 1 分工作人员；2–3 分司法所长 | 十八 |
| 公示 | 考核结果与奖惩公示 5 日 | 五 |
| 异议 | 县级 1 个月内处理；检察院 1 个月内答复 | 二十七 |
| 未成年 | 分开考核，结果不公示 | 二十八 |

## 8. 标签体系（63 项）

### 8.1 基础身份（14）

| 编码 | 中文名 | 类型 | 取值/规则 | 条款 |
|---|---|---|---|---|
| `sqjz_correction_type` | 矫正类型 | enum | 管制/缓刑/假释/暂予监外执行 | 二十六 |
| `sqjz_crime_type` | 犯罪类型 | string | 业务字典 | 二 |
| `sqjz_sentence` | 原判刑罚 | string | — | 二十六 |
| `sqjz_registration_date` | 登记接收日期 | date | — | 十六 |
| `sqjz_cycle_start` | 首周期起始 | date | 登记接收之日 | 十六 |
| `sqjz_cycle_end` | 首周期截止 | date | 次月起第三个月月底 | 十六 |
| `sqjz_execution_location` | 执行地 | string | — | 十九 |
| `sqjz_household` | 户籍地 | string | — | 十七(一) |
| `sqjz_residence` | 居住地 | string | — | 十七(一) |
| `sqjz_contact` | 联系方式 | string(PII) | — | 十七(七) |
| `sqjz_guarantor` | 保证人 | string(PII) | — | 十四 |
| `sqjz_is_minor` | 是否未成年 | bool | — | 二十八 |
| `sqjz_special_group` | 特殊群体 | multi | 年老/体弱/残疾/疾病/怀孕/就读 | 十四 |
| `sqjz_special_adjust` | 特殊调整 | bool | 申请+证明+审批 | 十四 |

### 8.2 分类管理（11）

| 编码 | 中文名 | 类型 | 取值/规则 | 条款 |
|---|---|---|---|---|
| `sqjz_mgmt_category` | 管理类别 | enum | 普通/严格/特殊 | 七 |
| `sqjz_mgmt_approval` | 审批层级 | enum | 县级/市级备案 | 七 |
| `sqjz_mgmt_effective` | 生效日期 | date | — | 七 |
| `sqjz_mgmt_basis` | 认定依据 | multi | 首周期/不合格/风险情形/调整 | 八/九/十 |
| `sqjz_special_reason` | 特殊情形 | multi | 国家安全/公共秩序/社会稳定 | 十 |
| `sqjz_special_deadline` | 特殊期限 | date | — | 十 |
| `sqjz_report_phone_freq` | 电话报告频次 | enum | 每周1/每周2/每日1 | 八/九/十 |
| `sqjz_report_inperson_freq` | 当面报告频次 | enum | 每月1/每月2/每周1 | 八/九/十 |
| `sqjz_outing_policy` | 外出政策 | enum | 允许/从严/不批准 | 八/九/十 |
| `sqjz_info_check_freq` | 信息化核查频次 | enum | 按类别调整 | 十二 |
| `sqjz_measure_adjustment` | 措施调整 | bool | 特殊情况/入解矫月 | 十一 |

### 8.3 考核（12）

| 编码 | 中文名 | 类型 | 取值/规则 | 条款 |
|---|---|---|---|---|
| `sqjz_cycle_key` | 考核周期 | string | 3 个月 | 十六 |
| `sqjz_deduction_total` | 累计扣分 | number | ≥0，不跨周期 | 十六 |
| `sqjz_deduction_items` | 扣分项 | array | 19 项明细 | 十七 |
| `sqjz_deduction_authority` | 扣分审批 | enum | 工作人员/司法所长 | 十八 |
| `sqjz_cycle_result` | 周期结论 | enum | 合格/不合格 | 二十 |
| `sqjz_qualify_rule` | 合格规则 | bool | 扣分<10 且训诫<2 | 二十 |
| `sqjz_unqualify_reason` | 不合格原因 | multi | 扣分≥10/训诫≥2/警告/治安 | 二十 |
| `sqjz_assessment_date` | 考核日期 | date | 周期后 5 个工作日 | 十六 |
| `sqjz_cross_cycle` | 跨周期累计 | bool | 应 false | 十六 |
| `sqjz_outside_transfer` | 省外转入 | bool | — | 十九 |
| `sqjz_prior_penalty_accum` | 原奖惩累计 | bool | 训诫/警告/治安累计 | 十九 |
| `sqjz_assessment_status` | 考核状态 | enum | 待考核/已考核/逾期 | 十六 |

### 8.4 奖惩（12）

| 编码 | 中文名 | 类型 | 取值/规则 | 条款 |
|---|---|---|---|---|
| `sqjz_admonition_count` | 训诫次数 | number | — | 二十一/二十四 |
| `sqjz_warning_count` | 警告次数 | number | — | 二十二/二十五 |
| `sqjz_public_security_count` | 治安处罚次数 | number | — | 二十六 |
| `sqjz_commendation_count` | 表扬次数 | number | — | 二十三 |
| `sqjz_commendation_basis` | 表扬依据 | enum | 六个月条件/突出表现/表现突出 | 二十三 |
| `sqjz_outstanding` | 表现突出 | bool | 连续2周期无扣分且每月≥12h | 二十三 |
| `sqjz_direct_legal` | 直接依法处理 | bool | 不再扣分 | 二十一 |
| `sqjz_revoked` | 奖惩撤销 | bool | — | 三十 |
| `sqjz_revoke_reason` | 撤销原因 | enum | 条件不符/程序违规/材料不符 | 三十 |
| `sqjz_objection_status` | 异议状态 | enum | 无/待处理/已处理/检察院 | 二十七 |
| `sqjz_public_notice` | 公示 | string | 5 日；未成年不公示 | 五/二十八 |
| `sqjz_commutation_basis` | 减刑建议依据 | bool | 表扬为主要标志 | 二十三 |

### 8.5 教育帮扶（8）

| 编码 | 中文名 | 类型 | 取值/规则 | 条款 |
|---|---|---|---|---|
| `sqjz_thought_report_count` | 思想汇报次数 | number | 每月≥1 | 八(三) |
| `sqjz_individual_edu_count` | 个别教育次数 | number | 按类别 | 八/九/十 |
| `sqjz_collective_edu_count` | 集体教育次数 | number | 每月≥1 | 八(六) |
| `sqjz_public_welfare_hours` | 公益活动时长 | number | 计入规则 | 十三/十五 |
| `sqjz_edu_completion` | 教育完成率 | number | 0–100 | 八(六) |
| `sqjz_edu_adjustment` | 教育调整 | bool/enum | 申请+审批 | 十四 |
| `sqjz_edu_adjust_approved` | 调整批准 | bool | 县级批准 | 十四 |
| `sqjz_external_counted` | 外部教育计入 | bool | 证明材料 | 十五 |

### 8.6 风险（6）

| 编码 | 中文名 | 类型 | 取值/规则 | 条款 |
|---|---|---|---|---|
| `sqjz_risk_level` | 风险等级 | enum | 高/中/低 | 二 |
| `sqjz_risk_type` | 风险类型 | multi | 国家安全/公共秩序/社会稳定/脱管/再犯 | 十 |
| `sqjz_escape_days` | 脱管天数 | number | <10/10–20/20–30/>30 | 二十四–二十六 |
| `sqjz_recidivism_risk` | 再犯风险 | enum | 高/中/低 | 二 |
| `sqjz_special_management` | 特殊管理 | bool | — | 十 |
| `sqjz_risk_review_date` | 风险复核日期 | date | — | — |

## 9. 数据来源与采集

| 数据 | 来源系统/材料 | 频率 | 责任 |
|---|---|---|---|
| 基础信息、矫正类型、期限 | 社区矫正一体化平台/入矫登记 | 事件 | 司法所 |
| 分类审批、特殊管理备案 | 县级审批表、市级备案 | 事件 | 县级机构 |
| 考核扣分 | 扣分审批表、日常台账 | 每周期 | 司法所 |
| 奖惩决定 | 训诫书、警告决定书、表扬决定书、治安处罚决定 | 事件 | 县级机构 |
| 教育学习、公益活动 | 教育台账、证明材料 | 月度 | 司法所 |
| 报告/核查/外出 | 定位核查、外出审批、报告记录 | 每日/事件 | 司法所 |
| 异议/撤销 | 异议处理记录、撤销决定 | 事件 | 县级机构 |

采集方式沿用统一管线：API/DB 同步、Excel 导入、人工补录；全部落 `import_task`/`sync_task` 并可追溯。

## 10. 与 DPS 模型映射

| 设计对象 | DPS 表/字段 |
|---|---|
| 主模板 | `portrait_template`：`code=sqjz_object_composite`、`profile_type='business'`、`subject_type='person'`、`template_kind='composite'` |
| 子模板 | `portrait_template`：`template_kind='component'`；`portrait_template_component` 挂载与权重 |
| 标注模板 | `annotation_template`：`template_code` 绑定子模板，`scenario='sqjz'`，`field_schema` 为第 6 节字段 |
| 标签 | `tag_definition`（编码/名称/类型/取值）、`tag_value`（对象取值）、`profile_tag`（绑定） |
| 子数据 | `portrait_extension`：`ext_type='business_item'/'progress_snapshot'/'evidence'` |
| 周期快照 | `profile_history` 扩展 `period_type/period_key/snapshot_type` |
| 任务 | `portrait_calc_task`、`sync_task`、`import_task` |

> 说明：现有 `portrait_template.profile_type` 已支持 `business`，**无需新增字段**；实施方案中 `profile_family` 的建议应改为复用该字段。

## 11. 种子数据与交付清单

| 交付 | 内容 |
|---|---|
| 模板种子 | `scripts/seed_sqjz_templates.py`：1 主 + 8 子 + 挂载关系 + 权重 |
| 标注种子 | 6 个 `annotation_template`，`field_schema` 按第 6 节 |
| 标签种子 | 63 个 `tag_definition`，按第 8 节编码 |
| 判定规则 | 第 7 节矩阵落为模板 `anomaly_rules`/服务规则配置 |
| 前端 | 分类管理、考核、奖惩、教育、风险五个页签；周期趋势与证据查看 |
| 导入模板 | 考核扣分、奖惩、教育台账三张 Excel 模板 |

## 12. 验收标准

| 项 | 标准 |
|---|---|
| 条款覆盖 | 33 条均有模板/标签/规则映射，见附录 |
| 模板 | 主模板可预览、可挂载 8 子模板、权重合计 100 |
| 标注 | 6 个标注模板可按场景生成任务，必复核项无法直接通过 |
| 标签 | 63 个标签可绑定、可取值、可筛选 |
| 规则 | 分类/合格/训诫/警告/表扬/治安/撤销 7 类判定可回归验证 |
| 安全 | 姓名/身份证/联系方式/保证人按 PII 规则脱敏 |
| 追溯 | 每个标签可回溯到条款与证据材料 |

## 13. 附录：条款-模板-标签追溯矩阵

| 条款 | 主题 | 模板 | 关键标签 |
|---|---|---|---|
| 二 | 分类与考核定义 | 主模板 | `sqjz_mgmt_category`、`sqjz_cycle_result` |
| 三–四 | 职责与方案调整 | 分类管理 | `sqjz_mgmt_approval`、`sqjz_measure_adjustment` |
| 五–六 | 考核原则/公示/免罚 | 奖惩 | `sqjz_public_notice`、`sqjz_direct_legal` |
| 七 | 管理类别与审批 | 分类管理 | `sqjz_mgmt_category`、`sqjz_mgmt_approval` |
| 八–十 | 三类管理措施 | 遵规/分类 | `sqjz_report_*_freq`、`sqjz_outing_policy` |
| 十一–十二 | 特殊调整/核查频次 | 分类/遵规 | `sqjz_measure_adjustment`、`sqjz_info_check_freq` |
| 十三–十五 | 公益/特殊群体/外部教育 | 教育帮扶 | `sqjz_public_welfare_hours`、`sqjz_special_group` |
| 十六 | 考核周期与时限 | 考核 | `sqjz_cycle_key`、`sqjz_assessment_date` |
| 十七 | 19 项扣分 | 考核 | `sqjz_deduction_items` |
| 十八 | 扣分权限 | 考核 | `sqjz_deduction_authority` |
| 十九 | 省外转入 | 考核 | `sqjz_outside_transfer`、`sqjz_prior_penalty_accum` |
| 二十 | 合格/不合格 | 考核 | `sqjz_cycle_result`、`sqjz_unqualify_reason` |
| 二十一–二十二 | 训诫/警告 | 奖惩 | `sqjz_admonition_count`、`sqjz_warning_count` |
| 二十三 | 表扬 | 奖惩/成效 | `sqjz_commendation_basis`、`sqjz_outstanding` |
| 二十四–二十六 | 训诫/警告/治安情形 | 奖惩/风险 | `sqjz_escape_days`、`sqjz_public_security_count` |
| 二十七 | 异议处理 | 奖惩 | `sqjz_objection_status` |
| 二十八 | 未成年 | 未成年专项 | `sqjz_is_minor`、`sqjz_public_notice` |
| 二十九 | 类别调整 | 分类管理 | `sqjz_mgmt_effective` |
| 三十 | 撤销奖惩 | 奖惩 | `sqjz_revoked`、`sqjz_revoke_reason` |
| 三十一–三十三 | 定义/生效 | — | 口径说明 |
