<template>
  <div>
    <div class="page-toolbar">
      <h3>个人设置</h3>
    </div>

    <el-alert
      v-if="pageError"
      :title="pageError"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="settings-error"
      @close="pageError = ''"
    />

    <el-row :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card v-loading="loading" header="资料编辑" data-test="profile-card">
          <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="90px">
            <el-form-item label="显示名" prop="displayName">
              <el-input v-model="profileForm.displayName" placeholder="请输入显示名" data-test="profile-nickname" />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="profileForm.email" placeholder="you@example.com" data-test="profile-email" />
            </el-form-item>
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="profileForm.phone" placeholder="可选" data-test="profile-phone" />
            </el-form-item>
            <el-button type="primary" :loading="savingProfile" data-test="profile-save" @click="handleSaveProfile">
              保存资料
            </el-button>
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
          <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="110px">
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
            <el-button type="primary" :loading="changingPassword" data-test="password-save" @click="handleChangePassword">
              修改密码
            </el-button>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-loading="loadingNotify" header="通知偏好" class="mt-16" data-test="notify-card">
      <el-alert
        v-if="notifyError"
        :title="notifyError"
        type="error"
        show-icon
        closable
        class="card-alert"
        data-test="notify-error"
        @close="notifyError = ''"
      />
      <el-form label-width="120px">
        <el-form-item label="站内通知">
          <el-switch v-model="notifyForm.in_app" data-test="notify-in-app" />
        </el-form-item>
        <el-form-item label="邮件通知">
          <el-switch v-model="notifyForm.email" data-test="notify-email" />
        </el-form-item>
        <el-form-item label="Webhook 通知">
          <el-switch v-model="notifyForm.webhook" data-test="notify-webhook" />
        </el-form-item>
        <el-form-item v-if="notifyForm.webhook" label="Webhook 地址">
          <el-input
            v-model="notifyForm.webhook_url"
            placeholder="回调地址（需以 http(s):// 开头）"
            data-test="notify-webhook-url"
          />
        </el-form-item>
        <el-form-item label="通知事件">
          <el-checkbox v-model="notifyForm.events.alert" data-test="notify-event-alert">告警</el-checkbox>
          <el-checkbox v-model="notifyForm.events.approval" data-test="notify-event-approval">审批</el-checkbox>
          <el-checkbox v-model="notifyForm.events.system" data-test="notify-event-system">系统</el-checkbox>
        </el-form-item>
        <el-button type="primary" :loading="savingNotify" data-test="notify-save" @click="handleSaveNotify">
          保存偏好
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { authApi, type NotificationPreferences } from '@/core/api/auth'
import { useAuthStore } from '@/core/stores/auth'

/**
 * 个人设置（v1.9.7 R7 真实化 + v1.10.1 OB-01）：`GET/PUT /auth/me` 资料、
 * `POST /auth/change-password` 改密、`GET/PUT /auth/notification-preferences` 通知偏好。
 */
const EMAIL_RE = /^[\w.+-]+@[\w-]+(\.[\w-]+)+$/
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/
const WEBHOOK_RE = /^https?:\/\/\S+$/

const auth = useAuthStore()
const loading = ref(false)
const savingProfile = ref(false)
const changingPassword = ref(false)
const loadingNotify = ref(false)
const savingNotify = ref(false)
const pageError = ref('')
const passwordError = ref('')
const notifyError = ref('')

const notifyForm = reactive<NotificationPreferences>({
  in_app: true,
  email: false,
  webhook: false,
  webhook_url: null,
  events: { alert: true, approval: true, system: true },
})

const profileFormRef = ref<FormInstance>()
const profileForm = reactive({ displayName: '', email: '', phone: '' })
const profileRules: FormRules = {
  displayName: [{ required: true, message: '请输入显示名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { pattern: EMAIL_RE, message: '邮箱格式不正确', trigger: 'blur' },
  ],
}

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

function errorText(error: unknown, fallback: string) {
  const message = (error as { response?: { data?: { message?: string } } })?.response?.data?.message
  if (message) return message
  return error instanceof Error ? error.message : fallback
}

async function loadProfile() {
  loading.value = true
  pageError.value = ''
  try {
    const user = await authApi.me()
    auth.user = user
    profileForm.displayName = user.display_name || user.username
    profileForm.email = user.email || ''
    profileForm.phone = user.phone || ''
  } catch (error) {
    pageError.value = `资料加载失败：${errorText(error, '未知错误')}`
  } finally {
    loading.value = false
  }
}

async function handleSaveProfile() {
  if (!profileFormRef.value) return
  const valid = await profileFormRef.value.validate().catch(() => false)
  if (!valid) return
  savingProfile.value = true
  try {
    await authApi.updateProfile({
      display_name: profileForm.displayName.trim(),
      email: profileForm.email.trim() || null,
      phone: profileForm.phone.trim() || null,
    })
    await auth.loadMe()
    ElMessage.success('资料已保存')
  } catch (error) {
    pageError.value = `资料保存失败：${errorText(error, '未知错误')}`
  } finally {
    savingProfile.value = false
  }
}

async function handleChangePassword() {
  passwordError.value = ''
  if (!passwordFormRef.value) return
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return
  changingPassword.value = true
  try {
    await authApi.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    ElMessage.success('密码修改成功')
  } catch (error) {
    passwordError.value = `密码修改失败：${errorText(error, '未知错误')}`
  } finally {
    changingPassword.value = false
  }
}

async function loadNotify() {
  loadingNotify.value = true
  notifyError.value = ''
  try {
    const prefs = await authApi.getNotificationPreferences()
    notifyForm.in_app = prefs.in_app
    notifyForm.email = prefs.email
    notifyForm.webhook = prefs.webhook
    notifyForm.webhook_url = prefs.webhook_url
    notifyForm.events = { alert: true, approval: true, system: true, ...(prefs.events || {}) }
  } catch (error) {
    notifyError.value = `通知偏好加载失败：${errorText(error, '未知错误')}`
  } finally {
    loadingNotify.value = false
  }
}

async function handleSaveNotify() {
  notifyError.value = ''
  const webhookUrl = (notifyForm.webhook_url || '').trim()
  if (notifyForm.webhook && !WEBHOOK_RE.test(webhookUrl)) {
    notifyError.value = '启用 Webhook 时，回调地址需以 http(s) 协议开头'
    return
  }
  savingNotify.value = true
  try {
    const saved = await authApi.updateNotificationPreferences({
      in_app: notifyForm.in_app,
      email: notifyForm.email,
      webhook: notifyForm.webhook,
      webhook_url: webhookUrl || null,
      events: { ...notifyForm.events },
    })
    notifyForm.in_app = saved.in_app
    notifyForm.email = saved.email
    notifyForm.webhook = saved.webhook
    notifyForm.webhook_url = saved.webhook_url
    notifyForm.events = { alert: true, approval: true, system: true, ...(saved.events || {}) }
    ElMessage.success('通知偏好已保存')
  } catch (error) {
    notifyError.value = `通知偏好保存失败：${errorText(error, '未知错误')}`
  } finally {
    savingNotify.value = false
  }
}

onMounted(() => {
  void loadProfile()
  void loadNotify()
})
</script>

<style scoped>
.page-toolbar h3 {
  margin: 0;
}
.mb-16 { margin-bottom: 16px; }
.card-alert { margin-bottom: 12px; }
.mt-16 { margin-top: 16px; }
</style>
