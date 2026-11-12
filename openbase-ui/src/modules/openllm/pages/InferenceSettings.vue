<template>
  <PageContainer title="推理设置" description="查看与配置对话上下文裁剪策略（context_policy）" test-id="inference-settings-page">
    <el-card data-test="context-policy-card">
      <template #header>
        <div class="card-header">
          <span>上下文裁剪策略</span>
          <el-tag :type="canManage ? 'success' : 'info'" size="small">
            {{ canManage ? '可编辑' : '只读' }}
          </el-tag>
        </div>
      </template>

      <el-alert
        v-if="!canManage"
        title="只读：修改上下文裁剪策略需系统管理员权限（system:config）"
        type="info"
        show-icon
        :closable="false"
        class="mb-16"
        data-test="context-policy-readonly"
      />

      <el-form label-width="150px">
        <el-form-item label="裁剪策略">
          <el-select
            v-model="form.strategy"
            :disabled="!canManage"
            data-test="context-policy-strategy"
            class="strategy-select"
          >
            <el-option
              v-for="strategy in CONTEXT_STRATEGIES"
              :key="strategy"
              :label="CONTEXT_STRATEGY_LABELS[strategy]"
              :value="strategy"
            />
          </el-select>
          <div class="field-hint" data-test="context-policy-strategy-desc">
            {{ CONTEXT_STRATEGY_DESCRIPTIONS[form.strategy] }}
          </div>
        </el-form-item>

        <el-form-item label="启用 token 预算">
          <el-switch
            v-model="form.maxTokensEnabled"
            :disabled="!canManage"
            data-test="context-policy-max-tokens-switch"
          />
        </el-form-item>

        <el-form-item v-if="form.maxTokensEnabled" label="token 预算">
          <el-input-number
            v-model="form.maxTokens"
            :min="1"
            :max="200000"
            :step="256"
            :disabled="!canManage"
            data-test="context-policy-max-tokens"
          />
          <div class="field-hint">缺省沿用 OpenLLM 现有窗口预算（上限 200000）。</div>
        </el-form-item>

        <el-form-item v-if="form.strategy === 'system_priority'" label="保留最近条数">
          <el-input-number
            v-model="form.preserveRecent"
            :min="0"
            :max="100"
            :disabled="!canManage"
            data-test="context-policy-preserve"
          />
          <div class="field-hint">仅「系统优先」策略生效，缺省 4 条。</div>
        </el-form-item>

        <el-form-item label="当前生效">
          <span class="current-policy" data-test="context-policy-current">{{ currentPolicyText }}</span>
        </el-form-item>

        <el-form-item v-if="canManage">
          <el-button type="primary" data-test="context-policy-save" @click="handleSave">保存</el-button>
          <el-button data-test="context-policy-reset" @click="handleReset">恢复默认</el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <div class="notes">
        <p>策略随对话请求（`context_policy`）透传至 OpenLLM，响应回显 `context_meta`，在 Playground 中展示实际入参条数与预算。</p>
        <p>配置保存在当前浏览器，仅影响本机后续对话；未配置时使用后端默认「保留最近」。</p>
      </div>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import PageContainer from '@/components/page/PageContainer.vue'
import { useAuthStore } from '@/core/stores/auth'
import {
  CONTEXT_STRATEGIES,
  CONTEXT_STRATEGY_DESCRIPTIONS,
  CONTEXT_STRATEGY_LABELS,
  loadContextPolicy,
  saveContextPolicy,
  type ContextPolicy,
  type ContextStrategy,
} from '@/core/contextPolicy'

/**
 * 推理设置（批次 4 R7）：上下文裁剪策略的只读展示与管理员配置。
 *
 * 后端能力由批次 3 提供（`context_policy` 透传 / `context_meta` 回显）；
 * 本页仅维护浏览器本地配置，不新增后端配置端点。
 */
const auth = useAuthStore()
/** 系统管理员：职责码 system:config，或超级管理员通配 */
const canManage = computed(
  () => auth.hasPermission('system:config') || auth.hasPermission('system:superadmin'),
)

const stored = loadContextPolicy()

const form = reactive<{
  strategy: ContextStrategy
  maxTokensEnabled: boolean
  maxTokens: number | null
  preserveRecent: number | null
}>({
  strategy: stored?.strategy ?? 'recent',
  maxTokensEnabled: stored?.max_tokens !== undefined,
  maxTokens: stored?.max_tokens ?? 2048,
  preserveRecent: stored?.preserve_recent_n ?? 4,
})

const currentPolicyText = computed(() => {
  const policy = loadContextPolicy()
  if (!policy) return '默认（保留最近，沿用 OpenLLM 窗口预算）'
  const parts = [CONTEXT_STRATEGY_LABELS[policy.strategy]]
  if (policy.max_tokens !== undefined) parts.push(`预算 ${policy.max_tokens} tokens`)
  if (policy.preserve_recent_n !== undefined) parts.push(`保留最近 ${policy.preserve_recent_n} 条`)
  return parts.join(' · ')
})

function handleSave() {
  const policy: ContextPolicy = { strategy: form.strategy }
  if (form.maxTokensEnabled && form.maxTokens !== null) policy.max_tokens = form.maxTokens
  if (form.strategy === 'system_priority' && form.preserveRecent !== null) {
    policy.preserve_recent_n = form.preserveRecent
  }
  saveContextPolicy(policy)
  ElMessage.success('已保存（仅影响当前浏览器，下一次对话生效）')
}

function handleReset() {
  saveContextPolicy(null)
  form.strategy = 'recent'
  form.maxTokensEnabled = false
  form.maxTokens = 2048
  form.preserveRecent = 4
  ElMessage.success('已恢复默认策略')
}
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mb-16 { margin-bottom: 16px; }
.strategy-select { width: 260px; }
.field-hint {
  width: 100%;
  margin-top: 4px;
  font-size: 12px;
  color: var(--ob-text-secondary);
}
.current-policy { font-size: 13px; color: var(--ob-text-primary, inherit); }
.notes p { margin: 0 0 6px; font-size: 12px; color: var(--ob-text-secondary); }
</style>
