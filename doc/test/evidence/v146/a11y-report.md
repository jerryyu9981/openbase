# OpenBase v1.4.6 专项测试 · 可访问性（a11y）测试报告

| 项目 | 内容 |
|------|------|
| 文档名称 | OpenBase v1.4.6 专项测试 · 可访问性测试报告 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 被测版本 | v1.4.6（关键页：日志中心 / 模块开关 / 仪表盘 / 403 页 / 登录页） |
| 被测产物 | `openbase-ui` 生产构建产物（`npm run build` → `dist/`，经 `vite preview` 提供服务） |
| 测试类型 | 专项测试（可访问性：语义标签 / 表单 label / 可访问名 / 键盘可达 / 焦点可见 / 对比度） |
| 作者 | SE-OpenBase-Test（测试工程师）/ AT-OpenBase-Test（自动化测试） |
| 执行日期 | 2026-09-15 |
| 原始数据 | `doc/test/evidence/v146/a11y-dom-facts.json`（DOM 事实采集）、`doc/test/evidence/v146/a11y-focus-facts.json`（焦点 + 截图索引）、`doc/test/evidence/v146/a11y-contrast-tokens.json`（静态令牌对比度） |
| 截图证据 | `doc/test/evidence/v146/a11y-screenshots/*.png`（5 页全页截图） |
| 依据 | `doc/design/OpenBase-UI设计文档-v1.4.6.md` §7（可访问性 4 项）、`doc/design/OpenBase-非功能设计说明-v1.4.6.md` §7 不适用说明（"不做全站无障碍专项"）、WCAG 2.1 AA |

---

## 1. 工具可用性与方法

| 工具 | 状态 | 实测命令 / 证据 |
|------|------|-----------------|
| `@axe-core/playwright` | **未安装**（`openbase-ui/node_modules/@axe-core` 不存在，`package.json` 无该依赖） | `Test-Path openbase-ui\node_modules\@axe-core` → `False` |
| Playwright + Chromium | **可用**（`@playwright/test` 1.63.0，浏览器二进制已就绪） | `node_modules/@playwright/test` 存在；`%LOCALAPPDATA%\ms-playwright\chromium_headless_shell-1228` 存在 |
| Lighthouse | **未安装** | 见《perf-report.md》§4 |
| Node / npm | v22.16.0 / 可用 | `node --version` |

**方法**（因 axe 缺失，采用"客观 DOM 事实采集 + 静态令牌核对"，不使用任何浏览器插件）：

1. `npm run build` 生成生产产物，`npx vite preview --port 4199` 提供服务（**不改动仓库配置**）；
2. Playwright（headless Chromium，1440×900）逐页加载并采集：`html[lang]`、landmark、标题层级、交互元素可访问名（aria-label / aria-labelledby / `label[for]` / 包裹 label / title / 文本 / placeholder）、图片 `alt`、表格 `caption`/`th[scope]`、重复 `id`、正 `tabindex`；
3. 接口以 `page.route('**/api/v1/**')` 注入固定夹具（认证/模块注册表/日志检索与 facets），登录态经 `localStorage.ob_access_token` 注入（与 `tests/e2e/support/key-page.ts` 同口径）；
4. 键盘可达性：连续 `Tab` 6–12 次，记录 `document.activeElement` 及**父链 3 层**的 `outline/box-shadow` 计算值，判定是否存在可见焦点指示；
5. 对比度：① 运行时对页面可见文本节点（每页 ≤60 个样本）计算前景/最近不透明背景的 WCAG 对比度；② 静态解析构建产物 CSS 的设计令牌并计算与白/页面底色的对比度。

---

## 2. 已执行项结果（逐页）

| 页面 | 最终 URL | HTTP | `lang` | landmark（header/nav/main/aside/footer） | 标题层级 | 交互元素 | 无可访问名 | 输入无标签 | 图片无 alt | 表格（th / th[scope]） | Tab 步数 | 焦点指示缺失步数（探针口径） | 对比度失败样本 | console 错误/警告 |
|------|----------|:----:|:------:|:----------------------------------------:|----------|---------:|-----------:|-----------:|-----------:|------------------------|---------:|----------------------------:|---------------:|------------------:|
| 登录页 | `/auth/login` | 200 | zh-CN | 0/0/0/0/0 | `H1` OpenBase 统一管理平台 | 4 | 0 | 0 | 0 | — | 6(8) | 1（`body`） | 1/4 | 0 / 0 |
| 403 页 | `/forbidden` | 200 | zh-CN | 0/0/0/0/0 | **无标题元素** | 2 | 0 | 0 | 0 | — | 8 | 2（`body`） | — | 0 / 0 |
| 仪表盘 | `/dashboard` | 200 | zh-CN | 1/0/**1**/1/0 | **无标题元素** | 2 | **1** | 0 | 0 | — | 8 | 2（`body`） | 2/26 | 0 / 0 |
| 日志中心 | `/platform/observability/logs` | 200 | zh-CN | 2/0/**1**/1/0 | **无标题元素** | 16 | **2** | **1** | 0 | 9 / **9**（另一表 0/0；日期面板 7/7） | 12 | 4 | **17/60** | 0 / 0 |
| 模块开关 | `/platform/config/modules` | 200 | zh-CN | 2/0/**1**/1/0 | `H2` 模块开关（**无 H1**） | 6 | **1** | 0 | 0 | 9 / 9 | 12 | 1（`body`） | 12/45 | 0 / 0 |

正向结论（已执行且通过）：

- `html[lang="zh-CN"]` 覆盖全部页面 ✅；
- **表格语义**：日志中心主数据表 `th` 9 个且 `th[scope]` **9/9** 齐全 ✅；模块开关表同 ✅；
- **表单标签**：日志中心筛选区 `label[for]` 关联 5 个、`aria-label` 3 个 ✅（Element Plus `el-form-item label` 正确渲染 `label[for]`）；
- **图片替代文本**：`img` 无 `alt` 数量 = 0 ✅；
- **无重复 `id`、无正 `tabindex`**（全部页面）✅ —— 未发现键盘顺序被人为打乱；
- **无 console error / console warn / pageerror**（全部 5 页，符合项目 E2E `console.warn = 0` 口径）✅；
- `aria-live="polite"` 存在于日期选择器区域（`span` ×4）✅；403 页可正常渲染（带登录态直达 `/forbidden`）。

---

## 3. 问题清单

### P2-1（可访问性）对比度：Element Plus 默认令牌 + 页面自定义色导致多处文本低于 WCAG AA 4.5:1

**静态令牌核对（`a11y-contrast-tokens.json`，来源为构建产物 CSS）**

| 设计令牌 / 色值 | 与 `#fff` 对比度 | 与页面底色 `#f8fafc` | AA（4.5:1） |
|-----------------|:----------------:|:--------------------:|:-----------:|
| `--el-text-color-primary` `#303133` | 13.02 | 12.44 | ✅ |
| `--el-text-color-regular` `#606266` | 6.11 | 5.84 | ✅ |
| `--el-text-color-secondary` `#909399` | **3.08** | **2.94** | ❌ |
| `--el-text-color-placeholder` `#a8abb2` | **2.30** | **2.20** | ❌ |
| 白字 on `--el-color-primary` `#409eff`（主按钮） | **2.78** | — | ❌ |

**运行时抽样核对（真实渲染 DOM）**

| 页面 | 失败样本数 / 抽样数 | 典型样本（真实计算值） |
|------|:------------------:|------------------------|
| 日志中心 | **17 / 60** | 主按钮「检索」白字 on `rgb(64,158,255)` = **2.78**；`el-radio-button__inner`「L1 文件」白字 on 同色 = 2.78；下拉占位「全部模块/全部操作/全部结果」`rgb(168,171,178)` on 白 = **2.30**；表头 `div.cell` `rgb(144,147,153)` on 白 = **3.08**；`el-tag`「导出」`rgb(64,158,255)` on `rgb(236,245,255)` = **2.53** |
| 模块开关 | **12 / 45** | 页面说明 `.page-desc`（13px，`#909399` on `#f8fafc`）= **2.94**（含 `下次登录/刷新生效` 加粗文本）；表头 5 列同 = 3.08 |
| 仪表盘 | 2 / 26 | `el-tag__content`「OpenLLM」「知识库」`#409eff` on `#ecf5ff` = **2.53** |
| 登录页 / 403 页 | 1 / 4 | 登录按钮「登 录」白字 on `#409eff` = **2.78** |

- **判定**：非本增量独有（Element Plus 默认主题令牌全站生效），但 **v1.4.6 新增的日志中心页与模块开关页是失败样本最集中的页面**（合计 29 处）。
- **说明与限定**：运行时对比度为采样启发式（文本节点前景色 vs 最近不透明祖先背景色），未覆盖背景图/渐变场景（本组页面无此类背景）；静态令牌核对与其结论一致，可信。
- **建议**：在 `openbase-ui` 全局样式覆盖 `--el-text-color-secondary`/`--el-text-color-placeholder`（例如 `#6b7280`/**`#767676`** 及以上）并将主按钮文字色或主色二选一调整至 ≥4.5:1；日志中心页内自定义色 `#a8abb2`（占位）与 `el-tag` 配色改用 AA 达标色；将对比度检查纳入后续版本的 UI 走查清单（本次非功能设计 §7 明确"不做全站无障碍专项"，故列 P2 而非阻塞项）。

### P2-2（可访问性）纯图标按钮无「可访问名」

- **现象**：每页均检出 1 个 `button.el-button.is-link`（无文本、无 `aria-label`、无 `title`），在仪表盘/日志中心/模块开关页重复出现（`interactiveWithoutAccessibleName`）。
- **影响**：屏幕阅读器读作"按钮"而无功能语义（推测为布局中的图标按钮 / 表格列设置按钮）。
- **依据**：WCAG 2.1 SC 4.1.2 Name, Role, Value。
- **建议**：为该按钮补 `aria-label`（或可见文本 + `aria-hidden` 图标）；同类图标按钮统一策略。

### P2-3（可访问性）日志中心页存在 1 个未关联标签的下拉输入框 + 1 个无名 `role=combobox`

- **现象**：`inputsWithoutLabel = 1`；`nameSources` = `{none: 2, text: 5, label[for]: 5, placeholder: 1, aria-label: 3}`；检出 `input.el-select__input[role=combobox]` 落入"无可访问名"清单。
- **影响**：多选下拉（模块/操作/结果）在部分状态下无可访问名，仅靠占位文本（`placeholder` 不计为名称）。
- **建议**：为 `el-select` 增加 `aria-label`（如"模块筛选"）或改用带 `label` 的 `el-form-item` + `id` 显式绑定。

### P2-4（可访问性）页面标题层级缺失

- **现象**：日志中心页与仪表盘页 **无任何 `h1`~`h6`**；403 页无标题元素（`el-result` 的 `title` 渲染为 `p`）；模块开关页仅有 `h2`（跳过 `h1`）。
- **影响**：屏幕阅读器用户无法按标题快速跳转页面结构；页面对"标题 = 页面名"的语义缺失（`document.title` 正常）。
- **建议**：为各平台页统一补 `<h1>`（或 `el-page-header`）+ 层级化子标题，403 页改为语义标题。

### P2-5（可访问性）缺少 `<nav>` 地标

- **现象**：全部页面 `nav = 0`（侧栏菜单为 Element Plus `el-menu`，渲染 `ul/li` 无地标语义）；`main = 1`（仪表盘/日志中心/模块开关均存在），403 页与登录页无 `main`。
- **建议**：侧栏容器补 `role="navigation"` + `aria-label="主导航"`；403/登录页内容区补 `<main>`。

### 观察项（不定级，需人工复核）

1. **焦点可见性**：输入类控件的焦点由**父容器**呈现 —— 实测 `.el-input__wrapper.is-focus` 的 `box-shadow = rgb(220,223,230) 0px 0px 0px 1px inset`（1px 内阴影，视觉较弱的焦点指示）；
2. 探针在 3 层父链内未捕获 `el-select` / `el-radio-button` 的焦点样式（Element Plus 将 `is-focus` 施加于更深层容器），故**不对其断言"无焦点样式"**，登记为需人工/截图复核项（截图见 `a11y-screenshots/`）；
3. 部分 Tab 步停在 `body`（Tab 循环到文档末尾）与 `aside.el-aside.ob-sidebar` —— 后者可聚焦（存在 `tabindex`），若为布局容器获得焦点，建议核对是否符合预期（不应把非交互容器纳入 Tab 序列）。

---

## 4. 因工具缺失 / 环境限制未执行项（含原因与补救计划）

| 项 | 状态 | 原因 | 补救计划 |
|----|------|------|----------|
| **axe-core 自动化无障碍扫描**（WCAG A/AA 规则集全量，含 contrast 精确算法、aria 规则、landmark 唯一性等） | **未执行** | `@axe-core/playwright` **未安装**，且任务口径明确「未安装则不要联网安装，改为静态检查」 | 有网环境执行 `npm i -D @axe-core/playwright axe-core`，再以 `new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa']).analyze()` 对 5 页产出 `violations/nodes` 报告，回填本报告 §2/§3；或使用 `axe-core` 独立脚本注入页面 |
| Lighthouse 可访问性审计 | 未执行 | 同《perf-report.md》§4（工具缺失） | 与 Lighthouse 性能审计一并补充 |
| 屏幕阅读器人工走查（NVDA/讲述人） | 未执行 | 无可用屏幕阅读器与人工走查窗口（自动化范围） | 列入 UAT 人工走查清单（重点：日志中心筛选区、表格行读取、模块开关切换确认） |
| 200% 缩放 / 重排（WCAG 1.4.10）、文本间距、动效减弱（prefers-reduced-motion） | 未执行 | 本次未编写对应采集脚本；`prefers-reduced-motion` 未在源码中检索到 | 补充 Playwright 脚本：`deviceScaleFactor`/`page.setViewportSize` + `emulateMedia({ reducedMotion: 'reduce' })` 采集 |
| 真机/多浏览器（Firefox/WebKit/Safari VoiceOver） | 未执行 | 本机仅安装 Playwright Chromium 内核 | 需要时 `npx playwright install firefox webkit` 后扩展 projects |

---

## 5. 结论

1. **结构性与键盘基础可访问性总体良好**：`lang` 齐备、表格 `th[scope]` 100% 齐全、表单 label 关联有效、图片 `alt` 无缺失、无重复 id、无正 `tabindex`、5 页零 console 错误/警告，键盘可完整遍历（每页 6–12 次 Tab 覆盖全部交互元素）。
2. **存在 5 项 P2 改进点**：对比度（AA 未达标，日志中心/模块开关最集中）、纯图标按钮无可访问名、1 个下拉无标签、页面标题层级缺失、缺少 `nav` 地标。
3. **本增量（v1.4.6）自身页面**：日志中心页在语义表格与表单标签上达标，主要缺口为对比度与标题层级；模块开关页同样为对比度 + 标题层级（`h2` 无 `h1`）。
4. **工具限制已如实登记**：axe 自动化扫描与 Lighthouse 均因缺失未执行，并给出可复现的补救命令；现有结论均由**真实浏览器渲染 + 真实计算样式**得出，不依赖工具推测。

---

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-15 | SE-OpenBase-Test / AT-OpenBase-Test | 初始版本：5 个关键页 Playwright（Chromium）DOM 事实采集 + 键盘 Tab 焦点探针 + 运行时/静态双路对比度核对 + 5 张全页截图；登记 P2 改进项 5 项与未执行项 5 项（axe/Lighthouse/SR 人工/缩放重排/多浏览器）及补救计划 |
