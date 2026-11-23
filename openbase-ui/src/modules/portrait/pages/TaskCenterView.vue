<template>
  <PageContainer title="任务中心" description="引入任务、数据源调度与审计留痕的统一入口" test-id="task-center-page">
    <el-tabs v-model="activeTab" data-test="task-center-tabs">
      <el-tab-pane label="引入任务" name="ingest">
        <div class="toolbar">
          <el-select v-model="ingestStatus" size="small" clearable placeholder="全部状态" style="width: 160px" @change="loadIngest">
            <el-option label="待执行" value="pending" />
            <el-option label="执行中" value="running" />
            <el-option label="成功" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
          <el-button size="small" :loading="ingestLoading" @click="loadIngest">刷新</el-button>
        </div>
        <el-table v-loading="ingestLoading" :data="ingestTasks" size="small" empty-text="暂无引入任务" data-test="task-center-ingest">
          <el-table-column prop="id" label="任务 ID" min-width="180" show-overflow-tooltip />
          <el-table-column prop="file_name" label="文件" min-width="160" show-overflow-tooltip />
          <el-table-column label="进度" width="130">
            <template #default="{ row }">{{ row.success_rows ?? 0 }}/{{ row.total_rows ?? 0 }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="created_at" label="创建时间" width="170" show-overflow-tooltip />
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openIngest(row.id)">详情</el-button>
              <el-button
                v-if="row.status === 'failed'"
                link
                type="warning"
                size="small"
                data-test="task-center-ingest-retry"
                @click="retryIngest(row.id)"
              >
                重试
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="数据源调度" name="schedule">
        <div class="toolbar">
          <el-button size="small" type="primary" data-test="task-center-schedule-new" @click="openSchedule(null)">
            新建调度
          </el-button>
          <el-button size="small" :loading="scheduleLoading" @click="loadSchedules">刷新</el-button>
        </div>
        <el-table v-loading="scheduleLoading" :data="schedules" size="small" empty-text="暂无调度" data-test="task-center-schedules">
          <el-table-column prop="datasource_id" label="数据源" min-width="140" show-overflow-tooltip />
          <el-table-column label="表达式" min-width="150">
            <template #default="{ row }">
              {{ row.schedule_type === 'interval' ? `每 ${row.interval_seconds}s` : row.cron_expr }}
            </template>
          </el-table-column>
          <el-table-column prop="next_run_at" label="下次触发" width="170" show-overflow-tooltip />
          <el-table-column prop="last_status" label="上次结果" width="110" />
          <el-table-column label="失败" width="80">
            <template #default="{ row }">{{ row.failure_count ?? 0 }}/{{ row.max_failures ?? 3 }}</template>
          </el-table-column>
          <el-table-column label="启用" width="80">
            <template #default="{ row }">
              <el-switch
                :model-value="Boolean(row.enabled)"
                size="small"
                data-test="task-center-schedule-toggle"
                @change="toggleSchedule(row)"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openSchedule(row)">编辑</el-button>
              <el-button link type="warning" size="small" data-test="task-center-schedule-run" @click="runSchedule(row.id)">
                执行
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="审计日志" name="audit">
        <div class="toolbar">
          <el-select v-model="auditAction" size="small" clearable placeholder="全部动作" style="width: 160px" @change="loadAudit">
            <el-option label="读取" value="READ" />
            <el-option label="导出" value="EXPORT" />
            <el-option label="删除" value="DELETE" />
            <el-option label="范围变更" value="SCOPE_CHANGE" />
          </el-select>
          <el-button size="small" :loading="auditLoading" @click="loadAudit">刷新</el-button>
        </div>
        <el-table v-loading="auditLoading" :data="auditLogs" size="small" empty-text="暂无审计记录" data-test="task-center-audit">
          <el-table-column prop="timestamp" label="时间" width="170" show-overflow-tooltip />
          <el-table-column prop="user_id" label="用户" width="120" show-overflow-tooltip />
          <el-table-column prop="action" label="动作" width="120" />
          <el-table-column prop="resource_type" label="资源" width="120" />
          <el-table-column prop="resource_id" label="资源 ID" min-width="140" show-overflow-tooltip />
          <el-table-column prop="result" label="结果" width="90" />
          <el-table-column prop="detail" label="详情" min-width="160" show-overflow-tooltip />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="scheduleVisible" title="调度配置" size="520px" data-test="task-center-schedule-drawer">
      <ScheduleEditor :schedule="editingSchedule" @saved="onScheduleSaved" />
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageContainer from '@/components/page/PageContainer.vue'
import ScheduleEditor from '../components/ScheduleEditor.vue'
import {
  dpsApi,
  type DpsAuditLog,
  type DpsIngestTask,
  type DpsSchedule,
} from '@/core/api/dps'
import { describeError } from '@/core/api/error'

const router = useRouter()
const activeTab = ref('ingest')

const ingestStatus = ref('')
const ingestTasks = ref<DpsIngestTask[]>([])
const ingestLoading = ref(false)

const schedules = ref<DpsSchedule[]>([])
const scheduleLoading = ref(false)
const scheduleVisible = ref(false)
const editingSchedule = ref<DpsSchedule | null>(null)

const auditAction = ref('')
const auditLogs = ref<DpsAuditLog[]>([])
const auditLoading = ref(false)

async function loadIngest() {
  ingestLoading.value = true
  try {
    const payload = await dpsApi.listIngestTasks({
      status: ingestStatus.value || undefined,
      page: 1,
      page_size: 50,
    })
    ingestTasks.value = payload.items || []
  } catch (err) {
    ElMessage.error(describeError(err).detail || '引入任务加载失败')
  } finally {
    ingestLoading.value = false
  }
}

function openIngest(taskId: string) {
  router.push(`/portrait/dps/ingest-tasks/${encodeURIComponent(taskId)}`)
}

async function retryIngest(taskId: string) {
  try {
    await dpsApi.retryIngestTask(taskId)
    ElMessage.success('已提交重试')
    await loadIngest()
  } catch (err) {
    ElMessage.error(describeError(err).detail || '重试失败')
  }
}

async function loadSchedules() {
  scheduleLoading.value = true
  try {
    const payload = await dpsApi.listSchedules()
    schedules.value = payload.items || []
  } catch (err) {
    ElMessage.error(describeError(err).detail || '调度加载失败（可能未开启 DPS_PROGRESS_ENABLED）')
  } finally {
    scheduleLoading.value = false
  }
}

function openSchedule(schedule: DpsSchedule | null) {
  editingSchedule.value = schedule
  scheduleVisible.value = true
}

async function onScheduleSaved() {
  scheduleVisible.value = false
  await loadSchedules()
}

async function toggleSchedule(schedule: DpsSchedule) {
  try {
    await dpsApi.updateSchedule(schedule.id, { enabled: !Boolean(schedule.enabled) })
    await loadSchedules()
  } catch (err) {
    ElMessage.error(describeError(err).detail || '切换失败')
  }
}

async function runSchedule(scheduleId: string) {
  try {
    const result = await dpsApi.runSchedule(scheduleId)
    ElMessage.success(`执行完成：${result.status}`)
    await loadSchedules()
  } catch (err) {
    ElMessage.error(describeError(err).detail || '执行失败')
  }
}

async function loadAudit() {
  auditLoading.value = true
  try {
    const payload = await dpsApi.listAuditLogs({
      action: auditAction.value || undefined,
      page: 1,
      page_size: 50,
    })
    auditLogs.value = (payload.items || []) as DpsAuditLog[]
  } catch (err) {
    ElMessage.error(describeError(err).detail || '审计加载失败')
  } finally {
    auditLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadIngest(), loadSchedules(), loadAudit()])
})
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
</style>
