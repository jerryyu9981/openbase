# Tasks：A7 模板列表服务端筛选

| 项 | 内容 |
|---|---|
| 需求基线 | 《OpenBase-开发需求文档-v1.8.0》 |
| 设计依据 | 《OpenBase-A7模板服务端筛选-设计文档-v1.0.0》 |
| 状态 | [Done] 已验收（2026-11-21） |

## T1 DPS 服务端筛选

- [x] T1.1 `template_engine.py::list_templates` 增加 `keyword/category_id/template_kind`（LIKE 转义 ＋ ESCAPE）
- [x] T1.2 `routes_profiles.py::api_list_portrait_templates` 增加 Query 参数与 `template_kind` 校验
- [x] T1.3 新增 `src/tests/test_template_filter_v2_16.py`（引擎 5 条 ＋ 路由 1 条）
- [x] T1.4 DPS 版本 `2.15.0 → 2.16.0`

## T2 OpenBase 代理

- [x] T2.1 `dps_templates_list` docstring 补三参数（透传逻辑不变）
- [x] T2.2 代理回归用例：三参数原样到达上游
- [x] T2.3 OpenBase 版本 `1.6.0 → 1.7.0`

## T3 前端

- [x] T3.1 `DpsTemplateFilter` 增加三字段
- [x] T3.2 模板中心 `load()` 传服务端参数，删除客户端过滤
- [x] T3.3 分类点击/清除/重置/保存视图均触发 `load()`
- [x] T3.4 新增 `tests/dps-template-filter-v180.spec.ts`（4 条）
- [x] T3.5 前端版本 `1.7.0 → 1.8.0`

## T4 验证与留痕

- [x] T4.1 DPS 定向 pytest 全绿
- [x] T4.2 OpenBase 代理回归全绿
- [x] T4.3 前端定向 vitest ＋ `npm run build` 成功
- [x] T4.4 设计/开发/测试/部署文档 v1.8.0 与设计回填 v2.7.0
- [x] T4.5 仅 stage 本任务文件，提交并推送 origin/backup/github
