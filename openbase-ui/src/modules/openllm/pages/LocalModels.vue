<template>
  <div>
    <div class="page-toolbar">
      <el-button type="primary" data-test="pull-model" :loading="pulling" @click="pullModel">拉取新模型（Ollama）</el-button>
      <el-button data-test="open-repo" @click="repoVisible = true">模型仓库</el-button>
      <el-button data-test="open-gpu" @click="gpuVisible = true">GPU 调度</el-button>
    </div>
    <el-row :gutter="16">
      <el-col v-for="m in models" :key="m.name" :xs="24" :sm="12" :lg="8">
        <el-card class="model-card">
          <h3>{{ m.name }}</h3>
          <p class="meta">大小：{{ m.size }} · 运行时长：{{ m.runtime }} · GPU 占用：{{ m.gpu }}</p>
          <div>
            <el-button size="small" :type="m.running ? 'danger' : 'success'" @click="toggle(m.name)">
              {{ m.running ? '停止' : '启动' }}
            </el-button>
            <el-button size="small" :loading="m.updating" @click="updateModel(m)">更新</el-button>
            <el-popconfirm title="确认删除该本地模型？" @confirm="remove(m.name)">
              <template #reference><el-button size="small" type="danger" plain>删除</el-button></template>
            </el-popconfirm>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="repoVisible" title="模型仓库" width="520px">
      <el-table :data="repoModels" max-height="360">
        <el-table-column prop="name" label="模型" />
        <el-table-column prop="size" label="大小" width="100" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="installFromRepo(row.name)">安装</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="repoVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="gpuVisible" title="GPU 调度" width="520px">
      <el-table :data="gpus" max-height="360">
        <el-table-column prop="device" label="设备" width="140" />
        <el-table-column prop="utilization" label="利用率" width="100" />
        <el-table-column prop="memory" label="显存" />
        <el-table-column prop="temperature" label="温度" width="90" />
        <el-table-column label="调度" width="100">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="(v: boolean) => toggleGpu(row, v)" />
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="gpuVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface LocalModel { name: string; running: boolean; runtime: string; gpu: string; size: string; updating?: boolean }
interface RepoModel { name: string; size: string }
interface GpuCard { device: string; utilization: string; memory: string; temperature: string; enabled: boolean }

const models = ref<LocalModel[]>([
  { name: 'qwen2.5-7b', running: true, runtime: '2h 15m', gpu: '38%', size: '4.7GB' },
  { name: 'llama3.1-8b', running: false, runtime: '-', gpu: '-', size: '4.9GB' },
])
const repoModels = ref<RepoModel[]>([
  { name: 'qwen3-8b', size: '5.1GB' },
  { name: 'deepseek-r1-7b', size: '4.8GB' },
  { name: 'gemma2-9b', size: '5.6GB' },
])
const gpus = ref<GpuCard[]>([
  { device: 'GPU 0 (NVIDIA A100)', utilization: '42%', memory: '24/80GB', temperature: '58°C', enabled: true },
  { device: 'GPU 1 (NVIDIA A100)', utilization: '12%', memory: '8/80GB', temperature: '44°C', enabled: true },
])
const pulling = ref(false)
const repoVisible = ref(false)
const gpuVisible = ref(false)

function toggle(name: string) {
  const m = models.value.find((x) => x.name === name)
  if (m) { m.running = !m.running; ElMessage.success(`${m.running ? '已启动' : '已停止'}：${name}`) }
}
function updateModel(m: LocalModel) {
  m.updating = true
  setTimeout(() => {
    m.updating = false
    m.size = m.size
    ElMessage.success(`已更新：${m.name}（版本已同步）`)
  }, 600)
}
function remove(name: string) {
  models.value = models.value.filter((x) => x.name !== name)
  ElMessage.success(`已删除：${name}`)
}
function pullModel() {
  pulling.value = true
  setTimeout(() => { pulling.value = false; ElMessage.success('模型拉取任务已提交') }, 600)
}
function installFromRepo(name: string) {
  models.value.push({ name, running: false, runtime: '-', gpu: '-', size: '4.5GB' })
  ElMessage.success(`安装任务已提交：${name}`)
}
function toggleGpu(row: GpuCard, enabled: boolean) {
  row.enabled = enabled
  ElMessage.success(`GPU 调度已${enabled ? '启用' : '禁用'}：${row.device}`)
}
</script>

<style scoped>
.page-toolbar { margin-bottom: 16px; display: flex; gap: 8px; flex-wrap: wrap; }
.model-card { margin-bottom: 16px; }
.model-card h3 { margin: 0 0 8px; }
.meta { color: var(--ob-text-secondary); font-size: 13px; }
</style>
