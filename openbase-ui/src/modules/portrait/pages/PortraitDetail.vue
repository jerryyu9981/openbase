<template>
  <div>
    <el-page-header content="画像详情" class="mb-16" @back="$router.push('/portrait')" />
    <el-row :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card header="基本信息" class="mb-16">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="名称">{{ profile.name }}</el-descriptions-item>
            <el-descriptions-item label="描述">{{ profile.description }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag size="small">{{ profile.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="数据源">{{ profile.data_source }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card header="标签维护" class="mb-16">
          <div class="tags">
            <el-tag v-for="t in profile.tags" :key="t" closable class="tag-item" @close="removeTag(t)">{{ t }}</el-tag>
          </div>
          <div class="add-tag">
            <el-input v-model="newTag" placeholder="添加标签" style="width: 200px" @keyup.enter="addTag" />
            <el-button data-test="add-tag" @click="addTag">添加</el-button>
          </div>
        </el-card>
        <el-card header="特征分布" class="mb-16" data-test="feature-dist">
          <div v-for="f in features" :key="f.label" class="feature-row">
            <span class="feature-label">{{ f.label }}</span>
            <el-progress :percentage="f.value" :stroke-width="10" :color="f.value >= 70 ? '#16a34a' : f.value >= 40 ? '#d97706' : '#dc2626'" />
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-card header="关联画像" class="mb-16" data-test="related-profiles">
      <el-table :data="related" size="small">
        <el-table-column prop="name" label="画像" min-width="160" />
        <el-table-column prop="relation" label="关联关系" width="120" />
        <el-table-column prop="strength" label="关联强度" width="140">
          <template #default="{ row }">
            <el-progress :percentage="row.strength" :stroke-width="8" />
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="related.length === 0" description="暂无关联画像" :image-size="50" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const newTag = ref('')
const profile = reactive({
  id: route.params.id,
  name: '核心用户-张伟',
  description: '高频使用 RAG 检索用户，偏好深度技术内容',
  status: 'active',
  data_source: 'openllm',
  tags: ['高频用户', 'RAG', '技术型'],
})
const features = ref([
  { label: '活跃度', value: 92 },
  { label: '技术倾向', value: 85 },
  { label: '付费意愿', value: 58 },
  { label: '内容偏好', value: 74 },
])
const related = ref([
  { name: '开发者-陈晨', relation: '同类画像', strength: 78 },
  { name: '数据分析师-周杰', relation: '协作画像', strength: 62 },
])

function addTag() {
  const tag = newTag.value.trim()
  if (!tag) return
  if (!profile.tags.includes(tag)) profile.tags.push(tag)
  newTag.value = ''
}
function removeTag(tag: string) {
  profile.tags = profile.tags.filter((t) => t !== tag)
  ElMessage.success(`已移除标签：${tag}`)
}
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.add-tag { display: flex; gap: 8px; }
.feature-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.feature-label { width: 70px; color: var(--ob-text-secondary); font-size: 13px; }
</style>
