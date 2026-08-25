<template>
  <div>
    <el-page-header @back="$router.push('/knowledge/list')" :content="`知识库：${kb?.name || '详情'}`" class="mb-16" />
    <el-row :gutter="16">
      <el-col :xs="24" :lg="10">
        <el-card header="文档管理" class="mb-16">
          <el-upload drag multiple :auto-upload="false" data-test="doc-upload" class="uploader">
            <el-icon size="32"><UploadFilled /></el-icon>
            <div>拖拽或点击上传文档（PDF/DOCX/MD/HTML/TXT ≤100MB）</div>
          </el-upload>
          <div class="ob-table-scroll mt-16">
            <el-table :data="documents" size="small">
              <el-table-column prop="name" label="文档" min-width="140" />
              <el-table-column label="状态" width="200">
                <template #default="{ row }">
                  <el-tag :type="docStatusType(row.status)" size="small">{{ docStatusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button link type="primary" @click="reindex(row)">重新索引</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="14">
        <el-card header="检索测试台" class="mb-16">
          <div class="test-toolbar">
            <el-input v-model="query" placeholder="输入查询内容" data-test="retrieval-query" />
            <el-select v-model="agentMode" style="width: 170px">
              <el-option label="standard" value="standard" />
              <el-option label="self_rag" value="self_rag" />
              <el-option label="corrective" value="corrective" />
              <el-option label="adaptive" value="adaptive" />
            </el-select>
            <el-button type="primary" data-test="retrieval-run" @click="runRetrieval">检索</el-button>
          </div>
          <el-divider />
          <div v-for="r in results" :key="r.chunk_id" class="result-item">
            <div class="result-head">
              <span>{{ r.filename }}</span>
              <el-tag size="small" :type="scoreType(r.score)">score {{ r.score }}</el-tag>
            </div>
            <p class="result-content">{{ r.content }}</p>
          </div>
          <el-empty v-if="searched && results.length === 0" description="无检索结果" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { UploadFilled } from '@element-plus/icons-vue'

interface DocumentRow { id: number; name: string; status: string }
interface RetrievalResult { chunk_id: string; filename: string; content: string; score: number }

const route = useRoute()
const kb = computed(() => ({ id: route.params.id, name: `知识库 #${route.params.id}` }))
const documents = ref<DocumentRow[]>([
  { id: 1, name: '快速开始.md', status: 'completed' },
  { id: 2, name: 'API 参考.pdf', status: 'embedding' },
  { id: 3, name: '架构设计.docx', status: 'error' },
])
const query = ref('')
const agentMode = ref('standard')
const searched = ref(false)
const results = ref<RetrievalResult[]>([])

function docStatusType(status: string) {
  return { pending: 'info', parsing: 'info', chunking: 'warning', embedding: 'warning', indexing: 'warning', completed: 'success', error: 'danger' }[status] || 'info'
}
function docStatusLabel(status: string) {
  return { pending: '待处理', parsing: '解析中', chunking: '分块中', embedding: '向量化', indexing: '索引中', completed: '完成', error: '失败' }[status] || status
}
function scoreType(score: number) { return score >= 0.7 ? 'success' : score >= 0.5 ? 'warning' : 'danger' }

function runRetrieval() {
  searched.value = true
  results.value = [
    { chunk_id: 'c1', filename: '快速开始.md', content: 'OpenBase 提供统一登录与动态模块挂载能力……', score: 0.86 },
    { chunk_id: 'c2', filename: 'API 参考.pdf', content: 'POST /api/v1/auth/login 获取 JWT……', score: 0.72 },
  ]
}
function reindex(row: DocumentRow) {
  row.status = 'indexing'
  setTimeout(() => { row.status = 'completed' }, 800)
}
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-16 { margin-top: 16px; }
.uploader { width: 100%; }
.test-toolbar { display: flex; gap: 12px; flex-wrap: wrap; }
.result-item { border-bottom: 1px dashed var(--ob-border); padding: 8px 0; }
.result-head { display: flex; justify-content: space-between; font-weight: 600; font-size: 13px; }
.result-content { color: var(--ob-text-secondary); font-size: 13px; margin: 6px 0 0; }
</style>
