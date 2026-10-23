<template>
  <PageContainer title="我的收藏" description="常用模型与应用的收藏夹" test-id="favorites-page">
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
            <el-col v-for="item in groupModels(group)" :key="item.id" :xs="24" :sm="12" :lg="8">
              <el-card class="model-card" data-test="favorite-card">
                <div class="model-head">
                  <span class="model-name">{{ modelName(item) }}</span>
                  <el-tag size="small" type="info">{{ item.model?.source || '未知来源' }}</el-tag>
                </div>
                <p class="meta">参数规模：{{ item.model?.parameters || '未知' }} · 许可证：{{ item.model?.license || '未知' }}</p>
                <div class="cap-list">
                  <el-tag v-for="tag in item.model?.tags || []" :key="tag" size="small" type="info" class="cap-tag">
                    {{ tag }}
                  </el-tag>
                </div>
                <p class="desc">{{ item.model?.description || '暂无模型描述' }}</p>
                <p class="meta">收藏时间：{{ formatDate(item.created_at) }}</p>
                <div class="actions">
                  <el-button link type="primary" data-test="favorite-download" @click="handleDownload(item)">下载</el-button>
                  <el-popconfirm title="确认取消收藏该模型？" data-test="favorite-remove-confirm" @confirm="removeFavorite(item)">
                    <template #reference><el-button link type="danger">取消收藏</el-button></template>
                  </el-popconfirm>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { favoritesApi, openModelsApi, type LlmFavorite } from '@/core/api/governance'
import { describeError } from '@/core/api/error'

const DEFAULT_FOLDER = '默认收藏'

const loading = ref(true)
const errorMessage = ref('')
const activeGroup = ref(DEFAULT_FOLDER)
const favorites = ref<LlmFavorite[]>([])
const folderNames = ref<string[]>([])

const groups = computed(() => {
  const names = new Set<string>(folderNames.value)
  favorites.value.forEach((item) => names.add(item.folder_name || DEFAULT_FOLDER))
  return names.size ? Array.from(names) : [DEFAULT_FOLDER]
})

const totalCount = computed(() => favorites.value.length)

function modelName(item: LlmFavorite) {
  return item.model?.name || item.model_id
}

function formatDate(value: string | null) {
  if (!value) return '-'
  return value.slice(0, 10)
}

function groupModels(group: string) {
  return favorites.value.filter((item) => (item.folder_name || DEFAULT_FOLDER) === group)
}

function groupCount(group: string) {
  return groupModels(group).length
}

function errorText(error: unknown, fallback: string) {
  return describeError(error).detail || fallback
}

async function loadFavorites() {
  loading.value = true
  errorMessage.value = ''
  const results = await Promise.allSettled([favoritesApi.list(), favoritesApi.folders()])
  const [listResult, folderResult] = results

  if (listResult.status === 'fulfilled') {
    favorites.value = listResult.value
  } else {
    errorMessage.value = errorText(listResult.reason, '收藏列表加载失败，请稍后重试')
  }

  if (folderResult.status === 'fulfilled') {
    folderNames.value = folderResult.value.map((item) => item.name)
  }

  if (groups.value.length && !groups.value.includes(activeGroup.value)) {
    activeGroup.value = groups.value[0]
  }
  loading.value = false
}

async function removeFavorite(item: LlmFavorite) {
  try {
    await favoritesApi.remove(item.model_id)
    favorites.value = favorites.value.filter((row) => row.id !== item.id)
    ElMessage.success(`已取消收藏：${modelName(item)}`)
  } catch (error) {
    ElMessage.error(errorText(error, '取消收藏失败'))
  }
}

async function handleDownload(item: LlmFavorite) {
  try {
    await openModelsApi.startDownload(item.model_id)
    ElMessage.success(`下载任务已提交：${modelName(item)}`)
  } catch (error) {
    ElMessage.error(errorText(error, '下载任务提交失败'))
  }
}

onMounted(() => {
  void loadFavorites()
})
</script>

<style scoped>
.page-toolbar h3 {
  margin: 0;
}
.page-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
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
