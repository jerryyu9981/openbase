# OpenBase 四系统 API Key 优化 —— E3 批次执行总结报告

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.1.0 |
| 文档状态 | [Review] |
| 适用环境 | 本机（Windows / 无 Docker）/ Pre-Pro / Pro（仅语义对齐） |
| 关联批次 | `doc/audit/verification/OpenBase-四系统APIKey优化-残余项分批推进方案-v1.3.0.md`（§9.3 / §9.4 / §9.5 / §9.6） |
| 关联记录 | `...-D类部署取证执行记录-v1.0.3.md`（§5.3 E3 逐项登记、§5.4 E3b 逐项登记） |
| 关联方案 | `doc/audit/OpenBase-四系统APIKey与授权全生命周期评估与优化方案-v1.29.0.md`（§10.31 / §10.32） |
| 关联台账 | `...-残余项统一处置方案-v1.3.0.md`（§2.1 / §5.5 / §6） |
| 关联清单 | `...-A1生产验收清单-v1.1.6.md`、`...-A2生产配置收口清单-v1.1.8.md` |
| 证据文件 | `doc/audit/verification/evidence/e3/e3-native-20261102.json`（7447 B，SHA-256 `18224176AB92FDA0DA913BF83910A04DBCBC1680A4658B3EEF601D773CC94550`）；`.../e3/e3b-openllm-20261102.json`（7628 B，SHA-256 `370DAA5CA97D342E8FBD4401C1C1EF460091509DB3F5323DE39B1C7EA92D5C61`） |
| 编写 | FA-OpenBase-Dev（AI 辅助） |
| 批准 | 待人工批准 |

## 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|---|---|---|---|
| v1.1.0 | 2026-11-02 | FA-OpenBase-Dev（AI 辅助） | **E3b 补充：OpenLLM R17 身份权威进程级两向**：N1（`openbase` 缺 `OPENBASE_JWKS_URL`）拒启 `exit=3`（176.3s）、N2（非法取值 `openid`）拒启 `exit=1`（12.5s）、P1（`openbase` 正向）`/health` 200 + 本地登录 **403** 含 R17 文案、P2（`local` 对照）登录 **401** 无 R17 文案；新增 §10，同步 §1 摘要与 §7 联动；生产 ENV 全套门禁与 OpenBase 令牌放行仍 ⛔ Blocked；证据 `evidence/e3/e3b-openllm-20261102.json`（7628 B，SHA-256 `370DAA5C…D5C61`） |
| v1.0.0 | 2026-11-02 | FA-OpenBase-Dev（AI 辅助） | 首版：汇总 E3「本机生产形态」批次的目标、环境、用例矩阵、逐系统结果、Blocked 解除条件、判定边界、文档联动与复现方式；结论为 27 项 Pass / 3 项服务级 Blocked / 6 项生产前置 Blocked，真实生产实测仍 ⛔ Blocked |

---

## 1. 执行摘要

**一句话结论**：凡「启动服务即可验证」的生产门禁与两向语义，已在**本机生产形态**下一轮跑通；没有发现代码缺口，无需改业务代码；真实生产切换所需的**生产主机、DBA 变更单、共享 PG/Redis、真实 IdP** 仍不具备，相关项如实 ⛔ Blocked。

| 维度 | 结果 |
|---|---|
| 判定项合计 | **42**（31 Pass + 3 服务级 Blocked + 8 生产前置 Blocked，含重叠见 §4.4/§10；E3b 计入 4 Pass + 2 Blocked） |
| OpenLLM（E3b 补充） | R17 进程级两向全部命中（N1/N2 拒启、P1 403 含 R17、P2 401 无 R17，4 Pass）；生产 ENV 与令牌放行 ⛔ Blocked（见 §10） |
| OpenBase | D-03 / D-05 / D-06 两向全部命中（7 Pass，1 Blocked：PEM 0600） |
| DPS | K-01 / K-02 两向全部命中（4 Pass） |
| OpenRAG / OpenMemory | K-01 门禁级策略 **8/8 + 8/8** 断言通过；整服务启动 ⛔ Blocked |
| Docker | 全程**未使用**（用户约束：电脑资源有限） |
| 秘密卫生 | 证据仅含键名/状态/判定，无 PEM、密钥、令牌原文；DPS 审计仅落 `sha256[:12]` |
| 代码变更 | **无**（本批次仅取证 + 文档留痕） |

## 2. 目标与范围

**触发指令（用户原文）**：「需要生产环境启动服务执行的都一起实施」。

**目标**：把此前停留在「构造期断言 / 静态核对」的残余项，一次性推进到「真实启动进程 + 两向探针」的可复现证据状态，覆盖《残余项分批推进方案 v1.2.0》§9.3 中 E3 的**本机可执行部分**。

**范围内（本批次执行）**

| 系统 | 覆盖对象 |
|---|---|
| OpenBase | D-03（RS256 强制与验签白名单）、D-05（服务账号主体映射解析）、D-06（MCP 摘要/密钥文件/明文拒绝） |
| DPS | K-01（`STATIC_KEY_CHANNEL=closed` 与应急 bypass）、K-02（`IDENTITY_AUTHORITY=openbase`） |
| OpenRAG | K-01 静态 Key 通道策略层（`dual` / `closed` / 应急 bypass / 启动门禁） |
| OpenMemory | 同上 |
| OpenLLM（E3b 补充，v1.1.0） | R17 身份权威进程级两向：缺 JWKS 拒启、非法取值拒启、`openbase` 本地登录 403、`local` 对照 401（见 §10） |

**范围外（不在本批次，保持 Blocked）**：D-04 存量 Key 收敛、D-05 出站映射两向、D-06 只读挂载 0600、A2-04 四仓 `iss/aud` 镜像矩阵、A2-05 服务 Key 权限面、V-04/V-05/V-13、E4 跨仓、E5 触发式暂缓。解除条件见 §5。

## 3. 执行环境与方法

### 3.1 环境实测

| 项 | 实测 |
|---|---|
| 操作系统 | Windows（PowerShell 5） |
| Python | 3.12.10（`.venv-test/Scripts/python.exe`） |
| 补充依赖 | `tmp/e3-native/libs`（aiofiles / openpyxl；该 venv 无 pip，采用全局 pip 装到独立目录后注入 `PYTHONPATH`） |
| Docker | ⛔ 未安装（按用户约束不使用） |
| 数据库 | OpenBase / DPS 使用 SQLite 单进程；OpenBase 本机 PG 专用 SQL 初始化失败后自动回退内存（不影响本批门禁语义） |
| HTTP 探针 | `httpx`（脚本内置） |
| 证据生成时间 | 2026-11-02T01:42:29Z（UTC）/ 09:42:29（UTC+8） |

### 3.2 端口分配（避免与常驻服务冲突）

| 端口 | 用途 | 形态 |
|---|---|---|
| 18012 | OpenBase 正向（D-03/D-05/D-06 摘要） | `OPENBASE_ENV=production` |
| 18014 | OpenBase D-06 密钥文件形态 | 同上 + `MCP_API_KEYS_FILE` |
| 18013 | DPS `STATIC_KEY_CHANNEL=closed` | 生产形态 |
| 18015 | DPS `closed` + 应急 bypass | 生产形态 |
| 18017 | DPS `IDENTITY_AUTHORITY=openbase` | 生产形态 |

### 3.3 方法（6 步）

1. **临时材料**：脚本内生成一次性 RSA 私钥与 kid（仅落 `tmp/`，不落 `doc/`）。
2. **正向启动**：以生产形态环境变量拉起原生 `uvicorn` 单进程，等待 `/health` 或 JWKS 可达。
3. **正向探针**：`/health`、`/.well-known/jwks.json`（`kty` / `kids` / 私钥字段缺失）、受保护端点、配置解析结果。
4. **负向重启**：移走/置空关键材料（RS256 路径/kid、应急过期时间、明文 MCP Key）后**真实重启**，断言进程拒启（`exit=1`）。
5. **落证据**：按段 try/except，任一段失败不影响证据落盘；写入前对 pydantic `input_value=` 之后内容截断（含 Redis URL 片段）。
6. **判定**：仅允许 `Pass / Fail / Blocked`；`Blocked` 必须写解除条件。

## 4. 逐项结果

### 4.1 OpenBase（D-03 / D-05 / D-06）

| 编号 | 用例 | 结果 | 关键观测 |
|---|---|---|---|
| D-03 正向 | `jwt_require_rs256=true` + PEM + kid 启动 | ✅ Pass | `/health` 200；JWKS `key_count=1`、`kty=[RSA]`、`kids=[e3-native-kid]`、`private_fields=[]` |
| D-03 负向 | HS256 令牌访问 `/api/v1/auth/me` | ✅ Pass | **401** `AUTH_401 invalid or expired token`（验签白名单收敛为 `{RS256}`） |
| D-03 负向 | 缺 RS256 私钥路径 / kid 启动 | ✅ Pass | 拒启 `exit=1`；报错「生产/门禁要求 RS256：必须同时配置 … 否则拒绝启动（fail-closed）」 |
| D-05 | `SERVICE_ACCOUNT_SUBJECT_MAP` 生产启动 | ✅ Pass（配置口径） | `map_entries=1`，生产门禁放行；出站两向留 E4 |
| D-06 正向 | 生产配 MCP **摘要** 启动 | ✅ Pass | 启动 200；`mcp_hashes_configured=true` |
| D-06 正向 | 生产配 **密钥文件** 启动 | ✅ Pass | 启动 200；JWKS 同上 |
| D-06 负向 | 生产配**明文** `MCP_API_KEYS` | ✅ Pass | 拒启 `exit=1`；报错「生产环境禁止配置明文 MCP 静态 Key」 |
| D-06 负向 | PEM 只读挂载 0600 | ⛔ Blocked | Windows 无 POSIX mode 可核验（见 §5） |

### 4.2 DPS（K-01 / K-02）

| 编号 | 用例 | 结果 | 关键观测 |
|---|---|---|---|
| K-01A | `closed` + 非应急静态 Key 访问 `/api/v2/profiles` | ✅ Pass | **401** `AUTH_STATIC_KEY_CHANNEL_CLOSED`（服务本身启动成功） |
| K-01B | `closed` + 应急 bypass（ISO-8601 未来过期） | ✅ Pass | 关闭码消失（转为业务侧「缺少组织或租户标识」）；审计事件 `static_key_emergency_bypass` 存在且**无明文 Key** |
| K-01C | 配应急 Key 但 `EMERGENCY_BYPASS_EXPIRES_AT` 为空 | ✅ Pass | 拒启 `exit=1`；报错「K-01 启动门禁：应急通道必须有明确过期时间」 |
| K-02 | `IDENTITY_AUTHORITY=openbase`，`POST /api/v1/auth/login` | ✅ Pass | **403**，响应含 `AUTH_LOCAL_LOGIN_DISABLED`（仅受理 OpenBase RS256/JWKS）；`/health/liveness` 200 |

### 4.3 OpenRAG / OpenMemory（K-01 策略层）

两个仓库的 `static_key_channel` 判定逻辑同构，各执行 **8 项断言**，全部为 `true`：

| # | 断言 | OpenRAG | OpenMemory |
|---|---|---|---|
| 1 | `dual` 默认主通道启用 | ✅ | ✅ |
| 2 | `closed` 主通道关闭 | ✅ | ✅ |
| 3 | 非法模式归一为 `dual` | ✅ | ✅ |
| 4 | 应急 Key + 未来过期 → 放行 | ✅ | ✅ |
| 5 | 应急 Key 已过期 → 拒绝 | ✅ | ✅ |
| 6 | 错误应急 Key → 拒绝 | ✅ | ✅ |
| 7 | 缺过期时间 → 启动门禁抛错 | ✅ | ✅ |
| 8 | `closed` + bypass 组合策略 | ✅ | ✅ |

**限值说明**：以上为**模块级/门禁级**判定，不含整服务 HTTP 面；整服务启动因本机缺重依赖（OpenRAG 导入期原生崩溃 `0xC0000005`、OpenMemory 缺 qdrant/neo4j/sentence-transformers 等）如实 ⛔ Blocked。

### 4.4 汇总计数

| 类别 | 数量 | 说明 |
|---|---|---|
| Pass（本机生产形态） | **27** | OpenBase 7 + DPS 4 + OpenRAG 8 + OpenMemory 8 |
| 服务级 Blocked | **3** | D-06 0600、OpenRAG 整服务、OpenMemory 整服务 |
| 生产前置 Blocked | **6** | D-04、D-05 出站、D-06 0600、A2-04、A2-05、V-04/V-05/V-13（与上表 0600 重叠计一次） |

> 计数说明：证据 JSON 中 `process_exit_code=1` 属**取证结束时脚本主动终止进程**，不代表启动失败；启动成功一律以 `started=true` + `/health=200` 为准，拒启一律以 `rejected_at_startup=true` + `exit_code=1` 为准。

## 5. Blocked 清单与解除条件

| 项 | 状态 | 解除条件 |
|---|---|---|
| D-04 存量 `ob_k_` 收敛 | ⛔ Blocked | 生产 DBA 会话 + 变更单；按 `evidence/d/d-04-expired-key-convergence-20261101.sql` 分批执行（必须先于 K-01 `closed` 上线） |
| D-05 出站映射两向（映射放行 / 未映射拒绝） | ⛔ Blocked | 真实下游代理可达 |
| D-06 PEM 只读挂载 0600 | ⛔ Blocked | POSIX 部署主机侧挂载（禁内联 env） |
| A2-04 四仓 `iss/aud` 镜像矩阵 | ⛔ Blocked | 四仓同时可达（OpenRAG/OpenMemory 本机不可启动） |
| A2-05 服务 Key 权限面最小化 | ⛔ Blocked | 真实服务 Key 注册表取样 |
| V-04 跨仓吊销时延 / V-05 多实例审计链 / V-13 真实 IdP | ⛔ Blocked | 共享 PG/Redis 多实例 + 可达 IdP |
| OpenRAG 整服务启动 | ⛔ Blocked | 安装 aiohttp / qdrant-client / faiss / sentence-transformers（或换生产主机） |
| OpenMemory 整服务启动 | ⛔ Blocked | 安装 qdrant-client / neo4j / sentence-transformers / openai 且具备 PG/Redis 共享态 |

**硬顺序约束（不可颠倒）**：`D-04 收敛 → K-01 closed`；`全量 RS256 换发 → D-03`；`E1 模板补齐 → D-06 注入`；`D-05 注入与 D-06 挂载同窗口`。

## 6. 判定边界与合规声明

1. ✅ 一律为 **`Pass（本机生产形态）`**：验证的是代码门禁与两向语义，**不替代**真实生产主机、共享 PG/Redis、多实例与真实 IdP 实测。
2. 本机 SQLite 回退内存：不覆盖 DB 相关语义（事务、迁移、多实例一致性）。
3. 秘密零泄漏：证据与文档只保留键名与「已配置/未配置」；不落 PEM/证书/令牌原文；DPS 审计仅 `sha256[:12]`。
4. 无 Docker：全部为原生进程取证，符合用户「资源有限」约束，但也意味着容器化路径（镜像、健康检查、只读挂载）未验。
5. 构造期门禁 ≠ 真实重启：本批次已把此前「构造期断言」升级为**真实重启两向**，两者不可混用。

## 7. 文档联动与留痕

### 7.1 本批次联动升版

| 文档 | 版本 | 变更要点 |
|---|---|---|
| 评估与优化方案 | v1.29.0（E3 时 v1.28.0） | 新增 §10.31（E3 本机生产形态 14 行用例表 + 判定边界）；E3b 新增 §10.32 |
| 残余项统一处置方案（台账） | v1.3.0（E3 时 v1.2.0） | §2.1 增「已完成 · E3」、§5.4/§5.5/§6/§9.1 同步；E3b 补 §5 K 类说明 |
| 残余项分批推进方案 | v1.3.0（E3 时 v1.2.0） | 新增 §9.4 结果表、§9.5 判定边界；§9.3 状态更新；E3b 新增 §9.6 |
| D 类部署取证执行记录 | v1.0.3（E3 时 v1.0.2） | 新增 §5.3（16 行用例）、§3 证据清单、§4 结论修订；E3b 新增 §5.4 |
| A2 生产配置收口清单 | v1.1.8（E3 时 v1.1.7） | §6.2/§6.4/§7 补 E3 证据；0600 仍 Blocked；E3b 补 OpenLLM `IDENTITY_AUTHORITY` 证据口径 |
| A1 生产验收清单 | v1.1.5 | A1-01/A1-02/A1-11 证据列追加 e3 佐证 |
| **本报告** | v1.1.0（首版 v1.0.0） | E3 汇总 + E3b 补充（§10） |

### 7.2 交叉引用一致性

- 六份既有文档均已指向同版关联方案 v1.29.0，并对 0600 / D-04 / A2-04 / A2-05 / V 类统一标注 ⛔ 与解除条件。
- 改名升版后已全目录 grep 校验，无旧文件名（v1.28.0 / v1.2.0 / v1.0.2 / v1.1.7 / v1.0.0）残留（历史版本引用除外）。

### 7.3 提交与推送

- E3 实施与证据提交：`1de34dc`（7 files changed，321 insertions，52 deletions，含 6 个 rename + 1 个新增证据）。
- 推送：`origin` / `backup` / `github` 三远程均推进至 `1de34dc`，`git ls-remote` 三处 `refs/heads/main` 一致。
- 本报告为补录，单独提交（可用 `git log -1 --format=%h -- "doc/audit/verification/OpenBase-四系统APIKey优化-E3批次执行总结报告-v1.0.0.md"` 查询）。

## 8. 风险与后续建议

| 风险 | 影响 | 建议 |
|---|---|---|
| 本机结论被误读为生产通过 | 上线门禁形同虚设 | 交付物统一以「本机生产形态」前缀标注；生产验收仍走 A1/A2 |
| D-04 未收敛即关 `closed` | 存量 `ob_k_` 业务中断 | 严格按 §5 顺序，先分批收敛并灰度 |
| PEM 未按 0600 挂载 | 私钥可被同机进程读取 | 生产主机侧只读挂载 + 启动自检（可选：加 mode 校验告警） |
| OpenRAG/OpenMemory 依赖未装 | 无法做四仓联调（E4） | 生产窗口统一依赖基线，避免本机逐仓补装 |
| SQLite 回退内存 | 掩盖 DB 层缺陷 | 生产必须 PG；本机结论不用于 DB 相关签核 |

**建议下一步**：本批次已闭合「可本机执行」的全部项；剩余工作均需外部条件，进入**等待生产窗口**状态，不再安排本机取证。

## 9. 附录

### 9.1 证据字段索引（`evidence/e3/e3-native-20261102.json`）

| 顶层键 | 内容 |
|---|---|
| `openbase` | `d03_d05_d06_positive`、`d03_negative_missing_rs256_key`、`d06_negative_plaintext_key`、`d06_positive_keys_file`、`d06_permission_0600` |
| `dps` | `k01_closed_reject`、`k01_emergency_bypass`、`k01_negative_missing_expiry`、`k02_openbase_authority` |
| `static_key_channel` | `openrag_gate_level`、`openmemory_gate_level`、两个 `*_full_startup`（Blocked） |
| `blocked_production_items` | 6 项生产前置阻塞与原因 |
| `environment` / `generated_at` / `scope` | 解释器、补充依赖目录、UTC 时间、批次范围 |

### 9.2 复现命令（本机，无 Docker）

```powershell
& "d:\Trae CN\myproject\Dev\OpenBase\.venv-test\Scripts\python.exe" `
  "d:\Trae CN\myproject\Dev\OpenBase\tmp\e3-native\run_e3.py"
```

- 脚本内部：DPS 子进程注入 `PYTHONPATH=<DPS>/src;<libs>`；OpenMemory 以 `sys.path.insert` 加载；OpenRAG 以模块级 `importlib` 加载（须先 `sys.modules[name]=module`，否则 dataclass 解析失败）。
- 前置：`.venv-test` 存在；`tmp/e3-native/libs` 已装 aiofiles/openpyxl；端口 18012/18013/18014/18015/18017 空闲。
- 输出：证据 JSON 覆盖写入同一路径；`tmp/` 与 `libs/` 均为**非交付物**，不进 git。

### 9.3 术语

| 术语 | 含义 |
|---|---|
| 两向 | 正向（合规放行）+ 负向（违规拒绝/拒启）成对取证 |
| 本机生产形态 | 用生产配置语义在本机拉起单进程，验证门禁与语义，不替代生产实测 |
| D-03 / D-05 / D-06 | RS256 强制 / 主体映射注入 / 秘密形态与挂载 |
| K-01 / K-02 | 静态 Key 通道关闭与应急 bypass / DPS 身份权威切 OpenBase |
| Blocked | 环境不可达，必须写明解除条件，不得以构造替代 |

---

## 10. E3b 补充：OpenLLM R17 身份权威进程级两向（2026-11-02）

> **背景**：E3 覆盖 OpenBase / DPS / OpenRAG / OpenMemory 四仓，**未覆盖 OpenLLM**。R17（身份权威切到 OpenBase 后本地身份通道关闭）此前仅在 OpenBase 文档 v1.9.0 以单测闭合，缺真实进程两向。本节补齐，证据 `evidence/e3/e3b-openllm-20261102.json`（7628 B，SHA-256 `370DAA5C…D5C61`，`generated_at=2026-11-02T07:53:01Z`）。

### 10.1 环境与方法

| 项 | 实测 |
|---|---|
| 目标仓 | `D:\Trae CN\myproject\Dev\OpenLLM\backend`（只读引用，不改代码） |
| 解释器 | `.venv-test/Scripts/python.exe` + `PYTHONPATH` 追加 `tmp/e3b-openllm/libs` → `.venv-libs` → `.pylib` |
| 数据库 | 子进程 `init_db()` 预建 SQLite（`tmp/e3b-openllm/openllm.db`），`db_prepare exit=0 / ready=true` |
| ENV | `development`（R17 为 pydantic/settings 级门禁，源码无 ENV 分支，故结论与 ENV 无关） |
| JWKS | `http://127.0.0.1:18012/.well-known/jwks.json`（不可达；JWKS 惰性拉取，启动不触网） |
| Docker | ⛔ 未使用 |

### 10.2 逐项结果

| 编号 | 用例 | 结果 |
|---|---|---|
| N1 | `IDENTITY_AUTHORITY=openbase` 且 `OPENBASE_JWKS_URL` 空（`lifespan=on`） | ✅ Pass：拒启 `exit=3`，176.3s，`ValueError: IDENTITY_AUTHORITY=openbase 必须同时配置 OPENBASE_JWKS_URL（R17）` |
| N2 | `IDENTITY_AUTHORITY=openid`（`lifespan=on`） | ✅ Pass：拒启 `exit=1`，12.5s，pydantic `ValidationError`「仅允许 'local' 或 'openbase'（R17）」 |
| P1 | `openbase` 正向（`lifespan=off`） | ✅ Pass：`/health` 200；`/api/v1/auth/login` **403** 含「身份由 OpenBase 统一管理，本地开户/登录已关闭（R17）」；注册 422 |
| P2 | `local` 对照（`lifespan=off`） | ✅ Pass：`/health` 200；登录 **401**「用户名或密码错误」，**不含** R17 文案 |
| 生产 ENV 全套门禁 | 需生产 ENV + 可达 JWKS | ⛔ Blocked（`openllm_prod_env_smoke`） |
| OpenLLM 接受 OpenBase 令牌 | 需真实令牌 + JWKS | ⛔ Blocked（`openllm_openbase_token_accept`），归 E4 |

### 10.3 判定边界

- R17 与 ENV 无关：development ENV 下的拒启结论**等价于**生产口径。
- N1/N2 用 `lifespan=on`（真启动门禁路径）；P1/P2 用 `lifespan=off` 起真实进程（跳过插件发现/EdgeRouter/回写恢复等重型自检），**路由与鉴权代码路径不变**，403/401 均为真实 HTTP 响应。
- 本机导入耗时 150–185s，首跑超时曾误记为失败，已复现修正；证据含 `elapsed_seconds` / `startup_mode`。
- ✅ 一律为 `Pass（本机进程级）`，不替代生产 ENV 与跨仓令牌放行实测。
