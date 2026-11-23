<template>
  <el-form label-width="96px" size="small" data-test="schedule-editor">
    <el-form-item label="数据源 ID">
      <el-input v-model="form.datasource_id" placeholder="DPS 数据源 ID" data-test="schedule-datasource" />
    </el-form-item>
    <el-form-item label="调度类型">
      <el-radio-group v-model="form.schedule_type" data-test="schedule-type">
        <el-radio-button label="cron">cron</el-radio-button>
        <el-radio-button label="interval">固定间隔</el-radio-button>
      </el-radio-group>
    </el-form-item>
    <el-form-item v-if="form.schedule_type === 'cron'" label="cron">
      <CronInput v-model="form.cron_expr" />
    </el-form-item>
    <el-form-item v-else label="间隔（秒）">
      <el-input-number v-model="form.interval_seconds" :min="60" :step="60" data-test="schedule-interval" />
    </el-form-item>
    <el-form-item label="启用">
      <el-switch v-model="form.enabled" data-test="schedule-enabled" />
    </el-form-item>
    <el-form-item label="失败上限">
      <el-input-number v-model="form.max_failures" :min="1" :max="20" data-test="schedule-max-failures" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" size="small" :loading="saving" data-test="schedule-save" @click="save">
        {{ editingId ? '保存修改' : '创建调度' }}
      </el-button>
      <el-button size="small" @click="reset">重置</el-button>
    </el-form-item>
    <el-alert v-if="error" type="error" show-icon :closable="false" :title="error" />
  </el-form>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import CronInput from './CronInput.vue'
import { dpsApi, type DpsSchedule, type DpsScheduleInput } from '@/core/api/dps'
import { describeError } from '@/core/api/error'

const props = defineProps<{ schedule?: DpsSchedule | null }>()
const emit = defineEmits<{ (event: 'saved'): void }>()

const emptyForm = (): Required<Pick<DpsScheduleInput, 'datasource_id' | 'schedule_type' | 'cron_expr' | 'interval_seconds' | 'enabled' | 'max_failures'>> => ({
  datasource_id: '',
  schedule_type: 'cron',
  cron_expr: '0 3 * * *',
  interval_seconds: 3600,
  enabled: false,
  max_failures: 3,
})

const form = ref(emptyForm())
const editingId = ref('')
const saving = ref(false)
const error = ref('')

function loadSchedule(schedule?: DpsSchedule | null) {
  if (!schedule) {
    editingId.value = ''
    form.value = emptyForm()
    return
  }
  editingId.value = schedule.id
  form.value = {
    datasource_id: String(schedule.datasource_id || ''),
    schedule_type: (schedule.schedule_type as 'cron' | 'interval') || 'cron',
    cron_expr: String(schedule.cron_expr || ''),
    interval_seconds: Number(schedule.interval_seconds || 3600),
    enabled: Boolean(schedule.enabled),
    max_failures: Number(schedule.max_failures || 3),
  }
}

function reset() {
  loadSchedule(props.schedule)
  error.value = ''
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    const payload: DpsScheduleInput = {
      datasource_id: form.value.datasource_id || undefined,
      schedule_type: form.value.schedule_type,
      cron_expr: form.value.schedule_type === 'cron' ? form.value.cron_expr : undefined,
      interval_seconds: form.value.schedule_type === 'interval' ? form.value.interval_seconds : undefined,
      enabled: form.value.enabled,
      max_failures: form.value.max_failures,
    }
    if (editingId.value) {
      await dpsApi.updateSchedule(editingId.value, payload)
    } else {
      await dpsApi.createSchedule(payload)
    }
    loadSchedule(null)
    emit('saved')
  } catch (err) {
    error.value = describeError(err).detail || '保存失败'
  } finally {
    saving.value = false
  }
}

watch(() => props.schedule, loadSchedule, { immediate: true })
</script>
