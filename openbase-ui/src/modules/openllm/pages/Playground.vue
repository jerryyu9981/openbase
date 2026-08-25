<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="prompt" placeholder="输入对话内容，回车发送（流式 SSE）" data-test="playground-input" @keyup.enter="send" />
      <el-button type="primary" data-test="playground-send" :loading="streaming" @click="send">发送</el-button>
    </div>
    <div class="chat-panel">
      <div v-for="(m, i) in messages" :key="i" class="chat-msg" :class="m.role">
        <span class="chat-role">{{ m.role === 'user' ? '我' : '模型' }}</span>
        <div class="chat-content">{{ m.content }}</div>
      </div>
      <el-empty v-if="messages.length === 0" description="开始一段对话调试" :image-size="60" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface ChatMessage { role: 'user' | 'assistant'; content: string }

const prompt = ref('')
const streaming = ref(false)
const messages = ref<ChatMessage[]>([])

function send() {
  const text = prompt.value.trim()
  if (!text) return
  messages.value.push({ role: 'user', content: text })
  prompt.value = ''
  streaming.value = true
  // 演示：模拟流式输出（真实接入经 /api/v1/proxy/openllm/chat/stream SSE 透传）
  setTimeout(() => {
    messages.value.push({ role: 'assistant', content: `（演示响应）收到：${text}\n生产环境经 openbase 代理 SSE 流式返回。` })
    streaming.value = false
  }, 500)
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.chat-panel { min-height: 360px; border: 1px solid var(--ob-border); border-radius: var(--ob-radius-md); padding: 16px; background: var(--ob-surface); }
.chat-msg { margin-bottom: 12px; }
.chat-role { font-weight: 600; font-size: 13px; color: var(--ob-text-secondary); }
.chat-content { margin-top: 4px; white-space: pre-wrap; line-height: 1.6; }
</style>
