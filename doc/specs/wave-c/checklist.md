# 波次 C（2.20.0）验收核对单

| 项 | 内容 |
|---|---|
| 文档编号 | OB-CHECKLIST-PORTRAIT-WAVE-C |
| 版本 | v1.0.1 |
| 状态 | [Review] |
| 规格 | [spec.md](./spec.md) v1.0.0 |
| 日期 | 2026-11-23 |

## 修订历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-11-23 | 首次编制 | AI 编码代理 |
| v1.0.1 | 2026-11-23 | 追加验收记录（21 项单测、回归 111 项、flake8、前端 build、代理 11 项） | AI 编码代理 |
| v1.0.2 | 2026-11-23 | 回勾推送项并记录提交哈希（DPS 8768a2c、OpenBase f73b176） | AI 编码代理 |

## 1. 功能

- [x] `business_item` 可增改查，唯一键幂等。
- [x] `POST /progress/calculate` 生成/更新 `progress_snapshot`。
- [x] 按时率、逾期数、质量均分、工作量求和与 spec §3 口径一致。
- [x] `GET /progress/{person_id}` 返回趋势；日/周/月切换可用。
- [x] 调度 cron/interval 到点触发；未来 5 次预览正确。
- [x] 任务中心三类任务可查；失败可重试。

## 2. 可靠

- [x] worker 重启后过期 running 任务自动回队。
- [x] 重复触发不产生重复快照（唯一键）。
- [x] 连续失败达阈值后调度自动停用且状态可见。

## 3. 安全

- [x] 读取/导出/删除/范围变更均落审计。
- [x] 审计 detail 不含 PII，导出动作记为 EXPORT。
- [x] 保留期外审计被清理，期内保留。
- [x] 关闭开关时进度接口 409，不泄露数据。

## 4. 兼容与迁移

- [x] `DPS_PROGRESS_ENABLED=false`、`DPS_SCHEDULER_ENABLED=false` 时既有接口行为不变。
- [ ] PG/SQLite 迁移连续执行两次均成功（SQLite 已验证；PG 待发布环境演练）。
- [ ] 旧库升级后既有画像列表/详情/标注功能正常（2.19.0 旧库演练待发布环境执行）。

## 5. 质量与留痕

- [x] 新增测试全绿，回归全绿。
- [x] 变更文件 flake8 0 错误；前端 build 通过。
- [x] 版本号 2.20.0 一致；DevLogReport 与计划 v1.0.4 已更新。
- [x] 两仓已推送 origin/backup/github（DPS 8768a2c、OpenBase f73b176）。

## 6. 验收记录（2026-11-23）

| 项 | 结果 |
|---|---|
| 单测 | `test_v2_20_wave_c.py` 21 passed |
| 回归 | wave A/B、画像列表、租户隔离、批量合计 111 passed（1 skipped） |
| 静态检查 | 变更文件 flake8 0 error |
| 前端 | `openbase-ui` build 通过（TaskCenterView 11.51 kB） |
| 代理 | 波次 B/C 代理用例 11 passed |

未覆盖项：PG 实例迁移演练、试点组织性能压测需在发布环境执行（计划 §5.3/§7）。
任务中心页签偏差见 DPS DevLogReport §5（画像计算任务无列表接口，改取审计日志）。
