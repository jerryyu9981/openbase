<template>
  <div class="oidc-callback-page">
    <el-card class="oidc-callback-card">
      <h2 v-if="processing" class="oidc-title">OIDC 登录处理中…</h2>
      <template v-else>
        <h2 v-if="error" class="oidc-title">{{ error }}</h2>
        <el-button v-if="error" class="oidc-back" @click="goLogin">返回登录页</el-button>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { tokenStore } from '@/core/api/http'
import { useAuthStore } from '@/core/stores/auth'
import { parseOidcHash } from '@/core/api/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const processing = ref(true)
const error = ref('')

function goLogin() {
  router.replace('/auth/login')
}

onMounted(() => {
  const { access_token, refresh_token } = parseOidcHash(window.location.hash)
  if (!access_token) {
    processing.value = false
    error.value = 'OIDC 回调缺少令牌，请重新登录'
    return
  }
  tokenStore.set(access_token, refresh_token)
  auth.user = null
  auth.loaded = false
  // 令牌落库后跳转目标页；路由守卫将加载当前用户（me）并在失效时回登录页
  router.replace((route.query.redirect as string) || '/dashboard')
})
</script>

<style scoped>
.oidc-callback-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3a8a, #2563eb);
}
.oidc-callback-card {
  width: 380px;
  text-align: center;
  padding: 12px 8px;
}
.oidc-title {
  font-size: 16px;
  color: #606266;
}
.oidc-back {
  margin-top: 8px;
}
</style>
