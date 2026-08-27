<template>
  <div>
    <div class="page-toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索用户名 / 邮箱"
        clearable
        style="width: 240px"
        data-test="user-search"
      />
      <el-button type="primary" data-test="create-user" @click="openCreate">新建用户</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      @close="errorMessage = ''"
    />

    <div class="ob-table-scroll">
      <el-table
        v-loading="tableLoading"
        element-loading-text="加载用户列表中…"
        :data="filteredUsers"
        stripe
        data-test="user-table"
      >
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="roleType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="170" />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="edit-role" @click="openRole(row)">编辑角色</el-button>
            <el-tooltip :disabled="row.role !== 'admin'" content="内置管理员不可停用" placement="top">
              <el-switch
                :model-value="row.status === 'active'"
                size="small"
                :disabled="row.role === 'admin'"
                data-test="toggle-user"
                @change="(val: boolean) => toggleStatus(row, val)"
              />
            </el-tooltip>
            <el-popconfirm
              :title="`确认删除用户「${row.username}」？删除后不可恢复。`"
              :disabled="row.role === 'admin'"
              @confirm="remove(row.id)"
            >
              <template #reference>
                <el-button link type="danger" :disabled="row.role === 'admin'" data-test="delete-user">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无匹配的用户" :image-size="60" />
        </template>
      </el-table>
    </div>

    <!-- 新建用户 -->
    <el-dialog v-model="createDialogVisible" title="新建用户" width="480px" data-test="create-user-dialog">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="登录用户名" data-test="username-input" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="createForm.email" placeholder="user@example.com" data-test="email-input" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password placeholder="至少 6 位" data-test="password-input" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="createForm.role" style="width: 100%" data-test="role-input">
            <el-option label="管理员" value="admin" />
            <el-option label="编辑者" value="editor" />
            <el-option label="只读用户" value="viewer" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" data-test="create-user-submit" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑角色 -->
    <el-dialog v-model="roleDialogVisible" title="编辑角色" width="420px" data-test="role-dialog">
      <el-form label-width="100px">
        <el-form-item label="用户名"><span>{{ roleForm.username }}</span></el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="roleForm.role" style="width: 100%" data-test="role-select">
            <el-option label="管理员" value="admin" />
            <el-option label="编辑者" value="editor" />
            <el-option label="只读用户" value="viewer" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" data-test="role-submit" @click="saveRole">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

interface UserRow {
  id: number
  username: string
  email: string
  role: string
  status: 'active' | 'disabled'
  last_login: string
}

const keyword = ref('')
const tableLoading = ref(true)
const errorMessage = ref('')
const createDialogVisible = ref(false)
const roleDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()

const users = ref<UserRow[]>([
  { id: 1, username: 'admin', email: 'admin@openbase.dev', role: 'admin', status: 'active', last_login: '2026-08-27 09:12' },
  { id: 2, username: 'alice', email: 'alice@openbase.dev', role: 'editor', status: 'active', last_login: '2026-08-26 18:40' },
  { id: 3, username: 'bob', email: 'bob@openbase.dev', role: 'viewer', status: 'disabled', last_login: '2026-08-20 11:05' },
  { id: 4, username: 'carol', email: 'carol@openbase.dev', role: 'editor', status: 'active', last_login: '2026-08-25 15:22' },
])

const createForm = reactive({ username: '', email: '', password: '', role: 'viewer' })

const createRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]{3,20}$/, message: '3-20 位字母、数字、下划线或连字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

const roleForm = reactive({ id: 0, username: '', role: 'viewer' })

const filteredUsers = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return users.value
  return users.value.filter(
    (user) => user.username.toLowerCase().includes(kw) || user.email.toLowerCase().includes(kw),
  )
})

function roleType(role: string) {
  return { admin: 'danger', editor: 'warning', viewer: 'info' }[role] || 'info'
}
function roleLabel(role: string) {
  return { admin: '管理员', editor: '编辑者', viewer: '只读用户' }[role] || role
}

function openCreate() {
  errorMessage.value = ''
  createForm.username = ''
  createForm.email = ''
  createForm.password = ''
  createForm.role = 'viewer'
  createFormRef.value?.clearValidate()
  createDialogVisible.value = true
}

async function submitCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  const duplicated = users.value.some(
    (user) => user.username === createForm.username.trim() || user.email === createForm.email.trim(),
  )
  if (duplicated) {
    errorMessage.value = '创建失败：用户名或邮箱已存在'
    return
  }
  users.value.push({
    id: Date.now(),
    username: createForm.username.trim(),
    email: createForm.email.trim(),
    role: createForm.role,
    status: 'active',
    last_login: '—',
  })
  createDialogVisible.value = false
  errorMessage.value = ''
  ElMessage.success('用户已创建')
}

function openRole(row: UserRow) {
  roleForm.id = row.id
  roleForm.username = row.username
  roleForm.role = row.role
  roleDialogVisible.value = true
}

function saveRole() {
  const target = users.value.find((user) => user.id === roleForm.id)
  if (target) {
    target.role = roleForm.role
    ElMessage.success(`已更新「${target.username}」的角色为 ${roleLabel(target.role)}`)
  }
  roleDialogVisible.value = false
}

function toggleStatus(row: UserRow, val: boolean) {
  row.status = val ? 'active' : 'disabled'
  ElMessage.success(`「${row.username}」已${val ? '启用' : '停用'}`)
}

function remove(id: number) {
  const target = users.value.find((user) => user.id === id)
  if (target?.role === 'admin') {
    errorMessage.value = '内置管理员账号不可删除'
    return
  }
  users.value = users.value.filter((user) => user.id !== id)
  ElMessage.success('用户已删除')
}

onMounted(() => {
  setTimeout(() => {
    tableLoading.value = false
  }, 400)
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.mb-16 { margin-bottom: 16px; }
</style>
