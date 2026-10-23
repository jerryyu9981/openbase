<template>
  <PageContainer title="工作空间" description="工作空间、成员与 Virtual Key（OpenLLM 团队空间）" test-id="workspaces-view-page">
    <div class="page-toolbar">
      <el-button type="primary" data-test="ws-new" @click="openCreate">新建工作空间</el-button>
      <el-button :loading="loading" data-test="ws-refresh" @click="loadWorkspaces">刷新</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="ws-error"
      @close="errorMessage = ''"
    />

    <el-card header="工作空间" data-test="ws-card">
      <div v-loading="loading" class="ob-table-scroll">
        <el-table :data="workspaces" stripe data-test="ws-table">
          <template #empty>
            <el-empty description="暂无工作空间" :image-size="60" data-test="ws-empty" />
          </template>
          <el-table-column prop="name" label="名称" min-width="150" />
          <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
          <el-table-column label="成员数" width="90">
            <template #default="{ row }">{{ resourcesMap[row.id]?.member_count ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="Virtual Key" min-width="200">
            <template #default="{ row }">
              <el-tag v-if="keysMap[row.id]?.length" size="small" type="warning" class="key-tag">
                {{ maskKey(keysMap[row.id][0].key_prefix) }}
              </el-tag>
              <span v-else class="key-empty">未创建</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
                {{ row.status === 'active' ? '启用' : row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="ws-members" @click="openMembers(row)">成员</el-button>
              <el-button link type="primary" size="small" data-test="ws-key" @click="rotateOrCreateKey(row)">
                {{ keysMap[row.id]?.length ? '轮换 Key' : '创建 Key' }}
              </el-button>
              <el-popconfirm title="确认删除该工作空间？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small" data-test="ws-delete">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="dialogOpen" title="新建工作空间" width="480px" data-test="ws-dialog">
      <el-form :model="form" label-width="70px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" data-test="ws-name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="ws-save" @click="save">创建</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="memberDrawer" :title="`成员管理 - ${currentWs?.name || ''}`" size="440px" data-test="ws-members-drawer">
      <div v-loading="memberLoading">
        <el-table :data="currentMembers" size="small" data-test="ws-member-table">
          <template #empty>
            <el-empty description="暂无成员" :image-size="50" />
          </template>
          <el-table-column label="用户" min-width="150">
            <template #default="{ row }">{{ row.username || row.user_id }}</template>
          </el-table-column>
          <el-table-column prop="role" label="角色" width="90" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button link type="danger" size="small" @click="removeMember(row.user_id)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="member-add">
        <el-input v-model="newMemberName" placeholder="用户名" size="small" data-test="ws-member-name" />
        <el-select v-model="newMemberRole" size="small" style="width: 110px">
          <el-option label="管理员" value="admin" />
          <el-option label="成员" value="member" />
          <el-option label="只读" value="viewer" />
        </el-select>
        <el-button size="small" type="primary" :loading="memberSaving" data-test="ws-member-add" @click="addMember">添加</el-button>
      </div>
    </el-drawer>

    <el-dialog v-model="keyDialogVisible" title="Virtual Key（仅显示一次）" width="560px" data-test="ws-key-dialog">
      <el-alert type="warning" :closable="false" show-icon title="请立即保存该 Key，关闭后无法再次查看完整值" class="mb-16" />
      <el-input :model-value="createdKey" readonly data-test="ws-key-value" />
      <template #footer>
        <el-button type="primary" @click="keyDialogVisible = false">我已保存</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  virtualKeysApi,
  workspacesApi,
  type LlmVirtualKey,
  type LlmWorkspace,
  type LlmWorkspaceMember,
  type LlmWorkspaceResources,
} from '@/core/api/governance'

/**
 * 工作空间（v1.9.5 R5 真实化）：`/workspaces` 列表/新建/删除、成员增删、资源统计；
 * Virtual Key 走 `/virtual-keys`（列表/创建/轮换），完整 Key 仅在创建/轮换响应中出现一次。
 * v1.12.0（XR-LLM-06）：成员邀请支持按用户名（精确匹配），不再要求用户 UUID。
 */
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const workspaces = ref<LlmWorkspace[]>([])
const resourcesMap = ref<Record<string, LlmWorkspaceResources>>({})
const keysMap = ref<Record<string, LlmVirtualKey[]>>({})

const dialogOpen = ref(false)
const form = reactive({ name: '', description: '' })

const memberDrawer = ref(false)
const memberLoading = ref(false)
const memberSaving = ref(false)
const currentWs = ref<LlmWorkspace | null>(null)
const currentMembers = ref<LlmWorkspaceMember[]>([])
const newMemberName = ref('')
const newMemberRole = ref('member')

const keyDialogVisible = ref(false)
const createdKey = ref('')

function maskKey(prefix: string) {
  if (!prefix) return '-'
  return `${prefix}****`
}

async function loadWorkspaces() {
  loading.value = true
  errorMessage.value = ''
  try {
    const items = await workspacesApi.list({ limit: 200 })
    workspaces.value = items
    const entries = await Promise.all(
      items.map(async (item) => {
        const [resources, keys] = await Promise.all([
          workspacesApi.resources(item.id).catch(() => null),
          virtualKeysApi.list({ workspace_id: item.id }).catch(() => [] as LlmVirtualKey[]),
        ])
        return { id: item.id, resources, keys }
      }),
    )
    const nextResources: Record<string, LlmWorkspaceResources> = {}
    const nextKeys: Record<string, LlmVirtualKey[]> = {}
    for (const entry of entries) {
      if (entry.resources) nextResources[entry.id] = entry.resources
      nextKeys[entry.id] = entry.keys
    }
    resourcesMap.value = nextResources
    keysMap.value = nextKeys
  } catch (error) {
    errorMessage.value = `工作空间加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    loading.value = false
  }
}

function openCreate() {
  errorMessage.value = ''
  form.name = ''
  form.description = ''
  dialogOpen.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  saving.value = true
  try {
    await workspacesApi.create({ name: form.name.trim(), description: form.description || undefined })
    ElMessage.success('工作空间已创建')
    dialogOpen.value = false
    await loadWorkspaces()
  } catch (error) {
    errorMessage.value = `工作空间创建失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    saving.value = false
  }
}

async function remove(workspaceId: string) {
  try {
    await workspacesApi.remove(workspaceId)
    ElMessage.success('工作空间已删除')
    await loadWorkspaces()
  } catch (error) {
    errorMessage.value = `工作空间删除失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function openMembers(row: LlmWorkspace) {
  currentWs.value = row
  memberDrawer.value = true
  memberLoading.value = true
  newMemberName.value = ''
  try {
    currentMembers.value = await workspacesApi.members(row.id)
  } catch (error) {
    errorMessage.value = `成员列表加载失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    memberLoading.value = false
  }
}

async function addMember() {
  if (!currentWs.value || !newMemberName.value.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  memberSaving.value = true
  try {
    await workspacesApi.addMember(currentWs.value.id, {
      username: newMemberName.value.trim(),
      role: newMemberRole.value,
    })
    ElMessage.success('成员已添加')
    currentMembers.value = await workspacesApi.members(currentWs.value.id)
    newMemberName.value = ''
    await loadWorkspaces()
  } catch (error) {
    errorMessage.value = `添加成员失败：${error instanceof Error ? error.message : '未知错误'}`
  } finally {
    memberSaving.value = false
  }
}

async function removeMember(userId: string) {
  if (!currentWs.value) return
  try {
    await workspacesApi.removeMember(currentWs.value.id, userId)
    ElMessage.success('成员已移除')
    currentMembers.value = await workspacesApi.members(currentWs.value.id)
    await loadWorkspaces()
  } catch (error) {
    errorMessage.value = `移除成员失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

async function rotateOrCreateKey(row: LlmWorkspace) {
  try {
    const existing = keysMap.value[row.id]?.[0]
    const result = existing
      ? await virtualKeysApi.rotate(existing.id)
      : await virtualKeysApi.create(row.id, { name: `${row.name}-key` })
    createdKey.value = result.key
    keyDialogVisible.value = true
    await loadWorkspaces()
  } catch (error) {
    errorMessage.value = `Virtual Key 操作失败：${error instanceof Error ? error.message : '未知错误'}`
  }
}

onMounted(loadWorkspaces)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.key-tag { font-family: monospace; }
.key-empty { color: var(--ob-text-secondary); font-size: 12px; }
.member-add { display: flex; gap: 8px; margin-top: 12px; }
</style>
