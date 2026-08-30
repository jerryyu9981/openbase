<template>
  <div class="roles-page">
    <div class="page-toolbar">
      <el-button type="primary" data-test="role-new" @click="openCreate">新建角色</el-button>
    </div>
    <el-card header="角色列表" data-test="role-card">
      <div class="ob-table-scroll">
        <el-table :data="roles" stripe empty-text="暂无角色" data-test="role-table">
          <el-table-column prop="name" label="角色名称" min-width="150" />
          <el-table-column prop="description" label="描述" min-width="200" />
          <el-table-column prop="permission_count" label="权限数" width="90" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" data-test="role-toggle" @change="toggle(row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="role-edit" @click="openEdit(row)">编辑</el-button>
              <el-button link type="primary" size="small" data-test="role-perms" @click="openPerms(row)">权限</el-button>
              <el-popconfirm title="确认删除该角色？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 新建/编辑 -->
    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑角色' : '新建角色'" width="480px" data-test="role-dialog">
      <el-form :model="form" label-width="70px">
        <el-form-item label="名称">
          <el-input v-model="form.name" data-test="role-name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" data-test="role-save" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 权限清单 -->
    <el-dialog v-model="permOpen" title="权限清单" width="560px" data-test="role-perms-dialog">
      <el-checkbox-group v-model="checkedPerms" class="perm-group">
        <el-checkbox v-for="p in allPerms" :key="p" :value="p" :label="p" />
      </el-checkbox-group>
      <template #footer>
        <el-button @click="permOpen = false">取消</el-button>
        <el-button type="primary" data-test="role-perms-save" @click="savePerms">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface Role {
  id: number
  name: string
  description: string
  permission_count: number
  enabled: boolean
}

const allPerms = [
  'user:list', 'user:create', 'user:update', 'user:delete',
  'role:list', 'role:create', 'role:update', 'role:delete',
  'model:list', 'model:create', 'model:deploy',
  'config:view', 'config:update',
  'gateway:view', 'gateway:register', 'gateway:aggregate',
]

const roles = ref<Role[]>([
  { id: 1, name: '超级管理员', description: '全部权限', permission_count: 16, enabled: true },
  { id: 2, name: '运营', description: '模型与用量管理', permission_count: 8, enabled: true },
  { id: 3, name: '开发', description: 'API 与网关管理', permission_count: 6, enabled: true },
  { id: 4, name: '审计员', description: '只读审计', permission_count: 3, enabled: false },
])

const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const form = ref({ name: '', description: '' })
const permOpen = ref(false)
const checkedPerms = ref<string[]>([])
const currentRole = ref<Role | null>(null)

function openCreate() {
  editingId.value = null
  form.value = { name: '', description: '' }
  dialogOpen.value = true
}

function openEdit(row: Role) {
  editingId.value = row.id
  form.value = { name: row.name, description: row.description }
  dialogOpen.value = true
}

function save() {
  if (!form.value.name) {
    ElMessage.warning('请填写角色名称')
    return
  }
  if (editingId.value) {
    const r = roles.value.find((x) => x.id === editingId.value)
    if (r) {
      r.name = form.value.name
      r.description = form.value.description
    }
    ElMessage.success('角色已更新')
  } else {
    const id = Math.max(0, ...roles.value.map((r) => r.id)) + 1
    roles.value.push({ id, name: form.value.name, description: form.value.description, permission_count: 0, enabled: true })
    ElMessage.success('角色已创建')
  }
  dialogOpen.value = false
}

function toggle(row: Role) {
  ElMessage.success(row.enabled ? '角色已启用' : '角色已停用')
}

function openPerms(row: Role) {
  currentRole.value = row
  checkedPerms.value = allPerms.slice(0, row.permission_count)
  permOpen.value = true
}

function savePerms() {
  if (currentRole.value) {
    currentRole.value.permission_count = checkedPerms.value.length
    ElMessage.success('权限清单已保存')
  }
  permOpen.value = false
}

function remove(id: number) {
  roles.value = roles.value.filter((r) => r.id !== id)
  ElMessage.success('角色已删除')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.perm-group { display: flex; flex-wrap: wrap; gap: 8px 20px; max-height: 360px; overflow: auto; }
</style>
