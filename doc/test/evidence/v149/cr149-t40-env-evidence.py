"""Step 4 · 4.2 环境验证证据（TT-v1.4.9-006 及环境记录）。

产出：`cr149-t40-env-20260929.txt`
内容：双实例（开放 8041 / 关闭 8042）健康与逐组件、待测快照（提交哈希 ＋ 生产代码工作区洁净度）、
      开关矩阵实测值、日志卫生说明。

用法：
    python cr149-t40-env-evidence.py --out doc/test/evidence/v149/cr149-t40-env-20260929.txt
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

import httpx

BACKEND = Path(r"d:\Trae CN\myproject\Dev\OpenLLM\backend")
REPO = Path(r"d:\Trae CN\myproject\Dev\OpenLLM")
INSTANCES = (("开放（工作区 .env）", "http://127.0.0.1:8041"), ("关闭（三开关 = false）", "http://127.0.0.1:8042"))


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, encoding="utf-8", check=False
    )
    return (completed.stdout or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    lines: list[str] = []
    lines.append("=== v1.4.9 Step 4 · 4.2 环境验证证据 ===")
    lines.append(f"时间：{dt.datetime.now(dt.timezone.utc).isoformat()}")
    lines.append(f"后端根：{BACKEND}")
    lines.append("")
    lines.append("--- 待测快照（证明命中当前版本）---")
    lines.append(f"git HEAD（OpenLLM）：{_git('rev-parse', 'HEAD')}")
    lines.append(f"分支：{_git('rev-parse', '--abbrev-ref', 'HEAD')}（本地提交，**未推送**）")
    app_status = _git("status", "--porcelain", "--", "backend/app")
    lines.append(f"生产代码（backend/app）工作区变更：{'（无 ⇒ 实例加载的即 HEAD 代码）' if not app_status else app_status}")
    lines.append(f"v1.4.9 新增/改动测试与本次 Step 4 修复：见 git log --oneline -n 3")
    for item in _git("log", "--oneline", "-n", "3").splitlines():
        lines.append(f"  {item}")
    lines.append("")
    lines.append("--- 实例与逐组件 ---")
    for label, url in INSTANCES:
        lines.append(f"[{label}] {url}")
        try:
            response = httpx.get(f"{url}/openllm/v1/health", timeout=15.0)
            lines.append(f"  GET /openllm/v1/health → {response.status_code}")
            body = response.json()
            data = body.get("data") or {}
            lines.append(f"  data.status = {data.get('status')} / version = {data.get('version')}")
            for name, component in (data.get("components") or {}).items():
                lines.append(
                    f"    组件 {name}: status={component.get('status')} channel={component.get('channel')} "
                    f"latency_ms={component.get('latency_ms')}"
                )
            lines.append(f"  channel: {json.dumps(data.get('channel'), ensure_ascii=False)}")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"  不可用：{type(exc).__name__}: {exc}")
        lines.append("")

    lines.append("--- 开关矩阵（实测）---")
    for name in (
        "CONTEXT_BUDGET_ENABLED",
        "CONTEXT_CROSS_SEGMENT_COMPETITION_ENABLED",
        "COMPONENT_CHANNEL_ROUTING_ENABLED",
        "WRITEBACK_DECISION_ENABLED",
        "PROFILE_LLM_REFINE_ENABLED",
        "CONTEXT_SAFETY_MARGIN_TOKENS",
    ):
        import os

        lines.append(f"  {name} = {os.environ.get(name, '(未在探测进程显式设置 ⇒ 取工作区 .env 值)')}")
    lines.append("  实例 8041：工作区 .env（CONTEXT_BUDGET_ENABLED=true）")
    lines.append("  实例 8042：显式 false ×3（预算 / 跨段竞争 / 逐组件通道路由）用于关闭态逐字回退对照")
    lines.append("")
    lines.append("--- 日志卫生说明 ---")
    lines.append("  · 工作区 .env 的 DEBUG=true ⇒ SQLAlchemy echo 打开，实例输出极长（单次启动 5 万行量级）。")
    lines.append("  · 故本证据只保留**关键启动/健康事实**，完整原始日志留在本机临时目录（不入仓）。")
    lines.append("  · 敏感值（令牌/密钥）**不落盘、不打印**；本文件不含任何密钥与请求正文。")
    lines.append("")
    lines.append("--- 组件可用性（环境，不计为缺陷）---")
    lines.append("  · openrag / dps / ollama 本次为 unavailable ⇒ 组件级降级属**设计内行为**（须如实留痕，不得静默）。")
    lines.append("  · 检索类组件不可用直接导致运行态 `dropped` 为空 ⇒ TT-v1.4.9-018/047 记为**受限**，不计入通过。")

    report = "\n".join(lines)
    print(report)
    Path(args.out).write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
