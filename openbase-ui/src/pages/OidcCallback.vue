<template>
  <div class="oidc-callback-page">
    <el-card class="oidc-callback-card">
      <h2 v-if="processing" class="oidc-title">OIDC 登录处理中…</h2>
      <template v-else>
        <h2 v-if="error" class="oidc-title" data-test="oidc-error">{{ error }}</h2>
        <el-button v-if="error" class="oidc-back" data-test="oidc-back-login" @click="goLogin">返回登录页</el-button>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { tokenStore } from '@/core/api/http'
import { useAuthStore } from '@/core/stores/auth'
import { parseOidcError, parseOidcHash } from '@/core/api/auth'
import { safeRedirect } from '@/core/api/redirect'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const processing = ref(true)
const error = ref('')

function goLogin() {
  router.replace('/auth/login')
}

/**
 * 清空地址栏 fragment（S6-T4-3）：令牌/IdP 回传参数只经一次解析即消除，
 * 不残留于 URL 与浏览器历史，避免刷新或分享时泄漏。
 */
function clearUrlFragment(): void {
  if (typeof window === 'undefined') return
  const { pathname, search } = window.location
  window.history.replaceState(window.history.state, '', `${pathname}${search}`)
}

onMounted(() => {
  const { access_token, refresh_token } = parseOidcHash(window.location.hash)
  if (!access_token) {
    // IdP 错误（code/state 校验失败）与缺令牌统一走可重试错误页，非白屏
    const oidcError = parseOidcError(window.location.hash)
    const reason = oidcError.error_description || oidcError.error || '缺少令牌，请重新登录'
    processing.value = false
    error.value = `OIDC 回调失败：${reason}`
    clearUrlFragment()
    return
  }
  tokenStore.set(access_token, refresh_token)
  // 令牌落库后立即清理 fragment，再跳转目标页；路由守卫将加载当前用户（me）
  clearUrlFragment()
  auth.user = null
  auth.loaded = false
  router.replace(safeRedirect(route.query.redirect))
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
