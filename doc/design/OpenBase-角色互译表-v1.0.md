# OpenBase-角色互译表-v1.0（OB-12 角色互译配置文档）

- 文档编号：OB-INTG-P21-OB12-ROLEMAP
- 版本：v1.0.0
- 状态：[Review]（S1b 段随 T6 评审后回写 [Approved]）
- 适用环境：OpenBase 全环境（dps-proxy 出站 X-User-Role 互译；其余系统接入时扩展）
- 作者：P2-1 批次 2（T6）
- 关联设计：OpenBase-P2-1-统一身份协议头与信任链收口设计草案-v1.0.0.md §6（OB-12）

## 修订历史

| 版本 | 日期 | 修订人 | 变更摘要 | 状态 |
|------|------|--------|---------|------|
| v1.0.0 | 2026-09-07 | P2-1 批次 2 | 从设计草案 §6 裁出互译表正文；登记 Q-D-1~Q-D-3 评审结论；代码落点 role_map.py 接线（settings.role_intertranslate → dps 出站翻译） | [Draft]→[Review] |

## 1. 目的与范围

OpenBase 与下游系统（起步 DPS）间角色码粗粒度互译的唯一配置事实源。互译只覆盖粗粒度
语义档，细粒度权限不入互译（最小集 §6.3-3）。

范围：OpenBase 现役角色码（admin/org_admin/org_member/viewer）→ DPS 角色码
（super_admin/org_admin/user）的出站翻译与回译（对账/审计展示）。

## 2. 语义档锚（§6.1）

| 语义档 | rank | 覆盖动作 | OpenBase 现役 code | DPS 角色（起步） | 说明 |
|--------|------|---------|-------------------|------------------|------|
| 管理档（manage） | 3 | 平台/租户级管理 | `admin` | `super_admin` | 起步映射（Q-D） |
| 读写/域管理档（readwrite） | 2 | 域内读写 + 域管理 | `org_admin` | `org_admin` | editor 语义档由 org_admin 承担（Q-D-2） |
| 只读档（readonly） | 1 | 只读 | `org_member`、`viewer` | `user` | 只读语义两码收敛到 DPS user |
| （未映射角色） | — | — | 未知/新 code | — | fail-closed（Q-D-3） |

## 3. 互译表结构（§6.2，三层 JSON 配置化）

互译表 = schema_version + anchors（语义档只读参考）+ systems.<system>. 双向映射。
配置落点：settings `role_intertranslate`（JSON 字符串；示范默认值内置
`protocol_headers/role_map.default_role_intertranslate()`；生产经 .env/配置覆盖）。

```jsonc
{
  "schema_version": 1,
  "reconciled_at": "2026-09-07",
  "anchors": {
    "manage":    {"rank": 3},
    "readwrite": {"rank": 2},
    "readonly":  {"rank": 1}
  },
  "systems": {
    "dps": {
      "openbase_to_target": {
        "admin":      {"target": "super_admin", "anchor": "manage"},
        "org_admin":  {"target": "org_admin",   "anchor": "readwrite"},
        "org_member": {"target": "user",        "anchor": "readonly"},
        "viewer":     {"target": "user",        "anchor": "readonly"}
      },
      "target_to_openbase": {
        "super_admin": {"source": ["admin"]},
        "org_admin":   {"source": ["org_admin"]},
        "user":        {"source": ["org_member", "viewer"]}
      }
    }
  }
}
```

## 4. 校验规则（§6.2，validate_role_map）

1. JSON 合法、schema_version=1；
2. code 集合法：源 code ∈ 现役 OpenBase 码集（editor/幽灵码拒绝，Q-D-2）；
   已登记目标枚举（dps）的 target/回译目标码 ∈ 目标枚举；
3. 无重复源：回译单目标 source 列表不得重复；
4. 无越档：语义档 rank 单调不减（源 rank ≥ 目标 rank）；升档（如 org_member→
   super_admin）→ 配置非法；
5. 双向逆一致：target_to_openbase 与 openbase_to_target 逐目标互逆。

配置校验失败 → fail-fast（装配/verify-env 拒绝带病启动），不得静默降 viewer。

## 5. 出站翻译挂点（§6.3）

- 唯一挂点：`protocol_headers/inject.build_outbound_headers(..., target_system, role_map)`
  ——目标系统配置互译表时对 `X-User-Role` 翻译（dps-proxy 起步；
  dps `_build_identity_headers` 经 settings.role_intertranslate 装配 role_map）。
- 无互译表系统（llm/rag/memory v1.0）原样透传 OpenBase 角色码（下游语义自行解释）。
- 翻译只作用于主体解析出的有效角色；显式默认角色（如 dps 历史语义 "user"）为目标侧
  原生码，原样透传。
- 无映射角色请求 → fail-closed：出站装配抛 403（不静默降 viewer）。

## 6. Q-D 评审结论记录（§6.4，T6-6 回写）

| Q-D 项 | 本批次结论 | 状态 |
|--------|-----------|------|
| Q-D-1 起步范围 | 仅 OpenBase↔DPS 起步（manage/readwrite/readonly 三档语义均已纳入
  org_admin 对账结论）；其余系统接入时扩展 | [确认] |
| Q-D-2 editor 语义档 | 现役 code 无 `editor`；editor（读写/域管理）档由 `org_admin`
  承担，`editor` 不入互译表（editor 不入互译表，避免幽灵码；editor 不入现役码集常量） | [确认] |
| Q-D-3 未映射 fail-closed 形态 | 拒绝（403）优先于降级提示（默认 viewer） |
  [确认] |

评审人：P2-1 批次 2 设计评审（S1b 门禁项 T6-6）；遗留：真实 DPS 角色对账双签随
R5 联调用例（§6.3 DPS 侧配合点）。

## 7. 测试与验收锚点

- 测试载体：`tests/test_role_intertranslate.py`（T6-1~T6-6）。
- 验收：语义档映射绿、回译逆一致、越档配置拒绝、无映射角色 fail-closed 403、
  Q-D 结论记录回写。
