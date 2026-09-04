<template>
  <div>
    <!-- TD-13-24 画像查询：多条件组合查询表单（真实 DPS 数据；维度对齐 profile 表实际字段） -->
    <el-card shadow="never" class="query-card mb-16" data-test="portrait-search-form">
      <el-form inline :model="queryForm" label-width="auto">
        <el-form-item label="关键字">
          <el-input v-model="queryForm.keyword" placeholder="姓名 / 画像 ID 模糊" clearable style="width: 200px" data-test="search-keyword" />
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="queryForm.risk" placeholder="全部" clearable style="width: 110px" data-test="search-risk">
            <el-option label="低" value="low" />
            <el-option label="中" value="mid" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>
        <el-form-item label="创建时间">
          <el-date-picker
            v-model="queryForm.createRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
            data-test="search-create-range"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" data-test="search-submit" @click="handleQuery">查询</el-button>
          <el-button data-test="search-reset" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
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

    <!-- 查询结果表格（加载态 + 空态） -->
    <div v-loading="loading" class="ob-table-scroll">
      <el-table :data="pagedRows" stripe data-test="portrait-search-table">
        <el-table-column prop="person_id" label="画像 ID" min-width="170" show-overflow-tooltip />
        <el-table-column prop="name" label="姓名" min-width="120" />
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
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsPortrait } from '@/core/api/dps'

interface QueryForm {
  keyword: string
  risk: string
  createRange: [string, string] | null
}

const queryForm = reactive<QueryForm>({ keyword: '', risk: '', createRange: null })
const loading = ref(false)
const queried = ref(false)
const errorMessage = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const rows = ref<DpsPortrait[]>([])

const filteredRows = computed(() => {
  if (!queried.value) return []
  const kw = queryForm.keyword.trim().toLowerCase()
  const risk = queryForm.risk
  const [start, end] = queryForm.createRange ?? [null, null]
  return rows.value.filter((row) => {
    if (kw) {
      const hit =
        String(row.name ?? '').toLowerCase().includes(kw) ||
        String(row.person_id ?? '').toLowerCase().includes(kw)
      if (!hit) return false
    }
    if (risk && !riskOf(row, risk)) return false
    const created = String(row.created_at ?? '').slice(0, 10)
    if (start && created < start) return false
    if (end && created > end) return false
    return true
  })
})

const pagedRows = computed(() => {
  const offset = (currentPage.value - 1) * pageSize.value
  return filteredRows.value.slice(offset, offset + pageSize.value)
})

/** 真实画像 risk_score（≥70 高 / ≥40 中 / 其余低），与画像列表口径一致 */
function scoreOf(row: DpsPortrait): number {
  const n = Number(row.risk_score ?? -1)
  return Number.isFinite(n) ? n : -1
}

function riskLabel(row: DpsPortrait): string {
  const v = scoreOf(row)
  if (v < 0) return '未知'
  if (v >= 70) return '高'
  if (v >= 40) return '中'
  return '低'
}

function riskType(row: DpsPortrait): 'success' | 'warning' | 'danger' | 'info' {
  const v = scoreOf(row)
  if (v < 0) return 'info'
  if (v >= 70) return 'danger'
  if (v >= 40) return 'warning'
  return 'success'
}

function riskOf(row: DpsPortrait, band: string): boolean {
  const v = scoreOf(row)
  if (v < 0) return false
  if (band === 'high') return v >= 70
  if (band === 'mid') return v >= 40 && v < 70
  return v < 40
}

function formatTime(v?: string): string {
  if (!v) return '-'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v.slice(0, 10) : d.toLocaleString('zh-CN', { hour12: false })
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
    errorMessage.value = `画像查询失败：${(err as Error).message || '网络错误'}`
  } finally {
    loading.value = false
  }
}

function handleReset() {
  queryForm.keyword = ''
  queryForm.risk = ''
  queryForm.createRange = null
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
.table-pagination { margin-top: 12px; justify-content: flex-end; }
</style>
