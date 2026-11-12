<template>
  <PageContainer title="记忆详情" description="单条记忆的内容、来源与关联" test-id="memory-detail-page">
    <el-page-header content="记忆详情" class="mb-16" @back="$router.push('/memory')" />
    <div v-loading="loading">
      <template v-if="memory">
        <el-row :gutter="16">
          <el-col :xs="24" :lg="14">
            <el-card class="mb-16">
              <template #header>
                <div class="card-header">
                  <span>记忆内容</span>
                  <el-button
                    type="primary"
                    size="small"
                    data-test="memory-edit"
                    @click="openEdit"
                  >
                    编辑
                  </el-button>
                </div>
              </template>
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
            <el-card v-if="hasMetadata" header="元数据" class="mb-16">
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
    <el-dialog v-model="editVisible" title="编辑记忆" width="560px">
      <el-form label-width="110px">
        <el-form-item label="内容">
          <el-input
            v-model="editForm.content"
            type="textarea"
            :rows="5"
            maxlength="8000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-input v-model="editForm.memory_type" placeholder="如 episodic / semantic" />
        </el-form-item>
        <el-form-item label="元数据(JSON)">
          <el-input
            v-model="editForm.metadata"
            type="textarea"
            :rows="4"
            placeholder='{"key": "value"}'
          />
        </el-form-item>
        <el-form-item label="归属用户">
          <el-input v-model="editForm.owner" placeholder="仅变更归属时填写" />
        </el-form-item>
        <el-form-item label="确认变更归属">
          <el-switch v-model="editForm.allow_ownership_change" />
          <span class="hint">仅 owner 变更时需要；跨租户/越权将由服务端拒绝</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="saving"
          data-test="memory-edit-submit"
          @click="submitEdit"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { ElMessage } from 'element-plus'
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

const editVisible = ref(false)
const saving = ref(false)
const editForm = ref({
  content: '',
  memory_type: '',
  metadata: '',
  owner: '',
  allow_ownership_change: false,
})

function openEdit() {
  if (!memory.value) return
  editForm.value = {
    content: memory.value.content || '',
    memory_type: memory.value.memory_type || '',
    metadata: JSON.stringify(memory.value.metadata || {}, null, 2),
    owner: memory.value.user_id || '',
    allow_ownership_change: false,
  }
  editVisible.value = true
}

async function submitEdit() {
  if (!memory.value) return
  const payload: Record<string, unknown> = {}
  if (editForm.value.content !== memory.value.content) {
    payload.content = editForm.value.content
  }
  if (editForm.value.memory_type !== memory.value.memory_type) {
    payload.memory_type = editForm.value.memory_type
  }
  const metadataText = editForm.value.metadata.trim()
  if (metadataText) {
    try {
      payload.metadata = JSON.parse(metadataText)
    } catch {
      ElMessage.error('元数据必须是合法 JSON')
      return
    }
  }
  if (editForm.value.owner && editForm.value.owner !== (memory.value.user_id || '')) {
    payload.owner = editForm.value.owner
    payload.allow_ownership_change = editForm.value.allow_ownership_change
  }
  if (Object.keys(payload).length === 0) {
    ElMessage.info('没有需要保存的修改')
    return
  }
  saving.value = true
  try {
    await http.patch(`/memory-proxy/memories/${memory.value.id}`, payload)
    ElMessage.success('已保存')
    editVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

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
.card-header { display: flex; align-items: center; justify-content: space-between; }
.hint { margin-left: 8px; color: var(--ob-text-secondary); font-size: 12px; }
</style>
