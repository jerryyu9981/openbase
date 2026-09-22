# OpenBase 数据库设计文档 - v1.4.8

| 项 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.8（会话编排前置与回写闭环） |
| 文档版本 | v1.0.0 |
| 状态 | [Approved]（2026-09-21 人工批准） |
| 作者 | DA-OpenBase-Dev |
| 创建日期 | 2026-09-21 |
| 更新日期 | 2026-09-21 |
| 存放 | doc/design/ |
| 上游依据 | 《开发需求文档-v1.4.8》§6 数据需求、《会话编排派单-OpenLLM-v1.2.0》§3.3、《系统架构设计文档-v1.4.8》 |

---

## 1. 设计原则

* **本版本不新增独立持久化实体进程**；数据落点复用既有表（`routing_trace`）或独立表（由本设计定稿），数据生命周期按《开发需求文档-v1.4.8》§6。
* **幂等且不丢**（F-08）：回写键回会话维度、序号取持久化来源，禁止进程内计数器。
* **历史兼容**：既有 `writeback.db` 26 行 / 8 会话数据保留 + 迁移说明，不做破坏性删除。
* **可批量导出**：计量回执维度字段（`request_id` / 会话标识 / 模型 / 时间戳）须支持按批导出。
* **参数化 + 敏感脱敏**：SQLAlchemy 参数化查询；计量/回执字段不落令牌/密码/密钥/完整请求体（`core/mask.py` 覆盖凭据模式）。

---

## 2. 数据流概览

```text
聊天请求 ──▶ 编排链路计量埋点 ──▶ routing_trace（计量回执，可批量导出）
              │
              └──▶ 回写回调（memory/rag/profile）──▶ WritebackStore.writeback.db
                                                      (session_id, seq, target) 幂等键
                                                       seq = max_seq+1
会话消息 ──▶ ConversationMessage 表（按新会话标识口径落库与检索）
```

---

## 3. 数据模型设计

### 3.1 `routing_trace` 计量表（DT-148-C1，工装 3 落点定稿）

**决策（AD-12 定稿）**：落点选 **`routing_trace` 表增列**（沿用既有路控/编排追踪表，避免另立表导致口径割裂）；若既有表结构不支持 JSON 分项，则 DDL 增列或旁挂 JSON 列，由 OpenLLM 仓按前置核实 §2.3 回填最终形态。本设计定义逻辑字段集：

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| request_id | string | ✔ | 请求唯一标识（维度字段） |
| session_id | string | — | 会话标识（可选；缺省按用户记账） |
| user_id | string | — | 关联用的落库标识（不作为幂等键） |
| model | string | ✔ | 模型名（维度字段） |
| created_at | datetime | ✔ | 时间戳（维度字段） |
| prompt_total_tokens | int | ✔ | prompt 总 token（工装 1） |
| segment_tokens | json | ✔ | 六段分项：system/profile/memory/rag/history/query |
| memory_items | json | — | 检索快照：条目数、各条 score、实际进入 prompt 条目与 token（工装 2） |
| rag_items | json | — | 同 memory_items（rag 检索快照） |
| attribution_a | json | — | 归因 A 引用检测结果（命中的片段 n-gram/关键词） |
| output_reserve | int | — | 输出 max_tokens 预留（定位分母口径边界，本版仅记录） |
| mask_flag | int | — | 脱敏标记（0/1）；提示字段是否经 `mask.py` 处理 |

> **导出**：款项按 `request_id` + `session_id` 条件批量导出，供工装 7 汇总脚本计算 WCR / 注入覆盖率等指标。

### 3.2 `ConversationMessage` 会话消息表（DT-148-C1，R-396 会话落库）

| 字段 | 类型 | 变更 |
|------|------|------|
| session_id | string | **口径对齐**：与 `OpenLLMChatRequest.session_id` 一致；缺省退化场景按 user 记账 |
| seq / role / content / created_at | ... | 沿用既有 |

> 会话消息落库与检索对齐新会话标识口径（《开发需求文档》§6；AC-148-04 相关）；迁移与既有数据兼容策略见 §4。

### 3.3 `WritebackStore` 回写存储（DT-148-06，幂等键修正落点）

**幂等键**：`(session_id, seq, target)`，其中 `session_id` 必须为真实会话标识，**禁用 `identity.user_id` 顶替**（AC-148-06-1）。

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | string | 真实会话标识（键） |
| seq | int | **`WritebackStore.max_seq(session_id) + 1`**（持久化来源，禁进程内计数器；AC-148-06-2） |
| target | enum(memory/rag/profile) | 回写目标（键） |
| payload | json | `{query, response}`（第三批复写竞争载荷；本版不涉及 F-10 判定但保留结构） |
| status | enum(pending/accepted/duplicated/failed) | 回写回执状态 |
| created_at | datetime | 受理时间戳 |

**既有数据兼容（AD-10）**：既有行（`backend/data/writeback.db`，26 行/8 会话，含 `s1` seq 1..4、`s2` seq 1..8）**保留**；提供迁移说明将既有 `session_id=user_id` 语义标注为「历史按用户记账行」，新写入按真实会话标识——**不做破坏性删除**（AC-148-06-4；R6）。

---

## 4. 迁移与幂等说明

| 项 | 约定 |
|----|------|
| 迁移幂等 | `WHERE NOT EXISTS` 防重；`create_all` 兜底（AGENTS.md §5） |
| 既有行处理 | 保留；仅补迁移说明字段（如 `legacy_user_scoped=1` 标记），不改写既有内容 |
| 序号语义 | 新会话首写必 `seq=1`（`max_seq` 为空时为 1）；重启后再写续接 DB 侧最大序号，**不丢不重**（AC-148-06-3） |
| 多租户 | 会话语义与租户过滤沿用既有实现口径（AGENTS.md §5） |
| 禁用 | 进程内模块级计数器；`recover_pending` 不作为计数器回填手段（派选 §3.2） |

---

## 5. 数据一致性 / 完整性约束

* **硬判据**：重启后回写丢失数 = 0（AC-148-06-3），由 DB `max_seq+1` 保证首次不冲突、重启后续接。
* **回写回执**：三路 `accepted/duplicated/failed` 落地 `WritebackStore.status`，供可查与批量核对（AC-148-05-2）。
* **敏感字段**：`routing_trace` 计量字段与回写 payload **不含**令牌/密码/密钥/完整请求体（AC-148-01-5；需求 §7）。

---

## 6. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-09-21 | DA-OpenBase-Dev | 初始创建。定稿三项数据落点：`routing_trace` 计量表（逻辑字段集 + 批量导出）、`ConversationMessage` 会话块口径对齐、`WritebackStore` 回写存储（会话维度幂等键 + `max_seq+1`）；含既有 26 行/8 会话迁移策略、迁移幂等与硬判据。状态 [Review] |