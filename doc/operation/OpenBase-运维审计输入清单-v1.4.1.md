# OpenBase 运维审计输入清单 - v1.4.1

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.1 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | DO-OpenBase-Test |
| 创建日期 | 2026-08-29 |
| 存放 | doc/operation/ |

---

## 1. 审计输入材料清单

| # | 材料 | 文件 | 状态 |
|---|------|------|:----:|
| 1 | 发布计划（含入场检查/版本记录） | doc/operation/OpenBase-发布计划-v1.4.1.md | ✅ |
| 2 | 部署执行报告 | doc/operation/OpenBase-部署执行报告-v1.4.1.md | ✅ |
| 3 | 上线检查报告 | doc/operation/OpenBase-上线检查报告-v1.4.1.md | ✅ |
| 4 | 数据运维说明 | doc/operation/OpenBase-数据运维说明-v1.4.1.md | ✅ |
| 5 | 回滚方案 | doc/operation/OpenBase-回滚方案-v1.4.1.md | ✅ |
| 6 | 运维手册（含移交清单） | doc/operation/OpenBase-运维手册-v1.4.1.md | ✅ |
| 7 | 发布复盘报告 | doc/operation/OpenBase-发布复盘报告-v1.4.1.md | ✅ |
| 8 | Release Note | doc/release/OpenBase-Release-Note-v1.4.1.md | ✅ |
| 9 | 测试回溯审计（Step 4 门禁） | doc/audit/verification/OpenBase-测试回溯对比审计报告-v1.4.1.md | ✅ |
| 10 | 阶段审计报告 Stage4 | doc/audit/review/OpenBase-阶段审计报告-Stage4-v1.4.1.md | ✅ |

## 2. 部署验证关联测试追溯

| 验证项 | 关联 TT-ID | 结果 |
|--------|-----------|:----:|
| 登录 admin（真实 PG） | TT-v1.4.1-001 | ✅ |
| 服务 Key 签发/列表/吊销 | TT-v1.4.1-003/017 | ✅ |
| proxy 双通道（X-API-Key/Bearer/JWT） | TT-v1.4.1-041~044/046 | ✅ |
| 越权/越 scope（401/403） | TT-v1.4.1-018/045 | ✅ |
| 四维身份头 | TT-v1.4.1-013 | ✅ |

## 3. 遗留事项（移交运维跟踪）

| 项 | 级别 | 计划 |
|----|:---:|------|
| 服务 Key 内存存储无持久化 | P2 | v1.5+ 接 DB |
| S3/MinIO 生产全量接入验证 | P2 | 测试基座批次 |
| OTel/告警/依赖扫描 | P2 | B 类 v1.5+ |
| 四系统对接 | P2 | 按需分批 |
| TD-新增-009（全量 pytest 崩溃） | P2 | v1.4.2 还债 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | DO-OpenBase-Test | 初始创建：v1.4.1 运维审计输入清单（10 项材料 + 追溯 + 遗留） |
