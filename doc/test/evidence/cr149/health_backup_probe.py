"""CR-149 第二批运行态证据：备通道健康探针（方案 §4.1「配套两项必做」之一）

在**真实网关探测函数**下取证：`GET /openllm/v1/health` 的 `components` 是否**同时**
给出外部三组件与**备通道事实**（内置 RAG 底座 / Ollama 可达性），使「备通道存在但无内容」
这一静默劣化**前置可视化**。

本脚本调用真实实现：
  - `_probe_components(db)`（并行探测入口；`db=None` 时 KB 行数按 0 计并显式标注）
  - `_probe_builtin_rag(db)` / `_count_faiss_indexes(FAISS_ROOT)` / `_probe_ollama()`

用法（在 OpenLLM/backend 下）::

    python <此脚本>
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from app.api import openllm_gateway as gateway  # noqa: E402
from app.api.openllm_gateway import (  # noqa: E402
    _count_faiss_indexes,
    _probe_builtin_rag,
    _probe_ollama,
)
from app.services.vector_store import FAISS_ROOT  # noqa: E402


async def main() -> dict:
    # 绕过探测缓存，取本次真实结果
    gateway._health_cache = {}
    gateway._health_cache_ts = 0.0

    builtin = await _probe_builtin_rag(None)
    ollama = await _probe_ollama()
    components = await gateway._probe_components(None)

    return {
        "faiss_root": FAISS_ROOT,
        "faiss_root_exists": os.path.isdir(FAISS_ROOT),
        "faiss_indexes_scanned": _count_faiss_indexes(FAISS_ROOT),
        "builtin_rag_probe": builtin,
        "ollama_probe": ollama,
        "components_keys": sorted(components),
        "health_components": components,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main()), ensure_ascii=False, indent=2))
