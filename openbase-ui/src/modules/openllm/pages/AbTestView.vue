<template>
  <div class="ab-test-page">
    <div class="page-toolbar">
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 130px" data-test="ab-status-filter">
        <el-option label="运行中" value="running" />
        <el-option label="已停止" value="stopped" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-button type="primary" data-test="ab-new" @click="openCreate">创建实验</el-button>
    </div>

    <el-card header="A/B 测试实验" data-test="ab-card">
      <div class="ob-table-scroll">
        <el-table :data="filteredRows" stripe empty-text="暂无实验" data-test="ab-table">
          <el-table-column prop="name" label="实验名称" min-width="160" />
          <el-table-column prop="version" label="版本" width="90" />
          <el-table-column label="流量分配" width="130">
            <template #default="{ row }">
              <div class="traffic-bar">
                <span class="traffic-a">{{ row.groupA }}%</span>
                <el-progress :percentage="row.groupA" :show-text="false" :stroke-width="10" color="#1677FF" />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small" data-test="ab-status">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240">
            <template #default="{ row }">
              <el-button v-if="row.status !== 'running'" link type="success" size="small" data-test="ab-start" @click="setStatus(row, 'running')">启动</el-button>
              <el-button v-if="row.status === 'running'" link type="warning" size="small" data-test="ab-stop" @click="setStatus(row, 'stopped')">停止</el-button>
              <el-button v-if="row.status !== 'archived'" link type="info" size="small" data-test="ab-archive" @click="setStatus(row, 'archived')">归档</el-button>
              <el-button link type="primary" size="small" data-test="ab-detail" @click="openDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 创建 -->
    <el-dialog v-model="dialogOpen" title="创建 A/B 实验" width="520px" data-test="ab-dialog">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称">
          <el-input v-model="form.name" data-test="ab-name" />
        </el-form-item>
        <el-form-item label="对比对象">
          <el-select v-model="form.subject" style="width: 100%">
            <el-option label="模型" value="model" />
            <el-option label="Prompt 模板" value="prompt" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本 A">
          <el-input v-model="form.groupA" placeholder="版本 A 标识" />
        </el-form-item>
        <el-form-item label="版本 B">
          <el-input v-model="form.groupB" placeholder="版本 B 标识" />
        </el-form-item>
        <el-form-item label="流量占比 A">
          <el-input-number v-model="form.ratioA" :min="1" :max="99" /> %
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" data-test="ab-save" @click="save">创建</el-button>
      </template>
    </el-dialog>

    <!-- 详情 -->
    <el-drawer v-model="detailOpen" title="实验详情" size="480px" data-test="ab-detail-drawer">
      <template v-if="currentDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="名称" :span="2">{{ currentDetail.name }}</el-descriptions-item>
          <el-descriptions-item label="状态" :span="2">{{ statusLabel(currentDetail.status) }}</el-descriptions-item>
          <el-descriptions-item label="流量 A">{{ currentDetail.groupA }}%</el-descriptions-item>
          <el-descriptions-item label="流量 B">{{ 100 - currentDetail.groupA }}%</el-descriptions-item>
        </el-descriptions>
        <div class="metric-title">分组指标</div>
        <el-table :data="detailMetrics" size="small">
          <el-table-column prop="metric" label="指标" />
          <el-table-column prop="groupA" label="A" width="90" />
          <el-table-column prop="groupB" label="B" width="90" />
          <el-table-column prop="delta" label="变化" width="100">
            <template #default="{ row }">
              <el-tag :type="row.delta.startsWith('+') ? 'success' : 'danger'" size="small">{{ row.delta }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

type AbStatus = 'running' | 'stopped' | 'archived'

interface AbExperiment {
  id: number
  name: string
  version: number
  groupA: number
  status: AbStatus
}

const experiments = ref<AbExperiment[]>([
  { id: 1, name: '客服模型 A/B', version: 3, groupA: 50, status: 'running' },
  { id: 2, name: '摘要提示词灰度', version: 1, groupA: 70, status: 'stopped' },
  { id: 3, name: '代码模型切换验证', version: 2, groupA: 30, status: 'archived' },
])

const statusFilter = ref('')
const dialogOpen = ref(false)
const form = ref({ name: '', subject: 'model', groupA: '', groupB: '', ratioA: 50 })
const detailOpen = ref(false)
const currentDetail = ref<AbExperiment | null>(null)

const detailMetrics = ref([
  { metric: '成功率', groupA: '95%', groupB: '92%', delta: '+3.0%' },
  { metric: '平均延迟', groupA: '420ms', groupB: '510ms', delta: '-17.6%' },
  { metric: '用户满意度', groupA: '8.5', groupB: '8.1', delta: '+0.4' },
])

const filteredRows = computed(() =>
  statusFilter.value ? experiments.value.filter((e) => e.status === statusFilter.value) : experiments.value,
)

function openCreate() {
  form.value = { name: '', subject: 'model', groupA: '', groupB: '', ratioA: 50 }
  dialogOpen.value = true
}

function save() {
  if (!form.value.name) {
    ElMessage.warning('请填写实验名称')
    return
  }
  const id = Math.max(0, ...experiments.value.map((e) => e.id)) + 1
  experiments.value.push({ id, name: form.value.name, version: 1, groupA: form.value.ratioA, status: 'stopped' })
  ElMessage.success('实验已创建')
  dialogOpen.value = false
}

function statusType(s: AbStatus) {
  return { running: 'success', stopped: 'warning', archived: 'info' }[s] as 'success' | 'warning' | 'info'
}

function statusLabel(s: AbStatus) {
  return { running: '运行中', stopped: '已停止', archived: '已归档' }[s]
}

function setStatus(row: AbExperiment, status: AbStatus) {
  row.status = status
  const msg = { running: '实验已启动', stopped: '实验已停止', archived: '实验已归档' }[status]
  ElMessage.success(msg)
}

function openDetail(row: AbExperiment) {
  currentDetail.value = row
  detailOpen.value = true
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.traffic-bar { display: flex; align-items: center; gap: 8px; }
.traffic-a { font-size: 12px; color: #1677FF; width: 34px; }
.metric-title { font-weight: 600; margin: 16px 0 8px; }
</style>
