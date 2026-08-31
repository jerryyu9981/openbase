# OpenBase 需求基线及设计移交说明 - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | RA-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/requirements/ |

---

## 1. 需求基线

| 项 | 内容 |
|----|------|
| 基线版本 | v1.0.0（2026-08-31 需求评审批准） |
| 基线范围 | R-381 DPS 对接（RT-145-01~06，6 项 P1） |
| 变更规则 | 进入 Step 2 后需求变更须走范围变更记录（提出→分析→更新→评审→批准），回写候选需求池 |

## 2. 设计移交材料清单

| # | 材料 | 文件 | 状态 |
|:-:|------|------|:---:|
| 1 | 需求文档（FR/AC） | doc/requirements/OpenBase-开发需求文档-v1.4.5.md | ✅ |
| 2 | 需求追溯矩阵 | doc/requirements/OpenBase-需求追溯矩阵-v1.4.5.md | ✅ |
| 3 | 需求来源与干系人 | doc/requirements/OpenBase-需求来源与干系人-v1.4.5.md | ✅ |
| 4 | 需求评审记录 | doc/requirements/OpenBase-需求评审记录-v1.4.5.md | ✅ |
| 5 | 身份头映射预研 | 需求文档 §3（JWT sub/tenant_id/org_id/role → 四头） | ✅ |
| 6 | DPS 调研结论 | Explore 实测（技术栈/端口/认证/端点/无 SSE） | ✅ |

## 3. 移交要点（Step 2 设计输入）

| 要点 | 说明 |
|------|------|
| 认证设计 | dps-proxy JWT 门禁 + 四头注入（X-User-ID/X-Tenant-ID/X-Org-ID/X-User-Role），映射兜底配置 |
| 模块设计 | dps_proxy 独立模块（对标 rag_proxy，无 SSE）；settings dps_* 配置 |
| 端口规划 | DPS API_PORT=8030（注意变量名非 PORT）；入口 src/rest_api/app.py |
| 前端设计 | 画像列表/详情 2 页真实化（走 dps-proxy） |
| 排除提醒 | 四维专项挂起（本版本身份头用既有 JWT 字段）；无 SSE；DPS 前端历史条目不纳入 |
| 联调风险 | OQ-145-1（组织/租户映射）+ OQ-145-2（AI 模型服务依赖） |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | RA-OpenBase-Dev | 初始创建：需求基线 v1.0.0 + 设计移交材料（6 项）+ 移交要点 |
