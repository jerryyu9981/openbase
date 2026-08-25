<template>
  <div>
    <el-row :gutter="16">
      <el-col :xs="24" :sm="12" :lg="6" v-for="card in cards" :key="card.label">
        <el-card class="stat-card">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16" class="mt-16">
      <el-col :xs="24" :lg="12">
        <el-card header="统一入口">
          <p>单前端登录访问四系统特色模块：对话监控 / 知识库 / 记忆 / 画像。</p>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card header="动态模块">
          <el-tag v-for="m in registry.enabledModules" :key="m.info.id" class="module-tag" type="primary">
            {{ m.info.name }}
          </el-tag>
          <el-empty v-if="registry.enabledModules.length === 0" description="暂无可用模块" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'

const registry = useModuleRegistry()
const cards = computed(() => [
  { label: '已启用模块', value: registry.enabledModules.length },
  { label: '当前用户', value: 'admin' },
  { label: '系统版本', value: 'v1.2.0' },
  { label: '统一入口', value: '4 系统' },
])
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-label { color: var(--ob-text-secondary); font-size: 13px; }
.stat-value { font-size: 24px; font-weight: 600; margin-top: 8px; }
.mt-16 { margin-top: 16px; }
.module-tag { margin-right: 8px; }
</style>
