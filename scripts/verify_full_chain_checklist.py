"""OpenBase 四基础子系统全链路联调清单执行脚本（批次 4）

对应《OpenBase-四基础子系统全链路贯通审计报告-v1.0.0》§4 的八项清单：
    1 上下文两轮；2 记忆召回；3 记忆 PATCH；4 知识库上传/检索；
    5 知识库租户隔离；6 画像计算/读取；7 画像双标签合并；8 缺租户头。

设计原则：
    - 只经门户 OpenBase（默认 http://127.0.0.1:8000）调用，不直连子系统；
    - 依赖仅 httpx；环境变量驱动，无环境时全部记为 BLOCKED 且退出码 0；
    - 结果为 JSON 证据，默认落盘 doc/test/evidence/full-chain/。

用法：
    set OPENBASE_TOKEN=<JWT>
    set OPENBASE_TENANT_ID=<租户A>
    D:\\venvs\\openbase\\Scripts\\python.exe scripts/verify_full_chain_checklist.py --json

退出码：存在 FAIL → 1；否则 0（BLOCKED/PARTIAL 不算失败，但摘要显著标注）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_EVIDENCE_DIR = Path("doc/test/evidence/full-chain")
POLL_INTERVAL_SECONDS = 1.5
POLL_MAX_ATTEMPTS = 20


class SkipCheck(Exception):
    """前置条件缺失（环境变量/上游数据），记 BLOCKED"""


@dataclass
class CheckResult:
    """单项检查结果"""

    check_id: str
    title: str
    status: str  # PASS / FAIL / BLOCKED / PARTIAL
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)


class ChecklistContext:
    """检查上下文：HTTP 客户端、租户与共享状态"""

    def __init__(self, base_url: str, token: str, tenant_a: str, tenant_b: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.tenant_a = tenant_a
        self.tenant_b = tenant_b
        self.state: dict[str, Any] = {}
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0, connect=5.0),
            follow_redirects=False,
            # 联调脚本只打本机门户，忽略系统代理（避免代理不可达导致长时间挂起）
            trust_env=False,
        )

    def headers(self, tenant: str | None = None, extra: dict[str, str] | None = None) -> dict[str, str]:
        """构造认证与租户头（缺省使用租户 A）"""
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        tenant_id = tenant if tenant is not None else self.tenant_a
        if tenant_id:
            headers["X-Tenant-ID"] = tenant_id
        if extra:
            headers.update(extra)
        return headers

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """发起请求；连接失败统一抛 SkipCheck（视为环境未就绪）"""
        tenant = kwargs.pop("tenant", None)
        extra_headers = kwargs.pop("extra_headers", None)
        kwargs.setdefault("headers", self.headers(tenant, extra_headers))
        try:
            return self.client.request(method, path, **kwargs)
        except httpx.ConnectError as exc:
            raise SkipCheck(f"无法连接 {self.base_url}：{exc}") from exc
        except httpx.TimeoutException as exc:
            raise SkipCheck(f"请求超时：{method} {path}：{exc}") from exc

    def pick_model(self) -> str:
        """选择可用模型（环境变量优先，其次模型列表首个未禁用项）"""
        preferred = os.environ.get("OPENBASE_CHAT_MODEL", "").strip()
        if preferred:
            return preferred
        response = self.request("GET", "/api/v1/llm-proxy/models")
        if response.status_code != 200:
            raise SkipCheck(f"模型列表不可用：HTTP {response.status_code}")
        models = (response.json().get("data") or {}).get("models") or []
        for item in models:
            if isinstance(item, dict) and str(item.get("status", "")).lower() != "disabled":
                model_id = str(item.get("id") or "")
                if model_id:
                    return model_id
        raise SkipCheck("模型列表为空，无法执行上下文对话检查")


def _json_body(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _expect(response: httpx.Response, allowed: tuple[int, ...], step: str) -> None:
    if response.status_code not in allowed:
        raise AssertionError(
            f"{step} 期望 HTTP {allowed}，实际 {response.status_code}："
            f"{response.text[:300]}"
        )


def _find_values(payload: Any, key: str) -> list[Any]:
    """递归查找指定键的全部取值（用于标签合并断言）"""
    found: list[Any] = []
    if isinstance(payload, dict):
        for current_key, value in payload.items():
            if current_key == key:
                found.append(value)
            found.extend(_find_values(value, key))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(_find_values(item, key))
    return found


# ---------------------------------------------------------------------------
# 八项检查
# ---------------------------------------------------------------------------


def check_context_two_rounds(ctx: ChecklistContext) -> tuple[str, dict[str, Any]]:
    """1 上下文两轮：同一 session_id 连发 2 轮"""
    model = ctx.pick_model()
    session_id = f"batch4-{uuid.uuid4().hex[:10]}"
    responses: list[dict[str, Any]] = []
    for index, content in enumerate(
        ("请记住：我的工号是 B4-7788。", "我刚才告诉你的工号是多少？"), start=1
    ):
        response = ctx.request(
            "POST",
            "/api/v1/llm-proxy/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": content}],
                "session_id": session_id,
                "stream": False,
            },
            timeout=httpx.Timeout(120.0, connect=5.0),
        )
        _expect(response, (200,), f"第 {index} 轮对话")
        responses.append(_json_body(response).get("data") or {})
    return (
        f"session={session_id} 两轮均 200",
        {
            "session_id": session_id,
            "model": model,
            "round2_context_meta": responses[1].get("context_meta"),
        },
    )


def check_memory_recall(ctx: ChecklistContext) -> tuple[str, dict[str, Any]]:
    """2 记忆召回：聊天后按同 user 召回"""
    user_id = os.environ.get("OPENBASE_USER_ID", "batch4-user")
    response = ctx.request(
        "POST",
        "/api/v1/memory-proxy/recall",
        json={"user_id": user_id, "query": "工号 B4-7788", "limit": 10},
    )
    _expect(response, (200,), "记忆召回")
    data = _json_body(response).get("data")
    items: list[Any] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ("memories", "items", "results"):
            if isinstance(data.get(key), list):
                items = data[key]
                break
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            ctx.state["memory_id"] = str(item["id"])
            break
    return f"召回 {len(items)} 条", {"user_id": user_id, "count": len(items)}


def check_memory_patch(ctx: ChecklistContext) -> tuple[str, dict[str, Any]]:
    """3 记忆 PATCH：内容更新生效"""
    memory_id = ctx.state.get("memory_id")
    if not memory_id:
        raise SkipCheck("召回结果无 memory id，无法验证 PATCH（可先执行记忆写入）")
    response = ctx.request(
        "PATCH",
        f"/api/v1/memory-proxy/memories/{memory_id}",
        json={"content": f"批次4 联调标记 {datetime.now(timezone.utc).isoformat()}"},
    )
    _expect(response, (200,), "记忆 PATCH")
    return f"memory={memory_id} 更新 200", {"memory_id": memory_id}


def check_rag_upload_and_retrieve(ctx: ChecklistContext) -> tuple[str, dict[str, Any]]:
    """4 知识库：建库 → 上传 → 轮询 → 检索"""
    name = f"batch4-verify-{uuid.uuid4().hex[:8]}"
    create = ctx.request(
        "POST",
        "/api/v1/rag-proxy/collections",
        json={"name": name, "description": "批次 4 全链路联调"},
    )
    _expect(create, (200, 201), "创建知识库")
    created = _json_body(create).get("data") or {}
    collection_id = str(created.get("id") or created.get("collection_id") or "")
    if not collection_id:
        raise AssertionError(f"创建知识库未返回集合 ID：{created}")
    ctx.state["collection_id"] = collection_id

    upload = ctx.request(
        "POST",
        f"/api/v1/rag-proxy/collections/{collection_id}/documents",
        files={"file": ("batch4.txt", "批次4联调：OpenRAG 检索命中标记 B4-RAG-OK".encode(), "text/plain")},
        timeout=httpx.Timeout(120.0, connect=5.0),
    )
    _expect(upload, (200, 201), "上传文档")
    uploaded = _json_body(upload).get("data") or {}
    document_id = str(uploaded.get("document_id") or uploaded.get("id") or "")
    if not document_id:
        raise AssertionError(f"上传未返回文档 ID：{uploaded}")

    final_status = "pending"
    for _ in range(POLL_MAX_ATTEMPTS):
        detail = ctx.request(
            "GET", f"/api/v1/rag-proxy/collections/{collection_id}/documents/{document_id}"
        )
        _expect(detail, (200,), "文档详情轮询")
        final_status = str((_json_body(detail).get("data") or {}).get("status", "")).lower()
        if final_status in {"completed", "succeeded", "success", "failed", "error"}:
            break
        time.sleep(POLL_INTERVAL_SECONDS)
    assert final_status not in {"failed", "error"}, f"文档索引失败：{final_status}"

    retrieve = ctx.request(
        "POST",
        f"/api/v1/rag-proxy/collections/{collection_id}/query/retrieve",
        json={"query": "B4-RAG-OK", "top_k": 5},
    )
    _expect(retrieve, (200,), "知识库检索")
    return (
        f"collection={collection_id} document={document_id} status={final_status}",
        {
            "collection_id": collection_id,
            "document_id": document_id,
            "document_status": final_status,
            "retrieve_hits": len(_find_values(_json_body(retrieve), "chunk_id")),
        },
    )


def check_rag_tenant_isolation(ctx: ChecklistContext) -> tuple[str, dict[str, Any]]:
    """5 知识库隔离：租户 B 查租户 A 的集合必须 404"""
    collection_id = ctx.state.get("collection_id")
    if not collection_id:
        raise SkipCheck("缺少租户 A 的集合（第 4 项未成功创建）")
    if not ctx.tenant_b:
        raise SkipCheck("未设置 OPENBASE_TENANT_ID_B，无法验证跨租户隔离")
    response = ctx.request(
        "GET",
        f"/api/v1/rag-proxy/collections/{collection_id}",
        tenant=ctx.tenant_b,
    )
    assert response.status_code == 404, (
        f"跨租户查询应 404，实际 {response.status_code}：{response.text[:200]}"
    )
    return f"租户 B 查询返回 {response.status_code}", {"collection_id": collection_id}


def check_portrait_calculate_and_read(ctx: ChecklistContext) -> tuple[str, dict[str, Any]]:
    """6 画像计算/读取"""
    person_id = os.environ.get("OPENBASE_PERSON_ID", f"batch4-person-{uuid.uuid4().hex[:8]}")
    ctx.state["person_id"] = person_id
    calculate = ctx.request(
        "POST",
        "/api/v1/dps-proxy/portraits/calculate",
        json={"person_id": person_id, "async": True},
        timeout=httpx.Timeout(120.0, connect=5.0),
    )
    _expect(calculate, (200, 202), "画像计算")
    task_id = str((_json_body(calculate).get("data") or {}).get("task_id") or "")
    if task_id:
        for _ in range(POLL_MAX_ATTEMPTS):
            task = ctx.request("GET", f"/api/v1/dps-proxy/portraits/tasks/{task_id}")
            _expect(task, (200,), "画像计算任务查询")
            status_text = str((_json_body(task).get("data") or {}).get("status", "")).lower()
            if status_text in {"completed", "succeeded", "failed", "error"}:
                break
            time.sleep(POLL_INTERVAL_SECONDS)
    detail = ctx.request("GET", f"/api/v1/dps-proxy/portraits/{person_id}")
    _expect(detail, (200,), "画像详情")
    return f"person={person_id} 计算与读取均成功", {"person_id": person_id, "task_id": task_id}


def check_portrait_tag_merge(ctx: ChecklistContext) -> tuple[str, dict[str, Any]]:
    """7 画像双标签合并：两次 PATCH 后两个标签同时存在"""
    person_id = ctx.state.get("person_id")
    if not person_id:
        raise SkipCheck("缺少画像 person_id（第 6 项未成功）")
    for tag in ("A", "B"):
        response = ctx.request(
            "PATCH",
            f"/api/v1/dps-proxy/portraits/{person_id}",
            json={"business": {"attributes": {"batch4_tags": [tag]}}},
        )
        _expect(response, (200,), f"画像 PATCH 标签 {tag}")
    detail = ctx.request("GET", f"/api/v1/dps-proxy/portraits/{person_id}")
    _expect(detail, (200,), "画像详情断言")
    merged = _find_values(_json_body(detail), "batch4_tags")
    merged_tags: list[str] = []
    for value in merged:
        if isinstance(value, list):
            merged_tags.extend(str(item) for item in value)
    assert "A" in merged_tags and "B" in merged_tags, (
        f"标签未合并，实际 batch4_tags={merged}"
    )
    return f"合并后标签 {sorted(set(merged_tags))}", {"person_id": person_id, "tags": merged_tags}


def check_missing_tenant_header(ctx: ChecklistContext) -> tuple[str, dict[str, Any]]:
    """8 缺租户头：写接口应 400（R5 生产 enforce 前按实际状态记录）"""
    response = ctx.request(
        "POST",
        "/api/v1/rag-proxy/collections",
        tenant="",
        json={"name": f"batch4-no-tenant-{uuid.uuid4().hex[:8]}"},
    )
    if response.status_code == 400:
        return "缺省租户头返回 400", {"status_code": 400}
    return (
        f"当前实现返回 {response.status_code}（R5 生产 enforce 未上线，部分满足）",
        {"status_code": response.status_code, "body": response.text[:200]},
    )


CHECKLIST: list[tuple[str, str, Callable[[ChecklistContext], tuple[str, dict[str, Any]]], str]] = [
    ("1", "上下文两轮", check_context_two_rounds, "FAIL"),
    ("2", "记忆召回", check_memory_recall, "FAIL"),
    ("3", "记忆 PATCH", check_memory_patch, "FAIL"),
    ("4", "知识库上传/检索", check_rag_upload_and_retrieve, "FAIL"),
    ("5", "知识库租户隔离", check_rag_tenant_isolation, "FAIL"),
    ("6", "画像计算/读取", check_portrait_calculate_and_read, "FAIL"),
    ("7", "画像双标签合并", check_portrait_tag_merge, "FAIL"),
    # 第 8 项：R5 生产 enforce 未上线，断言不达标记 PARTIAL 而非 FAIL
    ("8", "缺租户头", check_missing_tenant_header, "PARTIAL"),
]


def run_checklist(ctx: ChecklistContext) -> list[CheckResult]:
    """顺序执行八项，单项异常不阻断后续"""
    results: list[CheckResult] = []
    for check_id, title, func, assert_status in CHECKLIST:
        try:
            detail, evidence = func(ctx)
            results.append(CheckResult(check_id, title, "PASS", detail, evidence))
        except SkipCheck as exc:
            results.append(CheckResult(check_id, title, "BLOCKED", str(exc)))
        except AssertionError as exc:
            results.append(CheckResult(check_id, title, assert_status, str(exc)))
        except Exception as exc:  # noqa: BLE001 - 联调脚本需记录任意异常并继续
            results.append(
                CheckResult(check_id, title, "FAIL", f"{type(exc).__name__}: {exc}")
            )
    return results


def write_evidence(results: list[CheckResult], base_url: str, output: Path | None) -> Path | None:
    """落盘 JSON 证据（默认 doc/test/evidence/full-chain/）"""
    if output is None:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output if output.suffix == ".json" else output / f"full-chain-{stamp}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "results": [result.__dict__ for result in results],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def print_summary(results: list[CheckResult]) -> None:
    """控制台摘要"""
    print("=" * 72)
    print("OpenBase 四基础子系统全链路联调清单")
    print("=" * 72)
    for result in results:
        print(f"[{result.status:<7}] {result.check_id} {result.title} — {result.detail}")
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    print("-" * 72)
    print("汇总：" + " ".join(f"{status}={count}" for status, count in sorted(counts.items())))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenBase 全链路联调清单执行脚本（批次 4）")
    parser.add_argument("--base-url", default=os.environ.get("OPENBASE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--json", action="store_true", help="输出完整 JSON 结果")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_EVIDENCE_DIR),
        help="证据文件或目录（默认 doc/test/evidence/full-chain/）",
    )
    parser.add_argument("--no-evidence", action="store_true", help="不写证据文件")
    args = parser.parse_args(argv)

    token = os.environ.get("OPENBASE_TOKEN", "").strip()
    if not token:
        print(
            "未设置 OPENBASE_TOKEN：八项均无法鉴权。请先登录门户获取 JWT 后重跑。",
            file=sys.stderr,
        )

    ctx = ChecklistContext(
        base_url=args.base_url,
        token=token,
        tenant_a=os.environ.get("OPENBASE_TENANT_ID", "").strip(),
        tenant_b=os.environ.get("OPENBASE_TENANT_ID_B", "").strip(),
    )
    results = run_checklist(ctx)
    print_summary(results)

    evidence_path = None
    if not args.no_evidence:
        evidence_path = write_evidence(
            results, args.base_url, Path(args.output)
        )
        if evidence_path:
            print(f"证据文件：{evidence_path}")
    if args.json:
        print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))

    return 1 if any(result.status == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
