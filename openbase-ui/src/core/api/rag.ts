/**
 * OpenRAG rag-proxy API 封装（v1.4.4 R-380）
 * 全部走 OpenBase /api/v1/rag-proxy/*，前端不直连 OpenRAG（无认证，OpenBase 为唯一认证入口）。
 * 对齐《OpenBase-API接口设计文档-v1.4.4》§1（11 端点）
 */
import { http } from '@/core/api/http'
import { parseSseStream, type SseEvent } from './llm'

export interface RagCollection {
  id: string
  name: string
  description?: string
  chunk_strategy?: string
  chunk_size?: number
  chunk_overlap?: number
  document_count?: number
  status?: string
  created_at?: string
  [key: string]: unknown
}

export interface RagDocument {
  id: string
  filename?: string
  status?: string
  chunk_count?: number
  created_at?: string
  [key: string]: unknown
}

export interface RagSource {
  chunk_id?: string
  content?: string
  score?: number
  doc_name?: string
  snippet?: string
  [key: string]: unknown
}

export interface RagQueryResult {
  answer?: string
  sources?: RagSource[]
  [key: string]: unknown
}

export interface RetrieveItem {
  chunk_id?: string
  content?: string
  score?: number
  retrieval_channel?: string
  [key: string]: unknown
}

export const ragApi = {
  /** 知识库列表（GET /api/v1/rag-proxy/collections） */
  async listCollections(params?: { page?: number; page_size?: number }): Promise<{ items: RagCollection[]; total?: number }> {
    const { data } = await http.get<{ code: number; data: { items: RagCollection[]; total?: number } }>('/rag-proxy/collections', { params })
    return data.data
  },

  /** 创建知识库（POST /api/v1/rag-proxy/collections） */
  async createCollection(payload: { name: string; description?: string; chunk_strategy?: string; chunk_size?: number; chunk_overlap?: number }): Promise<RagCollection> {
    const { data } = await http.post<{ code: number; data: RagCollection }>('/rag-proxy/collections', payload)
    return data.data
  },

  /** 知识库详情（GET /api/v1/rag-proxy/collections/{id}） */
  async getCollection(collectionId: string): Promise<RagCollection> {
    const { data } = await http.get<{ code: number; data: RagCollection }>(`/rag-proxy/collections/${encodeURIComponent(collectionId)}`)
    return data.data
  },

  /** 删除知识库（DELETE /api/v1/rag-proxy/collections/{id}） */
  async deleteCollection(collectionId: string): Promise<unknown> {
    const { data } = await http.delete<{ code: number; data: unknown }>(`/rag-proxy/collections/${encodeURIComponent(collectionId)}`)
    return data.data
  },

  /** 文档上传（POST /collections/{cid}/documents，multipart，异步返回 PENDING） */
  async uploadDocument(collectionId: string, file: File): Promise<{ status: string; document_id: string }> {
    const form = new FormData()
    form.append('file', file)
    const { data } = await http.post<{ code: number; data: { status: string; document_id: string } }>(
      `/rag-proxy/collections/${encodeURIComponent(collectionId)}/documents`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return data.data
  },

  /** 文档列表（GET /collections/{cid}/documents） */
  async listDocuments(
    collectionId: string,
    params?: { page?: number; page_size?: number; status_filter?: string },
  ): Promise<{ items: RagDocument[]; total?: number }> {
    const { data } = await http.get<{ code: number; data: { items: RagDocument[]; total?: number } }>(
      `/rag-proxy/collections/${encodeURIComponent(collectionId)}/documents`,
      { params },
    )
    return data.data
  },

  /** 文档详情（GET /collections/{cid}/documents/{did}，上传异步 PENDING→轮询） */
  async getDocument(collectionId: string, documentId: string): Promise<RagDocument> {
    const { data } = await http.get<{ code: number; data: RagDocument }>(
      `/rag-proxy/collections/${encodeURIComponent(collectionId)}/documents/${encodeURIComponent(documentId)}`,
    )
    return data.data
  },

  /** 删除文档（DELETE /collections/{cid}/documents/{did}） */
  async deleteDocument(collectionId: string, documentId: string): Promise<unknown> {
    const { data } = await http.delete<{ code: number; data: unknown }>(
      `/rag-proxy/collections/${encodeURIComponent(collectionId)}/documents/${encodeURIComponent(documentId)}`,
    )
    return data.data
  },

  /** RAG 查询（POST /collections/{cid}/query，检索 + 生成） */
  async query(collectionId: string, payload: { query: string; top_k?: number; filters?: Record<string, unknown> }): Promise<RagQueryResult> {
    const { data } = await http.post<{ code: number; data: RagQueryResult }>(
      `/rag-proxy/collections/${encodeURIComponent(collectionId)}/query`,
      payload,
    )
    return data.data
  },

  /**
   * RAG 流式（POST /collections/{cid}/query/stream）
   * SSE 逐事件透传：event: start → token×N → done（answer + sources）
   */
  async queryStream(
    collectionId: string,
    payload: { query: string; top_k?: number; collection_ids?: string[] },
    onEvent: (evt: SseEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    // adapter: 'fetch'：浏览器端 XHR 不支持 responseType 'stream'，
    // fetch adapter 返回真实 ReadableStream 供 SSE 逐事件消费
    const resp = await http.post<ReadableStream<Uint8Array>>(
      `/rag-proxy/collections/${encodeURIComponent(collectionId)}/query/stream`,
      { ...payload, stream: true },
      { responseType: 'stream', timeout: 120000, signal, adapter: 'fetch' },
    )
    if (resp.data && typeof resp.data.getReader === 'function') {
      await parseSseStream(resp.data, onEvent)
      return
    }
    // 非流式兜底（上游降级时）
    onEvent({ event: 'done', data: JSON.stringify({}) })
  },

  /** 纯检索（POST /collections/{cid}/query/retrieve） */
  async retrieve(collectionId: string, payload: { query: string; top_k?: number }): Promise<{ items: RetrieveItem[]; total?: number }> {
    const { data } = await http.post<{ code: number; data: { items: RetrieveItem[]; total?: number } }>(
      `/rag-proxy/collections/${encodeURIComponent(collectionId)}/query/retrieve`,
      payload,
    )
    return data.data
  },

  /** 上游健康（GET /api/v1/rag-proxy/health） */
  async getRagHealth(): Promise<{ status: string; components?: Record<string, string> }> {
    const { data } = await http.get<{ code: number; data: { status: string; components?: Record<string, string> } }>('/rag-proxy/health')
    return data.data
  },
}
