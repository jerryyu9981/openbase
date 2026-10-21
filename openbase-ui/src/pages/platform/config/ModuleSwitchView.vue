<template>
  <PageContainer
    title="模块开关"
    description="控制各业务模块的启用状态。修改后立即生效：侧栏菜单与模块路由同步增删（后端仍按 next_login 记录审计留痕）。"
    test-id="module-switch-page"
  >
    <template #actions>
      <el-button data-test="refresh-modules" @click="load()">刷新</el-button>
    </template>

    <el-alert
      v-if="loadingError"
      type="error"
      :closable="false"
      :title="`加载失败：${loadingError}`"
      class="mb12"
    />

    <el-alert
      v-if="migratedModules.length"
      type="info"
      :closable="false"
      class="mb12"
      data-test="module-migrated-hint"
      :title="`${migratedModules.map((m) => m.name).join('、')} 已迁入公共功能（页面常驻），不再随模块开关启停`"
    />

    <el-table v-loading="loading" :data="switchableModules" size="default" class="ob-table-scroll" :empty-text="emptyText">
      <el-table-column prop="name" label="模块" min-width="140" />
      <el-table-column prop="id" label="模块 ID" min-width="120">
        <template #default="{ row }"><span class="mono">{{ row.id }}</span></template>
      </el-table-column>
      <el-table-column prop="route_prefix" label="路由前缀" min-width="120">
        <template #default="{ row }"><span class="mono">{{ row.route_prefix }}</span></template>
      </el-table-column>
      <el-table-column prop="permission" label="权限标识" min-width="140">
        <template #default="{ row }"><span class="mono">{{ row.permission }}</span></template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'enabled' ? 'success' : 'info'">
            {{ row.status === 'enabled' ? '已启用' : '已停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-switch
            :model-value="row.status === 'enabled'"
            :loading="switchingId === row.id"
            :disabled="switchingId !== null"
            data-test="module-switch"
            @change="(next: string | number | boolean) => toggle(row, next)"
          />
          <span class="ml8">{{ row.status === 'enabled' ? '启用中' : '停用中' }}</span>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="drawerVisible" title="修改详情" size="420px">
      <el-descriptions v-if="lastResult" :column="1" border>
        <el-descriptions-item label="模块">{{ lastResult.id }}</el-descriptions-item>
        <el-descriptions-item label="新状态">{{ lastResult.status }}</el-descriptions-item>
        <el-descriptions-item label="前端生效">立即生效（菜单/路由已同步）</el-descriptions-item>
        <el-descriptions-item label="审计口径">{{ lastResult.effective === 'next_login' ? '下次登录/刷新' : lastResult.effective }}</el-descriptions-item>
        <el-descriptions-item label="请求号">
          <span class="mono">{{ lastResult.request_id }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageContainer from '@/components/page/PageContainer.vue'
import { listModuleDefinitions, modulesWriteApi, type ModuleDefinition, type ModuleSwitchResult } from '@/core/api/modules'
import { useAuthStore } from '@/core/stores/auth'
import { useModuleRegistry } from '@/core/stores/moduleRegistry'

const auth = useAuthStore()
const registry = useModuleRegistry()

const modules = ref<ModuleDefinition[]>([])
const loading = ref(false)
const loadingError = ref('')
const switchingId = ref<string | null>(null)
const drawerVisible = ref(false)
const lastResult = ref<ModuleSwitchResult | null>(null)

const emptyText = computed(() => (loading.value ? '加载中…' : '暂无模块'))

/**
 * 已迁入公共功能的模块（v1.4.11）：其前端页面已常驻 `/platform/**`，不再由模块路由装载，
 * 因此开关对其前端无效果——只做只读说明，不提供可误导的切换。
 */
const MIGRATED_MODULE_IDS = new Set(['gateway'])

const switchableModules = computed(() => modules.value.filter((m) => !MIGRATED_MODULE_IDS.has(m.id)))
const migratedModules = computed(() => modules.value.filter((m) => MIGRATED_MODULE_IDS.has(m.id)))

async function load() {
  loading.value = true
  loadingError.value = ''
  try {
    modules.value = await listModuleDefinitions()
  } catch (error) {
    loadingError.value = (error as Error).message || '请求失败'
  } finally {
    loading.value = false
  }
}

async function toggle(row: ModuleDefinition, next: string | number | boolean) {
  const nextStatus = next === true ? 'enabled' : 'disabled'
  if (row.status === nextStatus) return
  switchingId.value = row.id
  try {
    const result = await modulesWriteApi.switch(row.id, nextStatus)
    lastResult.value = result
    const target = modules.value.find((m) => m.id === row.id)
    if (target) target.status = result.status
    // 即时生效：重建注册表 + 同步模块路由（侧栏菜单随之增删）。
    // 同步失败不回滚后端结果（已留痕），仅提示需刷新页面。
    try {
      await registry.reload(auth.permissions)
    } catch (reloadError) {
      console.warn('[module-switch] registry reload failed', reloadError)
      ElMessage.warning('模块状态已保存，但菜单同步失败，请刷新页面')
    }
    ElMessage.success(`模块 ${row.id} 已${nextStatus === 'enabled' ? '启用' : '停用'}，已即时生效`)
    drawerVisible.value = true
  } catch (error) {
    ElMessage.error((error as Error).message || '操作失败')
    // 失败则回滚开关视觉状态：重载以服务端为准
    await load()
  } finally {
    switchingId.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.mb12 { margin-bottom: 12px; }
.ml8 { margin-left: 8px; }
</style>
