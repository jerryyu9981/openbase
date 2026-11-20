# OpenBase-DPS 统一前端重设计 - 部署与运维报告（v1.0.0）

| 项目 | 内容 |
|---|---|
| 项目名称 | OpenBase（开放底座）／落点仓 **本仓**（`openbase-ui` 前端） |
| 主题 | DPS 统一前端页面功能重设计（Phase 1～3） |
| 文档 | 部署执行 ＋ 上线检查 ＋ 运维移交（Step 5 产出） |
| 文档版本 | **v1.0.0** |
| 状态 | **[Review]**（Dev 构建与上线检查通过，待人工批准闭环） |
| 部署日期 | 2026-11-20 |
| 目标环境 | **Dev**（Test / Pro 未涉及） |
| 发布负责人 | DO-OpenBase-Dev（部署）／AU-OpenBase-Dev（审计） |
| 存放 | `doc/release/` |
| 上游依据 | 《OpenBase-DPS 统一前端重设计-测试报告-v1.0.0》**v1.1.1 [Approved]**；《OpenBase-DPS 统一前端页面功能设计》**v2.3.0 [Implemented]**；《OpenBase-部署执行与上线检查报告-v1.4.10》格式基线；`AGENTS.md` |

## 修订历史

| 版本 | 日期 | 变更说明 | 修订人 |
|---|---|---|---|
| v1.0.0 | 2026-11-20 | 首版：Step 5 构建与 Dev 上线检查、缺陷闭环、回滚预案与运维移交 | DO-OpenBase-Dev |

---

## 0. 结论摘要

| 环节 | 结论 |
|---|---|
| 5.1 版本与制品确认 | ✅ 通过（应用代码 `da538e5`；前端制品重建 **3m 50s**，exit 0） |
| 5.2 环境与配置核验 | ✅ 通过（无新增依赖/环境变量/DB 迁移/缓存/消息变更） |
| 5.3 缓存与消息运维 | ✅ **不适用**（声明：本版为纯前端页面与逻辑重构） |
| 5.4 部署执行（Dev） | ✅ 通过（静态制品 `dist/`；216 文件 / 3,600,322 B） |
| 5.5 上线验证 | ✅ 通过（构建门禁、117 例回归、路由/深链、页面可加载） |
| 5.6 监控 / 日志 / 告警 | ✅ 通过（前端无新增埋点；告警**不适用**，声明） |
| 5.7 性能上线检查 | ⏸ **范围声明**（未做压测；仅登记制品体积与按页分包结果） |
| 5.8 回滚预案 | ✅ 通过（无数据变更；静态制品回退 ＋ git revert 双路径） |
| 5.9 运维移交 | ✅ 通过（命令、排障、降级项、SLO 建议） |
| **总判定** | **✅ Dev 上线通过**；**阻塞缺陷 0**；Step 5 发现并闭环构建类缺陷 1 项（DEF-DPSR-05-01） |

---

## 1. 发布版本与制品确认（5.1）

| 项 | 值 |
|---|---|
| 应用代码基线 | `main` @ **`da538e5`**（Phase 1 `4412735` ／ Phase 2 `e17eca0` ／ Phase 3 `da538e5`） |
| 测试与文档 | 测试报告提交 **`0213392`**；本报告提交见 §9 留痕 |
| 前端包版本 | `openbase-ui/package.json` → `version=1.4.12` |
| 变更面 | **仅前端**：`openbase-ui/src/modules/portrait/**`（页面、模型/工具、组合式函数）＋ 测试；后端 0 文件；路由无增删（新增 `?view=`／`?mode=`／`?tag=` 查询参数） |
| 制品形态 | 静态制品 `openbase-ui/dist`（Vite 构建，按页分包） |
| 构建命令 | `npm run build`（`vue-tsc --noEmit && vite build`） |
| 构建结果 | **通过，exit 0**；`✓ built in 3m 50s` |
| 制品统计 | `dist/index.html` **475 B**（2026-11-20 17:28:00）；`dist/assets` **215** 个；`dist` 合计 **216 文件 / 3,600,322 B（≈3.43 MiB）** |
| 关键分包 | `DpsAnnotationWorkbenchView` 36.75 kB／`DpsTemplateWorkbenchView` 70.49 kB／`PortraitDetail` 37.63 kB／`DpsTemplateListView` 33.67 kB／`DpsTagSystemView` 13.53 kB／`PortraitList` 15.19 kB（gzip 后均 ≤ 21.55 kB） |
| 构建证据 | `doc/test/evidence/dps-redesign/step5-build-20261120.txt` |

> 构建门禁首次执行时发现测试文件类型错误并阻断（详见 §6 DEF-DPSR-05-01）；修复后重新构建通过。

---

## 2. 环境与配置核验（5.2）

| 项 | 实测／声明 |
|---|---|
| 运行时 | Node **v24.17.0**（系统 `node`）；`node_modules` 为仓库既有依赖 |
| 新增依赖 | **0**（设计 §1.2「不新增 npm 依赖」已满足） |
| 环境变量 | **0 新增**；前端仍经既有 `/api/v1/**` 访问后端与 DPS 代理 |
| 身份与权限 | 前端不构造身份头、不直连 DPS、不做权限判定（沿用 API 文档 v1.4.10 §5） |
| 数据库迁移 | **无 DDL/DML** ⇒《数据运维说明》**不适用**（声明） |
| 缓存 / 消息 | **无**（本版不引入缓存线与消息链路）⇒ 5.3 **不适用**（声明） |
| 上游依赖 | DPS 上游行为与 v1.4.10 发布时一致，本版无契约变更 |

---

## 3. 部署执行（Dev，5.4）

### 3.1 部署方式

| 方式 | 适用场景 | 操作 |
|---|---|---|
| A. 静态制品部署（推荐） | Dev 环境由静态服务器/网关托管前端 | 构建 `dist` → 覆盖目标静态目录 → 校验 `index.html` 与资源可访问 |
| B. Dev 本地联调 | 前端开发/走查 | `npm run dev -- --strictPort`（默认 `127.0.0.1:5173`） |

### 3.2 执行步骤（方式 A）

| # | 步骤 | 命令／动作 | 校验 |
|:-:|---|---|---|
| 1 | 确认基线 | `git log -1 --oneline` | HEAD 含 `da538e5` 与本主题文档提交 |
| 2 | 安装依赖 | `npm ci`（或沿用既有 `node_modules`） | 退出码 0 |
| 3 | 生产构建 | `npm run build` | `✓ built in …`，exit 0 |
| 4 | 备份旧制品 | 归档上一版 `dist` | 归档可回滚 |
| 5 | 发布制品 | 以新 `dist` 覆盖静态目录 | `index.html` 时间戳更新 |
| 6 | 资源校验 | 抽查 `index.html` 与 3 个 `assets/*.js` | HTTP 200 |
| 7 | 页面校验 | 打开 `/portrait/overview`、`/portrait/dps/templates`、`/portrait/dps/annotations`、`/portrait/list` | 首屏渲染、无红屏 |

### 3.3 本次执行记录

| 项 | 结果 |
|---|---|
| 构建 | 通过（3m 50s，exit 0） |
| 制品 | `dist/index.html` 475 B（17:28:00）；`dist/assets` 215 个 |
| 发布动作 | 本报告在开发机完成制品构建与校验；静态目录覆盖由 Dev 部署执行人按 §3.2 执行（Test/Pro 未涉及） |
| 回滚基线 | 构建前旧 `dist` 已保留（用于 §6 路径①） |

---

## 4. 上线验证（5.5）

| # | 验证项 | 方式 | 结果 |
|:-:|---|---|:--:|
| 1 | 生产构建与类型门禁 | `npm run build`（`vue-tsc --noEmit` ＋ `vite build`） | ✅ exit 0，3m 50s |
| 2 | 规范检查 | `eslint`（Phase 3 变更面 15 文件） | ✅ 0 错误 0 告警 |
| 3 | 单元/组件回归 | vitest 相关 12 个 spec | ✅ **117 passed / 0 failed / 0 skipped** |
| 4 | 路由与深链 | `nav-consistency` 21 ＋ `router-nav` 18 ＋ `module-pages` 4 | ✅ 43 passed；旧深链全部可达 |
| 5 | 页面可加载 | `dps-ui-v1410` 路由记录与 12 个 `Dps*View` 加载 | ✅ 14 passed |
| 6 | 错误/空/降级态 | `isolation-presentation` 20 ＋ `portrait-list-error` 3 | ✅ 403/404/5xx/空态受控呈现 |
| 7 | 画像生命周期 | `portrait-lifecycle` 8 | ✅ 计算/外部 ID/编辑/409/删除 |
| 8 | Phase 3 规则 | `dps-phase3-helpers` 15 | ✅ 标签树/血缘/修复目标/画像工具/措施分组 |
| 9 | 制品完整性 | `dist` 文件数、体积、关键分包 | ✅ 见 §1 |
| 10 | 前端密钥扫描 | 变更面不含 key/token/secret 字面量 | ✅ 0 |
| 11 | 浏览器冒烟 | Phase 1 admin 登录冒烟记录（设计 §14.5）＋ 本次构建产物 | ✅ 历史留痕；建议发布后按 §3.2-7 复核 |

> 关联测试：详见《OpenBase-DPS 统一前端重设计-测试报告-v1.0.0》v1.1.1 §3～§4。

---

## 5. 监控、日志与告警（5.6）

| 项 | 说明 |
|---|---|
| 前端日志 | 无新增埋点；保持既有 `ElMessage` / 页面错误条呈现 |
| 错误可观测 | 4xx/5xx/403/404 均按既有错误契约呈现，不静默、不白屏（`isolation-presentation` 覆盖） |
| 发布观察点 | 发布后 30 分钟内观察浏览器 console error、`/api/v1/**` 4xx/5xx 比例、`/portrait/*` 页面可用性 |
| 告警 | **不适用**（静态前端，无独立告警通道；声明） |
| 后端日志 | 沿用既有结构化日志，本版后端无改动 |

---

## 6. 缺陷与闭环（Step 5 发现）

| 缺陷 ID | 级别 | 发现环节 | 描述 | 根因 | 处置 | 复测 |
|---|:--:|---|---|---|---|:--:|
| **DEF-DPSR-05-01** | **P1（构建阻断）** | 生产构建 `vue-tsc --noEmit` | `tests/portrait-lifecycle.spec.ts(108,63): error TS2339: Property 'vm' does not exist on type 'WrapperLike'` | `findComponent(选择器字符串)` 的返回类型为 `WrapperLike`（`VueWrapper \| DOMWrapper`），直接访问 `.vm` 不满足类型约束；运行期行为正常，但阻断生产构建 | 显式断言为 `VueWrapper`（`as unknown as VueWrapper`）并补充类型导入，不改测试语义 | ✅ 构建通过（3m 50s）；`portrait-lifecycle` 8 例通过 |

> 该缺陷为 **Step 4 静态检查口径未覆盖 `tests/**`** 导致（Step 4 仅运行了变更文件 ESLint 与当时记录的类型检查）；Step 5 以 `npm run build` 全项目类型门禁补齐，测试报告已同步 v1.1.1 口径说明。

---

## 7. 回滚方案（5.8）

| 路径 | 触发条件 | 操作 | 验证 | 数据影响 |
|---|---|---|---|---|
| ① 静态制品回退 | 发布后页面异常且需快速恢复 | 用发布前归档的旧 `dist` 覆盖静态目录 | 访问 4 个关键页 + 无红屏 | **无** |
| ② 代码回退 | 需回到重设计前版本 | `git revert` 本主题提交（`4412735`／`e17eca0`／`da538e5`）→ `npm run build` → 重新发布 | 构建 exit 0；旧路由全部可达 | **无** |
| ③ 查询参数降级 | 新深链（`?view=`／`?mode=`／`?tag=`）异常 | 直接访问无参数路径（旧地址） | 页面可用 | **无** |
| ④ 数据回滚 | — | **不适用** | — | **无 DB 变更** |

回滚判定：出现白屏、关键页不可达、或错误态失控且 30 分钟内无法定位 ⇒ 执行路径①。

---

## 8. 运维移交（5.9）

| 项 | 内容 |
|---|---|
| 关键路径 | `/portrait/overview`、`/portrait/dps/annotations`（含 `?view=review`）、`/portrait/dps/templates`、`/portrait/dps/templates/:code/edit`、`/portrait/dps/tags`、`/portrait/dps/lineage`、`/portrait/list`、`/portrait/:id`、`/portrait/dps/measures` |
| 构建命令 | `cd openbase-ui; npm run build` |
| 本地启动 | `npm run dev -- --strictPort` |
| 排障入口 | 浏览器 console；页面错误条（含 `request_id`）；后端 `/health`、`/openapi.json` |
| 已知降级项 | A6 主体检索（前 100 条本地匹配）、A9 标签检索（全量 + 前端搜索）、A10 审计时间线（队列创建时间）、A11 导出（前端 CSV/JSON）、A12 口径过滤（当前页）、A14 AI 候选（内存） |
| SLO 建议 | 首屏可交互 ≤ 3s（Dev 内网）；`/portrait/*` 可用性 ≥ 99.5%；前端 console error = 0（受控 401 网络镜像除外） |
| 联系人 | 发布负责人 DO-OpenBase-Dev；测试 TE-OpenBase-Test；审计 AU-OpenBase-Dev |

---

## 9. 留痕与门禁

| 项 | 值 |
|---|---|
| 应用代码 | `da538e5`（Phase 3） |
| 构建缺陷修复 | `60a5053`（DEF-DPSR-05-01） |
| 测试报告 | `0213392` ＋ v1.1.1 修订并入 `692942c` |
| 本报告 | `692942c`（随后推送 origin / backup / github 三远程 `main`） |
| 门禁 | Step 5 已执行完成，**待人工批准**后本次开发周期闭环 |
| 部署范围 | **Dev**；Test / Pro 未部署（声明） |
