<template>
  <div class="dps-rate-limit">
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card header="限流规则" data-test="rl-card">
          <div class="page-toolbar">
            <el-button type="primary" size="small" data-test="rl-new" @click="openCreate">新建规则</el-button>
          </div>
          <div class="ob-table-scroll">
            <el-table :data="rules" stripe empty-text="暂无规则" data-test="rl-table">
              <el-table-column prop="name" label="规则名" min-width="140" />
              <el-table-column prop="tenant" label="租户" width="110" />
              <el-table-column prop="qps" label="QPS" width="80" />
              <el-table-column prop="concurrency" label="并发" width="80" />
              <el-table-column prop="window" label="窗口" width="80" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" data-test="rl-toggle" @change="toggle(row)" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
                  <el-popconfirm title="确认删除该规则？" @confirm="remove(row.id)">
                    <template #reference>
                      <el-button link type="danger" size="small">删除</el-button>
                    </template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card header="租户配额" class="mb-16" data-test="rl-quota-card">
          <el-table :data="quotas" size="small" empty-text="暂无配额">
            <el-table-column prop="tenant" label="租户" width="90" />
            <el-table-column prop="limit" label="配额" width="90" />
            <el-table-column prop="used" label="已用" width="80" />
          </el-table>
        </el-card>
        <el-card header="熔断状态" data-test="rl-circuit-card">
          <el-table :data="circuits" size="small" empty-text="无熔断实例">
            <el-table-column prop="target" label="目标" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.open ? 'danger' : 'success'" size="small" data-test="rl-circuit-badge">
                  {{ row.open ? '熔断' : '正常' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button v-if="row.open" link type="primary" size="small" data-test="rl-recover" @click="recover(row)">恢复</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 规则弹窗 -->
    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑规则' : '新建规则'" width="480px" data-test="rl-dialog">
      <el-form :model="form" label-width="70px">
        <el-form-item label="规则名">
          <el-input v-model="form.name" data-test="rl-name" />
        </el-form-item>
        <el-form-item label="租户">
          <el-select v-model="form.tenant" style="width: 100%">
            <el-option v-for="t in ['全部', 'AI 平台部', '模型组']" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="QPS">
          <el-input-number v-model="form.qps" :min="1" :max="100000" />
        </el-form-item>
        <el-form-item label="并发">
          <el-input-number v-model="form.concurrency" :min="1" :max="10000" />
        </el-form-item>
        <el-form-item label="窗口">
          <el-select v-model="form.window" style="width: 100%">
            <el-option label="1 秒" value="1s" />
            <el-option label="1 分钟" value="1m" />
            <el-option label="1 小时" value="1h" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" data-test="rl-save" @click="save">保存并即时生效</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface RateRule {
  id: number
  name: string
  tenant: string
  qps: number
  concurrency: number
  window: string
  enabled: boolean
}

const rules = ref<RateRule[]>([
  { id: 1, name: '全局默认限流', tenant: '全部', qps: 500, concurrency: 100, window: '1s', enabled: true },
  { id: 2, name: '模型组高优', tenant: '模型组', qps: 2000, concurrency: 300, window: '1s', enabled: true },
  { id: 3, name: 'API 批量防刷', tenant: 'AI 平台部', qps: 100, concurrency: 20, window: '1m', enabled: false },
])

const quotas = ref([
  { tenant: 'AI 平台部', limit: '5,000,000', used: '2,340,000' },
  { tenant: '模型组', limit: '2,000,000', used: '1,890,000' },
])

const circuits = ref([
  { target: 'openllm/providers/openai', open: true },
  { target: 'openrag/kb/search', open: false },
])

const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const form = ref({ name: '', tenant: '全部', qps: 100, concurrency: 10, window: '1s' })

function openCreate() {
  editingId.value = null
  form.value = { name: '', tenant: '全部', qps: 100, concurrency: 10, window: '1s' }
  dialogOpen.value = true
}

function openEdit(row: RateRule) {
  editingId.value = row.id
  form.value = { name: row.name, tenant: row.tenant, qps: row.qps, concurrency: row.concurrency, window: row.window }
  dialogOpen.value = true
}

function save() {
  if (!form.value.name) {
    ElMessage.warning('请填写规则名')
    return
  }
  if (editingId.value) {
    const r = rules.value.find((x) => x.id === editingId.value)
    if (r) Object.assign(r, form.value)
    ElMessage.success('规则已更新并即时生效')
  } else {
    const id = Math.max(0, ...rules.value.map((r) => r.id)) + 1
    rules.value.push({ id, ...form.value, enabled: true })
    ElMessage.success('规则已创建并即时生效')
  }
  dialogOpen.value = false
}

function toggle(row: RateRule) {
  ElMessage.success(row.enabled ? '限流规则已启用' : '限流规则已停用')
}

function recover(row: { target: string; open: boolean }) {
  row.open = false
  ElMessage.success(`熔断已手动恢复：${row.target}`)
}

function remove(id: number) {
  rules.value = rules.value.filter((r) => r.id !== id)
  ElMessage.success('规则已删除')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
</style>
