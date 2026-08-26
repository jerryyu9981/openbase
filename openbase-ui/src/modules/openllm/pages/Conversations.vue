<template>
  <div>
    <div class="page-toolbar">
      <el-input v-model="keyword" placeholder="搜索对话标题" clearable style="width: 240px" data-test="conversation-search" />
      <el-select v-model="modelFilter" placeholder="模型筛选" clearable style="width: 160px">
        <el-option label="gpt-4o" value="gpt-4o" />
        <el-option label="qwen2.5-7b" value="qwen2.5-7b" />
      </el-select>
      <el-button data-test="export-conversations" @click="exportJson">导出（JSON）</el-button>
      <el-popconfirm title="确认批量删除选中对话？" @confirm="batchDelete">
        <template #reference>
          <el-button type="danger" plain :disabled="selection.length === 0">批量删除</el-button>
        </template>
      </el-popconfirm>
    </div>
    <div class="ob-table-scroll">
      <el-table :data="conversations" stripe data-test="conversation-table" @selection-change="(rows: any[]) => (selection = rows)">
        <el-table-column type="selection" width="44" />
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column prop="model" label="模型" width="130" />
        <el-table-column prop="messages" label="消息数" width="90" />
        <el-table-column prop="started_at" label="开始时间" width="170" />
        <el-table-column label="Token 消耗" width="110">
          <template #default="{ row }">{{ row.tokens ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
            <el-popconfirm title="确认删除该对话？" @confirm="remove(row.id)">
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface Conversation { id: number; title: string; model: string; messages: number; started_at: string; tokens?: number }

const keyword = ref('')
const modelFilter = ref('')
const selection = ref<Conversation[]>([])
const conversations = ref<Conversation[]>([
  { id: 1, title: 'RAG 知识库测试对话', model: 'qwen2.5-7b', messages: 12, started_at: '2026-08-25 10:20', tokens: 3842 },
  { id: 2, title: '多轮需求讨论', model: 'gpt-4o', messages: 8, started_at: '2026-08-25 09:10', tokens: 5210 },
  { id: 3, title: 'SQL 生成练习', model: 'gpt-4o', messages: 5, started_at: '2026-08-24 16:45', tokens: 2980 },
])

function openDetail(row: Conversation) {
  ElMessage.info(`对话详情（完整内容+Token 消耗）：${row.title}`)
}
function remove(id: number) {
  conversations.value = conversations.value.filter((c) => c.id !== id)
  ElMessage.success('对话已删除')
}
function batchDelete() {
  const ids = selection.value.map((s) => s.id)
  conversations.value = conversations.value.filter((c) => !ids.includes(c.id))
  ElMessage.success(`已删除 ${ids.length} 条对话`)
}
function exportJson() {
  const data = JSON.stringify(conversations.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `conversations-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${conversations.value.length} 条对话`)
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
</style>
