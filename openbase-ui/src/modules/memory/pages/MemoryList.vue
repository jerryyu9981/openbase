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
      <el-table :data="memories" stripe data-test="memory-table" @selection-change="(rows: any[]) => (selection = rows)">
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface MemoryRow { id: number; content: string; type: string; weight: number; created_at: string }

const keyword = ref('')
const typeFilter = ref('')
const selection = ref<MemoryRow[]>([])
const memories = ref<MemoryRow[]>([
  { id: 1, content: '用户偏好使用简洁的技术文档风格', type: 'text', weight: 0.92, created_at: '2026-08-25 10:00' },
  { id: 2, content: '近期关注 RAG 检索优化方向', type: 'text', weight: 0.64, created_at: '2026-08-20 14:30' },
  { id: 3, content: '产品架构图（图像记忆）', type: 'image', weight: 0.78, created_at: '2026-08-18 09:00' },
])

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
</style>
