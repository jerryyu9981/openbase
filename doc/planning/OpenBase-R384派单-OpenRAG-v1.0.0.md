# OpenBase-R384派单-OpenRAG-v1.0.0

| 项 | 内容 |
|------|------|
| 文档编号 | OB-DISPATCH-R384-OPENRAG-v1.0.0 |
| 文档版本 | v1.0.0 |
| 状态 | [Approved]（待分发执行） |
| 出具方 | OpenBase 项目（PM-OpenBase-Dev / AA-OpenBase-Dev） |
| 接收方 | **OpenRAG 仓对话**（本仓独立评审、独立提交、独立发布） |
| 出具日期 | 2026-09-16 |
| 版本归属 | OpenBase v1.4.7（承接型小版本）；OpenRAG 侧为跨仓改动 |
| 上游依据 | 《OpenBase-D6四仓request_id日志接线改动说明-v1.0.0》§3.4；《OpenBase-R384改动包-v1.0.0》§6；《OpenBase-R384四仓施工派单-v1.0.0》 |
| 性质 | **单仓施工指令（自包含）**——本文件无需依赖其他 OpenBase 文档即可执行 |
| 特殊说明 | 本仓是四仓中**改动量最大**的一仓（需启用一个从未注册的中间件）；但**降险结论**已取得，见 §2 |

---

## 1. 任务与目标

| 项 | 内容 |
|----|------|
| 需求 | **R-384 四仓日志接入**（OpenRAG 切片）：请求日志携带 `request_id`（与网关出站头 `X-Request-Id` 一致），并输出 **JSON Lines**，使 OpenRAG 日志可在 OpenBase 日志中心按 `module=rag` 检索、按 `request_id` 从网关串联追踪 |
| 关联 | OpenBase **BL-147-02**（`request_id` 接线）、**BL-147-03**（JSONL 结构化） |
| 本仓底数 | 全仓 `X-Request-Id` **零匹配**（相关性 ID 走 `X-Correlation-ID`）；`observability/logging.py:390` 的 `LoggingMiddleware` **定义但从未注册**（`main.py:96-177` 只注册 CORS / TraceContext / RoleGate / BlockSubjectGate / IdentityGate / APIKey / Prometheus） |
| 验收 | ① 经网关调用 → OpenRAG 日志 `request_id` 与网关一致；② 直连（非受信）携带伪造头 → 生成新的 `req-{12hex}`；③ 日志为合法 JSON 且 `status_code` 为**数字**；④ 回归全通过 |

## 2. 前置核实与降险结论（已取得，施工前请复核）

| # | 项 | 结论 / 要求 |
|:-:|----|------------|
| 1 | **两套日志栈是否真的并存**（D-6 R-3） | **已实测降险**：`observability/logging.py:410` 的 `self.logger = get_logger("openrag.api")` 与 `config/logging.py:71` 的 `get_logger` **同源**（均取 structlog 门面）；因此其 `logger.info("request_started", method=..., ...)` 的 **kwargs 风格成立，注册中间件不会报错**；两处**并非两套栈**。→ 本项降级为"**确认 contextvar 单一来源**"：核对 `set_correlation_id` 与（新增的）`set_request_id` 是否落在同一 contextvar 机制上 |
| 2 | **实际启动路径与日志配置生效点** | 实测：`python -m uvicorn openrag.main:app --app-dir src`；`main.py:51` 在 **lifespan 内**调用 `setup_logging(level=settings.log_level, json_format=settings.is_production)` → 落点有效（本指令按此给出） |
| 3 | **受信来源判定实现位置** | 本仓既有代理来源校验（对标 OpenBase `TRUSTED_PROXY_SOURCES`）需指明其函数/常量位置，供 §4.3 复用；若本仓无实现，需按协议头规范新增最小判定并单测 |

## 3. 契约（强制）

| 项 | 约定 |
|----|------|
| 头名 | `X-Request-Id`；受信来源**透传复用**，非受信来源**忽略并本地重新生成** `req-{12hex}` |
| 日志字段 | 统一 `request_id`（**JSON key 必须为 `request_id`**）；无上下文一律 `"-"` |
| 输出流 | 维持现状（**stdout**），不得改为仅落自有文件 |
| 禁止 | 不记录令牌/密码/密钥/完整请求体；保持 `log_request_body=False` / `log_response_body=False` 默认 |
| 采集目录 | `logs/openrag/`（**目录名不得改**，OpenBase 按目录名映射 `module=rag`） |

**JSONL 字段契约**（OpenBase 适配器实际读取键，超集允许）：

| 字段 | 必需 | 类型 | 说明 |
|------|:---:|------|------|
| `timestamp` 或 `ts` | 必需 | ISO 8601 字符串 | 本仓 structlog `TimeStamper(fmt="iso")` 输出键为 **`timestamp`**——适配器已接受该别名；无时区按 UTC；**无法解析的行整行丢弃** |
| `request_id` | 必需 | 字符串 | 与网关一致（**键名必须精确为 `request_id`**） |
| `method` / `path` | 必需 | 字符串 | 中间件已在 `request_started` 中输出 |
| `status_code` | 必需 | **JSON 数字** | 中间件已在 `request_completed` 中输出（须为 int） |
| `duration_ms` | 建议 | 数字 | 中间件已有（与 `status_code` 同条记录） |
| `level` | 建议 | 字符串 | structlog 自动加 |
| `module` | — | — | **无需输出**（由采集目录名映射） |

## 4. 改动清单

### 4.1 新增 `request_id` 上下文与生成函数（`src/openrag/observability/logging.py`）

在本仓既有 correlation-id 工具旁并列新增（**沿用本仓 contextvar/structlog 机制**，使字段自动合入 JSON 输出）：

```python
import secrets


def generate_request_id() -> str:
    """生成 req-{12hex}（对齐 OpenBase 协议头规范 v1.0 §1）。"""
    return f"req-{secrets.token_hex(6)}"


def set_request_id(request_id: str) -> None:
    """写入 request_id。

    注意：本仓 JSON 输出由 structlog 组装（`config/logging.py::setup_logging` 含
    `structlog.contextvars.merge_contextvars`），因此**优先**用 structlog contextvars 绑定，
    以保证键名精确为 `request_id` 并出现在每条日志中：
        structlog.contextvars.bind_contextvars(request_id=request_id)
    若本仓既有 correlation-id 采用自建 ContextVar，请保持同一机制并确保 JSON 键名为 request_id。
    """
    structlog.contextvars.bind_contextvars(request_id=request_id)
```

### 4.2 注册日志中间件（`src/openrag/main.py`，**Prometheus 之后**）

按本仓既有 `try/except ImportError` 风格追加：

```python
    # R-384（BL-147-02）：请求日志中间件（X-Request-Id 贯穿），置于 Prometheus 之后
    try:
        from openrag.observability.logging import LoggingMiddleware

        app.add_middleware(LoggingMiddleware, service_name="openrag")
    except ImportError:
        logger.warning("LoggingMiddleware 未安装，跳过")
```

> `add_middleware` 后注册者位于外层（本仓既有注释即如此说明），置于此处可覆盖全部请求。

### 4.3 补 `X-Request-Id` 受信透传（`src/openrag/observability/logging.py`，`LoggingMiddleware.__call__`）

在既有 `X-Correlation-ID` 处理之后**并列新增**（该段实测位于 `:412-428`）：

```python
        # R-384（BL-147-02）：X-Request-Id 受信透传 / 非受信忽略重生成
        rid = request.headers.get("X-Request-Id")
        if rid and _is_trusted_source(request):
            set_request_id(rid)
        elif rid:
            set_request_id(generate_request_id())
        else:
            set_request_id(generate_request_id())
```

> `_is_trusted_source` **复用本仓既有代理来源判定实现**（见前置核实③）；请勿新造第二套判定口径。`set_request_id` / `generate_request_id` 见 §4.1。
>
> 说明：无头（内部直连未带头）时也生成本地 `req-{12hex}`，保证每条请求日志都有 `request_id`（便于串联排查）；若本仓希望无头时留空，须改为输出 `"-"` 并同步单测。

### 4.4 JSONL 输出（BL-147-03）

`main.py:51` 现为 `setup_logging(level=settings.log_level, json_format=settings.is_production)`——**开发态为彩色控制台输出（非 JSON）**。建议：

```python
    setup_logging(
        level=settings.log_level,
        json_format=settings.is_production or getattr(settings, "log_json", False),
    )
```

并新增配置项 `log_json`（环境变量 `OPENRAG_LOG_JSON`），用于采集环境显式开启 JSON **而不与 `is_production` 语义耦合**；或直接由编排器/部署侧置生产态。

> 本仓 JSON 输出的时间键为 `timestamp`（`TimeStamper(fmt="iso")`），OpenBase 适配器已接受。

## 5. 新增单测 `tests/unit/test_r384_request_id.py`

```python
# -*- coding: utf-8 -*-
"""R-384/BL-147-02：X-Request-Id 受信透传 / 非受信忽略重生成 两分支。"""
from __future__ import annotations

import re

from openrag.observability.logging import generate_request_id

_REQ_ID_RE = re.compile(r"^req-[0-9a-f]{12}$")


def test_generate_request_id_shape() -> None:
    """生成形态：req-{12hex}（12 hex = 48bit 熵）。"""
    assert _REQ_ID_RE.match(generate_request_id())


# 说明：受信透传 / 非受信重生成 两分支需在中间件层断言，建议参照本仓既有范式
# tests/unit/test_s3_t7_audit_identity.py 的 request_id 用例组织：
#   - 受信来源 + X-Request-Id: req-abc123456789 → 日志/上下文中 request_id == 原值
#   - 非受信来源 + 伪造 X-Request-Id        → 生成新的 req-{12hex}（不等于原值）
#   - 无头                                  → 生成新的 req-{12hex}
```

## 6. 校验与回归（本仓执行）

```powershell
cd 'D:\Trae CN\myproject\Dev\OpenRAG'

python -m pytest tests/unit/test_r384_request_id.py -p no:cacheprovider
python run_tests.py                                       # 仓内聚合入口（含静态扫描门禁）
python -m ruff check src scripts tests/unit
python scripts/scan_no_edgerouter_assembly.py
python scripts/scan_no_identity_header_bypass.py
python scripts/scan_tenant_scope.py
python scripts/scan_auto_purge.py
python scripts/k07_endpoint_matrix.py
python scripts/smoke_l3_2.py
```

**端到端验证**：经 OpenBase `rag-proxy` 调用 → OpenRAG 日志 `request_id` 与网关日志一致；直连携带伪造头 → 生成新的 `req-{12hex}`。

## 7. 提交与回执

| 项 | 要求 |
|----|------|
| 分支 | 本仓当前分支（实测 `release/v1.10.0`）或本仓发布分支 |
| 提交信息 | `feat(logging): R-384/BL-147-02 request_id 日志接线 + JSONL 结构化` |
| 提交纪律 | **禁止 `git add -A`**；只 add 本指令涉及文件（`src/openrag/observability/logging.py`、`src/openrag/main.py`、配置项所在文件、`tests/unit/test_r384_request_id.py`）；提交前复核无敏感文件（本仓已跟踪 `.env.shared-infra`） |
| 可用辅助 | 本仓已有 `f2-commit-push.bat` / `scripts/f2_commit_push.ps1`、`rag1-commit-push.bat` / `scripts/rag1_commit_push.ps1`（沙箱外执行） |
| **回执内容** | ① commit hash；② 回归命令与通过数；③ 新增单测结果；④ 核实项①②③结论；⑤ 是否达到 §1 四项验收 |

**回执模板**：

```text
[OpenRAG / R-384 回执]
- commit: <hash>
- 核实①: contextvar 单一来源 = <同一机制 / 差异说明>
- 核实②: 启动路径 = uvicorn openrag.main:app --app-dir src；setup_logging 调用点 = lifespan(:51)
- 核实③: 受信来源判定函数 = <模块:函数>
- 回归: run_tests.py = exit <0/其他>；pytest tests/unit = <n> passed；ruff = 0；四静态扫描 = 0 命中；k07 = exit 0；smoke = exit 0
- 单测: test_r384_request_id.py = <n> passed（含受信/非受信/无头三分支）
- 验收: ①request_id 串联 ✅ ②非受信重生成 ✅ ③JSONL(status_code 数字) ✅ ④回归全通过 ✅
- 备注: <日志量变化/采样设置/偏差>
```

## 8. 约束与风险

| # | 项 | 说明 |
|:-:|----|------|
| 1 | 本指令未在 OpenRAG 仓运行验证 | 出具方沙箱禁止写入同级仓 → **务必执行 §6 回归后再提交** |
| 2 | 启用中间件后**日志量上升** | 保持 `log_request_body=False` / `log_response_body=False` 默认；必要时按级别采样（D-6 R-4） |
| 3 | 受信判定口径 | 必须复用本仓既有实现，勿新造第二套（D-6 R-6） |
| 4 | `request_id` 键名 | structlog 输出键必须精确为 `request_id`；若走自建 ContextVar 需确保映射，否则 OpenBase 侧取不到（会回退到 `trace_id`/`requestId` 别名，仍可能落空） |
| 5 | 采集命名 | 本仓采集文件名当前仍为启动时间戳（`openrag-YYYYMMDD-HHMMSS.log`）——由 OpenBase 采集侧（BL-147-04）统一为按日切分，**本仓无需处理** |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-09-16 | AA-OpenBase-Dev | 初始创建：OpenRAG 单仓施工指令（自包含）。含 **3 项前置核实与已取得的降险结论**（两处 `get_logger` 同源、注册不会报错、两处非"两套栈"）、契约与 JSONL 字段表（时间键为 `timestamp`，适配器已接受该别名）、完整改动（新增 `request_id` 工具 + 注册 `LoggingMiddleware` + `X-Request-Id` 受信透传 + JSONL 开关）、单测三分支、回归命令（含四静态扫描）、回执模板与 5 项风险 |
