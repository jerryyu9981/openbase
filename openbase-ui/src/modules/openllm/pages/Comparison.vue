<template>
  <PageContainer title="模型对比" description="多模型效果与成本对比" test-id="comparison-page">
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
              <span v-if="row.key === 'tags'">
                <el-tag v-for="tag in model.tags" :key="tag" size="small" type="info" class="cap-tag">{{ tag }}</el-tag>
                <span v-if="model.tags.length === 0">-</span>
              </span>
              <span v-else-if="row.key === 'advantage'">{{ advantageOf(model.name) }}</span>
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
              <el-tag size="small" type="info">{{ model.source || '未知来源' }}</el-tag>
              <span class="pool-meta">{{ model.parameters || '未知参数' }} · {{ model.license || '未知许可' }}</span>
            </el-checkbox>
          </div>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" data-test="comparison-confirm" @click="confirmAdd">加入对比</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  modelCompareApi,
  openModelsApi,
  type LlmMarketModel,
} from '@/core/api/governance'
import { describeError } from '@/core/api/error'

const maxModels = 4

interface AttributeRow {
  key: string
  label: string
}

const loading = ref(false)
const errorMessage = ref('')
const dialogVisible = ref(false)
const dialogError = ref('')
const poolLoading = ref(false)
const dialogSelection = ref<string[]>([])
const poolModels = ref<LlmMarketModel[]>([])
const selectedModels = ref<LlmMarketModel[]>([])
const advantages = ref<Record<string, string>>({})
const compared = ref(false)

const attributeRows: AttributeRow[] = [
  { key: 'name', label: '名称' },
  { key: 'source', label: '来源' },
  { key: 'parameters', label: '参数规模' },
  { key: 'license', label: '许可证' },
  { key: 'tags', label: '标签' },
  { key: 'advantage', label: '对比结论' },
]

function isSelected(id: string) {
  return selectedModels.value.some((model) => model.id === id)
}

function cellValue(model: LlmMarketModel, key: string): string {
  const value = (model as unknown as Record<string, unknown>)[key]
  return value ? String(value) : '-'
}

function advantageOf(name: string) {
  return compared.value ? advantages.value[name] || '无明显优势' : '对比后生成'
}

function errorText(error: unknown, fallback: string) {
  return describeError(error).detail || fallback
}

async function loadPool() {
  poolLoading.value = true
  errorMessage.value = ''
  try {
    const data = await openModelsApi.list({ page: 1, page_size: 100 })
    poolModels.value = data.items ?? []
  } catch (error) {
    errorMessage.value = errorText(error, '模型数据加载失败，请稍后重试')
  } finally {
    poolLoading.value = false
  }
}

async function runCompare() {
  if (selectedModels.value.length < 2) {
    advantages.value = {}
    compared.value = false
    return
  }
  loading.value = true
  try {
    const result = await modelCompareApi.compare(selectedModels.value.map((model) => model.id))
    const raw = (result.comparison?.advantages ?? {}) as Record<string, string>
    advantages.value = raw
    compared.value = true
  } catch (error) {
    errorMessage.value = errorText(error, '模型对比计算失败')
    compared.value = false
  } finally {
    loading.value = false
  }
}

function openDialog() {
  dialogSelection.value = []
  dialogError.value = ''
  dialogVisible.value = true
}

async function confirmAdd() {
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
  await runCompare()
}

async function removeModel(id: string) {
  const target = selectedModels.value.find((model) => model.id === id)
  selectedModels.value = selectedModels.value.filter((model) => model.id !== id)
  ElMessage.success(`已移除对比模型：${target?.name ?? id}`)
  await runCompare()
}

function clearAll() {
  selectedModels.value = []
  advantages.value = {}
  compared.value = false
  ElMessage.success('已清空对比列表')
}

onMounted(() => {
  void loadPool()
})
</script>

<style scoped>
.page-toolbar h3 {
  margin: 0;
}
.page-toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
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
