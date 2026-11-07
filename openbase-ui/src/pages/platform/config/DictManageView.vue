<template>
  <PageContainer
    title="数据字典"
    description="字典类型与字典项集中管理（数据源：OpenBase /api/v1/dicts）"
    test-id="dict-manage-page"
  >
    <div class="page-toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索类型编码 / 名称"
        clearable
        style="width: 240px"
        data-test="dict-search"
      />
      <el-button :loading="loadingTypes" data-test="dict-reload" @click="loadTypes">刷新</el-button>
      <el-button type="primary" data-test="dict-create-type" @click="openCreateType">新建类型</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="dict-error"
      @close="errorMessage = ''"
    />

    <div class="dict-layout">
      <el-card class="dict-types" data-test="dict-type-card">
        <template #header>字典类型（{{ filteredTypes.length }}）</template>
        <el-table
          v-loading="loadingTypes"
          :data="filteredTypes"
          row-key="code"
          highlight-current-row
          :current-row-key="selectedCode"
          empty-text="暂无字典类型"
          data-test="dict-type-table"
          @row-click="onTypeClick"
        >
          <el-table-column prop="code" label="类型编码" min-width="140">
            <template #default="{ row }">
              <code>{{ row.code }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button
                link
                type="danger"
                size="small"
                data-test="dict-type-delete"
                @click.stop="removeType(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="dict-items" data-test="dict-item-card">
        <template #header>
          <div class="card-header">
            <span>{{ selectedCode ? `字典项：${selectedCode}` : '字典项' }}</span>
            <el-button
              type="primary"
              size="small"
              :disabled="!selectedCode"
              data-test="dict-create-item"
              @click="openCreateItem"
            >
              新建字典项
            </el-button>
          </div>
        </template>
        <el-table
          v-loading="loadingItems"
          :data="items"
          row-key="id"
          empty-text="请选择左侧字典类型，或该类型暂无字典项"
          data-test="dict-item-table"
        >
          <el-table-column prop="label" label="显示名" min-width="140" />
          <el-table-column prop="value" label="值" min-width="140">
            <template #default="{ row }">
              <code>{{ row.value }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button
                link
                type="danger"
                size="small"
                data-test="dict-item-delete"
                @click="removeItem(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-dialog v-model="typeDialogOpen" title="新建字典类型" width="460px" data-test="dict-type-dialog">
      <el-form :model="typeForm" label-width="80px">
        <el-form-item label="类型编码">
          <el-input v-model="typeForm.code" placeholder="如 order_status" data-test="dict-type-code" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="typeForm.name" placeholder="如 订单状态" data-test="dict-type-name" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="typeDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="dict-type-save" @click="submitCreateType">
          创建
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="itemDialogOpen" title="新建字典项" width="460px" data-test="dict-item-dialog">
      <el-form :model="itemForm" label-width="80px">
        <el-form-item label="显示名">
          <el-input v-model="itemForm.label" placeholder="如 已支付" data-test="dict-item-label" />
        </el-form-item>
        <el-form-item label="值">
          <el-input v-model="itemForm.value" placeholder="如 paid" data-test="dict-item-value" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="itemForm.sort_order" :min="0" :step="1" data-test="dict-item-sort" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="dict-item-save" @click="submitCreateItem">
          创建
        </el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dictsApi, type DictItem, type DictType } from '@/core/api/dicts'

const types = ref<DictType[]>([])
const items = ref<DictItem[]>([])
const keyword = ref('')
const selectedCode = ref('')
const loadingTypes = ref(false)
const loadingItems = ref(false)
const saving = ref(false)
const errorMessage = ref('')

const typeDialogOpen = ref(false)
const typeForm = ref<{ code: string; name: string }>({ code: '', name: '' })

const itemDialogOpen = ref(false)
const itemForm = ref<{ label: string; value: string; sort_order: number }>({
  label: '',
  value: '',
  sort_order: 0,
})

const filteredTypes = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return types.value
  return types.value.filter(
    (item) => item.code.toLowerCase().includes(kw) || item.name.toLowerCase().includes(kw),
  )
})

function messageOf(error: unknown, fallback: string): string {
  const payload = (error as { response?: { data?: { message?: string } } }).response?.data
  if (payload?.message) return payload.message
  if (error instanceof Error && error.message) return error.message
  return fallback
}

async function loadTypes(): Promise<void> {
  loadingTypes.value = true
  errorMessage.value = ''
  try {
    types.value = await dictsApi.listTypes()
    const stillExists = types.value.some((item) => item.code === selectedCode.value)
    if (!stillExists) {
      selectedCode.value = types.value[0]?.code ?? ''
    }
    await loadItems()
  } catch (error) {
    errorMessage.value = `字典类型加载失败：${messageOf(error, '未知错误')}`
  } finally {
    loadingTypes.value = false
  }
}

async function loadItems(): Promise<void> {
  if (!selectedCode.value) {
    items.value = []
    return
  }
  loadingItems.value = true
  try {
    items.value = await dictsApi.listItems(selectedCode.value)
  } catch (error) {
    items.value = []
    errorMessage.value = `字典项加载失败：${messageOf(error, '未知错误')}`
  } finally {
    loadingItems.value = false
  }
}

async function onTypeClick(row: DictType): Promise<void> {
  if (row.code === selectedCode.value) return
  selectedCode.value = row.code
  await loadItems()
}

function openCreateType(): void {
  typeForm.value = { code: '', name: '' }
  typeDialogOpen.value = true
}

async function submitCreateType(): Promise<void> {
  const code = typeForm.value.code.trim()
  const name = typeForm.value.name.trim()
  if (!code || !name) {
    ElMessage.warning('类型编码与名称均不能为空')
    return
  }
  saving.value = true
  try {
    await dictsApi.createType({ code, name })
    ElMessage.success(`字典类型 ${code} 已创建`)
    typeDialogOpen.value = false
    selectedCode.value = code
    await loadTypes()
  } catch (error) {
    errorMessage.value = `创建字典类型失败：${messageOf(error, '未知错误')}`
  } finally {
    saving.value = false
  }
}

function openCreateItem(): void {
  itemForm.value = { label: '', value: '', sort_order: 0 }
  itemDialogOpen.value = true
}

async function submitCreateItem(): Promise<void> {
  const label = itemForm.value.label.trim()
  const value = itemForm.value.value.trim()
  if (!label || !value) {
    ElMessage.warning('显示名与值均不能为空')
    return
  }
  saving.value = true
  try {
    await dictsApi.createItem(selectedCode.value, {
      label,
      value,
      sort_order: itemForm.value.sort_order,
    })
    ElMessage.success('字典项已创建')
    itemDialogOpen.value = false
    await loadItems()
  } catch (error) {
    errorMessage.value = `创建字典项失败：${messageOf(error, '未知错误')}`
  } finally {
    saving.value = false
  }
}

async function removeType(row: DictType): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认删除字典类型 ${row.code}？若其下仍有字典项将被拒绝（需先删除全部字典项）。`,
      '删除字典类型',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await dictsApi.removeType(row.code)
    ElMessage.success(`字典类型 ${row.code} 已删除`)
    if (selectedCode.value === row.code) selectedCode.value = ''
    await loadTypes()
  } catch (error) {
    errorMessage.value = `删除字典类型失败：${messageOf(error, '未知错误')}`
  }
}

async function removeItem(row: DictItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认删除字典项 ${row.label}（${row.value}）？`,
      '删除字典项',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await dictsApi.removeItem(row.id)
    ElMessage.success(`字典项 ${row.label} 已删除`)
    await loadItems()
  } catch (error) {
    errorMessage.value = `删除字典项失败：${messageOf(error, '未知错误')}`
  }
}

onMounted(loadTypes)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.dict-layout { display: grid; grid-template-columns: minmax(320px, 1fr) minmax(360px, 1.4fr); gap: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
@media (max-width: 960px) {
  .dict-layout { grid-template-columns: 1fr; }
}
</style>
