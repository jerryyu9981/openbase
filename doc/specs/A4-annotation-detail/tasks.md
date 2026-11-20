# Tasks：A4 标注详情接口（DPS v2.15.0 ＋ OpenBase v1.6.0）

> 依赖：`spec.md` 已获批。执行顺序按 Phase 串行；每 Phase 完成即验证，失败即回退修复，不带病推进。

## Phase 0：需求与设计文档（人工门禁）

- [x] T0.1 产出 `DPS/doc/requirements/DPS-开发需求文档-v2.15.0.md`（FR/NFR/AC，含 A4 契约与降级兼容）。
- [x] T0.2 产出 `DPS/doc/requirements/DPS-需求追溯矩阵-v2.15.0.md`、`DPS-需求评审记录-v2.15.0.md`。
- [x] T0.3 产出 `OpenBase/doc/requirements/OpenBase-开发需求文档-v1.6.0.md`、`OpenBase-需求追溯矩阵-v1.6.0.md`、`OpenBase-需求评审记录-v1.6.0.md`。
- [x] T0.4 产出 `OpenBase/doc/design/OpenBase-A4标注详情接口-设计文档-v1.0.0.md`（端到端时序、字段映射、错误语义、回退）。
- 验收：文档存在、版本/状态/修订历史齐全；契约与 spec §3 一致。

## Phase 1：DPS 后端实现（TDD）

- [x] T1.1 先写 `DPS/src/tests/test_v2_15_annotation_detail.py`（rich/legacy/404/租户四类用例）。
- [x] T1.2 `AnnotationDetailReader.get_annotation_detail(...)` 实现至用例转绿（独立文件，避免混入既有未提交改动）。
- [x] T1.3 `routes_profiles.py` 新增 `GET /portrait/annotations/{annotation_id}`。
- [x] T1.4 `src/__init__.py` 版本升至 `2.15.0`。
- 验收：定向用例全绿（4 passed）；新增文件 `ruff check --select E,F,W,I` 0 错误。

## Phase 2：OpenBase 后端代理（TDD）

- [x] T2.1 先写 `OpenBase/tests/test_a4_annotation_detail_v160.py`（路由注册/路径与头/404 保真）。
- [x] T2.2 `dps_proxy` 新增 `dps_annotation_detail` 路由（`quote` 编码、`_forward` 透传）。
- [x] T2.3 `openbase/__init__.py` 版本升至 `1.6.0`。
- 验收：定向用例全绿（4 passed）；`ruff check` 0 错误。

## Phase 3：前端接入（TDD）

- [x] T3.1 先写 `OpenBase/openbase-ui/tests/dps-backend-v160.spec.ts`（方法、路径、字段）。
- [x] T3.2 `core/api/dps.ts` 新增 `DpsAnnotationDetail` ＋ `getAnnotationDetail`。
- [x] T3.3 `DpsAnnotationWorkbenchView.vue` 并行加载详情、字段优先取详情、展示审核人/意见、失败回退。
- [x] T3.4 `package.json` 版本升至 `1.6.0`。
- 验收：新增 spec ＋ `dps-ui-v1410.spec.ts` 通过（15 passed）；`npm run build` 成功。

## Phase 4：全量回归与测试报告

- [x] T4.1 DPS 全量 `pytest src/tests -q --no-cov`（0 failed）。
- [x] T4.2 OpenBase 全量 `pytest tests -q -o addopts=""`（0 failed；因 Windows 临时库并发锁改为三片串行，覆盖全部 138 个测试文件）。
- [x] T4.3 产出 `DPS/doc/test/DPS-测试报告-v2.15.0.md`、`OpenBase/doc/test/OpenBase-测试报告-v1.6.0.md`（含用例数、耗时、回归结论）。

## Phase 5：留痕、部署报告与推送

- [x] T5.1 产出 `DPS/doc/development/DPS-DevLogReport-v2.15.0.md`、`OpenBase/doc/development/OpenBase-DevLogReport-v1.6.0.md`。
- [x] T5.2 产出两仓 `部署与运维报告`（构建/启动/健康检查/回滚）。
- [x] T5.3 回填 `OpenBase-DPS统一前端页面功能设计-v1.0.0.md` 至内容版本 v2.5.0（A4 已交付、剩余缺口刷新）。
- [x] T5.4 两仓仅 stage 本任务文件 → commit → push `main` 三远程（origin/backup/github）。
- 验收：推送成功；`git status` 无本任务残留；无夹带文件。

## 完成判据（Definition of Done）

1. `GET /api/v2/portrait/annotations/{id}` 与 OpenBase 代理可用，200/404/租户隔离语义正确。
2. 前端审核对照使用详情接口，DPS 未升级时自动回退且可用。
3. 两仓全量测试 0 failed，前端构建成功。
4. 六类文档（需求/矩阵/评审/设计/DevLog/测试/部署）齐备并含修订历史。
5. 两仓 main 三远程推送完成，提交仅含本任务文件。
