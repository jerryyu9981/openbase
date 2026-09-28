"""装配**保真度对照**报告工具：智能体原文 ⇄ 最终投喂上下文

**用途（用户口径，2026-09-28）**：对比「智能体发起的对话原文」与「最终投喂给 LLM 的上下文」
的异同，据此**调整装配流程与装配方案**，确保**不失真地反馈用户真实意图**。

**三种输入方式**

  1. ``--capture <file.json>`` —— 读 `GET /openllm/v1/trace/fidelity/export` 的产物
     （或其 `items[i]` 单条记录）；可用 ``--index N`` 选第 N 条，``--all`` 逐条汇总。
  2. ``--request-file a.txt --final-file b.txt`` —— 直接给两端文本（离线对照，无需服务）。
  3. ``--demo`` —— 用合成样本**进程内**跑一遍（**无需服务、无需开关**），演示报告形态。

**输出**：可读对照报告（默认标准输出；``--md`` 落 Markdown，``--json`` 落机读结果）。
``--strict``：`verdict != intact` 即**非零退出**（可作评测/发布门禁）。

用法（cwd = OpenLLM/backend）：
    python <此脚本> --demo
    python <此脚本> --capture fidelity-export.json --index 0 --md report.md --json report.json --strict
    python <此脚本> --request-file req.txt --final-file prompt.txt
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.getcwd())

from app.edgerouter.orchestration.assembler import PromptAssembler  # noqa: E402
from app.edgerouter.orchestration.fidelity_capture import (  # noqa: E402
    FLAG_ADVICE,
    SEGMENT_MARKERS,
    analyze_fidelity,
    mask_sensitive,
    split_prompt_segments,
)

# 调整建议映射**取自生产侧**（`fidelity_capture.FLAG_ADVICE`，唯一来源）—— 本工具不再自持一份，
# 避免「接口给的说明」与「工具给的说明」两处漂移。


def _record_from_texts(request_text: str, final_prompt: str) -> dict:
    """由两端文本构造与线上同构的记录（离线对照用）"""
    import hashlib

    segments = split_prompt_segments(final_prompt)
    return {
        "request": {
            "query": mask_sensitive(request_text),
            "text": mask_sensitive(request_text),
            "sha256": hashlib.sha256(request_text.encode("utf-8")).hexdigest(),
            "chars": len(request_text),
            "truncated_for_capture": False,
        },
        "final": {
            "text": mask_sensitive(final_prompt),
            "sha256": hashlib.sha256(final_prompt.encode("utf-8")).hexdigest(),
            "chars": len(final_prompt),
            "truncated_for_capture": False,
            "segment_chars": {
                name: len(segments[name] or "") for name, _ in (("system", ""), *SEGMENT_MARKERS)
            },
        },
        "analysis": analyze_fidelity(
            final_prompt=final_prompt, request_query=request_text
        ),
    }


def build_report(record: dict, *, label: str = "", preview_chars: int = 400) -> str:
    """把一条对照记录渲染为**可读报告**（纯函数，便于测试与复用于不同输出面）"""
    analysis = record.get("analysis") or {}
    request = record.get("request") or {}
    final = record.get("final") or {}
    verdict = analysis.get("verdict", "unknown")
    flags = list(analysis.get("flags") or [])
    query = analysis.get("query") or {}
    history = analysis.get("history") or {}
    injected = analysis.get("injected") or {}

    lines: list[str] = []
    lines.append(f"# 装配保真度对照报告{f'（{label}）' if label else ''}")
    lines.append("")
    lines.append(f"**判定：`{verdict}`**" + (f"　信号：{flags}" if flags else "　（无失真信号）"))
    lines.append("")

    lines.append("## 1. 两端规模与指纹")
    lines.append("")
    lines.append("| 端 | 字符数 | 指纹(sha256 前 12) | 展示是否被截断 |")
    lines.append("|----|-------:|--------------------|:--------------:|")
    lines.append(
        f"| 智能体原文 | {request.get('chars', 0)} | `{str(request.get('sha256') or '')[:12]}` "
        f"| {'是' if request.get('truncated_for_capture') else '否'} |"
    )
    lines.append(
        f"| 最终投喂 Prompt | {final.get('chars', 0)} | `{str(final.get('sha256') or '')[:12]}` "
        f"| {'是' if final.get('truncated_for_capture') else '否'} |"
    )
    lines.append("")

    lines.append("## 2. 段位分布（最终 Prompt）")
    lines.append("")
    segment_chars = final.get("segment_chars") or {}
    total = max(1, int(final.get("chars", 0) or 0))
    lines.append("| 段 | 字符数 | 占最终 Prompt | 段内文本（前 40 字） |")
    lines.append("|----|-------:|-------------:|----------------------|")
    segments = split_prompt_segments(final.get("text") or "")
    for name in ("system", "profile", "memory", "rag", "history", "query"):
        chars = int(segment_chars.get(name, len(segments.get(name) or "")) or 0)
        preview = (segments.get(name) or "").replace("\n", " ")[:40]
        preview = preview + ("…" if len(segments.get(name) or "") > 40 else "")
        lines.append(f"| {name} | {chars} | {chars / total:.1%} | {preview or '（空）'} |")
    lines.append("")

    lines.append("## 3. 用户意图核对")
    lines.append("")
    lines.append(
        f"- 用户问题**逐字保留**：**{'是' if query.get('verbatim_preserved') else '否'}**"
        f"（原文 {query.get('request_chars', 0)} 字 → 最终 {query.get('final_chars', 0)} 字）"
    )
    lines.append(f"- 用户问题出现在最终 Prompt 中：{'是' if query.get('present_in_prompt') else '否'}")
    lines.append(
        f"- 历史轮次：原始 {history.get('turns_total', 0)} 轮 / 命中最终 Prompt "
        f"{history.get('turns_included', 0)} 轮 / 被丢 {history.get('turns_dropped', 0)} 轮"
    )
    lines.append(
        f"- 注入的非用户素材占比：**{float(injected.get('ratio', 0.0)):.1%}**"
        f"（system {int((injected.get('system') or {}).get('chars', 0))} / "
        f"profile {int((injected.get('profile') or {}).get('chars', 0))} / "
        f"memory {int((injected.get('memory') or {}).get('chars', 0))} / "
        f"rag {int((injected.get('rag') or {}).get('chars', 0))} / "
        f"history {int((injected.get('history') or {}).get('chars', 0))} 字）"
    )
    lines.append("")

    lines.append("## 4. 并排对照")
    lines.append("")
    lines.append("**智能体原文（截断展示）**")
    lines.append("")
    lines.append("```text")
    lines.append((request.get("text") or "（空）")[:preview_chars])
    lines.append("```")
    lines.append("")
    lines.append("**最终投喂的 `[用户问题]` 段（截断展示）**")
    lines.append("")
    lines.append("```text")
    lines.append((query.get("final_text") or "（空）")[:preview_chars])
    lines.append("```")
    lines.append("")

    lines.append("## 5. 调整建议")
    lines.append("")
    if flags:
        for flag in flags:
            lines.append(f"- `{flag}`：{FLAG_ADVICE.get(flag, '请人工核查该信号对应的装配环节。')}")
    else:
        lines.append(
            "- 本次**未发现失真信号**：用户问题逐字进入最终 Prompt、无历史裁剪信号。"
            "如需进一步评估「注入是否过量/不足」，请看 §2 段位分布与 `injected.ratio`。"
        )
    lines.append("")
    lines.append(
        "> 说明：报告文本均为**掩码后**内容（`***` 处为凭据掩码）；"
        "`verdict` / `flags` 等判定基于**原文**计算，为真值。"
    )
    return "\n".join(lines)


def _demo_record() -> dict:
    """合成样本：一段智能体对话 + 注入画像/记忆/知识（含一轮历史被裁剪）"""
    conversation = [
        {"role": "user", "content": "我想对比装配前后的差异，确保不失真。"},
        {"role": "assistant", "content": "可以提供两端口径。"},
        {"role": "user", "content": "请说明装配流程里哪些环节可能改写我的问题。"},
    ]
    final_prompt = PromptAssembler().render(
        system_prompt="你是企业知识助手，须依据所给素材回答。",
        profile_ctx="[个人画像]\nname: 张三\ntone: formal",
        memory_ctx="[M1] 用户偏好逐字保留问题原意\n[M2] 上轮讨论了装配流程",
        rag_ctx="[K1] 装配流程：取数 → 选择 → 预算 → 精炼 → 组装",
        history_ctx="user: 我想对比装配前后的差异，确保不失真。",
        query=conversation[-1]["content"],
    )
    import hashlib

    segments = split_prompt_segments(final_prompt)
    return {
        "model": "demo-model",
        "request": {
            "query": mask_sensitive(conversation[-1]["content"]),
            "messages": [
                {"role": m["role"], "content": mask_sensitive(m["content"])}
                for m in conversation
            ],
            "text": mask_sensitive(
                "\n".join(f"{m['role']}: {m['content']}" for m in conversation)
            ),
            "sha256": hashlib.sha256(
                "\n".join(m["content"] for m in conversation).encode("utf-8")
            ).hexdigest(),
            "chars": len("\n".join(m["content"] for m in conversation)),
            "truncated_for_capture": False,
        },
        "final": {
            "text": final_prompt,
            "sha256": hashlib.sha256(final_prompt.encode("utf-8")).hexdigest(),
            "chars": len(final_prompt),
            "truncated_for_capture": False,
            "segment_chars": {
                name: len(segments[name] or "")
                for name, _ in (("system", ""), *SEGMENT_MARKERS)
            },
        },
        "analysis": analyze_fidelity(
            final_prompt=final_prompt,
            request_query=conversation[-1]["content"],
            request_messages=conversation,
        ),
    }


def _load_records(args) -> list[tuple[str, dict]]:
    if args.demo:
        return [("demo 合成样本", _demo_record())]
    if args.request_file and args.final_file:
        request_text = io.open(args.request_file, encoding="utf-8").read()
        final_prompt = io.open(args.final_file, encoding="utf-8").read()
        return [("离线两端文本", _record_from_texts(request_text, final_prompt))]
    payload = json.load(io.open(args.capture, encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else None
    if items is None:
        return [("单条记录", payload)]
    if args.all:
        return [
            (f"记录 #{index}", item) for index, item in enumerate(items)
        ]
    index = int(args.index or 0)
    if index >= len(items):
        raise SystemExit(f"记录索引越界：items 共 {len(items)} 条，请求 #{index}")
    return [(f"记录 #{index}", items[index])]


def main() -> int:
    parser = argparse.ArgumentParser(description="装配保真度对照报告（智能体原文 ⇄ 最终投喂上下文）")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--capture", help="导出的 JSON（export 产物或单条记录）")
    source.add_argument("--demo", action="store_true", help="用合成样本进程内演示")
    parser.add_argument("--request-file", help="离线模式：智能体原文文本文件")
    parser.add_argument("--final-file", help="离线模式：最终 Prompt 文本文件")
    parser.add_argument("--index", default=0, help="多记录时选第 N 条（默认 0）")
    parser.add_argument("--all", action="store_true", help="逐条输出全部记录")
    parser.add_argument("--md", default="", help="把报告写入该路径（Markdown）")
    parser.add_argument("--json", default="", help="把机读结果写入该路径")
    parser.add_argument("--strict", action="store_true", help="verdict != intact 即非零退出")
    args = parser.parse_args()

    records = _load_records(args)
    reports = [build_report(record, label=label) for label, record in records]
    output = "\n\n---\n\n".join(reports)
    print(output)

    if args.md:
        io.open(args.md, "w", encoding="utf-8", newline="\n").write(output + "\n")
        print(f"\n已落盘报告：{args.md}")
    if args.json:
        io.open(args.json, "w", encoding="utf-8", newline="\n").write(
            json.dumps(
                {
                    "records": [
                        {"label": label, "analysis": record.get("analysis")}
                        for label, record in records
                    ]
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        print(f"已落盘机读结果：{args.json}")

    bad = [
        label
        for label, record in records
        if (record.get("analysis") or {}).get("verdict") != "intact"
    ]
    if args.strict and bad:
        print(f"\n[STRICT] 非 intact 记录：{bad} ⇒ 退出码 1")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
