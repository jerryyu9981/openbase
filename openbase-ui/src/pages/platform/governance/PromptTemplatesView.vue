<template>
  <PageContainer title="Prompt 模板" description="Prompt 资产、版本与导入（OpenLLM Prompt Template）" test-id="prompt-templates-view-page">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索模板" clearable style="width: 200px" data-test="pt-search" @keyup.enter="reload" />
      <el-select v-model="categoryFilter" placeholder="分类" clearable style="width: 140px" data-test="pt-category-filter" @change="reload">
        <el-option v-for="item in CATEGORIES" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-button type="primary" data-test="pt-search-btn" @click="reload">查询</el-button>
      <el-button type="primary" data-test="pt-new" @click="openCreate">新建模板</el-button>
      <el-upload :auto-upload="false" :show-file-list="false" accept=".json,.yaml,.yml" data-test="pt-import" @change="onImport">
        <el-button data-test="pt-import-btn">导入</el-button>
      </el-upload>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="pt-error"
      @close="errorMessage = ''"
    />

    <el-card header="Prompt 模板" data-test="pt-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="templates" stripe data-test="pt-table">
          <template #empty>
            <el-empty description="暂无模板" :image-size="60" data-test="pt-empty" />
          </template>
          <el-table-column label="模板名称" min-width="180">
            <template #default="{ row }">
              {{ row.name }}
              <el-tag v-if="row.is_system" size="small" type="info" class="ml-6">系统</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="分类" width="110">
            <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
          </el-table-column>
          <el-table-column prop="current_version" label="当前版本" width="100">
            <template #default="{ row }">v{{ row.current_version }}</template>
          </el-table-column>
          <el-table-column label="更新时间" width="170">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" :disabled="row.is_system" data-test="pt-edit" @click="openEdit(row)">
                编辑
              </el-button>
              <el-button link type="info" size="small" data-test="pt-versions" @click="openVersions(row)">版本</el-button>
              <el-popconfirm
                title="确认删除该模板？"
                :disabled="row.is_system"
                @confirm="remove(row.id)"
              >
                <template #reference>
                  <el-button link type="danger" size="small" :disabled="row.is_system" data-test="pt-delete">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        data-test="pt-pagination"
        @current-change="load"
        @size-change="reload"
      />
    </el-card>

    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑模板' : '新建模板'" width="580px" data-test="pt-dialog">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" data-test="pt-form-name" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="item in CATEGORIES" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="7"
            placeholder="支持 {{variable}} 变量"
            data-test="pt-form-content"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item v-if="editingId" label="变更说明">
          <el-input v-model="form.changelog" placeholder="可选，记录本次版本变更" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="pt-save" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="versionDrawer" :title="`版本历史 - ${currentTemplate?.name || ''}`" size="480px" data-test="pt-version-drawer">
      <div v-loading="versionLoading">
        <el-table :data="versions" size="small" data-test="pt-version-table">
          <template #empty>
            <el-empty description="暂无版本记录" :image-size="50" />
          </template>
          <el-table-column label="版本" width="80">
            <template #default="{ row }">v{{ row.version }}</template>
          </el-table-column>
          <el-table-column prop="changelog" label="变更说明" min-width="150" />
          <el-table-column label="时间" width="160">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                size="small"
                :disabled="currentTemplate?.is_system"
                @click="rollback(row.version)"
              >
                回滚
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  promptTemplatesApi,
  type LlmPromptTemplate,
  type LlmPromptVersion,
} from '@/core/api/governance'

/**
 * Prompt 模板（v1.9.5 R5 真实化）：`/prompt-templates` 列表/新建/更新/删除/版本/回滚/导入。
 * 系统模板由上游保护（不可改/删/回滚），前端同步禁用对应动作。
 */
const CATEGORIES = [
  { value: 'chat', label: '对话' },
  { value: 'translate', label: '翻译' },
  { value: 'summary', label: '摘要' },
  { value: 'code', label: '代码' },
  { value: 'analysis', label: '分析' },
  { value: 'custom', label: '自定义' },
]

const keyword = ref('')
const categoryFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')

const templates = ref<LlmPromptTemplate[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const dialogOpen = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({
  name: '',
  category: 'chat',
  content: '',
  description: '',
  changelog: '',
})

const versionDrawer = ref(false)
const versionLoading = ref(false)
const currentTemplate = ref<LlmPromptTemplate | null>(null)
const versions = ref<LlmPromptVersion[]>([])

function categoryLabel(category: string) {
  return CATEGORIES.find((item) => item.value === category)?.label || category
}
function formatTime(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await promptTemplatesApi.list({
      category: categoryFilter.value || undefined,
      keyword: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    templates.value = result.items
    total.value = result.total
  } catch (error) {
    errorMessage.value = `Prompt 模板加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  void load()
}

function openCreate() {
  errorMessage.value = ''
  editingId.value = null
  form.name = ''
  form.category = 'chat'
  form.content = ''
  form.description = ''
  form.changelog = ''
  dialogOpen.value = true
}

function openEdit(row: LlmPromptTemplate) {
  errorMessage.value = ''
  editingId.value = row.id
  form.name = row.name
  form.category = row.category
  form.content = row.content
  form.description = row.description || ''
  form.changelog = ''
  dialogOpen.value = true
}

async function save() {
  if (!form.name.trim() || !form.content.trim()) {
    ElMessage.warning('请填写名称与内容')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await promptTemplatesApi.update(editingId.value, {
        name: form.name.trim(),
        category: form.category,
        content: form.content,
        description: form.description || undefined,
        changelog: form.changelog || undefined,
      })
      ElMessage.success('模板已更新')
    } else {
      await promptTemplatesApi.create({
        name: form.name.trim(),
        category: form.category,
        content: form.content,
        description: form.description || undefined,
      })
      ElMessage.success('模板已创建')
    }
    dialogOpen.value = false
    await load()
  } catch (error) {
    errorMessage.value = `模板保存失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    saving.value = false
  }
}

async function remove(templateId: string) {
  try {
    await promptTemplatesApi.remove(templateId)
    ElMessage.success('模板已删除')
    await load()
  } catch (error) {
    errorMessage.value = `模板删除失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function openVersions(row: LlmPromptTemplate) {
  currentTemplate.value = row
  versionDrawer.value = true
  versionLoading.value = true
  versions.value = []
  try {
    const result = await promptTemplatesApi.versions(row.id)
    versions.value = result.items
  } catch (error) {
    errorMessage.value = `版本历史加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    versionLoading.value = false
  }
}

async function rollback(version: number) {
  if (!currentTemplate.value) return
  const templateId = currentTemplate.value.id
  try {
    await promptTemplatesApi.rollback(templateId, version)
    ElMessage.success(`已回滚到 v${version}`)
    const result = await promptTemplatesApi.versions(templateId)
    versions.value = result.items
    await load()
  } catch (error) {
    errorMessage.value = `版本回滚失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

function onImport(file: { raw?: File }) {
  const raw = file.raw
  if (!raw) return
  const reader = new FileReader()
  reader.onload = async () => {
    const content = String(reader.result || '')
    const format = /\.ya?ml$/i.test(raw.name) ? 'yaml' : 'json'
    try {
      const created = await promptTemplatesApi.importTemplate({ content, format })
      ElMessage.success(`模板 ${created.name} 导入成功`)
      await load()
    } catch (error) {
      errorMessage.value = `模板导入失败：${error instanceof Error ? error.message : '未知错误'}`
    }
  }
  reader.readAsText(raw)
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.ml-6 { margin-left: 6px; }
.pagination { margin-top: 12px; justify-content: flex-end; }
</style>
