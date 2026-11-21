<template>
  <PageContainer title="关系总览" description="模板分类 → 复合模板 → 子模板 → 标注项 → 画像实例：五层引用关系与快速跳转" test-id="portrait-relation-view-page">
    <template #actions>
      <span v-if="lastUpdatedText" class="updated-at" data-test="relation-updated-at">统计时间 {{ lastUpdatedText }}</span>
      <el-button :loading="loading" title="重新拉取五层实时数量" data-test="relation-refresh" @click="load">刷新</el-button>
    </template>

    <el-alert
      v-if="error"
      type="error"
      show-icon
      :closable="false"
      class="mb-16"
      data-test="relation-error"
    >
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="relation-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="relation-retry" @click="load">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="relation-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <div class="relation-tips" data-test="relation-tips">
      <span class="tips-dot" aria-hidden="true" />
      <span>点击任意卡片进入对应页面（支持 Enter / 空格键）；数量为实时统计，口径见页面底部「数据说明」。</span>
    </div>

    <el-card shadow="never" class="mapping-card" data-test="relation-tag-mapping">
      <template #header>
        <div class="mapping-header">
          <span class="mapping-title">标签分类 → 标注模板映射</span>
          <el-tag size="small" :type="mappingEnabled ? 'success' : 'info'" effect="plain" data-test="relation-mapping-status">
            {{ mappingEnabled ? '校验已启用' : '未启用校验' }}
          </el-tag>
          <el-button link type="primary" size="small" data-test="relation-manage-tags" @click="router.push('/portrait/tags')">
            管理标签分类
          </el-button>
        </div>
      </template>
      <p class="mapping-summary">
        标注模板共使用 {{ mappingRows.length }} 个维度，已映射 {{ mappingRows.length - unmappedCount }} 个<template v-if="unmappedCount">，<span class="mapping-warning">{{ unmappedCount }} 个未映射</span></template>。
      </p>
      <el-table :data="mappingRows" size="small" data-test="relation-mapping-table">
        <el-table-column label="维度编码" width="150">
          <template #default="{ row }"><code class="mapping-code">{{ row.dimension }}</code></template>
        </el-table-column>
        <el-table-column label="标签分类" min-width="150">
          <template #default="{ row }">
            <span v-if="row.categoryName">{{ row.categoryName }}</span>
            <span v-else class="text-muted">未映射</span>
          </template>
        </el-table-column>
        <el-table-column label="使用该维度的标注模板" min-width="280">
          <template #default="{ row }">{{ row.templates.join('、') }}</template>
        </el-table-column>
        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <el-tag size="small" :type="row.mapped ? 'success' : 'danger'" effect="plain">{{ row.mapped ? '已映射' : '未映射' }}</el-tag>
          </template>
        </el-table-column>
        <template #empty>
          <span class="text-muted">暂无配置 target_dimension 的标注项</span>
        </template>
      </el-table>
      <p class="mapping-foot">
        校验口径：只要有一个标签分类配置了维度编码，保存标注模板时每个 target_dimension 都必须能映射到分类；全部未配置时放行存量模板。
      </p>
    </el-card>

    <div v-loading="loading" class="relation-flow" data-test="relation-flow">
      <template v-for="(layer, index) in layers" :key="layer.key">
        <el-card
          shadow="never"
          class="relation-card"
          role="link"
          tabindex="0"
          :aria-label="`${layer.title}：${layer.action}`"
          :title="`点击进入${layer.action}`"
          :data-test="`relation-layer-${layer.key}`"
          @click="go(layer)"
          @keydown.enter.prevent="go(layer)"
          @keydown.space.prevent="go(layer)"
        >
          <div class="layer-head">
            <span class="layer-index">{{ index + 1 }}</span>
            <span class="layer-stage">{{ layer.stage }}</span>
            <el-tag size="small" effect="plain">{{ layer.tag }}</el-tag>
          </div>
          <div class="layer-body">
            <div class="layer-main">
              <h3 class="layer-title">{{ layer.title }}</h3>
              <p class="layer-desc">{{ layer.description }}</p>
              <p class="layer-hint">{{ layer.hint }}</p>
            </div>
            <div class="layer-metric">
              <div class="metric-value" :data-test="`relation-count-${layer.key}`">{{ layer.count }}</div>
              <div class="metric-label">{{ layer.countLabel }}</div>
            </div>
          </div>
          <div class="layer-actions">
            <el-button
              type="primary"
              plain
              size="small"
              :data-test="`relation-link-${layer.key}`"
              @click.stop="go(layer)"
            >
              {{ layer.action }}
            </el-button>
            <code class="layer-path">{{ layer.to }}</code>
            <span v-if="layer.empty" class="layer-empty">暂无数据，进入后可新建</span>
          </div>
        </el-card>
        <div v-if="index < layers.length - 1" class="relation-edge" data-test="relation-edge">
          <span class="edge-line" aria-hidden="true" />
          <span class="edge-label">{{ layer.edge }}</span>
          <span class="edge-desc">{{ layer.edgeDesc }}</span>
        </div>
      </template>
    </div>

    <el-card shadow="never" class="relation-notes" data-test="relation-notes">
      <template #header>
        <span class="notes-title">数据说明</span>
      </template>
      <dl class="notes-list">
        <div class="notes-item">
          <dt>模板分类（{{ noteCount(counts.templateCategoryCount) }}）</dt>
          <dd>三级分类树节点总数（数字画像 / 人物画像 / 业务画像 / 具体画像）；模板只能绑定第 3 层分类。</dd>
        </div>
        <div class="notes-item">
          <dt>复合模板 / 子模板（{{ noteCount(counts.compositeTemplateCount) }} / {{ noteCount(counts.componentTemplateCount) }}）</dt>
          <dd>按 <code>template_kind</code> 区分：复合模板由子模板挂载组成；子模板为可复用的维度单元，不参与再次挂载。</dd>
        </div>
        <div class="notes-item">
          <dt>标注项（{{ formatCount(counts.fieldCount) }}）</dt>
          <dd>各标注模板 <code>field_schema</code> 中的字段条数之和；同一字段被多个模板复用时分别计数，因此可能大于去重后的字段种类数。</dd>
        </div>
        <div class="notes-item">
          <dt>标注模板（{{ noteCount(counts.annotationTemplateCount) }}）</dt>
          <dd>DPS 标注模板总数，包含草稿与启用状态；每个模板须归属一个画像模板。</dd>
        </div>
        <div class="notes-item">
          <dt>画像实例（{{ noteCount(counts.portraitCount) }}）</dt>
          <dd>画像列表中的实例总数，按实体 <code>person_id</code> 统计；同一实体在不同模板口径下可能对应多条结果。</dd>
        </div>
      </dl>
      <p class="notes-foot">
        数据来源：DPS 标注模板、模板族与画像列表接口。页面加载或点击「刷新」时实时统计；显示「—」表示明细接口暂不可用，显示 0 表示尚未创建。
      </p>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { dpsApi } from '@/core/api/dps'
import { useAsyncState } from '@/core/composables/useAsyncState'

interface DimensionMappingRow {
  dimension: string
  categoryName: string
  templates: string[]
  mapped: boolean
}

interface RelationCounts {
  fieldCount: number | null
  templateCategoryCount: number
  compositeTemplateCount: number
  componentTemplateCount: number
  annotationTemplateCount: number
  profileTemplateCount: number
  portraitCount: number
  configuredDimensions: string[]
  mappingRows: DimensionMappingRow[]
}

const router = useRouter()
const { data, loading, error, run } = useAsyncState<RelationCounts>(() => false)

const counts = computed<RelationCounts>(() => data.value ?? {
  fieldCount: null,
  templateCategoryCount: 0,
  compositeTemplateCount: 0,
  componentTemplateCount: 0,
  annotationTemplateCount: 0,
  profileTemplateCount: 0,
  portraitCount: 0,
  configuredDimensions: [],
  mappingRows: [],
})

const mappingRows = computed(() => data.value?.mappingRows ?? [])
const mappingEnabled = computed(() => (data.value?.configuredDimensions.length ?? 0) > 0)
const unmappedCount = computed(() => mappingRows.value.filter((row) => !row.mapped).length)

function formatCount(value: number | null): string {
  return value === null ? '—' : String(value)
}

function noteCount(value: number): string {
  return data.value ? String(value) : '—'
}

const lastUpdatedAt = ref<Date | null>(null)
const lastUpdatedText = computed(() => lastUpdatedAt.value
  ? lastUpdatedAt.value.toLocaleTimeString('zh-CN', { hour12: false })
  : '')

function go(layer: { to: string }) {
  void router.push(layer.to)
}

const layers = computed(() => [
  {
    key: 'template-category',
    stage: '目录层',
    tag: '分类',
    title: '模板分类',
    description: '三级目录树：数字画像 → 人物画像/业务画像 → 具体画像，用于归集全部模板。',
    hint: '模板只能绑定第 3 层分类；第 4 层会被拒绝。',
    count: formatCount(counts.value.templateCategoryCount),
    countLabel: '分类节点数',
    empty: counts.value.templateCategoryCount === 0,
    to: '/portrait/dps/templates',
    action: '进入模板族管理',
    edge: '归类出',
    edgeDesc: '分类节点下归集复合模板与子模板',
  },
  {
    key: 'profile-template',
    stage: '定义层',
    tag: '复合',
    title: '复合模板',
    description: '由若干子模板挂载组成的画像模板，如「社区矫正对象全景画像基础模板」。',
    hint: '挂载变更会升父模板版本并写入快照，历史画像按原快照回放。',
    count: formatCount(counts.value.compositeTemplateCount),
    countLabel: '复合模板数',
    empty: counts.value.compositeTemplateCount === 0,
    to: '/portrait/dps/templates',
    action: '进入模板族管理',
    edge: '挂载',
    edgeDesc: '复合模板按顺序挂载多个子模板，可设置必挂与权重覆盖',
  },
  {
    key: 'component-template',
    stage: '定义层',
    tag: '子模板',
    title: '子模板',
    description: '可独立维护、可被多个复合模板复用的模板单元，对应原六维之一。',
    hint: '子模板只参与组合，不能再挂载其他模板，避免循环。',
    count: formatCount(counts.value.componentTemplateCount),
    countLabel: '子模板数',
    empty: counts.value.componentTemplateCount === 0,
    to: '/portrait/dps/templates',
    action: '进入模板族管理',
    edge: '被标注',
    edgeDesc: '标注模板按维度编码映射到子模板，产出标签与评分项',
  },
  {
    key: 'field',
    stage: '定义层',
    tag: '原子',
    title: '标注项',
    description: '字段、标签或评分点的最小定义，存放在标注模板的 field_schema 中。',
    hint: `来自 ${noteCount(counts.value.annotationTemplateCount)} 个标注模板；不单独建页，随所属标注模板维护。`,
    count: formatCount(counts.value.fieldCount),
    countLabel: '标注项（字段）总数',
    empty: counts.value.fieldCount === 0,
    to: '/portrait/dps/annotation-templates',
    action: '查看标注模板',
    edge: '计算生成',
    edgeDesc: '按模板版本对实体数据计算，产出画像结果快照',
  },
  {
    key: 'portrait',
    stage: '运行层',
    tag: '快照',
    title: '画像实例',
    description: '某个实体（person_id）在某个模板版本下的计算结果，可按画像码检索。',
    hint: '列表默认展示画像名称，画像码作为次要信息单独展示。',
    count: formatCount(counts.value.portraitCount),
    countLabel: '画像实例数',
    empty: counts.value.portraitCount === 0,
    to: '/portrait/list',
    action: '进入画像列表',
    edge: '',
    edgeDesc: '',
  },
])

async function load() {
  await run(async () => {
    const [annotationTemplates, profileTemplates, portraits, tagCategories, templateCategories] = await Promise.all([
      dpsApi.listAnnotationTemplates({ page: 1, page_size: 100 }),
      dpsApi.listTemplates({ page: 1, page_size: 100 }),
      dpsApi.listPortraits({ page: 1, page_size: 1 }),
      dpsApi.listTagCategories().catch(() => ({ items: [] })),
      dpsApi.listTemplateCategories().catch(() => []),
    ])

    const profileTemplateItems = profileTemplates.items ?? []
    const compositeTemplateCount = profileTemplateItems
      .filter((item) => (item.template_kind ?? 'composite') !== 'component').length
    const componentTemplateCount = profileTemplateItems
      .filter((item) => item.template_kind === 'component').length

    const annotationItems = annotationTemplates.items ?? []
    const templateCodes = annotationItems.map((item) => item.code).filter(Boolean)
    let fieldCount: number | null = null
    const details = templateCodes.length > 0
      ? await Promise.all(templateCodes.map((code) => dpsApi.getAnnotationTemplate(code).catch(() => null)))
      : []
    if (details.length > 0 && details.every((detail) => detail !== null)) {
      fieldCount = details.reduce((total, detail) => total + (detail?.field_schema?.length ?? 0), 0)
    }

    const categoryByDimension = new Map<string, string>()
    for (const category of tagCategories.items ?? []) {
      const dimension = String(category.dimension_code ?? '').trim()
      if (dimension) {
        categoryByDimension.set(dimension, String(category.name ?? category.id ?? ''))
      }
    }

    const usage = new Map<string, Set<string>>()
    for (const detail of details) {
      if (!detail) continue
      const templateName = String(detail.name || detail.code)
      for (const field of detail.field_schema ?? []) {
        const dimension = String(field.target_dimension ?? '').trim()
        if (!dimension) continue
        if (!usage.has(dimension)) usage.set(dimension, new Set())
        usage.get(dimension)?.add(templateName)
      }
    }

    const mappingRows: DimensionMappingRow[] = [...usage.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([dimension, templates]) => ({
        dimension,
        categoryName: categoryByDimension.get(dimension) ?? '',
        templates: [...templates],
        mapped: categoryByDimension.has(dimension),
      }))

    return {
      fieldCount,
      templateCategoryCount: templateCategories.length,
      compositeTemplateCount,
      componentTemplateCount,
      annotationTemplateCount: annotationTemplates.total ?? annotationItems.length,
      profileTemplateCount: profileTemplates.total ?? profileTemplateItems.length,
      portraitCount: portraits.total ?? (portraits.items?.length ?? 0),
      configuredDimensions: [...categoryByDimension.keys()].sort(),
      mappingRows,
    }
  })
  if (!error.value) {
    lastUpdatedAt.value = new Date()
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.mapping-card {
  max-width: 980px;
  margin-bottom: 16px;
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius-lg);
}

.mapping-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mapping-title {
  font-size: 14px;
  line-height: 20px;
  font-weight: 500;
  color: var(--ob-text);
}

.mapping-summary {
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-secondary);
}

.mapping-warning {
  color: var(--ob-danger);
}

.mapping-code {
  padding: 0 4px;
  border-radius: var(--ob-radius-sm);
  background: var(--ob-bg);
  font-size: 12px;
}

.mapping-foot {
  margin: 12px 0 0;
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-disabled);
}

.text-muted {
  color: var(--ob-text-disabled);
}

.relation-flow {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  max-width: 980px;
}

.updated-at {
  margin-right: 12px;
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-disabled);
}

.relation-tips {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 12px;
  border-radius: var(--ob-radius-md);
  background: var(--ob-bg);
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-secondary);
}

.tips-dot {
  flex: none;
  width: 6px;
  height: 6px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--ob-primary);
}

.relation-card {
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius-lg);
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.relation-card:hover {
  border-color: var(--ob-primary);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}

.relation-card:focus-visible {
  outline: 2px solid var(--ob-primary);
  outline-offset: 2px;
}

.relation-notes {
  max-width: 980px;
  margin-top: 24px;
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius-lg);
}

.notes-title {
  font-size: 14px;
  line-height: 20px;
  font-weight: 500;
  color: var(--ob-text);
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 0;
  padding: 0;
}

.notes-item {
  margin: 0;
}

.notes-item dt {
  font-size: 13px;
  line-height: 20px;
  font-weight: 500;
  color: var(--ob-text);
}

.notes-item dd {
  margin: 2px 0 0;
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-secondary);
}

.notes-item code {
  padding: 0 4px;
  border-radius: var(--ob-radius-sm);
  background: var(--ob-bg);
  font-size: 12px;
}

.notes-foot {
  margin: 16px 0 0;
  padding-top: 12px;
  border-top: 1px dashed var(--ob-border);
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-disabled);
}

.layer-empty {
  margin-left: auto;
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-disabled);
}

.layer-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.layer-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--ob-primary);
  color: #fff;
  font-size: 13px;
  line-height: 1;
}

.layer-stage {
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-secondary);
}

.layer-body {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}

.layer-main {
  min-width: 0;
}

.layer-title {
  margin: 0 0 6px;
  font-size: 16px;
  line-height: 24px;
  font-weight: 500;
  color: var(--ob-text);
}

.layer-desc {
  margin: 0 0 4px;
  font-size: 14px;
  line-height: 20px;
  color: var(--ob-text-secondary);
}

.layer-hint {
  margin: 0;
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-disabled);
}

.layer-metric {
  flex: none;
  min-width: 140px;
  text-align: right;
}

.metric-value {
  font-size: 24px;
  line-height: 32px;
  font-weight: 600;
  color: var(--ob-text);
  font-variant-numeric: tabular-nums;
}

.metric-label {
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-disabled);
}

.layer-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--ob-border);
}

.layer-path {
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-disabled);
}

.relation-edge {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 56px;
  padding-left: 32px;
}

.edge-line {
  width: 2px;
  height: 36px;
  flex: none;
  background: var(--ob-border);
}

.edge-label {
  font-size: 13px;
  line-height: 20px;
  font-weight: 500;
  color: var(--ob-primary);
}

.edge-desc {
  font-size: 12px;
  line-height: 18px;
  color: var(--ob-text-secondary);
}

@media (max-width: 768px) {
  .layer-body {
    flex-direction: column;
    gap: 8px;
  }

  .layer-metric {
    text-align: left;
  }
}
</style>
