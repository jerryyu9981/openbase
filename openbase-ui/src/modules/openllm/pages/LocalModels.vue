<template>
  <div>
    <div class="page-toolbar">
      <el-button type="primary" data-test="pull-model" :loading="pulling" @click="pullModel">拉取新模型（Ollama）</el-button>
    </div>
    <el-row :gutter="16">
      <el-col :xs="24" :sm="12" :lg="8" v-for="m in models" :key="m.name">
        <el-card class="model-card">
          <h3>{{ m.name }}</h3>
          <p class="meta">运行时长：{{ m.runtime }} · GPU 占用：{{ m.gpu }}</p>
          <div>
            <el-button size="small" :type="m.running ? 'danger' : 'success'" @click="toggle(m.name)">
              {{ m.running ? '停止' : '启动' }}
            </el-button>
            <el-popconfirm title="确认删除该本地模型？" @confirm="remove(m.name)">
              <template #reference><el-button size="small" type="danger" plain>删除</el-button></template>
            </el-popconfirm>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface LocalModel { name: string; running: boolean; runtime: string; gpu: string }

const models = ref<LocalModel[]>([
  { name: 'qwen2.5-7b', running: true, runtime: '2h 15m', gpu: '38%' },
  { name: 'llama3.1-8b', running: false, runtime: '-', gpu: '-' },
])
const pulling = ref(false)

function toggle(name: string) {
  const m = models.value.find((x) => x.name === name)
  if (m) { m.running = !m.running; ElMessage.success(`${m.running ? '已启动' : '已停止'}：${name}`) }
}
function remove(name: string) {
  models.value = models.value.filter((x) => x.name !== name)
  ElMessage.success(`已删除：${name}`)
}
function pullModel() {
  pulling.value = true
  setTimeout(() => { pulling.value = false; ElMessage.success('模型拉取任务已提交') }, 600)
}
</script>

<style scoped>
.page-toolbar { margin-bottom: 16px; }
.model-card { margin-bottom: 16px; }
.model-card h3 { margin: 0 0 8px; }
.meta { color: var(--ob-text-secondary); font-size: 13px; }
</style>
