<template>
  <div class="dps-api">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索端点" clearable style="width: 200px" data-test="api-search" />
      <el-button type="primary" data-test="api-new" @click="openCreate">新增端点</el-button>
      <el-button data-test="api-export" @click="exportDocs">导出文档</el-button>
    </div>

    <el-card header="API 端点" data-test="api-card">
      <div class="ob-table-scroll">
        <el-table :data="filteredApis" stripe empty-text="暂无端点" data-test="api-table">
          <el-table-column prop="name" label="端点名" min-width="140" />
          <el-table-column label="方法" width="80">
            <template #default="{ row }">
              <el-tag :type="methodType(row.method)" size="small">{{ row.method }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="path" label="路径" min-width="180">
            <template #default="{ row }"><code>{{ row.path }}</code></template>
          </el-table-column>
          <el-table-column prop="version" label="版本" width="70" />
          <el-table-column label="操作" width="260">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="api-debug" @click="openDebug(row)">调试</el-button>
              <el-button link type="primary" size="small" data-test="api-versions" @click="openVersions(row)">版本</el-button>
              <el-button link type="primary" size="small" @click="openErrors(row)">错误码</el-button>
              <el-popconfirm title="确认删除该端点？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 新增 -->
    <el-dialog v-model="createOpen" title="新增端点" width="480px" data-test="api-dialog">
      <el-form :model="form" label-width="70px">
        <el-form-item label="端点名">
          <el-input v-model="form.name" data-test="api-name" />
        </el-form-item>
        <el-form-item label="方法">
          <el-select v-model="form.method" style="width: 100%">
            <el-option v-for="m in ['GET', 'POST', 'PUT', 'DELETE']" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="路径">
          <el-input v-model="form.path" placeholder="/portrait/tags" data-test="api-path" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" data-test="api-save" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 调试 -->
    <el-drawer v-model="debugOpen" title="端点调试" size="440px" data-test="api-debug-drawer">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="端点">{{ current?.name }}</el-descriptions-item>
        <el-descriptions-item label="版本">{{ current?.version }}</el-descriptions-item>
      </el-descriptions>
      <el-input v-model="debugBody" type="textarea" :rows="4" class="mt-8" placeholder="请求体 JSON" data-test="api-debug-body" />
      <el-button type="primary" size="small" class="mt-8" :loading="debugging" data-test="api-debug-send" @click="sendDebug">发送请求</el-button>
      <el-divider />
      <pre class="code-block" data-test="api-debug-response">{{ debugResponse || '等待发送...' }}</pre>
    </el-drawer>

    <!-- 版本时间线 -->
    <el-drawer v-model="versionOpen" title="版本时间线" size="400px">
      <el-timeline>
        <el-timeline-item v-for="v in versionTimeline" :key="v.version" :timestamp="v.time" type="primary">
          <div class="ver-row">
            <strong>v{{ v.version }}</strong>
            <span class="ver-desc">{{ v.desc }}</span>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-drawer>

    <!-- 错误码 -->
    <el-drawer v-model="errorOpen" title="错误码维护" size="420px">
      <el-table :data="errorCodes" size="small">
        <el-table-column prop="code" label="错误码" width="90" />
        <el-table-column prop="message" label="说明" min-width="200" />
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ApiEndpoint {
  id: number
  name: string
  method: string
  path: string
  version: number
}

const apis = ref<ApiEndpoint[]>([
  { id: 1, name: '画像列表', method: 'GET', path: '/portrait/list', version: 2 },
  { id: 2, name: '标签管理', method: 'POST', path: '/portrait/tags', version: 1 },
  { id: 3, name: '规则引擎', method: 'PUT', path: '/portrait/rules/{id}', version: 3 },
])

const keyword = ref('')
const createOpen = ref(false)
const form = ref({ name: '', method: 'GET', path: '' })
const debugOpen = ref(false)
const current = ref<ApiEndpoint | null>(null)
const debugBody = ref('{}')
const debugResponse = ref('')
const debugging = ref(false)
const versionOpen = ref(false)
const versionTimeline = ref([{ version: 3, time: '2026-08-20', desc: '新增熔断参数' }, { version: 2, time: '2026-07-15', desc: '支持租户过滤' }, { version: 1, time: '2026-06-01', desc: '初始发布' }])
const errorOpen = ref(false)
const errorCodes = ref([{ code: 'PARAM_422', message: '参数校验失败' }, { code: 'AUTH_401', message: '未登录' }, { code: 'PERM_403', message: '无权限' }, { code: 'SYS_500', message: '内部错误' }])

const filteredApis = computed(() =>
  keyword.value ? apis.value.filter((a) => a.name.includes(keyword.value) || a.path.includes(keyword.value)) : apis.value,
)

function methodType(m: string) {
  return { GET: 'success', POST: 'warning', PUT: 'primary', DELETE: 'danger' }[m] as 'success' | 'warning' | 'primary' | 'danger'
}

function openCreate() {
  form.value = { name: '', method: 'GET', path: '' }
  createOpen.value = true
}

function save() {
  if (!form.value.name || !form.value.path) {
    ElMessage.warning('请填写名称与路径')
    return
  }
  const id = Math.max(0, ...apis.value.map((a) => a.id)) + 1
  apis.value.push({ id, ...form.value, version: 1 })
  ElMessage.success('端点已创建')
  createOpen.value = false
}

function openDebug(row: ApiEndpoint) {
  current.value = row
  debugResponse.value = ''
  debugOpen.value = true
}

function sendDebug() {
  debugging.value = true
  setTimeout(() => {
    debugging.value = false
    debugResponse.value = JSON.stringify({ code: 0, data: { ok: true }, traceId: 't-' + Math.random().toString(16).slice(2, 10) }, null, 2)
  }, 400)
}

function openVersions(row: ApiEndpoint) {
  current.value = row
  versionOpen.value = true
}

function openErrors(row: ApiEndpoint) {
  current.value = row
  errorOpen.value = true
}

function exportDocs() {
  const content = apis.value.map((a) => `${a.method} ${a.path} — ${a.name} (v${a.version})`).join('\n')
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'dps-api-docs.md'
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('API 文档已导出')
}

function remove(id: number) {
  apis.value = apis.value.filter((a) => a.id !== id)
  ElMessage.success('端点已删除')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.mt-8 { margin-top: 8px; }
.code-block { background: #f6f8fa; color: #334155; border-radius: 8px; padding: 12px; font-size: 12px; min-height: 120px; }
.ver-row { display: flex; gap: 12px; align-items: center; }
.ver-desc { color: #6b7280; font-size: 13px; }
</style>
