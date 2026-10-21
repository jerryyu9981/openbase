<template>
  <section class="ob-page" :data-test="testId">
    <PageHeader
      v-if="title"
      :title="title"
      :description="description"
      :back="back"
    >
      <template v-if="$slots.actions" #actions>
        <slot name="actions" />
      </template>
      <template v-if="$slots.meta" #meta>
        <slot name="meta" />
      </template>
    </PageHeader>
    <slot />
  </section>
</template>

<script setup lang="ts">
import PageHeader from './PageHeader.vue'

withDefaults(
  defineProps<{
    title?: string
    description?: string
    back?: boolean
    testId?: string
  }>(),
  { title: '', description: '', back: false, testId: undefined },
)
</script>

<style scoped>
.ob-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
</style>
