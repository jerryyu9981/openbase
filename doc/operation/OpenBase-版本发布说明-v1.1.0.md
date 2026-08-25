# OpenBase 版本发布说明（Release Note）- v1.1.0

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.1.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Final] |
| 日期 | 2026-08-25 |
| 存放 | doc/operation/ |

---

## 版本概览

**OpenBase v1.1.0：四系统接入准备 + 生产就绪**

## 新增功能

| 功能 | 说明 |
|------|------|
| 回灌兼容层 | openbase/compat：字段映射、函数别名、回滚提示（四系统接入桥接） |
| AI 编码规则 | AGENTS.md + .cursor/rules/backend.mdc（AI 辅助编码规范） |
| 模块独立版本 | 11 模块 `__version__` + versions.json + 模块 CHANGELOG |
| OTLP 告警配置 | alert-rules.yml（P99/登录失败/宕机/5xx 四规则） |
| 多实例 SSE | Redis pub/sub 跨实例广播（notify 订阅接收） |
| 发布工具链 | build_release.ps1（PyPI 构建）、deploy_pro.ps1（蓝绿/金丝雀） |
| 接入指南 | 四系统灰度接入步骤 + 回滚预案 |

## 修复与改进

- 覆盖率提升至 90%（新增灰度/兼容层/SSE 测试 12 用例）
- 全量回归 119 用例通过，ruff 0 错误

## 已知限制

| 项 | 说明 |
|----|------|
| PyPI 实际发布 | 待账号确认（R-103） |
| OTLP 告警实际触发 | 待 Collector 确认（R-103） |
| 四系统灰度切换 | 在各自环境执行（接入指南提供步骤） |
| 统一前端 | v1.2.0 规划 |

## 升级指引

```bash
pip install openbase==1.1.0   # PyPI 发布后
# 或源码部署
git checkout v1.1.0
python -m uvicorn openbase.demo_app:app --port 8765
```

## 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-25 | DO-OpenBase-Dev | 初始创建：v1.1.0 发布说明 |
