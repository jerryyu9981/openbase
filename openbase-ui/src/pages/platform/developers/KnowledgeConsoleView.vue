<template>
  <PageContainer title="知识库 API 控制台" description="知识库接口调试（真实链路）" test-id="knowledge-console-view-page">
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="rag-console-error"
      @close="errorMessage = ''"
    />

    <el-tabs v-model="activeTab" data-test="rag-console-tabs">
      <!-- 控制台概览 -->
      <el-tab-pane label="概览" name="overview">
        <el-card data-test="rag-console-overview">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="接入 Base URL">
              <code>{{ proxyBase }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="鉴权方式">
              <el-tag size="small">OpenBase 登录态</el-tag> 前端不持有 OpenRAG 凭据，统一由 OpenBase 代理注入
            </el-descriptions-item>
            <el-descriptions-item label="上游健康">
              <el-tag size="small" :type="healthOk ? 'success' : 'danger'" data-test="rag-health-tag">
                {{ healthStatus || '未知' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <div class="console-snippet">
            <div class="snippet-title">接入示例（Python，经 OpenBase 代理）</div>
            <pre class="code-block">{{ snippet }}</pre>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- API 调试器 -->
      <el-tab-pane label="API 调试器" name="debugger">
        <el-card data-test="rag-debugger">
          <el-form label-width="90px">
            <el-form-item label="知识库">
              <el-radio-group v-model="collectionId" size="small" data-test="rag-collection-picker">
                <el-radio-button v-for="collection in collections" :key="collection.id" :value="collection.id">
                  {{ collection.name }}
                </el-radio-button>
              </el-radio-group>
              <span v-if="collections.length === 0" class="hint">暂无知识库</span>
            </el-form-item>
            <el-form-item label="检索语句">
              <el-input v-model="query" placeholder="输入自然语言查询" data-test="rag-query" @keyup.enter="sendRequest" />
            </el-form-item>
            <el-form-item label="Top K">
              <el-input-number v-model="topK" :min="1" :max="20" size="small" data-test="rag-topk" />
              <el-button type="primary" :loading="sending" class="ml-8" data-test="rag-send" @click="sendRequest">
                发送检索
              </el-button>
            </el-form-item>
          </el-form>
          <el-divider />
          <div class="resp-header">
            响应
            <span v-if="lastLatency !== null" class="latency" data-test="rag-latency">耗时 {{ lastLatency }} ms</span>
          </div>
          <pre class="code-block resp-block" data-test="rag-response">{{ response || '等待发送请求...' }}</pre>
        </el-card>
      </el-tab-pane>

      <!-- 接口文档 -->
      <el-tab-pane label="接口文档" name="docs">
        <el-card data-test="rag-api-docs">
          <el-table :data="apis" stripe size="small">
            <el-table-column prop="method" label="方法" width="80" />
            <el-table-column prop="path" label="路径" min-width="240" />
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
                <div class="perf-label">最近检索耗时</div>
                <div class="perf-value">{{ lastLatency === null ? '—' : `${lastLatency} ms` }}</div>
                <div class="perf-hint">本页最近一次真实检索</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="perf-card">
                <div class="perf-label">知识库数量</div>
                <div class="perf-value">{{ collections.length }}</div>
                <div class="perf-hint">来自 /rag-proxy/collections</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="perf-card">
                <div class="perf-label">上游健康</div>
                <div class="perf-value">{{ healthStatus || '未知' }}</div>
                <div class="perf-hint">来自 /rag-proxy/health</div>
              </div>
            </el-col>
          </el-row>
          <el-descriptions v-if="healthComponents.length" :column="1" border class="mt-16">
            <el-descriptions-item v-for="item in healthComponents" :key="item.name" :label="item.name">
              <el-tag size="small" :type="item.ok ? 'success' : 'danger'">{{ item.value }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="上游未返回组件状态" :image-size="60" />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { ragApi, type RagCollection } from '@/core/api/rag'
import { describeError } from '@/core/api/error'

/**
 * 知识库 API 控制台（v1.12.0 OB-04）：全部走 `rag-proxy` 真实链路，
 * 调试器调用 `/collections/{id}/query/retrieve`，性能页只展示可得真实指标
 * （最近检索耗时 / 知识库数 / 上游健康），不虚构 QPS 与错误率曲线。
 */
const activeTab = ref('overview')
const collections = ref<RagCollection[]>([])
const collectionId = ref('')
const query = ref('OpenBase 网关')
const topK = ref(5)
const response = ref('')
const sending = ref(false)
const lastLatency = ref<number | null>(null)
const errorMessage = ref('')
const healthStatus = ref('')
const healthComponents = ref<Array<{ name: string; value: string; ok: boolean }>>([])

const proxyBase = `${window.location.origin}/api/v1/rag-proxy`

const healthOk = computed(() => healthStatus.value.toLowerCase() === 'ok' || healthStatus.value.toLowerCase() === 'healthy')

const snippet = computed(() => `import httpx

client = httpx.Client(
    base_url="${proxyBase}",
    headers={"Authorization": "Bearer <OpenBase 登录令牌>"},
)
resp = client.post(
    "/collections/${collectionId.value || '<collection_id>'}/query/retrieve",
    json={"query": "网关", "top_k": 5},
)
print(resp.json())`)

const apis = [
  { method: 'GET', path: '/rag-proxy/collections', description: '知识库列表' },
  { method: 'GET', path: '/rag-proxy/collections/{id}', description: '知识库详情' },
  { method: 'GET', path: '/rag-proxy/collections/{id}/documents', description: '文档列表' },
  { method: 'POST', path: '/rag-proxy/collections/{id}/query', description: '检索 + 生成' },
  { method: 'POST', path: '/rag-proxy/collections/{id}/query/retrieve', description: '纯检索（本控制台使用）' },
  { method: 'GET', path: '/rag-proxy/health', description: '上游健康' },
]

function errorText(error: unknown, fallback: string) {
  return describeError(error).detail || fallback
}

async function loadCollections() {
  try {
    const data = await ragApi.listCollections()
    collections.value = data.items ?? []
    if (!collectionId.value && collections.value.length) {
      collectionId.value = collections.value[0].id
    }
  } catch (error) {
    errorMessage.value = errorText(error, '知识库列表加载失败')
  }
}

async function loadHealth() {
  try {
    const health = await ragApi.getRagHealth()
    healthStatus.value = health.status || ''
    healthComponents.value = Object.entries(health.components ?? {}).map(([name, value]) => ({
      name,
      value: String(value),
      ok: String(value).toLowerCase() === 'ok' || String(value).toLowerCase() === 'healthy',
    }))
  } catch (error) {
    errorMessage.value = errorText(error, '上游健康加载失败')
  }
}

async function sendRequest() {
  if (!collectionId.value) {
    errorMessage.value = '请先选择知识库'
    return
  }
  if (!query.value.trim()) {
    errorMessage.value = '请输入检索语句'
    return
  }
  sending.value = true
  errorMessage.value = ''
  const started = performance.now()
  try {
    const result = await ragApi.retrieve(collectionId.value, {
      query: query.value.trim(),
      top_k: topK.value,
    })
    lastLatency.value = Math.round(performance.now() - started)
    response.value = JSON.stringify(result, null, 2)
  } catch (error) {
    lastLatency.value = null
    response.value = ''
    errorMessage.value = errorText(error, '检索请求失败')
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadCollections(), loadHealth()])
})
</script>

<style scoped>
.mb-16 { margin-bottom: 12px; }
.mt-16 { margin-top: 16px; }
.ml-8 { margin-left: 8px; }
.console-snippet { margin-top: 16px; }
.snippet-title { font-weight: 600; margin-bottom: 8px; }
.code-block { background: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 12px; font-size: 12px; overflow: auto; }
.resp-block { background: #f6f8fa; color: #334155; min-height: 160px; }
.resp-header { font-weight: 600; margin-bottom: 8px; display: flex; gap: 12px; align-items: center; }
.latency { font-weight: 400; font-size: 12px; color: var(--ob-text-secondary); }
.perf-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; text-align: center; }
.perf-label { font-size: 13px; color: #6b7280; }
.perf-value { font-size: 22px; font-weight: 600; margin: 4px 0; }
.perf-hint { font-size: 12px; color: var(--ob-text-secondary); }
.hint { margin-left: 8px; font-size: 12px; color: var(--ob-text-secondary); }
</style>
