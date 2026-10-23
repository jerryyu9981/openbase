<template>
  <PageContainer title="模型部署" description="开源模型部署、状态与日志（OpenLLM Model Deploy）" test-id="model-deploy-page">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="按模型名筛选" clearable style="width: 200px" data-test="deploy-keyword" />
      <el-button type="primary" :loading="loading" data-test="deploy-refresh" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="deploy-error"
      @close="errorMessage = ''"
    />

    <el-card header="模型列表" data-test="deploy-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="filteredModels" stripe data-test="deploy-table">
          <template #empty>
            <el-empty description="暂无开源模型" :image-size="60" data-test="deploy-empty" />
          </template>
          <el-table-column prop="name" label="模型" min-width="180" />
          <el-table-column prop="model_id" label="模型标识" min-width="180" show-overflow-tooltip />
          <el-table-column prop="source" label="来源" width="110" />
          <el-table-column prop="parameters" label="参数" width="100" />
          <el-table-column label="下载状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.download_status === 'completed' ? 'success' : 'info'" size="small">
                {{ row.download_status || 'not_downloaded' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="部署状态" width="120">
            <template #default="{ row }">
              <el-tag :type="deployStatusType(row.deploy_status)" size="small">
                {{ row.deploy_status || 'not_deployed' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="deploy-action" @click="openDeploy(row)">部署</el-button>
              <el-button link type="info" size="small" data-test="deploy-status-action" @click="openStatus(row)">状态</el-button>
              <el-button link type="primary" size="small" data-test="deploy-logs-action" @click="openLogs(row)">日志</el-button>
              <el-popconfirm title="确认停止该模型服务？" @confirm="stop(row)">
                <template #reference>
                  <el-button link type="danger" size="small" data-test="deploy-stop">停止</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="deployVisible" :title="`部署模型 - ${currentModel?.name || ''}`" width="560px" data-test="deploy-dialog">
      <el-form label-width="120px">
        <el-form-item label="推理框架">
          <el-select v-model="deployForm.framework" style="width: 100%" data-test="deploy-framework">
            <el-option label="自动" value="auto" />
            <el-option label="llama.cpp" value="llama.cpp" />
            <el-option label="vLLM" value="vllm" />
            <el-option label="transformers" value="transformers" />
          </el-select>
        </el-form-item>
        <el-form-item label="量化">
          <el-input v-model="deployForm.quantization" placeholder="可选，如 q4_k_m" />
        </el-form-item>
        <el-form-item label="GPU 设备">
          <el-input v-model="deployForm.gpuDevices" placeholder="可选，逗号分隔，如 0,1" data-test="deploy-gpu" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="deployForm.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最大上下文">
          <el-input-number v-model="deployForm.maxContext" :min="512" :step="512" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deployVisible = false">取消</el-button>
        <el-button type="primary" :loading="deploying" data-test="deploy-submit" @click="submitDeploy">部署</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="statusVisible" title="部署状态" size="520px" data-test="deploy-status-drawer">
      <div v-loading="statusLoading">
        <el-empty v-if="!deployStatus" description="暂无部署记录" :image-size="60" />
        <el-descriptions v-else :column="1" border data-test="deploy-status-meta">
          <el-descriptions-item label="部署 ID">{{ deployStatus.deployment_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ deployStatus.status }}</el-descriptions-item>
          <el-descriptions-item label="框架">{{ deployStatus.framework || '-' }}</el-descriptions-item>
          <el-descriptions-item label="端口">{{ deployStatus.port ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="进程 ID">{{ deployStatus.process_id ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="健康检查">
            <el-tag :type="deployStatus.is_healthy ? 'success' : 'warning'" size="small">
              {{ deployStatus.is_healthy ? '健康' : '未就绪' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="启动时间">{{ deployStatus.start_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="运行时长">{{ deployStatus.uptime_seconds ?? '-' }} s</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>

    <el-drawer v-model="logsVisible" title="部署日志" size="640px" data-test="deploy-logs-drawer">
      <div v-loading="logsLoading">
        <el-empty v-if="deployLogs.length === 0" description="暂无日志" :image-size="60" />
        <pre v-else class="logs" data-test="deploy-logs">{{ logsText }}</pre>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  openModelsApi,
  type LlmDeployStatus,
  type LlmMarketModel,
} from '@/core/api/governance'

/**
 * 模型部署（v1.9.7 R7 新增）：`/open-models` 列表 + `/{id}/deploy|deploy-status|logs|stop`。
 * 上游返回真实部署状态与日志，页面不做本地模拟。
 */
const keyword = ref('')
const loading = ref(false)
const errorMessage = ref('')
const models = ref<LlmMarketModel[]>([])

const deployVisible = ref(false)
const deploying = ref(false)
const currentModel = ref<LlmMarketModel | null>(null)
const deployForm = reactive({
  framework: 'auto',
  quantization: '',
  gpuDevices: '',
  port: 8000,
  maxContext: 4096,
})

const statusVisible = ref(false)
const statusLoading = ref(false)
const deployStatus = ref<LlmDeployStatus | null>(null)

const logsVisible = ref(false)
const logsLoading = ref(false)
const deployLogs = ref<Array<Record<string, unknown>>>([])

const filteredModels = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return models.value
  return models.value.filter(
    (model) =>
      model.name.toLowerCase().includes(text) || model.model_id.toLowerCase().includes(text),
  )
})
const logsText = computed(() => JSON.stringify(deployLogs.value, null, 2))

function deployStatusType(status: string | null) {
  return {
    running: 'success',
    healthy: 'success',
    deployed: 'success',
    failed: 'danger',
    stopped: 'info',
    not_deployed: 'info',
  }[status || ''] || 'info'
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const page = await openModelsApi.list({ page: 1, page_size: 100 })
    models.value = page.items
  } catch (error) {
    errorMessage.value = `模型列表加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

function openDeploy(model: LlmMarketModel) {
  currentModel.value = model
  deployForm.framework = 'auto'
  deployForm.quantization = ''
  deployForm.gpuDevices = ''
  deployForm.port = 8000
  deployForm.maxContext = 4096
  deployVisible.value = true
}

async function submitDeploy() {
  if (!currentModel.value) return
  deploying.value = true
  try {
    const gpuDevices = deployForm.gpuDevices
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => Number(item))
      .filter((item) => Number.isInteger(item))
    await openModelsApi.deploy(currentModel.value.model_id, {
      framework: deployForm.framework,
      quantization: deployForm.quantization || null,
      gpu_devices: gpuDevices.length ? gpuDevices : null,
      port: deployForm.port,
      max_context_length: deployForm.maxContext,
    })
    ElMessage.success(`模型 ${currentModel.value.name} 部署已触发`)
    deployVisible.value = false
    await load()
  } catch (error) {
    errorMessage.value = `部署失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    deploying.value = false
  }
}

async function openStatus(model: LlmMarketModel) {
  statusVisible.value = true
  statusLoading.value = true
  deployStatus.value = null
  try {
    deployStatus.value = await openModelsApi.deployStatus(model.model_id)
  } catch (error) {
    errorMessage.value = `部署状态加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    statusLoading.value = false
  }
}

async function openLogs(model: LlmMarketModel) {
  logsVisible.value = true
  logsLoading.value = true
  deployLogs.value = []
  try {
    const result = await openModelsApi.logs(model.model_id)
    deployLogs.value = result.logs ?? []
  } catch (error) {
    errorMessage.value = `部署日志加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    logsLoading.value = false
  }
}

async function stop(model: LlmMarketModel) {
  try {
    await openModelsApi.stop(model.model_id)
    ElMessage.success('停止指令已下发')
    await load()
  } catch (error) {
    errorMessage.value = `停止失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.logs {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
}
</style>
