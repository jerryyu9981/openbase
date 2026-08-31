<template>
  <div>
    <el-row :gutter="16" class="mb-16">
      <el-col :span="8">
        <el-card shadow="hover" data-test="dps-kpi">
          <div class="kpi-label">画像总数</div>
          <div class="kpi-value">{{ overview.total ?? '-' }}</div>
          <div class="kpi-sub">报表概览</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" data-test="dps-kpi">
          <div class="kpi-label">高风险画像</div>
          <div class="kpi-value">{{ overview.risk_high ?? '-' }}</div>
          <div class="kpi-sub">风险等级=high</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" data-test="dps-kpi">
          <div class="kpi-label">上游健康度</div>
          <div class="kpi-value">{{ health.status || '-' }}</div>
          <div class="kpi-sub">DPS v{{ health.version || '?' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索画像（姓名/ID 模糊）" clearable style="width: 240px" data-test="dps-search" />
      <el-button type="primary" data-test="dps-create" @click="$router.push('/portrait/search')">画像查询</el-button>
      <el-button :loading="loading" @click="loadData">刷新</el-button>
    </div>
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      @close="errorMessage = ''"
    >
      <template #default>
        <el-button link type="primary" size="small" @click="loadData">点击重试</el-button>
      </template>
    </el-alert>
    <div class="ob-table-scroll">
      <el-table v-loading="loading" :data="filtered" stripe data-test="portrait-table">
        <el-table-column prop="name" label="画像名称" min-width="160" />
        <el-table-column prop="person_id" label="画像 ID" min-width="180" show-overflow-tooltip />
        <el-table-column label="标签" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="t in (row.tags || [])" :key="String(t)" size="small" class="tag-item" type="info">{{ t }}</el-tag>
            <span v-if="!(row.tags || []).length" class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="风险等级" width="110">
          <template #default="{ row }">
            <el-tag :type="riskType(row.risk_level)" size="small">{{ riskLabel(row.risk_level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/portrait/${row.person_id || row.id}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && filtered.length === 0" description="暂无画像数据" :image-size="60" />
    </div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        background
        @current-change="loadData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { dpsApi, type DpsPortrait } from '@/core/api/dps'

const portraits = ref<DpsPortrait[]>([])
const overview = ref<Record<string, unknown>>({})
const health = ref<{ status?: string; version?: string }>({})
const keyword = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')

const filtered = computed(() => {
  if (!keyword.value) return portraits.value
  const kw = keyword.value.toLowerCase()
  return portraits.value.filter(
    (p) => String(p.name ?? '').toLowerCase().includes(kw) || String(p.person_id ?? '').toLowerCase().includes(kw),
  )
})

function riskLabel(level?: string) {
  if (!level) return '未知'
  return { low: '低', medium: '中', high: '高' }[level] || level
}

function riskType(level?: string) {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = { low: 'success', medium: 'warning', high: 'danger' }
  return map[level || ''] || 'info'
}

function formatTime(v?: string) {
  if (!v) return '-'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('zh-CN', { hour12: false })
}

async function loadHealth() {
  try {
    health.value = await dpsApi.getDpsHealth()
  } catch {
    health.value = { status: '不可达' }
  }
}

async function loadOverview() {
  try {
    overview.value = await dpsApi.getReportsOverview()
  } catch {
    overview.value = {}
  }
}

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await dpsApi.listPortraits({ page: page.value, page_size: pageSize })
    portraits.value = result.items || []
    total.value = result.total ?? 0
  } catch (err) {
    errorMessage.value = `画像列表加载失败：${(err as Error).message || '网络错误'}`
  } finally {
    loading.value = false
  }
  void loadHealth()
  void loadOverview()
}

onMounted(() => {
  void loadData()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.kpi-label { font-size: 13px; color: #6b7280; }
.kpi-value { font-size: 24px; font-weight: 600; margin: 4px 0; }
.kpi-sub { font-size: 12px; color: #9ca3af; }
.tag-item { margin-right: 4px; }
.text-muted { color: #9ca3af; }
.pager { display: flex; justify-content: flex-end; margin-top: 12px; }
</style>
