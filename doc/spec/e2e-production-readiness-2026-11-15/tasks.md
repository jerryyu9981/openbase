# OpenBase 上生产就绪修复 Tasks

- 对应 Spec：`doc/spec/e2e-production-readiness-2026-11-15/spec.md` v1.0.0
- 状态：[Draft]（待批准后执行）
- 修订历史：
  - v1.0.0（2026-11-15）：首版任务拆解。

## T1 补测（RED）
- [x] T1.1 `tests/test_gateway.py`：新增聚合绝对 URL + 转发头透传测试（Fake AsyncClient 记录 URL/headers）。
- [x] T1.2 `tests/test_gateway.py`：新增 `_probe_health` 路径回落测试（`/health` 404 → `/health/liveness` 200 为可达；全 404 为不可达）。
- [x] T1.3 `tests/test_gateway_api.py`：新增聚合路由透传断言（`proxy_base` 以 http 开头、`forward_headers` 含 Authorization）。
- [x] T1.4 `tests/test_gateway_api.py`：新增 ping 接口 dps 健康判定回归（mock 上游）。
- [x] T1.5 运行新测试确认 RED（预期失败）。

## T2 实现（GREEN）
- [x] T2.1 `openbase/modules/gateway/aggregate.py`：`_fetch_step` / `execute_aggregate` 支持 `forward_headers`，默认 `proxy_base` 改绝对地址。
- [x] T2.2 `openbase/modules/gateway/router.py`：聚合路由改为接收 `Request`，传绝对 `proxy_base` 与 `Authorization`。
- [x] T2.3 `openbase/modules/gateway/router.py`：新增 `_HEALTH_PATHS` 与 `_probe_health`，`gateway_ping` 改用之。
- [x] T2.4 `openbase-ui/src/pages/platform/observability/GatewayAggregateView.vue`：默认步骤与映射改为 openllm `/openllm/v1/models` + dps `/health/liveness`。

## T3 验证
- [x] T3.1 `python -m ruff check openbase tests` → 0 错误。
- [x] T3.2 `python -m pytest tests/test_gateway.py tests/test_gateway_api.py -q` → 全通过。
- [x] T3.3 `python -m pytest --cov=openbase.modules.gateway --cov-report=term-missing tests/test_gateway.py tests/test_gateway_api.py` → 新增/修改行覆盖 ≥90%。
- [x] T3.4 重启 openbase 与前端（编排器 `-Action start -Only openbase,frontend` 或 monitor 触发）。
- [x] T3.5 运行时：聚合两步 `errors=[]` 且 `dps_status=healthy`；`/gateway/ping` 四系统全 true。

## T4 浏览器复走查
- [x] T4.1 `/platform/observability/gateway-test` 执行聚合成功、无错误提示。
- [x] T4.2 `/platform/observability/service-discovery` 四系统连通性全绿。
- [x] T4.3 登录/仪表盘/OpenLLM/知识库/记忆/画像/退出登录 全 PASS，无 console error / 404。

## T5 留痕与交付
- [x] T5.1 在 Spec 追加「变更记录」并升版 v1.1.0（含修订历史）。
- [x] T5.2 更新遗留登记（DEF-03 / DEF-04）。
- [x] T5.3 提交并推送 origin / backup / github 三远程。
- [x] T5.4 输出上生产就绪结论（含证据与残留风险）。

## 门禁
- 需人工批准本 Spec 后方可进入 T1；T3 全绿且 T4 全 PASS 方可判定「可上生产」。

## 执行结果（2026-11-15）
- T1：新增 6 条测试（test_gateway.py 4 条、test_gateway_api.py 2 条），先 RED 后 GREEN。
- T3：`ruff` 0 错误；网关定向测试 37 条全通过；openbase 重启后聚合 `errors=0 / dps_status=healthy / models=5`，ping 四系统全 `reachable=true`。
- T4：聚合页执行成功；服务发现 4 实例全健康；仪表盘/OpenLLM/知识库/记忆/画像 全部 PASS（5/5/8/31/18 条数据）。
- T5：Spec 升版 v1.1.0 并追加 §8 变更记录；DEF-03/DEF-04 维持 P2 遗留。
