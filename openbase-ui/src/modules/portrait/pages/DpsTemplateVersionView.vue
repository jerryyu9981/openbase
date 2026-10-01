<template>
  <div class="dps-version">
    <div class="page-toolbar">
      <el-input v-model="code" placeholder="模板 code" style="width: 220px" data-test="version-code" />
      <el-select v-model="fromVersion" placeholder="版本 A" style="width: 130px" data-test="version-from">
        <el-option v-for="v in versionOptions" :key="`a-${v}`" :label="`v${v}`" :value="v" />
      </el-select>
      <span class="muted">⇄</span>
      <el-select v-model="toVersion" placeholder="版本 B" style="width: 130px" data-test="version-to">
        <el-option v-for="v in versionOptions" :key="`b-${v}`" :label="`v${v}`" :value="v" />
      </el-select>
      <el-button type="primary" :disabled="!canCompare" data-test="version-compare" @click="compare">对比</el-button>
    </div>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="compare">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card header="差异（分组呈现）" class="mb-16">
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="changes" stripe empty-text="暂无可对比差异" data-test="diff-table">
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="changeTagType(row.change_type)" size="small">{{ changeLabel(row.change_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="path" label="字段 / 维度" min-width="200" />
          <el-table-column label="版本 A" min-width="140">
            <template #default="{ row }">{{ formatValue(row.before) }}</template>
          </el-table-column>
          <el-table-column label="版本 B" min-width="140">
            <template #default="{ row }">{{ formatValue(row.after) }}</template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无可对比差异" :image-size="60" data-test="diff-empty" />
          </template>
        </el-table>
      </div>
    </el-card>

    <el-card header="执行回滚（写操作 · 需 portrait_template:update）" class="mb-16">
      <el-form label-width="90px">
        <el-form-item label="目标版本">
          <el-select v-model="rollbackTarget" placeholder="选择目标版本" style="width: 160px" data-test="rollback-target">
            <el-option v-for="v in versionOptions" :key="`rb-${v}`" :label="`v${v}`" :value="v" />
          </el-select>
        </el-form-item>
        <el-form-item label="回滚原因">
          <el-input v-model="rollbackReason" placeholder="如：误改维度权重" data-test="rollback-reason" />
        </el-form-item>
      </el-form>
      <el-button type="danger" plain :disabled="!rollbackTarget" data-test="rollback-open" @click="openRollback">回滚到目标版本…</el-button>
    </el-card>

    <el-alert v-if="rollbackResult" type="success" show-icon :closable="false" class="mb-16" data-test="rollback-result">
      <template #title>回滚已完成</template>
      <div>
        当前版本 v{{ rollbackResult.new_version ?? '-' }}（回滚至内容等价 v{{ rollbackResult.rolled_back_to ?? '-' }}）；
        等价性自检 {{ rollbackResult.equivalence_check ? '通过' : '未通过' }}。
      </div>
    </el-alert>

    <!-- 二次确认四要素 -->
    <el-dialog v-model="rollbackOpen" title="确认回滚" width="560px" data-test="rollback-dialog">
      <ol class="confirm-list">
        <li><b>目标版本：v{{ rollbackTarget }}</b>（当前 v{{ toVersion }}）</li>
        <li class="mt-8">
          <b>影响面摘要</b>：受影响标注模板 <b>{{ impact.annotation_template_count ?? 0 }}</b> ／
          标注 <b>{{ impact.annotation_count ?? 0 }}</b> ／ 标签 <b>{{ impact.tag_count ?? 0 }}</b>
          <div class="basis">
            <el-button link type="primary" size="small" :aria-expanded="basisAria" data-test="basis-trigger" @click="toggleBasis()">
              <span class="caret">{{ basisExpanded ? '▾' : '▸' }}</span> 口径（basis）
            </el-button>
            <div v-if="basisExpanded" class="basis-content" data-test="basis-content">
              tag_count 口径：<code>tag_lineage.template_code = code</code> 的 distinct <code>tag_code</code> 数（未联动过则为 0）。
              <div v-if="basisForced" class="forced">※ 标签数为 0 → 强制展开口径，避免误判为缺陷。</div>
            </div>
          </div>
        </li>
        <li class="mt-8"><span class="danger">⚠ 该操作不可撤销</span></li>
        <li class="mt-8">主按钮文案固定为「<b>确认回滚</b>」（不使用「确定」等模糊措辞）</li>
      </ol>
      <template #footer>
        <el-button data-test="rollback-cancel" @click="rollbackOpen = false">取消</el-button>
        <el-button type="danger" :loading="submitting" data-test="rollback-confirm" @click="doRollback">确认回滚</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  dpsApi,
  type DpsImpactResult,
  type DpsPortraitTemplate,
  type DpsRollbackResult,
  type DpsTemplateDiff,
  type DpsTemplateDiffEntry,
} from '@/core/api/dps'
import { describeDpsError } from '@/core/api/error'
import { useAsyncState } from '@/core/composables/useAsyncState'
import { useBasisTooltip } from '@/core/composables/useBasisTooltip'

const route = useRoute()
const code = ref(String(route.params.code || ''))
const currentVersion = ref(1)
const fromVersion = ref<number | null>(null)
const toVersion = ref<number>(1)
const changes = ref<DpsTemplateDiffEntry[]>([])
const impact = ref<DpsImpactResult>({})
const rollbackTarget = ref<number | null>(null)
const rollbackReason = ref('')
const rollbackOpen = ref(false)
const submitting = ref(false)
const rollbackResult = ref<DpsRollbackResult | null>(null)

const { loading, error, run } = useAsyncState<unknown>()

const versionOptions = computed(() => {
  const options: number[] = []
  for (let v = currentVersion.value; v >= 1; v -= 1) options.push(v)
  return options
})
const canCompare = computed(() => !!code.value && fromVersion.value !== null && toVersion.value !== null && fromVersion.value !== toVersion.value)

const tagCount = computed(() => impact.value.tag_count ?? 0)
const {
  isExpanded: basisExpanded,
  isForced: basisForced,
  ariaExpanded: basisAria,
  toggle: toggleBasis,
} = useBasisTooltip(() => tagCount.value === 0)

function changeLabel(type?: string): string {
  return { create: '新增', update: '修改', delete: '删除' }[type || ''] || (type || '变更')
}
function changeTagType(type?: string): 'success' | 'warning' | 'danger' | 'info' {
  if (type === 'create') return 'success'
  if (type === 'update') return 'warning'
  if (type === 'delete') return 'danger'
  return 'info'
}
function formatValue(value: unknown): string {
  if (value === undefined || value === null || value === '') return '—'
  return typeof value === 'string' ? value : JSON.stringify(value)
}

async function loadMeta() {
  const template = (await run(() => dpsApi.getTemplate(code.value))) as DpsPortraitTemplate | null
  if (template) {
    currentVersion.value = template.version ?? 1
    fromVersion.value = currentVersion.value
    toVersion.value = Math.max(1, currentVersion.value - 1)
  }
}

async function compare() {
  const result = (await run(() => dpsApi.diffVersions(code.value, fromVersion.value as number, toVersion.value))) as DpsTemplateDiff | null
  changes.value = result?.changes ?? []
}

async function loadImpact() {
  const result = await dpsApi.queryImpact({ template_code: code.value }).catch(() => ({}) as DpsImpactResult)
  impact.value = result
}

function openRollback() {
  rollbackOpen.value = true
  void loadImpact()
}

async function doRollback() {
  if (!rollbackTarget.value) return
  submitting.value = true
  try {
    rollbackResult.value = await dpsApi.rollbackTemplate(code.value, {
      target_version: rollbackTarget.value,
      reason: rollbackReason.value || undefined,
    })
    ElMessage.success('回滚已完成，正在验证生效结果')
    rollbackOpen.value = false
    await loadMeta()
    await compare()
  } catch (caught) {
    const presentation = describeDpsError(caught)
    ElMessage.error(presentation.hint || presentation.title)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await loadMeta()
  if (code.value) await compare()
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.mb-16 { margin-bottom: 16px; }
.mt-8 { margin-top: 8px; }
.muted { color: var(--ob-text-secondary); }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.confirm-list { margin: 0 0 0 18px; padding: 0; }
.danger { color: var(--ob-danger); }
.basis { margin-top: 6px; }
.basis-content { color: var(--ob-text-secondary); font-size: 12px; margin-top: 6px; }
.forced { color: var(--ob-warning); }
.caret { margin-right: 2px; }
</style>
