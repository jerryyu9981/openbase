<template>
  <div class="auth-ext-page">
    <el-card class="auth-card" data-test="auth-ext-card">
      <div class="auth-header">
        <h2>OpenBase 账户</h2>
        <p class="auth-subtitle">注册新账户或重置密码</p>
      </div>

      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        closable
        class="auth-alert"
        data-test="auth-error"
        @close="errorMessage = ''"
      />

      <el-tabs v-model="activeTab" stretch data-test="auth-tabs">
        <!-- 注册 -->
        <el-tab-pane label="注册" name="register">
          <el-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            label-position="top"
            size="large"
            @submit.prevent="handleRegister"
          >
            <el-form-item label="用户名" prop="username">
              <el-input v-model="registerForm.username" placeholder="3-20 位字母、数字或下划线" data-test="register-username" />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="registerForm.email" placeholder="you@example.com" data-test="register-email" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="registerForm.password"
                type="password"
                show-password
                placeholder="至少 8 位，需同时包含字母和数字"
                data-test="register-password"
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input v-model="registerForm.confirmPassword" type="password" show-password placeholder="再次输入密码" data-test="register-confirm" />
            </el-form-item>
            <el-button type="primary" :loading="registering" class="auth-submit" data-test="register-submit" @click="handleRegister">
              注册
            </el-button>
          </el-form>
        </el-tab-pane>

        <!-- 找回密码 -->
        <el-tab-pane label="找回密码" name="forgot">
          <el-form
            ref="forgotFormRef"
            :model="forgotForm"
            :rules="forgotRules"
            label-position="top"
            size="large"
            @submit.prevent="handleReset"
          >
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="forgotForm.email" placeholder="请输入注册邮箱" data-test="forgot-email" />
            </el-form-item>
            <el-form-item label="验证码" prop="code">
              <div class="code-row">
                <el-input v-model="forgotForm.code" placeholder="6 位验证码" data-test="forgot-code" />
                <el-button
                  :disabled="countdown > 0"
                  :loading="sendingCode"
                  data-test="forgot-send-code"
                  @click="handleSendCode"
                >
                  {{ countdown > 0 ? `${countdown}s 后重发` : '发送验证码' }}
                </el-button>
              </div>
            </el-form-item>
            <el-form-item label="新密码" prop="password">
              <el-input
                v-model="forgotForm.password"
                type="password"
                show-password
                placeholder="至少 8 位，需同时包含字母和数字"
                data-test="forgot-password"
              />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirmPassword">
              <el-input v-model="forgotForm.confirmPassword" type="password" show-password placeholder="再次输入新密码" data-test="forgot-confirm" />
            </el-form-item>
            <el-button type="primary" :loading="resetting" class="auth-submit" data-test="forgot-submit" @click="handleReset">
              重置密码
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div class="auth-footer">
        <el-button link type="primary" data-test="back-to-login" @click="goLogin">返回登录</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

const router = useRouter()
const activeTab = ref('register')
const errorMessage = ref('')

const EMAIL_RE = /^[\w.+-]+@[\w-]+(\.[\w-]+)+$/
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/

/** 契约 mock：已注册邮箱与验证码（不调用真实 API） */
const registeredEmails = ['admin@openbase.local']
const MOCK_CODE = '123456'

// ---------- 注册 ----------
const registerFormRef = ref<FormInstance>()
const registerForm = reactive({ username: '', email: '', password: '', confirmPassword: '' })
const registering = ref(false)

function validateEmail(_rule: unknown, value: string, callback: (error?: Error) => void) {
  if (!EMAIL_RE.test(value)) callback(new Error('邮箱格式不正确'))
  else callback()
}
function validatePasswordStrength(_rule: unknown, value: string, callback: (error?: Error) => void) {
  if (!PASSWORD_RE.test(value)) callback(new Error('密码至少 8 位，且需同时包含字母和数字'))
  else callback()
}
function validateRegisterConfirm(_rule: unknown, value: string, callback: (error?: Error) => void) {
  if (value !== registerForm.password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^\w{3,20}$/, message: '用户名为 3-20 位字母、数字或下划线', trigger: 'blur' },
  ],
  email: [{ required: true, trigger: 'blur', validator: validateEmail }],
  password: [{ required: true, trigger: 'blur', validator: validatePasswordStrength }],
  confirmPassword: [{ required: true, trigger: 'blur', validator: validateRegisterConfirm }],
}

async function handleRegister() {
  errorMessage.value = ''
  if (!registerFormRef.value) return
  const valid = await registerFormRef.value.validate().catch(() => false)
  if (!valid) return
  if (registeredEmails.includes(registerForm.email.trim().toLowerCase())) {
    errorMessage.value = '该邮箱已注册，请直接登录或使用找回密码'
    return
  }
  registering.value = true
  await mockDelay(600) // 契约 mock：模拟提交注册
  registering.value = false
  ElMessage.success('注册成功，即将跳转登录')
  window.setTimeout(() => router.push('/auth/login'), 800)
}

// ---------- 找回密码 ----------
const forgotFormRef = ref<FormInstance>()
const forgotForm = reactive({ email: '', code: '', password: '', confirmPassword: '' })
const sendingCode = ref(false)
const resetting = ref(false)
const countdown = ref(0)
let countdownTimer: number | undefined

function validateForgotConfirm(_rule: unknown, value: string, callback: (error?: Error) => void) {
  if (value !== forgotForm.password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const forgotRules: FormRules = {
  email: [{ required: true, trigger: 'blur', validator: validateEmail }],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { pattern: /^\d{6}$/, message: '验证码为 6 位数字', trigger: 'blur' },
  ],
  password: [{ required: true, trigger: 'blur', validator: validatePasswordStrength }],
  confirmPassword: [{ required: true, trigger: 'blur', validator: validateForgotConfirm }],
}

async function handleSendCode() {
  const email = forgotForm.email.trim()
  if (!EMAIL_RE.test(email)) {
    ElMessage.warning('请先输入正确的邮箱')
    return
  }
  if (!registeredEmails.includes(email.toLowerCase())) {
    errorMessage.value = '该邮箱未注册，无法发送验证码'
    return
  }
  sendingCode.value = true
  errorMessage.value = ''
  await mockDelay(400) // 契约 mock：模拟发送验证码
  sendingCode.value = false
  ElMessage.success(`验证码已发送至 ${email}（Mock：${MOCK_CODE}）`)
  countdown.value = 60
  window.clearInterval(countdownTimer)
  countdownTimer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) window.clearInterval(countdownTimer)
  }, 1000)
}

async function handleReset() {
  errorMessage.value = ''
  if (!forgotFormRef.value) return
  const valid = await forgotFormRef.value.validate().catch(() => false)
  if (!valid) return
  if (forgotForm.code.trim() !== MOCK_CODE) {
    errorMessage.value = '验证码错误，请重新输入'
    return
  }
  resetting.value = true
  await mockDelay(600) // 契约 mock：模拟重置密码
  resetting.value = false
  ElMessage.success('密码已重置，即将跳转登录')
  window.setTimeout(() => router.push('/auth/login'), 800)
}

function goLogin() {
  router.push('/auth/login')
}

function mockDelay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

onBeforeUnmount(() => {
  window.clearInterval(countdownTimer)
})
</script>

<style scoped>
.auth-ext-page {
  display: flex;
  justify-content: center;
  padding: 40px 16px;
}
.auth-card {
  width: 100%;
  max-width: 440px;
}
.auth-header {
  text-align: center;
  margin-bottom: 8px;
}
.auth-header h2 {
  margin: 0;
}
.auth-subtitle {
  color: var(--ob-text-secondary);
  font-size: 13px;
  margin: 6px 0 0;
}
.auth-alert {
  margin-bottom: 12px;
}
.auth-submit {
  width: 100%;
  margin-top: 4px;
}
.code-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.auth-footer {
  text-align: center;
  margin-top: 12px;
}
</style>
