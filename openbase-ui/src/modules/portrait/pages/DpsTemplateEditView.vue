<template>
  <div class="dps-template-edit">
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
        <el-option v-for="item in extendsOptions" :key="item.code" :label="`${item.code}（${item.status || 'draft'}）`" :value="item.code" />
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
      <el-button data-test="edit-cancel" @click="router.push('/dps/templates')">取消</el-button>
      <span class="muted sm">保存中按钮置灰（表单提交态）</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dpsApi, type DpsPortraitTemplate } from '@/core/api/dps'
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
})

const jsonBlocks = reactive<Record<string, string>>({
  dimension_config: '{}',
  attributes_schema: '{}',
  tag_bindings: '[]',
  evidence_policy: '{}',
  anomaly_rules: '{}',
})

const templates = ref<DpsPortraitTemplate[]>([])
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
  const list = await dpsApi.listTemplates().catch(() => ({ items: [] as DpsPortraitTemplate[] }))
  templates.value = list.items || []
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
    jsonBlocks.dimension_config = JSON.stringify(template.dimension_config ?? {}, null, 2)
    jsonBlocks.attributes_schema = JSON.stringify(template.attributes_schema ?? {}, null, 2)
    jsonBlocks.tag_bindings = JSON.stringify(template.tag_bindings ?? [], null, 2)
    jsonBlocks.evidence_policy = JSON.stringify(template.evidence_policy ?? {}, null, 2)
    jsonBlocks.anomaly_rules = JSON.stringify(template.anomaly_rules ?? {}, null, 2)
  } catch (caught) {
    error.value = describeDpsError(caught)
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
      await router.push('/dps/templates')
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
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.mb-16 { margin-bottom: 16px; }
.mt-12 { margin-top: 12px; }
.muted { color: var(--ob-text-secondary); }
.sm { font-size: 12px; margin-left: 6px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
</style>
