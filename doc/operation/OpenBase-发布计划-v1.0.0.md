# OpenBase 发布计划 - v1.0.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Approved] |
| 作者 | DO-OpenBase-Dev |
| 日期 | 2026-08-25 |
| 存放 | doc/operation/ |

---

## 1. 发布入场检查记录

| 检查项 | 输入 | 结果 |
|--------|------|------|
| Step 4 测试通过 | 测试报告 v1.0.0（96+ 用例、覆盖率 90%） | ✅ |
| 测试回溯审计通过 | 测试回溯对比审计报告 v1.0.0 | ✅ |
| P0/P1 缺陷闭环 | BUG-001/002 已闭环，BUG-003 已修复 | ✅ |
| 待发布版本 | v1.0.0（git tag 已创建，commit 4c2edd8） | ✅ |
| 部署架构输入 | 部署架构草案 v1.0.0 | ✅ |
| 回滚策略 | 回滚方案 v1.0.0（本章节配套文档） | ✅ |

## 2. 发布窗口与负责人

| 项 | 内容 |
|----|------|
| 发布窗口 | 2026-08-25（Dev 环境） |
| 发布负责人 | DO-OpenBase-Dev |
| 审批人 | PM-OpenBase-Dev（人工批准） |
| 通知对象 | 四系统开发团队（v1.1.0 回灌后） |
| 影响范围 | 共享库 nuct 中 openbase schema（与其他系统 schema 隔离，无冲突） |

## 3. 版本与制品确认

| 项 | 值 |
|----|-----|
| 版本号 | v1.0.0 |
| Git tag | v1.0.0（4c2edd8，origin/backup 三处一致） |
| 构建方式 | pip install -e . --no-build-isolation |
| 制品 | openbase 包（可导入）+ demo_app 可执行 |
| 变更摘要 | 见版本发布说明 v1.0.0 |

## 4. 环境配置

| 环境 | 数据库 | Redis | 端口 |
|------|--------|-------|------|
| Dev（本次） | PG 192.168.0.151:5432/nuct（openbase schema） | 192.168.0.151:6380 | 8765 |
| Test（待建） | 同上（独立 schema 或同库 openbase） | 同上 | 8766 |
| Pro（规划） | 生产库（v1.1.0 规划） | 生产 Redis | 8765 |

**环境变量**（生产必须覆盖默认值）：`OPENBASE_DB_URL`、`OPENBASE_REDIS_URL`、`OPENBASE_JWT_SECRET`、`OPENBASE_MCP_API_KEYS`。敏感配置不落库、不进 git（.env* 已 gitignore）。

## 5. 发布步骤

```text
1. 环境变量注入（DB/Redis/JWT Secret/MCP Key）
2. 服务启动：uvicorn openbase.demo_app:app（端口 8765）
3. 启动时自动：建 schema/表（幂等）→ 种子 admin 用户/角色/权限 → 恢复配置（ConfigStore.hydrate）
4. 上线验证：health/login/鉴权/业务 API（13 项，见上线检查报告）
5. 监控确认：日志/Redis 缓存/健康检查
```

## 6. 风险与冻结

| 项 | 内容 |
|----|------|
| 发布冻结窗口 | 发布期间禁止其他 schema 变更（共享库操作） |
| 回滚触发 | 健康检查失败 / 登录异常 / 核心 API 5xx |
| 回滚目标 | v1.0.0 前基线（git 历史保留，DB 幂等可重跑） |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | DO-OpenBase-Dev | 初始创建：入场检查通过、发布窗口/负责人/环境/步骤/风险明确 |
