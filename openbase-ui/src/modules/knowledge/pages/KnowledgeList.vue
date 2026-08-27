<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索知识库" clearable style="width: 240px" data-test="kb-search" />
      <el-button type="primary" data-test="create-kb" @click="dialogVisible = true">创建知识库</el-button>
    </div>
    <el-row v-loading="loading" :gutter="16">
      <el-col v-for="kb in paged" :key="kb.id" :xs="24" :sm="12" :lg="8">
        <el-card class="kb-card" data-test="kb-card">
          <h3 @click="$router.push(`/knowledge/${kb.id}`)">{{ kb.name }}</h3>
          <p class="meta">文档 {{ kb.documents }} · 分块 {{ kb.chunks }} · {{ kb.embedding_model }}</p>
          <div class="card-actions">
            <el-button size="small" type="primary" plain @click="$router.push(`/knowledge/${kb.id}`)">进入</el-button>
            <el-popconfirm title="确认删除该知识库？" @confirm="remove(kb.id)">
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
        <el-form-item label="Embedding 模型">
          <el-select v-model="form.embedding_model" style="width: 100%">
            <el-option label="BAAI/bge-m3" value="BAAI/bge-m3" />
            <el-option label="text-embedding-3-small" value="text-embedding-3-small" />
          </el-select>
        </el-form-item>
        <el-form-item label="分块策略">
          <el-select v-model="form.chunk_strategy" style="width: 100%">
            <el-option label="structured（结构化）" value="structured" />
            <el-option label="semantic（语义）" value="semantic" />
            <el-option label="fixed（固定长度）" value="fixed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" data-test="create-kb-submit" @click="createKb">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface KnowledgeBase { id: number; name: string; documents: number; chunks: number; embedding_model: string }

const keyword = ref('')
const dialogVisible = ref(false)
const loading = ref(false)
const page = ref(1)
const pageSize = 6
const form = reactive({ name: '', embedding_model: 'BAAI/bge-m3', chunk_strategy: 'structured' })
const knowledgeBases = ref<KnowledgeBase[]>([
  { id: 1, name: '产品文档库', documents: 24, chunks: 1560, embedding_model: 'bge-m3' },
  { id: 2, name: '技术问答库', documents: 12, chunks: 890, embedding_model: 'bge-m3' },
  { id: 3, name: '法律合规库', documents: 8, chunks: 420, embedding_model: 'text-embedding-3-small' },
  { id: 4, name: '研发规范库', documents: 16, chunks: 1020, embedding_model: 'bge-m3' },
  { id: 5, name: '市场资料库', documents: 30, chunks: 2100, embedding_model: 'text-embedding-3-small' },
  { id: 6, name: '客服话术库', documents: 5, chunks: 240, embedding_model: 'bge-m3' },
])

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return knowledgeBases.value.filter((kb) => !kw || kb.name.toLowerCase().includes(kw))
})
const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

function createKb() {
  if (!form.name) { ElMessage.warning('请输入知识库名称'); return }
  knowledgeBases.value.push({ id: Date.now(), name: form.name, documents: 0, chunks: 0, embedding_model: form.embedding_model })
  dialogVisible.value = false
  ElMessage.success('知识库已创建')
}
function remove(id: number) {
  knowledgeBases.value = knowledgeBases.value.filter((kb) => kb.id !== id)
  ElMessage.success('知识库已删除')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.kb-card { margin-bottom: 16px; }
.kb-card h3 { margin: 0 0 8px; cursor: pointer; }
.meta { color: var(--ob-text-secondary); font-size: 13px; margin-bottom: 10px; }
.card-actions { display: flex; gap: 8px; }
.pager { margin-top: 8px; display: flex; justify-content: flex-end; }
</style>
