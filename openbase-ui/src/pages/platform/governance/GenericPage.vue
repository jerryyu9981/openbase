<template>
  <PageContainer :title="title" description="该能力依赖上游系统接口就绪后启用" test-id="generic-page">
    <el-card>
      <el-result icon="info" :title="`${title}尚未交付`" sub-title="页面框架与入口已就位；上游接口就绪后在此接入真实数据，期间不提供占位数据以免误导。">
        <template #extra>
          <el-button type="primary" @click="$router.push('/dashboard')">返回仪表盘</el-button>
        </template>
      </el-result>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import PageContainer from '@/components/page/PageContainer.vue'

const route = useRoute()
const title = computed(() => (route.meta.title as string) || '功能页')
</script>
