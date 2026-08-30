<template>
  <div class="dps-monitor">
    <!-- 依赖健康 -->
    <el-row :gutter="16" class="mb-16">
      <el-col v-for="dep in deps" :key="dep.name" :span="6">
        <el-card shadow="hover" data-test="mon-dep">
          <div class="dep-header">
            <span>{{ dep.name }}</span>
            <el-tag :type="dep.ok ? 'success' : 'danger'" size="small" data-test="mon-dep-badge">{{ dep.ok ? '健康' : '异常' }}</el-tag>
          </div>
          <div class="dep-latency">延迟 {{ dep.latency }}ms</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- QPS / 资源 -->
    <el-row :gutter="16" class="mb-16">
      <el-col :span="12">
        <el-card header="QPS 趋势" data-test="mon-qps-card">
          <div ref="qpsRef" class="chart" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="内存 / CPU" data-test="mon-res-card">
          <div ref="resRef" class="chart" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 告警规则 -->
    <el-card header="告警规则" data-test="mon-alert-card">
      <div class="page-toolbar">
        <el-button type="primary" size="small" data-test="mon-alert-new" @click="addAlert">新增规则</el-button>
      </div>
      <el-table :data="alerts" stripe empty-text="暂无告警规则" data-test="mon-alert-table">
        <el-table-column prop="name" label="规则名" min-width="150" />
        <el-table-column prop="metric" label="指标" width="120" />
        <el-table-column prop="condition" label="条件" width="140" />
        <el-table-column prop="channels" label="通知渠道" width="140" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-popconfirm title="确认删除该规则？" @confirm="removeAlert(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const deps = ref([
  { name: 'OpenLLM', ok: true, latency: 42 },
  { name: 'OpenRAG', ok: true, latency: 38 },
  { name: 'OpenMemory', ok: true, latency: 8 },
  { name: '对象存储', ok: false, latency: 1200 },
])

const alerts = ref([
  { name: 'QPS 过高告警', metric: 'qps', condition: '> 2000 持续 5m', channels: '邮件+钉钉' },
  { name: '内存水位告警', metric: 'memory', condition: '> 85%', channels: 'Webhook' },
  { name: '依赖不可用告警', metric: 'dependency', condition: '连续 3 次探测失败', channels: '邮件' },
])

const qpsRef = ref<HTMLDivElement>()
const resRef = ref<HTMLDivElement>()
let qpsChart: echarts.ECharts | null = null
let resChart: echarts.ECharts | null = null

function renderCharts() {
  if (qpsRef.value) {
    qpsChart = qpsChart || echarts.init(qpsRef.value)
    const hours = ['00', '04', '08', '12', '16', '20', '24']
    qpsChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: hours },
      yAxis: { type: 'value' },
      series: [{ name: 'QPS', type: 'line', smooth: true, areaStyle: { opacity: 0.15 }, data: [320, 480, 650, 980, 860, 720, 540] }],
    })
  }
  if (resRef.value) {
    resChart = resChart || echarts.init(resRef.value)
    const hours = ['00', '04', '08', '12', '16', '20', '24']
    resChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['内存%', 'CPU%'] },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: hours },
      yAxis: { type: 'value', max: 100 },
      series: [
        { name: '内存%', type: 'line', smooth: true, data: [55, 58, 62, 68, 74, 70, 66] },
        { name: 'CPU%', type: 'line', smooth: true, data: [35, 42, 58, 72, 65, 50, 40] },
      ],
    })
  }
}

function addAlert() {
  alerts.value.push({ name: `告警规则-${alerts.value.length + 1}`, metric: 'qps', condition: '> 5000 持续 10m', channels: '邮件' })
  ElMessage.success('告警规则已新增')
}

function removeAlert(row: { name: string }) {
  alerts.value = alerts.value.filter((a) => a.name !== row.name)
  ElMessage.success('告警规则已删除')
}

onMounted(() => nextTick(renderCharts))
onBeforeUnmount(() => {
  qpsChart?.dispose()
  qpsChart = null
  resChart?.dispose()
  resChart = null
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.dep-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.dep-latency { font-size: 13px; color: #6b7280; margin-top: 8px; }
.chart { height: 260px; }
</style>
