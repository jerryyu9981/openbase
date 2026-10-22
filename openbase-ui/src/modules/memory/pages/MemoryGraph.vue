<template>
  <PageContainer title="记忆图谱" description="OpenMemory 投影的记忆—实体关系（只读）" test-id="memory-graph-page">
    <div class="page-toolbar">
      <el-button type="primary" :loading="loading" data-test="graph-refresh" @click="load">刷新图谱</el-button>
      <el-switch v-model="showEntities" active-text="显示实体" data-test="graph-show-entities" @change="renderGraph" />
      <span class="graph-hint">数据源：memory_metadata → graph_outbox → graph worker → Neo4j</span>
    </div>

    <el-row :gutter="12" class="mb-16" data-test="graph-stats">
      <el-col :xs="12" :sm="6">
        <el-card shadow="never"><div class="stat-label">记忆节点</div><div class="stat-value">{{ stats.memory_nodes }}</div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="never"><div class="stat-label">实体节点</div><div class="stat-value">{{ stats.entity_nodes }}</div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="never"><div class="stat-label">关系数（当前视图）</div><div class="stat-value">{{ stats.edges }}</div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="never">
          <div class="stat-label">待投影 / 死信</div>
          <div class="stat-value">
            {{ stats.outbox_pending }}<span class="stat-sub"> / {{ stats.outbox_dead }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-alert
      v-if="stats.outbox_dead > 0"
      :title="`存在 ${stats.outbox_dead} 条投影死信，请检查 graph worker 日志并执行 graph_repair --replay`"
      type="error"
      show-icon
      class="mb-16"
      data-test="graph-dead-alert"
    />
    <el-alert
      v-else-if="stats.outbox_pending > 0"
      :title="`${stats.outbox_pending} 条记忆等待图投影（异步，通常数秒内完成）`"
      type="warning"
      show-icon
      class="mb-16"
      data-test="graph-pending-alert"
    />
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

    <el-card body-style="padding: 0" class="graph-card">
      <div v-loading="loading" class="graph-body" data-test="memory-graph">
        <div ref="graphRef" class="graph-canvas" />
        <el-empty
          v-if="!loading && visibleNodeCount === 0"
          description="暂无图谱数据：请先写入记忆，并等待 graph worker 完成投影"
          class="graph-empty-overlay"
          data-test="graph-empty"
        />
      </div>
      <div v-show="tooltipVisible" ref="tooltipRef" class="graph-tooltip" :style="{ left: tooltipPos.left, top: tooltipPos.top }" data-test="graph-tooltip">
        <div class="tooltip-name" :style="{ color: tooltipColor }">{{ hoverNode?.label }}</div>
        <div class="tooltip-meta">{{ tooltipMeta }}</div>
        <div v-if="hoverNode?.node_type === 'memory'" class="tooltip-link">点击节点查看记忆详情</div>
      </div>
    </el-card>
  </PageContainer>
</template>

<script setup lang="ts">
import PageContainer from '@/components/page/PageContainer.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as d3 from 'd3'
import { http } from '@/core/api/http'

interface GraphNode {
  id: string
  label: string
  node_type: string
  memory_type?: string | null
  content?: string | null
  updated_at?: string | null
}

interface GraphEdge {
  source: string
  target: string
  relation: string
}

interface GraphStats {
  memory_nodes: number
  entity_nodes: number
  edges: number
  outbox_pending: number
  outbox_dead: number
}

interface GraphOverview {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: GraphStats
}

interface SimNode extends d3.SimulationNodeDatum {
  id: string
  label: string
  node_type: string
  memory_type?: string | null
  content?: string | null
  updated_at?: string | null
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  relation: string
}

const MEMORY_COLORS: Record<string, string> = {
  persistent: '#6366f1',
  session: '#10b981',
  episode: '#f59e0b',
  graph: '#0ea5e9',
}

const ENTITY_COLORS: Record<string, string> = {
  person: '#8b5cf6',
  organization: '#0ea5e9',
  location: '#14b8a6',
  event: '#f59e0b',
  concept: '#10b981',
  custom: '#94a3b8',
}

const router = useRouter()
const graphRef = ref<HTMLDivElement>()
const tooltipRef = ref<HTMLDivElement>()
const loading = ref(false)
const errorMsg = ref('')
const showEntities = ref(true)
const nodes = ref<GraphNode[]>([])
const edges = ref<GraphEdge[]>([])
const stats = ref<GraphStats>({ memory_nodes: 0, entity_nodes: 0, edges: 0, outbox_pending: 0, outbox_dead: 0 })
const tooltipVisible = ref(false)
const hoverNode = ref<SimNode | null>(null)
const tooltipPos = reactive({ left: '0px', top: '0px' })

let simulation: d3.Simulation<SimNode, undefined> | null = null
let resizeTimer: number | undefined

const visibleNodeCount = computed(() =>
  showEntities.value ? nodes.value.length : nodes.value.filter((node) => node.node_type === 'memory').length,
)

const tooltipColor = computed(() => nodeColor(hoverNode.value))
const tooltipMeta = computed(() => {
  const node = hoverNode.value
  if (!node) return ''
  if (node.node_type === 'memory') {
    return `记忆 · ${node.memory_type || 'unknown'} · ${node.updated_at || '-'}`
  }
  return `实体 · ${node.node_type}`
})

function nodeColor(node: SimNode | GraphNode | null | undefined) {
  if (!node) return '#909399'
  if (node.node_type === 'memory') return MEMORY_COLORS[node.memory_type || 'graph'] || '#6366f1'
  return ENTITY_COLORS[node.node_type] || '#94a3b8'
}

function shortLabel(node: GraphNode) {
  const text = (node.node_type === 'memory' ? node.content || node.label : node.label) || node.id
  return text.length > 18 ? `${text.slice(0, 18)}…` : text
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<{ code: number; message: string; data: GraphOverview }>(
      '/memory-proxy/graph/overview',
      { params: { limit: 120 } },
    )
    const overview = data.data
    nodes.value = overview?.nodes || []
    edges.value = overview?.edges || []
    stats.value = overview?.stats || { memory_nodes: 0, entity_nodes: 0, edges: 0, outbox_pending: 0, outbox_dead: 0 }
    await nextTick()
    renderGraph()
  } catch (e) {
    nodes.value = []
    edges.value = []
    errorMsg.value =
      (e as { response?: { data?: { message?: string } } })?.response?.data?.message || '图谱加载失败，请稍后重试'
    renderGraph()
  } finally {
    loading.value = false
  }
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

  const allowEntity = (node: GraphNode) => showEntities.value || node.node_type === 'memory'
  const visibleNodes = nodes.value.filter(allowEntity)
  if (visibleNodes.length === 0) return
  const visibleIds = new Set(visibleNodes.map((node) => node.id))
  const visibleEdges = edges.value.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))

  const width = canvas.clientWidth || 800
  const height = canvas.clientHeight || 520

  const simNodes: SimNode[] = visibleNodes.map((node) => ({
    id: node.id,
    label: shortLabel(node),
    node_type: node.node_type,
    memory_type: node.memory_type,
    content: node.content,
    updated_at: node.updated_at,
  }))
  const nodeById = new Map(simNodes.map((node) => [node.id, node]))
  const simLinks: SimLink[] = []
  for (const edge of visibleEdges) {
    const source = nodeById.get(edge.source)
    const target = nodeById.get(edge.target)
    if (source && target) simLinks.push({ relation: edge.relation, source, target })
  }

  const svg = d3.select(canvas).append('svg').attr('width', width).attr('height', height)
  const container = svg.append('g')

  svg
    .append('defs')
    .append('marker')
    .attr('id', 'graph-arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22)
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
    .data(simLinks)
    .join('line')
    .attr('stroke', '#c0c4cc')
    .attr('stroke-width', 1.4)
    .attr('stroke-opacity', 0.7)
    .attr('marker-end', 'url(#graph-arrow)')

  const nodeElements = container
    .append('g')
    .selectAll<SVGGElement, SimNode>('g')
    .data(simNodes)
    .join('g')
    .attr('class', 'graph-node')
    .style('cursor', (node) => (node.node_type === 'memory' ? 'pointer' : 'default'))
    .call(dragBehavior())

  nodeElements
    .append('circle')
    .attr('r', (node) => (node.node_type === 'memory' ? 20 : 13))
    .attr('fill', (node) => nodeColor(node))
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 2)

  nodeElements
    .append('text')
    .attr('dy', (node) => (node.node_type === 'memory' ? 34 : 26))
    .attr('text-anchor', 'middle')
    .attr('font-size', 11)
    .attr('fill', '#303133')
    .text((node) => node.label)

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
    .on('click', (_event: MouseEvent, node: SimNode) => {
      if (node.node_type === 'memory') router.push(`/memory/${node.id}`)
    })

  const zoomBehavior = d3
    .zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.3, 3])
    .on('zoom', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
      container.attr('transform', event.transform.toString())
    })
  svg.call(zoomBehavior)

  simulation = d3
    .forceSimulation<SimNode>(simNodes)
    .force('link', d3.forceLink<SimNode, SimLink>(simLinks).id((node) => node.id).distance(90).strength(0.5))
    .force('charge', d3.forceManyBody<SimNode>().strength(-260))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide<SimNode>().radius(36))

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
  tooltipVisible.value = true
  window.requestAnimationFrame(() => {
    const canvas = graphRef.value
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    tooltipPos.left = `${event.clientX - rect.left + 14}px`
    tooltipPos.top = `${event.clientY - rect.top + 14}px`
  })
}

function handleResize() {
  window.clearTimeout(resizeTimer)
  resizeTimer = window.setTimeout(() => renderGraph(), 200)
}

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  window.clearTimeout(resizeTimer)
  simulation?.stop()
  simulation = null
  if (graphRef.value) d3.select(graphRef.value).selectAll('*').remove()
})
</script>

<style scoped>
.graph-hint { color: var(--ob-text-secondary); font-size: 13px; }
.mb-16 { margin-bottom: 16px; }
.stat-label { color: var(--ob-text-secondary); font-size: 12px; }
.stat-value { font-size: 22px; font-weight: 600; margin-top: 4px; }
.stat-sub { font-size: 14px; color: var(--ob-text-secondary); font-weight: 400; }
.graph-card { position: relative; }
.graph-body { position: relative; height: 520px; }
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
  max-width: 280px;
  font-size: 12px;
}
.tooltip-name { font-weight: 600; font-size: 14px; }
.tooltip-meta { color: var(--ob-text-secondary); margin: 4px 0 6px; }
.tooltip-link { color: var(--ob-text-secondary); line-height: 1.7; }
</style>
