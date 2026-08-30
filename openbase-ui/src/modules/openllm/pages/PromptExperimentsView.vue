<template>
  <div class="prompt-experiments">
    <div class="page-toolbar">
      <el-button type="primary" data-test="pe-new" @click="openCreate">创建实验</el-button>
    </div>
    <el-card header="Prompt 实验列表" data-test="pe-card">
      <div class="ob-table-scroll">
        <el-table :data="experiments" stripe empty-text="暂无实验" data-test="pe-table">
          <el-table-column prop="name" label="实验名称" min-width="160" />
          <el-table-column prop="template" label="关联模板" width="140" />
          <el-table-column label="变体数" width="90">
            <template #default="{ row }">{{ row.variants.length }}</template>
          </el-table-column>
          <el-table-column label="流量分配" width="110">
            <template #default="{ row }">{{ row.traffic }}%</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-switch v-model="row.running" data-test="pe-toggle" @change="toggle(row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button link type="primary" size="small" data-test="pe-report" @click="openReport(row)">报表</el-button>
              <el-popconfirm title="确认删除该实验？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 创建 -->
    <el-dialog v-model="dialogOpen" title="创建 Prompt 实验" width="560px" data-test="pe-dialog">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称">
          <el-input v-model="form.name" data-test="pe-name" />
        </el-form-item>
        <el-form-item label="关联模板">
          <el-select v-model="form.template" style="width: 100%">
            <el-option v-for="t in ['通用客服助手', '代码审查助手', '文章摘要模板']" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="变体集">
          <div class="variant-list">
            <div v-for="(v, idx) in form.variants" :key="idx" class="variant-row">
              <el-input v-model="v.name" placeholder="变体名称" style="width: 130px" />
              <el-input v-model="v.content" placeholder="变体内容" style="flex: 1" data-test="pe-variant" />
              <el-button link type="danger" :disabled="form.variants.length <= 1" @click="form.variants.splice(idx, 1)">删除</el-button>
            </div>
            <el-button size="small" data-test="pe-variant-add" @click="form.variants.push({ name: '', content: '' })">+ 添加变体</el-button>
          </div>
        </el-form-item>
        <el-form-item label="流量分配">
          <el-input-number v-model="form.traffic" :min="1" :max="100" /> %
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" data-test="pe-save" @click="save">创建</el-button>
      </template>
    </el-dialog>

    <!-- 报表 -->
    <el-drawer v-model="reportOpen" title="实验报表" size="480px" data-test="pe-report-drawer">
      <el-date-picker v-model="reportRange" type="daterange" range-separator="至" size="small" data-test="pe-report-range" @change="renderReport" />
      <div ref="reportRef" class="report-chart" />
      <el-table :data="reportTable" size="small" class="mt-8">
        <el-table-column prop="variant" label="变体" />
        <el-table-column prop="successRate" label="成功率" width="90" />
        <el-table-column prop="quality" label="质量分" width="90" />
        <el-table-column prop="latency" label="延迟(ms)" width="90" />
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

interface Variant { name: string; content: string }
interface Experiment {
  id: number
  name: string
  template: string
  variants: Variant[]
  traffic: number
  running: boolean
}

const experiments = ref<Experiment[]>([
  { id: 1, name: '客服开场白优化', template: '通用客服助手', variants: [{ name: 'A-简洁', content: '...' }, { name: 'B-详细', content: '...' }], traffic: 50, running: true },
  { id: 2, name: '代码审查温度对比', template: '代码审查助手', variants: [{ name: 'A-低温', content: '...' }, { name: 'B-高温', content: '...' }], traffic: 30, running: false },
])

const dialogOpen = ref(false)
const form = ref({ name: '', template: '通用客服助手', traffic: 50, variants: [{ name: '', content: '' }] as Variant[] })
const reportOpen = ref(false)
const reportRange = ref<[string, string] | null>(null)
const reportRef = ref<HTMLDivElement>()
const reportTable = ref([
  { variant: 'A-简洁', successRate: '96%', quality: '8.2', latency: '412' },
  { variant: 'B-详细', successRate: '91%', quality: '8.8', latency: '628' },
])

function openCreate() {
  form.value = { name: '', template: '通用客服助手', traffic: 50, variants: [{ name: '', content: '' }] }
  dialogOpen.value = true
}

function save() {
  if (!form.value.name) {
    ElMessage.warning('请填写实验名称')
    return
  }
  const id = Math.max(0, ...experiments.value.map((e) => e.id)) + 1
  experiments.value.push({ id, name: form.value.name, template: form.value.template, variants: form.value.variants.filter((v) => v.name), traffic: form.value.traffic, running: false })
  ElMessage.success('实验已创建')
  dialogOpen.value = false
}

function toggle(row: Experiment) {
  ElMessage.success(row.running ? '实验已启动' : '实验已停止')
}

function openReport(row: Experiment) {
  void row
  reportOpen.value = true
  nextTick(renderReport)
}

function renderReport() {
  if (!reportRef.value) return
  const chart = echarts.init(reportRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['成功率', '质量分'] },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: ['A-简洁', 'B-详细'] },
    yAxis: [
      { type: 'value', name: '成功率%', max: 100 },
      { type: 'value', name: '质量分', max: 10 },
    ],
    series: [
      { name: '成功率', type: 'bar', data: [96, 91], yAxisIndex: 0 },
      { name: '质量分', type: 'line', data: [8.2, 8.8], yAxisIndex: 1 },
    ],
  })
}

function remove(id: number) {
  experiments.value = experiments.value.filter((e) => e.id !== id)
  ElMessage.success('实验已删除')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.variant-row { display: flex; gap: 8px; margin-bottom: 8px; }
.report-chart { height: 260px; margin-top: 8px; }
.mt-8 { margin-top: 8px; }
</style>
