# OpenBase-G5-OBS 迁移窗口执行单-v1.1.0

| 项目 | 内容 |
|------|------|
| 文档名称 | G5-OBS（OpenMemory 历史 `default` 域记忆迁移 + 租户头开关灰度）迁移窗口执行单 |
| 文档编号 | OB-G5-OBS-MIG-v1.1.0 |
| 版本 | **v1.1.0** |
| 状态 | **[Final]**（T5 迁移、T6 开关、AC-MT-2~6 全部执行完成并留证） |
| 编制日期 | 2026-10-18（首版）/ 2026-10-19（执行回填） |
| 编制人 | OpenBase 架构组 |
| 裁定人 | 项目负责人（MQ1=A / MQ3=A，2026-10-19） |
| 关联立项方案 | 《OpenBase-G5-OBS-Memory跨租户隔离修复立项方案-v1.1.0》§4/§5/§6 |
| 关联清单 | 《OpenBase-主备双通道生产上线必办事项清单-v2.0.0》G5-OBS |
| 关联迁移脚本 | OpenMemory `scripts/migrate_memory_tenant_domain.py` |
| 目标库 | 共享 PostgreSQL `nuct`（schema：`public.memory_metadata` / `openbase.tenants`） |
| 关联开关 | OpenLLM `OPENMEMORY_TENANT_HEADERS`（默认 `false`） |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：迁移前检查、MQ1/MQ3 裁定栏、dry-run/apply/verify/rollback 步骤、T6 灰度与 AC-MT-2~6 验收、回滚与签字 |
| v1.1.0 | 2026-10-19 | OpenBase 架构组 | 执行回填：MQ1=A/MQ3=A 签字；T5 批次 `g5obs-20261019-0113`（41 行）+ `g5obs-20261019-0132`（1 行）；T6 开启；AC-MT-2~6 全 PASS；登记 D20 跨租户 API Key 一致性门禁冲突（探针实例 8012 完成 AC-MT-4/5） |

---

## 1. 范围与前置

### 1.1 范围

- 将 `public.memory_metadata` 中可解析主体的 `tenant_code='default'` 历史行迁移至真实租户域；
- 迁移完成后灰度开启 `OPENMEMORY_TENANT_HEADERS=true`，使新写入按请求 `X-Tenant-ID` 落域；
- **不删除任何数据**；不可解析行保持 `default`，由 MQ1 裁定处置。

### 1.2 前置（全部满足才可进窗口）

| 项 | 要求 | 当前状态 |
|----|------|:--------:|
| T1~T4 | 开关/迁移脚本/单测/目标库 dry-run 完成 | ✅ |
| dry-run 结果 | 迁移窗口实测 `total_default=283`、`migratable=41`、`unresolved=242` | ✅（[migration-dryrun-20261019.json](computer://d:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\s7\g5\migration-dryrun-20261019.json)） |
| 目标库可达 | 共享 PG `nuct`：`public.memory_metadata` / `openbase.tenants` 可读 | ✅ |
| 备份 | 表级备份 `backup_memory_metadata_20261019-011227.dump`（36,331 B，SHA256 `A45C841B…BD49D`） | ✅ |
| 双人 | 执行：OpenBase 架构组；裁定：项目负责人 | ✅ |
| 变更单 | 本执行单（OB-G5-OBS-MIG-v1.1.0）即变更凭据 | ✅ |

## 2. 裁定栏（已签字）

### 2.1 MQ1：242 条不可解析行处置

> 样本 owner 形如 `e2e-user-*` / `e2e-forget-*` / `e2e-decay-*` / `e2e-graph-*`（测试遗留）。

| 选项 | 内容 | 影响 | 勾选 |
|:----:|------|------|:----:|
| **A（推荐）** | 保留 `default`，仅归档清单，不迁移 | 测试数据不进入业务租户域 | ☑ |
| B | 迁移至指定测试租户 `<tenant_code>` | 需确认该租户存在且可承载 | ☐ |
| C | 按保留策略清理（需另行审批，非本单范围） | 不可逆 | ☐ |

裁定人：项目负责人　日期：2026-10-19

### 2.2 MQ3：迁移期间是否暂停 memory 写回

| 选项 | 内容 | 影响 | 勾选 |
|:----:|------|------|:----:|
| **A（推荐）** | 暂停 memory 写回（回写队列暂存），迁移完成后恢复 | 窗口内记忆不实时沉淀，队列可补偿 | ☑ |
| B | 不暂停，迁移后按批次补偿新增 `default` 行 | 需二次迁移，复杂度高 | ☐ |

裁定人：项目负责人　日期：2026-10-19

## 3. 迁移前检查（已执行）

```bash
# 1) 库连通与目标对象存在
psql "$OPENMEMORY_DATABASE_URL" -c "select count(*) from public.memory_metadata where tenant_code='default';"

# 2) 确认迁移批次表不存在或为空（幂等前提）
psql "$OPENMEMORY_DATABASE_URL" -c "\dt public.memory_tenant_migration*"

# 3) 记录基线（行数/租户分布）
psql "$OPENMEMORY_DATABASE_URL" -c "select tenant_code, count(*) from public.memory_metadata group by 1 order by 2 desc;"

# 4) 备份（二选一）
pg_dump "$OPENMEMORY_DATABASE_URL" -t public.memory_metadata -Fc -f backup_memory_metadata_<ts>.dump
```

检查项：

- [x] `openbase.tenants.code` 可读，41 行对应租户码全部存在（`tenants=19`）
- [x] 无长事务/锁等待
- [x] 回写队列已按 MQ3 处置（OpenLLM 8001 已停止，写回暂停）
- [x] 变更单号（本单）、执行人、裁定人已登记

基线：`default=283 / total=321 / tenants=19 / migration_tables=0`。

## 4. 执行步骤（T5，已执行）

```bash
# 4.1 dry-run（不写库）
python scripts/migrate_memory_tenant_domain.py --dry-run --dsn "$OPENMEMORY_DATABASE_URL"

# 4.2 apply（单事务 + 批次号）
python scripts/migrate_memory_tenant_domain.py --apply \
  --batch-id g5obs-20261019-0113 --operator OpenBase-Arch --dsn "$OPENMEMORY_DATABASE_URL"

# 4.3 verify（按租户聚合 + 可解析集合无 default 残留）
python scripts/migrate_memory_tenant_domain.py --verify \
  --batch-id g5obs-20261019-0113 --dsn "$OPENMEMORY_DATABASE_URL"

# 4.4 幂等复验（第二次 apply 影响行数必须为 0）
python scripts/migrate_memory_tenant_domain.py --apply \
  --batch-id g5obs-20261019-0113-idem --operator OpenBase-Arch --dsn "$OPENMEMORY_DATABASE_URL"

# 4.5 T6 开启后新增 default 行的收口（探针早期失败写入 1 行）
python scripts/migrate_memory_tenant_domain.py --apply \
  --batch-id g5obs-20261019-0132 --operator OpenBase-Arch --dsn "$OPENMEMORY_DATABASE_URL"
python scripts/migrate_memory_tenant_domain.py --verify \
  --batch-id g5obs-20261019-0132 --dsn "$OPENMEMORY_DATABASE_URL"
python scripts/migrate_memory_tenant_domain.py --apply \
  --batch-id g5obs-20261019-0132-idem --operator OpenBase-Arch --dsn "$OPENMEMORY_DATABASE_URL"
```

实际结果：

| 步骤 | 结果 | 证据 |
|------|------|------|
| dry-run | `total_default=283 / migratable=41 / unresolved=242` | `migration-dryrun-20261019.json` |
| apply `g5obs-20261019-0113` | `updated_rows=41` | `migration-apply-g5obs-20261019-0113.json` |
| verify `…-0113` | `by_tenant {"tenant-1":41}`、`leftover_default=0`、`passed=true` | `migration-verify-g5obs-20261019-0113.json` |
| 幂等 `…-0113-idem` | `updated_rows=0` | `migration-idem-g5obs-20261019-0113.json` |
| apply `g5obs-20261019-0132` | `updated_rows=1`（T6 开启后收口） | `migration-apply-g5obs-20261019-0132.json` |
| verify `…-0132` | `by_tenant {"tenant-1":1}`、`leftover_default=0`、`passed=true` | `migration-verify-g5obs-20261019-0132.json` |
| 幂等 `…-0132-idem` | `updated_rows=0` | `migration-idem-g5obs-20261019-0132.json` |
| 不可解析行 | 242 行保持 `default`（MQ1=A） | 同 dry-run |

> 缺陷修复：首次 apply 因「先查批次表、后建表」触发 `UndefinedTableError`（D-3）；已将 `ensure_schema()` 调整到批次查重之前（OpenMemory `scripts/migrate_memory_tenant_domain.py`）。

## 5. T6：开关灰度与验收

### 5.1 开启

```dotenv
OPENMEMORY_TENANT_HEADERS=true
```

- 生产 overlay（`start-openllm-prod.ps1`）注入 `OPENMEMORY_TENANT_HEADERS=true` 并重启 OpenLLM（8001）；
- OpenMemory 受信来源包含 `openbase-orchestrator`，出站 `X-Tenant-ID` 方可被采纳为数据域。

### 5.2 验收（AC-MT-2~6，全部 PASS）

| 编号 | 判据 | 实测 | 证据 |
|------|------|------|:----:|
| AC-MT-2 | 新写入落 `X-Tenant-ID` 指定域 | 直查 `public.memory_metadata`：2 行均 `tenant_code=tenant-1`、`owner=tenant-1_user-1`，无 `default` 残留 | ✅ `ac-mt-2.json` |
| AC-MT-3 | 跨租户不可见 | tenant-1 正例命中 1 条；tenant-2 同一 query 返回 0 条（marker 不可见） | ✅ `ac-mt-3.json` |
| AC-MT-4 | B/A 同域 | B（OpenLLM writeback）写入 → A（OpenMemory 直连 recall）命中；DB `tenant_code=tenant-1`、`owner=tenant-1_1` | ✅ `ac-mt-4.json` |
| AC-MT-5 | 三路回写 | 三路 `accepted=true`；async 首投 `duplicated=false`、复投三路 `duplicated=true`；memory/rag 落 `tenant-1`、profile 落 `tenant-1_1` | ✅ `ac-mt-5.json` |
| AC-MT-6 | 迁移幂等 | 批次 `…-0132` verify PASS，二次 apply `updated_rows=0` | ✅ `ac-mt-6.json` |

### 5.3 执行发现：D20 与跨租户 API Key 写冲突（需 OPS 裁定）

- 现象：在生产 overlay（`ENV=production` + `TENANT_HEADER_CONSISTENCY_ENFORCE=true`）下，以默认租户（`default-tenant`）归属的 API Key 携带 `X-Tenant-ID: tenant-1` 调用 `/openllm/v1/writeback` → **403「入站租户标识与 API Key 归属租户不一致」**。
- 原因：D20 门禁要求「受信来源 + API Key 通道」的 `X-Tenant-ID` 必须等于 API Key 所有者所属租户码；OpenLLM 侧现有 API Key 均归属 `default-tenant`，无 `tenant-1` 归属主体。
- 影响：若生产 B 通道以**单一服务账号 API Key** 承载多租户写入，跨租户写路径会被 D20 拦截。
- 本次处置：AC-MT-4/5 在与生产同真实数据面开关、仅 `ENV=staging` + `TENANT_HEADER_CONSISTENCY_ENFORCE=false` 的**隔离探针实例 8012** 上完成（未改动生产实例配置）；证据 JSON 内 `openllm_base` 与 `probe_note` 已如实标注。
- 待办（阻断上线）：OPS/LL 需在「按租户配置归属一致的 API Key」与「调整 D20 策略」之间裁定，并补一条生产实例上的跨租户写验证。

## 6. 回滚

| 级别 | 动作 | 验证 |
|:----:|------|------|
| 开关级 | `OPENMEMORY_TENANT_HEADERS=false` + 重启 | 新写入恢复既有行为；历史数据仍可读 |
| 数据级 | `python scripts/migrate_memory_tenant_domain.py --rollback --batch-id <batch> --dsn ...` | 明细表对应行恢复 `default`；批次状态 `rolled_back` |
| 库级 | 恢复 `backup_memory_metadata_<ts>.dump` | 行数与基线一致 |

任一 AC 失败：先回滚开关，再评估是否回滚数据。

## 7. 记录与证据

| 文件 | 内容 |
|------|------|
| `doc/test/evidence/s7/g5/migration-dryrun-20261019.json` | 迁移窗口 dry-run（283/41/242） |
| `doc/test/evidence/s7/g5/migration-apply-g5obs-20261019-0113.json` | 主批次 apply（41 行） |
| `doc/test/evidence/s7/g5/migration-verify-g5obs-20261019-0113.json` | 主批次 verify（tenant-1:41、leftover 0） |
| `doc/test/evidence/s7/g5/migration-idem-g5obs-20261019-0113.json` | 主批次幂等复跑（0 行） |
| `doc/test/evidence/s7/g5/migration-apply-g5obs-20261019-0132.json` | T6 后收口批次（1 行） |
| `doc/test/evidence/s7/g5/migration-verify-g5obs-20261019-0132.json` | 收口批次 verify |
| `doc/test/evidence/s7/g5/migration-idem-g5obs-20261019-0132.json` | 收口批次幂等复跑（0 行） |
| `doc/test/evidence/s7/g5/ac-mt-2.json` ~ `ac-mt-6.json` | AC-MT-2~6 运行态证据 |
| `doc/tmp/g5obs/backup_memory_metadata_20261019-011227.dump` | 表级备份（36,331 B，不入库） |

## 8. 签字栏

| 角色 | 姓名 / 工号 | 日期 | 结论 |
|------|-------------|------|------|
| 执行人（OpenBase 架构组） | OpenBase-Arch | 2026-10-19 | 已按单执行（T5 两批次 + T6 + AC-MT-2~6） |
| 复核人（OpenBase 架构组） | OpenBase-Arch | 2026-10-19 | 行数/verify/幂等/跨租户不可见复核通过 |
| 裁定人（项目负责人） | 项目负责人 | 2026-10-19 | MQ1=A、MQ3=A；同意开启 T6 |
| 发布负责人 | 待 OPS 指派 | — | 待 D20 冲突裁定后签署 |

## 9. 风险控制

| 风险 | 缓解 |
|------|------|
| 误改他租户数据 | 仅迁移 owner 前缀可解析且租户存在的行；dry-run 样本复核；单事务 + 批次明细 |
| 迁移期间新增 `default` 行 | MQ3 暂停写回；T6 开启后新增 1 行已由批次 `…-0132` 二次收口 |
| 开关开启后历史数据不可见 | 强制 verify 通过后再开 T6；开关可即时回退 |
| 回滚遗漏 | 批次明细表逐行可回退；库级备份兜底 |
| **D20 与跨租户 API Key 写冲突** | 生产实例按单租户 API Key 归属；跨租户写需 OPS 裁定并补生产实例验证（见 §5.3） |
