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
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/core/stores/auth'
import { isApiError } from '@/core/api/http'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名与密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push((route.query.redirect as string) || '/dashboard')
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
@media (max-width: 767px) { .login-card { width: calc(100vw - 48px); } }
</style>
