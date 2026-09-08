# OpenBase-P2-1-统一身份协议头与信任链收口-DevLogReport-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-P21-DEVLOG-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Review]（P2-1 T1~T10 开发完成；S1b 段门禁五项自检完成（①~④ 全绿 + ⑤ 发布物 [Review] 待人工批准登记）；待测试回溯与人工批准进入部署/S2 移交） |
| 日期 | 2026-09-08 |
| 作者 | P2-1 开发组（OpenBase 主仓） |
| 存放 | doc/development/ |
| 版本主题 | P2-1（S1b 协议与服务段）T1~T10 开发记录（RED/GREEN 断言、改动文件、提交链、回归/覆盖率、S1b 段门禁五项自检、R3 补测与 S2-S5 移交登记） |
| 适用范围 | OpenBase 主仓（openbase/、tests/、scripts/、config/、doc/、仓根 P2-1 立项与设计文档回写） |
| 上游依据 | 《OpenBase-P2-1-统一身份协议头与信任链收口立项方案》v1.1.0（[Approved]；T1~T10 与 §5 验收）；《OpenBase-P2-1-统一身份协议头与信任链收口设计草案》v1.1.0（[Approved]；§10 T1~T10 RED 断言为唯一实现规格）；《OpenBase-多系统联调联试分阶段版本规划（子系统纵切）》v1.3.0（S1b 门禁）；《OpenBase-数据隔离实现任务卡》v1.3.0（K01/K02/K03/K07/K08 与 OB-3/6/8/9/12/13 状态回写） |

> 版本管理：本报告遵循项目文档规范（元信息 + 修订历史 + 随改随提）；与 P2-1 测试报告
> （doc/test/OpenBase-P2-1-统一身份协议头与信任链收口-测试报告-v1.0.0.md）配套交付。
> 纪律：TDD（RED→GREEN，断言先写对齐设计草案 §10）；`ruff` 0；分组回归硬前提；
> 文档与台账按项目版本管理规范回写。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-08 | P2-1 开发组 | 初始版本：T1~T10 逐任务 RED/GREEN 摘要与改动文件、提交链（批次 1/2 25b65d7→9a0aa49 + 批次 3 代码提交 + 本批次文档提交）、分组回归结果、覆盖率与缺口 R3 登记、追溯矩阵、S1b 段门禁五项自检、遗留项登记（R3 补测/评审人工复核点/移交 S2-S5 说明） |

---

## 1. 版本记录与入场检查

| 项 | 内容 |
|----|------|
| 开发范围 | P2-1（S1b）：T1 四头/委托头唯一签发与出站对齐（K01）→ T2 禁旁路 + fail-open 裁定（K03）→ T3 协议头规范 v1.0 发布物 + OpenBase 试点（K02）→ T4 端点-过滤矩阵模板 v1.0（K07）→ T5 OB-6 服务账号受信源收口 → T6 OB-12 角色互译（最小集 §6.3）→ T7 OB-8 code 化收口 → T8 OB-13 审计贯穿（OpenBase 侧）→ T9 OB-9 verify-env 雏形 → T10 回归与 S1b 段门禁收口 |
| 入场确认 | 设计草案 v1.0.0 于 2026-09-08 经人工批准「按草案进入开发阶段」（依据：用户对话确认 Q-D-1~3 与「按这个方案来」，流程批准登记，已回写设计草案 v1.1.0 / 立项方案 v1.1.0） |
| 基线 | main @ 9a0aa49（批次 1/2 收口 HEAD）；批次 1/2 前置提交链 25b65d7 → 51c6657 → 09f28fa → 9a0aa49 |
| 开发纪律 | TDD（RED→GREEN，断言先行对齐设计草案 §10，断言编号 T{n}-{m} 全仓唯一）；ruff 0；`python -m pytest tests` 全绿；分组回归硬前提 |

## 2. 实现内容（T1~T10 逐任务 RED/GREEN 摘要）

> RED 说明：每个任务先写断言测试（对齐 §10 断言编号），在实现落位前运行记录 RED
> （失败/错误断言）；实现落位后再运行转 GREEN。批次 3（T7/T8/T9）的 RED 证据以
> 「受控回退复现」登记：将实现改动临时回退到批次 1/2 基线（git stash + 移出新增实现
> 文件）后运行新断言 → 失败（RED）；恢复实现 → 全绿（GREEN）。断言 RED→GREEN
> 逐条记录见下方各任务小节与测试报告 §3。

### 2.1 T1 四头/委托头唯一签发与出站对齐（K01/OB-3，commit 25b65d7）

- RED→GREEN：`tests/test_protocol_headers_lib.py`（21 例）+ `tests/test_proxy_outbound_matrix.py`（11 例）对齐 §10 T1-1~T1-12（出站矩阵绿 / 伪造头不采信 / sk-agent 经 llm·memory 出站不再 401 / 委托出站唯一签发 / 来源常量单一写法 / 静态扫描 0 第二写法 / X-Proxy-Source 全链透传 / 各 proxy 缺失头补齐 / 匿名不注入伪身份头 / 通用 proxy 双通道 / 委托唯一签发规范文档化 / U1 存量回归）。
- 实现要点：`openbase/modules/protocol_headers/` 共享包（constants/identity_context/validate/inject）；`inject.build_outbound_headers` 唯一装配点；dps/llm/rag/memory/通用 proxy 删除二次解码改统一装配；来源标识常量收口。
- 改动文件：`openbase/modules/protocol_headers/{__init__,constants,identity_context,validate,inject}.py`、`openbase/modules/dps_proxy/__init__.py`、`llm_proxy/__init__.py`、`rag_proxy/__init__.py`、`proxy/memory_proxy.py`、`proxy/__init__.py`、`settings.py` 及配套测试。

### 2.2 T2 禁旁路 + fail-open 裁定落地（K03/OB-3，commit 51c6657）

- RED→GREEN：`tests/test_verdict_k03.py`（14 例）对齐 §10 T2-1~T2-10（V-1~V-5 裁定分支 / D-V6 白名单外写 403 / D-V7 agent DB 故障 fail-closed / 旁路扫描 0 高危 / WARN 指标 / 白名单过期条目 WARN 与 `proxy.bypass_write` 审计）。
- 实现要点：verify_principal fail-open/fail-closed 分支（DB 不可达/行缺失/委托/Redis 降级）；`k03_bypass_whitelist` 过渡白名单；`scripts/bypass_scan.py` 静态盘点。
- 改动文件：`openbase/modules/identity/verification.py`、`core/deps/auth.py`、`settings.py`、`core/errors/codes.py`、`modules/proxy/__init__.py`、`scripts/bypass_scan.py` 及测试。

### 2.3 T3 协议头规范 v1.0 发布物 + OpenBase 试点（K02/SYS-1，commit 25b65d7）

- RED→GREEN：`tests/test_protocol_headers_lib.py`（T3-1~T3-9）+ `tests/test_inbound_header_gate.py`（7 例：非白名单带头 403 / 剥离开关 / 白名单矩阵）+ `tests/test_api_keys.py`（get_identity_context 忽略非受信头）对齐 §10 T3-1~T3-9。
- 实现要点：协议头规范 v1.0 文档裁出（doc/design/OpenBase-协议头规范-v1.0.md）；`validate_identity_headers`/`assert_trusted_source`/`classify_inbound`；get_current_tenant 收口、get_identity_context 来源校验、非白名单带头 403 开关化；request.state.identity 写入。
- 改动文件：`doc/design/OpenBase-协议头规范-v1.0.md`、`openbase/core/deps/auth.py`、`protocol_headers/validate.py`、`settings.py` 及测试。

### 2.4 T4 端点-过滤矩阵模板 v1.0（K07/SYS-1，commit 09f28fa）

- RED→GREEN：`tests/` K07 模板断言 + `scripts/k07_endpoint_matrix.py` 核对脚本骨架（openapi.json → 端点骨架行）对齐 §10 T4-1~T4-5。
- 实现要点：doc/design/OpenBase-端点过滤矩阵模板-v1.0.md（十列模板 + 填报说明 + S2-S5 流程 + S7 终验规则 + 填报跟踪表）；脚本骨架。
- 改动文件：`doc/design/OpenBase-端点过滤矩阵模板-v1.0.md`、`scripts/k07_endpoint_matrix.py` 及测试。

### 2.5 T5 OB-6 服务账号受信源收口（Q2-S6/L3-1 前置，commit 9a0aa49）

- RED→GREEN：`tests/test_service_agent_outbound.py`（17 例）对齐 §10 T5-1~T5-7（四 proxy agent 出站头 / 匿名直连写拒绝 / agent 出站审计 / U1 密钥面回归 / ob_k_ 服务账号映射）。
- 实现要点：`protocol_headers/identity_audit.py`（identity 审计块 + attach_outbound_identity + enqueue_proxy_outbound_audit seam）；AuditMiddleware 并入 extra.identity；service_account_subject_map 接线。
- 改动文件：`protocol_headers/identity_audit.py`、`inject.py`、`core/deps/auth.py`、`modules/audit/__init__.py`、`settings.py` 及测试。

### 2.6 T6 OB-12 角色互译配置（最小集 §6.3，Q-D，commit 9a0aa49）

- RED→GREEN：`tests/test_role_intertranslate.py`（27 例）对齐 §10 T6-1~T6-6（起步表校验 / 档位映射 / 回译逆一致 / 无映射 fail-closed / 越档拒绝 / Q-D 文档归档）。
- 实现要点：`protocol_headers/role_map.py` 完整语义；doc/design/OpenBase-角色互译表-v1.0.md；dps-proxy 出站经 settings.role_intertranslate 接线。
- 改动文件：`protocol_headers/role_map.py`、`inject.py`、`dps_proxy/__init__.py`、`doc/design/OpenBase-角色互译表-v1.0.md` 及测试。

### 2.7 T7 OB-8 code 化收口（P1-2/P1-3，批次 3 代码提交 B3）

- RED→GREEN：`tests/test_org_alias_code.py`（24 例）对齐 §10 T7-1~T7-7 + 附断言；RED 复现（回退基线）：T7-1 `X-Org-ID == X-Tenant-ID` 断言失败（出站仍取 `ctx.org_id` 独立链 `ghost-org`）、T7-7 示例文件缺失 → 失败；GREEN：恢复实现后 24 例全绿。
- 实现要点：
  - **T7-1/T7-2 别名收敛**：`inject.build_outbound_headers` 不再读 `identity.org_id` 独立中间态；X-Org-ID = X-Tenant-ID（tenant 同源）或 `org_value_map` 命中值；memory 硬编码默认 org 链（openbase-default）退役、仅 tenant 显式兜底。
  - **T7-3 别名强模式**：`enforce_org_alias=true` 且出站 X-Org-ID ≠ X-Tenant-ID → 403 `BIZ_ORG_ALIAS_MISMATCH`；dps/llm/rag/memory/通用 proxy 出站统一接线（默认 false 兼容段两段式开关）。
  - **T7-4/T7-5 登记式基线**：`protocol_headers/dps_code_map.py`（`parse_dps_code_map`/`validate_dps_code_map`/`dps_code_map_conflicts`/`build_compat_value_maps`）；默认空表、旧 JSON 兼容读取、同 code 双映射 → 冲突项（0 未决为门禁）。
  - **T7-6/T7-7 默认值策略与对账脚本**：settings `deprecated_dps_defaults()`/`dps_defaults_deprecation_warnings()`（verify-env WARN 数据源）；`scripts/audit_dps_code_map.py` 对账（tenants.code 唯一事实源，`--tenants-json` 离线，报告 JSON + 退出码 0/1）；示例 config/dps_code_map.example.json + doc/design/OpenBase-DPS-code映射基线登记示例-v1.0.0.md。
- 改动文件（批次 3）：`protocol_headers/inject.py`、`protocol_headers/dps_code_map.py`（新增）、`dps_proxy/__init__.py`、`llm_proxy/__init__.py`、`rag_proxy/__init__.py`、`proxy/__init__.py`、`proxy/memory_proxy.py`、`settings.py`、`config/dps_code_map.example.json`（新增）、`scripts/audit_dps_code_map.py`（新增）、`doc/design/OpenBase-DPS-code映射基线登记示例-v1.0.0.md`（新增）、既有 proxy 测试适配（test_dps_proxy/test_llm_proxy/test_memory_proxy/test_proxy_outbound_matrix 的 X-Org-ID 断言改别名口径）。

### 2.8 T8 OB-13 审计贯穿（OpenBase 侧，批次 3 代码提交 B3）

- RED→GREEN：`tests/test_audit_identity_chain.py`（12 例）对齐 §10 T8-1~T8-7；RED 复现（回退基线）：`ImportError: cannot import name 'build_identity_section'`（T8-1 identity 块未并入）→ 失败；GREEN：恢复实现后 12 例全绿。
- 实现要点：
  - **T8-1/T8-6 schema 并入**：`identity_audit.build_identity_section`（§8.2 六键恒有 principal/delegated/effective/proxy_source/proxy_chain/request_id）；lifecycle/delegation/purge 的 DB 审计 detail 并入 identity 块；legacy 顶层字段（principal/delegated/tenant_code/request_id）与 user_id/tenant_id/request_id 结构列保留不回退（兼容 U1 委托签发审计 schema）。
  - **T8-3 出站 DB 钩子**：`record_proxy_hop`（action=`proxy.outbound`，同一 request_id，proxy_chain 全链落 detail）；AuditMiddleware 响应后 `_persist_outbound_proxy_hop`（`request.state.outbound_assembled` 标注 → best-effort 落库，失败 WARN 不阻断）；build_outbound_headers→attach_outbound_identity 标注出站。
  - **T8-2/T8-4/T8-5**：委托出站 X-Agent-Id==审计 principal、X-User-ID==delegated 抽样比对；agent 直连/出站审计含 agent_id+source+域+动作；AuthMiddleware→AuditMiddleware request.state.identity 并入 extra/detail。
  - **T8-7 U4 边界文档化**：设计草案 §8.1 D-OB13-1~3（audit_logs 不新增列；U4/R3 如需结构化列再评估）。
- 改动文件（批次 3）：`protocol_headers/identity_audit.py`、`modules/audit/__init__.py`、`identity/lifecycle.py`、`identity/delegation.py`、`identity/purge.py`。

### 2.9 T9 OB-9 verify-env 雏形（commit ef0d028）

- RED→GREEN：`tests/test_verify_env.py`（6 例）对齐 §10 T9-1~T9-6 + 产物/复用断言；RED 复现（临时移出 scripts/verify-env.ps1 与 verify-env/）：`契约清单缺失`/`verify-env.ps1 缺失`/clean run 报告缺失 → 失败；GREEN：恢复后 6 例全绿。
- 实现要点：
  - **T9-1 契约清单**：`scripts/verify-env/contract.json`（config_single_source 含本批全部新键 role_intertranslate/dps_code_map/service_account_subject_map/trusted_proxy_sources/enforce_org_alias/enforce_token_version/k03_bypass_whitelist 等 + config_deprecated + upstreams + whitelist_matrix + mapping_reconcile + db_checks + tracking.contract_rail 契约轨标记）。
  - **T9-2/T9-6 自检脚本**：`scripts/verify-env.ps1`（缺键/端口不可达/白名单不一致/deprecated → WARN；dps_code_map 冲突/校验错误 → ERROR；退出码 0 干净 / 1 仅 WARN / 2 有 ERROR；`-FailFast` 置错即失败 1/2；报告落盘 `verify-env-report.json` 含 WARN/ERROR 清单与 summary）。
  - **T9-3/T9-4/T9-5 对账**：白名单矩阵比对（expected/actual/missing/extra 可定位）；dps_code_map 冲突/校验对账（复用 dps_code_map 模块，与 audit_dps_code_map.py 同源）；DB 检查位（OB-7 登记配合）+ upstream TCP 探活由 `scripts/verify-env/snapshot.py` 采集（密钥不落盘，jwt 仅存 `jwt_secret_ok`）。
- 改动文件（批次 3）：`scripts/verify-env/contract.json`、`scripts/verify-env.ps1`、`scripts/verify-env/snapshot.py`（均新增）。

### 2.10 T10 回归与 S1b 段门禁收口（本批次文档/台账提交 B4）

- 分组全量回归（`scripts/run_regression.py --group-size 3 --cov`）结果见 §4；ruff 0 见 §3；覆盖率见 §5；S1b 段门禁五项自检见 §7；台账回写（任务卡 v1.3.0 / 立项方案 v1.1.0 / 设计草案 v1.1.0 / 协议头规范 v1.0 批准回写 + K07 模板·角色互译表 [Review] 待人工批准登记）见 P2-1 测试报告 §6 与本报告 §9。

## 3. 静态质量检查

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 后端 Lint/静态 | `python -m ruff check openbase tests` | ✅ All checks passed（0 错误） |
| 批次 3 新增脚本专项 | `python -m ruff check scripts/audit_dps_code_map.py scripts/verify-env/snapshot.py` | ✅ All checks passed |

## 4. 兼容回归结果（T10，分组全绿为硬前提）

- 执行：`python scripts/run_regression.py --group-size 3`（Windows 平台单进程 C 层崩溃规避，子进程分组隔离 + 崩溃组自动重试，见 `scripts/run_regression.py` 与 TD-新增-009）。
- 结果汇总（批次 3 实测）：**556 passed / 0 failed / 4 skipped**（19 组子进程全绿；4 skipped 为 `test_storage_s3_real` 真实存储凭据类用例，`OPENBASE_TEST_REAL_INFRA` 未置位，与存量基线一致，非 P2-1 引入）。
- 兼容回归范围：存量 proxy/服务 Key/调用方（test_proxy_auth、test_dps_proxy、test_llm_proxy、test_rag_proxy、test_memory_proxy、test_api_keys* 等）+ P2-1 全量新断言（protocol_headers/outbound_matrix/inbound_header_gate/verdict_k03/role_intertranslate/service_agent_outbound/org_alias_code/audit_identity_chain/verify_env）+ U1 identity 存量，全绿。

## 5. 覆盖率结果与缺口说明（T10-3）

- 执行：`python scripts/run_regression.py --group-size 3 --cov`（分组 `--cov-append` 合并，`coverage report` 汇总）。
- 实测（批次 3）：全仓 `openbase` 行覆盖率 **86%**（6763 语句 / 925 miss）；`openbase/modules/protocol_headers/` 包 **92%**（589 语句 / 46 miss）——**保持 ≥90% 门槛**（inject 98% / identity_audit 100% / role_map 90% / validate 96% / identity_context 97% / dps_code_map 78%）。
- 覆盖缺口登记（与既有口径一致）：存量/端点驱动模块的低覆盖行集中在「HTTP 端点 + 真实 SQLite/外部 DB」驱动路径与 Windows TestClient 线程桥采集边界（TD-新增-009 同源），随 R3 补测治理（R3-1，详见测试报告 §7 遗留登记）。

## 6. 追溯矩阵（T1~T10 ↔ 设计草案 §10 ↔ 立项 §5 ↔ 落实状态）

| 任务 | 设计草案 §10 RED 断言 | 立项 §5 验收 | 落实状态（证据） |
|------|----------------------|-------------|-----------------|
| T1 唯一签发/出站对齐（K01/OB-3） | T1-1~T1-12 | 出站头仅来自签发上下文；TRUSTED_PROXY_SOURCES 单一取值 | ✅ test_protocol_headers_lib.py（21）+ test_proxy_outbound_matrix.py（11）；提交 25b65d7 |
| T2 禁旁路/fail-open（K03） | T2-1~T2-10 | 扫描报告 0 高危；白名单外写 403；V-1~V-5 裁定 | ✅ test_verdict_k03.py（14）；提交 51c6657 |
| T3 规范发布 + 试点（K02/SYS-1） | T3-1~T3-9 | 规范 v1.0 发布物齐备；非白名单带头 403 | ✅ test_protocol_headers_lib.py（T3）+ test_inbound_header_gate.py（7）；提交 25b65d7；规范文档 [Approved] |
| T4 端点矩阵模板（K07/SYS-1） | T4-1~T4-5 | 模板齐备 + 脚本骨架 + 填报跟踪表 + 评审通过 | ✅ 模板 v1.0 发布物 [Review] 待人工批准（S1b 门禁项⑤登记）；提交 09f28fa |
| T5 服务账号受信源（OB-6） | T5-1~T5-7 | sk-agent 四 proxy 出站头齐全；匿名直连写拒绝；密钥面回归 | ✅ test_service_agent_outbound.py（17）；提交 9a0aa49 |
| T6 角色互译（OB-12，Q-D） | T6-1~T6-6 | 映射校验/档位/逆一致/fail-closed；Q-D 结论记录 | ✅ test_role_intertranslate.py（27）；提交 9a0aa49；互译表 v1.0 发布物 [Review] 待人工批准（S1b 门禁项⑤登记） |
| T7 code 化收口（OB-8） | T7-1~T7-7 | X-Org-ID 别名收敛；登记式基线 0 未决冲突；deprecated WARN | ✅ test_org_alias_code.py（24）；提交 2fe18b2 |
| T8 审计贯穿（OB-13） | T8-1~T8-7 | detail.identity 六键；proxy.outbound 钩子同 request_id；U4 边界文档 | ✅ test_audit_identity_chain.py（12）；提交 0f65363 |
| T9 verify-env 雏形（OB-9） | T9-1~T9-6 | contract.json schema；ps1 可执行（WARN/exit 区分/--fail-fast）；报告可定位 | ✅ test_verify_env.py（6）；提交 ef0d028 |
| T10 回归与门禁 | T10-1~T10-6 | pytest 全绿；ruff 0；覆盖率口径记录；S1b 门禁；台账回写 | ✅ 本报告 §3~§7 + P2-1 测试报告；文档/台账提交 B4（docs(protocol)） |

## 7. S1b 段门禁五项自检（依据逐项，详细核对见 P2-1 测试报告 §6）

| # | 门禁自检项 | 结论 | 依据 |
|---|--------|:---:|------|
| 1 | 协议头规范 v1.0 发布物齐备 | ✅ | doc/design/OpenBase-协议头规范-v1.0.md（[Approved]，T3-1 发布物齐备断言）；`protocol_headers/` 六模块；constants 值与规范 §3.3 一致（test_protocol_headers_lib.py T3-1） |
| 2 | 非白名单带头 403（enforce）用例 | ✅ | test_inbound_header_gate.py::test_t2_5_enforce_403_untrusted_identity_headers（enforce 开 → 403 `PERM_UNTRUSTED_IDENTITY_HEADER`）；test_t3_7_strip_removes_headers_without_403（剥离过渡）；test_api_keys.py::test_identity_context_ignores_untrusted_headers |
| 3 | 服务账号用例全绿（sk-agent 四 proxy 出站+审计+ob_k_ 主体映射） | ✅ | test_service_agent_outbound.py（T5-1~T5-7：四 proxy 出站头/匿名直连写拒绝/agent 审计）；test_identity_t1.py（sk-agent 发放/吊销/状态门禁用例）；test_audit_identity_chain.py T8-4（agent 直连审计含 agent_id+source+域+动作） |
| 4 | verify-env 可用 | ✅ | scripts/verify-env.ps1 实跑：warnings=9 errors=0 exit_code=1（本环境 dps_default_* deprecated + 本地服务未启动 + 白名单未配置，均 WARN 非阻断），报告落盘 doc/test/evidence/verify-env-report.json；test_verify_env.py T9-1~T9-6（clean=0/WARN=1/ERROR=2/--fail-fast 非 0） |
| 5 | K07 模板 v1.0 + 角色互译表发布物 [Review] 待人工批准（文档版本/修订历史登记） | ✅ | doc/design/OpenBase-端点过滤矩阵模板-v1.0.md（v1.0.0 [Review] 待人工批准，修订历史 v1.0.0 行已登记）+ doc/design/OpenBase-角色互译表-v1.0.md（v1.0.0 [Review] 待人工批准，修订历史 v1.0.0 行已登记）；随 P2-1 测试报告 §6 G-5 提交人工门禁 |

> 说明：K07 模板 v1.0 / 角色互译表 v1.0 为 S1b 段发布物，**本批次维持 [Review] 状态（待人工批准）**，随本批次文档一并提交人工门禁，不在开发侧自行回写 [Approved]（见 §8 评审人工复核点登记）。

## 8. 遗留项登记（R3 补测 / 评审人工复核点 / 移交 S2-S5）

| # | 遗留项 | 级别 | 归属/处置 |
|---|--------|:---:|---------|
| R3-1 | 覆盖缺口补测（存量/端点驱动模块 + Windows TestClient 线程桥采集边界；口径同 U1 R3-1，protocol_headers 核心模块已 ≥90%） | P2 | R3 批次补测 |
| R3-2 | `enforce_org_alias` / `enforce_inbound_identity_headers` / `enforce_token_version` 等强模式开关默认关 → 部署段（S1b 门禁后）按两段式发布第二段开启并观察存量调用方 | P2 | 部署段 + 发布说明（§11.2 开关矩阵） |
| R3-3 | verify-env fail-fast 语义收紧（当前雏形 WARN 非阻断 exit 0/1/2；R3 完整版接管启动编排并收紧阈值） | P2 | R3/S7（§11.3 风险 6） |
| R3-4 | dps_code_map 生产登记（本仓默认空表 + .env 仍配置 dps_default_* 触发 deprecated WARN；新租户经 audit_dps_code_map.py 登记入基线） | P2 | 部署段配置收口（§7.2 默认值策略） |
| 评审人工复核点 | ① K07 模板 v1.0（doc/design/OpenBase-端点过滤矩阵模板-v1.0.md）与角色互译表 v1.0（doc/design/OpenBase-角色互译表-v1.0.md）发布物处于 **[Review] 待人工批准**——请人工门禁回写 [Approved]（S1b 门禁项⑤）；② 协议头规范 v1.0 [Approved] 与立项/设计草案版本回写（v1.3.0/v1.1.0）内容核对 | P1 | 本文档提交后人工门禁 |
| 移交 S2-S5 | K02 各子系统落地（OpenMemory S2/OpenRAG S3/OpenLLM S4/DPS S5 按协议头规范 v1.0 + 共享校验参考实现）；K07 端点矩阵各段填报（模板 v1.0 已发布）；DPS 角色对账真实双签随 R5 联调用例；L3-1/S7 端到端 | P1 | S2-S5 段执行（B-1/B-2/B-4） |

## 9. 产出物存在性验证（T10 门禁 + 台账回写）

| 产出物 | 存在性 |
|--------|:---:|
| `openbase/modules/protocol_headers/{__init__,constants,identity_context,validate,inject,role_map,dps_code_map,identity_audit}.py` | ✅ |
| 批次 3 脚本：`scripts/audit_dps_code_map.py`、`scripts/verify-env.ps1`、`scripts/verify-env/contract.json`、`scripts/verify-env/snapshot.py` | ✅ |
| 测试：test_protocol_headers_lib / proxy_outbound_matrix / inbound_header_gate / verdict_k03 / role_intertranslate / service_agent_outbound / org_alias_code / audit_identity_chain / verify_env | ✅ |
| 发布物（doc/design）：协议头规范 v1.0（[Approved]）、端点过滤矩阵模板 v1.0（[Review] 待人工批准）、角色互译表 v1.0（[Review] 待人工批准）、DPS-code 映射基线登记示例 v1.0.0 | ✅ |
| `doc/development/OpenBase-P2-1-统一身份协议头与信任链收口-DevLogReport-v1.0.0.md`（本报告） | ✅ |
| `doc/test/OpenBase-P2-1-统一身份协议头与信任链收口-测试报告-v1.0.0.md`（P2-1 测试报告，含 S1b 门禁核对） | ✅ |
| 台账回写：任务卡 v1.3.0、P2-1 立项方案 v1.1.0、P2-1 设计草案 v1.1.0 | ✅ |
| verify-env 实跑报告证据：`doc/test/evidence/verify-env-report.json` | ✅ |

## 10. 移交说明

- 本报告与 P2-1 测试报告（doc/test）配套进入测试回溯（测试报告回溯覆盖立项 §5 全部验收项后人工批准进入部署/S2 移交）。
- 提交链：批次 1/2（25b65d7 → 51c6657 → 09f28fa → 9a0aa49，T1~T6）；批次 3 代码提交 T7=2fe18b2 / T8=0f65363 / T9=ef0d028；本批次文档/台账提交（T10）见 git log 头部（docs(protocol) 提交）。
