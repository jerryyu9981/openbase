<template>
  <div class="page">
    <div class="page-toolbar">
      <div>
        <h2 class="page-title">模块开关</h2>
        <p class="page-desc">
          控制各业务模块的启用状态。修改后<b>下次登录/刷新生效</b>（不热生效，ADR-146-07）；操作会写入审计留痕。
        </p>
      </div>
      <el-button data-test="refresh-modules" @click="load()">刷新</el-button>
    </div>

    <el-alert
      v-if="loadingError"
      type="error"
      :closable="false"
      :title="`加载失败：${loadingError}`"
      class="mb12"
    />

    <el-table v-loading="loading" :data="modules" size="default" class="ob-table-scroll" :empty-text="emptyText">
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
        <el-descriptions-item label="生效方式">{{ lastResult.effective === 'next_login' ? '下次登录/刷新' : lastResult.effective }}</el-descriptions-item>
        <el-descriptions-item label="请求号">
          <span class="mono">{{ lastResult.request_id }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listModuleDefinitions, modulesWriteApi, type ModuleDefinition, type ModuleSwitchResult } from '@/core/api/modules'

const modules = ref<ModuleDefinition[]>([])
const loading = ref(false)
const loadingError = ref('')
const switchingId = ref<string | null>(null)
const drawerVisible = ref(false)
const lastResult = ref<ModuleSwitchResult | null>(null)

const emptyText = computed(() => (loading.value ? '加载中…' : '暂无模块'))

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
    // 以服务端回读为准刷新状态（语义不变：不热生效，注册表仍显示目标状态）
    const target = modules.value.find((m) => m.id === row.id)
    if (target) target.status = result.status
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
.page-title { font-size: 18px; font-weight: 600; margin: 0 0 4px; }
.page-desc { font-size: 13px; color: var(--el-text-color-secondary); margin: 0 0 12px; }
.mb12 { margin-bottom: 12px; }
.ml8 { margin-left: 8px; }
</style>