<template>
  <PageContainer title="用户管理" description="账号、状态与角色分配（数据源：OpenBase /api/v1/users）" test-id="users-view-page">
    <div class="page-toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索用户名 / 显示名 / 邮箱"
        clearable
        style="width: 260px"
        data-test="user-search"
      />
      <el-button data-test="refresh-users" :loading="tableLoading" @click="load">刷新</el-button>
      <el-button type="primary" data-test="create-user" @click="openCreate">新建用户</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="users-error"
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
        <el-table-column prop="display_name" label="显示名" min-width="120" />
        <el-table-column label="邮箱" min-width="200">
          <template #default="{ row }">{{ row.email || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="130">
          <template #default="{ row }">
            <el-tag v-for="role in row.roles" :key="role" :type="roleTagType(role)" size="small" class="role-tag">
              {{ roleLabel(role) }}
            </el-tag>
            <span v-if="!row.roles.length">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="租户" width="90">
          <template #default="{ row }">{{ row.tenant_id ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="edit-role" @click="openRole(row)">编辑角色</el-button>
            <el-tooltip :disabled="!isBuiltinAdmin(row)" content="内置管理员不可停用" placement="top">
              <el-switch
                :model-value="row.status === 1"
                size="small"
                :disabled="isBuiltinAdmin(row)"
                data-test="toggle-user"
                @change="(val: boolean) => toggleStatus(row, val)"
              />
            </el-tooltip>
            <el-popconfirm
              :title="`确认停用用户「${row.username}」？停用后该账号不可登录。`"
              :disabled="isBuiltinAdmin(row)"
              @confirm="remove(row)"
            >
              <template #reference>
                <el-button link type="danger" :disabled="isBuiltinAdmin(row)" data-test="delete-user">停用</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无匹配的用户" :image-size="60" data-test="users-empty" />
        </template>
      </el-table>
    </div>

    <!-- 新建用户 -->
    <el-dialog v-model="createDialogVisible" title="新建用户" width="520px" data-test="create-user-dialog">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="登录用户名" data-test="username-input" />
        </el-form-item>
        <el-form-item label="显示名" prop="display_name">
          <el-input v-model="createForm.display_name" placeholder="如：张三" data-test="display-name-input" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="createForm.email" placeholder="user@example.com" data-test="email-input" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password placeholder="至少 6 位" data-test="password-input" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="createForm.role" style="width: 100%" data-test="role-input">
            <el-option v-for="item in ROLE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" data-test="create-user-submit" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑角色 -->
    <el-dialog v-model="roleDialogVisible" title="编辑角色" width="420px" data-test="role-dialog">
      <el-form label-width="100px">
        <el-form-item label="用户名"><span>{{ roleForm.username }}</span></el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="roleForm.role" style="width: 100%" data-test="role-select">
            <el-option v-for="item in ROLE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" data-test="role-submit" @click="saveRole">保存</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  ROLE_OPTIONS,
  roleLabel,
  roleTagType,
  usersApi,
  type PlatformUser,
} from '@/core/api/users'

const keyword = ref('')
const tableLoading = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const createDialogVisible = ref(false)
const roleDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()

const users = ref<PlatformUser[]>([])

const createForm = reactive({
  username: '',
  display_name: '',
  email: '',
  password: '',
  role: 'viewer',
})

const createRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_.-]{2,64}$/, message: '2-64 位字母、数字、下划线、点或连字符', trigger: 'blur' },
  ],
  display_name: [{ required: true, message: '请输入显示名', trigger: 'blur' }],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

const roleForm = reactive({ userId: 0, username: '', role: 'viewer' })

const filteredUsers = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return users.value
  return users.value.filter((user) => {
    const haystack = [user.username, user.display_name, user.email ?? ''].join(' ').toLowerCase()
    return haystack.includes(kw)
  })
})

function isBuiltinAdmin(user: PlatformUser): boolean {
  return user.username === 'admin'
}

function messageOf(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  return fallback
}

async function load(): Promise<void> {
  tableLoading.value = true
  errorMessage.value = ''
  try {
    users.value = await usersApi.list()
  } catch (error) {
    errorMessage.value = `用户列表加载失败：${messageOf(error, '未知错误')}`
  } finally {
    tableLoading.value = false
  }
}

function openCreate(): void {
  errorMessage.value = ''
  createForm.username = ''
  createForm.display_name = ''
  createForm.email = ''
  createForm.password = ''
  createForm.role = 'viewer'
  createFormRef.value?.clearValidate()
  createDialogVisible.value = true
}

async function submitCreate(): Promise<void> {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await usersApi.create({
      username: createForm.username.trim(),
      password: createForm.password,
      display_name: createForm.display_name.trim(),
      email: createForm.email.trim() || undefined,
      role: createForm.role,
    })
    createDialogVisible.value = false
    ElMessage.success('用户已创建')
    await load()
  } catch (error) {
    errorMessage.value = `创建失败：${messageOf(error, '未知错误')}`
  } finally {
    submitting.value = false
  }
}

function openRole(row: PlatformUser): void {
  roleForm.userId = row.id
  roleForm.username = row.username
  roleForm.role = row.roles[0] ?? 'viewer'
  roleDialogVisible.value = true
}

async function saveRole(): Promise<void> {
  submitting.value = true
  try {
    const updated = await usersApi.assignRole(roleForm.userId, roleForm.role)
    const target = users.value.find((user) => user.id === roleForm.userId)
    if (target) target.roles = updated.roles
    ElMessage.success(`已更新「${target?.username ?? roleForm.username}」的角色为 ${roleLabel(roleForm.role)}`)
    roleDialogVisible.value = false
  } catch (error) {
    errorMessage.value = `角色更新失败：${messageOf(error, '未知错误')}`
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(row: PlatformUser, enabled: boolean): Promise<void> {
  try {
    const updated = await usersApi.update(row.id, { status: enabled ? 1 : 0 })
    row.status = updated.status
    ElMessage.success(`「${row.username}」已${enabled ? '启用' : '停用'}`)
  } catch (error) {
    errorMessage.value = `状态更新失败：${messageOf(error, '未知错误')}`
  }
}

async function remove(row: PlatformUser): Promise<void> {
  if (isBuiltinAdmin(row)) {
    errorMessage.value = '内置管理员账号不可停用'
    return
  }
  try {
    await usersApi.remove(row.id)
    users.value = users.value.filter((user) => user.id !== row.id)
    ElMessage.success('用户已停用')
  } catch (error) {
    errorMessage.value = `停用失败：${messageOf(error, '未知错误')}`
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.role-tag { margin-right: 4px; }
</style>
