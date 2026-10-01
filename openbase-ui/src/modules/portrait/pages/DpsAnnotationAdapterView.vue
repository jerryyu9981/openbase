<template>
  <div class="dps-adapter">
    <!-- 状态一 · 能力未启用（信息态，非报错；零写入） -->
    <el-card v-if="capabilityDisabled" data-test="adapter-disabled">
      <el-empty description="该能力当前未启用">
        <template #default>
          <div class="disabled-desc">
            请联系管理员开启 AI 标注通道。<strong>未启用状态下本页不会发起任何写请求</strong>（零写入约束），亦不呈现为错误。
          </div>
        </template>
      </el-empty>
      <div class="muted sm">对应后端 403（AI 通道未启用），呈现为信息态而非报错态。</div>
    </el-card>

    <template v-else>
      <div class="page-toolbar">
        <el-input v-model="adapterId" placeholder="adapter_id（如 stub-v1）" style="width: 200px" data-test="adapter-id" />
        <el-input v-model="annotationTemplate" placeholder="标注模板 code" style="width: 200px" data-test="adapter-template" />
        <el-input v-model="text" placeholder="待标注文本" style="width: 300px" data-test="adapter-text" />
        <el-button type="primary" :loading="generating" data-test="adapter-generate" @click="generate">生成 AI 候选</el-button>
      </div>

      <el-alert v-if="adapterUnavailable" type="warning" show-icon :closable="false" class="mb-16" data-test="adapter-unavailable">
        <template #title>AI 适配器暂不可用</template>
        <div>人工路径不受影响，可继续使用人工标注与复核提交。</div>
      </el-alert>

      <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
        <template #title>{{ error.title }}</template>
        <div>{{ error.detail }}</div>
        <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
        <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
      </el-alert>

      <el-card header="候选列表（逐条 通过 / 驳回）" class="mb-16">
        <div class="ob-table-scroll">
          <el-table :data="candidates" stripe empty-text="暂无候选" data-test="adapter-table">
            <el-table-column prop="id" label="候选 ID" width="140" />
            <el-table-column prop="review_status" label="复核状态" width="140">
              <template #default="{ row }">
                <el-tag :type="row.review_status === 'pending' ? 'warning' : row.review_status === 'rejected' ? 'danger' : 'success'" size="small">
                  {{ row.review_status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="来源" min-width="200">
              <template #default="{ row }">
                <el-tag size="small">{{ row.source }}</el-tag>
                <span class="muted sm">{{ row.adapter_id }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="320" fixed="right">
              <template #default="{ row }">
                <el-button size="small" :loading="assistingId === row.id" data-test="adapter-assist" @click="assist(row.id)">复核辅助（LLM）</el-button>
                <el-button link type="primary" size="small" data-test="adapter-approve" @click="review(row.id, 'approved')">通过</el-button>
                <el-button link type="danger" size="small" data-test="adapter-reject" @click="review(row.id, 'rejected')">驳回</el-button>
              </template>
            </el-table-column>
            <template #empty>
              <el-empty description="暂无候选" :image-size="60" data-test="adapter-empty" />
            </template>
          </el-table>
        </div>
        <div v-if="assistSuggestion" class="assist" data-test="adapter-assist-result">
          <strong>LLM 复核建议（来源：OpenLLM 通道，仅供参考）：</strong>
          <div>{{ assistSuggestion }}</div>
        </div>
      </el-card>

      <el-alert type="warning" show-icon :closable="false" class="mb-16" data-test="adapter-gate">
        <template #title>提交前置检查</template>
        <div>存在未复核候选时<strong>阻止提交</strong>并提示；后端 409 兜底：未复核候选不得进入标签/画像路径。</div>
      </el-alert>

      <div class="page-toolbar">
        <el-button type="primary" data-test="adapter-submit" @click="submitAll">提交复核结果</el-button>
        <span class="muted sm">（{{ pendingCount }} 条未复核）</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsReviewSubmitRequest } from '@/core/api/dps'
import { describeDpsError, type DpsErrorPresentation } from '@/core/api/error'

interface Candidate { id: string; review_status: string; source: string; adapter_id?: string }

const adapterId = ref('stub-v1')
const annotationTemplate = ref('')
const text = ref('')
const generating = ref(false)
const assistingId = ref('')
const candidates = ref<Candidate[]>([])
const assistSuggestion = ref('')
const capabilityDisabled = ref(false)
const adapterUnavailable = ref(false)
const error = ref<DpsErrorPresentation | null>(null)

const pendingCount = computed(() => candidates.value.filter((item) => item.review_status === 'pending').length)

async function generate() {
  if (!text.value || !annotationTemplate.value) {
    ElMessage.warning('请填写标注模板与待标注文本')
    return
  }
  generating.value = true
  error.value = null
  adapterUnavailable.value = false
  try {
    const result = await dpsApi.generateAnnotationCandidates(adapterId.value, {
      text: text.value,
      annotation_template: annotationTemplate.value,
    })
    const annotation = result.annotation || {}
    candidates.value = [
      {
        id: String(annotation.id || `cand-${candidates.value.length + 1}`),
        review_status: String(annotation.review_status || 'pending'),
        source: String(result.source || 'ai_annotation'),
        adapter_id: result.adapter_id,
      },
      ...candidates.value,
    ]
    ElMessage.success('候选已生成')
  } catch (caught) {
    const presentation = describeDpsError(caught)
    if (presentation.kind === 'forbidden') capabilityDisabled.value = true
    else if (caught && (caught as { response?: { status?: number } }).response?.status === 503) adapterUnavailable.value = true
    else error.value = presentation
  } finally {
    generating.value = false
  }
}

async function assist(candidateId: string) {
  assistingId.value = candidateId
  assistSuggestion.value = ''
  try {
    const result = await dpsApi.assistReview({
      messages: [{ role: 'user', content: `请复核候选 ${candidateId} 的标注建议` }],
    })
    assistSuggestion.value = result.choices?.[0]?.message?.content || '（无返回内容）'
  } catch {
    assistSuggestion.value = '复核辅助暂不可用，复核提交仍可进行。'
  } finally {
    assistingId.value = ''
  }
}

async function review(candidateId: string, reviewStatus: 'approved' | 'rejected') {
  const body: DpsReviewSubmitRequest = { review_status: reviewStatus }
  try {
    await dpsApi.submitReview(candidateId, body)
    candidates.value = candidates.value.map((item) =>
      item.id === candidateId ? { ...item, review_status: reviewStatus } : item,
    )
    ElMessage.success(reviewStatus === 'approved' ? '已通过' : '已驳回')
  } catch (caught) {
    error.value = describeDpsError(caught)
  }
}

async function submitAll() {
  if (pendingCount.value > 0) {
    ElMessage.warning('存在未复核候选，不得进入标签/画像路径')
    return
  }
  ElMessage.success('复核结果已提交')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.mb-16 { margin-bottom: 16px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; margin-left: 6px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.assist { margin-top: 12px; border-top: 1px solid var(--ob-border); padding-top: 12px; color: var(--ob-text-secondary); }
.disabled-desc { color: var(--ob-text-secondary); font-size: 13px; margin: 8px 0; }
</style>
