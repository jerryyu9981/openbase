<template>
  <div>
    <div class="page-toolbar">
      <el-button type="primary" data-test="register-provider" @click="$router.push('/openllm/providers/register')">注册提供商</el-button>
    </div>
    <el-row :gutter="16">
      <el-col :xs="24" :sm="12" :lg="8" v-for="p in providers" :key="p.name">
        <el-card class="provider-card">
          <div class="provider-head">
            <el-tag size="small">{{ p.type }}</el-tag>
            <el-switch :model-value="p.enabled" size="small" @change="(v: boolean) => toggle(p.name, v)" />
          </div>
          <h3>{{ p.name }}</h3>
          <p class="meta">支持模型：{{ p.model_count }} · P50 延迟：{{ p.latency_ms }}ms</p>
          <el-button link type="primary" @click="openDetail(p)">查看详情</el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface Provider { name: string; type: string; enabled: boolean; model_count: number; latency_ms: number; healthy: boolean }

const providers = ref<Provider[]>([
  { name: 'OpenAI', type: '商业', enabled: true, model_count: 8, latency_ms: 320, healthy: true },
  { name: 'Ollama 本地', type: '本地', enabled: true, model_count: 5, latency_ms: 85, healthy: true },
  { name: 'Azure OpenAI', type: 'Azure', enabled: false, model_count: 4, latency_ms: 0, healthy: false },
])

function toggle(name: string, enabled: boolean) {
  const p = providers.value.find((x) => x.name === name)
  if (p) { p.enabled = enabled; ElMessage.success(`${name} 已${enabled ? '启用' : '禁用'}`) }
}
function openDetail(p: Provider) {
  ElMessage.info(`提供商详情：${p.name}（健康：${p.healthy ? '正常' : '异常'}）`)
}
</script>

<style scoped>
.page-toolbar { margin-bottom: 16px; }
.provider-card { margin-bottom: 16px; }
.provider-head { display: flex; justify-content: space-between; align-items: center; }
.provider-card h3 { margin: 8px 0; }
.meta { color: var(--ob-text-secondary); font-size: 13px; }
</style>
