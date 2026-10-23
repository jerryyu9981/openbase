<template>
  <PageContainer title="A/B 测试" description="模型流量对比实验（OpenLLM A/B Test）" test-id="ab-test-view-page">
    <div class="page-toolbar">
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px" data-test="ab-status-filter" @change="load">
        <el-option label="运行中" value="running" />
        <el-option label="已暂停" value="paused" />
        <el-option label="已完成" value="completed" />
      </el-select>
      <el-button type="primary" data-test="ab-new" @click="openCreate">创建实验</el-button>
      <el-button :loading="loading" data-test="ab-refresh" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="ab-error"
      @close="errorMessage = ''"
    />

    <el-card header="A/B 测试实验" data-test="ab-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="experiments" stripe data-test="ab-table">
          <template #empty>
            <el-empty description="暂无实验" :image-size="60" data-test="ab-empty" />
          </template>
          <el-table-column prop="name" label="实验名称" min-width="170" />
          <el-table-column prop="model_a" label="模型 A" width="150" />
          <el-table-column prop="model_b" label="模型 B" width="150" />
          <el-table-column label="流量 A" width="130">
            <template #default="{ row }">
              <div class="traffic-bar">
                <span class="traffic-a">{{ trafficA(row) }}%</span>
                <el-progress :percentage="trafficA(row)" :show-text="false" :stroke-width="10" color="#1677FF" />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small" data-test="ab-status">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'paused'" link type="success" size="small" data-test="ab-start" @click="resume(row)">
                启动
              </el-button>
              <el-button v-if="row.status === 'running'" link type="warning" size="small" data-test="ab-stop" @click="pause(row)">
                暂停
              </el-button>
              <el-button
                v-if="row.status === 'running' || row.status === 'paused'"
                link
                type="info"
                size="small"
                data-test="ab-archive"
                @click="complete(row)"
              >
                完成
              </el-button>
              <el-button link type="primary" size="small" data-test="ab-detail" @click="openDetail(row)">详情</el-button>
              <el-popconfirm title="确认删除该实验？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small" data-test="ab-delete">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="dialogOpen" title="创建 A/B 实验" width="540px" data-test="ab-dialog">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" data-test="ab-name" />
        </el-form-item>
        <el-form-item label="模型 A" required>
          <el-input v-model="form.model_a" placeholder="对照组模型" data-test="ab-model-a" />
        </el-form-item>
        <el-form-item label="模型 B" required>
          <el-input v-model="form.model_b" placeholder="实验组模型" data-test="ab-model-b" />
        </el-form-item>
        <el-form-item label="流量占比 A">
          <el-input-number v-model="form.ratioA" :min="1" :max="99" data-test="ab-ratio-a" /> %
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="ab-save" @click="save">创建</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailOpen" :title="`实验详情 - ${currentDetail?.name || ''}`" size="620px" data-test="ab-detail-drawer">
      <div v-loading="detailLoading">
        <el-descriptions v-if="currentDetail" :column="2" border>
          <el-descriptions-item label="模型 A">{{ currentDetail.model_a }}</el-descriptions-item>
          <el-descriptions-item label="模型 B">{{ currentDetail.model_b }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(currentDetail.status) }}</el-descriptions-item>
          <el-descriptions-item label="流量 A">{{ trafficA(currentDetail) }}%</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(currentDetail.start_time) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatTime(currentDetail.end_time) }}</el-descriptions-item>
        </el-descriptions>

        <div class="metric-title">分组指标</div>
        <el-empty v-if="metricRows.length === 0" description="暂无结果数据" :image-size="50" />
        <el-table v-else :data="metricRows" size="small" data-test="ab-metric-table">
          <el-table-column prop="metric" label="指标" min-width="160" />
          <el-table-column prop="valueA" label="模型 A" width="130" />
          <el-table-column prop="valueB" label="模型 B" width="130" />
        </el-table>

        <div v-if="report?.significance" class="metric-title">统计显著性</div>
        <el-descriptions v-if="report?.significance" :column="2" border>
          <el-descriptions-item label="p 值">{{ report.significance.p_value ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="是否显著">
            {{ report.significance.is_significant ? '显著' : '不显著' }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="report" class="recommendation" data-test="ab-recommendation">
          <strong>建议：</strong>{{ report.recommendation || '数据不足，暂无推荐' }}
        </div>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { abTestsApi, type LlmAbTest, type LlmAbTestReport } from '@/core/api/governance'

/**
 * A/B 测试（v1.9.5 R5 真实化）：`/routing/ab-tests` 列表/创建/暂停/恢复/完成/删除/报表。
 * 原「版本号/归档」为前端概念，上游只有 running/paused/completed 三态，按真实状态呈现。
 */
const statusFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const experiments = ref<LlmAbTest[]>([])

const dialogOpen = ref(false)
const form = reactive({
  name: '',
  model_a: '',
  model_b: '',
  ratioA: 50,
  description: '',
})

const detailOpen = ref(false)
const detailLoading = ref(false)
const currentDetail = ref<LlmAbTest | null>(null)
const report = ref<LlmAbTestReport | null>(null)
const metricRows = ref<Array<{ metric: string; valueA: string; valueB: string }>>([])

function trafficA(row: LlmAbTest) {
  const value = row.traffic_split?.model_a
  return Math.round(Number(value ?? 0.5) * 100)
}
function statusType(status: string) {
  return { running: 'success', paused: 'warning', completed: 'info' }[status] || 'info'
}
function statusLabel(status: string) {
  return { running: '运行中', paused: '已暂停', completed: '已完成' }[status] || status
}
function formatTime(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}
function formatValue(value: unknown) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(3)
  return String(value)
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    experiments.value = await abTestsApi.list({
      status_filter: statusFilter.value || undefined,
      limit: 200,
    })
  } catch (error) {
    errorMessage.value = `A/B 测试加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

function openCreate() {
  errorMessage.value = ''
  form.name = ''
  form.model_a = ''
  form.model_b = ''
  form.ratioA = 50
  form.description = ''
  dialogOpen.value = true
}

async function save() {
  if (!form.name.trim() || !form.model_a.trim() || !form.model_b.trim()) {
    ElMessage.warning('请填写实验名称与两个模型')
    return
  }
  saving.value = true
  try {
    const ratio = form.ratioA / 100
    await abTestsApi.create({
      name: form.name.trim(),
      model_a: form.model_a.trim(),
      model_b: form.model_b.trim(),
      description: form.description || undefined,
      traffic_split: { model_a: ratio, model_b: Number((1 - ratio).toFixed(2)) },
    })
    ElMessage.success('实验已创建')
    dialogOpen.value = false
    await load()
  } catch (error) {
    errorMessage.value = `实验创建失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    saving.value = false
  }
}

async function pause(row: LlmAbTest) {
  try {
    await abTestsApi.pause(row.id)
    ElMessage.success('实验已暂停')
    await load()
  } catch (error) {
    errorMessage.value = `实验暂停失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function resume(row: LlmAbTest) {
  try {
    await abTestsApi.resume(row.id)
    ElMessage.success('实验已启动')
    await load()
  } catch (error) {
    errorMessage.value = `实验启动失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function complete(row: LlmAbTest) {
  try {
    await abTestsApi.complete(row.id)
    ElMessage.success('实验已完成')
    await load()
  } catch (error) {
    errorMessage.value = `实验完成失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function remove(testId: string) {
  try {
    await abTestsApi.remove(testId)
    ElMessage.success('实验已删除')
    await load()
  } catch (error) {
    errorMessage.value = `实验删除失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function openDetail(row: LlmAbTest) {
  currentDetail.value = row
  detailOpen.value = true
  detailLoading.value = true
  report.value = null
  metricRows.value = []
  try {
    const result = await abTestsApi.report(row.id)
    report.value = result
    const statsA = result.model_a_stats || {}
    const statsB = result.model_b_stats || {}
    const keys = Array.from(new Set([...Object.keys(statsA), ...Object.keys(statsB)]))
    metricRows.value = keys.map((key) => ({
      metric: key,
      valueA: formatValue(statsA[key]),
      valueB: formatValue(statsB[key]),
    }))
  } catch (error) {
    errorMessage.value = `实验报表加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    detailLoading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.traffic-bar { display: flex; align-items: center; gap: 8px; }
.traffic-a { font-size: 12px; color: #1677ff; width: 34px; }
.metric-title { font-weight: 600; margin: 16px 0 8px; }
.recommendation {
  margin-top: 16px;
  padding: 12px;
  border-radius: 4px;
  background: var(--el-fill-color-lighter);
  font-size: 13px;
}
</style>
