# OpenBase 设计开发追溯矩阵 - v1.1.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.1.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-25 |
| 关联设计 | 系统架构设计文档 v1.1.0 + 部署架构设计 v1.1.0 |

---

## 1. 追溯链说明

追溯链：**DT-ID（设计项）→ TD-ID（开发项）→ 涉及文件 → 完成状态**。

## 2. TD-ID 追溯矩阵

| TD-ID | 设计项（DT-ID） | 开发任务 | 涉及文件 | 状态 |
|-------|----------------|---------|---------|------|
| TD-11-01 | DT-11-03 模块独立版本 | 各模块 __version__ + versions.json + CHANGELOG 拆分 | openbase/modules/*/__init__.py, docs/changelog/, scripts/gen_versions.py | ✅ |
| TD-11-02 | DT-11-02 AI 规则 | .cursor/rules + AGENTS.md 编码规范 | .cursor/rules/*.md, AGENTS.md | ✅ |
| TD-11-03 | DT-11-04 OTLP 告警 | 告警规则配置 + OTLP 端点配置 | config/alerting/alert-rules.yml, openbase/settings.py, .env.example | ✅ |
| TD-11-04 | DT-11-05 多实例 SSE | Redis pub/sub 订阅接收 + 连接管理 | openbase/modules/notify/__init__.py, openbase/core/cache/redis_client.py | ✅ |
| TD-11-05 | DT-11-06 PyPI 发布 | pyproject 完善 + 构建脚本 + 发布验证 | pyproject.toml, scripts/build_release.ps1, README.md | ✅ |
| TD-11-06 | DT-11-07 Pro 部署 | 蓝绿/金丝雀部署脚本 + 上线检查脚本 | scripts/deploy_pro.ps1, scripts/verify_release.py, doc/operation/ | ✅ |
| TD-11-07 | DT-11-01 回灌兼容层 | 旧 API 别名 + 字段映射兼容层 | openbase/compat/__init__.py, openbase/compat/backends.py | ✅ |
| TD-11-08 | DT-11-01 接入指南 | 四系统接入指南 + 灰度步骤 + 回滚预案 | doc/guides/OpenBase-四系统接入指南-v1.1.0.md | ✅ |
| TD-11-09 | DT-11-08 灰度验证 | 灰度验证测试（Dev/Test/Pro 三阶段验证用例） | tests/test_grayscale.py, scripts/grayscale_check.ps1 | ✅ |

## 3. Subtask CheckList

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 设计文档规划的新建文件全部落地 | ✅ | 9 个开发项对应文件全部存在 |
| 实际文件名与设计命名一致 | ✅ | 与系统架构 v1.1.0 一致 |
| 未完成项推迟记录 | ✅ 无 | 全部完成 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | AD-OpenBase-Dev | 初始创建：9 个开发项（TD-11-01~09）对应 DT-11 设计项 |
