<template>
  <PageContainer title="GPU 资源" description="GPU 分配、利用率与占用模型（OpenLLM GPU Monitor）" test-id="gpu-monitor-view-page">
    <div class="page-toolbar">
      <el-button :loading="loading" data-test="gpu-refresh" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="gpu-error"
      @close="errorMessage = ''"
    />

    <el-alert
      v-if="!available"
      :title="unavailableMessage"
      type="warning"
      show-icon
      :closable="false"
      class="mb-16"
      data-test="gpu-no-env"
    />

    <el-card header="GPU 卡列表" class="mb-16" data-test="gpu-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="gpus" stripe data-test="gpu-table">
          <template #empty>
            <el-empty description="当前环境未检测到 GPU" :image-size="60" data-test="gpu-empty" />
          </template>
          <el-table-column prop="name" label="型号" min-width="180" />
          <el-table-column label="利用率" min-width="180">
            <template #default="{ row }">
              <el-progress :percentage="Number(row.utilization ?? 0)" :color="utilColor(row.utilization)" />
            </template>
          </el-table-column>
          <el-table-column label="显存" width="180">
            <template #default="{ row }">
              {{ toGb(row.used_memory_mb) }} / {{ toGb(row.total_memory_mb) }} GB
            </template>
          </el-table-column>
          <el-table-column label="可用显存" width="120">
            <template #default="{ row }">{{ toGb(row.free_memory_mb) }} GB</template>
          </el-table-column>
          <el-table-column label="占用模型" min-width="220">
            <template #default="{ row }">
              <template v-if="row.allocated_models?.length">
                <el-tag v-for="model in row.allocated_models" :key="model.model_name" size="small" class="model-tag">
                  {{ model.model_name }}（{{ model.schedule_type }}）
                </el-tag>
              </template>
              <span v-else class="text-muted">未分配</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card header="Ollama 运行中模型" data-test="gpu-running-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="runningModels" stripe data-test="gpu-running-table">
          <template #empty>
            <el-empty description="暂无运行中模型" :image-size="60" data-test="gpu-running-empty" />
          </template>
          <el-table-column label="模型" min-width="200">
            <template #default="{ row }">{{ row.name || row.model || '-' }}</template>
          </el-table-column>
          <el-table-column label="占用显存" width="150">
            <template #default="{ row }">{{ toGb(Number(row.size ?? 0) / 1024 / 1024) }} GB</template>
          </el-table-column>
          <el-table-column label="GPU 信息" min-width="200">
            <template #default="{ row }">{{ formatGpuInfo(row.gpu) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import {
  localModelsApi,
  type LlmGpuAllocationStatus,
} from '@/core/api/governance'

/**
 * GPU 资源（v1.9.6 R6 真实化）：`/local-models/gpu-allocation/status`（分配/利用率/显存）
 * 与 `/local-models/gpu-info`（Ollama 运行中模型）。
 * 原 mock 卡列表、随机趋势图与温度/功耗列无上游数据支撑，本轮移除，不做假数据。
 */
const loading = ref(false)
const errorMessage = ref('')
const allocation = ref<LlmGpuAllocationStatus | null>(null)
const runningModels = ref<Array<Record<string, unknown>>>([])

const available = computed(() => allocation.value?.available === true)
const gpus = computed(() => allocation.value?.gpus ?? [])
const unavailableMessage = computed(
  () => allocation.value?.message || '当前环境未检测到 GPU 或 GPU 监控不可用',
)

function utilColor(value: number) {
  return value > 90 ? '#DC2626' : value > 70 ? '#D97706' : '#16A34A'
}
function toGb(megabytes: number) {
  return (Number(megabytes ?? 0) / 1024).toFixed(1)
}
function formatGpuInfo(gpu: unknown) {
  if (!gpu || typeof gpu !== 'object') return '-'
  const entries = Object.entries(gpu as Record<string, unknown>)
  if (entries.length === 0) return '-'
  return entries.map(([key, value]) => `${key}: ${value}`).join(', ')
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [status, info] = await Promise.all([
      localModelsApi.gpuAllocation(),
      localModelsApi.gpuInfo(),
    ])
    allocation.value = status
    runningModels.value = info.running_models ?? []
  } catch (error) {
    errorMessage.value = `GPU 资源加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.text-muted { color: var(--ob-text-secondary); font-size: 12px; }
.model-tag { margin: 2px 6px 2px 0; }
</style>
