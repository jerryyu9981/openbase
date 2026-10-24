<template>
  <PageContainer title="画像 API 管理" description="DPS API 注册表与错误码只读视图" test-id="dps-api-manage-view-page">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb-16"
      title="只读视图：DPS API/错误码写操作已按 ADR-290-01 收口为 410；本页仅展示注册表与错误码。"
      data-test="api-readonly-notice"
    />

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="api-error"
      @close="errorMessage = ''"
    />

    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索端点" clearable style="width: 200px" data-test="api-search" />
      <el-button :loading="loading" data-test="api-refresh" @click="load">刷新</el-button>
      <el-button :loading="errorsLoading" data-test="api-error-codes" @click="openErrors">错误码</el-button>
      <el-button data-test="api-export" @click="exportDocs">导出文档</el-button>
    </div>

    <el-card header="API 注册表（只读）" data-test="api-card">
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="filteredEntries" stripe data-test="api-table">
          <template #empty>
            <el-empty description="暂无注册端点" :image-size="50" data-test="api-empty" />
          </template>
          <el-table-column prop="endpoint" label="路径" min-width="220" show-overflow-tooltip>
            <template #default="{ row }"><code>{{ row.endpoint }}</code></template>
          </el-table-column>
          <el-table-column label="方法" width="90">
            <template #default="{ row }">
              <el-tag :type="methodType(row.method)" size="small">{{ row.method || '—' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ row.status || '—' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sunset_date" label="Sunset" width="130">
            <template #default="{ row }">{{ row.sunset_date || '—' }}</template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.description || '—' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-drawer v-model="errorOpen" title="错误码（只读）" size="520px" data-test="api-error-drawer">
      <el-alert v-if="errorsMessage" :title="errorsMessage" type="error" show-icon :closable="false" class="mb-16" />
      <el-table v-loading="errorsLoading" :data="errorCodes" size="small" data-test="api-error-table">
        <template #empty>
          <el-empty description="暂无错误码" :image-size="50" />
        </template>
        <el-table-column prop="code" label="错误码" width="140" />
        <el-table-column prop="http_status" label="HTTP" width="70" />
        <el-table-column prop="message" label="说明" min-width="180" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="100" />
      </el-table>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsApiRegistryEntry, type DpsErrorCode } from '@/core/api/dps'

/**
 * 画像 API 管理（v1.12.0 XR-DPS-03 只读真实化）：
 * - 注册表 `GET /dps-proxy/api-registry`（version/status 可透传）；
 * - 错误码 `GET /dps-proxy/error-codes`；
 * 上游写面已 410，本页不提供新增/调试/删除入口；导出仅基于已加载的真实注册表数据。
 */
const loading = ref(false)
const errorMessage = ref('')
const entries = ref<DpsApiRegistryEntry[]>([])
const keyword = ref('')

const errorOpen = ref(false)
const errorsLoading = ref(false)
const errorsMessage = ref('')
const errorCodes = ref<DpsErrorCode[]>([])

const filteredEntries = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return entries.value
  return entries.value.filter((row) =>
    `${row.endpoint || ''} ${row.description || ''}`.toLowerCase().includes(text),
  )
})

function methodType(method?: string): 'success' | 'warning' | 'primary' | 'danger' | 'info' {
  const value = (method || '').toUpperCase()
  return ({ GET: 'success', POST: 'warning', PUT: 'primary', DELETE: 'danger' } as const)[
    value as 'GET' | 'POST' | 'PUT' | 'DELETE'
  ] ?? 'info'
}

function statusType(status?: string): 'success' | 'info' | 'warning' | 'danger' {
  const value = (status || '').toLowerCase()
  if (value === 'active' || value === 'enabled') return 'success'
  if (value === 'deprecated') return 'warning'
  if (value === 'retired') return 'danger'
  return 'info'
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    entries.value = await dpsApi.getApiRegistry()
  } catch (error) {
    errorMessage.value = `API 注册表加载失败：${error instanceof Error ? error.message : '未知错误'}`
    entries.value = []
  } finally {
    loading.value = false
  }
}

async function loadErrors() {
  errorsLoading.value = true
  errorsMessage.value = ''
  try {
    errorCodes.value = await dpsApi.getErrorCodes()
  } catch (error) {
    errorsMessage.value = `错误码加载失败：${error instanceof Error ? error.message : '未知错误'}`
    errorCodes.value = []
  } finally {
    errorsLoading.value = false
  }
}

function openErrors() {
  errorOpen.value = true
  void loadErrors()
}

function exportDocs() {
  if (!entries.value.length) {
    ElMessage.warning('暂无可导出的注册端点')
    return
  }
  const content = entries.value
    .map((entry) => `${entry.method || ''} ${entry.endpoint || ''} — ${entry.description || ''} (${entry.version || '-'})`)
    .join('\n')
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'dps-api-registry.md'
  anchor.click()
  URL.revokeObjectURL(url)
  ElMessage.success('API 注册表已导出')
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
</style>
