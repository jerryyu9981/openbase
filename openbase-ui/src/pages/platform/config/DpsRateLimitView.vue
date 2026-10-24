<template>
  <PageContainer title="画像接口限流" description="DPS 限流状态只读视图" test-id="dps-rate-limit-view-page">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb-16"
      title="只读视图：DPS 限流写操作已收口为 410；本条数据为业务限流只读指标（source 标注来源）。"
      data-test="rl-readonly-notice"
    />

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="rl-error"
      @close="errorMessage = ''"
    />

    <el-card header="限流状态（只读）" data-test="rl-card">
      <div class="page-toolbar">
        <el-input
          v-model="tenantId"
          placeholder="租户 ID（可选）"
          clearable
          style="width: 200px"
          data-test="rl-tenant"
          @keyup.enter="load"
        />
        <el-button :loading="loading" data-test="rl-refresh" @click="load">刷新</el-button>
      </div>
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="rows" stripe data-test="rl-table">
          <template #empty>
            <el-empty description="暂无限流记录" :image-size="50" data-test="rl-empty" />
          </template>
          <el-table-column prop="tenant_id" label="租户" min-width="130" show-overflow-tooltip />
          <el-table-column prop="endpoint" label="端点" min-width="200" show-overflow-tooltip />
          <el-table-column prop="count" label="当前计数" width="100" />
          <el-table-column prop="limit" label="上限" width="90" />
          <el-table-column prop="window" label="窗口(秒)" width="100" />
          <el-table-column label="利用率" width="100">
            <template #default="{ row }">{{ formatPercent(row.utilization) }}</template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="100" />
          <el-table-column prop="window_start" label="窗口开始" min-width="180" show-overflow-tooltip />
        </el-table>
      </div>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, ref } from 'vue'
import { dpsApi, type DpsRateLimitStatus } from '@/core/api/dps'

/**
 * 画像接口限流（v1.12.0 XR-DPS-03 只读真实化）：
 * 数据源 `GET /dps-proxy/rate-limits/status`（查询参数 tenant_id 透传）；
 * 上游写面已收口 410，本页不提供规则增删改 / 熔断恢复入口。
 */
const loading = ref(false)
const errorMessage = ref('')
const tenantId = ref('')
const rows = ref<DpsRateLimitStatus[]>([])

function formatPercent(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${value.toFixed(2)}%`
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    rows.value = await dpsApi.getRateLimitStatus({
      tenant_id: tenantId.value.trim() || undefined,
    })
  } catch (error) {
    errorMessage.value = `限流状态加载失败：${error instanceof Error ? error.message : '未知错误'}`
    rows.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
</style>
