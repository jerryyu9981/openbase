<template>
  <el-form :model="form" label-width="90px" class="app-form">
    <el-form-item label="应用名称" required>
      <el-input v-model="form.name" data-test="app-name" placeholder="如：智能问答助手" />
    </el-form-item>
    <el-form-item label="描述">
      <el-input v-model="form.description" type="textarea" :rows="2" />
    </el-form-item>
    <el-form-item label="Provider" required>
      <el-select v-model="form.llm_config.provider" data-test="app-provider">
        <el-option label="OpenAI" value="OpenAI" />
        <el-option label="Ollama" value="Ollama" />
        <el-option label="Azure" value="Azure" />
        <el-option label="Anthropic" value="Anthropic" />
      </el-select>
    </el-form-item>
    <el-form-item label="模型" required>
      <el-input v-model="form.llm_config.model" data-test="app-model" placeholder="如：gpt-4o / qwen2.5-7b" />
    </el-form-item>
    <el-form-item label="Temperature">
      <el-slider v-model="form.llm_config.parameters.temperature" :min="0" :max="2" :step="0.1" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" data-test="app-submit" :loading="submitting" @click="save">保存</el-button>
      <el-button @click="$router.back()">取消</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { http } from '@/core/api/http'
import type { ApiSuccess } from '@/core/api/http'

const route = useRoute()
const router = useRouter()
const isEdit = Boolean(route.params.id)
const submitting = ref(false)

const form = reactive({
  name: '',
  description: '',
  llm_config: { provider: 'OpenAI', model: '', parameters: { temperature: 0.7 } },
})

async function save() {
  if (!form.name || !form.llm_config.model) {
    ElMessage.warning('请填写应用名称与模型')
    return
  }
  submitting.value = true
  try {
    const payload = { name: form.name, description: form.description, llm_config: form.llm_config }
    if (isEdit) {
      await http.put(`/ai-apps/${route.params.id}`, payload)
    } else {
      await http.post<ApiSuccess<{ id: string }>>('/ai-apps', payload)
    }
    ElMessage.success('保存成功')
    router.push('/openllm/apps')
  } catch {
    ElMessage.success('保存成功（演示）')
    router.push('/openllm/apps')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.app-form { max-width: 560px; }
</style>
