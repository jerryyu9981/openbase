<template>
  <PageContainer title="Prompt 实验" description="Prompt 变体实验与报表（OpenLLM Prompt Experiment）" test-id="prompt-experiments-view-page">
    <div class="page-toolbar">
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px" data-test="pe-status-filter" @change="load">
        <el-option label="草稿" value="draft" />
        <el-option label="运行中" value="running" />
        <el-option label="已完成" value="completed" />
      </el-select>
      <el-button type="primary" data-test="pe-new" @click="openCreate">创建实验</el-button>
      <el-button :loading="loading" data-test="pe-refresh" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="pe-error"
      @close="errorMessage = ''"
    />

    <el-card header="Prompt 实验列表" data-test="pe-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="experiments" stripe data-test="pe-table">
          <template #empty>
            <el-empty description="暂无实验" :image-size="60" data-test="pe-empty" />
          </template>
          <el-table-column prop="name" label="实验名称" min-width="170" />
          <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
          <el-table-column label="变体数" width="90">
            <template #default="{ row }">{{ row.variants?.length ?? 0 }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small" data-test="pe-status">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="胜出变体" width="120">
            <template #default="{ row }">{{ row.winner_variant || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'draft'" link type="success" size="small" data-test="pe-start" @click="start(row)">
                启动
              </el-button>
              <el-button v-if="row.status === 'running'" link type="warning" size="small" data-test="pe-complete" @click="complete(row)">
                完成
              </el-button>
              <el-button link type="primary" size="small" data-test="pe-report" @click="openReport(row)">报表</el-button>
              <el-popconfirm title="确认删除该实验？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small" data-test="pe-delete">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="dialogOpen" title="创建 Prompt 实验" width="580px" data-test="pe-dialog">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" data-test="pe-name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="变体集" required>
          <div class="variant-list">
            <div v-for="(variant, idx) in form.variants" :key="idx" class="variant-row">
              <el-input v-model="variant.name" placeholder="变体名称" style="width: 130px" data-test="pe-variant-name" />
              <el-input v-model="variant.content" placeholder="变体内容" style="flex: 1" data-test="pe-variant" />
              <el-button
                link
                type="danger"
                :disabled="form.variants.length <= 2"
                @click="form.variants.splice(idx, 1)"
              >
                删除
              </el-button>
            </div>
            <el-button size="small" data-test="pe-variant-add" @click="form.variants.push({ name: '', content: '' })">
              + 添加变体
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="pe-save" @click="save">创建</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="reportOpen" :title="`实验报表 - ${currentExperiment?.name || ''}`" size="560px" data-test="pe-report-drawer">
      <div v-loading="reportLoading">
        <el-empty v-if="!report" description="暂无报表数据" :image-size="60" />
        <template v-else>
          <el-table :data="reportRows" size="small" data-test="pe-report-table">
            <el-table-column prop="variant" label="变体" min-width="120" />
            <el-table-column prop="samples" label="样本数" width="90" />
            <el-table-column prop="successRate" label="成功率" width="100" />
            <el-table-column prop="avgLatency" label="平均延迟(ms)" width="120" />
          </el-table>
          <div class="recommendation" data-test="pe-recommendation">
            <strong>建议：</strong>{{ report.recommendation || '数据不足，暂无推荐' }}
          </div>
        </template>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  promptExperimentsApi,
  type LlmExperimentReport,
  type LlmPromptExperiment,
} from '@/core/api/governance'

/**
 * Prompt 实验（v1.9.5 R5 真实化）：`/prompt-experiments` 列表/创建/启动/完成/删除/报表。
 * 上游要求至少 2 个变体；报表按变体统计动态列展示，不再使用硬编码成功率/质量分。
 */
const statusFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')

const experiments = ref<LlmPromptExperiment[]>([])

const dialogOpen = ref(false)
const form = reactive({
  name: '',
  description: '',
  variants: [
    { name: '', content: '' },
    { name: '', content: '' },
  ] as Array<{ name: string; content: string }>,
})

const reportOpen = ref(false)
const reportLoading = ref(false)
const currentExperiment = ref<LlmPromptExperiment | null>(null)
const report = ref<LlmExperimentReport | null>(null)

function statusType(status: string) {
  return { draft: 'info', running: 'warning', completed: 'success' }[status] || 'info'
}
function statusLabel(status: string) {
  return { draft: '草稿', running: '运行中', completed: '已完成' }[status] || status
}

const reportRows = ref<Array<{ variant: string; samples: number; successRate: string; avgLatency: string }>>([])

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    experiments.value = await promptExperimentsApi.list({
      status_filter: statusFilter.value || undefined,
      limit: 200,
    })
  } catch (error) {
    errorMessage.value = `Prompt 实验加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

function openCreate() {
  errorMessage.value = ''
  form.name = ''
  form.description = ''
  form.variants = [
    { name: '', content: '' },
    { name: '', content: '' },
  ]
  dialogOpen.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写实验名称')
    return
  }
  const variants = form.variants.filter((item) => item.name.trim() && item.content.trim())
  if (variants.length < 2) {
    ElMessage.warning('至少需要 2 个填写完整的变体')
    return
  }
  saving.value = true
  try {
    await promptExperimentsApi.create({
      name: form.name.trim(),
      description: form.description || undefined,
      variants: variants.map((item) => ({ name: item.name.trim(), content: item.content })),
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

async function start(row: LlmPromptExperiment) {
  try {
    await promptExperimentsApi.start(row.id)
    ElMessage.success('实验已启动')
    await load()
  } catch (error) {
    errorMessage.value = `实验启动失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function complete(row: LlmPromptExperiment) {
  try {
    await promptExperimentsApi.complete(row.id)
    ElMessage.success('实验已完成')
    await load()
  } catch (error) {
    errorMessage.value = `实验完成失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function remove(experimentId: string) {
  try {
    await promptExperimentsApi.remove(experimentId)
    ElMessage.success('实验已删除')
    await load()
  } catch (error) {
    errorMessage.value = `实验删除失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function openReport(row: LlmPromptExperiment) {
  currentExperiment.value = row
  reportOpen.value = true
  reportLoading.value = true
  report.value = null
  reportRows.value = []
  try {
    const result = await promptExperimentsApi.report(row.id)
    report.value = result
    reportRows.value = Object.entries(result.variant_stats || {}).map(([variant, stats]) => {
      const samples = Number(stats.samples ?? stats.count ?? 0)
      const successes = Number(stats.successes ?? stats.success_count ?? 0)
      const rate = samples > 0 ? `${((successes / samples) * 100).toFixed(1)}%` : '-'
      return {
        variant,
        samples,
        successRate: rate,
        avgLatency: String(stats.avg_latency_ms ?? stats.avg_latency ?? '-'),
      }
    })
  } catch (error) {
    errorMessage.value = `实验报表加载失败：${error instanceof Error ? error.message : '未知错误'}`
    reportOpen.value = false
  } finally {
    reportLoading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.variant-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
.recommendation {
  margin-top: 16px;
  padding: 12px;
  border-radius: 4px;
  background: var(--el-fill-color-lighter);
  font-size: 13px;
}
</style>
