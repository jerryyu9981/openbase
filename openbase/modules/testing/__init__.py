"""testing 模块：人工测试结论记录 API（C-10）.

批 2 C-10：受权 "test:record" 端点族——
``POST /api/v1/test-runs``（开轮）／``POST /api/v1/test-records``（单条）／
``PATCH /api/v1/test-records/{id}``（改判）／``GET /api/v1/test-runs/{run_id}/summary``（汇总）。

设计口径（方案《OpenBase-人工端到端测试日志记录方案》§5 批 2 C-10 + §9.1 D-1/D-2）：
- 落库复用 ``audit_logs``（JSON ``detail``，零迁移），以独立 action 区分，跨重启可查；
- FAIL/BLOCKED 强制 reason（§7 主观性约束），并要求附 ``request_id`` 客观证据（条数上软提示不强制）；
- 内存态即查（SummaryService），DB 为持久化镜像；best-effort 落库失败仅 WARN 不阻断。
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request

from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.auth.rbac import require_permission
from openbase.modules.testing.schemas import (
    RESULT_REQUIRES_REASON,
    TestRecordRequest,
    TestRecordUpdate,
    TestRunRequest,
)

logger = logging.getLogger("openbase.testing")

# 请求级记录通道标识（对齐 audit 模块；人工记录语义上仅 B 通道经网关编排）
CHANNEL_GATEWAY = "B"

# C-4 落库开关复用（测试环境由 tests/conftest.py 置 0，避免请求期访问 DB）
ENV_AUDIT_DB_PERSIST = "OPENBASE_AUDIT_DB_PERSIST"

# 审计动作码：与批 1 L2 用例事件日志同源，供 query_audit_logs_by_action 检索
ACTION_TEST_RUN = "test.run"
ACTION_TEST_RECORD = "test.record"
ACTION_TEST_RECORD_UPDATE = "test.record.update"

router = APIRouter(prefix="/api/v1", tags=["testing"])

__all__ = ["router", "TestRecordService", "TestResultService", "build_summary"]


def _new_run_id() -> str:
    """自动生成测试轮次号（UTC 时间，解析为本地稳定文本后去标点）。

    格式对齐方案 §4.2 示例 ``run-20260913-2130``（本地时间语义，便于测试者阅读）。
    """
    now = datetime.now().strftime("%Y%m%d-%H%M")
    return f"run-{now}"


def _new_record_id() -> int:
    """生成自增记录 ID."""
    return TestRecordService.next_id()


def _normalize_step_id(raw: int | str | None) -> int | str | None:
    """步骤序号归一化（同 audit 模块口径）：纯数字 → int。"""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    return int(text) if text.isdigit() else text


def _now() -> str:
    """ISO 8601 UTC 毫秒（对齐日志规范 ts 口径）."""
    return datetime.now(timezone.utc).isoformat()


class TestRecordService:
    """人工测试结论内存服务（C-10；DB 为持久化镜像，best-effort）.

    单例模式：进程内共享，供端点与 summary 即时读取（对齐 AuditService 方式）。
    """

    _records: list[dict[str, Any]] = []  # 最近 5000 条（淘汰最旧，防内存无限增长）
    _runs: dict[str, dict[str, Any]] = {}
    _seq: int = 0
    MAX_RECORDS = 5000

    @classmethod
    def next_id(cls) -> int:
        cls._seq += 1
        return cls._seq

    @classmethod
    def reset(cls) -> None:
        """测试用：清空全部状态（恢复进程内空态）。"""
        cls._records = []
        cls._runs = {}
        cls._seq = 0

    @classmethod
    def create_run(
        cls,
        *,
        run_id: str | None,
        title: str | None,
        scope: str | None,
        operator: str | None,
        request: Request,
    ) -> dict[str, Any]:
        """开一轮人工测试."""
        resolved_run_id = (run_id or "").strip() or _new_run_id()
        if resolved_run_id in cls._runs:
            raise BaseError(
                ErrorCode.BIZ_CONFLICT,
                f"test run already exists: {resolved_run_id}",
                detail={"run_id": resolved_run_id},
            )
        run = {
            "id": resolved_run_id,
            "title": title or "",
            "scope": scope or "",
            "operator": operator,
            "created_at": _now(),
            "records": [],
        }
        cls._runs[resolved_run_id] = run
        return dict(run)

    @classmethod
    def find_run(cls, run_id: str) -> dict[str, Any]:
        run = cls._runs.get(run_id)
        if run is None:
            raise BaseError(
                ErrorCode.BIZ_NOT_FOUND,
                f"test run not found: {run_id}",
                detail={"run_id": run_id},
            )
        return run

    @classmethod
    def create_record(
        cls, *, run_id: str, payload: TestRecordRequest, operator: str | None
    ) -> dict[str, Any]:
        """记录一条用例/步骤结论."""
        run = cls.find_run(run_id)
        step_id = _normalize_step_id(payload.step_id)
        result = payload.result
        if result in RESULT_REQUIRES_REASON and not (payload.reason or "").strip():
            raise _reason_required(result)

        record = {
            "id": _new_record_id(),
            "run_id": run_id,
            "case_id": payload.case_id,
            "step_id": step_id,
            "result": result,
            "title": payload.title or "",
            "expected": payload.expected or "",
            "observed": payload.observed or "",
            "reason": payload.reason or "",
            "request_id": payload.request_id or "",
            "duration_ms": payload.duration_ms,
            "operator": operator,
            "channel": CHANNEL_GATEWAY,
            "created_at": _now(),
        }
        run["records"].append(record)
        cls._records.append(record)
        cls._trim()
        return dict(record)

    @classmethod
    def find_record(cls, record_id: int) -> dict[str, Any]:
        for record in cls._records:
            if record.get("id") == record_id:
                return record
        raise BaseError(
            ErrorCode.BIZ_NOT_FOUND,
            f"test record not found: {record_id}",
            detail={"record_id": record_id},
        )

    @classmethod
    def update_record(
        cls, *, record_id: int, payload: TestRecordUpdate, operator: str | None
    ) -> dict[str, Any]:
        """改判：更新既有记录，追加变异审计标记 .updated."""
        record = cls.find_record(record_id)
        result = payload.result
        if result in RESULT_REQUIRES_REASON and not (payload.reason or "").strip():
            raise _reason_required(result)

        record["result"] = result
        if payload.reason is not None:
            record["reason"] = payload.reason
        if payload.observed is not None:
            record["observed"] = payload.observed
        record["updated_by"] = operator
        record["updated_at"] = _now()
        return dict(record)

    @classmethod
    def record_audit_detail(cls, record: dict[str, Any]) -> dict[str, Any]:
        """构造落库 detail（仅保留可审计字段，不含内部 state）. """
        return {
            "run_id": record.get("run_id"),
            "case_id": record.get("case_id"),
            "step_id": record.get("step_id"),
            "result": record.get("result"),
            "title": record.get("title") or None,
            "expected": record.get("expected") or None,
            "observed": record.get("observed") or None,
            "reason": record.get("reason") or None,
            "request_id": record.get("request_id") or None,
            "duration_ms": record.get("duration_ms"),
            "channel": record.get("channel"),
            "operator": record.get("operator"),
        }

    @classmethod
    def _trim(cls) -> None:
        if len(cls._records) > cls.MAX_RECORDS:
            del cls._records[: len(cls._records) - cls.MAX_RECORDS]


class TestResultService:
    """结论规则服务：校验硬约束（FAIL/BLOCKED 必填 reason）. """

    @staticmethod
    def require_reason(result: str, reason: str | None) -> None:
        if result in RESULT_REQUIRES_REASON and not (reason or "").strip():
            raise _reason_required(result)


def _reason_required(result: str) -> BaseError:
    return BaseError(
        ErrorCode.PARAM_INVALID,
        f"{result} requires a non-empty reason",
        detail={"result": result, "field": "reason"},
    )


def build_summary(run_id: str, *, records: list[dict[str, Any]]) -> dict[str, Any]:
    """聚合一轮测试的 summary（对齐方案 §4.3 ``test.run.end`` 计数）. """
    total = len(records)
    counts = {"pass": 0, "fail": 0, "blocked": 0, "skipped": 0}
    for record in records:
        result = record.get("result") or ""
        if result == "PASS":
            counts["pass"] += 1
        elif result == "FAIL":
            counts["fail"] += 1
        elif result == "BLOCKED":
            counts["blocked"] += 1
        elif result == "SKIPPED":
            counts["skipped"] += 1

    cases: dict[str, dict[str, Any]] = {}
    for record in records:
        case_id = record.get("case_id") or "<unlabeled>"
        case = cases.setdefault(
            case_id,
            {"case_id": case_id, "latest_result": "PASS", "steps": []},
        )
        case["steps"].append(
            {
                "id": record.get("id"),
                "step_id": record.get("step_id"),
                "result": record.get("result"),
                "reason": record.get("reason") or None,
                "request_id": record.get("request_id") or None,
                "duration_ms": record.get("duration_ms"),
                "title": record.get("title") or None,
            }
        )
        case["latest_result"] = record.get("result") or case["latest_result"]

    return {
        "run_id": run_id,
        "total": total,
        "pass": counts["pass"],
        "fail": counts["fail"],
        "blocked": counts["blocked"],
        "skipped": counts["skipped"],
        "passed": total > 0 and counts["fail"] == 0 and counts["blocked"] == 0,
        "cases": _sorted_cases(cases),
    }


def _sorted_cases(cases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(cases.values(), key=lambda case: str(case["case_id"]))


async def _persist(action: str, *, user_id: str | None, detail: dict[str, Any]) -> None:
    """best-effort 落 ``audit_logs``（复用 JSON ``detail``，零迁移）.

    C-10：人工测试结论作为审计镜像持久化，跨重启可查。失败仅 WARN 且回滚，不阻断响应。
    """
    if os.getenv(ENV_AUDIT_DB_PERSIST, "1") == "0":
        return
    session = None
    try:
        from openbase.core.db.session import get_session_factory
        from openbase.core.models import AuditLog

        operator_text = str(user_id) if user_id is not None else ""
        async with get_session_factory()() as session:
            session.add(
                AuditLog(
                    user_id=int(operator_text) if operator_text.isdigit() else None,
                    tenant_id=None,
                    action=action,
                    resource=detail.get("case_id") or detail.get("run_id") or "test-record",
                    resource_id=str(detail.get("id") or detail.get("run_id"))[:64] or None,
                    request_id=detail.get("request_id") or f"req-test-{uuid.uuid4().hex[:8]}",
                    detail=detail,
                )
            )
            await session.commit()
    except Exception:  # noqa: BLE001 - 审计尽力留痕，不阻断
        logger.warning(
            "test record db persist failed (degraded)",
            extra={"action": action, "run_id": detail.get("run_id")},
        )
        if session is not None:
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001
                pass


def _ok(data: Any) -> dict[str, Any]:
    """统一响应信封 {code, message, data}（对齐 API 契约）."""
    return {"code": 0, "message": "success", "data": data}


def _operator(request: Request) -> tuple[str | None, str | None]:
    """从 request.state 提取操作者（user_id/user_name），缺省 None."""
    user_id = getattr(request.state, "user_id", None)
    user_name = getattr(request.state, "user_name", None)
    return user_id, user_name


# ---- 受权端点（统一 require_permission("test:record")） ----

_deps = [Depends(require_permission("test:record"))]


@router.post("/test-runs", dependencies=_deps)
async def create_test_run(payload: TestRunRequest, request: Request) -> dict[str, Any]:
    """开一轮人工测试."""
    user_id, user_name = _operator(request)
    run = TestRecordService.create_run(
        run_id=payload.run_id,
        title=payload.title,
        scope=payload.scope,
        operator=str(user_id) if user_id is not None else user_name,
        request=request,
    )
    detail = {"run_id": run["id"], "title": run["title"], "scope": run["scope"]}
    await _persist(ACTION_TEST_RUN, user_id=user_id, detail=detail)
    return _ok({"run_id": run["id"], "title": run["title"], "scope": run["scope"], "records": []})


@router.post("/test-records", dependencies=_deps)
async def create_test_record(payload: TestRecordRequest, request: Request) -> dict[str, Any]:
    """记录一条用例/步骤结论."""
    user_id, user_name = _operator(request)
    record = TestRecordService.create_record(
        run_id=payload.run_id, payload=payload, operator=user_name or str(user_id) if user_id else None
    )
    detail = TestRecordService.record_audit_detail(record)
    detail["id"] = record["id"]
    await _persist(ACTION_TEST_RECORD, user_id=user_id, detail=detail)
    return _ok(record)


@router.patch("/test-records/{record_id}", dependencies=_deps)
async def update_test_record(record_id: int, payload: TestRecordUpdate, request: Request) -> dict[str, Any]:
    """改判（追加审计 trace）. """
    user_id, user_name = _operator(request)
    record = TestRecordService.update_record(
        record_id=record_id, payload=payload, operator=user_name or str(user_id) if user_id else None
    )
    detail = TestRecordService.record_audit_detail(record)
    detail["id"] = record["id"]
    detail["updated_by"] = record.get("updated_by")
    detail["updated_at"] = record.get("updated_at")
    await _persist(ACTION_TEST_RECORD_UPDATE, user_id=user_id, detail=detail)
    return _ok(record)


@router.get("/test-runs/{run_id}/summary", dependencies=_deps)
async def test_run_summary(run_id: str) -> dict[str, Any]:
    """一轮测试 result summary(含按用例分组的步骤清单). """
    run = TestRecordService.find_run(run_id)
    return _ok(build_summary(run_id, records=run["records"]))


__version__ = "1.0.0"
