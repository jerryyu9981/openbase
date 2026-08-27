<template>
  <div>
    <div class="page-toolbar">
      <h3>模型对比</h3>
      <el-button type="primary" data-test="comparison-add" @click="openDialog">添加对比模型</el-button>
      <el-button :disabled="selectedModels.length < 2" data-test="comparison-clear" @click="clearAll">清空对比</el-button>
      <el-tag type="info" data-test="comparison-count">已选 {{ selectedModels.length }} / {{ maxModels }} 个模型</el-tag>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="comparison-error"
      @close="errorMessage = ''"
    />

    <el-card v-loading="loading" data-test="comparison-card">
      <el-empty
        v-if="selectedModels.length === 0"
        description="请添加至少 2 个模型进行对比"
        :image-size="80"
        data-test="comparison-empty"
      >
        <el-button type="primary" @click="openDialog">添加模型</el-button>
      </el-empty>

      <div v-else class="ob-table-scroll">
        <el-table :data="attributeRows" border data-test="comparison-table">
          <el-table-column prop="label" label="对比项" width="130" fixed />
          <el-table-column v-for="model in selectedModels" :key="model.id" :label="model.name" min-width="160">
            <template #header>
              <div class="column-header">
                <span class="model-col-name">{{ model.name }}</span>
                <el-popconfirm title="确认将该模型移出对比？" data-test="comparison-remove" @confirm="removeModel(model.id)">
                  <template #reference><el-button link type="danger" size="small">移除</el-button></template>
                </el-popconfirm>
              </div>
            </template>
            <template #default="{ row }">
              <span v-if="row.key === 'capabilities'">
                <el-tag v-for="cap in model.capabilities" :key="cap" size="small" type="info" class="cap-tag">{{ cap }}</el-tag>
              </span>
              <span v-else-if="row.key === 'price'">{{ formatPrice(model) }}</span>
              <span v-else>{{ cellValue(model, row.key) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" title="选择对比模型（最多 4 个）" width="640px" data-test="comparison-dialog">
      <el-alert
        v-if="dialogError"
        :title="dialogError"
        type="error"
        show-icon
        closable
        class="mb-16"
        data-test="comparison-dialog-error"
        @close="dialogError = ''"
      />
      <div v-loading="poolLoading">
        <el-empty v-if="poolModels.length === 0" description="暂无可用模型" :image-size="60" data-test="comparison-pool-empty" />
        <el-checkbox-group v-else v-model="dialogSelection" data-test="comparison-checkbox-group">
          <div v-for="model in poolModels" :key="model.id" class="pool-item">
            <el-checkbox
              :value="model.id"
              :disabled="isSelected(model.id) || (dialogSelection.length >= maxModels && !dialogSelection.includes(model.id))"
              data-test="comparison-checkbox"
            >
              <span class="pool-name">{{ model.name }}</span>
              <el-tag size="small" type="info">{{ model.provider }}</el-tag>
              <span class="pool-meta">{{ model.context_length }} · {{ model.speed }}</span>
            </el-checkbox>
          </div>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" data-test="comparison-confirm" @click="confirmAdd">加入对比</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

const maxModels = 4

interface PoolModel {
  id: number
  name: string
  provider: string
  type: string
  capabilities: string[]
  input_price: number
  output_price: number
  context_length: string
  speed: string
  description: string
}

interface AttributeRow {
  key: string
  label: string
}

const loading = ref(true)
const errorMessage = ref('')
const dialogVisible = ref(false)
const dialogError = ref('')
const poolLoading = ref(true)
const dialogSelection = ref<number[]>([])

/** 契约 mock：可对比模型池（不调用真实 API） */
const poolModels = ref<PoolModel[]>([
  { id: 1, name: 'gpt-4o', provider: 'OpenAI', type: '商业', capabilities: ['chat', 'vision'], input_price: 0.005, output_price: 0.015, context_length: '128K', speed: '180 tokens/s', description: '旗舰多模态模型' },
  { id: 2, name: 'gpt-4o-mini', provider: 'OpenAI', type: '商业', capabilities: ['chat', 'vision'], input_price: 0.00015, output_price: 0.0006, context_length: '128K', speed: '320 tokens/s', description: '轻量高效版' },
  { id: 3, name: 'claude-3-5-sonnet', provider: 'Anthropic', type: '商业', capabilities: ['chat', 'code'], input_price: 0.003, output_price: 0.015, context_length: '200K', speed: '150 tokens/s', description: '擅长代码与长文本' },
  { id: 4, name: 'qwen2.5-72b', provider: '阿里云', type: '开源', capabilities: ['chat', 'code', 'reasoning'], input_price: 0.0008, output_price: 0.002, context_length: '128K', speed: '95 tokens/s', description: '开源旗舰模型' },
  { id: 5, name: 'qwen2.5-7b', provider: 'Ollama', type: '本地', capabilities: ['chat'], input_price: 0, output_price: 0, context_length: '32K', speed: '260 tokens/s', description: '本地轻量部署' },
  { id: 6, name: 'bge-m3', provider: 'BAAI', type: '开源', capabilities: ['embedding'], input_price: 0.0002, output_price: 0.0002, context_length: '8K', speed: '400 tokens/s', description: '多语言向量模型' },
  { id: 7, name: 'llama3.1-8b', provider: 'Meta', type: '开源', capabilities: ['chat'], input_price: 0.0001, output_price: 0.0004, context_length: '128K', speed: '210 tokens/s', description: '通用开源模型' },
  { id: 8, name: 'gemini-1.5-pro', provider: 'Google', type: '商业', capabilities: ['chat', 'vision', 'audio'], input_price: 0.00125, output_price: 0.005, context_length: '2M', speed: '140 tokens/s', description: '超长上下文多模态模型' },
])

const selectedModels = ref<PoolModel[]>([])

const attributeRows: AttributeRow[] = [
  { key: 'name', label: '名称' },
  { key: 'provider', label: 'Provider' },
  { key: 'type', label: '类型' },
  { key: 'capabilities', label: '能力' },
  { key: 'price', label: '定价(输入/输出)' },
  { key: 'context', label: '上下文长度' },
  { key: 'speed', label: '速度' },
]

function isSelected(id: number) {
  return selectedModels.value.some((model) => model.id === id)
}

function cellValue(model: PoolModel, key: string): string {
  if (key === 'context') return model.context_length
  if (key === 'speed') return model.speed
  return String(model[key as keyof PoolModel])
}

function formatPrice(model: PoolModel) {
  return `$${model.input_price} / $${model.output_price}`
}

function openDialog() {
  dialogSelection.value = []
  dialogError.value = ''
  dialogVisible.value = true
}

function confirmAdd() {
  if (dialogSelection.value.length === 0) {
    dialogError.value = '请至少选择 1 个模型'
    return
  }
  const added = poolModels.value.filter(
    (model) => dialogSelection.value.includes(model.id) && !isSelected(model.id),
  )
  if (selectedModels.value.length + added.length > maxModels) {
    dialogError.value = `最多只能同时对比 ${maxModels} 个模型`
    return
  }
  selectedModels.value = [...selectedModels.value, ...added]
  dialogVisible.value = false
  ElMessage.success(`已添加 ${added.length} 个模型参与对比`)
}

function removeModel(id: number) {
  const target = selectedModels.value.find((model) => model.id === id)
  selectedModels.value = selectedModels.value.filter((model) => model.id !== id)
  ElMessage.success(`已移除对比模型：${target?.name ?? id}`)
}

function clearAll() {
  selectedModels.value = []
  ElMessage.success('已清空对比列表')
}

async function loadPool() {
  loading.value = true
  poolLoading.value = true
  errorMessage.value = ''
  try {
    await mockDelay(500) // 契约 mock：模拟拉取模型池
    const initialIds = [1, 3]
    selectedModels.value = poolModels.value.filter((model) => initialIds.includes(model.id))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模型数据加载失败，请稍后重试'
  } finally {
    loading.value = false
    poolLoading.value = false
  }
}

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

onMounted(() => {
  void loadPool()
})
</script>

<style scoped>
.page-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.page-toolbar h3 {
  margin: 0;
}
.mb-16 {
  margin-bottom: 12px;
}
.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.model-col-name {
  font-weight: 600;
}
.cap-tag {
  margin-right: 4px;
}
.pool-item {
  padding: 8px 4px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.pool-item:last-child {
  border-bottom: none;
}
.pool-name {
  font-weight: 600;
  margin-right: 8px;
}
.pool-meta {
  color: var(--ob-text-secondary);
  font-size: 12px;
  margin-left: 8px;
}
</style>
