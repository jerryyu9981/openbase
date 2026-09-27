"""异步精炼产物归属与装配期缓存探针（CR-149 §9 问题 6 裁定的取证）

**用途**：把裁定的**契约行为**落成可复现的判定表 —— 对「产物归属判定」与「装配期缓存」
各分支打印「归属 / 是否写记忆 / 缓存键 / 命中结果 / 淘汰与过期」，供人工核对
「异步精炼产物到底去了哪里」。

**裁定口径（2026-09-27）**：会话后批量压缩（异步精炼）的产物**归属＝装配期缓存**
（`assembly_cache`，**唯一合法值**），**不改写记忆粒度**；任何其它值（含 `memory_write`）
⇒ WARN ＋ 回退（fail-safe，**不提供开启口**）。缓存键 ＝ `(query_hash, 段内容 hash)`，
TTL 默认 600s、容量默认 256（**置 0 = 关闭**）。

用法（cwd = OpenLLM/backend）：python <此脚本> [--json]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration import refine_artifact as ra  # noqa: E402


def _case(name: str, expect: dict, actual: dict) -> dict:
    """汇总单个用例（expect/actual 均为判定键 ⇒ 自检可逐项比对）"""
    mismatched = [key for key in expect if expect[key] != actual.get(key)]
    return {
        "case": name,
        "expect": expect,
        "actual": actual,
        "ok": not mismatched,
        "mismatched": mismatched,
    }


def _owner_case(name: str, candidate) -> dict:
    """归属判定用例：**任何候选都不得写记忆**（核心契约）"""
    disposition = ra.describe_artifact_disposition(candidate)
    return _case(
        name,
        {"owner": ra.ARTIFACT_OWNER_ASSEMBLY_CACHE, "writes_memory": False},
        {"owner": disposition["owner"], "writes_memory": disposition["writes_memory"]},
    )


def _with_cache(size: int, ttl: int):
    """临时改缓存配置的上下文（返回还原函数）"""
    previous_size = settings.CONTEXT_REFINE_RESULT_CACHE_SIZE
    previous_ttl = settings.CONTEXT_REFINE_RESULT_CACHE_TTL_SECONDS
    settings.CONTEXT_REFINE_RESULT_CACHE_SIZE = size
    settings.CONTEXT_REFINE_RESULT_CACHE_TTL_SECONDS = ttl
    ra.reset_refine_cache()

    def restore() -> None:
        settings.CONTEXT_REFINE_RESULT_CACHE_SIZE = previous_size
        settings.CONTEXT_REFINE_RESULT_CACHE_TTL_SECONDS = previous_ttl
        ra.reset_refine_cache()

    return restore


def main() -> int:
    report: dict = {
        "probe": "refine_artifact_cache",
        "ruling": "§9 问题 6：异步精炼产物归属＝仅装配期缓存（assembly_cache 唯一合法），不改写记忆粒度",
    }
    cases: list[dict] = []

    # ---- ①~④ 产物归属判定（含裁定明确不放行的 memory_write） ----
    cases.append(_owner_case("① 默认归属 ⇒ 装配期缓存", None))
    cases.append(_owner_case("② 显式 memory_write ⇒ 回退（不写记忆）", "memory_write"))
    cases.append(_owner_case("③ 大小写变体 MEMORY_WRITE ⇒ 回退", "MEMORY_WRITE"))
    cases.append(_owner_case("④ 空值 ⇒ 回退", ""))

    # ---- ⑤~⑦ 缓存键：归一化稳定性与区分性 ----
    key_same = ra.compute_refine_cache_key("Hello   World", "Some\tContent") == (
        ra.compute_refine_cache_key("hello world", "some content")
    )
    cases.append(
        _case(
            "⑤ 键归一化（空白/大小写不敏感）⇒ 同键",
            {"same": True},
            {"same": key_same},
        )
    )
    cases.append(
        _case(
            "⑥ query 变化 ⇒ 换键",
            {"changed": True},
            {"changed": ra.compute_refine_cache_key("q1", "c") != ra.compute_refine_cache_key("q2", "c")},
        )
    )
    cases.append(
        _case(
            "⑦ 段内容变化 ⇒ 换键",
            {"changed": True},
            {"changed": ra.compute_refine_cache_key("q", "c1") != ra.compute_refine_cache_key("q", "c2")},
        )
    )

    # ---- ⑧~⑫ 装配期缓存语义 ----
    restore = _with_cache(size=256, ttl=600)
    try:
        stored = ra.refine_cache_store("译文查询", "段落原文", {"compressed": "压缩结果"})
        hit = ra.refine_cache_lookup("译文查询", "段落原文")
        cases.append(
            _case(
                "⑧ 存取往返 ⇒ 命中同值",
                {"stored": True, "hit": {"compressed": "压缩结果"}},
                {"stored": stored, "hit": hit},
            )
        )
        hit["compressed"] = "被篡改"
        cases.append(
            _case(
                "⑨ 命中返回副本（篡改不污染缓存）",
                {"hit": {"compressed": "压缩结果"}},
                {"hit": ra.refine_cache_lookup("译文查询", "段落原文")},
            )
        )
        ttl = settings.CONTEXT_REFINE_RESULT_CACHE_TTL_SECONDS
        cases.append(
            _case(
                "⑩ TTL 过期 ⇒ 未命中",
                {"hit": None},
                {"hit": ra.refine_cache_lookup("译文查询", "段落原文", now=ra._now() + ttl + 1)},
            )
        )
    finally:
        restore()

    restore = _with_cache(size=0, ttl=600)
    try:
        cases.append(
            _case(
                "⑪ 容量 0 ⇒ 关闭（不缓存）",
                {"stored": False, "hit": None},
                {
                    "stored": ra.refine_cache_store("q", "c", 1),
                    "hit": ra.refine_cache_lookup("q", "c"),
                },
            )
        )
    finally:
        restore()

    restore = _with_cache(size=2, ttl=600)
    try:
        ra.refine_cache_store("q1", "c", 1)
        ra.refine_cache_store("q2", "c", 2)
        ra.refine_cache_store("q3", "c", 3)
        cases.append(
            _case(
                "⑫ 超容量淘汰最旧",
                {"oldest": None, "newest": 3},
                {"oldest": ra.refine_cache_lookup("q1", "c"), "newest": ra.refine_cache_lookup("q3", "c")},
            )
        )
    finally:
        restore()

    report["cases"] = cases
    report["guardrail_summary"] = (
        "归属**恒为** assembly_cache：任何候选（含 memory_write / 大小写变体 / 空值）"
        "⇒ WARN ＋ 回退 ⇒ `writes_memory=false`（**不提供开启口**）；"
        "缓存键 ＝ (query_hash, 段内容 hash)，命中返回副本、TTL 过期失效、容量 0 关闭"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # ---- 探针自检 ----
    failed = [item["case"] for item in cases if not item["ok"]]
    # 核心契约独立复核：任何候选都不得被判为「写记忆」
    candidates = ["memory_write", "MEMORY_WRITE", "Memory_Write", "", None, "assembly_cache", "memory"]
    memory_write_leaked = [
        candidate
        for candidate in candidates
        if ra.describe_artifact_disposition(candidate)["writes_memory"]
    ]
    verdict_ok = not failed and not memory_write_leaked
    verdict = "PASS" if verdict_ok else "FAIL"
    print(
        f"probe self-check: {verdict}（{len(cases)} 例 / 不符 {len(failed)} 个 / "
        f"误判写记忆 {len(memory_write_leaked)} 个）"
    )
    for name in failed:
        print(f"  ! 用例期望与实测不符: {name}")
    for candidate in memory_write_leaked:
        print(f"  ! 候选被误判为写记忆: {candidate!r}")
    report["self_check"] = {
        "ok": verdict_ok,
        "cases": len(cases),
        "mismatched": failed,
        "memory_write_leaked": memory_write_leaked,
    }

    if "--json" in sys.argv:
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "refine_artifact_cache_probe-result.json"
        )
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"报告已写入: {out}")
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
