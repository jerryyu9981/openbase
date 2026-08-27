<template>
  <div>
    <div v-loading="loading">
      <el-tabs v-model="activeTab" data-test="api-tabs">
        <el-tab-pane label="访问密钥" name="keys">
          <div class="page-toolbar">
            <el-button type="primary" data-test="create-key" @click="openCreateDialog">创建密钥</el-button>
            <span class="tab-hint" data-test="keys-hint">密钥创建后仅展示一次，请妥善保管</span>
          </div>
          <el-alert
            v-if="errorMsg"
            :title="errorMsg"
            type="error"
            show-icon
            closable
            class="mb-16"
            data-test="keys-error"
            @close="errorMsg = ''"
          />
          <div class="ob-table-scroll">
            <el-table :data="apiKeys" stripe data-test="key-table" empty-text="暂无密钥">
              <el-table-column prop="name" label="名称" min-width="140" />
              <el-table-column label="Token 前缀" width="210">
                <template #default="{ row }">
                  <code class="token-prefix" data-test="token-prefix">{{ row.token_prefix }}...</code>
                </template>
              </el-table-column>
              <el-table-column label="权限" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="permissionType(row.permission)">{{ row.permission }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
                    {{ row.status === 'active' ? '启用' : '停用' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="170" />
              <el-table-column prop="expires_at" label="过期时间" width="120" />
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" data-test="view-key" @click="openDetail(row)">详情</el-button>
                  <el-popconfirm title="确认删除该密钥？删除后相关调用将立即失效" @confirm="removeKey(row.id)">
                    <template #reference><el-button link type="danger" data-test="delete-key">删除</el-button></template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="审计日志" name="logs">
          <div class="page-toolbar">
            <el-input
              v-model="keyword"
              placeholder="搜索操作、路径或 IP"
              clearable
              style="width: 260px"
              data-test="log-search"
              @input="page = 1"
            />
            <el-button type="primary" plain data-test="export-csv" @click="exportCsv">导出 CSV</el-button>
            <span class="tab-hint">共 {{ filteredLogs.length }} 条记录</span>
          </div>
          <el-alert
            v-if="logError"
            :title="logError"
            type="error"
            show-icon
            closable
            class="mb-16"
            data-test="logs-error"
            @close="logError = ''"
          />
          <div class="ob-table-scroll">
            <el-table :data="pagedLogs" stripe size="small" data-test="audit-table">
              <el-table-column prop="time" label="时间" width="170" />
              <el-table-column prop="action" label="操作" min-width="110" />
              <el-table-column label="方法" width="90">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain" :type="methodType(row.method)">{{ row.method }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="path" label="路径" min-width="180" show-overflow-tooltip />
              <el-table-column prop="source_ip" label="来源 IP" width="130" />
              <el-table-column label="结果" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="resultType(row.result)">{{ resultLabel(row.result) }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
            <el-empty
              v-if="!loading && filteredLogs.length === 0"
              description="未找到匹配的审计日志"
              data-test="log-empty"
            />
          </div>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="filteredLogs.length"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              data-test="log-pagination"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="createVisible" title="创建访问密钥" width="480px" data-test="create-key-dialog">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="keyForm.name" placeholder="如：生产环境服务密钥" data-test="key-name-input" />
        </el-form-item>
        <el-form-item label="权限" required>
          <el-select v-model="keyForm.permission" style="width: 100%" data-test="key-permission">
            <el-option label="只读" value="只读" />
            <el-option label="读写" value="读写" />
            <el-option label="管理" value="管理" />
          </el-select>
        </el-form-item>
        <el-form-item label="过期时间">
          <el-date-picker
            v-model="keyForm.expiresAt"
            type="date"
            placeholder="选择过期日期（留空为永不过期）"
            value-format="YYYY-MM-DD"
            style="width: 100%"
            data-test="key-expires"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" data-test="create-key-submit" @click="createKey">创建</el-button>
      </template>
    </el-dialog>

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

    <el-dialog v-model="detailVisible" title="密钥详情" width="480px" data-test="key-detail-dialog">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="名称">{{ detailRow?.name }}</el-descriptions-item>
        <el-descriptions-item label="Token 前缀">{{ detailRow?.token_prefix }}...</el-descriptions-item>
        <el-descriptions-item label="权限">{{ detailRow?.permission }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          {{ detailRow?.status === 'active' ? '启用' : '停用' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ detailRow?.created_at }}</el-descriptions-item>
        <el-descriptions-item label="过期时间">{{ detailRow?.expires_at }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ApiKeyRow {
  id: number
  name: string
  token_prefix: string
  permission: string
  status: 'active' | 'disabled'
  created_at: string
  expires_at: string
}

interface AuditLogRow {
  id: number
  time: string
  action: string
  method: string
  path: string
  source_ip: string
  result: string
}

const activeTab = ref('keys')
const loading = ref(true)
const errorMsg = ref('')
const logError = ref('')

// TD-13-21 API 网关：访问密钥 mock
const apiKeys = ref<ApiKeyRow[]>([
  { id: 1, name: '生产环境服务密钥', token_prefix: 'ob-8fK2mQ3xL9pZc4tW', permission: '读写', status: 'active', created_at: '2026-08-10 09:12', expires_at: '2026-11-10' },
  { id: 2, name: '数据同步专用密钥', token_prefix: 'ob-2hN7bV5sD8jR1wE6', permission: '只读', status: 'active', created_at: '2026-07-28 14:30', expires_at: '永不过期' },
  { id: 3, name: '测试环境调试密钥', token_prefix: 'ob-5tY9cU3aF7kM2xQ8', permission: '管理', status: 'disabled', created_at: '2026-07-15 18:05', expires_at: '2026-10-15' },
])

const createVisible = ref(false)
const keyForm = reactive<{ name: string; permission: string; expiresAt: string }>({
  name: '',
  permission: '只读',
  expiresAt: '',
})

const tokenVisible = ref(false)
const latestToken = ref('')
const detailVisible = ref(false)
const detailRow = ref<ApiKeyRow | null>(null)

// TD-13-21 API 网关：审计日志 mock
const auditLogs = ref<AuditLogRow[]>(buildMockLogs())
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)

const filteredLogs = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return auditLogs.value
  return auditLogs.value.filter(
    (log) =>
      log.action.toLowerCase().includes(kw) ||
      log.path.toLowerCase().includes(kw) ||
      log.source_ip.includes(kw),
  )
})

const pagedLogs = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredLogs.value.slice(start, start + pageSize.value)
})

function buildMockLogs() {
  const actions = ['查询记忆', '写入记忆', '删除记忆', '图谱查询', '创建密钥', '更新配置', '导出日志']
  const methods = ['GET', 'POST', 'PUT', 'DELETE']
  const paths = ['/api/v1/memories', '/api/v1/memories/{id}', '/api/v1/graph/entities', '/api/v1/keys', '/api/v1/config', '/api/v1/logs/export']
  const ips = ['10.20.1.15', '172.16.8.3', '192.168.1.88', '10.20.3.27']
  const results = ['success', 'success', 'success', 'denied', 'failed']
  const rows: AuditLogRow[] = []
  const base = new Date('2026-08-27T12:00:00')
  for (let i = 1; i <= 32; i++) {
    const time = new Date(base.getTime() - i * 9 * 60 * 1000)
    rows.push({
      id: i,
      time: formatTime(time),
      action: actions[(i * 3) % actions.length],
      method: methods[(i * 2) % methods.length],
      path: paths[(i * 5) % paths.length],
      source_ip: ips[(i * 7) % ips.length],
      result: results[(i * 3) % results.length],
    })
  }
  return rows
}

function formatTime(date: Date) {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function permissionType(permission: string) {
  return { 只读: 'info', 读写: 'warning', 管理: 'danger' }[permission] || 'info'
}

function methodType(method: string) {
  return { GET: 'success', POST: 'warning', PUT: 'primary', DELETE: 'danger' }[method] || 'info'
}

function resultType(result: string) {
  return { success: 'success', denied: 'warning', failed: 'danger' }[result] || 'info'
}

function resultLabel(result: string) {
  return { success: '成功', denied: '拒绝', failed: '失败' }[result] || result
}

function openCreateDialog() {
  keyForm.name = ''
  keyForm.permission = '只读'
  keyForm.expiresAt = ''
  createVisible.value = true
}

function createKey() {
  const name = keyForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入密钥名称')
    return
  }
  if (apiKeys.value.some((key) => key.name === name)) {
    errorMsg.value = `密钥名称「${name}」已存在`
    return
  }
  const token = generateToken()
  latestToken.value = token
  apiKeys.value.unshift({
    id: Date.now(),
    name,
    token_prefix: token.slice(0, 16),
    permission: keyForm.permission,
    status: 'active',
    created_at: nowText(),
    expires_at: keyForm.expiresAt || '永不过期',
  })
  createVisible.value = false
  errorMsg.value = ''
  ElMessage.success('密钥创建成功')
  tokenVisible.value = true
}

function generateToken() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  const parts: string[] = []
  for (let i = 0; i < 3; i++) {
    let part = ''
    for (let j = 0; j < 16; j++) {
      part += chars[Math.floor(Math.random() * chars.length)]
    }
    parts.push(part)
  }
  return `ob-${parts.join('-')}`
}

function nowText() {
  const date = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

async function copyToken() {
  try {
    await navigator.clipboard.writeText(latestToken.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

function openDetail(row: ApiKeyRow) {
  detailRow.value = row
  detailVisible.value = true
}

function removeKey(id: number) {
  apiKeys.value = apiKeys.value.filter((key) => key.id !== id)
  ElMessage.success('密钥已删除')
}

function exportCsv() {
  if (filteredLogs.value.length === 0) {
    logError.value = '暂无可导出的审计日志'
    return
  }
  const headers = ['时间', '操作', '方法', '路径', '来源 IP', '结果']
  const body = filteredLogs.value.map((log) => [
    log.time,
    log.action,
    log.method,
    log.path,
    log.source_ip,
    resultLabel(log.result),
  ])
  const csv = [headers, ...body]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `audit-logs-${nowText().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${filteredLogs.value.length} 条审计日志`)
}

onMounted(() => {
  // 模拟拉取网关数据
  window.setTimeout(() => {
    loading.value = false
  }, 500)
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.tab-hint { color: var(--ob-text-secondary); font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
.token-prefix { background: #f5f7fa; padding: 2px 6px; border-radius: 4px; font-size: 12px; color: var(--el-text-color-regular); }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 12px; }
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
