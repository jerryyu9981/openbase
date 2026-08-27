<template>
  <div v-loading="pageLoading" element-loading-text="加载系统配置中…">
    <el-alert
      v-if="alertMessage"
      :title="alertMessage"
      :type="alertType"
      show-icon
      closable
      class="mb-16"
      @close="alertMessage = ''"
    />

    <!-- 检索配置 -->
    <el-card header="检索配置" class="mb-16">
      <el-form ref="configFormRef" :model="config" :rules="configRules" label-width="170px" class="config-form">
        <el-form-item label="默认分块大小" prop="chunk_size">
          <el-input-number v-model="config.chunk_size" :min="100" :max="5000" :step="100" style="width: 200px" data-test="chunk-size" />
          <span class="form-hint">字符数，范围 100 - 5000</span>
        </el-form-item>
        <el-form-item label="检索 TopK" prop="top_k">
          <el-input-number v-model="config.top_k" :min="1" :max="50" :step="1" style="width: 200px" data-test="top-k" />
          <span class="form-hint">召回候选分块数，范围 1 - 50</span>
        </el-form-item>
        <el-form-item label="重排序">
          <el-switch v-model="config.rerank_enabled" data-test="rerank-switch" />
          <span class="form-hint">
            {{ config.rerank_enabled ? '已开启：检索后对候选分块精排' : '已关闭：按向量相似度直接返回' }}
          </span>
        </el-form-item>
        <el-form-item label="Embedding 模型" prop="embedding_model">
          <el-select v-model="config.embedding_model" style="width: 280px" data-test="embedding-model">
            <el-option label="BAAI/bge-m3" value="BAAI/bge-m3" />
            <el-option label="text-embedding-3-small" value="text-embedding-3-small" />
            <el-option label="text-embedding-3-large" value="text-embedding-3-large" />
          </el-select>
        </el-form-item>
        <el-form-item label="召回阈值">
          <el-slider
            v-model="config.threshold"
            :min="0"
            :max="1"
            :step="0.05"
            show-input
            style="width: 340px"
            data-test="threshold-slider"
          />
          <span class="form-hint">低于该相似度的分块将被过滤，当前 {{ config.threshold.toFixed(2) }}</span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 存储设置 -->
    <el-card header="存储设置" class="mb-16">
      <el-form label-width="170px" class="config-form">
        <el-form-item label="上传目录">
          <el-input
            v-model="storage.upload_dir"
            placeholder="如：/data/openbase/uploads"
            style="width: 360px"
            data-test="upload-dir"
          />
        </el-form-item>
        <el-form-item label="连接状态">
          <el-button :loading="testing" data-test="test-connection" @click="testConnection">测试连接</el-button>
          <span v-if="storage.connected === true" class="form-hint success">连接成功：目录可正常读写</span>
          <span v-else-if="storage.connected === false" class="form-hint error">连接失败：请检查路径与权限</span>
          <span v-else class="form-hint">尚未测试</span>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="save-bar">
      <el-button type="primary" :loading="saving" data-test="save-config" @click="saveConfig">保存配置</el-button>
      <el-button :disabled="saving" data-test="reset-config" @click="resetConfig">重置</el-button>
    </div>

    <!-- 配置版本历史 -->
    <el-card header="配置版本历史" class="mb-16">
      <el-empty v-if="history.length === 0" description="暂无配置变更记录，保存后生成" :image-size="70" />
      <div v-else class="ob-table-scroll">
        <el-table :data="history" size="small" data-test="config-history">
          <el-table-column prop="version" label="版本" width="90" />
          <el-table-column prop="chunk_size" label="分块大小" width="110" />
          <el-table-column prop="top_k" label="TopK" width="90" />
          <el-table-column prop="embedding_model" label="Embedding 模型" width="200" />
          <el-table-column prop="saved_at" label="保存时间" width="170" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

interface HistoryRow {
  version: string
  chunk_size: number
  top_k: number
  embedding_model: string
  saved_at: string
}

const configFormRef = ref<FormInstance>()
const pageLoading = ref(true)
const saving = ref(false)
const testing = ref(false)
const alertMessage = ref('')
const alertType = ref<'success' | 'warning' | 'error'>('error')
const history = ref<HistoryRow[]>([])
let versionCounter = 1

const config = reactive({
  chunk_size: 512,
  top_k: 10,
  rerank_enabled: true,
  embedding_model: 'BAAI/bge-m3',
  threshold: 0.5,
})

const defaultConfig = {
  chunk_size: 512,
  top_k: 10,
  rerank_enabled: true,
  embedding_model: 'BAAI/bge-m3',
  threshold: 0.5,
}

const configRules: FormRules = {
  chunk_size: [
    { required: true, message: '请输入默认分块大小', trigger: 'blur' },
    { type: 'number', min: 100, max: 5000, message: '分块大小需在 100 - 5000 之间', trigger: 'blur' },
  ],
  top_k: [
    { required: true, message: '请输入检索 TopK', trigger: 'blur' },
    { type: 'number', min: 1, max: 50, message: 'TopK 需在 1 - 50 之间', trigger: 'blur' },
  ],
  embedding_model: [{ required: true, message: '请选择 Embedding 模型', trigger: 'change' }],
}

const storage = reactive<{ upload_dir: string; connected: boolean | null }>({
  upload_dir: '/data/openbase/uploads',
  connected: null,
})

function testConnection() {
  const dir = storage.upload_dir.trim()
  if (!dir) {
    alertMessage.value = '上传目录不能为空'
    alertType.value = 'error'
    return
  }
  testing.value = true
  alertMessage.value = ''
  setTimeout(() => {
    testing.value = false
    storage.connected = dir.startsWith('/data')
    if (storage.connected) {
      alertMessage.value = `目录「${dir}」连接成功，可正常读写`
      alertType.value = 'success'
    } else {
      alertMessage.value = `目录「${dir}」连接失败：路径不存在或权限不足`
      alertType.value = 'error'
    }
  }, 800)
}

async function saveConfig() {
  const valid = (await configFormRef.value?.validate().catch(() => false)) ?? false
  if (!valid) return
  saving.value = true
  setTimeout(() => {
    saving.value = false
    const version = `v1.${versionCounter}`
    history.value.unshift({
      version,
      chunk_size: config.chunk_size,
      top_k: config.top_k,
      embedding_model: config.embedding_model,
      saved_at: new Date().toISOString().slice(0, 16).replace('T', ' '),
    })
    versionCounter += 1
    ElMessage.success('配置已保存')
    ElMessageBox.alert('配置已保存，部分参数需重启服务后生效。是否现在重启？', '模拟重启提示', {
      confirmButtonText: '立即重启',
      cancelButtonText: '稍后重启',
      type: 'warning',
    })
      .then(() => {
        ElMessage.success('服务重启中，预计 30 秒后恢复')
      })
      .catch(() => {
        ElMessage.info('已取消重启，配置将在下次重启时生效')
      })
  }, 600)
}

function resetConfig() {
  config.chunk_size = defaultConfig.chunk_size
  config.top_k = defaultConfig.top_k
  config.rerank_enabled = defaultConfig.rerank_enabled
  config.embedding_model = defaultConfig.embedding_model
  config.threshold = defaultConfig.threshold
  configFormRef.value?.clearValidate()
  alertMessage.value = ''
  ElMessage.info('已恢复默认配置（未保存）')
}

onMounted(() => {
  setTimeout(() => {
    pageLoading.value = false
  }, 400)
})
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.config-form { max-width: 760px; }
.form-hint { color: var(--ob-text-secondary); font-size: 12px; margin-left: 12px; line-height: 1.6; }
.form-hint.success { color: var(--ob-success); }
.form-hint.error { color: var(--ob-danger); }
.save-bar { display: flex; gap: 12px; margin-bottom: 16px; }
</style>
