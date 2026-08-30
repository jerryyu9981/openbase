<template>
  <div>
    <div class="page-toolbar">
      <span class="page-title" data-test="decay-title">衰减配置</span>
      <span class="tab-hint">记忆衰减引擎参数：控制记忆随时间的权重衰减策略（OpenMemory GET/PUT /decay/config）</span>
    </div>
    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="decay-error"
      @close="errorMsg = ''"
    />
    <div v-loading="loading">
      <template v-if="config">
        <el-card class="mb-16">
          <template #header>当前配置</template>
          <el-form label-width="160px" :model="config">
            <el-form-item label="衰减策略">
              <el-select v-model="config.strategy" style="width: 200px" data-test="decay-strategy">
                <el-option label="自适应（adaptive）" value="adaptive" />
                <el-option label="固定（fixed）" value="fixed" />
                <el-option label="线性（linear）" value="linear" />
              </el-select>
            </el-form-item>
            <el-form-item label="时间衰减因子">
              <el-slider v-model="config.time_decay_factor" :min="0" :max="1" :step="0.01" show-input style="max-width: 320px" data-test="decay-factor" />
            </el-form-item>
            <el-form-item label="半衰期（天）">
              <el-input-number v-model="config.half_life_days" :min="1" :max="3650" data-test="decay-halflife" />
            </el-form-item>
            <el-form-item label="情感权重">
              <el-slider v-model="config.emotion_weight" :min="0" :max="2" :step="0.1" show-input style="max-width: 320px" data-test="decay-emotion" />
            </el-form-item>
            <el-form-item label="频率权重">
              <el-slider v-model="config.frequency_weight" :min="0" :max="2" :step="0.1" show-input style="max-width: 320px" data-test="decay-frequency" />
            </el-form-item>
            <el-form-item label="租户">
              <el-tag size="small" effect="plain" data-test="decay-tenant">{{ config.tenant_id || 'default' }}</el-tag>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" data-test="decay-save" @click="save">保存配置</el-button>
              <el-button @click="load">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
        <el-card v-if="config.updated_at || config.created_at">
          <template #header>更新时间</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="创建时间">{{ config.created_at || '—' }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ config.updated_at || '—' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </template>
      <el-empty v-else-if="!loading" description="衰减配置加载失败或无数据" data-test="decay-empty" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/core/api/http'

interface DecayConfig {
  tenant_id: string | null
  strategy: string
  time_decay_factor: number
  half_life_days: number
  emotion_weight: number
  frequency_weight: number
  created_at: string | null
  updated_at: string | null
}

const config = ref<DecayConfig | null>(null)
const loading = ref(false)
const saving = ref(false)
const errorMsg = ref('')

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<{ code: number; message: string; data: DecayConfig }>('/memory-proxy/decay/config')
    config.value = data.data || null
  } catch (e) {
    config.value = null
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '衰减配置加载失败'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!config.value) return
  saving.value = true
  errorMsg.value = ''
  try {
    const payload = {
      strategy: config.value.strategy,
      time_decay_factor: config.value.time_decay_factor,
      half_life_days: config.value.half_life_days,
      emotion_weight: config.value.emotion_weight,
      frequency_weight: config.value.frequency_weight,
    }
    const { data } = await http.put<{ code: number; message: string; data: DecayConfig }>('/memory-proxy/decay/config', payload)
    config.value = data.data || config.value
    ElMessage.success('衰减配置已保存')
  } catch (e) {
    errorMsg.value = (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.page-title { font-size: 16px; font-weight: 600; }
.tab-hint { color: var(--ob-text-secondary); font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
</style>
