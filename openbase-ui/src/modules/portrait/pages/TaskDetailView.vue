<template>
  <PageContainer title="引入任务详情" description="任务摘要、错误行与重试；错误记录已由后端脱敏" test-id="ingest-task-detail-page">
    <div class="page-toolbar">
      <el-button data-test="ingest-back" @click="$router.push('/portrait/dps/ingest-tasks')">返回列表</el-button>
      <el-button type="primary" :disabled="task?.status === 'running'" data-test="ingest-retry" @click="retry">
        重试任务
      </el-button>
      <el-button :disabled="errors.length === 0" data-test="ingest-error-export" @click="downloadErrors">
        导出错误 CSV
      </el-button>
    </div>

    <el-descriptions v-if="task" :column="3" border data-test="ingest-summary">
      <el-descriptions-item label="任务 ID">{{ task.id }}</el-descriptions-item>
      <el-descriptions-item label="文件">{{ task.file_name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="格式">{{ task.file_format || '-' }}</el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag :type="statusType(task.status)" size="small">{{ statusText(task.status) }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="成功 / 总数">
        {{ task.success_rows ?? 0 }} / {{ task.total_rows ?? 0 }}
      </el-descriptions-item>
      <el-descriptions-item label="失败">{{ task.failed_rows ?? 0 }}</el-descriptions-item>
      <el-descriptions-item label="触发来源">{{ task.trigger_source || '-' }}</el-descriptions-item>
      <el-descriptions-item label="创建时间">{{ task.created_at || '-' }}</el-descriptions-item>
      <el-descriptions-item label="完成时间">{{ task.finished_at || '-' }}</el-descriptions-item>
    </el-descriptions>

    <h3 class="section-title">错误行（已脱敏）</h3>
    <el-table v-loading="loading" :data="errors" border data-test="ingest-error-table">
      <el-table-column prop="row_number" label="行号" width="90" />
      <el-table-column prop="error" label="错误" min-width="220" />
      <el-table-column label="记录（脱敏）" min-width="320">
        <template #default="{ row }">
          <code class="record">{{ JSON.stringify(row.record || {}) }}</code>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && errors.length === 0" description="无错误行" />
  </PageContainer>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsIngestError, type DpsIngestTask } from '@/core/api/dps'

/** 引入任务详情（波次 B / B-09）：摘要 + 错误行 + 重试 + 脱敏 CSV */
const route = useRoute()
const taskId = computed(() => String(route.params.id || ''))
const loading = ref(false)
const task = ref<DpsIngestTask | null>(null)
const errors = ref<DpsIngestError[]>([])

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

async function load(): Promise<void> {
  if (!taskId.value) return
  loading.value = true
  try {
    task.value = await dpsApi.getIngestTask(taskId.value)
    errors.value = await dpsApi.getIngestTaskErrors(taskId.value)
  } catch (error) {
    ElMessage.error(`加载任务失败：${(error as Error).message}`)
  } finally {
    loading.value = false
  }
}

async function retry(): Promise<void> {
  try {
    await dpsApi.retryIngestTask(taskId.value)
    ElMessage.success('已重新执行')
    await load()
  } catch (error) {
    ElMessage.error(`重试失败：${(error as Error).message}`)
  }
}

function downloadErrors(): void {
  const header = 'row_number,error,record\n'
  const lines = errors.value.map((item) => {
    const record = JSON.stringify(item.record || {}).replace(/"/g, '""')
    return `${item.row_number},"${item.error.replace(/"/g, '""')}","${record}"`
  })
  const blob = new Blob([header + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${taskId.value}-errors.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<style scoped>
.section-title {
  margin: 20px 0 10px;
  font-size: 15px;
}

.record {
  font-size: 12px;
  word-break: break-all;
}
</style>
