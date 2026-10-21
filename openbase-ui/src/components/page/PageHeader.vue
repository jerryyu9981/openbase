<template>
  <header class="ob-page-header">
    <div class="ob-page-header-main">
      <div class="ob-page-header-title-row">
        <el-button v-if="back" link class="ob-page-back" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h2 class="ob-page-title">{{ title }}</h2>
        <slot name="meta" />
      </div>
      <p v-if="description" class="ob-page-desc">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="ob-page-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    back?: boolean
    backTo?: string
  }>(),
  { description: '', back: false, backTo: '' },
)

const router = useRouter()

function goBack() {
  if (props.backTo) {
    router.push(props.backTo)
    return
  }
  if (window.history.length > 1) router.back()
  else router.push('/dashboard')
}
</script>

<style scoped>
.ob-page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.ob-page-header-main { min-width: 0; }
.ob-page-header-title-row { display: flex; align-items: center; gap: 8px; }
.ob-page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  line-height: 28px;
  color: var(--el-text-color-primary);
}
.ob-page-desc {
  margin: 4px 0 0;
  font-size: 13px;
  line-height: 20px;
  color: var(--el-text-color-secondary);
}
.ob-page-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.ob-page-back { padding: 0; }
</style>
