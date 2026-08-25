<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索模型" clearable style="width: 260px" data-test="model-search" />
      <el-button type="primary" data-test="create-model">新增模型</el-button>
    </div>
    <div class="ob-table-scroll">
      <el-table :data="models" stripe data-test="model-table">
        <el-table-column prop="name" label="模型" min-width="160" />
        <el-table-column prop="provider" label="Provider" width="120" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }"><el-tag size="small">{{ row.type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-popconfirm title="确认删除该模型？" @confirm="remove(row.id)">
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

interface ModelRow {
  id: number
  name: string
  provider: string
  type: string
  status: string
  updated_at: string
}

const keyword = ref('')
const models = ref<ModelRow[]>([
  { id: 1, name: 'gpt-4o', provider: 'OpenAI', type: '商业', status: 'online', updated_at: '2026-08-25 10:00' },
  { id: 2, name: 'qwen2.5-7b', provider: 'Ollama', type: '本地', status: 'online', updated_at: '2026-08-25 09:30' },
  { id: 3, name: 'bge-m3', provider: 'BAAI', type: '开源', status: 'deploying', updated_at: '2026-08-25 08:00' },
])

function statusType(status: string) {
  return { online: 'success', offline: 'info', deploying: 'warning', error: 'danger' }[status] || 'info'
}
function statusLabel(status: string) {
  return { online: '在线', offline: '离线', deploying: '部署中', error: '异常' }[status] || status
}
function openDetail(row: ModelRow) {
  ElMessage.info(`查看模型详情：${row.name}`)
}
function remove(id: number) {
  models.value = models.value.filter((m) => m.id !== id)
  ElMessage.success('模型已删除')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
</style>
