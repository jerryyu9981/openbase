<template>
  <PageContainer
    title="模型分类"
    description="开源模型的分类归属与分类下模型（数据源：OpenLLM /api/v1/model-categories，经 OpenBase 通用代理）"
    test-id="categories-page"
  >
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索分类名称 / 代码" clearable style="width: 220px" data-test="category-search" />
      <el-radio-group v-model="dimension" data-test="category-dimension" @change="onDimensionChange">
        <el-radio-button value="capability">能力</el-radio-button>
        <el-radio-button value="scene">场景</el-radio-button>
        <el-radio-button value="architecture">架构</el-radio-button>
        <el-radio-button value="scale">规模</el-radio-button>
      </el-radio-group>
      <el-button :loading="loading" data-test="category-refresh" @click="loadTree">刷新</el-button>
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
      <el-empty v-if="dimensionTags.length === 0" description="该维度暂无分类" :image-size="60" data-test="tag-cloud-empty" />
      <div v-else class="tag-cloud">
        <el-tag
          v-for="tag in dimensionTags"
          :key="tag.id"
          :size="tagSize(tag.model_count ?? 0)"
          :type="activeCategory?.id === tag.id ? 'primary' : 'info'"
          :effect="activeCategory?.id === tag.id ? 'dark' : 'plain'"
          class="cloud-tag"
          data-test="category-tag"
          @click="selectCategory(tag)"
        >
          {{ tag.name }} ({{ tag.model_count ?? 0 }})
        </el-tag>
      </div>
    </el-card>

    <el-card :header="activeCategory ? `模型列表 · ${activeCategory.name}` : '模型列表'" data-test="category-model-card">
      <el-empty
        v-if="!activeCategory"
        description="请选择上方分类标签查看该分类下的模型"
        :image-size="60"
        data-test="category-model-empty"
      />
      <template v-else>
        <div class="ob-table-scroll">
          <el-table v-loading="modelsLoading" :data="filteredModels" stripe empty-text="该分类下暂无模型" data-test="category-table">
            <el-table-column label="模型" min-width="220">
              <template #default="{ row }">
                <div class="model-name">{{ row.name }}</div>
                <div class="model-id">{{ row.model_id }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="120" />
            <el-table-column label="架构" width="140">
              <template #default="{ row }">{{ row.architecture || '—' }}</template>
            </el-table-column>
            <el-table-column label="参数规模" width="110">
              <template #default="{ row }">{{ row.parameters || '—' }}</template>
            </el-table-column>
            <el-table-column label="许可证" width="130">
              <template #default="{ row }">{{ row.license || '—' }}</template>
            </el-table-column>
            <el-table-column prop="download_count" label="下载量" width="100" />
            <el-table-column label="部署状态" width="120">
              <template #default="{ row }">
                <el-tag :type="deployType(row.deploy_status)" size="small">{{ deployLabel(row.deploy_status) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-pagination
          v-if="modelTotal > pageSize"
          class="pager"
          layout="prev, pager, next, total"
          :total="modelTotal"
          :page-size="pageSize"
          :current-page="page"
          @current-change="changePage"
        />
      </template>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { modelCategoriesApi, type ModelCategory, type OpenSourceModel } from '@/core/api/governance'

type Dimension = 'capability' | 'scene' | 'architecture' | 'scale'

const loading = ref(false)
const modelsLoading = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const dimension = ref<Dimension>('capability')

const categories = ref<ModelCategory[]>([])
const activeCategory = ref<ModelCategory | null>(null)
const models = ref<OpenSourceModel[]>([])
const modelTotal = ref(0)
const page = ref(1)
const pageSize = 20

/** 拍平分类树（父 → 子），保留层级用于展示 */
function flatten(nodes: ModelCategory[]): ModelCategory[] {
  const rows: ModelCategory[] = []
  for (const node of nodes) {
    rows.push(node)
    if (node.children?.length) rows.push(...flatten(node.children))
  }
  return rows
}

const dimensionTags = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return categories.value
    .filter((item) => item.category_type === dimension.value)
    .filter((item) => !kw || item.name.toLowerCase().includes(kw) || item.code.toLowerCase().includes(kw))
    .sort((a, b) => (b.model_count ?? 0) - (a.model_count ?? 0))
})

const filteredModels = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return models.value
  return models.value.filter(
    (model) => model.name.toLowerCase().includes(kw) || model.model_id.toLowerCase().includes(kw),
  )
})

function tagSize(count: number): 'large' | 'default' | 'small' {
  if (count >= 10) return 'large'
  if (count >= 3) return 'default'
  return 'small'
}

const DEPLOY_LABELS: Record<string, string> = {
  deployed: '已部署',
  deploying: '部署中',
  not_deployed: '未部署',
  stopped: '已停止',
  failed: '失败',
}

function deployLabel(status: string | null): string {
  return status ? DEPLOY_LABELS[status] ?? status : '—'
}

function deployType(status: string | null): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'deployed') return 'success'
  if (status === 'deploying') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

function messageOf(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  return fallback
}

async function loadTree(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const tree = await modelCategoriesApi.tree()
    categories.value = flatten(tree)
    const stillExists = categories.value.find((item) => item.id === activeCategory.value?.id)
    const fallback = dimensionTags.value[0] ?? null
    if (stillExists) {
      await selectCategory(stillExists)
    } else if (fallback) {
      await selectCategory(fallback)
    } else {
      activeCategory.value = null
      models.value = []
      modelTotal.value = 0
    }
  } catch (error) {
    errorMessage.value = `分类加载失败：${messageOf(error, '未知错误')}`
  } finally {
    loading.value = false
  }
}

async function selectCategory(category: ModelCategory): Promise<void> {
  activeCategory.value = category
  page.value = 1
  await loadModels()
}

async function loadModels(): Promise<void> {
  if (!activeCategory.value) return
  modelsLoading.value = true
  try {
    const result = await modelCategoriesApi.models(activeCategory.value.id, {
      page: page.value,
      page_size: pageSize,
    })
    models.value = result.items
    modelTotal.value = result.total
  } catch (error) {
    models.value = []
    modelTotal.value = 0
    errorMessage.value = `模型列表加载失败：${messageOf(error, '未知错误')}`
  } finally {
    modelsLoading.value = false
  }
}

function changePage(next: number): void {
  page.value = next
  void loadModels()
}

async function onDimensionChange(): Promise<void> {
  const first = dimensionTags.value[0] ?? null
  if (first) {
    await selectCategory(first)
  } else {
    activeCategory.value = null
    models.value = []
    modelTotal.value = 0
  }
}

onMounted(() => {
  void loadTree()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.tag-cloud { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.cloud-tag { cursor: pointer; }
.model-name { font-weight: 500; }
.model-id { color: var(--ob-text-secondary); font-size: 12px; word-break: break-all; }
.pager { margin-top: 12px; justify-content: flex-end; }
</style>
