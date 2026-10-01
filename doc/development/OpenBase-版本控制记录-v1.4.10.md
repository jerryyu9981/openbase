# OpenBase 版本控制记录 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | **v1.4.10** |
| 文档 | 版本控制记录（Step 3.2 产出，依 `code-version-backup-management`） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]** |
| 日期 | 2026-10-01 |
| 编制 | AD-OpenBase-Dev（后端）／FD-OpenBase-Dev（前端） |
| 存放 | `doc/development/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-10-01 | AD-OpenBase-Dev | 初始版本：分支策略、commit 模板与 RT-ID footer 约定、三远程推送与 tag 规则、回滚命令基线 |

---

## 1. 分支策略（配置驱动）

| 项 | 值 | 来源 |
|----|----|------|
| `branchStrategy` | **`git-flow`** | `.devflow/project-config.json` |
| 主干 | **`main`**（生产发布，稳定） | 同上 |
| 分支用途 | `release/v{版本号}` 发布准备；`develop` 日常集成；`feature/{issue}-{name}` 新功能；`hotfix/{issue}-{name}` 紧急修复 | 技能 §2.4 |
| **本版实际形态** | 本项目**单人／单线推进**，v1.4.9 及以前均**直接在 `main` 上原子提交**（无 develop／feature 分支）；**v1.4.10 沿用同一形态**（不引入分支复杂度），以**原子提交 ＋ 版本探针（tag）**保证可追溯 | 沿用既有先例 |

> **说明**：`git-flow` 配置为**可选能力**；本仓实际采用「main 单线 ＋ 原子提交 ＋ tag」形态，与 v1.4.5~v1.4.9 一致。若后续多人并行再启用 `feature/*`。

## 2. 提交约定

### 2.1 提交信息格式

```
{type}({scope}): {subject}

[optional body]

[optional footer: RT-{ID}]
```

### 2.2 类型（本版适用）

| type | 用途（本版） |
|------|-------------|
| `feat` | 22 端点代理扩展、12 页面实现（**须含对应测试文件变更** —— TDD 合规） |
| `fix` | 缺陷修复（**须含测试**） |
| `test` | 测试补强（vitest／playwright／pytest） |
| `docs` | Step 3 文档（追溯矩阵／DevLogReport／审计移交等） |
| `chore` | 配置／依赖／构建（本版**不新增依赖**，ADR-05） |
| `refactor` | 仅限 `dps_proxy` 文件拆分（ADR-01／TD-039，**不得改对外路径**） |

### 2.3 原子提交分组（本版建议序列）

| 序 | scope | 内容 | RT-ID footer |
|:--:|-------|------|--------------|
| 1 | `dps-proxy` | 22 端点路由扩展 ＋ 错误透传（先后端桩／只读） | RT-01／RT-18 |
| 2 | `dps-proxy` | 权限动作映射与身份注入对齐（不改判定逻辑） | RT-16 |
| 3 | `dps-api` | `core/api/dps.ts` 扩展 22 方法 ＋ `error.ts` 映射 | RT-02~09 |
| 4 | `portrait-ui` | 12 页面（P-01~P-12）＋ 12 路由 | RT-02~09／RT-20 |
| 5 | `ui-core` | `useAsyncState()`／`useBasisTooltip()` 抽取 | RT-02~09 |
| 6 | `test` | vitest 单测 ＋ playwright E2E ＋ 覆盖率门禁 | RT-11／RT-22 |
| 7 | `docs` | DevLogReport／静态质量／逻辑审查／审计移交 | 全局 |

### 2.4 RT-ID footer 约定

- 每条提交 footer **须引用对应 RT-ID**（《需求追溯矩阵-v1.4.10》RT-01~RT-28）；
- 一条提交涉及多 RT 时，footer 逐行列出；
- **TDD 合规**：`feat`／`fix` 提交**必须包含对应测试文件变更**，且**测试先行**（RED→GREEN）。

## 3. 版本探针与三远程

| 项 | 规则 |
|----|------|
| 版本号 | `v1.4.10`（语义化 `MAJOR.MINOR.PATCH`；本版为 **Minor**：新增能力，无破坏性变更） |
| **tag 创建时机** | **Step 5 发布阶段**创建 annotated tag `v1.4.10`（Step 3 不建 tag） |
| 三远程 | `origin`（内网主）／`backup`（内网备份，Dur-09 强制）／`github`（外网镜像） |
| 推送规则 | `git push {origin,backup,github} main`；tag 创建后 `git push {origin,backup,github} v1.4.10` |
| 一致性判据 | `git ls-remote` 三远程 `refs/heads/main` 与 `refs/tags/v1.4.10` **hash 100% 一致** |
| 备份主通道 | **本机／内网侧三远程推送**（CI 侧 `backup-mirror` 仅当 runner 可达备份远程时适用） |

## 4. 回滚基线（Step 5 用）

| 项 | 值 |
|----|----|
| 回滚目标 | 上一个已打 tag 版本 = **`v1.4.9`** |
| 首选命令 | `git revert <发布提交>`（保留历史，不触发引用改写） |
| 备选 | `git checkout v1.4.9 -- <file>`（单文件恢复） |
| 数据回滚 | **待 Step 3 完成后判定**（本版后端为**代理层**，预期**无 DB schema 变更**；若涉及则须在 Step 5 回滚方案写明） |

## 5. 环境与凭据边界

| 项 | 规则 |
|----|------|
| 开发环境 | 仅使用开发环境；**不得污染 Test／Pro** |
| 凭据 | **前端零密钥**；日志**零凭据**；`.env*` 不落 git |
| 高危操作 | 删除／批量替换／密钥写入**执行前须告警确认** |
| 文件范围保护 | **仅允许修改本版追溯矩阵「涉及文件」列内文件**；越界须请求确认 |
