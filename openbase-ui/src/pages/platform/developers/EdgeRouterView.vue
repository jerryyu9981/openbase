<template>
  <PageContainer
    title="EdgeRouter 与适配器"
    description="边缘路由的组织、配额、适配器与审计（数据源：OpenLLM /api/v1/edge/**，经 OpenBase 通用代理）"
    test-id="edge-router-view-page"
  >
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="er-error"
      @close="errorMessage = ''"
    />

    <el-tabs v-model="activeTab" data-test="er-tabs" @tab-change="onTabChange">
      <!-- 概览 -->
      <el-tab-pane label="概览" name="overview">
        <div v-loading="overviewLoading" class="overview-grid" data-test="er-overview">
          <el-card shadow="never">
            <template #header>运行状态</template>
            <el-descriptions v-if="status" :column="1" size="small" border>
              <el-descriptions-item label="状态">
                <el-tag :type="status.status === 'running' ? 'success' : 'info'" size="small">{{ status.status }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="版本">{{ status.version }}</el-descriptions-item>
              <el-descriptions-item label="运行时长">{{ formatUptime(status.uptime_seconds) }}</el-descriptions-item>
              <el-descriptions-item label="路由模式">{{ status.router_mode }}</el-descriptions-item>
              <el-descriptions-item label="适配器数">{{ status.adapter_count }}</el-descriptions-item>
            </el-descriptions>
            <el-empty v-else description="暂无状态数据" :image-size="60" />
          </el-card>

          <el-card shadow="never">
            <template #header>组件健康</template>
            <el-descriptions v-if="health" :column="1" size="small" border>
              <el-descriptions-item label="总体">
                <el-tag :type="health.status === 'healthy' ? 'success' : 'danger'" size="small">{{ health.status }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item v-for="(value, name) in health.components" :key="name" :label="String(name)">
                {{ value }}
              </el-descriptions-item>
            </el-descriptions>
            <el-empty v-else description="暂无健康数据" :image-size="60" />
          </el-card>

          <el-card shadow="never">
            <template #header>能力开关</template>
            <div v-if="status" class="feature-tags">
              <el-tag
                v-for="(enabled, name) in status.features"
                :key="name"
                :type="enabled ? 'success' : 'info'"
                size="small"
                class="perm-tag"
              >
                {{ name }}：{{ enabled ? '开' : '关' }}
              </el-tag>
            </div>
            <el-empty v-else description="暂无开关数据" :image-size="60" />
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 组织管理 -->
      <el-tab-pane label="组织管理" name="orgs">
        <div class="page-toolbar">
          <el-button data-test="er-org-refresh" :loading="orgLoading" @click="loadOrganizations">刷新</el-button>
          <el-button type="primary" size="small" data-test="er-org-add" @click="openOrgForm()">新增组织</el-button>
        </div>
        <el-table v-loading="orgLoading" :data="orgs" stripe empty-text="暂无组织" data-test="er-org-table">
          <el-table-column prop="name" label="组织标识" min-width="150" />
          <el-table-column prop="display_name" label="显示名称" min-width="150" />
          <el-table-column prop="description" label="描述" min-width="180">
            <template #default="{ row }">{{ row.description || '—' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="er-org-edit" @click="openOrgForm(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 配额管理 -->
      <el-tab-pane label="配额管理" name="quotas">
        <div class="page-toolbar">
          <el-select
            v-model="quotaOrg"
            placeholder="选择组织"
            style="width: 220px"
            data-test="er-quota-org"
            @change="loadQuotas"
          >
            <el-option v-for="org in orgs" :key="org.name" :label="org.display_name || org.name" :value="org.name" />
          </el-select>
          <el-button data-test="er-quota-refresh" :loading="quotaLoading" :disabled="!quotaOrg" @click="loadQuotas">刷新</el-button>
        </div>
        <el-alert
          v-if="!orgs.length"
          type="info"
          :closable="false"
          show-icon
          title="尚无组织，配额以组织为维度管理；请先在「组织管理」创建组织。"
          data-test="er-quota-empty-hint"
        />
        <el-table v-loading="quotaLoading" :data="quotas" stripe empty-text="暂无配额" data-test="er-quota-table">
          <el-table-column prop="resource_type" label="资源" width="160" />
          <el-table-column prop="limit_value" label="额度" width="120" />
          <el-table-column prop="current_usage" label="已用" width="120" />
          <el-table-column label="预警阈值" width="110">
            <template #default="{ row }">{{ row.warning_threshold }}%</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="er-quota-edit" @click="openQuotaForm(row)">调整</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 适配器管理 -->
      <el-tab-pane label="适配器管理" name="adapters">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          class="mb-16"
          title="适配器由 EdgeRouter 启动时注册，状态只读；注销会直接影响运行态路由分发，需在运维窗口由后端接口执行。"
          data-test="er-adapter-notice"
        />
        <el-table v-loading="adapterLoading" :data="adapters" stripe empty-text="暂无适配器" data-test="er-adapter-table">
          <el-table-column prop="name" label="适配器" min-width="170" />
          <el-table-column prop="isolation_type" label="隔离方式" width="170" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="注册时间" min-width="170">
            <template #default="{ row }">{{ row.registered_at || '—' }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 路由审计 -->
      <el-tab-pane label="路由审计" name="audit">
        <div class="page-toolbar">
          <el-button data-test="er-audit-refresh" :loading="auditLoading" @click="loadAudit">刷新</el-button>
          <span class="text-muted">共 {{ auditTotal }} 条</span>
        </div>
        <el-table v-loading="auditLoading" :data="auditRows" stripe empty-text="暂无审计记录" data-test="er-audit-table">
          <el-table-column prop="timestamp" label="时间" width="190">
            <template #default="{ row }">{{ row.timestamp || '—' }}</template>
          </el-table-column>
          <el-table-column prop="org_id" label="组织" width="130" />
          <el-table-column prop="action" label="动作" width="150" />
          <el-table-column prop="request_path" label="路径" min-width="200" />
          <el-table-column prop="request_method" label="方法" width="90" />
          <el-table-column prop="response_status" label="状态码" width="90" />
        </el-table>
        <el-pagination
          v-if="auditTotal > auditPageSize"
          class="pager"
          layout="prev, pager, next"
          :total="auditTotal"
          :page-size="auditPageSize"
          :current-page="auditPage"
          @current-change="changeAuditPage"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- 组织表单 -->
    <el-dialog v-model="orgDialogVisible" :title="editingOrg ? '编辑组织' : '新增组织'" width="480px" data-test="er-org-dialog">
      <el-form label-width="100px">
        <el-form-item label="组织标识" required>
          <el-input v-model="orgForm.name" :disabled="!!editingOrg" placeholder="如：ai-platform" data-test="er-org-name" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="orgForm.display_name" placeholder="如：AI 平台部" data-test="er-org-display" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="orgForm.description" type="textarea" :rows="2" data-test="er-org-desc" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="orgDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" data-test="er-org-submit" @click="saveOrg">保存</el-button>
      </template>
    </el-dialog>

    <!-- 配额表单 -->
    <el-dialog v-model="quotaDialogVisible" title="调整配额" width="460px" data-test="er-quota-dialog">
      <el-form label-width="110px">
        <el-form-item label="资源"><span>{{ quotaForm.resource_type }}</span></el-form-item>
        <el-form-item label="额度上限">
          <el-input-number v-model="quotaForm.limit_value" :min="1" :step="1000" style="width: 100%" data-test="er-quota-limit" />
        </el-form-item>
        <el-form-item label="预警阈值（%）">
          <el-input-number v-model="quotaForm.warning_threshold" :min="0" :max="100" style="width: 100%" data-test="er-quota-threshold" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quotaDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" data-test="er-quota-submit" @click="saveQuota">保存</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  edgeApi,
  type EdgeAdapter,
  type EdgeAuditLog,
  type EdgeHealth,
  type EdgeOrganization,
  type EdgeQuota,
  type EdgeStatus,
} from '@/core/api/governance'

const activeTab = ref('overview')

const status = ref<EdgeStatus | null>(null)
const health = ref<EdgeHealth | null>(null)
const overviewLoading = ref(false)

const orgs = ref<EdgeOrganization[]>([])
const orgLoading = ref(false)

const adapters = ref<EdgeAdapter[]>([])
const adapterLoading = ref(false)

const quotaOrg = ref('')
const quotas = ref<EdgeQuota[]>([])
const quotaLoading = ref(false)

const auditRows = ref<EdgeAuditLog[]>([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditPageSize = 20
const auditLoading = ref(false)

const submitting = ref(false)
const errorMessage = ref('')

const orgDialogVisible = ref(false)
const editingOrg = ref<EdgeOrganization | null>(null)
const orgForm = reactive({ name: '', display_name: '', description: '' })

const quotaDialogVisible = ref(false)
const quotaForm = reactive({ resource_type: '', limit_value: 1, warning_threshold: 80 })

function messageOf(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  return fallback
}

function formatUptime(seconds: number): string {
  if (!seconds && seconds !== 0) return '—'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${days}天 ${hours}小时 ${minutes}分`
}

async function loadOverview(): Promise<void> {
  overviewLoading.value = true
  try {
    const [statusData, healthData] = await Promise.all([edgeApi.status(), edgeApi.health()])
    status.value = statusData
    health.value = healthData
  } catch (error) {
    errorMessage.value = `EdgeRouter 概览加载失败：${messageOf(error, '未知错误')}`
  } finally {
    overviewLoading.value = false
  }
}

async function loadOrganizations(): Promise<void> {
  orgLoading.value = true
  try {
    orgs.value = await edgeApi.listOrganizations()
  } catch (error) {
    errorMessage.value = `组织列表加载失败：${messageOf(error, '未知错误')}`
  } finally {
    orgLoading.value = false
  }
}

async function loadAdapters(): Promise<void> {
  adapterLoading.value = true
  try {
    adapters.value = await edgeApi.listAdapters()
  } catch (error) {
    errorMessage.value = `适配器列表加载失败：${messageOf(error, '未知错误')}`
  } finally {
    adapterLoading.value = false
  }
}

async function loadQuotas(): Promise<void> {
  if (!quotaOrg.value) return
  quotaLoading.value = true
  try {
    quotas.value = await edgeApi.listQuotas(quotaOrg.value)
  } catch (error) {
    quotas.value = []
    errorMessage.value = `配额加载失败：${messageOf(error, '未知错误')}`
  } finally {
    quotaLoading.value = false
  }
}

async function loadAudit(): Promise<void> {
  auditLoading.value = true
  try {
    const page = await edgeApi.listAuditLogs({ page: auditPage.value, page_size: auditPageSize })
    auditRows.value = page.items
    auditTotal.value = page.total
  } catch (error) {
    auditRows.value = []
    auditTotal.value = 0
    errorMessage.value = `审计日志加载失败：${messageOf(error, '未知错误')}`
  } finally {
    auditLoading.value = false
  }
}

function changeAuditPage(page: number): void {
  auditPage.value = page
  void loadAudit()
}

function onTabChange(name: string | number): void {
  if (name === 'quotas' && !quotas.value.length && quotaOrg.value) void loadQuotas()
  if (name === 'audit' && !auditRows.value.length) void loadAudit()
  if (name === 'adapters' && !adapters.value.length) void loadAdapters()
  if (name === 'orgs' && !orgs.value.length) void loadOrganizations()
}

function openOrgForm(target?: EdgeOrganization): void {
  editingOrg.value = target ?? null
  orgForm.name = target?.name ?? ''
  orgForm.display_name = target?.display_name ?? ''
  orgForm.description = target?.description ?? ''
  orgDialogVisible.value = true
}

async function saveOrg(): Promise<void> {
  if (!orgForm.name.trim()) {
    ElMessage.warning('请输入组织标识')
    return
  }
  submitting.value = true
  try {
    if (editingOrg.value) {
      await edgeApi.updateOrganization(editingOrg.value.id, {
        display_name: orgForm.display_name.trim() || undefined,
        description: orgForm.description.trim() || undefined,
      })
      ElMessage.success('组织已更新')
    } else {
      await edgeApi.createOrganization({
        name: orgForm.name.trim(),
        display_name: orgForm.display_name.trim() || undefined,
        description: orgForm.description.trim() || undefined,
      })
      ElMessage.success('组织已创建')
    }
    orgDialogVisible.value = false
    await loadOrganizations()
  } catch (error) {
    errorMessage.value = `保存组织失败：${messageOf(error, '未知错误')}`
  } finally {
    submitting.value = false
  }
}

function openQuotaForm(row: EdgeQuota): void {
  quotaForm.resource_type = row.resource_type
  quotaForm.limit_value = row.limit_value
  quotaForm.warning_threshold = row.warning_threshold
  quotaDialogVisible.value = true
}

async function saveQuota(): Promise<void> {
  if (!quotaOrg.value) return
  submitting.value = true
  try {
    await edgeApi.updateQuota(quotaOrg.value, {
      resource_type: quotaForm.resource_type,
      limit_value: quotaForm.limit_value,
      warning_threshold: quotaForm.warning_threshold,
    })
    ElMessage.success('配额已更新')
    quotaDialogVisible.value = false
    await loadQuotas()
  } catch (error) {
    errorMessage.value = `配额更新失败：${messageOf(error, '未知错误')}`
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void loadOverview()
  void loadOrganizations()
  void loadAdapters()
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.overview-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
.feature-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.perm-tag { margin-right: 4px; }
.text-muted { color: var(--ob-text-secondary); }
.pager { margin-top: 12px; justify-content: flex-end; }
</style>
