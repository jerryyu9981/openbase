/**
 * 批次 5：知识库全生命周期回归
 *
 * 覆盖 AC-KB-1~8：真实集合/文档加载、上传轮询、重建索引、删除、
 * 纯检索与 RAG 问答双模式、集合配置更新（rebuild）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus, { ElMessageBox } from 'element-plus'

const ragMocks = vi.hoisted(() => ({
  getCollection: vi.fn(),
  listDocuments: vi.fn(),
  getDocument: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  retryDocument: vi.fn(),
  retrieve: vi.fn(),
  query: vi.fn(),
  updateCollection: vi.fn(),
}))

vi.mock('@/core/api/rag', () => ({ ragApi: ragMocks }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: 'kb-1' } }) }))

import KnowledgeDetail from '@/modules/knowledge/pages/KnowledgeDetail.vue'

const dialogStub = {
  props: ['modelValue', 'title'],
  template: '<div v-if="modelValue"><slot /><slot name="footer" /></div>',
}

function mountPage() {
  return mount(KnowledgeDetail as never, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' }, ElDialog: dialogStub },
      mocks: { $router: { push: vi.fn() } },
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never)
  ragMocks.getCollection.mockResolvedValue({
    id: 'kb-1',
    name: '产品知识库',
    description: '产品文档',
    chunk_strategy: 'structured',
    chunk_size: 1024,
    chunk_overlap: 128,
    document_count: 1,
  })
  ragMocks.listDocuments.mockResolvedValue({
    items: [{ id: 'd1', filename: 'manual.md', status: 'COMPLETED', chunk_count: 12 }],
    total: 1,
  })
  ragMocks.getDocument.mockResolvedValue({ id: 'd2', filename: 'new.md', status: 'COMPLETED' })
  ragMocks.uploadDocument.mockResolvedValue({ status: 'PENDING', document_id: 'd2' })
  ragMocks.retrieve.mockResolvedValue({
    items: [{ chunk_id: 'c1', content: '部署步骤：先安装依赖', score: 0.88 }],
    total: 1,
  })
  ragMocks.query.mockResolvedValue({
    answer: '请先安装依赖再启动服务。',
    sources: [{ chunk_id: 'c1', doc_name: 'manual.md', snippet: '安装依赖后启动', score: 0.9 }],
  })
  ragMocks.updateCollection.mockResolvedValue({ id: 'kb-1', name: '产品知识库', chunk_size: 2048 })
})

describe('批次 5：知识库详情真实数据', () => {
  it('集合与文档均来自 API，不含硬编码假数据（AC-KB-1/2）', async () => {
    const wrapper = mountPage()
    await flushPromises()

    expect(ragMocks.getCollection).toHaveBeenCalledWith('kb-1')
    expect(ragMocks.listDocuments).toHaveBeenCalledWith('kb-1', { page: 1, page_size: 50 })
    expect(wrapper.text()).toContain('产品知识库')
    expect(wrapper.text()).toContain('manual.md')
    expect(wrapper.text()).toContain('完成')
    expect(wrapper.text()).not.toContain('快速开始.md')
    expect(wrapper.text()).not.toContain('API 参考.pdf')
  })

  it('上传后轮询至终态并刷新列表（AC-KB-3）', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const upload = wrapper.findComponent({ name: 'ElUpload' })
    const httpRequest = upload.props('httpRequest') as (options: { file: File }) => Promise<void>
    await httpRequest({ file: new File(['hello'], 'new.md') })
    await flushPromises()

    expect(ragMocks.uploadDocument).toHaveBeenCalledWith('kb-1', expect.any(File))
    expect(ragMocks.getDocument).toHaveBeenCalledWith('kb-1', 'd2')
    // 首屏 1 次 + 上传完成后刷新 1 次
    expect(ragMocks.listDocuments).toHaveBeenCalledTimes(2)
  })

  it('重建索引调用 reindex 接口并刷新（AC-KB-4）', async () => {
    const wrapper = mountPage()
    await flushPromises()

    await wrapper.find('[data-test="doc-reindex"]').trigger('click')
    await flushPromises()

    expect(ragMocks.retryDocument).toHaveBeenCalledWith('kb-1', 'd1')
    expect(ragMocks.listDocuments).toHaveBeenCalledTimes(2)
  })

  it('删除文档需二次确认后调用删除接口（AC-KB-5）', async () => {
    const wrapper = mountPage()
    await flushPromises()

    await wrapper.find('[data-test="doc-delete"]').trigger('click')
    await flushPromises()

    expect(ElMessageBox.confirm).toHaveBeenCalled()
    expect(ragMocks.deleteDocument).toHaveBeenCalledWith('kb-1', 'd1')
    expect(ragMocks.listDocuments).toHaveBeenCalledTimes(2)
  })

  it('纯检索调用 retrieve 并渲染片段（AC-KB-6）', async () => {
    const wrapper = mountPage()
    await flushPromises()

    await wrapper.find('input[data-test="retrieval-query"]').setValue('如何部署')
    await wrapper.find('[data-test="retrieval-run"]').trigger('click')
    await flushPromises()

    expect(ragMocks.retrieve).toHaveBeenCalledWith('kb-1', { query: '如何部署', top_k: 5 })
    expect(ragMocks.query).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="retrieval-result"]').text()).toContain('部署步骤')
  })

  it('RAG 问答调用 query 并渲染答案与来源（AC-KB-6）', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const radios = wrapper.findAll('input[type="radio"]')
    await radios[1].setValue(true)
    await wrapper.find('input[data-test="retrieval-query"]').setValue('怎么启动')
    await wrapper.find('[data-test="retrieval-run"]').trigger('click')
    await flushPromises()

    expect(ragMocks.query).toHaveBeenCalledWith('kb-1', { query: '怎么启动', top_k: 5 })
    expect(wrapper.find('[data-test="rag-answer"]').text()).toContain('请先安装依赖')
    expect(wrapper.find('[data-test="rag-source"]').text()).toContain('manual.md')
  })

  it('分块配置变更时确认并以 rebuild=true 提交（AC-KB-7/8）', async () => {
    const wrapper = mountPage()
    await flushPromises()

    await wrapper.find('[data-test="collection-edit-open"]').trigger('click')
    const numberInputs = wrapper.findAllComponents({ name: 'ElInputNumber' })
    await numberInputs[0].vm.$emit('update:modelValue', 2048)
    await wrapper.find('[data-test="collection-edit-save"]').trigger('click')
    await flushPromises()

    expect(ElMessageBox.confirm).toHaveBeenCalled()
    expect(ragMocks.updateCollection).toHaveBeenCalledWith(
      'kb-1',
      expect.objectContaining({ name: '产品知识库', chunk_size: 2048 }),
      true,
    )
  })
})
