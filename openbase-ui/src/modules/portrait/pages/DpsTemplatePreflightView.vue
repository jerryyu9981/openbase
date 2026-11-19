<template>
  <PageContainer title="预检与影响面" description="变更前预检与影响面评估" test-id="dps-template-preflight-view-page">
    <div class="page-toolbar">
      <el-input v-model="code" placeholder="模板 code" style="width: 220px" data-test="preflight-code" />
      <el-button type="primary" :loading="loading" data-test="preflight-run" @click="runPreflight">执行预检</el-button>
      <el-button data-test="preflight-export" @click="exportReport">导出预检报告</el-button>
    </div>

    <el-alert type="info" show-icon :closable="false" class="mb-16" data-test="preflight-banner">
      <template #title>预检模式（不写入）</template>
      <div>本页所有操作<strong>不会写入</strong>，仅返回校验结果与影响面统计（template 与 package 预检同源口径）。</div>
    </el-alert>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="runPreflight">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card header="校验结果" class="mb-16">
      <el-table v-loading="loading" :data="checks" stripe empty-text="暂无校验结果" data-test="preflight-checks">
        <el-table-column prop="item" label="校验项" min-width="220" />
        <el-table-column label="结果" width="120">
          <template #default="{ row }">
            <el-tag :type="row.passed ? 'success' : 'danger'" size="small">{{ row.passed ? '通过' : '未通过' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="说明" min-width="240" />
        <template #empty>
          <el-empty description="暂无校验结果" :image-size="60" data-test="preflight-checks-empty" />
        </template>
      </el-table>
    </el-card>

    <el-card header="评分口径一致性（v2.13.0）" class="mb-16" data-test="preflight-scoring-consistency">
      <div class="ob-metrics scoring-metrics">
        <div class="metric">
          <div class="metric-num danger">{{ consistency.block }}</div>
          <div class="metric-label">阻断（BLOCK）</div>
        </div>
        <div class="metric">
          <div class="metric-num">{{ consistency.warn }}</div>
          <div class="metric-label">告警（WARN）</div>
        </div>
      </div>
      <el-alert
        v-if="consistency.error"
        type="warning"
        :closable="false"
        show-icon
        class="mb-12"
        :title="`一致性校验降级：${consistency.error}`"
        data-test="preflight-scoring-degraded"
      />
      <el-table
        :data="consistency.issues"
        size="small"
        stripe
        empty-text="评分口径一致，未发现问题"
        data-test="preflight-scoring-issues"
      >
        <el-table-column label="级别" width="90">
          <template #default="{ row }">
            <el-tag :type="row.severity === 'BLOCK' ? 'danger' : 'warning'" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="问题码" width="210" />
        <el-table-column prop="tag_code" label="标签" min-width="150" show-overflow-tooltip />
        <el-table-column prop="annotation_template" label="标注模板" min-width="140" show-overflow-tooltip />
        <el-table-column prop="message" label="说明" min-width="240" show-overflow-tooltip />
      </el-table>
      <div class="muted sm mt-8">BLOCK 将阻断模板激活；可通过 SCORING_CONSISTENCY_GATE=warn/off 临时降级。</div>
    </el-card>

    <el-card header="影响面（三项指标）">
      <el-radio-group v-model="dimension" class="mb-12" data-test="impact-dimension" @change="loadImpact">
        <el-radio-button value="template_code">按模板 template_code</el-radio-button>
        <el-radio-button value="annotation_template_code">按标注模板</el-radio-button>
        <el-radio-button value="tag_code">按标签 tag_code</el-radio-button>
      </el-radio-group>
      <el-input
        v-if="dimension !== 'template_code'"
        v-model="dimensionValue"
        :placeholder="dimension === 'tag_code' ? 'tag_code（如 service:channel）' : 'annotation_template_code'"
        style="width: 320px"
        class="mb-12"
        data-test="impact-dimension-value"
      />
      <el-button size="small" class="mb-12" data-test="impact-load" @click="loadImpact">查询影响面</el-button>

      <div class="ob-metrics">
        <div class="metric">
          <div class="metric-num">{{ metrics.annotation_template_count }}</div>
          <div class="metric-label">受影响标注模板数</div>
        </div>
        <div class="metric">
          <div class="metric-num">{{ metrics.annotation_count }}</div>
          <div class="metric-label">受影响标注数</div>
        </div>
        <div class="metric">
          <div class="metric-num">{{ metrics.tag_count }}</div>
          <div class="metric-label">受影响标签数</div>
        </div>
      </div>

      <div class="basis">
        <el-button link type="primary" size="small" :aria-expanded="basisAria" data-test="basis-trigger" @click="toggleBasis()">
          <span class="caret">{{ basisExpanded ? '▾' : '▸' }}</span> 口径（basis）
        </el-button>
        <div v-if="basisExpanded" class="basis-content" data-test="basis-content">
          annotation_template_count：annotation_template.template_code = code 的标注模板数；
          annotation_count：上述标注模板下 annotation.template_id 关联的标注数；
          tag_count：tag_lineage.template_code = code 的 distinct tag_code 数（谱系口径：未联动过则为 0）。
          <div v-if="basisForced" class="forced">※ 标签数为 0 → 强制展开口径，避免误判为缺陷。</div>
        </div>
      </div>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { dpsApi, type DpsImpactResult, type DpsPreflightResult } from '@/core/api/dps'
import { useAsyncState } from '@/core/composables/useAsyncState'
import { useBasisTooltip } from '@/core/composables/useBasisTooltip'

const route = useRoute()
const code = ref(String(route.params.code || ''))
const dimension = ref<'template_code' | 'annotation_template_code' | 'tag_code'>('template_code')
const dimensionValue = ref('')
const preflight = ref<DpsPreflightResult | null>(null)
const impact = ref<DpsImpactResult>({})

const { loading, error, run } = useAsyncState<unknown>()

const checks = computed(() => preflight.value?.checks || [])
const consistency = computed(
  () => preflight.value?.scoring_consistency || { block: 0, warn: 0, issues: [] },
)
const metrics = computed(() => ({
  annotation_template_count: impact.value.annotation_template_count ?? 0,
  annotation_count: impact.value.annotation_count ?? 0,
  tag_count: impact.value.tag_count ?? 0,
}))

const {
  isExpanded: basisExpanded,
  isForced: basisForced,
  ariaExpanded: basisAria,
  toggle: toggleBasis,
} = useBasisTooltip(() => metrics.value.tag_count === 0)

async function runPreflight() {
  if (!code.value) return
  const result = (await run(() => dpsApi.preflightTemplate(code.value))) as DpsPreflightResult | null
  preflight.value = result
  if (result?.impact) impact.value = result.impact
  else await loadImpact()
}

async function loadImpact() {
  const params =
    dimension.value === 'template_code'
      ? { template_code: code.value }
      : dimension.value === 'tag_code'
        ? { tag_code: dimensionValue.value }
        : { annotation_template_code: dimensionValue.value }
  // field_key 显式不支持（400）；未选维度值时按模板维度兜底，避免无意义请求
  if (dimension.value !== 'template_code' && !dimensionValue.value) return
  impact.value = await dpsApi.queryImpact(params).catch(() => ({}) as DpsImpactResult)
}

function exportReport() {
  const payload = { code: code.value, preflight: preflight.value, impact: impact.value }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `dps-preflight-${code.value || 'template'}.json`
  anchor.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  if (code.value) void runPreflight()
})
</script>

<style scoped>
.mb-12 { margin-bottom: 12px; }
.mb-16 { margin-bottom: 16px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.ob-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px; }
.metric { border: 1px solid var(--ob-border); border-radius: var(--ob-radius-md); padding: 12px; text-align: center; }
.scoring-metrics { grid-template-columns: repeat(2, minmax(0, 200px)); }
.danger { color: var(--el-color-danger, #f56c6c); }
.mt-8 { margin-top: 8px; }
.metric-num { font-size: 26px; font-weight: 600; }
.metric-label { font-size: 12px; color: var(--ob-text-secondary); margin-top: 4px; }
.basis-content { color: var(--ob-text-secondary); font-size: 12px; margin-top: 6px; }
.forced { color: var(--ob-warning); }
.caret { margin-right: 2px; }
@media (max-width: 767px) {
  .ob-metrics { grid-template-columns: 1fr; }
}
</style>
