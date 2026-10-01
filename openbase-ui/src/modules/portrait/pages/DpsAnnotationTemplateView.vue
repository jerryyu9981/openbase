<template>
  <div class="dps-annotation-templates">
    <div class="page-toolbar">
      <el-input v-model="templateCodeFilter" placeholder="按 template_code 过滤" clearable style="width: 220px" data-test="annotation-template-filter" />
      <el-select v-model="scenarioFilter" placeholder="scenario：全部" clearable style="width: 170px" data-test="annotation-scenario-filter">
        <el-option v-for="item in SCENARIOS" :key="item" :label="item" :value="item" />
      </el-select>
      <el-button type="primary" data-test="annotation-query" @click="load">查询</el-button>
      <el-button data-test="annotation-reset" @click="resetFilters">重置</el-button>
      <el-button type="primary" plain data-test="annotation-new" @click="openCreate">新建标注模板</el-button>
    </div>

    <!-- 删除被拒（409 且显示关联条数） -->
    <el-alert v-if="deleteRejected" type="error" show-icon :closable="true" class="mb-16" data-test="annotation-delete-rejected" @close="deleteRejected = ''">
      <template #title>删除被拒（409）</template>
      <div>{{ deleteRejected }}</div>
    </el-alert>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <el-button v-if="error.retryable" link type="primary" size="small" data-test="dps-retry" @click="load">点击重试</el-button>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card header="标注模板">
      <div class="ob-table-scroll">
        <el-table v-loading="loading" :data="items" stripe empty-text="暂无标注模板" data-test="annotation-table">
          <el-table-column prop="code" label="标注模板" min-width="180" />
          <el-table-column label="归属画像模板" min-width="170">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="annotation-owner" @click="router.push(`/dps/templates/${row.template_code}/edit`)">
                {{ row.template_code || '-' }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column prop="scenario" label="scenario" width="120" />
          <el-table-column label="字段数" width="90">
            <template #default="{ row }">{{ (row.field_schema || []).length }}</template>
          </el-table-column>
          <el-table-column label="版本" width="80">
            <template #default="{ row }">v{{ row.version ?? 1 }}</template>
          </el-table-column>
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="annotation-detail" @click="openDetail(row.code)">详情</el-button>
              <el-button link type="primary" size="small" data-test="annotation-fields" @click="router.push(`/dps/annotation-templates/${row.code}/fields`)">字段与归属</el-button>
              <el-popconfirm title="确认删除该标注模板？" @confirm="remove(row.code)">
                <template #reference>
                  <el-button link type="danger" size="small" data-test="annotation-delete">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无标注模板" :image-size="60" data-test="annotation-empty">
              <el-button type="primary" size="small" @click="openCreate">新建标注模板</el-button>
            </el-empty>
          </template>
        </el-table>
      </div>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailOpen" title="标注模板详情" size="480px" data-test="annotation-detail-drawer">
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="code">{{ detail?.code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="name">{{ detail?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="归属（强归属）">{{ detail?.template_code || '-' }}（不可置空；改挂见「字段与归属」）</el-descriptions-item>
        <el-descriptions-item label="scenario">{{ detail?.scenario || '-' }}</el-descriptions-item>
        <el-descriptions-item label="version">v{{ detail?.version ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="status">{{ detail?.status || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>

    <!-- 新建 -->
    <el-dialog v-model="createOpen" title="新建标注模板" width="560px" data-test="annotation-create-dialog">
      <el-form label-width="130px">
        <el-form-item label="code *">
          <el-input v-model="createForm.code" data-test="annotation-create-code" />
        </el-form-item>
        <el-form-item label="name">
          <el-input v-model="createForm.name" data-test="annotation-create-name" />
        </el-form-item>
        <el-form-item label="归属画像模板 *">
          <el-select v-model="createForm.template_code" placeholder="仅可选 active 画像模板" style="width: 260px" data-test="annotation-create-owner">
            <el-option v-for="item in activeTemplates" :key="item.code" :label="item.code" :value="item.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="scenario">
          <el-select v-model="createForm.scenario" style="width: 200px" data-test="annotation-create-scenario">
            <el-option v-for="item in SCENARIOS" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="description">
          <el-input v-model="createForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="annotation-create-save" @click="create">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsAnnotationTemplate, type DpsPortraitTemplate } from '@/core/api/dps'
import { describeDpsError } from '@/core/api/error'
import { useAsyncState } from '@/core/composables/useAsyncState'

const SCENARIOS = ['intake', 'assess', 'check', 'general']

const router = useRouter()
const templateCodeFilter = ref('')
const scenarioFilter = ref('')
const detailOpen = ref(false)
const detail = ref<DpsAnnotationTemplate | null>(null)
const createOpen = ref(false)
const saving = ref(false)
const deleteRejected = ref('')
const activeTemplates = ref<DpsPortraitTemplate[]>([])
const createForm = reactive({ code: '', name: '', template_code: '', scenario: 'general', description: '' })

const { data, loading, error, run } = useAsyncState<{ items: DpsAnnotationTemplate[]; total?: number }>()
const items = computed(() => data.value?.items || [])

async function load() {
  await run(() =>
    dpsApi.listAnnotationTemplates({
      template_code: templateCodeFilter.value || undefined,
      scenario: scenarioFilter.value || undefined,
    }),
  )
}

function resetFilters() {
  templateCodeFilter.value = ''
  scenarioFilter.value = ''
  void load()
}

async function openDetail(code: string) {
  detailOpen.value = true
  detail.value = null
  try {
    detail.value = await dpsApi.getAnnotationTemplate(code)
  } catch (caught) {
    error.value = describeDpsError(caught)
  }
}

async function openCreate() {
  createOpen.value = true
  deleteRejected.value = ''
  const result = await dpsApi.listTemplates({ status: 'active' }).catch(() => ({ items: [] as DpsPortraitTemplate[] }))
  activeTemplates.value = result.items || []
}

async function create() {
  if (!createForm.code || !createForm.template_code) {
    ElMessage.warning('code 与归属画像模板必填')
    return
  }
  saving.value = true
  try {
    await dpsApi.createAnnotationTemplate({
      code: createForm.code,
      name: createForm.name,
      template_code: createForm.template_code,
      scenario: createForm.scenario,
      description: createForm.description,
    })
    ElMessage.success('标注模板已创建')
    createOpen.value = false
    await load()
  } catch (caught) {
    const presentation = describeDpsError(caught)
    createOpen.value = false
    deleteRejected.value = presentation.kind === 'conflict' ? `code 已存在：${presentation.detail}` : ''
    if (!deleteRejected.value) ElMessage.error(presentation.hint || presentation.title)
  } finally {
    saving.value = false
  }
}

async function remove(code: string) {
  deleteRejected.value = ''
  try {
    await dpsApi.deleteAnnotationTemplate(code)
    ElMessage.success('标注模板已删除')
    await load()
  } catch (caught) {
    const presentation = describeDpsError(caught)
    if (presentation.kind === 'conflict') {
      deleteRejected.value = presentation.detail || '存在关联标注数据，禁止删除'
    } else {
      ElMessage.error(presentation.hint || presentation.title)
    }
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.mb-16 { margin-bottom: 16px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
</style>
