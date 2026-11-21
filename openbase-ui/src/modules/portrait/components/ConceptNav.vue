<template>
  <nav class="concept-nav" aria-label="画像域功能分区" data-test="concept-nav">
    <div class="concept-nav-title">
      <span class="label">功能分区</span>
      <span class="hint">标签 → 标注模板 → 标注 → 画像模板 → 画像</span>
    </div>
    <div class="concept-nav-items">
      <template v-for="(item, index) in items" :key="item.key">
        <RouterLink
          :to="item.to"
          class="concept-item"
          :class="{ active: item.key === current }"
          :aria-current="item.key === current ? 'page' : undefined"
          :data-test="`concept-${item.key}`"
        >
          <span class="name">{{ item.name }}</span>
          <span class="desc">{{ item.desc }}</span>
        </RouterLink>
        <span v-if="index < items.length - 1" class="arrow" aria-hidden="true">→</span>
      </template>
    </div>
  </nav>
</template>

<script setup lang="ts">
type ConceptKey = 'tag' | 'annotation-template' | 'annotation' | 'portrait-template' | 'portrait'

interface ConceptItem {
  key: ConceptKey
  name: string
  desc: string
  to: string
}

defineProps<{ current: ConceptKey }>()

const items: ConceptItem[] = [
  { key: 'tag', name: '标签', desc: '语义定义与词表', to: '/portrait/dps/tags' },
  { key: 'annotation-template', name: '标注模板', desc: '采集契约', to: '/portrait/dps/annotation-templates' },
  { key: 'annotation', name: '标注', desc: '采集记录与审核', to: '/portrait/dps/annotations' },
  { key: 'portrait-template', name: '画像模板', desc: '评分契约', to: '/portrait/dps/templates' },
  { key: 'portrait', name: '画像', desc: '计算结果与快照', to: '/portrait/list' },
]
</script>

<style scoped>
.concept-nav {
  margin-bottom: 16px;
  padding: 10px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-blank);
}

.concept-nav-title {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 8px;
}

.concept-nav-title .label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.concept-nav-title .hint {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.concept-nav-items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.concept-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  color: var(--el-text-color-regular);
  text-decoration: none;
}

.concept-item:hover {
  background: var(--el-fill-color-light);
}

.concept-item.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.concept-item .name {
  font-size: 13px;
  font-weight: 600;
}

.concept-item .desc {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.concept-item.active .desc {
  color: var(--el-color-primary);
}

.arrow {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}
</style>
