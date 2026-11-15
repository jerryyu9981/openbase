<template>
  <div data-test="attribute-field-table">
    <el-alert type="info" show-icon :closable="false" class="mb-12">
      <template #title>属性字段按「分组 → 字段 key 数组」组织（与运行态 attributes_schema 契约一致）</template>
      <div>字段 key 建议使用 snake_case；跨分组重复会提示冲突，保存时原样写入 JSONB，未识别键不受影响。</div>
    </el-alert>

    <el-card v-for="(group, groupIndex) in groups" :key="group.name + groupIndex" shadow="never" class="group-card" data-test="attribute-group">
      <div class="group-head">
        <el-input :model-value="group.name" size="small" class="group-name" placeholder="分组名，如 identity" data-test="attribute-group-name" @update:model-value="(value: string) => renameGroup(group.name, value)" />
        <span class="muted sm">{{ group.fields.length }} 个字段</span>
        <el-button link type="danger" size="small" data-test="attribute-group-remove" @click="removeGroup(group.name)">删除分组</el-button>
      </div>
      <div class="field-tags">
        <el-tag
          v-for="field in group.fields"
          :key="field"
          :type="duplicates.has(field) ? 'warning' : 'info'"
          closable
          size="small"
          data-test="attribute-field-tag"
          @close="removeField(group.name, field)"
        >
          {{ field }}
        </el-tag>
        <span v-if="!group.fields.length" class="muted sm">暂无字段</span>
      </div>
      <div class="add-row">
        <el-input
          v-model="drafts[group.name]"
          size="small"
          placeholder="新增字段 key，回车添加"
          class="add-input"
          data-test="attribute-field-input"
          @keyup.enter="addField(group.name)"
        />
        <el-button size="small" data-test="attribute-field-add" @click="addField(group.name)">添加</el-button>
      </div>
    </el-card>

    <div class="add-row">
      <el-input v-model="newGroupName" size="small" placeholder="新分组名" class="add-input" data-test="attribute-group-input" @keyup.enter="addGroup" />
      <el-button size="small" type="primary" plain data-test="attribute-group-add" @click="addGroup">＋新增分组</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

const props = defineProps<{ modelValue: Record<string, string[]> }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: Record<string, string[]>): void }>()

const drafts = reactive<Record<string, string>>({})
const newGroupName = ref('')

const groups = computed(() =>
  Object.entries(props.modelValue || {}).map(([name, fields]) => ({
    name,
    fields: Array.isArray(fields) ? fields : [],
  })),
)

const duplicates = computed(() => {
  const counts = new Map<string, number>()
  groups.value.forEach((group) => group.fields.forEach((field) => counts.set(field, (counts.get(field) || 0) + 1)))
  return new Set([...counts.entries()].filter(([, count]) => count > 1).map(([field]) => field))
})

function commit(next: Record<string, string[]>) {
  emit('update:modelValue', next)
}

function renameGroup(oldName: string, newName: string) {
  const next: Record<string, string[]> = {}
  for (const [name, fields] of Object.entries(props.modelValue || {})) {
    next[name === oldName ? newName : name] = fields
  }
  commit(next)
}

function removeGroup(name: string) {
  const next: Record<string, string[]> = { ...(props.modelValue || {}) }
  delete next[name]
  commit(next)
}

function addGroup() {
  const name = newGroupName.value.trim()
  if (!name) return
  commit({ ...(props.modelValue || {}), [name]: props.modelValue?.[name] || [] })
  newGroupName.value = ''
}

function addField(groupName: string) {
  const field = String(drafts[groupName] || '').trim()
  if (!field) return
  const fields = props.modelValue?.[groupName] || []
  if (fields.includes(field)) return
  commit({ ...(props.modelValue || {}), [groupName]: [...fields, field] })
  drafts[groupName] = ''
}

function removeField(groupName: string, field: string) {
  const fields = (props.modelValue?.[groupName] || []).filter((item) => item !== field)
  commit({ ...(props.modelValue || {}), [groupName]: fields })
}
</script>

<style scoped>
.mb-12 { margin-bottom: 12px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; margin-left: 6px; }
.group-card { margin-bottom: 12px; }
.group-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.group-name { width: 220px; }
.field-tags { display: flex; flex-wrap: wrap; gap: 6px; min-height: 24px; }
.add-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.add-input { width: 220px; }
</style>
