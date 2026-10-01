<template>
  <div class="dps-lineage">
    <div class="page-toolbar">
      <el-input v-model="tagCode" placeholder="tag_code（如 service:channel）" style="width: 280px" data-test="lineage-tag" />
      <el-button type="primary" :loading="loading" data-test="lineage-run" @click="lookup">反查</el-button>
      <el-button :disabled="!sources.length" data-test="lineage-export" @click="exportResult">导出结果</el-button>
    </div>

    <!-- 无谱系（正常业务结果，非错误页） -->
    <el-empty
      v-if="notFound"
      description="未找到该标签的谱系（该标签尚未产生任何标注联动）"
      data-test="lineage-not-found"
    />

    <!-- 接口失败（异常） -->
    <el-alert v-else-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="lookup">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <div v-else class="grid-2">
      <el-card :header="`血缘来源（反查结果）· ${sources.length} 条`">
        <div class="ob-table-scroll">
          <el-table v-loading="loading" :data="sources" stripe empty-text="暂无血缘来源" data-test="lineage-table">
            <el-table-column prop="annotation_id" label="标注 ID" width="130" />
            <el-table-column prop="template_code" label="模板" min-width="160" />
            <el-table-column label="来源" min-width="180">
              <template #default="{ row }">
                <el-tag :type="row.source === 'ai_annotation' ? '' : 'info'" size="small">{{ row.source || '-' }}</el-tag>
                <span v-if="row.adapter_id" class="muted sm">adapter: {{ row.adapter_id }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" min-width="170" />
            <template #empty>
              <el-empty description="暂无血缘来源" :image-size="60" data-test="lineage-empty" />
            </template>
          </el-table>
        </div>
      </el-card>

      <el-card header="影响面统计">
        <div class="metrics-2">
          <div class="metric">
            <div class="metric-num">{{ impact.tag_count ?? 0 }}</div>
            <div class="metric-label">关联标签数（tag_count）</div>
          </div>
          <div class="metric">
            <div class="metric-num">{{ impact.profile_count ?? 0 }}</div>
            <div class="metric-label">关联画像数（profile_count）</div>
          </div>
        </div>
        <div class="basis">
          <el-button link type="primary" size="small" :aria-expanded="basisAria" data-test="basis-trigger" @click="toggleBasis()">
            <span class="caret">{{ basisExpanded ? '▾' : '▸' }}</span> 口径（basis）
          </el-button>
          <div v-if="basisExpanded" class="basis-content" data-test="basis-content">
            三层维度：template_code ／ annotation_template_code ／ tag_code；
            tag_count 谱系口径：未联动过则为 0。
            <div v-if="basisForced" class="forced">※ 标签数为 0 → 强制展开口径。</div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { dpsApi, type DpsImpactResult, type DpsLineageSource } from '@/core/api/dps'
import { useAsyncState } from '@/core/composables/useAsyncState'
import { useBasisTooltip } from '@/core/composables/useBasisTooltip'

const route = useRoute()
const tagCode = ref(String(route.query.tag_code || ''))
const impact = ref<DpsImpactResult>({})

const { data, loading, error, run } = useAsyncState<{ sources?: DpsLineageSource[] }>()

const sources = computed(() => data.value?.sources || [])
const notFound = computed(() => error.value?.kind === 'not-found')
const {
  isExpanded: basisExpanded,
  isForced: basisForced,
  ariaExpanded: basisAria,
  toggle: toggleBasis,
} = useBasisTooltip(() => (impact.value.tag_count ?? 0) === 0)

async function lookup() {
  if (!tagCode.value) return
  const result = await run(() => dpsApi.getTagLineage(tagCode.value))
  if (result || error.value?.kind === 'not-found') {
    impact.value = await dpsApi.queryImpact({ tag_code: tagCode.value }).catch(() => ({}) as DpsImpactResult)
  }
}

function exportResult() {
  const payload = { tag_code: tagCode.value, sources: sources.value, impact: impact.value }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `dps-lineage-${tagCode.value.replace(/[:/]/g, '_')}.json`
  anchor.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  if (tagCode.value) void lookup()
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.mb-16 { margin-bottom: 16px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.metrics-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.metric { border: 1px solid var(--ob-border); border-radius: var(--ob-radius-md); padding: 12px; text-align: center; }
.metric-num { font-size: 26px; font-weight: 600; }
.metric-label { font-size: 12px; color: var(--ob-text-secondary); margin-top: 4px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; margin-left: 6px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.basis-content { color: var(--ob-text-secondary); font-size: 12px; margin-top: 6px; }
.forced { color: var(--ob-warning); }
.caret { margin-right: 2px; }
@media (max-width: 767px) {
  .grid-2, .metrics-2 { grid-template-columns: 1fr; }
}
</style>
