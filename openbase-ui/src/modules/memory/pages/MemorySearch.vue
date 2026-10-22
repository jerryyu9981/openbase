<template>
  <PageContainer title="记忆搜索" description="语义检索与相似度排序" test-id="memory-search-page">
    <div class="page-toolbar">
      <span class="tab-hint">语义召回：输入查询词，经 memory-proxy 调用 OpenMemory recall 检索最相关记忆</span>
    </div>
    <el-card class="mb-16">
      <el-form label-width="80px" inline @submit.prevent>
        <el-form-item label="查询词">
          <el-input
            v-model="query"
            placeholder="如：咖啡、项目偏好、会议纪要"
            clearable
            style="width: 320px"
            data-test="search-query"
            @keyup.enter="runSearch"
          />
        </el-form-item>
        <el-form-item label="策略">
          <el-select v-model="strategy" style="width: 160px" data-test="search-strategy">
            <el-option label="自动" value="auto" />
            <el-option label="语义" value="semantic" />
            <el-option label="关键词" value="keyword" />
            <el-option label="混合" value="hybrid" />
            <el-option label="图谱" value="graph" />
            <el-option label="时序" value="temporal" />
            <el-option label="融合" value="fusion" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="topK" :min="1" :max="50" data-test="search-topk" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" data-test="search-run" @click="runSearch">搜索</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-alert
      v-if="isGraphStrategy && !errorMsg"
      title="图谱检索仅返回记忆：实体命中会沿 MENTIONS 解析为关联记忆；未关联任何记忆的孤立实体会以实体节点展示"
      type="info"
      show-icon
      class="mb-16"
      data-test="search-graph-hint"
    />

    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="search-error"
      @close="errorMsg = ''"
    />

    <div v-loading="loading">
      <template v-if="results.length">
        <div class="result-meta" data-test="search-meta">
          共 {{ results.length }} 条结果 · 策略 {{ strategy }}
        </div>
        <el-table :data="results" stripe data-test="search-table">
          <el-table-column label="记忆内容（摘要）" min-width="260">
            <template #default="{ row }">
              <div class="cell-content" data-test="search-content">{{ row.content }}</div>
            </template>
          </el-table-column>
          <el-table-column label="相关度" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="scoreType(row.score)" data-test="search-score">
                {{ (row.score ?? 0).toFixed(3) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.memory_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="命中方式" min-width="150">
            <template #default="{ row }">
              <el-tag v-if="row.metadata?.node_type === 'memory'" size="small" type="success" effect="plain" data-test="search-hit-mode">
                记忆命中
              </el-tag>
              <el-tag v-else-if="row.metadata?.node_type" size="small" type="warning" effect="plain" data-test="search-hit-mode">
                实体节点 · {{ row.metadata.node_type }}
              </el-tag>
              <span v-else class="muted">-</span>
              <div v-if="row.metadata?.matched_entity" class="matched-entity" data-test="search-matched-entity">
                实体：{{ row.metadata.matched_entity }}
              </div>
            </template>
          </el-table-column>
          <el-table-column label="标签" min-width="130">
            <template #default="{ row }">
              <el-tag v-for="t in row.tags || []" :key="t" size="small" type="info" class="mr-4">{{ t }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="来源" width="90">
            <template #default="{ row }">
              <el-tag size="small" effect="plain" :type="sourceType(row.source)">{{ row.source }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="isMemoryId(row.memory_id)"
                link
                type="primary"
                data-test="search-detail"
                @click="$router.push(`/memory/${row.memory_id}`)"
              >详情</el-button>
              <span v-else class="muted">实体节点</span>
            </template>
          </el-table-column>
        </el-table>
      </template>
      <el-empty
        v-else-if="!loading && searched"
        description="未检索到匹配的记忆"
        data-test="search-empty"
      />
      <el-empty
        v-else-if="!loading && !searched"
        description="输入查询词开始搜索"
        :image-size="70"
      />
    </div>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, ref } from 'vue'
import { http } from '@/core/api/http'

interface RecallMetadata {
  node_type?: string
  matched_entity?: string
  tags?: string[]
  [key: string]: unknown
}

interface RecallResult {
  memory_id: string
  content: string
  score: number | null
  memory_type: string
  source: string
  tags: string[]
  entities: unknown[]
  metadata?: RecallMetadata
}

const query = ref('')
const strategy = ref('semantic')
const topK = ref(10)
const loading = ref(false)
const searched = ref(false)
const errorMsg = ref('')
const results = ref<RecallResult[]>([])

const isGraphStrategy = computed(() => strategy.value === 'graph' || strategy.value === 'temporal')

async function runSearch() {
  const q = query.value.trim()
  if (!q) {
    errorMsg.value = '请输入查询词'
    return
  }
  errorMsg.value = ''
  loading.value = true
  searched.value = true
  try {
    const { data } = await http.post<{ code: number; message: string; data: { results: RecallResult[] } }>(
      '/memory-proxy/recall',
      { query: q, top_k: topK.value, strategy: strategy.value },
    )
    results.value = (data.data?.results || []).map((m) => ({
      ...m,
      tags: m.metadata?.tags || m.tags || [],
    }))
  } catch (e) {
    results.value = []
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '搜索失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function scoreType(score: number | null) {
  const s = score ?? 0
  if (s >= 0.3) return 'success'
  if (s >= 0.1) return 'warning'
  return 'info'
}

function sourceType(source: string) {
  if (source === 'graph') return 'success'
  if (source === 'semantic') return 'primary'
  if (source === 'keyword') return 'warning'
  return 'info'
}

/** 仅 UUID 记忆 id 可进入详情；`entity:*` 为孤立实体节点。 */
function isMemoryId(memoryId: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(memoryId)
}
</script>

<style scoped>
.tab-hint { color: var(--ob-text-secondary); font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
.mr-4 { margin-right: 4px; }
.result-meta { margin-bottom: 8px; color: var(--ob-text-secondary); font-size: 13px; }
.cell-content { white-space: pre-wrap; line-height: 1.6; }
.muted { color: var(--ob-text-secondary); font-size: 12px; }
.matched-entity { color: var(--ob-text-secondary); font-size: 12px; margin-top: 2px; }
</style>
