<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索租户（编码/名称）" clearable style="width: 240px" data-test="tenant-search" />
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px">
        <el-option label="启用" value="active" />
        <el-option label="停用" value="inactive" />
      </el-select>
      <el-button type="primary" data-test="create-tenant" @click="openForm()">创建租户</el-button>
    </div>
    <div class="ob-table-scroll">
      <el-table :data="paged" stripe data-test="tenant-table">
        <el-table-column prop="code" label="租户编码" min-width="130" />
        <el-table-column prop="name" label="租户名称" min-width="160" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="user_count" label="用户数" width="90" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="tenant-quota" @click="openQuota(row)">配额</el-button>
            <el-button link type="primary" @click="toggle(row)">{{ row.status === 'active' ? '停用' : '启用' }}</el-button>
            <el-popconfirm title="确认删除该租户？" @confirm="remove(row.id)">
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="paged.length === 0" description="暂无租户" :image-size="60" />
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
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" data-test="tenant-submit" @click="saveTenant">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="quotaVisible" :title="`配额管理：${currentTenant?.name || ''}`" width="520px" data-test="quota-dialog">
      <el-form label-width="110px">
        <el-form-item label="资源">
          <el-select v-model="quotaForm.resource" style="width: 100%">
            <el-option label="models（模型数）" value="models" />
            <el-option label="tokens（Token 配额）" value="tokens" />
            <el-option label="seats（席位）" value="seats" />
          </el-select>
        </el-form-item>
        <el-form-item label="额度上限">
          <el-input-number v-model="quotaForm.limit" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="当前用量">
          <el-progress :percentage="usagePercent" :stroke-width="12" :color="usagePercent >= 90 ? '#dc2626' : '#16a34a'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quotaVisible = false">取消</el-button>
        <el-button type="primary" data-test="quota-submit" @click="saveQuota">保存配额</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface Tenant { id: number; code: string; name: string; status: string; user_count: number; created_at: string }

const keyword = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = 8
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const quotaVisible = ref(false)
const currentTenant = ref<Tenant | null>(null)
const form = reactive({ code: '', name: '', status: 'active' })
const quotaForm = reactive({ resource: 'models', limit: 100, usage: 0 })

const tenants = ref<Tenant[]>([
  { id: 1, code: 'tenant_demo', name: '演示租户', status: 'active', user_count: 12, created_at: '2026-08-20 10:00' },
  { id: 2, code: 'tenant_a', name: 'A 科技有限公司', status: 'active', user_count: 48, created_at: '2026-08-18 14:30' },
  { id: 3, code: 'tenant_b', name: 'B 咨询公司', status: 'inactive', user_count: 5, created_at: '2026-08-15 09:00' },
])

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return tenants.value.filter((t) => {
    const matchKw = !kw || t.code.toLowerCase().includes(kw) || t.name.toLowerCase().includes(kw)
    const matchStatus = !statusFilter.value || t.status === statusFilter.value
    return matchKw && matchStatus
  })
})
const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})
const usagePercent = computed(() => Math.min(100, Math.round((quotaForm.usage / Math.max(1, quotaForm.limit)) * 100)))

function openForm(t?: Tenant) {
  editingId.value = t?.id ?? null
  form.code = t?.code ?? ''
  form.name = t?.name ?? ''
  form.status = t?.status ?? 'active'
  formVisible.value = true
}
function saveTenant() {
  if (!form.code.trim() || !form.name.trim()) { ElMessage.warning('请输入租户编码与名称'); return }
  if (editingId.value) {
    const target = tenants.value.find((t) => t.id === editingId.value)
    if (target) { Object.assign(target, { name: form.name.trim(), status: form.status }); ElMessage.success('租户已更新') }
  } else {
    if (tenants.value.some((t) => t.code === form.code.trim())) { ElMessage.error('租户编码已存在'); return }
    tenants.value.push({ id: Date.now(), code: form.code.trim(), name: form.name.trim(), status: form.status, user_count: 0, created_at: new Date().toISOString().slice(0, 16).replace('T', ' ') })
    ElMessage.success('租户已创建')
  }
  formVisible.value = false
}
function toggle(t: Tenant) {
  t.status = t.status === 'active' ? 'inactive' : 'active'
  ElMessage.success(`${t.name} 已${t.status === 'active' ? '启用' : '停用'}`)
}
function remove(id: number) {
  tenants.value = tenants.value.filter((t) => t.id !== id)
  ElMessage.success('租户已删除')
}
function openQuota(t: Tenant) {
  currentTenant.value = t
  quotaForm.resource = 'models'
  quotaForm.limit = 100
  quotaForm.usage = Math.floor(Math.random() * 60)
  quotaVisible.value = true
}
function saveQuota() {
  ElMessage.success(`已为 ${currentTenant.value?.name} 设置 ${quotaForm.resource} 配额：${quotaForm.limit}`)
  quotaVisible.value = false
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pager { margin-top: 8px; display: flex; justify-content: flex-end; }
</style>
