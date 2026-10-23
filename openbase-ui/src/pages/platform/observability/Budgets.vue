<template>
  <PageContainer title="预算管理" description="预算额度、用量进度与预测（OpenLLM 成本服务）" test-id="budgets-page">
    <div class="page-toolbar">
      <el-button type="primary" data-test="create-budget" @click="openCreate">新建预算</el-button>
      <el-button :loading="loading" data-test="budget-refresh" @click="loadBudgets">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="budgets-error"
      @close="errorMessage = ''"
    />

    <el-card header="预算列表" data-test="budget-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="budgets" stripe data-test="budget-table">
          <template #empty>
            <el-empty description="暂无预算，点击左上角新建" :image-size="60" data-test="budgets-empty" />
          </template>
          <el-table-column prop="name" label="预算名" min-width="160" />
          <el-table-column label="范围" width="100">
            <template #default="{ row }">{{ scopeLabel(row.scope) }}</template>
          </el-table-column>
          <el-table-column label="周期" width="90">
            <template #default="{ row }">{{ periodLabel(row.period) }}</template>
          </el-table-column>
          <el-table-column label="额度($)" width="120">
            <template #default="{ row }">{{ formatAmount(row.limit_usd) }}</template>
          </el-table-column>
          <el-table-column label="已用($)" width="120">
            <template #default="{ row }">{{ formatAmount(row.current_usage_usd) }}</template>
          </el-table-column>
          <el-table-column label="进度" min-width="200">
            <template #default="{ row }">
              <el-progress
                :percentage="progressPercent(row)"
                :status="row.is_exceeded ? 'exception' : undefined"
                data-test="budget-progress"
              />
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_exceeded ? 'danger' : row.enabled ? 'success' : 'info'" size="small">
                {{ row.is_exceeded ? '已超限' : row.enabled ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" data-test="budget-status" @click="openStatus(row)">状态</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="createVisible" title="新建预算" width="540px" data-test="budget-dialog">
      <el-form label-width="110px">
        <el-form-item label="预算名" required>
          <el-input v-model="form.name" placeholder="如：AI 研发月度预算" data-test="budget-name-input" />
        </el-form-item>
        <el-form-item label="范围" required>
          <el-select v-model="form.scope" style="width: 100%" data-test="budget-scope-select">
            <el-option v-for="item in SCOPES" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="周期" required>
          <el-select v-model="form.period" style="width: 100%" data-test="budget-period-select">
            <el-option v-for="item in PERIODS" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="额度($)" required>
          <el-input-number v-model="form.limit_usd" :min="1" :step="100" style="width: 100%" data-test="budget-limit-input" />
        </el-form-item>
        <el-form-item label="告警阈值">
          <el-input-number
            v-model="form.alert_threshold"
            :min="1"
            :max="100"
            :step="5"
            style="width: 100%"
            data-test="budget-threshold-input"
          />
          <div class="text-muted">达到该百分比时触发 warning 告警</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="budget-submit" @click="submit">创建</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="statusVisible" title="预算状态" size="460px" data-test="budget-status-drawer">
      <div v-loading="statusLoading">
        <el-descriptions v-if="statusDetail" :column="1" border data-test="budget-status-meta">
          <el-descriptions-item label="预算名">{{ statusDetail.name }}</el-descriptions-item>
          <el-descriptions-item label="范围">{{ scopeLabel(statusDetail.scope) }}</el-descriptions-item>
          <el-descriptions-item label="周期">{{ periodLabel(statusDetail.period) }}</el-descriptions-item>
          <el-descriptions-item label="额度($)">{{ formatAmount(statusDetail.limit_usd) }}</el-descriptions-item>
          <el-descriptions-item label="已用($)">{{ formatAmount(statusDetail.current_usage_usd) }}</el-descriptions-item>
          <el-descriptions-item label="使用率">{{ Number(statusDetail.usage_percentage ?? 0).toFixed(1) }}%</el-descriptions-item>
          <el-descriptions-item label="剩余($)">{{ formatAmount(statusDetail.remaining_usd) }}</el-descriptions-item>
          <el-descriptions-item label="剩余天数">{{ statusDetail.days_remaining }}</el-descriptions-item>
          <el-descriptions-item label="预测用量($)">{{ formatAmount(statusDetail.projected_usage_usd) }}</el-descriptions-item>
          <el-descriptions-item label="是否超限">
            <el-tag :type="statusDetail.is_exceeded ? 'danger' : 'success'" size="small">
              {{ statusDetail.is_exceeded ? '已超限' : '正常' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { budgetsApi, type LlmBudget, type LlmBudgetStatus } from '@/core/api/governance'

/**
 * 预算管理（v1.9.4 R4 新增）：替换原 GenericPage 占位。
 * 数据源：`/api/v1/budgets`、`/api/v1/budgets/{id}/status`。
 */
const SCOPES = [
  { value: 'global', label: '全局' },
  { value: 'team', label: '团队' },
  { value: 'project', label: '项目' },
  { value: 'workspace', label: '工作区' },
  { value: 'user', label: '用户' },
  { value: 'api_key', label: 'API Key' },
]
const PERIODS = [
  { value: 'daily', label: '日' },
  { value: 'weekly', label: '周' },
  { value: 'monthly', label: '月度' },
  { value: 'quarterly', label: '季度' },
  { value: 'yearly', label: '年度' },
]

const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const budgets = ref<LlmBudget[]>([])

const createVisible = ref(false)
const form = reactive({
  name: '',
  scope: 'global',
  period: 'monthly',
  limit_usd: 500,
  alert_threshold: 80,
})

const statusVisible = ref(false)
const statusLoading = ref(false)
const statusDetail = ref<LlmBudgetStatus | null>(null)

function scopeLabel(scope: string) {
  return SCOPES.find((item) => item.value === scope)?.label || scope
}
function periodLabel(period: string) {
  return PERIODS.find((item) => item.value === period)?.label || period
}
function formatAmount(value: number | null | undefined) {
  return Number(value ?? 0).toFixed(2)
}
function progressPercent(row: LlmBudget) {
  return Math.max(0, Math.min(100, Math.round(Number(row.usage_percentage ?? 0))))
}

async function loadBudgets() {
  loading.value = true
  errorMessage.value = ''
  try {
    const page = await budgetsApi.list({ page: 1, page_size: 100 })
    budgets.value = page.budgets
  } catch (error) {
    errorMessage.value = `预算列表加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

function openCreate() {
  errorMessage.value = ''
  form.name = ''
  form.scope = 'global'
  form.period = 'monthly'
  form.limit_usd = 500
  form.alert_threshold = 80
  createVisible.value = true
}

async function submit() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入预算名称')
    return
  }
  if (form.limit_usd <= 0) {
    errorMessage.value = '预算额度必须大于 0'
    return
  }
  saving.value = true
  try {
    await budgetsApi.create({
      name: form.name.trim(),
      scope: form.scope,
      period: form.period,
      limit_usd: form.limit_usd,
      alert_thresholds: [{ type: 'warning', value: form.alert_threshold }],
    })
    createVisible.value = false
    ElMessage.success('预算已创建')
    await loadBudgets()
  } catch (error) {
    errorMessage.value = `预算创建失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    saving.value = false
  }
}

async function openStatus(row: LlmBudget) {
  statusVisible.value = true
  statusLoading.value = true
  statusDetail.value = null
  try {
    statusDetail.value = await budgetsApi.status(row.id)
  } catch (error) {
    errorMessage.value = `预算状态加载失败：${error instanceof Error ? error.message : '未知错误'}`
    statusVisible.value = false
  } finally {
    statusLoading.value = false
  }
}

onMounted(loadBudgets)
</script>

<style scoped>
.mb-16 {
  margin-bottom: 16px;
}
.text-muted {
  color: var(--ob-text-secondary);
  font-size: 12px;
}
</style>
