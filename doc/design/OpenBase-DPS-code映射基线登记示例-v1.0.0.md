# OpenBase-DPS code 映射基线登记示例-v1.0.0（OB-8，P2-1 §7.2）

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-P21-DPSCODEMAP-SAMPLE-v1.0.0 |
| 版本 | v1.0.1 |
| 状态 | [Approved]（2026-09-08 P2-1 S1b 段评审通过：T7 OB-8 登记式基线随实施回写；依据用户对话确认「按这个方案来」） |
| 日期 | 2026-09-07 |
| 上游正文 | 《OpenBase-P2-1-统一身份协议头与信任链收口设计草案》v1.0.0 §7.2 |

> 本文为 DPS org/tenant code→UUID **登记式基线**（`settings.dps_code_map`）的
> 登记纪律、结构与对账说明。示例文件：`config/dps_code_map.example.json`。

## 1. 基线结构（schema_version=1）

```jsonc
{
  "schema_version": 1,
  "source_of_truth": "openbase.tenants.code",
  "last_reconciled_at": "2026-09-07",
  "entries": [
    {"tenant_code": "acme", "dps_org_id": "<uuid>", "dps_tenant_id": "<uuid>",
     "reconciled_at": "2026-09-07", "status": "verified"}
  ]
}
```

- `tenant_code`：OpenBase `tenants.code`（唯一事实源）。
- `dps_org_id` / `dps_tenant_id`：DPS 侧值（登记式 UUID 基线；别名收敛下
  X-Org-ID == X-Tenant-ID，取值一致）。
- `status`：`verified`（已核）/`pending`（待核，禁止参与出站基线）。

## 2. 登记纪律

- **默认无条目（空表）**；`dps_default_org_id/dps_default_tenant_id` 标记
  deprecated（仅显式兜底保留，verify-env WARN）。
- 新租户经迁移/对账工具（`scripts/audit_dps_code_map.py`，T7-7）登记入基线，
  **禁止运行期隐式新增**。
- 以 OpenBase `tenants.code` 为唯一事实源：接入前跑重复 code 对账 → 冲突清单 →
  以 OpenBase 为准重映射 → 留痕（R-L3-1/Q3）。
- 旧 JSON（`dps_org_map/dps_tenant_map`）兼容读取：`build_compat_value_maps`
  将基线条目折算为 org/tenant 值映射并优先于旧表（§11.2 迁移提示）。

## 3. 校验规则（validate_dps_code_map）

JSON 合法；`tenant_code` 须命中 `tenants.code`（或显式别名表）；dps 侧 org/tenant
id 非空；无重复 code；同 code 双映射不同 DPS 值 → 冲突项（S7 前清零）。

## 4. 对账脚本

```bash
python scripts/audit_dps_code_map.py                     # 读 settings（DB 位 best-effort）
python scripts/audit_dps_code_map.py --map-json config/dps_code_map.example.json \
    --tenants-json tenants.json --report out/audit_report.json
```

退出码：0 = 0 未决冲突；1 = 存在未决冲突或校验错误（T7-7 对账门禁）。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 | 状态 |
|------|------|--------|---------|------|
| v1.0.0 | 2026-09-07 | P2-1 批次 3 | 初始版本：登记式基线结构/纪律/校验/对账说明；示例 config/dps_code_map.example.json | [Draft]→[Review] |
| v1.0.1 | 2026-09-08 | P2-1 开发组 | 评审状态回写：P2-1 S1b 段 T7 OB-8 评审通过（依据：用户对话确认「按这个方案来」）；[Review] → [Approved] | [Review]→[Approved] |
