<template>
  <div class="rag-admin">
    <!-- KPI 概览（真实数据） -->
    <el-row :gutter="16" class="mb-16">
      <el-col :span="6">
        <el-card shadow="hover" data-test="rag-kpi">
          <div class="kpi-label">知识库数</div>
          <div class="kpi-value">{{ kpis.kbCount }}</div>
          <div class="kpi-sub">当前页 {{ kbs.length }} 条</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" data-test="rag-kpi">
          <div class="kpi-label">文档总数</div>
          <div class="kpi-value">{{ kpis.docCount.toLocaleString() }}</div>
          <div class="kpi-sub">列表统计</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" data-test="rag-kpi">
          <div class="kpi-label">上游健康度</div>
          <div class="kpi-value">{{ health.status || '-' }}</div>
          <div class="kpi-sub">{{ health.componentsText }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" data-test="rag-kpi">
          <div class="kpi-label">数据来源</div>
          <div class="kpi-value" style="font-size: 18px">OpenRAG</div>
          <div class="kpi-sub">经 rag-proxy 代理</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 知识库管理后台 -->
    <el-card header="知识库管理后台" data-test="rag-admin-card">
      <div class="page-toolbar">
        <el-input v-model="keyword" placeholder="搜索知识库" clearable style="width: 200px" data-test="rag-search" />
        <el-button type="primary" data-test="rag-create" @click="openCreate">新建知识库</el-button>
        <el-button :loading="loading" @click="loadData">刷新</el-button>
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
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="filteredKbs" stripe empty-text="暂无知识库" data-test="rag-kb-table">
          <el-table-column prop="name" label="知识库" min-width="160" />
          <el-table-column prop="document_count" label="文档数" width="90">
            <template #default="{ row }">{{ row.document_count ?? 0 }}</template>
          </el-table-column>
          <el-table-column prop="chunk_strategy" label="分块策略" width="110">
            <template #default="{ row }">{{ row.chunk_strategy || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="healthType(row.status)" size="small" data-test="rag-health">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
              <el-button link type="primary" size="small" @click="openDocuments(row)">文档</el-button>
              <el-popconfirm title="确认删除该知识库？此操作不可恢复" @confirm="removeKb(row)">
                <template #reference>
                  <el-button link type="danger" size="small" data-test="rag-delete">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          data-test="rag-pager"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 新建知识库 -->
    <el-dialog v-model="createOpen" title="新建知识库" width="480px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="createForm.name" placeholder="知识库名称（必填）" data-test="rag-create-name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
        <el-form-item label="分块策略">
          <el-select v-model="createForm.chunk_strategy" placeholder="默认" clearable style="width: 100%">
            <el-option label="固定长度" value="fixed" />
            <el-option label="语义分块" value="semantic" />
          </el-select>
        </el-form-item>
        <el-form-item label="分块大小">
          <el-input-number v-model="createForm.chunk_size" :min="64" :max="4096" :step="64" />
        </el-form-item>
        <el-form-item label="重叠">
          <el-input-number v-model="createForm.chunk_overlap" :min="0" :max="1024" :step="16" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailOpen" title="知识库详情" size="420px">
      <el-descriptions v-if="currentKb" :column="1" border>
        <el-descriptions-item label="名称">{{ currentKb.name }}</el-descriptions-item>
        <el-descriptions-item label="描述">{{ currentKb.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="文档数">{{ currentKb.document_count ?? 0 }}</el-descriptions-item>
        <el-descriptions-item label="分块策略">{{ currentKb.chunk_strategy || '-' }}</el-descriptions-item>
        <el-descriptions-item label="分块大小">{{ currentKb.chunk_size ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="重叠">{{ currentKb.chunk_overlap ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabel(currentKb.status) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(currentKb.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>

    <!-- 文档管理抽屉 -->
    <el-drawer v-model="docOpen" title="文档管理" size="520px">
      <template #default>
        <div class="doc-upload">
          <input ref="fileInput" type="file" hidden @change="onFileChange" />
          <el-button type="primary" :loading="uploading" data-test="rag-upload" @click="pickFile">上传文档</el-button>
          <span v-if="uploadingDoc" class="doc-upload-status">{{ uploadStatusText }}</span>
        </div>
        <el-table v-loading="docsLoading" :data="documents" stripe empty-text="暂无文档" data-test="rag-doc-table">
          <el-table-column prop="filename" label="文件名" min-width="180" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="docStatusType(row.status)" size="small">{{ row.status || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="chunk_count" label="分块" width="80">
            <template #default="{ row }">{{ row.chunk_count ?? 0 }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-popconfirm title="确认删除该文档？" @confirm="removeDocument(row)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ragApi, type RagCollection, type RagDocument } from '@/core/api/rag'

const kbs = ref<RagCollection[]>([])
const documents = ref<RagDocument[]>([])
const keyword = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)
const docsLoading = ref(false)
const creating = ref(false)
const uploading = ref(false)
const errorMessage = ref('')
const createOpen = ref(false)
const detailOpen = ref(false)
const docOpen = ref(false)
const currentKb = ref<RagCollection | null>(null)
const currentDocCollectionId = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const uploadingDoc = ref<RagDocument | null>(null)
const health = reactive({ status: '-', componentsText: '' })

const kpis = computed(() => {
  const docCount = kbs.value.reduce((sum, kb) => sum + (kb.document_count ?? 0), 0)
  return { kbCount: total.value, docCount }
})

const filteredKbs = computed(() => {
  if (!keyword.value) return kbs.value
  return kbs.value.filter((kb) => kb.name.includes(keyword.value))
})

const uploadStatusText = computed(() => {
  const status = String(uploadingDoc.value?.status ?? '').toUpperCase()
  if (status === 'PENDING') return '排队中…'
  if (status === 'PROCESSING') return '解析向量化中…'
  if (status === 'COMPLETED') return '已完成'
  if (status === 'FAILED') return '处理失败'
  return '上传中…'
})

function statusLabel(s?: string) {
  if (!s) return '未知'
  return { ready: '就绪', indexing: '索引中', error: '异常', normal: '正常' }[s] || s
}

function healthType(s?: string) {
  const map: Record<string, 'success' | 'warning' | 'danger'> = { ready: 'success', normal: 'success', indexing: 'warning', error: 'danger' }
  return map[s || ''] || 'info'
}

function docStatusType(s?: string) {
  const status = String(s ?? '').toUpperCase()
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    COMPLETED: 'success',
    PENDING: 'info',
    PROCESSING: 'warning',
    FAILED: 'danger',
  }
  return map[status] || 'info'
}

function formatTime(v?: string) {
  if (!v) return '-'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('zh-CN', { hour12: false })
}

async function loadHealth() {
  try {
    const h = await ragApi.getRagHealth()
    health.status = h.status || '-'
    const comps = h.components || {}
    const fmtComponent = (value: unknown): string => {
      if (value && typeof value === 'object') {
        return String((value as { status?: string }).status ?? '')
      }
      return String(value ?? '')
    }
    health.componentsText = Object.entries(comps)
      .map(([key, value]) => `${key}:${fmtComponent(value)}`)
      .join(' / ')
  } catch {
    health.status = '不可达'
    health.componentsText = '请检查 OpenRAG 服务'
  }
}

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await ragApi.listCollections({ page: page.value, page_size: pageSize })
    kbs.value = result.items || []
    total.value = result.total ?? 0
  } catch (err) {
    errorMessage.value = `知识库列表加载失败：${(err as Error).message || '网络错误'}`
  } finally {
    loading.value = false
  }
  void loadHealth()
}

function openCreate() {
  createForm.name = ''
  createForm.description = ''
  createForm.chunk_strategy = ''
  createForm.chunk_size = 512
  createForm.chunk_overlap = 50
  createOpen.value = true
}

const createForm = reactive({
  name: '',
  description: '',
  chunk_strategy: '',
  chunk_size: 512,
  chunk_overlap: 50,
})

async function submitCreate() {
  if (!createForm.name.trim()) {
    ElMessage.warning('知识库名称必填')
    return
  }
  creating.value = true
  try {
    await ragApi.createCollection({
      name: createForm.name.trim(),
      description: createForm.description || undefined,
      chunk_strategy: createForm.chunk_strategy || undefined,
      chunk_size: createForm.chunk_size,
      chunk_overlap: createForm.chunk_overlap,
    })
    ElMessage.success('知识库创建成功')
    createOpen.value = false
    await loadData()
  } catch {
    // http.ts 已统一错误提示
  } finally {
    creating.value = false
  }
}

async function openDetail(row: RagCollection) {
  try {
    currentKb.value = await ragApi.getCollection(row.id)
  } catch {
    currentKb.value = row
  }
  detailOpen.value = true
}

async function removeKb(row: RagCollection) {
  try {
    await ragApi.deleteCollection(row.id)
    ElMessage.success(`知识库 ${row.name} 已删除`)
    await loadData()
  } catch {
    // http.ts 已统一错误提示
  }
}

async function openDocuments(row: RagCollection) {
  currentDocCollectionId.value = row.id
  docOpen.value = true
  await loadDocuments()
}

async function loadDocuments() {
  if (!currentDocCollectionId.value) return
  docsLoading.value = true
  try {
    const result = await ragApi.listDocuments(currentDocCollectionId.value, { page: 1, page_size: 100 })
    documents.value = result.items || []
  } catch {
    documents.value = []
  } finally {
    docsLoading.value = false
  }
}

function pickFile() {
  fileInput.value?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !currentDocCollectionId.value) return
  uploading.value = true
  uploadingDoc.value = { id: '', filename: file.name, status: 'PENDING' }
  try {
    const result = await ragApi.uploadDocument(currentDocCollectionId.value, file)
    const documentId = result.document_id
    ElMessage.success('文档上传成功，开始解析')
    await pollDocumentStatus(documentId)
  } catch {
    uploadingDoc.value = null
  } finally {
    uploading.value = false
  }
}

let pollTimer: number | undefined

async function pollDocumentStatus(documentId: string) {
  const cid = currentDocCollectionId.value
  for (let attempt = 0; attempt < 60; attempt += 1) {
    await new Promise((resolve) => {
      pollTimer = window.setTimeout(resolve, 2000)
    })
    try {
      const doc = await ragApi.getDocument(cid, documentId)
      uploadingDoc.value = { ...doc, id: documentId }
      const status = String(doc.status ?? '').toUpperCase()
      if (status === 'COMPLETED' || status === 'FAILED') {
        if (status === 'FAILED') ElMessage.error(`文档处理失败：${doc.filename || documentId}`)
        else ElMessage.success(`文档处理完成：${doc.filename || documentId}`)
        uploadingDoc.value = null
        await loadDocuments()
        await loadData()
        return
      }
    } catch {
      uploadingDoc.value = null
      ElMessage.error('文档状态查询失败，请稍后在文档列表中查看')
      return
    }
  }
  uploadingDoc.value = null
  ElMessage.warning('文档处理超时，请稍后在文档列表中刷新查看')
}

async function removeDocument(row: RagDocument) {
  if (!currentDocCollectionId.value) return
  try {
    await ragApi.deleteDocument(currentDocCollectionId.value, row.id)
    ElMessage.success(`文档 ${row.filename || row.id} 已删除`)
    await loadDocuments()
    await loadData()
  } catch {
    // http.ts 已统一错误提示
  }
}

onMounted(() => {
  void loadData()
})

onBeforeUnmount(() => {
  if (pollTimer !== undefined) {
    window.clearTimeout(pollTimer)
  }
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.kpi-label { font-size: 13px; color: #6b7280; }
.kpi-value { font-size: 24px; font-weight: 600; margin: 4px 0; }
.kpi-sub { font-size: 12px; color: #9ca3af; }
.pager { display: flex; justify-content: flex-end; margin-top: 12px; }
.doc-upload { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.doc-upload-status { font-size: 13px; color: var(--ob-text-secondary); }
</style>
