# Spec：A2 审核人视角与任务领取（DPS 2.16.0 / OpenBase 1.7.0 / 前端 1.8.0）

| 项 | 内容 |
|---|---|
| 状态 | **[Implemented]**（2026-11-21 已批准并交付） |
| 日期 | 2026-11-21 |
| 上游依据 | 《OpenBase-DPS 统一前端页面功能设计》v2.6.0 §9 A2（L338）、§3 「标注员 · 快速领取任务」（L107、L114）、§12 「待我审核」依赖（L528）；用户 2026-11-21 指令 |
| 版本冻结 | DPS `2.15.0 → 2.16.0`；OpenBase 后端 `1.6.0 → 1.7.0`；前端 `1.7.0 → 1.8.0` |
| 交付链 | DPS `GET /annotations?reviewer=me&level=` ＋ `POST /annotations/{id}/claim` → OpenBase `dps-proxy` → 审核收件箱 |

## 1. 目标与范围

**目标**：让审核人按「我的 / 指定级数」查看队列，并能显式领取待审任务，使「待我审核」与任务锁定具备真实数据口径。

**范围内**
1. DPS 列表新增 `reviewer`、`level` 两个查询参数；`reviewer=me` 由服务端按 `X-User-ID`（contextvar）解析，前端不构造身份头。
2. DPS 新增 `POST /portrait/annotations/{annotation_id}/claim`（幂等领取）。
3. 列表返回 `reviewer_id`（列存在时），供前端展示归属。
4. 权限：`POST .../claim` 端点级动作声明为 `update`（语义为对既有记录的更新，非 create）。
5. OpenBase 代理新增 claim 端点；GET 参数天然透传。
6. 前端审核收件箱：`只看我的` 勾选、级数筛选、队列归属标识、`领取` 按钮。
7. 测试、版本、文档与设计回填。

**范围外**
- 不做「释放/退回领取」（上游无此语义，与既有禁则一致）；不做企微/SSO 身份改造。
- 不新增权限点。

## 2. 源码事实（已核对）

| # | 事实 | 位置 |
|:-:|---|---|
| F1 | 列表仅支持 `annotation_template/review_status/person_id/page/page_size` | `DPS/src/rest_api/routes/routes_profiles.py` L1220-1250 |
| F2 | 队列 SQL 已 JOIN `annotation_template`/`profile`，列集合经 `_annotation_columns()` 守卫 | `DPS/src/engines/annotation_template_engine.py` L909-960 |
| F3 | 审核人取自 `data.reviewer` 或 `_current_operator(x_org_id)`，后者优先 `get_user_id()`（X-User-ID contextvar） | `routes_profiles.py` L48-55、L1453-1462 |
| F4 | 审核写入 `reviewer_id` 已具备，列缺失时降级不持久化 | `annotation_template_engine.py` L1110-1140 |
| F5 | 前端严禁构造身份头，身份由 OpenBase 代理注入 | `openbase-ui/src/core/api/dps.ts` 文件头禁则 |
| F6 | 代理动态段 `/annotations/{annotation_id}` 已存在，claim 为三段路径不冲突，但需与 review 同区注册 | `openbase/modules/dps_proxy/__init__.py` L2076-2097 |
| F7 | 端点级动作覆盖表当前仅 rollback/activate/deactivate | `DPS/src/middleware/permission_middleware.py` L142-146 |

## 3. 契约

### 3.1 DPS `GET /api/v2/portrait/annotations`（扩展）

| 参数 | 类型 | 语义 |
|---|---|---|
| `reviewer` | string 可选 | `me` → 当前 `get_user_id()`；其他值按 `reviewer_id` 精确匹配 |
| `level` | int 可选，0~5 | 精确匹配 `review_level`；越界 → 400 |

- `reviewer=me` 但当前无用户身份 → 401（`detail="无法解析当前用户身份"`）。
- `reviewer_id`/`review_level` 列缺失且请求了对应过滤 → 返回空页（`total=0`），不抛错。
- 列表行新增 `reviewer_id`（列存在时），沿用既有 `items/total/page/page_size`。

### 3.2 DPS `POST /api/v2/portrait/annotations/{annotation_id}/claim`

请求体：`{}`（忽略未知字段）。

| 场景 | 响应 |
|---|---|
| 领取成功 | 200 `{annotation_id, reviewer, claimed:true, already:false}` |
| 已是本人领取（幂等） | 200 `{annotation_id, reviewer, claimed:true, already:true}` |
| 记录不存在/跨租户不可见 | 404 |
| 非 `pending` 状态 | 409 `detail="仅待审核记录可领取"` |
| 已被他人领取 | 409 `detail="记录已被其他审核人领取"` |
| 无用户身份 | 401 |
| 审核列未迁移 | 409 `detail="审核列未迁移，无法领取"` |

实现要点：单条 `SELECT ... FOR UPDATE` 不跨库可用，故采用「读 → 条件 UPDATE（`WHERE id=? AND (reviewer_id IS NULL OR reviewer_id=?)`）→ 影响行数判定」，冲突时重读并返回 409，保证并发幂等。

### 3.3 权限

- `ENDPOINT_ACTION_OVERRIDES` 增加 `("POST", "/claim"): "update"`。
- 同步 `DPS/src/tests/test_v2_9_1_permission_mapping.py` 的「后缀唯一性」断言（`/claim` 仅标注领取使用）。

### 3.4 OpenBase 代理

- `GET /annotations`：参数透传（无改动）。
- 新增 `POST /api/v1/dps-proxy/annotations/{annotation_id}/claim`，路径片段 `quote(safe="")`，请求体原样透传，错误保真。

### 3.5 前端

- `DpsAnnotationQuery` 增加 `reviewer?: 'me' | string`、`level?: number`。
- `DpsAnnotationRow` 增加 `reviewer_id?: string | null`。
- `claimAnnotation(id)` 新增。
- 审核收件箱（`view === 'review'`）：
  - 筛选区新增 `只看我的` 复选框（`reviewer: 'me' | undefined`）与级数下拉（全部/1~5）；
  - 队列增加「审核人」列：本人显示「我」，他人显示用户名，未领取显示「未领取」；
  - 详情面板头部新增 `领取` 按钮：`pending` 且非本人领取时可见；成功后提示并 `reloadQueue()`；
  - 已他人领取时按钮禁用并提示。

## 4. 实现清单（精确到文件/函数）

1. `DPS/src/engines/annotation_template_engine.py`：
   - `query_annotations` 增加 `reviewer_id`/`review_level` 过滤与 `reviewer_id` 选取；
   - 新增 `async def claim_annotation(self, annotation_id, reviewer, tenant_id=None) -> Dict[str, Any]`。
2. `DPS/src/rest_api/routes/routes_profiles.py`：
   - `api_list_annotations` 增加 `reviewer`/`level`，`me` 解析与 401/400；
   - 新增 `api_claim_annotation`。
3. `DPS/src/middleware/permission_middleware.py`：`ENDPOINT_ACTION_OVERRIDES` 增加 `/claim`。
4. `DPS/src/__init__.py` → `2.16.0`。
5. `OpenBase/openbase/modules/dps_proxy/__init__.py`：新增 `dps_annotation_claim`；更新 `dps_annotations_list` docstring。
6. `OpenBase/openbase/__init__.py` → `1.7.0`。
7. `openbase-ui/src/core/api/dps.ts`：类型与 `claimAnnotation`。
8. `DpsAnnotationWorkbenchView.vue`：筛选/列/领取按钮/刷新。
9. `openbase-ui/package.json` → `1.8.0`。

## 5. 测试

| 层 | 用例 | 断言 |
|---|---|---|
| DPS 引擎 | `test_annotation_claim_v2_16.py` 8 条 | reviewer 过滤；level 过滤；me 解析；claim 成功/幂等/他人已领/非 pending/不存在/缺列 |
| DPS 路由 | 同上 4 条 | 401/400/404/409 状态码与 detail |
| DPS 权限 | `test_v2_9_1_permission_mapping.py` | `/claim` 映射 update 且后缀唯一 |
| 代理 | `tests/test_dps_proxy_claim_v170.py` 3 条 | 路径映射；请求体透传；409 保真 |
| 前端 | `tests/dps-annotation-claim-v180.spec.ts` 5 条 | 只看我的参数；级数参数；claim 调用；归属文案；失败提示 |
| 构建 | `npm run build` | 成功 |

## 6. 验证命令

```powershell
cd "d:\Trae CN\myproject\Dev\DPS\src"
D:\Python\python.exe -m pytest tests/test_annotation_claim_v2_16.py tests/test_v2_9_1_permission_mapping.py -q -o addopts=""

cd "d:\Trae CN\myproject\Dev\OpenBase"
D:\Python\python.exe -m pytest tests/test_dps_proxy_claim_v170.py tests/test_dps_proxy.py -q -o addopts=""

cd "d:\Trae CN\myproject\Dev\OpenBase\openbase-ui"
node node_modules/vitest/vitest.mjs run tests/dps-annotation-claim-v180.spec.ts
npm run build
```

## 7. 文档交付

同 A7：v1.8.0 需求/矩阵/评审，`doc/design/OpenBase-A2审核人视角与领取-设计文档-v1.0.0.md`，开发/测试/部署 v1.8.0，设计总文档回填 v2.7.0（§9 A2、§12「待我审核」解除临时口径）。

## 8. 风险与决策

| 风险 | 处置 |
|---|---|
| 并发领取双写 | 条件 UPDATE ＋ 影响行数判定；冲突返回 409 |
| 前端伪造审核人 | `reviewer=me` 由服务端解析；前端不传他人 ID，代理注入身份头 |
| 存量库缺列 | 过滤退化为空页；claim 返回 409 明确文案 |
| 权限误判为 create | 端点级动作覆盖为 update，并补唯一性断言 |
| 领取后审核责任不清 | 审核时 `reviewer_id` 仍写实际操作人（既有语义），领取仅为锁定 |
| 提交夹带既有改动 | 仅 stage 本任务文件 |
