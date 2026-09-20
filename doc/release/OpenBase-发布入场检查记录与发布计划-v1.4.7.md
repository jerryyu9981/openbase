# OpenBase 发布入场检查记录 + 发布计划 - v1.4.7

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.7（四仓日志接入补完 · 日志域收官 · 跨仓，承接型小版本） |
| 文档版本 | v1.0.1 |
| 状态 | **[Approved]**（上线发布批准：2026-09-20，批准人＝用户） |
| 作者 | DO-OpenBase-Ops |
| 创建日期 | 2026-09-20 |
| 存放 | doc/release/ |

---

## 1. 发布入场检查（5.0）

| 检查项 | 结果 | 依据（可复核） |
|--------|:---:|------|
| Step 4 测试矩阵完成 | ✅ | 《OpenBase-测试报告-v1.4.7》**v1.10.0**；测试计划四项判据全达成 |
| 覆盖率达标 | ✅ | 全量套件 `run_regression.py --cov`（85 文件 / 29 组）包级 TOTAL **87.7%**；本版本修改文件 `openbase/settings.py` **100%**、`openbase/modules/rag_proxy/__init__.py` **93.8%**（均达 `AGENTS.md` 新增代码 ≥90% 口径） |
| UAT 通过 | ✅ | BL-147-05 四仓端到端验收（验收数值最终权威口径 `-PerFamily 10`：业务路径 **22/22**、四仓可检索 **4/4**、JSONL 合法率 **100%**） |
| 测试回溯审计通过 | ✅ | 《OpenBase-测试回溯对比审计报告-v1.4.7》**v1.0.8**：判据 1~4 全达成、缺陷 5/5 闭环、观察项 **5/5 闭合**、审计侧建议允许进入 Step 5（**已获人工批准，2026-09-20**） |
| Step 4 阶段审计通过 | ✅ | 《OpenBase-阶段审计报告-Stage4-v1.4.7》**v1.0.6**：6 项关键检查点 **6/6 一致通过**、产出物 6/6、结论＝允许进入 Step 5 |
| 未解决 P0/P1 缺陷 | ✅ **0** | DEF-BE-147-001（P0）/002（P0）/003（P1）/005（P1）全部闭环；004（P2，工具链）闭环；无未闭环 P0/P1 |
| 全量回归基线 | ✅ | **`passed=1008 / failed=0 / skipped=4`**（2026-09-20 20:51→21:41 全量复跑，退出码 0；同批 `ruff` 0 错误） |
| 版本/commit/tag 明确 | ✅ 已完成 | 发布分支 `main`；发布 commit **`8d22302`**；**tag `v1.4.7` 已创建并推送**（附注标签 `b29ae9e6` → `8d22302`，origin + backup 双远程，见 §3） |
| 回滚策略明确 | ✅ | 见《OpenBase-回滚方案与运维手册-v1.4.7》：tag 回滚 + 四仓各仓独立回滚；本版本**无 DB schema 变更** |
| 四仓跨仓回执完整 | ✅ | DPS `145d858` + **`0954b9a`（P1 修正，三远程同 hash）**、OpenLLM `0c44c26`、OpenMemory `6d18e49`、OpenRAG `390f5dd` |
| 全阶段产出物盘点（空输出率） | ✅ **0%** | 见 §4 盘点表（`doc/version` 50、`doc/requirements` 52、`doc/design` 91、`doc/development` 50、`doc/test` 368、`doc/operation` 45、`doc/audit` 117 个文件，均非空） |
| 版本号一致性（强制规则 10） | ✅ | `.devflow/project-config.json` → `"version": "1.4.7"`（与待发布版本一致，**无需自动更新**）；`lastRelease` 仍为 `v1.4.6`，将在发布完成后更新；本项目**无 `devflow-plugin/devflow-config.json`**（该文件属 DevFlow 插件仓库，非本项目），项目侧版本载体为本配置 + `.devflow/state.json` |

**入场结论：✅ 通过 —— 材料齐备、无未闭环 P0/P1；`tag v1.4.7` 已于发布时创建并推送 origin + backup，Chekclist 第 8~12 项全部闭合（证据见 §3）。**

## 2. 发布计划（5.1）

| 项 | 内容 |
|----|------|
| 发布窗口 | 2026-09-20（开发环境 Dev 发布） |
| 负责人 | DO-OpenBase-Ops（发布执行）；AU-OpenBase-Ops（审计）；**审批人＝用户（上线发布批准）** |
| 影响范围 | 后端：`openbase/settings.py`（`rag_inject_identity_headers` 开关）、`openbase/modules/rag_proxy/__init__.py`（身份注入策略分支）、`openbase/modules/logs/repository.py`（注释 + 公开常量导出，无行为变更）、`scripts/verify_repo_log_naming.py`（新增脚本）；前端：无本版本功能变更（构建产物用于回归托管）。**四仓（DPS / OpenLLM / OpenMemory / OpenRAG）由各仓独立发布，不属本次部署范围** |
| 发布方式 | Dev 直接部署：git tag + 后端服务重启；前端 `npm run build` 静态产物（dist） |
| 发布步骤 | 1) 获「上线发布批准」→ 2) 创建附注 tag `v1.4.7` 并推送 origin / backup / github 三远程 → 3) 重启 OpenBase 后端并执行健康检查 → 4) 上线验证（§2 清单，关联 TT-ID）→ 5) 配置版本号同步（`project-config.json` `lastRelease`）→ 6) 文档归档与运维移交 |
| 排除声明 | ① 四仓 R-384 接入文件中 DPS/OpenLLM/OpenMemory/OpenRAG 侧改动由各仓自行评审发布（各仓 hash 已入库、DPS P1 修正三远程已同步）；② R-387 / R-388（CR-147-006）**已登记未实施**，不属本版本范围；③ Pro 环境发布与告警通道配置按《回滚方案与运维手册》约定在 Pro 窗口单独执行 |
| 通知对象 | 开发团队（本项目会话） |
| 冻结窗口 | 发布期间禁止合入 `main`（发布提交除外） |

## 3. 发布版本记录（已回填）

| 项 | 内容 |
|----|------|
| 发布分支 | `main` |
| 发布 commit | **`8d22302c29801131ec981a76a1b868d8b4c192d1`**（`docs(v1.4.7): 运维审计输入清单 v1.0.1（后端日志未入库如实更正）`，2026-09-20 21:59:16） |
| git tag | **`v1.4.7`**（附注标签，tag object **`b29ae9e6a1fc74cfd9806f1a8fbeb84cf9a638c7`** → 指向 `8d22302`；`git cat-file -t` = `tag`） |
| 推送范围 | **`main` + `v1.4.7` 同推 origin 与 backup**（本项目仅两远程；`remote.github` 为空配置，**维持豁免**，见《发布复盘与问题跟踪记录》R5/I5） |
| 推送输出原文 | origin：`738472e..8d22302  main -> main`、`* [new tag] v1.4.7 -> v1.4.7`；backup：`738472e..8d22302  main -> main`、`* [new tag] v1.4.7 -> v1.4.7` |
| 一致性自检（`git ls-remote`） | origin：`refs/heads/main = 8d22302`、`refs/tags/v1.4.7 = b29ae9e6`；backup：`refs/heads/main = 8d22302`、`refs/tags/v1.4.7 = b29ae9e6`；本地 HEAD = `8d22302`、本地 tag = `b29ae9e6` —— **三处一致** |
| 备份动作 | 执行**非破坏式** `push main + tag` 完成归档；**未执行 `git push --mirror`**（backup 仓含 `refs/remotes/*`，mirror 语义会删除远端 ref，属破坏性操作）——偏差与依据见《回滚方案与运维手册》§4 T5 |
| 变更摘要 | 四仓日志接入补完与跨仓验收闭环（BL-147-01/02/03/05）+ 日志域收官；5 项缺陷全部闭环；新增 12 例 settings 分支护栏（覆盖率 80%→100%） |
| 制品 | 源码（Python 后端 + Vue3 前端静态产物）；**无镜像构建**（沿用项目现行交付形态） |

## 4. 全阶段产出物盘点（发布前必查）

| 阶段 | 目录 | 文件数 | 本版本关键产出 | 空输出 |
|:----:|------|:-----:|---------------|:------:|
| Step 0 版本规划 | `doc/version` | 50 | 单版本规划文档 v1.4.7、Phase迭代计划 v1.4.7、本版本Backlog v1.4.7、版本规划评审记录 v1.4.7 | 无 |
| Step 1 需求分析 | `doc/requirements` | 52 | **本版本为承接型小版本，无新增需求文档**（沿用 v1.4.6 需求基线）；已完成需求侧为四仓日志接入的既有需求条目 | 无（无空输出；缺项已由版本性质声明覆盖） |
| Step 2 架构与设计 | `doc/design` | 91 | **无新增设计文档**（沿用既有部署架构与非功能设计）；策略分支设计依据见 DevLogReport §3.5 | 无 |
| Step 3 开发 | `doc/development` | 50 | DevLogReport v1.4.7、静态质量检查记录、代码逻辑审查记录、设计开发追溯矩阵、开发审计移交材料 | 无 |
| Step 4 测试 | `doc/test` | 368 | 测试计划/测试报告/测试用例 v1.4.7 + 证据目录 `evidence/v147`（回归、覆盖率、四仓补跑、部署核验） | 无 |
| Step 5 部署与运维 | `doc/operation`、`doc/release` | 45 / 见文件 | 本报告、部署执行与上线检查报告、回滚方案与运维手册、发布复盘、运维审计输入清单 | 无 |
| 审计 | `doc/audit` | 117 | Stage0/Stage3/Stage4 阶段审计、测试回溯对比审计、运维审计、全流程闭环审计 | 无 |

## 5. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-20 | DO-OpenBase-Ops | 初始创建：入场检查（12 项，唯一待办为 tag 创建，属人工门禁）+ 发布计划 + 全阶段产出物盘点（空输出率 0%）+ 版本号一致性核对（强制规则 10：无需自动更新） |
| v1.0.1 | 2026-09-20 | DO-OpenBase-Ops | **发布动作回填（获上线发布批准后执行）**：§1 tag 行由 ⚠️ 待创建改为 ✅ 已完成；入场结论由「有条件通过」改为**通过**；§3 回填发布 commit `8d22302`、附注标签 `v1.4.7`（`b29ae9e6`）、`main`+tag 双远程推送输出与 `ls-remote` 三处一致性自检、非破坏式备份决策（未执行 mirror，附依据）；状态置 **[Approved]**；文档版本 v1.0.0 → **v1.0.1** |
