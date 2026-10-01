<template>
  <div class="dps-tag-system">
    <el-alert type="info" show-icon :closable="false" class="mb-16" data-test="tag-readonly-tip">
      <template #title>本页为只读呈现：分类 → 标签值两层结构</template>
      <div>分类的增删改沿用既有「标签分类」能力（/tags/categories），本页不复制编辑入口。</div>
    </el-alert>

    <el-alert type="warning" show-icon :closable="false" class="mb-16" data-test="tag-subtag-tip">
      <template #title>子标签／标签层级当前不提供</template>
      <div>DPS 实现暂无 parent_tag_code 落库 ⇒ 本版不呈现子标签、不做伪功能（已登记跨仓需求）。</div>
    </el-alert>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="load">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <div class="grid-2">
      <el-card :header="`标签分类 tag_category · ${categories.length} 条`">
        <div class="ob-table-scroll">
          <el-table
            v-loading="loading"
            :data="categories"
            stripe
            highlight-current-row
            empty-text="暂无标签分类"
            data-test="tag-category-table"
            @current-change="onSelectCategory"
          >
            <el-table-column prop="name" label="分类" min-width="160" />
            <el-table-column prop="description" label="说明" min-width="180" />
            <template #empty>
              <el-empty description="暂无标签分类" :image-size="60" data-test="tag-category-empty" />
            </template>
          </el-table>
        </div>
        <div class="muted sm mt-8">选中左侧分类 → 右侧展示其标签值（两层结构，无第三层）。</div>
      </el-card>

      <el-card :header="`标签值 tag_value${selectedCategory ? ` · 分类：${selectedCategory.name}` : ''}`">
        <div class="ob-table-scroll">
          <el-table :data="filteredLabels" stripe empty-text="暂无标签值" data-test="tag-value-table">
            <el-table-column prop="name" label="标签值" min-width="140" />
            <el-table-column prop="color" label="颜色" width="130">
              <template #default="{ row }">
                <el-tag v-if="row.color" size="small" :style="{ background: String(row.color), color: '#fff', border: 'none' }">{{ row.color }}</el-tag>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="sort_order" label="排序" width="90" />
            <template #empty>
              <el-empty
                :description="selectedCategory ? '该分类暂无标签值' : '请选择左侧分类'"
                :image-size="60"
                data-test="tag-value-empty"
              />
            </template>
          </el-table>
        </div>
        <div class="muted sm mt-8">标签值归属于分类（category_id 外键）。</div>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { dpsApi, type DpsTagCategory } from '@/core/api/dps'
import { describeDpsError, type DpsErrorPresentation } from '@/core/api/error'

interface LabelItem { name: string; color?: string; sort_order?: number; category?: string; category_id?: string; [key: string]: unknown }

const categories = ref<DpsTagCategory[]>([])
const labels = ref<LabelItem[]>([])
const selectedCategory = ref<DpsTagCategory | null>(null)
const loading = ref(false)
const error = ref<DpsErrorPresentation | null>(null)

const LINKAGE_RULES = [
  { field: 'cc-annot-intake · channel', dimension: 'service', tagCode: 'service:channel', scoring: 'enum 逆序线性：首项 100 → 末项 0' },
  { field: 'cc-annot-intake · score', dimension: 'service', tagCode: 'service:score', scoring: 'number 裁剪至 0~100' },
  { field: 'cc-annot-intake · tags', dimension: 'service', tagCode: 'service:tags', scoring: '其他有值类型默认 80' },
  { field: 'cc-annot-intake · visit_date', dimension: '—', tagCode: '不生成', scoring: '未声明 target_dimension ⇒ 不参与联动' },
]

const filteredLabels = computed(() => {
  if (!selectedCategory.value) return labels.value
  const target = selectedCategory.value
  return labels.value.filter((item) => {
    if (item.category_id && target.id) return String(item.category_id) === String(target.id)
    if (item.category) return String(item.category) === String(target.name)
    return true
  })
})

function onSelectCategory(row: DpsTagCategory | null) {
  selectedCategory.value = row
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
    labels.value = (labelResult.items || []).map((item) => {
      const record = item as Record<string, unknown>
      return {
        ...record,
        name: String(record.name ?? record.value ?? record.code ?? '-'),
        color: record.color ? String(record.color) : undefined,
        sort_order: typeof record.sort_order === 'number' ? record.sort_order : undefined,
      } as LabelItem
    })
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
.mt-16 { margin-top: 16px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
@media (max-width: 767px) {
  .grid-2 { grid-template-columns: 1fr; }
}
</style>
