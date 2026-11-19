<template>
  <PageContainer
    title="评分口径一致性"
    description="画像模板 × 标注模板的评分口径体检（只读，v2.13.0）"
    test-id="dps-scoring-consistency-page"
  >
    <div class="page-toolbar">
      <el-input
        v-model="categoryCode"
        placeholder="分类 code（可选）"
        style="width: 200px"
        data-test="scoring-category"
      />
      <el-switch v-model="onlyActive" active-text="仅 active" data-test="scoring-only-active" />
      <el-button type="primary" :loading="loading" data-test="scoring-refresh" @click="load(0)">刷新</el-button>
      <el-button data-test="scoring-export" @click="exportReport">导出 JSON</el-button>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb-16"
      :title="`口径：${report?.basis || '—'}`"
      data-test="scoring-basis"
    />

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
    </el-alert>

    <div class="ob-metrics">
      <div class="metric">
        <div class="metric-num">{{ report?.scanned?.templates ?? 0 }}</div>
        <div class="metric-label">画像模板</div>
      </div>
      <div class="metric">
        <div class="metric-num">{{ report?.scanned?.annotation_templates ?? 0 }}</div>
        <div class="metric-label">标注模板</div>
      </div>
      <div class="metric">
        <div class="metric-num">{{ report?.scanned?.fields ?? 0 }}</div>
        <div class="metric-label">字段数</div>
      </div>
      <div class="metric">
        <div class="metric-num danger">{{ report?.summary?.block ?? 0 }}</div>
        <div class="metric-label">阻断（BLOCK）</div>
      </div>
      <div class="metric">
        <div class="metric-num">{{ report?.summary?.warn ?? 0 }}</div>
        <div class="metric-label">告警（WARN）</div>
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="report?.issues || []"
      stripe
      empty-text="评分口径一致，未发现问题"
      data-test="scoring-issues"
    >
      <el-table-column label="级别" width="90">
        <template #default="{ row }">
          <el-tag :type="row.severity === 'BLOCK' ? 'danger' : 'warning'" size="small">{{ row.severity }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="code" label="问题码" width="210" />
      <el-table-column prop="portrait_template" label="画像模板" min-width="130" show-overflow-tooltip />
      <el-table-column prop="annotation_template" label="标注模板" min-width="130" show-overflow-tooltip />
      <el-table-column prop="tag_code" label="标签" min-width="150" show-overflow-tooltip />
      <el-table-column prop="message" label="说明" min-width="260" show-overflow-tooltip />
    </el-table>

    <el-pagination
      class="mt-12"
      layout="total, prev, pager, next"
      :page-size="pageSize"
      :current-page="page + 1"
      :total="report?.pagination?.total || 0"
      data-test="scoring-pagination"
      @current-change="onPageChange"
    />
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { dpsApi, type DpsScoringConsistencyReport } from '@/core/api/dps'
import { useAsyncState } from '@/core/composables/useAsyncState'

const categoryCode = ref('')
const onlyActive = ref(true)
const page = ref(0)
const pageSize = ref(20)
const report = ref<DpsScoringConsistencyReport | null>(null)

const { loading, error, run } = useAsyncState<unknown>()

const summaryText = computed(() => {
  const byCode = report.value?.summary?.by_code || {}
  return Object.entries(byCode)
    .map(([code, count]) => `${code}×${count}`)
    .join('、')
})

async function load(nextPage = 0) {
  page.value = nextPage
  const result = (await run(() =>
    dpsApi.getScoringConsistency({
      category_code: categoryCode.value || undefined,
      only_active: onlyActive.value,
      limit: pageSize.value,
      offset: page.value * pageSize.value,
    }),
  )) as DpsScoringConsistencyReport | null
  report.value = result
}

function onPageChange(current: number) {
  void load(current - 1)
}

function exportReport() {
  const payload = {
    exported_at: new Date().toISOString(),
    filters: { category_code: categoryCode.value || null, only_active: onlyActive.value },
    summary_text: summaryText.value,
    report: report.value,
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'dps-scoring-consistency.json'
  anchor.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  void load(0)
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-12 { margin-top: 12px; }
.ob-metrics { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px; }
.metric { border: 1px solid var(--ob-border); border-radius: var(--ob-radius-md); padding: 12px; text-align: center; }
.metric-num { font-size: 26px; font-weight: 600; }
.danger { color: var(--el-color-danger, #f56c6c); }
.metric-label { font-size: 12px; color: var(--ob-text-secondary); margin-top: 4px; }
@media (max-width: 900px) {
  .ob-metrics { grid-template-columns: repeat(2, 1fr); }
}
</style>
