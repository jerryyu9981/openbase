# OpenBase 社区矫正画像标签字典

| 项 | 内容 |
|---|---|
| 文档编号 | OB-TAG-SQJZ-001 |
| 版本 | v1.0.0 |
| 状态 | [Review] |
| 依据 | 粤司办〔2022〕97 号；《基于人物画像标签体系制定个性化矫正方案的操作框架》（附件 A）；《教育帮扶信息标注模板》（附件 B）；《心理特征标签层标注模板》（附件 C）；SF/T 0081-2020、SF/T 0015-2021 |
| 配套模板 | 《社区矫正对象画像模板与标注模板设计 v2.0.0》 |
| 作者 | AI 编码代理 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制：六维标签 + 心理特征 + 业务规则共 118 项 | AI 编码代理 |

## 1. 使用说明

- 编码统一前缀 `sqjz_`，snake_case；中文名为展示名，英文编码创建后不可修改。
- 类型：`enum` 单值枚举、`multi` 多值、`bool`、`number`、`percent`、`date`、`datetime`、`string`、`array`、`object`。
- 依据列缩写：`97-八` = 粤司办〔2022〕97 号第八条；`A/B/C` = 三份附件；`SF81/SF15` = SF/T 0081-2020 / SF/T 0015-2021；`扩展` = 附件补充指标，需业务确认。
- `(PII)` 标记字段按 L3 掩码、`(PII-L4)` 按 L4 剔除。

## 2. 基础信息层（19）

| 编码 | 中文名 | 类型 | 取值/规则 | 依据 |
|---|---|---|---|---|
| `sqjz_correction_type` | 矫正类型 | enum | 管制/缓刑/假释/暂予监外执行 | 97-二十六 |
| `sqjz_crime_type` | 犯罪类型 | string | 业务字典 | 97-二 |
| `sqjz_sentence` | 原判刑罚 | string | — | 97-二十六 |
| `sqjz_registration_date` | 登记接收日期 | date | — | 97-十六 |
| `sqjz_cycle_start` | 首周期起始 | date | 登记接收之日 | 97-十六 |
| `sqjz_cycle_end` | 首周期截止 | date | 次月起第三个月月底 | 97-十六 |
| `sqjz_execution_location` | 执行地 | string | — | 97-十九 |
| `sqjz_household` | 户籍地 | string | — | 97-十七 |
| `sqjz_residence` | 居住地 | string | — | 97-十七 |
| `sqjz_contact` | 联系方式 | string(PII) | — | 97-十七 |
| `sqjz_guarantor` | 保证人 | string(PII) | — | 97-十四 |
| `sqjz_is_minor` | 是否未成年 | bool | — | 97-二十八 |
| `sqjz_minor_age_band` | 未成年年龄段 | enum | 14–16/16–18 | 社区矫正法 52–58 |
| `sqjz_special_group` | 特殊群体 | multi | 年老/体弱/残疾/疾病/怀孕/就读 | 97-十四 |
| `sqjz_special_adjust` | 特殊调整 | bool | 申请+证明+审批 | 97-十四 |
| `sqjz_three_no` | 三无人员 | bool | 无生活来源/无劳动能力/无赡养扶养 | A |
| `sqjz_disability_type` | 残疾类型 | enum | 肢体/视力/听力/言语/智力/精神 | A |
| `sqjz_pregnancy` | 是否孕期 | bool | — | A |
| `sqjz_execution_change` | 变更执行地 | bool/date | 记录变更日期 | A |

## 3. 行为表现层（12）

| 编码 | 中文名 | 类型 | 取值/规则 | 依据 |
|---|---|---|---|---|
| `sqjz_report_phone_freq` | 电话报告频次 | enum | 每周1/每周2/每日1 | 97-八/九/十 |
| `sqjz_report_inperson_freq` | 当面报告频次 | enum | 每月1/每月2/每周1 | 97-八/九/十 |
| `sqjz_thought_report_count` | 思想汇报次数 | number | 每月≥1 | 97-八(三) |
| `sqjz_info_check_freq` | 信息化核查频次 | enum | 按类别调整 | 97-十二 |
| `sqjz_outing_policy` | 外出政策 | enum | 允许/从严/不批准 | 97-八(八) |
| `sqjz_change_reports` | 变更报告 | array | 联系方式/居所/工作/家庭/外出返回 | 97-十七 |
| `sqjz_location_abnormal` | 定位轨迹异常 | bool/number | 越界/离线次数 | A |
| `sqjz_education_absence` | 教育缺席次数 | number | ≥2 触发 | A |
| `sqjz_late_report` | 未按时报告次数 | number | — | A |
| `sqjz_prohibition_violation` | 违反禁止令 | bool | — | A |
| `sqjz_violation_level` | 违规级别 | enum | 无/轻微/严重 | 97-二十四至二十六 |
| `sqjz_compliance_rate` | 合规率 | percent | 报告/核查/外出综合 | 系统计算 |

## 4. 风险评估层（14）

| 编码 | 中文名 | 类型 | 取值/规则 | 依据 |
|---|---|---|---|---|
| `sqjz_risk_level` | 风险等级 | enum | 高/中/低 | A |
| `sqjz_risk_tags` | 风险核心标签 | multi | 暴力前科/接触高危/经济窘迫/无固定工作/有固定工作/配合监管 | A |
| `sqjz_recidivism_risk` | 再犯风险 | enum | 高/中/低 | A/C |
| `sqjz_psych_state` | 主导心理状态 | multi | 平静/焦虑/抑郁/烦躁/恐惧 | C |
| `sqjz_psych_crisis_level` | 心理危机等级 | enum | 正常/关注/干预/紧急 | C |
| `sqjz_psych_crisis_deadline` | 危机转介时限 | datetime | 紧急 24 小时内 | C |
| `sqjz_escape_days` | 脱管天数 | number | <10/10–20/20–30/>30 | 97-二十四至二十六 |
| `sqjz_special_management` | 特殊管理 | bool | — | 97-十 |
| `sqjz_special_reason` | 特殊情形 | multi | 国家安全/公共秩序/社会稳定 | 97-十 |
| `sqjz_special_deadline` | 特殊期限 | date | 批准时限 | 97-十 |
| `sqjz_risk_review_date` | 风险复核日期 | date | — | — |
| `sqjz_violation_tendency` | 违规倾向预警 | bool | — | C |
| `sqjz_self_harm_risk` | 自伤风险预警 | bool | — | C |
| `sqjz_cooperation_prediction` | 配合度预测 | enum | 高/中/低 | C |

## 5. 教育帮扶层（27）

| 编码 | 中文名 | 类型 | 取值/规则 | 依据 |
|---|---|---|---|---|
| `sqjz_collective_required` | 集体教育规定频次 | number | 次/月；按类别 | 97-八(六)；B |
| `sqjz_collective_actual` | 集体教育实际次数 | number | 关联签到表 | B |
| `sqjz_collective_content` | 集体教育内容 | array | 思想政治/法律/道德/心理/专项 | B |
| `sqjz_collective_score` | 集体教育成绩 | number | ≥60 合格 | B |
| `sqjz_online_required_hours` | 线上规定时长 | number | 小时/月 | B（扩展） |
| `sqjz_online_actual_hours` | 线上实际时长 | number | 平台日志 | B |
| `sqjz_online_completion` | 线上完成率 | percent | 已完成/应完成 | B |
| `sqjz_individual_edu_count` | 个别教育次数 | number | 每月≥1 | 97-八(四) |
| `sqjz_individual_edu_theme` | 个别教育主题 | string | 匹配需求 | B |
| `sqjz_individual_edu_effect` | 个别教育效果 | enum | 优秀/合格/待提升 | B |
| `sqjz_psych_counsel_count` | 个体心理辅导次数 | number | 每次≥40 分钟 | B/C |
| `sqjz_psych_counsel_theme` | 心理辅导主题 | string | 情绪管理/人际关系等 | B/C |
| `sqjz_psych_counsel_qualification` | 辅导师资质 | string | 姓名+证书编号 | B/C |
| `sqjz_psych_assess_date` | 心理测评时间 | date | 季度内 | B/C |
| `sqjz_psych_assess_result` | 心理测评结果 | enum | 正常/轻度/中度/重度 | B/C |
| `sqjz_psych_assess_report_no` | 测评报告编号 | string | `GD+区划+年份+心理+流水` | C |
| `sqjz_vocational_project` | 职业培训项目 | enum | 电工/家政/电商/餐饮 | B |
| `sqjz_vocational_required_hours` | 培训规定时长 | number | 人社标准 | B |
| `sqjz_vocational_actual_hours` | 培训实际时长 | number | 考勤记录 | B |
| `sqjz_vocational_certificate` | 证书获取 | enum | 已获取/待考试/未通过 | B |
| `sqjz_employment_guidance_count` | 就业指导次数 | number | 有意愿者推荐≥2 岗位 | B |
| `sqjz_employment_result` | 就业结果 | enum | 已就业/待就业/无意愿 | B |
| `sqjz_social_assistance_type` | 社会救助类型 | multi | 低保/临时救助/住房帮扶/无 | B |
| `sqjz_social_assistance_proof` | 救助证明编号 | string | 民政编号 | B |
| `sqjz_education_effect_level` | 帮扶成效等级 | enum | 优秀(≥3类)/合格(2类)/待提升(<2类) | B |
| `sqjz_education_improvement_plan` | 未达标改进计划 | string | 待提升必填 | B |
| `sqjz_next_cycle_focus` | 下一周期重点 | array | 基于成效制定 | B |

## 6. 矫正进展层（18）

| 编码 | 中文名 | 类型 | 取值/规则 | 依据 |
|---|---|---|---|---|
| `sqjz_correction_stage` | 矫正阶段 | enum | 初期(1–3月)/中期(4–6月)/后期(解矫前3月) | A |
| `sqjz_cycle_key` | 考核周期 | string | 3 个月 | 97-十六 |
| `sqjz_deduction_total` | 累计扣分 | number | 不跨周期 | 97-十六 |
| `sqjz_deduction_items` | 扣分项 | array | 19 项明细 | 97-十七 |
| `sqjz_cycle_result` | 周期结论 | enum | 合格/不合格 | 97-二十 |
| `sqjz_unqualify_reason` | 不合格原因 | multi | 扣分≥10/训诫≥2/警告/治安 | 97-二十 |
| `sqjz_assessment_date` | 考核日期 | date | 周期后 5 个工作日 | 97-十六 |
| `sqjz_admonition_count` | 训诫次数 | number | — | 97-二十一/二十四 |
| `sqjz_warning_count` | 警告次数 | number | — | 97-二十二/二十五 |
| `sqjz_public_security_count` | 治安处罚次数 | number | — | 97-二十六 |
| `sqjz_commendation_count` | 表扬次数 | number | — | 97-二十三 |
| `sqjz_commendation_basis` | 表扬依据 | enum | 六个月条件/突出表现/表现突出 | 97-二十三 |
| `sqjz_outstanding` | 表现突出 | bool | 连续2周期无扣分且每月教育+公益≥12h | 97-二十三 |
| `sqjz_plan_execution_rate` | 方案执行率 | percent | 措施完成/应完成 | A |
| `sqjz_violation_rate_trend` | 违规率变化 | percent | 环比下降幅度 | A |
| `sqjz_employment_success` | 就业成功率 | percent | 已就业/有就业意愿 | A |
| `sqjz_repentance` | 悔改表现 | enum | 好/一般/差 | 97-二十三 |
| `sqjz_trend` | 画像趋势 | enum | 上升/持平/下降 | A |

## 7. 特殊属性层（12）

| 编码 | 中文名 | 类型 | 取值/规则 | 依据 |
|---|---|---|---|---|
| `sqjz_mgmt_category` | 管理类别 | enum | 普通/严格/特殊 | 97-七 |
| `sqjz_mgmt_approval` | 审批层级 | enum | 县级/市级备案 | 97-七 |
| `sqjz_mgmt_effective` | 生效日期 | date | — | 97-七 |
| `sqjz_mgmt_basis` | 认定依据 | multi | 首周期/不合格/风险情形/调整 | 97-八/九/十 |
| `sqjz_measure_adjustment` | 措施调整 | bool | 特殊情况/入解矫月 | 97-十一 |
| `sqjz_minor_separate` | 未成年分开考核 | bool | — | 97-二十八 |
| `sqjz_no_public_notice` | 不公示 | bool | 未成年考核结果 | 97-二十八 |
| `sqjz_objection_status` | 异议状态 | enum | 无/待处理/已处理/检察院 | 97-二十七 |
| `sqjz_revoked` | 奖惩撤销 | bool | — | 97-三十 |
| `sqjz_revoke_reason` | 撤销原因 | enum | 条件不符/程序违规/材料不符 | 97-三十 |
| `sqjz_commutation_basis` | 减刑建议依据 | bool | 表扬为主要标志 | 97-二十三 |
| `sqjz_public_notice` | 公示 | string | 5 日；未成年不公示 | 97-五/二十八 |

## 8. 心理特征层（16）

| 编码 | 中文名 | 类型 | 取值/规则 | 依据 |
|---|---|---|---|---|
| `sqjz_psych_tools` | 测评工具 | multi | SCL-90/EPQ/SAS/SDS/PCL-R | C |
| `sqjz_psych_assess_status` | 测评状态 | enum | 自主完成/辅助完成/强制完成 | C |
| `sqjz_psych_counselor` | 心理服务专员 | string | 省备案人员 | C |
| `sqjz_personality_neuroticism` | 神经质 | enum | 低/中/高 | C |
| `sqjz_personality_extraversion` | 外向性 | enum | 低/中/高 | C |
| `sqjz_personality_conscientiousness` | 责任心 | enum | 低/中/高 | C |
| `sqjz_personality_disorder` | 特殊人格倾向 | multi | 反社会/冲动型/依赖型/无 | C |
| `sqjz_emotion_intensity` | 情绪强度 | enum | 轻度/中度/重度 | C |
| `sqjz_emotion_trigger` | 情绪触发事件 | string | 失业/家庭冲突/监管压力 | C |
| `sqjz_attribution_style` | 归因方式 | enum | 内归因/外归因/混合 | C |
| `sqjz_value_orientation` | 价值观倾向 | multi | 规则认同/功利导向/消极逃避/积极重构 | C |
| `sqjz_self_cognition` | 自我认知 | enum | 积极/中性/消极/模糊 | C |
| `sqjz_risk_warning_emotion` | 情绪异常预警 | bool | — | C |
| `sqjz_risk_warning_violation` | 违规倾向预警 | bool | 与 `sqjz_violation_tendency` 同源 | C |
| `sqjz_risk_warning_self_harm` | 自伤风险预警 | bool | 与 `sqjz_self_harm_risk` 同源 | C |
| `sqjz_psych_crisis_intervention` | 危机干预措施 | object | 转介机构/频次/启动时间 | C |

## 9. 标签与模板/标注映射

| 标签组 | 子模板 | 标注模板 | 更新触发 |
|---|---|---|---|
| 基础信息（19） | `sqjz_basic` | `ann_sqjz_special`（特殊属性） | 入矫、信息变更 |
| 行为表现（12） | `sqjz_behavior` | `ann_sqjz_behavior` | 日报、核查、外出、违规 |
| 风险（14） | `sqjz_risk` | `ann_sqjz_risk` | 入矫评估、危机、风险变化 |
| 教育帮扶（27） | `sqjz_education` | `ann_sqjz_education_support` | 月度/季度台账、培训就业 |
| 矫正进展（18） | `sqjz_progress` | `ann_sqjz_assessment`/`ann_sqjz_reward_punish` | 周期结算、奖惩决定 |
| 特殊属性（12） | `sqjz_special` | `ann_sqjz_classification`/`ann_sqjz_special` | 审批、调整、撤销 |
| 心理特征（16） | `sqjz_risk`（心理部分） | `ann_sqjz_psych` | 测评、辅导、危机 |

## 10. 关键取值字典

| 字典 | 取值 |
|---|---|
| 管理类别 | 普通管理 / 严格管理 / 特殊管理 |
| 风险等级 | 高 / 中 / 低 |
| 心理危机等级 | 正常 / 关注 / 干预 / 紧急 |
| 考核结论 | 合格 / 不合格 |
| 奖惩类型 | 训诫 / 警告 / 治安管理处罚 / 表扬 / 撤销 |
| 帮扶成效 | 优秀 / 合格 / 待提升 |
| 矫正阶段 | 初期 / 中期 / 后期 |
| 测评结果 | 正常 / 轻度异常 / 中度异常 / 重度异常 |
| 就业结果 | 已就业 / 待就业 / 无就业意愿 |
| 证书情况 | 已获取 / 待考试 / 未通过 |

## 11. 维护规则

1. 新增标签须先在本字典登记编码、中文名、类型、取值、依据，再落 `tag_definition`。
2. 编码不复用、不重命名；废弃标签置 `status=deprecated`，保留历史值。
3. 枚举值新增视为次版本，编码或语义变更视为主版本。
4. 每个标签必须能回溯到 97 号条款、附件字段或标准条目；无依据的扩展标签需业务负责人确认。
5. 涉及 PII 的标签必须在 `field_classification` 登记级别与掩码规则。
