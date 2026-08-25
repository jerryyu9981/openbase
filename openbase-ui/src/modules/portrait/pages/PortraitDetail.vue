<template>
  <div>
    <el-page-header @back="$router.push('/portrait')" content="画像详情" class="mb-16" />
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
      </el-col>
    </el-row>
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
</style>
