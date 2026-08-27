<template>
  <div>
    <div class="page-toolbar">
      <h3>我的收藏</h3>
      <el-tag type="info" data-test="favorites-total">{{ totalCount }} 个收藏模型</el-tag>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="favorites-error"
      @close="errorMessage = ''"
    />
    <el-button v-if="errorMessage" link type="primary" data-test="favorites-retry" @click="loadFavorites">重试加载</el-button>

    <el-card v-loading="loading" data-test="favorites-card">
      <el-tabs v-model="activeGroup" data-test="favorites-tabs">
        <el-tab-pane v-for="group in groups" :key="group" :name="group" :label="`${group} (${groupCount(group)})`">
          <el-empty
            v-if="groupModels(group).length === 0"
            :description="`「${group}」分组暂无收藏`"
            :image-size="80"
            data-test="favorites-empty"
          />
          <el-row v-else :gutter="16">
            <el-col v-for="model in groupModels(group)" :key="model.id" :xs="24" :sm="12" :lg="8">
              <el-card class="model-card" data-test="favorite-card">
                <div class="model-head">
                  <span class="model-name">{{ model.name }}</span>
                  <el-tag size="small" :type="modelType(model.type)">{{ model.type }}</el-tag>
                </div>
                <p class="meta">Provider：{{ model.provider }}</p>
                <div class="cap-list">
                  <el-tag v-for="cap in model.capabilities" :key="cap" size="small" type="info" class="cap-tag">
                    {{ cap }}
                  </el-tag>
                </div>
                <p class="desc">{{ model.description }}</p>
                <p class="meta">收藏时间：{{ model.added_at }}</p>
                <div class="actions">
                  <el-button link type="primary" data-test="favorite-download" @click="handleDownload(model)">下载</el-button>
                  <el-popconfirm title="确认取消收藏该模型？" data-test="favorite-remove-confirm" @confirm="removeFavorite(model.id)">
                    <template #reference><el-button link type="danger">取消收藏</el-button></template>
                  </el-popconfirm>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface FavoriteModel {
  id: number
  name: string
  provider: string
  type: string
  group: string
  capabilities: string[]
  description: string
  added_at: string
}

const loading = ref(true)
const errorMessage = ref('')
const activeGroup = ref('对话模型')

const groups = ['对话模型', '多模态', 'Embedding', '代码生成']

/** 契约 mock：收藏列表（不调用真实 API） */
const favorites = ref<FavoriteModel[]>([
  { id: 1, name: 'gpt-4o', provider: 'OpenAI', type: '商业', group: '对话模型', capabilities: ['chat', 'vision'], description: '旗舰多模态对话模型', added_at: '2026-08-20' },
  { id: 2, name: 'claude-3-5-sonnet', provider: 'Anthropic', type: '商业', group: '对话模型', capabilities: ['chat', 'code'], description: '擅长代码与长文本理解', added_at: '2026-08-21' },
  { id: 3, name: 'qwen2.5-7b', provider: 'Ollama', type: '本地', group: '对话模型', capabilities: ['chat'], description: '本地轻量部署的开源模型', added_at: '2026-08-22' },
  { id: 4, name: 'gemini-1.5-pro', provider: 'Google', type: '商业', group: '多模态', capabilities: ['vision', 'audio', 'video'], description: '超长上下文多模态模型', added_at: '2026-08-18' },
  { id: 5, name: 'llava-13b', provider: 'HuggingFace', type: '开源', group: '多模态', capabilities: ['vision'], description: '开源视觉语言模型', added_at: '2026-08-19' },
  { id: 6, name: 'bge-m3', provider: 'BAAI', type: '开源', group: 'Embedding', capabilities: ['embedding'], description: '多语言向量检索模型', added_at: '2026-08-15' },
  { id: 7, name: 'text-embedding-3-large', provider: 'OpenAI', type: '商业', group: 'Embedding', capabilities: ['embedding'], description: '高质量文本向量模型', added_at: '2026-08-16' },
  { id: 8, name: 'deepseek-coder-33b', provider: 'DeepSeek', type: '开源', group: '代码生成', capabilities: ['code'], description: '面向代码生成的专家模型', added_at: '2026-08-17' },
])

const totalCount = computed(() => favorites.value.length)

function groupModels(group: string) {
  return favorites.value.filter((model) => model.group === group)
}
function groupCount(group: string) {
  return groupModels(group).length
}

function modelType(type: string) {
  return { 商业: 'primary', 开源: 'success', 本地: 'warning' }[type] || 'info'
}

async function loadFavorites() {
  loading.value = true
  errorMessage.value = ''
  try {
    await mockDelay(500) // 契约 mock：模拟拉取收藏列表
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '收藏列表加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function removeFavorite(id: number) {
  const target = favorites.value.find((model) => model.id === id)
  favorites.value = favorites.value.filter((model) => model.id !== id)
  ElMessage.success(`已取消收藏：${target?.name ?? id}`)
}

function handleDownload(model: FavoriteModel) {
  // 契约 mock：下载入口，仅提示开始下载
  ElMessage.info(`开始下载：${model.name}`)
}

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

onMounted(() => {
  void loadFavorites()
})
</script>

<style scoped>
.page-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
.page-toolbar h3 {
  margin: 0;
}
.mb-16 {
  margin-bottom: 12px;
}
.model-card {
  margin-bottom: 16px;
}
.model-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.model-name {
  font-weight: 600;
}
.meta {
  color: var(--ob-text-secondary);
  font-size: 13px;
  margin: 6px 0;
}
.desc {
  font-size: 13px;
  margin: 6px 0;
}
.cap-list {
  margin: 6px 0;
}
.cap-tag {
  margin-right: 4px;
}
.actions {
  margin-top: 8px;
}
</style>
