<template>
  <PageContainer title="画像详情" description="单主体画像 360 视图与标签明细" test-id="portrait-detail-page">
    <el-page-header content="画像详情" class="mb-16" @back="$router.push('/portrait/list')" />

    <el-result
      v-if="isForbidden"
      icon="error"
      :title="presentation?.title || ''"
      :sub-title="presentation?.detail || ''"
      data-test="isolation-forbidden"
    >
      <template #extra>
        <p v-if="presentation?.requestId" class="request-id" data-test="error-request-id">
          请求编号：{{ presentation.requestId }}
        </p>
        <el-button data-test="isolation-back" @click="$router.push('/portrait/list')">返回列表</el-button>
      </template>
    </el-result>

    <div v-else-if="isNotFound" data-test="isolation-not-found">
      <el-empty description="资源不存在或已被移除">
        <el-button data-test="isolation-back" @click="$router.push('/portrait/list')">返回列表</el-button>
      </el-empty>
    </div>

    <template v-else>
      <el-alert
        v-if="showErrorBar"
        :title="errorMessage"
        type="error"
        show-icon
        closable
        class="mb-16"
        data-test="isolation-error-bar"
        @close="presentation = null"
      >
        <template #default>
          <div v-if="presentation?.detail" class="error-detail">{{ presentation.detail }}</div>
          <el-button link type="primary" size="small" data-test="isolation-retry" @click="loadData">点击重试</el-button>
        </template>
      </el-alert>

      <div v-loading="loading">
        <!-- 口径与操作 -->
        <el-card shadow="never" class="mb-16">
          <div class="toolbar">
            <span class="toolbar-label">计算口径</span>
            <el-select
              v-model="selectedTemplate"
              placeholder="默认口径（六维基础分）"
              clearable
              :disabled="recalcRunning"
              style="width: 300px"
              data-test="portrait-template-select"
              @change="onTemplateChange"
            >
              <el-option label="默认口径（六维基础分）" value="" />
              <el-option
                v-for="item in templateOptions"
                :key="item.code"
                :label="`${item.name || item.code}（${item.code}）`"
                :value="item.code"
              />
            </el-select>
            <el-tag v-if="templateVersion" size="small" type="info">{{ selectedTemplate }} · v{{ templateVersion }}</el-tag>
            <el-button
              size="small"
              link
              type="primary"
              :disabled="!selectedTemplate"
              data-test="portrait-scoring-items"
              @click="openScoringItems"
            >
              查看评分项
            </el-button>
            <div class="toolbar-actions">
              <el-tooltip
                content="按当前「计算口径」重新计算并回写画像；完成后在下方卡片展示本次结果"
                placement="bottom"
              >
                <el-button
                  size="small"
                  type="primary"
                  plain
                  :loading="recalcRunning"
                  data-test="portrait-recalc"
                  @click="recalculate"
                >
                  重算
                </el-button>
              </el-tooltip>
              <el-button size="small" :loading="loading" data-test="portrait-refresh" @click="loadData">刷新</el-button>
              <el-button link type="primary" data-test="portrait-edit-open" @click="openEdit">编辑属性</el-button>
              <el-button link type="danger" data-test="portrait-delete-open" @click="removePortrait">删除画像</el-button>
            </div>
          </div>
          <el-alert
            v-if="templateMissing"
            type="info"
            show-icon
            :closable="false"
            class="mt-12"
            data-test="portrait-template-missing"
          >
            <template #title>该画像尚无模板「{{ selectedTemplate }}」的计算结果</template>
            <div>请点击上方「重算」以该模板计算，或切回默认口径查看六维基础分。</div>
          </el-alert>
        </el-card>

        <!-- 重算结果：对接任务查询接口 GET /portraits/tasks/{task_id} -->
        <el-card
          v-if="recalcVisible"
          ref="recalcCardRef"
          shadow="never"
          class="mb-16"
          data-test="portrait-recalc-result"
        >
          <template #header>
            <div class="card-head">
              <span>重算结果</span>
              <div class="card-head-actions" aria-live="polite">
                <el-tag size="small" :type="recalcStatusType" data-test="portrait-recalc-status">
                  {{ recalcStatusLabel }}
                </el-tag>
                <span v-if="recalcRunning" class="muted sm">已等待 {{ recalcElapsed }}s</span>
                <el-button link size="small" data-test="portrait-recalc-dismiss" @click="recalcVisible = false">
                  收起
                </el-button>
              </div>
            </div>
          </template>

          <div v-if="recalcRunning" class="recalc-progress" data-test="portrait-recalc-progress">
            <el-progress
              :percentage="100"
              :indeterminate="true"
              :duration="1.2"
              :show-text="false"
              :stroke-width="6"
            />
            <div class="muted sm mt-8">
              {{
                recalcTaskId
                  ? `任务 ${recalcTaskId} 已提交，正在计算…`
                  : '正在提交重算任务…'
              }}
              完成后本卡片自动展示结果，并刷新下方画像数据。
            </div>
          </div>

          <el-alert
            v-if="recalcError"
            type="error"
            show-icon
            :closable="false"
            :title="recalcError"
            class="mb-12"
            data-test="portrait-recalc-error"
          >
            <el-button link type="primary" size="small" data-test="portrait-recalc-retry" @click="recalculate">
              重试
            </el-button>
          </el-alert>

          <el-descriptions v-if="recalcResult" :column="2" border size="small">
            <el-descriptions-item label="任务 ID">
              <span data-test="portrait-recalc-task-id">{{ recalcTaskId || '同步计算（无任务 ID）' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="计算口径">{{ recalcTemplateLabel }}</el-descriptions-item>
            <el-descriptions-item label="完成时间">{{ formatTime(recalcFinishedAt) }}</el-descriptions-item>
            <el-descriptions-item label="计算耗时">{{ recalcDurationText }}</el-descriptions-item>
            <el-descriptions-item label="综合评分">
              <strong data-test="portrait-recalc-overall">
                {{ recalcOverall === null ? '—' : recalcOverall.toFixed(1) }}
              </strong>
              <span
                v-if="recalcOverallDelta !== null"
                class="delta"
                :class="recalcOverallDelta >= 0 ? 'delta-up' : 'delta-down'"
                data-test="portrait-recalc-delta"
              >
                {{ recalcOverallDelta >= 0 ? '+' : '' }}{{ recalcOverallDelta.toFixed(1) }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="数据完整度">
              {{ recalcCompleteness === null ? '—' : `${Math.round(recalcCompleteness * 100)}%` }}
            </el-descriptions-item>
            <el-descriptions-item label="存储落点">{{ recalcStorage }}</el-descriptions-item>
          </el-descriptions>

          <el-table
            v-if="recalcDimensions.length"
            :data="recalcDimensions"
            size="small"
            class="mt-12"
            data-test="portrait-recalc-dimensions"
          >
            <el-table-column prop="label" label="维度" min-width="120" />
            <el-table-column label="得分" width="100">
              <template #default="{ row }">{{ row.score === null ? '未采集' : row.score.toFixed(1) }}</template>
            </el-table-column>
            <el-table-column label="变化" width="90">
              <template #default="{ row }">
                <span
                  v-if="row.delta !== null"
                  class="delta"
                  :class="row.delta >= 0 ? 'delta-up' : 'delta-down'"
                >
                  {{ row.delta >= 0 ? '+' : '' }}{{ row.delta.toFixed(1) }}
                </span>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
            <el-table-column label="置信度" width="100">
              <template #default="{ row }">{{ row.confidence === null ? '—' : row.confidence.toFixed(2) }}</template>
            </el-table-column>
          </el-table>

          <div v-if="recalcResult" class="muted sm mt-8">
            本次重算已回写画像数据，页面已自动刷新；维度得分与标签以当前展示为准。
          </div>
        </el-card>

        <el-row :gutter="16">
          <!-- 身份卡 + 分数 -->
          <el-col :xs="24" :lg="14">
            <el-card class="mb-16" data-test="portrait-identity">
              <template #header>
                <div class="card-head">
                  <span>身份与状态</span>
                  <el-tag v-if="isStale" size="small" type="warning">数据可能过期</el-tag>
                </div>
              </template>
              <el-descriptions v-if="profile" :column="2" border>
                <el-descriptions-item label="画像名称">{{ profile.name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="画像 ID">{{ profile.person_id || personId || '-' }}</el-descriptions-item>
                <el-descriptions-item label="风险等级">
                  <el-tag :type="riskType(profile)" size="small">{{ riskLabel(profile) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="画像版本">{{ profile.version ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="更新时间">{{ formatTime(profile.updated_at) }}</el-descriptions-item>
                <el-descriptions-item label="计算时刻">{{ formatTime(resultCalculatedAt) }}</el-descriptions-item>
                <el-descriptions-item label="综合评分">
                  <strong data-test="portrait-overall">{{ overallScore === null ? '—' : overallScore.toFixed(1) }}</strong>
                </el-descriptions-item>
                <el-descriptions-item label="数据完整度">
                  <span v-if="completeness !== null" data-test="portrait-completeness">
                    {{ Math.round(completeness * 100) }}%
                    <el-tag v-if="completeness < 0.8" size="small" type="warning">偏低，结果为部分完成</el-tag>
                  </span>
                  <span v-else class="muted">—</span>
                </el-descriptions-item>
              </el-descriptions>
              <el-empty v-else-if="!loading" description="当前租户暂无数据（如为权限问题请联系管理员）" :image-size="50" />
            </el-card>

            <el-card class="mb-16" data-test="portrait-dimensions">
              <template #header>
                <div class="card-head">
                  <span>维度得分</span>
                  <span class="muted sm">点击任一维度查看证据</span>
                </div>
              </template>

              <el-empty
                v-if="!loading && !dimensionScores.length"
                description="暂无维度数据，请先计算画像"
                :image-size="50"
              >
                <el-button size="small" type="primary" plain :loading="recalcRunning" @click="recalculate">立即重算</el-button>
              </el-empty>

              <div v-else class="dimension-layout">
                <div v-if="radar" class="radar-wrap">
                  <svg :width="radar.size" :height="radar.size" role="img" aria-label="维度雷达图">
                    <polygon
                      v-for="(ring, index) in radar.rings"
                      :key="`ring-${index}`"
                      :points="ring"
                      fill="none"
                      stroke="#e5e7eb"
                      stroke-width="1"
                    />
                    <line
                      v-for="(point, index) in radar.axes"
                      :key="`axis-${index}`"
                      :x1="radar.center"
                      :y1="radar.center"
                      :x2="point.x"
                      :y2="point.y"
                      stroke="#e5e7eb"
                      stroke-width="1"
                    />
                    <polygon :points="radar.polygon" fill="rgba(59,130,246,0.22)" stroke="#3b82f6" stroke-width="2" />
                    <circle
                      v-for="(point, index) in radar.points"
                      :key="`dot-${index}`"
                      :cx="point.x"
                      :cy="point.y"
                      r="3"
                      fill="#3b82f6"
                    />
                    <text
                      v-for="(point, index) in radar.labels"
                      :key="`label-${index}`"
                      :x="point.x"
                      :y="point.y"
                      text-anchor="middle"
                      dominant-baseline="middle"
                      font-size="11"
                      fill="#6b7280"
                    >
                      {{ point.text }}
                    </text>
                  </svg>
                </div>

                <div class="dimension-list">
                  <div
                    v-for="item in dimensionScores"
                    :key="item.code"
                    class="dimension-row"
                    data-test="portrait-dimension-row"
                    @click="openEvidence(item)"
                  >
                    <div class="dimension-row-head">
                      <span class="dimension-name">{{ item.label }}</span>
                      <span class="dimension-score" :class="{ missing: item.score === null }">
                        {{ item.score === null ? '未采集' : item.score.toFixed(1) }}
                      </span>
                    </div>
                    <el-progress
                      :percentage="item.score === null ? 0 : Math.min(100, Math.round(item.score))"
                      :stroke-width="8"
                      :status="item.score === null ? 'warning' : undefined"
                      :show-text="false"
                    />
                    <div class="dimension-meta">
                      <span class="muted sm">置信度 {{ item.confidence === null ? '—' : item.confidence.toFixed(2) }}</span>
                      <span v-if="item.score === null" class="muted sm">缺值按 50 分计入总分</span>
                    </div>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>

          <!-- 标签 -->
          <el-col :xs="24" :lg="10">
            <el-card class="mb-16" data-test="portrait-tags">
              <template #header>
                <div class="card-head">
                  <span>标签（按维度分组）</span>
                  <span class="muted sm">共 {{ tagItems.length }} 个</span>
                </div>
              </template>
              <el-empty v-if="!tagItems.length" description="暂无标签" :image-size="50" />
              <div v-for="group in tagGroups" :key="group.dimension" class="tag-group">
                <div class="tag-group-head">
                  <span class="tag-group-title">{{ group.label }}</span>
                  <span class="muted sm">{{ group.items.length }}</span>
                </div>
                <div class="tags">
                  <el-tag
                    v-for="tag in group.items"
                    :key="`${tag.code}-${tag.name}`"
                    class="tag-item"
                    type="info"
                    size="small"
                  >
                    {{ tag.name }}<span v-if="tag.score !== null" class="tag-score">{{ tag.score }}</span>
                  </el-tag>
                </div>
              </div>
            </el-card>

            <el-card shadow="never" header="口径说明" class="mb-16">
              <ul class="notes">
                <li>默认口径展示画像主表的六维基础分（`basic/behavioral/...`）。</li>
                <li>选择具体模板后展示该模板命名空间内的计算结果与置信度。</li>
                <li>缺值按 50 分计入总分；`when` 条件不成立的规则会被跳过。</li>
              </ul>
            </el-card>
          </el-col>
        </el-row>

        <el-drawer v-model="evidenceVisible" :title="`证据 · ${evidenceTitle}`" size="520px" data-test="portrait-evidence-drawer">
          <el-empty v-if="!evidenceRows.length" description="该维度暂无标签证据（可能尚未计算或证据策略未保留）" :image-size="60" />
          <el-table v-else :data="evidenceRows" size="small" data-test="portrait-evidence-table">
            <el-table-column prop="name" label="标签" min-width="160" show-overflow-tooltip />
            <el-table-column prop="code" label="标签键" min-width="150" show-overflow-tooltip />
            <el-table-column label="得分" width="90">
              <template #default="{ row }">{{ row.score === null ? '—' : row.score }}</template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="110" />
          </el-table>
          <template #footer>
            <span class="muted sm">证据来源于标签联动与计算时的维度标签快照；无证据时请检查模板证据策略。</span>
          </template>
        </el-drawer>

        <el-drawer v-model="editVisible" title="编辑画像属性" size="480px" data-test="portrait-edit-drawer">
          <el-alert
            title="增量更新（PATCH）：对象递归合并、数组去重追加、标量覆盖、null 删除键"
            type="info"
            show-icon
            :closable="false"
            class="mb-16"
          />
          <el-input
            v-model="editText"
            type="textarea"
            :rows="16"
            spellcheck="false"
            data-test="portrait-edit-json"
          />
          <template #footer>
            <el-button @click="editVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" data-test="portrait-edit-save" @click="saveEdit">保存</el-button>
          </template>
        </el-drawer>

        <el-dialog
          v-model="scoringVisible"
          title="本模板实际评分项"
          width="880px"
          data-test="portrait-scoring-dialog"
        >
          <div v-loading="scoringLoading">
            <el-alert
              v-if="scoringError"
              type="error"
              show-icon
              :closable="false"
              :title="scoringError"
              class="mb-12"
            />
            <div v-if="scoringItems" class="muted sm mb-12">
              共 {{ scoringItems.dimension_count }} 个维度 / {{ scoringItems.rule_count }} 条规则；
              继承自 {{ scoringItems.extends || '独立模板' }}。缺值按 50 分计，维度分按规则权重加权，
              综合分按维度权重归一化。
            </div>
            <div v-if="scoringItems" class="scoring-dims">
              <div v-for="dim in scoringItems.dimensions" :key="dim.code" class="scoring-dim">
                <div class="scoring-dim-head">
                  <strong>{{ dim.name }}</strong>
                  <el-tag size="small" type="info">{{ dim.code }}</el-tag>
                  <span class="muted sm">维度权重 {{ Math.round(dim.weight * 1000) / 10 }}%</span>
                </div>
                <el-table :data="dim.rules" size="small">
                  <el-table-column prop="key" label="规则 key" min-width="180" />
                  <el-table-column prop="tag_key" label="标签 key" width="150" />
                  <el-table-column prop="type" label="打分类型" width="130" />
                  <el-table-column label="权重" width="80">
                    <template #default="{ row }">{{ Math.round(row.weight * 100) }}%</template>
                  </el-table-column>
                  <el-table-column prop="description" label="说明" min-width="180" />
                </el-table>
              </div>
            </div>
          </div>
          <template #footer>
            <el-button @click="scoringVisible = false">关闭</el-button>
          </template>
        </el-dialog>
      </div>
    </template>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  dpsApi,
  type DpsPortrait,
  type DpsPortraitCalcTask,
  type DpsPortraitTemplate,
  type DpsTemplateScoringItems,
} from '@/core/api/dps'
import { describeError, type ErrorPresentation } from '@/core/api/error'

interface DimensionScore {
  code: string
  label: string
  score: number | null
  confidence: number | null
}

/** 重算维度行：在维度分基础上附带较上次的变化值 */
interface RecalcDimension extends DimensionScore {
  delta: number | null
}

interface TagView {
  dimension: string
  code: string
  name: string
  score: number | null
  source: string
}

const DIMENSION_LABELS: Record<string, string> = {
  basic: '基础属性',
  behavior: '行为特征',
  behavioral: '行为特征',
  psychology: '心理评估',
  psychological: '心理评估',
  social: '社会关系',
  correction: '矫正表现',
  risk: '风险等级',
}

/** 默认口径：画像主表六维列（DDL 稳定列）。 */
const DEFAULT_DIMENSION_FIELDS: Array<{ code: string; label: string; field: keyof DpsPortrait }> = [
  { code: 'basic', label: '基础属性', field: 'basic_score' },
  { code: 'behavior', label: '行为特征', field: 'behavioral_score' },
  { code: 'psychology', label: '心理评估', field: 'psychological_score' },
  { code: 'social', label: '社会关系', field: 'social_score' },
  { code: 'correction', label: '矫正表现', field: 'correction_score' },
  { code: 'risk', label: '风险等级', field: 'risk_score' },
]

const route = useRoute()
const router = useRouter()
const personId = String(route.params.id || '')
const profile = ref<DpsPortrait | null>(null)
const templateOptions = ref<DpsPortraitTemplate[]>([])
const selectedTemplate = ref('')
const templateResult = ref<Record<string, unknown> | null>(null)
const templateMissing = ref(false)
const loading = ref(false)
const presentation = ref<ErrorPresentation | null>(null)
const editVisible = ref(false)
const editText = ref('')
const saving = ref(false)
const evidenceVisible = ref(false)
const evidenceTitle = ref('')
const evidenceRows = ref<TagView[]>([])

/** 重算：提交异步任务 → 轮询任务查询接口 → 展示结果并刷新画像 */
const recalcVisible = ref(false)
const recalcRunning = ref(false)
const recalcTask = ref<DpsPortraitCalcTask | null>(null)
const recalcResult = ref<Record<string, unknown> | null>(null)
const recalcError = ref('')
const recalcSynchronous = ref(false)
const recalcBeforeOverall = ref<number | null>(null)
const recalcBeforeDimensions = ref(new Map<string, number | null>())
const recalcElapsed = ref(0)
const recalcTimer = ref<ReturnType<typeof setInterval> | null>(null)
const recalcCardRef = ref<{ $el?: HTMLElement } | null>(null)
const scoringVisible = ref(false)
const scoringLoading = ref(false)
const scoringError = ref('')
const scoringItems = ref<DpsTemplateScoringItems | null>(null)

const isForbidden = computed(() => presentation.value?.pageLevel === true)
const isNotFound = computed(() => presentation.value?.kind === 'not-found')
const showErrorBar = computed(
  () => !!presentation.value && !presentation.value.pageLevel && presentation.value.kind !== 'not-found',
)
const errorMessage = computed(() =>
  showErrorBar.value ? `画像详情加载失败：${presentation.value?.detail || '网络错误'}` : '',
)

const templateVersion = computed(() => {
  const matched = templateOptions.value.find((item) => item.code === selectedTemplate.value)
  return matched?.version
})

/** 所选模板的计算结果（缺省为空对象 → 回落默认口径）。 */
const resultPayload = computed<Record<string, unknown>>(() => templateResult.value || {})

const resultCalculatedAt = computed(() => {
  const value = resultPayload.value.calculated_at
  return typeof value === 'string' ? value : undefined
})

const completeness = computed(() => {
  const raw = Number(resultPayload.value.data_completeness)
  return Number.isFinite(raw) ? raw : null
})

const isStale = computed(() => !!resultPayload.value && completeness.value !== null && completeness.value < 0.8)

const overallScore = computed<number | null>(() => {
  if (templateResult.value) return toNumber(resultPayload.value.overall_score)
  return toNumber(profile.value?.overall_score)
})

/** 维度分：有模板结果用模板维度，否则用六维基础列。 */
const dimensionScores = computed<DimensionScore[]>(() => {
  const payloadDimensions = resultPayload.value.dimensions
  if (payloadDimensions && typeof payloadDimensions === 'object') {
    const entries = Object.entries(payloadDimensions as Record<string, unknown>)
    if (entries.length) {
      return entries.map(([code, value]) => {
        const row = (value || {}) as Record<string, unknown>
        return {
          code,
          label: DIMENSION_LABELS[code] || String(row.dimension || code),
          score: toNumber(row.score),
          confidence: toNumber(row.confidence),
        }
      })
    }
  }
  return DEFAULT_DIMENSION_FIELDS.map((item) => ({
    code: item.code,
    label: item.label,
    score: toNumber(profile.value?.[item.field]),
    confidence: null,
  }))
})

/** 重算任务结果字段（异步任务返回 task.result，同步计算直接返回结果体） */
const recalcTaskId = computed(() => String(recalcTask.value?.task_id || ''))
const recalcOverall = computed(() => toNumber(recalcResult.value?.overall_score))
const recalcOverallDelta = computed<number | null>(() => {
  if (recalcOverall.value === null || recalcBeforeOverall.value === null) return null
  return recalcOverall.value - recalcBeforeOverall.value
})
const recalcCompleteness = computed(() => {
  const raw = Number(recalcResult.value?.data_completeness)
  return Number.isFinite(raw) ? raw : null
})
const recalcFinishedAt = computed(() => {
  const value = recalcTask.value?.finished_at
  return typeof value === 'string' ? value : undefined
})
const recalcTemplateLabel = computed(() => {
  const code = String(recalcResult.value?.template_code || '')
  return code ? code : '默认口径（六维基础分）'
})
const recalcStorage = computed(() => {
  const storage = recalcResult.value?.storage as Record<string, unknown> | undefined
  if (!storage) return '默认口径（六维列）'
  if (storage.persisted) return `已写入 ${String(storage.namespace || '模板命名空间')}`
  return `未写入（${String(storage.reason || '未知原因')}）`
})
const recalcDimensions = computed<RecalcDimension[]>(() => {
  const dimensions = recalcResult.value?.dimensions
  if (!dimensions || typeof dimensions !== 'object') return []
  return Object.entries(dimensions as Record<string, unknown>).map(([code, value]) => {
    const row = (value || {}) as Record<string, unknown>
    const score = toNumber(row.score)
    const before = recalcBeforeDimensions.value.get(code)
    return {
      code,
      label: DIMENSION_LABELS[code] || String(row.dimension || code),
      score,
      confidence: toNumber(row.confidence),
      delta: score === null || before === null || before === undefined ? null : score - before,
    }
  })
})
const recalcDurationText = computed(() => {
  const milliseconds = Number(recalcResult.value?.calculation_time_ms)
  if (Number.isFinite(milliseconds) && milliseconds > 0) return `${(milliseconds / 1000).toFixed(2)} s`
  if (recalcSynchronous.value) return '—'
  return recalcElapsed.value > 0 ? `约 ${recalcElapsed.value} s` : '—'
})
const recalcStatusLabel = computed(() => {
  if (recalcError.value) return '计算失败'
  const status = recalcTask.value?.status
  if (status === 'pending') return '排队中'
  if (status === 'running') return '计算中'
  if (status === 'failed') return '计算失败'
  if (recalcSynchronous.value) return '已完成（同步）'
  return '已完成'
})
const recalcStatusType = computed<'success' | 'warning' | 'danger' | 'info'>(() => {
  if (recalcError.value) return 'danger'
  const status = recalcTask.value?.status
  if (status === 'pending' || status === 'running') return 'warning'
  if (status === 'failed') return 'danger'
  return 'success'
})

const tagItems = computed<TagView[]>(() => {
  const rawTags = profile.value?.tags || []
  return rawTags.map((raw) => {
    if (typeof raw === 'string') {
      return { dimension: dimensionOf(raw), code: raw, name: raw, score: null, source: '标签' }
    }
    const code = String(raw.tag_code || raw.tag_value || '')
    const score = toNumber(raw.score)
    return {
      dimension: String(raw.dimension || dimensionOf(code)),
      code: code || '-',
      name: String(raw.tag_name || code || '-'),
      score,
      source: score === null ? '标签' : '标签联动',
    }
  })
})

const tagGroups = computed(() => {
  const groups = new Map<string, TagView[]>()
  for (const tag of tagItems.value) {
    const key = tag.dimension || 'other'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)?.push(tag)
  }
  return Array.from(groups.entries()).map(([dimension, items]) => ({
    dimension,
    label: DIMENSION_LABELS[dimension] || dimension || '其他',
    items,
  }))
})

/** 雷达图几何：≥3 个有分维度才渲染，避免退化图形。 */
const radar = computed(() => {
  const items = dimensionScores.value.filter((item) => item.score !== null)
  if (items.length < 3) return null
  const size = 240
  const center = size / 2
  const radius = 78
  const angleOf = (index: number) => (Math.PI * 2 * index) / items.length - Math.PI / 2
  const points = items.map((item, index) => {
    const angle = angleOf(index)
    const ratio = Math.max(0, Math.min(100, item.score ?? 0)) / 100
    return {
      x: center + Math.cos(angle) * radius * ratio,
      y: center + Math.sin(angle) * radius * ratio,
    }
  })
  const axes = items.map((_item, index) => ({
    x: center + Math.cos(angleOf(index)) * radius,
    y: center + Math.sin(angleOf(index)) * radius,
  }))
  const labels = items.map((item, index) => ({
    x: center + Math.cos(angleOf(index)) * (radius + 22),
    y: center + Math.sin(angleOf(index)) * (radius + 22),
    text: `${item.label} ${item.score === null ? '' : item.score.toFixed(0)}`.trim(),
  }))
  const rings = [0.25, 0.5, 0.75, 1].map((scale) =>
    items
      .map((_item, index) => {
        const angle = angleOf(index)
        return `${(center + Math.cos(angle) * radius * scale).toFixed(1)},${(center + Math.sin(angle) * radius * scale).toFixed(1)}`
      })
      .join(' '),
  )
  return {
    size,
    center,
    points,
    axes,
    labels,
    rings,
    polygon: points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' '),
  }
})

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function dimensionOf(code: string): string {
  return code.includes(':') ? code.split(':')[0] : 'other'
}

function riskOf(row: DpsPortrait): number {
  const raw = row.risk_level ?? row.risk_score
  const n = Number(raw)
  return Number.isFinite(n) ? n : -1
}

function riskLabel(row: DpsPortrait): string {
  const v = riskOf(row)
  if (v < 0) return '未知'
  if (v >= 70) return '高'
  if (v >= 40) return '中'
  return '低'
}

function riskType(row: DpsPortrait): 'success' | 'warning' | 'danger' | 'info' {
  const v = riskOf(row)
  if (v < 0) return 'info'
  if (v >= 70) return 'danger'
  if (v >= 40) return 'warning'
  return 'success'
}

function formatTime(v?: string) {
  if (!v) return '—'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('zh-CN', { hour12: false })
}

function openEvidence(item: DimensionScore) {
  evidenceTitle.value = item.label
  const matched = tagItems.value.filter((tag) => tag.dimension === item.code)
  if (matched.length) {
    evidenceRows.value = matched
  } else {
    const snapshot = (resultPayload.value.dimensions as Record<string, Record<string, unknown>> | undefined)?.[item.code]
    const snapshotTags = (snapshot?.tags || {}) as Record<string, unknown>
    evidenceRows.value = Object.entries(snapshotTags).map(([code, value]) => ({
      dimension: item.code,
      code,
      name: String(value ?? code),
      score: toNumber(value),
      source: '计算快照',
    }))
  }
  evidenceVisible.value = true
}

function openEdit() {
  const attributes = (profile.value?.attributes || {}) as Record<string, unknown>
  editText.value = JSON.stringify(attributes, null, 2)
  editVisible.value = true
}

/** 提交属性增量更新：JSON 校验 → PATCH（携带 If-Match version）→ 刷新 */
async function saveEdit() {
  if (!profile.value) return
  let parsed: unknown
  try {
    parsed = JSON.parse(editText.value || '{}')
  } catch {
    ElMessage.error('属性必须是合法 JSON')
    return
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    ElMessage.error('属性必须是 JSON 对象')
    return
  }
  saving.value = true
  try {
    const version = Number(profile.value.version)
    await dpsApi.updatePortrait(
      personId,
      { business: { attributes: parsed } },
      Number.isFinite(version) ? version : undefined,
    )
    ElMessage.success('画像属性已更新')
    editVisible.value = false
    await loadData()
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 409) {
      ElMessage.warning('版本已变更，已刷新最新数据')
      editVisible.value = false
      await loadData()
    } else {
      ElMessage.error('保存失败，请检查属性内容后重试')
    }
  } finally {
    saving.value = false
  }
}

/** 删除当前画像：二次确认 → DELETE → 返回列表（避免停留已删除详情页） */
async function removePortrait() {
  try {
    await ElMessageBox.confirm(
      `确认删除画像「${profile.value?.name || personId}」？删除后将不再出现在列表与检索中（保留历史审计）。`,
      '删除确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await dpsApi.deletePortrait(personId)
    ElMessage.success('画像已删除')
    await router.replace('/portrait')
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    ElMessage.error(status === 404 ? '画像不存在或已被删除' : '删除失败，请稍后重试')
  }
}

function startRecalcTimer() {
  stopRecalcTimer()
  recalcElapsed.value = 0
  recalcTimer.value = setInterval(() => {
    recalcElapsed.value += 1
  }, 1000)
}

function stopRecalcTimer() {
  if (recalcTimer.value !== null) {
    clearInterval(recalcTimer.value)
    recalcTimer.value = null
  }
}

/** 重算完成后把结果卡片滚入视口，避免用户以为没有反应 */
async function scrollToRecalcCard() {
  await nextTick()
  const element = recalcCardRef.value?.$el
  element?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/** 加载并展示当前口径模板的实际评分项（与计算口径一致） */
async function openScoringItems() {
  if (!selectedTemplate.value) {
    ElMessage.info('请先选择计算口径模板')
    return
  }
  scoringVisible.value = true
  scoringLoading.value = true
  scoringError.value = ''
  scoringItems.value = null
  try {
    scoringItems.value = await dpsApi.getTemplateScoringItems(selectedTemplate.value)
  } catch (err) {
    const described = describeError(err)
    scoringError.value = described.detail || described.title || '评分项加载失败'
  } finally {
    scoringLoading.value = false
  }
}

/**
 * 重算：按当前口径提交计算；异步返回 task_id 时轮询任务查询接口，
 * 终态后展示任务结果并刷新 360 视图。
 */
async function recalculate() {
  if (!personId || recalcRunning.value) return
  recalcVisible.value = true
  recalcRunning.value = true
  recalcError.value = ''
  recalcTask.value = null
  recalcResult.value = null
  recalcSynchronous.value = false
  recalcBeforeOverall.value = overallScore.value
  recalcBeforeDimensions.value = new Map(dimensionScores.value.map((item) => [item.code, item.score]))
  startRecalcTimer()
  try {
    const payload: Record<string, unknown> = { person_id: personId }
    if (selectedTemplate.value) payload.template_code = selectedTemplate.value
    const response = await dpsApi.calculatePortrait(payload)
    const taskId = String(response.task_id || '')
    if (taskId) {
      recalcTask.value = { task_id: taskId, status: 'pending' }
      ElMessage.info('重算任务已提交，正在等待结果…')
      const task = await dpsApi.waitPortraitTask(taskId, {
        onStatus: (next) => {
          recalcTask.value = next
        },
      })
      recalcTask.value = task
      recalcResult.value = (task.result || null) as Record<string, unknown> | null
    } else {
      recalcSynchronous.value = true
      recalcResult.value = response
    }
    stopRecalcTimer()
    ElMessage.success('重算完成，画像数据已刷新')
    await loadData()
    await scrollToRecalcCard()
  } catch (err) {
    stopRecalcTimer()
    const described = describeError(err)
    recalcError.value = described.detail || described.title || '重算失败'
    ElMessage.error(recalcError.value)
  } finally {
    recalcRunning.value = false
  }
}

async function loadTemplateOptions() {
  try {
    const result = await dpsApi.listTemplates({ status: 'active' })
    templateOptions.value = result.items || []
  } catch {
    templateOptions.value = []
  }
}

/** 所选模板口径的结果：404 视为「该模板尚未计算」，不当作加载失败。 */
async function loadTemplateResult() {
  templateResult.value = null
  templateMissing.value = false
  if (!selectedTemplate.value) return
  try {
    const row = await dpsApi.getPortrait(personId, selectedTemplate.value)
    const namespace = row.result_namespace
    if (namespace && typeof namespace === 'object') {
      templateResult.value = namespace as Record<string, unknown>
    } else {
      templateMissing.value = true
    }
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 404) {
      templateMissing.value = true
      return
    }
    throw err
  }
}

async function onTemplateChange() {
  loading.value = true
  presentation.value = null
  try {
    await loadTemplateResult()
  } catch (err) {
    presentation.value = describeError(err)
  } finally {
    loading.value = false
  }
}

async function loadData() {
  if (!personId) {
    presentation.value = {
      kind: 'unknown',
      title: '加载失败',
      detail: '缺少画像 ID 参数',
      requestId: '',
      retryable: false,
      pageLevel: false,
    }
    return
  }
  loading.value = true
  presentation.value = null
  try {
    profile.value = await dpsApi.getPortrait(personId)
    await loadTemplateResult()
  } catch (err) {
    profile.value = null
    presentation.value = describeError(err)
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  stopRecalcTimer()
})

onMounted(() => {
  void loadTemplateOptions()
  void loadData()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-12 { margin-top: 12px; }
.card-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.card-head-actions { display: flex; align-items: center; gap: 8px; }
.recalc-progress { margin-bottom: 12px; }
.scoring-dim { margin-bottom: 16px; }
.scoring-dim-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.delta { margin-left: 6px; font-size: 12px; }
.delta-up { color: #16a34a; }
.delta-down { color: #dc2626; }
.toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.toolbar-label { font-size: 13px; color: #4b5563; }
.toolbar-actions { margin-left: auto; display: flex; align-items: center; gap: 4px; }
.dimension-layout { display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap; }
.radar-wrap { flex: 0 0 240px; display: flex; justify-content: center; }
.dimension-list { flex: 1 1 260px; min-width: 240px; display: flex; flex-direction: column; gap: 12px; }
.dimension-row { cursor: pointer; padding: 6px 8px; border-radius: 8px; transition: background 0.2s; }
.dimension-row:hover { background: #f3f4f6; }
.dimension-row-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }
.dimension-name { font-weight: 600; font-size: 13px; color: #374151; }
.dimension-score { font-size: 15px; font-weight: 600; color: #2563eb; }
.dimension-score.missing { color: #9ca3af; font-weight: 400; font-size: 12px; }
.dimension-meta { display: flex; justify-content: space-between; margin-top: 2px; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag-item { margin-right: 2px; }
.tag-score { margin-left: 4px; color: #2563eb; }
.tag-group { margin-bottom: 12px; }
.tag-group-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.tag-group-title { font-size: 13px; font-weight: 600; color: #374151; }
.muted { color: #9ca3af; }
.sm { font-size: 12px; }
.notes { margin: 0; padding-left: 18px; font-size: 13px; color: #4b5563; line-height: 1.9; }
.request-id { color: #6b7280; font-size: 12px; margin-bottom: 8px; }
.error-detail { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
</style>
