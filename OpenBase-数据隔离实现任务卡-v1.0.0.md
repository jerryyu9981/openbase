# OpenBase-数据隔离实现任务卡-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-ISOCARDS-v1.0.0 |
| 版本 | v1.7.0 |
| 状态 | [Review]（24 卡：R1=14（K01-K08 + RA-01~RA-06）/ R2=10；v1.4.0 回写：S2（OpenMemory）段收口——K02(OM)/K05(OM-2)/RA-05(OM-1)/K06(OM-3) 已完成、K07 OM 端点-过滤矩阵填报完成，OB-11(OM 存量回填)/L1-1(OM 事件消费端)/OM-4/L3-2 贯通冒烟经 S2 段门禁（五项全绿）登记于卡尾执行摘要；OpenMemory 侧提交链待沙箱外放行后回填（见放行清单 v1.0.0）；v1.5.0 回写：S3（OpenRAG）段收口——K02(RG)/K16(RG-1)/K10(RG-2)/K11(RG-3)/K07 RG 端点-过滤矩阵填报 已完成，L1-1(RG 事件消费端)/fail-open 收口(RG 侧)/OB-13(RG 审计贯穿)/角色档位/M1/M2/L3-2 贯通冒烟经 S3 段门禁（五项全绿）登记于卡尾执行摘要；OpenRAG 侧提交链待沙箱外放行后回填（见放行清单 v1.0.1）；v1.6.0 回写：S4（OpenLLM）段收口——K09（S4-T2）/LL-1 探活（S4-T1）/LL-2 REAL 契约开关（S4-T4）/LL-4/K17（S4-T5）/LL-5（S4-T6）/LL-6（S4-T6）/K15（S4-T3）/L2-1（S4-T7）/L2-2（S4-T8）/K02(LL)（S4-T9）/OB-13 LL 侧（S4-T10）/K07 LL 端点-过滤矩阵填报（S4-T11）/角色档位（S4-T12）/M1/M2（S4-T13）/verify-env（S4-T14）/L3-2 LL 贯通冒烟（S4-T15）已完成，经 S4 段门禁（五项全绿）登记于卡尾执行摘要；OpenLLM 侧提交链待沙箱外放行后回填（见放行清单 v1.0.2）；v1.7.0 回写：S5（DPS）段收口——K02(DPS) 协议头入站校验（S5-T1）、K07 DPS 端点-过滤矩阵填报（S5-T10，169 行=覆盖 134/豁免 35/缺口 0 + CI 门禁）、K12(DP-6) person 复合唯一（S5-T5）、K14(DP-4) 并发写规则固化（S5-T4）、K18(DP-2) org/tenant 归一与 code 冲突检测（S5-T2，含 DP-3 绑定总线化 S5-T3）状态更新为「✅已完成」；经 S5 段门禁（五项全绿）登记于卡尾执行摘要（DPS-T1~T12）；DPS 侧提交链待沙箱外放行后回填（见放行清单 v1.0.5）） |
| 日期 | 2026-09-10 |
| 作者 | AD（跨项目分析） |
| 版本主题 | 将《统一身份最小特征集与隔离模型设计 v1.3.0》§12 数据隔离实现细则（22 条规则）拆为可执行任务卡，并补齐 R1 批次范围内非 §12 工作项（U1/P2-2/治理）：每卡含目标升级项、系统、批次、改动点、实现步骤、测试用例、验收断言（v1.2.0：S1a 收口回写 RA-01/RA-02/K04/K08 状态与提交链；v1.3.0：S1b/P2-1 收口回写 K01/K03/K02/K07 与 OB-3/6/8/9/12/13 状态与提交链；v1.4.0：S2（OpenMemory）段收口回写 K02(OM)/K05(OM)/RA-05/K06/K07(OM 填报) 状态与卡尾 S2 段执行摘要（OB-11(OM)/L1-1(OM)/OM-4/L3-2）；v1.5.0：S3（OpenRAG）段收口回写 K02(RG)/K10(RG-2)/K11(RG-3)/K16(RG-1)/K07(RG 填报) 状态与卡尾 S3 段执行摘要（L1-1(RG)/fail-open 收口/OB-13(RG 侧)/角色档位/M1/M2/L3-2）；v1.6.0：S4（OpenLLM）段收口回写 K09/K15/K17/K02(LL)/K07(LL 填报) 状态与卡尾 S4 段执行摘要（LL-1~LL-6/L2-1/L2-2/OB-13 LL 侧/K07 LL 填报/角色档位/M1/M2/verify-env/L3-2 LL 贯通冒烟）；v1.7.0：S5（DPS）段收口回写 K02(DPS)/K07(DPS 填报)/K12(DP-6)/K14(DP-4)/K18(DP-2) 状态与卡尾 S5 段执行摘要（DP-2/K18、DP-3、DP-4/K14、DP-6/K12、K02(DPS)、K07(DPS)、角色互译表 DPS 侧接线、L1-1 DPS 真实消费端、OB-13 DPS 审计六键、M1/M2 与服务账号、verify-env、L3-2 冒烟）） |
| 上游依据 | 身份最小集 v1.3.0 §12（R-H/M/L 规则）；文档体系与升级路线规划 v1.1.0（升级项编号 OB-*/OM-*/RG-*/DP-*/LL-*/SYS-1 与批次）；P2-2 立项方案 v1.0.0；U1 立项方案 v1.1.0 / 设计草案 v1.1.0（实施依据）；P2-1 立项方案 v1.1.0 / 设计草案 v1.1.0（S1b 收口依据，均已 [Approved]） |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-09-06 | AD（跨项目分析） | 初始版本：§12 规则全部任务卡化（K01-K18，R1 八卡 + R2 十卡） |
| v1.1.0 | 2026-09-06 | AD（跨项目分析） | R1 范围评审补齐：新增 RA-01~RA-06 六卡（主体模型/login 闭环/fail-closed/绑定收紧/sessions 端点归属/R1 门禁聚合），覆盖 R1 批次非 §12 工作项；K05 显式协同 OM-1 |
| v1.2.0 | 2026-09-07 | U1 开发组 | S1a（U1）收口回写：RA-01/RA-02/K04/K08 状态由「待立项（U1）」更新为「✅已完成（实施）」，登记 U1 T1~T4 提交链（c1869bf/9a8dc24/bdbe146/993bc57）；K08 委托头唯一签发收口按依赖 R2 移交 S1b（P2-1） |
| v1.3.0 | 2026-09-08 | P2-1 开发组 | S1b（P2-1）收口回写：K01/K03（OB-3）状态改「✅已完成（实施，P2-1 批次 1~3）」，K02（SYS-1）改「✅规范 v1.0 已发布 + OpenBase 试点完成（下游 S2-S5 落地）」，K07（SYS-1 续）改「✅模板 v1.0 已发布（填报随 S2-S5）」，K08 补充登记委托头唯一签发规范 v1.0 收口；升级项 OB-6/OB-8/OB-9/OB-12/OB-13 已完成（P2-1），OB-7/OB-10 外移；登记 P2-1 提交链（批次 1/2：25b65d7/51c6657/09f28fa/9a0aa49；批次 3 见 P2-1 DevLogReport v1.0.0） |
| v1.4.0 | 2026-09-09 | AD（跨项目分析） | S2（OpenMemory）段收口回写：K02(OM) 协议头入站校验（S2-T1/T2：IdentityGate 白名单/fail-closed + B-1 agent 双层认证）、K05(OM-2) 行控强制过滤（S2-T3）、RA-05(OM-1) sessions 归属（S2-T4）、K06(OM-3) 复合唯一（S2-T5 落地 alembic v702）状态更新为「✅已完成」；K07 登记 OM 端点-过滤矩阵填报完成（S2-T10，doc/design/OpenMemory-K07-端点过滤矩阵填报 v1.0.1 [Approved]，缺口清零）；卡尾登记 S2 段执行摘要（OB-11(OM) 存量回填 v703 0 孤儿、L1-1(OM) 事件真实消费端 v704 阻断集+幂等+双通道、OM-4 M1/M2、L3-2 贯通冒烟 S2-T13 真实 HTTP 双签移交部署/联调窗口与 S7）；提交链以 OpenMemory S2 DevLogReport v1.0.1 为准，OpenMemory 侧提交待沙箱外执行（见 doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md），OpenBase 侧锚点 commit 0713ec1=事件列表契约端点 |
| v1.5.0 | 2026-09-09 | AD（跨项目分析） | S3（OpenRAG）段收口回写：K02(RG) 协议头入站校验（S3-T1：IdentityGate 行为矩阵四态 + B1 EdgeRouter 不装配处置）、K16(RG-1) 表级归属迁移（S3-T2：归属列 tenant_code 幂等迁移 + 保留码 openrag-local 回填 0 孤儿 + B2 碰撞防护）、K10(RG-2) 行控强制过滤（S3-T3：强制注入 + 豁免清单 + 静态门禁）、K11(RG-3) 复合唯一（S3-T4：collection (tenant_code, name) 复合唯一，同域同名 409）状态更新为「✅已完成」；K07 登记 OpenRAG 端点-过滤矩阵填报完成（S3-T8，doc/design/OpenRAG-K07-端点过滤矩阵填报 v1.0.0，openapi 底单 121 行=豁免 10/覆盖 111，缺口清零）；卡尾登记 S3 段执行摘要（L1-1(RG) 事件真实消费端 S3-T5 阻断集+幂等+Push/Pull 契约 v1.0、fail-open 收口 S3-T6 D-V 映射、OB-13(RG 侧) S3-T7 审计 detail.identity 六键、角色档位 S3-T9 Q-RG-6、M1/M2 S3-T10、L3-2 贯通冒烟 S3-T11 通过——真实 HTTP 双签与 PG/Redis 实跑登记联调窗口）；提交链以 OpenRAG S3 DevLogReport v1.0.1 为准，OpenRAG 侧提交待沙箱外执行（见 doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md v1.0.1），OpenBase 侧锚点 commit 0713ec1=事件列表契约端点 |
| v1.6.0 | 2026-09-10 | AD（跨项目分析） | S4（OpenLLM）段收口回写：K09 编排出站身份透传（S4-T2：external_identity 透传基座全四维采纳 + 白名单矩阵）、K15 REAL_* 兜底收口（S4-T3：出站头唯一装配统一 + 业务路径 REAL 零依赖）、K17 前缀归一（S4-T5：namespace 归一 tenant_code + org 只读别名 + 保留码）、K02(LL) 强校验（S4-T9：豁免清单 + IdentityGate 全端点收口 + 保留码 400）状态更新为「✅已完成」；K07 登记 OpenLLM 端点-过滤矩阵填报完成（S4-T11，doc/design/OpenLLM-K07-端点过滤矩阵填报 v1.0.0，S4 聚焦端点集全覆盖 + A 直连豁免行对账 + 隔离注册表缺口清零）；卡尾登记 S4 段执行摘要（LL-1 探活 S4-T1、LL-2 REAL 契约开关 S4-T4、LL-5/LL-6 S4-T6、L2-1 S4-T7、L2-2 S4-T8、OB-13 LL 侧 S4-T10、角色档位 S4-T12、M1/M2 S4-T13、verify-env S4-T14、L3-2 贯通冒烟 S4-T15——真实 HTTP 双签登记联调窗口与 S7）；提交链以 OpenLLM S4 DevLogReport v1.0.1 为准，OpenLLM 侧提交待沙箱外执行（见 doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md v1.0.2），OpenBase 侧锚点 commit 0713ec1=事件列表契约端点 |
| v1.7.0 | 2026-09-10 | AD（跨项目分析） | S5（DPS）段收口回写：K18(DP-2) org/tenant 归一（S5-T2：tenants.code 对齐 OpenBase 权威源 + 冲突检测与重映射脚本 tenant_code_reconcile.py + 冲突清单 0 未决）、DP-3 绑定总线化（S5-T3：user_roles 以 OpenBase 主体键绑定 + deactivated/restored 生命周期联动）、K14(DP-4) 并发写规则固化（S5-T4：画像写链 WHERE version 乐观锁冲突 409 + message_hash 幂等盘点结论「0 适用」落档）、K12(DP-6) person 复合唯一（S5-T5：复核即达 + 对账 0 孤儿 + 跨租户同名互不可见）、K02(DPS) 协议头入站校验（S5-T1：来源白名单 + 行为矩阵四态 + 保留码/非法头 400 + 装配顺序断言）、K07 DPS 端点-过滤矩阵填报（S5-T10：169 行=覆盖 134/豁免 35/缺口 0 + CI 门禁）状态更新为「✅已完成」；卡尾登记 S5 段执行摘要（角色互译表 DPS 侧接线 S5-T9、L1-1 DPS 真实消费端 S5-T6、OB-13 DPS 审计六键 S5-T8、M1/M2 与服务账号 S5-T11、verify-env 契约键 S5-T14、L3-2 冒烟 S5-T12）；提交链以 DPS S5 DevLogReport（doc/development/DPS-S5-画像数据隔离与身份接入收口-DevLogReport-v1.0.0.md）为准，DPS 侧提交待沙箱外执行（见 doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md v1.0.5）；OpenBase 侧锚点 commit 0713ec1=事件列表契约端点 |

---

## 0. 使用说明

- **卡字段**：ID / 规则（§12 规则或规划/U1/P2-2 依据）/ 升级项（规划 v1.1.0）/ 系统 / 批次 / 前置 / 状态 / 改动点 / 实现步骤 / 测试用例 / 验收断言。
- **状态图例**：⏳待立项 / 🚧实施中 / ✅已闭环（随实施更新；本版为初始状态）。
- **批次**：R1 身份与隔离收口；R2 通道契约与数据迁移（规划 v1.1.0 §4）。
- 编码与测试遵循 AGENTS.md（TDD、参数化查询、错误码、覆盖 ≥90%）；测试命令 `python -m pytest tests` / `python -m ruff check openbase tests`（各仓对应）。
- 卡分组：K 组 = §12 规则拆解；RA 组 = R1 批次范围内非 §12 规则工作项（U1/P2-2/治理承接）。

## 批次 R1 卡组（§12 规则：身份与隔离收口）

### K01 唯一身份注入点
- 规则/升级项：§12.1 R-H1-1 → OB-3（协议头与信任链）；批次 R1；前置 —；状态 ✅已完成（实施，P2-1 批次 1~3：protocol_headers 共享包 + build_outbound_headers 唯一装配 + 委托头唯一签发规范 v1.0 + org 别名收敛，见 P2-1 DevLogReport v1.0.0）
- 系统：OpenBase（网关/签发侧）
- 改动点：token 签发模块（auth/refresh）+ 各 proxy（llm/rag/memory/dps）出站头组装；配置项 `TRUSTED_PROXY_SOURCES` 收敛单一写法。
- 实现步骤：① 签发处统一注入四头（X-User-ID/X-Tenant-ID/X-User-Role/X-Proxy-Source）与 request_id；② proxy 层删除各自为政的头组装，改读统一上下文；③ 出站请求剥离客户端伪造头（白名单来源除外）。
- 测试用例：单测：无/伪造头请求 → 剥离或拒绝；签发后四头齐全且与 JWT claim 一致；request_id 贯通。
- 验收断言：任意 proxy 出站请求头仅来自签发上下文；`TRUSTED_PROXY_SOURCES` 全仓仅一种取值。

### K02 白名单身份头下游校验（SYS-1）
- 规则/升级项：§12.1 R-H1-2 → SYS-1；批次 R1；前置 K01；状态 ✅规范 v1.0 已发布（P2-1 T3/S1b）+ OpenBase 试点完成（非白名单带头 403 开关化/剥除/审计）+ **OpenMemory 段落地完成（S2-T1/T2：IdentityGate 协议头入站校验与来源白名单 + block_subject_gate + B-1 agent 双层认证，fail-closed）** + **OpenRAG 段落地完成（S3-T1：IdentityGate 行为矩阵四态裁决（受信+头=信任 / 白名单无头=自身认证 / 非受信+头=403 / 非受信无头=本地认证）+ block_subject_gate/role_gate + 身份解析收口 request.state.identity + B1 EdgeRouter 不装配静态门禁，强校验期 fail-closed，见 OpenRAG S3 DevLogReport v1.0.1）** + **OpenLLM 段落地完成（S4-T9：IdentityGate 强校验收口（全端点 + GATE_EXEMPT_PATH_PREFIXES 健康/管理面 A 直连豁免清单 ticket+审批+到期）+ 保留码 org 只读别名入站 400 + scan_identity_bypass 0 绕过，见 OpenLLM S4 DevLogReport v1.0.1）** + **DPS 段落地完成（S5-T1：协议头入站校验与来源白名单——白名单来源+头=信任 / 白名单无头=自身认证 / 非白名单带头=403 / 非白名单无头=本地认证四态行为矩阵 + 保留码与非法头入站 400 + 装配顺序断言，强校验期 fail-closed，见 DPS S5 DevLogReport v1.0.0）**
- 系统：OpenRAG / OpenMemory / DPS / OpenLLM 网关（各功能系统入口中间件）
- 改动点：各系统鉴权/身份中间件新增"来源白名单校验"：请求带身份头但来源（X-Proxy-Source/对端 IP）不在白名单 → 403；匿名请求走自身认证（M1）。
- 实现步骤：① 各仓引入统一白名单配置键；② 中间件在身份解析前校验来源与头一致性；③ 行为矩阵化（白名单+头=信任 / 白名单无头=自身认证 / 非白名单带头=403）。
- 测试用例：每系统 ≥3 例：受信来源带头放行、非受信带头 403、匿名按自身 API Key 认证。
- 验收断言：跨系统矩阵测试全绿；非白名单携带身份头请求全链路 403（无绕过端点）。

### K03 禁止旁路审计
- 规则/升级项：§12.1 R-H1-4 → OB-3；批次 R1；前置 —；状态 ✅已完成（实施，P2-1 T2/T5：V-1~V-5 信任链裁定 + k03_bypass_whitelist 过渡白名单 + 旁路扫描 0 高危项，见 P2-1 DevLogReport v1.0.0）
- 系统：OpenBase（全量盘点）
- 改动点：扫描全部业务写路径，产出"绕过 OpenBase 直连子系统"清单；将旁路端点收口到 proxy/编排受信通道。
- 实现步骤：① 盘点各 proxy 与子系统直连调用点；② 对旁路写路径加白名单与审计（或改走受信通道）；③ 在复盘文档登记收口结果。
- 测试用例：静态扫描（禁止绕过网关直写子系统的调用模式）+ 审计抽查。
- 验收断言：业务面无"未审计直连写"路径（扫描报告 0 高危项）。

### K04 token 吊销即时性
- 规则/升级项：§12.2 R-H2-1/2/3 → OB-2（吊销部分）；批次 R1；前置 RA-02（生命周期状态机）；状态 ⏳待立项（U1）
- 系统：OpenBase（生命周期/令牌）
- 改动点：吊销机制三选一（a. token 版本号 jti 递增比对【推荐】/ b. 黑名单缓存 / c. access≤5min+refresh 校验）；鉴权中间件每请求校验主体状态（禁仅验签）。
- 实现步骤：① 主体验证器新增状态校验；② 实现选定吊销机制并接 refresh/签发链；③ admin 停用 API 联动吊销（联动 RA-02）。
- 测试用例：suspend 后存量 access 立即/一次刷新内失效（三种机制各用例）；deactivated 后全部凭据失效；恢复后需重新登录。
- 验收断言：停用→存量 token 请求返回 401/403（最迟一次刷新窗口）；无"仅验签不验状态"路径。

### K05 OpenMemory 强制过滤骨架（协同 OM-1/OM-2）
- 规则/升级项：§12.3 R-H3-1/2/3/4 → OM-2；协同 OM-1（sessions 端点归属，见 RA-05）；批次 R1；前置 —；状态 ✅已完成（实施，OpenMemory S2-T3 行控强制过滤收口（repository 强制注入 (tenant_code, owner)、豁免清单、fail-closed 默认）+ S2-T4 sessions 归属收口（协同 RA-05/OM-1），见 OpenMemory S2 DevLogReport v1.0.1）
- 系统：OpenMemory（repository/数据访问层）
- 改动点：repository/DAO 基类强制注入 `(tenant_code, owner)` 过滤；原生 SQL 豁免走显式清单+评审；ORM 钩子纵深防御；memories/sessions 存量查询全部迁移骨架（sessions 端点归属在 RA-05 做端点级显式化）。
- 实现步骤：① 建带强制过滤的查询基类（所有查询入口必经）；② memories/sessions 存量查询全部迁移到骨架；③ 豁免清单机制+代码评审门禁；④ 可选 SQLAlchemy event 兜底。
- 测试用例：隔离基座断言"任何 repository 方法返回集不含他域行"；全端点跨域不可见。
- 验收断言：双租户隔离用例全绿（跨域读 404/403）；sessions list 不再全量遍历。

### K06 OpenMemory 复合唯一
- 规则/升级项：§12.4 R-M1-1/2（OM 部分）→ OM-3；批次 R1；前置 K05；状态 ✅已完成（实施，OpenMemory S2-T5：namespace 唯一升级 (tenant_code, name) 复合唯一，alembic v702 幂等落地，见 OpenMemory S2 DevLogReport v1.0.1）
- 系统：OpenMemory（schema/迁移）
- 改动点：namespace 唯一索引升级为 `(tenant_code, name)` 复合唯一；存量迁移增量回填。
- 实现步骤：① 迁移新增复合唯一约束（幂等，W1-4）；② 存量重复名按域拆分；③ 写路径冲突按 (tenant,name) 判定。
- 测试用例：跨域同名创建均成功且互不可见；同域同名冲突返回 409。
- 验收断言：复合唯一迁移幂等可重放；跨域同名隔离用例通过。

### K07 端点-过滤矩阵（SYS-1 续）
- 规则/升级项：§12.5 R-M2-1/2 → SYS-1；批次 R1；前置 K02/K05；状态 ✅模板 v1.0 已发布（P2-1 T4/S1b：模板文档 + k07_endpoint_matrix.py 脚本骨架 + S2-S5 填报跟踪表登记）+ **OpenMemory 段填报完成（S2-T10：doc/design/OpenMemory-K07-端点过滤矩阵填报 v1.0.1 [Approved]，缺口清零，CI s2-k07-matrix-gate job 注册）** + **OpenRAG 段填报完成（S3-T8：doc/design/OpenRAG-K07-端点过滤矩阵填报 v1.0.0（[Final]，经 S3 段门禁人工批准复核），openapi 权威底单 121 行：豁免 10/覆盖 111，缺口清零，CI s3-static-gates k07 门禁注册）** + **OpenLLM 段填报完成（S4-T11：doc/design/OpenLLM-K07-端点过滤矩阵填报 v1.0.0，S4 聚焦端点集全覆盖 + A 直连豁免行（GATE_EXEMPT_PATH_PREFIXES 对账） + k07_isolation_registry 隔离注册表缺口清零）** + **DPS 段填报完成（S5-T10：doc/design/DPS-K07-端点过滤矩阵填报 v1.0.0，169 行=覆盖 134/豁免 35/缺口 0，隔离注册位（IS-DPS-*）成套登记 + 漂移门禁 0 + CI「S5-K07 endpoint matrix gate」注册，见 DPS S5 DevLogReport v1.0.0）**；S7 RA-06 终验引用
- 系统：OpenBase（编排/proxy）+ OpenMemory + OpenRAG + DPS（端点盘点）
- 改动点：按端点类别（CRUD/列表分页/搜索/聚合/导出/回调/批量）全量盘点并建立"端点-过滤矩阵"；每新增端点默认配套隔离测试。
- 实现步骤：① 每系统导出 openapi 端点清单；② 按类别核对过滤覆盖，标红缺口端点；③ 缺口端点补过滤（接 K02/K05 骨架）；④ 新增端点模板内置隔离用例。
- 测试用例：矩阵自动核对测试（端点×类别×过滤三态）；新增端点 CI 强制带隔离用例。
- 验收断言：矩阵缺口清零；新增端点无隔离用例不放行（评审门禁）。

### K08 委托不跨界
- 规则/升级项：§12.7 R-M4-1/2 → OB-11；批次 R1；前置 RA-01（主体模型）+K01/K04；状态 ✅已完成（实施，U1 T4 → 993bc57 委托域不变式校验 + P2-1 批次 1/3：委托头唯一签发规范 v1.0（§3.6）与委托出站/审计贯穿收口，见 P2-1 DevLogReport v1.0.0）
- 系统：OpenBase（签发/委托）
- 改动点：签发 on_behalf_of claim 时校验 `delegated.tenant == agent.tenant`（不等 403）；嵌套主体链每跳重校验委托不变式。
- 实现步骤：① 委托 claim 结构与校验器（依赖 RA-01 模型）；② 签发链校验归属并签名；③ 中间件对嵌套链逐跳重校验（X-Proxy-Source 链解析）。
- 测试用例：跨域委托请求 403；同域委托放行且审计记两层；三级嵌套链中任意跳跨界即拒。
- 验收断言：委托跨界 403 用例全绿；无跨界委托可达数据面。

## 批次 R1 补充卡组（RA：R1 范围内非 §12 规则工作项，U1/P2-2/治理承接）

### RA-01 主体模型落地（OB-1）
- 规则/升级项：最小集 §4.5/§11 → OB-1；批次 R1；前置 —；状态 ⏳待立项（U1）
- 系统：OpenBase（数据模型/签发）
- 改动点：Principal 模型落库（user/agent 平级，subject_type、on_behalf_of 可选字段、凭据类型 user=password|oidc、agent=api_key）；登录端点对 subject_type=agent 拒绝。
- 实现步骤：① 表/模型迁移（主体抽象字段）；② 签发与认证按 subject_type 分叉；③ agent 密钥表（前缀 sk-agent-*、明文仅示一次、哈希存储）；④ RBAC 挂载（默认 viewer）。
- 测试用例：agent 建号→密钥发放/轮换/吊销；agent 密码登录被拒；on_behalf_of 字段序列化。
- 验收断言：user/agent 同一主体模型可实例化；agent 无交互登录路径（0 可达）。

### RA-02 生命周期状态机与 login 闭环（OB-2 状态机 + OB-4）
- 规则/升级项：最小集 §4.1 status / §5 login 目标 → OB-2（状态机）、OB-4；批次 R1；前置 RA-01；状态 ✅已完成（实施，U1 T2 → 9a8dc24）
- 系统：OpenBase（生命周期/签发）
- 改动点：status 状态机（provisioned→active→suspended→deactivated→purged 规则与级联语义）；**login 亦签发 tenant_code**（闭环存量令牌缺口）；停用/恢复 API（admin）。
- 实现步骤：① 状态迁移校验与 API；② login/refresh 签发补 tenant_code claim；③ 停用/恢复联动吊销（K04）；④ 存量令牌兼容（无 tenant 的旧令牌刷新后补齐）。
- 测试用例：状态机非法迁移拒绝；login 后 token 含 tenant_code；停用→恢复→再停用全链路。
- 验收断言：登录态令牌 100% 含 tenant_code（抽样/注入用例）；状态迁移 0 非法路径。

### RA-03 fail-closed 收口（OB-5/DP-1）
- 规则/升级项：P2-2 Phase1（复盘 L2 fail-open 两项）→ OB-5、DP-1；批次 R1；前置 —；状态 🚧已立项（P2-2）
- 系统：DPS（tenant 中间件 + permission 引擎）＋ OpenBase（同构校验兜底）
- 改动点：tenant 中间件 DB 故障按配置 `MULTI_TENANT_ENABLED + fail_closed=true` 拒绝而非放行；permission 引擎未初始化/异常 → 拒绝；配置开关默认 fail-closed。
- 实现步骤：① 中间件异常分支改拒绝（默认）；② permission 引擎初始化检查（未就绪即 503/403）；③ 配置开关默认值 fail-closed；④ OpenBase 侧同构规则核对。
- 测试用例：DB 故障注入→请求 503/403 不放行；引擎未初始化→拒绝；显式 fail-open 仅测试环境可用。
- 验收断言：故障注入下无放行路径（fail-closed 用例全绿）。

### RA-04 绑定收紧（DP-5）
- 规则/升级项：复盘 S3-3 / P2-2 T4 → DP-5；批次 R1；前置 RA-03；状态 🚧已立项（P2-2）
- 系统：DPS（user_roles 种子/绑定）
- 改动点：`DPS_DEMO_USER_ROLES` 显式收紧为生产基线；X-User-ID=1 演示硬绑固化核销（仅种子/测试可用，生产绑定必须经 OpenBase 总线）。
- 实现步骤：① 生产基线角色清单定稿；② 演示种子与生产基线隔离（环境开关）；③ 未绑定主体访问画像返回 403（无隐式降级）。
- 测试用例：演示绑定在生产环境不可用；未绑定主体 403；基线角色最小集核对。
- 验收断言：生产配置下无"隐式绑定放行"路径。

### RA-05 sessions 端点归属显式化（OM-1，协同 K05）
- 规则/升级项：P2-2 Phase2（复盘 L2 sessions 无归属）→ OM-1；批次 R1；前置 K05 骨架；状态 ✅已完成（实施，OpenMemory S2-T4：sessions list/get/terminate 端点归属显式化（owner/tenant 过滤、list 分页禁全量遍历、跨域 404），见 OpenMemory S2 DevLogReport v1.0.1）
- 系统：OpenMemory（sessions API）
- 改动点：sessions list/get/terminate 显式归属校验（owner/tenant 过滤）；list 禁全量遍历（分页+过滤必需）；terminate 仅本人/域内 admin。
- 实现步骤：① 端点层归属参数解析与校验；② list 强制过滤+分页；③ get/terminate 归属断言（跨域 404）。
- 测试用例：跨域 get/terminate 404；list 仅本域；未带身份请求走自身认证。
- 验收断言：sessions 三端点归属用例全绿；无全量遍历路径。

### RA-06 R1 门禁聚合卡
- 规则/升级项：规划 §4 R1 门禁 → 验收收口；批次 R1；前置 K01-K08+RA-01~RA-05 全部；状态 ⏳
- 系统：跨系统（回归基座）
- 改动点：聚合验收脚本/CI 门禁：双租户隔离回归、fail-closed 用例、OIDC 批次隔离（存量 T2 归档）、委托跨界 403、吊销即时性。
- 实现步骤：① 门禁清单固化（对齐存量测试清单 v1.2.0）；② 各卡验收断言转 pytest/E2E 用例注册；③ 单命令全绿收口。
- 测试用例：门禁批次独立进程运行（S4 分批范式）；覆盖率 ≥90%。
- 验收断言：R1 门禁单命令全绿；T2 OIDC 台账归档关闭。

## 批次 R2 卡组（通道契约与数据迁移）

### K09 编排出站身份透传
- 规则/升级项：§12.1 R-H1-3 → LL-3；批次 R2；前置 K01；状态 ✅已完成（实施，OpenLLM S4-T2：身份透传基座收口——backend/app/services/external_identity.py 对话上下文身份 resolve 链（user→tenant 全四维采纳）+ 来源白名单矩阵 + 身份解析收口 request.state.identity 六键，REAL_* 兜底废弃为服务账号/探活专用，见 OpenLLM S4 DevLogReport v1.0.1）
- 系统：OpenLLM（编排出站）
- 改动点：ProfileAdapter/DPSClient 等出站身份改为透传对话上下文 resolve 所得身份；REAL_* 配置默认值降级为服务账号/探活专用并标记 deprecated。
- 实现步骤：① 对话上下文身份 resolve 链（user→tenant）；② 出站头取 resolve 值而非配置默认；③ REAL_* 兜底仅服务/探活分支保留 + WARN 日志。
- 测试用例：用户对话触发 DPS 读 → DPS 侧审计用户域一致；无上下文时走服务账号且不落业务域。
- 验收断言：通道 B 数据落用户域（双通道等价用例前置）；REAL_* 不作为业务身份出现。

### K10 OpenRAG 强制过滤骨架
- 规则/升级项：§12.3 R-H3（RG 部分）→ RG-2；批次 R2；前置 RG-1（K16）先；状态 ✅已完成（实施，OpenRAG S3-T3：store/查询骨架 tenant_code 强制注入（postgres/sqlite 统一 scope 契约）+ scope_exemption 豁免清单（ticket+审批，豁免只放宽 scope 不触及身份信任）+ scan_tenant_scope/scan_no_identity_header_bypass 静态门禁 0 违规 + fail-closed 默认，见 OpenRAG S3 DevLogReport v1.0.1）
- 系统：OpenRAG（repository/查询层）
- 改动点：同 K05 范式：查询基类强制注入 tenant_code；豁免审批；ORM 钩子兜底。
- 实现步骤：① 查询骨架落地；② collections/documents 查询全迁；③ 豁免清单机制。
- 测试用例：隔离基座（返回集不含他域行）；分页/搜索/聚合端点跨域不可见。
- 验收断言：双域并行查询互不可见全绿。

### K11 OpenRAG 复合唯一
- 规则/升级项：§12.4 R-M1（RG 部分）→ RG-3；批次 R2；前置 K10；状态 ✅已完成（实施，OpenRAG S3-T4：collection 唯一升级 (tenant_code, name) 复合唯一（storage/migrations.py 幂等迁移器），同域同名 409、跨域同名并存互不可见，见 OpenRAG S3 DevLogReport v1.0.1）
- 系统：OpenRAG（schema/迁移）
- 改动点：collection 唯一升级 `(tenant_code, name)`；存量迁移（幂等）。
- 实现步骤/测试用例/验收断言：同 K06 范式（collection 维度）。
- 验收断言：跨域同名 collection 并存互不可见；同域同名 409。

### K12 DPS person 复合唯一
- 规则/升级项：§12.4 R-M1（DPS 部分）→ DP-6；批次 R2；前置 DP-2（K18）；状态 ✅已完成（实施，DPS S5-T5：person_key 建模定案后唯一键对齐 (tenant_id, person_key)「复核即达」+ 对账 0 孤儿 + 跨租户同 person_key 并存互不可见、同租户冲突 409，见 DPS S5 DevLogReport v1.0.0）
- 系统：DPS（schema/迁移）
- 改动点：person 唯一键升级 `(tenant_id, person_key)`；迁移对账重复 person_key。
- 测试用例：跨租户同 person_key 均可建且隔离；同租户冲突 409。
- 验收断言：唯一含域键迁移幂等；跨租户同名互不可见。

### K13 存储账号权限分离
- 规则/升级项：§12.6 R-M3-1/2 → OB-7；批次 R2；前置 —；状态 ⏳待立项（U2）
- 系统：共享 PG 基础设施
- 改动点：openbase 应用账号与 platform（DPS 等）应用账号分离，各自仅授本 schema DML；迁移账号与运行时账号分离；不授 superuser。
- 实现步骤：① 建账号矩阵（schema×账号×权限）；② 迁移 SQL 授权；③ 各仓连接串指向各自账号；④ 复核无跨 schema 写。
- 测试用例：跨 schema 写被拒（DB 级）；运行账号无法 DDL。
- 验收断言：账号矩阵核对通过；跨 schema 写 0 成功路径。

### K14 并发写规则固化
- 规则/升级项：§12.8 R-M5-1/2 → DP-4；批次 R2；前置 —；状态 ✅已完成（实施，DPS S5-T4：画像写链 `WHERE version` 乐观锁冲突返回 409 + 版本单调递增；异步/队列写 message_hash 幂等键适用范围盘点结论「0 适用」落档（doc/development/DPS-S5-写链幂等盘点-v1.0.0.md），见 DPS S5 DevLogReport v1.0.0）
- 系统：DPS（画像写链）+ OpenMemory（写链）+ OpenLLM（writeback 队列）
- 改动点：共享业务对象更新带版本/乐观锁（DPS version 递增为范式）；异步/队列写带幂等键（message_hash UNIQUE）防重放双写。
- 实现步骤：① 写链统一"读版本→校验→版本+1 写"；② 队列消费按幂等键去重；③ 冲突返回 409 并留痕。
- 测试用例：并发双写版本冲突 409；消息重放不产生双写；version 单调递增。
- 验收断言：并发写用例全绿；重放幂等（DB 行数不变）。

### K15 REAL_* 兜底收口
- 规则/升级项：§12.9 R-L1-1 → LL-3 + 复盘 §8.2-6；批次 R2；前置 K09；状态 ✅已完成（实施，OpenLLM S4-T3：出站头唯一装配统一收口——build_outbound_headers 统一装配 + REAL_* 配置默认值标记 deprecated 业务路径零依赖（兜底仅服务账号/健康探活保留）+ scan_real_fallback_business_usage 静态扫描 0 命中，见 OpenLLM S4 DevLogReport v1.0.1）
- 系统：OpenLLM（配置/编排）
- 改动点：REAL_* 配置默认值标记 deprecated；仅服务账号/健康探活场景允许；随发布批次移除业务路径依赖。
- 实现步骤：① 全仓定位 REAL_* 读取点；② 业务路径改读透传/服务账号身份；③ deprecated 日志 WARN；④ 发布批次删除残留。
- 测试用例：无 REAL_* 默认值时业务链路不依赖配置兜底。
- 验收断言：业务数据请求身份与 REAL_* 默认值零耦合（静态扫描）。

### K16 OpenRAG 表级归属迁移
- 规则/升级项：§12.9 R-L2-1（RG 部分）→ RG-1；批次 R2；前置 —（先于 LL-2 REAL 启用）；状态 ✅已完成（实施，OpenRAG S3-T2：collections/documents/chunks 归属列 tenant_code 幂等迁移（无 alembic，storage/migrations.py create_all/DDL 幂等迁移器）+ 存量回填保留码 openrag-local（可推导行按 metadata 回填）+ scripts/tenant_backfill_report.py 对账 0 孤儿 + B2 碰撞防护（openrag-local/default ∉ OpenBase 租户码空间；M2 受信保留码入站 400），键不迁移遵循 §6，见 OpenRAG S3 DevLogReport v1.0.1）
- 系统：OpenRAG（schema/迁移）
- 改动点：collections/documents（chunks 随文档）补 `tenant_code` 列；存量行增量回填（键不迁移，遵循 §6）。
- 实现步骤：① 迁移加列（幂等）；② 回填策略：默认域/按归属规则逐行回填并出对账报告；③ 写路径落 tenant_code。
- 测试用例：迁移幂等重放；回填后查询过滤正确；对账报告 0 孤儿行。
- 验收断言：全量行带 tenant_code；无"无主"数据（对账报告）。

### K17 OpenLLM 前缀归一
- 规则/升级项：§12.9 R-L2-1（LL 部分）→ LL-4；批次 R2；前置 K09；状态 ✅已完成（实施，OpenLLM S4-T5：会话/记忆前缀与 namespace 归一 tenant_code（M2=受信 X-Tenant-ID / M1=本地租户码）+ org 兼容只读别名 + 保留码空间不变，跨域会话互不可见，见 OpenLLM S4 DevLogReport v1.0.1）
- 系统：OpenLLM（会话/记忆命名）
- 改动点：会话/记忆前缀/namespace 归一 tenant_code（替换 org 兼容写法）。
- 实现步骤：① 盘点前缀语义；② 归一为 tenant_code；③ org 兼容读路径保留（只读别名）。
- 测试用例：新旧前缀会话串接正确；跨域会话互不可见。
- 验收断言：新写数据全部 tenant_code 前缀；旧数据只读兼容无串域。

### K18 DPS org/tenant 归一 + code 冲突检测
- 规则/升级项：§12.9 R-L2-1（DPS）+ R-L3-1 → DP-2；批次 R2；前置 —；状态 ✅已完成（实施，DPS S5-T2：org/tenant 归一 tenants.code 对齐 OpenBase 权威源（X-Tenant-ID=code 规范形态 + id/code 双形态解析收口）+ code 冲突检测与重映射脚本 `scripts/tenant_code_reconcile.py`（以 OpenBase 为准重映射 + 留痕）+ 冲突清单 0 未决；步骤③ user_roles 绑定 OpenBase 主体键随 DP-3（S5-T3 绑定总线化：user_roles 以 OpenBase 主体键绑定 + deactivated/restored 生命周期联动）一并收口，见 DPS S5 DevLogReport v1.0.0）
- 系统：DPS（schema/映射/中间件）
- 改动点：org/tenant 归一 tenants.code 语义；接入前执行 code 冲突检测（对账 SQL/脚本）→ 冲突清单 → 以 OpenBase 为准重映射 → 留痕。
- 实现步骤：① 冲突检测脚本（本地 vs OpenBase code 对账）；② 归一迁移与重映射；③ user_roles 绑定 OpenBase 主体键（联动 DP-3）；④ 迁移记录归档。
- 测试用例：冲突检测脚本输出与人工对账一致；重映射后双通道身份等价。
- 验收断言：code 冲突清单闭环（0 未决）；归一后隔离/鉴权回归全绿。

## 附：卡 ↔ 规则 ↔ 升级项总表

| 卡 | 规则/依据 | 升级项 | 批次 |
|----|-----------|--------|------|
| K01 | R-H1-1 | OB-3 | R1 |
| K02 | R-H1-2 | SYS-1 | R1 |
| K03 | R-H1-4 | OB-3 | R1 |
| K04 | R-H2-1/2/3 | OB-2 | R1 |
| K05 | R-H3-1/2/3/4 | OM-2（协同 OM-1） | R1 |
| K06 | R-M1-1/2 | OM-3 | R1 |
| K07 | R-M2-1/2 | SYS-1 | R1 |
| K08 | R-M4-1/2 | OB-11 | R1 |
| RA-01 | 最小集 §4.5/§11（非 §12） | OB-1 | R1 |
| RA-02 | 最小集 §4.1/§5（非 §12） | OB-2 状态机 / OB-4 | R1 |
| RA-03 | P2-2 Phase1 | OB-5 / DP-1 | R1 |
| RA-04 | S3-3 / P2-2 T4 | DP-5 | R1 |
| RA-05 | P2-2 Phase2 | OM-1 | R1 |
| RA-06 | 规划 §4 门禁 | R1 门禁 | R1 |
| K09 | R-H1-3 | LL-3 | R2 |
| K10 | R-H3 | RG-2 | R2 |
| K11 | R-M1 | RG-3 | R2 |
| K12 | R-M1 | DP-6 | R2 |
| K13 | R-M3-1/2 | OB-7 | R2 |
| K14 | R-M5-1/2 | DP-4 | R2 |
| K15 | R-L1-1 | LL-3 | R2 |
| K16 | R-L2-1（RG） | RG-1 | R2 |
| K17 | R-L2-1（LL） | LL-4 | R2 |
| K18 | R-L2-1（DPS）+R-L3-1 | DP-2 | R2 |

## 附：S2 段（OpenMemory）跨仓收口执行摘要（v1.4.0 回写，2026-09-09）

> 依据：OpenMemory S2 立项方案 v1.1.0 [Approved] / 设计草案 v1.0.3 [Approved] / DevLogReport v1.0.1 [Approved] / 测试报告 v1.0.1 [Approved] / doc/design/OpenMemory-K07-端点过滤矩阵填报 v1.0.1 [Approved]；OpenBase 侧事件契约端点 commit 0713ec1（GET /api/v1/identity/events，2026-09-09 冻结）；S2 段门禁 2026-09-09 人工批准五项全绿，遗留=无阻断项。

| 本卡/规划项 | S2 落地（T# / 迁移 / 产物） | 状态 |
|-------------|------------------------------|------|
| K02(OM) 协议头入站校验（SYS-1 下游） | S2-T1/T2：IdentityGate 来源白名单（非白名单带头 403）+ block_subject_gate + B-1 agent 双层认证（受信白名单来源身份头），fail-closed | ✅已完成 |
| K05(OM-2) 行控 | S2-T3：repository/数据访问行级 (tenant_code, owner) 强制过滤 fail-closed 收口（豁免清单/审计门禁） | ✅已完成 |
| RA-05(OM-1) sessions 端点归属 | S2-T4：sessions list/get/terminate 归属显式化收口 | ✅已完成 |
| K06(OM-3) 复合唯一 | S2-T5：namespace → (tenant_code, name) 复合唯一，alembic v702 幂等 | ✅已完成 |
| OB-11(OM 存量归属映射，§12.9 R-L2-1(OM)；编号口径见 OM-S2 文档) | S2-T6：alembic v703 幂等回填 + scripts/scope_backfill_report.py 对账 0 孤儿（W1-4，不改主键不迁键） | ✅已完成 |
| L1-1 OM 事件真实消费端（domain=memory） | S2-T7：alembic v704 阻断集 + event_id 幂等落库 + 主备双通道（PullChannel 契约桩回放绿，S2-T13-4） | ✅已完成（真实 HTTP 双签移交部署/联调窗口与 S7 级联验证） |
| K07 OM 端点-过滤矩阵填报（SYS-1 续） | S2-T10：doc/design/OpenMemory-K07-端点过滤矩阵填报 v1.0.1 [Approved]（底单全覆盖、缺口清零）+ CI s2-k07-matrix-gate job | ✅已完成 |
| OM-4（M1 独立模式兼容 / M2 受信编排头采纳） | S2-T11（角色互译 OM 档位）+ S2-T12（M1/M2 推导开关） | ✅已完成 |
| L3-2 OM 贯通冒烟 | S2-T13：scripts/smoke_l3_2.py + tests/unit/test_l3_2_smoke.py（契约桩回放断言绿；真实 HTTP 双签依赖 OpenBase commit 0713ec1，移交部署/联调窗口与 S7；事件通道属身份权威同步面，不纳入 S7 主备切换演练——原则边界①） | ✅已完成 |
| S2 段门禁 | 五项门禁（协议头入站校验 / 行控 fail-closed 默认 / 消费端阻断生效 / 存量回填 0 孤儿 / 冒烟用例绿）2026-09-09 人工批准全绿 | ✅ |

- **OM-1~4 收口**：OM-1（RA-05）→ S2-T4；OM-2（K05）→ S2-T3；OM-3（K06）→ S2-T5；OM-4 → S2-T11/T12，均已收口（见 OpenMemory S2 文档 §1.1）。
- **提交链说明**：OpenMemory 仓 S2 产物因 git 沙箱受限保留工作树（HEAD 6cbfb71=v6.9.0 发布闭环），实际提交待沙箱外按《doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md》执行（v7.2 基线 → S2 批次），提交后 hash 回填本摘要；任务执行链以 OpenMemory S2 DevLogReport v1.0.1 T1~T13 记录为准。OpenBase 侧锚点 commit 0713ec1=事件列表契约端点（已在 main）。

## 附：S3 段（OpenRAG）跨仓收口执行摘要（v1.5.0 回写，2026-09-09）

> 依据：OpenRAG S3 立项方案 v1.1.0 [Approved] / 设计草案 v1.0.1 [Approved] / DevLogReport v1.0.1 [Approved]（2026-09-09 S3 段门禁人工批准，评审人=项目负责人） / 测试报告 v1.0.0 [Final] / doc/design/OpenRAG-K07-端点过滤矩阵填报 v1.0.0 [Final]（openapi 权威底单 121 行：豁免 10/覆盖 111，经 S3 段门禁人工批准复核）；OpenBase 侧事件契约端点 commit 0713ec1（GET /api/v1/identity/events，2026-09-09 冻结）；S3 段门禁 2026-09-09 人工批准五项全绿，遗留=无阻断项（Pull 真实 HTTP 双签挂起登记 Q-RG-7 与 PG/Redis 实跑补验移交部署/联调窗口，见 OpenRAG S3 DevLogReport v1.0.1 §7 / 测试报告 v1.0.0 §6）。

| 本卡/规划项 | S3 落地（T# / 迁移 / 产物） | 状态 |
|-------------|------------------------------|------|
| K02(RG) 协议头入站校验（SYS-1 下游） | S3-T1：IdentityGate 行为矩阵四态（受信+头=信任 / 白名单无头=自身认证 / 非受信+头=403 PERM_UNTRUSTED_IDENTITY_HEADER / 非受信无头=本地认证不采信头）+ 身份解析收口 request.state.identity + B1 EdgeRouterMiddleware 不装配（deprecated + scan_no_edgerouter_assembly 0 违规），强校验期 fail-closed | ✅已完成 |
| RG-1/K16 表级归属迁移 | S3-T2：storage/migrations.py 幂等迁移器（无 alembic，create_all/DDL）：collections/documents/chunks 补 tenant_code 归属列 + 存量回填保留码 openrag-local（可推导行按 metadata 回填）+ B2 碰撞防护（openrag-local/default ∉ OpenBase 租户码空间；M2 保留码入站 400）+ scripts/tenant_backfill_report.py 对账 0 孤儿（不改主键不迁移 key） | ✅已完成 |
| RG-2/K10 行控强制过滤 | S3-T3：store/查询骨架 tenant_code 强制注入（postgres/sqlite 统一 scope 契约）+ scope_exemption 豁免清单（ticket+审批，只放宽 scope 不触及身份信任）+ scan_tenant_scope/scan_no_identity_header_bypass 静态门禁 0 违规，fail-closed 默认 | ✅已完成 |
| RG-3/K11 复合唯一 | S3-T4：collection 唯一升级 (tenant_code, name) 复合唯一（幂等迁移器）；同域同名 409、跨域同名并存互不可见 | ✅已完成 |
| L1-1 RG 事件真实消费端（domain=rag） | S3-T5：identity/event_consumer + blocklist：级联阻断集（deactivated 401 / suspended 403 / restored 解除）+ event_id 幂等落库 + Push（Redis pub/sub）/Pull（HttpEventsPollProvider 契约 v1.0）双通道 | ✅已完成（Pull 真实 HTTP 双签挂起登记 Q-RG-7，移交联调窗口与 S7 级联验证） |
| fail-open 收口（RG 侧，P2-1 D-V1~D-V7 / P2-2 D3 裁定映射） | S3-T6：D-V 映射表落地（D-V1 域过滤按已解析域执行 + 禁"DB 故障→无域放行"、D-V4 阻断集不可达直读 DB 不可证即拒、D-V5 非受信带头 403、D-V6 本地 service_api_key 写守卫、D-V7 agent 解析不可达 401；D-V2/D-V3 无委托不适用留痕），故障注入用例全绿 | ✅已完成 |
| OB-13 RG 侧（审计 detail.identity 六键） | S3-T7：security/audit_logger 注入 detail.identity 六键（principal/delegated=null/effective/proxy_source/proxy_chain/request_id，对齐 P2-1 §8.2），不新增审计表列 | ✅已完成 |
| K07 RG 端点-过滤矩阵填报（SYS-1 续） | S3-T8：doc/design/OpenRAG-K07-端点过滤矩阵填报 v1.0.0 + matrix.json（openapi 权威底单 121 行：豁免 10/覆盖 111，缺口清零、未覆盖清零、豁免有效、注册表无漂移）+ CI s3-static-gates k07 门禁（registry_drift 新增端点拒合并） | ✅已完成 |
| 角色档位（Q-RG-6） | S3-T9：identity/role_map 角色本地解释档位（viewer/org_member→RG viewer 只读、org_admin→editor 读写、admin→admin 管理、未知码 fail-closed ROLE_UNMAPPED 0 静默降 viewer，editor 码不入表）+ role_gate（M2 档位/写守卫）+ agent 出站头集采纳（subject_type=agent，审计含 agent/域） | ✅已完成 |
| M1/M2（Q-5=A 语义） | S3-T10：trust_mode 推导（白名单空=M1 本地认证 + default 域 / 非空=M2 受信头采纳为身份事实源，同构键覆盖）+ M1↔M2 切换 0 键/数据迁移 + verify-env contract.json schema v2 契约键分组对账（identity_trust/row_scope/identity_event/api） | ✅已完成 |
| L3-2 RG 贯通冒烟 | S3-T11：scripts/smoke_l3_2.py + tests/unit/test_s3_t11_l3_2_smoke.py（场景 ① 受信通道端到端 ② 越权矩阵 ③ 跨域同名不可见 ④ 级联阻断 ⑤ Pull 契约桩遍历 + 真实双签登记）+ run_all_checks 聚合退出码 0（段门禁自检五项） | ✅已完成（通过；真实 HTTP 双签与 PG/Redis 实跑登记联调/部署验证窗口） |
| S3 段门禁 | 五项门禁（① 过滤隔离用例全绿 ② 协议头入站校验生效 ③ 级联阻断生效 ④ 存量回填 0 孤儿 ⑤ L3-2 冒烟通过）2026-09-09 人工批准全绿 | ✅ |

- **RG-1~RG-3 与 K02/K07(RG) 收口**：RG-1（K16）→ S3-T2；RG-2（K10）→ S3-T3；RG-3（K11）→ S3-T4；K02(RG) → S3-T1；K07(RG) → S3-T8；角色档位 → S3-T9（Q-RG-6）；均随 OpenRAG v1.10.0（拟）S3 段收口（见 OpenRAG S3 文档 §1.1 定案与设计草案 §1.4 覆盖矩阵；S3 全组 144 用例恒绿，74 条 RED 断言全覆盖）。
- **提交链说明**：OpenRAG 仓 S3 产物因 git 沙箱受限保留工作树（HEAD 959ef83=v1.9.1 发布闭环；2026-09-09 实测 22 M + 32 ??，全部属 S3、无历史未提交基线），实际提交待沙箱外按《doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md》v1.0.1 执行（release/v1.10.0 拟 → S3 四批），提交后 hash 回填本摘要；任务执行链以 OpenRAG S3 DevLogReport v1.0.1 批次 1~3（T1~T11 + B2 遗留 + 段门禁自检五项）记录为准。OpenBase 侧锚点 commit 0713ec1=事件列表契约端点（已在 main）。

## 附：S4 段（OpenLLM）跨仓收口执行摘要（v1.6.0 回写，2026-09-10）

> 依据：OpenLLM S4 立项方案 v1.1.0 [Approved]（OB-LL-S4-v1.1.0）/ 设计草案 v1.0.1 [Approved]（OB-LL-S4-DESIGN-v1.0.1） / DevLogReport v1.0.1 [Approved] / 测试报告 v1.0.1 [Approved] / doc/test/OpenLLM-JT-台账-S4（[Approved]，2026-09-10 S4 段门禁人工批准，评审人=项目负责人） / doc/design/OpenLLM-K07-端点过滤矩阵填报 v1.0.0（经 S4 段门禁人工批准复核）/ doc/planning/OpenLLM-S4-批次1基线收口登记清单 v1.0.0（基线 A~E 分类：A=S0 探活既有已审查 / B=版本欠账对齐 v2.14.3 / C=S4 承载版本 v2.15.0 拟仅登记 / D=S4 批次1 / E=噪音不提交）；OpenBase 侧事件契约端点 commit 0713ec1（GET /api/v1/identity/events，2026-09-09 冻结）；S4 段门禁 2026-09-10 人工批准五项全绿，遗留=无阻断项（真实 HTTP 双签登记非沙箱复核与联调/部署验证窗口；写路径等价/K14 幂等/L2-1 切换演练终验/L2-2 终验/K07 RA-06 终验引用/错误面收敛随 S7，见 OpenLLM S4 测试报告 §4）。

| 本卡/规划项 | S4 落地（T# / 模块 / 产物） | 状态 |
|-------------|------------------------------|------|
| K09（R-H1-3 → LL-3）编排出站身份透传 | S4-T2：backend/app/services/external_identity.py 身份透传基座（对话上下文 identity resolve 链 user→tenant 全四维采纳 + 来源白名单矩阵）+ 身份解析收口 request.state.identity 六键 | ✅已完成 |
| LL-1 探活提交（S4-T1） | S4-T1：doc/planning/OpenLLM-S4-批次1基线收口登记清单 v1.0.0（A~E 分类）+ backend/tests/unit/test_dps_probe_real_health.py 真实契约只读面健康检查接入契约对账（client.ping GET /api/v2/portrait/list?page=1&page_size=1），A 直连标注（Q-LL-3），S0 基线文件不改造 | ✅已完成 |
| LL-2 REAL 契约开关（S4-T4） | REAL 双义拆分（探活/服务兜底 vs 业务身份）全启用 + 业务兜底身份废弃（无 resolve 上下文走服务账号语义不落业务域 WARN）；verify-env production REAL 主用期望拦截登记非沙箱复核 | ✅已完成 |
| LL-4/K17 前缀归一（S4-T5） | namespace/会话/记忆前缀归一 tenant_code（M2=受信 X-Tenant-ID / M1=本地租户码）+ org 兼容只读别名 + 保留码空间不变，跨域会话互不可见 | ✅已完成 |
| LL-5 服务账号化（S4-T6） | 服务账号语义（M1 sk-openllm-* 自身认证）+ 匿名写拒绝 PERM_SERVICE_KEY_WRITE_DENIED；服务账号消费随 S1b 完成态（sk-agent）双签 | ✅已完成 |
| LL-6 画像注入发布（S4-T6） | DPS 画像服务账号写守卫 + 注入发布批次登记（发布批次核查表登记非沙箱复核） | ✅已完成 |
| K15 REAL_* 兜底收口（S4-T3） | build_outbound_headers 出站头唯一装配统一 + REAL_* 配置默认值 deprecated 业务路径零依赖（兜底仅服务账号/探活保留 + WARN）+ scan_real_fallback_business_usage 静态扫描 0 命中 | ✅已完成 |
| L2-1 B 主 A 备（S4-T7） | backend/app/identity/channel.py ChannelStateManager 状态机单主路径（配置声明 + 显式切换/回切 + 降级头/告警，禁双主双写）；真实切换演练 S7（本段产出演练脚本与矩阵基线） | ✅已完成（真实切换演练 S7 终验） |
| L2-2 通道矩阵基座（S4-T8） | matrix_rows 通道覆盖矩阵（读路径 B 主全绿 + A 备 covered + 健康探活/管理面 A 直连豁免行显式标注）；写路径 A/B 等价与 K14 幂等登记 S7 终验（Q-LL-8） | ✅已完成（写路径等价/K14 登记 S7 终验） |
| K02(LL) 协议头入站强校验（S4-T9） | IdentityGate 全端点收口 + 强校验豁免清单（GATE_EXEMPT_PATH_PREFIXES=/health /metrics /docs /redoc /openapi.json，ticket+审批+到期）+ 保留码 org 只读别名入站 400 + scan_identity_bypass 0 绕过（放宽期→豁免清单→enforce 强校验到期清零，Q-LL-2） | ✅已完成 |
| OB-13 LL 侧（审计 detail.identity 六键） | S4-T10：audit_identity.build_identity_detail 六键（principal 含 agent_id/auth_method / delegated=null / effective / proxy_source / proxy_chain / request_id）+ 审计中间件 extra.identity 接线 + X-Request-Id 受信透传/非受信重生成 + 通道切换事件并入 identity + 敏感字段不落静态断言 | ✅已完成 |
| K07 LL 端点-过滤矩阵填报（S4-T11） | doc/design/OpenLLM-K07-端点过滤矩阵填报 v1.0.0（S4 聚焦端点集十列全覆盖 + A 直连豁免行对账 + k07_isolation_registry 隔离注册表缺口清零 + 新增端点无隔离用例门禁拒绝） | ✅已完成 |
| 角色档位（互译表 DPS 出站） | S4-T12：role_map 本地解释四码→档位（admin/org_admin/org_member/viewer，未知码 403 ROLE_UNMAPPED 0 静默降级）+ 写守卫 require_write_tier（只读档 4034 PERM_FORBIDDEN）+ 出站 DPS 互译（对齐 OpenBase 角色互译表 Q-D）+ OM/RG 原样透传 + agent 头集 | ✅已完成 |
| M1/M2（Q-5=A 语义） | S4-T13：config.trust_mode 推导（非空⇔m2）+ M1 本地会话自足 / M2 受信头覆盖本地身份 + 键/数据 0 迁移（键生成幂等 + org 只读别名 + 保留码空间不变） | ✅已完成 |
| verify-env（S4-T14） | backend/scripts/verify-env/contract.json 契约键组（identity_trust/REAL/channel/upstream）+ verify_env.py 对账（dev 全 pass / production REAL 期望拦截 fail-fast 非零退出） | ✅已完成 |
| L3-2 LL 贯通冒烟（S4-T15） | backend/scripts/smoke_l3_2.py + tests/unit/test_s4_t15_l3_2_smoke.py（B 编排出站带头全绿 / A-B 等价 / 越权 403 / 跨域不可见 / REAL 零耦合 + 段门禁自检五项）；真实 HTTP 双签登记联调窗口与 S7 | ✅已完成（通过；真实 HTTP 双签登记非沙箱复核与联调/部署验证窗口） |
| S4 段门禁 | 五项门禁（① 通道 B 全面主用 ② 通道矩阵全绿 ③ LL 收口用例全绿 ④ 强校验生效 0 绕过 ⑤ L3-2 冒烟通过）2026-09-10 人工批准全绿 | ✅ |

- **LL-1~LL-6 与 L2-1/L2-2/K02(LL)/OB-13/K07(LL)/角色档位/M1/M2 收口**：LL-1 → S4-T1；K09（LL-3 透传）→ S4-T2；K15（LL-3 REAL 收口）→ S4-T3；LL-2 → S4-T4；LL-4/K17 → S4-T5；LL-5/LL-6 → S4-T6；L2-1 → S4-T7；L2-2 → S4-T8；K02(LL) → S4-T9；OB-13 → S4-T10；K07(LL) → S4-T11；角色档位 → S4-T12；M1/M2 → S4-T13；verify-env → S4-T14；L3-2 → S4-T15；均随 OpenLLM v2.15.0（拟）S4 段收口（S4 全组 306 passed 恒绿 + ruff 0；见 OpenLLM S4 文档 §1.1 与设计草案 §1.4 覆盖矩阵）。
- **提交链说明**：OpenLLM 仓 S4 产物因 git 沙箱受限保留工作树（HEAD a552cbf=v2.14.3 发布闭环，分支 `feature/v2.13.0-openrag`；2026-09-10 实测 git status 430 项——.pylib/__pycache__/data db/backup 等噪音占多数，S0 探活等既有基线已按 doc/planning/OpenLLM-S4-批次1基线收口登记清单 v1.0.0 分类 A~E 文件级登记），实际提交待沙箱外按《doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md》v1.0.2 执行（基线 1 批 + S4 四~六批），提交后 hash 回填本摘要；任务执行链以 OpenLLM S4 DevLogReport v1.0.1 T1~T15 记录为准。OpenBase 侧锚点 commit 0713ec1=事件列表契约端点（已在 main）。

## 附：S5 段（DPS）跨仓收口执行摘要（v1.7.0 回写，2026-09-10）

> 依据：DPS-S5-画像数据隔离与身份接入收口-立项方案 v1.1.0 [Approved] / 设计草案 v1.0.1 [Approved] / DevLogReport v1.0.1 [Approved] / 测试报告 v1.0.1 [Approved] / doc/design/DPS-K07-端点过滤矩阵填报 v1.0.1 [Approved] / doc/testing/evidence/s5_gate_self_check.json（段门禁自检五项证据，含 Pull 真实 HTTP 双签 PENDING 挂起登记，见 DPS 测试报告 §7）；OpenBase 侧事件契约端点 commit 0713ec1（GET /api/v1/identity/events，2026-09-09 冻结）；S5 段门禁批准口径：`2026-09-10 S5 段门禁人工批准：评审人=项目负责人经 AI 开发会话人工确认、段门禁自检五项全绿（Pull 真实 HTTP 双签 PENDING 挂起登记不阻断）、遗留=无阻断项`。

| 本卡/规划项 | S5 落地（T# / 模块 / 产物） | 状态 |
|-------------|------------------------------|------|
| K02(DPS) 协议头入站校验（SYS-1 下游） | DPS-T1：入站身份门禁（`src/identity/inbound_gate.py` + `src/middleware/identity_gate_middleware.py`）——来源白名单 + 行为矩阵四态（白名单来源+头=信任 / 白名单无头=自身认证 / 非白名单带头=403 PERM_UNTRUSTED_IDENTITY_HEADER / 非白名单无头=本地认证）；保留码与非法头入站 400（BIZ_RESERVED_TENANT_CODE）；装配顺序断言；强校验期 fail-closed（24 用例） | ✅已完成 |
| DP-2/K18 org/tenant 归一 + code 冲突检测 | DPS-T2：`tenants.code` 对齐 OpenBase 权威源（X-Tenant-ID=code 规范形态 + id/code 双形态解析收口）+ 冲突检测与重映射脚本 `scripts/tenant_code_reconcile.py`（以 OpenBase 为准重映射 + 留痕）+ 冲突清单 **0 未决**；步骤③ user_roles 绑 OpenBase 主体键联动 DP-3（11 用例） | ✅已完成 |
| DP-3 绑定总线化 | DPS-T3：`user_roles` 以 OpenBase 主体键绑定（绑定源切 OpenBase 身份总线：服务账号/角色/生命周期事件）+ deactivated/restored 生命周期联动（级联阻断与解除）+ 未绑定主体访问画像 403（延续 RA-04 无隐式降级）；废除「本地种子为唯一绑定来源」（12 用例） | ✅已完成 |
| DP-4/K14 并发写规则固化 | DPS-T4：画像写链 `WHERE version` 乐观锁（冲突 409 + 版本单调递增）；异步/队列写 `message_hash` 幂等键适用范围盘点结论 **「0 适用」** 落档（doc/development/DPS-S5-写链幂等盘点-v1.0.0.md，Q-DPS-6）（12 用例） | ✅已完成 |
| DP-6/K12 person 复合唯一 | DPS-T5：person_key 建模定案（doc/design/DPS-S5-person_key建模评审-v1.0.0.md，Q-DPS-2）后唯一键对齐 `(tenant_id, person_key)`——现约束复核即达 + 对账 **0 孤儿** + 同租户冲突 409 应用层契约 + 跨租户同 person_key 并存互不可见（12 用例） | ✅已完成 |
| L1-1 DPS 事件真实消费端（domain=dps） | DPS-T6：`src/engines/identity_event_engine.py` + 阻断集门禁（`src/middleware/block_subject_gate_middleware.py`）：级联阻断（deactivated 403 / suspended 403 / restored 解除）+ `event_id` 幂等落库 + Pull 契约桩先行（19 用例） | ✅已完成（Pull 真实 HTTP 双签 PENDING 挂起登记 Q-DPS-5，移交联调窗口与 S7 级联验证） |
| fail-open 收口（DPS 侧，D-V 裁定映射） | DPS-T7：doc/design/DPS-S5-failopen-DV裁定映射-v1.0.0.md [Approved] 落地——tenant/permission 中间件故障注入下无放行路径（fail-closed 默认），裁定映射逐条落档（14 用例） | ✅已完成 |
| OB-13 DPS 侧（审计 detail.identity 六键） | DPS-T8：审计 `detail.identity` 六键（principal / delegated / effective / proxy_source / proxy_chain / request_id，对齐 P2-1 §8.2），不新增审计表列（10 用例） | ✅已完成 |
| 角色互译表 DPS 侧接线（OB-12） | DPS-T9：角色本地解释**双码面档位化**（OpenBase 码面 + DPS 本地码面 → 档位映射）+ 未知码 **403（ROLE_UNMAPPED，0 静默降级）**（15 用例） | ✅已完成 |
| K07 DPS 端点-过滤矩阵填报（SYS-1 续） | DPS-T10：doc/design/DPS-K07-端点过滤矩阵填报 v1.0.1 + `scripts/k07_endpoint_matrix.py`——离线 openapi 权威底单 **169 行 = 覆盖 134 / 豁免 35 / 缺口 0**（uncovered 0 / 豁免无审批 0 / drift_missing 0）+ 隔离注册位（IS-DPS-*）成套登记 + CI `ci.yml` Stage2「S5-K07 endpoint matrix gate」注册（7 用例） | ✅已完成 |
| M1/M2 与服务账号（Q-DPS-7 口径） | DPS-T11：M1 独立模式（本地 JWT 签发/校验等价，trusted_proxy_sources="" ⇔ m1）/ M2 受信头采纳为事实源（键/数据 0 迁移）；服务账号写守卫新增 `src/identity/write_guard.py` 并接线 `permission_middleware.py`（X-API-Key/匿名写 403 PERM_SERVICE_KEY_WRITE_DENIED；agent 未绑定同码收敛；自然人写不受影响）；保留码入站 400；trust_mode 推导（非空⇔m2）（26 用例） | ✅已完成 |
| verify-env（契约键） | S5-T11 配套：`scripts/verify-env/contract.json` 契约键组（identity_trust / row_scope / identity_event / api，命名对齐 OpenBase 与 OpenRAG）产出登记 | ✅已完成 |
| L3-2 DPS 贯通冒烟（S5-T12） | DPS-T12：`scripts/smoke_l3_2.py` + `src/tests/test_s5_t12_l3_2_smoke.py`（① 受信通道端到端画像读 200 ② 越权矩阵 403/404 ③ 跨租户同名 person 不可见 ④ 级联阻断 deactivated→403 / restored→解除 200 ⑤ Pull 真实 HTTP 双签挂起登记 + A 直连健康探活）；`--quick` 与 `--full-gate --gate-report` 均 EXIT=0（6 用例） | ✅已完成（通过；Pull 真实双签 PENDING 挂起登记，移交联调/部署验证窗口） |
| S5 段门禁 | 五项门禁（① 画像隔离用例全绿 ② 协议头入站校验生效（enforce）③ 级联阻断生效 ④ person 复合唯一（存量回填 0 孤儿）⑤ L3-2 贯通冒烟通过）2026-09-10 人工批准全绿；证据 doc/testing/evidence/s5_gate_self_check.json（`passed: true`，`pending: true`=Pull 双签挂起位） | ✅ |

- **DP 收口与段内引用**：K18(DP-2) → DPS-T2；DP-3 → DPS-T3；K14(DP-4) → DPS-T4；K12(DP-6) → DPS-T5；K02(DPS) → DPS-T1；K07(DPS) → DPS-T10；L1-1(domain=dps) → DPS-T6；fail-open 收口 → DPS-T7；OB-13(DPS 侧) → DPS-T8；角色互译表 DPS 侧接线 → DPS-T9（OB-12）；M1/M2 与服务账号 → DPS-T11；verify-env → DPS-T11 配套；L3-2 → DPS-T12；均随 DPS v2.10.0（拟）S5 段收口（S5 全组 **168 用例恒绿**（批1 47 + 批2 43 + 批3 39 + 批4 39，12 文件逐文件独立进程）+ ruff（select=E9,F63,F7,F82,F401,F811）0 错误；见 DPS S5 DevLogReport v1.0.1 §1/§5 与设计草案 v1.0.1 §1.1 覆盖矩阵）。R1 批次 RA-03/RA-04 已随 S0 收口（DPS 提交 887c214），本段只做回归引用与联动。
- **版本处置（Q-DPS-1）**：S5 承载版本 **DPS v2.10.0（拟，随版本规划批准）**；本段**不执行** `src/config.py` version/mcp_server_version 升级动作（保持 **2.8.1**，版本号升级属发布收口步骤）；工作树 v2.9.0 未跟踪文档 3 项（画像/标注模板扩展设计文档、设计评审记录、功能需求清单）**未触碰、未混批**，另起独立隔离批。
- **提交链说明**：DPS 仓 S5 产物因 git 沙箱受限保留工作树（基线 HEAD `6b39dd4`=S0 门禁补充 / `main`；2026-09-10 实测 `git status --porcelain -uall` = **57** = A 联调 52 + B 类在途 3（v2.9.0）+ C 类噪音 2），实际提交待沙箱外按《doc/development/OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md》**v1.0.5** 执行（S5-B1 内核装配 19 → S5-B2 路由权限测试 17 → S5-B3 脚本门禁证据 8 → S5-B4 联调文档 8，共 4 批），提交后 hash 回填 DPS-JT 台账与本摘要；任务执行链以 DPS S5 DevLogReport v1.0.1 批 1~4（T1~T12）记录为准。OpenBase 侧锚点 commit 0713ec1=事件列表契约端点（已在 main）。
- **遗留（均非阻断）**：① Pull 真实 HTTP 双签 PENDING（Q-DPS-5：配置 `IDENTITY_EVENTS_BASE_URL` 指向 OpenBase commit 0713ec1 事件端点后 `smoke_l3_2.py --full-gate --strict-gate` 补跑并回填证据）；② 非沙箱复核清单（真实 PG/Redis 复核、`test_tenant_isolation attack_19` SQLite 分支、lifespan 连 PG 用例、`test_auth_v280`/`test_v2_7_api_integration` 依赖 PG/种子绑定，均登记非沙箱复核，无本段引入的新失败）；③ DPS 仓 S5 提交 hash 待沙箱外放行后回填 DPS-JT 台账与本摘要。

状态随实施推进更新；每卡验收断言可直接转测试用例标题（TDD RED 起步）。
