<template>
  <PageContainer title="API 密钥" description="服务级 API Key 的创建与吊销（数据源：OpenBase /api/v1/auth/api-keys）" test-id="api-keys-page">
    <div class="page-toolbar">
      <el-button data-test="refresh-api-keys" :loading="loading" @click="load">刷新</el-button>
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

    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb-16"
      title="完整密钥仅在创建成功时展示一次；列表不回显明文。吊销按记录 id 执行，不依赖明文。"
      data-test="api-keys-notice"
    />

    <div v-loading="loading" class="ob-table-scroll">
      <el-table :data="apiKeys" stripe data-test="api-keys-table">
        <template #empty>
          <el-empty description="暂无 API 密钥，点击右上角创建" :image-size="60" data-test="api-keys-empty" />
        </template>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column label="访问范围" min-width="240">
          <template #default="{ row }">
            <div class="scope-row">
              <span class="scope-label">系统</span>
              <el-tag v-for="system in row.scope.system || []" :key="`s-${system}`" size="small" type="info" class="perm-tag">
                {{ system }}
              </el-tag>
            </div>
            <div class="scope-row">
              <span class="scope-label">租户</span>
              <el-tag v-for="tenant in row.scope.tenants || []" :key="`t-${tenant}`" size="small" class="perm-tag">
                {{ tenant }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="160">
          <template #default="{ row }">{{ row.description || '—' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatCreated(row.created) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.revoked ? 'danger' : 'success'" size="small">{{ row.revoked ? '已吊销' : '有效' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="view-api-key" @click="openDetail(row)">详情</el-button>
            <el-tooltip :disabled="canRevoke(row)" content="该密钥已吊销，无需重复操作" placement="top">
              <span>
                <el-popconfirm
                  title="确认吊销该密钥？关联调用将立即失效"
                  :disabled="!canRevoke(row)"
                  @confirm="revoke(row)"
                >
                  <template #reference>
                    <el-button link type="danger" :disabled="!canRevoke(row)" data-test="delete-api-key">吊销</el-button>
                  </template>
                </el-popconfirm>
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="createVisible" title="创建 API 密钥" width="560px" data-test="create-api-key-dialog">
      <el-form label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：生产环境密钥" maxlength="64" data-test="api-key-name-input" />
        </el-form-item>
        <el-form-item label="可访问系统">
          <el-select
            v-model="form.systems"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="不选默认 *（全部系统）"
            style="width: 100%"
            data-test="api-key-systems-select"
          >
            <el-option v-for="system in API_KEY_SYSTEM_OPTIONS" :key="system" :label="system" :value="system" />
          </el-select>
        </el-form-item>
        <el-form-item label="可访问租户">
          <el-select
            v-model="form.tenants"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="不选默认 *（全部租户）"
            style="width: 100%"
            data-test="api-key-tenants-select"
          >
            <el-option v-for="tenant in tenantOptions" :key="tenant" :label="tenant" :value="tenant" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" maxlength="200" placeholder="用途说明（可选）" data-test="api-key-desc-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" data-test="create-api-key-submit" @click="saveKey">创建</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="密钥详情" size="440px" data-test="api-key-detail-drawer">
      <el-descriptions v-if="detailRow" :column="1" border data-test="api-key-detail-desc">
        <el-descriptions-item label="名称">{{ detailRow.name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="detailRow.revoked ? 'danger' : 'success'" size="small">
            {{ detailRow.revoked ? '已吊销' : '有效' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="完整密钥">
          <span v-if="detailRow.key" class="key-text" data-test="api-key-full-text">{{ detailRow.key }}</span>
          <span v-else class="text-muted">创建时已展示过一次，列表不再提供明文</span>
        </el-descriptions-item>
        <el-descriptions-item label="可访问系统">
          <el-tag v-for="system in detailRow.scope.system || []" :key="`ds-${system}`" size="small" type="info" class="perm-tag">
            {{ system }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="可访问租户">
          <el-tag v-for="tenant in detailRow.scope.tenants || []" :key="`dt-${tenant}`" size="small" class="perm-tag">
            {{ tenant }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="描述">{{ detailRow.description || '—' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatCreated(detailRow.created) }}</el-descriptions-item>
      </el-descriptions>
      <div class="drawer-footer">
        <el-button v-if="detailRow?.key" type="primary" data-test="copy-api-key" @click="copyKey(detailRow)">复制密钥</el-button>
        <span v-if="!detailRow?.key" class="text-muted">完整密钥仅在创建时展示一次，出于安全考虑不再提供明文查看</span>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { API_KEY_SYSTEM_OPTIONS, apiKeysApi, type ApiKeyRecord } from '@/core/api/apiKeys'

const loading = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const createVisible = ref(false)
const detailVisible = ref(false)
const detailRow = ref<ApiKeyRecord | null>(null)

const apiKeys = ref<ApiKeyRecord[]>([])
/** 本次会话创建且仍持有明文 Key 的记录（仅这些可吊销） */
const ownedKeys = ref<Record<string, string>>({})
const tenantOptions = ref<string[]>([])

const form = reactive({
  name: '',
  systems: [] as string[],
  tenants: [] as string[],
  description: '',
})

function recordKey(record: ApiKeyRecord): string {
  return `${record.name}|${record.created}`
}

function formatCreated(created: number): string {
  if (!created) return '—'
  const date = new Date(created * 1000)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

function messageOf(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  return fallback
}

function canRevoke(record: ApiKeyRecord): boolean {
  return Boolean(record.id) && !record.revoked
}

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    apiKeys.value = await apiKeysApi.list()
    const tenants = new Set<string>()
    for (const record of apiKeys.value) {
      for (const tenant of record.scope.tenants || []) tenants.add(tenant)
    }
    tenantOptions.value = [...tenants]
  } catch (error) {
    errorMessage.value = `密钥列表加载失败：${messageOf(error, '未知错误')}`
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  errorMessage.value = ''
  form.name = ''
  form.systems = []
  form.tenants = []
  form.description = ''
  createVisible.value = true
}

async function saveKey(): Promise<void> {
  if (!form.name.trim()) {
    ElMessage.warning('请输入密钥名称')
    return
  }
  submitting.value = true
  try {
    const record = await apiKeysApi.create({
      name: form.name.trim(),
      scope: {
        system: form.systems.length ? [...form.systems] : ['*'],
        tenants: form.tenants.length ? [...form.tenants] : ['*'],
      },
      description: form.description.trim(),
    })
    if (record.key) ownedKeys.value[recordKey(record)] = record.key
    createVisible.value = false
    ElMessage.success('创建成功，密钥仅展示一次')
    detailRow.value = record
    detailVisible.value = true
    await load()
  } catch (error) {
    errorMessage.value = `创建失败：${messageOf(error, '未知错误')}`
  } finally {
    submitting.value = false
  }
}

function openDetail(record: ApiKeyRecord): void {
  errorMessage.value = ''
  detailRow.value = { ...record, key: ownedKeys.value[recordKey(record)] }
  detailVisible.value = true
}

async function copyKey(record: ApiKeyRecord): Promise<void> {
  if (!record.key) return
  try {
    await navigator.clipboard.writeText(record.key)
    ElMessage.success('密钥已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

async function revoke(record: ApiKeyRecord): Promise<void> {
  if (!record.id) {
    errorMessage.value = '该密钥缺少稳定标识，无法吊销'
    return
  }
  try {
    await apiKeysApi.revokeById(record.id)
    delete ownedKeys.value[recordKey(record)]
    ElMessage.success(`密钥「${record.name}」已吊销`)
    await load()
  } catch (error) {
    errorMessage.value = `吊销失败：${messageOf(error, '未知错误')}`
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.perm-tag { margin-right: 4px; }
.scope-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.scope-label { color: var(--ob-text-secondary); font-size: 12px; min-width: 28px; }
.text-muted { color: var(--ob-text-secondary); }
.key-text { font-family: monospace; word-break: break-all; user-select: all; }
.drawer-footer { margin-top: 16px; display: flex; align-items: center; gap: 12px; }
</style>
