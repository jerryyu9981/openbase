<template>
  <div>
    <div class="page-toolbar">
      <el-button type="primary" data-test="new-entity" @click="openEntityForm()">新建实体</el-button>
      <el-button type="primary" plain data-test="new-relation" @click="openRelationForm()">新建关系</el-button>
      <span class="graph-hint" data-test="graph-hint">拖动节点调整布局 · 滚轮缩放 · 悬停查看实体详情</span>
    </div>
    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      closable
      class="mb-16"
      data-test="graph-error"
      @close="errorMsg = ''"
    />
    <el-row :gutter="16">
      <el-col :xs="24" :lg="16">
        <el-card header="记忆图谱" body-style="padding: 0" class="graph-card">
          <div v-loading="loading" class="graph-body" data-test="memory-graph">
            <div ref="graphRef" class="graph-canvas" />
            <el-empty
              v-if="!loading && entities.length === 0"
              description="暂无实体数据，请先新建实体"
              class="graph-empty-overlay"
              data-test="graph-empty"
            />
          </div>
          <div
            v-show="tooltipVisible"
            ref="tooltipRef"
            class="graph-tooltip"
            :style="{ left: tooltipPos.left, top: tooltipPos.top }"
            data-test="graph-tooltip"
          >
            <div class="tooltip-name" :style="{ color: typeColor(hoverNode?.type ?? '') }">{{ hoverNode?.name }}</div>
            <div class="tooltip-meta">{{ hoverNode?.type }} · {{ hoverNode?.description }}</div>
            <div class="tooltip-links">
              <div v-if="hoverLinks.length === 0" class="tooltip-link">暂无关联关系</div>
              <div v-for="(link, index) in hoverLinks" :key="index" class="tooltip-link">{{ link }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="8">
        <el-card header="实体列表" body-style="padding: 0">
          <div class="ob-table-scroll">
            <el-table :data="entities" stripe size="small" data-test="entity-table" empty-text="暂无实体">
              <el-table-column prop="name" label="实体" min-width="110" />
              <el-table-column label="类型" width="84">
                <template #default="{ row }">
                  <el-tag size="small" effect="dark" :color="typeColor(row.type)" style="border: none">{{ row.type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="关系数" width="80" align="center">
                <template #default="{ row }">
                  <span :style="{ color: 'var(--ob-text-secondary)' }">{{ relationCount(row.id) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="118" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" data-test="edit-entity" @click="openEntityForm(row)">编辑</el-button>
                  <el-popconfirm title="确认删除该实体及其全部关系？" @confirm="removeEntity(row.id)">
                    <template #reference><el-button link type="danger" data-test="delete-entity">删除</el-button></template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="entityFormVisible" :title="editingEntityId ? '编辑实体' : '新建实体'" width="480px" data-test="entity-dialog">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="entityForm.name" placeholder="如：OpenBase 项目" data-test="entity-name-input" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="entityForm.type" style="width: 100%">
            <el-option v-for="type in entityTypes" :key="type" :label="type" :value="type" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="entityForm.description" type="textarea" :rows="2" placeholder="实体描述信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="entityFormVisible = false">取消</el-button>
        <el-button type="primary" data-test="save-entity" @click="saveEntity">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="relationFormVisible" title="新建关系" width="480px" data-test="relation-dialog">
      <el-form label-width="80px">
        <el-form-item label="源实体" required>
          <el-select v-model="relationForm.source" filterable placeholder="选择源实体" style="width: 100%" data-test="relation-source">
            <el-option v-for="entity in entities" :key="entity.id" :label="entity.name" :value="entity.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关系" required>
          <el-select v-model="relationForm.label" filterable allow-create default-first-option placeholder="如：参与、创建" style="width: 100%">
            <el-option v-for="label in relationLabels" :key="label" :label="label" :value="label" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标实体" required>
          <el-select v-model="relationForm.target" filterable placeholder="选择目标实体" style="width: 100%" data-test="relation-target">
            <el-option v-for="entity in entities" :key="entity.id" :label="entity.name" :value="entity.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="relationFormVisible = false">取消</el-button>
        <el-button type="primary" data-test="save-relation" :disabled="entities.length < 2" @click="saveRelation">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as d3 from 'd3'
import { ElMessage } from 'element-plus'

type EntityType = '人物' | '事件' | '概念' | '项目'

interface GraphEntity {
  id: number
  name: string
  type: EntityType
  description: string
}

interface GraphRelation {
  id: number
  source: number
  target: number
  label: string
}

interface SimNode extends d3.SimulationNodeDatum {
  id: number
  name: string
  type: EntityType
  description: string
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  id: number
  label: string
}

const TYPE_COLORS: Record<EntityType, string> = {
  人物: '#6366f1',
  事件: '#f59e0b',
  概念: '#10b981',
  项目: '#0ea5e9',
}

const entityTypes: EntityType[] = ['人物', '事件', '概念', '项目']
const relationLabels = ['参与', '创建', '关联', '引用', '影响', '提出', '负责', '属于']

const graphRef = ref<HTMLDivElement>()
const tooltipRef = ref<HTMLDivElement>()
const loading = ref(true)
const errorMsg = ref('')
const tooltipVisible = ref(false)
const hoverNode = ref<SimNode | null>(null)
const hoverLinks = ref<string[]>([])
const tooltipPos = reactive({ left: '0px', top: '0px' })

let simulation: d3.Simulation<SimNode, undefined> | null = null
let currentLinks: SimLink[] = []
let resizeTimer: number | undefined

// TD-13-18 记忆图谱 mock 实体（10 个）与关系（12 条）
const entities = ref<GraphEntity[]>([
  { id: 1, name: '张伟', type: '人物', description: 'OpenBase 项目发起人' },
  { id: 2, name: '李娜', type: '人物', description: '算法工程师，负责记忆模块' },
  { id: 3, name: 'OpenBase', type: '项目', description: '开源多智能体协作平台' },
  { id: 4, name: '记忆图谱', type: '概念', description: '实体与关系的语义网络' },
  { id: 5, name: '语义检索', type: '概念', description: '基于向量的相似度召回' },
  { id: 6, name: '2026 产品发布会', type: '事件', description: '2026-06 举办的产品发布活动' },
  { id: 7, name: 'RAG 架构评审', type: '事件', description: '2026-07 完成 RAG 架构评审' },
  { id: 8, name: 'OpenMemory', type: '项目', description: '记忆子系统，版本 v6.7' },
  { id: 9, name: '王强', type: '人物', description: '前端工程师，负责图谱可视化' },
  { id: 10, name: '知识蒸馏', type: '概念', description: '大模型轻量化技术' },
])

const relations = ref<GraphRelation[]>([
  { id: 1, source: 1, target: 3, label: '发起' },
  { id: 2, source: 2, target: 8, label: '负责' },
  { id: 3, source: 9, target: 4, label: '开发' },
  { id: 4, source: 3, target: 4, label: '包含' },
  { id: 5, source: 4, target: 5, label: '依赖' },
  { id: 6, source: 8, target: 4, label: '实现' },
  { id: 7, source: 3, target: 7, label: '组织' },
  { id: 8, source: 6, target: 3, label: '推广' },
  { id: 9, source: 5, target: 8, label: '用于' },
  { id: 10, source: 7, target: 2, label: '参与' },
  { id: 11, source: 1, target: 6, label: '演讲' },
  { id: 12, source: 3, target: 10, label: '研究' },
])

const entityFormVisible = ref(false)
const editingEntityId = ref<number | null>(null)
const entityForm = reactive<{ name: string; type: EntityType; description: string }>({
  name: '',
  type: '人物',
  description: '',
})

const relationFormVisible = ref(false)
const relationForm = reactive<{ source: number | undefined; label: string; target: number | undefined }>({
  source: undefined,
  label: '',
  target: undefined,
})

function typeColor(type: string) {
  return TYPE_COLORS[type as EntityType] ?? '#909399'
}

function relationCount(id: number) {
  return relations.value.filter((relation) => relation.source === id || relation.target === id).length
}

function renderGraph() {
  const canvas = graphRef.value
  if (!canvas) return
  if (simulation) {
    simulation.stop()
    simulation = null
  }
  d3.select(canvas).selectAll('*').remove()
  tooltipVisible.value = false
  currentLinks = []
  if (entities.value.length === 0) return

  const width = canvas.clientWidth || 800
  const height = canvas.clientHeight || 560

  const nodes: SimNode[] = entities.value.map((entity) => ({
    id: entity.id,
    name: entity.name,
    type: entity.type,
    description: entity.description,
  }))
  const nodeById = new Map<number, SimNode>(nodes.map((node) => [node.id, node]))
  const links: SimLink[] = []
  for (const relation of relations.value) {
    const source = nodeById.get(relation.source)
    const target = nodeById.get(relation.target)
    if (source && target) {
      links.push({ id: relation.id, label: relation.label, source, target })
    }
  }
  currentLinks = links

  const svg = d3.select(canvas).append('svg').attr('width', width).attr('height', height)
  const container = svg.append('g')

  // 类型图例（不随缩放）
  const legend = svg.append('g').attr('class', 'graph-legend')
  entityTypes.forEach((type, index) => {
    const item = legend.append('g').attr('transform', `translate(12, ${14 + index * 22})`)
    item.append('circle').attr('r', 6).attr('fill', TYPE_COLORS[type])
    item.append('text').attr('x', 14).attr('y', 4).attr('font-size', 12).attr('fill', '#909399').text(type)
  })

  // 有向箭头
  svg.append('defs')
    .append('marker')
    .attr('id', 'graph-arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 30)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#c0c4cc')

  const linkElements = container
    .append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', '#c0c4cc')
    .attr('stroke-width', 1.6)
    .attr('stroke-opacity', 0.75)
    .attr('marker-end', 'url(#graph-arrow)')

  const nodeElements = container
    .append('g')
    .selectAll<SVGGElement, SimNode>('g')
    .data(nodes)
    .join('g')
    .attr('class', 'graph-node')
    .call(dragBehavior())

  nodeElements
    .append('circle')
    .attr('r', 26)
    .attr('fill', (node) => TYPE_COLORS[node.type])
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 2)

  nodeElements
    .append('text')
    .attr('dy', 40)
    .attr('text-anchor', 'middle')
    .attr('font-size', 12)
    .attr('fill', '#303133')
    .text((node) => node.name)

  nodeElements
    .on('mouseover', (event: MouseEvent, node: SimNode) => {
      showTooltip(event, node)
      d3.select(event.currentTarget as SVGGElement)
        .select<SVGCircleElement>('circle')
        .attr('stroke', '#1f2d3d')
        .attr('stroke-width', 3)
    })
    .on('mouseout', () => {
      tooltipVisible.value = false
      nodeElements.select<SVGCircleElement>('circle').attr('stroke', '#ffffff').attr('stroke-width', 2)
    })

  const zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.3, 3])
    .on('zoom', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
      container.attr('transform', event.transform.toString())
    })
  svg.call(zoomBehavior)

  simulation = d3
    .forceSimulation<SimNode>(nodes)
    .force('link', d3.forceLink<SimNode, SimLink>(links).id((node) => node.id).distance(120).strength(0.5))
    .force('charge', d3.forceManyBody<SimNode>().strength(-420))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide<SimNode>().radius(46))

  simulation.on('tick', () => {
    linkElements
      .attr('x1', (link) => (link.source as SimNode).x ?? 0)
      .attr('y1', (link) => (link.source as SimNode).y ?? 0)
      .attr('x2', (link) => (link.target as SimNode).x ?? 0)
      .attr('y2', (link) => (link.target as SimNode).y ?? 0)
    nodeElements.attr('transform', (node) => `translate(${node.x ?? 0},${node.y ?? 0})`)
  })
}

function dragBehavior() {
  return d3
    .drag<SVGGElement, SimNode>()
    .on('start', (event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>, node: SimNode) => {
      if (!event.active && simulation) simulation.alphaTarget(0.3).restart()
      node.fx = node.x ?? 0
      node.fy = node.y ?? 0
    })
    .on('drag', (event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>, node: SimNode) => {
      node.fx = event.x
      node.fy = event.y
    })
    .on('end', (event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>, node: SimNode) => {
      if (!event.active && simulation) simulation.alphaTarget(0)
      node.fx = null
      node.fy = null
    })
}

function showTooltip(event: MouseEvent, node: SimNode) {
  hoverNode.value = node
  hoverLinks.value = currentLinks.map((link) => {
    const source = link.source as SimNode
    const target = link.target as SimNode
    if (source.id !== node.id && target.id !== node.id) return ''
    return source.id === node.id ? `${link.label} → ${target.name}` : `${source.name} → ${link.label}`
  }).filter((text) => text !== '')
  tooltipVisible.value = true
  window.requestAnimationFrame(() => {
    const canvas = graphRef.value
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    tooltipPos.left = `${event.clientX - rect.left + 14}px`
    tooltipPos.top = `${event.clientY - rect.top + 14}px`
  })
}

function openEntityForm(row?: GraphEntity) {
  editingEntityId.value = row?.id ?? null
  entityForm.name = row?.name ?? ''
  entityForm.type = row?.type ?? '人物'
  entityForm.description = row?.description ?? ''
  entityFormVisible.value = true
}

function saveEntity() {
  const name = entityForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入实体名称')
    return
  }
  if (entities.value.some((entity) => entity.name === name && entity.id !== editingEntityId.value)) {
    errorMsg.value = `实体名称「${name}」已存在`
    return
  }
  if (editingEntityId.value) {
    const target = entities.value.find((entity) => entity.id === editingEntityId.value)
    if (target) {
      target.name = name
      target.type = entityForm.type
      target.description = entityForm.description.trim()
      ElMessage.success('实体已更新')
    }
  } else {
    entities.value.push({
      id: Date.now(),
      name,
      type: entityForm.type,
      description: entityForm.description.trim(),
    })
    ElMessage.success('实体已创建')
  }
  entityFormVisible.value = false
  errorMsg.value = ''
  renderGraph()
}

function removeEntity(id: number) {
  entities.value = entities.value.filter((entity) => entity.id !== id)
  relations.value = relations.value.filter((relation) => relation.source !== id && relation.target !== id)
  ElMessage.success('实体及其关系已删除')
  renderGraph()
}

function openRelationForm() {
  relationForm.source = undefined
  relationForm.label = ''
  relationForm.target = undefined
  relationFormVisible.value = true
}

function saveRelation() {
  if (relationForm.source === undefined || relationForm.target === undefined || !relationForm.label.trim()) {
    ElMessage.warning('请完整填写源实体、关系与目标实体')
    return
  }
  if (relationForm.source === relationForm.target) {
    errorMsg.value = '源实体与目标实体不能相同'
    return
  }
  const label = relationForm.label.trim()
  if (
    relations.value.some(
      (relation) => relation.source === relationForm.source && relation.target === relationForm.target && relation.label === label,
    )
  ) {
    errorMsg.value = '该关系已存在'
    return
  }
  relations.value.push({ id: Date.now(), source: relationForm.source, target: relationForm.target, label })
  ElMessage.success('关系已创建')
  relationFormVisible.value = false
  errorMsg.value = ''
  renderGraph()
}

function handleResize() {
  window.clearTimeout(resizeTimer)
  resizeTimer = window.setTimeout(() => renderGraph(), 200)
}

onMounted(() => {
  // 模拟拉取图谱数据
  window.setTimeout(() => {
    loading.value = false
    renderGraph()
  }, 600)
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  window.clearTimeout(resizeTimer)
  simulation?.stop()
  simulation = null
  if (graphRef.value) {
    d3.select(graphRef.value).selectAll('*').remove()
  }
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.graph-hint { color: var(--ob-text-secondary); font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
.graph-card { position: relative; }
.graph-body { position: relative; height: 560px; }
.graph-canvas { width: 100%; height: 100%; }
.graph-canvas :deep(svg) { display: block; }
.graph-empty-overlay { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: #fff; }
.graph-tooltip {
  position: absolute;
  z-index: 20;
  pointer-events: none;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  padding: 10px 12px;
  max-width: 260px;
  font-size: 12px;
}
.tooltip-name { font-weight: 600; font-size: 14px; }
.tooltip-meta { color: var(--ob-text-secondary); margin: 4px 0 6px; }
.tooltip-link { color: var(--ob-text-secondary); line-height: 1.7; }
</style>
