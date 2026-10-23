<template>
  <PageContainer title="全局配置" description="平台级配置项集中管理（数据源：OpenBase /api/v1/configs）" test-id="config-manage-view-page">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索配置键 / 分组" clearable style="width: 240px" data-test="cfg-search" />
      <el-input v-model="levelFilter" placeholder="级别（system/tenant/user）" clearable style="width: 180px" data-test="cfg-level-filter" />
      <el-button type="primary" :loading="loading" data-test="cfg-reload" @click="load">刷新</el-button>
      <el-button data-test="cfg-export" :disabled="!items.length" @click="exportJson">导出 JSON</el-button>
      <el-upload :auto-upload="false" :show-file-list="false" accept=".json" data-test="cfg-import" @change="onImport">
        <el-button>导入</el-button>
      </el-upload>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="cfg-error"
      @close="errorMessage = ''"
    />

    <el-card header="配置项（三级合并：USER > TENANT > SYSTEM）" data-test="cfg-card">
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="filteredItems" stripe empty-text="暂无配置项" data-test="cfg-table">
          <el-table-column label="分组" width="130">
            <template #default="{ row }">{{ groupOf(row.key) }}</template>
          </el-table-column>
          <el-table-column prop="key" label="配置键" min-width="240">
            <template #default="{ row }">
              <code>{{ row.key }}</code>
            </template>
          </el-table-column>
          <el-table-column label="值" min-width="200">
            <template #default="{ row }">
              <span class="value-text">{{ formatValue(row.value) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="level" label="级别" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="levelType(row.level)">{{ String(row.level).toUpperCase() }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="cfg-edit" @click="openEdit(row)">编辑</el-button>
              <el-button link type="primary" size="small" data-test="cfg-versions" @click="openVersions(row)">版本</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="dialogOpen" title="编辑配置项" width="520px" data-test="cfg-dialog">
      <el-form :model="form" label-width="80px">
        <el-form-item label="配置键">
          <code>{{ form.key }}</code>
        </el-form-item>
        <el-form-item label="值">
          <el-input v-model="form.value" type="textarea" :rows="3" data-test="cfg-value" />
          <div class="text-muted">对象/数组请填 JSON，字符串直接填写</div>
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="form.level" style="width: 100%" data-test="cfg-level">
            <el-option label="SYSTEM" value="system" />
            <el-option label="TENANT" value="tenant" />
            <el-option label="USER" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="cfg-save" @click="save">保存（即时生效）</el-button>
      </template>
    </el-dialog>

    <!-- 版本历史 -->
    <el-drawer v-model="versionsOpen" :title="`版本历史：${versionsKey}`" size="420px" data-test="cfg-versions-drawer">
      <div v-loading="versionsLoading">
        <el-empty v-if="!versions.length" description="暂无版本记录" :image-size="60" data-test="cfg-versions-empty" />
        <div v-for="version in versions" :key="version.version" class="version-row" data-test="cfg-version-row">
          <span>v{{ version.version }} · {{ formatValue(version.value) }}</span>
          <el-button link type="primary" size="small" data-test="cfg-rollback" @click="rollback(version.version)">
            回滚
          </el-button>
        </div>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { configsApi, type ConfigItem, type ConfigLevel, type ConfigVersion } from '@/core/api/configs'

const items = ref<ConfigItem[]>([])
const keyword = ref('')
const levelFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')

const dialogOpen = ref(false)
const form = ref<{ key: string; value: string; level: ConfigLevel }>({ key: '', value: '', level: 'system' })

const versionsOpen = ref(false)
const versionsLoading = ref(false)
const versionsKey = ref('')
const versions = ref<ConfigVersion[]>([])

const filteredItems = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const level = levelFilter.value.trim().toLowerCase()
  return items.value.filter((item) => {
    const matchKeyword = !kw || item.key.toLowerCase().includes(kw) || groupOf(item.key).toLowerCase().includes(kw)
    const matchLevel = !level || String(item.level).toLowerCase() === level
    return matchKeyword && matchLevel
  })
})

function groupOf(key: string): string {
  return key.includes('.') ? key.split('.')[0] : '（未分组）'
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function parseValue(raw: string): unknown {
  const text = raw.trim()
  if (!text) return ''
  if (text.startsWith('{') || text.startsWith('[')) {
    try {
      return JSON.parse(text)
    } catch {
      return raw
    }
  }
  if (text === 'true') return true
  if (text === 'false') return false
  if (/^-?\d+(\.\d+)?$/.test(text)) return Number(text)
  return raw
}

function levelType(level: string): 'info' | 'warning' | 'success' {
  return ({ system: 'info', tenant: 'warning', user: 'success' } as const)[level as 'system'] ?? 'info'
}

function messageOf(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  return fallback
}

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await configsApi.list()
    items.value = result.items
  } catch (error) {
    errorMessage.value = `配置加载失败：${messageOf(error, '未知错误')}`
  } finally {
    loading.value = false
  }
}

function openEdit(row: ConfigItem): void {
  form.value = { key: row.key, value: formatValue(row.value), level: row.level }
  dialogOpen.value = true
}

async function save(): Promise<void> {
  saving.value = true
  try {
    await configsApi.set(form.value.key, parseValue(form.value.value), form.value.level)
    ElMessage.success(`配置 ${form.value.key} 已保存并即时生效`)
    dialogOpen.value = false
    await load()
  } catch (error) {
    errorMessage.value = `保存失败：${messageOf(error, '未知错误')}`
  } finally {
    saving.value = false
  }
}

async function openVersions(row: ConfigItem): Promise<void> {
  versionsKey.value = row.key
  versions.value = []
  versionsOpen.value = true
  versionsLoading.value = true
  try {
    versions.value = await configsApi.versions(row.key)
  } catch (error) {
    errorMessage.value = `版本历史加载失败：${messageOf(error, '未知错误')}`
  } finally {
    versionsLoading.value = false
  }
}

async function rollback(version: number): Promise<void> {
  try {
    await configsApi.rollback(versionsKey.value, version)
    ElMessage.success(`已回滚 ${versionsKey.value} 到 v${version}`)
    versionsOpen.value = false
    await load()
  } catch (error) {
    errorMessage.value = `回滚失败：${messageOf(error, '未知错误')}`
  }
}

function exportJson(): void {
  const payload = items.value.map((item) => ({ key: item.key, value: item.value, level: item.level }))
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'openbase-configs.json'
  anchor.click()
  URL.revokeObjectURL(url)
  ElMessage.success('配置已导出')
}

async function onImport(file: { raw?: File }): Promise<void> {
  const raw = file.raw
  if (!raw) return
  const text = await raw.text()
  let parsed: Array<{ key?: string; value?: unknown; level?: string }>
  try {
    const data = JSON.parse(text)
    if (!Array.isArray(data)) throw new Error('not array')
    parsed = data
  } catch {
    errorMessage.value = '导入文件格式不正确：需为 [{key, value, level}] 数组'
    return
  }
  const valid = parsed.filter((item) => typeof item.key === 'string' && item.key.trim())
  if (!valid.length) {
    errorMessage.value = '导入文件中没有有效的配置项（缺少 key）'
    return
  }
  let ok = 0
  for (const item of valid) {
    try {
      await configsApi.set(String(item.key), item.value, (item.level as ConfigLevel) || 'system')
      ok += 1
    } catch {
      // 单条失败不中断，最后统一汇报
    }
  }
  ElMessage.success(`已导入 ${ok}/${valid.length} 条配置`)
  await load()
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.version-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--ob-border-color, #eee); }
.value-text { word-break: break-all; }
.text-muted { color: var(--ob-text-secondary); font-size: 12px; }
</style>
