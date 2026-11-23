<template>
  <div class="business-item-table" data-test="business-item-table">
    <div class="table-head">
      <el-radio-group v-model="statusFilter" size="small" data-test="business-item-filter" @change="load">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="pending">待完成</el-radio-button>
        <el-radio-button label="done">已完成</el-radio-button>
      </el-radio-group>
      <el-button size="small" :loading="loading" data-test="business-item-refresh" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="error"
      type="warning"
      show-icon
      :closable="false"
      :title="error"
      data-test="business-item-error"
    />
    <el-table
      v-else
      v-loading="loading"
      :data="items"
      size="small"
      :row-class-name="rowClass"
      empty-text="暂无业务事项"
    >
      <el-table-column prop="item_type" label="事项类型" width="110">
        <template #default="{ row }">{{ typeLabel(row.item_type) }}</template>
      </el-table-column>
      <el-table-column prop="item_name" label="事项" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.item_name || row.item_code || '—' }}</template>
      </el-table-column>
      <el-table-column prop="planned_at" label="计划时间" width="170" show-overflow-tooltip />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="质量" width="80">
        <template #default="{ row }">{{ row.quality_score ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="工作量(h)" width="100">
        <template #default="{ row }">{{ row.workload_hours ?? '—' }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { dpsApi, type DpsBusinessItem } from '@/core/api/dps'
import { describeError } from '@/core/api/error'

const props = defineProps<{ personId: string; limit?: number }>()

const statusFilter = ref('')
const items = ref<DpsBusinessItem[]>([])
const loading = ref(false)
const error = ref('')

const TYPE_LABELS: Record<string, string> = {
  study: '教育学习',
  labor: '公益劳动',
  visit: '走访报到',
  psychology: '心理辅导',
  employment: '就业帮扶',
}

function typeLabel(value?: string) {
  const key = String(value || '')
  return TYPE_LABELS[key] || key || '—'
}

function statusLabel(value?: string) {
  if (value === 'done') return '已完成'
  if (value === 'cancelled') return '已取消'
  return '待完成'
}

function statusType(value?: string) {
  if (value === 'done') return 'success'
  if (value === 'cancelled') return 'info'
  return 'warning'
}

function rowClass({ row }: { row: DpsBusinessItem }) {
  if (String(row.status || '') === 'pending') return 'row-pending'
  return ''
}

async function load() {
  if (!props.personId) return
  loading.value = true
  error.value = ''
  try {
    const payload = await dpsApi.listProgressItems(props.personId, {
      status: statusFilter.value || undefined,
      limit: props.limit ?? 100,
    })
    items.value = payload.items || []
  } catch (err) {
    error.value = describeError(err).detail || '事项加载失败（可能未开启 DPS_PROGRESS_ENABLED）'
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.personId, load)
</script>

<style scoped>
.table-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
:deep(.row-pending) { --el-table-tr-bg-color: var(--el-color-warning-light-9); }
</style>
