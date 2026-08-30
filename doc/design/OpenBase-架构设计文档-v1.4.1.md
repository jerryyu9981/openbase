# OpenBase 架构设计文档 - v1.4.1

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.1 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase |
| 创建日期 | 2026-08-29 |
| 存放 | doc/design/ |

---

## 1. 设计总览

| 需求 | 设计要点 | 涉及文件 |
|------|---------|---------|
| R-367/368 服务 Key 认证 | ApiKeyStore（签发/吊销/scope）+ require_api_key 依赖（网关 /proxy 双通道：JWT 优先 + Bearer Key 回退） | 新建 `openbase/modules/auth/api_keys.py`；修改 `openbase/core/deps/auth.py` |
| R-369 四维身份头 | get_identity_context 依赖（解析 X-User-Id/X-Team-Id/X-Agent-Id/X-Tenant-Id） | 修改 `openbase/core/deps/auth.py` |
| R-370 审计上下文 | 审计中间件注入 identity 上下文（tenant_id/user_id） | 修改 `openbase/modules/audit/__init__.py` |
| R-371 openbase-cli | 新建 `openbase/cli/`（click 命令：create-project/create-module/create-crud + Jinja 模板） | 新建 cli 包 |
| R-372 BaseCRUDRouter | 新建 `openbase/core/crud.py`（通用 CRUD 路由工厂，Pydantic 模式驱动） | 新建 core/crud.py |
| R-373 storage S3 | storage 模块新增 S3 后端（可选依赖 boto3，配置切换） | 修改 `openbase/modules/storage/__init__.py` |

## 2. 关键设计

### 2.1 服务 Key 认证（R-367/368）

```text
请求 /api/v1/proxy/... 
  ├─ Authorization: Bearer <user-jwt> → get_current_user（既有通道）
  └─ X-API-Key / Authorization: Bearer <service-key> → require_api_key
        → ApiKeyStore 校验（哈希比对 + 未吊销）→ scope 校验 → 配额
```

- ApiKeyStore：内存存储 + 哈希保存（`sha256(key)`），API：create/list/revoke/verify
- scope 模型：`{"system": ["openllm"], "tenants": ["*"]}`（平台级/租户级）
- 错误码：`AUTH_API_KEY_INVALID`（401）/`PERM_API_KEY_SCOPE`（403）

### 2.2 四维身份头（R-369）

```text
IdentityContext = { user_id, tenant_id, team_id, agent_id }
get_identity_context(request) → 从 4 头解析（X-User-Id 等），X-Tenant-Id 已有逻辑复用
```

### 2.3 BaseCRUDRouter（R-372）

```python
router = BaseCRUDRouter(
    prefix="/api/v1/dict",
    service=DictService,          # 需提供 list/get/create/update/delete
    create_schema=DictCreate,
    update_schema=DictUpdate,
    out_schema=DictOut,
)
# 自动生成 5 个端点：GET list / GET {id} / POST / PUT {id} / DELETE {id}
```

### 2.4 storage S3（R-373）

- 后端选择：`storage.backend = local | s3`（config 键）
- S3Backend：boto3 可选依赖，`import` 失败时回退本地并告警
- 接口对齐：save/load/delete（与 LocalBackend 一致）

## 3. 设计决策（ADR）

| ADR | 决策 | 理由 |
|-----|------|------|
| ADR-141-01 | 服务 Key 认证走 X-API-Key 头（非复用 JWT 通道） | 机器凭据与用户凭据分离，避免语义混淆 |
| ADR-141-02 | CLI 用 click + Jinja 模板 | 轻量、可测试，模板与模块规范对齐 |
| ADR-141-03 | BaseCRUDRouter 基于 Service 层适配（非直接 ORM） | 保持分层架构约束（AGENTS.md） |
| ADR-141-04 | S3 适配可选依赖（boto3 懒加载） | 避免强制依赖，本地环境零配置 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-29 | AD-OpenBase | 初始创建：A 类 7 项设计 + ADR-141-01~04 |