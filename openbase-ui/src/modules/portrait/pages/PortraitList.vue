<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索画像（姓名/ID 模糊）" clearable style="width: 240px" />
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px">
        <el-option label="活跃" value="active" />
        <el-option label="停用" value="inactive" />
        <el-option label="归档" value="archived" />
      </el-select>
      <el-button type="primary" data-test="create-portrait" @click="createVisible = true">创建画像</el-button>
      <el-button @click="$router.push('/portrait/batch')">批量导入/导出</el-button>
    </div>
    <div class="ob-table-scroll">
      <el-table :data="profiles" stripe data-test="portrait-table">
        <el-table-column prop="name" label="画像名称" min-width="160" />
        <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标签" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="t in row.tags" :key="t" size="small" class="tag-item" type="info">{{ t }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="data_source" label="数据源" width="110" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/portrait/${row.id}`)">详情</el-button>
            <el-dropdown @command="(cmd: string) => flow(row, cmd)">
              <el-button link>状态流转</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="active">设为活跃</el-dropdown-item>
                  <el-dropdown-item command="inactive">停用</el-dropdown-item>
                  <el-dropdown-item command="archived">归档</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="createVisible" title="创建画像" width="480px">
      <el-form label-width="80px">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="数据源"><el-input v-model="form.data_source" placeholder="如：user_service" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" data-test="create-portrait-submit" @click="createProfile">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface Profile { id: number; name: string; description: string; status: string; tags: string[]; data_source: string }

const keyword = ref('')
const statusFilter = ref('')
const createVisible = ref(false)
const form = reactive({ name: '', description: '', data_source: '' })
const profiles = ref<Profile[]>([
  { id: 1, name: '核心用户-张伟', description: '高频使用 RAG 检索用户', status: 'active', tags: ['高频用户', 'RAG'], data_source: 'openllm' },
  { id: 2, name: '试用用户-李娜', description: '试用期用户，转化评估中', status: 'inactive', tags: ['试用'], data_source: 'signup' },
  { id: 3, name: '归档-旧版', description: '历史遗留画像', status: 'archived', tags: ['历史'], data_source: 'legacy' },
])

function statusType(status: string) {
  return { active: 'success', inactive: 'info', archived: 'warning' }[status] || 'info'
}
function statusLabel(status: string) {
  return { active: '活跃', inactive: '停用', archived: '归档' }[status] || status
}
function flow(row: Profile, status: string) {
  row.status = status
  ElMessage.success(`${row.name} 状态已更新为 ${statusLabel(status)}`)
}
function createProfile() {
  if (!form.name) { ElMessage.warning('请输入画像名称'); return }
  profiles.value.push({ id: Date.now(), name: form.name, description: form.description, status: 'active', tags: [], data_source: form.data_source || 'manual' })
  createVisible.value = false
  ElMessage.success('画像已创建')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.tag-item { margin-right: 4px; }
</style>
