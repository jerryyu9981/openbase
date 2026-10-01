<template>
  <div class="dps-scoring">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索评分类型" clearable style="width: 220px" data-test="scoring-search" />
      <el-button type="primary" :loading="loading" data-test="scoring-query" @click="load">查询</el-button>
    </div>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="load">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card header="已注册评分类型">
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="filtered" stripe empty-text="暂无已注册的评分类型" data-test="scoring-table">
          <el-table-column prop="name" label="评分类型" min-width="180" />
          <el-table-column prop="code" label="标识" min-width="170" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'inactive' ? 'info' : 'success'" size="small">{{ row.status || '已注册' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="200" />
          <template #empty>
            <el-empty description="暂无已注册的评分类型" :image-size="60" data-test="scoring-empty" />
          </template>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { dpsApi, type DpsScoringType } from '@/core/api/dps'
import { useAsyncState } from '@/core/composables/useAsyncState'

const keyword = ref('')
const { data, loading, error, run } = useAsyncState<{ items: DpsScoringType[]; total?: number }>()

const filtered = computed(() => {
  const items = data.value?.items || []
  if (!keyword.value) return items
  const kw = keyword.value.toLowerCase()
  return items.filter((item) => String(item.name || '').toLowerCase().includes(kw) || String(item.code || '').toLowerCase().includes(kw))
})

async function load() {
  await run(() => dpsApi.listScoringTypes())
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.mb-16 { margin-bottom: 16px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
</style>
