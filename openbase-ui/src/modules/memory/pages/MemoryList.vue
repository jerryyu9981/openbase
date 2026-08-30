<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索记忆内容/标签" clearable style="width: 220px" data-test="memory-keyword" />
      <el-select v-model="typeFilter" placeholder="记忆类型" clearable style="width: 140px" @change="onFilterChange">
        <el-option label="文本" value="text" />
        <el-option label="图像" value="image" />
        <el-option label="音频" value="audio" />
      </el-select>
      <el-button type="primary" data-test="write-memory" @click="$router.push('/memory/write')">写入记忆</el-button>
      <el-popconfirm title="确认批量删除选中记忆？" @confirm="batchDelete">
        <template #reference>
          <el-button type="danger" plain :disabled="selection.length === 0" data-test="batch-delete">批量删除</el-button>
        </template>
      </el-popconfirm>
    </div>
    <div v-loading="loading" class="ob-table-scroll">
      <el-table :data="paged" stripe data-test="memory-table" @selection-change="(rows: any[]) => (selection = rows)">
        <el-table-column type="selection" width="44" />
        <el-table-column prop="content" label="记忆内容（摘要）" min-width="220" show-overflow-tooltip />
        <el-table-column label="类型" width="90">
          <template #default="{ row }"><el-tag size="small">{{ row.memory_type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="标签" min-width="120">
          <template #default="{ row }">
            <el-tag v-for="t in row.tags" :key="t" size="small" type="info" class="mr-4">{{ t }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="衰减权重" width="110">
          <template #default="{ row }">
            <span :style="{ color: weightColor(row.decayed_weight ?? row.score ?? 0) }" data-test="decay-weight">
              {{ (row.decayed_weight ?? row.score ?? 0).toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/memory/${row.memory_id}`)">详情</el-button>
            <el-popconfirm title="确认删除该记忆？" @confirm="remove(row.memory_id)">
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && paged.length === 0" description="暂无匹配的记忆" :image-size="60" />
    </div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        background
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/core/api/http'

interface MemoryRow {
  memory_id: string
  content: string
  memory_type: string
  score: number | null
  decayed_weight: number | null
  created_at: string | null
  tags: string[]
}

interface MemoryListData {
  items: MemoryRow[]
  total: number
  page: number
  page_size: number
}

const keyword = ref('')
const typeFilter = ref('')
const selection = ref<MemoryRow[]>([])
const page = ref(1)
const pageSize = 10
const total = ref(0)
const memories = ref<MemoryRow[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await http.get<{ code: number; message: string; data: MemoryListData }>(
      '/memory-proxy/memories',
      { params: { page: page.value, page_size: pageSize } },
    )
    memories.value = data.data.items
    total.value = data.data.total
  } catch {
    memories.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  load()
}

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return memories.value.filter((m) => {
    const matchKw = !kw || m.content.toLowerCase().includes(kw) || (m.tags || []).some((t) => t.includes(kw))
    const matchType = !typeFilter.value || m.memory_type === typeFilter.value
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

async function forgetOne(memoryId: string) {
  const { data } = await http.post<{ code: number; message: string; data: unknown }>(
    '/memory-proxy/forget',
    { memory_id: memoryId, user_id: '' },
  )
  return data.code === 0
}

async function remove(memoryId: string) {
  try {
    const ok = await forgetOne(memoryId)
    if (ok) {
      ElMessage.success('记忆已删除')
      await load()
    }
  } catch {
    ElMessage.error('删除失败')
  }
}

async function batchDelete() {
  const ids = selection.value.map((s) => s.memory_id)
  try {
    for (const id of ids) {
      await forgetOne(id)
    }
    ElMessage.success(`已删除 ${ids.length} 条记忆`)
    await load()
  } catch {
    ElMessage.error('批量删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pager { margin-top: 8px; display: flex; justify-content: flex-end; }
.mr-4 { margin-right: 4px; }
</style>
