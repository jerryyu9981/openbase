# Tasks：A2 审核人视角与任务领取

| 项 | 内容 |
|---|---|
| 需求基线 | 《OpenBase-开发需求文档-v1.8.0》 |
| 设计依据 | 《OpenBase-A2审核人视角与领取-设计文档-v1.0.0》 |
| 状态 | [Done] 已验收（2026-11-21） |

## T1 DPS 列表扩展

- [x] T1.1 `query_annotations` 增加 `reviewer_id`／`review_level` 过滤与 `reviewer_id` 选取（缺列守卫）
- [x] T1.2 `api_list_annotations` 增加 `reviewer`（me 解析）与 `level`（0~5）
- [x] T1.3 用例：reviewer/level/me/缺列空页

## T2 DPS 领取端点

- [x] T2.1 `claim_annotation`（条件 UPDATE ＋ 幂等 ＋ 409 分支）
- [x] T2.2 `POST /portrait/annotations/{id}/claim`
- [x] T2.3 权限覆盖 `("POST","/claim") → update` ＋ 唯一性断言
- [x] T2.4 新增 `src/tests/test_annotation_claim_v2_16.py`（引擎 8 条 ＋ 路由 4 条）
- [x] T2.5 DPS 版本 `2.15.0 → 2.16.0`

## T3 OpenBase 代理

- [x] T3.1 新增 `dps_annotation_claim`
- [x] T3.2 新增 `tests/test_dps_proxy_claim_v170.py`（3 条）
- [x] T3.3 OpenBase 版本 `1.6.0 → 1.7.0`

## T4 前端

- [x] T4.1 `dps.ts` 类型扩展 ＋ `claimAnnotation`
- [x] T4.2 「只看我的」＋级数筛选
- [x] T4.3 审核人列与领取按钮
- [x] T4.4 新增 `tests/dps-annotation-claim-v180.spec.ts`（5 条）
- [x] T4.5 前端版本 `1.7.0 → 1.8.0`

## T5 验证与留痕

- [x] T5.1 DPS 定向 pytest 全绿
- [x] T5.2 代理回归全绿
- [x] T5.3 前端定向 vitest ＋ `npm run build` 成功
- [x] T5.4 文档 v1.8.0 与设计回填 v2.7.0
- [x] T5.5 仅 stage 本任务文件，提交并推送三远程
