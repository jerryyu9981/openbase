<template>
  <PageContainer title="画像数据权限" description="DPS 角色与权限码只读视图" test-id="dps-permission-view-page">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb-16"
      title="只读视图：DPS 角色/权限写操作已按 ADR-290-01 收口为 410，如需变更请前往平台身份域。"
      data-test="perm-readonly-notice"
    />

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="perm-error"
      @close="errorMessage = ''"
    />

    <el-card header="角色权限（只读）" data-test="perm-card">
      <div class="page-toolbar">
        <el-button :loading="loading" data-test="perm-refresh" @click="load">刷新</el-button>
      </div>
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="roles" stripe data-test="perm-table">
          <template #empty>
            <el-empty description="暂无角色" :image-size="50" data-test="perm-empty" />
          </template>
          <el-table-column prop="name" label="角色" min-width="150" show-overflow-tooltip />
          <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">{{ row.description || '—' }}</template>
          </el-table-column>
          <el-table-column label="权限数" width="90">
            <template #default="{ row }">{{ permissionsOf(row).length }}</template>
          </el-table-column>
          <el-table-column label="类型" width="90">
            <template #default="{ row }">
              <el-tag :type="isBuiltin(row) ? 'warning' : 'info'" size="small">
                {{ isBuiltin(row) ? '内置' : '自定义' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="perm-view" @click="openDetail(row)">查看权限</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-drawer v-model="detailOpen" :title="`权限明细 - ${current?.name || ''}`" size="420px" data-test="perm-drawer">
      <el-empty v-if="!currentPermissions.length" description="该角色暂无权限点" :image-size="50" />
      <div v-else class="perm-tags">
        <el-tag v-for="item in currentPermissions" :key="item" size="small" type="info">{{ item }}</el-tag>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, ref } from 'vue'
import { dpsApi, type DpsRole } from '@/core/api/dps'

/**
 * 画像数据权限（v1.12.0 XR-DPS-03 只读真实化）：
 * 数据源 `GET /dps-proxy/permissions/roles`；上游写面已 410，本页不提供任何写入口。
 */
const loading = ref(false)
const errorMessage = ref('')
const roles = ref<DpsRole[]>([])
const detailOpen = ref(false)
const current = ref<DpsRole | null>(null)
const currentPermissions = ref<string[]>([])

function permissionsOf(role: DpsRole): string[] {
  const raw = role.permissions
  if (Array.isArray(raw)) return raw.map((item) => String(item))
  if (typeof raw === 'string' && raw.trim()) {
    try {
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed.map((item) => String(item)) : []
    } catch {
      return raw.split(',').map((item) => item.trim()).filter(Boolean)
    }
  }
  return []
}

function isBuiltin(role: DpsRole): boolean {
  return role.is_builtin === true || role.is_builtin === 1
}

function openDetail(role: DpsRole) {
  current.value = role
  currentPermissions.value = permissionsOf(role)
  detailOpen.value = true
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    roles.value = await dpsApi.getPermissionRoles()
  } catch (error) {
    errorMessage.value = `角色权限加载失败：${error instanceof Error ? error.message : '未知错误'}`
    roles.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.perm-tags { display: flex; flex-wrap: wrap; gap: 8px; }
</style>
