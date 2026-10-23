<template>
  <PageContainer title="应用调用记录" description="跨应用调用明细（服务端分页）" test-id="app-calls-page">
    <div class="page-toolbar">
      <span class="filter-label">应用</span>
      <el-radio-group v-model="appFilter" size="small" data-test="calls-app-filter">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button v-for="app in apps" :key="app.id" :value="app.id">{{ app.name }}</el-radio-button>
      </el-radio-group>
      <span class="filter-label">状态</span>
      <el-radio-group v-model="statusFilter" size="small" data-test="calls-status-filter">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="success">成功</el-radio-button>
        <el-radio-button value="error">失败</el-radio-button>
      </el-radio-group>
      <el-button :loading="loading" data-test="calls-refresh" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="calls-error"
      @close="errorMessage = ''"
    />

    <el-table v-loading="loading" :data="calls" size="small" data-test="calls-table">
      <el-table-column prop="app_name" label="应用" min-width="140" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'success' ? 'success' : 'danger'">{{ row.status || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="耗时" width="100">
        <template #default="{ row }">{{ row.latency_ms ?? '-' }} ms</template>
      </el-table-column>
      <el-table-column label="Token" width="120">
        <template #default="{ row }">{{ (row.total_tokens ?? 0).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column prop="error_code" label="错误码" width="130">
        <template #default="{ row }">{{ row.error_code || '-' }}</template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="90">
        <template #default="{ row }">{{ row.version || '-' }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && calls.length === 0" description="暂无调用记录" :image-size="80" />

    <el-pagination
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      class="calls-pagination"
      data-test="calls-pagination"
    />
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, ref, watch } from 'vue'
import { aiAppsApi, type AiAppCall, type AiAppItem } from '@/core/api/aiApps'
import { describeError } from '@/core/api/error'

const loading = ref(false)
const errorMessage = ref('')
const apps = ref<AiAppItem[]>([])
const calls = ref<AiAppCall[]>([])
const appFilter = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

function errorText(error: unknown, fallback: string) {
  return describeError(error).detail || fallback
}

async function loadApps() {
  try {
    apps.value = await aiAppsApi.list()
  } catch {
    // 应用列表失败不阻断调用记录加载；筛选退化为「全部」
    apps.value = []
  }
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await aiAppsApi.listCalls({
      app_id: appFilter.value || undefined,
      status: statusFilter.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    calls.value = data.items
    total.value = data.total
  } catch (error) {
    errorMessage.value = errorText(error, '调用记录加载失败')
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  page.value = 1
  void load()
}

watch([appFilter, statusFilter], applyFilter)
watch(page, () => void load())

onMounted(async () => {
  await loadApps()
  await load()
})
</script>

<style scoped>
.page-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.filter-label { font-size: 13px; color: var(--ob-text-secondary); }
.mb-16 { margin-bottom: 12px; }
.calls-pagination { margin-top: 12px; justify-content: flex-end; }
</style>
