<template>
  <div class="login-page">
    <el-card class="login-card">
      <h1 class="login-title">OpenBase 统一管理平台</h1>
      <el-form :model="form" @submit.prevent="onSubmit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" data-test="username" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" show-password :prefix-icon="Lock" data-test="password" @keyup.enter="onSubmit" />
        </el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" data-test="submit" native-type="submit">登 录</el-button>
      </el-form>
      <el-divider class="login-divider">或</el-divider>
      <el-button class="login-btn oidc-btn" :disabled="oidcLoading" data-test="oidc-login" @click="onOidcLogin">
        OIDC 统一登录
      </el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/core/stores/auth'
import { http, isApiError } from '@/core/api/http'
import { safeRedirect } from '@/core/api/redirect'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', password: '' })
const loading = ref(false)
const oidcLoading = ref(false)

/** OIDC 统一登录：跳转网关 authorize → IdP 授权 → 回跳前端回调路由（fragment 令牌） */
async function onOidcLogin() {
  if (oidcLoading.value) return
  oidcLoading.value = true
  try {
    const resp = await http.get<{ authorize_url: string }>('/auth/oidc/authorize')
    window.location.href = resp.data.authorize_url
  } catch {
    oidcLoading.value = false
    ElMessage.error('OIDC 服务不可用，请稍后重试')
  }
}

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名与密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    // 回跳安全（S6-T4-1）：redirect 仅接受站内相对路径，恶意值回落 /dashboard
    router.push(safeRedirect(route.query.redirect))
  } catch (error) {
    if (isApiError(error)) {
      ElMessage.error(error.response?.data?.message || '登录失败')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #1e3a8a, #2563eb); }
.login-card { width: 360px; padding: 8px 12px; }
.login-title { font-size: 18px; text-align: center; margin-bottom: 20px; }
.login-btn { width: 100%; }
.login-divider { margin: 14px 0 8px; }
.oidc-btn { margin-top: 0; }
@media (max-width: 767px) { .login-card { width: calc(100vw - 48px); } }
</style>
