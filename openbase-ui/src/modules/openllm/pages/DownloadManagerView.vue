<template>
  <div class="download-manager">
    <div class="page-toolbar">
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 150px" data-test="dl-status-filter">
        <el-option label="下载中" value="downloading" />
        <el-option label="已完成" value="completed" />
        <el-option label="失败" value="failed" />
        <el-option label="已暂停" value="paused" />
      </el-select>
      <el-button type="primary" :loading="loading" data-test="dl-refresh" @click="load">刷新</el-button>
    </div>

    <el-card header="下载任务" data-test="dl-card">
      <div class="ob-table-scroll">
        <el-table :data="filteredTasks" stripe empty-text="暂无下载任务" data-test="dl-table">
          <el-table-column prop="model" label="模型" min-width="160" />
          <el-table-column prop="size" label="大小" width="90" />
          <el-table-column label="进度" min-width="200">
            <template #default="{ row }">
              <el-progress :percentage="row.progress" :status="progressStatus(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="speed" label="速度" width="100">
            <template #default="{ row }">{{ row.speed }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button v-if="row.status === 'downloading'" link type="warning" size="small" data-test="dl-pause" @click="toggle(row)">暂停</el-button>
              <el-button v-if="row.status === 'paused'" link type="success" size="small" @click="toggle(row)">恢复</el-button>
              <el-button v-if="row.status === 'failed'" link type="primary" size="small" data-test="dl-retry" @click="retry(row)">重试</el-button>
              <el-button v-if="row.status === 'completed'" link type="primary" size="small" data-test="dl-deploy" @click="deploy(row)">部署</el-button>
              <el-popconfirm title="确认删除该任务？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface DownloadTask {
  id: number
  model: string
  size: string
  progress: number
  speed: string
  status: 'downloading' | 'completed' | 'failed' | 'paused'
}

const mockTasks: DownloadTask[] = [
  { id: 1, model: 'llama3-8b', size: '4.9GB', progress: 68, speed: '18.5 MB/s', status: 'downloading' },
  { id: 2, model: 'qwen2-7b', size: '4.4GB', progress: 100, speed: '—', status: 'completed' },
  { id: 3, model: 'deepseek-coder-6.7b', size: '3.8GB', progress: 32, speed: '12.0 MB/s', status: 'downloading' },
  { id: 4, model: 'bge-large-zh', size: '1.3GB', progress: 0, speed: '—', status: 'failed' },
]

const tasks = ref<DownloadTask[]>([])
const statusFilter = ref('')
const loading = ref(false)

const filteredTasks = computed(() =>
  statusFilter.value ? tasks.value.filter((t) => t.status === statusFilter.value) : tasks.value,
)

function load() {
  loading.value = true
  setTimeout(() => {
    tasks.value = mockTasks.map((t) => ({ ...t }))
    loading.value = false
  }, 300)
}

function progressStatus(row: DownloadTask): 'success' | 'exception' {
  if (row.status === 'completed') return 'success'
  if (row.status === 'failed') return 'exception'
  return 'success'
}

function statusType(s: DownloadTask['status']): 'success' | 'warning' | 'danger' | 'info' {
  return { downloading: 'warning', completed: 'success', failed: 'danger', paused: 'info' }[s] as 'success' | 'warning' | 'danger' | 'info'
}

function statusLabel(s: DownloadTask['status']): string {
  return { downloading: '下载中', completed: '已完成', failed: '失败', paused: '已暂停' }[s]
}

function toggle(row: DownloadTask) {
  row.status = row.status === 'paused' ? 'downloading' : 'paused'
  ElMessage.success(row.status === 'paused' ? '任务已暂停' : '任务已恢复')
}

function retry(row: DownloadTask) {
  row.status = 'downloading'
  row.progress = 0
  ElMessage.success('任务已重新开始')
}

function deploy(row: DownloadTask) {
  ElMessage.success(`模型 ${row.model} 部署已触发`)
}

function remove(id: number) {
  tasks.value = tasks.value.filter((t) => t.id !== id)
  ElMessage.success('任务已删除')
}

onMounted(load)
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
</style>
