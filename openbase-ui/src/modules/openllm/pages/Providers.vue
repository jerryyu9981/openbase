<template>
  <div>
    <div class="page-toolbar">
      <el-button type="primary" data-test="register-provider" @click="openForm()">新增提供商</el-button>
    </div>
    <el-row :gutter="16">
      <el-col v-for="p in providers" :key="p.id" :xs="24" :sm="12" :lg="8">
        <el-card class="provider-card">
          <div class="provider-head">
            <el-tag size="small">{{ p.type }}</el-tag>
            <el-switch :model-value="p.enabled" size="small" data-test="provider-toggle" @change="(v: boolean) => toggle(p, v)" />
          </div>
          <h3>{{ p.name }}</h3>
          <p class="meta">{{ p.base_url }}</p>
          <p class="meta">支持模型：{{ p.model_count }} · P50 延迟：{{ p.latency_ms }}ms</p>
          <div class="actions">
            <el-button link type="primary" @click="testConnection(p)">测试连接</el-button>
            <el-button link type="primary" @click="syncModels(p)">同步模型</el-button>
            <el-button link type="primary" @click="openForm(p)">编辑</el-button>
            <el-popconfirm title="确认删除该提供商？" @confirm="remove(p.id)">
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-dialog v-model="formVisible" :title="editingId ? '编辑提供商' : '新增提供商'" width="520px" data-test="provider-dialog">
      <el-form label-width="110px">
        <el-form-item label="名称" required><el-input v-model="form.name" placeholder="如：OpenAI" data-test="provider-name-input" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="商业" value="商业" />
            <el-option label="开源" value="开源" />
            <el-option label="本地" value="本地" />
            <el-option label="Azure" value="Azure" />
          </el-select>
        </el-form-item>
        <el-form-item label="Base URL" required><el-input v-model="form.base_url" placeholder="https://api.openai.com" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="form.api_key" type="password" show-password placeholder="留空不修改" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" data-test="provider-submit" @click="saveProvider">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface Provider {
  id: number
  name: string
  type: string
  enabled: boolean
  base_url: string
  api_key: string
  description: string
  model_count: number
  latency_ms: number
  healthy: boolean
}

const formVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ name: '', type: '商业', base_url: '', api_key: '', description: '' })

const providers = ref<Provider[]>([
  { id: 1, name: 'OpenAI', type: '商业', enabled: true, base_url: 'https://api.openai.com', api_key: '', description: '商业模型提供商', model_count: 8, latency_ms: 320, healthy: true },
  { id: 2, name: 'Ollama 本地', type: '本地', enabled: true, base_url: 'http://127.0.0.1:11434', api_key: '', description: '本地 Ollama 服务', model_count: 5, latency_ms: 85, healthy: true },
  { id: 3, name: 'Azure OpenAI', type: 'Azure', enabled: false, base_url: 'https://xxx.openai.azure.com', api_key: '', description: 'Azure 部署', model_count: 4, latency_ms: 0, healthy: false },
])

function openForm(p?: Provider) {
  editingId.value = p?.id ?? null
  form.name = p?.name ?? ''
  form.type = p?.type ?? '商业'
  form.base_url = p?.base_url ?? ''
  form.api_key = ''
  form.description = p?.description ?? ''
  formVisible.value = true
}
function saveProvider() {
  if (!form.name.trim() || !form.base_url.trim()) {
    ElMessage.warning('请输入名称与 Base URL')
    return
  }
  if (editingId.value) {
    const target = providers.value.find((x) => x.id === editingId.value)
    if (target) {
      Object.assign(target, {
        name: form.name.trim(),
        type: form.type,
        base_url: form.base_url.trim(),
        api_key: form.api_key ? form.api_key : target.api_key,
        description: form.description,
      })
      ElMessage.success('提供商已更新')
    }
  } else {
    providers.value.push({
      id: Date.now(),
      name: form.name.trim(),
      type: form.type,
      enabled: true,
      base_url: form.base_url.trim(),
      api_key: form.api_key,
      description: form.description,
      model_count: 0,
      latency_ms: 0,
      healthy: false,
    })
    ElMessage.success('提供商已添加')
  }
  formVisible.value = false
}
function toggle(p: Provider, enabled: boolean) {
  p.enabled = enabled
  p.healthy = enabled
  ElMessage.success(`${p.name} 已${enabled ? '启用' : '禁用'}`)
}
function testConnection(p: Provider) {
  const ok = p.base_url.length > 5
  p.healthy = ok
  p.latency_ms = ok ? Math.floor(60 + Math.random() * 120) : 0
  ElMessage[ok ? 'success' : 'error'](`${p.name} 连接${ok ? '成功' : '失败'}（${p.latency_ms}ms）`)
}
function syncModels(p: Provider) {
  p.model_count = p.model_count + Math.floor(1 + Math.random() * 3)
  ElMessage.success(`${p.name} 模型同步完成，当前 ${p.model_count} 个`)
}
function remove(id: number) {
  providers.value = providers.value.filter((x) => x.id !== id)
  ElMessage.success('提供商已删除')
}
</script>

<style scoped>
.page-toolbar { margin-bottom: 16px; }
.provider-card { margin-bottom: 16px; }
.provider-head { display: flex; justify-content: space-between; align-items: center; }
.provider-card h3 { margin: 8px 0; }
.meta { color: var(--ob-text-secondary); font-size: 13px; margin: 2px 0; }
.actions { margin-top: 8px; }
</style>
