<template>
  <div class="evidence-layout" data-test="evidence-policy-form">
    <el-card shadow="never" class="form-card">
      <el-form label-width="150px">
        <el-form-item label="策略说明">
          <el-input
            :model-value="String(modelValue.description || '')"
            type="textarea"
            :rows="3"
            placeholder="如：每条标注须记录数据来源文书编号，三级审核后生效"
            data-test="evidence-description"
            @update:model-value="(value: string) => patch({ description: value })"
          />
        </el-form-item>
        <el-form-item label="审核层级 review_levels">
          <el-input-number
            :model-value="Number(modelValue.review_levels ?? 1)"
            :min="1"
            :max="5"
            size="small"
            data-test="evidence-review-levels"
            @update:model-value="(value: number | undefined) => patch({ review_levels: Number(value ?? 1) })"
          />
        </el-form-item>
        <el-form-item label="必须记录来源">
          <el-switch
            :model-value="Boolean(modelValue.require_source)"
            data-test="evidence-require-source"
            @update:model-value="(value: boolean) => patch({ require_source: Boolean(value) })"
          />
        </el-form-item>
        <el-form-item label="最大证据条数">
          <el-input-number
            :model-value="Number(modelValue.max_items ?? 10)"
            :min="1"
            :max="100"
            size="small"
            data-test="evidence-max-items"
            @update:model-value="(value: number | undefined) => patch({ max_items: Number(value ?? 10) })"
          />
        </el-form-item>
        <el-form-item label="脱敏展示">
          <el-switch
            :model-value="Boolean(modelValue.mask_sensitive)"
            data-test="evidence-mask"
            @update:model-value="(value: boolean) => patch({ mask_sensitive: Boolean(value) })"
          />
        </el-form-item>
        <el-form-item label="留存天数">
          <el-input-number
            :model-value="Number(modelValue.retention_days ?? 365)"
            :min="1"
            :max="3650"
            size="small"
            data-test="evidence-retention"
            @update:model-value="(value: number | undefined) => patch({ retention_days: Number(value ?? 365) })"
          />
        </el-form-item>
      </el-form>
      <div v-if="unknownKeys.length" class="unknown">
        <div class="unknown-title">未识别键（原样保留，不参与可视化编辑）</div>
        <el-tag v-for="key in unknownKeys" :key="key" size="small" type="info" class="mr-6">{{ key }}</el-tag>
      </div>
    </el-card>

    <el-card shadow="never" header="证据示例（一份画像将携带的证据）" class="sample-card">
      <div class="sample-item">
        <div class="sample-title">来源文书</div>
        <div class="sample-value">{{ modelValue.require_source ? '《扣分审批表》No.2026-0915' : '（未要求来源）' }}</div>
      </div>
      <div class="sample-item">
        <div class="sample-title">审核链路</div>
        <div class="sample-value">{{ Number(modelValue.review_levels ?? 1) }} 级审核</div>
      </div>
      <div class="sample-item">
        <div class="sample-title">展示上限</div>
        <div class="sample-value">最多 {{ Number(modelValue.max_items ?? 10) }} 条 · 留存 {{ Number(modelValue.retention_days ?? 365) }} 天</div>
      </div>
      <div class="sample-item">
        <div class="sample-title">脱敏</div>
        <div class="sample-value">{{ modelValue.mask_sensitive ? '开启（证件/联系方式打码）' : '关闭' }}</div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ modelValue: Record<string, unknown> }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: Record<string, unknown>): void }>()

const KNOWN_KEYS = ['description', 'review_levels', 'require_source', 'max_items', 'mask_sensitive', 'retention_days']
const unknownKeys = computed(() => Object.keys(props.modelValue || {}).filter((key) => !KNOWN_KEYS.includes(key)))

function patch(changes: Record<string, unknown>) {
  emit('update:modelValue', { ...(props.modelValue || {}), ...changes })
}
</script>

<style scoped>
.evidence-layout { display: flex; gap: 14px; align-items: flex-start; flex-wrap: wrap; }
.form-card { flex: 2 1 460px; }
.sample-card { flex: 1 1 260px; }
.unknown { margin-top: 8px; }
.unknown-title { font-size: 12px; color: var(--ob-text-secondary); margin-bottom: 6px; }
.mr-6 { margin-right: 6px; margin-bottom: 6px; }
.sample-item { margin-bottom: 10px; }
.sample-title { font-size: 12px; color: var(--ob-text-secondary); }
.sample-value { font-size: 13px; }
</style>
