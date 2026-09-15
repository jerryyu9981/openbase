<template>
  <div class="gateway-services">
    <div class="page-toolbar">
      <el-button type="primary" :loading="loading" data-test="gw-refresh" @click="load">刷新</el-button>
      <el-button :loading="pinging" data-test="gw-ping" @click="runPing">连通性检测</el-button>
      <el-button type="success" data-test="gw-register-open" @click="registerOpen = true">注册实例</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="gw-error"
      @close="errorMessage = ''"
    />

    <!-- 连通性结果 -->
    <el-card v-if="pingResults.length" header="连通性检测结果" class="mb-16" data-test="gw-ping-card">
      <el-table :data="pingResults" size="small" empty-text="暂无结果">
        <el-table-column prop="system" label="系统" width="140" />
        <el-table-column label="可达" width="90">
          <template #default="{ row }">
            <el-tag :type="row.reachable ? 'success' : 'danger'" size="small">
              {{ row.reachable ? '可达' : '不可达' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="latency_ms" label="延迟(ms)" width="120">
          <template #default="{ row }">{{ row.latency_ms ?? '—' }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 服务实例列表 -->
    <el-card v-for="group in systems" :key="group.system" :header="`${systemLabel(group.system)}（${group.system}）`" class="mb-16" data-test="gw-system-card">
      <div class="ob-table-scroll">
        <el-table :data="group.instances" stripe empty-text="暂无实例（静态表兜底时显示默认实例）" data-test="gw-instance-table">
          <el-table-column prop="instance_id" label="实例 ID" min-width="150" />
          <el-table-column label="地址" width="160">
            <template #default="{ row }">{{ row.host }}:{{ row.port }}</template>
          </el-table-column>
          <el-table-column prop="weight" label="权重" width="70" />
          <el-table-column label="健康状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.healthy ? 'success' : 'danger'" size="small" data-test="gw-health-badge">
                {{ row.healthy ? '健康' : '异常' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="连续失败" width="90">
            <template #default="{ row }">{{ row.consecutive_failures }}</template>
          </el-table-column>
          <el-table-column label="操作" width="110">
            <template #default="{ row }">
              <el-popconfirm title="确认下线该实例？" @confirm="deregister(group.system, row.instance_id)">
                <template #reference>
                  <el-button link type="danger" size="small" data-test="gw-deregister">下线</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-empty v-if="!loading && systems.length === 0" description="暂无服务实例" :image-size="80" />

    <!-- 注册实例弹窗 -->
    <el-dialog v-model="registerOpen" title="注册服务实例" width="480px" data-test="gw-register-dialog">
      <el-form :model="registerForm" label-width="90px">
        <el-form-item label="系统">
          <el-select v-model="registerForm.system" data-test="gw-register-system">
            <el-option v-for="s in ['openllm', 'openrag', 'openmemory', 'dps']" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="主机">
          <el-input v-model="registerForm.host" placeholder="如 10.0.0.5" data-test="gw-register-host" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="registerForm.port" :min="1" :max="65535" data-test="gw-register-port" />
        </el-form-item>
        <el-form-item label="权重">
          <el-input-number v-model="registerForm.weight" :min="1" :max="100" data-test="gw-register-weight" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="registerOpen = false">取消</el-button>
        <el-button type="primary" :loading="registering" data-test="gw-register-submit" @click="register">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { gatewayApi, type SystemServices } from '@/core/api/gateway'

const loading = ref(false)
const pinging = ref(false)
const registering = ref(false)
const errorMessage = ref('')
const systems = ref<SystemServices[]>([])
const pingResults = ref<Array<{ system: string; reachable: boolean; latency_ms: number | null }>>([])
const registerOpen = ref(false)
const registerForm = ref({ system: 'openllm', host: '127.0.0.1', port: 8001, weight: 1 })

const SYSTEM_LABELS: Record<string, string> = {
  openllm: 'OpenLLM',
  openrag: 'OpenRAG',
  openmemory: 'OpenMemory',
  dps: 'DPS',
}
const systemLabel = (s: string) => SYSTEM_LABELS[s] || s

const totalInstances = computed(() =>
  systems.value.reduce((sum, g) => sum + g.instances.length, 0),
)

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await gatewayApi.listAllServices()
    systems.value = result.systems
    if (totalInstances.value === 0) {
      await loadHealthFallback()
    }
  } catch (error) {
    errorMessage.value = (error as Error).message || '加载服务列表失败'
  } finally {
    loading.value = false
  }
}

/** 服务列表为空时回退到健康状态接口展示（保证页面可用） */
async function loadHealthFallback() {
  try {
    const health = await gatewayApi.health()
    systems.value = health.systems.map((h) => ({
      system: h.system,
      instances: [],
    }))
  } catch {
    /* 忽略回退失败 */
  }
}

async function runPing() {
  pinging.value = true
  try {
    pingResults.value = (await gatewayApi.ping()).results
  } catch (error) {
    errorMessage.value = (error as Error).message || '连通性检测失败'
  } finally {
    pinging.value = false
  }
}

async function register() {
  registering.value = true
  try {
    const instance = await gatewayApi.registerService(registerForm.value)
    ElMessage.success(`实例 ${instance.instance_id} 注册成功`)
    registerOpen.value = false
    await load()
  } catch (error) {
    errorMessage.value = (error as Error).message || '注册失败'
  } finally {
    registering.value = false
  }
}

async function deregister(system: string, instanceId: string) {
  try {
    await gatewayApi.deregisterService(system, instanceId)
    ElMessage.success(`实例 ${instanceId} 已下线`)
    await load()
  } catch (error) {
    errorMessage.value = (error as Error).message || '下线失败'
  }
}

onMounted(load)
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
</style>
