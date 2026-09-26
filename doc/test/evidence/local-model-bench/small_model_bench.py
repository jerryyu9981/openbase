"""本地小模型精炼对比基准（Ollama，精度 × 时延）

用途：为「上下文精炼」选型提供可复现的对比数据 —— 在同一个 Ollama 端点上跑同一套
中文评测集，比较候选小模型在四类精炼任务上的**精度**与**时延**，产出一份可用于
「精准度 / 时延」权衡决策的报告。

评测任务（与 `OpenBase-上下文精装配与组件通道优化技术方案-v1.0.0.md` §5.3 一一对应）：

| 任务 | 输入 | 期望输出 | 精度指标 |
|------|------|----------|----------|
| route      | 一条用户问题 | JSON `{"need_memory":bool,"need_rag":bool}` | 逐字段 F1 / 完全一致率 / JSON 合规率 |
| select     | 问题 + 10 条候选条目（含标注相关项） | 相关条目编号 | 与标注的精确率 / 召回率 / F1 |
| compress   | 问题 + 5 条长条目 | 编号要点列表（抽取式压缩） | 关键事实保留率 / 压缩率 / 格式合规率 |
| summarize  | 1 条长记忆 | 一句话要点 | 关键事实保留率 / 压缩率 / 格式合规率 |

时延口径：**预热后**单次调用的墙钟耗时（P50/P95），并从 Ollama 响应读取
`total_duration` / `load_duration` / `prompt_eval_*` / `eval_count` / `eval_duration`
计算 tokens/s、首包加载耗时；失败调用单独计数（不计入分位）。

用法::

    python small_model_bench.py --models qwen2.5:0.5b,llama3.2:1b,qwen3:0.6b
    python small_model_bench.py --models qwen3.5:0.8b --tasks route,select
    python small_model_bench.py --dump-dataset          # 只导出评测集

退出码：0＝批次完成（达标与否见输出与报告 JSON）。
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_BASE = "http://192.168.0.4:11434"
DEFAULT_OUT = Path(__file__).resolve().parent
DEFAULT_TASKS = ("route", "select", "compress", "summarize")
ALL_TASKS = ("route", "select", "compress", "summarize")

# 统一生成参数（跨模型一致，保证可比）
DEFAULT_NUM_PREDICT = {"route": 64, "select": 96, "compress": 192, "summarize": 128}
NUM_CTX = 4096
SEED = 20260927
TEMPERATURE = 0.0

# ---------------------------------------------------------------------------
# 评测集（确定性合成；领域取自本项目真实语义，带可判定的关键事实）
# ---------------------------------------------------------------------------

KB_MARKER = "AGENT-CTX-KB-20260926"
BUDGET_CODE = "CONTEXT-BUDGET-4096"

_LONG_ENTRIES = [
    (
        "会话编排的读侧顺序固定为 auth → profile_fetch → memory/rag → 上下文装配 → llm。"
        "知识库样本标识为 {kb}，预算代号 {budget}，端到端实测 21.4 秒通过。"
        "回写侧三路（memory / rag / profile）逐路独立入队，权威回执以回写队列表为准。"
    ).format(kb=KB_MARKER, budget=BUDGET_CODE),
    (
        "记忆往返闭环的判据：同一主体连续两轮对话，第 2 轮记忆段注入 5 条、"
        "segment_tokens.memory 应大于 0；读路径资源键为 {tenant}_{user} 形态，"
        "回写必须用同一事实源派生，否则落在两个键上导致永不沉淀。"
    ).format(tenant="tenant-1", user="179fc89c"),
    (
        "知识库段落检索命中真实 OpenRAG 时 rag_source=external；外部不可用且开启回退开关时"
        "rag_source=builtin，但内置 RAG 需要本租户存在知识库记录与 FAISS 索引，"
        "本环境实测知识库表 0 行、索引目录 0 个，因此接管后注入为空。"
    ),
    (
        "画像段由 DPS 提供，固定注入且不受组件路由影响；拉取失败开启 30 秒负缓存，"
        "避免每次对话重复付出约 2.04 秒的连接代价，总开关为 PROFILE_INJECTION_ENABLED。"
    ),
    (
        "组件路由阈值 0.85：单次关键词命中置信度 0.8 不达标，回落最优候选；"
        "同一规则命中两次为 0.95，进入信号并集，于是记忆与知识库同时装配，路径为 C。"
    ),
    (
        "回写队列幂等键为 (session_id, seq, target)，seq 取持久化 max_seq+1；"
        "最大重试 3 次、退避基数 0.5 秒；启动恢复施加 30 分钟时间窗与 200 行条数上界。"
    ),
]

_OFF_TOPIC_ENTRIES = [
    "差旅报销标准：市内交通单次不超过 80 元，跨城高铁需附行程单，住宿上限按城市分级。",
    "机房巡检要点：每周检查 UPS 电池电压、空调回风温度与消防喷淋压力，异常记入台账。",
    "番茄牛腩做法：牛腩冷水下锅焯水，加番茄与洋葱小火炖 90 分钟，最后收汁调味。",
    "马拉松备赛：赛前 3 周逐步减量，周跑量从 60 公里降到 35 公里，赛前 2 天补碳水。",
    "台风蓝色预警：沿海风力 8 级以上，渔船回港避风，停止高空与水上作业。",
    "前端构建优化：开启 tree-shaking 与代码分割，首屏体积从 1.8MB 降到 620KB。",
]

_COMPRESS_FACTS = [
    [KB_MARKER, BUDGET_CODE, "21.4"],
    ["5", "0", "tenant-1"],
    ["external", "builtin", "0"],
    ["DPS", "30", "2.04"],
    ["0.85", "0.8", "0.95", "C"],
    ["3", "0.5", "30", "200"],
]

_ROUTE_CASES = [
    ("请结合我的偏好和知识库资料，说明会话编排的前置与回写闭环是怎么设计的？", True, True),
    ("我上次说的那个偏好，你还记得吗？", True, False),
    ("知识库里关于回写队列的技术资料有哪些？", False, True),
    ("公司差旅住宿的报销标准是多少？", False, True),
    ("我的记忆里有没有记录过项目预算代号？", True, False),
    ("把知识库文档里关于上下文装配的章节要点列出来。", False, True),
    ("根据我的偏好来组织回答，同时引用知识库里的编排顺序。", True, True),
    ("什么是向量数据库？", False, False),
    ("之前提到的启动恢复上界是多少？", True, False),
    ("资料里有没有写内置 RAG 的索引要求？", False, True),
    ("我的画像里记录了哪些偏好维度？", True, False),
    ("知识库里的样本标识是什么？", False, True),
]

_SELECT_QUERY = "会话编排前置与回写闭环的设计要点是什么？"
_SELECT_GOLD = [0, 2, 4, 5]  # 与查询相关的条目下标（0-based）
_SUMMARIZE_ENTRY = _LONG_ENTRIES[0]
_SUMMARIZE_FACTS = [KB_MARKER, BUDGET_CODE, "21.4", "memory", "rag", "profile"]


def build_dataset() -> dict[str, Any]:
    """构造评测集（确定性；含 gold 标注）"""
    compress_items = [
        {
            "id": f"compress-{index + 1}",
            "query": "会话编排的前置与回写闭环有哪些关键事实？",
            "entries": _LONG_ENTRIES,
            "gold_facts": _COMPRESS_FACTS[index % len(_COMPRESS_FACTS)],
        }
        for index in range(len(_LONG_ENTRIES))
    ]
    select_items = []
    for index in range(6):
        entries = []
        for slot in range(10):
            if slot in _SELECT_GOLD:
                entries.append(_LONG_ENTRIES[(slot + index) % len(_LONG_ENTRIES)])
            else:
                entries.append(_OFF_TOPIC_ENTRIES[(slot + index) % len(_OFF_TOPIC_ENTRIES)])
        select_items.append(
            {
                "id": f"select-{index + 1}",
                "query": _SELECT_QUERY,
                "entries": entries,
                "gold_indices": _SELECT_GOLD,
            }
        )
    route_items = [
        {"id": f"route-{index + 1}", "query": query, "need_memory": memory, "need_rag": rag}
        for index, (query, memory, rag) in enumerate(_ROUTE_CASES)
    ]
    summarize_items = [
        {"id": f"summarize-{index + 1}", "entry": entry, "gold_facts": _SUMMARIZE_FACTS}
        for index, entry in enumerate(_LONG_ENTRIES[:5])
    ]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": SEED,
        "tasks": {
            "route": route_items,
            "select": select_items,
            "compress": compress_items,
            "summarize": summarize_items,
        },
    }


# ---------------------------------------------------------------------------
# Prompt（跨模型完全一致）
# ---------------------------------------------------------------------------

_SYSTEM = (
    "你是上下文精炼器。只允许抽取或改写输入中已出现的信息，"
    "禁止引入输入中不存在的事实、实体、数字或结论。严格按要求的格式输出。"
)


def _numbered(entries: list[str]) -> str:
    return "\n".join(f"{index + 1}. {text}" for index, text in enumerate(entries))


def build_prompt(task: str, item: dict[str, Any]) -> str:
    if task == "route":
        return (
            "判断下面这条用户问题需要检索哪类上下文。\n"
            "memory：需要用户历史记忆/偏好；rag：需要知识库/文档资料。\n"
            '只输出 JSON，不要解释：{"need_memory": true/false, "need_rag": true/false}\n\n'
            f"用户问题：{item['query']}"
        )
    if task == "select":
        return (
            f"用户问题：{item['query']}\n\n候选条目：\n{_numbered(item['entries'])}\n\n"
            "输出与该问题相关的条目编号，按相关性从高到低排列。\n"
            "只输出编号，用英文逗号分隔（例如：3,7,1）。不要输出其他内容。"
        )
    if task == "compress":
        return (
            f"用户问题：{item['query']}\n\n原始条目：\n{_numbered(item['entries'])}\n\n"
            "把上述条目压缩为不超过 5 条要点，每条一句话，保留关键标识、数字与专有名词。\n"
            "输出编号列表，每行一条，格式：1. 要点。不要输出解释或前言。"
        )
    if task == "summarize":
        return (
            f"原始记忆：\n{item['entry']}\n\n"
            "把它压缩为不超过 2 句话的要点，保留关键标识、数字与专有名词。\n"
            "只输出要点本身，不要编号，不要解释。"
        )
    raise ValueError(f"未知任务: {task}")


# ---------------------------------------------------------------------------
# Ollama 调用
# ---------------------------------------------------------------------------

def _post(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, Any]:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST"
    )
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except Exception as exc:  # noqa: BLE001 - 网络层异常统一返回 -1
        return -1, f"{type(exc).__name__}: {exc}"


def chat_once(
    base: str, model: str, prompt: str, task: str, timeout: float
) -> dict[str, Any]:
    """单次调用（非流式）；返回文本 + 时延 + Ollama 计数；失败返回 error"""
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": TEMPERATURE,
            "num_ctx": NUM_CTX,
            "num_predict": DEFAULT_NUM_PREDICT[task],
            "seed": SEED,
        },
    }
    started = time.perf_counter()
    status, body = _post(f"{base}/api/chat", payload, timeout)
    elapsed_ms = (time.perf_counter() - started) * 1000
    if status == 400 and isinstance(body, str) and "think" in body:
        # 兼容不支持 think 字段的旧端点
        payload.pop("think", None)
        started = time.perf_counter()
        status, body = _post(f"{base}/api/chat", payload, timeout)
        elapsed_ms = (time.perf_counter() - started) * 1000
    if status != 200 or not isinstance(body, dict):
        return {"ok": False, "error": f"http={status} {str(body)[:200]}", "elapsed_ms": elapsed_ms}
    message = body.get("message") or {}
    content = str(message.get("content") or "")
    thinking = str(message.get("thinking") or "")
    return {
        "ok": True,
        "raw": content,
        "thinking_chars": len(thinking),
        "elapsed_ms": round(elapsed_ms, 1),
        "total_duration_ms": round((body.get("total_duration") or 0) / 1e6, 1),
        "load_duration_ms": round((body.get("load_duration") or 0) / 1e6, 1),
        "prompt_eval_count": body.get("prompt_eval_count"),
        "eval_count": body.get("eval_count"),
        "eval_duration_ms": round((body.get("eval_duration") or 0) / 1e6, 1),
    }


def list_loaded(base: str) -> list[dict[str, Any]]:
    try:
        with urllib.request.urlopen(f"{base}/api/ps", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return []
    return list(payload.get("models") or [])


# ---------------------------------------------------------------------------
# 评测与打分
# ---------------------------------------------------------------------------

_THINK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.S | re.I)


def normalize_text(text: str) -> str:
    cleaned = _THINK_RE.sub(" ", text or "")
    cleaned = cleaned.replace("**", "").replace("`", "")
    return cleaned


def parse_indices(text: str, upper: int) -> list[int]:
    cleaned = normalize_text(text)
    found: list[int] = []
    for token in re.findall(r"\d{1,2}", cleaned):
        value = int(token)
        if 1 <= value <= upper and value not in found:
            found.append(value)
    return found


def parse_json_route(text: str) -> dict[str, Any] | None:
    cleaned = normalize_text(text)
    match = re.search(r"\{.*\}", cleaned, re.S)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("need_memory"), bool) or not isinstance(
        payload.get("need_rag"), bool
    ):
        return None
    return payload


def fact_recall(text: str, facts: list[str]) -> float:
    cleaned = normalize_text(text)
    if not facts:
        return 0.0
    hit = sum(1 for fact in facts if fact in cleaned)
    return round(hit / len(facts), 4)


def format_ok_list(text: str, max_items: int) -> bool:
    cleaned = normalize_text(text)
    numbered = re.findall(r"^\s*\d+[.、)]\s*\S", cleaned, re.M)
    return 0 < len(numbered) <= max_items


def score_item(task: str, item: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """按任务打分（精度指标）"""
    if not result.get("ok"):
        return {"error": result.get("error")}
    text = result["raw"]
    if task == "route":
        parsed = parse_json_route(text)
        if parsed is None:
            return {
                "json_ok": False,
                "exact": False,
                "memory_hit": False,
                "rag_hit": False,
            }
        memory_hit = parsed["need_memory"] == bool(item["need_memory"])
        rag_hit = parsed["need_rag"] == bool(item["need_rag"])
        return {
            "json_ok": True,
            "exact": memory_hit and rag_hit,
            "memory_hit": memory_hit,
            "rag_hit": rag_hit,
        }
    if task == "select":
        picked = parse_indices(text, len(item["entries"]))
        gold = {index + 1 for index in item["gold_indices"]}
        hit = set(picked) & gold
        precision = len(hit) / len(picked) if picked else 0.0
        recall = len(hit) / len(gold) if gold else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        return {
            "format_ok": bool(picked),
            "picked": picked,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
    if task == "compress":
        return {
            "format_ok": format_ok_list(text, 5),
            "fact_recall": fact_recall(text, item["gold_facts"]),
            "compression_ratio": round(
                len(normalize_text(text)) / max(1, sum(len(e) for e in item["entries"])), 4
            ),
        }
    if task == "summarize":
        return {
            "format_ok": bool(normalize_text(text).strip()),
            "fact_recall": fact_recall(text, item["gold_facts"]),
            "compression_ratio": round(
                len(normalize_text(text)) / max(1, len(item["entry"])), 4
            ),
        }
    raise ValueError(task)


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int(-(-len(ordered) * quantile // 1))))
    return round(ordered[rank - 1], 1)


def summarize_task(task: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok_rows = [row for row in rows if row.get("ok")]
    latencies = [float(row["elapsed_ms"]) for row in ok_rows]
    tokens_per_second = [
        round(
            (row["eval_count"] or 0) / (row["eval_duration_ms"] / 1000), 2
        )
        for row in ok_rows
        if row.get("eval_duration_ms")
    ]
    report: dict[str, Any] = {
        "n": len(rows),
        "ok": len(ok_rows),
        "failed": len(rows) - len(ok_rows),
        "latency_ms": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "max": round(max(latencies), 1) if latencies else 0.0,
        },
        "tokens_per_second_p50": percentile(tokens_per_second, 0.50),
    }
    if not ok_rows:
        return report
    if task == "route":
        report["json_ok_rate"] = round(
            sum(1 for row in ok_rows if row["score"].get("json_ok")) / len(ok_rows), 4
        )
        report["exact_rate"] = round(
            sum(1 for row in ok_rows if row["score"].get("exact")) / len(ok_rows), 4
        )
        report["field_accuracy"] = round(
            sum(
                (1 if row["score"].get("memory_hit") else 0)
                + (1 if row["score"].get("rag_hit") else 0)
                for row in ok_rows
            )
            / (2 * len(ok_rows)),
            4,
        )
        report["primary_metric"] = "field_accuracy"
        report["primary_value"] = report["field_accuracy"]
    elif task == "select":
        report["f1"] = round(sum(row["score"]["f1"] for row in ok_rows) / len(ok_rows), 4)
        report["precision"] = round(
            sum(row["score"]["precision"] for row in ok_rows) / len(ok_rows), 4
        )
        report["recall"] = round(
            sum(row["score"]["recall"] for row in ok_rows) / len(ok_rows), 4
        )
        report["format_ok_rate"] = round(
            sum(1 for row in ok_rows if row["score"].get("format_ok")) / len(ok_rows), 4
        )
        report["primary_metric"] = "f1"
        report["primary_value"] = report["f1"]
    else:
        report["fact_recall"] = round(
            sum(row["score"]["fact_recall"] for row in ok_rows) / len(ok_rows), 4
        )
        report["compression_ratio"] = round(
            sum(row["score"]["compression_ratio"] for row in ok_rows) / len(ok_rows), 4
        )
        report["format_ok_rate"] = round(
            sum(1 for row in ok_rows if row["score"].get("format_ok")) / len(ok_rows), 4
        )
        report["primary_metric"] = "fact_recall"
        report["primary_value"] = report["fact_recall"]
    return report


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_model(
    base: str,
    model: str,
    tasks: tuple[str, ...],
    dataset: dict[str, Any],
    timeout: float,
    repeats: int,
    limit_items: int = 0,
) -> dict[str, Any]:
    result: dict[str, Any] = {"model": model, "tasks": {}, "warmup": {}, "unavailable": False}
    # 预热（加载模型，不计入时延分位）
    warm = chat_once(base, model, build_prompt("route", dataset["tasks"]["route"][0]), "route", timeout)
    result["warmup"] = {
        "ok": warm.get("ok"),
        "error": warm.get("error"),
        "load_duration_ms": warm.get("load_duration_ms"),
        "elapsed_ms": warm.get("elapsed_ms"),
    }
    loaded = next((item for item in list_loaded(base) if item.get("name") == model), None)
    result["runtime"] = {
        "size_vram_bytes": (loaded or {}).get("size_vram"),
        "size_bytes": (loaded or {}).get("size"),
        "inference": ("gpu" if (loaded or {}).get("size_vram") else "cpu_or_partial"),
    }
    if not warm.get("ok"):
        result["unavailable"] = True
        return result
    for task in tasks:
        rows: list[dict[str, Any]] = []
        items = dataset["tasks"][task]
        if limit_items:
            items = items[:limit_items]
        for _ in range(repeats):
            for item in items:
                outcome = chat_once(
                    base, model, build_prompt(task, item), task, timeout
                )
                row = {
                    "id": item["id"],
                    "ok": outcome.get("ok"),
                    "error": outcome.get("error"),
                    "elapsed_ms": outcome.get("elapsed_ms"),
                    "eval_count": outcome.get("eval_count"),
                    "eval_duration_ms": outcome.get("eval_duration_ms"),
                    "thinking_chars": outcome.get("thinking_chars"),
                    "raw_preview": (normalize_text(outcome.get("raw") or ""))[:200],
                }
                row["score"] = score_item(task, item, outcome)
                rows.append(row)
        result["tasks"][task] = {"aggregate": summarize_task(task, rows), "rows": rows}
        print(
            f"  [{model}] {task}: 精度 {result['tasks'][task]['aggregate'].get('primary_metric')}"
            f"={result['tasks'][task]['aggregate'].get('primary_value')} "
            f"P50={result['tasks'][task]['aggregate']['latency_ms']['p50']}ms "
            f"P95={result['tasks'][task]['aggregate']['latency_ms']['p95']}ms"
        )
    return result


RULE_BASELINE_MODEL = "rule-baseline(no-model)"


def _rule_baseline(dataset: dict[str, Any]) -> dict[str, Any]:
    """解析式基线（不调用模型）：全部条目原样保留 → 用于衡量「精炼」的增益/代价

    仅 compress/summarize/select 有确定性的解析值；route 的标注源自规则语义，
    不构造自证基线。时延按 0 计（规则档无额外推理）。
    """
    compress_ratio = 1.0
    select_precision = len(_SELECT_GOLD) / 10.0
    select_recall = 1.0
    select_f1 = (
        2 * select_precision * select_recall / (select_precision + select_recall)
    )
    zero_latency = {"p50": 0.0, "p95": 0.0, "max": 0.0}
    return {
        "model": RULE_BASELINE_MODEL,
        "unavailable": False,
        "runtime": {"inference": "n/a(规则档)", "size_vram_bytes": 0, "size_bytes": 0},
        "tasks": {
            "compress": {
                "aggregate": {
                    "n": len(dataset["tasks"]["compress"]), "ok": len(dataset["tasks"]["compress"]),
                    "failed": 0, "latency_ms": zero_latency, "tokens_per_second_p50": 0.0,
                    "fact_recall": 1.0, "compression_ratio": compress_ratio,
                    "format_ok_rate": 1.0, "primary_metric": "fact_recall", "primary_value": 1.0,
                    "note": "原文原样保留（未压缩）",
                },
                "rows": [],
            },
            "summarize": {
                "aggregate": {
                    "n": len(dataset["tasks"]["summarize"]), "ok": len(dataset["tasks"]["summarize"]),
                    "failed": 0, "latency_ms": zero_latency, "tokens_per_second_p50": 0.0,
                    "fact_recall": 1.0, "compression_ratio": 1.0,
                    "format_ok_rate": 1.0, "primary_metric": "fact_recall", "primary_value": 1.0,
                    "note": "原文原样保留（未压缩）",
                },
                "rows": [],
            },
            "select": {
                "aggregate": {
                    "n": len(dataset["tasks"]["select"]), "ok": len(dataset["tasks"]["select"]),
                    "failed": 0, "latency_ms": zero_latency, "tokens_per_second_p50": 0.0,
                    "f1": round(select_f1, 4), "precision": select_precision, "recall": select_recall,
                    "format_ok_rate": 1.0, "primary_metric": "f1",
                    "primary_value": round(select_f1, 4),
                    "note": "全选（不做相关性筛选）",
                },
                "rows": [],
            },
        },
    }


def _ranking(payload: dict[str, Any], task: str) -> list[tuple[str, float, float]]:
    """按（主指标降序、P95 升序）给出该任务的候选排序"""
    rows: list[tuple[str, float, float]] = []
    for model, entry in payload["results"].items():
        task_entry = (entry.get("tasks") or {}).get(task)
        if not task_entry:
            continue
        agg = task_entry["aggregate"]
        rows.append(
            (model, float(agg.get("primary_value") or 0.0), float(agg["latency_ms"]["p95"]))
        )
    rows.sort(key=lambda item: (-item[1], item[2]))
    return rows


def write_report(out_dir: Path, payload: dict[str, Any]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d")
    tag = payload.get("tag") or ""
    suffix = f"-{tag}" if tag else ""
    json_path = out_dir / f"small-model-bench-{stamp}{suffix}.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines: list[str] = []
    lines.append("# 本地小模型精炼对比（Ollama，精度 × 时延）")
    lines.append("")
    lines.append(f"- 执行时间：{payload['generated_at']}")
    lines.append(f"- Ollama 端点：{payload['base_url']}（版本 {payload.get('server_version')}）")
    lines.append(f"- 生成参数：temperature=0、num_ctx={NUM_CTX}、seed={SEED}、think=false")
    lines.append(f"- 候选模型：{', '.join(payload['models'])}")
    lines.append("- 解析式基线：原文原样保留（不调用模型），用于衡量精炼的精度代价与压缩收益")
    lines.append("")
    csv_rows: list[str] = [
        "task,model,primary_metric,primary_value,p50_ms,p95_ms,tokens_per_second_p50,failed,"
        "compression_ratio,format_ok_rate"
    ]
    for task in payload["tasks"]:
        lines.append(f"## 任务：{task}")
        lines.append("")
        lines.append("| 模型 | 主指标 | 值 | 时延 P50 (ms) | 时延 P95 (ms) | tok/s (P50) | 压缩率 | 失败数 | 推理位置 |")
        lines.append("|------|--------|----|---------------|---------------|-------------|--------|--------|----------|")
        for model, entry in payload["results"].items():
            task_entry = (entry.get("tasks") or {}).get(task)
            if not task_entry:
                continue
            agg = task_entry["aggregate"]
            runtime = entry.get("runtime", {})
            lines.append(
                f"| {model} | {agg.get('primary_metric')} | {agg.get('primary_value')} | "
                f"{agg['latency_ms']['p50']} | {agg['latency_ms']['p95']} | "
                f"{agg.get('tokens_per_second_p50')} | {agg.get('compression_ratio', '-')} | "
                f"{agg['failed']} | {runtime.get('inference', '-')} |"
            )
            csv_rows.append(
                f"{task},{model},{agg.get('primary_metric')},{agg.get('primary_value')},"
                f"{agg['latency_ms']['p50']},{agg['latency_ms']['p95']},"
                f"{agg.get('tokens_per_second_p50')},{agg['failed']},"
                f"{agg.get('compression_ratio', '')},{agg.get('format_ok_rate', '')}"
            )
        lines.append("")
        ranking = _ranking(payload, task)
        if ranking:
            lines.append(
                "排序（主指标降序、P95 升序）："
                + "；".join(
                    f"{index + 1}. {model}（{value}／{p95}ms）"
                    for index, (model, value, p95) in enumerate(ranking)
                )
            )
            lines.append("")
    csv_path = out_dir / f"small-model-bench-{stamp}{suffix}.csv"
    csv_path.write_text("\n".join(csv_rows) + "\n", encoding="utf-8")
    unavailable = [
        model
        for model, entry in payload["results"].items()
        if entry.get("unavailable")
    ]
    if unavailable:
        lines.append("## 不可用模型")
        lines.append("")
        lines.append("；".join(unavailable) + "（端点未找到该模型，未参与评测）")
        lines.append("")
    md_path = out_dir / f"small-model-bench-{stamp}{suffix}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--models", default="qwen2.5:0.5b,llama3.2:1b")
    parser.add_argument("--tag", default="", help="报告文件名标签（同一日多次运行区分）")
    parser.add_argument("--tasks", default=",".join(DEFAULT_TASKS))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--limit-items", type=int, default=0, help="每任务仅取前 N 条（快速试跑）"
    )
    parser.add_argument("--dump-dataset", action="store_true")
    parser.add_argument(
        "--no-rule-baseline", action="store_true", help="不写入解析式基线行"
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset = build_dataset()
    dataset_path = out_dir / "dataset_refine_bench.json"
    if not dataset_path.exists():
        dataset_path.write_text(
            json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.dump_dataset:
        print(f"评测集已导出: {dataset_path}")
        return 0

    tasks = tuple(t for t in args.tasks.split(",") if t in ALL_TASKS)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    server_version = ""
    try:
        with urllib.request.urlopen(f"{args.base_url}/api/version", timeout=10) as resp:
            server_version = json.loads(resp.read().decode("utf-8")).get("version", "")
    except Exception:  # noqa: BLE001
        print(f"[FAIL] Ollama 端点不可达：{args.base_url}")
        return 1

    payload: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "server_version": server_version,
        "models": models,
        "tasks": list(tasks),
        "tag": args.tag,
        "limit_items": args.limit_items,
        "dataset": {"path": str(dataset_path), "seed": SEED},
        "results": {},
    }
    for model in models:
        print(f"[model] {model}")
        payload["results"][model] = run_model(
            args.base_url, model, tasks, dataset, args.timeout, args.repeats,
            args.limit_items,
        )
    if not args.no_rule_baseline:
        payload["results"][RULE_BASELINE_MODEL] = _rule_baseline(dataset)
    json_path = write_report(out_dir, payload)
    print(f"报告: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
