/**
 * 前端 OIDC 集成逻辑单元测试（v1.6.0）
 * 覆盖：parseOidcHash fragment 令牌解析（边界：无 # 前缀/缺 access_token/带 refresh）
 */
import { describe, expect, it } from 'vitest'
import { parseOidcHash } from '@/core/api/auth'

describe('parseOidcHash', () => {
  it('解析完整 fragment（# 前缀）', () => {
    const hash = '#access_token=at-1&refresh_token=rt-1&expires_in=7200'
    expect(parseOidcHash(hash)).toEqual({ access_token: 'at-1', refresh_token: 'rt-1' })
  })

  it('兼容无 # 前缀的输入', () => {
    const hash = 'access_token=at-2&refresh_token=rt-2'
    expect(parseOidcHash(hash)).toEqual({ access_token: 'at-2', refresh_token: 'rt-2' })
  })

  it('缺 access_token 返回空串（供调用方报错）', () => {
    expect(parseOidcHash('#refresh_token=rt-3')).toEqual({ access_token: '', refresh_token: 'rt-3' })
    expect(parseOidcHash('')).toEqual({ access_token: '', refresh_token: undefined })
  })

  it('无 refresh_token 时字段缺省', () => {
    expect(parseOidcHash('#access_token=at-4')).toEqual({ access_token: 'at-4', refresh_token: undefined })
  })
})
