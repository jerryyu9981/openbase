<template>
  <div class="workspaces-page">
    <div class="page-toolbar">
      <el-button type="primary" data-test="ws-new" @click="openCreate">新建工作空间</el-button>
    </div>
    <el-card header="工作空间" data-test="ws-card">
      <div class="ob-table-scroll">
        <el-table :data="workspaces" stripe empty-text="暂无工作空间" data-test="ws-table">
          <el-table-column prop="name" label="名称" min-width="150" />
          <el-table-column prop="description" label="描述" min-width="180" />
          <el-table-column prop="member_count" label="成员数" width="90" />
          <el-table-column label="Virtual Key" min-width="180">
            <template #default="{ row }">
              <el-tag v-if="row.virtualKey" size="small" type="warning" class="key-tag">{{ maskKey(row.virtualKey) }}</el-tag>
              <span v-else class="key-empty">未创建</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="260">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openMembers(row)">成员</el-button>
              <el-button link type="primary" size="small" data-test="ws-key" @click="rotateKey(row)">轮换 Key</el-button>
              <el-popconfirm title="确认删除该工作空间？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 新建 -->
    <el-dialog v-model="dialogOpen" title="新建工作空间" width="480px" data-test="ws-dialog">
      <el-form :model="form" label-width="70px">
        <el-form-item label="名称">
          <el-input v-model="form.name" data-test="ws-name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" data-test="ws-save" @click="save">创建</el-button>
      </template>
    </el-dialog>

    <!-- 成员 -->
    <el-drawer v-model="memberDrawer" :title="`成员管理 - ${currentWs?.name || ''}`" size="360px" data-test="ws-members-drawer">
      <el-table :data="currentMembers" size="small" empty-text="暂无成员">
        <el-table-column prop="username" label="用户" />
        <el-table-column prop="role" label="角色" width="90" />
      </el-table>
      <div class="member-add">
        <el-input v-model="newMember" placeholder="输入用户名添加" size="small" />
        <el-button size="small" type="primary" data-test="ws-member-add" @click="addMember">添加</el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface Workspace {
  id: number
  name: string
  description: string
  member_count: number
  virtualKey: string | null
}

const workspaces = ref<Workspace[]>([
  { id: 1, name: '默认工作空间', description: '平台默认空间', member_count: 3, virtualKey: 'ob_sk_live_8f3a2b1c9d4e' },
  { id: 2, name: '模型组空间', description: '模型研发专用', member_count: 5, virtualKey: null },
])

const dialogOpen = ref(false)
const form = ref({ name: '', description: '' })
const memberDrawer = ref(false)
const currentWs = ref<Workspace | null>(null)
const currentMembers = ref<Array<{ username: string; role: string }>>([])
const newMember = ref('')

function openCreate() {
  form.value = { name: '', description: '' }
  dialogOpen.value = true
}

function save() {
  if (!form.value.name) {
    ElMessage.warning('请填写名称')
    return
  }
  const id = Math.max(0, ...workspaces.value.map((w) => w.id)) + 1
  workspaces.value.push({ id, name: form.value.name, description: form.value.description, member_count: 0, virtualKey: null })
  ElMessage.success('工作空间已创建')
  dialogOpen.value = false
}

function openMembers(row: Workspace) {
  currentWs.value = row
  currentMembers.value = [{ username: 'admin', role: 'owner' }]
  memberDrawer.value = true
}

function addMember() {
  if (!newMember.value) return
  currentMembers.value.push({ username: newMember.value, role: 'member' })
  if (currentWs.value) currentWs.value.member_count += 1
  newMember.value = ''
  ElMessage.success('成员已添加')
}

function rotateKey(row: Workspace) {
  row.virtualKey = `ob_sk_live_${Math.random().toString(16).slice(2, 14)}`
  ElMessage.success('Virtual Key 已轮换（旧密钥已失效）')
}

function maskKey(key: string) {
  return `${key.slice(0, 12)}...${key.slice(-4)}`
}

function remove(id: number) {
  workspaces.value = workspaces.value.filter((w) => w.id !== id)
  ElMessage.success('工作空间已删除')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.key-tag { font-family: monospace; }
.key-empty { color: #909399; font-size: 12px; }
.member-add { display: flex; gap: 8px; margin-top: 12px; }
</style>
