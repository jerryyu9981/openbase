<template>
  <PageContainer title="本地模型" description="本地部署模型与运行状态" test-id="local-models-page">
    <div class="page-toolbar">
      <el-input
        v-model="pullTarget"
        placeholder="待拉取的模型标识（如 qwen3:8b）"
        clearable
        style="width: 260px"
        data-test="local-pull-input"
      />
      <el-button type="primary" data-test="pull-model" :loading="pulling" @click="pullModel">拉取新模型（Ollama）</el-button>
      <el-button data-test="open-repo" @click="repoVisible = true">模型仓库</el-button>
      <el-button data-test="open-gpu" @click="gpuVisible = true">GPU 调度</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="local-models-error"
      @close="errorMessage = ''"
    />

    <el-empty v-if="!loading && models.length === 0" description="暂无已安装的本地模型" :image-size="80" />

    <el-row :gutter="16">
      <el-col v-for="m in models" :key="m.name" :xs="24" :sm="12" :lg="8">
        <el-card class="model-card" data-test="local-model-card">
          <h3>{{ m.name }}</h3>
          <p class="meta">大小：{{ formatSize(m.size) }} · 更新时间：{{ m.modified_at || '-' }}</p>
          <div>
            <el-button size="small" :type="isRunning(m.name) ? 'danger' : 'success'" @click="toggle(m.name)">
              {{ isRunning(m.name) ? '停止' : '启动' }}
            </el-button>
            <el-button size="small" :loading="updatingName === m.name" @click="updateModel(m)">更新</el-button>
            <el-popconfirm title="确认删除该本地模型？" @confirm="remove(m.name)">
              <template #reference><el-button size="small" type="danger" plain>删除</el-button></template>
            </el-popconfirm>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="repoVisible" title="模型仓库" width="520px">
      <el-table :data="repoModels" max-height="360">
        <el-table-column prop="name" label="模型" />
        <el-table-column prop="parameters" label="参数" width="100" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="installFromRepo(row.id)">安装</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="repoVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="gpuVisible" title="GPU 调度" width="520px">
      <el-table :data="gpus" max-height="360">
        <el-table-column prop="name" label="设备" width="180" />
        <el-table-column prop="utilization" label="利用率" width="100" />
        <el-table-column prop="memory" label="显存" />
        <el-table-column label="分配模型">
          <template #default="{ row }">
            <span>{{ row.models.length ? row.models.join(', ') : '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="gpus.length === 0" description="未检测到可用 GPU" :image-size="60" />
      <template #footer>
        <el-button @click="gpuVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  localModelsApi,
  type LlmAvailableModel,
  type LlmGpuAllocation,
  type LlmLocalModelItem,
} from '@/core/api/governance'
import { describeError } from '@/core/api/error'

interface GpuRow {
  name: string
  utilization: string
  memory: string
  models: string[]
}

const models = ref<LlmLocalModelItem[]>([])
const repoModels = ref<LlmAvailableModel[]>([])
const gpus = ref<GpuRow[]>([])
const runningNames = ref<string[]>([])
const loading = ref(false)
const pulling = ref(false)
const updatingName = ref('')
const pullTarget = ref('')
const repoVisible = ref(false)
const gpuVisible = ref(false)
const errorMessage = ref('')

function formatSize(size?: number | null) {
  if (!size) return '-'
  const gb = size / 1024 ** 3
  return gb >= 1 ? `${gb.toFixed(1)}GB` : `${(size / 1024 ** 2).toFixed(0)}MB`
}

function errorText(error: unknown, fallback: string) {
  return describeError(error).detail || fallback
}

function isRunning(name: string) {
  return runningNames.value.includes(name)
}

function toGpuRow(gpu: LlmGpuAllocation): GpuRow {
  return {
    name: gpu.name || `GPU ${gpu.gpu_id}`,
    utilization: `${gpu.utilization ?? 0}%`,
    memory: `${gpu.used_memory_mb ?? 0}/${gpu.total_memory_mb ?? 0}MB`,
    models: (gpu.allocated_models ?? []).map((item) => item.model_name),
  }
}

async function loadAll() {
  loading.value = true
  errorMessage.value = ''
  const results = await Promise.allSettled([
    localModelsApi.list(),
    localModelsApi.gpuInfo(),
    localModelsApi.gpuAllocation(),
  ])
  const [listResult, gpuInfoResult, allocationResult] = results

  if (listResult.status === 'fulfilled') {
    models.value = listResult.value
  } else {
    errorMessage.value = errorText(listResult.reason, '本地模型列表加载失败')
  }

  if (gpuInfoResult.status === 'fulfilled') {
    runningNames.value = (gpuInfoResult.value.running_models ?? [])
      .map((item) => String((item as Record<string, unknown>).name ?? ''))
      .filter(Boolean)
  }

  if (allocationResult.status === 'fulfilled') {
    gpus.value = (allocationResult.value.gpus ?? []).map(toGpuRow)
  }

  loading.value = false
}

async function loadRepo() {
  try {
    const data = await localModelsApi.available()
    repoModels.value = data.models ?? []
  } catch (error) {
    errorMessage.value = errorText(error, '模型仓库加载失败')
  }
}

async function toggle(name: string) {
  try {
    if (isRunning(name)) {
      await localModelsApi.stop(name)
      runningNames.value = runningNames.value.filter((item) => item !== name)
      ElMessage.success(`已停止：${name}`)
    } else {
      await localModelsApi.start(name)
      runningNames.value = [...runningNames.value, name]
      ElMessage.success(`已启动：${name}`)
    }
  } catch (error) {
    ElMessage.error(errorText(error, '模型启停失败'))
  }
}

async function updateModel(m: LlmLocalModelItem) {
  updatingName.value = m.name
  try {
    await localModelsApi.update(m.name)
    ElMessage.success(`已提交更新：${m.name}`)
    await loadAll()
  } catch (error) {
    ElMessage.error(errorText(error, '模型更新失败'))
  } finally {
    updatingName.value = ''
  }
}

async function remove(name: string) {
  try {
    await localModelsApi.remove(name)
    models.value = models.value.filter((item) => item.name !== name)
    ElMessage.success(`已删除：${name}`)
  } catch (error) {
    ElMessage.error(errorText(error, '删除模型失败'))
  }
}

async function pullModel() {
  if (!pullTarget.value) {
    ElMessage.warning('请先选择要拉取的模型')
    return
  }
  pulling.value = true
  try {
    await localModelsApi.pull(pullTarget.value)
    ElMessage.success(`拉取任务已提交：${pullTarget.value}`)
    await loadAll()
  } catch (error) {
    ElMessage.error(errorText(error, '拉取模型失败'))
  } finally {
    pulling.value = false
  }
}

async function installFromRepo(modelId: string) {
  try {
    await localModelsApi.pull(modelId)
    ElMessage.success(`安装任务已提交：${modelId}`)
  } catch (error) {
    ElMessage.error(errorText(error, '安装模型失败'))
  }
}

onMounted(() => {
  void loadAll()
  void loadRepo()
})
</script>

<style scoped>
.model-card { margin-bottom: 16px; }
.model-card h3 { margin: 0 0 8px; }
.meta { color: var(--ob-text-secondary); font-size: 13px; }
.page-toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }
.mb-16 { margin-bottom: 12px; }
</style>
