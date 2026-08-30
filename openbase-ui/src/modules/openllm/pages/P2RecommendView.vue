<template>
  <div class="p2-recommend">
    <el-row :gutter="16">
      <!-- 模型对比推荐 -->
      <el-col :span="14">
        <el-card header="模型对比推荐" data-test="rec-card">
          <div class="page-toolbar">
            <el-select v-model="dimension" style="width: 200px" data-test="rec-dimension">
              <el-option v-for="d in dimensions" :key="d" :label="d" :value="d" />
            </el-select>
            <el-button type="primary" data-test="rec-compare" @click="applyRecommendation">开始对比</el-button>
          </div>
          <el-table :data="recommendations" stripe empty-text="选择维度后推荐" data-test="rec-table">
            <el-table-column prop="rank" label="排名" width="60" />
            <el-table-column prop="model" label="模型" min-width="140" />
            <el-table-column prop="score" label="推荐指数" width="100">
              <template #default="{ row }">
                <el-progress :percentage="row.score" :show-text="true" />
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="推荐理由" min-width="220" />
          </el-table>
        </el-card>
      </el-col>
      <!-- 文档内容库 -->
      <el-col :span="10">
        <el-card header="文档内容库" data-test="rec-doc-card">
          <div class="page-toolbar">
            <el-input v-model="docKeyword" placeholder="检索文档" clearable size="small" style="width: 160px" data-test="rec-doc-search" />
            <el-button size="small" type="primary" data-test="rec-doc-query" @click="searchDoc">检索</el-button>
          </div>
          <div v-for="doc in docs" :key="doc.id" class="doc-item" data-test="rec-doc-item">
            <div class="doc-title">{{ doc.title }}</div>
            <div class="doc-meta">{{ doc.category }} · {{ doc.size }}</div>
          </div>
          <el-empty v-if="docs.length === 0" description="无文档" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const dimensions = ['通用能力', '中文能力', '代码能力', '推理速度', '性价比']

interface Recommendation { rank: number; model: string; score: number; reason: string }
interface DocItem { id: number; title: string; category: string; size: string }

const dimension = ref('通用能力')
const recommendations = ref<Recommendation[]>([])
const docs = ref<DocItem[]>([
  { id: 1, title: 'OpenBase 网关接入指南', category: '集成', size: '2.4MB' },
  { id: 2, title: 'RAG 最佳实践', category: '教程', size: '1.8MB' },
  { id: 3, title: '模型部署规范 v2', category: '规范', size: '860KB' },
  { id: 4, title: '聚合编排示例集', category: '示例', size: '1.2MB' },
])
const docKeyword = ref('')

const mockResults: Record<string, Recommendation[]> = {
  '通用能力': [
    { rank: 1, model: 'Qwen2.5 14B', score: 92, reason: '中文与英文综合能力均衡，指令遵循优' },
    { rank: 2, model: 'Llama 3 8B', score: 86, reason: '生态完善，社区支持广泛' },
    { rank: 3, model: 'ChatGLM3 6B', score: 82, reason: '中文场景优化，部署门槛低' },
  ],
  '代码能力': [
    { rank: 1, model: 'DeepSeek Coder 6.7B', score: 95, reason: '代码生成与补全专项优化' },
    { rank: 2, model: 'Qwen2.5-Coder 7B', score: 90, reason: '多语言覆盖，注释理解好' },
    { rank: 3, model: 'CodeLlama 7B', score: 84, reason: 'Meta 代码系列，生态成熟' },
  ],
}

function applyRecommendation() {
  recommendations.value = mockResults[dimension.value] || mockResults['通用能力']
  ElMessage.success(`已按「${dimension.value}」生成推荐`)
}

function searchDoc() {
  const kw = docKeyword.value.trim().toLowerCase()
  if (!kw) {
    docs.value = [
      { id: 1, title: 'OpenBase 网关接入指南', category: '集成', size: '2.4MB' },
      { id: 2, title: 'RAG 最佳实践', category: '教程', size: '1.8MB' },
      { id: 3, title: '模型部署规范 v2', category: '规范', size: '860KB' },
      { id: 4, title: '聚合编排示例集', category: '示例', size: '1.2MB' },
    ]
    return
  }
  const all: DocItem[] = [
    { id: 1, title: 'OpenBase 网关接入指南', category: '集成', size: '2.4MB' },
    { id: 2, title: 'RAG 最佳实践', category: '教程', size: '1.8MB' },
    { id: 3, title: '模型部署规范 v2', category: '规范', size: '860KB' },
    { id: 4, title: '聚合编排示例集', category: '示例', size: '1.2MB' },
  ]
  docs.value = all.filter((d) => d.title.toLowerCase().includes(kw) || d.category.includes(kw))
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.doc-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.doc-title { font-weight: 600; font-size: 14px; }
.doc-meta { font-size: 12px; color: #9ca3af; margin-top: 4px; }
</style>
