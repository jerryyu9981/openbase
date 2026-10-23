<template>
  <PageContainer :title="pageTitle" description="语义路由策略与熔断器（按路由 meta 呈现标题）" test-id="routing-page">
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
          <el-button :loading="loading" data-test="routing-refresh" @click="loadRoutes">刷新</el-button>
          <el-button data-test="route-cache-stats" @click="showCacheStats">缓存统计</el-button>
        </div>
        <div v-loading="loading" class="ob-table-scroll">
          <el-table :data="routes" stripe data-test="strategies-table">
            <template #empty>
              <el-empty description="暂无路由策略，点击上方新建策略" :image-size="60" data-test="strategies-empty" />
            </template>
            <el-table-column prop="name" label="策略名" min-width="150" />
            <el-table-column prop="category" label="类别" width="120" />
            <el-table-column prop="priority" label="优先级" width="90" />
            <el-table-column label="阈值" width="90">
              <template #default="{ row }">{{ Number(row.threshold ?? 0).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="启用" width="90">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" data-test="strategy-toggle" @change="toggleRoute(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" data-test="edit-strategy" @click="openEditStrategy(row)">编辑</el-button>
                <el-button link type="primary" data-test="test-strategy" @click="openTestDialog">测试</el-button>
                <el-popconfirm title="确认删除该策略？" @confirm="removeStrategy(row.id)">
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
        <div class="page-toolbar">
          <el-button :loading="breakerLoading" data-test="breaker-refresh" @click="loadBreakers">刷新</el-button>
        </div>
        <div v-loading="breakerLoading" class="ob-table-scroll">
          <el-table :data="breakers" stripe data-test="breakers-table">
            <template #empty>
              <el-empty description="暂无熔断器配置" :image-size="60" data-test="breakers-empty" />
            </template>
            <el-table-column prop="provider" label="提供商" min-width="140" />
            <el-table-column prop="model" label="模型" min-width="140" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="breakerStatusType(row.state)" size="small">{{ breakerStatusLabel(row.state) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="错误率" width="110">
              <template #default="{ row }">{{ (Number(row.error_rate ?? 0) * 100).toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column prop="total_calls" label="总调用" width="100" />
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-popconfirm title="确认重置该熔断器？" @confirm="resetBreaker(row.id)">
                  <template #reference>
                    <el-button link type="warning" data-test="breaker-reset">重置</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="strategyDialogVisible" :title="editingStrategyId ? '编辑策略' : '新建策略'" width="560px" data-test="strategy-dialog">
      <el-form label-width="100px">
        <el-form-item label="策略名" required>
          <el-input v-model="strategyForm.name" placeholder="如：客服意图路由" data-test="strategy-name-input" />
        </el-form-item>
        <el-form-item label="类别" required>
          <el-input v-model="strategyForm.category" placeholder="如：chat" data-test="strategy-category-input" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="strategyForm.priority" :min="0" :max="1000" :step="1" style="width: 100%" data-test="strategy-priority-input" />
          <div class="text-muted">数值越大优先级越高</div>
        </el-form-item>
        <el-form-item label="相似度阈值">
          <el-input-number v-model="strategyForm.threshold" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="示例问题">
          <el-input
            v-model="strategyForm.sampleQueries"
            type="textarea"
            :rows="4"
            placeholder="每行一条示例问题，用于计算语义向量"
            data-test="strategy-samples-input"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="strategyForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="strategyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="save-strategy" @click="saveStrategy">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="testDialogVisible" title="语义路由测试" width="580px" data-test="route-test-dialog">
      <el-input
        v-model="testPrompt"
        type="textarea"
        :rows="4"
        placeholder="输入一段提示词，模拟路由决策…"
        data-test="test-prompt-input"
      />
      <div class="test-actions">
        <el-button type="primary" :loading="testing" data-test="run-route-test" @click="runTest">运行测试</el-button>
        <el-button data-test="clear-route-cache" @click="clearCache">清缓存</el-button>
      </div>
      <el-descriptions v-if="testResult" :column="1" border class="test-result" data-test="test-result">
        <el-descriptions-item label="是否命中">{{ testResult.result.matched ? '命中' : '未命中' }}</el-descriptions-item>
        <el-descriptions-item label="匹配类别">{{ testResult.result.category || '-' }}</el-descriptions-item>
        <el-descriptions-item label="相似度">{{ Number(testResult.result.similarity_score ?? 0).toFixed(4) }}</el-descriptions-item>
        <el-descriptions-item label="目标模型">{{ testResult.result.model_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="来源">{{ testResult.result.from_cache ? '缓存' : '实时计算' }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ testResult.processing_time_ms }} ms</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageContainer from '@/components/page/PageContainer.vue'
import {
  circuitBreakersApi,
  routingApi,
  type LlmCircuitBreaker,
  type LlmRouteTestResponse,
  type LlmSemanticRoute,
} from '@/core/api/governance'

/**
 * 路由策略与熔断器（v1.9.5 R5 真实化）：
 * - 策略 = OpenLLM 语义路由 `/routing/semantic`（列表/新建/编辑/启停/删除/测试/缓存）
 * - 熔断器 = `/routing/circuit-breakers`（列表/重置）
 * 上游未提供「手动开启/关闭」端点，本轮仅保留「重置」，不做本地假动作。
 */
const route = useRoute()
const pageTitle = computed(() => (route.meta.title as string) || '路由策略')

const activeTab = ref('strategies')
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')

const routes = ref<LlmSemanticRoute[]>([])
const breakers = ref<LlmCircuitBreaker[]>([])
const breakerLoading = ref(false)

function breakerStatusType(state: string) {
  const normalized = (state || '').toUpperCase()
  return { OPEN: 'danger', HALF_OPEN: 'warning', CLOSED: 'success' }[normalized] || 'info'
}
function breakerStatusLabel(state: string) {
  const normalized = (state || '').toUpperCase()
  return { OPEN: '开启', HALF_OPEN: '半开', CLOSED: '关闭' }[normalized] || state
}

async function loadRoutes() {
  loading.value = true
  errorMessage.value = ''
  try {
    const page = await routingApi.list({ limit: 200 })
    routes.value = page.items
  } catch (error) {
    errorMessage.value = `路由策略加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

async function loadBreakers() {
  breakerLoading.value = true
  try {
    const page = await circuitBreakersApi.list({ page: 1, page_size: 100 })
    breakers.value = page.items
  } catch (error) {
    errorMessage.value = `熔断器加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    breakerLoading.value = false
  }
}

// ---------- 策略编辑 ----------
const strategyDialogVisible = ref(false)
const editingStrategyId = ref<string | null>(null)
const strategyForm = reactive({
  name: '',
  category: 'chat',
  priority: 10,
  threshold: 0.7,
  sampleQueries: '',
  description: '',
})

function openCreateStrategy() {
  errorMessage.value = ''
  editingStrategyId.value = null
  strategyForm.name = ''
  strategyForm.category = 'chat'
  strategyForm.priority = 10
  strategyForm.threshold = 0.7
  strategyForm.sampleQueries = ''
  strategyForm.description = ''
  strategyDialogVisible.value = true
}

function openEditStrategy(row: LlmSemanticRoute) {
  errorMessage.value = ''
  editingStrategyId.value = row.id
  strategyForm.name = row.name
  strategyForm.category = row.category
  strategyForm.priority = row.priority
  strategyForm.threshold = row.threshold
  strategyForm.sampleQueries = (row.sample_queries || []).join('\n')
  strategyForm.description = row.description || ''
  strategyDialogVisible.value = true
}

function sampleQueries(): string[] {
  return strategyForm.sampleQueries
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

async function saveStrategy() {
  if (!strategyForm.name.trim() || !strategyForm.category.trim()) {
    ElMessage.warning('请填写策略名与类别')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: strategyForm.name.trim(),
      category: strategyForm.category.trim(),
      priority: strategyForm.priority,
      threshold: strategyForm.threshold,
      sample_queries: sampleQueries(),
      description: strategyForm.description || undefined,
    }
    if (editingStrategyId.value) {
      await routingApi.update(editingStrategyId.value, payload)
      ElMessage.success('策略已更新')
    } else {
      await routingApi.create({ ...payload, enabled: true })
      ElMessage.success('策略已创建')
    }
    strategyDialogVisible.value = false
    await loadRoutes()
  } catch (error) {
    errorMessage.value = `策略保存失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    saving.value = false
  }
}

async function toggleRoute(row: LlmSemanticRoute) {
  const next = row.enabled
  try {
    await routingApi.update(row.id, { enabled: next })
    ElMessage.success(next ? '策略已启用' : '策略已停用')
  } catch (error) {
    row.enabled = !next
    errorMessage.value = `策略启停失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function removeStrategy(routeId: string) {
  try {
    await routingApi.remove(routeId)
    ElMessage.success('策略已删除')
    await loadRoutes()
  } catch (error) {
    errorMessage.value = `策略删除失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

// ---------- 路由测试 ----------
const testDialogVisible = ref(false)
const testPrompt = ref('')
const testing = ref(false)
const testResult = ref<LlmRouteTestResponse | null>(null)

function openTestDialog() {
  errorMessage.value = ''
  testPrompt.value = ''
  testResult.value = null
  testDialogVisible.value = true
}

async function runTest() {
  if (!testPrompt.value.trim()) {
    ElMessage.warning('请输入提示词后再测试')
    return
  }
  testing.value = true
  try {
    testResult.value = await routingApi.test({ message: testPrompt.value.trim() })
  } catch (error) {
    errorMessage.value = `路由测试失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    testing.value = false
  }
}

async function clearCache() {
  try {
    await routingApi.clearCache()
    testResult.value = null
    ElMessage.success('路由缓存已清空')
  } catch (error) {
    errorMessage.value = `清缓存失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function showCacheStats() {
  try {
    const stats = await routingApi.cacheStats()
    ElMessage.success(
      `缓存：${stats.current_size}/${stats.max_size}，命中率 ${stats.hit_rate_percent}%，查询均值 ${stats.avg_lookup_time_ms}ms`,
    )
  } catch (error) {
    errorMessage.value = `缓存统计加载失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

// ---------- 熔断器 ----------
async function resetBreaker(breakerId: string) {
  try {
    const result = await circuitBreakersApi.reset(breakerId)
    ElMessage.success(result.message || `熔断器已重置（${result.current_state}）`)
    await loadBreakers()
  } catch (error) {
    errorMessage.value = `熔断器重置失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

onMounted(async () => {
  await Promise.all([loadRoutes(), loadBreakers()])
})
</script>

<style scoped>
.mb-16 {
  margin-bottom: 16px;
}
.text-muted {
  color: var(--ob-text-secondary);
  font-size: 12px;
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
