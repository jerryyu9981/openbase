<template>
  <PageContainer title="标签体系" description="标签分类 → 标签值两层结构，可下钻血缘与评分命中" test-id="dps-tag-system-view-page">
    <el-alert type="info" show-icon :closable="false" class="mb-16" data-test="tag-readonly-tip">
      <template #title>本页为只读呈现：分类 → 标签值两层结构</template>
      <div>分类的增删改沿用既有「标签分类管理」能力（/portrait/tags），本页不复制编辑入口。</div>
    </el-alert>

    <el-alert type="warning" show-icon :closable="false" class="mb-16" data-test="tag-subtag-tip">
      <template #title>子标签／标签层级当前不提供</template>
      <div>DPS 实现暂无 parent_tag_code 落库 ⇒ 本版不呈现子标签、不做伪功能（已登记 A9 跨仓需求）。</div>
    </el-alert>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="load">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <div class="page-toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索分类 / 标签 / 说明"
        clearable
        style="width: 260px"
        data-test="tag-search"
        @keyup.enter="queryLabelsByKeyword"
      />
      <el-button data-test="tag-category-manage" @click="goCategoryManage">标签分类管理</el-button>
      <el-button type="primary" plain data-test="tag-lineage-nav" @click="openLineage()">标签血缘</el-button>
      <el-button :loading="loading" data-test="tag-refresh" @click="load">刷新</el-button>
      <span class="muted sm">共 {{ categories.length }} 个分类 / {{ labels.length }} 个标签值（A9 服务端检索）</span>
    </div>

    <div class="grid-2">
      <el-card :header="`标签树 tag_category · ${categories.length} 条`">
        <div class="tree-wrap" data-test="tag-category-table">
          <el-empty v-if="!treeNodes.length" description="暂无标签分类" :image-size="60" data-test="tag-category-empty" />
          <el-tree
            v-else
            :data="filteredTree"
            node-key="key"
            default-expand-all
            :expand-on-click-node="false"
            highlight-current
            empty-text="无匹配分类或标签"
            @node-click="onNodeClick"
          >
            <template #default="{ data }">
              <span class="tree-node" :class="{ 'tree-node--active': data.key === activeKey }">
                <span v-if="data.color" class="color-dot" :style="{ background: String(data.color) }" />
                <span class="tree-name">{{ data.name }}</span>
                <el-tag v-if="data.kind === 'label'" size="small" type="success">标签</el-tag>
                <el-tag v-else size="small" type="info">{{ (data.children || []).length }} 个标签</el-tag>
                <span v-if="data.code" class="muted sm">{{ data.code }}</span>
              </span>
            </template>
          </el-tree>
        </div>
        <div class="muted sm mt-8">选中左侧标签 → 右侧展示定义、产出模板、最近标注与评分命中。</div>
      </el-card>

      <el-card :header="detailHeader">
        <el-empty v-if="!selectedNode || selectedNode.kind !== 'label'" description="请选择左侧标签查看详情" :image-size="60" data-test="tag-detail-empty" />
        <template v-else>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="标签值">{{ selectedNode.name }}</el-descriptions-item>
            <el-descriptions-item label="tag_code">
              <span v-if="selectedTagCode">{{ selectedTagCode }}</span>
              <span v-else class="muted">—（无 code）</span>
            </el-descriptions-item>
            <el-descriptions-item label="所属分类">{{ selectedNode.categoryName || '未分类' }}</el-descriptions-item>
            <el-descriptions-item label="排序">{{ selectedNode.sortOrder ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="颜色">
              <el-tag v-if="selectedNode.color" size="small" :style="{ background: String(selectedNode.color), color: '#fff', border: 'none' }">
                {{ selectedNode.color }}
              </el-tag>
              <span v-else class="muted">—</span>
            </el-descriptions-item>
            <el-descriptions-item label="说明">{{ selectedNode.description || '—' }}</el-descriptions-item>
          </el-descriptions>

          <div class="detail-actions">
            <el-button type="primary" size="small" :disabled="!selectedTagCode" data-test="tag-lineage-open" @click="openLineage()">
              血缘反查
            </el-button>
            <el-button size="small" :disabled="!selectedTagCode" data-test="tag-code-copy" @click="copyTagCode">复制标签码</el-button>
          </div>
          <div v-if="!selectedTagCode" class="muted sm">
            该标签无 tag_code，无法反查血缘；标签检索与 code 回填依赖 A9（待后端）。
          </div>

          <el-alert v-if="detailError" type="error" show-icon :closable="false" class="mt-12" data-test="tag-detail-error">
            <template #title>{{ detailError.title }}</template>
            <div>{{ detailError.detail }}</div>
          </el-alert>

          <div v-loading="detailLoading" class="detail-body">
            <div class="section-title">产出模板 / 最近标注</div>
            <el-table :data="detailSources" stripe size="small" empty-text="暂无标注来源" data-test="tag-source-table">
              <el-table-column prop="template_code" label="画像模板" min-width="150" show-overflow-tooltip />
              <el-table-column prop="source" label="来源" width="130">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.source === 'ai_annotation' ? '' : 'info'">{{ row.source || '-' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="annotation_id" label="标注 ID" min-width="130" show-overflow-tooltip />
              <el-table-column prop="created_at" label="时间" min-width="160">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
            </el-table>

            <div class="metrics-2 mt-12">
              <div class="metric">
                <div class="metric-num">{{ detailImpact.tag_count ?? 0 }}</div>
                <div class="metric-label">关联标签数</div>
              </div>
              <div class="metric">
                <div class="metric-num">{{ detailImpact.profile_count ?? 0 }}</div>
                <div class="metric-label">关联画像数</div>
              </div>
            </div>

            <div class="section-title">评分命中</div>
            <el-empty
              v-if="!detailHits.length"
              :description="detailLoaded ? '未命中评分项（或模板血缘不可用）' : '选择标签后加载'"
              :image-size="50"
              data-test="tag-scoring-empty"
            />
            <el-table v-else :data="detailHits" size="small" data-test="tag-scoring-table">
              <el-table-column prop="dimension" label="维度" width="120" />
              <el-table-column prop="rule_key" label="评分规则" min-width="180" show-overflow-tooltip />
              <el-table-column prop="weight" label="权重" width="80" />
              <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
            </el-table>

            <div v-for="group in detailGroups" :key="group.templateCode" class="chain-line">
              <el-tag size="small" type="info">{{ group.templateName || group.templateCode }}</el-tag>
              <span v-if="group.missingField" class="muted sm">未找到产出该标签的字段（血缘缺口）</span>
              <span v-else class="muted sm">
                {{ group.fields.length }} 个字段 ·
                {{ group.fields.reduce((total, field) => total + field.scoringHits.length, 0) }} 个评分命中
              </span>
            </div>
          </div>
        </template>
      </el-card>
    </div>

    <el-card header="标注字段 → 画像标签 联动口径（只读说明）" class="mt-16">
      <el-table :data="LINKAGE_RULES" stripe data-test="tag-linkage-table">
        <el-table-column prop="field" label="标注模板 · 字段" min-width="190" />
        <el-table-column prop="dimension" label="target_dimension" width="160" />
        <el-table-column label="生成 tag_code" width="230">
          <template #default="{ row }"><el-tag size="small">{{ row.tagCode }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="scoring" label="评分口径" min-width="230" />
      </el-table>
      <div class="muted sm mt-8">
        人工标注优先（人工值覆盖自动计算结果）；联动落库为 profile_tag，并可经标签血缘反查追溯来源。
      </div>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  dpsApi,
  type DpsImpactResult,
  type DpsLineageScoringHit,
  type DpsLineageSource,
  type DpsTagCategory,
} from '@/core/api/dps'
import { describeDpsError, type DpsErrorPresentation } from '@/core/api/error'
import {
  buildTagTree,
  filterTagTree,
  normalizeTagLabel,
  resolveTagCode,
  type TagLabelItem,
  type TagTreeNode,
} from '@/modules/portrait/tags/tagTree'
import {
  buildTagChainGroups,
  collectScoringHits,
  type TagChainGroup,
} from '@/modules/portrait/lineage/lineageChain'

const router = useRouter()

const categories = ref<DpsTagCategory[]>([])
const labels = ref<TagLabelItem[]>([])
const keyword = ref('')
const loading = ref(false)
const error = ref<DpsErrorPresentation | null>(null)

const selectedNode = ref<TagTreeNode | null>(null)
const detailLoading = ref(false)
const detailError = ref<DpsErrorPresentation | null>(null)
const detailSources = ref<DpsLineageSource[]>([])
const detailImpact = ref<DpsImpactResult>({})
const detailGroups = ref<TagChainGroup[]>([])
const detailLoaded = ref(false)

const LINKAGE_RULES = [
  { field: 'cc-annot-intake · channel', dimension: 'service', tagCode: 'service:channel', scoring: 'enum 逆序线性：首项 100 → 末项 0' },
  { field: 'cc-annot-intake · score', dimension: 'service', tagCode: 'service:score', scoring: 'number 裁剪至 0~100' },
  { field: 'cc-annot-intake · tags', dimension: 'service', tagCode: 'service:tags', scoring: '其他有值类型默认 80' },
  { field: 'cc-annot-intake · visit_date', dimension: '—', tagCode: '不生成', scoring: '未声明 target_dimension ⇒ 不参与联动' },
]

const treeNodes = computed(() => buildTagTree(categories.value, labels.value))
const filteredTree = computed(() => filterTagTree(treeNodes.value, keyword.value))
const selectedTagCode = computed(() => resolveTagCode(selectedNode.value))
const activeKey = computed(() => selectedNode.value?.key || '')
const detailHeader = computed(() => {
  const node = selectedNode.value
  if (!node) return '标签详情'
  return node.kind === 'label' ? `标签详情 · ${node.name}` : `标签详情 · 分类 ${node.name}`
})
const detailHits = computed<DpsLineageScoringHit[]>(() => collectScoringHits(detailGroups.value))

function formatTime(value?: string): string {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

function onNodeClick(node: TagTreeNode) {
  selectedNode.value = node
  if (node.kind !== 'label') return
  void loadLabelDetail(node)
}

async function loadLabelDetail(node: TagTreeNode) {
  detailSources.value = []
  detailImpact.value = {}
  detailGroups.value = []
  detailError.value = null
  detailLoaded.value = false
  const tagCode = resolveTagCode(node)
  if (!tagCode) {
    detailLoaded.value = true
    return
  }
  detailLoading.value = true
  try {
    const result = await dpsApi.getTagLineage(tagCode)
    detailSources.value = result.sources || []
    detailLoaded.value = true
    detailImpact.value = await dpsApi
      .queryImpact({ tag_code: tagCode })
      .catch(() => ({}) as DpsImpactResult)
    const templateCodes = Array.from(
      new Set(detailSources.value.map((source) => String(source.template_code || '')).filter(Boolean)),
    )
    const lineages = await Promise.all(
      templateCodes.map((code) => dpsApi.getTemplateLineage(code).catch(() => null)),
    )
    detailGroups.value = buildTagChainGroups(tagCode, detailSources.value, lineages)
  } catch (caught) {
    const described = describeDpsError(caught)
    detailLoaded.value = true
    if (described.kind !== 'not-found') detailError.value = described
  } finally {
    detailLoading.value = false
  }
}

function openLineage() {
  if (!selectedTagCode.value) {
    ElMessage.info('请先选择带 tag_code 的标签，或前往血缘页手动输入')
    void router.push('/portrait/dps/lineage')
    return
  }
  void router.push({ path: '/portrait/dps/lineage', query: { tag: selectedTagCode.value } })
}

function goCategoryManage() {
  void router.push('/portrait/tags')
}

async function copyTagCode() {
  const code = selectedTagCode.value
  if (!code) return
  try {
    await navigator.clipboard?.writeText(code)
    ElMessage.success(`已复制 ${code}`)
  } catch {
    ElMessage.info(`标签码：${code}`)
  }
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const [categoryResult, labelResult] = await Promise.all([
      dpsApi.listTagCategories(),
      dpsApi.listLabels(),
    ])
    categories.value = categoryResult.items || []
    labels.value = (labelResult.items || []).map((item) => normalizeTagLabel(item))
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    loading.value = false
  }
}

/** A9：关键字检索优先走服务端扁平标签检索；DPS 未升级（404）时回退全量 + 本地过滤 */
async function queryLabelsByKeyword() {
  const kw = keyword.value.trim()
  if (!kw) {
    await load()
    return
  }
  loading.value = true
  error.value = null
  try {
    try {
      const result = await dpsApi.listTags({ keyword: kw, page: 1, page_size: 100 })
      labels.value = result.items.map((item) =>
        normalizeTagLabel({
          name: item.value,
          code: item.value_id,
          color: item.color,
          sort_order: item.order_num,
          category: item.category_name,
          category_id: item.category_id,
        }),
      )
    } catch (caught) {
      if ((caught as { response?: { status?: number } })?.response?.status !== 404) throw caught
      const labelResult = await dpsApi.listLabels()
      labels.value = (labelResult.items || []).map((item) => normalizeTagLabel(item))
    }
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-8 { margin-top: 8px; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.tree-wrap { min-height: 260px; max-height: 520px; overflow: auto; }
.tree-node { display: inline-flex; align-items: center; gap: 6px; }
.tree-node--active .tree-name { font-weight: 600; color: var(--el-color-primary); }
.tree-name { font-size: 13px; }
.color-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.detail-actions { display: flex; gap: 8px; margin-top: 12px; }
.detail-body { margin-top: 12px; }
.section-title { font-size: 13px; font-weight: 600; margin: 14px 0 8px; color: var(--ob-text-primary); }
.metrics-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.metric { border: 1px solid var(--ob-border); border-radius: var(--ob-radius-md); padding: 10px; text-align: center; }
.metric-num { font-size: 22px; font-weight: 600; }
.metric-label { font-size: 12px; color: var(--ob-text-secondary); margin-top: 4px; }
.chain-line { display: flex; align-items: center; gap: 8px; padding: 4px 0; }
@media (max-width: 767px) {
  .grid-2 { grid-template-columns: 1fr; }
}
</style>
