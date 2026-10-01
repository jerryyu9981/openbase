<template>
  <div class="dps-package">
    <el-card>
      <el-tabs v-model="activeTab" data-test="package-tabs">
        <!-- 导出 -->
        <el-tab-pane label="导出" name="export">
          <el-form label-width="140px">
            <el-form-item label="scope.type">
              <el-select v-model="exportScopeType" style="width: 200px" data-test="export-scope-type">
                <el-option label="template" value="template" />
                <el-option label="annotation_template" value="annotation_template" />
              </el-select>
            </el-form-item>
            <el-form-item label="scope.codes">
              <el-select
                v-model="exportCodes"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入或选择模板 code"
                style="width: 420px"
                data-test="export-codes"
              />
            </el-form-item>
            <el-form-item label="include_annotation_templates">
              <el-switch v-model="includeAnnotationTemplates" data-test="export-include-annotation" />
            </el-form-item>
          </el-form>
          <el-button type="primary" :loading="exporting" data-test="export-run" @click="doExport">导出</el-button>
        </el-tab-pane>

        <!-- 导入 -->
        <el-tab-pane label="导入" name="import">
          <el-alert type="warning" show-icon :closable="false" class="mb-16" data-test="import-mode-warning">
            <template #title>模式须显式选择</template>
            <div>不得默认实做；默认落在最安全的 dry_run，切换为「实做」时须二次确认。</div>
          </el-alert>
          <el-form label-width="140px">
            <el-form-item label="导入模式">
              <el-radio-group v-model="dryRun" data-test="import-mode">
                <el-radio :value="true">dry_run（预检，不写入）</el-radio>
                <el-radio :value="false">实做（写入）</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="冲突策略">
              <el-select v-model="conflictPolicy" placeholder="未指定（存在冲突 → 409）" clearable style="width: 220px" data-test="import-conflict-policy">
                <el-option label="overwrite" value="overwrite" />
                <el-option label="skip" value="skip" />
                <el-option label="rename" value="rename" />
              </el-select>
            </el-form-item>
            <el-form-item label="package（JSON）">
              <el-input v-model="packageJson" type="textarea" :rows="6" placeholder="package JSON（含 format_version 等字段）" data-test="import-package-json" />
            </el-form-item>
          </el-form>
          <el-button type="primary" :loading="importing" data-test="import-run" @click="doImport">执行</el-button>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-alert v-if="error" type="error" show-icon :closable="false" class="mt-16" data-test="dps-error">
      <template #title>{{ error.title }}</template>
      <div>{{ error.detail }}</div>
      <div v-if="error.hint" class="hint" data-test="dps-error-hint">{{ error.hint }}</div>
      <span v-if="error.requestId" class="request-id" data-test="dps-request-id">请求编号：{{ error.requestId }}</span>
    </el-alert>

    <div v-if="exportResult" class="mt-16">
      <el-card header="导出结果">
        <el-descriptions :column="1" border size="small" data-test="export-result">
          <el-descriptions-item label="format_version">{{ exportResult.format_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="package_hash">{{ exportResult.package_hash || '-' }}</el-descriptions-item>
          <el-descriptions-item label="items">{{ (exportResult.items || []).length }} 项</el-descriptions-item>
          <el-descriptions-item label="dependencies">{{ (exportResult.dependencies || []).length }} 项</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>

    <div v-if="importResult" class="grid-2 mt-16">
      <el-card :header="dryRun ? '结果 · dry_run' : '结果 · 实做'">
        <el-descriptions v-if="dryRun" :column="1" border size="small" data-test="import-result-dry">
          <el-descriptions-item label="would_create">{{ importResult.would_create ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="would_skip">{{ importResult.would_skip ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="would_conflict">{{ importResult.would_conflict ?? 0 }}</el-descriptions-item>
        </el-descriptions>
        <el-descriptions v-else :column="1" border size="small" data-test="import-result-apply">
          <el-descriptions-item label="created">{{ importResult.created ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="skipped">{{ importResult.skipped ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="identical">{{ importResult.identical ? 'true' : 'false' }}</el-descriptions-item>
        </el-descriptions>
        <el-tag class="mt-8" :type="dryRun ? 'warning' : 'success'" data-test="import-result-tag">
          {{ dryRun ? '预检' : '已执行' }}
        </el-tag>
      </el-card>

      <el-card v-if="failures.length" header="失败项（逐条列出）">
        <el-table :data="failures" stripe data-test="import-failures">
          <el-table-column type="index" label="#" width="60" />
          <el-table-column prop="object" label="对象" min-width="200" />
          <el-table-column prop="reason" label="原因" min-width="220" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dpsApi, type DpsPackageImportResult, type DpsTemplatePackage } from '@/core/api/dps'
import { describeDpsError, type DpsErrorPresentation } from '@/core/api/error'

const activeTab = ref<'export' | 'import'>('export')
const exportScopeType = ref('template')
const exportCodes = ref<string[]>([])
const includeAnnotationTemplates = ref(true)
const dryRun = ref(true)
const conflictPolicy = ref('')
const packageJson = ref('')
const exporting = ref(false)
const importing = ref(false)
const exportResult = ref<DpsTemplatePackage | null>(null)
const importResult = ref<DpsPackageImportResult | null>(null)
const error = ref<DpsErrorPresentation | null>(null)

interface FailureItem { object: string; reason: string }
const failures = computed<FailureItem[]>(() =>
  (importResult.value?.errors || []).map((item) => {
    const record = (item ?? {}) as Record<string, unknown>
    return { object: String(record.object ?? record.code ?? '未知对象'), reason: String(record.reason ?? record.message ?? '未知原因') }
  }),
)

async function doExport() {
  exporting.value = true
  error.value = null
  try {
    exportResult.value = await dpsApi.exportPackage({
      scope: { type: exportScopeType.value, codes: exportCodes.value },
      include_annotation_templates: includeAnnotationTemplates.value,
    })
    ElMessage.success('导出完成')
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    exporting.value = false
  }
}

async function doImport() {
  if (!packageJson.value.trim()) {
    ElMessage.warning('请先提供 package JSON')
    return
  }
  if (!dryRun.value) {
    try {
      await ElMessageBox.confirm('当前为「实做（写入）」模式，导入将真实写入数据，确认继续？', '确认实做导入', {
        confirmButtonText: '确认实做',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }
  }
  importing.value = true
  error.value = null
  try {
    importResult.value = await dpsApi.importPackage({
      package: JSON.parse(packageJson.value) as Record<string, unknown>,
      conflict_policy: (conflictPolicy.value || undefined) as 'overwrite' | 'skip' | 'rename' | undefined,
      dry_run: dryRun.value,
    })
    ElMessage.success(dryRun.value ? '预检完成（未写入）' : '导入已执行')
  } catch (caught) {
    error.value = describeDpsError(caught)
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.mt-8 { margin-top: 8px; }
.mt-16 { margin-top: 16px; }
.mb-16 { margin-bottom: 16px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.hint { color: var(--ob-text-secondary); font-size: 12px; margin-top: 4px; }
.request-id { color: var(--ob-text-disabled); font-size: 12px; margin-left: 8px; }
@media (max-width: 767px) {
  .grid-2 { grid-template-columns: 1fr; }
}
</style>
