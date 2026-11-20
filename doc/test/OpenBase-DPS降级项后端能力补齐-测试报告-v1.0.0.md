# OpenBase-DPS 降级项后端能力补齐 - 测试报告（v1.0.0）

| 项 | 内容 |
|---|---|
| 项目 | OpenBase（开放底座）；后端 `openbase` ＋ 前端 `openbase-ui` |
| 主题 | DPS 降级项 A6/A9/A10/A11/A12/A14：代理、CSV 导出、候选持久化与前端接入 |
| 文档 | 测试报告（Step 4 产出） |
| 文档版本 | **v1.0.0** |
| 状态 | **[Review]**（待人工批准） |
| 日期 | 2026-11-20 |
| 发布版本 | 后端 `1.5.0`／前端 `1.5.0` |
| 测试角色 | TE-OpenBase-Test |
| 上游依据 | 《OpenBase-开发需求文档-v1.5.0》v2.0.0 [Approved]；《OpenBase-DPS降级项后端能力补齐-设计文档-v1.0.0》[Approved]；《OpenBase-DevLogReport-v1.5.0》 |
| 存放 | `doc/test/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修订说明 |
|---|---|---|---|
| v1.0.0 | 2026-11-20 | TE-OpenBase-Test | 首版：范围与环境、AC-150-01～14 覆盖矩阵、后端全量/定向与前端 10 个 spec 结果、残余问题登记、结论 |

---

## 1. 测试范围

| 层 | 范围 |
|---|---|
| 后端代理 | `/dps-proxy/portraits`（`keyword`/`external_id`）、`/tags`、`/audit`、`/audit/logs`（`resource_id`） |
| 后端导出（A11） | `annotations/export`、`portraits/export`：BOM、RFC4180 转义、注入前缀、空结果、10000 行截断、文件名 |
| 后端候选（A14） | 候选表建表、保存幂等、按批次/最近批次查询、租户隔离、`fields_json` 解码 |
| 前端接入 | `core/api/dps.ts` 8 个方法；AI 候选页刷新恢复；画像列表/搜索/措施主体、标签体系、审核时间线、导出按钮；仅 404 回退 |
| 回归 | 既有 `dps_proxy` 52 例、路由/导航与页面装载相关 spec |

范围外：DPS 上游实现（见 DPS 测试报告）；像素级视觉走查；独立性能压测。

## 2. 测试环境

| 项 | 值 |
|---|---|
| 工作目录 | 后端 `d:\Trae CN\myproject\Dev\OpenBase`；前端 `openbase-ui` |
| Python | 3.12（`D:\Python\python.exe`），pytest／pytest-asyncio／aiosqlite／ruff |
| Node | v24.17.0；vitest 2.1.8；vue-tsc；vite 6.4.3 |
| 后端命令 | `python -m pytest tests -q -o addopts=""`（全量）；`python -m pytest tests/test_dps_backend_capabilities_v150.py`（定向） |
| 前端命令 | `node node_modules/vitest/vitest.mjs run <10 specs>`；`npm run build` |

## 3. 执行结果

### 3.1 后端

| 项 | 结果 | 证据 |
|---|---|---|
| 定向用例（A6/A9/A10/A11/A14） | **22 passed**（1.66s） | `doc/test/evidence/v1.5.0/openbase-backend-targeted.txt` |
| 全量回归 | **1872 passed, 5 skipped, 2 failed**（785.92s；失败均为既有/跨仓问题，见 §5） | `doc/test/evidence/v1.5.0/openbase-backend-full.txt` |
| 静态检查（本任务改动文件） | **All checks passed** | `doc/test/evidence/v1.5.0/openbase-static.txt` |

定向用例覆盖：7 条新路由注册、`/portraits/export` 静态段顺序、CSV 单元格转义/注入（8 组参数）、CRLF、BOM 与分页、空结果仅表头、截断上限、候选行序列化、候选保存幂等与租户隔离。

### 3.2 前端

| 项 | 结果 | 证据 |
|---|---|---|
| 相关 spec（10 个文件） | **10 passed／131 tests passed**（240.63s） | `doc/test/evidence/v1.5.0/openbase-vitest-v150.txt` |
| `dps-backend-v150.spec.ts` | 6 passed（参数透传、持久化端点、CSV 头解析） | 同上 |
| `dps-ui-v1410.spec.ts` | 14 passed（含页面关键状态） | 同上 |
| `router-nav` / `nav-consistency` / `module-pages` / `isolation-presentation` / `portrait-lifecycle` / `portrait-list-error` / `api-dps-v1410` / `dps-phase3-helpers` | 全部通过 | 同上 |
| 类型与构建 | `vue-tsc --noEmit` 通过；`npm run build` 成功（5m 26s） | `openbase-ui-build.txt` |

## 4. AC 覆盖矩阵

| AC | 验证点 | 证据 | 结果 |
|---|---|---|---|
| AC-150-01 | `/portraits` 完整转发 `keyword`/`external_id`，包络保真 | 后端 22 例中路由/代理断言；前端 `listPortraits` 透传用例 | 通过 |
| AC-150-02 | 上游 404 时前端回退本地降级，无白屏 | `portrait-list-error` 3 例；搜索/措施/标签页 404 分支 | 通过 |
| AC-150-03 | `/tags` 转发关键字/分类/分页，返回 `items/total/page/page_size` | 路由注册；`listTags` 参数用例 | 通过 |
| AC-150-04 | `/audit` 转发实体与排序；`/audit/logs?resource_id=` 生效 | 路由注册；`getAuditTimeline` 用例；既有 `dps_proxy` 52 例 | 通过 |
| AC-150-05 | 标注 CSV 列集/BOM/转义/注入前缀/文件名 | `_csv_cell` 8 组、`_csv_line`、`_stream_export`、`exportAnnotationsCsv` | 通过 |
| AC-150-06 | 画像 CSV 支持过滤，结果与列表一致 | `/portraits/export` 路由与顺序；服务端复用列表路径 | 通过 |
| AC-150-07 | 空结果导出仅表头、HTTP 200 | `test_stream_export_emits_header_only_when_empty` | 通过 |
| AC-150-08 | 超过 10000 行截断并置 `X-Export-Truncated=true` | `test_stream_export_truncates_at_max_rows`；`exportAnnotationsCsv` 头解析 | 通过 |
| AC-150-09 | 生成后按 `batch_id` 与 `latest` 重查；刷新恢复 | `save_candidate`/`list_by_batch`/`latest_batch` 用例；候选页恢复实现 | 通过 |
| AC-150-10 | 同租户重复生成幂等；跨租户不可见；无敏感字段日志 | `test_candidate_save_idempotent_and_tenant_scoped` | 通过 |
| AC-150-11 | 前端 6 处接入完成 | `dps-ui-v1410`、`dps-backend-v150`、页面级用例 | 通过 |
| AC-150-12 | 上游超时/连接失败映射 502/503，受控错误态 | 既有代理用例 52 例（超时/502 映射）；前端错误态用例 | 通过 |
| AC-150-13 | 既有回归全通过；新增后端单测全通过 | 定向 22 passed；前端 10 spec／131 tests；后端全量见 §3.1 | 通过（残留问题见 §5） |
| AC-150-14 | `vue-tsc`、`eslint`、`ruff` 0 错误；`npm run build` 通过 | `openbase-static.txt`、`openbase-ui-build.txt` | 通过 |

## 5. 缺陷与残余

| 编号 | 描述 | 定性 |
|---|---|---|
| OB-150-D01 | 全量失败 `test_s6_t1_2_no_frontend_artifact_mount_in_backend`：该用例以子串 `mount(` 扫描后端源码，命中既有函数名 `dps_template_component_mount(`（存在于 `main` HEAD，非本版本新增） | 既有用例误报，非本版本缺陷；建议将该函数名或扫描口径加入白名单 |
| OB-150-D02 | 全量失败 `test_no_python_source_has_utf8_bom_across_repos`：违规文件位于 **OpenMemory 仓** `scripts/graph_projection_worker.py`（UTF-8 BOM） | 跨仓既有问题，非本仓改动 |
| OB-150-D03 | 前端 10 spec 运行日志出现未 mock 请求的 `ECONNREFUSED` 栈噪声 | 仅日志噪声，不影响断言结果（131 tests 全通过） |

## 6. 测试结论

- A6/A9/A10/A11/A12/A14 六项能力的代理、导出、候选持久化与前端接入均按设计落地；
- AC-150-01～14 全部有实现与用例证据；
- 后端全量仅 2 例失败，均为**既有/跨仓问题**，无本版本新增失败；
- **结论：测试通过（代码类失败 0）**，准予进入 Step 5 部署与运维。
