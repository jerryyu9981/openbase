<template>
  <PageContainer
    title="插件管理"
    description="插件注册、启停与工具清单（数据源：OpenLLM /api/v1/plugins，经 OpenBase 通用代理）"
    test-id="plugins-page"
  >
    <div class="page-toolbar">
      <el-select v-model="typeFilter" placeholder="类型" clearable style="width: 140px" data-test="plugin-type-filter">
        <el-option label="内置" value="builtin" />
        <el-option label="外部" value="external" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px" data-test="plugin-status-filter">
        <el-option label="已启用" value="enabled" />
        <el-option label="已禁用" value="disabled" />
      </el-select>
      <el-button :loading="loading" data-test="plugin-refresh" @click="load">刷新</el-button>
      <el-button type="primary" data-test="plugin-register" @click="openRegister">注册插件</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="plugin-error"
      @close="errorMessage = ''"
    />

    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb-16"
      title="启停会即时影响工具可用性；系统插件不允许删除。"
      data-test="plugin-notice"
    />

    <div v-loading="loading" class="ob-table-scroll">
      <el-table :data="plugins" stripe data-test="plugin-table">
        <template #empty>
          <el-empty description="暂无插件，可点击「注册插件」添加" :image-size="60" data-test="plugin-empty" />
        </template>
        <el-table-column label="插件" min-width="200">
          <template #default="{ row }">
            <div class="plugin-name">{{ row.display_name || row.name }}</div>
            <div class="plugin-code">{{ row.name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ typeLabel(row.plugin_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="90" />
        <el-table-column label="工具数" width="90">
          <template #default="{ row }">{{ toolCount(row) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-switch
              :model-value="row.status === 'enabled'"
              :loading="togglingId === row.id"
              data-test="plugin-toggle"
              @change="(val: boolean) => toggle(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column label="系统插件" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_system" size="small" type="warning">是</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="描述" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" data-test="plugin-health" @click="checkHealth(row)">健康检查</el-button>
            <el-popconfirm
              title="确认删除该插件？相关工具将不可用"
              :disabled="row.is_system"
              @confirm="remove(row)"
            >
              <template #reference>
                <el-button link type="danger" size="small" :disabled="row.is_system" data-test="plugin-delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-card class="mt-16" header="可用工具" data-test="plugin-tools-card">
      <div class="tool-hint" data-test="plugin-tools-hint">
        「运行期内建」= 运行时注册表中的内建工具（未落 plugin 表）；「插件注册」= 由已启用插件元数据提供。
      </div>
      <div v-loading="toolsLoading">
        <el-empty v-if="!tools.length" description="暂无可用工具" :image-size="60" data-test="plugin-tools-empty" />
        <el-table v-else :data="tools" stripe data-test="plugin-tools-table">
          <el-table-column prop="plugin_name" label="所属插件" width="160" />
          <el-table-column label="来源" width="120">
            <template #default="{ row }">
              <el-tag v-if="isRuntimeTool(row)" size="small" type="warning" data-test="tool-runtime-tag">运行期内建</el-tag>
              <el-tag v-else size="small" type="info">插件注册</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="tool_name" label="工具" width="200" />
          <el-table-column label="描述" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">{{ row.description || '—' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 注册插件 -->
    <el-dialog v-model="registerVisible" title="注册插件" width="520px" data-test="plugin-register-dialog">
      <el-form label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="唯一标识，如 http_tools" data-test="plugin-name-input" />
        </el-form-item>
        <el-form-item label="版本">
          <el-input v-model="form.version" placeholder="1.0.0" data-test="plugin-version-input" />
        </el-form-item>
        <el-form-item label="入口点">
          <el-input v-model="form.entry_point" placeholder="可选，插件入口路径" data-test="plugin-entry-input" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" data-test="plugin-desc-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="registerVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" data-test="plugin-register-submit" @click="submitRegister">注册</el-button>
      </template>
    </el-dialog>

    <!-- 健康检查 -->
    <el-dialog v-model="healthVisible" title="插件健康检查" width="480px" data-test="plugin-health-dialog">
      <el-descriptions v-if="health" :column="1" border data-test="plugin-health-desc">
        <el-descriptions-item label="插件">{{ health.name || health.plugin_id }}</el-descriptions-item>
        <el-descriptions-item label="健康">
          <el-tag :type="health.is_healthy ? 'success' : 'danger'" size="small">
            {{ health.is_healthy ? '正常' : '异常' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">{{ health.status }}</el-descriptions-item>
        <el-descriptions-item label="调用次数">{{ health.total_calls }}（成功 {{ health.success_calls }} / 失败 {{ health.failed_calls }}）</el-descriptions-item>
        <el-descriptions-item label="平均延迟">{{ health.avg_latency_ms }} ms</el-descriptions-item>
        <el-descriptions-item label="工具数">{{ health.tools_count }}</el-descriptions-item>
        <el-descriptions-item v-if="health.error" label="错误">{{ health.error }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  pluginsApi,
  type LlmAvailableTool,
  type LlmPlugin,
  type LlmPluginHealth,
} from '@/core/api/governance'

const plugins = ref<LlmPlugin[]>([])
const tools = ref<LlmAvailableTool[]>([])
const loading = ref(false)
const toolsLoading = ref(false)
const submitting = ref(false)
const togglingId = ref('')
const errorMessage = ref('')
const typeFilter = ref('')
const statusFilter = ref('')

const registerVisible = ref(false)
const form = reactive({ name: '', version: '1.0.0', entry_point: '', description: '' })

const healthVisible = ref(false)
const health = ref<LlmPluginHealth | null>(null)

const TYPE_LABELS: Record<string, string> = { builtin: '内置', external: '外部' }

function typeLabel(value: string): string {
  return TYPE_LABELS[value] ?? value
}

function toolCount(plugin: LlmPlugin): number {
  const defs = (plugin.metadata_?.tools ?? []) as unknown[]
  return Array.isArray(defs) ? defs.length : 0
}

/**
 * XR-LLM-08（口径说明，不改后端）：`/plugins/tools` 合并「运行时注册表」与
 * 「DB 插件元数据」两种来源。凡 plugin_id / plugin_name 不在当前插件列表中者，
 * 即运行时注册表内建工具 → 标注「运行期内建」。
 */
const dbPluginIds = computed(() => new Set(plugins.value.map((item) => String(item.id))))
const dbPluginNames = computed(() => new Set(plugins.value.map((item) => item.name)))

function isRuntimeTool(tool: LlmAvailableTool): boolean {
  return (
    !dbPluginIds.value.has(String(tool.plugin_id))
    && !dbPluginNames.value.has(tool.plugin_name)
  )
}

function messageOf(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  return fallback
}

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const page = await pluginsApi.list({
      plugin_type: typeFilter.value || undefined,
      status: statusFilter.value || undefined,
      limit: 200,
    })
    plugins.value = page.items
  } catch (error) {
    errorMessage.value = `插件列表加载失败：${messageOf(error, '未知错误')}`
  } finally {
    loading.value = false
  }
}

async function loadTools(): Promise<void> {
  toolsLoading.value = true
  try {
    tools.value = await pluginsApi.listTools()
  } catch (error) {
    errorMessage.value = `工具列表加载失败：${messageOf(error, '未知错误')}`
  } finally {
    toolsLoading.value = false
  }
}

async function toggle(plugin: LlmPlugin, enabled: boolean): Promise<void> {
  togglingId.value = plugin.id
  try {
    const updated = await pluginsApi.setEnabled(plugin.id, enabled)
    plugin.status = updated.status
    ElMessage.success(`插件「${plugin.name}」已${enabled ? '启用' : '禁用'}`)
    await loadTools()
  } catch (error) {
    errorMessage.value = `状态切换失败：${messageOf(error, '未知错误')}`
  } finally {
    togglingId.value = ''
  }
}

function openRegister(): void {
  form.name = ''
  form.version = '1.0.0'
  form.entry_point = ''
  form.description = ''
  registerVisible.value = true
}

async function submitRegister(): Promise<void> {
  if (!form.name.trim()) {
    ElMessage.warning('请输入插件名称')
    return
  }
  submitting.value = true
  try {
    await pluginsApi.register({
      name: form.name.trim(),
      version: form.version.trim() || '1.0.0',
      entry_point: form.entry_point.trim(),
      description: form.description.trim(),
    })
    ElMessage.success('插件已注册')
    registerVisible.value = false
    await load()
    await loadTools()
  } catch (error) {
    errorMessage.value = `注册失败：${messageOf(error, '未知错误')}`
  } finally {
    submitting.value = false
  }
}

async function remove(plugin: LlmPlugin): Promise<void> {
  try {
    await pluginsApi.remove(plugin.id)
    plugins.value = plugins.value.filter((item) => item.id !== plugin.id)
    ElMessage.success('插件已删除')
    await loadTools()
  } catch (error) {
    errorMessage.value = `删除失败：${messageOf(error, '未知错误')}`
  }
}

async function checkHealth(plugin: LlmPlugin): Promise<void> {
  try {
    health.value = await pluginsApi.health(plugin.id)
    healthVisible.value = true
  } catch (error) {
    errorMessage.value = `健康检查失败：${messageOf(error, '未知错误')}`
  }
}

watch([typeFilter, statusFilter], () => {
  void load()
})

onMounted(() => {
  void load()
  void loadTools()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-16 { margin-top: 16px; }
.plugin-name { font-weight: 500; }
.plugin-code { color: var(--ob-text-secondary); font-size: 12px; }
.tool-hint { margin-bottom: 12px; color: var(--ob-text-secondary); font-size: 12px; }
</style>
