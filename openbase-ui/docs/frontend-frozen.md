# 统一前端唯一维护面与子系统前端冻结声明

> 登记时点：2026-09-10（S6 段 T1 边界收口）。上游依据：《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0》§1.1 Q-FE-1、§3.4、§4.1（S6-T1-1/S6-T1-3）；《OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0》（OB-S6-T1-FRONTEND-FREEZE-v1.0.0）。

## 1. 统一前端唯一维护面

**统一前端唯一维护面 = `OpenBase/openbase-ui`**（本目录，`D:\Trae CN\myproject\Dev\OpenBase\openbase-ui`，已入库跟踪）。

- 前端需求变更、缺陷修复、依赖升级、构建与发布形态调整，**一律且仅在本目录内进行**；
- 发布形态：`dist-vX.Y.Z` 版本目录 + nginx 同域 `/ui/` 静态 + `/api/` 反代（SSE `proxy_buffering off`），见 `../nginx.conf.example`；
- 与 JT 线以**提交号**桥接，前端产品版本线与 OpenBase 仓版本线解耦。

## 2. 子系统前端冻结声明

各子系统自带 `frontend/`（DPS / OpenLLM / OpenMemory / OpenRAG 的独立前端）自 2026-09-10 起**冻结**：

> **保留目录不删除**、**不再构建/发布**、**后端不再挂载其产物**。

- 历史代码保留以供追溯与回滚（可回滚性见登记文档 §3 各条「回滚性」）；
- 统一前端已承接原四个子系统前端的展示职责，各子系统后端仅提供 API；
- 各子系统 `frontend/` 改动一律**不属联调提交面**（归 B/C 类），不得纳入任何联调提交批（见《OpenBase-多系统联调-跨仓提交放行清单》§0 通用红线第 5 条「统一前端口径」）。

## 3. 子系统 3 处待改造指引（S6 只登记，改造归属各子系统仓）

| # | 归属仓 | 证据行号（2026-09-10 复核） | 改造指引 |
|---|--------|---------------------------|---------|
| 1 | OpenMemory | `deploy/nginx/conf.d/openmemory.conf:90`（`root /app/frontend/dist;`）、`:93-101`（SPA 兜底 `try_files … /index.html`） | 下线 SPA 承载：移除上述两处；保留 `/api/` 反代 `:106-124`（`proxy_buffering off` 保 SSE）与 `/health` `:129-133`；`/` 改 301 → 统一前端 `/ui/` |
| 2 | OpenLLM | `docker-compose.yml:141-172`（`frontend` 服务）、`docker-compose.prod.yml:19`（`./frontend/dist:/usr/share/nginx/html:ro`） | 移除 `frontend` 服务与 `frontend/dist` 挂载；`frontend/Dockerfile`、`frontend/Dockerfile.dev`、`frontend/nginx.conf` 保留不删但不再被编排引用 |
| 3 | DPS + OpenRAG | DPS `.github/workflows/ci.yml`：前端 Lint `L68-79`、Coverage `L114-129`、Build `L164-195`、E2E `L213-230`；OpenRAG `.github/workflows/frontend-ci.yml`（共 65 行：`paths` L6/L9、quality L12-41、e2e L43-65） | 前端 job/step 收敛为「冻结校验 / 跳过」；后端 CI 与后端门禁不变 |

> **执行顺序约束**：**先发布统一前端（`dist-v1.3.0` + nginx `/ui/` 可用）→ 再在下游子系统仓收敛前端承载**；否则前端面将不可访问。
>
> **状态口径**：上述 3 处改造在 S6 内仅完成**口径闭环（登记完成）**；**物理闭环（各子系统仓实际改造）为 PENDING，交 S7 按 Q-S6-D7 复核**。

## 4. 相关落点

- 口径登记文档：`doc/planning/OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md`（S6-T1-1）；
- 后端不挂载静态断言：`tests/test_s6_t1_frontend_boundary.py`（S6-T1-2，防漂移固化）；
- 清单引用位：清点总清单 §5.6、跨仓提交放行清单 §0（S6-T1-4）。
