<template>
  <div>
    <el-page-header @back="$router.push('/memory')" content="记忆详情" class="mb-16" />
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
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.content { line-height: 1.8; white-space: pre-wrap; }
.meta { color: var(--ob-text-secondary); font-size: 13px; }
</style>
