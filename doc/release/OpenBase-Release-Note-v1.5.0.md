# OpenBase Release Note v1.5.0

| 项 | 内容 |
|---|---|
| 版本 | **v1.5.0**（后端 `openbase` ＋ 前端 `openbase-ui`） |
| 日期 | 2026-11-20 |
| 类型 | 功能增强（向后兼容） |
| 主题 | DPS 降级项后端能力补齐（A6/A9/A10/A11/A12/A14） |

## 新增

- `GET /api/v1/dps-proxy/tags`：转发 DPS 标签检索（关键字/分类/分页）。
- `GET /api/v1/dps-proxy/audit`：转发 DPS 实体审计时间线；`/audit/logs` 支持 `resource_id`。
- `GET /api/v1/dps-proxy/annotations/export`、`GET /api/v1/dps-proxy/portraits/export`：服务端 CSV 导出（UTF-8 BOM、RFC4180 转义、注入防护、最多 10000 行、`X-Export-Truncated`）。
- `POST /api/v1/dps-proxy/annotation-candidates`、`GET .../annotation-candidates?batch_id=`、`GET .../annotation-candidates/latest`：AI 标注候选持久化（同租户幂等）。
- 新表 `dps_annotation_candidate`（随 `create_all` 幂等创建）。

## 增强

- `GET /api/v1/dps-proxy/portraits` 支持 `keyword`／`external_id` 透传。
- 前端：AI 候选页刷新恢复；画像列表/搜索/措施主体与标签体系改服务端检索；审核时间线接入 `/audit`；导出按钮改调后端 CSV；口径问题展示修复建议。

## 兼容与回滚

- 全部新增能力可选；上游 404 时前端回退既有本地降级，403/5xx 呈现受控错误态。
- 回滚：前后端同步回退至 `1.4.12`；新增表保留不写入，无数据回滚需求。

## 验证

- 后端定向 22 passed；前端相关 10 个 spec 通过；`npm run build` 成功。详见测试报告与部署报告。
