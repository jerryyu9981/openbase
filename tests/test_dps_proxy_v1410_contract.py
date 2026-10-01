"""v1.4.10 Step 3 P1 契约测试：dps-proxy 新增 22 端点（10 新增 ＋ 12 补代理）.

契约事实源：《OpenBase-API接口设计文档-v1.4.10》§1（路径映射）／§1.1（补代理路由）／
§3.1（权限动作映射，仅文档对齐，本仓不做权限判定）／§3.2（新增端点请求响应要点）／
§3.4（补代理端点契约与错误码口径）；追溯：《OpenBase-设计开发追溯矩阵-v1.4.10》§2.1
（TD-1410-01／02／03／32）。

断言口径（与既有 ``tests/test_dps_proxy.py`` 同一 mock 上游模式，探活开关关闭）：
1. **路径映射**：本仓 ``/api/v1/dps-proxy/{path}`` → 上游
   ``{dps_upstream_base}/api/v2/portrait/{path}``（22 条逐条）；
2. **方法保真**：GET／POST／PUT／DELETE 透传；
3. **参数透传**：查询参数原样转发（不在本仓裁剪，含 ``?field_key=`` 不拦截）；
4. **请求体透传**：POST／PUT body 原样转发；
5. **身份头注入**：四头 ＋ ``X-Proxy-Source=dps`` ＋ ``X-Request-Id``；
6. **错误语义保真**：上游 4xx／5xx 原样呈现（不转 500、不改 message/code）；
7. **认证门禁**：无 token → 401（既有行为不变）。
"""

from __future__ import annotations

import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from openbase import init_app
from openbase.modules import dps_proxy as dps_proxy_module
from openbase.modules.auth import UserService
from openbase.modules.auth.jwt import create_access_token
from openbase.modules.protocol_headers import PROXY_SOURCE_DPS
from openbase.settings import Settings

PREFIX = "/api/v1/dps-proxy"
UPSTREAM_BASE = "http://127.0.0.1:8000"

# v1.4.10 新增 22 端点契约用例（编号，方法，本仓相对路径，上游路径，查询参数，请求体）
V1410_CASES: list[dict] = [
    {
        "id": "#1-template-package-export",
        "method": "POST",
        "path": "/template-packages/export",
        "upstream": "/api/v2/portrait/template-packages/export",
        "params": {},
        "body": {"scope": {"type": "all", "codes": []}, "include_annotation_templates": True},
    },
    {
        "id": "#2-template-package-import",
        "method": "POST",
        "path": "/template-packages/import",
        "upstream": "/api/v2/portrait/template-packages/import",
        "params": {},
        "body": {"package": {"format_version": "1.0"}, "conflict_policy": "skip", "dry_run": True},
    },
    {
        "id": "#3-template-diff",
        "method": "GET",
        "path": "/templates/tpl-1/diff",
        "upstream": "/api/v2/portrait/templates/tpl-1/diff",
        "params": {"target_version": "1"},
        "body": None,
    },
    {
        "id": "#4-template-rollback",
        "method": "POST",
        "path": "/templates/tpl-1/rollback",
        "upstream": "/api/v2/portrait/templates/tpl-1/rollback",
        "params": {},
        "body": {"target_version": "1", "reason": "回归验证"},
    },
    {
        "id": "#5-template-preflight",
        "method": "GET",
        "path": "/templates/tpl-1/preflight",
        "upstream": "/api/v2/portrait/templates/tpl-1/preflight",
        "params": {},
        "body": None,
    },
    {
        "id": "#6-lineage-tag-sources",
        "method": "GET",
        "path": "/lineage/tags/tag-1",
        "upstream": "/api/v2/portrait/lineage/tags/tag-1",
        "params": {},
        "body": None,
    },
    {
        "id": "#7-lineage-impact",
        "method": "GET",
        "path": "/lineage/impact",
        "upstream": "/api/v2/portrait/lineage/impact",
        "params": {"template_code": "tpl-1"},
        "body": None,
    },
    {
        "id": "#8-measures-suggest",
        "method": "GET",
        "path": "/measures/suggest",
        "upstream": "/api/v2/portrait/measures/suggest",
        "params": {"person_id": "p1"},
        "body": None,
    },
    {
        "id": "#9-annotation-adapter-generate",
        "method": "POST",
        "path": "/annotation-adapters/adp-1/generate",
        "upstream": "/api/v2/portrait/annotation-adapters/adp-1/generate",
        "params": {},
        "body": {"text": "示例文本", "annotation_template": "at-1"},
    },
    {
        "id": "#10-scoring-types",
        "method": "GET",
        "path": "/scoring-types",
        "upstream": "/api/v2/portrait/scoring-types",
        "params": {"page": "1", "page_size": "20"},
        "body": None,
    },
    {
        "id": "#11-templates-list",
        "method": "GET",
        "path": "/templates",
        "upstream": "/api/v2/portrait/templates",
        "params": {"status": "active", "profile_type": "persona", "subject_type": "person"},
        "body": None,
    },
    {
        "id": "#12-template-detail",
        "method": "GET",
        "path": "/templates/tpl-1",
        "upstream": "/api/v2/portrait/templates/tpl-1",
        "params": {},
        "body": None,
    },
    {
        "id": "#13-template-create",
        "method": "POST",
        "path": "/templates",
        "upstream": "/api/v2/portrait/templates",
        "params": {},
        "body": {"code": "tpl-1", "name": "示例模板", "profile_type": "persona"},
    },
    {
        "id": "#14-template-update",
        "method": "PUT",
        "path": "/templates/tpl-1",
        "upstream": "/api/v2/portrait/templates/tpl-1",
        "params": {},
        "body": {"name": "示例模板v2", "extends": None},
    },
    {
        "id": "#15-template-activate",
        "method": "POST",
        "path": "/templates/tpl-1/activate",
        "upstream": "/api/v2/portrait/templates/tpl-1/activate",
        "params": {},
        "body": None,
    },
    {
        "id": "#16-template-deactivate",
        "method": "POST",
        "path": "/templates/tpl-1/deactivate",
        "upstream": "/api/v2/portrait/templates/tpl-1/deactivate",
        "params": {},
        "body": None,
    },
    {
        "id": "#17-annotation-templates-list",
        "method": "GET",
        "path": "/annotation-templates",
        "upstream": "/api/v2/portrait/annotation-templates",
        "params": {"template_code": "tpl-1", "scenario": "intake"},
        "body": None,
    },
    {
        "id": "#18-annotation-template-detail",
        "method": "GET",
        "path": "/annotation-templates/at-1",
        "upstream": "/api/v2/portrait/annotation-templates/at-1",
        "params": {},
        "body": None,
    },
    {
        "id": "#19-annotation-template-create",
        "method": "POST",
        "path": "/annotation-templates",
        "upstream": "/api/v2/portrait/annotation-templates",
        "params": {},
        "body": {"code": "at-1", "name": "标注模板", "template_code": "tpl-1", "scenario": "intake"},
    },
    {
        "id": "#20-annotation-template-update",
        "method": "PUT",
        "path": "/annotation-templates/at-1",
        "upstream": "/api/v2/portrait/annotation-templates/at-1",
        "params": {},
        "body": {"template_code": "tpl-2", "field_schema": []},
    },
    {
        "id": "#21-annotation-template-delete",
        "method": "DELETE",
        "path": "/annotation-templates/at-1",
        "upstream": "/api/v2/portrait/annotation-templates/at-1",
        "params": {},
        "body": None,
    },
    {
        "id": "#22-labels-list",
        "method": "GET",
        "path": "/labels",
        "upstream": "/api/v2/portrait/labels",
        "params": {"action": "list"},
        "body": None,
    },
]


class FakeResponse:
    """模拟 httpx.Response."""

    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    """模拟 httpx.AsyncClient：记录请求并返回预设响应."""

    def __init__(self, *args, **kwargs):
        self.request_calls: list[dict] = []
        self.responses: list[FakeResponse] = []
        self.fail_with: Exception | None = None

    def set_responses(self, responses: list[FakeResponse]) -> None:
        self.responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, method: str, url: str, **kwargs) -> FakeResponse:
        self.request_calls.append({"method": method, "url": url, **kwargs})
        if self.fail_with is not None:
            raise self.fail_with
        if self.responses:
            resp = self.responses.pop(0)
            if not self.responses:
                self.responses.append(resp)
            return resp
        return FakeResponse(200, {"code": 200, "message": "success", "data": {}})


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """构造启用 auth + dps_proxy 的应用，替换上游 httpx 客户端并覆盖 dps 配置."""
    settings = Settings()
    for module in ("auth", "proxy", "dps_proxy", "audit", "tenant", "config"):
        settings.enable_module(module)
    settings.dps_upstream_base = UPSTREAM_BASE
    settings.dps_default_org_id = "default-org"
    settings.dps_default_tenant_id = "default-tenant"
    # 关闭探活：避免探活请求插入 request_calls 序列，破坏"恰一次转发"断言
    settings.dps_health_check_enabled = False
    import importlib

    settings_module = importlib.import_module("openbase.settings")
    monkeypatch.setattr(settings_module, "_settings", settings)
    UserService.seed_memory_user("admin", "admin123")
    app = init_app(settings)
    fake = FakeAsyncClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: fake)
    tc = TestClient(app)
    tc.fake = fake  # type: ignore[attr-defined]
    return tc


def _token(client: TestClient) -> str:
    """登录获取 token（JWT 含 tenant_id/org_id/role）."""
    resp = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _token_with_identity() -> str:
    """直接签发带完整身份的 JWT（sub/tenant_id/org_id/role）."""
    return create_access_token(
        "42",
        username="identity-user",
        tenant_id="tenant-001",
        extra={"org_id": "org-001", "role": "admin"},
    )


def _ok_response() -> FakeResponse:
    """构造上游成功响应（DPS 网关形态 {code,message,data}）."""
    return FakeResponse(200, {"code": 200, "message": "success", "data": {"echo": True}})


# ---------------------------------------------------------------------------
# 1~6. 22 端点契约：路径映射 / 方法保真 / 参数与 body 透传 / 身份头注入
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", V1410_CASES, ids=[c["id"] for c in V1410_CASES])
def test_v1410_endpoint_proxy_contract(client: TestClient, case: dict) -> None:
    """v1.4.10 端点 → 上游路径/方法/参数/请求体/身份头逐条保真."""
    token = _token_with_identity()
    client.fake.set_responses([_ok_response()])  # type: ignore[attr-defined]
    resp = client.request(
        case["method"],
        f"{PREFIX}{case['path']}",
        params=case["params"] or None,
        json=case["body"] if case["body"] is not None else None,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == {"code", "message", "data", "timestamp"}
    assert body["code"] == 0
    assert body["message"] == "success"
    assert body["data"] == {"echo": True}

    calls = client.fake.request_calls  # type: ignore[attr-defined]
    assert len(calls) == 1, "应恰有一次上游转发（探活已关闭）"
    call = calls[0]
    assert call["method"] == case["method"]
    assert call["url"] == f"{UPSTREAM_BASE}{case['upstream']}"
    assert call["params"] == case["params"]
    assert call["json"] == case["body"]

    headers = call["headers"]
    assert headers["X-User-ID"] == "42"
    assert headers["X-Tenant-ID"] == "tenant-001"
    assert headers["X-Org-ID"] == "tenant-001"  # OB-8 别名收敛
    assert headers["X-User-Role"] == "admin"
    assert headers["X-Proxy-Source"] == PROXY_SOURCE_DPS
    assert headers["X-Request-Id"]


def test_v1410_all_new_upstream_paths_under_portrait_prefix() -> None:
    """22 端点上游路径全部落在 /api/v2/portrait 前缀下（契约 §1 映射规则）."""
    for case in V1410_CASES:
        assert case["upstream"].startswith("/api/v2/portrait/"), case["id"]


# ---------------------------------------------------------------------------
# 7. 认证门禁（既有行为不变）
# ---------------------------------------------------------------------------


def test_v1410_new_endpoint_requires_auth(client: TestClient) -> None:
    """无认证头访问新增端点 → 401（fail-closed，AC 兼容既有口径）."""
    resp = client.get(f"{PREFIX}/templates")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "AUTH_401"


# ---------------------------------------------------------------------------
# 8. 错误语义保真：4xx / 5xx 透传（TD-1410-03）
# ---------------------------------------------------------------------------


def test_v1410_4xx_detail_passthrough(client: TestClient) -> None:
    """上游 404 {detail} → 本仓 404，code=HTTP 状态码，message=detail，不转 500."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(404, {"detail": "画像模板不存在: tpl-x"}),
    ])
    resp = client.get(
        f"{PREFIX}/templates/tpl-x", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body["code"] == 404
    assert "画像模板不存在" in body["message"]


def test_v1410_409_gateway_error_passthrough(client: TestClient) -> None:
    """上游 409 {code,message} → code/message 原样透传（不映射为 OpenBase 错误码）."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(409, {"code": 409, "message": "annotation template code already exists", "data": None}),
    ])
    resp = client.post(
        f"{PREFIX}/annotation-templates",
        json={"code": "at-1", "template_code": "tpl-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409, resp.text
    body = resp.json()
    assert body["code"] == 409
    assert body["message"] == "annotation template code already exists"


def test_v1410_503_adapter_unavailable_passthrough(client: TestClient) -> None:
    """上游 503（适配器不可用，降级非阻塞）语义保真透传."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(503, {"code": 503, "message": "annotation adapter unavailable"}),
    ])
    resp = client.post(
        f"{PREFIX}/annotation-adapters/adp-1/generate",
        json={"text": "x", "annotation_template": "at-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 503, resp.text
    assert resp.json()["code"] == 503
    assert resp.json()["message"] == "annotation adapter unavailable"


def test_v1410_upstream_unreachable_returns_502(client: TestClient) -> None:
    """上游不可达 → 502 SYS_UPSTREAM_ERROR（既有归一语义，未新增端点不改变）."""
    token = _token_with_identity()
    client.fake.fail_with = httpx.ConnectError("connection refused")  # type: ignore[attr-defined]
    resp = client.get(
        f"{PREFIX}/scoring-types", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 502, resp.text
    assert resp.json()["code"] == "SYS_502"


# ---------------------------------------------------------------------------
# 9. 查询参数不拦截（D-6-6：?field_key= 显式不支持，本仓透传上游 400 语义）
# ---------------------------------------------------------------------------


def test_v1410_lineage_impact_field_key_not_intercepted(client: TestClient) -> None:
    """?field_key= 不支持的参数由上游裁决：本仓原样透传并保真上游 400."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(400, {"code": 400, "message": "field_key is not supported", "data": None}),
    ])
    resp = client.get(
        f"{PREFIX}/lineage/impact?field_key=age",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["params"] == {"field_key": "age"}
    assert call["url"] == f"{UPSTREAM_BASE}/api/v2/portrait/lineage/impact"


def test_v1410_import_dry_run_flag_passthrough(client: TestClient) -> None:
    """导入 dry_run 与 conflict_policy 原样透传（透传不本仓去重，幂等由上游 package_hash）."""
    token = _token_with_identity()
    client.fake.set_responses([_ok_response()])  # type: ignore[attr-defined]
    payload = {
        "package": {"format_version": "1.0", "package_hash": "hash-abc"},
        "conflict_policy": "overwrite",
        "dry_run": True,
    }
    resp = client.post(
        f"{PREFIX}/template-packages/import",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["json"] == payload
    assert call["url"] == f"{UPSTREAM_BASE}/api/v2/portrait/template-packages/import"


# ---------------------------------------------------------------------------
# 10. 既有端点回归（保持 12 条路由行为不变）
# ---------------------------------------------------------------------------


def test_v1410_existing_portrait_route_still_maps(client: TestClient) -> None:
    """既有 /portraits 路由行为不变（回归，TD-21 兼容性）."""
    token = _token(client)
    client.fake.set_responses([_ok_response()])  # type: ignore[attr-defined]
    resp = client.get(
        f"{PREFIX}/portraits?page=1&page_size=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["url"].startswith(f"{UPSTREAM_BASE}/api/v2/portrait/list")


def test_v1410_module_version_declared() -> None:
    """模块版本常量存在（留痕可核）."""
    assert isinstance(dps_proxy_module.__version__, str)


# ---------------------------------------------------------------------------
# 11. dps_proxy 未覆盖分支回归（v1.4.10 Step 4 缺陷修复）
#
# 目标分支（openbase/modules/dps_proxy/__init__.py）：
#   - 503 显式降级（连续转发失败达 dps_degrade_threshold，约 300-325 行）；
#   - 错误体 {detail} 为 dict / list 的归一化提取（约 158-175 行）；
#   - 非 JSON / 非 dict 响应体的 raw 兜底（约 139-142、157 行）；
#   - 值映射 JSON 解析空值／非法值回落（约 81-89 行）。
# ---------------------------------------------------------------------------


class _NonJsonResponse(FakeResponse):
    """上游返回无法解析为 JSON 的响应体（触发 raw 截断兜底）."""

    def __init__(self, status_code: int, raw_text: str) -> None:
        self.status_code = status_code
        self._payload: dict = {}
        self.text = raw_text

    def json(self) -> dict:
        raise ValueError("response body is not JSON")


def test_v1410_upstream_degrade_threshold_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """连续失败达阈值 → 503 显式降级（X-DPS-Upstream-Degraded + data.degraded）.

    覆盖 ``_forward`` 异常分支中的 503 显式降级路径：预置连续失败计数为
    ``threshold - 1``，本次转发再失败一次即达阈值 → 返回 503（而非既有 502），
    响应头置 ``X-DPS-Upstream-Degraded: true`` 并以 ERROR 记录降级日志。
    """
    token = _token_with_identity()
    threshold = max(1, dps_proxy_module.get_settings().dps_degrade_threshold)
    monkeypatch.setattr(dps_proxy_module, "_dps_consecutive_failures", threshold - 1)
    client.fake.fail_with = httpx.ConnectError("connection refused")  # type: ignore[attr-defined]
    with caplog.at_level(logging.ERROR, logger="openbase.dps_proxy"):
        resp = client.get(
            f"{PREFIX}/templates", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["code"] == 503
    assert body["data"]["degraded"] is True
    assert body["data"]["consecutive_failures"] == threshold
    assert resp.headers.get("X-DPS-Upstream-Degraded") == "true"
    assert any(
        "degraded" in record.getMessage() for record in caplog.records
    ), "达阈值应记录 ERROR 降级日志"


def test_v1410_degrade_counter_resets_after_recovery(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """阈值内失败 → 502 且计数 +1；上游随后成功 → 计数归零（fail-open 复原）."""
    token = _token_with_identity()
    monkeypatch.setattr(dps_proxy_module, "_dps_consecutive_failures", 0)
    client.fake.fail_with = httpx.ConnectError("connection refused")  # type: ignore[attr-defined]
    failing = client.get(
        f"{PREFIX}/templates", headers={"Authorization": f"Bearer {token}"}
    )
    assert failing.status_code == 502, failing.text
    assert dps_proxy_module._dps_consecutive_failures == 1

    client.fake.fail_with = None  # type: ignore[attr-defined]
    client.fake.set_responses([_ok_response()])  # type: ignore[attr-defined]
    recovered = client.get(
        f"{PREFIX}/templates", headers={"Authorization": f"Bearer {token}"}
    )
    assert recovered.status_code == 200, recovered.text
    assert dps_proxy_module._dps_consecutive_failures == 0


def test_v1410_422_dict_detail_normalization(client: TestClient) -> None:
    """上游 422 {detail:{code,message}} → 从 detail 提取 code/message（dict 分支）."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(422, {"detail": {"code": "BIZ_4220", "message": "字段校验失败"}}),
    ])
    resp = client.get(
        f"{PREFIX}/templates/tpl-1", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == "BIZ_4220"
    assert body["message"] == "字段校验失败"


def test_v1410_422_dict_detail_error_alias_and_message_fallback(client: TestClient) -> None:
    """上游 422 {message, detail:{error}} → code 取 detail.error，message 保留顶层值."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(422, {"message": "请求体校验失败", "detail": {"error": "PARAM_INVALID"}}),
    ])
    resp = client.post(
        f"{PREFIX}/templates",
        json={"code": "tpl-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == "PARAM_INVALID"
    assert body["message"] == "请求体校验失败"


def test_v1410_422_list_detail_normalization(client: TestClient) -> None:
    """上游 422 {detail:[{msg},...]} → message 合并各 msg（list 分支）."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(
            422,
            {
                "detail": [
                    {"loc": ["body", "code"], "msg": "field required"},
                    {"loc": ["body", "name"], "msg": "字符串过短"},
                ]
            },
        ),
    ])
    resp = client.post(
        f"{PREFIX}/templates",
        json={"code": "tpl-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == 422  # 无顶层 code → 兜底 HTTP 状态码
    assert body["message"] == "field required; 字符串过短"


def test_v1410_422_list_detail_without_msg_uses_fallback(client: TestClient) -> None:
    """上游 422 {detail:[...]} 无有效 msg → message 兜底 'upstream error'（list 空集分支）."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        FakeResponse(422, {"detail": [{"loc": ["body"]}, "not-a-dict"]}),
    ])
    resp = client.post(
        f"{PREFIX}/templates",
        json={"code": "tpl-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == 422
    assert body["message"] == "upstream error"


def test_v1410_error_non_json_body_raw_fallback(client: TestClient) -> None:
    """上游非 2xx 且响应体非 JSON → raw 截断兜底，code=HTTP 状态码."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[attr-defined]
        _NonJsonResponse(500, "<html>bad gateway</html>"),
    ])
    resp = client.get(
        f"{PREFIX}/templates", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 500, resp.text
    body = resp.json()
    assert body["code"] == 500
    assert body["message"] == "upstream error"


def test_v1410_error_non_dict_json_payload_falls_back(client: TestClient) -> None:
    """上游非 2xx 且 JSON 体为数组（非 dict）→ code=HTTP 状态码，message 兜底."""
    token = _token_with_identity()
    client.fake.set_responses([  # type: ignore[arg-type, attr-defined]
        FakeResponse(502, ["unexpected"]),
    ])
    resp = client.get(
        f"{PREFIX}/templates", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 502, resp.text
    body = resp.json()
    assert body["code"] == 502
    assert body["message"] == "upstream error"


@pytest.mark.parametrize(
    ("method", "path", "upstream_path", "body"),
    [
        ("POST", "/tags/categories", "/api/v2/tags/categories", {"name": "消费"}),
        ("PUT", "/tags/categories/c1", "/api/v2/tags/categories/c1", {"name": "消费v2"}),
        ("DELETE", "/tags/categories/c1", "/api/v2/tags/categories/c1", None),
    ],
    ids=["tags-category-create", "tags-category-update", "tags-category-delete"],
)
def test_v1410_existing_tag_category_write_routes_forward(
    client: TestClient, method: str, path: str, upstream_path: str, body: dict | None
) -> None:
    """既有标签分类写路由（POST／PUT／DELETE）转发保真（回归，v1.4.10 行为不变）."""
    token = _token_with_identity()
    client.fake.set_responses([_ok_response()])  # type: ignore[attr-defined]
    resp = client.request(
        method,
        f"{PREFIX}{path}",
        json=body if body is not None else None,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    call = client.fake.request_calls[0]  # type: ignore[attr-defined]
    assert call["method"] == method
    assert call["url"] == f"{UPSTREAM_BASE}{upstream_path}"
    assert call["json"] == body


def test_v1410_parse_map_json_empty_and_invalid_returns_empty_table() -> None:
    """dps 值映射 JSON：空串／非法 JSON／非 dict 均回落空表（不抛错），合法 dict 原样返回."""
    assert dps_proxy_module._parse_map_json("") == {}
    assert dps_proxy_module._parse_map_json("{not-json}") == {}
    assert dps_proxy_module._parse_map_json("[1, 2, 3]") == {}
    assert dps_proxy_module._parse_map_json('{"a": "b"}') == {"a": "b"}
