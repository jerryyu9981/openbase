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

    <!-- TD-13-25 标签管理：顶部统计卡片（真实 DPS 标签分类数据） -->
    <el-row :gutter="16" class="mb-16">
      <el-col v-for="stat in statCards" :key="stat.label" :xs="12" :sm="8" :md="6">
        <el-card shadow="hover" class="stat-card" data-test="tag-stat-card">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="text-secondary stat-label">{{ stat.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索分类名称" clearable style="width: 220px" data-test="tag-search" />
      <el-button type="primary" data-test="create-tag" @click="openForm()">新建分类</el-button>
      <el-button :loading="loading" data-test="tag-refresh" @click="loadData">刷新</el-button>
    </div>

    <!-- 分类列表（加载态 + 空态） -->
    <div v-loading="loading" class="ob-table-scroll">
      <el-table :data="filteredTags" stripe data-test="tag-table">
        <el-table-column prop="name" label="分类名" min-width="160" />
        <el-table-column prop="description" label="描述" min-width="220">
          <template #default="{ row }">
            <span :class="{ 'text-secondary': !row.description }">{{ row.description || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="edit-tag" @click="openForm(row)">编辑</el-button>
            <el-popconfirm :title="deleteTitle(row)" @confirm="removeTag(row)">
              <template #reference><el-button link type="danger" data-test="delete-tag">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无标签分类，点击右上角新建" :image-size="90" data-test="tag-empty" />
        </template>
      </el-table>
    </div>

    <!-- 新建/编辑标签分类 -->
    <el-dialog v-model="formVisible" :title="editingId ? '编辑分类' : '新建分类'" width="480px" data-test="tag-dialog">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：行为标签" data-test="tag-name-input" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="分类用途说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="tag-submit" @click="saveTag">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsTagCategory } from '@/core/api/dps'

interface TagForm {
  name: string
  description: string
}

const keyword = ref('')
const formVisible = ref(false)
const editingId = ref<string | null>(null)
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const form = reactive<TagForm>({ name: '', description: '' })
const categories = ref<DpsTagCategory[]>([])

const statCards = computed(() => [
  { label: '标签分类总数', value: categories.value.length },
  { label: '含描述分类', value: categories.value.filter((c) => c.description).length },
])

const filteredTags = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return categories.value
  return categories.value.filter((c) => String(c.name ?? '').toLowerCase().includes(kw))
})

function deleteTitle(row: DpsTagCategory) {
  return `确认删除分类「${row.name}」？删除后不可恢复`
}

function formatTime(v?: string): string {
  if (!v) return '-'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? String(v).slice(0, 10) : d.toLocaleString('zh-CN', { hour12: false })
}

function openForm(row?: DpsTagCategory) {
  errorMessage.value = ''
  editingId.value = row?.id ?? null
  form.name = row?.name ?? ''
  form.description = row?.description ?? ''
  formVisible.value = true
}

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await dpsApi.listTagCategories()
    categories.value = result.items || []
  } catch (err) {
    categories.value = []
    errorMessage.value = `标签分类加载失败：${(err as Error).message || '网络错误'}`
  } finally {
    loading.value = false
  }
}

async function saveTag() {
  const name = form.name.trim()
  if (!name) {
    ElMessage.warning('请输入分类名称')
    return
  }
  const duplicated = categories.value.some((c) => c.name === name && c.id !== editingId.value)
  if (duplicated) {
    errorMessage.value = `分类名称「${name}」已存在，请更换名称`
    return
  }
  errorMessage.value = ''
  saving.value = true
  try {
    if (editingId.value) {
      await dpsApi.updateTagCategory(editingId.value, { name, description: form.description.trim() })
      ElMessage.success('分类已更新')
    } else {
      await dpsApi.createTagCategory({ name, description: form.description.trim() })
      ElMessage.success('分类已创建')
    }
    formVisible.value = false
    await loadData()
  } catch (err) {
    errorMessage.value = `${editingId.value ? '更新' : '创建'}失败：${(err as Error).message || '网络错误'}`
  } finally {
    saving.value = false
  }
}

async function removeTag(row: DpsTagCategory) {
  errorMessage.value = ''
  try {
    await dpsApi.deleteTagCategory(String(row.id))
    ElMessage.success(`分类「${row.name}」已删除`)
    await loadData()
  } catch (err) {
    errorMessage.value = `删除失败：${(err as Error).message || '网络错误'}`
  }
}

onMounted(() => {
  void loadData()
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.mb-16 { margin-bottom: 16px; }
.text-secondary { color: var(--ob-text-secondary); }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; color: var(--ob-text); }
.stat-label { margin-top: 6px; font-size: 13px; }
</style>
