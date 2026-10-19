# OpenBase-G7-D20跨租户APIKey裁定与生产验证记录-v1.0.0

| 项目 | 内容 |
|------|------|
| 文档名称 | G7（D20 租户一致性门禁与跨租户 API Key 写冲突）裁定与生产验证记录 |
| 文档编号 | OB-G7-D20-v1.0.0 |
| 版本 | **v1.0.0** |
| 状态 | **[Approved]**（方案 ① 执行完成，生产实例验证 PASS） |
| 编制日期 | 2026-10-19 |
| 编制人 | OpenBase 架构组 |
| 裁定人 | 项目负责人（G7 选 ①，2026-10-19） |
| 关联清单 | 《OpenBase-主备双通道生产上线必办事项清单-v2.1.0》G7 |
| 关联记录 | 《OpenBase-主备双通道生产上线必办事项处置记录-v1.7.0》 |
| 关联执行单 | 《OpenBase-G5-OBS迁移窗口执行单-v1.1.1》§5.3（G7 发现来源） |
| 验证证据 | `doc/test/evidence/s7/g5/g7-production-writeback.json` |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-19 | OpenBase 架构组 | 首次产出：G7 冲突复述、方案 ① 裁定、租户/服务账号/API Key 落地、生产实例三路回写验证、DPS 映射依赖、交接与回滚 |

---

## 1. 问题复述

G5-OBS 执行期间发现：生产实例（`ENV=production` + `TENANT_HEADER_CONSISTENCY_ENFORCE=true`）下，归属 `default-tenant` 的 API Key 携带 `X-Tenant-ID=tenant-1` 调用 `/openllm/v1/writeback` 返回：

```
403 入站租户标识与 API Key 归属租户不一致
```

即 D20 要求「受信来源 + API Key 通道」的 `X-Tenant-ID` 必须与 API Key 所有者所属租户码一致。此前 OpenLLM 侧不存在 `tenant-1` 归属的主体，B 通道无法以单一 `default-tenant` 服务密钥承载多租户写入。

## 2. 裁定

**采用方案 ①：按租户发放归属一致的 API Key，保持 D20 强制开启。**

- 不为跨租户写入放宽或关闭 D20；
- OpenLLM 侧新增与 OpenBase 同码的租户 `tenant-1` 及其服务账号，签发归属该租户的 API Key；
- B 通道按数据租户选择对应租户的 Service Key。

方案 ②（放宽受信编排来源的租户一致性）未采纳。

## 3. 落地内容

| 对象 | 结果 |
|------|------|
| 租户 | `tenant_code=tenant-1`，`tenant_id=ae2130a8-14fe-4606-a5cf-09ce75d3d1f1`，名称 `Tenant 1 (G7 service)` |
| 服务账号 | `svc-tenant-1`，角色 `org_admin`，归属上述租户；UUID `15837fe6-53d6-44b9-b894-5280de9a259f` |
| API Key | 名称 `g7-tenant-1-service`，前缀 `sk-openllm-4010c`，Key ID `d73b9386-aba3-434c-a7a3-7d8a3b65e2e6`；重复执行时已撤销上一把 `0c6d83f9-…` |
| 出站映射 | 生产 overlay 的 `DPS_ORG_CODE_MAP` / `DPS_TENANT_CODE_MAP` 增加 `ae2130a8-… → 10000000-…001 / 20000000-…001` |

> 密钥明文与服务账号口令仅落在 `doc/tmp/g7/handoff.txt`（不入库），交付 OPS 后须转入密钥管理系统并轮换。文档与证据只记录 Key ID 与前缀。

## 4. 生产实例验证（8001）

调用方式：`Authorization: Bearer <tenant-1 服务密钥>` + 受信头
`X-Proxy-Source: openbase-llm-proxy`、`X-Tenant-ID: tenant-1`、`X-Org-ID: tenant-1`、`X-User-ID: 1`、`X-User-Role: org_admin`。

| 检查 | 结果 |
|------|:----:|
| D20 强制开关 | `TENANT_HEADER_CONSISTENCY_ENFORCE=true`（生产启动门禁） |
| writeback HTTP | 200，`code=0` |
| 三路 accepted | memory / rag / profile 全 `true` |
| 首投 duplicated | 三路全 `false` |
| memory 落域 | `public.memory_metadata`：`tenant_code=tenant-1`、`owner=tenant-1_1` |
| RAG 落域 | `public.documents`：`tenant_code=tenant-1`，内容含探针标记 |
| profile 落域 | DPS `tenant-1_1.attributes_json` 含 `g7_d20_probe` 标记 |
| 组件健康 | openmemory / openrag / dps / ollama 均 `ok`，`primary_channel=b` |

结论：**PASS**。证据见 [g7-production-writeback.json](computer://d:\Trae CN\myproject\Dev\OpenBase\doc\test\evidence\s7\g5\g7-production-writeback.json)。

> 说明：首次验证因新租户 UUID 未纳入 DPS 码表，profile 路返回 `403 组织不存在`；补齐映射并重启生产实例后复跑通过。该映射属生产环境配置项，已在 §5 列为 OPS 下发要求。

## 5. 运维下发要求

1. **密钥注入**：将 `g7-tenant-1-service` 密钥注入 OpenBase B 通道的租户级配置，按 `tenant_code` 选择 Key；禁止回落到 `default-tenant` 服务密钥承载 `tenant-1` 写入。
2. **DPS 码表**：真实生产环境的 OpenLLM 侧需登记该环境 `tenant-1` 租户 UUID → DPS org/tenant 的映射（本地验证值为 `ae2130a8-…`，生产以实际建租户结果为准）。
3. **密钥轮换**：首次注入完成后轮换一次；后续按密钥管理策略周期轮换，轮换窗口需覆盖旧 Key 有效期。
4. **租户事实源**：OpenBase `openbase.tenants` 仍是租户码唯一事实源；OpenLLM `tenants` 为其服务侧镜像，新增/变更需双写同步并纳入巡检。

## 6. 回滚

| 级别 | 动作 | 验证 |
|:----:|------|------|
| 密钥级 | `DELETE /api/v1/auth/api-keys/{key_id}` 撤销租户级 Key | 旧 Key 调用返回 401 |
| 账号级 | 停用 `svc-tenant-1` | 该账号无法登录/签发新 Key |
| 配置级 | 移除码表中的租户 UUID 映射并重启 | profile 路恢复「组织不存在」；memory/rag 不受影响 |

> 不建议删除 `tenant-1` 租户行（存在用户/密钥关联），以撤销密钥 + 停用账号作为回滚手段。

## 7. 风险与后续

| 风险 | 缓解 |
|------|------|
| 租户级 Key 数量随租户增长 | 按租户签发 + 统一密钥管理；禁止跨租户复用 |
| OpenLLM 租户镜像与 OpenBase 漂移 | 双写同步 + 巡检；以 OpenBase 为唯一事实源 |
| DPS 码表遗漏新租户 UUID | 建租户后强制登记映射；纳入发布前机械校验 |
| 交接明文 | 仅落 `doc/tmp`（不入库），交付后立即轮换并转入密钥管理 |
