<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索知识库" clearable style="width: 240px" data-test="kb-search" />
      <el-button type="primary" data-test="create-kb" @click="dialogVisible = true">创建知识库</el-button>
      <el-button :loading="loading" data-test="kb-refresh" @click="loadData">刷新</el-button>
    </div>
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      @close="errorMessage = ''"
    >
      <template #default>
        <el-button link type="primary" size="small" @click="loadData">点击重试</el-button>
      </template>
    </el-alert>
    <el-row v-loading="loading" :gutter="16">
      <el-col v-for="kb in paged" :key="kb.id" :xs="24" :sm="12" :lg="8">
        <el-card class="kb-card" data-test="kb-card">
          <h3 @click="$router.push(`/knowledge/${kb.id}`)">{{ kb.name }}</h3>
          <p class="meta">文档 {{ kb.documents }} · 策略 {{ kb.chunk_strategy }} · {{ createdText(kb) }}</p>
          <div class="card-actions">
            <el-button size="small" type="primary" plain @click="$router.push(`/knowledge/${kb.id}`)">进入</el-button>
            <el-popconfirm title="确认删除该知识库？此操作不可恢复" @confirm="remove(kb.id)">
              <template #reference><el-button size="small" type="danger" plain>删除</el-button></template>
            </el-popconfirm>
          </div>
        </el-card>
      </el-col>
      <el-col v-if="paged.length === 0 && !loading" :span="24">
        <el-empty description="暂无知识库，点击右上角创建" />
      </el-col>
    </el-row>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="filtered.length"
        layout="total, prev, pager, next"
        background
      />
    </div>
    <el-dialog v-model="dialogVisible" title="创建知识库" width="480px">
      <el-form label-width="110px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="知识库名称" data-test="kb-name-input" />
        </el-form-item>
        <el-form-item label="分块策略">
          <el-select v-model="form.chunk_strategy" style="width: 100%" clearable placeholder="默认">
            <el-option label="固定长度" value="fixed" />
            <el-option label="语义分块" value="semantic" />
          </el-select>
        </el-form-item>
        <el-form-item label="分块大小">
          <el-input-number v-model="form.chunk_size" :min="64" :max="4096" :step="64" />
        </el-form-item>
        <el-form-item label="重叠">
          <el-input-number v-model="form.chunk_overlap" :min="0" :max="1024" :step="16" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" data-test="create-kb-submit" @click="createKb">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ragApi, type RagCollection } from '@/core/api/rag'

interface CardKB {
  id: string
  name: string
  documents: number
  chunk_strategy: string
  created_at?: string
}

const keyword = ref('')
const dialogVisible = ref(false)
const loading = ref(false)
const creating = ref(false)
const errorMessage = ref('')
const page = ref(1)
const pageSize = 6
const form = reactive({ name: '', chunk_strategy: '' as string | undefined, chunk_size: 512, chunk_overlap: 0 })
const kbs = ref<CardKB[]>([])

function toCard(item: RagCollection): CardKB {
  return {
    id: item.id,
    name: item.name,
    documents: Number(item.document_count ?? item.documents ?? 0) || 0,
    chunk_strategy: item.chunk_strategy || '默认',
    created_at: item.created_at,
  }
}

function createdText(kb: CardKB): string {
  if (!kb.created_at) return '—'
  const d = new Date(kb.created_at)
  return Number.isNaN(d.getTime()) ? kb.created_at.slice(0, 10) : d.toLocaleDateString('zh-CN')
}

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return kbs.value.filter((kb) => !kw || kb.name.toLowerCase().includes(kw))
})
const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await ragApi.listCollections({ page: 1, page_size: 100 })
    kbs.value = (result.items || []).map(toCard)
  } catch (err) {
    kbs.value = []
    errorMessage.value = `知识库列表加载失败：${(err as Error).message || '网络错误'}`
  } finally {
    loading.value = false
  }
}

async function createKb() {
  if (!form.name.trim()) { ElMessage.warning('请输入知识库名称'); return }
  creating.value = true
  errorMessage.value = ''
  try {
    await ragApi.createCollection({
      name: form.name.trim(),
      chunk_strategy: form.chunk_strategy || undefined,
      chunk_size: form.chunk_size,
      chunk_overlap: form.chunk_overlap,
    })
    form.name = ''
    form.chunk_strategy = undefined
    dialogVisible.value = false
    ElMessage.success('知识库已创建')
    await loadData()
  } catch (err) {
    errorMessage.value = `知识库创建失败：${(err as Error).message || '网络错误'}`
  } finally {
    creating.value = false
  }
}

async function remove(id: string) {
  try {
    await ragApi.deleteCollection(id)
    ElMessage.success('知识库已删除')
    await loadData()
  } catch (err) {
    errorMessage.value = `知识库删除失败：${(err as Error).message || '网络错误'}`
  }
}

onMounted(() => {
  void loadData()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.kb-card { margin-bottom: 16px; }
.kb-card h3 { margin: 0 0 8px; cursor: pointer; }
.meta { color: var(--ob-text-secondary); font-size: 13px; margin-bottom: 10px; }
.card-actions { display: flex; gap: 8px; }
.pager { margin-top: 8px; display: flex; justify-content: flex-end; }
</style>
