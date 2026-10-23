<template>
  <PageContainer title="告警中心" description="告警规则与告警记录（OpenLLM 告警服务）" test-id="alerts-page">
    <div class="page-toolbar">
      <el-button type="primary" data-test="create-alert-rule" @click="openCreateRule">新建规则</el-button>
      <el-button :loading="loading" data-test="alerts-refresh" @click="loadAll">刷新</el-button>
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
            <el-table-column label="类型" width="120">
              <template #default="{ row }">{{ alertTypeLabel(row.alert_type) }}</template>
            </el-table-column>
            <el-table-column label="触发条件" width="180">
              <template #default="{ row }">{{ conditionText(row) }}</template>
            </el-table-column>
            <el-table-column label="级别" width="90">
              <template #default="{ row }">
                <el-tag :type="levelType(row.severity)" size="small">{{ levelLabel(row.severity) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="最近触发" width="170">
              <template #default="{ row }">{{ formatTime(row.last_fired_at) }}</template>
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
          <el-select
            v-model="historyStatusFilter"
            placeholder="状态筛选"
            clearable
            style="width: 150px"
            data-test="alert-history-status-filter"
            @change="reloadHistory"
          >
            <el-option label="触发中" value="firing" />
            <el-option label="已确认" value="acknowledged" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已静默" value="silenced" />
          </el-select>
        </div>
        <div v-loading="historyLoading" class="ob-table-scroll">
          <el-table :data="alerts" stripe data-test="alert-history-table">
            <template #empty>
              <el-empty description="暂无告警历史" :image-size="60" data-test="alert-history-empty" />
            </template>
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatTime(row.fired_at || row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="级别" width="90">
              <template #default="{ row }">
                <el-tag :type="levelType(row.severity)" size="small">{{ levelLabel(row.severity) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
            <el-table-column prop="message" label="内容" min-width="220" show-overflow-tooltip />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="historyStatusType(row.status)" size="small">{{ historyStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" data-test="alert-history-detail" @click="openHistoryDetail(row)">详情</el-button>
                <template v-if="row.status === 'firing'">
                  <el-button link type="info" data-test="ignore-alert" @click="acknowledgeHistory(row.id)">确认</el-button>
                  <el-button link type="success" data-test="resolve-alert" @click="resolveHistory(row.id)">解决</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-pagination
          v-model:current-page="historyPage"
          v-model:page-size="historyPageSize"
          :total="historyTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          class="pagination"
          data-test="alert-history-pagination"
          @current-change="loadHistory"
          @size-change="reloadHistory"
        />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="ruleDialogVisible" :title="editingRuleId ? '编辑规则' : '新建规则'" width="540px" data-test="rule-dialog">
      <el-form label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="ruleForm.name" placeholder="如：延迟超过 500ms 告警" data-test="rule-name-input" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="ruleForm.alert_type" placeholder="选择类型" style="width: 100%" data-test="rule-type-select">
            <el-option v-for="item in alertTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="指标" required>
          <el-select v-model="ruleForm.metric" placeholder="选择指标" style="width: 100%" data-test="rule-metric-select">
            <el-option v-for="metric in metrics" :key="metric.value" :label="metric.label" :value="metric.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件" required>
          <el-select v-model="ruleForm.operator" placeholder="选择条件" style="width: 100%" data-test="rule-condition-select">
            <el-option v-for="condition in conditions" :key="condition.value" :label="condition.label" :value="condition.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值" required>
          <el-input-number
            v-model="ruleForm.threshold"
            :min="0"
            :precision="2"
            :step="10"
            style="width: 100%"
            data-test="rule-threshold-input"
          />
        </el-form-item>
        <el-form-item label="级别" required>
          <el-select v-model="ruleForm.severity" style="width: 100%" data-test="rule-level-select">
            <el-option label="严重" value="critical" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
            <el-option label="提示" value="info" />
          </el-select>
        </el-form-item>
        <el-form-item label="冷却(秒)">
          <el-input-number v-model="ruleForm.cooldown_seconds" :min="0" :step="60" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="save-alert-rule" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="historyDetailVisible" title="告警详情" width="560px" data-test="alert-history-detail-dialog">
      <el-descriptions v-if="historyDetailRow" :column="1" border>
        <el-descriptions-item label="时间">{{ formatTime(historyDetailRow.fired_at || historyDetailRow.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="级别">
          <el-tag :type="levelType(historyDetailRow.severity)" size="small">{{ levelLabel(historyDetailRow.severity) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="类型">{{ alertTypeLabel(historyDetailRow.alert_type) }}</el-descriptions-item>
        <el-descriptions-item label="标题">{{ historyDetailRow.title }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="historyStatusType(historyDetailRow.status)" size="small">
            {{ historyStatusLabel(historyDetailRow.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="内容">{{ historyDetailRow.message }}</el-descriptions-item>
        <el-descriptions-item label="提供商">{{ historyDetailRow.provider || '-' }}</el-descriptions-item>
        <el-descriptions-item label="模型">{{ historyDetailRow.model || '-' }}</el-descriptions-item>
        <el-descriptions-item label="解决时间">{{ formatTime(historyDetailRow.resolved_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { alertsApi, type LlmAlertItem, type LlmAlertRule } from '@/core/api/governance'

/**
 * 告警中心（v1.9.4 R4 真实化）：规则 = `/api/v1/alerts/rules`，记录 = `/api/v1/alerts`。
 * 所有写操作（新建/编辑/启停/删除/确认/解决）均走上游真实端点，失败即错误态，不做本地假成功。
 */
const activeTab = ref('rules')
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')

const rules = ref<LlmAlertRule[]>([])
const alerts = ref<LlmAlertItem[]>([])

const alertTypes = [
  { value: 'provider_health', label: '提供商健康' },
  { value: 'latency_spike', label: '延迟激增' },
  { value: 'error_rate', label: '错误率' },
  { value: 'cost_threshold', label: '成本阈值' },
  { value: 'quota_exceeded', label: '配额超限' },
  { value: 'token_usage', label: 'Token 用量' },
  { value: 'rate_limit', label: '速率限制' },
  { value: 'system_resource', label: '系统资源' },
  { value: 'custom', label: '自定义' },
]
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

function alertTypeLabel(alertType: string) {
  return alertTypes.find((item) => item.value === alertType)?.label || alertType
}
function metricLabel(metric: string) {
  return metrics.find((item) => item.value === metric)?.label || metric
}
function conditionLabel(condition: string) {
  return conditions.find((item) => item.value === condition)?.label || condition
}
function levelType(level: string) {
  return { critical: 'danger', high: 'danger', medium: 'warning', low: 'info', info: 'info' }[level] || 'info'
}
function levelLabel(level: string) {
  return { critical: '严重', high: '高', medium: '中', low: '低', info: '提示' }[level] || level
}
function historyStatusType(status: string) {
  return { firing: 'danger', acknowledged: 'warning', resolved: 'success', silenced: 'info' }[status] || 'info'
}
function historyStatusLabel(status: string) {
  return { firing: '触发中', acknowledged: '已确认', resolved: '已解决', silenced: '已静默' }[status] || status
}
function formatTime(value: string | null | undefined) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

function conditionText(row: LlmAlertRule) {
  const condition = row.condition || {}
  const metric = typeof condition.metric === 'string' ? condition.metric : ''
  const operator = typeof condition.operator === 'string' ? condition.operator : ''
  const threshold = condition.threshold
  if (metric && operator && threshold !== undefined) {
    return `${metricLabel(metric)} ${conditionLabel(operator)} ${threshold}`
  }
  return JSON.stringify(condition)
}

// ---------- 规则 ----------
async function loadRules() {
  try {
    const page = await alertsApi.listRules({ page: 1, page_size: 100 })
    rules.value = page.rules
  } catch (error) {
    errorMessage.value = `告警规则加载失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

const ruleDialogVisible = ref(false)
const editingRuleId = ref<string | null>(null)
const ruleForm = reactive({
  name: '',
  alert_type: 'latency_spike',
  metric: 'latency',
  operator: 'gt',
  threshold: 100,
  severity: 'medium',
  cooldown_seconds: 300,
})

function openCreateRule() {
  errorMessage.value = ''
  editingRuleId.value = null
  ruleForm.name = ''
  ruleForm.alert_type = 'latency_spike'
  ruleForm.metric = 'latency'
  ruleForm.operator = 'gt'
  ruleForm.threshold = 100
  ruleForm.severity = 'medium'
  ruleForm.cooldown_seconds = 300
  ruleDialogVisible.value = true
}

function openEditRule(row: LlmAlertRule) {
  errorMessage.value = ''
  editingRuleId.value = row.id
  const condition = row.condition || {}
  ruleForm.name = row.name
  ruleForm.alert_type = row.alert_type
  ruleForm.metric = typeof condition.metric === 'string' ? condition.metric : 'latency'
  ruleForm.operator = typeof condition.operator === 'string' ? condition.operator : 'gt'
  ruleForm.threshold = typeof condition.threshold === 'number' ? condition.threshold : 0
  ruleForm.severity = row.severity
  ruleForm.cooldown_seconds = row.cooldown_seconds
  ruleDialogVisible.value = true
}

async function saveRule() {
  if (!ruleForm.name.trim()) {
    ElMessage.warning('请输入规则名称')
    return
  }
  const payload = {
    name: ruleForm.name.trim(),
    alert_type: ruleForm.alert_type,
    condition: { metric: ruleForm.metric, operator: ruleForm.operator, threshold: ruleForm.threshold },
    severity: ruleForm.severity,
    cooldown_seconds: ruleForm.cooldown_seconds,
  }
  saving.value = true
  try {
    if (editingRuleId.value) {
      await alertsApi.updateRule(editingRuleId.value, payload)
      ElMessage.success('规则已更新')
    } else {
      await alertsApi.createRule(payload)
      ElMessage.success('规则已创建')
    }
    ruleDialogVisible.value = false
    await loadRules()
  } catch (error) {
    errorMessage.value = `规则保存失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    saving.value = false
  }
}

async function toggleRule(row: LlmAlertRule) {
  const nextEnabled = row.enabled
  try {
    await alertsApi.updateRule(row.id, { enabled: nextEnabled })
    ElMessage.success(`规则「${row.name}」已${nextEnabled ? '启用' : '停用'}`)
  } catch (error) {
    row.enabled = !nextEnabled
    errorMessage.value = `规则启停失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function removeRule(ruleId: string) {
  try {
    await alertsApi.removeRule(ruleId)
    ElMessage.success('规则已删除')
    await loadRules()
  } catch (error) {
    errorMessage.value = `规则删除失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

// ---------- 告警历史 ----------
const historyStatusFilter = ref('')
const historyLoading = ref(false)
const historyPage = ref(1)
const historyPageSize = ref(20)
const historyTotal = ref(0)

async function loadHistory() {
  historyLoading.value = true
  try {
    const page = await alertsApi.list({
      status: historyStatusFilter.value || undefined,
      page: historyPage.value,
      page_size: historyPageSize.value,
    })
    alerts.value = page.alerts
    historyTotal.value = page.total
  } catch (error) {
    errorMessage.value = `告警历史加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    historyLoading.value = false
  }
}

function reloadHistory() {
  historyPage.value = 1
  void loadHistory()
}

const historyDetailVisible = ref(false)
const historyDetailRow = ref<LlmAlertItem | null>(null)

function openHistoryDetail(row: LlmAlertItem) {
  historyDetailRow.value = row
  historyDetailVisible.value = true
}

async function resolveHistory(alertId: string) {
  try {
    await alertsApi.resolve(alertId)
    ElMessage.success('告警已标记为已解决')
    await loadHistory()
  } catch (error) {
    errorMessage.value = `告警解决失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function acknowledgeHistory(alertId: string) {
  try {
    await alertsApi.acknowledge(alertId)
    ElMessage.success('告警已确认')
    await loadHistory()
  } catch (error) {
    errorMessage.value = `告警确认失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function loadAll() {
  errorMessage.value = ''
  loading.value = true
  try {
    await Promise.all([loadRules(), loadHistory()])
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.mb-16 {
  margin-bottom: 16px;
}
.table-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.pagination {
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
