/**
 * 无权限访问页（403）。
 * 平台权限门禁指向此处（§3.2 ③：无权限跳 403，不回退 /dashboard）。
 * `?from=` 记录失败前地址，便于返回审计。
 */
<template>
  <div class="forbidden-page">
    <el-result icon="warning" title="无权限访问" :sub-title="subTitle">
      <template #extra>
        <el-button type="primary" @click="router.push('/dashboard')">返回仪表盘</el-button>
        <el-button @click="router.back()">返回上一页</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const subTitle = computed(
  () => `当前账号缺少访问该页面所需的权限${route.query.from ? `（来源：${String(route.query.from)}）` : ''}`,
)
</script>

<style scoped>
.forbidden-page { display: flex; align-items: center; justify-content: center; height: 100vh; }
</style>