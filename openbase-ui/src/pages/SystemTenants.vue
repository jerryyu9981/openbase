<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索租户（编码/名称）" clearable style="width: 240px" data-test="tenant-search" />
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px">
        <el-option label="启用" value="1" />
        <el-option label="停用" value="0" />
      </el-select>
      <el-button type="primary" data-test="create-tenant" @click="openForm()">创建租户</el-button>
    </div>
    <div class="ob-table-scroll">
      <el-table v-loading="loading" :data="paged" stripe data-test="tenant-table">
        <el-table-column prop="code" label="租户编码" min-width="130" />
        <el-table-column prop="name" label="租户名称" min-width="160" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="配额" min-width="160">
          <template #default="{ row }">
            <span class="quota-summary">{{ quotaSummary(row.quota) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="tenant-quota" @click="openQuota(row)">配额</el-button>
            <el-button link type="primary" @click="toggle(row)">{{ row.status === 1 ? '停用' : '启用' }}</el-button>
            <el-popconfirm title="确认停用该租户？" @confirm="remove(row)">
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="paged.length === 0 && !loading" description="暂无租户" :image-size="60" />
    </div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="filtered.length"
        layout="total, prev, pager, next"
        background
      />
    </div>

    <el-dialog v-model="formVisible" :title="editingId ? '编辑租户' : '创建租户'" width="480px" data-test="tenant-dialog">
      <el-form label-width="100px">
        <el-form-item label="租户编码" required><el-input v-model="form.code" placeholder="如：tenant_a" :disabled="!!editingId" data-test="tenant-code-input" /></el-form-item>
        <el-form-item label="租户名称" required><el-input v-model="form.name" placeholder="如：A 公司" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="tenant-submit" @click="saveTenant">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="quotaVisible" :title="`配额管理：${currentTenant?.name || ''}`" width="520px" data-test="quota-dialog">
      <el-form label-width="110px">
        <el-form-item label="配额配置（JSON）">
          <el-input v-model="quotaText" type="textarea" :rows="4" placeholder="{&quot;users&quot;: 100, &quot;storage&quot;: 1024}" data-test="quota-input" />
        </el-form-item>
        <el-form-item label="当前配置">
          <span class="quota-summary">{{ quotaSummary(currentTenant?.quota) || '未配置' }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quotaVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="quota-submit" @click="saveQuota">保存配额</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/core/api/http'

interface Tenant { id: number; code: string; name: string; status: number; quota: Record<string, number> | null; created_at: string }

const keyword = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = 8
const loading = ref(false)
const saving = ref(false)
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const quotaVisible = ref(false)
const currentTenant = ref<Tenant | null>(null)
const form = reactive({ code: '', name: '', status: 1 })
const quotaText = ref('{}')

const tenants = ref<Tenant[]>([])

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return tenants.value.filter((t) => {
    const matchKw = !kw || t.code.toLowerCase().includes(kw) || t.name.toLowerCase().includes(kw)
    const matchStatus = statusFilter.value === '' || String(t.status) === statusFilter.value
    return matchKw && matchStatus
  })
})
const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

function quotaSummary(quota: Record<string, number> | null | undefined): string {
  if (!quota) return ''
  return Object.entries(quota)
    .map(([k, v]) => `${k}: ${v}`)
    .join('，')
}

async function loadTenants() {
  loading.value = true
  try {
    const { data } = await http.get<Tenant[]>('/tenants')
    tenants.value = data
  } finally {
    loading.value = false
  }
}

function openForm(t?: Tenant) {
  editingId.value = t?.id ?? null
  form.code = t?.code ?? ''
  form.name = t?.name ?? ''
  form.status = t?.status ?? 1
  formVisible.value = true
}

async function saveTenant() {
  if (!form.code.trim() || !form.name.trim()) { ElMessage.warning('请输入租户编码与名称'); return }
  saving.value = true
  try {
    if (editingId.value) {
      await http.put(`/tenants/${editingId.value}`, { name: form.name.trim(), status: form.status })
      ElMessage.success('租户已更新')
    } else {
      await http.post('/tenants', { code: form.code.trim(), name: form.name.trim(), status: form.status })
      ElMessage.success('租户已创建')
    }
    formVisible.value = false
    await loadTenants()
  } catch {
    /* 拦截器已提示错误 */
  } finally {
    saving.value = false
  }
}

async function toggle(t: Tenant) {
  const next = t.status === 1 ? 0 : 1
  await http.put(`/tenants/${t.id}`, { status: next })
  t.status = next
  ElMessage.success(`${t.name} 已${next === 1 ? '启用' : '停用'}`)
}

async function remove(t: Tenant) {
  await http.delete(`/tenants/${t.id}`)
  ElMessage.success('租户已停用')
  await loadTenants()
}

function openQuota(t: Tenant) {
  currentTenant.value = t
  quotaText.value = t.quota ? JSON.stringify(t.quota, null, 2) : '{}'
  quotaVisible.value = true
}

async function saveQuota() {
  if (!currentTenant.value) return
  let parsed: Record<string, number>
  try {
    parsed = JSON.parse(quotaText.value || '{}')
  } catch {
    ElMessage.error('配额 JSON 格式不正确')
    return
  }
  saving.value = true
  try {
    const { data } = await http.put<Tenant>(`/tenants/${currentTenant.value.id}/quota`, { quota: parsed })
    currentTenant.value.quota = data.quota
    ElMessage.success('配额已保存')
    quotaVisible.value = false
    await loadTenants()
  } finally {
    saving.value = false
  }
}

onMounted(loadTenants)
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pager { margin-top: 8px; display: flex; justify-content: flex-end; }
.quota-summary { color: var(--el-text-color-secondary); font-size: 12px; }
</style>
