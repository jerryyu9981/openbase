<template>
  <div class="config-page">
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索配置项" clearable style="width: 220px" data-test="cfg-search" />
      <el-button type="primary" :loading="loading" data-test="cfg-reload" @click="load">刷新</el-button>
      <el-button data-test="cfg-export" @click="exportJson">导出 JSON</el-button>
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
        <el-table :data="filteredItems" stripe empty-text="暂无配置项" data-test="cfg-table">
          <el-table-column prop="group" label="分组" width="120" />
          <el-table-column prop="key" label="配置键" min-width="200">
            <template #default="{ row }">
              <code>{{ row.key }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="值" min-width="160" />
          <el-table-column prop="level" label="级别" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="levelType(row.level)">{{ row.level.toUpperCase() }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="version" label="版本" width="70" />
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="cfg-edit" @click="openEdit(row)">编辑</el-button>
              <el-button link type="primary" size="small" data-test="cfg-hot-reload" @click="hotReload(row)">热加载</el-button>
              <el-popover trigger="click" placement="bottom" width="280">
                <template #reference>
                  <el-button link type="info" size="small">版本</el-button>
                </template>
                <div class="version-list">
                  <div v-for="v in row.history" :key="v" class="version-row">
                    <span>v{{ v }}</span>
                    <el-button link type="primary" size="small" @click="rollback(row, v)">回滚</el-button>
                  </div>
                </div>
              </el-popover>
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
          <el-input v-model="form.value" data-test="cfg-value" />
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="form.level" style="width: 100%">
            <el-option label="SYSTEM" value="system" />
            <el-option label="TENANT" value="tenant" />
            <el-option label="USER" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" data-test="cfg-save" @click="save">保存并热加载</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ConfigItem {
  group: string
  key: string
  value: string
  level: 'system' | 'tenant' | 'user'
  version: number
  history: number[]
}

const mockConfigs: ConfigItem[] = [
  { group: 'gateway', key: 'gateway.discovery.enabled', value: 'true', level: 'system', version: 2, history: [1, 2] },
  { group: 'gateway', key: 'gateway.discovery.interval', value: '10', level: 'system', version: 1, history: [1] },
  { group: 'gateway', key: 'gateway.discovery.health_path', value: '/health', level: 'system', version: 1, history: [1] },
  { group: 'proxy', key: 'proxy.openllm.instances', value: '[{"host":"127.0.0.1","port":8001}]', level: 'system', version: 3, history: [1, 2, 3] },
  { group: 'system', key: 'system.default_locale', value: 'zh-CN', level: 'system', version: 1, history: [1] },
  { group: 'tenant', key: 'tenant.default_quota', value: '1000000', level: 'tenant', version: 2, history: [1, 2] },
]

const items = ref<ConfigItem[]>([])
const keyword = ref('')
const loading = ref(false)
const errorMessage = ref('')
const dialogOpen = ref(false)
const form = ref({ key: '', value: '', level: 'system' as 'system' | 'tenant' | 'user' })

const filteredItems = computed(() =>
  keyword.value ? items.value.filter((i) => i.key.includes(keyword.value) || i.group.includes(keyword.value)) : items.value,
)

function load() {
  loading.value = true
  setTimeout(() => {
    items.value = mockConfigs.map((c) => ({ ...c, history: [...c.history] }))
    loading.value = false
  }, 300)
}

function levelType(level: string) {
  return { system: 'info', tenant: 'warning', user: 'success' }[level] as 'info' | 'warning' | 'success'
}

function openEdit(row: ConfigItem) {
  form.value = { key: row.key, value: row.value, level: row.level }
  dialogOpen.value = true
}

function save() {
  const item = items.value.find((i) => i.key === form.value.key)
  if (item) {
    item.value = form.value.value
    item.level = form.value.level
    item.version += 1
    item.history.unshift(item.version)
    ElMessage.success(`配置 ${item.key} 已保存并热加载（无需重启）`)
  }
  dialogOpen.value = false
}

function hotReload(row: ConfigItem) {
  ElMessage.success(`配置 ${row.key} 已热加载生效`)
}

function rollback(row: ConfigItem, version: number) {
  row.version = version
  ElMessage.success(`已回滚到 v${version} 并热加载`)
}

function exportJson() {
  const blob = new Blob([JSON.stringify(items.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'openbase-configs.json'
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('配置已导出')
}

function onImport(file: { raw?: File }) {
  const raw = file.raw
  if (!raw) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      const parsed = JSON.parse(String(reader.result || '[]')) as ConfigItem[]
      if (Array.isArray(parsed)) {
        items.value = parsed
        ElMessage.success(`已导入 ${parsed.length} 条配置`)
      }
    } catch {
      ElMessage.error('导入文件格式不正确')
    }
  }
  reader.readAsText(raw)
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.version-row { display: flex; justify-content: space-between; padding: 4px 0; }
</style>
