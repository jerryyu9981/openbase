<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索模型名称 / Provider" clearable style="width: 240px" data-test="category-search" />
      <el-radio-group v-model="dimension" data-test="category-dimension" @change="handleDimensionChange">
        <el-radio-button value="capability">能力</el-radio-button>
        <el-radio-button value="scenario">场景</el-radio-button>
        <el-radio-button value="scale">规模</el-radio-button>
      </el-radio-group>
      <el-tag type="info" data-test="category-result-count">共 {{ filteredModels.length }} 个模型</el-tag>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="category-error"
      @close="errorMessage = ''"
    />

    <el-card v-loading="loading" header="分类标签云" class="mb-16" data-test="tag-cloud-card">
      <el-empty v-if="dimensionTags.length === 0" description="暂无分类标签" :image-size="60" data-test="tag-cloud-empty" />
      <div v-else class="tag-cloud">
        <el-tag
          v-for="tag in dimensionTags"
          :key="tag.name"
          :size="tagSize(tag.count)"
          :type="activeTag === tag.name ? 'primary' : 'info'"
          :effect="activeTag === tag.name ? 'dark' : 'plain'"
          class="cloud-tag"
          data-test="category-tag"
          @click="toggleTag(tag.name)"
        >
          {{ tag.name }} ({{ tag.count }})
        </el-tag>
      </div>
    </el-card>

    <el-card header="模型列表" data-test="category-model-card">
      <div class="ob-table-scroll">
        <el-table :data="filteredModels" stripe empty-text="暂无匹配的模型" data-test="category-table">
          <el-table-column prop="name" label="模型" min-width="140" />
          <el-table-column prop="provider" label="Provider" width="110" />
          <el-table-column label="类型" width="90">
            <template #default="{ row }"><el-tag size="small">{{ row.type }}</el-tag></template>
          </el-table-column>
          <el-table-column label="能力" min-width="150">
            <template #default="{ row }">
              <el-tag v-for="cap in row.capabilities" :key="cap" size="small" class="cap-tag" type="info">{{ cap }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="场景" min-width="150">
            <template #default="{ row }">
              <el-tag v-for="scenario in row.scenarios" :key="scenario" size="small" class="cap-tag" type="success">{{ scenario }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="scale" label="规模" width="120" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

type Dimension = 'capability' | 'scenario' | 'scale'

interface CategoryModel {
  id: number
  name: string
  provider: string
  type: string
  status: string
  capabilities: string[]
  scenarios: string[]
  scale: string
}

const loading = ref(true)
const errorMessage = ref('')
const keyword = ref('')
const dimension = ref<Dimension>('capability')
const activeTag = ref('')

/** 契约 mock：模型分类数据（不调用真实 API） */
const models = ref<CategoryModel[]>([
  { id: 1, name: 'gpt-4o', provider: 'OpenAI', type: '商业', status: 'online', capabilities: ['对话', '多模态', '视觉理解'], scenarios: ['客服', '内容创作'], scale: '超大型(70B+)' },
  { id: 2, name: 'gpt-4o-mini', provider: 'OpenAI', type: '商业', status: 'online', capabilities: ['对话', '多模态'], scenarios: ['客服', '办公协作'], scale: '中小(1B-7B)' },
  { id: 3, name: 'claude-3-5-sonnet', provider: 'Anthropic', type: '商业', status: 'online', capabilities: ['对话', '代码生成', '推理'], scenarios: ['代码助手', '数据分析'], scale: '超大型(70B+)' },
  { id: 4, name: 'qwen2.5-72b', provider: '阿里云', type: '开源', status: 'online', capabilities: ['对话', '代码生成', '推理'], scenarios: ['代码助手', '知识库'], scale: '中大型(7B-70B)' },
  { id: 5, name: 'qwen2.5-7b', provider: 'Ollama', type: '本地', status: 'online', capabilities: ['对话'], scenarios: ['办公协作', '客服'], scale: '中小(1B-7B)' },
  { id: 6, name: 'llama3.2-1b', provider: 'Meta', type: '开源', status: 'offline', capabilities: ['对话'], scenarios: ['办公协作'], scale: '轻量(<1B)' },
  { id: 7, name: 'bge-m3', provider: 'BAAI', type: '开源', status: 'online', capabilities: ['Embedding'], scenarios: ['知识库', '检索增强'], scale: '中小(1B-7B)' },
  { id: 8, name: 'text-embedding-3-large', provider: 'OpenAI', type: '商业', status: 'online', capabilities: ['Embedding'], scenarios: ['知识库', '检索增强'], scale: '超大型(70B+)' },
  { id: 9, name: 'deepseek-coder-33b', provider: 'DeepSeek', type: '开源', status: 'deploying', capabilities: ['代码生成'], scenarios: ['代码助手'], scale: '中大型(7B-70B)' },
  { id: 10, name: 'gemini-1.5-pro', provider: 'Google', type: '商业', status: 'online', capabilities: ['对话', '多模态', '视觉理解'], scenarios: ['数据分析', '内容创作'], scale: '超大型(70B+)' },
])

const tagConfig = computed<{ pick: (model: CategoryModel) => string[] }>(() => {
  if (dimension.value === 'capability') return { pick: (model) => model.capabilities }
  if (dimension.value === 'scenario') return { pick: (model) => model.scenarios }
  return { pick: (model) => [model.scale] }
})

const dimensionTags = computed(() => {
  const counts = new Map<string, number>()
  for (const model of models.value) {
    for (const tag of tagConfig.value.pick(model)) {
      counts.set(tag, (counts.get(tag) ?? 0) + 1)
    }
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
})

const filteredModels = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return models.value.filter((model) => {
    const matchKeyword =
      !kw || model.name.toLowerCase().includes(kw) || model.provider.toLowerCase().includes(kw)
    const matchTag = !activeTag.value || tagConfig.value.pick(model).includes(activeTag.value)
    return matchKeyword && matchTag
  })
})

function tagSize(count: number) {
  if (count >= 3) return 'large'
  if (count >= 2) return 'default'
  return 'small'
}

function toggleTag(name: string) {
  activeTag.value = activeTag.value === name ? '' : name
}

function handleDimensionChange() {
  activeTag.value = ''
}

function statusType(status: string) {
  return { online: 'success', offline: 'info', deploying: 'warning', error: 'danger' }[status] || 'info'
}
function statusLabel(status: string) {
  return { online: '在线', offline: '离线', deploying: '部署中', error: '异常' }[status] || status
}

async function loadCategories() {
  loading.value = true
  errorMessage.value = ''
  try {
    await mockDelay(500) // 契约 mock：模拟拉取分类数据
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '分类数据加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

onMounted(() => {
  void loadCategories()
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
.mb-16 {
  margin-bottom: 16px;
}
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.cloud-tag {
  cursor: pointer;
}
.cap-tag {
  margin-right: 4px;
}
</style>
