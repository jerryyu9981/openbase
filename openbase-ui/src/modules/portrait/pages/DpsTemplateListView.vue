<template>
  <div class="dps-templates">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索模板族名称 / code" clearable style="width: 240px" data-test="template-search" />
      <el-select v-model="statusFilter" placeholder="状态：全部" clearable style="width: 140px" data-test="template-status-filter">
        <el-option label="active" value="active" />
        <el-option label="inactive" value="inactive" />
        <el-option label="draft" value="draft" />
      </el-select>
      <el-button type="primary" data-test="template-query" @click="load">查询</el-button>
      <el-button data-test="template-reset" @click="resetFilters">重置</el-button>
      <el-button type="primary" plain data-test="template-new" @click="router.push('/dps/templates/new')">新建模板</el-button>
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
            <template #default="{ row }">v{{ row.version ?? 1 }}</template>
          </el-table-column>
          <el-table-column prop="profile_type" label="profile_type" width="140" />
          <el-table-column prop="subject_type" label="subject_type" width="140" />
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="template-detail" @click="openDetail(row.code)">详情</el-button>
              <el-button link type="primary" size="small" data-test="template-versions" @click="router.push(`/dps/templates/${row.code}/versions`)">查看对比</el-button>
              <el-button link type="primary" size="small" data-test="template-preflight" @click="router.push(`/dps/templates/${row.code}/preflight`)">预检</el-button>
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

    <el-drawer v-model="detailOpen" title="模板族详情" size="480px" data-test="template-detail-drawer">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="code">{{ detail?.code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ detail?.status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="name">{{ detail?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="version">v{{ detail?.version ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="profile_type">{{ detail?.profile_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="subject_type">{{ detail?.subject_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="extends">{{ detail?.extends || '—（无继承）' }}</el-descriptions-item>
        <el-descriptions-item label="description">{{ detail?.description || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div class="mt-12">
        <el-button size="small" @click="router.push(`/dps/templates/${detail?.code}/versions`)">查看对比</el-button>
        <el-button size="small" @click="router.push(`/dps/templates/${detail?.code}/preflight`)">预检</el-button>
        <el-button size="small" data-test="template-edit" @click="router.push(`/dps/templates/${detail?.code}/edit`)">编辑</el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsPortraitTemplate } from '@/core/api/dps'
import { describeDpsError } from '@/core/api/error'
import { useAsyncState } from '@/core/composables/useAsyncState'

const router = useRouter()
const keyword = ref('')
const statusFilter = ref('')
const detailOpen = ref(false)
const detail = ref<DpsPortraitTemplate | null>(null)

const { data, loading, error, run } = useAsyncState<{ items: DpsPortraitTemplate[]; total?: number }>()

const filteredItems = computed(() => {
  const items = data.value?.items || []
  if (!keyword.value) return items
  const kw = keyword.value.toLowerCase()
  return items.filter((item) => String(item.code || '').toLowerCase().includes(kw) || String(item.name || '').toLowerCase().includes(kw))
})

function statusTagType(status?: string): 'success' | 'info' | 'warning' {
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
  try {
    detail.value = await dpsApi.getTemplate(code)
  } catch (caught) {
    error.value = describeDpsError(caught)
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
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.mb-16 { margin-bottom: 16px; }
.mt-12 { margin-top: 12px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
</style>
