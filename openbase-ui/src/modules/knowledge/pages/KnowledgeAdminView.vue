<template>
  <div class="rag-admin">
    <!-- KPI 概览 -->
    <el-row :gutter="16" class="mb-16">
      <el-col v-for="kpi in kpis" :key="kpi.label" :span="6">
        <el-card shadow="hover" data-test="rag-kpi">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value">{{ kpi.value }}</div>
          <div class="kpi-sub">{{ kpi.sub }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 知识库管理后台 -->
    <el-card header="知识库管理后台" data-test="rag-admin-card">
      <div class="page-toolbar">
        <el-input v-model="keyword" placeholder="搜索知识库" clearable style="width: 200px" data-test="rag-search" />
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 130px">
          <el-option label="正常" value="normal" />
          <el-option label="索引中" value="indexing" />
          <el-option label="异常" value="error" />
        </el-select>
      </div>
      <div class="ob-table-scroll">
        <el-table :data="filteredKbs" stripe empty-text="暂无知识库" data-test="rag-kb-table">
          <el-table-column prop="name" label="知识库" min-width="160" />
          <el-table-column prop="docs" label="文档数" width="90" />
          <el-table-column prop="vectors" label="向量数" width="90" />
          <el-table-column prop="size" label="占用空间" width="110" />
          <el-table-column label="健康状态" width="100">
            <template #default="{ row }">
              <el-tag :type="healthType(row.status)" size="small" data-test="rag-health">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
              <el-popconfirm title="确认清空该知识库全部向量？此操作不可恢复" @confirm="clearKb(row)">
                <template #reference>
                  <el-button link type="warning" size="small" data-test="rag-clear">清空</el-button>
                </template>
              </el-popconfirm>
              <el-popconfirm title="确认后台删除该知识库并回收资源？" @confirm="removeKb(row)">
                <template #reference>
                  <el-button link type="danger" size="small" data-test="rag-delete">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailOpen" title="知识库详情" size="420px">
      <el-descriptions v-if="currentKb" :column="1" border>
        <el-descriptions-item label="名称">{{ currentKb.name }}</el-descriptions-item>
        <el-descriptions-item label="文档数">{{ currentKb.docs }}</el-descriptions-item>
        <el-descriptions-item label="向量数">{{ currentKb.vectors }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabel(currentKb.status) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ currentKb.created }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

type KbStatus = 'normal' | 'indexing' | 'error'

interface KbRow {
  id: number
  name: string
  docs: number
  vectors: number
  size: string
  status: KbStatus
  created: string
}

const kpis = ref([
  { label: '知识库数', value: '6', sub: '正常 5 / 异常 1' },
  { label: '文档总数', value: '1,284', sub: '本月 +124' },
  { label: '向量总数', value: '2,031,450', sub: '占用 8.4GB' },
  { label: '系统健康度', value: '92%', sub: '平均检索延迟 38ms' },
])

const kbs = ref<KbRow[]>([
  { id: 1, name: '产品知识库', docs: 320, vectors: 512000, size: '1.2GB', status: 'normal', created: '2026-05-12' },
  { id: 2, name: '技术文档库', docs: 486, vectors: 780000, size: '2.1GB', status: 'normal', created: '2026-05-18' },
  { id: 3, name: '客服话术库', docs: 152, vectors: 240000, size: '0.6GB', status: 'indexing', created: '2026-07-01' },
  { id: 4, name: '法律条款库', docs: 78, vectors: 122000, size: '0.4GB', status: 'error', created: '2026-06-20' },
])

const keyword = ref('')
const statusFilter = ref('')
const detailOpen = ref(false)
const currentKb = ref<KbRow | null>(null)

const filteredKbs = computed(() =>
  kbs.value.filter((k) => {
    const matchKw = !keyword.value || k.name.includes(keyword.value)
    const matchStatus = !statusFilter.value || k.status === statusFilter.value
    return matchKw && matchStatus
  }),
)

function statusLabel(s: KbStatus) {
  return { normal: '正常', indexing: '索引中', error: '异常' }[s]
}

function healthType(s: KbStatus) {
  return { normal: 'success', indexing: 'warning', error: 'danger' }[s] as 'success' | 'warning' | 'danger'
}

function openDetail(row: KbRow) {
  currentKb.value = row
  detailOpen.value = true
}

function clearKb(row: KbRow) {
  row.vectors = 0
  row.size = '0MB'
  ElMessage.success(`知识库 ${row.name} 已清空并回收资源`)
}

function removeKb(row: KbRow) {
  kbs.value = kbs.value.filter((k) => k.id !== row.id)
  ElMessage.success(`知识库 ${row.name} 已后台删除`)
}
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.kpi-label { font-size: 13px; color: #6b7280; }
.kpi-value { font-size: 24px; font-weight: 600; margin: 4px 0; }
.kpi-sub { font-size: 12px; color: #9ca3af; }
</style>
