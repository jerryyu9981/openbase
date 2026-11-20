<template>
  <PageContainer
    title="标注作业台"
    :description="view === 'review' ? '审核收件箱：按级对照提交内容与当前画像，逐条或批量复核' : '选择主体 → 按模板录入 → 提交待审；提交后自动进入下一条'"
    test-id="dps-annotation-workbench"
  >
    <template #actions>
      <el-radio-group :model-value="view" data-test="annotation-view-toggle" @update:model-value="switchView">
        <el-radio-button value="entry">录入作业</el-radio-button>
        <el-radio-button value="review">审核收件箱</el-radio-button>
      </el-radio-group>
      <el-button link type="primary" data-test="annotation-shortcut-open" @click="shortcutVisible = true">快捷键 ?</el-button>
    </template>

    <el-alert
      v-if="pageError"
      :title="pageError"
      type="error"
      show-icon
      :closable="false"
      class="mb-16"
      data-test="annotation-page-error"
    />

    <el-row :gutter="16">
      <!-- 左栏：队列 + 保存视图 + 批量 -->
      <el-col :xs="24" :lg="6">
        <el-card shadow="never" class="queue-card" data-test="annotation-queue-card">
          <template #header>
            <div class="card-head">
              <span>{{ view === 'review' ? '审核队列' : '任务队列' }}</span>
              <span class="muted sm">共 {{ queueTotal }} 条</span>
            </div>
          </template>

          <div class="filters">
            <el-select v-model="statusFilter" size="small" style="width: 108px" data-test="annotation-status-filter">
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已驳回" value="rejected" />
              <el-option label="全部" value="all" />
            </el-select>
            <el-select
              v-model="templateFilter"
              size="small"
              clearable
              placeholder="全部模板"
              style="flex: 1; min-width: 110px"
              data-test="annotation-queue-template-filter"
            >
              <el-option v-for="item in templates" :key="item.code" :label="item.name || item.code" :value="item.code">
                <NameCodeLabel :name="item.name" :code="item.code" />
              </el-option>
            </el-select>
            <el-button size="small" :loading="loadingQueue" data-test="annotation-queue-refresh" @click="reloadQueue">
              刷新
            </el-button>
            <el-button size="small" :loading="exporting" data-test="annotation-export" @click="exportAnnotations">
              导出
            </el-button>
          </div>

          <div class="view-tools">
            <el-select
              v-model="activeViewId"
              size="small"
              clearable
              placeholder="保存视图"
              style="flex: 1; min-width: 100px"
              data-test="annotation-saved-view"
              @change="applySavedView"
            >
              <el-option v-for="saved in savedViews" :key="saved.id" :label="saved.name" :value="saved.id" />
            </el-select>
            <el-button link size="small" data-test="annotation-save-view" @click="saveCurrentView">保存视图</el-button>
            <el-dropdown trigger="click" :hide-on-click="false">
              <el-button link size="small" data-test="annotation-column-settings">列设置</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="column in columns" :key="column.key" @click="toggleColumn(column.key)">
                    <el-checkbox :model-value="column.visible" @click.stop>{{ column.label }}</el-checkbox>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <div v-if="view === 'review' && selectedCount" class="batch-bar" data-test="annotation-batch-bar">
            <span class="sm">已选 {{ selectedCount }} 条</span>
            <div class="batch-actions">
              <el-button size="small" type="primary" :loading="batchLoading" data-test="annotation-batch-approve" @click="batchApprove">
                批量通过
              </el-button>
              <el-button size="small" type="danger" :loading="batchLoading" data-test="annotation-batch-reject" @click="batchReject">
                批量驳回
              </el-button>
              <el-button link size="small" @click="clearQueueSelection">取消</el-button>
            </div>
          </div>

          <el-table
            ref="queueTableRef"
            v-loading="loadingQueue"
            :data="rows"
            size="small"
            row-key="id"
            highlight-current-row
            class="queue-table"
            data-test="annotation-queue-table"
            @row-click="selectTask"
            @selection-change="onSelectionChange"
          >
            <el-table-column v-if="view === 'review'" type="selection" width="36" reserve-selection />
            <el-table-column v-if="columnVisible('person')" prop="person_id" label="主体" width="112" show-overflow-tooltip />
            <el-table-column v-if="columnVisible('template')" label="模板" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">
                <NameCodeLabel :name="row.annotation_template_name" :code="row.annotation_template" layout="stack" />
              </template>
            </el-table-column>
            <el-table-column v-if="columnVisible('status')" label="状态" width="76">
              <template #default="{ row }">
                <el-tag size="small" :type="statusType(row.review_status)">{{ statusLabel(row.review_status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column v-if="columnVisible('progress')" label="级数" width="70" data-test="annotation-review-progress">
              <template #default="{ row }">
                <span class="muted sm" data-test="annotation-review-progress-text">{{ progressLabel(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column v-if="columnVisible('created')" label="提交时间" width="90" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="muted sm">{{ shortTime(row.created_at) }}</span>
              </template>
            </el-table-column>
            <template #empty>
              <el-empty description="队列为空" :image-size="60" />
            </template>
          </el-table>

          <div class="pager">
            <el-pagination
              small
              layout="prev, pager, next"
              :total="queueTotal"
              :page-size="pageSize"
              :current-page="page"
              @current-change="changePage"
            />
          </div>
        </el-card>
      </el-col>

      <!-- 中栏：录入表单 / 审核对照 -->
      <el-col :xs="24" :lg="12">
        <el-card v-if="view === 'entry'" shadow="never" class="mb-16" data-test="annotation-entry-card">
          <template #header>
            <div class="card-head">
              <span>录入标注</span>
              <span v-if="currentTask" class="muted sm">
                当前任务 {{ taskIndex + 1 }} / {{ rows.length }}
              </span>
            </div>
          </template>

          <div ref="formRoot">
            <el-form label-width="104px" @submit.prevent>
              <el-form-item label="标注模板" required>
                <el-select
                  v-model="selectedTemplate"
                  filterable
                  placeholder="选择已启用的标注模板"
                  style="width: 100%"
                  data-test="annotation-template-select"
                  @change="onTemplateChange"
                >
                  <el-option v-for="item in templates" :key="item.code" :label="item.name || item.code" :value="item.code">
                    <NameCodeLabel :name="item.name" :code="item.code" />
                  </el-option>
                </el-select>
                <div v-if="currentTemplate" class="hint">
                  <span>归属画像模板：</span>
                  <NameCodeLabel :name="ownerTemplateName" :code="currentTemplate.template_code" />
                  <span> · 场景：{{ currentTemplate.scenario || 'general' }}</span>
                </div>
                <div v-if="mappingLoading" class="hint">字段映射加载中…</div>
                <el-alert
                  v-else-if="fieldMapping && !fieldMapping.scoring_available"
                  type="warning"
                  show-icon
                  :closable="false"
                  class="mt-8"
                  data-test="annotation-mapping-unavailable"
                  title="归属画像模板当前无运行时评分口径（未激活），字段仅写入标签"
                />
              </el-form-item>

              <el-form-item label="主体检索">
                <div class="subject-search">
                  <el-input
                    v-model="subjectKeyword"
                    clearable
                    placeholder="姓名 / person_id / 外部 ID"
                    data-test="annotation-subject-keyword"
                    @keyup.enter="searchSubject"
                  />
                  <el-button :loading="subjectLoading" data-test="annotation-subject-search" @click="searchSubject">
                    检索
                  </el-button>
                </div>
                <el-select
                  v-if="subjectResults.length"
                  :model-value="personId"
                  filterable
                  placeholder="选择检索结果"
                  style="width: 100%; margin-top: 8px"
                  data-test="annotation-subject-results"
                  @change="loadSubjectById"
                >
                  <el-option
                    v-for="item in subjectResults"
                    :key="item.person_id"
                    :label="`${item.name || '-'}（${item.person_id}）`"
                    :value="item.person_id || ''"
                  />
                </el-select>
                <div class="hint">支持姓名、person_id 或外部 ID 模糊检索（服务端）；DPS 未升级时回退精确查询与前 100 条匹配。</div>
                <div v-if="recentSubjects.length" class="recent">
                  <span class="muted sm">最近：</span>
                  <el-tag
                    v-for="item in recentSubjects"
                    :key="item.person_id"
                    size="small"
                    class="recent-tag"
                    @click="loadSubjectById(item.person_id)"
                  >
                    {{ item.name || item.person_id }}
                  </el-tag>
                </div>
              </el-form-item>

              <el-form-item label="主体 person_id" required>
                <el-input
                  v-model="personId"
                  placeholder="如 P-2026-0001（须已存在画像）"
                  data-test="annotation-person-id"
                  @blur="loadSubjectSummary"
                />
                <div class="hint">结构化标注要求主体已有画像，否则后端返回「画像不存在」。</div>
              </el-form-item>

              <el-form-item label="证据来源" :required="evidenceRequired">
                <el-input
                  v-model="evidenceSource"
                  maxlength="200"
                  show-word-limit
                  placeholder="文书编号，如 WS-2026-001"
                  data-test="annotation-evidence-source"
                />
                <div class="hint">
                  {{ evidenceRequired ? '该画像模板要求证据来源，缺失将无法审核通过' : '可选：填写后可追溯标注依据' }}
                </div>
              </el-form-item>

              <div v-if="hasDraftTip" class="draft-tip" data-test="annotation-draft-tip">{{ hasDraftTip }}</div>

              <el-form-item
                v-for="field in schema"
                :key="field.key"
                :label="fieldLabel(field)"
                :required="!!field.required"
                :error="fieldErrors[field.key]"
              >
                <div :data-field-key="field.key" class="field-slot">
                  <el-select
                    v-if="field.type === 'enum'"
                    :model-value="stringValue(field.key)"
                    clearable
                    placeholder="请选择"
                    style="width: 100%"
                    @update:model-value="(value: string) => setValue(field.key, value)"
                  >
                    <el-option v-for="option in field.options || []" :key="option" :label="option" :value="option" />
                  </el-select>
                  <el-select
                    v-else-if="field.type === 'list'"
                    :model-value="listValue(field.key)"
                    multiple
                    filterable
                    allow-create
                    default-first-option
                    placeholder="可多选，回车新增"
                    style="width: 100%"
                    @update:model-value="(value: string[]) => setValue(field.key, value)"
                  >
                    <el-option v-for="option in field.options || []" :key="option" :label="option" :value="option" />
                  </el-select>
                  <el-input
                    v-else
                    :model-value="stringValue(field.key)"
                    :placeholder="fieldPlaceholder(field)"
                    @update:model-value="(value: string) => setValue(field.key, value)"
                  />
                </div>
                <div v-if="fieldHint(field)" class="hint field-mapping" data-test="annotation-field-mapping">
                  {{ fieldHint(field) }}
                </div>
              </el-form-item>

              <el-empty v-if="!schema.length" description="请选择一个标注模板以渲染字段" :image-size="50" />

              <el-alert v-if="submitError" type="error" show-icon :closable="false" class="mb-12" data-test="annotation-submit-error">
                <template #title>{{ submitError }}</template>
              </el-alert>
            </el-form>
          </div>

          <div class="card-actions">
            <el-button
              type="primary"
              :loading="submitting"
              :disabled="!selectedTemplate || !personId.trim()"
              data-test="annotation-submit"
              @click="submit"
            >
              提交标注（Ctrl+Enter）
            </el-button>
            <el-button data-test="annotation-draft-save" @click="saveDraft(true)">暂存（Ctrl+S）</el-button>
            <el-button data-test="annotation-reset" @click="resetForm">重置（Alt+R）</el-button>
            <el-button link data-test="annotation-prev" :disabled="taskIndex <= 0" @click="moveTask(-1)">上一条</el-button>
            <el-button link data-test="annotation-next" :disabled="taskIndex < 0 || taskIndex >= rows.length - 1" @click="moveTask(1)">
              下一条
            </el-button>
          </div>
        </el-card>

        <el-card v-else shadow="never" class="mb-16" data-test="annotation-review-detail">
          <template #header>
            <div class="card-head">
              <span>审核对照</span>
              <span v-if="currentTask" class="muted sm">
                第 {{ Math.min((currentTask.review_level || 0) + 1, reviewRequired(currentTask)) }}/{{ reviewRequired(currentTask) }} 级
              </span>
            </div>
          </template>

          <el-empty v-if="!currentTask" description="从左侧队列选择一条待审记录" :image-size="70" />

          <template v-else>
            <el-descriptions :column="2" border size="small" class="mb-12">
              <el-descriptions-item label="主体">{{ currentTask.person_id || '-' }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag size="small" :type="statusType(currentTask.review_status)">{{ statusLabel(currentTask.review_status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="标注模板">
                <NameCodeLabel :name="currentTask.annotation_template_name" :code="currentTask.annotation_template" />
              </el-descriptions-item>
              <el-descriptions-item label="提交时间">{{ formatTime(currentTask.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="证据来源" :span="2">
                {{ reviewTask?.evidence_source || '-' }}
              </el-descriptions-item>
              <el-descriptions-item
                v-if="reviewTask?.reviewer_id || reviewTask?.review_comment"
                label="审核结论"
                :span="2"
              >
                审核人 {{ reviewTask?.reviewer_id || '-' }} · {{ reviewTask?.review_comment || '-' }}
              </el-descriptions-item>
            </el-descriptions>

            <el-table :data="reviewFields" size="small" border data-test="annotation-review-compare">
              <el-table-column prop="key" label="字段" width="110" />
              <el-table-column prop="value" label="提交值" min-width="120" show-overflow-tooltip />
              <el-table-column prop="current" label="当前画像值" min-width="120" show-overflow-tooltip />
              <el-table-column prop="tag" label="将写入标签" min-width="130" show-overflow-tooltip />
              <el-table-column prop="score" label="评分联动" min-width="150" show-overflow-tooltip />
              <template #empty>
                <el-empty description="该记录无结构化字段" :image-size="50" />
              </template>
            </el-table>
          </template>
        </el-card>
      </el-col>

      <!-- 右栏：上下文（录入）/ 动作与时间线（审核） -->
      <el-col :xs="24" :lg="6">
        <template v-if="view === 'entry'">
          <el-card shadow="never" class="mb-16" data-test="annotation-subject-card">
            <template #header>
              <div class="card-head"><span>主体摘要</span></div>
            </template>
            <el-empty v-if="!subjectSummary" description="检索或输入主体后展示" :image-size="50" />
            <template v-else>
              <div class="subject-name">{{ subjectSummary.name || '-' }}</div>
              <div class="subject-id">{{ subjectSummary.person_id }}</div>
              <div class="subject-meta">
                <el-tag size="small" :type="riskType(subjectSummary)">风险 {{ riskLabel(subjectSummary) }}</el-tag>
                <span class="muted sm">综合分 {{ subjectSummary.overall_score ?? '-' }}</span>
              </div>
              <div class="muted sm">更新时间：{{ formatTime(subjectSummary.updated_at) }}</div>
              <div class="muted sm">标签数：{{ (subjectSummary.tags || []).length }}</div>
              <el-button link type="primary" size="small" @click="goPortrait(subjectSummary.person_id)">查看 360 →</el-button>
            </template>
          </el-card>

          <el-card shadow="never" class="mb-16" data-test="annotation-template-hint-card">
            <template #header>
              <div class="card-head"><span>标注提示</span></div>
            </template>
            <ul class="tip-list">
              <li>归属模板：{{ currentTemplate?.template_code || '-' }}</li>
              <li>评分口径：{{ fieldMapping ? (fieldMapping.scoring_available ? '可用' : '不可用（仅写标签）') : '未加载' }}</li>
              <li>证据来源：{{ evidenceRequired ? '必填' : '可选' }}</li>
              <li>字段数：{{ schema.length }}（其中 {{ mappedFieldCount }} 个字段可生成标签）</li>
            </ul>
          </el-card>

          <el-card shadow="never" data-test="annotation-recent-card">
            <template #header>
              <div class="card-head"><span>最近标注</span></div>
            </template>
            <el-empty v-if="!recentAnnotations.length" description="暂无记录" :image-size="50" />
            <ul v-else class="recent-list">
              <li v-for="item in recentAnnotations" :key="item.id">
                <div class="recent-list__title">{{ item.annotation_template_name || item.annotation_template }}</div>
                <div class="muted sm">{{ formatTime(item.created_at) }} · {{ statusLabel(item.review_status) }}</div>
              </li>
            </ul>
          </el-card>
        </template>

        <template v-else>
          <el-card shadow="never" class="mb-16" data-test="annotation-review-actions">
            <template #header>
              <div class="card-head"><span>审核动作</span></div>
            </template>
            <el-empty v-if="!currentTask" description="选择记录后可审核" :image-size="50" />
            <template v-else>
              <div class="reason-title muted sm">驳回原因模板</div>
              <div class="reason-tags">
                <el-tag
                  v-for="reason in reasonTemplates"
                  :key="reason"
                  size="small"
                  class="reason-tag"
                  @click="appendReason(reason)"
                >
                  {{ reason }}
                </el-tag>
              </div>
              <el-input
                v-model="rejectComment"
                type="textarea"
                :rows="3"
                maxlength="200"
                show-word-limit
                placeholder="审核意见（驳回时作为统一原因）"
                data-test="annotation-review-comment"
              />
              <div class="review-buttons">
                <el-button
                  type="primary"
                  :loading="reviewing"
                  data-test="annotation-approve"
                  @click="approveCurrent"
                >
                  {{ approveLabel(currentTask) }}
                </el-button>
                <el-button type="danger" :loading="reviewing" data-test="annotation-reject" @click="rejectCurrent">
                  驳回
                </el-button>
              </div>
              <div class="muted sm mt-8">Alt+←/→ 切换记录；末级通过才联动标签。</div>
            </template>
          </el-card>

          <el-card shadow="never" data-test="annotation-timeline-card">
            <template #header>
              <div class="card-head"><span>审计时间线</span></div>
            </template>
            <div v-loading="reviewLogLoading">
              <el-empty v-if="!reviewLogs.length" description="暂无审核记录" :image-size="50" />
              <el-timeline v-else>
                <el-timeline-item
                  v-for="log in reviewLogs"
                  :key="`${log.review_level}-${log.created_at}-${log.action}`"
                  :timestamp="formatTime(log.created_at)"
                  placement="top"
                >
                  <div class="timeline-title">第 {{ log.review_level }} 级 · {{ actionLabel(log.action) }}</div>
                  <div class="muted sm">审核人：{{ log.reviewer || '-' }}</div>
                  <div v-if="log.comment" class="muted sm">意见：{{ log.comment }}</div>
                </el-timeline-item>
              </el-timeline>
            </div>
          </el-card>
        </template>
      </el-col>
    </el-row>

    <el-dialog v-model="shortcutVisible" title="快捷键" width="460px" data-test="annotation-shortcut-dialog">
      <el-table :data="shortcutRows" size="small" :show-header="false">
        <el-table-column prop="keys" label="快捷键" width="170" />
        <el-table-column prop="action" label="作用" />
      </el-table>
    </el-dialog>

    <el-dialog v-model="saveViewVisible" title="保存当前视图" width="420px" data-test="annotation-save-view-dialog">
      <el-input v-model="saveViewName" maxlength="20" show-word-limit placeholder="视图名称，如：我的待初审" />
      <template #footer>
        <el-button @click="saveViewVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSaveView">保存</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import NameCodeLabel from '@/components/common/NameCodeLabel.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  dpsApi,
  type DpsAnnotationField,
  type DpsAnnotationFieldMapping,
  type DpsAnnotationFieldMappingEntry,
  type DpsAnnotationDetail,
  type DpsAnnotationReviewLogItem,
  type DpsAnnotationReviewProgress,
  type DpsAnnotationRow,
  type DpsAnnotationTemplate,
  type DpsEvidencePolicy,
  type DpsPortrait,
  type DpsPortraitTemplate,
} from '@/core/api/dps'
import { describeDpsError } from '@/core/api/error'
import { useDpsListView } from '../composables/useDpsListView'

type WorkbenchView = 'entry' | 'review'

interface RecentSubject {
  person_id: string
  name?: string
}

const route = useRoute()
const router = useRouter()

/* ------------------------------ 路由视图与筛选 ------------------------------ */

function queryText(value: unknown): string {
  if (Array.isArray(value)) return String(value[0] ?? '')
  return String(value ?? '')
}

const view = computed<WorkbenchView>(() => (queryText(route.query.view) === 'review' ? 'review' : 'entry'))

const statusFilter = computed({
  get: () => queryText(route.query.status) || 'pending',
  set: (value: string) => patchQuery({ status: value || 'pending', page: undefined }),
})

const templateFilter = computed({
  get: () => queryText(route.query.template),
  set: (value: string) => patchQuery({ template: value || undefined, page: undefined }),
})

const page = computed(() => Math.max(1, Number(queryText(route.query.page)) || 1))

/** 查询参数写回 URL（视图切换 push，筛选 replace），保证深链/刷新/前进后退一致 */
function patchQuery(patch: Record<string, string | undefined>, replace = true) {
  const merged: Record<string, unknown> = { ...route.query, ...patch }
  const query: Record<string, string> = {}
  Object.entries(merged).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    query[key] = String(value)
  })
  const location = { path: route.path, query }
  void (replace ? router.replace(location) : router.push(location))
}

function switchView(next: string | number | boolean | undefined) {
  const target: WorkbenchView = String(next) === 'review' ? 'review' : 'entry'
  if (target === view.value) return
  currentTask.value = null
  clearQueueSelection()
  patchQuery({ view: target === 'review' ? 'review' : undefined }, false)
}

/* ------------------------------ 模板与字段 ------------------------------ */

const templates = ref<DpsAnnotationTemplate[]>([])
const portraitTemplates = ref<DpsPortraitTemplate[]>([])
const selectedTemplate = ref('')
const fieldMapping = ref<DpsAnnotationFieldMapping | null>(null)
const evidencePolicy = ref<DpsEvidencePolicy | null>(null)
const mappingLoading = ref(false)

const currentTemplate = computed(() => templates.value.find((item) => item.code === selectedTemplate.value) || null)

const ownerTemplateName = computed(() => {
  const code = currentTemplate.value?.template_code
  if (!code) return ''
  return portraitTemplates.value.find((item) => item.code === code)?.name || ''
})

const schema = computed<DpsAnnotationField[]>(() => {
  const raw = currentTemplate.value?.field_schema
  const parsed = typeof raw === 'string' ? safeParse(raw) : raw
  return Array.isArray(parsed) ? (parsed as DpsAnnotationField[]) : []
})

const mappingByField = computed<Record<string, DpsAnnotationFieldMappingEntry>>(() => {
  const map: Record<string, DpsAnnotationFieldMappingEntry> = {}
  ;(fieldMapping.value?.fields || []).forEach((item) => {
    map[item.key] = item
  })
  return map
})

const mappedFieldCount = computed(
  () => schema.value.filter((field) => mappingByField.value[field.key]?.scoring_status !== 'no_tag').length,
)

const evidenceRequired = computed(() => !!evidencePolicy.value?.require_source)

function safeParse(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function fieldLabel(field: DpsAnnotationField): string {
  return field.key
}

function fieldPlaceholder(field: DpsAnnotationField): string {
  if (field.type === 'number') return field.range ? `数值（${(field.range as number[]).join(' ~ ')}）` : '数值'
  if (field.type === 'date') return 'YYYY-MM-DD'
  return '请输入'
}

/** 字段 → 标签 → 评分项提示 */
function fieldHint(field: DpsAnnotationField): string {
  const entry = mappingByField.value[field.key]
  if (!entry) {
    return field.target_dimension ? `→ 通过后计入维度 ${field.target_dimension}` : ''
  }
  if (entry.scoring_status === 'no_tag') return '不生成标签（未配置目标维度）'
  const tagPart = `→ 写入 ${entry.tag_code}`
  const scorePart = entry.score_rule ? ` · 计分：${entry.score_rule.summary}` : ''
  if (entry.scoring_status === 'affects' && entry.affects_scoring.length) {
    const hits = entry.affects_scoring.map((hit) => `${hit.rule_key}（权重 ${hit.weight}）`).join('、')
    return `${tagPart}${scorePart} · 影响评分项 ${hits}`
  }
  return `${tagPart}${scorePart} · 仅生成标签，当前模板无同名评分项`
}

async function loadFieldMapping() {
  if (!selectedTemplate.value) {
    fieldMapping.value = null
    evidencePolicy.value = null
    return
  }
  mappingLoading.value = true
  const templateCode = currentTemplate.value?.template_code
  const [mappingResult, templateResult] = await Promise.allSettled([
    dpsApi.getAnnotationFieldMapping(selectedTemplate.value),
    templateCode ? dpsApi.getTemplate(templateCode) : Promise.resolve(null),
  ])
  fieldMapping.value = mappingResult.status === 'fulfilled' ? mappingResult.value : null
  evidencePolicy.value =
    templateResult.status === 'fulfilled' ? templateResult.value?.evidence_policy || null : null
  mappingLoading.value = false
}

async function loadTemplates() {
  try {
    const [result, portraitResult] = await Promise.all([
      dpsApi.listAnnotationTemplates({ page: 1, page_size: 100 }),
      dpsApi.listTemplates().catch(() => ({ items: [] as DpsPortraitTemplate[] })),
    ])
    portraitTemplates.value = portraitResult.items || []
    templates.value = (result.items || []).filter((item) => item.status !== 'inactive')
    if (!selectedTemplate.value && templates.value.length) {
      selectedTemplate.value = templates.value[0].code
      applyDefaults()
      void loadFieldMapping()
    }
  } catch (err) {
    pageError.value = `标注模板加载失败：${describeDpsError(err).detail}`
  }
}

/* ------------------------------ 录入表单 ------------------------------ */

const personId = ref('')
const values = reactive<Record<string, unknown>>({})
const evidenceSource = ref('')
const fieldErrors = reactive<Record<string, string>>({})
const submitting = ref(false)
const submitError = ref('')
const pageError = ref('')
const formRoot = ref<HTMLElement | null>(null)
const hasDraftTip = ref('')

const subjectKeyword = ref('')
const subjectResults = ref<DpsPortrait[]>([])
const subjectLoading = ref(false)
const subjectSummary = ref<DpsPortrait | null>(null)
const recentSubjects = ref<RecentSubject[]>(readRecentSubjects())
const recentAnnotations = ref<DpsAnnotationRow[]>([])
const currentTask = ref<DpsAnnotationRow | null>(null)

function stringValue(key: string): string {
  const raw = values[key]
  return raw === null || raw === undefined ? '' : String(raw)
}

function listValue(key: string): string[] {
  const raw = values[key]
  return Array.isArray(raw) ? (raw as string[]) : []
}

function setValue(key: string, value: unknown) {
  values[key] = value
  if (fieldErrors[key]) delete fieldErrors[key]
}

function applyDefaults() {
  schema.value.forEach((field) => {
    if (field.type === 'enum' && field.options?.length) values[field.key] = field.options[0]
  })
}

function resetForm() {
  Object.keys(values).forEach((key) => delete values[key])
  Object.keys(fieldErrors).forEach((key) => delete fieldErrors[key])
  submitError.value = ''
  evidenceSource.value = ''
  personId.value = ''
  subjectSummary.value = null
  recentAnnotations.value = []
  hasDraftTip.value = ''
  currentTask.value = null
  applyDefaults()
}

async function onTemplateChange() {
  Object.keys(values).forEach((key) => delete values[key])
  Object.keys(fieldErrors).forEach((key) => delete fieldErrors[key])
  submitError.value = ''
  evidenceSource.value = ''
  hasDraftTip.value = ''
  applyDefaults()
  await loadFieldMapping()
}

function isEmptyRaw(raw: unknown): boolean {
  if (raw === undefined || raw === null) return true
  if (Array.isArray(raw)) return raw.length === 0
  return String(raw).trim() === ''
}

function validateFields(): boolean {
  Object.keys(fieldErrors).forEach((key) => delete fieldErrors[key])
  schema.value.forEach((field) => {
    const raw = values[field.key]
    if (field.required && isEmptyRaw(raw)) {
      fieldErrors[field.key] = '必填'
      return
    }
    if (field.type === 'number' && !isEmptyRaw(raw)) {
      const numeric = Number(raw)
      if (!Number.isFinite(numeric)) {
        fieldErrors[field.key] = '请输入数字'
        return
      }
      if (Array.isArray(field.range) && field.range.length === 2) {
        const low = Number(field.range[0])
        const high = Number(field.range[1])
        if (numeric < low || numeric > high) {
          fieldErrors[field.key] = `取值范围 ${low} ~ ${high}`
        }
      }
    }
    if (field.type === 'enum' && !isEmptyRaw(raw) && field.options?.length && !field.options.includes(String(raw))) {
      fieldErrors[field.key] = '请选择有效选项'
    }
  })

  if (!selectedTemplate.value) submitError.value = '请选择标注模板'
  else if (!personId.value.trim()) submitError.value = '请选择或填写主体 person_id'
  else if (evidenceRequired.value && !evidenceSource.value.trim()) submitError.value = '该画像模板要求证据来源（文书编号），请补充后提交'
  else if (Object.keys(fieldErrors).length) submitError.value = `请检查 ${Object.keys(fieldErrors).length} 个字段`
  else submitError.value = ''

  return (
    !!selectedTemplate.value &&
    !!personId.value.trim() &&
    !(evidenceRequired.value && !evidenceSource.value.trim()) &&
    Object.keys(fieldErrors).length === 0
  )
}

/** 自动聚焦首个错误字段（字段 key 由后端 schema 约束，不含引号） */
async function focusFirstError() {
  await nextTick()
  const firstKey = Object.keys(fieldErrors)[0]
  if (!firstKey || !formRoot.value) return
  const wrapper = formRoot.value.querySelector<HTMLElement>(`[data-field-key="${firstKey}"]`)
  wrapper?.querySelector<HTMLElement>('input, textarea')?.focus()
}

async function submit() {
  if (!validateFields()) {
    await focusFirstError()
    return
  }
  const fields: Record<string, unknown> = {}
  schema.value.forEach((field) => {
    const raw = values[field.key]
    if (isEmptyRaw(raw)) return
    fields[field.key] = field.type === 'number' ? Number(raw) : raw
  })

  submitting.value = true
  try {
    await dpsApi.createAnnotation({
      action: 'create',
      person_id: personId.value.trim(),
      annotation_template: selectedTemplate.value,
      template_code: currentTemplate.value?.template_code,
      fields,
      created_by: 'operator',
      evidence_source: evidenceSource.value.trim() || undefined,
    })
    ElMessage.success('标注已提交，进入待审核队列')
    clearDraft()
    const submittedTemplate = selectedTemplate.value
    Object.keys(values).forEach((key) => delete values[key])
    evidenceSource.value = ''
    submitError.value = ''
    hasDraftTip.value = ''
    selectedTemplate.value = submittedTemplate
    applyDefaults()
    currentTask.value = null
    await loadQueue()
    const nextTask = rows.value.find((row) => row.person_id !== personId.value) || rows.value[0]
    if (nextTask) void selectTask(nextTask)
  } catch (err) {
    const described = describeDpsError(err)
    submitError.value = described.detail || described.title
  } finally {
    submitting.value = false
  }
}

/* ------------------------------ 草稿 ------------------------------ */

interface DraftPayload {
  values: Record<string, unknown>
  evidence_source: string
  saved_at: number
}

function draftKey(): string {
  return `dps.annotation.draft.${selectedTemplate.value}.${personId.value.trim()}`
}

function saveDraft(notify: boolean) {
  if (!selectedTemplate.value || !personId.value.trim()) {
    if (notify) ElMessage.warning('请先选择标注模板与主体再暂存')
    return
  }
  const payload: DraftPayload = {
    values: { ...values },
    evidence_source: evidenceSource.value,
    saved_at: Date.now(),
  }
  try {
    localStorage.setItem(draftKey(), JSON.stringify(payload))
    if (notify) ElMessage.success('草稿已暂存到本地')
  } catch {
    if (notify) ElMessage.warning('本地暂存不可用，请直接提交')
  }
}

function restoreDraft() {
  if (!selectedTemplate.value || !personId.value.trim()) return
  let raw = ''
  try {
    raw = localStorage.getItem(draftKey()) || ''
  } catch {
    return
  }
  if (!raw) return
  try {
    const draft = JSON.parse(raw) as DraftPayload
    Object.keys(values).forEach((key) => delete values[key])
    Object.assign(values, draft.values || {})
    evidenceSource.value = draft.evidence_source || ''
    hasDraftTip.value = `已恢复本地草稿（${formatTime(new Date(draft.saved_at).toISOString())}）`
  } catch {
    // 损坏草稿直接忽略，不阻断录入
  }
}

function clearDraft() {
  try {
    localStorage.removeItem(draftKey())
  } catch {
    // 忽略存储清理失败
  }
}

/** 排除「枚举默认首项」造成的伪编辑，避免一选模板就拦截离开 */
const isDirty = computed(() => {
  const editedField = Object.entries(values).some(([key, value]) => {
    const field = schema.value.find((item) => item.key === key)
    if (
      field?.type === 'enum' &&
      field.options?.length &&
      value === field.options[0]
    ) {
      return false
    }
    return !isEmptyRaw(value)
  })
  return editedField || !!evidenceSource.value.trim()
})

/* ------------------------------ 主体检索 ------------------------------ */

function readRecentSubjects(): RecentSubject[] {
  try {
    const raw = localStorage.getItem('dps.subject.recent')
    const parsed = raw ? (JSON.parse(raw) as RecentSubject[]) : []
    return Array.isArray(parsed) ? parsed.slice(0, 6) : []
  } catch {
    return []
  }
}

function rememberSubject(portrait: DpsPortrait) {
  const personIdValue = portrait.person_id
  if (!personIdValue) return
  const next = [
    { person_id: personIdValue, name: portrait.name },
    ...recentSubjects.value.filter((item) => item.person_id !== personIdValue),
  ].slice(0, 6)
  recentSubjects.value = next
  try {
    localStorage.setItem('dps.subject.recent', JSON.stringify(next))
  } catch {
    // 存储不可用时仅保留内存态
  }
}

async function searchSubject() {
  const keyword = subjectKeyword.value.trim()
  if (!keyword) {
    ElMessage.warning('请输入姓名、person_id 或外部 ID')
    return
  }
  subjectLoading.value = true
  try {
    let found: DpsPortrait[] = []
    try {
      const paged = await dpsApi.listPortraits({ page: 1, page_size: 20, keyword })
      found = paged.items || []
    } catch (caught) {
      // DPS 未升级（404）→ 回退旧口径：精确 ID/外部 ID + 前 100 条本地匹配
      if ((caught as { response?: { status?: number } })?.response?.status !== 404) throw caught
      const [byExternal, byId] = await Promise.allSettled([
        dpsApi.getPortraitByExternal(keyword),
        dpsApi.getPortrait(keyword),
      ])
      ;[byExternal, byId].forEach((result) => {
        if (result.status === 'fulfilled' && result.value?.person_id) found.push(result.value)
      })
      if (!found.length) {
        const pageResult = await dpsApi.listPortraits({ page: 1, page_size: 100 }).catch(() => null)
        ;(pageResult?.items || [])
          .filter((item) => {
            const haystack = `${item.name || ''} ${item.person_id || ''}`.toLowerCase()
            return haystack.includes(keyword.toLowerCase())
          })
          .slice(0, 10)
          .forEach((item) => found.push(item))
      }
    }

    const deduped = new Map<string, DpsPortrait>()
    found.forEach((item) => {
      if (item.person_id) deduped.set(item.person_id, item)
    })
    subjectResults.value = Array.from(deduped.values())

    if (!subjectResults.value.length) {
      ElMessage.warning('未找到匹配主体（支持姓名、person_id 或外部 ID）')
    } else if (subjectResults.value.length === 1) {
      void loadSubjectById(subjectResults.value[0].person_id || '')
    }
  } catch (err) {
    pageError.value = `主体检索失败：${describeDpsError(err).detail}`
  } finally {
    subjectLoading.value = false
  }
}

async function loadSubjectById(personIdValue: string) {
  if (!personIdValue) return
  personId.value = personIdValue
  await loadSubjectSummary()
}

async function loadSubjectSummary() {
  const id = personId.value.trim()
  if (!id) {
    subjectSummary.value = null
    recentAnnotations.value = []
    return
  }
  const [portrait, history] = await Promise.allSettled([
    dpsApi.getPortrait(id),
    dpsApi.listAnnotations({ person_id: id, page: 1, page_size: 5 }),
  ])
  if (portrait.status === 'fulfilled') {
    subjectSummary.value = portrait.value
    rememberSubject(portrait.value)
  } else {
    subjectSummary.value = null
  }
  recentAnnotations.value = history.status === 'fulfilled' ? history.value.items || [] : []
}

/* ------------------------------ 队列 ------------------------------ */

const rows = ref<DpsAnnotationRow[]>([])
const queueTotal = ref(0)
const pageSize = ref(20)
const loadingQueue = ref(false)
const queueTableRef = ref<{ clearSelection: () => void } | null>(null)
const currentTaskId = computed(() => currentTask.value?.id || '')
const taskIndex = computed(() => rows.value.findIndex((row) => row.id === currentTaskId.value))

const {
  savedViews,
  activeViewId,
  saveView,
  applyView,
  columns,
  toggleColumn,
  columnVisible,
  selection,
  selectedCount,
  setSelection,
  clearSelection,
} = useDpsListView({
  pageKey: 'annotations',
  columns: [
    { key: 'person', label: '主体' },
    { key: 'template', label: '模板' },
    { key: 'status', label: '状态' },
    { key: 'progress', label: '级数' },
    { key: 'created', label: '提交时间' },
  ],
  hiddenByDefault: ['created'],
})

const saveViewVisible = ref(false)
const saveViewName = ref('')

async function loadQueue() {
  loadingQueue.value = true
  try {
    const result = await dpsApi.listAnnotations({
      annotation_template: templateFilter.value || undefined,
      review_status: statusFilter.value === 'all' ? undefined : statusFilter.value,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = result.items || []
    queueTotal.value = Number(result.total || 0)
    if (view.value === 'review' && !currentTask.value && rows.value.length) {
      void selectTask(rows.value[0])
    }
  } catch (err) {
    pageError.value = `标注队列加载失败：${describeDpsError(err).detail}`
    rows.value = []
    queueTotal.value = 0
  } finally {
    loadingQueue.value = false
  }
}

function reloadQueue() {
  if (page.value !== 1) {
    patchQuery({ page: undefined })
    return
  }
  void loadQueue()
}

function changePage(next: number) {
  patchQuery({ page: next > 1 ? String(next) : undefined })
}

function onSelectionChange(selected: DpsAnnotationRow[]) {
  setSelection(selected.map((row) => row.id))
}

function clearQueueSelection() {
  queueTableRef.value?.clearSelection()
  clearSelection()
}

async function selectTask(row: DpsAnnotationRow) {
  currentTask.value = row
  if (view.value === 'entry') {
    personId.value = row.person_id || ''
    if (row.annotation_template && templates.value.some((item) => item.code === row.annotation_template)) {
      selectedTemplate.value = row.annotation_template
      Object.keys(values).forEach((key) => delete values[key])
      applyDefaults()
      await loadFieldMapping()
      restoreDraft()
    }
    await loadSubjectSummary()
  } else {
    await loadReviewContext(row)
  }
}

function moveTask(offset: number) {
  if (!rows.value.length) return
  const baseIndex = taskIndex.value < 0 ? 0 : taskIndex.value
  const nextIndex = Math.min(Math.max(baseIndex + offset, 0), rows.value.length - 1)
  if (nextIndex === taskIndex.value) return
  void selectTask(rows.value[nextIndex])
}

function applySavedView(viewId: string) {
  const filters = applyView(viewId)
  if (!filters) return
  patchQuery({
    status: filters.status || 'pending',
    template: filters.template || undefined,
    page: undefined,
  })
}

function saveCurrentView() {
  saveViewName.value = ''
  saveViewVisible.value = true
}

function confirmSaveView() {
  const name = saveViewName.value.trim()
  if (!name) {
    ElMessage.warning('请输入视图名称')
    return
  }
  saveView(name, {
    status: statusFilter.value,
    template: templateFilter.value,
  })
  saveViewVisible.value = false
  ElMessage.success('视图已保存到本地')
}

/* ------------------------------ 审核 ------------------------------ */

const reviewing = ref(false)
const rejectComment = ref('')
const reasonTemplates = ['材料不足', '字段与事实不符', '证据缺失']
const batchLoading = ref(false)

const reviewPortrait = ref<DpsPortrait | null>(null)
const reviewMapping = ref<DpsAnnotationFieldMapping | null>(null)
/** A4：详情接口结果；上游未升级（404）时保持 null 并回退队列摘要 */
const reviewDetail = ref<DpsAnnotationDetail | null>(null)
const reviewLogs = ref<DpsAnnotationReviewLogItem[]>([])
const reviewLogLoading = ref(false)
const exporting = ref(false)

/** A11：按当前队列筛选导出标注 CSV（服务端生成；失败时提示，不造假数据） */
async function exportAnnotations() {
  exporting.value = true
  try {
    const result = await dpsApi.exportAnnotationsCsv({
      annotation_template: templateFilter.value || undefined,
      review_status: statusFilter.value !== 'all' ? statusFilter.value : undefined,
    })
    const url = URL.createObjectURL(result.blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = result.filename
    anchor.click()
    URL.revokeObjectURL(url)
    ElMessage.success(`标注 CSV 已导出${result.truncated ? '（超过 10000 行，已截断）' : ''}`)
  } catch {
    ElMessage.error('标注导出失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}

const reviewTask = computed(() => reviewDetail.value?.annotation || currentTask.value)

const reviewFields = computed(() => {
  const row = reviewTask.value
  if (!row?.fields) return []
  return Object.entries(row.fields).map(([key, value]) => {
    const entry = (reviewMapping.value?.fields || []).find((item) => item.key === key)
    return {
      key,
      value: Array.isArray(value) ? value.join('、') : String(value ?? ''),
      current: portraitValue(key),
      tag:
        entry?.scoring_status === 'no_tag'
          ? '不生成标签'
          : entry?.tag_code || '—',
      score:
        entry?.score_rule?.summary ||
        (entry?.affects_scoring?.length
          ? entry.affects_scoring.map((hit) => `${hit.rule_key}（权重 ${hit.weight}）`).join('、')
          : '—'),
    }
  })
})

function portraitValue(key: string): string {
  const portrait = reviewPortrait.value
  if (!portrait) return '—'
  const attributes = portrait.attributes || {}
  if (attributes[key] !== undefined) return String(attributes[key])
  const tag = (portrait.tags || []).find((item) => {
    if (typeof item !== 'object' || item === null) return false
    const record = item as Record<string, unknown>
    const code = String(record.tag_code || '')
    return code === key || code.endsWith(`:${key}`) || String(record.tag_name || '') === key
  })
  if (typeof tag === 'object' && tag !== null) {
    const record = tag as Record<string, unknown>
    return String(record.score ?? record.tag_value ?? record.tag_name ?? '—')
  }
  return '—'
}

async function loadReviewContext(row: DpsAnnotationRow) {
  reviewPortrait.value = null
  reviewMapping.value = null
  reviewDetail.value = null
  reviewLogs.value = []
  reviewLogLoading.value = true
  const [detail, portrait, mapping, logs] = await Promise.allSettled([
    dpsApi.getAnnotationDetail(row.id),
    row.person_id ? dpsApi.getPortrait(row.person_id) : Promise.reject(new Error('缺少主体')),
    row.annotation_template ? dpsApi.getAnnotationFieldMapping(row.annotation_template) : Promise.reject(new Error('缺少模板')),
    dpsApi.getAnnotationReviewLog(row.id),
  ])
  // A4：详情成功时以服务端全量上下文为准；404（DPS 未升级）静默回退队列摘要
  if (detail.status === 'fulfilled' && detail.value?.annotation) {
    reviewDetail.value = detail.value
  }
  if (portrait.status === 'fulfilled') reviewPortrait.value = portrait.value
  if (mapping.status === 'fulfilled') reviewMapping.value = mapping.value
  if (logs.status === 'fulfilled' && logs.value.items?.length) {
    reviewLogs.value = logs.value.items
  } else {
    // A10：审核留痕为空时回退实体审计时间线（DPS 未升级 404 时保持空态）
    try {
      const timeline = await dpsApi.getAuditTimeline({
        entity_type: 'annotation',
        entity_id: row.id,
        page_size: 50,
        order: 'asc',
      })
      reviewLogs.value = timeline.items.map((item) => ({
        review_level: 1,
        action: String(item.action || 'audit'),
        reviewer: item.user_id ? String(item.user_id) : null,
        comment: item.detail ? String(item.detail) : null,
        created_at: item.timestamp ? String(item.timestamp) : undefined,
      }))
    } catch {
      reviewLogs.value = []
    }
  }
  reviewLogLoading.value = false
}

function appendReason(reason: string) {
  rejectComment.value = rejectComment.value ? `${rejectComment.value}；${reason}` : reason
}

function reviewRequired(row: DpsAnnotationRow): number {
  return Math.max(1, Number(row.review_levels_required || 1))
}

function reviewLevel(row: DpsAnnotationRow): number {
  return Math.max(0, Number(row.review_level || 0))
}

function progressLabel(row: DpsAnnotationRow): string {
  if (row.review_status === 'approved') return '已完成'
  return `${Math.min(reviewLevel(row), reviewRequired(row))}/${reviewRequired(row)}`
}

function approveLabel(row: DpsAnnotationRow): string {
  const required = reviewRequired(row)
  if (required <= 1) return '通过'
  const nextLevel = reviewLevel(row) + 1
  return nextLevel < required ? `通过本级（${nextLevel}/${required}）` : '终审通过'
}

async function approveCurrent() {
  const row = currentTask.value
  if (!row) return
  const required = reviewRequired(row)
  const nextLevel = Math.min(reviewLevel(row) + 1, required)
  const finalStep = nextLevel >= required
  const scope = required > 1 ? `第 ${nextLevel}/${required} 级` : '单级'
  try {
    await ElMessageBox.confirm(
      `确认通过主体「${row.person_id || '-'}」的标注（${scope}）？${
        finalStep ? '终审通过后将按字段目标维度联动标签。' : '非末级通过不会联动标签。'
      }`,
      finalStep ? '终审确认' : '本级通过确认',
      { type: 'info', confirmButtonText: '确认通过' },
    )
  } catch {
    return
  }
  await doReview(row, 'approved', '')
}

async function rejectCurrent() {
  const row = currentTask.value
  if (!row) return
  if (!rejectComment.value.trim()) {
    ElMessage.warning('请填写驳回原因或选择原因模板')
    return
  }
  await doReview(row, 'rejected', rejectComment.value.trim())
}

async function doReview(row: DpsAnnotationRow, status: 'approved' | 'rejected', comment: string) {
  reviewing.value = true
  try {
    const result = await dpsApi.submitReview(row.id, { review_status: status, comment })
    if (status === 'rejected') {
      ElMessage.success('已驳回')
    } else {
      const review = result.review as DpsAnnotationReviewProgress | undefined
      if (review && !review.finalized) {
        ElMessage.success(`已通过第 ${review.level} 级，待第 ${review.level + 1} 级审核`)
      } else {
        ElMessage.success('终审通过，标签联动已执行')
      }
    }
    rejectComment.value = ''
    currentTask.value = null
    clearQueueSelection()
    await loadQueue()
  } catch (err) {
    pageError.value = `复核失败：${describeDpsError(err).detail}`
  } finally {
    reviewing.value = false
  }
}

async function batchApprove() {
  const ids = selection.value.slice()
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(
      `确认通过已选 ${ids.length} 条标注？非末级仅推进级数，末级才联动标签。`,
      '批量通过',
      { type: 'info', confirmButtonText: '确认通过' },
    )
  } catch {
    return
  }
  await runBatch(ids, 'approved')
}

async function batchReject() {
  const ids = selection.value.slice()
  if (!ids.length) return
  let comment = ''
  try {
    const result = await ElMessageBox.prompt('请填写统一驳回原因', '批量驳回', {
      inputPlaceholder: '如：材料不足 / 证据缺失',
      inputValidator: (value: string) => (value && value.trim() ? true : '驳回原因不能为空'),
    })
    comment = result.value || ''
  } catch {
    return
  }
  await runBatch(ids, 'rejected', comment)
}

async function runBatch(ids: string[], status: 'approved' | 'rejected', comment?: string) {
  batchLoading.value = true
  try {
    const result = await dpsApi.batchReviewAnnotations(
      ids.map((id) => ({
        annotation_id: id,
        status,
        current_status: 'pending',
        comment,
      })),
    )
    if (result.failed > 0) {
      ElMessage.warning(`批量复核完成：成功 ${result.succeeded} / 失败 ${result.failed}`)
    } else {
      ElMessage.success(`批量复核成功 ${result.succeeded} 条`)
    }
    currentTask.value = null
    clearQueueSelection()
    await loadQueue()
  } catch (err) {
    pageError.value = `批量复核失败：${describeDpsError(err).detail}`
  } finally {
    batchLoading.value = false
  }
}

/* ------------------------------ 展示工具 ------------------------------ */

const shortcutVisible = ref(false)
const shortcutRows = [
  { keys: 'Ctrl / Cmd + Enter', action: '提交当前标注 / 通过当前审核' },
  { keys: 'Ctrl / Cmd + S', action: '暂存草稿（仅录入视图）' },
  { keys: 'Alt + ← / →', action: '上一条 / 下一条队列任务' },
  { keys: 'Alt + R', action: '重置录入表单' },
  { keys: '?', action: '打开快捷键面板' },
  { keys: 'Esc', action: '关闭弹窗 / 抽屉' },
]

function statusLabel(status?: string): string {
  return { pending: '待审核', approved: '已通过', rejected: '已驳回', modified: '已修改' }[status || ''] || status || '-'
}

function statusType(status?: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  if (status === 'pending') return 'warning'
  return 'info'
}

function actionLabel(action?: string): string {
  return { approved: '通过', rejected: '驳回', modified: '修改' }[action || ''] || action || '-'
}

function riskOf(row: DpsPortrait): number {
  const raw = row.risk_level ?? row.risk_score
  const numeric = Number(raw)
  return Number.isFinite(numeric) ? numeric : -1
}

function riskLabel(row: DpsPortrait): string {
  const value = riskOf(row)
  if (value < 0) return '未知'
  if (value >= 70) return '高'
  if (value >= 40) return '中'
  return '低'
}

function riskType(row: DpsPortrait): 'success' | 'warning' | 'danger' | 'info' {
  const value = riskOf(row)
  if (value < 0) return 'info'
  if (value >= 70) return 'danger'
  if (value >= 40) return 'warning'
  return 'success'
}

function formatTime(value?: string): string {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

function shortTime(value?: string): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false })
}

function goPortrait(personIdValue?: string) {
  if (!personIdValue) return
  void router.push(`/portrait/${encodeURIComponent(personIdValue)}`)
}

/* ------------------------------ 快捷键与离开守卫 ------------------------------ */

function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  const tagName = target?.tagName || ''
  const mod = event.ctrlKey || event.metaKey

  if (mod && event.key === 'Enter') {
    event.preventDefault()
    if (view.value === 'entry') void submit()
    else void approveCurrent()
    return
  }
  if (mod && (event.key === 's' || event.key === 'S')) {
    event.preventDefault()
    if (view.value === 'entry') saveDraft(true)
    return
  }
  if (event.altKey && event.key === 'ArrowLeft') {
    event.preventDefault()
    moveTask(-1)
    return
  }
  if (event.altKey && event.key === 'ArrowRight') {
    event.preventDefault()
    moveTask(1)
    return
  }
  if (event.altKey && (event.key === 'r' || event.key === 'R')) {
    event.preventDefault()
    if (view.value === 'entry') resetForm()
    return
  }
  if (event.key === '?' && !['INPUT', 'TEXTAREA'].includes(tagName)) {
    event.preventDefault()
    shortcutVisible.value = true
  }
}

onBeforeRouteLeave((to, from) => {
  if (to.path === from.path || submitting.value || reviewing.value) return true
  if (!isDirty.value) return true
  return ElMessageBox.confirm(
    '当前标注尚未提交，离开将丢失已填内容（可先用 Ctrl+S 暂存到本地）。',
    '离开确认',
    { type: 'warning', confirmButtonText: '仍要离开', cancelButtonText: '留下继续' },
  )
    .then(() => true)
    .catch(() => false)
})

/* ------------------------------ 监听与生命周期 ------------------------------ */

let lastQueueKey = ''
watch(
  () => `${view.value}|${statusFilter.value}|${templateFilter.value}|${page.value}`,
  (key) => {
    const previous = lastQueueKey.split('|')
    const current = key.split('|')
    const filtersChanged =
      lastQueueKey === '' || previous[0] !== current[0] || previous[1] !== current[1] || previous[2] !== current[2]
    lastQueueKey = key
    if (filtersChanged) {
      currentTask.value = null
      clearQueueSelection()
    }
    void loadQueue()
  },
  { immediate: true },
)

watch([selectedTemplate, personId], () => {
  hasDraftTip.value = ''
  if (selectedTemplate.value && personId.value.trim()) restoreDraft()
})

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  void loadTemplates()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mb-12 { margin-bottom: 12px; }
.mt-8 { margin-top: 8px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; }
.card-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.card-actions { display: flex; gap: 8px; justify-content: flex-end; flex-wrap: wrap; }
.filters { display: flex; gap: 6px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }
.view-tools { display: flex; gap: 6px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
.batch-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 8px;
  border: 1px solid var(--ob-primary, #2563eb);
  border-radius: var(--ob-radius-md, 8px);
  background: #eff6ff;
  flex-wrap: wrap;
}
.batch-actions { display: flex; gap: 6px; }
.queue-card :deep(.el-card__body) { padding: 12px; }
.queue-table { width: 100%; }
.hint { font-size: 12px; color: #9ca3af; line-height: 1.6; margin-top: 4px; }
.field-mapping { color: #6b7280; }
.field-slot { width: 100%; }
.subject-search { display: flex; gap: 8px; width: 100%; }
.recent { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
.recent-tag { cursor: pointer; }
.draft-tip {
  margin: 0 0 12px 104px;
  padding: 6px 10px;
  font-size: 12px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
}
.tip-list { list-style: none; margin: 0; padding: 0; font-size: 13px; line-height: 1.9; color: var(--ob-text-secondary); }
.subject-name { font-size: 18px; font-weight: 600; color: var(--ob-text-primary); }
.subject-id { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 12px; color: var(--ob-text-secondary); margin: 2px 0 8px; }
.subject-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.recent-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.recent-list__title { font-size: 13px; color: var(--ob-text-primary); }
.reason-title { margin-bottom: 6px; }
.reason-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.reason-tag { cursor: pointer; }
.review-buttons { display: flex; gap: 8px; margin-top: 12px; }
.timeline-title { font-size: 13px; color: var(--ob-text-primary); }
.pager { display: flex; justify-content: flex-end; margin-top: 10px; }
</style>
