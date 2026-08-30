<template>
  <div class="gateway-aggregate">
    <div class="page-toolbar">
      <el-button type="primary" :loading="executing" data-test="agg-execute" @click="execute">执行聚合</el-button>
      <el-button data-test="agg-reset" @click="reset">重置</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="agg-error"
      @close="errorMessage = ''"
    />

    <el-row :gutter="16">
      <!-- 步骤配置 -->
      <el-col :span="14">
        <el-card header="聚合步骤配置（阶段一代码式）" data-test="agg-steps-card">
          <div v-for="(step, idx) in steps" :key="idx" class="step-row">
            <el-input v-model="step.id" placeholder="步骤 ID" style="width: 110px" data-test="agg-step-id" />
            <el-select v-model="step.system" style="width: 130px" data-test="agg-step-system">
              <el-option v-for="s in ['openllm', 'openrag', 'openmemory', 'dps']" :key="s" :label="s" :value="s" />
            </el-select>
            <el-input v-model="step.path" placeholder="/path" style="width: 150px" data-test="agg-step-path" />
            <el-select v-model="step.method" style="width: 100px">
              <el-option v-for="m in ['GET', 'POST']" :key="m" :label="m" :value="m" />
            </el-select>
            <el-button link type="danger" :disabled="steps.length <= 1" data-test="agg-step-remove" @click="steps.splice(idx, 1)">删除</el-button>
          </div>
          <el-button size="small" data-test="agg-step-add" @click="addStep">+ 添加步骤</el-button>

          <el-divider />
          <el-form label-width="120px">
            <el-form-item label="整体超时(ms)">
              <el-input-number v-model="timeoutMs" :min="500" :max="30000" :step="500" data-test="agg-timeout" />
            </el-form-item>
            <el-form-item label="部分失败策略">
              <el-select v-model="onPartialFailure" data-test="agg-failure-policy">
                <el-option label="return_errors（推荐）" value="return_errors" />
                <el-option label="strict" value="strict" />
                <el-option label="best_effort" value="best_effort" />
              </el-select>
            </el-form-item>
            <el-form-item label="结果映射">
              <div class="mapping-list">
                <div v-for="(item, idx) in mappingItems" :key="idx" class="mapping-row">
                  <el-input v-model="item.target" placeholder="目标字段" style="width: 150px" />
                  <span class="mapping-arrow">→</span>
                  <el-input v-model="item.expr" placeholder="${stepId.data.field}" style="width: 220px" data-test="agg-mapping-expr" />
                  <el-button link type="danger" :disabled="mappingItems.length <= 1" @click="mappingItems.splice(idx, 1)">删除</el-button>
                </div>
                <el-button size="small" data-test="agg-mapping-add" @click="mappingItems.push({ target: '', expr: '' })">+ 添加映射</el-button>
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 结果展示 -->
      <el-col :span="10">
        <el-card header="聚合结果" data-test="agg-result-card">
          <div v-loading="executing">
            <el-empty v-if="!result && errors.length === 0" description="配置步骤后点击执行" :image-size="80" />
            <template v-if="result">
              <pre class="result-json" data-test="agg-result">{{ JSON.stringify(result, null, 2) }}</pre>
            </template>
            <el-alert
              v-if="errors.length"
              :title="`部分步骤失败（${errors.length}）`"
              type="warning"
              show-icon
              class="mb-8"
              data-test="agg-errors"
            >
              <ul>
                <li v-for="(err, idx) in errors" :key="idx">{{ err }}</li>
              </ul>
            </el-alert>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { gatewayApi, type AggregateStep } from '@/core/api/gateway'

const steps = ref<AggregateStep[]>([
  { id: 'models', system: 'openllm', path: '/models', method: 'GET', timeout_ms: 2000 },
  { id: 'kbs', system: 'openrag', path: '/kb/list', method: 'GET', timeout_ms: 2000 },
])
const timeoutMs = ref(5000)
const onPartialFailure = ref<'return_errors' | 'strict' | 'best_effort'>('return_errors')
const mappingItems = ref([
  { target: 'model_total', expr: '${models.data.total}' },
  { target: 'kb_total', expr: '${kbs.data.total}' },
])
const executing = ref(false)
const errorMessage = ref('')
const result = ref<Record<string, unknown> | null>(null)
const errors = ref<string[]>([])

function addStep() {
  steps.value.push({ id: `step${steps.value.length + 1}`, system: 'openllm', path: '/', method: 'GET', timeout_ms: 2000 })
}

function reset() {
  result.value = null
  errors.value = []
  errorMessage.value = ''
}

async function execute() {
  executing.value = true
  errorMessage.value = ''
  result.value = null
  errors.value = []
  try {
    const mapping: Record<string, string> = {}
    for (const item of mappingItems.value) {
      if (item.target && item.expr) mapping[item.target] = item.expr
    }
    const output = await gatewayApi.aggregate({
      steps: steps.value,
      timeout_ms: timeoutMs.value,
      on_partial_failure: onPartialFailure.value,
      mapping,
    })
    result.value = output.result
    errors.value = output.errors
  } catch (error) {
    errorMessage.value = (error as Error).message || '聚合执行失败'
  } finally {
    executing.value = false
  }
}
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mb-8 { margin-bottom: 8px; }
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.step-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.mapping-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.mapping-arrow { color: #909399; }
.result-json { background: #f6f8fa; border-radius: 8px; padding: 12px; font-size: 12px; max-height: 360px; overflow: auto; }
</style>
