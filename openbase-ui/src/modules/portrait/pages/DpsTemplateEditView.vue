<template>
  <PageContainer title="画像模板" description="模板字段编排与保存" test-id="dps-template-edit-view-page">
    <el-alert type="info" show-icon :closable="false" class="mb-16" data-test="edit-version-tip">
      <template #title>保存后版本自动递增（v1 → v2）并写入模板变更历史；code 创建后不可修改。</template>
    </el-alert>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mb-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <el-card header="基本信息" class="mb-16">
      <el-form label-width="150px">
        <el-form-item label="code *">
          <el-input v-model="form.code" :disabled="isEdit" placeholder="cc-persona-v1" style="width: 320px" data-test="edit-code" />
          <span class="muted sm">唯一标识；重复 → 409</span>
        </el-form-item>
        <el-form-item label="name *">
          <el-input v-model="form.name" placeholder="客服画像模板 v1" style="width: 320px" data-test="edit-name" />
        </el-form-item>
        <el-form-item label="profile_type">
          <el-select v-model="form.profile_type" style="width: 200px" data-test="edit-profile-type">
            <el-option label="persona" value="persona" />
            <el-option label="organization" value="organization" />
          </el-select>
        </el-form-item>
        <el-form-item label="subject_type">
          <el-select v-model="form.subject_type" style="width: 200px" data-test="edit-subject-type">
            <el-option label="person" value="person" />
            <el-option label="team" value="team" />
          </el-select>
        </el-form-item>
        <el-form-item label="status">
          <el-select v-model="form.status" style="width: 200px" data-test="edit-status">
            <el-option label="active" value="active" />
            <el-option label="inactive" value="inactive" />
            <el-option label="draft" value="draft" />
          </el-select>
        </el-form-item>
        <el-form-item label="description">
          <el-input v-model="form.description" type="textarea" :rows="2" style="width: 420px" data-test="edit-description" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card header="继承 extends（深度 ≤ 2 层）" class="mb-16">
      <el-select v-model="form.extends" clearable placeholder="选择父模板（可不选）" style="width: 300px" data-test="edit-extends">
        <el-option
          v-for="item in extendsOptions"
          :key="item.code"
          :label="item.name || item.code"
          :value="item.code"
        >
          <NameCodeLabel :name="item.name" :code="item.code" />
          <span class="muted sm">{{ item.status || 'draft' }}</span>
        </el-option>
      </el-select>
      <el-alert
        v-if="extendsIssue"
        type="error"
        show-icon
        :closable="false"
        class="mt-12"
        data-test="edit-extends-issue"
      >
        <template #title>{{ extendsIssue }}</template>
        <div>约束：不得指向自身、不得成环、深度上限 2 层、父模板必须存在。前端仅即时提示，最终以服务端 400 为准。</div>
      </el-alert>
      <div class="muted sm mt-12">维度解析口径：父维度先入 → 子覆盖同名 → 追加新维度。</div>
    </el-card>

    <el-card header="分类与子模板挂载（v2.12.0）" class="mb-16" data-test="edit-catalog">
      <el-form label-width="150px">
        <el-form-item label="模板分类">
          <el-select v-model="form.category_id" clearable placeholder="选择具体画像分类（L3）" style="width: 320px" data-test="edit-category">
            <el-option v-for="item in leafCategories" :key="item.id" :label="item.name" :value="item.id">
              <NameCodeLabel :name="item.name" :code="item.code" />
            </el-option>
          </el-select>
          <span class="muted sm">分类树在「模板族管理 → 分类管理」维护</span>
        </el-form-item>
        <el-form-item label="模板类型">
          <el-radio-group v-model="form.template_kind" data-test="edit-template-kind">
            <el-radio-button value="composite">复合模板</el-radio-button>
            <el-radio-button value="component">子模板</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <el-divider content-position="left">子模板挂载</el-divider>
      <template v-if="isEdit && form.template_kind === 'composite'">
        <div class="mount-toolbar">
          <el-select v-model="mountChildCode" filterable placeholder="选择子模板" style="width: 280px" data-test="mount-child">
            <el-option
              v-for="item in mountableComponents"
              :key="item.code"
              :label="item.name || item.code"
              :value="item.code"
            >
              <NameCodeLabel :name="item.name" :code="item.code" />
            </el-option>
          </el-select>
          <el-input-number v-model="mountWeight" :min="0" :max="1" :step="0.05" :precision="2" placeholder="权重" />
          <el-checkbox v-model="mountRequired">必挂</el-checkbox>
          <el-button type="primary" :disabled="!mountChildCode" data-test="mount-submit" @click="mountComponent">挂载</el-button>
        </div>
        <el-table v-loading="componentsLoading" :data="components" size="small" empty-text="尚未挂载子模板" data-test="mount-table">
          <el-table-column label="子模板" min-width="240">
            <template #default="{ row }">
              <NameCodeLabel :name="row.child_name" :code="row.child_code" layout="stack" />
            </template>
          </el-table-column>
          <el-table-column label="版本" width="90">
            <template #default="{ row }">{{ row.child_version ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="权重" width="110">
            <template #default="{ row }">{{ row.weight_override ?? '继承' }}</template>
          </el-table-column>
          <el-table-column label="必挂" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="row.required ? 'warning' : 'info'" effect="plain">{{ row.required ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row, $index }">
              <el-button link type="primary" size="small" :disabled="$index === 0" @click="moveComponent($index, -1)">上移</el-button>
              <el-button link type="primary" size="small" :disabled="$index === components.length - 1" @click="moveComponent($index, 1)">下移</el-button>
              <el-button link type="danger" size="small" data-test="mount-remove" @click="unmountComponent(row)">卸载</el-button>
            </template>
          </el-table-column>
        </el-table>
        <p class="muted sm mt-8">挂载变更会写入模板版本快照；必挂子模板需先取消必挂才能卸载。</p>
      </template>
      <el-alert
        v-else
        type="info"
        show-icon
        :closable="false"
        title="保存为复合模板后，可在此挂载子模板；子模板仅用于组合，不能再次挂载其他模板。"
      />
    </el-card>

    <el-card header="配置块（JSON 原样编辑 · 前端不解析内部结构）" class="mb-16">
      <el-form label-width="150px">
        <el-form-item label="dimension_config">
          <el-input v-model="jsonBlocks.dimension_config" type="textarea" :rows="3" data-test="edit-dimension-config" />
        </el-form-item>
        <el-form-item label="attributes_schema">
          <el-input v-model="jsonBlocks.attributes_schema" type="textarea" :rows="2" data-test="edit-attributes-schema" />
        </el-form-item>
        <el-form-item label="tag_bindings">
          <el-input v-model="jsonBlocks.tag_bindings" type="textarea" :rows="2" data-test="edit-tag-bindings" />
        </el-form-item>
        <el-form-item label="evidence_policy">
          <el-input v-model="jsonBlocks.evidence_policy" type="textarea" :rows="2" data-test="edit-evidence-policy" />
        </el-form-item>
        <el-form-item label="anomaly_rules">
          <el-input v-model="jsonBlocks.anomaly_rules" type="textarea" :rows="2" data-test="edit-anomaly-rules" />
        </el-form-item>
      </el-form>
      <div class="muted sm">维度权重须在 0~1；dimensions 不得为空数组（上游校验）。</div>
    </el-card>

    <div class="page-toolbar">
      <el-button type="primary" :loading="saving" :disabled="!!extendsIssue || !canSave" data-test="edit-save" @click="save">保存</el-button>
      <el-button data-test="edit-cancel" @click="router.push('/portrait/dps/templates')">取消</el-button>
      <span class="muted sm">保存中按钮置灰（表单提交态）</span>
    </div>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import NameCodeLabel from '@/components/common/NameCodeLabel.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsPortraitTemplate, type DpsTemplateCategory, type DpsTemplateComponent } from '@/core/api/dps'
import { describeDpsError, type DpsErrorPresentation } from '@/core/api/error'

const route = useRoute()
const router = useRouter()
const editingCode = computed(() => String(route.params.code || ''))
const isEdit = computed(() => !!editingCode.value)

const form = reactive({
  code: '',
  name: '',
  profile_type: 'persona',
  subject_type: 'person',
  status: 'active',
  description: '',
  extends: '' as string,
  category_id: '' as string,
  template_kind: 'composite' as 'composite' | 'component',
})

const jsonBlocks = reactive<Record<string, string>>({
  dimension_config: '{}',
  attributes_schema: '{}',
  tag_bindings: '[]',
  evidence_policy: '{}',
  anomaly_rules: '{}',
})

const templates = ref<DpsPortraitTemplate[]>([])
const categories = ref<DpsTemplateCategory[]>([])
const components = ref<DpsTemplateComponent[]>([])
const componentsLoading = ref(false)
const mountChildCode = ref('')
const mountWeight = ref<number | null>(null)
const mountRequired = ref(true)
const saving = ref(false)
const error = ref<DpsErrorPresentation | null>(null)

const templateMap = computed<Record<string, DpsPortraitTemplate>>(() => {
  const map: Record<string, DpsPortraitTemplate> = {}
  templates.value.forEach((item) => {
    map[item.code] = item
  })
  return map
})
const extendsOptions = computed(() => templates.value.filter((item) => item.code !== form.code))
const leafCategories = computed(() => categories.value.filter((item) => Number(item.level) === 3))
const mountedCodes = computed(() => new Set(components.value.map((item) => item.child_code)))
const mountableComponents = computed(() =>
  templates.value.filter(
    (item) =>
      item.template_kind === 'component' &&
      item.code !== form.code &&
      !mountedCodes.value.has(item.code),
  ),
)
const canSave = computed(() => !!form.code && !!form.name)

/** 继承链深度（>2 或成环 → 返回 99 作为非法哨兵） */
function chainDepth(startCode: string): number {
  let depth = 0
  let cursor: string | undefined = startCode
  const seen = new Set<string>()
  while (cursor) {
    if (seen.has(cursor)) return 99
    seen.add(cursor)
    const parent: DpsPortraitTemplate | undefined = templateMap.value[cursor]
    if (!parent || !parent.extends) break
    cursor = parent.extends
    depth += 1
  }
  return depth
}

const extendsIssue = computed(() => {
  if (!form.extends) return ''
  if (form.extends === form.code) return 'extends 不得指向自身'
  const parent: DpsPortraitTemplate | undefined = templateMap.value[form.extends]
  if (!parent) return 'extends 指定的父模板不存在'
  // 自身(1) + 父链深度
  if (1 + chainDepth(form.extends) > 2) return 'extends 继承深度超过 2 层'
  return ''
})

function parseBlock(raw: string, label: string): unknown {
  try {
    return raw.trim() ? JSON.parse(raw) : null
  } catch {
    throw new Error(`${label} 不是合法 JSON`)
  }
}

async function load() {
  const [list, categoryList] = await Promise.all([
    dpsApi.listTemplates().catch(() => ({ items: [] as DpsPortraitTemplate[] })),
    dpsApi.listTemplateCategories().catch(() => [] as DpsTemplateCategory[]),
  ])
  templates.value = list.items || []
  categories.value = categoryList
  if (!isEdit.value) return
  try {
    const template = await dpsApi.getTemplate(editingCode.value)
    form.code = template.code
    form.name = String(template.name || '')
    form.profile_type = String(template.profile_type || 'persona')
    form.subject_type = String(template.subject_type || 'person')
    form.status = String(template.status || 'active')
    form.description = String(template.description || '')
    form.extends = template.extends ? String(template.extends) : ''
    form.category_id = template.category_id ? String(template.category_id) : ''
    form.template_kind = template.template_kind === 'component' ? 'component' : 'composite'
    jsonBlocks.dimension_config = JSON.stringify(template.dimension_config ?? {}, null, 2)
    jsonBlocks.attributes_schema = JSON.stringify(template.attributes_schema ?? {}, null, 2)
    jsonBlocks.tag_bindings = JSON.stringify(template.tag_bindings ?? [], null, 2)
    jsonBlocks.evidence_policy = JSON.stringify(template.evidence_policy ?? {}, null, 2)
    jsonBlocks.anomaly_rules = JSON.stringify(template.anomaly_rules ?? {}, null, 2)
    await loadComponents()
  } catch (caught) {
    error.value = describeDpsError(caught)
  }
}

async function loadComponents() {
  if (!isEdit.value || form.template_kind !== 'composite') {
    components.value = []
    return
  }
  componentsLoading.value = true
  try {
    components.value = await dpsApi.listTemplateComponents(editingCode.value)
  } catch (caught) {
    const presentation = describeDpsError(caught)
    ElMessage.error(presentation.hint || presentation.title)
  } finally {
    componentsLoading.value = false
  }
}

async function mountComponent() {
  if (!mountChildCode.value) return
  try {
    const result = await dpsApi.mountTemplateComponent(editingCode.value, {
      child_code: mountChildCode.value,
      required: mountRequired.value,
      weight_override: mountWeight.value,
    })
    components.value = result.components
    mountChildCode.value = ''
    mountWeight.value = null
    ElMessage.success('子模板已挂载')
  } catch (caught) {
    const presentation = describeDpsError(caught)
    ElMessage.error(presentation.hint || presentation.title)
  }
}

async function unmountComponent(row: DpsTemplateComponent) {
  try {
    components.value = await dpsApi.unmountTemplateComponent(editingCode.value, row.child_code)
    ElMessage.success('子模板已卸载')
  } catch (caught) {
    const presentation = describeDpsError(caught)
    ElMessage.error(presentation.hint || presentation.title)
  }
}

async function moveComponent(index: number, offset: number) {
  const target = index + offset
  if (target < 0 || target >= components.value.length) return
  const ordered = [...components.value]
  const [moved] = ordered.splice(index, 1)
  ordered.splice(target, 0, moved)
  components.value = ordered
  try {
    components.value = await dpsApi.reorderTemplateComponents(
      editingCode.value,
      ordered.map((item) => item.child_code),
    )
  } catch (caught) {
    const presentation = describeDpsError(caught)
    ElMessage.error(presentation.hint || presentation.title)
    await loadComponents()
  }
}

async function save() {
  error.value = null
  let payload: Record<string, unknown>
  try {
    payload = {
      code: form.code,
      name: form.name,
      profile_type: form.profile_type,
      subject_type: form.subject_type,
      status: form.status,
      description: form.description,
      extends: form.extends || null,
      dimension_config: parseBlock(jsonBlocks.dimension_config, 'dimension_config'),
      attributes_schema: parseBlock(jsonBlocks.attributes_schema, 'attributes_schema'),
      tag_bindings: parseBlock(jsonBlocks.tag_bindings, 'tag_bindings'),
      evidence_policy: parseBlock(jsonBlocks.evidence_policy, 'evidence_policy'),
      anomaly_rules: parseBlock(jsonBlocks.anomaly_rules, 'anomaly_rules'),
      category_id: form.category_id || null,
      template_kind: form.template_kind,
    }
  } catch (parseError) {
    ElMessage.warning((parseError as Error).message)
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      const updated = await dpsApi.updateTemplate(editingCode.value, payload)
      ElMessage.success(`已保存，版本递增至 v${updated.version ?? '-'}`)
    } else {
      const created = await dpsApi.createTemplate(payload as Partial<DpsPortraitTemplate> & { code: string })
      ElMessage.success(`创建成功（v${created.version ?? 1}）`)
      await router.push('/portrait/dps/templates')
    }
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.mount-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.mb-16 { margin-bottom: 16px; }
.mt-12 { margin-top: 12px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; margin-left: 6px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
</style>
