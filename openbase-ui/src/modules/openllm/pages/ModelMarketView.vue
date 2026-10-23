<template>
  <PageContainer title="开源模型市场" description="开源模型检索与引入" test-id="model-market-view-page">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索模型" clearable style="width: 220px" data-test="market-search" />
      <el-input v-model="sourceKeyword" placeholder="按来源筛选" clearable style="width: 160px" data-test="market-category" />
      <el-button type="primary" data-test="market-query" @click="reload">查询</el-button>
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

    <el-row v-loading="loading" :gutter="16">
      <el-col v-for="model in pagedModels" :key="model.id" :span="8" class="mb-16" data-test="market-card">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>{{ model.name }}</span>
              <el-tag size="small" type="info">{{ model.source || '未知来源' }}</el-tag>
            </div>
          </template>
          <p class="model-desc">{{ model.tags.length ? model.tags.join(' · ') : '暂无标签' }}</p>
          <div class="model-meta">
            <el-tag size="small">{{ model.parameters || '未知参数' }}</el-tag>
            <el-tag size="small" type="warning">{{ model.download_status || 'not_downloaded' }}</el-tag>
          </div>
          <div class="card-footer">
            <span class="license">{{ model.license || '未知许可' }}</span>
            <el-button
              type="primary"
              size="small"
              :loading="downloadingId === model.id"
              data-test="market-download"
              @click="download(model)"
            >
              下载部署
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && filteredModels.length === 0" description="无匹配模型" :image-size="80" />

    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="filteredModels.length"
      layout="total, prev, pager, next"
      class="market-pagination"
      data-test="market-pagination"
    />
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { openModelsApi, type LlmMarketModel } from '@/core/api/governance'
import { describeError } from '@/core/api/error'

const loading = ref(false)
const models = ref<LlmMarketModel[]>([])
const keyword = ref('')
const sourceKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(6)
const downloadingId = ref('')
const errorMessage = ref('')

const filteredModels = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const source = sourceKeyword.value.trim().toLowerCase()
  return models.value.filter((model) => {
    const matchKeyword =
      !kw || model.name.toLowerCase().includes(kw) || model.model_id.toLowerCase().includes(kw)
    const matchSource = !source || (model.source || '').toLowerCase().includes(source)
    return matchKeyword && matchSource
  })
})

const pagedModels = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredModels.value.slice(start, start + pageSize.value)
})

function errorText(error: unknown, fallback: string) {
  return describeError(error).detail || fallback
}

async function reload() {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await openModelsApi.list({ page: 1, page_size: 100 })
    models.value = data.items ?? []
    currentPage.value = 1
  } catch (error) {
    errorMessage.value = errorText(error, '开源模型列表加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function download(model: LlmMarketModel) {
  downloadingId.value = model.id
  try {
    await openModelsApi.startDownload(model.model_id)
    ElMessage.success(`模型 ${model.name} 下载任务已创建（可在下载管理中查看进度）`)
  } catch (error) {
    ElMessage.error(errorText(error, '下载任务创建失败'))
  } finally {
    downloadingId.value = ''
  }
}

onMounted(() => {
  void reload()
})
</script>

<style scoped>
.page-toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.mb-16 { margin-bottom: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.model-desc { min-height: 48px; font-size: 13px; color: #475569; line-height: 1.6; }
.model-meta { display: flex; gap: 8px; margin: 8px 0; }
.card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; }
.license { font-size: 12px; color: #909399; }
.market-pagination { margin-top: 16px; justify-content: flex-end; }
</style>
