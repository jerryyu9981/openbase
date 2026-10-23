<template>
  <PageContainer title="下载管理" description="模型下载任务与进度（OpenLLM Model Download）" test-id="download-manager-view-page">
    <div class="page-toolbar">
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 150px" data-test="dl-status-filter" @change="reload">
        <el-option label="等待中" value="pending" />
        <el-option label="下载中" value="downloading" />
        <el-option label="已暂停" value="paused" />
        <el-option label="已完成" value="completed" />
        <el-option label="失败" value="failed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-button type="primary" :loading="loading" data-test="dl-refresh" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="dl-error"
      @close="errorMessage = ''"
    />

    <el-card header="下载任务" data-test="dl-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="tasks" stripe data-test="dl-table">
          <template #empty>
            <el-empty description="暂无下载任务" :image-size="60" data-test="dl-empty" />
          </template>
          <el-table-column label="模型" min-width="200">
            <template #default="{ row }">{{ row.model_name || row.model_id }}</template>
          </el-table-column>
          <el-table-column label="大小" width="100">
            <template #default="{ row }">{{ formatSize(row.total_size) }}</template>
          </el-table-column>
          <el-table-column label="进度" min-width="200">
            <template #default="{ row }">
              <el-progress :percentage="Math.round(Number(row.progress ?? 0))" :status="progressStatus(row)" />
            </template>
          </el-table-column>
          <el-table-column label="速度" width="120">
            <template #default="{ row }">{{ formatSpeed(row.download_speed) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'downloading' || row.status === 'pending'"
                link
                type="warning"
                size="small"
                data-test="dl-pause"
                @click="pause(row)"
              >
                暂停
              </el-button>
              <el-button
                v-if="row.status === 'paused'"
                link
                type="success"
                size="small"
                data-test="dl-resume"
                @click="resume(row)"
              >
                恢复
              </el-button>
              <el-button
                v-if="row.status === 'failed' || row.status === 'cancelled'"
                link
                type="primary"
                size="small"
                data-test="dl-retry"
                @click="retry(row)"
              >
                重试
              </el-button>
              <el-button
                v-if="row.status === 'completed'"
                link
                type="primary"
                size="small"
                data-test="dl-deploy"
                @click="deploy(row)"
              >
                部署
              </el-button>
              <el-button
                v-if="['pending', 'downloading', 'paused', 'failed'].includes(row.status)"
                link
                type="danger"
                size="small"
                data-test="dl-cancel"
                @click="cancel(row)"
              >
                取消
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        data-test="dl-pagination"
        @current-change="load"
        @size-change="reload"
      />
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { openModelsApi, type LlmDownloadTask } from '@/core/api/governance'

/**
 * 下载管理（v1.9.6 R6 真实化）：`/open-models/downloads` 列表（服务端分页/状态筛选）+
 * 暂停/恢复/取消/重试（重试=重新创建下载任务）/部署。上游无「删除任务」端点，故不提供删除。
 */
const statusFilter = ref('')
const loading = ref(false)
const errorMessage = ref('')
const tasks = ref<LlmDownloadTask[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

function statusType(status: string) {
  return {
    pending: 'info',
    downloading: 'warning',
    paused: 'info',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }[status] || 'info'
}
function statusLabel(status: string) {
  return {
    not_downloaded: '未下载',
    pending: '等待中',
    downloading: '下载中',
    paused: '已暂停',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }[status] || status
}
function progressStatus(row: LlmDownloadTask): 'success' | 'exception' | undefined {
  if (row.status === 'completed') return 'success'
  if (row.status === 'failed') return 'exception'
  return undefined
}
function formatSize(bytes: number | null) {
  if (!bytes) return '-'
  return `${(Number(bytes) / 1024 / 1024 / 1024).toFixed(2)} GB`
}
function formatSpeed(bytesPerSecond: number | null) {
  if (!bytesPerSecond) return '—'
  return `${(Number(bytesPerSecond) / 1024 / 1024).toFixed(1)} MB/s`
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await openModelsApi.downloads({
      status: statusFilter.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    tasks.value = result.items
    total.value = result.total
  } catch (error) {
    errorMessage.value = `下载任务加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  void load()
}

async function pause(row: LlmDownloadTask) {
  try {
    await openModelsApi.pauseDownload(row.model_id)
    ElMessage.success('任务已暂停')
    await load()
  } catch (error) {
    errorMessage.value = `暂停失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function resume(row: LlmDownloadTask) {
  try {
    await openModelsApi.resumeDownload(row.model_id)
    ElMessage.success('任务已恢复')
    await load()
  } catch (error) {
    errorMessage.value = `恢复失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function retry(row: LlmDownloadTask) {
  try {
    await openModelsApi.startDownload(row.model_id, { version: 'main', resume: true })
    ElMessage.success('已重新创建下载任务')
    await load()
  } catch (error) {
    errorMessage.value = `重试失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function cancel(row: LlmDownloadTask) {
  try {
    await openModelsApi.cancelDownload(row.model_id)
    ElMessage.success('任务已取消')
    await load()
  } catch (error) {
    errorMessage.value = `取消失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function deploy(row: LlmDownloadTask) {
  try {
    await openModelsApi.deploy(row.model_id)
    ElMessage.success(`模型 ${row.model_name || row.model_id} 部署已触发`)
  } catch (error) {
    errorMessage.value = `部署失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.pagination { margin-top: 12px; justify-content: flex-end; }
</style>
