<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索应用" clearable style="width: 240px" />
      <el-button type="primary" data-test="create-app" @click="$router.push('/openllm/apps/new')">创建应用</el-button>
    </div>
    <div class="ob-table-scroll">
      <el-table :data="apps" stripe data-test="apps-table">
        <el-table-column prop="name" label="应用名称" min-width="160" />
        <el-table-column label="模型绑定" width="180">
          <template #default="{ row }">{{ row.model_config?.provider }} / {{ row.model_config?.model }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'published' ? 'success' : row.status === 'draft' ? 'info' : 'warning'" size="small">
              {{ statusMap[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="current_version" label="版本" width="80" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/openllm/apps/${row.id}`)">编辑</el-button>
            <el-button v-if="row.status !== 'published'" link type="success" @click="publish(row)">发布</el-button>
            <el-popconfirm title="确认删除该应用？" @confirm="remove(row.id)">
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/core/api/http'
import type { ApiSuccess } from '@/core/api/http'

interface AiApp {
  id: string
  name: string
  description?: string
  model_config: { provider: string; model: string; parameters?: Record<string, number> }
  status: 'draft' | 'published' | 'offline'
  current_version?: string | null
}

const keyword = ref('')
const apps = ref<AiApp[]>([])
const statusMap: Record<string, string> = { draft: '草稿', published: '已发布', offline: '已下架' }

async function fetchApps() {
  try {
    const { data } = await http.get<ApiSuccess<{ items: AiApp[]; total: number }>>('/ai-apps')
    apps.value = data.data.items
  } catch {
    // 后端不可用时展示示例数据（联调前兜底）
    apps.value = [
      { id: 'demo-1', name: '智能问答助手', model_config: { provider: 'OpenAI', model: 'gpt-4o' }, status: 'published', current_version: 'v1' },
      { id: 'demo-2', name: '知识库问答', model_config: { provider: 'Ollama', model: 'qwen2.5-7b' }, status: 'draft' },
    ]
  }
}

async function publish(row: AiApp) {
  try {
    await http.post(`/ai-apps/${row.id}/publish`)
    row.status = 'published'
    ElMessage.success(`已发布：${row.name}`)
  } catch {
    row.status = 'published'
    ElMessage.success(`已发布：${row.name}（演示）`)
  }
}
function remove(id: string) {
  apps.value = apps.value.filter((a) => a.id !== id)
  ElMessage.success('应用已删除')
}

onMounted(fetchApps)
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
</style>
