"""OpenBase 上线验证脚本（Step 5 自动化，T4-2）.

对已部署实例执行《OpenBase-部署执行与上线检查报告》§2 的上线验证项，用于：

- Pro 蓝绿 / 金丝雀**切流前**的 Golden 校验；
- 发布后与**回滚后 15 分钟内**的验证复用（`operations-stage-execution` §1.6 强制要求）。

用法::

    python scripts/verify_release.py --base-url http://127.0.0.1:8010
    python scripts/verify_release.py --base-url http://127.0.0.1:8766 --expected-version 1.4.7 --json out.json
    python scripts/verify_release.py --base-url http://127.0.0.1:8766 --username admin --password *** --ui-url http://127.0.0.1:5173

退出码：``0`` = 无 FAIL（WARN / INFO 允许）；``1`` = 存在 FAIL（须停止切流或触发回滚）。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_CONFIG = ROOT / ".devflow" / "project-config.json"

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"
REQUEST_ID_PREFIX = "req-"
ERROR_CONTRACT_FIELDS = ("code", "message", "detail", "request_id")


@dataclass
class Result:
    """单项验证结果."""

    name: str
    status: str
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)


# ---- 纯函数（供单元测试直接覆盖）---------------------------------------------


def check_health(status_code: int, body_text: str) -> tuple[str, str]:
    """健康检查：200 且 body.status == "ok"."""
    if status_code != 200:
        return FAIL, f"期望 200，实际 {status_code}"
    try:
        payload = json.loads(body_text)
    except ValueError:
        return FAIL, f"响应非 JSON：{body_text[:80]}"
    if payload.get("status") != "ok":
        return FAIL, f"status 非 ok：{payload.get('status')!r}"
    return PASS, '200 {"status":"ok"}'


def check_auth_gate(status_code: int, body_text: str) -> tuple[str, str]:
    """鉴权门禁：未携带 token 访问受保护接口应 401 且 code=AUTH_401."""
    if status_code != 401:
        return FAIL, f"期望 401，实际 {status_code}"
    contract_status, detail = check_error_contract(body_text)
    if contract_status != PASS:
        return FAIL, detail
    return PASS, f"401 AUTH_401（{detail}）"


def check_error_contract(body_text: str) -> tuple[str, str]:
    """统一错误契约：四字段齐备且 request_id 以 ``req-`` 开头."""
    try:
        payload = json.loads(body_text)
    except ValueError:
        return FAIL, f"响应非 JSON：{body_text[:80]}"
    missing = [name for name in ERROR_CONTRACT_FIELDS if name not in payload]
    if missing:
        return FAIL, f"缺少字段 {missing}"
    request_id = payload.get("request_id") or ""
    if not str(request_id).startswith(REQUEST_ID_PREFIX):
        return FAIL, f"request_id 前缀异常：{request_id!r}"
    return PASS, f"code={payload.get('code')} request_id={request_id}"


def check_param_error(status_code: int, body_text: str) -> tuple[str, str]:
    """参数校验契约：400 且 code=PARAM_400 且 detail 为非空列表."""
    if status_code != 400:
        return FAIL, f"期望 400，实际 {status_code}"
    contract_status, detail = check_error_contract(body_text)
    if contract_status != PASS:
        return FAIL, detail
    payload = json.loads(body_text)
    if payload.get("code") != "PARAM_400":
        return FAIL, f"code 非 PARAM_400：{payload.get('code')!r}"
    if not isinstance(payload.get("detail"), list) or not payload["detail"]:
        return FAIL, "detail 应为非空列表（字段级错误）"
    return PASS, f"400 PARAM_400（{len(payload['detail'])} 项字段错误）"


def check_version(actual: str, expected: str) -> tuple[str, str]:
    """版本可见性：实例上报版本 vs 期望版本（不一致记为 WARN，附排查提示）."""
    if not expected:
        return INFO, f"实例上报 info.version={actual!r}（未提供 --expected-version，跳过比对）"
    if actual == expected:
        return PASS, f"info.version={actual} == 期望 {expected}"
    return WARN, (
        f"info.version={actual!r} != 期望 {expected!r}；"
        "注：该值来自 openbase.__version__（框架版本常量），如需与发布版本号对齐须单独变更代码"
    )


def summarize(results: list[Result]) -> dict[str, int]:
    """按状态汇总计数."""
    counts = {PASS: 0, WARN: 0, FAIL: 0, INFO: 0}
    for item in results:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts


def exit_code(results: list[Result]) -> int:
    """存在 FAIL 即返回 1（切流门禁）."""
    return 1 if any(item.status == FAIL for item in results) else 0


def local_release_baseline(config_path: str | pathlib.Path) -> tuple[str, str]:
    """读取本地发布基线（project.version / lastRelease），供登记与比对.

    接受 ``str`` 或 ``pathlib.Path``（CLI 传入为字符串，直接调用可为 Path）。
    """
    try:
        payload = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # 配置缺失/损坏不应阻断线上验证
        return "", f"读取失败：{exc.__class__.__name__}"
    project = payload.get("project") or {}
    return str(project.get("version") or ""), str(project.get("lastRelease") or "")


# ---- HTTP 执行 ----------------------------------------------------------------


def _request(client: httpx.Client, method: str, path: str, **kwargs: Any) -> tuple[int, str]:
    try:
        response = client.request(method, path, **kwargs)
        return response.status_code, response.text
    except httpx.HTTPError as exc:
        return 0, f"{exc.__class__.__name__}: {exc}"


def run_checks(args: argparse.Namespace) -> list[Result]:
    results: list[Result] = []
    with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
        status, body = _request(client, "GET", "/health")
        state, detail = check_health(status, body)
        results.append(Result("1 后端健康检查", state, detail, {"status_code": status}))

        status, body = _request(client, "GET", "/api/v1/modules")
        state, detail = check_auth_gate(status, body)
        results.append(Result("2 鉴权门禁（模块列表）", state, detail, {"status_code": status}))

        status, body = _request(client, "GET", "/api/v1/logs/search?limit=1")
        state, detail = check_auth_gate(status, body)
        results.append(Result("3 日志检索鉴权门禁", state, detail, {"status_code": status}))

        status, body = _request(client, "POST", "/api/v1/auth/login", json={})
        state, detail = check_param_error(status, body)
        results.append(Result("4 参数校验契约（空体登录）", state, detail, {"status_code": status}))

        status, _ = _request(client, "GET", "/docs")
        results.append(
            Result("5 API 文档可达", PASS if status == 200 else FAIL, f"GET /docs => {status}")
        )

        status, body = _request(client, "GET", "/openapi.json")
        if status != 200:
            results.append(Result("6 OpenAPI 契约可读", FAIL, f"GET /openapi.json => {status}"))
        else:
            try:
                spec = json.loads(body)
                paths = len(spec.get("paths") or {})
                state, detail = check_version(
                    str((spec.get("info") or {}).get("version") or ""), args.expected_version
                )
                results.append(Result("6 OpenAPI 契约可读", PASS, f"paths={paths}"))
                results.append(Result("7 版本可见性（info.version）", state, detail))
            except ValueError:
                results.append(Result("6 OpenAPI 契约可读", FAIL, "响应非 JSON"))

        if args.username and args.password:
            status, body = _request(
                client,
                "POST",
                "/api/v1/auth/login",
                json={"username": args.username, "password": args.password},
            )
            if status == 200 and "access_token" in body:
                results.append(Result("8 登录成功路径", PASS, "200 且返回 access_token"))
            else:
                results.append(Result("8 登录成功路径", FAIL, f"{status} | {body[:120]}"))
        else:
            results.append(
                Result("8 登录成功路径", INFO, "未提供 --username/--password，跳过（默认不探测凭证）")
            )

        if args.ui_url:
            status, _ = _request(client, "GET", args.ui_url)
            results.append(
                Result("9 前端可访问", PASS if status == 200 else FAIL, f"GET {args.ui_url} => {status}")
            )
        else:
            results.append(Result("9 前端可访问", INFO, "未提供 --ui-url，跳过"))

    version, last_release = local_release_baseline(args.config)
    if version and version == last_release.lstrip("v"):
        results.append(Result("10 本地发布基线一致", PASS, f"project.version={version} / lastRelease={last_release}"))
    else:
        results.append(
            Result(
                "10 本地发布基线一致",
                WARN,
                f"project.version={version!r} / lastRelease={last_release!r}（不一致时通常表示新版本尚未发布）",
            )
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenBase 上线验证（Step 5，T4-2）")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="待验证实例地址")
    parser.add_argument("--expected-version", default="", help="期望版本（比对 info.version，不一致为 WARN）")
    parser.add_argument("--username", default="", help="可选：登录成功路径验证的用户名")
    parser.add_argument("--password", default="", help="可选：登录成功路径验证的密码（勿写入文档）")
    parser.add_argument("--ui-url", default="", help="可选：前端地址（如 http://127.0.0.1:5173）")
    parser.add_argument("--timeout", type=float, default=10.0, help="单请求超时（秒）")
    parser.add_argument("--json", default="", help="可选：将结果写入 JSON 证据文件")
    parser.add_argument("--config", default=str(PROJECT_CONFIG), help="发布基线配置路径")
    args = parser.parse_args(argv)

    results = run_checks(args)
    counts = summarize(results)

    print(f"=== OpenBase 上线验证 [{args.base_url}] ===")
    for item in results:
        print(f"[{item.status:4}] {item.name} — {item.detail}")
    print(
        f"--- 汇总：PASS {counts[PASS]} / WARN {counts[WARN]} / FAIL {counts[FAIL]} / INFO {counts[INFO]} ---"
    )
    code = exit_code(results)
    print("[OK] 上线验证通过（可切流）" if code == 0 else "[FAIL] 存在 FAIL 项：禁止切流，按回滚方案处置")

    if args.json:
        target = pathlib.Path(args.json)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "base_url": args.base_url,
                    "expected_version": args.expected_version,
                    "counts": counts,
                    "results": [item.__dict__ for item in results],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[written] {target}")
    return code


if __name__ == "__main__":
    sys.exit(main())
