# OpenBase 非功能设计说明 - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | SA-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/design/ |

---

## 1. 性能设计

| 指标 | 目标值 | 度量方式 |
|------|:------:|----------|
| dps-proxy 非流式转发 P95 | ≤ 500ms（不含 DPS 处理） | Step 4 性能快检（多次采样） |
| 画像列表 P95 | ≤ 300ms | Step 4 性能快检 |
| 超时控制 | dps_upstream_timeout=20s | httpx timeout |

## 2. 安全设计

| 项 | 方案 |
|----|------|
| 认证边界 | OpenBase JWT 唯一入口（未认证 401）；身份头由 proxy 构造（前端不可伪造/自定义） |
| 输入校验 | Pydantic schema（person_id/task_id 路径参数）；请求体透传上游校验 |
| 敏感信息 | 日志不记录 Authorization/身份头完整值/密钥；无 dps_api_key |
| 网络约束 | DPS 8030 仅内网访问（部署约束） |

## 3. 可靠性设计

| 项 | 方案 |
|----|------|
| 上游不可达 | BaseError(SYS_UPSTREAM_ERROR) → 502 |
| 错误归一化 | {code,message,data} + {detail}（str/dict/list）统一提取 |
| 幂等 | proxy 无状态转发（GET 幂等）；POST calculate 为上游语义 |

## 4. 兼容性设计

| 项 | 方案 |
|----|------|
| 既有端点 | llm_proxy/rag_proxy/memory_proxy/gateway 无回归（全量测试） |
| 前端 | 不直连 DPS；沿用 http.ts 统一响应解析 |
| 无 SSE | DPS 无流式端点（不适用 SSE 透传，与 llm/rag-proxy 差异记录） |

## 5. 可维护性设计

| 项 | 方案 |
|----|------|
| 模块结构 | dps_proxy 对标 rag_proxy（认证门禁/转发/响应适配 + 身份头构造） |
| 配置集中 | settings dps_* 前缀（dps_upstream_base/timeout/default_*/map） |
| 命名 | 模块 dps_proxy；路由 dps-proxy；配置 dps_* |

## 6. 可观测性设计

| 项 | 方案 |
|----|------|
| 日志 | 结构化日志（logging + extra），logger "openbase.dps_proxy"；extra: path/upstream_status/duration_ms |
| 指标 | 复用 observability 模块（http 指标挂 path 标签） |
| 告警 | Dev 环境无告警配置（Pro 部署时配置） |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | SA-OpenBase-Dev | 初始创建：性能/安全/可靠性/兼容性/可维护性/可观测性设计 |
