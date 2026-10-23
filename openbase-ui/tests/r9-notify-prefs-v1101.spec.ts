/**
 * v1.10.1（OB-01）：个人设置「通知偏好」真实读写回归。
 * 覆盖默认值回填、保存透传、Webhook 本地校验、加载失败错误态。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))

vi.mock('@/core/api/http', () => ({ http: mocks }))

import SettingsView from '@/pages/personal/SettingsView.vue'
import { useAuthStore } from '@/core/stores/auth'

function mountPage() {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore()
  return mount(SettingsView as never, {
    global: {
      plugins: [pinia, ElementPlus],
      stubs: { PageContainer: { template: '<div><slot /></div>' } },
    },
  })
}

const profile = {
  id: 1,
  username: 'alice',
  permissions: [],
  display_name: 'Alice',
  email: 'alice@example.com',
  phone: null,
}

const storedPrefs = {
  in_app: true,
  email: true,
  webhook: false,
  webhook_url: null,
  events: { alert: false, approval: true, system: true },
}

beforeEach(() => vi.clearAllMocks())

describe('v1.10.1 通知偏好', () => {
  it('加载时回填后端偏好', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/auth/me') return Promise.resolve({ data: profile })
      if (url === '/auth/notification-preferences') return Promise.resolve({ data: storedPrefs })
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(mocks.get).toHaveBeenCalledWith('/auth/notification-preferences')
    const vm = wrapper.vm as unknown as {
      notifyForm: { email: boolean; in_app: boolean; events: Record<string, boolean> }
    }
    expect(vm.notifyForm.email).toBe(true)
    expect(vm.notifyForm.in_app).toBe(true)
    expect(vm.notifyForm.events.alert).toBe(false)
    expect(wrapper.text()).toContain('通知偏好')
  }, 20000)

  it('保存时透传完整偏好并回填返回值', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/auth/me') return Promise.resolve({ data: profile })
      if (url === '/auth/notification-preferences') return Promise.resolve({ data: storedPrefs })
      return Promise.resolve({ data: {} })
    })
    mocks.put.mockResolvedValue({
      data: {
        in_app: false,
        email: true,
        webhook: true,
        webhook_url: 'https://example.com/hook',
        events: { alert: true, approval: false, system: true },
      },
    })

    const wrapper = mountPage()
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      notifyForm: {
        in_app: boolean
        email: boolean
        webhook: boolean
        webhook_url: string | null
        events: Record<string, boolean>
      }
      handleSaveNotify: () => Promise<void>
    }
    vm.notifyForm.in_app = false
    vm.notifyForm.webhook = true
    vm.notifyForm.webhook_url = 'https://example.com/hook'
    vm.notifyForm.events.alert = true
    vm.notifyForm.events.approval = false

    await vm.handleSaveNotify()
    await flushPromises()

    expect(mocks.put).toHaveBeenCalledWith('/auth/notification-preferences', {
      in_app: false,
      email: true,
      webhook: true,
      webhook_url: 'https://example.com/hook',
      events: { alert: true, approval: false, system: true },
    })
    expect(vm.notifyForm.email).toBe(true)
  }, 20000)

  it('启用 Webhook 但地址非法时本地拦截，不调用保存', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/auth/me') return Promise.resolve({ data: profile })
      if (url === '/auth/notification-preferences') return Promise.resolve({ data: storedPrefs })
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage()
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      notifyForm: { webhook: boolean; webhook_url: string | null }
      handleSaveNotify: () => Promise<void>
    }
    vm.notifyForm.webhook = true
    vm.notifyForm.webhook_url = 'ftp://example.com/hook'

    await vm.handleSaveNotify()
    await flushPromises()

    expect(mocks.put).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="notify-error"]').text()).toContain('http')
  }, 20000)

  it('偏好加载失败时展示错误态', async () => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/auth/me') return Promise.resolve({ data: profile })
      if (url === '/auth/notification-preferences') return Promise.reject(new Error('boom'))
      return Promise.resolve({ data: {} })
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.find('[data-test="notify-error"]').text()).toContain('通知偏好加载失败')
  }, 20000)
})
