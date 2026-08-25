<template>
  <el-card class="generic-page">
    <template #header>
      <span>{{ title }}</span>
    </template>
    <el-empty :description="`${title}（v1.2.0 已规划，深度对接依赖四系统 API，经 openbase 代理就绪后启用）`" :image-size="80" />
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => (route.meta.title as string) || '功能页')
</script>

<style scoped>
.generic-page { min-height: 360px; }
</style>
