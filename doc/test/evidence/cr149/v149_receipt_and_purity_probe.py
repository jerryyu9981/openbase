"""v1.4.9 Step 3 判据取证：**回执字段齐备率** 与 **不复用旧裁剪链路 / 无敏感落痕**

覆盖判据（《验收标准清单-v1.4.9》）：

  * **AC-149-05** 回执字段齐备率 100% —— 逐字段核对 10 项必填（模型/窗口/输出预留/安全余量/
    实际可用预算/裁剪前后 token/被丢弃片段及原因/是否硬截断/降级标记）；
  * **AC-149-10** 代码**未复用** `manage_context` / `_prune_recent` —— **静态引用扫描**
    （新预算/裁剪链路模块内零命中；旧实现仍仅在 `services/context_manager.py` 与
    `api/context.py` 内，未被新链路调用）；
  * **AC-149-11** 回执**不含**令牌/密钥/完整请求体/片段正文 —— 敏感串扫描 ＋ 正文哨兵扫描。

用法（在任意 cwd 下均可运行；backend 根按下方顺序自动定位）：

    python <此脚本> [--json 输出路径]

backend 根定位顺序：`OPENLLM_BACKEND` 环境变量 → 当前工作目录 → 与 OpenBase 同级的
`OpenLLM/backend`（仓库相邻布局）。定位失败即**显式报错退出**，不静默降级为漏扫。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

_EVIDENCE_DIR = os.path.dirname(os.path.abspath(__file__))

#: backend 根的**判定标记**（AC-149-10 扫描面之一；存在即认定为 backend 根）
_BACKEND_MARKER = os.path.join("app", "edgerouter", "orchestration", "prompt_pipeline.py")


def _resolve_backend_root() -> str:
    """定位 OpenLLM backend 根（使脚本在任意 cwd 下可复现）"""
    sibling = os.path.abspath(
        os.path.join(_EVIDENCE_DIR, *([os.pardir] * 5), "OpenLLM", "backend")
    )
    for candidate in (os.environ.get("OPENLLM_BACKEND", ""), os.getcwd(), sibling):
        if candidate and os.path.exists(os.path.join(candidate, _BACKEND_MARKER)):
            return os.path.abspath(candidate)
    raise SystemExit(
        "无法定位 OpenLLM backend（应含 app/edgerouter/orchestration/prompt_pipeline.py）："
        f"已尝试 OPENLLM_BACKEND / {os.getcwd()} / {sibling}；"
        "请设置 OPENLLM_BACKEND 环境变量后重跑。"
    )


_BACKEND_ROOT = _resolve_backend_root()
sys.path.insert(0, _BACKEND_ROOT)

#: **必须固定 cwd 到 backend 根**：`app.core.config` 的 `Settings` 用 `env_file=".env"`（**相对路径**），
#: 若在 OpenBase 仓根等他处执行，会把**他仓的 `.env`** 载入 `Settings`；而 `Settings` 为
#: `extra=forbid` ⇒ 直接校验失败（真实缺陷，Step 4 实测暴露）。固定 cwd 后脚本方**真正**与 cwd 无关。
os.chdir(_BACKEND_ROOT)

#: 新预算/裁剪链路模块（AC-149-10 的扫描面）—— 绝对路径，避免受 cwd 影响
NEW_PIPELINE_MODULES = tuple(
    os.path.join(_BACKEND_ROOT, relative)
    for relative in (
        os.path.join("app", "edgerouter", "orchestration", "prompt_pipeline.py"),
        os.path.join("app", "edgerouter", "orchestration", "context_metrics.py"),
        os.path.join("app", "edgerouter", "orchestration", "refine.py"),
        os.path.join("app", "edgerouter", "orchestration", "refine_placement.py"),
    )
)
LEGACY_SYMBOLS = ("manage_context", "_prune_recent")
#: 旧实现的合法落点（**允许**出现；关键是新链路不引用）
LEGACY_ALLOWED_FILES = tuple(
    os.path.join(_BACKEND_ROOT, relative)
    for relative in (
        os.path.join("app", "services", "context_manager.py"),
        os.path.join("app", "api", "context.py"),
    )
)

REQUIRED_RECEIPT_FIELDS = (
    "model",
    "model_window",
    "output_reserve",
    "safety_margin",
    "available_budget",
    "prompt_tokens_before",
    "prompt_tokens_after",
    "dropped",
    "hard_truncated",
    "degraded",
)

#: 敏感**字段名**白名单（**精确键名**匹配）—— 注意：`prompt_total_tokens` 一类**计量字段名**
#:   含 "token" 子串但**不是**密钥，故不得用裸子串扫描（首版探针误报，已更正口径）。
SENSITIVE_KEY_RE = re.compile(
    r'"(?:access_token|refresh_token|token|api_key|apikey|secret|password|'
    r'authorization|bearer_token)"\s*:',
    re.IGNORECASE,
)
#: 敏感**值形态**（真实凭据的典型形状）
SENSITIVE_VALUE_RE = re.compile(r"\bsk-[A-Za-z0-9]{8,}\b|Bearer\s+\S+")
#: 正文哨兵：素材正文若落痕即命中
BODY_SENTINEL = "哨兵正文不应出现在回执"


def _counter(text: str) -> int:
    return len(text or "")


def check_ac_149_10() -> dict[str, Any]:
    """AC-149-10：静态引用扫描（新链路零命中旧裁剪实现）"""
    hits: list[str] = []
    scanned: list[str] = []
    for path in NEW_PIPELINE_MODULES:
        relative = os.path.relpath(path, _BACKEND_ROOT).replace("\\", "/")
        if not os.path.exists(path):
            hits.append(f"{relative}: 文件不存在（扫描面缺失）")
            continue
        scanned.append(relative)
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        for symbol in LEGACY_SYMBOLS:
            if symbol in source:
                hits.append(f"{relative}: 命中旧裁剪符号 {symbol}")
    return {
        "backend_root": _BACKEND_ROOT,
        "scanned": scanned,
        "legacy_symbols": list(LEGACY_SYMBOLS),
        "legacy_allowed_files": [
            os.path.relpath(path, _BACKEND_ROOT).replace("\\", "/")
            for path in LEGACY_ALLOWED_FILES
        ],
        "violations": hits,
        "passed": not hits,
    }


def check_ac_149_05() -> dict[str, Any]:
    """AC-149-05：真实回执的字段齐备性（含数值自洽）"""
    from app.edgerouter.orchestration.context_metrics import ContextReceipt
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    policy = BudgetPolicy(
        enabled=True, window_tokens=1200, output_reserve_tokens=200, safety_margin_tokens=50
    )
    history = "\n".join(f"{i}. " + f"史{i}" * 30 for i in range(1, 9))
    _prompt, composition = build_prompt(
        count_tokens=_counter,
        budget=policy,
        query="问题",
        history_ctx=history,
        segment_items={"history": [
            {"source": "history", "id": f"h-{i:04d}", "score": None} for i in range(1, 9)
        ]},
    )
    record = ContextReceipt(
        request_id="probe-fields", model="probe-model", composition=composition
    ).to_record()

    missing = [name for name in REQUIRED_RECEIPT_FIELDS if name not in record]
    problems = [f"缺字段 {name}" for name in missing]
    # 「齐备」＝**键在**且**取值有语义**（除 `degraded` 按设计可为 null）——只查键存在会把
    # `{"model": null}` 误判为齐备（本探针首版即此弱点，已更正）。
    null_valued = [
        name
        for name in REQUIRED_RECEIPT_FIELDS
        if name != "degraded" and name in record and record[name] is None
    ]
    problems.extend(f"字段 {name} 为 null（未落有效取值）" for name in null_valued)
    if not missing:
        expected_available = (
            record["model_window"] - record["output_reserve"] - record["safety_margin"]
        )
        if record["available_budget"] != expected_available:
            problems.append(
                "available_budget 与预算公式不符（设计 §3.3）: "
                f"{record['available_budget']} != {expected_available}"
            )
        if record["prompt_tokens_before"] < record["prompt_tokens_after"]:
            problems.append("裁剪前 token 应 ≥ 裁剪后（本样本确有裁剪）")
        if record["hard_truncated"] is not False:
            problems.append("本样本为整条丢弃 ⇒ hard_truncated 应为 False")
        if record["degraded"] is not None:
            problems.append("本样本无段级降级 ⇒ degraded 应为 null")
        if not record["dropped"]:
            problems.append("提供条目身份且有丢弃 ⇒ dropped 不应为空")
    return {
        "required_fields": list(REQUIRED_RECEIPT_FIELDS),
        "observed": {name: record.get(name) for name in REQUIRED_RECEIPT_FIELDS},
        "problems": problems,
        "passed": not problems,
    }


def check_ac_149_11() -> dict[str, Any]:
    """AC-149-11：回执不含令牌/密钥/请求体/片段正文"""
    from app.edgerouter.orchestration.context_metrics import ContextReceipt
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    policy = BudgetPolicy(enabled=True, window_tokens=1200, output_reserve_tokens=200)
    history = f"1. {BODY_SENTINEL}\n2. 第二条素材正文"
    _prompt, composition = build_prompt(
        count_tokens=_counter,
        budget=policy,
        query="问题",
        history_ctx=history,
        segment_items={"history": [
            {"source": "history", "id": "h-1", "score": None},
            {"source": "history", "id": "h-2", "score": None},
        ]},
    )
    serialized = json.dumps(
        ContextReceipt(request_id="probe-purity", composition=composition).to_record(),
        ensure_ascii=False,
    )
    problems: list[str] = []
    key_hit = SENSITIVE_KEY_RE.search(serialized)
    if key_hit:
        problems.append(f"回执出现敏感**字段名**：{key_hit.group(0)}")
    value_hit = SENSITIVE_VALUE_RE.search(serialized)
    if value_hit:
        problems.append(f"回执出现敏感**取值形态**：{value_hit.group(0)}")
    if BODY_SENTINEL in serialized:
        problems.append("回执出现片段正文（哨兵命中）")
    return {
        "checked_scope": "回执 JSON（含 dropped/预算四项/分项计量）",
        "problems": problems,
        "passed": not problems,
    }


def check_ac_149_09() -> dict[str, Any]:
    """AC-149-09（NFR-149-02）：**开关默认关闭** ＋ **关闭即回执零新增字段**（逐字回退）"""
    from app.core.config import settings
    from app.edgerouter.orchestration.context_metrics import ContextReceipt
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    problems: list[str] = []
    from app.core.config import Settings

    switches = (
        "CONTEXT_BUDGET_ENABLED",
        "CONTEXT_CROSS_SEGMENT_COMPETITION_ENABLED",
        "COMPONENT_CHANNEL_ROUTING_ENABLED",
        "WRITEBACK_DECISION_ENABLED",
        "PROFILE_LLM_REFINE_ENABLED",
    )
    # 「出厂默认关闭」＝断言 **Settings 声明默认**（部署无关）；工作区 `.env` 可按批准开启，
    # 生效值仅作环境信息记录，不作为判据（口径同仓内 v1.18.4 订正）。
    declared = {name: Settings.model_fields[name].default for name in switches}
    effective = {name: bool(getattr(settings, name, False)) for name in switches}
    for name, value in declared.items():
        if value is not False:
            problems.append(f"{name} 出厂声明默认应为 False（实测 {value!r}）")

    _prompt, composition = build_prompt(
        count_tokens=_counter, budget=BudgetPolicy(enabled=False), query="问题",
        history_ctx="1. 一条历史素材",
    )
    record = ContextReceipt(request_id="probe-off", composition=composition).to_record()
    extension_fields = (
        "dropped", "over_window", "over_window_tokens", "over_window_recovered",
        "model_window", "output_reserve", "safety_margin", "available_budget",
        "prompt_tokens_before", "prompt_tokens_after", "hard_truncated", "degraded",
    )
    leaked = sorted(name for name in extension_fields if name in record)
    if leaked:
        problems.append(f"关闭预算时回执新增字段（破坏逐字回退）：{leaked}")
    if "budget" in record or "truncated" in record:
        problems.append("关闭预算时不应出现 budget/truncated 段落")
    return {
        "switch_declared_defaults": declared,
        "switch_effective_values": effective,
        "closed_path_keys": sorted(record.keys()),
        "leaked_extension_fields": leaked,
        "problems": problems,
        "passed": not problems,
    }


def check_ac_149_12() -> dict[str, Any]:
    """AC-149-12（超窗率 = 0）：**离线扫掠** —— 可容纳前提下从不超窗；不可容纳时**显式标记**（不静默）"""
    from app.edgerouter.orchestration.prompt_pipeline import BudgetPolicy, build_prompt

    problems: list[str] = []
    checked = 0
    # ① 可容纳：窗口足够大（system ＋ query ＋ 段标记 ＋ 素材上限 均在窗口内）⇒ 超窗率必须为 0
    for window in (1200, 2000, 4096, 8192):
        for material_chars in (0, 200, 1200, 4000):
            policy = BudgetPolicy(
                enabled=True, window_tokens=window, output_reserve_tokens=0,
                safety_margin_tokens=0, quota_ratios={"system": 0.0, "profile": 0.0,
                "memory": 0.0, "rag": 0.0, "history": 1.0},
            )
            history = "\n".join(
                f"{i}. " + f"史{i}" * max(1, material_chars // 20) for i in range(1, 9)
            )
            prompt, composition = build_prompt(
                count_tokens=_counter, budget=policy, query="问" * 10, system_prompt="系" * 50,
                history_ctx=history,
            )
            checked += 1
            if composition.over_window:
                problems.append(
                    f"可容纳输入却判超窗: window={window} material={material_chars} "
                    f"prompt={composition.prompt_total_tokens}"
                )
            if _counter(prompt) != composition.prompt_total_tokens:
                problems.append("回执总 token 与实际 Prompt 不一致（统计口径失真）")

    # ② 不可容纳（system 本身超过窗口）⇒ **必须显式标记**（可判、可统计，不静默）
    tight = BudgetPolicy(enabled=True, window_tokens=100, output_reserve_tokens=0)
    _p, composition = build_prompt(
        count_tokens=_counter, budget=tight, query="问" * 10, system_prompt="系" * 500
    )
    if not composition.over_window:
        problems.append("不可容纳输入未被显式标记（静默超窗，违反 AC-149-12 可观测要求）")
    return {
        "swept_cases": checked,
        "over_window_rate": 0.0 if not problems else None,
        "problems": problems,
        "passed": not problems,
    }


def check_config_keys_declared() -> dict[str, Any]:
    """**结构护栏**：凡经 `getattr(settings, "KEY"...)` 读取的键，**必须**在 `Settings` 显式声明

    **动因（真实缺陷）**：本仓 `Settings` 为 `extra=forbid` ⇒ 未声明的键既**无法**经 `.env`
    配置（dotenv 源下还会触发校验失败）⇒ 仅靠 `getattr` 读取的开关是**死开关**：
    功能在生产**不可达**。该缺陷由本探针的 AC-149-09 检查首次暴露（I-1 跨段竞争池开关）。

    **口径**：只扫描 `getattr(settings, "<字面量键>"` 形态；白名单仅限**确有理由**的键。
    """
    import re as _re

    from app.core.config import Settings

    pattern = _re.compile(r'getattr\(\s*settings\s*,\s*"([A-Z][A-Z0-9_]*)"')
    declared = set(Settings.model_fields)
    #: 白名单：允许「读取但未声明」的键（必须逐项给出理由）
    whitelist: dict[str, str] = {}
    app_root = os.path.join(_BACKEND_ROOT, "app")
    used: dict[str, list[str]] = {}
    for dirpath, _dirnames, filenames in os.walk(app_root):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(dirpath, filename)
            with open(path, encoding="utf-8") as handle:
                for match in pattern.finditer(handle.read()):
                    used.setdefault(match.group(1), []).append(
                        os.path.relpath(path, _BACKEND_ROOT).replace("\\", "/")
                    )
    undeclared = sorted(name for name in used if name not in declared and name not in whitelist)
    return {
        "backend_root": _BACKEND_ROOT,
        "read_keys": len(used),
        "declared_keys": len(declared),
        "whitelist": whitelist,
        "undeclared": {name: sorted(set(used[name])) for name in undeclared},
        "passed": not undeclared,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="v1.4.9 回执齐备率与纯度取证")
    parser.add_argument("--json", dest="json_out", default=None)
    args = parser.parse_args()

    payload = {
        "AC-149-05": check_ac_149_05(),
        "AC-149-09": check_ac_149_09(),
        "AC-149-10": check_ac_149_10(),
        "AC-149-11": check_ac_149_11(),
        "AC-149-12": check_ac_149_12(),
        "structural:config_keys_declared": check_config_keys_declared(),
    }
    for name, result in payload.items():
        flag = "PASS" if result["passed"] else "FAIL"
        print(f"[{flag}] {name}")
        for problem in result.get("problems", []) or result.get("violations", []):
            if isinstance(problem, str):
                print(f"        - {problem}")
        for key, files in (result.get("undeclared") or {}).items():
            print(f"        - 未声明配置键 {key}（读取点：{', '.join(files)}）")

    target = args.json_out or os.path.join(
        _EVIDENCE_DIR, "v149_receipt_and_purity_probe-result.json"
    )
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"结果已写入：{target}")
    return 0 if all(item["passed"] for item in payload.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
