<template>
  <div>
    <div class="page-toolbar">
      <h3>个人设置</h3>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card v-loading="loading" header="资料编辑" data-test="profile-card">
          <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="90px">
            <el-form-item label="昵称" prop="nickname">
              <el-input v-model="profileForm.nickname" placeholder="请输入昵称" data-test="profile-nickname" />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="profileForm.email" placeholder="you@example.com" data-test="profile-email" />
            </el-form-item>
            <el-form-item label="头像地址" prop="avatarUrl">
              <div class="avatar-row">
                <el-input v-model="profileForm.avatarUrl" placeholder="https://example.com/avatar.png" data-test="profile-avatar" />
                <el-avatar :size="40" :src="profileForm.avatarUrl || undefined" data-test="profile-avatar-preview">{{ avatarInitial }}</el-avatar>
              </div>
            </el-form-item>
            <el-button type="primary" :loading="savingProfile" data-test="profile-save" @click="handleSaveProfile">保存资料</el-button>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card v-loading="loading" header="修改密码" data-test="password-card">
          <el-alert
            v-if="passwordError"
            :title="passwordError"
            type="error"
            show-icon
            closable
            class="card-alert"
            data-test="password-error"
            @close="passwordError = ''"
          />
          <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="90px">
            <el-form-item label="旧密码" prop="oldPassword">
              <el-input v-model="passwordForm.oldPassword" type="password" show-password placeholder="请输入旧密码" data-test="password-old" />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input
                v-model="passwordForm.newPassword"
                type="password"
                show-password
                placeholder="至少 8 位，需同时包含字母和数字"
                data-test="password-new"
              />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirmPassword">
              <el-input v-model="passwordForm.confirmPassword" type="password" show-password placeholder="再次输入新密码" data-test="password-confirm" />
            </el-form-item>
            <el-button type="primary" :loading="changingPassword" data-test="password-save" @click="handleChangePassword">修改密码</el-button>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-loading="loading" header="通知偏好" class="mt-16" data-test="notify-card">
      <el-empty v-if="notifyPrefs.length === 0" description="暂无通知项" :image-size="60" data-test="notify-empty" />
      <el-form v-else label-width="200px" @submit.prevent="handleSaveNotify">
        <el-form-item v-for="item in notifyPrefs" :key="item.key" :label="item.label">
          <el-switch v-model="item.enabled" data-test="notify-switch" />
        </el-form-item>
        <el-button type="primary" :loading="savingNotify" data-test="notify-save" @click="handleSaveNotify">保存偏好</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

const EMAIL_RE = /^[\w.+-]+@[\w-]+(\.[\w-]+)+$/
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/

/** 契约 mock：当前账户旧密码（不调用真实 API） */
const MOCK_CURRENT_PASSWORD = 'OpenBase@123'

const loading = ref(true)
const savingProfile = ref(false)
const changingPassword = ref(false)
const savingNotify = ref(false)
const passwordError = ref('')

// ---------- 资料编辑 ----------
const profileFormRef = ref<FormInstance>()
const profileForm = reactive({ nickname: '', email: '', avatarUrl: '' })
const profileRules: FormRules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { pattern: EMAIL_RE, message: '邮箱格式不正确', trigger: 'blur' },
  ],
  avatarUrl: [{ pattern: /^https?:\/\/.+/, message: '请输入以 http(s) 开头的图片地址', trigger: 'blur' }],
}
const avatarInitial = computed(() => profileForm.nickname.trim().charAt(0).toUpperCase() || 'U')

// ---------- 修改密码 ----------
const passwordFormRef = ref<FormInstance>()
const passwordForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })

function validateNewPassword(_rule: unknown, value: string, callback: (error?: Error) => void) {
  if (value === passwordForm.oldPassword) callback(new Error('新密码不能与旧密码相同'))
  else if (!PASSWORD_RE.test(value)) callback(new Error('密码至少 8 位，且需同时包含字母和数字'))
  else callback()
}
function validatePasswordConfirm(_rule: unknown, value: string, callback: (error?: Error) => void) {
  if (value !== passwordForm.newPassword) callback(new Error('两次输入的密码不一致'))
  else callback()
}
const passwordRules: FormRules = {
  oldPassword: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  newPassword: [{ required: true, trigger: 'blur', validator: validateNewPassword }],
  confirmPassword: [{ required: true, trigger: 'blur', validator: validatePasswordConfirm }],
}

// ---------- 通知偏好 ----------
interface NotifyPreference {
  key: string
  label: string
  enabled: boolean
}
const notifyPrefs = ref<NotifyPreference[]>([
  { key: 'email', label: '邮件通知', enabled: true },
  { key: 'site', label: '站内通知', enabled: true },
  { key: 'version', label: '版本更新提醒', enabled: false },
  { key: 'quota', label: '用量告警', enabled: true },
])

onMounted(async () => {
  // 契约 mock：模拟拉取当前用户资料
  await mockDelay(500)
  profileForm.nickname = 'admin'
  profileForm.email = 'admin@openbase.local'
  profileForm.avatarUrl = ''
  loading.value = false
})

async function handleSaveProfile() {
  if (!profileFormRef.value) return
  const valid = await profileFormRef.value.validate().catch(() => false)
  if (!valid) return
  savingProfile.value = true
  await mockDelay(500) // 契约 mock：模拟保存资料
  savingProfile.value = false
  ElMessage.success('资料已保存')
}

async function handleChangePassword() {
  passwordError.value = ''
  if (!passwordFormRef.value) return
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return
  if (passwordForm.oldPassword !== MOCK_CURRENT_PASSWORD) {
    passwordError.value = '旧密码校验失败，请确认后重试'
    return
  }
  changingPassword.value = true
  await mockDelay(500) // 契约 mock：模拟修改密码
  changingPassword.value = false
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
  ElMessage.success('密码修改成功')
}

async function handleSaveNotify() {
  savingNotify.value = true
  await mockDelay(400) // 契约 mock：模拟保存通知偏好
  savingNotify.value = false
  ElMessage.success('通知偏好已保存')
}

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}
</script>

<style scoped>
.page-toolbar {
  margin-bottom: 16px;
}
.page-toolbar h3 {
  margin: 0;
}
.card-alert {
  margin-bottom: 12px;
}
.avatar-row {
  display: flex;
  gap: 12px;
  width: 100%;
  align-items: center;
}
.mt-16 {
  margin-top: 16px;
}
</style>
