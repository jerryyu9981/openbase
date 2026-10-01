<template>
  <div class="dps-measure">
    <div class="page-toolbar">
      <el-input v-model="personId" placeholder="person_id" style="width: 260px" data-test="measure-person" />
      <el-button type="primary" :loading="loading" data-test="measure-run" @click="load">查询建议</el-button>
    </div>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="load">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card header="建议列表（后端原文 · 前端原样呈现）">
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="suggestions" stripe empty-text="暂无措施建议" data-test="measure-table">
          <el-table-column prop="measure_text" label="建议内容" min-width="220" />
          <el-table-column prop="tag_code" label="标签" min-width="170" />
          <el-table-column prop="measure_code" label="措施码" width="110" />
          <el-table-column prop="source_tag" label="来源标签" min-width="140" />
          <template #empty>
            <el-empty description="暂无措施建议" :image-size="60" data-test="measure-empty" />
          </template>
        </el-table>
      </div>

      <el-alert v-if="disclaimer" type="warning" show-icon :closable="false" class="mt-16" data-test="measure-disclaimer">
        <template #title>免责声明（后端原文，前端不得改写）</template>
        <div>{{ disclaimer }}</div>
      </el-alert>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { dpsApi, type DpsMeasureSuggestion } from '@/core/api/dps'
import { useAsyncState } from '@/core/composables/useAsyncState'

const route = useRoute()
const personId = ref(String(route.query.person_id || ''))

const { data, loading, error, run } = useAsyncState<{ suggestions?: DpsMeasureSuggestion[]; disclaimer?: string }>()

const suggestions = computed(() => data.value?.suggestions || [])
const disclaimer = computed(() => data.value?.disclaimer || '')

async function load() {
  if (!personId.value) return
  await run(() => dpsApi.suggestMeasures(personId.value))
}

onMounted(() => {
  if (personId.value) void load()
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.mb-16 { margin-bottom: 16px; }
.mt-16 { margin-top: 16px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
</style>
