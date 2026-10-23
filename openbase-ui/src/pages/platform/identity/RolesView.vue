<template>
  <PageContainer title="角色与权限" description="角色档位与权限码绑定（OpenLLM RBAC）" test-id="roles-view-page">
    <div class="page-toolbar">
      <el-button type="primary" data-test="role-new" @click="openCreate">新建角色</el-button>
      <el-button :loading="loading" data-test="role-refresh" @click="loadRoles">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="role-error"
      @close="errorMessage = ''"
    />

    <el-card header="角色列表" data-test="role-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="roles" stripe data-test="role-table">
          <template #empty>
            <el-empty description="暂无角色" :image-size="60" data-test="role-empty" />
          </template>
          <el-table-column label="角色名称" min-width="160">
            <template #default="{ row }">
              {{ row.name }}
              <el-tag v-if="row.is_system" size="small" type="info" class="ml-6">系统</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="code" label="编码" width="140" />
          <el-table-column label="类型" width="100">
            <template #default="{ row }">{{ roleTypeLabel(row.role_type) }}</template>
          </el-table-column>
          <el-table-column prop="level" label="层级" width="80" />
          <el-table-column label="作用范围" width="100">
            <template #default="{ row }">{{ scopeLabel(row.scope) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-switch
                v-model="row.is_active"
                :disabled="row.is_system"
                data-test="role-toggle"
                @change="toggle(row)"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" :disabled="row.is_system" data-test="role-edit" @click="openEdit(row)">
                编辑
              </el-button>
              <el-button link type="primary" size="small" data-test="role-perms" @click="openPerms(row)">权限</el-button>
              <el-popconfirm
                title="确认删除该角色？"
                :disabled="row.is_system"
                @confirm="remove(row.id)"
              >
                <template #reference>
                  <el-button link type="danger" size="small" :disabled="row.is_system" data-test="role-delete">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑角色' : '新建角色'" width="520px" data-test="role-dialog">
      <el-form :model="form" label-width="90px">
        <el-form-item label="角色编码" required>
          <el-input v-model="form.code" :disabled="!!editingId" placeholder="如：org_admin" data-test="role-code" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" data-test="role-name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" data-test="role-description" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.role_type" style="width: 100%" data-test="role-type">
            <el-option v-for="item in ROLE_TYPES" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="层级">
          <el-input-number v-model="form.level" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="作用范围">
          <el-select v-model="form.scope" style="width: 100%">
            <el-option v-for="item in SCOPES" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="role-save" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="permOpen" :title="`权限清单 - ${currentRole?.name || ''}`" width="640px" data-test="role-perms-dialog">
      <div v-loading="permLoading">
        <el-empty v-if="catalog.length === 0" description="暂无权限目录数据" :image-size="60" />
        <el-checkbox-group v-else v-model="checkedPermIds" class="perm-group">
          <el-checkbox v-for="item in catalog" :key="item.id" :value="item.id">
            {{ item.code }} · {{ item.name }}
          </el-checkbox>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="permOpen = false">取消</el-button>
        <el-button type="primary" :loading="permSaving" data-test="role-perms-save" @click="savePerms">保存</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  rolesApi,
  type LlmPermissionCatalogItem,
  type LlmRole,
} from '@/core/api/governance'

/**
 * 角色与权限（v1.9.5 R5 真实化）：`/roles` 列表/新建/更新/删除 + `/roles/permissions/catalog`
 * 权限目录 + `PUT /roles/{id}/permissions` 分配。系统内置角色仅可查看权限，不允许改名/删除。
 */
const ROLE_TYPES = [
  { value: 'platform', label: '平台' },
  { value: 'org', label: '组织' },
  { value: 'team', label: '团队' },
  { value: 'custom', label: '自定义' },
]
const SCOPES = [
  { value: 'own', label: '本人' },
  { value: 'team', label: '团队' },
  { value: 'org', label: '组织' },
  { value: 'platform', label: '平台' },
]

const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const roles = ref<LlmRole[]>([])

const dialogOpen = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({
  code: '',
  name: '',
  description: '',
  role_type: 'custom',
  level: 0,
  scope: 'own',
})

const permOpen = ref(false)
const permLoading = ref(false)
const permSaving = ref(false)
const currentRole = ref<LlmRole | null>(null)
const catalog = ref<LlmPermissionCatalogItem[]>([])
const checkedPermIds = ref<string[]>([])

function roleTypeLabel(type: string) {
  return ROLE_TYPES.find((item) => item.value === type)?.label || type
}
function scopeLabel(scope: string) {
  return SCOPES.find((item) => item.value === scope)?.label || scope
}

async function loadRoles() {
  loading.value = true
  errorMessage.value = ''
  try {
    roles.value = await rolesApi.list({ limit: 200 })
  } catch (error) {
    errorMessage.value = `角色列表加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

function openCreate() {
  errorMessage.value = ''
  editingId.value = null
  form.code = ''
  form.name = ''
  form.description = ''
  form.role_type = 'custom'
  form.level = 0
  form.scope = 'own'
  dialogOpen.value = true
}

function openEdit(row: LlmRole) {
  errorMessage.value = ''
  editingId.value = row.id
  form.code = row.code
  form.name = row.name
  form.description = row.description || ''
  form.role_type = row.role_type
  form.level = row.level
  form.scope = row.scope
  dialogOpen.value = true
}

async function save() {
  if (!form.code.trim() || !form.name.trim()) {
    ElMessage.warning('请填写角色编码与名称')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await rolesApi.update(editingId.value, {
        name: form.name.trim(),
        description: form.description || undefined,
        level: form.level,
        scope: form.scope,
      })
      ElMessage.success('角色已更新')
    } else {
      await rolesApi.create({
        code: form.code.trim(),
        name: form.name.trim(),
        description: form.description || undefined,
        role_type: form.role_type,
        level: form.level,
        scope: form.scope,
      })
      ElMessage.success('角色已创建')
    }
    dialogOpen.value = false
    await loadRoles()
  } catch (error) {
    errorMessage.value = `角色保存失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    saving.value = false
  }
}

async function toggle(row: LlmRole) {
  const next = row.is_active
  if (row.is_system) return
  try {
    await rolesApi.update(row.id, { is_active: next })
    ElMessage.success(next ? '角色已启用' : '角色已停用')
  } catch (error) {
    row.is_active = !next
    errorMessage.value = `角色状态更新失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function remove(roleId: string) {
  if (!roleId) return
  try {
    await rolesApi.remove(roleId)
    ElMessage.success('角色已删除')
    await loadRoles()
  } catch (error) {
    errorMessage.value = `角色删除失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function openPerms(row: LlmRole) {
  errorMessage.value = ''
  currentRole.value = row
  permOpen.value = true
  permLoading.value = true
  try {
    const [items, detail] = await Promise.all([rolesApi.catalog(), rolesApi.detail(row.id)])
    catalog.value = items
    checkedPermIds.value = detail.permissions.map((item) => item.permission_id)
  } catch (error) {
    errorMessage.value = `权限清单加载失败：${error instanceof Error ? error.message : '未知错误'}`
    permOpen.value = false
  } finally {
    permLoading.value = false
  }
}

async function savePerms() {
  if (!currentRole.value) return
  permSaving.value = true
  try {
    await rolesApi.setPermissions(currentRole.value.id, checkedPermIds.value)
    ElMessage.success('权限清单已保存')
    permOpen.value = false
  } catch (error) {
    errorMessage.value = `权限保存失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    permSaving.value = false
  }
}

onMounted(loadRoles)
</script>

<style scoped>
.perm-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  max-height: 420px;
  overflow: auto;
}
.mb-16 { margin-bottom: 16px; }
.ml-6 { margin-left: 6px; }
</style>
