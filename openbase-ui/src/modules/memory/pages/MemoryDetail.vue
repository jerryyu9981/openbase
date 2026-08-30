<template>
  <div>
    <el-page-header content="记忆详情" class="mb-16" @back="$router.push('/memory')" />
    <div v-loading="loading">
      <template v-if="memory">
        <el-row :gutter="16">
          <el-col :xs="24" :lg="14">
            <el-card header="记忆内容" class="mb-16">
              <p class="content">{{ memory.content }}</p>
              <el-divider />
              <p class="meta">
                类型：{{ memory.memory_type }}
                · 创建：{{ memory.created_at || '-' }}
                · 相关度：{{ (memory.score ?? 0).toFixed(2) }}
              </p>
              <div v-if="memory.tags && memory.tags.length" class="mt-8">
                <el-tag v-for="t in memory.tags" :key="t" size="small" class="mr-4">{{ t }}</el-tag>
              </div>
            </el-card>
            <el-card header="元数据" class="mb-16" v-if="hasMetadata">
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item v-for="(value, key) in memory.metadata" :key="key" :label="String(key)">
                  {{ String(value) }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
          <el-col :xs="24" :lg="10">
            <el-card header="实体抽取" class="mb-16" data-test="entities">
              <el-table :data="entities" size="small">
                <el-table-column prop="name" label="实体" />
                <el-table-column prop="type" label="类型" width="110" />
              </el-table>
              <el-empty v-if="entities.length === 0" description="暂无实体" :image-size="50" />
            </el-card>
          </el-col>
        </el-row>
      </template>
      <el-empty v-else-if="!loading" description="记忆不存在或已被删除" :image-size="60" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { http } from '@/core/api/http'

interface MemoryDetail {
  id: string
  content: string
  memory_type: string
  user_id: string | null
  session_id: string | null
  agent_id: string | null
  metadata: Record<string, unknown>
  score: number | null
  entities: Array<{ name: string; type: string }>
  created_at: string | null
  tags: string[]
}

const route = useRoute()
const memory = ref<MemoryDetail | null>(null)
const loading = ref(false)

const entities = computed(() => memory.value?.entities || [])
const hasMetadata = computed(
  () => !!memory.value?.metadata && Object.keys(memory.value.metadata).length > 0,
)

async function load() {
  loading.value = true
  try {
    const { data } = await http.get<{ code: number; message: string; data: MemoryDetail }>(
      `/memory-proxy/memories/${route.params.id}`,
    )
    memory.value = data.data
  } catch {
    memory.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-8 { margin-top: 8px; }
.mr-4 { margin-right: 4px; }
.content { line-height: 1.8; white-space: pre-wrap; }
.meta { color: var(--ob-text-secondary); font-size: 13px; }
</style>
