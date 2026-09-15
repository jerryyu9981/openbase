<template>
  <div class="org-page">
    <el-row :gutter="16">
      <!-- 组织树（v1.4.2 保留占位，团队管理 v1.5 真实化） -->
      <el-col :span="8">
        <el-card header="组织架构" data-test="org-tree-card">
          <el-tree
            :data="orgTree"
            node-key="id"
            default-expand-all
            :props="{ label: 'name', children: 'children' }"
            data-test="org-tree"
            @node-click="selectOrg"
          />
          <div class="org-note">组织树为演示数据，团队管理随 v1.5 版本真实化</div>
        </el-card>
      </el-col>
      <!-- 用户列表（真实 API /api/v1/users） -->
      <el-col :span="16">
        <el-card header="用户管理" data-test="org-users-card">
          <div class="page-toolbar">
            <el-input v-model="keyword" placeholder="搜索用户名" clearable style="width: 200px" data-test="org-search" />
            <el-button type="primary" data-test="org-user-add" @click="addUser">新增用户</el-button>
          </div>
          <div class="ob-table-scroll">
            <el-table v-loading="loading" :data="filteredUsers" stripe empty-text="暂无用户" data-test="org-users-table">
              <el-table-column prop="username" label="用户名" min-width="120" />
              <el-table-column prop="display_name" label="姓名" min-width="100" />
              <el-table-column prop="email" label="邮箱" min-width="160" />
              <el-table-column label="角色" width="120">
                <template #default="{ row }">
                  <el-tag size="small">{{ roleLabel(row.roles) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">{{ row.status === 1 ? '启用' : '禁用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" data-test="org-user-edit" @click="editUser(row)">编辑</el-button>
                  <el-button link type="primary" size="small" @click="openRole(row)">分配角色</el-button>
                  <el-button link :type="row.status === 1 ? 'danger' : 'success'" size="small" @click="toggleUser(row)">
                    {{ row.status === 1 ? '禁用' : '启用' }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 用户弹窗 -->
    <el-dialog v-model="userDialog" :title="editingUser ? '编辑用户' : '新增用户'" width="480px" data-test="org-user-dialog">
      <el-form :model="userForm" label-width="70px">
        <el-form-item label="用户名">
          <el-input v-model="userForm.username" :disabled="!!editingUser" data-test="org-user-name" />
        </el-form-item>
        <el-form-item v-if="!editingUser" label="密码">
          <el-input v-model="userForm.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="userForm.display_name" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="userForm.email" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role" style="width: 100%">
            <el-option v-for="r in ['admin', 'org_admin', 'org_member', 'viewer']" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="org-user-save" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 角色分配弹窗 -->
    <el-dialog v-model="roleDialog" :title="`分配角色：${currentUser?.username || ''}`" width="360px">
      <el-select v-model="roleForm.role" style="width: 100%">
        <el-option v-for="r in ['admin', 'org_admin', 'org_member', 'viewer']" :key="r" :label="r" :value="r" />
      </el-select>
      <template #footer>
        <el-button @click="roleDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRole">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/core/api/http'

interface OrgNode {
  id: number
  name: string
  children?: OrgNode[]
}

interface UserRow {
  id: number
  username: string
  display_name: string
  email: string | null
  phone: string | null
  status: number
  tenant_id: number | null
  roles: string[]
}

const orgTree = ref<OrgNode[]>([
  { id: 1, name: '总公司', children: [{ id: 2, name: 'AI 平台部', children: [{ id: 3, name: '模型组' }, { id: 4, name: 'RAG 组' }] }, { id: 5, name: '运维部' }] },
])

const users = ref<UserRow[]>([])
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const userDialog = ref(false)
const roleDialog = ref(false)
const editingUser = ref<UserRow | null>(null)
const currentUser = ref<UserRow | null>(null)
const userForm = ref({ username: '', password: '', display_name: '', email: '', role: 'viewer' })
const roleForm = ref({ role: 'viewer' })

const filteredUsers = computed(() =>
  keyword.value ? users.value.filter((u) => u.username.includes(keyword.value) || (u.display_name || '').includes(keyword.value)) : users.value,
)

function roleLabel(roles: string[] | undefined): string {
  return roles && roles.length > 0 ? roles.join(', ') : 'viewer'
}

async function loadUsers() {
  loading.value = true
  try {
    const { data } = await http.get<UserRow[]>('/users')
    users.value = data
  } finally {
    loading.value = false
  }
}

function selectOrg() {
  /* 组织树为演示数据，选择不联动用户过滤（团队管理 v1.5 真实化） */
}

function addUser() {
  editingUser.value = null
  userForm.value = { username: '', password: '', display_name: '', email: '', role: 'viewer' }
  userDialog.value = true
}

function editUser(row: UserRow) {
  editingUser.value = row
  userForm.value = {
    username: row.username,
    password: '',
    display_name: row.display_name,
    email: row.email || '',
    role: roleLabel(row.roles),
  }
  userDialog.value = true
}

async function saveUser() {
  if (!userForm.value.username) {
    ElMessage.warning('请填写用户名')
    return
  }
  saving.value = true
  try {
    if (editingUser.value) {
      await http.put(`/users/${editingUser.value.id}`, {
        display_name: userForm.value.display_name,
        email: userForm.value.email || null,
      })
      ElMessage.success('用户已更新')
    } else {
      if (!userForm.value.password || userForm.value.password.length < 6) {
        ElMessage.warning('密码至少 6 位')
        return
      }
      await http.post('/users', {
        username: userForm.value.username,
        password: userForm.value.password,
        display_name: userForm.value.display_name || userForm.value.username,
        email: userForm.value.email || null,
        role: userForm.value.role,
      })
      ElMessage.success('用户已新增')
    }
    userDialog.value = false
    await loadUsers()
  } finally {
    saving.value = false
  }
}

async function toggleUser(row: UserRow) {
  const next = row.status === 1 ? 0 : 1
  await http.put(`/users/${row.id}`, { status: next })
  row.status = next
  ElMessage.success(next === 1 ? '用户已启用' : '用户已禁用')
}

function openRole(row: UserRow) {
  currentUser.value = row
  roleForm.value = { role: roleLabel(row.roles) }
  roleDialog.value = true
}

async function saveRole() {
  if (!currentUser.value) return
  saving.value = true
  try {
    const { data } = await http.put<UserRow>(`/users/${currentUser.value.id}/role`, { role: roleForm.value.role })
    currentUser.value.roles = data.roles
    ElMessage.success('角色已更新')
    roleDialog.value = false
    await loadUsers()
  } finally {
    saving.value = false
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.mt-8 { margin-top: 8px; }
.org-note { margin-top: 12px; color: var(--el-text-color-secondary); font-size: 12px; }
</style>
