<template>
  <div class="module-layout">
    <el-menu
      mode="horizontal"
      :default-active="route.path"
      router
      class="module-menu"
      :ellipsis="false"
    >
      <el-sub-menu v-for="group in groups" :key="group.label" :index="group.label">
        <template #title>{{ group.label }}</template>
        <el-menu-item v-for="item in group.items" :key="item.path" :index="item.path">
          {{ item.title }}
        </el-menu-item>
      </el-sub-menu>
    </el-menu>
    <div class="module-content">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

interface NavItem { path: string; title: string }
interface NavGroup { label: string; items: NavItem[] }

const route = useRoute()
const groups = computed<NavGroup[]>(() => (route.meta.navItems as NavGroup[] | undefined) || [])
</script>

<style scoped>
.module-layout { display: flex; flex-direction: column; }
.module-menu {
  border-bottom: 1px solid var(--ob-border);
  overflow-x: auto;
  white-space: nowrap;
  background: var(--ob-surface);
  border-radius: var(--ob-radius-md);
  padding: 0 8px;
}
.module-content { padding-top: 16px; }
@media (max-width: 767px) {
  .module-menu { border-radius: 0; }
  .module-menu :deep(.el-sub-menu__title) { min-height: 44px; }
}
</style>
