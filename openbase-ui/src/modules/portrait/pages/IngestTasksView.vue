<template>
  <PageContainer
    title="引入任务"
    description="导入/同步落库任务与错误行；错误记录由后端脱敏，前端不还原明文"
    test-id="ingest-tasks-page"
  >
    <div class="page-toolbar">
      <el-radio-group v-model="activeTab" data-test="ingest-tab" @change="loadTasks">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="running">进行中</el-radio-button>
        <el-radio-button value="failed">失败</el-radio-button>
      </el-radio-group>
      <el-button :loading="loading" data-test="ingest-refresh" @click="loadTasks">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="tasks" border data-test="ingest-task-table">
      <el-table-column prop="id" label="任务 ID" min-width="190" />
      <el-table-column prop="file_name" label="文件" min-width="160" />
      <el-table-column prop="file_format" label="格式" width="80" />
      <el-table-column label="进度" width="140">
        <template #default="{ row }">
          {{ row.success_rows ?? 0 }} / {{ row.total_rows ?? 0 }}
        </template>
      </el-table-column>
      <el-table-column label="失败" width="80">
        <template #default="{ row }">{{ row.failed_rows ?? 0 }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="trigger_source" label="触发" width="100" />
      <el-table-column prop="created_at" label="创建时间" min-width="170" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row.id)">详情</el-button>
          <el-button link type="warning" :disabled="row.status === 'running'" @click="retry(row.id)">
            重试
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && tasks.length === 0" description="暂无引入任务" />

    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadTasks"
      />
    </div>
  </PageContainer>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsIngestTask } from '@/core/api/dps'

/** 引入任务中心（波次 B / B-09）：三 Tab + 详情/重试 */
const router = useRouter()
const activeTab = ref<'all' | 'running' | 'failed'>('all')
const loading = ref(false)
const tasks = ref<DpsIngestTask[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const STATUS_TEXT: Record<string, string> = {
  pending: '待执行',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
}

function statusText(status?: string): string {
  return STATUS_TEXT[status || ''] || status || '-'
}

function statusType(status?: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'completed') return 'success'
  if (status === 'running' || status === 'pending') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

async function loadTasks(): Promise<void> {
  loading.value = true
  try {
    const status = activeTab.value === 'all' ? undefined : activeTab.value
    const data = await dpsApi.listIngestTasks({ status, page: page.value, page_size: pageSize.value })
    tasks.value = data.items || []
    total.value = data.total || 0
  } catch (error) {
    ElMessage.error(`加载引入任务失败：${(error as Error).message}`)
  } finally {
    loading.value = false
  }
}

function openDetail(taskId: string): void {
  router.push(`/portrait/dps/ingest-tasks/${encodeURIComponent(taskId)}`)
}

async function retry(taskId: string): Promise<void> {
  try {
    await dpsApi.retryIngestTask(taskId)
    ElMessage.success('已重新执行')
    await loadTasks()
  } catch (error) {
    ElMessage.error(`重试失败：${(error as Error).message}`)
  }
}

onMounted(loadTasks)
</script>

<style scoped>
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
