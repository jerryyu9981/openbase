<template>
  <div class="test-records-page">
    <!-- 工具栏：run 选择 + 开轮 -->
    <div class="page-toolbar">
      <el-input
        v-model="runIdInput"
        placeholder="测试轮次 run_id，如 run-20260914-0230"
        clearable
        style="width: 300px"
        data-test="testrun-input"
        @keyup.enter="loadSummary"
      />
      <el-button type="primary" :loading="loading" data-test="testrun-load" @click="loadSummary">加载</el-button>
      <el-button data-test="testrun-create" @click="openCreateRun">开新一轮</el-button>
      <span class="mode-hint" data-test="testrun-mode-hint">
        {{ testModeOn ? '测试模式：请求已注入 X-Test-Case-Id' : '测试模式关闭（开启后请求自动携带测试头）' }}
      </span>
    </div>

    <!-- 汇总卡片 -->
    <el-card v-if="summary" class="mt-8" header="汇总" data-test="testrun-summary-card">
      <el-row :gutter="16">
        <el-col :span="5">
          <div class="stat-item">
            <div class="stat-label">轮次</div>
            <div class="stat-value">{{ summary.run_id }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-label">总步骤</div>
            <div class="stat-value">{{ summary.total }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-label">通过</div>
            <div class="stat-value pass">{{ summary.pass }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-label">失败</div>
            <div class="stat-value fail">{{ summary.fail }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-label">阻塞/跳过</div>
            <div class="stat-value">{{ summary.blocked + summary.skipped }}</div>
          </div>
        </el-col>
        <el-col :span="3">
          <div class="stat-item">
            <div class="stat-label">结论</div>
            <el-tag :type="summary.passed ? 'success' : 'warning'" size="small" data-test="testrun-passed">
              {{ summary.passed ? '全通过' : '未全通过' }}
            </el-tag>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 用例步骤表 -->
    <el-card v-if="summary" class="mt-16" :header="`用例步骤（${summary.run_id}）`" data-test="testrun-card">
      <div class="ob-table-scroll">
        <el-table :data="flatCases" stripe empty-text="暂无用例记录" data-test="testrun-table">
          <el-table-column prop="case_id" label="用例编号" width="160" />
          <el-table-column prop="step_id" label="步骤" width="70" />
          <el-table-column label="结果" width="90">
            <template #default="{ row }">
              <el-tag :type="resultTag(row.result)" size="small">{{ resultText(row.result) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="140" show-overflow-tooltip />
          <el-table-column label="失败/阻塞理由" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="row.result !== 'PASS' && row.result !== 'SKIPPED' ? 'reason-text' : ''">{{ row.reason || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="request_id" label="请求 ID" width="170" show-overflow-tooltip />
          <el-table-column label="操作" width="170" fixed="right">
            <template #default="{ row }">
              <el-button link type="success" size="small" data-test="testrun-pass" :disabled="judgingId === row.id" @click="judge(row, 'PASS')">通过</el-button>
              <el-button link type="danger" size="small" data-test="testrun-fail" :disabled="judgingId === row.id" @click="judge(row, 'FAIL')">失败</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- FAIL/BLOCKED 理由录入 -->
    <el-dialog v-model="judgeOpen" :title="`判定：${judging?.case_id} 步骤 ${judging?.step_id ?? ''}`" width="460px" data-test="judge-dialog">
      <el-form label-width="80px">
        <el-form-item :label="judgingResult === 'FAIL' ? '失败原因' : '阻塞原因'">
          <el-input v-model="judgeReason" type="textarea" :rows="3" placeholder="必填：说明判定依据或失败现象" data-test="judge-reason" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="judgeOpen = false">取消</el-button>
        <el-button type="primary" :loading="submitting" data-test="judge-submit" @click="submitJudge">提交判定</el-button>
      </template>
    </el-dialog>

    <!-- 开轮 -->
    <el-dialog v-model="createRunOpen" title="开新一轮人工测试" width="460px" data-test="create-run-dialog">
      <el-form label-width="80px">
        <el-form-item label="轮次号">
          <el-input v-model="createRunId" placeholder="留空自动生成 run-YYYYMMDD-HHMM" data-test="create-run-id" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="createRunTitle" placeholder="如 S0 冒烟" data-test="create-run-title" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createRunOpen = false">取消</el-button>
        <el-button type="primary" :loading="submitting" data-test="create-run-submit" @click="submitCreateRun">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { testingApi, resultTagType, resultLabel, type CaseSummary, type TestResult } from '@/core/api/testing'
import { TEST_MODE_KEY } from '@/core/api/http'

const runIdInput = ref('')
const loading = ref(false)
const submitting = ref(false)
const summary = ref<{ run_id: string; total: number; pass: number; fail: number; blocked: number; skipped: number; passed: boolean; cases: CaseSummary[] } | null>(null)

interface FlatRow {
  id: number
  case_id: string
  step_id: number | string | null
  result: TestResult
  title: string
  reason: string
  request_id: string
}

const flatCases = computed<FlatRow[]>(() => {
  if (!summary.value) return []
  const rows: FlatRow[] = []
  for (const caseItem of summary.value.cases) {
    for (const step of caseItem.steps) {
      rows.push({
        id: step.id,
        case_id: caseItem.case_id,
        step_id: step.step_id,
        result: step.result,
        title: step.title ?? '',
        reason: step.reason ?? '',
        request_id: step.request_id ?? '',
      })
    }
  }
  return rows
})

const testModeOn = computed(() => localStorage.getItem(TEST_MODE_KEY) === '1')

function resultTag(result: TestResult): 'success' | 'danger' | 'warning' | 'info' {
  return resultTagType(result)
}
function resultText(result: TestResult): string {
  return resultLabel(result)
}

async function loadSummary(): Promise<void> {
  const runId = runIdInput.value.trim()
  if (!runId) {
    ElMessage.warning('请输入测试轮次 run_id')
    return
  }
  loading.value = true
  try {
    const res = await testingApi.runSummary(runId)
    summary.value = res.data
  } catch {
    summary.value = null
  } finally {
    loading.value = false
  }
}

const judgeOpen = ref(false)
const judging = ref<FlatRow | null>(null)
const judgingResult = ref<TestResult>('FAIL')
const judgeReason = ref('')
const judgingId = ref<number | null>(null)

function judge(row: FlatRow, result: TestResult): void {
  judging.value = row
  judgingResult.value = result
  judgeReason.value = ''
  if (result === 'PASS') {
    judgeOpen.value = false
    void submitDirect(row, 'PASS')
    return
  }
  judgeOpen.value = true
}

async function submitDirect(row: FlatRow, result: TestResult): Promise<void> {
  judgingId.value = row.id
  try {
    await testingApi.updateRecord(row.id, { result })
    ElMessage.success('已标记通过')
    await loadSummary()
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    judgingId.value = null
  }
}

async function submitJudge(): Promise<void> {
  if (!judging.value || !judgeReason.value.trim()) {
    ElMessage.warning('失败/阻塞必须填写理由')
    return
  }
  submitting.value = true
  try {
    await testingApi.updateRecord(judging.value.id, { result: judgingResult.value, reason: judgeReason.value.trim() })
    ElMessage.success('判定已提交')
    judgeOpen.value = false
    await loadSummary()
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    submitting.value = false
    judgingId.value = null
  }
}

const createRunOpen = ref(false)
const createRunId = ref('')
const createRunTitle = ref('')

function openCreateRun(): void {
  createRunId.value = ''
  createRunTitle.value = ''
  createRunOpen.value = true
}

async function submitCreateRun(): Promise<void> {
  submitting.value = true
  try {
    const body: { run_id?: string; title?: string } = {}
    if (createRunId.value.trim()) body.run_id = createRunId.value.trim()
    if (createRunTitle.value.trim()) body.title = createRunTitle.value.trim()
    const res = await testingApi.createRun(body)
    ElMessage.success(`已开新一轮：${res.data.run_id}`)
    createRunOpen.value = false
    runIdInput.value = res.data.run_id
    await loadSummary()
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mode-hint {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.stat-value {
  font-size: 22px;
  font-weight: 600;
}
.stat-value.pass {
  color: var(--el-color-success);
}
.stat-value.fail {
  color: var(--el-color-danger);
}
.stat-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-bottom: 4px;
}
.reason-text {
  color: var(--el-color-danger);
}
.mt-8 {
  margin-top: 8px;
}
.mt-16 {
  margin-top: 16px;
}
</style>