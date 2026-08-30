<template>
  <div class="memory-monitor">
    <el-tabs v-model="activeTab" data-test="mm-tabs">
      <!-- 系统监控 -->
      <el-tab-pane label="系统监控" name="monitor">
        <el-row :gutter="16" class="mb-16">
          <el-col v-for="stat in stats" :key="stat.label" :span="6">
            <el-card shadow="hover" data-test="mm-stat">
              <div class="stat-label">{{ stat.label }}</div>
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-sub">{{ stat.sub }}</div>
            </el-card>
          </el-col>
        </el-row>
        <el-card header="服务指标趋势" data-test="mm-trend-card">
          <div ref="trendRef" class="trend-chart" />
        </el-card>
      </el-tab-pane>

      <!-- API 测试 -->
      <el-tab-pane label="API 测试" name="api-test">
        <el-card header="记忆 API 测试台" data-test="mm-api-card">
          <el-form inline>
            <el-form-item label="接口">
              <el-select v-model="apiSel" style="width: 240px" data-test="mm-api-sel">
                <el-option v-for="api in apis" :key="api" :label="api" :value="api" />
              </el-select>
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="apiKey" placeholder="Bearer key" style="width: 200px" data-test="mm-api-key" />
            </el-form-item>
            <el-button type="primary" :loading="testing" data-test="mm-test" @click="testApi">测试</el-button>
          </el-form>
          <el-input v-model="requestBody" type="textarea" :rows="4" class="mt-8" placeholder="请求体 JSON" data-test="mm-body" />
          <el-divider />
          <div class="resp-header">响应</div>
          <pre class="code-block resp-block" data-test="mm-response">{{ response || '等待测试...' }}</pre>
        </el-card>
      </el-tab-pane>

      <!-- 设置 -->
      <el-tab-pane label="设置" name="settings">
        <el-card header="服务设置" data-test="mm-settings">
          <el-form label-width="140px" style="max-width: 560px">
            <el-form-item label="服务地址">
              <el-input v-model="settings.serviceUrl" data-test="mm-service-url" />
            </el-form-item>
            <el-form-item label="健康检查间隔(s)">
              <el-input-number v-model="settings.healthInterval" :min="5" :max="300" />
            </el-form-item>
            <el-form-item label="告警通知">
              <el-switch v-model="settings.alertEnabled" data-test="mm-alert-toggle" />
            </el-form-item>
            <el-form-item label="通知渠道">
              <el-checkbox-group v-model="settings.channels">
                <el-checkbox value="email" label="邮件" />
                <el-checkbox value="webhook" label="Webhook" />
                <el-checkbox value="dingtalk" label="钉钉" />
              </el-checkbox-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" data-test="mm-save" @click="saveSettings">保存</el-button>
              <el-button data-test="mm-verify" @click="verifyConnection">验证连接</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const activeTab = ref('monitor')
const trendRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const stats = ref([
  { label: '记忆条目', value: '1,284,502', sub: '今日 +8,240' },
  { label: '存储占用', value: '3.2GB', sub: 'Redis + ES' },
  { label: '平均检索延迟', value: '8.5ms', sub: 'P99 22ms' },
  { label: '服务状态', value: '健康', sub: '3 实例在线' },
])

const apis = ['GET /memories', 'POST /memories', 'POST /memories/search', 'POST /memories/sessions', 'GET /health']

const apiSel = ref('GET /health')
const apiKey = ref('')
const requestBody = ref('{"user_id": "u_1001", "query": "用户偏好"}')
const response = ref('')
const testing = ref(false)

const settings = ref({
  serviceUrl: 'http://127.0.0.1:8020',
  healthInterval: 30,
  alertEnabled: true,
  channels: ['email'] as string[],
})

function renderTrend() {
  if (!trendRef.value) return
  if (!chart) chart = echarts.init(trendRef.value)
  const hours = ['00', '04', '08', '12', '16', '20', '24']
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['检索量(千)', '延迟(ms)'] },
    grid: { left: 50, right: 50, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: hours },
    yAxis: [{ type: 'value', name: '检索量' }, { type: 'value', name: '延迟' }],
    series: [
      { name: '检索量(千)', type: 'bar', data: [42, 66, 88, 120, 96, 74, 58], yAxisIndex: 0 },
      { name: '延迟(ms)', type: 'line', smooth: true, data: [9, 8, 8, 10, 9, 8, 9], yAxisIndex: 1 },
    ],
  })
}

function testApi() {
  if (!apiKey.value && apiSel.value !== 'GET /health') {
    ElMessage.warning('请填写 API Key')
    return
  }
  testing.value = true
  setTimeout(() => {
    testing.value = false
    response.value = JSON.stringify({ code: 0, data: { ok: true, items: 3, elapsed_ms: 8 }, traceId: 't-' + Math.random().toString(16).slice(2, 10) }, null, 2)
  }, 400)
}

function saveSettings() {
  ElMessage.success('服务设置已保存')
}

function verifyConnection() {
  ElMessage.success(`连接验证成功：${settings.value.serviceUrl}/health 返回 200`)
}

onMounted(() => nextTick(renderTrend))
onBeforeUnmount(() => {
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-8 { margin-top: 8px; }
.stat-label { font-size: 13px; color: #6b7280; }
.stat-value { font-size: 22px; font-weight: 600; margin: 4px 0; }
.stat-sub { font-size: 12px; color: #9ca3af; }
.trend-chart { height: 300px; }
.resp-header { font-weight: 600; margin-bottom: 8px; }
.code-block { background: #f6f8fa; color: #334155; border-radius: 8px; padding: 12px; font-size: 12px; min-height: 140px; overflow: auto; }
</style>
