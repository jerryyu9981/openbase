# OpenBase-G5-OBS 迁移窗口执行单-v1.0.0

| 项目 | 内容 |
|------|------|
| 文档名称 | G5-OBS（OpenMemory 历史 `default` 域记忆迁移 + 租户头开关灰度）迁移窗口执行单 |
| 文档编号 | OB-G5-OBS-MIG-v1.0.0 |
| 版本 | **v1.0.0** |
| 状态 | **[Draft]**（待迁移窗口批准；MQ1/MQ3 待裁定） |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |
| 关联立项方案 | 《OpenBase-G5-OBS-Memory跨租户隔离修复立项方案-v1.1.0》§4/§5/§6 |
| 关联清单 | 《OpenBase-主备双通道生产上线必办事项清单-v1.7.0》G5-OBS |
| 关联迁移脚本 | OpenMemory `scripts/migrate_memory_tenant_domain.py` |
| 目标库 | 共享 PostgreSQL `nuct`（schema：`public.memory_metadata` / `openbase.tenants`） |
| 关联开关 | OpenLLM `OPENMEMORY_TENANT_HEADERS`（默认 `false`） |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：迁移前检查、MQ1/MQ3 裁定栏、dry-run/apply/verify/rollback 步骤、T6 灰度与 AC-MT-2~6 验收、回滚与签字 |

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
| dry-run 结果 | `total_default=279`、`migratable=37`、`unresolved=242` | ✅（[migration-dry-run-20261018.json](computer://d:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\s7\g5\migration-dry-run-20261018.json)） |
| 目标库可达 | `OPENMEMORY_DATABASE_URL` / `DATABASE_URL` 指向生产共享库 | 待 OPS 确认 |
| 备份 | 库级或表级备份 + 恢复演练 | 待 OPS |
| 双人 | 执行人 + 复核人（DBA/发布） | 待排班 |
| 变更单 | `<CHG-XXXX>` 已批准 | 待补录 |

## 2. 裁定栏（必须签字后执行）

### 2.1 MQ1：242 条不可解析行处置

> 样本 owner 形如 `e2e-user-*` / `e2e-forget-*` / `e2e-decay-*` / `e2e-graph-*`（测试遗留）。

| 选项 | 内容 | 影响 | 勾选 |
|:----:|------|------|:----:|
| **A（推荐）** | 保留 `default`，仅归档清单，不迁移 | 测试数据不进入业务租户域 | ☐ |
| B | 迁移至指定测试租户 `<tenant_code>` | 需确认该租户存在且可承载 | ☐ |
| C | 按保留策略清理（需另行审批，非本单范围） | 不可逆 | ☐ |

裁定人：__________ 日期：________

### 2.2 MQ3：迁移期间是否暂停 memory 写回

| 选项 | 内容 | 影响 | 勾选 |
|:----:|------|------|:----:|
| **A（推荐）** | 暂停 memory 写回（回写队列暂存），迁移完成后恢复 | 窗口内记忆不实时沉淀，队列可补偿 | ☐ |
| B | 不暂停，迁移后按批次补偿新增 `default` 行 | 需二次迁移，复杂度高 | ☐ |

裁定人：__________ 日期：________

## 3. 迁移前检查

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

- [ ] `openbase.tenants.code` 可读，37 行对应租户码全部存在
- [ ] 无长事务/锁等待
- [ ] 回写队列已按 MQ3 处置（暂停或确认可补偿）
- [ ] 变更单号、执行人、复核人已登记

## 4. 执行步骤（T5）

```bash
# 4.1 dry-run（再确认一次，不写库）
python scripts/migrate_memory_tenant_domain.py --dry-run \
  --dsn "$OPENMEMORY_DATABASE_URL"

# 4.2 apply（单事务 + 批次号；双人在场）
python scripts/migrate_memory_tenant_domain.py --apply \
  --batch-id g5obs-<YYYYMMDD-HHMM> --operator <执行人> \
  --dsn "$OPENMEMORY_DATABASE_URL"

# 4.3 verify（按租户聚合 + 可解析集合无 default 残留）
python scripts/migrate_memory_tenant_domain.py --verify \
  --batch-id g5obs-<YYYYMMDD-HHMM> --dsn "$OPENMEMORY_DATABASE_URL"

# 4.4 幂等复验（第二次 apply 影响行数必须为 0）
python scripts/migrate_memory_tenant_domain.py --apply \
  --batch-id g5obs-<YYYYMMDD-HHMM>-idem --operator <执行人> \
  --dsn "$OPENMEMORY_DATABASE_URL"
```

通过判据：

| 项 | 期望 |
|----|------|
| apply 更新行数 | = dry-run `migratable`（本次 37） |
| verify | PASS；可解析集合无 `default` 残留 |
| 批次表 | `public.memory_tenant_migration` 有对应批次，状态 `applied` |
| 明细表 | `memory_tenant_migration_item` 行数 = 37，可按 memory_id 回滚 |
| 幂等 | 第二次 apply 影响 0 行 |

## 5. T6：开关灰度与验收

### 5.1 开启

```dotenv
OPENMEMORY_TENANT_HEADERS=true
```

滚动重启 OpenLLM；先灰度 `tenant-1`，观察一个回写周期。

### 5.2 验收（AC-MT-2~6）

| 编号 | 判据 | 方法 | 结果 |
|------|------|------|:----:|
| AC-MT-2 | 新写入落 `X-Tenant-ID` 指定域 | 直查 `memory_metadata.tenant_code` | ☐ |
| AC-MT-3 | 跨租户不可见 | tenant-1 写入，tenant-2 检索不可见（反例） | ☐ |
| AC-MT-4 | B/A 同域 | `dual_channel_e2e.py` memory 段 PASS | ☐ |
| AC-MT-5 | 三路回写 | `writeback_realface.py`：`accepted=true`、复投 `duplicated=true`、落 `tenant-1` | ☐ |
| AC-MT-6 | 迁移幂等 | 第二次 apply 影响 0 行 | ☐ |

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
| `doc/test/evidence/s7/g5/migration-<batch>.json` | dry-run/apply/verify 输出、行数、样本 ID |
| `ac-mt-2~6` 运行态输出 | 跨租户正/反例、双通道 memory 段、三路回写复测 |
| 变更单与签字页 | 本单 §2/§8 扫描件 |

## 8. 签字栏

| 角色 | 姓名 / 工号 | 日期 | 结论 |
|------|-------------|------|------|
| 执行人（DBA / OPS） |  |  | 已按单执行 |
| 复核人（OpenBase 架构组） |  |  | 行数/verify/幂等复核通过 |
| 发布负责人 |  |  | 同意开启 T6 / 同意回滚 |

## 9. 风险控制

| 风险 | 缓解 |
|------|------|
| 误改他租户数据 | 仅迁移 owner 前缀可解析且租户存在的行；dry-run 样本复核；单事务 + 批次明细 |
| 迁移期间新增 `default` 行 | MQ3 暂停写回；或迁移后二次核对 |
| 开关开启后历史数据不可见 | 强制 verify 通过后再开 T6；开关可即时回退 |
| 回滚遗漏 | 批次明细表逐行可逆；库级备份兜底 |
