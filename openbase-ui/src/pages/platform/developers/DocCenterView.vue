<template>
  <div class="doc-center">
    <el-row :gutter="16">
      <!-- 分组目录 -->
      <el-col :span="6">
        <el-card header="文档目录" data-test="doc-tree-card">
          <el-menu default-active="doc-1" data-test="doc-tree" @select="selectDoc">
            <el-sub-menu v-for="group in docGroups" :key="group.name" :index="group.name">
              <template #title>{{ group.name }}</template>
              <el-menu-item v-for="doc in group.docs" :key="doc.id" :index="`doc-${doc.id}`">
                {{ doc.title }}
              </el-menu-item>
            </el-sub-menu>
          </el-menu>
        </el-card>
      </el-col>
      <!-- 文档内容 -->
      <el-col :span="18">
        <el-card>
          <template #header>
            <div class="doc-header">
              <span>{{ currentDoc?.title }}</span>
              <el-input v-model="keyword" placeholder="全文搜索" clearable style="width: 220px" size="small" data-test="doc-search" @keyup.enter="search" />
            </div>
          </template>
          <div class="doc-content" data-test="doc-content">
            <pre>{{ currentDoc?.content }}</pre>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface DocGroup {
  name: string
  docs: Array<{ id: number; title: string; content: string }>
}

const docGroups = ref<DocGroup[]>([
  {
    name: '快速开始',
    docs: [
      { id: 1, title: '平台简介', content: 'OpenBase 是四系统（OpenLLM/OpenRAG/OpenMemory/DPS）的统一基础设施公共底座，提供鉴权、租户、网关等公共能力。' },
      { id: 2, title: '快速上手', content: '1. 管理员登录（admin/admin123）\n2. 在模型中心接入提供商\n3. 在网关管理查看服务实例\n4. 使用聚合编排一次获取多系统数据' },
    ],
  },
  {
    name: '模型服务',
    docs: [
      { id: 3, title: '模型接入', content: '支持 OpenAI 兼容 API 与本地 Ollama。在提供商管理新增提供商，填写 base_url 与 api_key 后测试连接。' },
      { id: 4, title: '开源模型市场', content: '在模型市场浏览开源模型，点击下载部署创建下载任务，可在下载管理查看进度。' },
    ],
  },
  {
    name: '网关与集成',
    docs: [
      { id: 5, title: '服务发现', content: '四系统实例可通过 POST /api/v1/services 动态注册，网关每 10s 健康探测，连续 3 次失败自动剔除。' },
      { id: 6, title: '聚合编排', content: 'POST /api/v1/gateway/aggregate 支持 2~3 个子请求并发聚合，mapping 规则合并结果。' },
    ],
  },
])

const keyword = ref('')
const selectedId = ref(1)

const currentDoc = computed(() => {
  for (const group of docGroups.value) {
    const found = group.docs.find((d) => d.id === selectedId.value)
    if (found) return found
  }
  return docGroups.value[0].docs[0]
})

function selectDoc(index: string) {
  const id = Number(index.replace('doc-', ''))
  selectedId.value = id
}

function search() {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) {
    ElMessage.info('请输入搜索关键词')
    return
  }
  for (const group of docGroups.value) {
    const hit = group.docs.find((d) => d.title.toLowerCase().includes(kw) || d.content.toLowerCase().includes(kw))
    if (hit) {
      selectedId.value = hit.id
      ElMessage.success(`找到文档：${hit.title}`)
      return
    }
  }
  ElMessage.info('未找到匹配文档')
}
</script>

<style scoped>
.doc-header { display: flex; justify-content: space-between; align-items: center; }
.doc-content { min-height: 420px; }
.doc-content pre { white-space: pre-wrap; font-family: inherit; font-size: 14px; line-height: 1.8; color: #334155; }
</style>
