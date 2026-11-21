import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ConceptNav from '@/modules/portrait/components/ConceptNav.vue'

const RouterLinkStub = {
  props: ['to'],
  template: '<a :href="to"><slot /></a>',
}

function mountNav(current: 'tag' | 'annotation-template' | 'annotation' | 'portrait-template' | 'portrait') {
  return mount(ConceptNav, {
    props: { current },
    global: { stubs: { RouterLink: RouterLinkStub } },
  })
}

describe('画像域概念分区导航', () => {
  it('五类对象齐全且顺序体现生产到消费链路', () => {
    const wrapper = mountNav('tag')
    const names = wrapper.findAll('.concept-item .name').map((node) => node.text())
    expect(names).toEqual(['标签', '标注模板', '标注', '画像模板', '画像'])
  })

  it('仅当前模块高亮并标记 aria-current', () => {
    const wrapper = mountNav('annotation-template')
    const active = wrapper.findAll('.concept-item.active')
    expect(active).toHaveLength(1)
    expect(active[0].attributes('data-test')).toBe('concept-annotation-template')
    expect(active[0].attributes('aria-current')).toBe('page')
  })

  it('各项跳转到对应功能页', () => {
    const wrapper = mountNav('portrait')
    const hrefs = wrapper.findAll('.concept-item').map((node) => node.attributes('href'))
    expect(hrefs).toEqual([
      '/portrait/dps/tags',
      '/portrait/dps/annotation-templates',
      '/portrait/dps/annotations',
      '/portrait/dps/templates',
      '/portrait/list',
    ])
  })
})
