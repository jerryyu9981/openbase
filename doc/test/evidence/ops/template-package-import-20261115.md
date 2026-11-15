# 社区矫正模板包导入验证记录

- 版本：v1.0.0
- 日期：2026-11-15
- 环境：Dev（服务 127.0.0.1:8000/8030，共享 PG 192.168.0.151:5432/nuct）
- 操作人：AI 编码代理（经用户批准执行）

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

- 标注模板页的过滤框为 `template_code` **精确匹配**（服务端），输入 `cor` 或中文名称不会命中；按名称/前缀检索需前端增加本地关键词过滤或 DPS 增加 LIKE 参数。
- PG 中既有默认模板 `dps-correction-v1`（tenant_id=NULL）仍受租户过滤不可见，属 DPS 全局模板可见性缺口，未在本轮修改。
