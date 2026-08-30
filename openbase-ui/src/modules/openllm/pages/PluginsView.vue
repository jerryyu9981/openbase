<template>
  <div class="plugins-page">
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card header="插件列表" data-test="plugin-card">
          <div class="ob-table-scroll">
            <el-table :data="plugins" stripe empty-text="暂无插件" data-test="plugin-table">
              <el-table-column prop="name" label="插件" min-width="160" />
              <el-table-column prop="version" label="版本" width="80" />
              <el-table-column prop="description" label="描述" min-width="180" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" data-test="plugin-toggle" @change="toggle(row)" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" data-test="plugin-tools" @click="showTools(row)">内置工具</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card header="内置工具详情" data-test="plugin-tools-card">
          <el-empty v-if="!currentTools.length" description="选择插件查看内置工具" :image-size="70" />
          <div v-for="tool in currentTools" :key="tool.name" class="tool-item" data-test="plugin-tool-item">
            <div class="tool-header">
              <span class="tool-name">{{ tool.name }}</span>
              <el-tag size="small" type="info">{{ tool.category }}</el-tag>
            </div>
            <div class="tool-desc">{{ tool.description }}</div>
            <el-collapse class="tool-params">
              <el-collapse-item title="参数定义" name="params">
                <pre class="params-json">{{ JSON.stringify(tool.parameters, null, 2) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ToolDef {
  name: string
  category: string
  description: string
  parameters: Record<string, unknown>
}

interface PluginRow {
  name: string
  version: string
  description: string
  enabled: boolean
  tools: ToolDef[]
}

const plugins = ref<PluginRow[]>([
  {
    name: 'web-search', version: '1.2.0', description: '联网搜索工具（搜索引擎 API 封装）', enabled: true,
    tools: [{ name: 'web_search', category: 'search', description: '关键词联网搜索，返回 Top-K 结果', parameters: { query: { type: 'string', required: true }, top_k: { type: 'integer', default: 5 } } }],
  },
  {
    name: 'calculator', version: '1.0.0', description: '数学计算工具（安全沙箱执行）', enabled: true,
    tools: [{ name: 'calc', category: 'math', description: '安全计算表达式求值', parameters: { expr: { type: 'string', required: true } } }],
  },
  {
    name: 'database-reader', version: '0.9.1', description: '只读数据库查询工具（白名单表）', enabled: false,
    tools: [{ name: 'db_query', category: 'database', description: '参数化 SQL 查询（只读）', parameters: { sql: { type: 'string', required: true }, limit: { type: 'integer', default: 10 } } }],
  },
])

const currentTools = ref<ToolDef[]>(plugins.value[0]?.tools ?? [])

function toggle(row: PluginRow) {
  ElMessage.success(row.enabled ? `插件 ${row.name} 已启用` : `插件 ${row.name} 已停用`)
}

function showTools(row: PluginRow) {
  currentTools.value = row.tools
}
</script>

<style scoped>
.tool-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.tool-header { display: flex; justify-content: space-between; align-items: center; }
.tool-name { font-weight: 600; }
.tool-desc { font-size: 13px; color: #475569; margin: 6px 0; }
.params-json { background: #f6f8fa; border-radius: 6px; padding: 8px; font-size: 12px; }
</style>
