# Tasks：DPS 降级项后端能力补齐

> 需求批准后开始。按 Step 1→5 门禁推进；编码前须完成 Step 2 设计并获批。

## Step 1 需求（已完成）

- [x] T1.1 用户批准《DPS-开发需求文档-v2.14.0》与《OpenBase-开发需求文档-v1.5.0》
- [x] T1.2 回填两仓需求评审记录为 [Approved]，冻结需求基线
- [x] T1.3 提交并推送两仓 `main`（三远程）——随 Step 5 统一留痕

## Step 2 设计（已完成）

- [x] T2.1 DPS：API 设计增补（A6/A9/A10/A12 契约、错误码、权限）
- [x] T2.2 DPS：数据与兼容设计（零 DDL 证明、external_id 解析链路）
- [x] T2.3 OpenBase：代理契约表、CSV 导出设计、候选表模型与索引设计
- [x] T2.4 OpenBase：前端状态与回退设计（仅 404 回退）
- [x] T2.5 设计评审 → 随 Spec 人工批准（记录于两仓设计文档 §评审）

## Step 3 开发（已完成）

### DPS
- [x] T3.1 `api_list_portraits` 支持 `keyword`/`external_id`，复用 `search_portraits_advanced`
- [x] T3.2 新增 `GET /tags` 扁平检索（关键字/分类/分页/租户）
- [x] T3.3 `audit_log_engine.query` 支持 `resource_id`；新增 `GET /audit` 时间线
- [x] T3.4 `scoring_consistency._issue` 增 `suggestion`/`fix_target`（7 类问题码）
- [x] T3.5 新增需求用例（正常/空/边界/租户/回归）

### OpenBase 后端
- [x] T3.6 代理参数转发（portraits/tags/audit/audit logs）
- [x] T3.7 CSV 导出 2 个端点（BOM/转义/注入/截断/文件名）
- [x] T3.8 候选表模型＋存储＋3 个端点（幂等/租户）
- [x] T3.9 后端单测与 ruff

### OpenBase 前端
- [x] T3.10 `core/api/dps.ts` 新增 API 封装
- [x] T3.11 AI 候选页持久化＋刷新恢复
- [x] T3.12 画像列表/搜索/措施主体检索接入＋404 回退
- [x] T3.13 标签体系页服务端检索
- [x] T3.14 审核时间线接入 `/audit`
- [x] T3.15 导出按钮改调后端 CSV
- [x] T3.16 前端组件测试与回归

## Step 4 测试（已完成）

- [x] T4.1 DPS 全量 `pytest`＋`ruff`，记录基线对比
- [x] T4.2 OpenBase 后端 `pytest`／前端 `vitest`／`vue-tsc`／`eslint`
- [x] T4.3 导出内容与文件头验收（BOM、转义、截断）
- [x] T4.4 候选持久化与租户隔离验收
- [x] T4.5 DPS 未就绪回退验收
- [x] T4.6 产出两仓测试报告 → 人工批准

## Step 5 部署（已完成）

- [x] T5.1 OpenBase 后端依赖安装与构建
- [x] T5.2 OpenBase 前端 `npm run build`
- [x] T5.3 DPS 部署与迁移复跑（零 DDL，无需迁移）
- [x] T5.4 Dev 上线验证（6 项能力逐项）
- [x] T5.5 产出两仓部署与运维报告 → 人工批准 → 周期闭环
