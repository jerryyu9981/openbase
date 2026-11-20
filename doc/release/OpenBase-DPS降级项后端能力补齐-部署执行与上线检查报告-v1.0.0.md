# OpenBase-DPS 降级项后端能力补齐 - 部署执行与上线检查报告（v1.0.0）

| 项 | 内容 |
|---|---|
| 项目 | OpenBase（开放底座）后端 `openbase` ＋ 前端 `openbase-ui` |
| 主题 | DPS 降级项 A6/A9/A10/A11/A12/A14 后端能力与前端接入 |
| 文档 | 部署执行与上线检查报告（Step 5 产出） |
| 文档版本 | **v1.0.0** |
| 状态 | **[Review]**（待人工批准） |
| 日期 | 2026-11-20 |
| 发布版本 | 后端 `1.5.0`／前端 `1.5.0` |
| 执行人 | DO-OpenBase-Dev |
| 上游依据 | 《OpenBase-DPS降级项后端能力补齐-测试报告-v1.0.0》；《OpenBase-DevLogReport-v1.5.0》 |
| 存放 | `doc/release/` |

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|---|---|---|---|
| v1.0.0 | 2026-11-20 | DO-OpenBase-Dev | 首版：构建与制品核验、上线检查（6 项能力）、回滚与降级口径、运维观察项 |

---

## 1. 部署对象与制品

| 项 | 值 |
|---|---|
| 后端制品 | Python 源码；版本 `openbase.__version__ = 1.5.0` |
| 前端制品 | `openbase-ui/dist/`（`vue-tsc --noEmit && vite build`） |
| 后端数据变更 | 新增表 `dps_annotation_candidate`，随 `Base.metadata.create_all` 幂等创建；无存量迁移 |
| 依赖变更 | 无新增运行依赖 |
| 配置变更 | 无新增环境变量 |

## 2. 构建与制品核验

| 项 | 命令 | 结果 |
|---|---|---|
| 后端定向用例 | `python -m pytest tests/test_dps_backend_capabilities_v150.py` | **22 passed**（`doc/test/evidence/v1.5.0/openbase-backend-targeted.txt`） |
| 后端静态检查 | `python -m ruff check`（本任务改动文件） | **All checks passed**（`openbase-static.txt`） |
| 前端类型检查 | `vue-tsc --noEmit`（随构建执行） | **通过** |
| 前端生产构建 | `npm run build` | **成功，5m 26s**，3159 modules transformed（`openbase-ui-build.txt`） |
| 前端相关回归 | vitest 10 个 spec | 见测试报告 §3（`openbase-vitest-v150.txt`） |

## 3. 上线检查（Dev）

| # | 检查项 | 通过标准 | 结果 |
|:-:|---|---|:--:|
| 1 | `/api/v1/dps-proxy/portraits?keyword=&external_id=` | 参数完整转发；上游包络与状态码保真 | 通过 |
| 2 | `/api/v1/dps-proxy/tags` | 转发关键字/分类/分页，返回 `items/total/page/page_size` | 通过 |
| 3 | `/api/v1/dps-proxy/audit` | 转发实体与 `order`；回显实体键 | 通过 |
| 4 | `/api/v1/dps-proxy/audit/logs?resource_id=` | 新参数生效，旧参数不变 | 通过 |
| 5 | `/api/v1/dps-proxy/annotations/export` | UTF-8 BOM、RFC4180 转义、注入前缀、`X-Export-Truncated`、文件名规范 | 通过 |
| 6 | `/api/v1/dps-proxy/portraits/export` | 静态路由先于 `/portraits/{person_id}`；过滤与列表一致 | 通过 |
| 7 | 候选三端点 | 生成落库、按 `batch_id`/`latest` 重查、同租户幂等、跨租户不可见 | 通过 |
| 8 | 前端 6 处接入 | 刷新恢复候选；服务端检索；导出走后端 CSV；404 回退可用 | 通过 |
| 9 | 既有代理回归 | 52 例既有 `dps_proxy` 用例全通过 | 通过 |

## 4. 回滚方案

| 项 | 内容 |
|---|---|
| 触发条件 | 导出异常（编码/截断）、候选落库失败、代理 5xx 比例异常或前端白屏 |
| 回滚方式 | 回退至上一发布版本 `1.4.12`（后端与前端同版本回退）；重启服务并重新发布 `dist` |
| 数据回滚 | 无需删除表；`dps_annotation_candidate` 为新增表，回退后不再写入，保留数据不影响旧版本 |
| 降级兼容 | 上游 DPS 仍为 2.13.0 时：`/tags`、`/audit`、导出上游路径返回 404 → 前端按「仅 404 回退」走既有本地降级；403/5xx 呈现受控错误态 |
| 回滚验证 | 登录 + 画像列表 + 标注作业台 + 导出 + 版本字面量 `1.4.12` |

## 5. 运维观察项

| 编号 | 观察项 | 处置 |
|---|---|---|
| OPS-150-01 | 导出为同步流式，超大结果集（接近 10000 行）会占用连接较久 | 观察导出耗时与连接数；必要时下调上限或转异步任务 |
| OPS-150-02 | 候选表按 `(tenant_id, upstream_annotation_id)` 唯一，历史批次累积 | 评估按 `created_at` 定期归档策略 |
| OPS-150-03 | 前端回退仅针对 HTTP 404；5xx 不回退 | 联调期确认 DPS 未就绪时返回 404 而非 503 |

## 6. 结论

后端与前端 1.5.0 构建通过，上线检查 9 项全部通过，具备明确回滚与降级路径；本版本可作为 Dev 基线发布。
