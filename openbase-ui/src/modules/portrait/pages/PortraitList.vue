<template>
  <div>
    <el-result
      v-if="isForbidden"
      icon="error"
      :title="presentation?.title || ''"
      :sub-title="presentation?.detail || ''"
      data-test="isolation-forbidden"
    >
      <template #extra>
        <p v-if="presentation?.requestId" class="request-id" data-test="error-request-id">
          请求编号：{{ presentation.requestId }}
        </p>
        <el-button data-test="isolation-back" @click="$router.push('/dashboard')">返回仪表盘</el-button>
      </template>
    </el-result>

    <div v-else-if="isNotFound" data-test="isolation-not-found">
      <el-empty description="资源不存在或已被移除" />
    </div>

    <template v-else>
      <el-row :gutter="16" class="mb-16">
        <el-col :span="8">
          <el-card shadow="hover" data-test="dps-kpi">
            <div class="kpi-label">画像总数</div>
            <div class="kpi-value">{{ overview.total_profiles ?? overview.total ?? '-' }}</div>
            <div class="kpi-sub">报表概览（真实 DPS 数据）</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" data-test="dps-kpi">
            <div class="kpi-label">高风险画像</div>
            <div class="kpi-value">{{ overview.high_risk_count ?? overview.risk_high ?? '-' }}</div>
            <div class="kpi-sub">风险分 ≥ 70</div>
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
        v-if="showErrorBar"
        :title="errorMessage"
        type="error"
        show-icon
        closable
        class="mb-16"
        data-test="isolation-error-bar"
        @close="presentation = null"
      >
        <template #default>
          <el-button link type="primary" size="small" data-test="isolation-retry" @click="loadData">点击重试</el-button>
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
              <el-tag :type="riskType(row)" size="small">{{ riskLabel(row) }}</el-tag>
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
          <template #empty>
            <el-empty
              data-test="isolation-empty"
              :description="emptyDescription"
              :image-size="60"
            />
          </template>
        </el-table>
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { dpsApi, type DpsPortrait } from '@/core/api/dps'
import { describeError, type ErrorPresentation } from '@/core/api/error'

const portraits = ref<DpsPortrait[]>([])
const overview = ref<Record<string, unknown>>({})
const health = ref<{ status?: string; version?: string }>({})
const keyword = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)
const presentation = ref<ErrorPresentation | null>(null)

const isForbidden = computed(() => presentation.value?.pageLevel === true)
const isNotFound = computed(() => presentation.value?.kind === 'not-found')
/** 错误条仅承载可重试的页内错误（5xx/网络/未知），403/404 走页面级 / 空态 */
const showErrorBar = computed(
  () => !!presentation.value && !presentation.value.pageLevel && presentation.value.kind !== 'not-found',
)
const errorMessage = computed(() =>
  showErrorBar.value ? `画像列表加载失败：${presentation.value?.detail || '网络错误'}` : '',
)
const emptyDescription = computed(() => {
  if (showErrorBar.value) return '加载失败，请点击上方提示条「点击重试」'
  return '当前租户暂无数据（如为权限问题请联系管理员）'
})

const filtered = computed(() => {
  if (!keyword.value) return portraits.value
  const kw = keyword.value.toLowerCase()
  return portraits.value.filter(
    (p) => String(p.name ?? '').toLowerCase().includes(kw) || String(p.person_id ?? '').toLowerCase().includes(kw),
  )
})

function riskOf(row: DpsPortrait): number {
  const raw = row.risk_level ?? row.risk_score
  const n = Number(raw)
  return Number.isFinite(n) ? n : -1
}

function riskLabel(row: DpsPortrait): string {
  const v = riskOf(row)
  if (v < 0) return '未知'
  if (v >= 70) return '高'
  if (v >= 40) return '中'
  return '低'
}

function riskType(row: DpsPortrait): 'success' | 'warning' | 'danger' | 'info' {
  const v = riskOf(row)
  if (v < 0) return 'info'
  if (v >= 70) return 'danger'
  if (v >= 40) return 'warning'
  return 'success'
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
  presentation.value = null
  try {
    const result = await dpsApi.listPortraits({ page: page.value, page_size: pageSize })
    portraits.value = result.items || []
    total.value = result.total ?? 0
  } catch (err) {
    portraits.value = []
    total.value = 0
    presentation.value = describeError(err)
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
.request-id { color: #6b7280; font-size: 12px; margin-bottom: 8px; }
</style>
