# OpenBase-需求追溯矩阵-v1.6.0

| 需求编号 | 需求摘要 | 设计/实现 | 用例 | 验收 |
|---|---|---|---|---|
| RT-160-001 | 代理详情路由 | `dps_proxy.dps_annotation_detail` | `test_detail_route_registered` | AC-01 |
| RT-160-002 | 静态段顺序 | `/annotations/export` 先注册 | `test_static_export_precedes_dynamic_detail` | AC-01 |
| RT-160-003 | 路径编码 | `quote(annotation_id, safe="")` | `test_detail_forwards_encoded_path_and_identity` | AC-02 |
| RT-160-004 | 身份头注入 | `_build_identity_headers` | 同上 | AC-02 |
| RT-160-005 | 查询参数透传 | `_forward_query_params` | 同上 | AC-02 |
| RT-160-006 | 上游 404 保真 | `_forward` 透传 | `test_detail_upstream_404_passthrough` | AC-02 |
| RT-160-007 | 前端详情类型 | `DpsAnnotationDetail` | `dps-backend-v160.spec.ts` | AC-03 |
| RT-160-008 | 前端详情方法 | `getAnnotationDetail` | 同上 | AC-03 |
| RT-160-009 | 审核面板接详情 | `loadReviewContext`/`reviewTask`/`reviewFields` | 前端构建＋回归 | AC-03 |
| RT-160-010 | 404 回退 | `Promise.allSettled` 容错 | 代码审查 | AC-04 |
| RT-160-011 | 版本留痕 | 后端/前端 1.6.0 | 版本核对 | AC-05 |
| RT-160-012 | 零回归 | 不改既有端点 | 两仓全量回归 | AC-05 |
