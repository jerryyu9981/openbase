# OpenBase 数据运维说明 - v1.4.7

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.7 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | DO-OpenBase-Ops |
| 日期 | 2026-09-20 |
| 存放 | doc/operation/ |

---

## 1. 数据库迁移计划

| 项 | 内容 |
|----|------|
| 本版本 schema 变更 | **无**（无新增/修改 Alembic 或等价 migration 脚本） |
| 迁移步骤 | **不适用**（无迁移可执行） |
| 迁移回滚脚本 | **不适用** |
| 发布前数据备份 | 不触发（无数据面变更）；Pro 环境若后续有变更须按 `operations-stage-execution` 要求先备份 |
| 数据校验 | 不适用（无变更即无校验对象） |

**依据（可复核）**：本版本本仓代码增量为 ① `openbase/settings.py` 新增可选开关字段 `rag_inject_identity_headers`（配置项，无持久化）② `openbase/modules/rag_proxy/__init__.py` 新增身份注入策略分支（运行时行为分支）③ `scripts/verify_repo_log_naming.py`（运维核验脚本，不写库）④ `openbase/modules/logs/repository.py` 仅注释与公开常量导出（无行为变更）。上述均**不涉及表结构、索引、约束或数据写入语义变更**。

## 2. 缓存与消息运维说明

| 组件 | 本版本影响 | 运维动作 |
|------|-----------|---------|
| Redis（6379） | **无变更**（无 key 结构变更、无新缓存命名空间）；**当前 Dev 环境不可达**（`TcpClient 127.0.0.1:6379` → Timeout） | 无需预热/清理；Pro 环境确认 `OPENBASE_REDIS_URL` 可达即可；如需清理：`redis-cli DEL <prefix>*`（谨慎） |
| 消息队列 | 本版本不涉及（无生产者/消费者变更） | 无 |
| 缓存降级 | 既有行为（Redis 不可达时降级，conftest 与运行时均容忍） | 关注降级日志；不阻塞上线 |

## 3. 数据一致性证据（关联本版本判据）

| 证据 | 内容 | 位置 |
|------|------|------|
| 四仓 JSONL 契约 | 应用日志行合法率 **100%**、`status_code` 非数字计数 **0** | `doc/test/evidence/v147/bl147-05-jsonl-contract.json`（Step 4） |
| 串联一致性 | 业务路径 **22/22** 命中、命中率 1.0（`-PerFamily 10`） | `doc/test/evidence/v147/bl147-05-chain-consistency.json` |
| 时序/抽样 | 抽样总数 40 次（4 族 × 10）、40/40 带回 `X-Request-Id` | `doc/test/evidence/v147/bl147-05-sampling.json` |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-20 | DO-OpenBase-Ops | 初始创建：声明本版本**无 DB schema 变更 / 无数据迁移**（附代码增量依据）+ 缓存与消息运维说明（Redis 不可达降级）+ 数据一致性证据索引 |
