<template>
  <PageContainer title="画像系统监控" description="DPS 依赖健康状态（上游仅提供健康端点）" test-id="dps-monitor-view-page">
    <div class="page-toolbar">
      <el-button :loading="loading" data-test="dps-refresh" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="dps-monitor-error"
      @close="errorMessage = ''"
    />

    <el-row :gutter="16" class="mb-16">
      <el-col :span="8">
        <el-card shadow="hover" data-test="mon-dep">
          <div class="dep-header">
            <span>DPS 服务</span>
            <el-tag :type="healthy ? 'success' : 'danger'" size="small" data-test="mon-dep-badge">
              {{ healthy ? '健康' : '异常' }}
            </el-tag>
          </div>
          <div class="dep-meta">版本：{{ version || '-' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="QPS/CPU/内存等指标与告警规则暂无上游端点，本页仅展示 DPS 健康状态；指标端点上架后再行接线"
      data-test="dps-monitor-unavailable"
    />
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { dpsApi } from '@/core/api/dps'

/**
 * 画像系统监控（v1.9.7 R7 收敛）：仅接 `/dps-proxy/health`；上游未提供指标/告警规则端点，
 * 故移除原 mock 的 QPS、内存/CPU 曲线与告警规则，不做虚构数据。
 */
const loading = ref(false)
const errorMessage = ref('')
const status = ref('')
const version = ref('')

const healthy = computed(() => status.value.toLowerCase() === 'healthy' || status.value.toLowerCase() === 'ok')

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await dpsApi.getDpsHealth()
    status.value = result?.status || 'unknown'
    version.value = result?.version || ''
  } catch (error) {
    errorMessage.value = `DPS 健康状态加载失败：${error instanceof Error ? error.message : '未知错误'}`
    status.value = 'unknown'
    version.value = ''
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.dep-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.dep-meta { margin-top: 8px; color: var(--ob-text-secondary); font-size: 12px; }
</style>
