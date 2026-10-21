<template>
  <div class="ob-filter-bar">
    <div class="ob-filter-fields">
      <slot />
    </div>
    <div v-if="$slots.actions" class="ob-filter-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ testId?: string }>(), { testId: undefined })
</script>

<style scoped>
.ob-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 16px;
  background: var(--ob-surface);
  border: 1px solid var(--ob-border);
  border-radius: var(--ob-radius-md, 8px);
}
.ob-filter-fields {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  min-width: 0;
}
.ob-filter-actions { display: flex; align-items: center; gap: 8px; }
</style>
