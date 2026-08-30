<template>
  <div>
    <div class="page-toolbar">
      <span class="page-title" data-test="gateway-title">API 网关</span>
      <span class="tab-hint">统一网关：服务密钥（OpenBase 签发）+ 审计日志（真实记录）+ 网关健康（服务发现）</span>
    </div>
    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="gateway-error"
      @close="errorMsg = ''"
    />
    <div v-loading="loading">
      <el-tabs v-model="activeTab" data-test="gateway-tabs">
        <!-- 访问密钥：真实接口 /api/v1/auth/api-keys -->
        <el-tab-pane label="访问密钥" name="keys">
          <div class="page-toolbar">
            <el-button type="primary" data-test="create-key" @click="openCreateDialog">创建密钥</el-button>
            <el-button plain :loading="loading" data-test="refresh-keys" @click="loadKeys">刷新</el-button>
            <span class="tab-hint" data-test="keys-hint">密钥创建后仅展示一次，请妥善保管；列表不回显明文</span>
          </div>
          <el-table :data="apiKeys" stripe data-test="key-table" empty-text="暂无密钥">
            <el-table-column prop="name" label="名称" min-width="140" />
            <el-table-column label="权限范围" min-width="180">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ scopeLabel(row.scope) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">{{ row.description || '—' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.revoked ? 'info' : 'success'">
                  {{ row.revoked ? '已吊销' : '启用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="170">
              <template #default="{ row }">{{ formatTime(row.created) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 审计日志：真实接口 /audit/records -->
        <el-tab-pane label="审计日志" name="logs">
          <div class="page-toolbar">
            <el-input
              v-model="logKeyword"
              placeholder="搜索路径、操作人或 IP"
              clearable
              style="width: 260px"
              data-test="log-search"
              @input="logPage = 1"
            />
            <el-button plain :loading="loading" data-test="refresh-logs" @click="loadAudit">刷新</el-button>
            <span class="tab-hint">共 {{ filteredLogs.length }} 条记录</span>
          </div>
          <el-table :data="pagedLogs" stripe size="small" data-test="audit-table">
            <el-table-column label="请求 ID" width="180">
              <template #default="{ row }">
                <code class="mono">{{ row.request_id }}</code>
              </template>
            </el-table-column>
            <el-table-column prop="method" label="方法" width="90">
              <template #default="{ row }">
                <el-tag size="small" effect="plain" :type="methodType(row.method)">{{ row.method }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
            <el-table-column label="状态码" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status_code < 400 ? 'success' : row.status_code < 500 ? 'warning' : 'danger'">
                  {{ row.status_code }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="耗时" width="90">
              <template #default="{ row }">{{ row.duration_ms }}ms</template>
            </el-table-column>
            <el-table-column label="操作人" width="110">
              <template #default="{ row }">{{ row.operator_name || row.operator_id || '—' }}</template>
            </el-table-column>
            <el-table-column prop="ip_address" label="来源 IP" width="130" />
          </el-table>
          <el-empty
            v-if="!loading && filteredLogs.length === 0"
            description="未找到匹配的审计日志"
            data-test="log-empty"
          />
          <div v-if="filteredLogs.length > pageSize" class="pagination-wrap">
            <el-pagination
              v-model:current-page="logPage"
              :page-size="pageSize"
              :total="filteredLogs.length"
              layout="total, prev, pager, next"
              data-test="log-pagination"
            />
          </div>
        </el-tab-pane>

        <!-- 网关健康：真实接口 /api/v1/gateway/health -->
        <el-tab-pane label="网关健康" name="health">
          <div class="page-toolbar">
            <el-button plain :loading="loading" data-test="refresh-health" @click="loadGatewayHealth">刷新</el-button>
            <span class="tab-hint">服务发现注册表：各系统实例健康率</span>
          </div>
          <el-table :data="gatewaySystems" stripe data-test="gw-health-table" empty-text="暂无系统实例（服务发现注册表为空）">
            <el-table-column prop="system" label="系统" min-width="140" />
            <el-table-column label="健康状态" width="120">
              <template #default="{ row }">
                <el-tag :type="row.healthy ? 'success' : 'danger'" size="small">
                  {{ row.healthy ? '健康' : '异常' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="实例数" width="100">
              <template #default="{ row }">{{ row.instance_count }}</template>
            </el-table-column>
            <el-table-column label="健康率" min-width="200">
              <template #default="{ row }">
                <el-progress :percentage="Math.round((row.health_rate ?? 0) * 100)" :stroke-width="10" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 创建密钥对话框 -->
    <el-dialog v-model="createVisible" title="创建访问密钥" width="480px" data-test="create-key-dialog">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="keyForm.name" placeholder="如：生产环境服务密钥" data-test="key-name-input" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="keyForm.description" placeholder="用途说明（可选）" data-test="key-desc-input" />
        </el-form-item>
        <el-form-item label="权限范围">
          <el-select v-model="keyForm.scopeMode" style="width: 100%" data-test="key-scope">
            <el-option label="全部系统 + 全部租户" value="all" />
            <el-option label="仅 OpenMemory" value="memory" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" data-test="create-key-submit" @click="createKey">创建</el-button>
      </template>
    </el-dialog>

    <!-- 密钥创建成功（仅展示一次） -->
    <el-dialog v-model="tokenVisible" title="密钥创建成功" width="520px" data-test="token-dialog">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="密钥仅展示一次"
        description="关闭本窗口后将无法再次查看完整密钥，请立即复制并妥善保存。"
        class="mb-16"
        data-test="token-once-tip"
      />
      <div class="token-box">
        <code data-test="full-token">{{ latestToken }}</code>
      </div>
      <template #footer>
        <el-button @click="tokenVisible = false">我已保存</el-button>
        <el-button type="primary" data-test="copy-token" @click="copyToken">复制密钥</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/core/api/http'

interface ApiKeyRow {
  name: string
  scope: Record<string, unknown>
  description: string
  created: number
  revoked: boolean
  key: string | null
}

interface AuditLogRow {
  request_id: string
  time: string
  method: string
  path: string
  status_code: number
  duration_ms: number
  operator_id: string | null
  operator_name: string | null
  tenant_id: string | null
  ip_address: string | null
}

interface GatewaySystem {
  system: string
  healthy: boolean
  instance_count: number
  health_rate: number
}

const activeTab = ref('keys')
const loading = ref(false)
const errorMsg = ref('')

// 访问密钥
const apiKeys = ref<ApiKeyRow[]>([])
const createVisible = ref(false)
const creating = ref(false)
const tokenVisible = ref(false)
const latestToken = ref('')
const keyForm = reactive<{ name: string; description: string; scopeMode: string }>({
  name: '',
  description: '',
  scopeMode: 'all',
})

// 审计日志
const auditLogs = ref<AuditLogRow[]>([])
const logKeyword = ref('')
const logPage = ref(1)
const pageSize = 10

// 网关健康
const gatewaySystems = ref<GatewaySystem[]>([])

const filteredLogs = computed(() => {
  const kw = logKeyword.value.trim().toLowerCase()
  if (!kw) return auditLogs.value
  return auditLogs.value.filter(
    (log) =>
      log.path.toLowerCase().includes(kw) ||
      (log.operator_name || '').toLowerCase().includes(kw) ||
      (log.operator_id || '').toLowerCase().includes(kw) ||
      (log.ip_address || '').includes(kw),
  )
})

const pagedLogs = computed(() => {
  const start = (logPage.value - 1) * pageSize
  return filteredLogs.value.slice(start, start + pageSize)
})

async function loadKeys() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<{ code: number; message: string; data: ApiKeyRow[] }>('/auth/api-keys')
    apiKeys.value = data.data || []
  } catch (e) {
    apiKeys.value = []
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '密钥列表加载失败'
  } finally {
    loading.value = false
  }
}

async function loadAudit() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<{ records: AuditLogRow[] }>('/audit/records')
    auditLogs.value = (data.records || []).map((r) => ({
      ...r,
      request_id: r.request_id || '',
      time: r.time || '',
      method: r.method || 'GET',
      path: r.path || '',
      status_code: r.status_code ?? 0,
      duration_ms: r.duration_ms ?? 0,
      operator_name: r.operator_name || null,
      tenant_id: r.tenant_id || null,
      ip_address: r.ip_address || null,
    }))
  } catch (e) {
    auditLogs.value = []
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '审计日志加载失败'
  } finally {
    loading.value = false
  }
}

async function loadGatewayHealth() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<{ code: number; message: string; data: { systems: GatewaySystem[] } }>('/gateway/health')
    gatewaySystems.value = data.data?.systems || []
  } catch (e) {
    gatewaySystems.value = []
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '网关健康加载失败'
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  keyForm.name = ''
  keyForm.description = ''
  keyForm.scopeMode = 'all'
  createVisible.value = true
}

async function createKey() {
  const name = keyForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入密钥名称')
    return
  }
  creating.value = true
  errorMsg.value = ''
  try {
    const scope =
      keyForm.scopeMode === 'memory'
        ? { system: ['openmemory'], tenants: ['*'] }
        : { system: ['*'], tenants: ['*'] }
    const { data } = await http.post<{ code: number; message: string; data: ApiKeyRow }>('/auth/api-keys', {
      name,
      scope,
      description: keyForm.description.trim(),
    })
    const created = data.data
    latestToken.value = created.key || ''
    createVisible.value = false
    ElMessage.success('密钥创建成功')
    tokenVisible.value = true
    await loadKeys()
  } catch (e) {
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '密钥创建失败'
  } finally {
    creating.value = false
  }
}

async function copyToken() {
  try {
    await navigator.clipboard.writeText(latestToken.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

function scopeLabel(scope: Record<string, unknown>) {
  const system = Array.isArray(scope?.system) ? (scope.system as string[]).join(',') : '*'
  return `系统: ${system}`
}

function methodType(method: string) {
  return { GET: 'success', POST: 'warning', PUT: 'primary', DELETE: 'danger' }[method] || 'info'
}

function formatTime(epochSeconds: number) {
  if (!epochSeconds) return '—'
  const date = new Date(epochSeconds * 1000)
  const pad = (v: number) => String(v).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

onMounted(() => {
  loadKeys()
  loadAudit()
  loadGatewayHealth()
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.page-title { font-size: 16px; font-weight: 600; }
.tab-hint { color: var(--ob-text-secondary); font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 12px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; word-break: break-all; }
.token-box {
  background: #f5f7fa;
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  padding: 12px;
  word-break: break-all;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
</style>
