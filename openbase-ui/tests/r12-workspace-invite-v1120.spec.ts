/**
 * v1.12.0 B 批（XR-LLM-06）：工作空间按用户名邀请成员。
 * 覆盖：请求体使用 username、空用户名不发起请求、成员列表展示用户名。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))

import WorkspacesView from '@/pages/platform/identity/WorkspacesView.vue'

const OPENLLM = '/proxy/openllm/api/v1'

function mountPage() {
  return mount(WorkspacesView as never, {
    global: {
      plugins: [ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

const workspace = {
  id: 'ws-1',
  name: '研发空间',
  description: '团队空间',
  owner_id: 'u-1',
  settings: {},
  quota: {},
  status: 'active',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
}

const members = [
  {
    id: 'm-1',
    workspace_id: 'ws-1',
    user_id: 'u-1',
    role: 'admin',
    joined_at: '2026-10-01T00:00:00Z',
    invited_by: null,
    username: 'alice',
    email: 'alice@example.com',
  },
]

type WorkspacesVm = {
  currentWs: typeof workspace | null
  newMemberName: string
  newMemberRole: string
  currentMembers: Array<{ username: string | null }>
  addMember: () => Promise<void>
  openMembers: (row: typeof workspace) => Promise<void>
}

function vmOf(wrapper: ReturnType<typeof mountPage>) {
  return wrapper.vm as unknown as WorkspacesVm
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.get.mockImplementation((url: string) => {
    if (url === `${OPENLLM}/workspaces`) return Promise.resolve({ data: [workspace] })
    if (url === `${OPENLLM}/workspaces/ws-1/resources`) {
      return Promise.resolve({
        data: { workspace_id: 'ws-1', member_count: 1, virtual_key_count: 0, total_requests: 0, total_tokens: 0 },
      })
    }
    if (url === `${OPENLLM}/virtual-keys`) return Promise.resolve({ data: [] })
    if (url === `${OPENLLM}/workspaces/ws-1/members`) return Promise.resolve({ data: members })
    return Promise.resolve({ data: {} })
  })
})

describe('v1.12.0 工作空间按用户名邀请（XR-LLM-06）', () => {
  it('邀请成员时提交 username 而非 user_id', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const vm = vmOf(wrapper)

    vm.currentWs = workspace
    vm.newMemberName = 'alice'
    vm.newMemberRole = 'viewer'
    await vm.addMember()

    expect(mocks.post).toHaveBeenCalledWith(`${OPENLLM}/workspaces/ws-1/members`, {
      username: 'alice',
      role: 'viewer',
    })
  }, 20000)

  it('用户名为空时不发起请求', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const vm = vmOf(wrapper)

    vm.currentWs = workspace
    vm.newMemberName = '   '
    await vm.addMember()

    expect(mocks.post).not.toHaveBeenCalled()
  }, 20000)

  it('成员抽屉加载后展示用户名', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const vm = vmOf(wrapper)

    await vm.openMembers(workspace)
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith(`${OPENLLM}/workspaces/ws-1/members`)
    expect(vm.currentMembers[0].username).toBe('alice')
  }, 20000)
})
