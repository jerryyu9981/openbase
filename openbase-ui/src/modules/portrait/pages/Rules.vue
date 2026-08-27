<template>
  <div>
    <!-- 错误态 -->
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="rule-error"
      @close="errorMessage = ''"
    />

    <!-- TD-13-32 规则引擎：双 Tab -->
    <el-tabs v-model="activeTab" data-test="rule-tabs">
      <!-- 画像规则 -->
      <el-tab-pane label="画像规则" name="rules">
        <div class="page-toolbar">
          <el-button type="primary" data-test="create-rule" @click="openForm()">新建规则</el-button>
        </div>
        <div v-loading="runningRuleId !== null" class="ob-table-scroll">
          <el-table :data="rules" stripe data-test="rule-table">
            <el-table-column prop="name" label="规则名" min-width="150" />
            <el-table-column prop="condition_desc" label="触发条件描述" min-width="230" show-overflow-tooltip />
            <el-table-column label="执行动作" width="120">
              <template #default="{ row }">
                <el-tag :type="actionType(row.action)" size="small">{{ row.action }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" data-test="rule-toggle" @change="toggleRule(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="210" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" data-test="run-rule" :loading="runningRuleId === row.id" @click="runRule(row)">立即执行</el-button>
                <el-button link type="primary" data-test="edit-rule" @click="openForm(row)">编辑</el-button>
                <!-- 破坏性操作：删除二次确认 -->
                <el-popconfirm :title="deleteTitle(row)" @confirm="removeRule(row.id)">
                  <template #reference><el-button link type="danger" data-test="delete-rule">删除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
            <template #empty>
              <el-empty description="暂无画像规则" :image-size="90" data-test="rule-empty" />
            </template>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 执行任务 -->
      <el-tab-pane label="执行任务" name="tasks">
        <div class="ob-table-scroll">
          <el-table :data="tasks" stripe data-test="task-table">
            <el-table-column prop="name" label="任务名" min-width="200" />
            <el-table-column prop="rule_name" label="关联规则" min-width="150" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="taskStatusType(row.status)" size="small">{{ taskStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="start_time" label="开始时间" width="160" />
            <el-table-column prop="end_time" label="结束时间" width="160" />
            <el-table-column prop="trigger_count" label="触发次数" width="100" />
            <template #empty>
              <el-empty description="暂无执行任务" :image-size="90" data-test="task-empty" />
            </template>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 新建/编辑规则 -->
    <el-dialog v-model="formVisible" :title="editingId ? '编辑规则' : '新建规则'" width="520px" data-test="rule-dialog">
      <el-form label-width="90px">
        <el-form-item label="规则名称" required>
          <el-input v-model="form.name" placeholder="如：高频用户自动打标签" data-test="rule-name-input" />
        </el-form-item>
        <el-form-item label="条件类型" required>
          <el-select v-model="form.condition_type" style="width: 100%" @change="onConditionTypeChange">
            <el-option label="行为" value="行为" />
            <el-option label="属性" value="属性" />
            <el-option label="标签" value="标签" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件字段" required>
          <el-select v-model="form.condition_field" placeholder="选择条件字段" style="width: 100%" data-test="rule-field-select">
            <el-option v-for="field in conditionFieldOptions" :key="field" :label="field" :value="field" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件值" required>
          <el-input v-model="form.condition_value" placeholder="触发阈值 / 取值，如：3 次" data-test="rule-value-input" />
        </el-form-item>
        <el-form-item label="执行动作" required>
          <el-select v-model="form.action" style="width: 100%">
            <el-option label="打标签" value="打标签" />
            <el-option label="更新属性" value="更新属性" />
            <el-option label="新建画像" value="新建画像" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" data-test="rule-submit" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface RuleRow {
  id: number
  name: string
  condition_type: string
  condition_field: string
  condition_value: string
  condition_desc: string
  action: string
  enabled: boolean
  created_at: string
}

interface RuleForm {
  name: string
  condition_type: string
  condition_field: string
  condition_value: string
  action: string
}

interface TaskRow {
  id: number
  name: string
  rule_name: string
  status: 'running' | 'success' | 'failed'
  start_time: string
  end_time: string
  trigger_count: number
}

const activeTab = ref('rules')
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const runningRuleId = ref<number | null>(null)
const errorMessage = ref('')
const form = reactive<RuleForm>({ name: '', condition_type: '行为', condition_field: '', condition_value: '', action: '打标签' })

/** 契约 mock：条件类型 -> 可选条件字段映射 */
const conditionFieldMap: Record<string, string[]> = {
  行为: ['访问页面', '点击按钮', '提交表单', '搜索关键词'],
  属性: ['年龄段', '城市', '注册渠道', '会员等级'],
  标签: ['高频用户', 'RAG', '技术型', '付费用户'],
}

const conditionFieldOptions = computed(() => conditionFieldMap[form.condition_type] ?? [])

/** 契约 mock：本地画像规则数据，不调用真实 API */
const rules = ref<RuleRow[]>([
  { id: 1, name: '高频访问自动打标签', condition_type: '行为', condition_field: '访问页面', condition_value: '10 次/周', condition_desc: '行为：访问页面 满足「10 次/周」', action: '打标签', enabled: true, created_at: '2026-07-10 10:00' },
  { id: 2, name: '会员等级自动升级', condition_type: '属性', condition_field: '会员等级', condition_value: 'Lv5', condition_desc: '属性：会员等级 满足「Lv5」', action: '更新属性', enabled: true, created_at: '2026-07-15 14:30' },
  { id: 3, name: '付费用户画像合并', condition_type: '标签', condition_field: '付费用户', condition_value: '存在', condition_desc: '标签：付费用户 满足「存在」', action: '新建画像', enabled: false, created_at: '2026-07-20 09:00' },
  { id: 4, name: '夜间活跃行为标记', condition_type: '行为', condition_field: '点击按钮', condition_value: '5 次/晚', condition_desc: '行为：点击按钮 满足「5 次/晚」', action: '打标签', enabled: true, created_at: '2026-07-25 16:45' },
])

/** 契约 mock：本地执行任务数据 */
const tasks = ref<TaskRow[]>([
  { id: 1, name: '每日定时执行-20260827', rule_name: '高频访问自动打标签', status: 'running', start_time: '2026-08-27 02:00', end_time: '—', trigger_count: 23 },
  { id: 2, name: '每日定时执行-20260826', rule_name: '高频访问自动打标签', status: 'success', start_time: '2026-08-26 02:00', end_time: '2026-08-26 02:01', trigger_count: 482 },
  { id: 3, name: '会员等级属性同步-20260825', rule_name: '会员等级自动升级', status: 'success', start_time: '2026-08-25 02:00', end_time: '2026-08-25 02:02', trigger_count: 156 },
  { id: 4, name: '画像合并批处理-20260824', rule_name: '付费用户画像合并', status: 'failed', start_time: '2026-08-24 02:00', end_time: '2026-08-24 02:00', trigger_count: 0 },
])

function actionType(action: string) {
  return { 打标签: 'success', 更新属性: 'warning', 新建画像: 'primary' }[action] || 'info'
}

function taskStatusType(status: string) {
  return { running: 'success', success: 'success', failed: 'danger' }[status] || 'info'
}

function taskStatusLabel(status: string) {
  return { running: '运行中', success: '成功', failed: '失败' }[status] || status
}

function deleteTitle(row: RuleRow) {
  return `确认删除规则「${row.name}」？删除后不可恢复`
}

function toggleRule(row: RuleRow) {
  ElMessage.success(`规则「${row.name}」已${row.enabled ? '启用' : '停用'}`)
}

function buildConditionDesc(formData: RuleForm): string {
  return `${formData.condition_type}：${formData.condition_field} 满足「${formData.condition_value}」`
}

function openForm(row?: RuleRow) {
  errorMessage.value = ''
  editingId.value = row?.id ?? null
  form.name = row?.name ?? ''
  form.condition_type = row?.condition_type ?? '行为'
  form.condition_field = row?.condition_field ?? ''
  form.condition_value = row?.condition_value ?? ''
  form.action = row?.action ?? '打标签'
  formVisible.value = true
}

function onConditionTypeChange() {
  form.condition_field = ''
}

function saveRule() {
  const name = form.name.trim()
  if (!name) {
    ElMessage.warning('请输入规则名称')
    return
  }
  if (!form.condition_field) {
    ElMessage.warning('请选择条件字段')
    return
  }
  if (!form.condition_value.trim()) {
    ElMessage.warning('请输入条件值')
    return
  }
  const duplicated = rules.value.some((rule) => rule.name === name && rule.id !== editingId.value)
  if (duplicated) {
    errorMessage.value = `规则名称「${name}」已存在，请更换名称`
    return
  }
  errorMessage.value = ''
  if (editingId.value) {
    const target = rules.value.find((rule) => rule.id === editingId.value)
    if (target) {
      target.name = name
      target.condition_type = form.condition_type
      target.condition_field = form.condition_field
      target.condition_value = form.condition_value.trim()
      target.condition_desc = buildConditionDesc(form)
      target.action = form.action
      ElMessage.success('规则已更新')
    }
  } else {
    rules.value.push({
      id: Date.now(),
      name,
      condition_type: form.condition_type,
      condition_field: form.condition_field,
      condition_value: form.condition_value.trim(),
      condition_desc: buildConditionDesc(form),
      action: form.action,
      enabled: true,
      created_at: formatNow(),
    })
    ElMessage.success('规则已创建')
  }
  formVisible.value = false
}

function removeRule(id: number) {
  rules.value = rules.value.filter((rule) => rule.id !== id)
  ElMessage.success('规则已删除')
}

/** 立即执行：模拟生成一条执行任务（运行中 -> 成功） */
function runRule(row: RuleRow) {
  if (!row.enabled) {
    ElMessage.warning('该规则已停用，请先启用后再执行')
    return
  }
  if (runningRuleId.value !== null) {
    ElMessage.warning('已有规则正在执行，请稍候')
    return
  }
  runningRuleId.value = row.id
  const taskId = Date.now()
  tasks.value.unshift({
    id: taskId,
    name: `手动触发-${row.name}`,
    rule_name: row.name,
    status: 'running',
    start_time: formatNow(),
    end_time: '—',
    trigger_count: 0,
  })
  ElMessage.info(`规则「${row.name}」已触发执行`)
  window.setTimeout(() => {
    const task = tasks.value.find((item) => item.id === taskId)
    if (task) {
      task.status = 'success'
      task.end_time = formatNow()
      task.trigger_count = Math.floor(100 + Math.random() * 900)
    }
    runningRuleId.value = null
    ElMessage.success(`规则「${row.name}」执行完成，命中 ${task?.trigger_count ?? 0} 人`)
  }, 800)
}

function formatNow(): string {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.mb-16 { margin-bottom: 16px; }
</style>
