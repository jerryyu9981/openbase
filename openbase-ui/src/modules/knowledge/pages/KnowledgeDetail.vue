<template>
  <PageContainer description="知识库详情：文档管理、检索问答与配置维护" test-id="knowledge-detail-page">
    <el-page-header :content="`知识库：${collection?.name || '详情'}`" class="mb-16" @back="$router.push('/knowledge/list')" />

    <el-alert
      v-if="loadError"
      :title="loadError"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="knowledge-error"
      @close="loadError = ''"
    >
      <template #default>
        <el-button link type="primary" size="small" data-test="knowledge-retry" @click="loadAll">点击重试</el-button>
      </template>
    </el-alert>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="10">
        <el-card class="mb-16" data-test="collection-info">
          <template #header>
            <div class="card-head">
              <span>知识库信息</span>
              <el-button link type="primary" :disabled="!collection" data-test="collection-edit-open" @click="openEdit">
                编辑配置
              </el-button>
            </div>
          </template>
          <el-descriptions v-if="collection" :column="1" border size="small">
            <el-descriptions-item label="名称">{{ collection.name }}</el-descriptions-item>
            <el-descriptions-item label="描述">{{ collection.description || '-' }}</el-descriptions-item>
            <el-descriptions-item label="分块策略">{{ collection.chunk_strategy || '-' }}</el-descriptions-item>
            <el-descriptions-item label="分块大小">{{ collection.chunk_size ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="重叠长度">{{ collection.chunk_overlap ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="文档数">{{ collection.document_count ?? documents.length }}</el-descriptions-item>
          </el-descriptions>
          <el-empty v-else-if="!loading" description="知识库不存在或无权限" :image-size="50" />
        </el-card>

        <el-card class="mb-16" data-test="document-panel">
          <template #header>
            <div class="card-head">
              <span>文档管理</span>
              <el-tag v-if="uploadingCount > 0" size="small" type="warning" data-test="uploading-hint">
                正在处理 {{ uploadingCount }} 个文档…
              </el-tag>
            </div>
          </template>
          <el-upload
            drag
            multiple
            :show-file-list="false"
            :http-request="handleUpload"
            accept=".pdf,.docx,.md,.html,.txt"
            data-test="doc-upload"
            class="uploader"
          >
            <el-icon size="32"><UploadFilled /></el-icon>
            <div>拖拽或点击上传文档（PDF/DOCX/MD/HTML/TXT ≤100MB）</div>
          </el-upload>
          <div class="ob-table-scroll mt-16">
            <el-table v-loading="documentsLoading" :data="documents" size="small" data-test="document-table">
              <el-table-column label="文档" min-width="140">
                <template #default="{ row }">{{ row.filename || row.id }}</template>
              </el-table-column>
              <el-table-column prop="chunk_count" label="分块" width="70" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="docStatusType(row.status)" size="small">{{ docStatusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <el-button link type="primary" data-test="doc-reindex" @click="reindex(row)">重建索引</el-button>
                  <el-button link type="danger" data-test="doc-delete" @click="removeDoc(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-if="!documentsLoading && documents.length === 0" description="暂无文档，请先上传" :image-size="50" />
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="14">
        <el-card data-test="retrieval-panel">
          <template #header>
            <div class="card-head">
              <span>检索测试台</span>
              <el-radio-group v-model="mode" size="small" data-test="retrieval-mode">
                <el-radio-button value="retrieve">纯检索</el-radio-button>
                <el-radio-button value="query">RAG 问答</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div class="test-toolbar">
            <el-input v-model="queryText" placeholder="输入查询内容" data-test="retrieval-query" @keyup.enter="runRetrieval" />
            <el-select v-model="topK" style="width: 110px" data-test="retrieval-topk">
              <el-option :value="5" label="top 5" />
              <el-option :value="10" label="top 10" />
              <el-option :value="20" label="top 20" />
            </el-select>
            <el-button type="primary" :loading="searching" data-test="retrieval-run" @click="runRetrieval">运行</el-button>
          </div>
          <el-divider />

          <template v-if="mode === 'query'">
            <div v-if="answer" class="answer-block" data-test="rag-answer">{{ answer }}</div>
            <div v-for="(source, index) in sources" :key="index" class="result-item" data-test="rag-source">
              <div class="result-head">
                <span>{{ source.doc_name || source.chunk_id || `来源 ${index + 1}` }}</span>
                <el-tag v-if="source.score !== undefined" size="small" :type="scoreType(source.score)">score {{ source.score }}</el-tag>
              </div>
              <p class="result-content">{{ source.snippet || source.content }}</p>
            </div>
          </template>
          <template v-else>
            <div v-for="item in retrieveItems" :key="item.chunk_id" class="result-item" data-test="retrieval-result">
              <div class="result-head">
                <span>{{ item.chunk_id || '片段' }}</span>
                <el-tag v-if="item.score !== undefined" size="small" :type="scoreType(item.score)">score {{ item.score }}</el-tag>
              </div>
              <p class="result-content">{{ item.content }}</p>
            </div>
          </template>

          <el-empty v-if="searched && !hasResults" description="无检索结果" :image-size="60" data-test="retrieval-empty" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="editVisible" title="编辑知识库配置" width="520px" data-test="collection-edit-dialog">
      <el-form label-width="110px">
        <el-form-item label="名称" required>
          <el-input v-model="editForm.name" data-test="collection-name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="2" data-test="collection-description" />
        </el-form-item>
        <el-form-item label="分块策略">
          <el-select v-model="editForm.chunk_strategy" data-test="collection-chunk-strategy">
            <el-option v-for="strategy in CHUNK_STRATEGIES" :key="strategy.value" :label="strategy.label" :value="strategy.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="分块大小">
          <el-input-number v-model="editForm.chunk_size" :min="100" :max="8192" :step="100" data-test="collection-chunk-size" />
        </el-form-item>
        <el-form-item label="重叠长度">
          <el-input-number v-model="editForm.chunk_overlap" :min="0" :max="1024" :step="10" data-test="collection-chunk-overlap" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="collection-edit-save" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import {
  ragApi,
  type RagCollection,
  type RagCollectionUpdate,
  type RagDocument,
  type RagSource,
  type RetrieveItem,
} from '@/core/api/rag'
import { describeError } from '@/core/api/error'

const route = useRoute()
const collectionId = String(route.params.id || '')

const collection = ref<RagCollection | null>(null)
const documents = ref<RagDocument[]>([])
const loading = ref(false)
const documentsLoading = ref(false)
const loadError = ref('')
const uploadingCount = ref(0)

const mode = ref<'retrieve' | 'query'>('retrieve')
const queryText = ref('')
const topK = ref(5)
const searching = ref(false)
const searched = ref(false)
const retrieveItems = ref<RetrieveItem[]>([])
const answer = ref('')
const sources = ref<RagSource[]>([])

const editVisible = ref(false)
const saving = ref(false)
const editForm = ref<RagCollectionUpdate>({})

const CHUNK_STRATEGIES = [
  { value: 'structured', label: '结构感知（structured）' },
  { value: 'fixed', label: '固定长度（fixed）' },
  { value: 'paragraph', label: '段落（paragraph）' },
  { value: 'semantic', label: '语义（semantic）' },
  { value: 'late', label: '延迟分块（late）' },
  { value: 'multi_granularity', label: '多粒度（multi_granularity）' },
  { value: 'late_chunking', label: 'Late Chunking（late_chunking）' },
]

/** 文档状态（OpenRAG 对外枚举为大写）→ 中文标签 */
const DOC_STATUS_LABELS: Record<string, string> = {
  PENDING: '待处理',
  PARSING: '解析中',
  CHUNKING: '分块中',
  EMBEDDING: '向量化',
  INDEXING: '索引中',
  PROCESSING: '处理中',
  COMPLETED: '完成',
  FAILED: '失败',
}

const POLL_INTERVAL_MS = 2000
const POLL_TIMEOUT_MS = 120_000

/** 轮询定时器集合：组件卸载时统一清理，避免泄漏 */
const pollTimers = new Set<number>()

const hasResults = computed(() =>
  mode.value === 'query' ? Boolean(answer.value) || sources.value.length > 0 : retrieveItems.value.length > 0,
)

function normalizeStatus(status?: string): string {
  return String(status || '').toUpperCase()
}

function docStatusLabel(status?: string): string {
  const key = normalizeStatus(status)
  return DOC_STATUS_LABELS[key] || status || '-'
}

function docStatusType(status?: string): 'success' | 'danger' | 'info' | 'warning' {
  const key = normalizeStatus(status)
  if (key === 'COMPLETED') return 'success'
  if (key === 'FAILED') return 'danger'
  if (key === 'PENDING') return 'info'
  return 'warning'
}

function scoreType(score?: number): 'success' | 'warning' | 'danger' {
  const value = Number(score ?? 0)
  return value >= 0.7 ? 'success' : value >= 0.5 ? 'warning' : 'danger'
}

async function loadCollection() {
  collection.value = await ragApi.getCollection(collectionId)
}

async function loadDocuments() {
  documentsLoading.value = true
  try {
    const result = await ragApi.listDocuments(collectionId, { page: 1, page_size: 50 })
    documents.value = result.items || []
  } finally {
    documentsLoading.value = false
  }
}

/** 首屏并发加载集合信息与文档列表；失败统一提示并可重试 */
async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    await Promise.all([loadCollection(), loadDocuments()])
  } catch (err) {
    loadError.value = `知识库加载失败：${describeError(err).detail || '网络错误'}`
  } finally {
    loading.value = false
  }
}

/** 轮询单篇文档直至终态（COMPLETED/FAILED）或超时 */
function waitDocumentTerminal(documentId: string): Promise<RagDocument> {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + POLL_TIMEOUT_MS
    const tick = async () => {
      try {
        const document = await ragApi.getDocument(collectionId, documentId)
        const status = normalizeStatus(document.status)
        documents.value = documents.value.map((row) =>
          row.id === documentId ? { ...row, ...document } : row,
        )
        if (status === 'COMPLETED') {
          resolve(document)
          return
        }
        if (status === 'FAILED') {
          reject(new Error('文档处理失败'))
          return
        }
        if (Date.now() >= deadline) {
          reject(new Error('文档处理超时'))
          return
        }
        pollTimers.add(window.setTimeout(tick, POLL_INTERVAL_MS))
      } catch (err) {
        reject(err)
      }
    }
    void tick()
  })
}

/** el-upload 自定义上传：上传 → 轮询至终态 → 刷新列表 */
async function handleUpload(options: { file: File }) {
  uploadingCount.value += 1
  try {
    const { document_id: documentId } = await ragApi.uploadDocument(collectionId, options.file)
    ElMessage.info(`已上传 ${options.file.name}，正在处理…`)
    try {
      await waitDocumentTerminal(documentId)
      ElMessage.success(`${options.file.name} 处理完成`)
    } catch (err) {
      ElMessage.warning(`${options.file.name} 处理未完成：${(err as Error)?.message || '请稍后在列表中确认'}`)
    }
    await loadDocuments()
  } catch (err) {
    ElMessage.error(`上传失败：${describeError(err).detail || '网络错误'}`)
  } finally {
    uploadingCount.value -= 1
  }
}

async function reindex(row: RagDocument) {
  try {
    await ragApi.retryDocument(collectionId, row.id)
    ElMessage.success('已提交重建索引')
    await loadDocuments()
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    ElMessage.error(status === 429 ? '操作过于频繁，请 60 秒后重试' : '重建索引失败，请稍后重试')
  }
}

async function removeDoc(row: RagDocument) {
  try {
    await ElMessageBox.confirm(`确认删除文档「${row.filename || row.id}」？删除后不可恢复。`, '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await ragApi.deleteDocument(collectionId, row.id)
    ElMessage.success('文档已删除')
    await loadDocuments()
  } catch {
    ElMessage.error('删除失败，请稍后重试')
  }
}

/** 检索/问答：按模式调用 retrieve 或 query，结果分别渲染 */
async function runRetrieval() {
  const text = queryText.value.trim()
  if (!text) {
    ElMessage.warning('请输入查询内容')
    return
  }
  searching.value = true
  searched.value = false
  try {
    if (mode.value === 'retrieve') {
      const result = await ragApi.retrieve(collectionId, { query: text, top_k: topK.value })
      retrieveItems.value = result.items || []
      answer.value = ''
      sources.value = []
    } else {
      const result = await ragApi.query(collectionId, { query: text, top_k: topK.value })
      answer.value = result.answer || ''
      sources.value = result.sources || []
      retrieveItems.value = []
    }
    searched.value = true
  } catch (err) {
    ElMessage.error(`检索失败：${describeError(err).detail || '网络错误'}`)
  } finally {
    searching.value = false
  }
}

function openEdit() {
  if (!collection.value) return
  editForm.value = {
    name: collection.value.name,
    description: collection.value.description || '',
    chunk_strategy: collection.value.chunk_strategy || 'structured',
    chunk_size: Number(collection.value.chunk_size ?? 1024),
    chunk_overlap: Number(collection.value.chunk_overlap ?? 128),
  }
  editVisible.value = true
}

/** 保存配置：分块参数变更时二次确认并携带 rebuild=true（触发存量重建） */
async function saveEdit() {
  const name = String(editForm.value.name || '').trim()
  if (!name) {
    ElMessage.warning('知识库名称不能为空')
    return
  }
  const chunkChanged =
    editForm.value.chunk_strategy !== collection.value?.chunk_strategy ||
    editForm.value.chunk_size !== collection.value?.chunk_size ||
    editForm.value.chunk_overlap !== collection.value?.chunk_overlap

  if (chunkChanged) {
    try {
      await ElMessageBox.confirm('分块配置变更将触发存量文档重建，可能耗时较长，确认继续？', '重建确认', {
        type: 'warning',
      })
    } catch {
      return
    }
  }

  saving.value = true
  try {
    const payload: RagCollectionUpdate = {
      name,
      description: String(editForm.value.description || ''),
      chunk_strategy: editForm.value.chunk_strategy,
      chunk_size: editForm.value.chunk_size,
      chunk_overlap: editForm.value.chunk_overlap,
    }
    await ragApi.updateCollection(collectionId, payload, chunkChanged)
    ElMessage.success(chunkChanged ? '配置已更新，存量文档开始重建' : '配置已更新')
    editVisible.value = false
    await loadCollection()
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 409) {
      ElMessage.error('配置冲突或 embedding 参数不支持在线变更，请刷新后重试')
    } else {
      ElMessage.error(`保存失败：${describeError(err).detail || '网络错误'}`)
    }
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void loadAll()
})

onBeforeUnmount(() => {
  pollTimers.forEach((timer) => window.clearTimeout(timer))
  pollTimers.clear()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-16 { margin-top: 16px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.uploader { width: 100%; }
.test-toolbar { display: flex; gap: 12px; flex-wrap: wrap; }
.answer-block {
  padding: 12px; background: #f0f9ff; border-radius: 6px; font-size: 13px;
  line-height: 1.7; white-space: pre-wrap; margin-bottom: 12px;
}
.result-item { border-bottom: 1px dashed var(--ob-border); padding: 8px 0; }
.result-head { display: flex; justify-content: space-between; font-weight: 600; font-size: 13px; }
.result-content { color: var(--ob-text-secondary); font-size: 13px; margin: 6px 0 0; }
</style>
