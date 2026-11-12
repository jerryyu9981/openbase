<template>
  <PageContainer title="画像详情" description="单主体画像与标签明细" test-id="portrait-detail-page">
    <el-page-header content="画像详情" class="mb-16" @back="$router.push('/portrait')" />

    <el-result
      v-if="isForbidden"
      icon="error"
      :title="presentation?.title || ''"
      :sub-title="presentation?.detail || ''"
      data-test="isolation-forbidden"
    >
      <template #extra>
        <p v-if="presentation?.requestId" class="request-id" data-test="error-request-id">
          请求编号：{{ presentation.requestId }}
        </p>
        <el-button data-test="isolation-back" @click="$router.push('/portrait/list')">返回列表</el-button>
      </template>
    </el-result>

    <div v-else-if="isNotFound" data-test="isolation-not-found">
      <el-empty description="资源不存在或已被移除">
        <el-button data-test="isolation-back" @click="$router.push('/portrait/list')">返回列表</el-button>
      </el-empty>
    </div>

    <template v-else>
      <el-alert
        v-if="showErrorBar"
        :title="errorMessage"
        type="error"
        show-icon
        closable
        class="mb-16"
        data-test="isolation-error-bar"
        @close="presentation = null"
      >
        <template #default>
          <el-button link type="primary" size="small" data-test="isolation-retry" @click="loadData">点击重试</el-button>
        </template>
      </el-alert>
      <div v-loading="loading">
        <el-row :gutter="16">
          <el-col :xs="24" :lg="12">
            <el-card class="mb-16">
              <template #header>
                <div class="card-head">
                  <span>基本信息</span>
                  <div v-if="profile && !loading" class="card-actions">
                    <el-button link type="primary" data-test="portrait-edit-open" @click="openEdit">编辑属性</el-button>
                    <el-button link type="danger" data-test="portrait-delete-open" @click="removePortrait">删除画像</el-button>
                  </div>
                </div>
              </template>
              <el-descriptions v-if="profile" :column="1" border>
                <el-descriptions-item label="画像名称">{{ profile.name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="画像 ID">{{ profile.person_id || '-' }}</el-descriptions-item>
                <el-descriptions-item label="风险等级">
                  <el-tag :type="riskType(profile)" size="small">{{ riskLabel(profile) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="画像版本">{{ profile.version ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="更新时间">{{ formatTime(profile.updated_at) }}</el-descriptions-item>
              </el-descriptions>
              <el-empty v-else-if="!loading" description="当前租户暂无数据（如为权限问题请联系管理员）" :image-size="50" />
            </el-card>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-card header="标签" class="mb-16">
              <div class="tags">
                <el-tag v-for="t in (profile?.tags || [])" :key="String(t)" class="tag-item" type="info">{{ t }}</el-tag>
                <span v-if="!(profile?.tags || []).length" class="text-muted">暂无标签</span>
              </div>
            </el-card>
            <el-card header="画像维度" class="mb-16" data-test="feature-dist">
              <div v-if="dimensionEntries.length">
                <div v-for="[dimKey, dimValue] in dimensionEntries" :key="dimKey" class="dimension-block">
                  <div class="dimension-title">{{ dimKey }}</div>
                  <pre class="dimension-value">{{ JSON.stringify(dimValue, null, 2) }}</pre>
                </div>
              </div>
              <el-empty v-else-if="!loading" description="暂无维度数据" :image-size="50" />
            </el-card>
          </el-col>
        </el-row>

        <el-drawer v-model="editVisible" title="编辑画像属性" size="480px" data-test="portrait-edit-drawer">
          <el-alert
            title="增量更新（PATCH）：对象递归合并、数组去重追加、标量覆盖、null 删除键"
            type="info"
            show-icon
            :closable="false"
            class="mb-16"
          />
          <el-input
            v-model="editText"
            type="textarea"
            :rows="16"
            spellcheck="false"
            data-test="portrait-edit-json"
          />
          <template #footer>
            <el-button @click="editVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" data-test="portrait-edit-save" @click="saveEdit">保存</el-button>
          </template>
        </el-drawer>
      </div>
    </template>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dpsApi, type DpsPortrait } from '@/core/api/dps'
import { describeError, type ErrorPresentation } from '@/core/api/error'

const route = useRoute()
const router = useRouter()
const personId = String(route.params.id || '')
const profile = ref<DpsPortrait | null>(null)
const loading = ref(false)
const presentation = ref<ErrorPresentation | null>(null)
/** 属性编辑抽屉（批次 5：PATCH 深合并 + If-Match 乐观锁） */
const editVisible = ref(false)
const editText = ref('')
const saving = ref(false)

const isForbidden = computed(() => presentation.value?.pageLevel === true)
const isNotFound = computed(() => presentation.value?.kind === 'not-found')
const showErrorBar = computed(
  () => !!presentation.value && !presentation.value.pageLevel && presentation.value.kind !== 'not-found',
)
const errorMessage = computed(() =>
  showErrorBar.value ? `画像详情加载失败：${presentation.value?.detail || '网络错误'}` : '',
)

const dimensionEntries = computed(() => {
  const dims = (profile.value?.dimensions || {}) as Record<string, unknown>
  return Object.entries(dims)
})

function riskOf(row: DpsPortrait): number {
  const raw = row.risk_level ?? row.risk_score
  const n = Number(raw)
  return Number.isFinite(n) ? n : -1
}

function riskLabel(row: DpsPortrait): string {
  const v = riskOf(row)
  if (v < 0) return '未知'
  if (v >= 70) return '高'
  if (v >= 40) return '中'
  return '低'
}

function riskType(row: DpsPortrait): 'success' | 'warning' | 'danger' | 'info' {
  const v = riskOf(row)
  if (v < 0) return 'info'
  if (v >= 70) return 'danger'
  if (v >= 40) return 'warning'
  return 'success'
}

function formatTime(v?: string) {
  if (!v) return '-'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('zh-CN', { hour12: false })
}

function openEdit() {
  const attributes = (profile.value?.attributes || {}) as Record<string, unknown>
  editText.value = JSON.stringify(attributes, null, 2)
  editVisible.value = true
}

/** 提交属性增量更新：JSON 校验 → PATCH（携带 If-Match version）→ 刷新 */
async function saveEdit() {
  if (!profile.value) return
  let parsed: unknown
  try {
    parsed = JSON.parse(editText.value || '{}')
  } catch {
    ElMessage.error('属性必须是合法 JSON')
    return
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    ElMessage.error('属性必须是 JSON 对象')
    return
  }
  saving.value = true
  try {
    const version = Number(profile.value.version)
    await dpsApi.updatePortrait(
      personId,
      { business: { attributes: parsed } },
      Number.isFinite(version) ? version : undefined,
    )
    ElMessage.success('画像属性已更新')
    editVisible.value = false
    await loadData()
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 409) {
      ElMessage.warning('版本已变更，已刷新最新数据')
      editVisible.value = false
      await loadData()
    } else {
      ElMessage.error('保存失败，请检查属性内容后重试')
    }
  } finally {
    saving.value = false
  }
}

/** 删除当前画像：二次确认 → DELETE → 返回列表（避免停留已删除详情页） */
async function removePortrait() {
  try {
    await ElMessageBox.confirm(
      `确认删除画像「${profile.value?.name || personId}」？删除后将不再出现在列表与检索中（保留历史审计）。`,
      '删除确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await dpsApi.deletePortrait(personId)
    ElMessage.success('画像已删除')
    await router.replace('/portrait')
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    ElMessage.error(status === 404 ? '画像不存在或已被删除' : '删除失败，请稍后重试')
  }
}

async function loadData() {
  if (!personId) {
    presentation.value = {
      kind: 'unknown',
      title: '加载失败',
      detail: '缺少画像 ID 参数',
      requestId: '',
      retryable: false,
      pageLevel: false,
    }
    return
  }
  loading.value = true
  presentation.value = null
  try {
    profile.value = await dpsApi.getPortrait(personId)
  } catch (err) {
    profile.value = null
    presentation.value = describeError(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadData()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.card-actions { display: flex; align-items: center; gap: 4px; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag-item { margin-right: 4px; }
.text-muted { color: #9ca3af; }
.dimension-block { margin-bottom: 12px; }
.dimension-title { font-weight: 600; font-size: 13px; color: #374151; margin-bottom: 4px; text-transform: capitalize; }
.dimension-value {
  margin: 0; padding: 8px 10px; background: #f9fafb; border-radius: 6px;
  font-size: 12px; color: #6b7280; white-space: pre-wrap; word-break: break-all;
}
.request-id { color: #6b7280; font-size: 12px; margin-bottom: 8px; }
</style>
