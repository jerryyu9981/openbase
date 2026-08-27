<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索记忆" clearable style="width: 220px" />
      <el-select v-model="typeFilter" placeholder="记忆类型" clearable style="width: 140px">
        <el-option label="文本" value="text" />
        <el-option label="图像" value="image" />
        <el-option label="音频" value="audio" />
      </el-select>
      <el-button type="primary" data-test="write-memory" @click="$router.push('/memory/write')">写入记忆</el-button>
      <el-popconfirm title="确认批量删除选中记忆？" @confirm="batchDelete">
        <template #reference>
          <el-button type="danger" plain :disabled="selection.length === 0">批量删除</el-button>
        </template>
      </el-popconfirm>
    </div>
    <div class="ob-table-scroll">
      <el-table :data="paged" stripe data-test="memory-table" @selection-change="(rows: any[]) => (selection = rows)">
        <el-table-column type="selection" width="44" />
        <el-table-column prop="content" label="记忆内容（摘要）" min-width="220" show-overflow-tooltip />
        <el-table-column label="类型" width="90">
          <template #default="{ row }"><el-tag size="small">{{ row.type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="衰减权重" width="110">
          <template #default="{ row }">
            <span :style="{ color: weightColor(row.weight) }" data-test="decay-weight">{{ row.weight.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/memory/${row.id}`)">详情</el-button>
            <el-popconfirm title="确认删除该记忆？" @confirm="remove(row.id)">
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="paged.length === 0" description="暂无匹配的记忆" :image-size="60" />
    </div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="filtered.length"
        layout="total, prev, pager, next"
        background
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface MemoryRow { id: number; content: string; type: string; weight: number; created_at: string }

const keyword = ref('')
const typeFilter = ref('')
const selection = ref<MemoryRow[]>([])
const page = ref(1)
const pageSize = 10
const memories = ref<MemoryRow[]>([
  { id: 1, content: '用户偏好使用简洁的技术文档风格', type: 'text', weight: 0.92, created_at: '2026-08-25 10:00' },
  { id: 2, content: '近期关注 RAG 检索优化方向', type: 'text', weight: 0.64, created_at: '2026-08-20 14:30' },
  { id: 3, content: '产品架构图（图像记忆）', type: 'image', weight: 0.78, created_at: '2026-08-18 09:00' },
  { id: 4, content: '用户常用 Java 与 Python 双栈开发', type: 'text', weight: 0.88, created_at: '2026-08-15 16:00' },
  { id: 5, content: '季度技术评审录音（音频记忆）', type: 'audio', weight: 0.71, created_at: '2026-08-12 11:30' },
  { id: 6, content: '偏好异步沟通，会议纪要需同步到群', type: 'text', weight: 0.82, created_at: '2026-08-10 09:45' },
  { id: 7, content: '版本发布会海报设计稿（图像记忆）', type: 'image', weight: 0.59, created_at: '2026-08-08 15:20' },
  { id: 8, content: '关注向量数据库选型与成本对比', type: 'text', weight: 0.55, created_at: '2026-08-05 10:10' },
  { id: 9, content: '团队协作强调文档先行', type: 'text', weight: 0.86, created_at: '2026-08-02 14:00' },
  { id: 10, content: '知识库会议录音（音频记忆）', type: 'audio', weight: 0.47, created_at: '2026-07-30 17:30' },
  { id: 11, content: '多模态模型评测结果图（图像记忆）', type: 'image', weight: 0.63, created_at: '2026-07-28 10:40' },
  { id: 12, content: '客户访谈要点：偏好快速原型验证', type: 'text', weight: 0.9, created_at: '2026-07-25 13:20' },
])

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return memories.value.filter((m) => {
    const matchKw = !kw || m.content.toLowerCase().includes(kw)
    const matchType = !typeFilter.value || m.type === typeFilter.value
    return matchKw && matchType
  })
})
const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

// 衰减权重着色：>=0.80 绿 / 0.50~0.79 黄 / <0.50 红（OpenMemory v6.7 规则）
function weightColor(weight: number) {
  if (weight >= 0.8) return '#16a34a'
  if (weight >= 0.5) return '#d97706'
  return '#dc2626'
}
function remove(id: number) {
  memories.value = memories.value.filter((m) => m.id !== id)
  ElMessage.success('记忆已删除')
}
function batchDelete() {
  const ids = selection.value.map((s) => s.id)
  memories.value = memories.value.filter((m) => !ids.includes(m.id))
  ElMessage.success(`已删除 ${ids.length} 条记忆`)
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pager { margin-top: 8px; display: flex; justify-content: flex-end; }
</style>
