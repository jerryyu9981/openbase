<template>
  <PageContainer title="仪表盘" description="统一入口：公共功能与运行概览" test-id="dashboard-page">
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="warning"
      show-icon
      closable
      class="mb-16"
      data-test="dashboard-error"
      @close="errorMessage = ''"
    />
    <el-row :gutter="16" v-loading="loading">
      <el-col v-for="card in cards" :key="card.label" :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card" data-test="dashboard-stat">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-sub">{{ card.sub }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16" class="mt-16">
      <el-col :xs="24" :lg="12">
        <el-card header="当前用户" data-test="dashboard-user">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户名">{{ auth.user?.username || '-' }}</el-descriptions-item>
            <el-descriptions-item label="显示名">{{ auth.user?.display_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="租户">{{ auth.user?.tenant_id || '平台默认' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card header="动态模块" data-test="dashboard-modules">
          <el-tag v-for="m in registry.enabledModules" :key="m.info.id" class="module-tag" type="primary">
            {{ m.info.name }}
          </el-tag>
          <EmptyState v-if="registry.enabledModules.length === 0" description="暂无可用模块" />
        </el-card>
      </el-col>
    </el-row>
  </PageContainer>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageContainer from '@/components/page/PageContainer.vue'
import EmptyState from '@/components/page/EmptyState.vue'
import { useAuthStore } from '@/core/stores/auth'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'
import { usersApi } from '@/core/api/users'
import { monitoringApi, type LlmMonitoringDashboard } from '@/core/api/governance'

/**
 * 仪表盘（v1.9.7 R7 真实化）：模块数取本地注册表；平台用户数取 `/users`；
 * 24h 调用量与费用取 OpenLLM `/monitoring/dashboard`。任一数据源失败仅该卡片显示「—」，
 * 不伪造数值。
 */
const registry = useModuleRegistry()
const auth = useAuthStore()
const loading = ref(false)
const errorMessage = ref('')
const userCount = ref<number | null>(null)
const dashboard = ref<LlmMonitoringDashboard | null>(null)

const cards = computed(() => [
  { label: '已启用模块', value: String(registry.enabledModules.length), sub: '本地模块注册表' },
  { label: '平台用户数', value: userCount.value === null ? '—' : String(userCount.value), sub: 'OpenBase /users' },
  {
    label: '24h 调用量',
    value: dashboard.value?.overview ? String(dashboard.value.overview.total_requests) : '—',
    sub: 'OpenLLM 最近 24 小时',
  },
  {
    label: '24h 费用',
    value: dashboard.value?.overview ? `$${Number(dashboard.value.overview.total_cost).toFixed(2)}` : '—',
    sub: 'OpenLLM 最近 24 小时',
  },
])

async function load() {
  loading.value = true
  errorMessage.value = ''
  const [usersResult, dashboardResult] = await Promise.allSettled([
    usersApi.list(),
    monitoringApi.dashboard('24h'),
  ])
  if (usersResult.status === 'fulfilled') {
    userCount.value = usersResult.value.length
  }
  if (dashboardResult.status === 'fulfilled') {
    dashboard.value = dashboardResult.value
  }
  if (usersResult.status === 'rejected' || dashboardResult.status === 'rejected') {
    errorMessage.value = '部分概览数据加载失败，对应卡片显示「—」，请稍后刷新'
  }
  loading.value = false
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-label { color: var(--ob-text-secondary); font-size: 13px; }
.stat-value { font-size: 24px; font-weight: 600; margin-top: 8px; }
.stat-sub { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.mt-16 { margin-top: 16px; }
.module-tag { margin-right: 8px; }
</style>
