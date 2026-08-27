<template>
  <div>
    <!-- 错误态 -->
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="tag-error"
      @close="errorMessage = ''"
    />

    <!-- TD-13-25 标签管理：顶部标签统计卡片 -->
    <el-row :gutter="16" class="mb-16">
      <el-col v-for="stat in statCards" :key="stat.label" :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card" data-test="tag-stat-card">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="text-secondary stat-label">{{ stat.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索标签名称" clearable style="width: 220px" data-test="tag-search" />
      <el-button type="primary" data-test="create-tag" @click="openForm()">新建标签</el-button>
    </div>

    <!-- 标签列表（加载态 + 空态） -->
    <div v-loading="deletingId !== null" class="ob-table-scroll">
      <el-table :data="filteredTags" stripe data-test="tag-table">
        <el-table-column prop="name" label="标签名" min-width="150" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="tagTypeOf(row.type)" size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="usage_count" label="使用画像数" width="110" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="edit-tag" @click="openForm(row)">编辑</el-button>
            <!-- 破坏性操作：删除二次确认 -->
            <el-popconfirm :title="deleteTitle(row)" @confirm="removeTag(row)">
              <template #reference><el-button link type="danger" data-test="delete-tag">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无标签数据" :image-size="90" data-test="tag-empty" />
        </template>
      </el-table>
    </div>

    <!-- 新建/编辑标签 -->
    <el-dialog v-model="formVisible" :title="editingId ? '编辑标签' : '新建标签'" width="480px" data-test="tag-dialog">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：高频用户" data-test="tag-name-input" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="画像" value="画像" />
            <el-option label="行为" value="行为" />
            <el-option label="偏好" value="偏好" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="标签用途说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" data-test="tag-submit" @click="saveTag">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface TagRow {
  id: number
  name: string
  type: string
  description: string
  usage_count: number
  created_at: string
}

interface TagForm {
  name: string
  type: string
  description: string
}

const keyword = ref('')
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)
const errorMessage = ref('')
const form = reactive<TagForm>({ name: '', type: '画像', description: '' })

/** 契约 mock：本地标签数据，不调用真实 API */
const mockTags = ref<TagRow[]>([
  { id: 1, name: '高频用户', type: '行为', description: '近 30 天登录超过 15 次的用户', usage_count: 128, created_at: '2026-07-01 10:00' },
  { id: 2, name: 'RAG 检索偏好', type: '偏好', description: '偏好 RAG 检索类内容', usage_count: 96, created_at: '2026-07-03 14:20' },
  { id: 3, name: '技术型', type: '画像', description: '技术类画像标签', usage_count: 214, created_at: '2026-07-05 09:30' },
  { id: 4, name: '试用用户', type: '画像', description: '试用期用户', usage_count: 58, created_at: '2026-07-10 16:45' },
  { id: 5, name: '付费用户', type: '画像', description: '已付费用户', usage_count: 173, created_at: '2026-07-12 11:10' },
  { id: 6, name: '流失预警', type: '行为', description: '近 14 天未活跃用户', usage_count: 41, created_at: '2026-07-18 15:00' },
  { id: 7, name: '夜间活跃', type: '行为', description: '22:00-02:00 活跃用户', usage_count: 67, created_at: '2026-07-22 20:30' },
  { id: 8, name: '内容偏好', type: '偏好', description: '偏好深度长文内容', usage_count: 89, created_at: '2026-07-25 09:00' },
  { id: 9, name: '新客首单', type: '行为', description: '完成首单的新客', usage_count: 0, created_at: '2026-08-01 10:00' },
])

const statCards = computed(() => {
  const total = mockTags.value.length
  const portrait = mockTags.value.filter((tag) => tag.type === '画像').length
  const behavior = mockTags.value.filter((tag) => tag.type === '行为').length
  const preference = mockTags.value.filter((tag) => tag.type === '偏好').length
  return [
    { label: '总标签数', value: total },
    { label: '画像标签', value: portrait },
    { label: '行为标签', value: behavior },
    { label: '偏好标签', value: preference },
  ]
})

const filteredTags = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return mockTags.value
  return mockTags.value.filter((tag) => tag.name.toLowerCase().includes(kw))
})

function tagTypeOf(type: string) {
  return { 画像: 'primary', 行为: 'success', 偏好: 'warning' }[type] || 'info'
}

function deleteTitle(row: TagRow) {
  return `确认删除标签「${row.name}」？删除后不可恢复`
}

function openForm(row?: TagRow) {
  errorMessage.value = ''
  editingId.value = row?.id ?? null
  form.name = row?.name ?? ''
  form.type = row?.type ?? '画像'
  form.description = row?.description ?? ''
  formVisible.value = true
}

function saveTag() {
  const name = form.name.trim()
  if (!name) {
    ElMessage.warning('请输入标签名称')
    return
  }
  const duplicated = mockTags.value.some((tag) => tag.name === name && tag.id !== editingId.value)
  if (duplicated) {
    errorMessage.value = `标签名称「${name}」已存在，请更换名称`
    return
  }
  errorMessage.value = ''
  if (editingId.value) {
    const target = mockTags.value.find((tag) => tag.id === editingId.value)
    if (target) {
      target.name = name
      target.type = form.type
      target.description = form.description.trim()
      ElMessage.success('标签已更新')
    }
  } else {
    mockTags.value.push({
      id: Date.now(),
      name,
      type: form.type,
      description: form.description.trim(),
      usage_count: 0,
      created_at: formatNow(),
    })
    ElMessage.success('标签已创建')
  }
  formVisible.value = false
}

function removeTag(row: TagRow) {
  if (row.usage_count > 0) {
    errorMessage.value = `标签「${row.name}」已被 ${row.usage_count} 个画像使用，无法删除，请先解除关联`
    return
  }
  deletingId.value = row.id
  window.setTimeout(() => {
    mockTags.value = mockTags.value.filter((tag) => tag.id !== row.id)
    deletingId.value = null
    ElMessage.success(`标签「${row.name}」已删除`)
  }, 300)
}

function formatNow(): string {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.mb-16 { margin-bottom: 16px; }
.text-secondary { color: var(--ob-text-secondary); }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; color: var(--ob-text); }
.stat-label { margin-top: 6px; font-size: 13px; }
</style>
