<template>
  <div>
    <el-page-header content="记忆详情" class="mb-16" @back="$router.push('/memory')" />
    <el-row :gutter="16">
      <el-col :xs="24" :lg="14">
        <el-card header="记忆内容" class="mb-16">
          <p class="content">{{ memory.content }}</p>
          <el-divider />
          <p class="meta">类型：{{ memory.type }} · 创建：{{ memory.created_at }} · 衰减权重：{{ memory.weight.toFixed(2) }}</p>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="10">
        <el-card header="Waypoint 召回路径时间线" data-test="waypoint-timeline" class="mb-16">
          <el-timeline>
            <el-timeline-item v-for="node in waypoints" :key="node.label" :timestamp="node.time" :type="node.type">
              {{ node.label }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
        <el-card header="关联知识库记忆" class="mb-16" data-test="related-memories">
          <el-table :data="related" size="small">
            <el-table-column prop="source" label="来源" width="90" />
            <el-table-column prop="content" label="内容（摘要）" show-overflow-tooltip />
            <el-table-column label="相关性" width="90">
              <template #default="{ row }">
                <el-tag :type="row.score >= 0.7 ? 'success' : 'info'" size="small">{{ row.score.toFixed(2) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="related.length === 0" description="暂无关联记忆" :image-size="50" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
const memory = {
  id: route.params.id,
  content: '用户偏好使用简洁的技术文档风格，并在检索质量评估中关注 faithfulness 与 context_precision 指标。',
  type: 'text',
  weight: 0.92,
  created_at: '2026-08-25 10:00',
}
const waypoints = [
  { label: 'create · 记忆创建', time: '2026-08-25 10:00', type: 'primary' },
  { label: 'access · 最近访问', time: '2026-08-25 14:20', type: 'success' },
  { label: 'recall · 本次召回命中', time: '2026-08-25 15:00', type: 'warning' },
]
const related = [
  { source: '文档库', content: '技术文档写作规范：结构清晰、示例先行', score: 0.86 },
  { source: '会话', content: '讨论检索评估指标时的偏好', score: 0.72 },
]
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.content { line-height: 1.8; white-space: pre-wrap; }
.meta { color: var(--ob-text-secondary); font-size: 13px; }
</style>
