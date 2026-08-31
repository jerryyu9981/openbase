# OpenBase Phase 迭代计划 - v1.4.4

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.4 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/version/releases/v1.4.4/ |

---

## 1. Phase 拆分

| Phase | 时间 | 内容 | BL 项 | 里程碑 | 验收重点 |
|-------|------|------|-------|--------|---------|
| Phase 1 | 第 0-0.5 周 | OpenRAG 服务接入：OPENRAG_API_PORT=8010 启动 + /api/v1/system/health 健康检查 + PG/Qdrant 依赖 + 端口治理 | BL-144-01 | M1 OpenRAG 就绪 | 8010 健康检查 200（status=healthy）；依赖可用/降级；与 OpenBase 8000 并存 |
| Phase 2 | 第 0.5-1 周 | 认证边界 + rag-proxy 转发：JWT 门禁 + 知识库/文档/查询核心端点（统一响应 + {detail} 归一化 + SSE 透传） | BL-144-02/03 | M2 认证 + 转发打通 | 未认证 401；≥6 核心端点代理可用；SSE start/token/done 透传 |
| Phase 3 | 第 1-1.5 周 | 前端真实化：知识库管理/ RAG 对话 2 页 mock 替换真实 API（走 proxy） | BL-144-04 | M3 前端真实化 | 2 页真实数据可走查；文档上传 PENDING → 状态轮询 |
| Phase 4 | 第 1.5-2 周 | 联调收尾：知识库→文档→RAG 查询闭环 + 集成测试 + UAT + 回归 + 覆盖率 + 文档 + 发布 | BL-144-05/06/07（+ 全量） | M4 v1.4.4 发布 | 认证→知识库→文档→RAG 查询闭环可用；回归 ≥95%；覆盖率 ≥80%；Step 4/5 文档齐备 |

## 2. 里程碑与依赖

| 里程碑 | 依赖 | 前置 |
|--------|------|------|
| M1 OpenRAG 就绪 | BL-144-01 | v1.4.3（已发布） |
| M2 认证 + 转发打通 | BL-144-02/03 | M1（转发依赖服务就绪） |
| M3 前端真实化 | BL-144-04 | M2（前端依赖 proxy 端点） |
| M4 v1.4.4 发布 | BL-144-01~07（全量） | M3 |

## 3. 关键交付物与接口契约

| 交付物 | 说明 |
|--------|------|
| OpenRAG 服务 | OPENRAG_API_PORT=8010 启动，/api/v1/system/health 通过 |
| 认证边界 | OpenBase JWT 唯一认证入口（rag-proxy 未认证 401）；无上游密钥注入 |
| rag-proxy | OpenBase 侧代理路由（知识库/文档/查询核心端点），统一响应 {code,message,data,timestamp}，{detail} 归一化透传 + SSE start/token/done 透传 |
| OpenRAG 前端 | 知识库管理/ RAG 对话 2 页 mock/占位替换真实 API（走 proxy） |
| 对接完善任务书 | 联调发现的 OpenRAG 侧缺口登记（认证落地/文档异步/错误统一等） |

## 4. 版本成功指标

| 指标 | 目标 |
|------|------|
| OpenRAG 服务 | 8010 健康检查通过，PG/Qdrant 依赖可用或 SQLite 降级 |
| proxy 端点 | 核心业务端点经 OpenBase 代理 ≥6 个，统一响应 + 归一化正确 |
| 前端真实化 | 知识库管理/ RAG 对话 2 页真实 API（走 proxy） |
| 联调闭环 | OpenBase 统一认证 → 知识库→文档→RAG 查询真实闭环 |
| 质量门槛 | 全量回归 ≥95%；覆盖率 ≥80%；无新增 P0/P1；Step 4/5 文档齐备 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | PM-OpenBase-Dev | 初始创建：4 Phase（M1 OpenRAG 就绪 → M4 发布），里程碑依赖清晰 |
