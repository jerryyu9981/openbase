# 社区矫正模板包导入验证记录

- 版本：v1.1.0
- 日期：2026-11-15
- 环境：Dev（服务 127.0.0.1:8000/8030，共享 PG 192.168.0.151:5432/nuct）
- 操作人：AI 编码代理（经用户批准执行）
- 修订历史：
  - v1.0.0（2026-11-15）：模板包导入共享 PG 的预演、实做与数据/接口/页面复验记录。
  - v1.1.0（2026-11-15）：新增 §6 标注模板前端本地关键词过滤修复与复验（用户批准）；§5 第 1 条已知限制收敛。

## 1. 导入对象

- 文件：`DPS/import_packages/community_correction_templates_v1.json`
- 包格式：format_version 1.0，items 12（portrait_template 4 + annotation_template 8），dependencies 1
- 接口：`POST /api/v1/dps-proxy/template-packages/import`（租户由 OpenBase 身份头注入）

## 2. 执行结果

- dry_run：`would_create=12 / would_skip=0 / would_conflict=0 / failed=0`
- 实做：`created=12 / updated=0 / skipped=0 / failed=0`
- package_hash：`sha256:9dae80daf5eacb530aa1dd521b3fa45a6f4edc688a0bb754083c7b9278f33678`

## 3. 数据复核（PG，schema platform）

| 表 | 租户 | 行数 |
|---|---|---|
| portrait_template | 20000000-0000-0000-0000-000000000001 | 4 |
| portrait_template | NULL（既有默认模板） | 1 |
| annotation_template | 20000000-0000-0000-0000-000000000001 | 8 |
| template_package | - | 1 |

## 4. 接口与页面复核

- `GET /api/v1/dps-proxy/templates` → total=4（cor-persona-root/intake/assess/risk-v1）
- `GET /api/v1/dps-proxy/annotation-templates` → total=8（cor-anno-basic/psych/behavior/edu/mgmt/reward/category/eposition-v1）
- 浏览器：模板族管理 4 条、标注模板管理 8 条，名称均为中文「社区矫正…」，无错误提示。

## 5. 已知限制

- ~~标注模板页的过滤框为 `template_code` 精确匹配（服务端），输入 `cor` 或中文名称不会命中~~ → 已于 v1.1.0 修复（见 §6）。
- PG 中既有默认模板 `dps-correction-v1`（tenant_id=NULL）仍受租户过滤不可见，属 DPS 全局模板可见性缺口，未在本轮修改。

## 6. 标注模板前端本地关键词过滤（v1.1.0）

- 文件：`openbase-ui/src/modules/portrait/pages/DpsAnnotationTemplateView.vue`
- 变更：
  1. 过滤框改为本地关键词过滤，匹配 `code / name / template_code / scenario`（不区分大小写），不再向服务端传 `template_code` 精确条件；
  2. 工具栏新增「共 N 条」计数（`data-test="annotation-count"`），空结果文案区分「无匹配」与「暂无」。
- 校验：`vue-tsc --noEmit` 0 错误、`eslint` 0 错误。
- 浏览器复验：初始 8 条 → 搜「社区矫正」8 条 → 搜「心理」1 条（`cor-anno-psych-v1`）→ 搜 `cor` 8 条 → 清空恢复 8 条，全部 PASS。
