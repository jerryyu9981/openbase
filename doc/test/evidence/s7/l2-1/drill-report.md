# S7-T3 L2-1 主备切换演练报告

- 生成时间：2026-09-11T12:39:10+08:00
- 模式：dry-run；场景：both；结论：PENDING
- OpenBase 提交：0a195c4106ae150d98c812924ae3ffc6949bd0c6
- 边界：事件通道（L1-1）不纳入演练矩阵（Q-S7-4）

| 场景 | 命令 | 切换前路由 | 切换后路由 | 降级头 | 告警 | 回切条件 | 结论 |
|------|------|-----------|-----------|--------|------|---------|------|
| 场景 1：B 断 -> A 接管 | -Scenario b-down -BaseUrl <GATEWAY_BASE> -DryRun | B 编排（主） | A 直连接管（备转主） | X-Channel-Degrade: a-direct | channel.b.degraded | B /health 恢复 + 显式切回触发 | PENDING |
| 场景 2：A 断 -> B 维持 | -Scenario a-down -BaseUrl <GATEWAY_BASE> -DryRun | B 编排（主） | B 编排维持（A 备不可用） | X-Channel-Degrade: none | channel.a.unavailable | A /health 恢复 + 显式切回触发 | PENDING |

> 未真实执行项保持 PENDING；联调窗口执行后回填真实路由/降级头/告警并更新结论。