<template>
  <div class="dps-permission">
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card header="角色管理" data-test="perm-card">
          <div class="page-toolbar">
            <el-button type="primary" size="small" data-test="perm-new" @click="openCreate">新建角色</el-button>
          </div>
          <el-table :data="roles" stripe empty-text="暂无角色" data-test="perm-table">
            <el-table-column prop="name" label="角色" min-width="130" />
            <el-table-column prop="description" label="描述" min-width="160" />
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button link type="primary" size="small" data-test="perm-matrix" @click="openMatrix(row)">权限矩阵</el-button>
                <el-popconfirm title="确认删除该角色？" @confirm="remove(row.id)">
                  <template #reference>
                    <el-button link type="danger" size="small">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card header="权限矩阵" class="mt-16" data-test="perm-matrix-card">
          <el-checkbox-group v-model="matrixChecked" class="matrix-group">
            <el-checkbox v-for="p in matrixItems" :key="p" :value="p" :label="p" />
          </el-checkbox-group>
          <div class="page-toolbar mt-8">
            <el-button type="primary" size="small" data-test="perm-matrix-save" @click="saveMatrix">保存矩阵</el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="租户管理" data-test="perm-tenant-card">
          <el-table :data="tenants" stripe empty-text="暂无租户" data-test="perm-tenant-table">
            <el-table-column prop="name" label="租户" min-width="130" />
            <el-table-column prop="quota" label="配额" width="110" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" data-test="perm-tenant-toggle" @change="toggleTenant(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editQuota(row)">调配额</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 角色弹窗 -->
    <el-dialog v-model="dialogOpen" title="新建角色" width="420px" data-test="perm-dialog">
      <el-form :model="form" label-width="70px">
        <el-form-item label="角色名">
          <el-input v-model="form.name" data-test="perm-name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" data-test="perm-save" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface RoleRow { id: number; name: string; description: string }
interface TenantRow { id: number; name: string; quota: string; enabled: boolean }

const matrixItems = [
  'portrait:read', 'portrait:write', 'portrait:delete',
  'tag:read', 'tag:write', 'tag:delete',
  'rule:read', 'rule:write', 'rule:execute',
  'report:read', 'report:export',
]

const roles = ref<RoleRow[]>([
  { id: 1, name: 'DPS 管理员', description: '画像全量管理' },
  { id: 2, name: '分析师', description: '画像与报表只读' },
  { id: 3, name: '规则工程师', description: '规则引擎维护' },
])

const tenants = ref<TenantRow[]>([
  { id: 1, name: 'AI 平台部', quota: '5,000,000', enabled: true },
  { id: 2, name: '模型组', quota: '2,000,000', enabled: true },
  { id: 3, name: '外部客户', quota: '500,000', enabled: false },
])

const matrixChecked = ref<string[]>(['portrait:read', 'portrait:write'])
const dialogOpen = ref(false)
const form = ref({ name: '', description: '' })

function openCreate() {
  form.value = { name: '', description: '' }
  dialogOpen.value = true
}

function save() {
  if (!form.value.name) {
    ElMessage.warning('请填写角色名')
    return
  }
  const id = Math.max(0, ...roles.value.map((r) => r.id)) + 1
  roles.value.push({ id, name: form.value.name, description: form.value.description })
  ElMessage.success('角色已创建')
  dialogOpen.value = false
}

function openMatrix(row: RoleRow) {
  matrixChecked.value = row.name === 'DPS 管理员' ? [...matrixItems] : ['portrait:read']
  ElMessage.info(`已加载角色 ${row.name} 的权限矩阵`)
}

function saveMatrix() {
  ElMessage.success(`权限矩阵已保存（${matrixChecked.value.length} 项权限）`)
}

function toggleTenant(row: TenantRow) {
  ElMessage.success(row.enabled ? `租户 ${row.name} 已启用` : `租户 ${row.name} 已停用`)
}

function editQuota(row: TenantRow) {
  ElMessage.success(`租户 ${row.name} 配额调整为 ${row.quota}`)
}

function remove(id: number) {
  roles.value = roles.value.filter((r) => r.id !== id)
  ElMessage.success('角色已删除')
}
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.mt-16 { margin-top: 16px; }
.mt-8 { margin-top: 8px; }
.matrix-group { display: flex; flex-wrap: wrap; gap: 8px 20px; max-height: 260px; overflow: auto; }
</style>
