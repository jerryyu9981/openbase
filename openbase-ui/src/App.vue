<template>
  <router-view v-if="routeReady" />
  <div v-else class="ob-boot" data-test="app-boot">
    <div class="ob-boot-card">
      <div class="ob-boot-logo">OpenBase</div>
      <el-skeleton :rows="3" animated />
      <p class="ob-boot-text">正在加载工作区…</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

// v1.4.11：首帧导航等待期间显示骨架，替代白屏（后端慢时尤其明显）
const route = useRoute()
const routeReady = computed(() => route.matched.length > 0)
</script>

<style scoped>
.ob-boot {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ob-bg);
}
.ob-boot-card {
  width: 360px;
  padding: 24px;
  background: var(--ob-surface);
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius-md);
  box-shadow: var(--ob-shadow-sm);
}
.ob-boot-logo {
  font-size: 18px;
  font-weight: 600;
  color: var(--ob-primary);
  margin-bottom: 16px;
}
.ob-boot-text {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--ob-text-secondary);
}
</style>
