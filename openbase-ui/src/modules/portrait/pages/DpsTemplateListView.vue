<template>
  <PageContainer title="模板族管理" description="画像模板族列表与新建入口" test-id="dps-template-list-view-page">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索模板族名称 / code" clearable style="width: 240px" data-test="template-search" />
      <el-select v-model="statusFilter" placeholder="状态：全部" clearable style="width: 140px" data-test="template-status-filter">
        <el-option label="active" value="active" />
        <el-option label="inactive" value="inactive" />
        <el-option label="draft" value="draft" />
      </el-select>
      <el-button type="primary" data-test="template-query" @click="load">查询</el-button>
      <el-button data-test="template-reset" @click="resetFilters">重置</el-button>
      <el-button type="primary" plain data-test="template-new" @click="router.push('/portrait/dps/templates/new')">新建模板</el-button>
    </div>

    <el-alert
      v-if="error"
      type="error"
      show-icon
      :closable="false"
      class="mb-16"
      data-test="dps-error"
    >
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="load">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card header="模板族">
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="filteredItems" stripe empty-text="暂无模板族" data-test="template-table">
          <el-table-column prop="code" label="模板族" min-width="180" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ row.status || 'draft' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="版本" width="90">
            <template #default="{ row }">{{ formatVersion(row.version) }}</template>
          </el-table-column>
          <el-table-column prop="profile_type" label="profile_type" width="140" />
          <el-table-column prop="subject_type" label="subject_type" width="140" />
          <el-table-column label="操作" width="350" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="template-workbench" @click="router.push(`/portrait/dps/templates/${row.code}/edit`)">工作台</el-button>
              <el-button link type="primary" size="small" data-test="template-detail" @click="openDetail(row.code)">详情</el-button>
              <el-button link type="primary" size="small" data-test="template-versions" @click="router.push(`/portrait/dps/templates/${row.code}/versions`)">查看对比</el-button>
              <el-button link type="primary" size="small" data-test="template-preflight" @click="router.push(`/portrait/dps/templates/${row.code}/preflight`)">预检</el-button>
              <el-popconfirm
                :title="row.status === 'active' ? '确认停用该模板？' : '确认启用该模板？'"
                @confirm="toggleStatus(row)"
              >
                <template #reference>
                  <el-button link :type="row.status === 'active' ? 'danger' : 'success'" size="small" data-test="template-toggle">
                    {{ row.status === 'active' ? '停用' : '启用' }}
                  </el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无模板族" :image-size="60" data-test="template-empty" />
          </template>
        </el-table>
      </div>
    </el-card>

    <el-drawer v-model="detailOpen" title="模板族详情" size="860px" data-test="template-detail-drawer">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="code">{{ detail?.code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ detail?.status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="name">{{ detail?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="version">{{ formatVersion(detail?.version) }}</el-descriptions-item>
        <el-descriptions-item label="profile_type">{{ detail?.profile_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="subject_type">{{ detail?.subject_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="extends">{{ detail?.extends || '—（无继承）' }}</el-descriptions-item>
        <el-descriptions-item label="description">{{ detail?.description || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div class="mt-12">
        <el-button size="small" @click="router.push(`/portrait/dps/templates/${detail?.code}/versions`)">查看对比</el-button>
        <el-button size="small" @click="router.push(`/portrait/dps/templates/${detail?.code}/preflight`)">预检</el-button>
        <el-button size="small" data-test="template-edit" @click="router.push(`/portrait/dps/templates/${detail?.code}/edit`)">工作台</el-button>
        <el-button size="small" @click="router.push(`/portrait/dps/templates/${detail?.code}/raw`)">JSON 编辑</el-button>
      </div>

      <div v-loading="lineageLoading" class="mt-16">
        <el-alert
          v-if="lineage?.gaps?.items?.length"
          type="warning"
          show-icon
          :closable="false"
          class="mb-12"
          data-test="template-lineage-gaps"
        >
          <template #title>发现 {{ (lineage?.gaps?.items || []).length }} 项配置缺口</template>
          <div v-for="item in lineage?.gaps?.items || []" :key="`${item.type}-${item.code || ''}`" class="gap-line">
            {{ item.message }}
          </div>
        </el-alert>

        <el-tabs v-model="detailTab" data-test="template-lineage-tabs">
          <!-- ① 族谱 -->
          <el-tab-pane label="族谱" name="lineage" data-test="template-tab-lineage">
            <el-empty v-if="!lineage?.lineage?.length" description="暂无族谱数据" :image-size="48" />
            <div v-else class="lineage-chain">
              <div
                v-for="node in lineage?.lineage || []"
                :key="node.code"
                class="lineage-node"
                :class="{ current: node.current }"
                data-test="template-lineage-node"
              >
                <el-tag size="small" :type="node.current ? 'success' : 'info'">
                  {{ node.current ? '当前模板' : `父级 ${node.depth}` }}
                </el-tag>
                <span class="lineage-code">{{ node.code }}</span>
                <span class="muted sm">{{ node.name }}</span>
                <el-tag size="small" :type="statusTagType(node.status)">{{ node.status || 'draft' }}</el-tag>
              </div>
              <div class="muted sm mt-8">
                继承口径：父维度先入 → 子覆盖同名 → 追加新维度；深度上限 2 层。
              </div>
            </div>
          </el-tab-pane>

          <!-- ② 标注模板 -->
          <el-tab-pane label="标注模板" name="annotations" data-test="template-tab-annotations">
            <el-table :data="lineage?.annotation_templates || []" size="small" empty-text="暂无标注模板">
              <el-table-column prop="code" label="标注模板" min-width="180" />
              <el-table-column label="归属画像模板" min-width="170">
                <template #default="{ row }">
                  <span>{{ row.owned_by || '-' }}</span>
                  <el-tag
                    v-if="row.owned_by && row.owned_by !== lineage?.template_code"
                    size="small"
                    type="warning"
                    class="ml-6"
                    data-test="template-ownership-mismatch-tag"
                  >
                    归属不一致
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="当前模板绑定维度" min-width="150">
                <template #default="{ row }">
                  <span v-if="row.bound_to_current">{{ (row.bound_dimensions || []).join('、') || '-' }}</span>
                  <span v-else class="muted">未绑定</span>
                </template>
              </el-table-column>
              <el-table-column label="标签产出" width="100">
                <template #default="{ row }">{{ (row.tag_outputs || []).length }}</template>
              </el-table-column>
              <el-table-column label="缺口" width="120">
                <template #default="{ row }">
                  <el-tag v-if="row.unbound" size="small" type="danger" data-test="template-unbound-tag">未绑定</el-tag>
                  <span v-else class="muted sm">—</span>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="lineage?.gaps?.bound_annotation_templates_missing?.length" class="muted sm mt-8">
              绑定了不存在的标注模板：{{ (lineage?.gaps?.bound_annotation_templates_missing || []).join('、') }}
            </div>
          </el-tab-pane>

          <!-- ③ 标签产出 -->
          <el-tab-pane label="标签产出" name="tags" data-test="template-tab-tags">
            <el-table :data="tagRows" size="small" empty-text="当前模板绑定的标注模板没有标签产出">
              <el-table-column prop="annotation" label="标注模板" min-width="170" />
              <el-table-column prop="tag_code" label="标签（dimension:tag_key）" min-width="190" />
              <el-table-column prop="field_key" label="字段" min-width="140" />
              <el-table-column label="评分项命中" min-width="240">
                <template #default="{ row }">
                  <span v-if="row.hits.length" class="hit-text">
                    <span v-for="hit in row.hits" :key="hit.rule_key" class="hit-item">
                      {{ hit.rule_key }}（权重 {{ hit.weight }}）
                    </span>
                  </span>
                  <el-tag v-else size="small" type="warning" data-test="template-tag-only-tag">仅标签·不影响评分</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- ④ 评分项 -->
          <el-tab-pane label="评分项" name="scoring" data-test="template-tab-scoring">
            <el-empty v-if="!scoring" description="模板未激活，无运行时评分口径" :image-size="48" />
            <template v-else>
              <div class="muted sm mb-8">
                共 {{ scoring?.dimension_count }} 个维度 / {{ scoring?.rule_count }} 条规则；缺值按 50 分计。
              </div>
              <el-alert
                v-if="scoring?.dimensions_without_annotation_source?.length"
                type="warning"
                show-icon
                :closable="false"
                class="mb-12"
                data-test="template-scoring-gap"
                :title="`以下维度暂无标注来源：${(scoring?.dimensions_without_annotation_source || []).join('、')}`"
              />
              <div v-for="dim in scoring?.dimensions || []" :key="dim.code" class="scoring-dim">
                <div class="scoring-dim-head">
                  <strong>{{ dim.name }}</strong>
                  <span class="muted sm">{{ dim.code }} · 权重 {{ dim.weight }}</span>
                  <el-tag v-if="dim.source_gap" size="small" type="danger" data-test="template-dimension-gap-tag">无标注来源</el-tag>
                  <el-tag v-for="source in dim.annotation_sources || []" :key="source" size="small" type="success">
                    来源 {{ source }}
                  </el-tag>
                </div>
                <el-table :data="dim.rules" size="small">
                  <el-table-column prop="tag_key" label="tag_key" min-width="150" />
                  <el-table-column prop="description" label="说明" min-width="160" show-overflow-tooltip />
                  <el-table-column prop="type" label="类型" width="120" />
                  <el-table-column prop="weight" label="权重" width="80" />
                  <el-table-column label="缺值" width="80">
                    <template #default>50</template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsPortraitTemplate, type DpsTemplateLineage } from '@/core/api/dps'
import { describeDpsError } from '@/core/api/error'
import { useAsyncState } from '@/core/composables/useAsyncState'
import { formatVersion } from '@/modules/portrait/version'

const router = useRouter()
const keyword = ref('')
const statusFilter = ref('')
const detailOpen = ref(false)
const detail = ref<DpsPortraitTemplate | null>(null)
const detailTab = ref('lineage')
const lineage = ref<DpsTemplateLineage | null>(null)
const lineageLoading = ref(false)

const { data, loading, error, run } = useAsyncState<{ items: DpsPortraitTemplate[]; total?: number }>()

const filteredItems = computed(() => {
  const items = data.value?.items || []
  if (!keyword.value) return items
  const kw = keyword.value.toLowerCase()
  return items.filter((item) => String(item.code || '').toLowerCase().includes(kw) || String(item.name || '').toLowerCase().includes(kw))
})

/** 标签产出行（标签 → 字段 → 命中评分项），供第三页签平铺展示 */
const scoring = computed(() => lineage.value?.scoring || null)
const tagRows = computed(() =>
  (lineage.value?.annotation_templates || []).flatMap((view) =>
    view.tag_outputs.map((output) => ({
      annotation: view.code,
      tag_code: output.tag_code,
      field_key: output.field_key,
      hits: view.scoring_hits.filter((hit) => hit.tag_code === output.tag_code),
    })),
  ),
)

function statusTagType(status?: string | null): 'success' | 'info' | 'warning' {
  if (status === 'active') return 'success'
  if (status === 'inactive') return 'info'
  return 'warning'
}

async function load() {
  await run(() => dpsApi.listTemplates({ status: statusFilter.value || undefined }))
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = ''
  void load()
}

async function openDetail(code: string) {
  detailOpen.value = true
  detail.value = null
  lineage.value = null
  detailTab.value = 'lineage'
  lineageLoading.value = true
  try {
    const [template, lineageData] = await Promise.all([
      dpsApi.getTemplate(code),
      dpsApi.getTemplateLineage(code),
    ])
    detail.value = template
    lineage.value = lineageData
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    lineageLoading.value = false
  }
}

async function toggleStatus(row: DpsPortraitTemplate) {
  const next = row.status === 'active' ? 'inactive' : 'active'
  try {
    if (row.status === 'active') await dpsApi.deactivateTemplate(row.code)
    else await dpsApi.activateTemplate(row.code)
    ElMessage.success(`模板已${next === 'active' ? '启用' : '停用'}`)
    await load()
  } catch (caught) {
    const presentation = describeDpsError(caught)
    ElMessage.error(presentation.hint || presentation.title)
    // 幂等：失败后就地刷新，保持列表与实际状态一致
    await load()
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mb-12 { margin-bottom: 12px; }
.mb-8 { margin-bottom: 8px; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }
.mt-8 { margin-top: 8px; }
.ml-6 { margin-left: 6px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; }
.gap-line { font-size: 12px; line-height: 1.7; color: var(--ob-text-secondary); }
.lineage-chain { display: flex; flex-direction: column; gap: 8px; }
.lineage-node { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border: 1px solid var(--ob-border, #e5e7eb); border-radius: 8px; }
.lineage-node.current { border-color: var(--ob-primary); background: var(--ob-primary-lighter, #f8fbff); }
.lineage-code { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 13px; }
.scoring-dim { margin-bottom: 14px; }
.scoring-dim-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.hit-text { display: inline-flex; flex-direction: column; gap: 2px; font-size: 12px; }
</style>
