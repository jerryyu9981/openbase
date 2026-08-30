<template>
  <div class="model-market">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索模型" clearable style="width: 220px" data-test="market-search" />
      <el-select v-model="category" placeholder="分类" clearable style="width: 160px" data-test="market-category">
        <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
      </el-select>
      <el-button type="primary" data-test="market-query" @click="filtered = applyFilter()">查询</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="market-error"
      @close="errorMessage = ''"
    />

    <el-row :gutter="16">
      <el-col v-for="model in pagedModels" :key="model.id" :span="8" class="mb-16" data-test="market-card">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>{{ model.name }}</span>
              <el-tag size="small" type="info">{{ model.category }}</el-tag>
            </div>
          </template>
          <p class="model-desc">{{ model.description }}</p>
          <div class="model-meta">
            <el-tag size="small">{{ model.params }}B</el-tag>
            <el-tag size="small" type="warning">{{ model.size }}</el-tag>
          </div>
          <div class="card-footer">
            <span class="license">{{ model.license }}</span>
            <el-button type="primary" size="small" :loading="downloadingId === model.id" data-test="market-download" @click="download(model)">
              下载部署
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="filtered.length === 0" description="无匹配模型" :image-size="80" />

    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="filtered.length"
      :page-sizes="[6, 12, 24]"
      layout="total, sizes, prev, pager, next"
      class="market-pagination"
      data-test="market-pagination"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface MarketModel {
  id: string
  name: string
  category: string
  description: string
  params: number
  size: string
  license: string
}

const mockModels: MarketModel[] = [
  { id: 'llama3-8b', name: 'Llama 3 8B', category: '通用', description: 'Meta 开源通用大模型，支持对话/代码/推理。', params: 8, size: '4.9GB', license: 'Llama 3 License' },
  { id: 'qwen2-7b', name: 'Qwen2 7B', category: '通用', description: '通义千问开源版，中文能力强，支持多轮对话。', params: 7, size: '4.4GB', license: 'Apache 2.0' },
  { id: 'deepseek-coder-6.7b', name: 'DeepSeek Coder 6.7B', category: '代码', description: '代码生成/补全专用模型，支持多语言。', params: 6.7, size: '3.8GB', license: 'DeepSeek License' },
  { id: 'chatglm3-6b', name: 'ChatGLM3 6B', category: '通用', description: '智谱开源对话模型，中文场景优化。', params: 6, size: '6.4GB', license: 'MIT' },
  { id: 'bge-large-zh', name: 'BGE Large ZH', category: '向量', description: '中文向量检索模型，用于 RAG 检索。', params: 0.33, size: '1.3GB', license: 'MIT' },
  { id: 'whisper-small', name: 'Whisper Small', category: '语音', description: 'OpenAI 开源语音识别模型。', params: 0.244, size: '484MB', license: 'MIT' },
  { id: 'sd-xl-base', name: 'SDXL Base', category: '图像', description: 'Stable Diffusion XL 图像生成基座。', params: 3.5, size: '7GB', license: 'OpenRAIL' },
  { id: 'qwen2.5-14b', name: 'Qwen2.5 14B', category: '通用', description: 'Qwen2.5 系列中尺寸版本，综合能力强。', params: 14, size: '9.1GB', license: 'Apache 2.0' },
]

const categories = ['通用', '代码', '向量', '语音', '图像']
const keyword = ref('')
const category = ref('')
const filtered = ref<MarketModel[]>(mockModels)
const currentPage = ref(1)
const pageSize = ref(6)
const downloadingId = ref('')
const errorMessage = ref('')

const pagedModels = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

function applyFilter(): MarketModel[] {
  const kw = keyword.value.trim().toLowerCase()
  return mockModels.filter((m) => {
    const matchKw = !kw || m.name.toLowerCase().includes(kw) || m.description.toLowerCase().includes(kw)
    const matchCat = !category.value || m.category === category.value
    return matchKw && matchCat
  })
}

function download(model: MarketModel) {
  downloadingId.value = model.id
  setTimeout(() => {
    downloadingId.value = ''
    ElMessage.success(`模型 ${model.name} 下载任务已创建（可在下载管理中查看进度）`)
  }, 600)
}
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.model-desc { min-height: 48px; font-size: 13px; color: #475569; line-height: 1.6; }
.model-meta { display: flex; gap: 8px; margin: 8px 0; }
.card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; }
.license { font-size: 12px; color: #909399; }
.market-pagination { margin-top: 16px; justify-content: flex-end; }
</style>
