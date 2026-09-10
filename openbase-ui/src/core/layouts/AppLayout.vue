<template>
  <el-container class="ob-layout">
    <el-aside :width="ui.sidebarCollapsed ? '64px' : '220px'" class="ob-sidebar" :class="{ 'ob-sidebar-mobile': ui.isMobile }">
      <div class="ob-logo">{{ ui.sidebarCollapsed ? 'OB' : 'OpenBase' }}</div>
      <el-menu
        :default-active="activeMenu"
        :collapse="ui.sidebarCollapsed"
        :router="true"
        class="ob-menu"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
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
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
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
import { Fold, Expand, ArrowDown, Odometer, ChatDotRound, Collection, Memo, User, OfficeBuilding, Connection } from '@element-plus/icons-vue'
import { useAuthStore } from '@/core/stores/auth'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'
import { useUiStore } from '@/core/stores/ui'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const registry = useModuleRegistry()
const ui = useUiStore()

/** 模块图标映射（键 = 后端 `ModuleInfo.icon`；未命中由 menuItems 回退 ChatDotRound） */
const iconMap: Record<string, Component> = {
  Odometer, ChatDotRound, Collection, Memo, User, OfficeBuilding, Connection,
}

const menuItems = computed<{ path: string; title: string; icon: Component }[]>(() => {
  const items: { path: string; title: string; icon: Component }[] = [
    { path: '/dashboard', title: '仪表盘', icon: Odometer },
    { path: '/system/tenants', title: '租户管理', icon: OfficeBuilding },
  ]
  for (const m of registry.enabledModules) {
    items.push({ path: m.info.route_prefix, title: m.info.name, icon: iconMap[m.info.icon || 'ChatDotRound'] || ChatDotRound })
  }
  return items
})

/**
 * 顶层菜单高亮项：模块子页（如 `/portrait/list`）回退到模块 `route_prefix`（如 `/portrait`），
 * 使模块内任意子页时顶层模块项保持高亮（S6-T2 设计说明 3）。
 */
const activeMenu = computed(() => {
  const exact = menuItems.value.find((item) => item.path === route.path)
  if (exact) return exact.path
  const moduleId = route.meta.module as string | undefined
  const activeModule = moduleId ? registry.enabledModules.find((m) => m.info.id === moduleId) : undefined
  return activeModule?.info.route_prefix || route.path
})

function onCommand(command: string) {
  if (command === 'logout') {
    auth.logout()
    router.push('/auth/login')
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
