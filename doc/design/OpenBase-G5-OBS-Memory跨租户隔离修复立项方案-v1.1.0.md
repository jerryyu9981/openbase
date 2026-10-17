# OpenBase-G5-OBS Memory 跨租户隔离修复立项方案-v1.1.0

| 项目 | 内容 |
|------|------|
| 文档编号 | OB-GOLIVE-G5-OBS-MEMTENANT-v1.1.0 |
| 版本 | **v1.1.0** |
| 状态 | **[Approved]**（T1~T4 已实施并验证；T5 迁移执行 / T6 开关开启待迁移窗口显式批准） |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |
| 来源 | 《OpenBase-主备双通道生产上线必办事项处置记录-v1.2.0》观测项 **G5-OBS** |
| 关联证据 | `doc/test/evidence/s7/g5/writeback-realface.json`（`observed_domain=default`）；`migration-dry-run-20261018.json` |
| 关联清单 | 《OpenBase-主备双通道生产上线必办事项清单-v1.3.0》G5 |
| 迭代类型 | **跨仓小版本（minor）**：OpenLLM 行为开关 + OpenMemory 数据迁移 + OpenBase 治理验收 |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：G5-OBS 根因、跨仓改动范围、开关与迁移方案、验收判据、回滚与风险 |
| v1.1.0 | 2026-10-18 | OpenBase 架构组 | 状态转 [Approved]；T1~T4 实施完成（OpenLLM 2.18.0 / OpenMemory 7.3.2），T4 目标库 dry-run 实测 279/37/242；T5/T6 待迁移窗口批准 |

---

## 1. 背景与事实

G5 真实面演练（三路回写）确认 **memory 路真实落地**，但落库域为 `default`：

```json
{"content": "…g5-writeback-…", "owner": "tenant-1_1", "tenant_code": "default"}
```

- 表现：B 通道 memory 写入/检索均在 `default` 域，按 `owner` 隔离但**不按租户隔离**；
- 影响：同一实例内不同租户若 owner 键相同（如均使用 `{tenant}_1` 时前缀不同，风险较低；
  但 `default` 域聚合所有租户数据，违反多租户数据面隔离要求）；
- 结论：G5「真实落地」判据成立，但 **memory 跨租户隔离未闭环**，单列本迭代。

## 2. 根因（代码事实）

| 仓 | 位置 | 事实 |
|----|------|------|
| OpenLLM | `app/edgerouter/adapters/openmemory.py::_write_real` | 调用 `client.remember(...)` **不传** per-request 身份头 |
| OpenLLM | `app/edgerouter/adapters/openmemory_client.py::_request` | 已支持 per-request `headers` 合并（`{**self._outbound_headers, **headers, **self._auth_header}`），但上层未传 |
| OpenLLM | `openmemory_client.set_outbound_headers` | 进程级共享头，**全仓无调用方**（与 OpenRAG 修复前同构） |
| OpenRAG（对照） | `app/edgerouter/adapters/openrag.py::_outbound_headers` | 已按请求构造 `build_outbound_headers(target_system="openrag", identity_context=request_context)` 并随调用传入（A1 修复范式） |

结论：OpenMemory 侧**已具备** `X-Tenant-ID` 受信解析能力；缺口在 OpenLLM 适配器**未按请求透传**。

## 3. 方案（跨仓、小版本）

### 3.1 设计原则

1. **不翻转既有默认**：新增开关 `OPENLLM_OPENMEMORY_TENANT_HEADERS` 默认 `false`，出厂行为与现行逐字一致；
2. **按请求构造头**，不写客户端共享状态（并发安全）；
3. **先迁移、后开启**：历史 `default` 域数据必须迁移完成并校验后，才允许在目标环境置 `true`；
4. **可回滚**：开关关闭即回到现行行为；迁移提供反向 SQL。

### 3.2 改动清单

| 仓 | 文件 | 改动 | 版本 |
|----|------|------|------|
| OpenLLM | `app/edgerouter/adapters/openmemory_client.py` | `remember/search/history/forget` 增加可选 `headers` 参数并透传 `_request` | **2.18.0** |
| OpenLLM | `app/edgerouter/adapters/openmemory.py` | 新增 `_outbound_headers(request_context)`（对齐 OpenRAG 范式）；真实模式写入/检索带入 | 同上 |
| OpenLLM | `app/core/config.py` + `.env.example` | 新增 `OPENLLM_OPENMEMORY_TENANT_HEADERS=false`（含生产说明） | 同上 |
| OpenLLM | `tests/unit/test_openmemory_tenant_headers.py` | 新增：头集内容、开关关闭零变化、开关开启按请求透传、并发不串租户 | 同上 |
| OpenMemory | `scripts/migrate_memory_tenant_domain.py`（新增） | 迁移脚本：dry-run / apply / verify / rollback，幂等 | **7.3.2**（如脚本入仓） |
| OpenBase | `doc/design/*`、`doc/release/*`、`doc/test/evidence/s7/g5/**` | 立项/验收/证据归档与清单状态回写 | 文档版本递增 |

### 3.3 出站头口径

`build_outbound_headers(target_system="openmemory", identity_context=request_context)` 产出：

| 头 | 值来源 |
|----|--------|
| `X-Proxy-Source` | `openbase-orchestrator`（编排出站统一来源） |
| `X-Tenant-ID` | `request_context.tenant_code`（M2 数据面隔离键） |
| `X-User-ID` | `request_context.user_id`（含租户前缀的归一主体键） |
| `X-Org-ID` | `request_context.org_id` |
| `X-User-Role` | `request_context.role` |
| `X-Request-Id` | `request_context.request_id` |

> 与 OpenRAG 的差异：memory 额外保留既有 `X-API-Key` + 服务账号 JWT（`_auth_header` 合并顺序不变）。

## 4. 数据迁移

### 4.1 迁移范围

`public.memory_metadata` 中 `tenant_code='default'` 且 `owner` 形如 `{tenant_code}_{user_id}` 的行。

### 4.2 迁移规则（幂等）

```sql
-- 仅迁移 owner 前缀可解析为已登记租户的行；其余保持 default 并登记待人工判定
UPDATE public.memory_metadata m
SET tenant_code = substring(m.owner from '^([a-z0-9][a-z0-9-]*)_')
WHERE m.tenant_code = 'default'
  AND m.owner ~ '^[a-z0-9][a-z0-9-]*_[^_]+$'
  AND EXISTS (
    SELECT 1 FROM openbase.tenants t
    WHERE t.code = substring(m.owner from '^([a-z0-9][a-z0-9-]*)_')
  );
```

### 4.3 执行流程

| 阶段 | 动作 | 通过判据 |
|------|------|----------|
| P1 dry-run | 统计可迁移/不可解析行数，样本抽样 | 输出可复核清单，不写库 |
| P2 apply | 单事务执行 UPDATE + 行数核对 | 更新行数 = dry-run 可迁移数 |
| P3 verify | 按租户聚合 `count(*)`；跨租户查询不可见 | 无 `default` 残留（可解析集合） |
| P4 开启开关 | 目标环境 `OPENLLM_OPENMEMORY_TENANT_HEADERS=true` 灰度 | 新写入 `tenant_code=tenant-1` |
| P5 回滚 | 开关置 `false`；必要时执行反向 UPDATE（按迁移批次号回退） | 回到 `default` 域可读 |

> 迁移脚本须记录批次号、执行人、影响行数、样本 ID，落 `doc/test/evidence/s7/g5/migration-<batch>.json`。

## 5. 验收判据（AC-MT-1~6）

| 编号 | 判据 | 方法 |
|------|------|------|
| AC-MT-1 | 开关关闭：行为与 2.17.x 逐字一致 | 既有 memory 适配器单测 + 回写三路用例 |
| AC-MT-2 | 开关开启：写入落 `X-Tenant-ID` 指定域 | 直查 `memory_metadata.tenant_code` |
| AC-MT-3 | 跨租户不可见：tenant-1 写入，tenant-2 检索不可见 | 双租户检索负向用例（反例自证） |
| AC-MT-4 | B/A 双通道同域：B 写后 A 直连（带同租户头）可读 | `dual_channel_e2e.py` memory 段 PASS |
| AC-MT-5 | G5 三路回写复测：`accepted=true`、`duplicated=true`、memory 落 `tenant-1` | `writeback_realface.py` 复跑 |
| AC-MT-6 | 迁移幂等：重复执行不产生额外变更 | 连续两次 apply，第二次影响行数=0 |

## 6. 风险与回滚

| 风险 | 等级 | 缓解 |
|------|:----:|------|
| 迁移误改他租户数据 | 中 | 仅迁移 owner 前缀可解析且租户存在的行；dry-run 样本复核；单事务 + 批次号 |
| 开关开启后历史 `default` 数据不可见 | 中 | 强制「先 P3 通过再 P4 开启」；开关可随时回退 |
| 客户端 `headers` 参数改动影响既有调用 | 低 | 参数缺省 `None`；合并顺序不变；新增开关默认 `false` |
| 并发串租户 | 低 | 按请求构造头，不改共享状态；新增并发用例 |
| 迁移期间写入 | 中 | 迁移窗口内暂停 memory 写回（队列可暂存）或按批次补偿 |

**回滚**：开关置 `false`（立即）+ 迁移反向 SQL（按批次）→ 回到 2.17.x 行为。

## 7. 实施顺序（跨仓）

| 序号 | 仓 | 任务 | 依赖 |
|:----:|----|------|------|
| T1 | OpenLLM | 客户端 `headers` 参数 + 适配器按请求头 + 开关（默认 false） | 无 |
| T2 | OpenLLM | 单测（头集/零变化/并发/负向） | T1 |
| T3 | OpenMemory | 迁移脚本 dry-run/apply/verify/rollback | T1（口径确认） |
| T4 | OpenMemory | 目标库 dry-run + 样本复核（不写库） | T3 |
| T5 | OpenMemory | 迁移执行 + verify | T4 |
| T6 | OpenLLM | 目标环境开关置 `true`（灰度 tenant-1） | T5 |
| T7 | OpenBase | G5 复测 + 跨租户反例 + `dual_channel_e2e.py` memory 段 | T6 |
| T8 | OpenBase | 证据归档、清单/处置记录回写、G5-OBS 关闭 | T7 |

## 8. 未决事项

| 编号 | 事项 | 建议 |
|:----:|------|------|
| MQ1 | `default` 域中 owner 前缀不可解析的历史数据如何处置 | 保留 `default` 并登记清单，人工判定归档或清理；本迭代不自动删除 |
| MQ2 | OpenMemory 是否需要本仓代码改动 | 当前判断**不需要**（已支持受信 `X-Tenant-ID`）；若 T3 发现缺口则升 7.3.2 |
| MQ3 | 迁移窗口是否暂停 memory 写回 | 建议暂停（回写队列可暂存），避免迁移期间新增 `default` 行 |

---

## 9. 实施记录（v1.1.0，2026-10-18）

### 9.1 代码与开关（T1/T2）

| 仓 | 文件 | 变更 |
|----|------|------|
| OpenLLM | `app/edgerouter/adapters/openmemory_client.py` | `remember/recall/search/history` 新增 per-request `headers` 参数并透传 `_request`（与 `X-API-Key`/共享头合并顺序不变） |
| OpenLLM | `app/edgerouter/adapters/openmemory.py` | 新增 `_tenant_headers(request_context)`（对齐 OpenRAG 范式）；`write/search/history` 在开关开启时携带 |
| OpenLLM | `app/core/config.py` / 根与 backend `.env.example` | 新增 `OPENMEMORY_TENANT_HEADERS=false`（缺省不翻转行为） |
| OpenLLM | `tests/unit/test_openmemory_tenant_headers.py` | 7 例：开关关闭零变化、开启头集、无 tenant 不带头、双租户不串状态、客户端合并/缺省 |
| 版本 | — | OpenLLM **2.18.0** |

**回归**：`test_openmemory_tenant_headers.py` + 既有 OpenMemory 相关用例 **40 passed**。

### 9.2 迁移脚本（T3）

| 项 | 内容 |
|----|------|
| 脚本 | `OpenMemory/scripts/migrate_memory_tenant_domain.py` |
| 能力 | `--dry-run` / `--apply` / `--verify` / `--rollback`；批次表 `memory_tenant_migration` + 明细表 `memory_tenant_migration_item` |
| 安全 | 批次防重、单事务、仅迁移 owner 前缀可解析且租户存在的行、可精确回滚 |
| 测试 | `tests/unit/test_migrate_memory_tenant_domain.py` **6 passed** |
| 版本 | OpenMemory **7.3.2** |

### 9.3 目标库 dry-run（T4，只读）

证据：`doc/test/evidence/s7/g5/migration-dry-run-20261018.json`

| 指标 | 值 |
|------|----|
| `tenant_code='default'` 总行数 | **279** |
| 可迁移（owner 前缀可解析且租户存在） | **37** |
| 不可解析（保持 default，人工判定） | **242**（样本均为 `e2e-user-*`/`e2e-forget-*` 等测试主体） |

### 9.4 未执行项（需显式批准）

| 项 | 原因 |
|----|------|
| T5 迁移执行（`--apply`） | 写共享库，属高影响操作；须迁移窗口 + 双人确认 |
| T6 开关开启（`OPENMEMORY_TENANT_HEADERS=true`） | 依赖 T5 verify 通过；开启前保持 false |
| AC-MT-2/3/4/5 运行态验证 | 依赖 T6；当前仅完成单测与 dry-run |

---

**文档状态**：[Approved]（T1~T4 已闭环；T5/T6 待迁移窗口批准后执行，开启前不改动运行态默认值）
