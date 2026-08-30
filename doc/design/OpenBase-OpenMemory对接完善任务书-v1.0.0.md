# OpenBase-OpenMemory对接完善任务书-v1.0.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-v1.0.0 |
| 版本 | v1.0.0 |
| 状态 | [Draft] |
| 日期 | 2026-08-30 |
| 作者 | AD-OpenBase-Dev |
| 版本主题 | OpenMemory 侧对接完善：多模态图像真实落盘与检索、衰减配置持久化、会话与衰减联动 |
| 适用范围 | OpenMemory 项目（D:\Trae CN\myproject\Dev\OpenMemory），由独立会话据此实施 |

> 本任务书供另一个会话专据此完善 OpenMemory。所有修改项均含现状、目标、涉及文件、实现要点、验收标准与验证方法，可直接照单执行。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0.0 | 2026-08-30 | AD-OpenBase-Dev | 初始版本：梳理 OpenBase 最终规范对接下 OpenMemory 仍需完善的 M1~M5 项 |

---

## 1. 背景与目标

OpenBase（v1.4.2）已按《OpenMemory-对接使用指南 v6.8.0》完成主要对接：双层认证（X-API-Key + JWT）、记忆核心 API（remember/recall/forget/improve/detail）、会话管理、衰减配置、召回路径追踪、监控、健康检查、多模态与语音端点代理，OpenBase 侧 memory-proxy 全链路真实可用。

对照指南逐项核验后，OpenMemory 侧仍有 3 处占位实现（图像上传未真实落盘、图像搜索恒返回空、衰减配置未持久化）和 2 项建议优化。本任务书定义这些修改的精确方案，目标是把 OpenMemory 打造成与 OpenBase 规范完全对齐的生产可用服务。

## 2. 对接现状总览

| 类别 | 状态 | 说明 |
|------|:---:|------|
| 双层认证（API Key + JWT HS256） | ✅ 已完成 | 常量时间比较 + 白名单 /health；共享密钥 test-jwt-secret-for-v680 |
| 租户解析（X-Tenant-ID > JWT > default） | ✅ 已完成 | 指南 4.6 对齐 |
| 核心记忆 API（remember/recall/forget/improve/detail） | ✅ 已完成 | 指南 5.3 对齐 |
| 会话管理（sessions 三端点） | ✅ 已完成 | 指南 5.6 对齐 |
| 衰减配置（decay/config GET/PUT） | ⚠️ 待完善 | 内存实现，重启丢失（M3） |
| 召回路径追踪（recall/traces/{id}） | ✅ 已完成 | WaypointTracer 装配 + 缓存命中 end_trace 修复 |
| 监控（monitor?range=） | ✅ 已完成 | 指南 5.9 对齐 |
| 分层健康检查（health/readiness/liveness） | ✅ 已完成 | 指南 5.2 对齐 |
| 语音 API（audio/transcribe + remember-with-audio） | ✅ 已完成 | validate_audio_file 修复 + Whisper 预热 + HF 镜像 |
| 多模态图像上传（memories/image） | ⚠️ 待完善 | 未真实落盘（M1） |
| 图像搜索（memories/image/search） | ⚠️ 待完善 | 恒返回空（M2） |
| 图像嵌入（multimodal/image-embed） | ✅ 已完成 | CLIP 预热 + fallback 降级 |
| 软删一致（forget 同步 Qdrant + recall 过滤） | ✅ 已完成 | 走查修复：search→detail 链路闭环 |
| RBAC user 角色多模态/语音权限 | ✅ 已完成 | permission.py 补充 POST 权限 |
| 会话存储 TTL | 🔧 建议复核 | Redis 默认 7200s（M4） |
| 衰减引擎与配置联动 | 🔧 建议复核 | PUT 后引擎实时生效（M5） |

## 3. 待完善项详细方案

### M1 图像记忆上传真实落盘（memories/image）

**现状**：`src/openmemory/api/controllers.py` 的 `upload_image_memory`（约 563 行）校验格式/大小后仅生成 UUID 返回假 `storage_path`，注释 "In production, would store via MultiModalEngine"，文件未写入任何存储。

**目标**：调用现成 `MultiModalEngine.process_image` 完成校验 + 嵌入 + 真实落盘（LocalImageStorage），返回真实 `storage_path` 与文件元数据。

**涉及文件**：
- `src/openmemory/api/controllers.py`（修改 upload_image_memory）
- `src/openmemory/memory/multimodal_engine.py`（已具备能力，无需改）

**实现要点**：
1. 从 `request.app.state` 取 `clip_embedding_service`（`CLIPEmbeddingService` 已由启动脚本预热挂载）；若取到则 `MultiModalEngine(embedding_model=clip_service)`，否则默认 `CLIPImageEmbedding()`。
2. 调用 `await engine.process_image(content, filename, tenant_id, metadata={"source": "image_upload"})`，返回 `ImageMemory`。
3. 响应填充 `ImageMemoryResponse(id=image.id, tenant_id=image.tenant_id, storage_path=image.storage_path, format=image.format, size_bytes=image.size_bytes, created_at=image.created_at)`。
4. 保留既有 400/413 校验分支（MultiModalEngine._validate_image 亦含同样校验，异常映射：ImageTooLargeError → 413 E200004，UnsupportedFormatError → 400 E200003）。

**验收标准**：
- 上传 PNG/JPG 返回 200，`storage_path` 指向 `./storage/images/{tenant}/images/{id}.{ext}` 且文件真实存在（Test-Path）。
- 超 10MB 返回 413；非 jpg/jpeg/png 返回 400。
- 重复上传生成不同 id 与文件。

**验证方法**：`python -m pytest tests/test_multimodal_engine.py`；再经 OpenBase proxy `POST /api/v1/memory-proxy/memories/image` 上传真实图片后检查落盘文件。

---

### M2 图像文本搜索真实检索（memories/image/search）

**现状**：`controllers.py` 的 `search_image_memory`（约 589 行）恒返回 `ImageSearchResponse(results=[])`，注释 "In production, would use MultiModalEngine.search_by_text"；`MultiModalEngine.search_by_text` 同样返回空列表（未接向量检索）。

**目标**：用 CLIP 文本嵌入在已存图像记忆上做向量检索，返回真实 `results`。

**设计约束**：OpenMemory 未给图像单独建向量集合。推荐方案：**在现有 Qdrant `openmemory` 集合内以 payload 标记检索**，或为图像建独立 collection。以下给出低侵入方案 A（推荐）。

**方案 A：复用 Qdrant openmemory 集合（payload 区分）**

1. `process_image` 落盘后，把图像嵌入与元数据写入 Qdrant：
   - 点 ID：`img-{memory_id}`（与文本记忆 ID 区分前缀，避免冲突）。
   - payload：`{"kind": "image", "tenant_id": ..., "image_id": ..., "storage_path": ..., "format": ..., "is_active": true, "content": f"[image:{filename}]"}` + 向量为 CLIP 图像嵌入。
   - 复用 `RelationalStore` 侧 `memory_metadata` 表记录图像元数据（`memory_type="image"`，`metadata_json` 存 storage_path/format/size），保证与文本记忆同一套生命周期（软删/审计）。
2. `MultiModalEngine.search_by_text` 实现：
   - `text_embedding = await self._embedding_model.encode_text(query)`。
   - 用 `QdrantVectorStore.search(query_vector=text_embedding, top_k=top_k, filters={"kind": "image", "is_active": True})`。
   - 将命中点转换为 `ImageMemory`（从 payload 还原 storage_path/format/size + 从 PG 补 created_at/metadata）。
3. `controllers.py` `search_image_memory` 调用 `engine.search_by_text(query, tenant_id, top_k)` 并组装响应；空结果返回空数组（200）。

**方案 B（备选）：独立 Qdrant collection `openmemory_images`**
- 初始化时 `ensure_collection` 维度与 CLIP 对齐（512，与文本集合一致）；检索逻辑同方案 A 但过滤去掉 `kind`，查询目标换为 `openmemory_images`。适用场景：图像量级大、需独立容量管理时再选。

**验收标准**：
- 上传 2 张不同图片后，用描述性文本（如 "cat" / "mountain"）搜索，返回含对应 `storage_path` 的结果，score 排序合理。
- 上传后软删（forget）该图像，搜索不再返回（is_active 过滤生效）。
- 无匹配时返回 200 空数组，不报错。

**验证方法**：写临时脚本经 OpenBase proxy 上传两张图 → `POST /api/v1/memory-proxy/memories/image/search` 验证命中；再 forget 后复搜确认过滤。

---

### M3 衰减配置持久化（decay/config）

**现状**：`controllers.py` 的 `get_decay_config`/`update_decay_config` 读写 `request.app.state.decay_config`（内存 dict），注释 "In production, this would query/persist to database"。重启丢失、不按租户隔离（虽然读取 X-Tenant-ID 但未落库）。

**目标**：按租户（X-Tenant-ID）持久化到 PostgreSQL，重启可恢复，支持多租户隔离。

**涉及文件**：
- `src/openmemory/storage/relational_store.py`（新增表 + CRUD 方法）
- `src/openmemory/api/controllers.py`（get/put 改为走 RelationalStore）
- `src/openmemory/api/server.py` 或 `scripts/start_openmemory.py`（启动时预载到 app.state 供衰减引擎）

**实现要点**：

1. `relational_store.py` 新增表（幂等建表，沿用现有 `Base.metadata.create_all` 机制）：

```python
class DecayConfigTable(Base):
    """Per-tenant decay configuration."""
    __tablename__ = "decay_config"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="adaptive")
    time_decay_factor: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)
    half_life_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    emotion_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    frequency_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

2. `RelationalStore` 新增方法（参数化 SQLAlchemy select/update，禁止字符串拼接）：
   - `async def get_decay_config(self, tenant_id: str) -> dict | None`
   - `async def upsert_decay_config(self, tenant_id: str, config: dict) -> None`（不存在则 insert，存在则 update）
3. `controllers.py`：
   - `get_decay_config`：`store = getattr(request.app.state, "relational_store", None)`（若未挂载则从 `memory_service._dual_memory.persistent_store._metadata_store` 取）；先查库，未命中返回默认值（不落库，保持只读默认语义）。
   - `update_decay_config`：校验参数范围（time_decay_factor 0~1、half_life_days ≥1、emotion/frequency ≥0）后 upsert；更新 `app.state.decay_config`（供引擎即时使用）。
4. `scripts/start_openmemory.py`：启动时对 default 租户预载一次 `app.state.decay_config`（缺失则写默认值），保证引擎与 API 读同一实例。

**验收标准**：
- PUT 修改 `time_decay_factor=0.80` 后 GET 返回新值。
- 重启 OpenMemory 后 GET 仍返回 0.80（持久化生效）。
- 不同 X-Tenant-ID（如 default / tenant-a）互不覆盖。

**验证方法**：经 OpenBase proxy `GET/PUT /api/v1/memory-proxy/decay/config` 修改 → 重启 8020 → 复 GET 核对；PG 查 `decay_config` 表确认两租户行。

---

### M4 会话 TTL 复核（建议项）

**现状**：`SessionMemory` 默认 `default_ttl=7200`（2 小时）写入 Redis，`cache_store.add_session_memory(memory, ttl=...)`。

**建议**：确认对接业务是否需要更长会话。若需长期会话，将 TTL 配置化（`MemoryConfig.session_ttl` 或 env `OPENMEMORY_MEMORY__SESSION_TTL`）并在启动装配时传入，避免硬编码。

**验收标准**：配置项存在且生效；文档注明默认值与修改入口。

---

### M5 衰减引擎与配置实时联动（建议项）

**现状**：`decay/config` 可配置，但 `DecayEngine`（`/api/v1/recall?strategy=decay`）是否读取同一 `app.state.decay_config` 需复核。

**建议**：确认 `DecayEngine` 构造时注入的配置来源与 API 端一致；M3 落库后，在 `update_decay_config` 成功后同步刷新引擎配置（或引擎每次读取 app.state）。若引擎已读取同一实例，则本项仅需在任务书验证中覆盖一条用例：PUT 改参数 → `recall?strategy=decay` 结果权重随之变化。

**验收标准**：PUT 修改衰减参数后，decay 策略召回的结果排序/权重按新参数计算。

---

## 4. 实施顺序与依赖

| 顺序 | 项 | 依赖 | 说明 |
|:---:|-----|------|------|
| 1 | M1 图像落盘 | 无 | 独立可先行，形成图像数据闭环 |
| 2 | M2 图像检索 | M1 | 依赖已落盘图像 + 嵌入入库 |
| 3 | M3 衰减持久化 | 无 | 独立；涉及建表，需重启生效 |
| 4 | M4 会话 TTL | 无 | 配置化小改 |
| 5 | M5 衰减联动 | M3 | 验证项为主，代码改动视复核结果 |

建议一个会话内按 1→2→3 完成核心项，4/5 视资源安排；每项完成后跑对应测试与真实验证再进入下一项。

## 5. 全量回归验证清单

修改完成后，在 OpenMemory 项目内执行：

| 命令 | 预期 |
|------|------|
| `python -m ruff check src` | All checks passed（0 错误） |
| `python -m pytest tests/test_multimodal_engine.py -q` | 全部通过（沙箱写入 `./storage/images` 受限时可改用真实环境验证替代） |
| `python -m pytest tests/unit/test_rbac.py -q` | 22 passed（权限矩阵无回归） |
| `python -m pytest tests/test_v680_quality.py -q` | 通过（除沙箱写盘类用例） |

联调回归（OpenBase 8000 + OpenMemory 8020）：

| 场景 | 命令/操作 | 预期 |
|------|-----------|------|
| 图像上传 | OpenBase proxy `POST /api/v1/memory-proxy/memories/image` | 200 + 真实 storage_path |
| 图像搜索 | proxy `POST /api/v1/memory-proxy/memories/image/search` | 200 + 命中结果 |
| 衰减持久化 | proxy GET/PUT decay/config → 重启 → GET | 值保持 |
| 语音转写 | proxy `POST /api/v1/memory-proxy/audio/transcribe`（真实 WAV） | 200，duration>0 |
| 记忆搜索→详情 | proxy recall → GET memories/{id} | 全部 200（软删过滤生效） |
| 会话/监控/健康 | proxy sessions / monitor / health | 200 |

## 6. 风险与注意事项

- **Qdrant 点 ID 冲突**：M2 方案 A 使用 `img-{id}` 前缀隔离，避免与文本记忆点 ID 冲突；若未来统一命名需迁移脚本。
- **模型下载**：CLIP/Whisper 模型下载依赖 `HF_ENDPOINT=https://hf-mirror.com` + `HF_HUB_DISABLE_XET=1`（已固化在 `start_openmemory.py`）；新环境首次启动需网络可达。
- **torch 运行库**：System32 旧版 VC++ 运行库（14.00）会导致 c10.dll WinError 1114；已将 WinSxS 14.50 版复制至 Python 根目录与 torch/lib，新机器部署需复现该修复（详见 OpenBase 测试报告附录 C.5）。
- **软删一致性**：M2 图像软删必须同步 Qdrant payload `is_active=False` 与 PG 标记，遵循已修复的文本记忆软删模式（`PersistentMemory.delete` soft 分支 + retrieval 过滤）。
- **沙箱写盘限制**：自动化测试在沙箱内写 `./storage/images` 会被拦截（PermissionError），属环境限制非代码问题；验证时用真实环境或调整沙箱规则。
- **文档单一事实源**：本任务书为 OpenMemory 侧对接完善的唯一执行依据；修改完成后在 OpenMemory 项目内同步 DevLogReport 修订历史并回填本任务书状态列（待补充状态追踪表：M1/M2/M3/M4/M5 各自 PENDING/IN_PROGRESS/DONE/VERIFIED）。
