<template>
  <div class="edgerouter-page">
    <el-tabs v-model="activeTab" data-test="er-tabs">
      <!-- 组织管理 -->
      <el-tab-pane label="组织管理" name="orgs">
        <div class="page-toolbar">
          <el-button type="primary" size="small" data-test="er-org-add" @click="addOrg">新增组织</el-button>
        </div>
        <el-table :data="orgs" stripe empty-text="暂无组织" data-test="er-org-table">
          <el-table-column prop="name" label="组织名称" min-width="150" />
          <el-table-column prop="quota" label="配额" width="140" />
          <el-table-column prop="used" label="已用" width="100" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'danger'" size="small">{{ row.enabled ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="editOrg(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 配额管理 -->
      <el-tab-pane label="配额管理" name="quotas">
        <div class="page-toolbar">
          <el-button type="primary" size="small" data-test="er-quota-add" @click="addQuota">新增配额</el-button>
        </div>
        <el-table :data="quotas" stripe empty-text="暂无配额" data-test="er-quota-table">
          <el-table-column prop="org" label="组织" width="150" />
          <el-table-column prop="resource" label="资源" width="140" />
          <el-table-column prop="limit" label="额度" width="120" />
          <el-table-column prop="used" label="已用" width="100" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="er-quota-edit" @click="editQuota(row)">调整</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 适配器管理 -->
      <el-tab-pane label="适配器管理" name="adapters">
        <el-table :data="adapters" stripe empty-text="暂无适配器" data-test="er-adapter-table">
          <el-table-column prop="name" label="适配器" min-width="150" />
          <el-table-column prop="type" label="类型" width="140" />
          <el-table-column prop="endpoint" label="端点" min-width="180" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" data-test="er-adapter-toggle" @change="toggleAdapter(row)" />
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 路由审计 -->
      <el-tab-pane label="路由审计" name="audit">
        <el-table :data="routeAudit" stripe empty-text="暂无审计记录" data-test="er-audit-table">
          <el-table-column prop="time" label="时间" width="170" />
          <el-table-column prop="org" label="组织" width="120" />
          <el-table-column prop="action" label="动作" width="140" />
          <el-table-column prop="target" label="目标" min-width="180" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface OrgRow { name: string; quota: string; used: string; enabled: boolean }
interface QuotaRow { org: string; resource: string; limit: string; used: string }
interface AdapterRow { name: string; type: string; endpoint: string; enabled: boolean }

const activeTab = ref('orgs')

const orgs = ref<OrgRow[]>([
  { name: 'AI 平台部', quota: '5,000,000', used: '2,340,000', enabled: true },
  { name: '模型组', quota: '2,000,000', used: '1,890,000', enabled: true },
])

const quotas = ref<QuotaRow[]>([
  { org: 'AI 平台部', resource: 'tokens/month', limit: '5,000,000', used: '2,340,000' },
  { org: '模型组', resource: 'tokens/month', limit: '2,000,000', used: '1,890,000' },
])

const adapters = ref<AdapterRow[]>([
  { name: 'OpenAI 兼容适配器', type: 'openai', endpoint: 'http://10.0.0.5:8001/v1', enabled: true },
  { name: 'Ollama 适配器', type: 'ollama', endpoint: 'http://127.0.0.1:11434', enabled: true },
])

const routeAudit = ref([
  { time: '2026-08-28 11:20:00', org: 'AI 平台部', action: 'route.create', target: 'openllm/gpt-4o-mini' },
  { time: '2026-08-27 15:44:12', org: '模型组', action: 'quota.increase', target: 'tokens/month → 2,000,000' },
])

function addOrg() {
  orgs.value.push({ name: `新组织-${orgs.value.length + 1}`, quota: '1,000,000', used: '0', enabled: true })
  ElMessage.success('组织已新增')
}

function editOrg(row: OrgRow) {
  ElMessage.success(`组织 ${row.name} 已更新`)
}

function addQuota() {
  quotas.value.push({ org: '新组织', resource: 'tokens/month', limit: '1,000,000', used: '0' })
  ElMessage.success('配额已新增')
}

function editQuota(row: QuotaRow) {
  ElMessage.success(`配额 ${row.org}/${row.resource} 已调整并实时生效`)
}

function toggleAdapter(row: AdapterRow) {
  ElMessage.success(row.enabled ? `适配器 ${row.name} 已启用` : `适配器 ${row.name} 已停用`)
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
</style>
