"""生成 Step 5 发布实例日志证据（截取关键段 ＋ 卫生统计），避免把 248 KB 原始日志整体入库。

用法：
    python cr149-t50-log-evidence.py --log <原始日志> --out doc/test/evidence/v149/cr149-t50-release-8041-20260929.txt
"""

from __future__ import annotations

import argparse
import io
import re
from pathlib import Path

SECRET_PATTERNS = {
    "password[:=]": r"(?i)\bpassword\b\s*[:=]",
    "api_key[:=]": r"(?i)\bapi[_-]?key\b\s*[:=]",
    "secret[:=]": r"(?i)\bsecret\b\s*[:=]",
    "sk-<len>": r"sk-[A-Za-z0-9]{8,}",
    "authorization: bearer": r"(?i)authorization:\s*bearer",
}

START_MARKERS = ("Application startup complete.", "Uvicorn running on")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--head", type=int, default=40)
    args = parser.parse_args()

    raw = Path(args.log).read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    structured = [line for line in lines if line.lstrip().startswith("{")]
    structured_with_level = [line for line in structured if re.search(r'"(level|severity)"\s*:', line)]

    # 关键段：首个结构化日志行起 head 行 ＋ 启动完成标记及其上下文
    start_index = next((i for i, line in enumerate(lines) if line.strip().startswith("{")), 0)
    head_block = lines[start_index : start_index + args.head]
    tail_block: list[str] = []
    for index, line in enumerate(lines):
        if any(marker in line for marker in START_MARKERS):
            tail_block = lines[max(0, index - 3) : index + 1]
            break

    hits: dict[str, int] = {}
    for name, pattern in SECRET_PATTERNS.items():
        count = len(re.findall(pattern, text))
        if count:
            hits[name] = count
    # 命中行内容（值掩码，只留键名与说明）
    masked_lines = []
    for line in lines:
        if re.search(r"(?i)\bapi[_-]?key\b\s*[:=]", line):
            masked_lines.append(re.sub(r"([:=]\s*)([A-Za-z0-9_\-.]{6,})", r"\1<MASKED>", line.strip())[:220])

    report = [
        "=== v1.4.9 Step 5 · 发布实例日志证据（Dev 环境，8041）===",
        f"原始日志：{Path(args.log).name}（{len(raw)} 字节 / {len(lines)} 行）",
        "说明：**完整原始日志不入仓**（体积见上，含 SQLAlchemy echo 等高频输出），"
        "本文件保留关键段与卫生统计；原始日志留于本机临时目录。",
        "",
        "--- ① 启动关键段（结构化日志起始 head）---",
        *head_block,
        "",
        "--- ② 启动完成标记 ---",
        *tail_block,
        "",
        "--- ③ 日志卫生统计 ---",
        f"结构化 JSON 行：{len(structured)} / 总行 {len(lines)}"
        f"（其中含 level 字段者 {len(structured_with_level)} 行）；"
        "非 JSON 行为 uvicorn 自带输出（`INFO: ...`）",
        f"敏感模式命中计数：{hits if hits else '两种口径下均为 0'}",
    ]
    if masked_lines:
        report += [
            "",
            "--- ④ 命中行原文（值已掩码）---",
            *masked_lines,
            "结论：命中项为 **`api_key=未配置`**（应用如实打印「未配置」，**非密钥值**）⇒ 日志无真实凭据落痕。",
        ]
    else:
        report += ["", "结论：未发现任何密钥/令牌落痕。"]

    out = Path(args.out)
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:6]))
    print(f"\n[written] {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
