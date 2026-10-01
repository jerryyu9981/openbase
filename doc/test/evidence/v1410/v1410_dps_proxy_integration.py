"""OpenBase v1.4.10 Step 4 dps-proxy 真实上游集成检查客户端。

前置：OpenBase 服务已在 ``127.0.0.1:8000`` 运行（见 ``v1410_openbase_server.py``），
且真实 DPS v2.12.0 在 ``127.0.0.1:8030`` 健康。

本脚本经 OpenBase 网关前缀 ``/api/v1/dps-proxy/*`` 对真实 DPS 上游发起请求，
逐条记录 HTTP 状态码与响应片段，落盘 JSON（机读）与 TXT（人读）证据。

运行：``python doc/test/evidence/v1410/v1410_dps_proxy_integration.py``
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8000"
PREFIX = "/api/v1/dps-proxy"

# 联调身份：sub=1（DPS 种子绑定 1:super_admin）；tenant-1 经 ORG/TENANT_MAP 映射为
# dps-org-001 / dps-tenant-001（DPS 双形态可解析）。
TOKEN_KWARGS = {
    "subject": "1",
    "username": "admin",
    "tenant_id": "tenant-1",
    "tenant_code": "tenant-1",
    "extra": {"org_id": "tenant-1", "role": "super_admin"},
}

# (组, 方法, 本仓路径, 说明, 上游预期目标)
CASES: list[tuple[str, str, str, str, str]] = [
    ("既有12", "GET", "/health", "上游健康透传", "/health/liveness"),
    ("既有12", "GET", "/portraits?page=1&page_size=20", "画像列表", "/api/v2/portrait/list"),
    ("既有12", "GET", "/portraits/61", "画像详情", "/api/v2/portrait/61"),
    ("既有12", "GET", "/tags/categories", "标签分类列表", "/api/v2/tags/categories"),
    ("既有12", "GET", "/reports/overview", "报表概览", "/api/v2/reports/overview"),
    ("既有12", "GET", "/audit/logs?page=1&page_size=5", "审计日志", "/api/v2/audit/logs"),
    ("既有12", "GET", "/batch/tasks/nonexistent-task", "批量任务状态", "/api/v2/batch/import/nonexistent-task/status"),
    ("v1.4.10", "GET", "/templates", "画像模板列表", "/api/v2/portrait/templates"),
    ("v1.4.10", "GET", "/templates/nonexistent/diff?target_version=1", "模板版本对比", "/api/v2/portrait/templates/nonexistent/diff"),
    ("v1.4.10", "GET", "/templates/nonexistent/preflight", "模板预检", "/api/v2/portrait/templates/nonexistent/preflight"),
    ("v1.4.10", "GET", "/lineage/impact?template_code=nonexistent", "影响面", "/api/v2/portrait/lineage/impact"),
    ("v1.4.10", "GET", "/lineage/tags/nonexistent", "标签血缘反查", "/api/v2/portrait/lineage/tags/nonexistent"),
    ("v1.4.10", "GET", "/measures/suggest?person_id=61", "措施建议", "/api/v2/portrait/measures/suggest"),
    ("v1.4.10", "GET", "/scoring-types?page=1&page_size=20", "评分类型", "/api/v2/portrait/scoring-types"),
    ("v1.4.10", "GET", "/annotation-templates", "标注模板列表", "/api/v2/portrait/annotation-templates"),
    ("v1.4.10", "GET", "/labels?action=list", "标签列表", "/api/v2/portrait/labels"),
]


def _mint_token() -> str:
    from openbase.modules.auth.jwt import create_access_token

    return create_access_token(**TOKEN_KWARGS)


def _snippet(text: str, limit: int = 400) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


def main() -> int:
    token = _mint_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    results: list[dict] = []
    started = datetime.now(timezone.utc)

    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        # 0) 认证门禁负例：无 token → 401
        try:
            r = client.get(f"{PREFIX}/templates")
            results.append({
                "group": "门禁",
                "case": "无 token 访问新增端点",
                "method": "GET",
                "path": f"{PREFIX}/templates",
                "upstream": "/api/v2/portrait/templates",
                "status": r.status_code,
                "snippet": _snippet(r.text),
                "verdict": "PASS" if r.status_code == 401 else "FAIL",
            })
        except httpx.HTTPError as exc:
            results.append({
                "group": "门禁", "case": "无 token 访问新增端点", "method": "GET",
                "path": f"{PREFIX}/templates", "upstream": "-", "status": None,
                "snippet": f"transport error: {exc}", "verdict": "ERROR",
            })

        # 1) 正常上游透传用例
        for group, method, path, desc, upstream in CASES:
            try:
                r = client.request(method, f"{PREFIX}{path}", headers=auth_headers)
                results.append({
                    "group": group, "case": desc, "method": method,
                    "path": f"{PREFIX}{path}", "upstream": upstream,
                    "status": r.status_code, "snippet": _snippet(r.text),
                    "verdict": "OBSERVED",
                })
            except httpx.HTTPError as exc:
                results.append({
                    "group": group, "case": desc, "method": method,
                    "path": f"{PREFIX}{path}", "upstream": upstream, "status": None,
                    "snippet": f"transport error: {exc}", "verdict": "ERROR",
                })

    finished = datetime.now(timezone.utc)

    payload = {
        "generated_at": finished.isoformat(),
        "started_at": started.isoformat(),
        "openbase_base": BASE,
        "dps_upstream": "http://127.0.0.1:8030",
        "token_identity": {
            "sub": TOKEN_KWARGS["subject"],
            "tenant_id": TOKEN_KWARGS["tenant_id"],
            "org_id": TOKEN_KWARGS["extra"]["org_id"],
            "role": TOKEN_KWARGS["extra"]["role"],
        },
        "results": results,
    }

    stamp = finished.strftime("%Y%m%d-%H%M%S")
    json_path = OUT_DIR / f"dps-proxy-integration-{stamp}.json"
    txt_path = OUT_DIR / f"dps-proxy-integration-{stamp}.txt"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# OpenBase dps-proxy 真实上游集成检查  {finished.isoformat()}",
        f"# OpenBase={BASE}  DPS=127.0.0.1:8030  sub={TOKEN_KWARGS['subject']} tenant={TOKEN_KWARGS['tenant_id']} role={TOKEN_KWARGS['extra']['role']}",
        "",
    ]
    for item in results:
        lines.append(
            f"[{item['verdict']}] {item['group']:<7} {item['method']:<6} {item['path']:<55} "
            f"-> {item['status']}  {item['snippet']}"
        )
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for item in results:
        print(f"[{item['verdict']}] {item['group']:<7} {item['method']:<6} {item['path']:<55} -> {item['status']}")
    print(f"\nJSON: {json_path}")
    print(f"TXT : {txt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
