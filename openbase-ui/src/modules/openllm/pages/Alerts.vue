<template>
  <div>
    <div class="page-toolbar">
      <el-button type="primary" data-test="create-alert-rule" @click="openCreateRule">新建规则</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="alerts-error"
      @close="errorMessage = ''"
    />

    <el-tabs v-model="activeTab" data-test="alerts-tabs">
      <el-tab-pane label="告警规则" name="rules">
        <div v-loading="loading" class="ob-table-scroll">
          <el-table :data="rules" stripe data-test="alert-rules-table">
            <template #empty>
              <el-empty description="暂无告警规则，点击上方新建规则" :image-size="60" data-test="alert-rules-empty" />
            </template>
            <el-table-column prop="name" label="规则名" min-width="150" />
            <el-table-column label="指标" width="130">
              <template #default="{ row }">{{ metricLabel(row.metric) }}</template>
            </el-table-column>
            <el-table-column label="条件阈值" width="140">
              <template #default="{ row }">{{ conditionText(row) }}</template>
            </el-table-column>
            <el-table-column label="级别" width="90">
              <template #default="{ row }">
                <el-tag :type="levelType(row.level)" size="small">{{ levelLabel(row.level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="启停" width="90">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" data-test="rule-toggle" @change="toggleRule(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" data-test="edit-alert-rule" @click="openEditRule(row)">编辑</el-button>
                <el-popconfirm title="确认删除该规则？删除后相关告警将不再触发" @confirm="removeRule(row.id)">
                  <template #reference>
                    <el-button link type="danger" data-test="delete-alert-rule">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="告警历史" name="history">
        <div class="table-toolbar">
          <el-select v-model="historyStatusFilter" placeholder="状态筛选" clearable style="width: 150px" data-test="alert-history-status-filter">
            <el-option label="待处理" value="pending" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已忽略" value="ignored" />
          </el-select>
        </div>
        <div v-loading="loading" class="ob-table-scroll">
          <el-table :data="filteredHistory" stripe data-test="alert-history-table">
            <template #empty>
              <el-empty description="暂无告警历史" :image-size="60" data-test="alert-history-empty" />
            </template>
            <el-table-column prop="time" label="时间" width="160" />
            <el-table-column label="级别" width="90">
              <template #default="{ row }">
                <el-tag :type="levelType(row.level)" size="small">{{ levelLabel(row.level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="rule" label="规则" min-width="140" />
            <el-table-column prop="content" label="内容" min-width="220" show-overflow-tooltip />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="historyStatusType(row.status)" size="small">{{ historyStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" data-test="alert-history-detail" @click="openHistoryDetail(row)">详情</el-button>
                <template v-if="row.status === 'pending'">
                  <el-button link type="success" data-test="resolve-alert" @click="resolveHistory(row.id)">解决</el-button>
                  <el-button link type="info" data-test="ignore-alert" @click="ignoreHistory(row.id)">忽略</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="ruleDialogVisible" :title="editingRuleId ? '编辑规则' : '新建规则'" width="520px" data-test="rule-dialog">
      <el-form label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="ruleForm.name" placeholder="如：延迟超过 500ms 告警" data-test="rule-name-input" />
        </el-form-item>
        <el-form-item label="指标" required>
          <el-select v-model="ruleForm.metric" placeholder="选择指标" style="width: 100%" data-test="rule-metric-select">
            <el-option v-for="metric in metrics" :key="metric.value" :label="metric.label" :value="metric.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件" required>
          <el-select v-model="ruleForm.condition" placeholder="选择条件" style="width: 100%" data-test="rule-condition-select">
            <el-option v-for="condition in conditions" :key="condition.value" :label="condition.label" :value="condition.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值" required>
          <el-input-number v-model="ruleForm.threshold" :min="0" :precision="2" :step="10" style="width: 100%" data-test="rule-threshold-input" />
        </el-form-item>
        <el-form-item label="级别" required>
          <el-select v-model="ruleForm.level" style="width: 100%" data-test="rule-level-select">
            <el-option label="严重" value="critical" />
            <el-option label="警告" value="warning" />
            <el-option label="提示" value="info" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" data-test="save-alert-rule" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="historyDetailVisible" title="告警详情" width="520px" data-test="alert-history-detail-dialog">
      <el-descriptions v-if="historyDetailRow" :column="1" border>
        <el-descriptions-item label="时间">{{ historyDetailRow.time }}</el-descriptions-item>
        <el-descriptions-item label="级别">
          <el-tag :type="levelType(historyDetailRow.level)" size="small">{{ levelLabel(historyDetailRow.level) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="规则">{{ historyDetailRow.rule }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="historyStatusType(historyDetailRow.status)" size="small">{{ historyStatusLabel(historyDetailRow.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="内容">{{ historyDetailRow.content }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface AlertRule {
  id: number
  name: string
  metric: string
  condition: string
  threshold: number
  level: string
  enabled: boolean
}

interface AlertHistory {
  id: number
  time: string
  level: string
  rule: string
  content: string
  status: 'pending' | 'resolved' | 'ignored'
}

const activeTab = ref('rules')
const loading = ref(true)
const errorMessage = ref('')
const historyStatusFilter = ref('')

const metrics = [
  { value: 'latency', label: '延迟(ms)' },
  { value: 'error_rate', label: '错误率(%)' },
  { value: 'tokens', label: 'Token 消耗' },
  { value: 'cost', label: '费用($)' },
  { value: 'qps', label: 'QPS' },
]
const conditions = [
  { value: 'gt', label: '大于 >' },
  { value: 'gte', label: '大于等于 ≥' },
  { value: 'lt', label: '小于 <' },
  { value: 'lte', label: '小于等于 ≤' },
]

function metricLabel(metric: string) {
  return metrics.find((item) => item.value === metric)?.label || metric
}
function conditionLabel(condition: string) {
  return conditions.find((item) => item.value === condition)?.label || condition
}
function levelType(level: string) {
  return { critical: 'danger', warning: 'warning', info: 'info' }[level] || 'info'
}
function levelLabel(level: string) {
  return { critical: '严重', warning: '警告', info: '提示' }[level] || level
}
function historyStatusType(status: string) {
  return { pending: 'warning', resolved: 'success', ignored: 'info' }[status] || 'info'
}
function historyStatusLabel(status: string) {
  return { pending: '待处理', resolved: '已解决', ignored: '已忽略' }[status] || status
}
function conditionText(row: AlertRule) {
  return `${metricLabel(row.metric)} ${conditionLabel(row.condition)} ${row.threshold}`
}

/** 契约 mock：本地告警规则数据（不调用真实 API） */
const rules = ref<AlertRule[]>([
  { id: 1, name: '延迟超过 500ms 告警', metric: 'latency', condition: 'gt', threshold: 500, level: 'warning', enabled: true },
  { id: 2, name: '错误率过高告警', metric: 'error_rate', condition: 'gte', threshold: 5, level: 'critical', enabled: true },
  { id: 3, name: '每日费用超支告警', metric: 'cost', condition: 'gt', threshold: 100, level: 'warning', enabled: false },
  { id: 4, name: 'Token 消耗突增告警', metric: 'tokens', condition: 'gt', threshold: 1000000, level: 'info', enabled: true },
])

/** 契约 mock：本地告警历史数据（不调用真实 API） */
const history = ref<AlertHistory[]>([
  { id: 1, time: '2026-08-27 09:42', level: 'critical', rule: '错误率过高告警', content: 'gpt-4o 错误率 12.6%，持续 5 分钟', status: 'pending' },
  { id: 2, time: '2026-08-27 09:15', level: 'warning', rule: '延迟超过 500ms 告警', content: 'claude-3-5-sonnet P99 延迟 820ms', status: 'pending' },
  { id: 3, time: '2026-08-26 18:30', level: 'warning', rule: '每日费用超支告警', content: '当日费用已达 $86.4，接近阈值 $100', status: 'resolved' },
  { id: 4, time: '2026-08-26 10:05', level: 'info', rule: 'Token 消耗突增告警', content: 'bge-m3 单小时 Token 消耗 1.2M', status: 'ignored' },
  { id: 5, time: '2026-08-25 22:11', level: 'critical', rule: '错误率过高告警', content: 'qwen2.5-7b 错误率 23.1%，服务可能不可用', status: 'resolved' },
])

const filteredHistory = computed(() => {
  const status = historyStatusFilter.value
  return status ? history.value.filter((item) => item.status === status) : history.value
})

// ---------- 规则编辑 ----------
const ruleDialogVisible = ref(false)
const editingRuleId = ref<number | null>(null)
const ruleForm = reactive({
  name: '',
  metric: 'latency',
  condition: 'gt',
  threshold: 100,
  level: 'warning',
})

function openCreateRule() {
  errorMessage.value = ''
  editingRuleId.value = null
  ruleForm.name = ''
  ruleForm.metric = 'latency'
  ruleForm.condition = 'gt'
  ruleForm.threshold = 100
  ruleForm.level = 'warning'
  ruleDialogVisible.value = true
}

function openEditRule(row: AlertRule) {
  errorMessage.value = ''
  editingRuleId.value = row.id
  ruleForm.name = row.name
  ruleForm.metric = row.metric
  ruleForm.condition = row.condition
  ruleForm.threshold = row.threshold
  ruleForm.level = row.level
  ruleDialogVisible.value = true
}

function saveRule() {
  if (!ruleForm.name.trim()) {
    ElMessage.warning('请输入规则名称')
    return
  }
  if (editingRuleId.value) {
    const target = rules.value.find((item) => item.id === editingRuleId.value)
    if (target) {
      Object.assign(target, {
        name: ruleForm.name.trim(),
        metric: ruleForm.metric,
        condition: ruleForm.condition,
        threshold: ruleForm.threshold,
        level: ruleForm.level,
      })
      ElMessage.success('规则已更新')
    }
  } else {
    rules.value.push({
      id: Date.now(),
      name: ruleForm.name.trim(),
      metric: ruleForm.metric,
      condition: ruleForm.condition,
      threshold: ruleForm.threshold,
      level: ruleForm.level,
      enabled: true,
    })
    ElMessage.success('规则已创建')
  }
  ruleDialogVisible.value = false
}

function toggleRule(row: AlertRule) {
  ElMessage.success(`规则「${row.name}」已${row.enabled ? '启用' : '停用'}`)
}

function removeRule(id: number) {
  const target = rules.value.find((item) => item.id === id)
  rules.value = rules.value.filter((item) => item.id !== id)
  ElMessage.success(`规则「${target?.name || ''}」已删除`)
}

// ---------- 告警历史操作 ----------
const historyDetailVisible = ref(false)
const historyDetailRow = ref<AlertHistory | null>(null)

function openHistoryDetail(row: AlertHistory) {
  historyDetailRow.value = row
  historyDetailVisible.value = true
}

function resolveHistory(id: number) {
  const target = history.value.find((item) => item.id === id)
  if (target) {
    target.status = 'resolved'
    ElMessage.success('告警已标记为已解决')
  }
}

function ignoreHistory(id: number) {
  const target = history.value.find((item) => item.id === id)
  if (!target) return
  if (target.level === 'critical') {
    // 业务规则：严重级别告警不允许直接忽略
    errorMessage.value = '严重级别告警不允许直接忽略，请先「解决」确认恢复后再关闭'
    return
  }
  target.status = 'ignored'
  ElMessage.success('告警已忽略')
}

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

onMounted(async () => {
  loading.value = true
  await mockDelay(500) // 契约 mock：模拟加载告警数据
  loading.value = false
})
</script>

<style scoped>
.page-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.mb-16 {
  margin-bottom: 16px;
}
.table-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
</style>
