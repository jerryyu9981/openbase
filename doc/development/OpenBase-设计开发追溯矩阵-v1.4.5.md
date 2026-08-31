# OpenBase 设计开发追溯矩阵 TD-ID - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Draft] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/development/ |

---

## 1. 追溯矩阵（DT → TD → 文件）

| DT-ID（设计项） | TD-ID（开发项） | BL-ID | 涉及文件 | 状态 |
|----------------|-----------------|-------|----------|:----:|
| DT-145-01 DPS 服务部署 | TD-145-01 DPS 8030 启动 + health + 种子数据 | BL-145-01 | DPS 项目（API_PORT=8030）；启动验证 | ⚠️ 受阻（DPS 侧 config.settings 缺失，登记任务书 M4；health 透传 502 归一化验证 ✅） |
| DT-145-02 认证边界与身份头注入 | TD-145-02 settings dps_* 配置 + AVAILABLE_MODULES 注册 + JWT 门禁 + 四头注入 | BL-145-02/03 | `openbase/settings.py`；`openbase/demo_app.py` | ✅ 完成（401 门禁 + 四头注入单测） |
| DT-145-03 dps-proxy 转发适配 | TD-145-03 dps_proxy 模块 8 端点 + 统一响应 + {detail} 归一化 | BL-145-03 | `openbase/modules/dps_proxy/__init__.py`（新建）；`tests/test_dps_proxy.py`（新建） | ✅ 完成（15 单测 + 11 冒烟） |
| DT-145-04 前端画像页真实化 | TD-145-04 dps.ts API 层 + 画像列表/详情 2 页 | BL-145-04 | `openbase-ui/src/core/api/dps.ts`（新建）；PortraitList/PortraitDetail（改造） | ✅ 完成（真实 API + 加载/错误态） |
| DT-145-05 双系统联调 | TD-145-05 联调闭环（登录→四头注入→画像→标签→报表） | BL-145-05 | 联调验证（L2/L3） | ⚠️ 部分完成（JWT 门禁 + 502 归一化 ✅；真实 DPS 联调待 M4 修复后） |
| DT-145-06 收尾与还债 | TD-145-06 还债 TD-新增-011（llm.ts SSE fetch adapter）+ 回归/发布 | BL-145-06 | `openbase-ui/src/core/api/llm.ts`（修改）；测试基座 | ✅ 完成（还债 + 全量回归通过） |

## 2. Subtask CheckList（子任务状态表）

| 子任务 | 设计规划文件操作 | 实际状态 | 偏差 |
|--------|------------------|:--------:|------|
| TD-145-02 配置 | settings.py 新增 dps_* 6 项 + AVAILABLE_MODULES 注册 | ⬜ | - |
| TD-145-02 挂载 | demo_app.py enable_module 追加 "dps_proxy" | ⬜ | - |
| TD-145-03 模块 | 新建 openbase/modules/dps_proxy/__init__.py（8 端点 + 四头注入） | ⬜ | - |
| TD-145-03 测试 | 新建 tests/test_dps_proxy.py | ⬜ | - |
| TD-145-04 API 层 | 新建 openbase-ui/src/core/api/dps.ts | ⬜ | - |
| TD-145-04 页面 | 画像列表/详情 2 页改造 | ⬜ | - |
| TD-145-06 还债 | llm.ts sendChatStream 对齐 fetch adapter | ⬜ | - |

## 3. 版本控制记录（分支策略 + commit 约定）

| 项 | 内容 |
|----|------|
| 分支策略 | main 直发（项目惯例，v1.4.4 同） |
| commit 格式 | `type(scope): subject`，footer 引用 TD-ID（如 `refs TD-145-03`） |
| TDD 合规 | feat/fix 提交必须包含对应测试文件变更；测试先于生产代码提交 |
| 备份 | 提交前 .devflow hooks（post-push）自动备份；重要节点打标 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | AD-OpenBase-Dev | 初始创建：DT→TD 追溯矩阵（6 项）、Subtask CheckList、版本控制记录 |
