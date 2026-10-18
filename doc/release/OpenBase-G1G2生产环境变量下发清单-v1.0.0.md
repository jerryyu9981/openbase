# OpenBase-G1/G2 生产环境变量下发清单-v1.0.0

| 项目 | 内容 |
|------|------|
| 文档名称 | G1（三 REAL 开关）/ G2（生产门禁 5 组开关）生产环境变量下发清单与校验记录 |
| 文档编号 | OB-GOLIVE-G1G2-ENV-v1.0.0 |
| 版本 | **v1.0.0** |
| 状态 | **[Draft]**（待 OPS 认领窗口并执行下发） |
| 编制日期 | 2026-10-18 |
| 编制人 | OpenBase 架构组 |
| 关联清单 | 《OpenBase-主备双通道生产上线必办事项清单-v1.7.0》G1/G2 |
| 关联执行包 | 《OpenBase-豁免行加固生产窗口执行包-v1.0.0》§7（P2） |
| 关联权限单 | 《OpenBase-豁免行加固生产窗口访问权限申请单-v1.1.0》A-1/A-2/A-3 |
| 代码基线 | OpenLLM `feature/s4-identity-channel-b` @ `93ac545`（v2.19.1） |
| 目标文件 | OpenLLM `backend/.env`（单文件、不入库、最小 ACL） |

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-18 | OpenBase 架构组 | 首次产出：G1/G2 共 10 项开关、生产启动必需项、豁免加固 24 键、码值映射、机械校验与反例验收、回滚与签字栏。**窗口复跑补充**：`OPENRAG_API_KEY` 为 production 必需（缺失时 OpenRAG 401），已加入 §2.5 |

---

## 1. 适用范围与原则

- 仅覆盖 **OpenLLM 生产 `.env`**；OpenBase / OpenMemory / DPS 自身 `.env` 不在本单范围。
- 原则：**先备份、后变更**；**单文件下发**；**密钥不落工单/截图/命令行历史**；**不翻转代码默认值**（仅生产分支强制）。
- 未置真即拒绝启动（fail-closed），见 [config.py](file:///d:/Trae%20CN/myproject/Dev/OpenLLM/backend/app/core/config.py#L906-L965)。

## 2. 变量总表

### 2.1 G1 真实契约开关（5 项）

| 变量 | 期望值 | 敏感级 | 责任 | 说明 |
|------|--------|:------:|:----:|------|
| `OPENLLM_OPENRAG_REAL` | `true` | 低 | LL/OPS | 启用 OpenRAG 真实 `/api/v1/search` 契约 |
| `OPENLLM_OPENMEMORY_REAL` | `true` | 低 | LL/OPS | 启用 OpenMemory 真实 `/api/v1 remember/recall` |
| `OPENLLM_DPS_REAL` | `true` | 低 | LL/OPS | 启用 DPS 真实画像契约 |
| `OPENMEMORY_ENABLED` | `true` | 低 | LL/OPS | OpenMemory 接入总开关 |
| `DPS_ENABLED` | `true` | 低 | LL/OPS | DPS 接入总开关 |

### 2.2 G2 生产门禁（5 项）

| 变量 | 期望值 | 敏感级 | 责任 | 说明 |
|------|--------|:------:|:----:|------|
| `ENFORCE_INBOUND_IDENTITY_HEADERS` | `true` | 低 | LL/OPS | 入站身份头强校验 |
| `RBAC_PERMISSION_ENFORCE` | `true` | 低 | LL/OPS | RBAC 强制期 |
| `TENANT_SCOPE_ENFORCE` | `true` | 低 | LL/OPS | 缺租户标识拒绝 |
| `TENANT_HEADER_CONSISTENCY_ENFORCE` | `true` | 低 | LL/OPS | 头与 API Key 租户一致 |
| `QUOTA_MISSING_FAIL_CLOSED` | `true` | 低 | LL/OPS | 无配额记录 fail-closed |

### 2.3 生产启动必需项（6 项）

| 变量 | 期望值 | 敏感级 | 说明 |
|------|--------|:------:|------|
| `ENV` | `production` | 低 | 触发全部门禁 |
| `DEBUG` | `false` | 低 | 生产禁止调试 |
| `OPENAPI_PUBLIC` | `false` | 低 | 文档面关闭 |
| `SECRET_KEY` | `<32+ 字节随机>` | **高** | 缺失即拒启（[config.py](file:///d:/Trae%20CN/myproject/Dev/OpenLLM/backend/app/core/config.py#L906-L912)） |
| `RBAC_PERMISSION_ENFORCE_MODULES` | `[]` | 低 | `[]`=全部模块纳入强制期（不可写空字符串） |
| `APP_VERSION` | `2.19.1` | 低 | 与发布版本一致，防漂移 |

### 2.4 豁免行加固键（P2 其余，按需保留）

| 变量 | 期望值 | 敏感级 |
|------|--------|:------:|
| `OPENLLM_EXEMPT_MATCH_MODE` | `exact` | 低 |
| `OPENLLM_EXEMPT_ASSERT_ON_STARTUP` | `true` | 低 |
| `OPENLLM_EXEMPT_EXPIRY_ENFORCE` | `true` | 低 |
| `OPENLLM_EXEMPT_AUDIT_ENABLED` | `true` | 低 |
| `OPENLLM_EXEMPT_AUDIT_IP_MODE` | `full` | 低 |
| `OPENLLM_EXEMPT_AUDIT_RETENTION_DAYS` | `90` | 低 |
| `OPENLLM_EXEMPT_RATE_LIMIT_RPM` | `600` | 低 |
| `OPENLLM_METRICS_AUTH_MODE` | `token` | 低 |
| `OPENLLM_METRICS_TOKEN` | `<64 位 hex>` | **高** |
| `OPENLLM_METRICS_TOKEN_PREVIOUS` | 空（轮换期填旧 token） | **高** |
| `OPENLLM_METRICS_ALLOWED_SOURCES` | `<监控采集 CIDR>` | 低 |
| `OPENLLM_HEALTH_DETAIL_MODE` | `trusted-only` | 低 |
| `OPENLLM_HEALTH_TRUSTED_SOURCES` | `<监控/探活 CIDR>` | 低 |
| `OPENLLM_HEALTH_TOKEN` | 空或 `<64 位 hex>` | **高** |

### 2.5 码值映射与 DPS 兜底身份

| 变量 | 期望值 | 敏感级 | 说明 |
|------|--------|:------:|------|
| `DPS_ORG_CODE_MAP` | `{"<本仓org>":"<DPS org uuid>"}` | 低 | 组织码互译 |
| `DPS_TENANT_CODE_MAP` | `{"<本仓tenant>":"<DPS tenant uuid>"}` | 低 | 租户码互译 |
| `OPENBASE_DPS_ORG_MAP` | `{"<org>":"<dps-org>"}` | 低 | OpenBase 代理侧映射 |
| `OPENBASE_DPS_TENANT_MAP` | `{"<tenant>":"<dps-tenant>"}` | 低 | 同上 |
| `OPENBASE_PROXY_CODE_MAP` | `<JSON>` | 低 | 出站租户码登记/兜底 |
| `OPENLLM_DPS_REAL_ORG` | `<DPS 预建组织码>` | 低 | DPS 真实契约兜底身份 |
| `OPENLLM_DPS_REAL_TENANT` | `<DPS 预建租户码>` | 低 | 同上 |
| `OPENLLM_DPS_REAL_USER` | `<DPS 人员 ID>` | 低 | 同上 |
| `OPENLLM_DPS_REAL_ROLE` | `<标准角色码>` | 低 | 需在互译表内（如 `org_member`） |
| `OPENRAG_API_KEY` | `<OpenRAG X-API-Key>` | **高** | **窗口复跑发现**：production 模式 OpenRAG 强制 `X-API-Key`，缺失将导致 `openrag=unavailable`（401）。取值与 OpenRAG `.env::OPENRAG_API_SERVICE_API_KEY` 一致 |
| `OPENMEMORY_API_KEY` | `<OpenMemory API Key>`（如其启用） | **高** | 与 OpenMemory 侧配置一致；未启用可留空 |

> 码值映射必须由生成器产出，禁止手抄：`python scripts/gen_dps_code_map.py --format env`。

## 3. 下发步骤

| 步 | 动作 | 命令 / 判据 |
|:--:|------|-------------|
| 1 | 备份 | `copy .env .env.bak-<YYYYMMDD-HHMM>`，记录 SHA256 |
| 2 | 写入 | 由 OPS 在目标机编辑 `.env`，仅追加/覆盖上表键 |
| 3 | 权限 | 仅服务账号可读（等价 0600）；禁止 git/工单/截图 |
| 4 | 静态校验 | 见 §4 |
| 5 | 重启 | 滚动重启 OpenLLM，等待 `/health` 200 |
| 6 | 正例验收 | 见 §5.1 |
| 7 | 反例验收 | 见 §5.2（在隔离探针/临时目录执行，不触碰生产库） |
| 8 | 留证 | 输出落 `doc/test/evidence/s7/security/exempt-hardening/window-<日期>/` |

## 4. 机械校验命令与预期输出

```bash
# 1) 码值映射由登记式生成（禁止手抄）
python scripts/gen_dps_code_map.py --format env > /tmp/dps_code_map.env

# 2) 严格校验（三项：键齐备 / 值形态 / 目标系统登记）
python scripts/verify_dps_code_map.py --strict
# 期望：RESULT: PASS

# 3) 生产 profile 环境校验
python backend/scripts/verify-env/verify_env.py --profile production --fail-fast \
  --report-out /tmp/verify-env-production.json
# 期望：退出码 0；report 无 FAIL
```

附加自检（不启动服务）：

```bash
# 确认关键键存在且非空（不打印密钥值）
grep -E '^(ENV|DEBUG|OPENAPI_PUBLIC|APP_VERSION|OPENLLM_.*_REAL|OPENMEMORY_ENABLED|DPS_ENABLED|ENFORCE_INBOUND_IDENTITY_HEADERS|RBAC_PERMISSION_ENFORCE|TENANT_SCOPE_ENFORCE|TENANT_HEADER_CONSISTENCY_ENFORCE|QUOTA_MISSING_FAIL_CLOSED)=' .env
```

## 5. 验收

### 5.1 正例

| 判据 | 期望 |
|------|------|
| 启动日志 | 含 `豁免行启动断言通过（routes=5）`，无门禁 ERROR |
| `GET /health` | 200，`version=2.19.1`，`postgresql/redis=healthy` |
| 组件真实契约 | `routing_trace.rag_source=external`；OpenMemory 走 `/api/v1/remember`；DPS 画像 `person_id` 与实库一致 |
| `GET /docs`、`/openapi.json` | 404 |
| `GET /metrics`（无 token） | 401 |
| 版本 | `APP_VERSION=2.19.1` |

### 5.2 反例（逐项单独回退验证，验后恢复）

| 编号 | 变更 | 期望 |
|:----:|------|------|
| N-1 | `ENFORCE_INBOUND_IDENTITY_HEADERS=false` | 拒绝启动 |
| N-2 | `RBAC_PERMISSION_ENFORCE=false` | 拒绝启动 |
| N-3 | `TENANT_SCOPE_ENFORCE=false` | 拒绝启动 |
| N-4 | `QUOTA_MISSING_FAIL_CLOSED=false` | 拒绝启动 |
| N-5 | `OPENLLM_METRICS_AUTH_MODE=token` 且 token 为空 | 拒绝启动 |
| N-6 | `SECRET_KEY` 为空 | 拒绝启动 |
| N-7 | `OPENLLM_EXEMPT_EXPIRY_ENFORCE=false` | 拒绝启动 |

## 6. 回滚

1. 恢复 `.env.bak-<时间戳>`；
2. 重启服务；
3. 验证 `/health=200` 与业务抽样；
4. 在证据目录记录回滚原因与时间。

## 7. 签字栏

| 角色 | 姓名 / 工号 | 日期 | 结论 |
|------|-------------|------|------|
| 执行人（OPS） |  |  | 已按清单下发 |
| 复核人（OpenBase 架构组） |  |  | 键值/校验/反例复核通过 |
| 发布负责人 |  |  | 同意进入下一阶段 |

## 8. 证据归档

| 文件 | 说明 |
|------|------|
| `p0-precheck.json` | 版本/端口/DB 预检 |
| `p2-env-diff.json` | 键 diff（不含密钥明文） |
| `p3-startup.json` | 启动断言与正例 |
| `p4-negative.json` | N-1~N-7 反例 |
| `verify-env-production.json` | 环境校验报告 |
