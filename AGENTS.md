# OpenBase AI 编码规则（AGENTS.md）

本文件定义 OpenBase 项目 AI 辅助编码的强制规范，AI 按此规则生成代码。

## 1. 分层架构约束

* Controller（FastAPI 路由）：请求校验 + 调用 Service，不写业务逻辑

* Service：业务编排，不直接操作 HTTP

* Repository/DB 层：数据访问（SQLAlchemy 参数化查询）

* 禁止跨层调用、禁止在路由中直接拼 SQL

## 2. 错误码规范

* 错误响应统一格式：`{code, message, detail, request_id}`

* 错误码前缀：AUTH（鉴权）/PERM（权限）/PARAM（参数）/BIZ（业务）/SYS（系统）/STORAGE（存储）

* 使用 `BaseError(ErrorCode.XXX, "message")` 抛出，不直接返回裸 dict

## 3. 日志规范

* 使用结构化日志（logging + extra 字段），禁止 print

* 级别：DEBUG（调试）/ INFO（业务节点）/ WARN（可恢复）/ ERROR（不可恢复）

* 禁止记录：密码、令牌、密钥、完整请求体、个人隐私

## 4. 命名约定

* 模块/文件：snake\_case；类：PascalCase；常量：UPPER\_SNAKE\_CASE

* 禁止缩写与单字母变量（循环 i 除外）

* 有意义的描述性名称

## 5. 数据库操作规则

* SQLAlchemy 参数化查询（select/where），禁止字符串拼接 SQL

* 禁止 SELECT \*、禁止全表操作

* 迁移幂等（WHERE NOT EXISTS / create\_all）

* 多租户表操作带 tenant 过滤

## 6. 并发与安全

* 共享可变状态须加锁；关键操作幂等

* 输入校验（Pydantic schema）；SQL 注入/XSS 防护

* 敏感数据不落日志、不落 git（.env\* 排除）

## 7. 测试规则

* TDD：先写测试（RED）再实现（GREEN）

* 新增代码保持覆盖率 ≥90%

* 测试命令：`python -m pytest tests` / `python -m ruff check openbase tests`

## 8. 验证命令

```bash
python -m ruff check openbase tests   # 静态检查（0 错误）
python -m pytest tests                # 全量测试（全通过）
python -m pytest --cov=openbase       # 覆盖率（≥90%）
```

## 9. DevFlow 执行纪律（人工门禁后的连续性）

* **每一步人工批准后，直接开始下一步，不得重复询问用户是否继续**（用户指令 2026-09-30）。
* 仅在以下情形才需要回问：需要用户**决策或裁定**（如方案取舍、可行性与风险权衡）、需要**不可逆或高影响操作**的授权（如强推、改标签、删除文件）、或发现**门禁不通过 / 前置未闭合**而必须回退。
* 每步仍必须完整执行：文档产出 → 内容核对（含产出物存在性验证与变更一致性自检）→ 留痕（版本 + 修订历史）→ 推送三远程。
* 跨仓任务遵循同一纪律：派单交付后**直接推进本仓回填**，不额外征求确认。

