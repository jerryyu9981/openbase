<template>
  <PageContainer title="画像搜索" description="高级检索：条件行可增删，结果关键字高亮（前端降级 A6）" test-id="portrait-search-page">
    <div class="page-toolbar">
      <el-button link type="primary" data-test="search-back" @click="$router.push('/portrait/list')">← 返回画像列表</el-button>
      <span class="muted sm">服务端检索（A6）未就绪：先取前 100 条画像在本地组合条件匹配。</span>
    </div>

    <!-- 高级检索：条件行 -->
    <el-card shadow="never" class="query-card mb-16" data-test="portrait-search-form">
      <div v-for="(condition, index) in conditions" :key="condition.id" class="condition-row" data-test="search-condition">
        <el-select v-model="condition.field" style="width: 150px" data-test="search-field">
          <el-option label="关键字" value="keyword" />
          <el-option label="风险等级" value="risk" />
          <el-option label="创建时间 ≥" value="created_after" />
          <el-option label="创建时间 ≤" value="created_before" />
        </el-select>
        <el-select
          v-if="condition.field === 'risk'"
          v-model="condition.value"
          placeholder="全部"
          clearable
          style="width: 130px"
          data-test="search-risk"
        >
          <el-option label="低" value="low" />
          <el-option label="中" value="mid" />
          <el-option label="高" value="high" />
        </el-select>
        <el-date-picker
          v-else-if="condition.field === 'created_after' || condition.field === 'created_before'"
          v-model="condition.value"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择日期"
          style="width: 170px"
          data-test="search-date"
        />
        <el-input
          v-else
          v-model="condition.value"
          placeholder="姓名 / 画像 ID 模糊"
          clearable
          style="width: 240px"
          :data-test="index === 0 ? 'search-keyword' : 'search-condition-keyword'"
        />
        <el-button
          link
          type="danger"
          :disabled="conditions.length === 1"
          data-test="search-condition-remove"
          @click="removeCondition(condition.id)"
        >
          移除
        </el-button>
      </div>
      <div class="condition-actions">
        <el-button size="small" data-test="search-condition-add" @click="addCondition">添加条件</el-button>
        <el-button type="primary" :loading="loading" data-test="search-submit" @click="handleQuery">查询</el-button>
        <el-button data-test="search-reset" @click="handleReset">重置</el-button>
      </div>
    </el-card>

    <!-- 错误态 -->
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="search-error"
      @close="errorMessage = ''"
    />

    <!-- 查询结果表格（加载态 + 空态 + 命中高亮） -->
    <div v-loading="loading" class="ob-table-scroll">
      <el-table :data="pagedRows" stripe data-test="portrait-search-table">
        <el-table-column label="画像名称" min-width="150">
          <template #default="{ row }">
            <span>
              <template v-for="(segment, index) in highlightSegments(row.name)" :key="`name-${index}`">
                <mark v-if="segment.hit" class="hl">{{ segment.text }}</mark>
                <span v-else>{{ segment.text }}</span>
              </template>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="画像码（person_id）" min-width="190" show-overflow-tooltip>
          <template #default="{ row }">
            <span>
              <template v-for="(segment, index) in highlightSegments(row.person_id || row.id)" :key="`pid-${index}`">
                <mark v-if="segment.hit" class="hl">{{ segment.text }}</mark>
                <span v-else>{{ segment.text }}</span>
              </template>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="风险等级" width="110">
          <template #default="{ row }">
            <el-tag :type="riskType(row)" size="small">{{ riskLabel(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="170">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="search-detail" @click="$router.push(`/portrait/${row.person_id || row.id}`)">详情</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty
            :description="queried ? '未找到匹配的画像，请调整查询条件后重试' : '请输入查询条件后点击「查询」'"
            :image-size="90"
            data-test="search-empty"
          />
        </template>
      </el-table>
    </div>

    <el-pagination
      v-if="filteredRows.length > 0"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="filteredRows.length"
      :page-sizes="[5, 10, 20]"
      layout="total, sizes, prev, pager, next, jumper"
      class="table-pagination"
      data-test="search-pagination"
    />
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsPortrait } from '@/core/api/dps'
import {
  formatDateTime,
  matchPortraitConditions,
  riskLabelOf,
  riskScoreOf,
  splitHighlight,
  type HighlightSegment,
  type PortraitCondition,
  type PortraitConditionField,
} from '@/modules/portrait/portrait/portraitTools'

interface ConditionRow extends PortraitCondition {
  id: string
}

let conditionSeq = 1
const conditions = ref<ConditionRow[]>([{ id: `c${conditionSeq}`, field: 'keyword', value: '' }])
const loading = ref(false)
const queried = ref(false)
const errorMessage = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const rows = ref<DpsPortrait[]>([])

const activeConditions = computed<PortraitCondition[]>(() =>
  conditions.value
    .filter((condition) => String(condition.value || '').trim())
    .map((condition) => ({ id: condition.id, field: condition.field, value: condition.value })),
)
const filteredRows = computed(() => (queried.value ? matchPortraitConditions(rows.value, activeConditions.value) : []))
const pagedRows = computed(() => {
  const offset = (currentPage.value - 1) * pageSize.value
  return filteredRows.value.slice(offset, offset + pageSize.value)
})
const primaryKeyword = computed(() => {
  const condition = conditions.value.find(
    (item) => item.field === 'keyword' && String(item.value || '').trim(),
  )
  return condition ? String(condition.value).trim() : ''
})

function riskLabel(row: DpsPortrait): string {
  return riskLabelOf(row)
}

function riskType(row: DpsPortrait): 'success' | 'warning' | 'danger' | 'info' {
  const value = riskScoreOf(row)
  if (value < 0) return 'info'
  if (value >= 70) return 'danger'
  if (value >= 40) return 'warning'
  return 'success'
}

function formatTime(value?: string): string {
  return formatDateTime(value)
}

function highlightSegments(text: unknown): HighlightSegment[] {
  return splitHighlight(String(text ?? ''), primaryKeyword.value)
}

function addCondition() {
  conditionSeq += 1
  conditions.value = [
    ...conditions.value,
    { id: `c${conditionSeq}`, field: 'keyword' as PortraitConditionField, value: '' },
  ]
}

function removeCondition(id: string) {
  if (conditions.value.length <= 1) return
  conditions.value = conditions.value.filter((condition) => condition.id !== id)
}

async function handleQuery() {
  errorMessage.value = ''
  loading.value = true
  currentPage.value = 1
  try {
    const result = await dpsApi.listPortraits({ page: 1, page_size: 100 })
    rows.value = result.items || []
    queried.value = true
    if (!rows.value.length) {
      ElMessage.warning('暂无画像数据可查询')
    } else {
      ElMessage.success(`查询完成，共匹配 ${filteredRows.value.length} 条画像`)
    }
  } catch (err) {
    queried.value = false
    rows.value = []
    errorMessage.value = `画像查询失败：${(err as Error).message || '网络错误'}`
  } finally {
    loading.value = false
  }
}

function handleReset() {
  conditionSeq = 1
  conditions.value = [{ id: 'c1', field: 'keyword', value: '' }]
  errorMessage.value = ''
  currentPage.value = 1
  rows.value = []
  queried.value = false
  ElMessage.info('查询条件已重置')
}
</script>

<style scoped>
.query-card :deep(.el-form-item) { margin-bottom: 6px; }
.mb-16 { margin-bottom: 16px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; }
.condition-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.condition-actions { display: flex; align-items: center; gap: 8px; }
.table-pagination { margin-top: 12px; justify-content: flex-end; }
.hl { background: #fde68a; color: inherit; padding: 0 1px; border-radius: 2px; }
</style>
