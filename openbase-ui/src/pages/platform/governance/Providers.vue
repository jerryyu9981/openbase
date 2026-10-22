<template>
  <PageContainer title="提供商管理" description="模型提供商与接入凭据（经 OpenBase 通用代理聚合 OpenLLM）" test-id="providers-page">
    <div class="page-toolbar">
      <el-button type="primary" data-test="register-provider" @click="openForm()">新增提供商</el-button>
      <el-button data-test="provider-refresh" :loading="loading" @click="load()">刷新</el-button>
    </div>
    <el-alert
      v-if="errorText"
      type="error"
      :closable="false"
      show-icon
      class="page-alert"
      :title="errorText"
      data-test="provider-error"
    />
    <el-empty v-else-if="!loading && providers.length === 0" description="暂无提供商" data-test="provider-empty" />
    <el-row :gutter="16">
      <el-col v-for="p in providers" :key="p.id" :xs="24" :sm="12" :lg="8">
        <el-card class="provider-card" :data-test="`provider-card-${p.provider_code}`">
          <div class="provider-head">
            <el-tag size="small">{{ p.provider_type }}</el-tag>
            <el-switch
              :model-value="p.status === 'active'"
              size="small"
              data-test="provider-toggle"
              :loading="togglingId === p.id"
              @change="(value: boolean) => toggle(p, value)"
            />
          </div>
          <h3>{{ p.provider_name }}</h3>
          <p class="meta">{{ p.api_base_url }}</p>
          <p class="meta">
            健康：<el-tag size="small" :type="healthTagType(p.health_status)">{{ healthLabel(p.health_status) }}</el-tag>
            · 优先级：{{ p.priority }}
            · 模型数：{{ modelCounts[p.id] ?? '—' }}
          </p>
          <p class="meta">最近检查：{{ formatTime(p.last_health_check_at) }}</p>
          <div class="actions">
            <el-button link type="primary" @click="openForm(p)">编辑</el-button>
            <el-popconfirm title="确认删除该提供商？" @confirm="remove(p)">
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-dialog v-model="formVisible" :title="editing ? '编辑提供商' : '新增提供商'" width="520px" data-test="provider-dialog">
      <el-form label-width="110px">
        <el-form-item label="名称" required>
          <el-input v-model="form.provider_name" placeholder="如：OpenAI" data-test="provider-name-input" />
        </el-form-item>
        <el-form-item label="代码" :required="!editing">
          <el-input v-model="form.provider_code" :disabled="!!editing" placeholder="如：openai" data-test="provider-code-input" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.provider_type" style="width: 100%" data-test="provider-type-select">
            <el-option label="商业" value="commercial" />
            <el-option label="开源" value="open_source" />
            <el-option label="本地" value="local" />
            <el-option label="Azure" value="azure" />
          </el-select>
        </el-form-item>
        <el-form-item label="Base URL" required>
          <el-input v-model="form.api_base_url" placeholder="https://api.openai.com" data-test="provider-base-url-input" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="留空不修改" data-test="provider-key-input" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="0" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="provider-submit" @click="saveProvider">保存</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { governanceApi, type LlmProvider } from '@/core/api/governance'

/**
 * 提供商管理（v1.9.0 真实化）：数据源 = OpenLLM `/api/v1/providers`，
 * 经 `/api/v1/proxy/openllm/api/v1/providers` 聚合（OpenBase 注入 OpenLLM API Key）。
 * 原「测试连接 / 同步模型」为前端假动作（随机延迟、随机模型数），
 * 上游对应端点仅支持 JWT 通道，本轮先移除，缺口登记于能力缺口清单。
 */
const providers = ref<LlmProvider[]>([])
const modelCounts = ref<Record<string, number>>({})
const loading = ref(false)
const saving = ref(false)
const togglingId = ref('')
const errorText = ref('')

const formVisible = ref(false)
const editing = ref<LlmProvider | null>(null)
const form = reactive({
  provider_name: '',
  provider_code: '',
  provider_type: 'commercial',
  api_base_url: '',
  api_key: '',
  priority: 0,
})

const HEALTH_LABELS: Record<string, string> = {
  healthy: '正常',
  degraded: '降级',
  unhealthy: '异常',
  unknown: '未知',
}

function healthLabel(status: string): string {
  return HEALTH_LABELS[status] ?? status ?? '未知'
}

function healthTagType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'healthy') return 'success'
  if (status === 'degraded') return 'warning'
  if (status === 'unhealthy') return 'danger'
  return 'info'
}

function formatTime(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

async function loadModelCounts(items: LlmProvider[]): Promise<void> {
  const pairs = await Promise.all(
    items.map(async (item) => {
      try {
        const models = await governanceApi.listProviderModels(item.id)
        return [item.id, models.length] as const
      } catch {
        return [item.id, undefined] as const
      }
    }),
  )
  modelCounts.value = Object.fromEntries(pairs.filter((pair) => pair[1] !== undefined)) as Record<string, number>
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const items = await governanceApi.listProviders()
    providers.value = items
    await loadModelCounts(items)
  } catch (error) {
    const message = error instanceof Error ? error.message : '提供商列表加载失败'
    errorText.value = `提供商列表加载失败：${message}`
  } finally {
    loading.value = false
  }
}

function openForm(target?: LlmProvider): void {
  editing.value = target ?? null
  form.provider_name = target?.provider_name ?? ''
  form.provider_code = target?.provider_code ?? ''
  form.provider_type = target?.provider_type ?? 'commercial'
  form.api_base_url = target?.api_base_url ?? ''
  form.api_key = ''
  form.priority = target?.priority ?? 0
  formVisible.value = true
}

async function saveProvider(): Promise<void> {
  if (!form.provider_name.trim() || !form.api_base_url.trim()) {
    ElMessage.warning('请输入名称与 Base URL')
    return
  }
  if (!editing.value && !form.provider_code.trim()) {
    ElMessage.warning('请输入提供商代码')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await governanceApi.updateProvider(editing.value.id, {
        provider_name: form.provider_name.trim(),
        api_base_url: form.api_base_url.trim(),
        priority: form.priority,
        ...(form.api_key ? { api_key: form.api_key } : {}),
      })
      ElMessage.success('提供商已更新')
    } else {
      await governanceApi.createProvider({
        provider_name: form.provider_name.trim(),
        provider_code: form.provider_code.trim(),
        provider_type: form.provider_type,
        api_base_url: form.api_base_url.trim(),
        priority: form.priority,
        ...(form.api_key ? { api_key: form.api_key } : {}),
      })
      ElMessage.success('提供商已添加')
    }
    formVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggle(target: LlmProvider, enabled: boolean): Promise<void> {
  togglingId.value = target.id
  try {
    const updated = await governanceApi.updateProvider(target.id, { status: enabled ? 'active' : 'inactive' })
    target.status = updated.status
    ElMessage.success(`${target.provider_name} 已${enabled ? '启用' : '停用'}`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '状态切换失败')
  } finally {
    togglingId.value = ''
  }
}

async function remove(target: LlmProvider): Promise<void> {
  try {
    await governanceApi.deleteProvider(target.id)
    providers.value = providers.value.filter((item) => item.id !== target.id)
    ElMessage.success('提供商已删除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.page-alert { margin-bottom: 12px; }
.provider-card { margin-bottom: 16px; }
.provider-head { display: flex; justify-content: space-between; align-items: center; }
.provider-card h3 { margin: 8px 0; }
.meta { color: var(--ob-text-secondary); font-size: 13px; margin: 2px 0; }
.actions { margin-top: 8px; }
</style>
