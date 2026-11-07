<template>
  <PageContainer
    title="Agent 管理"
    description="统一身份 Agent 主体与 sk-agent-* 密钥管理（数据源：OpenBase /api/v1/identity/agents）"
    test-id="agent-manage-page"
  >
    <div class="page-toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索用户名 / 显示名 / 租户"
        clearable
        style="width: 240px"
        data-test="agent-search"
      />
      <el-button :loading="loading" data-test="agent-reload" @click="load">刷新</el-button>
      <el-button v-if="canManage" type="primary" data-test="agent-create" @click="openCreate">
        新建 Agent
      </el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="agent-error"
      @close="errorMessage = ''"
    />

    <el-card header="Agent 主体（删除为软删：status=0 / suspended，并吊销全部有效密钥）">
      <div class="ob-table-scroll">
        <el-table
          v-loading="loading"
          :data="filteredAgents"
          row-key="id"
          stripe
          empty-text="暂无 Agent"
          data-test="agent-table"
        >
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="username" label="用户名" min-width="140">
            <template #default="{ row }">
              <code>{{ row.username }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="display_name" label="显示名" min-width="140" />
          <el-table-column label="租户" min-width="110">
            <template #default="{ row }">{{ row.tenant_code || '—' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="170">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 1 ? 'success' : 'info'">
                {{ row.status === 1 ? '启用' : '停止' }}
              </el-tag>
              <span class="state-text">{{ row.status_state }}</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="agent-keys" @click="openKeys(row)">
                密钥
              </el-button>
              <el-button
                v-if="canManage"
                link
                type="danger"
                size="small"
                :disabled="row.status === 0"
                data-test="agent-delete"
                @click="remove(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="createOpen" title="新建 Agent" width="520px" data-test="agent-create-dialog">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="用户名">
          <el-input
            v-model="createForm.username"
            placeholder="字母/数字/_.:-，2~64 位"
            data-test="agent-username"
          />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="createForm.display_name" placeholder="如 报表助手" data-test="agent-display-name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-input v-model="createForm.role" placeholder="默认 viewer" data-test="agent-role" />
        </el-form-item>
        <el-form-item label="密钥名称">
          <el-input v-model="createForm.key_name" placeholder="可选，默认取显示名" data-test="agent-key-name" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="agent-create-submit" @click="submitCreate">
          创建
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="revealOpen" title="密钥明文（仅显示一次）" width="560px" data-test="agent-reveal-dialog">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="请立即复制保存。关闭后无法再次查看，遗失只能重新签发。"
        class="mb-16"
      />
      <code class="raw-key" data-test="agent-reveal-key">{{ revealedKey }}</code>
      <template #footer>
        <el-button data-test="agent-reveal-copy" @click="copyKey">复制</el-button>
        <el-button type="primary" @click="revealOpen = false">我已保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="keysOpen" :title="`密钥：${keysAgent?.username ?? ''}`" size="520px" data-test="agent-key-drawer">
      <div class="drawer-toolbar">
        <el-button :loading="keysLoading" data-test="agent-keys-reload" @click="loadKeys">刷新</el-button>
        <el-button v-if="canManage" type="primary" data-test="agent-key-issue" @click="issueKey">
          签发新密钥
        </el-button>
      </div>
      <el-table
        v-loading="keysLoading"
        :data="keys"
        row-key="id"
        empty-text="暂无密钥"
        data-test="agent-key-table"
      >
        <el-table-column prop="name" label="名称" min-width="110">
          <template #default="{ row }">{{ row.name || '—' }}</template>
        </el-table-column>
        <el-table-column label="密钥" min-width="160">
          <template #default="{ row }">
            <code>{{ row.key_prefix }}…{{ row.key_suffix || '' }}</code>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button
              v-if="canManage && row.status === 'active'"
              link
              type="danger"
              size="small"
              data-test="agent-key-revoke"
              @click="revokeKey(row)"
            >
              吊销
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentsApi, type AgentItem, type AgentKey } from '@/core/api/agents'
import { useAuthStore } from '@/core/stores/auth'

const auth = useAuthStore()

const agents = ref<AgentItem[]>([])
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')

const createOpen = ref(false)
const createForm = ref<{ username: string; display_name: string; role: string; key_name: string }>({
  username: '',
  display_name: '',
  role: 'viewer',
  key_name: '',
})

const revealOpen = ref(false)
const revealedKey = ref('')

const keysOpen = ref(false)
const keysLoading = ref(false)
const keysAgent = ref<AgentItem | null>(null)
const keys = ref<AgentKey[]>([])

const canManage = computed(() => auth.hasPermission('identity:manage'))

const filteredAgents = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return agents.value
  return agents.value.filter(
    (item) =>
      item.username.toLowerCase().includes(kw) ||
      item.display_name.toLowerCase().includes(kw) ||
      (item.tenant_code ?? '').toLowerCase().includes(kw),
  )
})

function messageOf(error: unknown, fallback: string): string {
  const payload = (error as { response?: { data?: { message?: string } } }).response?.data
  if (payload?.message) return payload.message
  if (error instanceof Error && error.message) return error.message
  return fallback
}

function formatTime(value: string | null): string {
  if (!value) return '—'
  return value.replace('T', ' ').slice(0, 19)
}

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    agents.value = await agentsApi.list({ page: 1, page_size: 100 })
  } catch (error) {
    errorMessage.value = `Agent 列表加载失败：${messageOf(error, '未知错误')}`
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  createForm.value = { username: '', display_name: '', role: 'viewer', key_name: '' }
  createOpen.value = true
}

async function submitCreate(): Promise<void> {
  const username = createForm.value.username.trim()
  const displayName = createForm.value.display_name.trim()
  if (!username || !displayName) {
    ElMessage.warning('用户名与显示名均不能为空')
    return
  }
  saving.value = true
  try {
    const created = await agentsApi.create({
      username,
      display_name: displayName,
      role: createForm.value.role.trim() || 'viewer',
      key_name: createForm.value.key_name.trim() || undefined,
    })
    createOpen.value = false
    revealedKey.value = created.api_key?.raw_key ?? ''
    revealOpen.value = Boolean(revealedKey.value)
    ElMessage.success(`Agent ${created.username} 已创建`)
    await load()
  } catch (error) {
    errorMessage.value = `创建 Agent 失败：${messageOf(error, '未知错误')}`
  } finally {
    saving.value = false
  }
}

async function remove(row: AgentItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认删除 Agent ${row.username}？将执行软删除并吊销其全部有效密钥。`,
      '删除 Agent',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const result = await agentsApi.remove(row.id)
    ElMessage.success(`Agent ${row.username} 已删除，吊销密钥 ${result.revoked_keys} 条`)
    await load()
  } catch (error) {
    errorMessage.value = `删除 Agent 失败：${messageOf(error, '未知错误')}`
  }
}

async function openKeys(row: AgentItem): Promise<void> {
  keysAgent.value = row
  keys.value = []
  keysOpen.value = true
  await loadKeys()
}

async function loadKeys(): Promise<void> {
  if (!keysAgent.value) return
  keysLoading.value = true
  try {
    keys.value = await agentsApi.listKeys(keysAgent.value.id)
  } catch (error) {
    keys.value = []
    errorMessage.value = `密钥列表加载失败：${messageOf(error, '未知错误')}`
  } finally {
    keysLoading.value = false
  }
}

async function issueKey(): Promise<void> {
  if (!keysAgent.value) return
  try {
    const record = await agentsApi.issueKey(keysAgent.value.id, { name: 'rotated' })
    revealedKey.value = record.raw_key ?? ''
    revealOpen.value = Boolean(revealedKey.value)
    ElMessage.success('密钥已签发')
    await loadKeys()
  } catch (error) {
    errorMessage.value = `签发密钥失败：${messageOf(error, '未知错误')}`
  }
}

async function revokeKey(row: AgentKey): Promise<void> {
  if (!keysAgent.value) return
  try {
    await ElMessageBox.confirm(`确认吊销密钥 ${row.key_prefix}…？吊销后立即失效。`, '吊销密钥', {
      type: 'warning',
      confirmButtonText: '吊销',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await agentsApi.revokeKey(keysAgent.value.id, row.id)
    ElMessage.success('密钥已吊销')
    await loadKeys()
  } catch (error) {
    errorMessage.value = `吊销密钥失败：${messageOf(error, '未知错误')}`
  }
}

async function copyKey(): Promise<void> {
  try {
    await navigator.clipboard.writeText(revealedKey.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选中复制')
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.state-text { margin-left: 6px; color: var(--ob-text-secondary); font-size: 12px; }
.raw-key { display: block; padding: 10px; background: var(--el-fill-color-light); word-break: break-all; }
.drawer-toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
</style>
