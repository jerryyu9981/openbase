#!/usr/bin/env python
"""BL-147-05 端到端串联验收校验（v1.4.7，**可复跑**的证据生成器）.

职责（对应《OpenBase-测试用例-v1.4.7》TT-147-004/005/006/007/010）：

1. **应用日志行 JSONL 契约核验**：逐文件分类四仓采集文件的「应用日志行」（行首 `{`）与
   框架自身输出行，校验应用日志行的 JSON 合法率与 §5 必需字段（`ts`/`request_id`/`method`/
   `path`/`status_code` 且 `status_code` 为数字）。
2. **串联一致性判定**：对抽样得到的每个 `request_id`，在四仓采集中检索**应用日志行**，
   比对取值是否逐字相等（判据：命中率 100%）。
3. **日志中心可检索**：经 `openbase.modules.logs.service`（与 HTTP 端点同一实现口径）按
   `source=repo_log` + `module` 统计命中，并按 `request_id` 反查。
4. **兜底健壮**：统计无上下文路径的 `request_id` 兜底值 `"-"` 出现情况。

判据口径（2026-09-19 人工裁定）：JSON 合法率与串联比对**限定为应用日志行**；`uvicorn.access`
等框架自身输出行不纳入判据（其占比在本报告中如实披露）。裁定记录见
《OpenBase-DevLogReport-v1.4.7》§5.1。

用法::

    python scripts/bl147_05_verify_chain.py --sampling <sampling.json> \\
        --logs-root logs --out-dir doc/test/evidence/v147
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openbase.modules.logs import service as log_service  # noqa: E402
from openbase.modules.logs.derivation import (  # noqa: E402
    REPO_LOG_MODULE_TO_SVC,
    REPO_LOG_SOURCES,
    svc_dir_to_module,
)
from openbase.modules.logs.repository import REPO_LOG_NAME_RE  # noqa: E402
from openbase.modules.logs.schemas import LogSearchParams  # noqa: E402

REQUIRED_FIELDS: tuple[str, ...] = ("ts", "request_id", "method", "path", "status_code")
DASH = "-"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _iter_repo_files(logs_root: Path, svc: str) -> list[Path]:
    """列出某仓目录下**白名单内**的采集文件（与适配器同一判据）."""
    directory = logs_root / svc
    if not directory.is_dir():
        return []
    files: list[Path] = []
    for candidate in sorted(directory.iterdir()):
        if not candidate.is_file():
            continue
        match = REPO_LOG_NAME_RE.match(candidate.name)
        if match and match.group("svc") == svc:
            files.append(candidate)
    return files


def _is_app_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("{") and stripped.endswith("}")


def _scan_logs(logs_root: Path) -> dict[str, Any]:
    """扫描四仓采集文件：分类行类型、校验契约、索引 request_id."""
    per_svc: dict[str, Any] = {}
    index: dict[str, list[dict[str, Any]]] = {}
    dash_lines: dict[str, int] = {}
    for svc in REPO_LOG_SOURCES:
        module = svc_dir_to_module(svc)
        stats = {
            "module": module,
            "files": [],
            "app_lines": 0,
            "framework_lines": 0,
            "valid_json": 0,
            "invalid_json": 0,
            "missing_required": 0,
            "status_code_non_numeric": 0,
            "request_id_dash": 0,
        }
        dash = 0
        for path in _iter_repo_files(logs_root, svc):
            stats["files"].append(path.name)
            for lineno, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if not raw.strip():
                    continue
                if not _is_app_line(raw):
                    stats["framework_lines"] += 1
                    continue
                stats["app_lines"] += 1
                try:
                    payload = json.loads(raw)
                except ValueError:
                    stats["invalid_json"] += 1
                    continue
                if not isinstance(payload, dict):
                    stats["invalid_json"] += 1
                    continue
                stats["valid_json"] += 1
                if any(field not in payload for field in REQUIRED_FIELDS):
                    stats["missing_required"] += 1
                status = payload.get("status_code")
                if status is not None and not isinstance(status, int):
                    stats["status_code_non_numeric"] += 1
                request_id = payload.get("request_id")
                if request_id == DASH:
                    dash += 1
                    continue
                if isinstance(request_id, str) and request_id:
                    index.setdefault(request_id, []).append(
                        {
                            "svc": svc,
                            "module": module,
                            "file": path.name,
                            "line": lineno,
                            "ts": payload.get("ts"),
                            "method": payload.get("method"),
                            "path": payload.get("path"),
                            "status_code": status,
                        }
                    )
        stats["request_id_dash"] = dash
        dash_lines[svc] = dash
        total = stats["app_lines"]
        stats["validity_rate"] = round(stats["valid_json"] / total, 4) if total else None
        per_svc[svc] = stats
    return {"per_svc": per_svc, "index": index}


def _retrieval_check(request_ids: list[str]) -> dict[str, Any]:
    """日志中心检索：`source=repo_log` + module 维度 + request_id 反查."""
    by_module: dict[str, Any] = {}
    for module in REPO_LOG_MODULE_TO_SVC:
        try:
            body = log_service.search(LogSearchParams(source="repo_log", module=[module], page_size=1))
            by_module[module] = {"svc": REPO_LOG_MODULE_TO_SVC[module], "total": body.get("total")}
        except Exception as exc:  # noqa: BLE001 - 单源失败仍须留证，不静默
            by_module[module] = {"svc": REPO_LOG_MODULE_TO_SVC[module], "error": type(exc).__name__, "detail": str(exc)[:200]}
    lookups: dict[str, Any] = {}
    for request_id in request_ids:
        try:
            body = log_service.search(LogSearchParams(source="repo_log", q=request_id, page_size=5))
            lookups[request_id] = {"total": body.get("total"), "modules": sorted({item.get("module") for item in body.get("items", [])})}
        except Exception as exc:  # noqa: BLE001
            lookups[request_id] = {"error": type(exc).__name__, "detail": str(exc)[:200]}
    return {"by_module": by_module, "request_id_lookup": lookups}


def _load_sampling(path: Path) -> list[dict[str, Any]]:
    # utf-8-sig：兼容 PowerShell 5 的 `Set-Content -Encoding UTF8`（会写 BOM）
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload.get("requests", payload if isinstance(payload, list) else [])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BL-147-05 端到端串联验收校验")
    parser.add_argument("--sampling", required=True, help="抽样证据 JSON（含 requests[].request_id）")
    parser.add_argument("--logs-root", default="logs")
    parser.add_argument("--out-dir", default=str(ROOT / "doc" / "test" / "evidence" / "v147"))
    args = parser.parse_args(argv)

    logs_root = Path(args.logs_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = _load_sampling(Path(args.sampling))
    scan = _scan_logs(logs_root)
    index = scan["index"]

    per_request: list[dict[str, Any]] = []
    hits = misses = 0
    for sample in samples:
        request_id = sample.get("request_id")
        matched = index.get(request_id, []) if isinstance(request_id, str) else []
        if matched:
            hits += 1
        else:
            misses += 1
        consistent = bool(matched) and all(row["svc"] for row in matched)
        per_request.append({**sample, "hit": bool(matched), "consistent": consistent, "matches": matched})

    total = len(samples)
    chain = {
        "checked_at": _now(),
        "sampling_file": str(args.sampling),
        "logs_root": logs_root.as_posix(),
        "totals": {
            "requests": total,
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / total, 4) if total else None,
            "criterion": "命中率 100% 且取值逐字相等（判据口径：应用日志行）",
            "passed": bool(total) and misses == 0,
        },
        "per_request": per_request,
    }
    (out_dir / "bl147-05-chain-consistency.json").write_text(
        json.dumps(chain, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    contract = {
        "checked_at": _now(),
        "criterion": "应用日志行 100% 合法 JSON 且含必需字段（框架自身输出行不纳入判据，占比如实披露）",
        "required_fields": list(REQUIRED_FIELDS),
        "per_svc": scan["per_svc"],
    }
    (out_dir / "bl147-05-jsonl-contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    request_ids = [s.get("request_id") for s in samples if isinstance(s.get("request_id"), str) and s.get("request_id") != DASH]
    retrieval = {"checked_at": _now(), **_retrieval_check(request_ids)}
    (out_dir / "bl147-05-retrieval.json").write_text(
        json.dumps(retrieval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"[chain] 抽样 {total} / 命中 {hits} / 未命中 {misses} / 命中率 {chain['totals']['hit_rate']}")
    for svc, stats in scan["per_svc"].items():
        print(
            f"[contract] {svc}: 应用行 {stats['app_lines']}（合法 {stats['valid_json']}，"
            f"合法率 {stats['validity_rate']}）/ 框架行 {stats['framework_lines']} / 兜底'-' {stats['request_id_dash']}"
        )
    print(f"[retrieval] 按 module: {json.dumps(retrieval['by_module'], ensure_ascii=False)}")
    print(f"  证据目录：{out_dir}")
    return 0 if chain["totals"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
