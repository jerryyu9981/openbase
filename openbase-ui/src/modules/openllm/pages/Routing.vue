<template>
  <div>
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="routing-error"
      @close="errorMessage = ''"
    />

    <el-tabs v-model="activeTab" data-test="routing-tabs">
      <el-tab-pane label="路由策略" name="strategies">
        <div class="page-toolbar">
          <el-button type="primary" data-test="create-strategy" @click="openCreateStrategy">新建策略</el-button>
        </div>
        <div v-loading="loading" class="ob-table-scroll">
          <el-table :data="strategies" stripe data-test="strategies-table">
            <template #empty>
              <el-empty description="暂无路由策略，点击上方新建策略" :image-size="60" data-test="strategies-empty" />
            </template>
            <el-table-column prop="name" label="策略名" min-width="150" />
            <el-table-column label="类型" width="110">
              <template #default="{ row }">{{ strategyTypeLabel(row.type) }}</template>
            </el-table-column>
            <el-table-column prop="priority" label="优先级" width="90" />
            <el-table-column prop="target_model" label="目标模型" min-width="150" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="strategyStatusType(row.status)" size="small">{{ strategyStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" data-test="edit-strategy" @click="openEditStrategy(row)">编辑</el-button>
                <el-button link type="primary" data-test="test-strategy" @click="openTestDialog(row)">测试</el-button>
                <el-popconfirm title="确认删除该策略？删除后相关流量将按剩余策略路由" @confirm="removeStrategy(row.id)">
                  <template #reference>
                    <el-button link type="danger" data-test="delete-strategy">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="熔断器" name="breakers">
        <div v-loading="loading" class="ob-table-scroll">
          <el-table :data="breakers" stripe data-test="breakers-table">
            <template #empty>
              <el-empty description="暂无熔断器配置" :image-size="60" data-test="breakers-empty" />
            </template>
            <el-table-column prop="service" label="服务" min-width="160" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="breakerStatusType(row.status)" size="small">{{ breakerStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="失败率" width="110">
              <template #default="{ row }">{{ row.failure_rate }}%</template>
            </el-table-column>
            <el-table-column label="熔断阈值" width="110">
              <template #default="{ row }">{{ row.threshold }}%</template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="success" data-test="manual-open-breaker" @click="manualOpen(row)">手动开启</el-button>
                <el-button link type="info" data-test="manual-close-breaker" @click="manualClose(row)">手动关闭</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="strategyDialogVisible" :title="editingStrategyId ? '编辑策略' : '新建策略'" width="520px" data-test="strategy-dialog">
      <el-form label-width="100px">
        <el-form-item label="策略名" required>
          <el-input v-model="strategyForm.name" placeholder="如：默认权重路由" data-test="strategy-name-input" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="strategyForm.type" style="width: 100%" data-test="strategy-type-select">
            <el-option v-for="type in strategyTypes" :key="type.value" :label="type.label" :value="type.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" required>
          <el-input-number v-model="strategyForm.priority" :min="1" :max="100" :step="1" style="width: 100%" data-test="strategy-priority-input" />
          <div class="text-muted">数值越小优先级越高</div>
        </el-form-item>
        <el-form-item label="目标模型" required>
          <el-select v-model="strategyForm.target_model" placeholder="选择目标模型" style="width: 100%" data-test="strategy-model-select">
            <el-option v-for="model in mockModels" :key="model" :label="model" :value="model" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="strategyDialogVisible = false">取消</el-button>
        <el-button type="primary" data-test="save-strategy" @click="saveStrategy">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="testDialogVisible" :title="`路由测试：${testStrategy?.name || ''}`" width="560px" data-test="route-test-dialog">
      <el-input
        v-model="testPrompt"
        type="textarea"
        :rows="4"
        placeholder="输入一段提示词，模拟路由决策…"
        data-test="test-prompt-input"
      />
      <div class="test-actions">
        <el-button type="primary" data-test="run-route-test" @click="runTest">运行测试</el-button>
        <el-button data-test="clear-route-cache" @click="clearCache">清缓存</el-button>
      </div>
      <el-descriptions v-if="testResult" :column="1" border class="test-result" data-test="test-result">
        <el-descriptions-item label="目标模型">{{ testResult.target_model }}</el-descriptions-item>
        <el-descriptions-item label="匹配策略">{{ testResult.strategy }}</el-descriptions-item>
        <el-descriptions-item label="置信度">{{ testResult.confidence }}</el-descriptions-item>
        <el-descriptions-item label="预估延迟">{{ testResult.latency }}</el-descriptions-item>
        <el-descriptions-item label="说明">{{ testResult.reason }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface RouteStrategy {
  id: number
  name: string
  type: string
  priority: number
  target_model: string
  status: string
}

interface CircuitBreaker {
  id: number
  service: string
  status: string
  failure_rate: number
  threshold: number
}

interface TestResult {
  target_model: string
  strategy: string
  confidence: string
  latency: string
  reason: string
}

const activeTab = ref('strategies')
const loading = ref(true)
const errorMessage = ref('')

const mockModels = ['gpt-4o', 'gpt-4o-mini', 'claude-3-5-sonnet', 'qwen2.5-7b']
const strategyTypes = [
  { value: 'weighted', label: '权重路由' },
  { value: 'priority', label: '优先级路由' },
  { value: 'fallback', label: '兜底路由' },
  { value: 'semantic', label: '语义路由' },
]

function strategyTypeLabel(type: string) {
  return strategyTypes.find((item) => item.value === type)?.label || type
}
function strategyStatusType(status: string) {
  return { enabled: 'success', disabled: 'info' }[status] || 'info'
}
function strategyStatusLabel(status: string) {
  return { enabled: '启用', disabled: '停用' }[status] || status
}
function breakerStatusType(status: string) {
  return { open: 'success', half_open: 'warning', closed: 'info' }[status] || 'info'
}
function breakerStatusLabel(status: string) {
  return { open: '开启', half_open: '半开', closed: '关闭' }[status] || status
}

/** 契约 mock：本地路由策略数据（不调用真实 API） */
const strategies = ref<RouteStrategy[]>([
  { id: 1, name: '默认权重路由', type: 'weighted', priority: 10, target_model: 'gpt-4o-mini', status: 'enabled' },
  { id: 2, name: '付费用户优先', type: 'priority', priority: 5, target_model: 'gpt-4o', status: 'enabled' },
  { id: 3, name: '高并发降级策略', type: 'fallback', priority: 20, target_model: 'qwen2.5-7b', status: 'enabled' },
  { id: 4, name: '夜间省钱策略', type: 'weighted', priority: 30, target_model: 'qwen2.5-7b', status: 'disabled' },
])

/** 契约 mock：本地熔断器数据（不调用真实 API） */
const breakers = ref<CircuitBreaker[]>([
  { id: 1, service: 'gpt-4o', status: 'closed', failure_rate: 1.2, threshold: 50 },
  { id: 2, service: 'claude-3-5-sonnet', status: 'half_open', failure_rate: 28.5, threshold: 50 },
  { id: 3, service: 'qwen2.5-7b', status: 'open', failure_rate: 67.3, threshold: 50 },
])

// ---------- 策略编辑 ----------
const strategyDialogVisible = ref(false)
const editingStrategyId = ref<number | null>(null)
const strategyForm = reactive({
  name: '',
  type: 'weighted',
  priority: 10,
  target_model: 'gpt-4o-mini',
})

function openCreateStrategy() {
  errorMessage.value = ''
  editingStrategyId.value = null
  strategyForm.name = ''
  strategyForm.type = 'weighted'
  strategyForm.priority = 10
  strategyForm.target_model = 'gpt-4o-mini'
  strategyDialogVisible.value = true
}

function openEditStrategy(row: RouteStrategy) {
  errorMessage.value = ''
  editingStrategyId.value = row.id
  strategyForm.name = row.name
  strategyForm.type = row.type
  strategyForm.priority = row.priority
  strategyForm.target_model = row.target_model
  strategyDialogVisible.value = true
}

function saveStrategy() {
  if (!strategyForm.name.trim()) {
    ElMessage.warning('请输入策略名称')
    return
  }
  if (editingStrategyId.value) {
    const target = strategies.value.find((item) => item.id === editingStrategyId.value)
    if (target) {
      Object.assign(target, {
        name: strategyForm.name.trim(),
        type: strategyForm.type,
        priority: strategyForm.priority,
        target_model: strategyForm.target_model,
      })
      ElMessage.success('策略已更新')
    }
  } else {
    strategies.value.push({
      id: Date.now(),
      name: strategyForm.name.trim(),
      type: strategyForm.type,
      priority: strategyForm.priority,
      target_model: strategyForm.target_model,
      status: 'enabled',
    })
    ElMessage.success('策略已创建')
  }
  strategyDialogVisible.value = false
}

function removeStrategy(id: number) {
  const target = strategies.value.find((item) => item.id === id)
  strategies.value = strategies.value.filter((item) => item.id !== id)
  ElMessage.success(`策略「${target?.name || ''}」已删除`)
}

// ---------- 路由测试 ----------
const testDialogVisible = ref(false)
const testStrategy = ref<RouteStrategy | null>(null)
const testPrompt = ref('')
const testResult = ref<TestResult | null>(null)

function openTestDialog(row: RouteStrategy) {
  errorMessage.value = ''
  testStrategy.value = row
  testPrompt.value = ''
  testResult.value = null
  testDialogVisible.value = true
}

function runTest() {
  if (!testStrategy.value) return
  if (!testPrompt.value.trim()) {
    ElMessage.warning('请输入提示词后再测试')
    return
  }
  const strategy = testStrategy.value
  // 契约 mock：本地模拟路由决策（不调用真实 API）
  testResult.value = {
    target_model: strategy.target_model,
    strategy: strategy.name,
    confidence: `${(85 + Math.random() * 14).toFixed(1)}%`,
    latency: `${Math.floor(120 + Math.random() * 380)}ms`,
    reason: strategy.status === 'disabled'
      ? '该策略当前处于停用状态，本次为模拟路由结果，启用后正式生效'
      : '命中策略优先级，成功路由至目标模型',
  }
}

function clearCache() {
  testPrompt.value = ''
  testResult.value = null
  ElMessage.success('路由缓存已清空')
}

// ---------- 熔断器操作 ----------
function manualOpen(row: CircuitBreaker) {
  if (row.status === 'open') {
    // 业务规则：重复开启无意义
    errorMessage.value = `服务「${row.service}」的熔断器已处于开启状态，无需重复操作`
    return
  }
  errorMessage.value = ''
  row.status = 'open'
  ElMessage.success(`服务「${row.service}」熔断器已手动开启，流量将熔断`)
}

function manualClose(row: CircuitBreaker) {
  if (row.status === 'closed') {
    // 业务规则：重复关闭无意义
    errorMessage.value = `服务「${row.service}」的熔断器已处于关闭状态，无需重复操作`
    return
  }
  errorMessage.value = ''
  row.status = 'closed'
  ElMessage.success(`服务「${row.service}」熔断器已手动关闭，流量恢复`)
}

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

onMounted(async () => {
  loading.value = true
  await mockDelay(500) // 契约 mock：模拟加载路由与熔断器数据
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
.test-actions {
  display: flex;
  gap: 12px;
  margin: 12px 0;
}
.test-result {
  margin-top: 12px;
}
</style>
