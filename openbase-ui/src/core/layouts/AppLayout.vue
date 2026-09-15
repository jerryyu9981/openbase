<template>
  <el-container class="ob-layout">
    <el-aside :width="ui.sidebarCollapsed ? '64px' : '220px'" class="ob-sidebar" :class="{ 'ob-sidebar-mobile': ui.isMobile }">
      <div class="ob-logo">{{ ui.sidebarCollapsed ? 'OB' : 'OpenBase' }}</div>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="openedGroups"
        :collapse="ui.sidebarCollapsed"
        :router="true"
        class="ob-menu"
      >
        <!-- 顶层单项：仪表盘 / 个人设置 -->
        <el-menu-item v-for="item in topLevelItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>

        <!-- 业务模块（动态模块平行呈现，gateway 已迁出） -->
        <el-sub-menu v-if="businessModules.length" index="business">
          <template #title><el-icon><Box /></el-icon><span>业务模块</span></template>
          <el-menu-item v-for="m in businessModules" :key="m.path" :index="m.path">
            <el-icon><component :is="m.icon" /></el-icon>
            <template #title>{{ m.title }}</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- 平台管理四域（域 → 页，二级分组，权限码驱动可见性） -->
        <el-sub-menu v-if="platformDomains.length" index="platform">
          <template #title><el-icon><Setting /></el-icon><span>平台管理</span></template>
          <el-sub-menu v-for="domain in platformDomains" :key="domain.label" :index="domain.label">
            <template #title>{{ domain.label }}</template>
            <el-menu-item v-for="item in domain.items" :key="item.path" :index="item.path">
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>{{ item.title }}</template>
            </el-menu-item>
          </el-sub-menu>
        </el-sub-menu>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="ob-header">
        <div class="ob-header-left">
          <el-button link @click="ui.toggleSidebar">
            <el-icon size="20"><Fold v-if="!ui.sidebarCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <span class="ob-header-title">{{ route.meta.title || '' }}</span>
        </div>
        <el-dropdown @command="onCommand">
          <span class="ob-user">{{ auth.user?.username || '未登录' }}<el-icon><ArrowDown /></el-icon></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="settings">个人设置</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="ob-main">
        <!-- 渲染异常兜底：防子页面抛错导致整页白屏（S6 §2.4 机制 3 / INV-3） -->
        <el-result
          v-if="renderError"
          icon="warning"
          title="页面加载失败"
          sub-title="页面渲染异常，可重试或返回仪表盘"
          data-test="layout-render-fallback"
        >
          <template #extra>
            <el-button type="primary" data-test="layout-render-retry" @click="retryRender">重试</el-button>
            <el-button @click="router.push('/dashboard')">返回仪表盘</el-button>
          </template>
        </el-result>
        <router-view v-else :key="viewKey" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onErrorCaptured, onMounted, ref, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Fold, Expand, ArrowDown, Odometer, ChatDotRound, Collection, User,
  OfficeBuilding, Connection, Setting, Grid, Key, Document, Monitor, DataLine, Money,
  Bell, TrendCharts, Cpu, Operation, Reading, Box, Memo as MemoAlias,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/core/stores/auth'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'
import { useUiStore } from '@/core/stores/ui'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const registry = useModuleRegistry()
const ui = useUiStore()

interface MenuLeaf { path: string; title: string; icon: Component; permission?: string }
interface MenuDomain { label: string; items: MenuLeaf[] }

/** 模块图标映射（键 = 后端 `ModuleInfo.icon`；未命中由回退 ChatDotRound） */
const moduleIconMap: Record<string, Component> = {
  Odometer, ChatDotRound, Collection, Memo: MemoAlias, User, OfficeBuilding, Connection,
}

/** 平台菜单叶子（§3.2：permission 与路由 meta 同源，无权限即不渲染该叶子；空域不显示） */
const PLATFORM_LEAVES: MenuDomain[] = [
  {
    label: '身份与权限',
    items: [
      { path: '/platform/identity/tenants', title: '租户管理', icon: OfficeBuilding },
      { path: '/platform/identity/roles', title: '角色与权限', icon: User },
      { path: '/platform/identity/org', title: '组织/团队/用户', icon: OfficeBuilding },
      { path: '/platform/identity/workspaces', title: '工作空间', icon: Grid },
      { path: '/platform/identity/users', title: '用户管理', icon: User },
      { path: '/platform/identity/memory-admin', title: '记忆管理席位', icon: Setting },
      { path: '/platform/identity/auth-ext', title: '注册/找回密码', icon: Key },
    ],
  },
  {
    label: '平台配置与密钥',
    items: [
      { path: '/platform/config/general', title: '全局配置', icon: Setting },
      { path: '/platform/config/modules', title: '模块开关', icon: Grid, permission: 'module:manage' },
      { path: '/platform/config/api-keys', title: 'API 密钥', icon: Key },
    ],
  },
  {
    label: '可观测与审计',
    items: [
      { path: '/platform/observability/logs', title: '日志中心', icon: Document, permission: 'log:read' },
      { path: '/platform/observability/test-records', title: '测试记录', icon: MemoAlias, permission: 'test:record' },
      { path: '/platform/observability/monitoring', title: '统一监控', icon: Monitor },
      { path: '/platform/observability/gpu', title: 'GPU 资源', icon: Cpu },
      { path: '/platform/observability/usage', title: '用量统计', icon: DataLine },
      { path: '/platform/observability/billing', title: '计费', icon: Money },
      { path: '/platform/observability/service-discovery', title: '服务发现与编排', icon: Connection },
      { path: '/platform/observability/gateway-test', title: '聚合网关测试', icon: Operation },
      { path: '/platform/observability/monitoring/costs', title: '成本分析', icon: TrendCharts },
      { path: '/platform/observability/monitoring/alerts', title: '告警中心', icon: Bell },
    ],
  },
  {
    label: '开发者资源',
    items: [
      { path: '/platform/developers/docs', title: '文档中心', icon: Reading },
      { path: '/platform/developers/edgerouter', title: 'EdgeRouter 与适配器', icon: Connection },
      { path: '/platform/developers/plugins', title: '插件管理', icon: Box },
    ],
  },
]

/** 是否有权限（`*` 为全量管理员） */
function hasPerm(permission?: string): boolean {
  if (!permission) return true
  return auth.permissions.includes('*') || auth.permissions.includes(permission)
}

/** 顶层单项（无 submenu）：仪表盘 + 个人设置 */
const topLevelItems = computed<MenuLeaf[]>(() => [
  { path: '/dashboard', title: '仪表盘', icon: Odometer },
  ...(hasPerm() ? [{ path: '/personal/settings', title: '个人设置', icon: User }] : []),
])

/** 业务模块（v1.4.6：gateway 已迁出至平台管理，不再作为业务模块显示） */
const businessModules = computed<MenuLeaf[]>(() =>
  registry.enabledModules
    .filter((m) => m.info.id !== 'gateway')
    .map((m) => ({
      path: m.info.route_prefix,
      title: m.info.name,
      icon: moduleIconMap[m.info.icon || 'ChatDotRound'] || ChatDotRound,
    })),
)

/** 平台管理四域（权限过滤：无权限叶子不渲染；空域不显示；AC-146-10-2 不受单模块启停影响） */
const platformDomains = computed<MenuDomain[]>(() =>
  PLATFORM_LEAVES.map((domain) => ({
    label: domain.label,
    items: domain.items.filter((item) => hasPerm(item.permission)),
  })).filter((domain) => domain.items.length > 0),
)

/** 侧栏菜单展开分组（业务模块 + 平台管理 + 当前命中平台域，保证高亮可见） */
const openedGroups = computed<string[]>(() => {
  const groups = ['business']
  if (platformDomains.value.length) groups.push('platform')
  if (route.path.startsWith('/platform/')) {
    const domain = platformDomains.value.find((d) => d.items.some((i) => route.path === i.path || route.path.startsWith(`${i.path}/`)))
    if (domain) groups.push(domain.label)
  }
  return groups
})

/**
 * 顶层菜单高亮项：模块子页（如 `/portrait/list`）回退到模块 `route_prefix`（如 `/portrait`），
 * 使模块内任意子页时顶层模块项保持高亮（S6-T2 设计说明 3）。平台/个人页按实际路径高亮。
 */
const activeMenu = computed(() => {
  const exact = [...topLevelItems.value, ...platformDomains.value.flatMap((d) => d.items)].find((item) => item.path === route.path)
  if (exact) return exact.path
  const moduleId = route.meta.module as string | undefined
  const activeModule = moduleId ? registry.enabledModules.find((m) => m.info.id === moduleId) : undefined
  return activeModule?.info.route_prefix || route.path
})

function onCommand(command: string) {
  if (command === 'logout') {
    auth.logout()
    router.push('/auth/login')
  } else if (command === 'settings') {
    router.push('/personal/settings')
  }
}

function handleResize() {
  ui.setMobile(window.innerWidth < 768)
}

/** 渲染异常兜底状态（onErrorCaptured 捕获子树错误后渲染提示，避免白屏） */
const renderError = ref('')
const viewKey = ref(0)

onErrorCaptured((error) => {
  renderError.value = (error as Error)?.message || '渲染异常'
  return false
})

function retryRender() {
  renderError.value = ''
  viewKey.value += 1
}

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => window.removeEventListener('resize', handleResize))
</script>

<style scoped>
.ob-layout { height: 100vh; }
.ob-sidebar {
  background: #0f172a;
  transition: width .2s;
  overflow-x: hidden;
}
.ob-logo { color: #fff; font-size: 18px; font-weight: 600; padding: 16px; text-align: center; }
.ob-menu { border-right: none; background: transparent; --el-menu-text-color: #cbd5e1; --el-menu-active-color: #fff; --el-menu-hover-bg-color: #1e293b; --el-menu-bg-color: transparent; }
.ob-header { display: flex; align-items: center; justify-content: space-between; background: var(--ob-surface); border-bottom: 1px solid var(--ob-border); height: var(--ob-header-height); }
.ob-header-left { display: flex; align-items: center; gap: 8px; }
.ob-header-title { font-weight: 600; }
.ob-user { display: flex; align-items: center; gap: 4px; cursor: pointer; }
.ob-main { padding: 16px; overflow: auto; background: var(--ob-bg); }
</style>