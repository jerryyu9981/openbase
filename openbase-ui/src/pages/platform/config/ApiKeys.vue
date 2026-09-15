<template>
  <div>
    <div class="page-toolbar">
      <el-button type="primary" data-test="create-api-key" @click="openCreate">创建密钥</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="api-keys-error"
      @close="errorMessage = ''"
    />

    <div v-loading="loading" class="ob-table-scroll">
      <el-table :data="apiKeys" stripe data-test="api-keys-table">
        <template #empty>
          <el-empty description="暂无 API 密钥，点击右上角创建" :image-size="60" data-test="api-keys-empty" />
        </template>
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column label="模型权限" min-width="190">
          <template #default="{ row }">
            <el-tag v-for="model in row.model_permissions" :key="model" size="small" class="perm-tag" type="info">{{ model }}</el-tag>
            <span v-if="!row.model_permissions.length" class="text-muted">全部模型</span>
          </template>
        </el-table-column>
        <el-table-column label="速率限制" width="110">
          <template #default="{ row }">{{ row.rate_limit }} rps</template>
        </el-table-column>
        <el-table-column label="过期时间" width="120">
          <template #default="{ row }">
            <span>{{ row.expires_at || '永不过期' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="view-api-key" @click="openDetail(row)">详情</el-button>
            <el-popconfirm title="确认删除该密钥？删除后所有关联调用将立即失效" @confirm="remove(row.id)">
              <template #reference>
                <el-button link type="danger" data-test="delete-api-key">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="createVisible" title="创建 API 密钥" width="520px" data-test="create-api-key-dialog">
      <el-form label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：生产环境密钥" maxlength="50" data-test="api-key-name-input" />
        </el-form-item>
        <el-form-item label="模型权限">
          <el-select
            v-model="form.model_permissions"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="不选则默认授予全部模型权限"
            style="width: 100%"
            data-test="api-key-models-select"
          >
            <el-option v-for="model in mockModels" :key="model" :label="model" :value="model" />
          </el-select>
        </el-form-item>
        <el-form-item label="速率限制">
          <el-input-number v-model="form.rate_limit" :min="1" :max="1000" :step="10" style="width: 100%" data-test="api-key-rate-input" />
          <div class="text-muted">单位：请求/秒（rps）</div>
        </el-form-item>
        <el-form-item label="过期时间">
          <el-date-picker
            v-model="form.expires_at"
            type="date"
            placeholder="选择过期日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
            data-test="api-key-expire-picker"
          />
          <div class="text-muted">留空表示永不过期</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" data-test="create-api-key-submit" @click="saveKey">创建</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="密钥详情" size="420px" data-test="api-key-detail-drawer">
      <el-descriptions v-if="detailRow" :column="1" border data-test="api-key-detail-desc">
        <el-descriptions-item label="名称">{{ detailRow?.name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(detailRow?.status || 'active')" size="small">{{ statusLabel(detailRow?.status || 'active') }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="完整密钥">
          <span v-if="detailRow?.full_key" class="key-text" data-test="api-key-full-text">{{ detailRow.full_key }}</span>
          <span v-else class="text-muted">{{ detailRow?.key_masked }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="模型权限">
          <template v-if="detailRow?.model_permissions.length">
            <el-tag v-for="model in detailRow?.model_permissions" :key="model" size="small" class="perm-tag" type="info">{{ model }}</el-tag>
          </template>
          <span v-else class="text-muted">全部模型</span>
        </el-descriptions-item>
        <el-descriptions-item label="速率限制">{{ detailRow?.rate_limit }} rps</el-descriptions-item>
        <el-descriptions-item label="过期时间">{{ detailRow?.expires_at || '永不过期' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ detailRow?.created_at }}</el-descriptions-item>
      </el-descriptions>
      <div class="drawer-footer">
        <el-button v-if="detailRow?.full_key" type="primary" data-test="copy-api-key" @click="copyKey(detailRow)">复制密钥</el-button>
        <span v-if="!detailRow?.full_key" class="text-muted">完整密钥仅在创建时展示一次，出于安全考虑不再提供明文查看</span>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ApiKeyRow {
  id: number
  name: string
  model_permissions: string[]
  rate_limit: number
  expires_at: string
  status: string
  created_at: string
  /** 完整密钥明文：仅新建时临时保留，用于创建后唯一一次展示 */
  full_key: string
  /** 列表中展示的脱敏密钥 */
  key_masked: string
}

const mockModels = ['gpt-4o', 'gpt-4o-mini', 'qwen2.5-7b', 'claude-3-5-sonnet', 'bge-m3']

const loading = ref(true)
const errorMessage = ref('')
const createVisible = ref(false)
const detailVisible = ref(false)
const detailRow = ref<ApiKeyRow | null>(null)

const form = reactive({
  name: '',
  model_permissions: [] as string[],
  rate_limit: 60,
  expires_at: '',
})

/** 契约 mock：本地密钥数据（不调用真实 API） */
const apiKeys = ref<ApiKeyRow[]>([
  {
    id: 1,
    name: '生产环境密钥',
    model_permissions: ['gpt-4o', 'gpt-4o-mini'],
    rate_limit: 120,
    expires_at: '2027-08-27',
    status: 'active',
    created_at: '2026-08-01 10:00',
    full_key: '',
    key_masked: 'ob-••••••••••••••••••••••••••••••••',
  },
  {
    id: 2,
    name: '测试环境密钥',
    model_permissions: [],
    rate_limit: 30,
    expires_at: '',
    status: 'active',
    created_at: '2026-08-10 14:30',
    full_key: '',
    key_masked: 'ob-••••••••••••••••••••••••••••••••',
  },
  {
    id: 3,
    name: '已过期密钥',
    model_permissions: ['qwen2.5-7b'],
    rate_limit: 10,
    expires_at: '2026-06-30',
    status: 'expired',
    created_at: '2026-05-01 09:00',
    full_key: '',
    key_masked: 'ob-••••••••••••••••••••••••••••••••',
  },
])

function statusType(status: string) {
  return { active: 'success', expired: 'info', revoked: 'danger' }[status] || 'info'
}
function statusLabel(status: string) {
  return { active: '有效', expired: '已过期', revoked: '已吊销' }[status] || status
}
function maskKey(fullKey: string): string {
  return `${fullKey.slice(0, 6)}••••••••••••••••••••••••••••••••`
}
function generateKey(): string {
  const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
  let randomPart = ''
  for (let index = 0; index < 32; index += 1) {
    randomPart += charset[Math.floor(Math.random() * charset.length)]
  }
  return `ob-${randomPart}`
}
function nowText(): string {
  return new Date().toISOString().slice(0, 16).replace('T', ' ')
}

function openCreate() {
  errorMessage.value = ''
  form.name = ''
  form.model_permissions = []
  form.rate_limit = 60
  form.expires_at = ''
  createVisible.value = true
}

function saveKey() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入密钥名称')
    return
  }
  const fullKey = generateKey()
  const newKey: ApiKeyRow = {
    id: Date.now(),
    name: form.name.trim(),
    model_permissions: [...form.model_permissions],
    rate_limit: form.rate_limit,
    expires_at: form.expires_at,
    status: 'active',
    created_at: nowText(),
    full_key: fullKey,
    key_masked: maskKey(fullKey),
  }
  apiKeys.value.push(newKey)
  createVisible.value = false
  ElMessage.success('创建成功，密钥仅展示一次')
  detailRow.value = newKey
  detailVisible.value = true
}

function openDetail(row: ApiKeyRow) {
  if (!row.full_key) {
    // 安全策略：完整明文仅创建时展示一次
    errorMessage.value = '该密钥的完整明文已在创建时展示过一次，出于安全考虑不再提供查看'
    return
  }
  errorMessage.value = ''
  detailRow.value = row
  detailVisible.value = true
}

async function copyKey(row: ApiKeyRow) {
  if (!row.full_key) return
  try {
    await navigator.clipboard.writeText(row.full_key)
    ElMessage.success('密钥已复制到剪贴板')
  } catch (_error) {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

function remove(id: number) {
  const target = apiKeys.value.find((item) => item.id === id)
  apiKeys.value = apiKeys.value.filter((item) => item.id !== id)
  ElMessage.success(`密钥「${target?.name || ''}」已删除`)
}

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

onMounted(async () => {
  loading.value = true
  await mockDelay(500) // 契约 mock：模拟加载密钥列表
  loading.value = false
})
</script>

<style scoped>
.page-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.mb-16 {
  margin-bottom: 16px;
}
.perm-tag {
  margin-right: 4px;
}
.text-muted {
  color: var(--ob-text-secondary);
}
.key-text {
  font-family: monospace;
  word-break: break-all;
  user-select: all;
}
.drawer-footer {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
