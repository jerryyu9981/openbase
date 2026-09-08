# OpenBase-事件消费契约-v1.0（Q-DESIGN-1 冻结）

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-U1-EVENT-CONTRACT-v1.0 |
| 版本 | v1.0 |
| 状态 | [Frozen]（2026-09-08 经跨项目契约 Q-DESIGN-1 责任登记冻结；OpenMemory S2 消费端按本契约落地） |
| 日期 | 2026-09-08 |
| 责任仓 | OpenBase 主仓（本仓负责契约冻结与端点实现；OpenMemory 仓 S2 段按同一契约消费对接） |
| 作者 | U1 跨项目契约组（Q-DESIGN-1 责任登记） |
| 上游依据 | 《OpenBase-U1-统一身份收口设计草案》v1.1.0 §8（事件 schema v1/outbox/投递通道）；OpenMemory S2 设计草案 Q-DESIGN-1（v1.0.1 §10.1）冻结契约 |
| 适用范围 | OpenMemory（S2）、OpenRAG/OpenLLM/DPS（S3/S5 段同类消费端复用）；OpenBase identity 模块 `/api/v1/identity/events` 实现 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0 | 2026-09-08 | OpenBase U1 跨项目契约组 | 初始冻结：单向事件列表契约（Push/Pull 双通道总览、schema v1 引用、cursor/limit/未知游标/错误码语义定案、示例、验收锚点） |

> 变更纪律：本契约为冻结文档，任何语义变更须走「提出 → 分析 → 更新 → 评审 → 批准」流程并升级版本（主.次.修订），禁止静默修改。

---

## 1. 背景与目的

U1（L1-1）跨系统生命周期级联事件的消费端（DPS/OpenMemory/OpenRAG）需要在数据面落地「停用/注销 → 阻断、恢复 → 解除」语义。OpenBase 侧事件源能力已具备：

- **outbox_events 可靠事件表**（`event_id` 全局唯一、`payload` 为 schema v1 载荷、状态 `pending/published/failed`）；
- **投递器**（`OutboxDispatcherService`：轮询 pending → Redis pub/sub + 本地通道发布 → 置 published；失败退避）；
- **契约桩 API**（`POST /events/apply` 投递+模拟消费、`GET /events/{event_id}` 状态查询、`GET /blocked/{subject_id}` 阻断对账）。

本契约冻结 **单向事件列表 Pull 端点**（`GET /api/v1/identity/events`），作为 Push（Redis pub/sub）之外的**轮询兜底通道**，供消费端断点续拉、全量补拉已发布事件。

## 2. 事件 schema v1（引用 U1 草案 §8.1）

事件载荷（`payload`）遵循《OpenBase-U1-统一身份收口设计草案》v1.1.0 §8.1 **schema v1**（冻结字段），本契约**不重复定义 schema**，仅登记引用与返回形态：

| 字段 | 类型 | 说明 |
|------|------|------|
| `event_id` | string | 全局唯一；**幂等消费键** |
| `event_type` | string | `user.provisioned` / `user.suspended` / `user.restored` / `user.deactivated` |
| `occurred_at` | string(ISO8601 UTC) | 事件发生时刻 |
| `source` | string | 事件源标识（`openbase`） |
| `request_id` | string\|null | 审计透传（U4 预留；可缺省） |
| `subject` | object | `{subject_id(int, users.id), subject_type("user"\|"agent"), username}` |
| `tenant_code` | string\|null | 唯一隔离键 |
| `role_codes` | array\<string> | 角色码快照（可为空数组） |
| `previous_state` | string | 迁移前状态 |
| `current_state` | string | 迁移后状态 |
| `reason` | string\|null | 迁移原因 |
| `schema_version` | int | 恒为 `1` |

列表端点返回的每个事件即为上表**全字段事件载荷**（逐字段透传 outbox `payload`），消费端无需二次映射。

## 3. 消费通道总览

| 通道 | 形态 | 方向 | 语义 | 状态 |
|------|------|------|------|------|
| **Push（主形态）** | Redis pub/sub，频道 `openbase:identity:events`（本地进程通道兜底，Redis 不可用不丢事件） | OpenBase → 消费端 | outbox 投递器在事件 published 时发布；消费端订阅即收；**不保证顺序与恰好一次** | 已具备（U1 T5） |
| **Pull（兜底轮询）** | `GET /api/v1/identity/events?cursor=&limit=`（本契约冻结端点） | 消费端 → OpenBase | 按 (occurred_at, event_id) 稳定序分页返回**已 published** 事件；消费端断点续拉/补拉 | **v1.0 冻结（本次实施）** |

消费端对接约定：

- **OpenMemory（S2）**：真实消费端按本契约对接（Push 订阅 + Pull 兜底轮询 + `event_id` 幂等表去重）；
- **OpenRAG / DPS（S3/S5）**：同类消费端**复用本契约**（同一端点、同一 schema、同一幂等约定），不得另立语义。

## 4. 单向事件列表接口

### 4.1 请求

| 项 | 值 |
|----|-----|
| 方法/路径 | `GET /api/v1/identity/events` |
| 鉴权 | `Authorization: Bearer <JWT>`；须具备 **`identity:view`** 权限（admin 通配放行，与 `GET /events/{event_id}`、`GET /blocked/{subject_id}` 同一读权限模型）；无令牌 → 401；无权限 → 403 |

查询参数：

| 参数 | 类型 | 必填 | 默认 | 语义（定案） |
|------|------|------|------|--------------|
| `cursor` | string | 否 | 无（从头部开始） | **排他游标**：上一页 `next_cursor`（即上一页最后一条已返回事件的 `event_id`）。下一页仅返回**严格晚于** cursor 定位位置的事件，**不含 cursor 自身** |
| `limit` | int | 否 | `50` | 页大小。**服务端钳制上限 `100`**：`limit > 100` 时返回 100 条（不报错）；`limit < 1` → 400 |

### 4.2 响应（200 OK）

```jsonc
{
  "events": [
    {
      "event_id": "uuid",
      "event_type": "user.deactivated",
      "occurred_at": "2026-09-07T00:00:00.123456+00:00",
      "source": "openbase",
      "request_id": null,
      "subject": { "subject_id": 123, "subject_type": "user", "username": "alice" },
      "tenant_code": "acme",
      "role_codes": ["viewer"],
      "previous_state": "active",
      "current_state": "deactivated",
      "reason": "管理员注销",
      "schema_version": 1
    }
  ],
  "next_cursor": "uuid-of-last-event-in-this-page"   // 无更多时为 null
}
```

| 字段 | 类型 | 语义 |
|------|------|------|
| `events` | array\<object> | 已 published 事件（schema v1 全字段载荷），按稳定序返回 |
| `next_cursor` | string\|null | **非空** = 本页之后还有更多，取本页最后一条事件的 `event_id` 作为下页 `cursor`；**null = 无更多**（服务端每页多取一条判定，不依赖“返回条数 == limit”猜测） |

### 4.3 分页 / 游标 / limit 语义（定案）

1. **稳定全序**：事件按 `(created_at, event_id)` 升序返回。`created_at` 为 outbox 行入队落库时刻，与载荷 `occurred_at` **同事务同刻**（同一事件两者同源），故等价于契约要求的 **(occurred_at, event_id) 升序稳定序**；同刻事件以 `event_id` 字典序决胜 → 全序确定、翻页稳定。
2. **cursor 排他上界**：`cursor` 指向上一页最后一条事件，下一页从**该事件之后**继续；上一页事件不会在下一页重复出现。消费端配合 `event_id` 幂等自滤，天然**不重不漏**。
3. **next_cursor 终止语义**：`next_cursor == null` 表示当前无更多已 published 事件（消费端应停止本轮轮询，等待下轮）；以最后一条事件为 cursor 再拉 → 返回空 `events` + `next_cursor=null`。
4. **增量语义**：新事件在稳定序中按序追加，消费端保存上次 `next_cursor` 下次续拉即得增量。
5. **limit 语义**：缺省 `50`；上限 `100`（服务端钳制，超限**不报错**）；`limit < 1` → 400 `PARAM_INVALID`（不可钳制）。
6. **仅 published 事件**：列表只包含 outbox 状态为 `published` 的事件；`pending`/`failed` 事件不出现（failed 为投递终态、不对外广播；pending 由投递器推进后再可见）。

### 4.4 消费端幂等自滤说明

本端点**无 ack、无 consumer 过滤**（不登记消费进度、不按消费端过滤事件）。消费端负责：

- 以 `event_id` 为幂等键本地去重（OpenMemory 侧 `identity_event_consumption` 幂等表，(event_id, consumer) 唯一；S3/S5 同类）；
- **重放（同一事件被再次拉到）不产生重复副作用**；跨页、跨轮、跨通道（Push/Pull 双通道可能收到同一事件）均可靠去重；
- 因 Push/Pull 双通道并存，消费端**不得**假设同一事件只到达一次，但**可**假设同一 event_id 的副作用至多执行一次。

## 5. 错误码

统一错误响应 `{code, message, detail, request_id}`（OpenBase 错误码规范）：

| HTTP | code | 场景（定案） |
|------|------|--------------|
| 401 | `AUTH_UNAUTHORIZED` / `AUTH_TOKEN_INVALID` | 未携带/无效 Bearer 令牌 |
| 403 | `PERM_FORBIDDEN` | 已认证但无 `identity:view` 权限（非 admin） |
| 400 | `PARAM_INVALID` | **未知游标**：`cursor` 对应的 `event_id` 在 outbox_events 中不存在；或对应事件**非 published**（`detail.status` 给出实际状态）。定案：**不静默从头部返回**，返回 400 以便消费端识别游标失效并决定从头部重拉（幂等自滤兜底去重） |
| 400 | `PARAM_INVALID` | `limit < 1`（`detail.field = "limit"`） |
| 422 | `PARAM_VALIDATION_ERROR` | `limit` 非整数等 FastAPI 参数解析失败（标准参数校验） |

> 未知游标定案理由：cursor 指向的事件由服务端此前返回（published 终态不回退），正常消费不会触发；触发即代表消费端本地进度异常或数据被外部干预，静默从头返回会掩盖问题且可能与消费端已处理窗口重叠，故显式 400。

## 6. 示例

### 6.1 首次拉取（头部，limit=2）

```
GET /api/v1/identity/events?limit=2
Authorization: Bearer <admin-or-identity:view-token>
```

```jsonc
{
  "events": [
    { "event_id": "a1", "event_type": "user.provisioned", "occurred_at": "…", "source": "openbase",
      "subject": { "subject_id": 1, "subject_type": "user", "username": "alice" },
      "tenant_code": "acme", "role_codes": ["viewer"],
      "previous_state": "provisioned", "current_state": "active",
      "reason": "activated by operator", "schema_version": 1 },
    { "event_id": "b2", "event_type": "user.suspended", "occurred_at": "…", "source": "openbase",
      "subject": { "subject_id": 2, "subject_type": "user", "username": "bob" },
      "tenant_code": "acme", "role_codes": [],
      "previous_state": "active", "current_state": "suspended",
      "reason": "hold", "schema_version": 1 }
  ],
  "next_cursor": "b2"
}
```

### 6.2 续拉（cursor=b2，limit=100）

```
GET /api/v1/identity/events?cursor=b2&limit=100
Authorization: Bearer <admin-or-identity:view-token>
```

```jsonc
{
  "events": [
    { "event_id": "c3", "event_type": "user.deactivated", "occurred_at": "…", "source": "openbase",
      "subject": { "subject_id": 3, "subject_type": "user", "username": "carol" },
      "tenant_code": "acme", "role_codes": ["viewer"],
      "previous_state": "active", "current_state": "deactivated",
      "reason": "offboard", "schema_version": 1 }
  ],
  "next_cursor": null
}
```

### 6.3 错误示例（未知游标）

```
GET /api/v1/identity/events?cursor=unknown-event-id
```

```jsonc
{
  "code": "PARAM_INVALID",
  "message": "unknown events list cursor",
  "detail": { "field": "cursor", "value": "unknown-event-id", "reason": "event_id not found" },
  "request_id": "req-…"
}
```

## 7. 测试与验收锚点（OpenBase 仓）

`tests/test_identity_events_list.py`（TDD，RED→GREEN）覆盖：分页游标稳定序、无重复无遗漏全量遍历、按 cursor 续拉不重叠、limit 钳制/缺省/limit<1、next_cursor 终止语义、schema v1 字段完整性、仅 published 可见、权限 403、未知/非 published 游标 400。实现对齐本契约第 4/5 节定案。

## 8. 遗留

- **OpenMemory S2-T13 真实双签对接（下一步）**：本契约完成 OpenBase 侧冻结与端点落地；OpenMemory S2 真实消费端按本契约对接（Push 订阅 + Pull 兜底 + `identity_event_consumption` 幂等表），并于双系统联调完成真实双签验证。
- 事件量级增长后如需更强扫描性能，可将 `occurred_at` 提升为 outbox 排序列（契约 v1.x 演进项，不改变本语义）。

---

## 附录 A：术语

| 术语 | 说明 |
|------|------|
| Push 主形态 | Redis pub/sub `openbase:identity:events`（+ 进程内本地通道兜底） |
| Pull 兜底 | `GET /api/v1/identity/events` 单向轮询通道（本契约冻结） |
| cursor | 排他游标（上一页最后一条事件的 `event_id`） |
| published | outbox 投递成功终态（可被本端点列出） |
