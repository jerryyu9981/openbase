# S7-T3 L2-1 主备切换演练报告

- 生成时间：2026-09-13T18:21:14+0800
- 驱动面：OpenLLM `app.identity.channel.ChannelStateManager`（S4-T7 真实状态机）
- 结论：PASS
- 边界：事件通道（L1-1）不纳入演练矩阵（Q-S7-4）

| 场景 | 命令 | 切换前路由 | 切换后路由 | 降级告警 | 回切条件 | 结论 |
|------|------|-----------|-----------|---------|---------|------|
| 场景 1：B 断 -> A 接管 | trigger_failover_to_a(source=component_degrade) | b | a | component_failure,component_failure,component_failure,failover_b_to_a | 显式 B 恢复 + 演练窗口 | PASS |
| 场景 2：A 断 -> B 维持 | record_a_failure(reason=演练注入) | b | b | a_failure（备不可用） | A 恢复 + 显式切回 | PASS |

## 单主路径采样

- initial：primary=b paths=['b']
- after-failover：primary=a paths=['a']
- after-switch-back：primary=b paths=['b']

## 回切链路审计留痕

- 回切成功：True
- 审计动作序列：['failover_b_to_a', 'recover_b', 'drill_window_open', 'drill_verified', 'drill_window_elapsed', 'switch_back_to_b']
- 缺失动作：[]
- 通道状态上报：{'preference': 'b-primary', 'primary_channel': 'b', 'single_primary': True, 'state': 'b-primary', 'healthy_b': True, 'drill_window_seconds': 300.0, 'auto_failover_enabled': False}

> 未真实执行项保持 PENDING；本报告由真实状态机驱动生成，非样例填充。