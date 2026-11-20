# OpenBase-开发需求文档-v1.6.0

## 文档信息

| 项 | 内容 |
|----|------|
| 文档名称 | OpenBase 开发需求文档（A4 标注详情代理与前端接入） |
| 文档编号 | OpenBase-REQ-v1.6.0 |
| 版本 | v1.0.0 |
| 状态 | [Approved]（2026-11-20 用户批准 Spec，进入设计与开发） |
| 日期 | 2026-11-20 |
| 编制人 | BA-OpenBase-Dev |
| 上游依据 | DPS《开发需求文档-v2.15.0》v1.0.0；《OpenBase-DPS 统一前端页面功能设计》v2.4.0 §9 A4；用户 2026-11-20 指令 |
| 需求总数 | FR 3 条 ＋ NFR 4 条 ＋ 验收 5 条 ＝ 12 条（RT-160-001~012） |
| 存放 | `doc/requirements/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-11-20 | BA-OpenBase-Dev | 首版：A4 代理透传与审核对照前端接入 |

---

## 1. 背景与目标

DPS v2.15.0 提供标注详情后，OpenBase 需把能力透传给统一前端，并让审核收件箱用详情替代「队列摘要＋画像详情」拼装；DPS 未升级时保持既有降级路径可用。

| 编号 | 目标 | 可衡量判据 |
|:----:|------|------------|
| B1 | 代理可用 | 路径/身份头/查询参数透传，404 语义保真（AC-01/02） |
| B2 | 前端一次取全 | 审核对照使用详情字段，展示审核人/意见（AC-03） |
| B3 | 优雅回退 | 详情 404/失败时保持队列摘要渲染（AC-04） |
| B4 | 零回归 | 两仓全量 0 failed、前端构建成功（AC-05） |

## 2. 范围

| 范围内 | 范围外 |
|---|---|
| 新增 `/api/v1/dps-proxy/annotations/{annotation_id}` | 新增页面路由、导航 IA 调整 |
| `dpsApi.getAnnotationDetail` 与审核面板接入 | DIFF/批量审核语义变更 |
| 代理与前端测试 | 权限模型变更 |

## 3. 功能需求

### FR-160-01 代理透传

- `GET /api/v1/dps-proxy/annotations/{annotation_id}` → 上游 `/api/v2/portrait/annotations/{id}`。
- 身份头沿用 `_build_identity_headers`；`annotation_id` 经 `quote(safe="")` 编码。
- 状态码与错误体语义保真（不映射 OpenBase 错误码）。

### FR-160-02 前端 API 封装

- 新增类型 `DpsAnnotationDetail`／`DpsAnnotationDetailAnnotation`。
- 新增 `dpsApi.getAnnotationDetail(annotationId)`。

### FR-160-03 审核对照接入

- `loadReviewContext` 并行加载详情、画像、字段映射、审核留痕。
- 详情成功：字段、证据来源、审核人/意见以详情为准。
- 详情失败（含 404）：静默回退队列摘要，不阻断其余请求。

## 4. 非功能需求

| 编号 | 要求 |
|---|---|
| NFR-160-01 | 代理不新增权限判定，前端不构造身份头 |
| NFR-160-02 | 异常不阻断并行请求（`Promise.allSettled`） |
| NFR-160-03 | 前端不新增 npm 依赖，不改布局与路由 |
| NFR-160-04 | 提交仅含本任务文件，无夹带 |

## 5. 验收标准

| 编号 | 方法与通过标准 |
|---|---|
| AC-01 | 代理路由注册且 `/annotations/export` 先于动态详情段 |
| AC-02 | 路径编码、身份头/查询参数透传、上游 404 原样返回 |
| AC-03 | 前端方法路径 `dps-proxy/annotations/{encoded}`，详情字段可读 |
| AC-04 | 详情 404 时审核面板仍展示队列摘要（前端容错） |
| AC-05 | 两仓全量 0 failed；`npm run build` 成功 |
