"""装配**保真度对照**探针：判定表 ＋ 结尾自检（含开关两态与掩码/有界红线）

**用途**：把「对比智能体原文 ⇄ 最终投喂上下文」的契约落成**可复现判定表** —— 逐例打印
「意图判定 / 信号 / 两端规模 / 是否掩码」并在结尾**自检**：任一不符即 `FAIL` 且返回码非 0。

**锁定的七条契约**：

  ① **逐字保留即 intact**（无注入、无裁剪时信号为空）；
  ② **被改写 ⇒ `mutated` ＋ `query_rewritten`**（用户意图失真信号）；
  ③ **缺 `[用户问题]` 段 ⇒ `missing` ＋ `query_absent`**（装配丢问题，最严重失真）；
  ④ **历史裁剪可见** ⇒ `turns_dropped > 0` ＋ `history_truncated`（设计行为，但**必须可见**）；
  ⑤ **凭据不出模块** ⇒ 落库文本中敏感串不出现（掩码生效）；
  ⑥ **有界** ⇒ 超长截断并标注 `truncated_for_capture`；
  ⑦ **开关两态** ⇒ 关闭返回 `None`（逐字回退）、开启返回完整记录。

用法（cwd = OpenLLM/backend）：python <此脚本> [--json]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from app.core.config import settings  # noqa: E402
from app.edgerouter.orchestration.assembler import PromptAssembler  # noqa: E402
from app.edgerouter.orchestration.fidelity_capture import (  # noqa: E402
    build_fidelity_capture,
)

SECRET = "sk-liveprobe0123456789abcdef"


def _with_capture(enabled: bool, max_chars: int = 20000):
    """临时置位捕获开关（退出恢复；只读探针**不改配置**）"""
    class _Guard:
        def __enter__(self):
            self._old_enabled = settings.CONTEXT_FIDELITY_CAPTURE_ENABLED
            self._old_max = settings.CONTEXT_FIDELITY_CAPTURE_MAX_CHARS
            settings.CONTEXT_FIDELITY_CAPTURE_ENABLED = enabled
            settings.CONTEXT_FIDELITY_CAPTURE_MAX_CHARS = max_chars
            return self

        def __exit__(self, *_exc):
            settings.CONTEXT_FIDELITY_CAPTURE_ENABLED = self._old_enabled
            settings.CONTEXT_FIDELITY_CAPTURE_MAX_CHARS = self._old_max
            return False

    return _Guard()


def _render(**kwargs) -> str:
    return PromptAssembler().render(**kwargs)


def _case(
    name: str,
    *,
    expect_verdict: str,
    expect_flags: list[str],
    request_query: str,
    request_messages: list[dict] | None = None,
    final_prompt: str | None,
    expect_masked: bool = False,
    expect_truncated: bool | None = None,
    max_chars: int = 20000,
) -> dict:
    with _with_capture(True, max_chars=max_chars):
        capture = build_fidelity_capture(
            request_query=request_query,
            request_messages=request_messages,
            final_prompt=final_prompt,
            model="probe-model",
        )
    assert capture is not None, f"{name}: 开关开启却返回 None"
    analysis = capture["analysis"]
    serialized = json.dumps(capture, ensure_ascii=False)

    checks = {
        "verdict_matches": analysis["verdict"] == expect_verdict,
        "flags_match": sorted(analysis["flags"]) == sorted(expect_flags),
        "masked": (SECRET not in serialized) if expect_masked else True,
        "truncated_flag_matches": (
            True
            if expect_truncated is None
            else capture["final"]["truncated_for_capture"] is expect_truncated
        ),
        "bounded": len(capture["final"]["text"]) <= max_chars,
    }
    return {
        "case": name,
        "verdict": analysis["verdict"],
        "flags": analysis["flags"],
        "request_chars": capture["request"]["chars"],
        "final_chars": capture["final"]["chars"],
        "masked": expect_masked,
        "checks": checks,
        "ok": all(checks.values()),
    }


def build_cases() -> list[dict]:
    """保真度对照判定表（**可由执行器 T16 直接复用**，避免判据与探针分叉）"""
    intact_prompt = _render(
        system_prompt="", profile_ctx=None, memory_ctx="[M1] 素材",
        rag_ctx=None, history_ctx=None, query="如何调整装配流程",
    )
    rewritten_prompt = _render(
        system_prompt="", profile_ctx=None, memory_ctx=None,
        rag_ctx=None, history_ctx=None, query="被改写的问法",
    )
    no_query_prompt = "[记忆上下文]\n[M1] 素材"
    history_prompt = _render(
        system_prompt="", profile_ctx=None, memory_ctx=None, rag_ctx=None,
        history_ctx="user: 第二轮问题", query="第三轮问题",
    )
    secret_prompt = _render(
        system_prompt="", profile_ctx=None, memory_ctx=None,
        rag_ctx=None, history_ctx=None, query=f"Bearer {SECRET}",
    )
    long_prompt = _render(
        system_prompt="", profile_ctx=None, memory_ctx=None,
        rag_ctx=None, history_ctx=None, query="长" * 500,
    )

    return [
        _case(
            "① 逐字保留、无裁剪 ⇒ intact 且信号为空",
            expect_verdict="intact",
            expect_flags=[],
            request_query="如何调整装配流程",
            final_prompt=intact_prompt,
        ),
        _case(
            "② 用户问题被改写 ⇒ mutated ＋ query_rewritten（意图失真）",
            expect_verdict="mutated",
            expect_flags=["query_rewritten"],
            request_query="原始问法",
            final_prompt=rewritten_prompt,
        ),
        _case(
            "③ 最终 Prompt 缺 [用户问题] 段 ⇒ missing ＋ query_absent",
            expect_verdict="missing",
            expect_flags=["query_absent"],
            request_query="原始问法",
            final_prompt=no_query_prompt,
        ),
        _case(
            "④ 历史被裁剪 ⇒ intact（意图未变）＋ history_truncated（裁剪可见）",
            expect_verdict="intact",
            expect_flags=["history_truncated"],
            request_query="第三轮问题",
            request_messages=[
                {"role": "user", "content": "第一轮问题"},
                {"role": "assistant", "content": "第一轮回答"},
                {"role": "user", "content": "第二轮问题"},
            ],
            final_prompt=history_prompt,
        ),
        _case(
            "⑤ 含凭据 ⇒ 落库文本已掩码（敏感串不出现）",
            expect_verdict="intact",
            expect_flags=[],
            request_query=f"Bearer {SECRET}",
            final_prompt=secret_prompt,
            expect_masked=True,
        ),
        _case(
            "⑥ 超长 ⇒ 有界截断并标注 truncated_for_capture",
            expect_verdict="intact",
            expect_flags=[],
            request_query="长" * 500,
            final_prompt=long_prompt,
            expect_truncated=True,
            max_chars=120,
        ),
    ]


def _switch_case() -> dict:
    """⑦ 开关两态：关闭 ⇒ None（逐字回退）；开启 ⇒ 完整记录"""
    prompt = _render(
        system_prompt="", profile_ctx=None, memory_ctx=None,
        rag_ctx=None, history_ctx=None, query="问",
    )
    with _with_capture(False):
        disabled = build_fidelity_capture(
            request_query="问", request_messages=None, final_prompt=prompt
        )
    with _with_capture(True):
        enabled = build_fidelity_capture(
            request_query="问", request_messages=None, final_prompt=prompt
        )
    checks = {
        "disabled_returns_none": disabled is None,
        "enabled_returns_record": isinstance(enabled, dict)
        and "analysis" in enabled,
    }
    return {
        "case": "⑦ 开关两态：关 ⇒ None（逐字回退）／开 ⇒ 完整记录",
        "verdict": "-",
        "flags": [],
        "request_chars": 0,
        "final_chars": 0,
        "masked": False,
        "checks": checks,
        "ok": all(checks.values()),
    }


def main() -> int:
    cases = [*build_cases(), _switch_case()]

    payload = {
        "probe": "fidelity_capture",
        "ruling": (
            "装配**保真度对照**（2026-09-28 用户口径）：把「智能体原文 ⇄ 最终投喂 Prompt」"
            "两端成对采集，**默认关闭**（逐字回退）、开启时**掩码 ＋ 有界**；输出机读"
            "`verdict` / `flags` 判定装配是否**失真反馈用户真实意图**"
        ),
        "cases": cases,
    }
    failures = [item["case"] for item in cases if not item["ok"]]
    payload["summary"] = {
        "total": len(cases),
        "failed": len(failures),
        "failed_cases": failures,
        "verdict": "PASS" if not failures else "FAIL",
    }

    if "--json" in sys.argv:
        target = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fidelity_capture_probe-result.json"
        )
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print(f"已落盘：{target}")

    for item in cases:
        bad = [name for name, ok in item["checks"].items() if not ok]
        print(
            f"{'OK ' if item['ok'] else 'BAD'} {item['case']} ⇒ "
            f"verdict={item['verdict']} flags={item['flags']} 不符={bad}"
        )
    print(f"\n判定: {payload['summary']['verdict']}（{len(cases)} 例 / 不符 {len(failures)}）")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
