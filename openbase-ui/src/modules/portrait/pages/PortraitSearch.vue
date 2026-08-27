<template>
  <div>
    <!-- TD-13-24 画像查询：多条件组合查询表单 -->
    <el-card shadow="never" class="query-card mb-16" data-test="portrait-search-form">
      <el-form inline :model="queryForm" label-width="auto">
        <el-form-item label="姓名">
          <el-input v-model="queryForm.name" placeholder="姓名模糊查询" clearable style="width: 160px" data-test="search-name" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="queryForm.phone" placeholder="11 位手机号" clearable style="width: 160px" data-test="search-phone" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="queryForm.gender" placeholder="全部" clearable style="width: 100px" data-test="search-gender">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
            <el-option label="未知" value="未知" />
          </el-select>
        </el-form-item>
        <el-form-item label="年龄段">
          <el-select v-model="queryForm.ageRange" placeholder="全部" clearable style="width: 120px" data-test="search-age-range">
            <el-option label="18 岁以下" value="under18" />
            <el-option label="18-25 岁" value="18-25" />
            <el-option label="26-35 岁" value="26-35" />
            <el-option label="36-45 岁" value="36-45" />
            <el-option label="46 岁以上" value="over45" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="queryForm.tags" multiple clearable collapse-tags placeholder="按标签筛选" style="width: 220px" data-test="search-tags">
            <el-option v-for="tag in tagOptions" :key="tag" :label="tag" :value="tag" />
          </el-select>
        </el-form-item>
        <el-form-item label="创建时间">
          <el-date-picker
            v-model="queryForm.createRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
            data-test="search-create-range"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" data-test="search-submit" @click="handleQuery">查询</el-button>
          <el-button data-test="search-reset" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 错误态 -->
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="search-error"
      @close="errorMessage = ''"
    />

    <!-- 查询结果表格（加载态 + 空态） -->
    <div v-loading="loading" class="ob-table-scroll">
      <el-table :data="pagedRows" stripe data-test="portrait-search-table">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="姓名" min-width="100" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="gender" label="性别" width="70" />
        <el-table-column prop="age" label="年龄" width="70" />
        <el-table-column label="标签" min-width="190">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" class="tag-item" type="info">{{ tag }}</el-tag>
            <span v-if="!row.tags.length" class="text-secondary">—</span>
          </template>
        </el-table-column>
        <el-table-column label="画像类型" width="110">
          <template #default="{ row }">
            <el-tag :type="portraitTypeTagType(row.portrait_type)" size="small">{{ row.portrait_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160" />
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="search-detail" @click="$router.push(`/portrait/${row.id}`)">详情</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty
            :description="queried ? '未找到匹配的画像，请调整查询条件后重试' : '请输入查询条件后点击「查询」'"
            :image-size="90"
            data-test="search-empty"
          />
        </template>
      </el-table>
    </div>

    <el-pagination
      v-if="filteredRows.length > 0"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="filteredRows.length"
      :page-sizes="[5, 10, 20]"
      layout="total, sizes, prev, pager, next, jumper"
      class="table-pagination"
      data-test="search-pagination"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

interface PortraitRow {
  id: number
  name: string
  phone: string
  gender: string
  age: number
  tags: string[]
  portrait_type: string
  created_at: string
  updated_at: string
}

interface QueryForm {
  name: string
  phone: string
  gender: string
  ageRange: string
  tags: string[]
  createRange: [string, string] | null
}

const tagOptions = ['高频用户', 'RAG', '技术型', '试用', '付费用户', '流失预警', '内容偏好', '夜间活跃']

const queryForm = reactive<QueryForm>({ name: '', phone: '', gender: '', ageRange: '', tags: [], createRange: null })
const loading = ref(false)
const queried = ref(false)
const errorMessage = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

/** 契约 mock：本地画像数据，不调用真实 API */
const mockProfiles = ref<PortraitRow[]>([
  { id: 1001, name: '张伟', phone: '13800138001', gender: '男', age: 32, tags: ['高频用户', 'RAG'], portrait_type: '行为画像', created_at: '2026-08-25', updated_at: '2026-08-26 09:12' },
  { id: 1002, name: '张敏', phone: '13800138002', gender: '女', age: 27, tags: ['付费用户', '内容偏好'], portrait_type: '偏好画像', created_at: '2026-08-24', updated_at: '2026-08-26 08:40' },
  { id: 1003, name: '李娜', phone: '13900139001', gender: '女', age: 24, tags: ['试用'], portrait_type: '基础画像', created_at: '2026-08-22', updated_at: '2026-08-25 18:05' },
  { id: 1004, name: '王强', phone: '13900139002', gender: '男', age: 41, tags: ['高频用户', '技术型'], portrait_type: '组合画像', created_at: '2026-08-20', updated_at: '2026-08-25 15:30' },
  { id: 1005, name: '刘洋', phone: '15000150001', gender: '男', age: 19, tags: ['试用', '夜间活跃'], portrait_type: '基础画像', created_at: '2026-08-18', updated_at: '2026-08-24 22:11' },
  { id: 1006, name: '陈静', phone: '15000150002', gender: '女', age: 33, tags: ['付费用户', 'RAG'], portrait_type: '行为画像', created_at: '2026-08-15', updated_at: '2026-08-24 10:00' },
  { id: 1007, name: '赵磊', phone: '18600186001', gender: '男', age: 47, tags: ['流失预警'], portrait_type: '组合画像', created_at: '2026-08-12', updated_at: '2026-08-23 14:22' },
  { id: 1008, name: '孙丽', phone: '18600186002', gender: '女', age: 28, tags: ['高频用户', '内容偏好'], portrait_type: '偏好画像', created_at: '2026-08-10', updated_at: '2026-08-23 09:45' },
  { id: 1009, name: '周杰', phone: '13700137001', gender: '男', age: 22, tags: ['技术型', '夜间活跃'], portrait_type: '行为画像', created_at: '2026-08-08', updated_at: '2026-08-22 20:18' },
  { id: 1010, name: '吴倩', phone: '13700137002', gender: '女', age: 36, tags: ['付费用户'], portrait_type: '基础画像', created_at: '2026-08-05', updated_at: '2026-08-22 11:36' },
  { id: 1011, name: '郑浩', phone: '13500135001', gender: '男', age: 29, tags: ['高频用户', 'RAG', '技术型'], portrait_type: '组合画像', created_at: '2026-08-02', updated_at: '2026-08-21 16:50' },
  { id: 1012, name: '冯雪', phone: '13500135002', gender: '女', age: 25, tags: ['内容偏好'], portrait_type: '偏好画像', created_at: '2026-07-30', updated_at: '2026-08-21 08:20' },
  { id: 1013, name: '林悦', phone: '13300133001', gender: '女', age: 43, tags: ['流失预警'], portrait_type: '基础画像', created_at: '2026-07-28', updated_at: '2026-08-20 17:40' },
  { id: 1014, name: '高翔', phone: '13300133002', gender: '男', age: 38, tags: ['付费用户', '夜间活跃'], portrait_type: '行为画像', created_at: '2026-07-25', updated_at: '2026-08-20 10:15' },
])

const filteredRows = computed(() => {
  if (!queried.value) return []
  const name = queryForm.name.trim().toLowerCase()
  const phone = queryForm.phone.trim()
  const gender = queryForm.gender
  const ageRange = queryForm.ageRange
  const tags = queryForm.tags
  const [start, end] = queryForm.createRange ?? [null, null]
  return mockProfiles.value.filter((row) => {
    // 契约 mock 核心：按输入姓名模糊过滤
    if (name && !row.name.toLowerCase().includes(name)) return false
    if (phone && row.phone !== phone) return false
    if (gender && row.gender !== gender) return false
    if (ageRange && !ageInRange(row.age, ageRange)) return false
    if (tags.length > 0 && !tags.some((tag) => row.tags.includes(tag))) return false
    if (start && row.created_at < start) return false
    if (end && row.created_at > end) return false
    return true
  })
})

const pagedRows = computed(() => {
  const offset = (currentPage.value - 1) * pageSize.value
  return filteredRows.value.slice(offset, offset + pageSize.value)
})

function ageInRange(age: number, range: string): boolean {
  if (range === 'under18') return age < 18
  if (range === '18-25') return age >= 18 && age <= 25
  if (range === '26-35') return age >= 26 && age <= 35
  if (range === '36-45') return age >= 36 && age <= 45
  if (range === 'over45') return age >= 46
  return true
}

function portraitTypeTagType(type: string) {
  return { 基础画像: 'info', 行为画像: 'success', 偏好画像: 'warning', 组合画像: 'danger' }[type] || 'info'
}

/** 查询：模拟 500ms 加载后展示本地 mock 过滤结果 */
function handleQuery() {
  const phone = queryForm.phone.trim()
  if (phone && !/^\d{11}$/.test(phone)) {
    errorMessage.value = '手机号格式不正确：请输入 11 位数字'
    return
  }
  errorMessage.value = ''
  loading.value = true
  currentPage.value = 1
  window.setTimeout(() => {
    queried.value = true
    loading.value = false
    ElMessage.success(`查询完成，共匹配 ${filteredRows.value.length} 条画像`)
  }, 500)
}

function handleReset() {
  queryForm.name = ''
  queryForm.phone = ''
  queryForm.gender = ''
  queryForm.ageRange = ''
  queryForm.tags = []
  queryForm.createRange = null
  errorMessage.value = ''
  currentPage.value = 1
  queried.value = false
  ElMessage.info('查询条件已重置')
}
</script>

<style scoped>
.query-card :deep(.el-form-item) { margin-bottom: 6px; }
.mb-16 { margin-bottom: 16px; }
.tag-item { margin-right: 4px; }
.text-secondary { color: var(--ob-text-secondary); }
.table-pagination { margin-top: 12px; justify-content: flex-end; }
</style>
