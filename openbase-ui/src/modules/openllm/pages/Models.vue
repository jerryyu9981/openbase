<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索模型" clearable style="width: 200px" data-test="model-search" />
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 130px" data-test="model-status-filter">
        <el-option label="在线" value="online" />
        <el-option label="离线" value="offline" />
        <el-option label="部署中" value="deploying" />
        <el-option label="异常" value="error" />
      </el-select>
      <el-button type="primary" data-test="create-model" @click="openForm()">新增模型</el-button>
    </div>
    <div class="ob-table-scroll">
      <el-table :data="filteredModels" stripe data-test="model-table">
        <el-table-column prop="name" label="模型" min-width="140" />
        <el-table-column prop="provider" label="Provider" width="110" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }"><el-tag size="small">{{ row.type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="能力" min-width="160">
          <template #default="{ row }">
            <el-tag v-for="cap in row.capabilities" :key="cap" size="small" class="cap-tag" type="info">{{ cap }}</el-tag>
            <span v-if="!row.capabilities?.length" class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="定价(输入/输出)" width="140">
          <template #default="{ row }">
            <span>{{ priceText(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" data-test="edit-model" @click="openForm(row)">编辑</el-button>
            <el-popconfirm title="确认删除该模型？" @confirm="remove(row.id)">
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="formVisible" :title="editingId ? '编辑模型' : '新增模型'" width="520px" data-test="create-model-dialog">
      <el-form label-width="100px">
        <el-form-item label="模型名称" required><el-input v-model="form.name" placeholder="如：gpt-4o-mini" data-test="model-name-input" /></el-form-item>
        <el-form-item label="Provider" required><el-input v-model="form.provider" placeholder="如：OpenAI" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="商业" value="商业" />
            <el-option label="开源" value="开源" />
            <el-option label="本地" value="本地" />
          </el-select>
        </el-form-item>
        <el-form-item label="能力标签">
          <el-select v-model="form.capabilities" multiple filterable allow-create default-first-option placeholder="如：chat、embedding" style="width: 100%" />
        </el-form-item>
        <el-form-item label="输入单价">
          <el-input-number v-model="form.input_price" :min="0" :precision="4" :step="0.0001" style="width: 100%" placeholder="$/1K tokens" />
        </el-form-item>
        <el-form-item label="输出单价">
          <el-input-number v-model="form.output_price" :min="0" :precision="4" :step="0.0001" style="width: 100%" placeholder="$/1K tokens" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
            <el-option label="部署中" value="deploying" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" data-test="create-model-submit" @click="saveModel">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ModelRow {
  id: number
  name: string
  provider: string
  type: string
  status: string
  capabilities: string[]
  input_price: number
  output_price: number
  updated_at: string
}

const keyword = ref('')
const statusFilter = ref('')
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ name: '', provider: '', type: '商业', capabilities: [] as string[], input_price: 0, output_price: 0, status: 'online' })

const models = ref<ModelRow[]>([
  { id: 1, name: 'gpt-4o', provider: 'OpenAI', type: '商业', status: 'online', capabilities: ['chat', 'vision'], input_price: 0.005, output_price: 0.015, updated_at: '2026-08-25 10:00' },
  { id: 2, name: 'qwen2.5-7b', provider: 'Ollama', type: '本地', status: 'online', capabilities: ['chat'], input_price: 0, output_price: 0, updated_at: '2026-08-25 09:30' },
  { id: 3, name: 'bge-m3', provider: 'BAAI', type: '开源', status: 'deploying', capabilities: ['embedding'], input_price: 0.002, output_price: 0.002, updated_at: '2026-08-25 08:00' },
])

const filteredModels = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return models.value.filter((m) => {
    const matchKw = !kw || m.name.toLowerCase().includes(kw) || m.provider.toLowerCase().includes(kw)
    const matchStatus = !statusFilter.value || m.status === statusFilter.value
    return matchKw && matchStatus
  })
})

function statusType(status: string) {
  return { online: 'success', offline: 'info', deploying: 'warning', error: 'danger' }[status] || 'info'
}
function statusLabel(status: string) {
  return { online: '在线', offline: '离线', deploying: '部署中', error: '异常' }[status] || status
}
function priceText(row: ModelRow) {
  return `$${row.input_price} / $${row.output_price}`
}
function openDetail(row: ModelRow) {
  ElMessage.info(`查看模型详情：${row.name}（${row.capabilities?.join('、') || '无能力标签'}）`)
}
function openForm(row?: ModelRow) {
  editingId.value = row?.id ?? null
  form.name = row?.name ?? ''
  form.provider = row?.provider ?? ''
  form.type = row?.type ?? '商业'
  form.capabilities = row?.capabilities ? [...row.capabilities] : []
  form.input_price = row?.input_price ?? 0
  form.output_price = row?.output_price ?? 0
  form.status = row?.status ?? 'online'
  formVisible.value = true
}
function saveModel() {
  if (!form.name.trim() || !form.provider.trim()) {
    ElMessage.warning('请输入模型名称与 Provider')
    return
  }
  if (editingId.value) {
    const target = models.value.find((m) => m.id === editingId.value)
    if (target) {
      Object.assign(target, {
        name: form.name.trim(),
        provider: form.provider.trim(),
        type: form.type,
        capabilities: [...form.capabilities],
        input_price: form.input_price,
        output_price: form.output_price,
        status: form.status,
        updated_at: new Date().toISOString().slice(0, 16).replace('T', ' '),
      })
      ElMessage.success('模型已更新')
    }
  } else {
    models.value.push({
      id: Date.now(),
      name: form.name.trim(),
      provider: form.provider.trim(),
      type: form.type,
      status: form.status,
      capabilities: [...form.capabilities],
      input_price: form.input_price,
      output_price: form.output_price,
      updated_at: new Date().toISOString().slice(0, 16).replace('T', ' '),
    })
    ElMessage.success('模型已添加')
  }
  formVisible.value = false
}
function remove(id: number) {
  models.value = models.value.filter((m) => m.id !== id)
  ElMessage.success('模型已删除')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.cap-tag { margin-right: 4px; }
.text-muted { color: #909399; }
</style>
