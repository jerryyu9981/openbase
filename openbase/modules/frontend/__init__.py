"""frontend 模块：统一前端动态模块注册 API（v1.2.0）.

提供 /api/v1/modules 供前端 ModuleRegistry 获取模块注册表
（模块 ID/名称/路由前缀/入口/权限标识/状态）。

状态存储（v1.4.6 Step 3 定案，ADR-146-07）：
- 读取：**优先 ``dynamic_modules`` 表**（core.models.business，随
  ``core/db/init.py`` 的 ``create_all`` 随初始化链建表），缺失行回退 ``DEFAULT_MODULES``
  出厂值；DB 不可用仅 WARN 并按内存回退（读不阻断）；
- 写入：留痕成功后落库（幂等 upsert：存在则 update ``status``，否则 insert）；
  落库失败 → 回退进程内存（``DEFAULT_MODULES`` 作进程内缓存）并 WARN；
- 留痕：``module.switch`` **先留痕后生效**——留痕不可用（``OPENBASE_AUDIT_DB_PERSIST=0``
  或 ``audit_logs`` 落库失败）即拒绝变更并抛 BIZ 错误，模块状态保持不变。
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from openbase.core.deps.auth import get_current_user
from openbase.core.errors import BaseError, ErrorCode
from openbase.modules.auth.rbac import require_permission
from openbase.modules.frontend.repository import ModuleStatusRepository

logger = logging.getLogger("openbase.frontend")

router = APIRouter(prefix="/api/v1/modules", tags=["modules"])

__all__ = ["ACTION_MODULE_SWITCH", "DEFAULT_MODULES", "ModuleService", "router"]

# 审计动作码：模块开关（v1.4.6 ADR-146-07，AC-146-15-3 强制留痕）
ACTION_MODULE_SWITCH = "module.switch"
# 留痕开关：测试环境置 0，避免请求期访问 DB（与 testing 模块同口径）
ENV_AUDIT_DB_PERSIST = "OPENBASE_AUDIT_DB_PERSIST"

MODULE_STATUS_VALUES: tuple[str, ...] = ("enabled", "disabled")


class ModuleStatusRequest(BaseModel):
    """模块开关请求体（AC-146-15-1：status 枚举白名单，非法 400）。"""

    status: Literal["enabled", "disabled"] = Field(..., description="目标状态")


# 模块注册表（对齐系统架构设计文档 §6：模块ID/路由前缀/权限标识）
DEFAULT_MODULES: list[dict] = [
    {
        "id": "openllm",
        "name": "OpenLLM",
        "icon": "chat",
        "route_prefix": "/openllm",
        "entry": "modules/openllm",
        "permission": "openllm:view",
        "status": "enabled",
        "sort_order": 10,
    },
    {
        "id": "knowledge",
        "name": "知识库",
        "icon": "collection",
        "route_prefix": "/knowledge",
        "entry": "modules/knowledge",
        "permission": "openrag:view",
        "status": "enabled",
        "sort_order": 20,
    },
    {
        "id": "memory",
        "name": "记忆",
        "icon": "memo",
        "route_prefix": "/memory",
        "entry": "modules/memory",
        "permission": "openmemory:view",
        "status": "enabled",
        "sort_order": 30,
    },
    {
        "id": "portrait",
        "name": "画像",
        "icon": "user",
        "route_prefix": "/portrait",
        "entry": "modules/portrait",
        "permission": "dps:view",
        "status": "enabled",
        "sort_order": 40,
    },
    {
        # v1.4.6+（网关模块页可达性修复）：统一网关为第 5 个动态模块。
        # 此前 gateway 仅存在于前端 moduleRouteLoaders，未注册进本表 →
        # 模块路由永不挂载，/gateway/* 落入守卫兜底跳 /dashboard。
        "id": "gateway",
        "name": "统一网关",
        "icon": "connection",
        "route_prefix": "/gateway",
        "entry": "modules/gateway",
        "permission": "gateway:view",
        "status": "enabled",
        "sort_order": 50,
    },
]


class ModuleService:
    """动态模块注册服务（读取 DB 优先、写入 DB 可用时落库，否则内存回退）."""

    # ---- 内存注册表（出厂值 + 进程内回退缓存） ----

    @staticmethod
    def _memory_entry(module_id: str) -> dict | None:
        """返回内存注册表中模块条目的**引用**（就地更新用）。"""
        return next((item for item in DEFAULT_MODULES if item["id"] == module_id), None)

    @classmethod
    def _memory_snapshot(cls) -> list[dict]:
        return [dict(item) for item in DEFAULT_MODULES]

    def list_modules(self) -> list[dict]:
        """内存注册表快照（同步口径；HTTP 读路径请用 :meth:`alist_modules` 以优先 DB）."""
        return self._memory_snapshot()

    def get_module(self, module_id: str) -> dict | None:
        """内存注册表单条查询（同步口径；HTTP 读路径请用 :meth:`aget_module`）."""
        entry = self._memory_entry(module_id)
        return dict(entry) if entry is not None else None

    def set_status(self, module_id: str, status: str) -> dict:
        """就地更新**内存**注册表状态（不落库）；返回 ``{module, previous_status, no_change}``.

        保留用途：进程内回退缓存同步（:meth:`aset_status` 内部调用）与既有调用面；
        HTTP 写路径统一走 :meth:`aset_status`（留痕成功后调用）。
        """
        module = self._memory_entry(module_id)
        if module is None:
            raise KeyError(module_id)
        previous_status = module.get("status", "enabled")
        module["status"] = status
        return {
            "module": dict(module),
            "previous_status": previous_status,
            "no_change": previous_status == status,
        }

    # ---- DB 优先读取 ----

    async def alist_modules(self) -> list[dict]:
        """模块注册表（状态读取优先 DB，缺失行回退出厂值）."""
        status_map = await self._effective_status_map()
        items = self._memory_snapshot()
        for item in items:
            if item["id"] in status_map:
                item["status"] = status_map[item["id"]]
        return items

    async def aget_module(self, module_id: str) -> dict | None:
        """模块详情（状态读取优先 DB）."""
        for item in await self.alist_modules():
            if item["id"] == module_id:
                return item
        return None

    async def _effective_status_map(self) -> dict[str, str]:
        """生效状态映射：DB 优先、缺失行回退内存出厂值.

        DB 不可用（连接/查询异常）仅 WARN 并整体回退内存——读路径不阻断，
        与写路径的 fail-closed 口径区别对待（读降级不会产生无留痕的状态漂移）。
        """
        baseline = {item["id"]: item["status"] for item in DEFAULT_MODULES}
        try:
            persisted = await ModuleStatusRepository.load_status_map()
        except Exception:  # noqa: BLE001 - 读降级：DB 不可用回退内存
            logger.warning(
                "dynamic_modules status read failed; fallback to in-memory registry",
                extra={"fallback": "memory"},
            )
            return baseline
        # 仅覆盖注册表内已知模块（注册表为模块全集，未知行不引入）
        baseline.update({key: value for key, value in persisted.items() if key in baseline})
        return baseline

    # ---- 写入（留痕成功后由路由调用） ----

    async def aset_status(self, module_id: str, status: str) -> dict:
        """变更模块状态：DB 可用则落库，不可用回退内存并 WARN.

        调用约束：**必须**在 ``module.switch`` 留痕成功之后调用（先留痕后生效）。

        Returns:
            ``{module, previous_status, no_change}``；``no_change=True`` 时状态与目标
            一致，不落库、不改内存（幂等，无副作用）。

        Raises:
            KeyError: 模块不在注册表内。
        """
        current = await self._effective_status_map()
        if module_id not in current:
            raise KeyError(module_id)
        previous_status = current[module_id]
        module = self.get_module(module_id) or {"id": module_id}
        module["status"] = status
        if previous_status == status:
            return {"module": module, "previous_status": previous_status, "no_change": True}

        try:
            await ModuleStatusRepository.upsert_status(module_id, status, defaults=module)
        except Exception:  # noqa: BLE001 - 写降级：内存生效 + WARN（不回滚已留痕的变更）
            logger.warning(
                "dynamic_modules status persist failed; in-memory registry keeps the change",
                extra={"module_id": module_id, "status": status},
            )
        entry = self._memory_entry(module_id)
        if entry is not None:
            entry["status"] = status  # 进程内回退缓存同步（DB 不可用时的读取来源）
        return {"module": module, "previous_status": previous_status, "no_change": False}


@router.get("")
async def list_modules(user: dict = Depends(get_current_user)) -> dict:
    """模块注册表（状态读取优先 DB，缺失行回退出厂值）."""
    items = await ModuleService().alist_modules()
    return {"code": 0, "message": "ok", "data": {"items": items, "total": len(items)}}


@router.get("/{id}")
async def get_module(id: str, user: dict = Depends(get_current_user)) -> dict:
    """模块详情（状态读取优先 DB）."""
    item = await ModuleService().aget_module(id)
    if item is None:
        raise BaseError(ErrorCode.PARAM_NOT_FOUND, f"module not found: {id}")
    return {"code": 0, "message": "ok", "data": item}


def _request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    return existing or f"req-{uuid.uuid4().hex[:12]}"


def _audit_unavailable(module_id: str, reason: str) -> BaseError:
    """构造「留痕不可用」业务错误（BIZ 前缀；模块状态保持不变）."""
    return BaseError(
        ErrorCode.BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE,
        "module switch rejected: audit trail unavailable",
        detail={"module_id": module_id, "reason": reason},
    )


async def _record_module_switch(
    *,
    operator_id: int | str | None,
    module_id: str,
    previous_status: str,
    status: str,
    request_id: str,
) -> None:
    """写 ``audit_logs(action=module.switch)``；**先留痕后生效**（ADR-146-07 Step 3 定案）.

    失败口径（与 audit/testing 模块的 best-effort 降级**刻意相反**）：

    - ``OPENBASE_AUDIT_DB_PERSIST=0`` = 留痕通道显式不可用 → 直接失败，不静默生效；
    - 落库异常（连接失败 / ``commit`` 失败）→ WARN 后抛错，**模块状态保持原值**。

    理由：模块启停是平台级高危变更（可整体摘除业务模块），若沿用「先改状态、
    留痕尽力而为」，则「状态已变 + 审计缺失」会同时成立且事后不可回溯；故取
    fail-closed（变更失败并回滚）——宁可拒绝变更，也不产生无留痕的状态漂移。

    Raises:
        BaseError: ``BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE``（留痕不可用）。
    """
    if os.getenv(ENV_AUDIT_DB_PERSIST, "1") == "0":
        raise _audit_unavailable(module_id, "audit persist disabled")

    detail = {
        "operator_id": str(operator_id) if operator_id is not None else None,
        "module_id": module_id,
        "previous_status": previous_status,
        "status": status,
    }
    operator_text = str(operator_id) if operator_id is not None else ""
    try:
        from openbase.core.db.session import get_session_factory
        from openbase.core.models import AuditLog

        async with get_session_factory()() as session:
            session.add(
                AuditLog(
                    user_id=int(operator_text) if operator_text.isdigit() else None,
                    tenant_id=None,
                    action=ACTION_MODULE_SWITCH,
                    resource=f"module:{module_id}",
                    resource_id=module_id[:64],
                    request_id=request_id,
                    detail=detail,
                )
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001 - 统一转为业务错误（拒绝变更，状态不变）
        logger.warning(
            "module.switch audit persist failed; change rejected",
            extra={"module_id": module_id, "operator_id": operator_text},
        )
        raise _audit_unavailable(module_id, "audit persist failed") from exc


@router.patch(
    "/{id}",
    dependencies=[Depends(require_permission("module:manage", error_code=ErrorCode.PERM_403))],
)
async def switch_module(
    id: str,
    payload: ModuleStatusRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    """模块启用/停用（v1.4.6 ADR-146-07，AC-146-15；Step 3 定案：先留痕后生效）.

    - 权限：``module:manage``（仅管理员），无权限 403（AC-146-15-2）；
    - 留痕：**先**写 ``audit_logs(action=module.switch)``；留痕不可用（开关置 0 或
      落库失败）→ ``BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE``（503）且模块状态不变；
    - 幂等：目标状态与当前相同 → 200 且**不重复留痕**（``no_change``）；
    - 生效：``effective=next_login`` —— **不承诺热生效**（ADR-146-07）；
    - 语义不变：不改动 ``id``/``route_prefix``/``permission``（AC-146-15-4）。
    """
    service = ModuleService()
    module = await service.aget_module(id)
    if module is None:
        allowed = [item["id"] for item in service.list_modules()]
        raise BaseError(
            ErrorCode.PARAM_NOT_FOUND,
            "module not found",
            detail={"module_id": id, "allowed": allowed},
        )

    request_id = _request_id(request)
    previous_status = module["status"]
    if previous_status == payload.status:
        # 幂等：无变更 → 200 且不重复留痕（不动 DB、不动内存）
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "id": id,
                "status": payload.status,
                "previous_status": previous_status,
                "effective": "next_login",
                "request_id": request_id,
            },
        }

    await _record_module_switch(
        operator_id=user.get("id"),
        module_id=id,
        previous_status=previous_status,
        status=payload.status,
        request_id=request_id,
    )
    result = await service.aset_status(id, payload.status)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "id": id,
            "status": result["module"]["status"],
            "previous_status": result["previous_status"],
            "effective": "next_login",
            "request_id": request_id,
        },
    }


__version__ = "1.3.0"
