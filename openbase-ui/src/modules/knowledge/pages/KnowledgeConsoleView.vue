<template>
  <div class="rag-console">
    <el-tabs v-model="activeTab" data-test="rag-console-tabs">
      <!-- 控制台概览 -->
      <el-tab-pane label="概览" name="overview">
        <el-card data-test="rag-console-overview">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="接入 Base URL">
              <code>https://openbase.example.com/api/v1/rag</code>
            </el-descriptions-item>
            <el-descriptions-item label="鉴权方式">
              <el-tag size="small">Bearer Token</el-tag> 在「API 密钥」创建后注入
            </el-descriptions-item>
          </el-descriptions>
          <div class="console-snippet">
            <div class="snippet-title">接入示例（Python）</div>
            <pre class="code-block">{{ snippet }}</pre>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- API 调试器 -->
      <el-tab-pane label="API 调试器" name="debugger">
        <el-card data-test="rag-debugger">
          <el-form inline>
            <el-form-item label="接口">
              <el-select v-model="apiSel" style="width: 260px" data-test="rag-api-sel">
                <el-option v-for="api in apis" :key="api.method + api.path" :label="`${api.method} ${api.path}`" :value="api.method + api.path" />
              </el-select>
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="apiKey" placeholder="Bearer key" style="width: 220px" />
            </el-form-item>
            <el-button type="primary" :loading="sending" data-test="rag-send" @click="sendRequest">发送</el-button>
          </el-form>
          <el-input v-model="requestBody" type="textarea" :rows="5" class="mt-8" placeholder="请求体 JSON" data-test="rag-body" />
          <el-divider />
          <div class="resp-header">响应</div>
          <pre class="code-block resp-block" data-test="rag-response">{{ response || '等待发送请求...' }}</pre>
        </el-card>
      </el-tab-pane>

      <!-- 接口文档 -->
      <el-tab-pane label="接口文档" name="docs">
        <el-card data-test="rag-api-docs">
          <el-table :data="apis" stripe size="small">
            <el-table-column prop="method" label="方法" width="80" />
            <el-table-column prop="path" label="路径" min-width="200" />
            <el-table-column prop="description" label="说明" min-width="220" />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 性能监控 -->
      <el-tab-pane label="性能监控" name="perf">
        <el-card data-test="rag-perf">
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="perf-card">
                <div class="perf-label">平均延迟</div>
                <div class="perf-value">38ms</div>
                <el-tag size="small" type="success">-12% 较上周</el-tag>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="perf-card">
                <div class="perf-label">QPS</div>
                <div class="perf-value">156</div>
                <el-tag size="small" type="info">峰值 320</el-tag>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="perf-card">
                <div class="perf-label">错误率</div>
                <div class="perf-value">0.8%</div>
                <el-tag size="small" type="warning">目标 &lt;1%</el-tag>
              </div>
            </el-col>
          </el-row>
          <div ref="perfRef" class="perf-chart" />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const activeTab = ref('overview')
const apiSel = ref('POST /kb/search')
const apiKey = ref('')
const requestBody = ref('{"query": "OpenBase 网关", "top_k": 5}')
const response = ref('')
const sending = ref(false)
const perfRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const snippet = `import httpx

client = httpx.Client(
    base_url="https://openbase.example.com/api/v1/rag",
    headers={"Authorization": "Bearer ${'YOUR_API_KEY'}"},
)
resp = client.post("/kb/search", json={"query": "网关", "top_k": 5})
print(resp.json())`

const apis = [
  { method: 'POST', path: '/kb/search', description: '知识库向量检索' },
  { method: 'GET', path: '/kb/{id}', description: '知识库详情' },
  { method: 'POST', path: '/kb/{id}/documents', description: '上传文档' },
  { method: 'POST', path: '/chat', description: 'RAG 对话（检索+生成）' },
  { method: 'GET', path: '/health', description: '健康检查' },
]

function sendRequest() {
  if (!apiKey.value) {
    ElMessage.warning('请填写 API Key')
    return
  }
  sending.value = true
  setTimeout(() => {
    sending.value = false
    response.value = JSON.stringify({
      code: 0,
      data: { hits: [{ doc_id: 'doc_123', score: 0.96, snippet: 'OpenBase 统一网关提供服务发现与聚合编排...' }] },
      traceId: 't-' + Math.random().toString(16).slice(2, 10),
    }, null, 2)
  }, 500)
}

function renderPerf() {
  if (!perfRef.value) return
  if (!chart) chart = echarts.init(perfRef.value)
  const hours = ['00', '04', '08', '12', '16', '20', '24']
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['延迟(ms)', 'QPS'] },
    grid: { left: 50, right: 50, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: hours },
    yAxis: [
      { type: 'value', name: '延迟' },
      { type: 'value', name: 'QPS' },
    ],
    series: [
      { name: '延迟(ms)', type: 'line', smooth: true, data: [42, 36, 34, 38, 41, 37, 39], yAxisIndex: 0 },
      { name: 'QPS', type: 'bar', data: [80, 120, 160, 200, 156, 140, 110], yAxisIndex: 1 },
    ],
  })
}

onMounted(() => nextTick(renderPerf))
onBeforeUnmount(() => {
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.mt-8 { margin-top: 8px; }
.console-snippet { margin-top: 16px; }
.snippet-title { font-weight: 600; margin-bottom: 8px; }
.code-block { background: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 12px; font-size: 12px; overflow: auto; }
.resp-block { background: #f6f8fa; color: #334155; min-height: 160px; }
.resp-header { font-weight: 600; margin-bottom: 8px; }
.perf-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; text-align: center; }
.perf-label { font-size: 13px; color: #6b7280; }
.perf-value { font-size: 22px; font-weight: 600; margin: 4px 0; }
.perf-chart { height: 280px; margin-top: 16px; }
</style>
