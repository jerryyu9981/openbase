<template>
  <div class="prompt-templates">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索模板" clearable style="width: 200px" data-test="pt-search" />
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 130px" data-test="pt-status-filter">
        <el-option label="启用" value="enabled" />
        <el-option label="停用" value="disabled" />
      </el-select>
      <el-button type="primary" data-test="pt-new" @click="openCreate">新建模板</el-button>
      <el-upload :auto-upload="false" :show-file-list="false" accept=".json,.md" data-test="pt-import" @change="onImport">
        <el-button data-test="pt-import-btn">导入</el-button>
      </el-upload>
    </div>

    <el-card header="Prompt 模板" data-test="pt-card">
      <div class="ob-table-scroll">
        <el-table :data="filteredTemplates" stripe empty-text="暂无模板" data-test="pt-table">
          <el-table-column prop="name" label="模板名称" min-width="160" />
          <el-table-column prop="category" label="分类" width="110" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" data-test="pt-toggle" @change="toggle(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column label="操作" width="210">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-popover trigger="click" placement="bottom" width="300">
                <template #reference>
                  <el-button link type="info" size="small" data-test="pt-versions">版本</el-button>
                </template>
                <div class="version-list">
                  <div v-for="v in row.versionHistory" :key="v.version" class="version-row">
                    <span>v{{ v.version }}</span>
                    <el-button link type="primary" size="small" @click="rollback(row, v.version)">回滚</el-button>
                  </div>
                </div>
              </el-popover>
              <el-popconfirm title="确认删除该模板？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑模板' : '新建模板'" width="560px" data-test="pt-dialog">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="form.name" data-test="pt-form-name" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in ['通用', '客服', '代码', '翻译', '摘要']" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="6" placeholder="支持 {{variable}} 变量" data-test="pt-form-content" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" data-test="pt-save" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface PromptTemplate {
  id: number
  name: string
  category: string
  content: string
  enabled: boolean
  version: number
  versionHistory: Array<{ version: number; content: string }>
}

const mockTemplates: PromptTemplate[] = [
  { id: 1, name: '通用客服助手', category: '客服', content: '你是一名专业客服，请友好地解答用户问题：{{question}}', enabled: true, version: 3, versionHistory: [{ version: 3, content: 'v3' }, { version: 2, content: 'v2' }] },
  { id: 2, name: '代码审查助手', category: '代码', content: '请审查以下代码的质量、安全与性能：\n{{code}}', enabled: true, version: 1, versionHistory: [{ version: 1, content: 'v1' }] },
  { id: 3, name: '文章摘要模板', category: '摘要', content: '请将以下文章总结为 3 点要点：\n{{article}}', enabled: false, version: 2, versionHistory: [{ version: 2, content: 'v2' }, { version: 1, content: 'v1' }] },
]

const templates = ref<PromptTemplate[]>(mockTemplates.map((t) => ({ ...t, versionHistory: [...t.versionHistory] })))
const keyword = ref('')
const statusFilter = ref('')
const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const form = ref({ name: '', category: '通用', content: '' })

const filteredTemplates = computed(() =>
  templates.value.filter((t) => {
    const matchKw = !keyword.value || t.name.includes(keyword.value)
    const matchStatus = !statusFilter.value || (statusFilter.value === 'enabled') === t.enabled
    return matchKw && matchStatus
  }),
)

function openCreate() {
  editingId.value = null
  form.value = { name: '', category: '通用', content: '' }
  dialogOpen.value = true
}

function openEdit(row: PromptTemplate) {
  editingId.value = row.id
  form.value = { name: row.name, category: row.category, content: row.content }
  dialogOpen.value = true
}

function save() {
  if (!form.value.name || !form.value.content) {
    ElMessage.warning('请填写名称与内容')
    return
  }
  if (editingId.value) {
    const t = templates.value.find((x) => x.id === editingId.value)
    if (t) {
      t.name = form.value.name
      t.category = form.value.category
      t.content = form.value.content
      t.version += 1
      t.versionHistory.unshift({ version: t.version, content: '新版本' })
    }
    ElMessage.success('模板已更新')
  } else {
    const id = Math.max(0, ...templates.value.map((t) => t.id)) + 1
    templates.value.push({
      id, name: form.value.name, category: form.value.category, content: form.value.content,
      enabled: true, version: 1, versionHistory: [{ version: 1, content: '初始版本' }],
    })
    ElMessage.success('模板已创建')
  }
  dialogOpen.value = false
}

function toggle(row: PromptTemplate) {
  void row
  ElMessage.success(row.enabled ? '模板已启用' : '模板已停用')
}

function rollback(row: PromptTemplate, version: number) {
  void row
  ElMessage.success(`已回滚到 v${version}`)
}

function remove(id: number) {
  templates.value = templates.value.filter((t) => t.id !== id)
  ElMessage.success('模板已删除')
}

function onImport(file: { raw?: File }) {
  const raw = file.raw
  if (!raw) return
  const reader = new FileReader()
  reader.onload = () => {
    const content = String(reader.result || '')
    const name = raw.name.replace(/\.(json|md)$/i, '')
    const id = Math.max(0, ...templates.value.map((t) => t.id)) + 1
    templates.value.push({
      id, name, category: '通用', content, enabled: true, version: 1,
      versionHistory: [{ version: 1, content: '导入版本' }],
    })
    ElMessage.success(`模板 ${name} 导入成功`)
  }
  reader.readAsText(raw)
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.version-list { max-height: 200px; overflow: auto; }
.version-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
</style>
