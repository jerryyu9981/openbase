<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索模型" clearable style="width: 260px" data-test="model-search" />
      <el-button type="primary" data-test="create-model" @click="createVisible = true">新增模型</el-button>
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
    <el-dialog v-model="createVisible" title="新增模型" width="480px" data-test="create-model-dialog">
      <el-form label-width="90px">
        <el-form-item label="模型名称" required><el-input v-model="form.name" placeholder="如：gpt-4o-mini" data-test="model-name-input" /></el-form-item>
        <el-form-item label="Provider" required><el-input v-model="form.provider" placeholder="如：OpenAI" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="商业" value="商业" />
            <el-option label="开源" value="开源" />
            <el-option label="本地" value="本地" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" data-test="create-model-submit" @click="createModel">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
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
const createVisible = ref(false)
const form = reactive({ name: '', provider: '', type: '商业' })
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
function createModel() {
  if (!form.name.trim() || !form.provider.trim()) {
    ElMessage.warning('请输入模型名称与 Provider')
    return
  }
  models.value.push({
    id: Date.now(),
    name: form.name.trim(),
    provider: form.provider.trim(),
    type: form.type,
    status: 'online',
    updated_at: new Date().toISOString().slice(0, 16).replace('T', ' '),
  })
  createVisible.value = false
  form.name = ''
  form.provider = ''
  ElMessage.success('模型已添加')
}
function remove(id: number) {
  models.value = models.value.filter((m) => m.id !== id)
  ElMessage.success('模型已删除')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
</style>
