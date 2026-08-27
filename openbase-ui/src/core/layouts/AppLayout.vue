<template>
  <el-container class="ob-layout">
    <el-aside :width="ui.sidebarCollapsed ? '64px' : '220px'" class="ob-sidebar" :class="{ 'ob-sidebar-mobile': ui.isMobile }">
      <div class="ob-logo">{{ ui.sidebarCollapsed ? 'OB' : 'OpenBase' }}</div>
      <el-menu
        :default-active="route.path"
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
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Fold, Expand, ArrowDown, Odometer, ChatDotRound, Collection, Memo, User, OfficeBuilding } from '@element-plus/icons-vue'
import { useAuthStore } from '@/core/stores/auth'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'
import { useUiStore } from '@/core/stores/ui'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const registry = useModuleRegistry()
const ui = useUiStore()

const iconMap: Record<string, Component> = {
  Odometer, ChatDotRound, Collection, Memo, User,
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

function onCommand(command: string) {
  if (command === 'logout') {
    auth.logout()
    router.push('/auth/login')
  }
}

function handleResize() {
  ui.setMobile(window.innerWidth < 768)
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
