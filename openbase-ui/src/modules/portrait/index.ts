import type { RouteRecordRaw } from 'vue-router'

/**
 * 画像模块（DPS 特色，RT-208）
 *
 * v1.4.11：治理类页面上收至公共功能域——
 * 权限管理 → `/platform/identity/dps-permissions`、限流管理 → `/platform/config/rate-limits`、
 * 系统监控 → `/platform/observability/dps-monitor`、API 管理 → `/platform/developers/dps-api`。
 * 旧路径经 legacyRedirects 承接（禁 404）。
 *
 * v1.4.11 收口：DPS 模板化 12 页（原 `/dps/**` 静态路由、无菜单、不受模块开关约束）
 * 归位到本模块 `dps/*` 子路径（`/portrait/dps/**`），随 portrait 模块启停；旧路径重定向承接。
 */

/**
 * DPS 模板化 12 页（P-01~P-12；P-09 由 `new` 与 `:code/edit` 两条路径承载 ⇒ 13 条 route record）。
 *
 * 静态段先于同名动态段（`new` 先于 `:code/edit`、`templates` 先于 `:code/*`），避免被 `:code` 吞并。
 * v1.4.11 收口：原挂在顶部 `/dps/**` 静态路由（无菜单、不受模块开关约束），现作为画像模块子路由，
 * 实际路径 `/portrait/dps/**`，随 portrait 启停并进入模块导航。
 */
export const dpsRoutes: RouteRecordRaw[] = [
  { path: 'dps/templates', name: 'dps-template-list', component: () => import('./pages/DpsTemplateListView.vue'), meta: { title: '模板族管理' } },
  { path: 'dps/templates/new', name: 'dps-template-new', component: () => import('./pages/DpsTemplateEditView.vue'), meta: { title: '画像模板新建' } },
  { path: 'dps/templates/:code/edit', name: 'dps-template-edit', component: () => import('./pages/DpsTemplateEditView.vue'), meta: { title: '画像模板编辑' } },
  { path: 'dps/templates/:code/versions', name: 'dps-template-versions', component: () => import('./pages/DpsTemplateVersionView.vue'), meta: { title: '版本对比与回滚' } },
  { path: 'dps/templates/:code/preflight', name: 'dps-template-preflight', component: () => import('./pages/DpsTemplatePreflightView.vue'), meta: { title: '预检与影响面' } },
  { path: 'dps/template-packages', name: 'dps-template-packages', component: () => import('./pages/DpsTemplatePackageView.vue'), meta: { title: '模板包导出／导入' } },
  { path: 'dps/lineage', name: 'dps-lineage', component: () => import('./pages/DpsLineageView.vue'), meta: { title: '标签血缘反查' } },
  { path: 'dps/measures', name: 'dps-measures', component: () => import('./pages/DpsMeasureView.vue'), meta: { title: '措施建议' } },
  { path: 'dps/scoring-types', name: 'dps-scoring-types', component: () => import('./pages/DpsScoringTypeView.vue'), meta: { title: '评分类型' } },
  { path: 'dps/annotation-adapters', name: 'dps-annotation-adapters', component: () => import('./pages/DpsAnnotationAdapterView.vue'), meta: { title: 'AI 标注候选与复核' } },
  { path: 'dps/annotation-templates', name: 'dps-annotation-templates', component: () => import('./pages/DpsAnnotationTemplateView.vue'), meta: { title: '标注模板管理' } },
  { path: 'dps/annotation-templates/:code/fields', name: 'dps-annotation-fields', component: () => import('./pages/DpsAnnotationFieldView.vue'), meta: { title: '标注模板字段与归属' } },
  { path: 'dps/tags', name: 'dps-tags', component: () => import('./pages/DpsTagSystemView.vue'), meta: { title: '标签体系查看' } },
]

export const routes: RouteRecordRaw[] = [
  { path: '', redirect: '/portrait/list' },
  { path: 'list', name: 'portrait-list', component: () => import('./pages/PortraitList.vue'), meta: { title: '画像管理' } },
  // 静态子页须先于 ':id' 声明，避免被详情动态段吞并
  { path: 'search', name: 'portrait-search', component: () => import('./pages/PortraitSearch.vue'), meta: { title: '画像搜索' } },
  { path: 'tags', name: 'portrait-tags', component: () => import('./pages/Tags.vue'), meta: { title: '标签管理' } },
  { path: 'overview', name: 'portrait-overview', component: () => import('./pages/Overview.vue'), meta: { title: '数据总览' } },
  { path: 'rules', name: 'portrait-rules', component: () => import('./pages/Rules.vue'), meta: { title: '规则引擎' } },
  // v1.4.11：「分析报表」「批量任务」原复用列表视图（点进去与画像列表完全一致，属误导），
  // 已下线为独立路由；旧直达链接经 legacyRedirects 回落到画像列表，待上游提供专用接口后再成页。
  ...dpsRoutes,
  { path: ':id', name: 'portrait-detail', component: () => import('./pages/PortraitDetail.vue'), meta: { title: '画像详情' } },
]

/** 板块导航 */
export const navItems = [
  {
    label: '画像管理',
    items: [
      { path: '/portrait/overview', title: '数据总览' },
      { path: '/portrait/list', title: '画像列表' },
      { path: '/portrait/search', title: '画像搜索' },
      { path: '/portrait/tags', title: '标签管理' },
      { path: '/portrait/rules', title: '规则引擎' },
    ],
  },
  {
    label: '画像模板化（DPS）',
    items: [
      { path: '/portrait/dps/templates', title: '模板族管理' },
      { path: '/portrait/dps/template-packages', title: '模板包导出/导入' },
      { path: '/portrait/dps/lineage', title: '标签血缘反查' },
      { path: '/portrait/dps/measures', title: '措施建议' },
      { path: '/portrait/dps/scoring-types', title: '评分类型' },
      { path: '/portrait/dps/annotation-adapters', title: 'AI 标注候选与复核' },
      { path: '/portrait/dps/annotation-templates', title: '标注模板管理' },
      { path: '/portrait/dps/tags', title: '标签体系查看' },
    ],
  },
]
