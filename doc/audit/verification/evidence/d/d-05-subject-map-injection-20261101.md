# D-05 显式主体映射注入模板（P4 批 D，2026-11-01）

> 裁定前提：D-05 采用 **A（显式 `*_SUBJECT_MAP` 主体映射，未映射即拒绝）**（2026-11-01，见残余项方案 §10）。
> 本文件只定义**部署注入口径与核对方法**，不修改任何仓的代码默认值（各仓缺省仍为空映射）。
> 禁止在本文件写入真实 `sub`/用户标识（示例一律用占位符）。

## 1. 适用面核定（实测结论）

| 仓 | 主体映射配置 | 缺省 | 未映射行为 | 落点 |
|---|---|---|---|---|
| OpenLLM | `OPENBASE_SUBJECT_MAP` | 空 | 命中失败即拒绝（RS256 主体无法落地） | `backend/app/security/openbase_jwt.py:133` |
| DPS | `DPS_OPENBASE_SUBJECT_MAP` | 空 | 命中失败即拒绝（与 `IDENTITY_AUTHORITY=openbase` 正交） | `src/identity/openbase_jwt.py:164` |
| OpenRAG | 不适用 | — | 以 OpenBase JWT `sub` 直通 + 受信代理/角色契约口径承载；非受信来源直接 403 | `src/openrag`（E1-5B 验签） |
| OpenMemory | 不适用 | — | 同 OpenRAG（组织/租户码口径 fail-closed） | `src/openmemory/gateway`（E1-5B 验签） |
| OpenBase（控制面） | `OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP` | 空 | 机器主体（服务账号）未映射即拒绝 | `openbase/settings.py`（`parse_service_account_subject_map`） |

**结论**：裁定口径「四仓显式映射」在实现层面收敛为 **OpenLLM / DPS 两仓有映射表**；OpenRAG / OpenMemory 的主体口令由 `sub` 直通 + 受信来源校验承载，**不引入第二套映射**（避免映射漂移与双写）。

## 2. 注入模板（部署窗口执行，参数化占位）

```jsonc
// OpenLLM：OPENBASE_SUBJECT_MAP
{"<openbase-sub>": "<openllm-local-user-id>", "<openbase-sub-2>": "<openllm-local-user-id-2>"}

// DPS：DPS_OPENBASE_SUBJECT_MAP
{"<openbase-sub>": "<dps-local-user-id>"}

// OpenBase 控制面：OPENBASE_SERVICE_ACCOUNT_SUBJECT_MAP（机器主体）
{"<idp-sub>": "<openbase-service-account-subject>"}
```

**注入约束**

1. 仅当 `jwt_require_rs256=true` / `IDENTITY_AUTHORITY=openbase` 生效时注入；`local` 迁移期保持空映射（零行为变化）。
2. 映射键必须为 OpenBase 归一后的统一主体（`sub`），禁止使用邮箱/显示名等可变字段。
3. 映射值必须为**本仓已存在**的用户标识；未建用户先建后映射，禁止映射到不存在的行。
4. 映射表随发布单下发，禁止写入 git、日志、监控标签。

## 3. 变更与审计口径

| 项 | 口径 |
|---|---|
| 变更留痕 | 每次映射变更随发布单记录：变更人、变更时间、新增/删除条数（不记录主体明文列表） |
| 最小校验 | 变更后冒烟：映射主体登录成功 + 未映射主体被拒绝（两向各一次） |
| 回退 | 移除映射项并重启即回到「未映射拒绝」；不涉及数据迁移 |
| 审计 | 拒绝事件走既有鉴权失败审计（`AUTH_*`）；映射表本身不进入请求级审计 |

## 4. 取证状态

- 本地静态核对：**已完成**（键名、缺省值、未映射行为三处落点均实测，见 `d-06-template-key-check-20261101.json`）。
- 生产注入与两向冒烟：**Blocked**（无生产主机访问权，见 `doc/release/OpenBase-生产环境配置下发单-XR-OPS-07-v1.0.0.md`），解除条件为获得生产会话并随发布窗口执行。
