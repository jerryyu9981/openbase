"""数据修正（续）：把其余**未部署**的本地模型置 inactive，并复验门禁候选

背景（2026-09-22 定点探测）：`qwen3:0.6b` / `qwen2.5:0.5b` / `llama3.2:1b` 三者在 ollama(-lan)
provider 下**均不可达**（HTTP 500 / `5001 LLM 组件调用失败`），而 `deepseek-v4-flash` 正常（200）；
三者价格均为 NULL → 成本评分 0 → 在「成本优先」下天然胜出 → 被反复选中并失败。

回滚 SQL（按 model_code 恢复，如需精确回滚请按 id 定位）：
  UPDATE llm_models SET status='active' WHERE provider_id IN
    (SELECT id FROM llm_providers WHERE provider_code IN ('ollama','ollama-lan'));
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text

_BACKEND_ROOT = Path(r"D:\Trae CN\myproject\Dev\OpenLLM\backend")
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.api import openllm_gateway as gateway  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.model import Model as LLMModel  # noqa: E402
from app.models.provider import Provider  # noqa: E402

UNDEPLOYED_PROVIDER_CODES = ("ollama", "ollama-lan")


def _active_rows(session) -> list[dict]:
    return [
        dict(row)
        for row in session.execute(
            text(
                "SELECT m.model_code, m.status, p.provider_code, p.status AS provider_status "
                "FROM llm_models m LEFT JOIN llm_providers p ON p.id = m.provider_id "
                "WHERE m.status = 'active' ORDER BY m.model_code"
            )
        ).mappings().all()
    ]


def main() -> int:
    with SessionLocal() as session:
        print("=== [只读] 修正前 active 模型 ===")
        for row in _active_rows(session):
            print("  " + json.dumps(row, ensure_ascii=False, default=str))

        result = session.execute(
            text(
                "UPDATE llm_models SET status = 'inactive' WHERE status = 'active' AND provider_id IN "
                "(SELECT id FROM llm_providers WHERE provider_code = ANY(:codes))"
            ),
            {"codes": list(UNDEPLOYED_PROVIDER_CODES)},
        )
        session.commit()
        print(f"=== [数据修正] 未部署本地模型置 inactive：affected_rows={result.rowcount} ===")
        print("=== [只读] 修正后 active 模型 ===")
        for row in _active_rows(session):
            print("  " + json.dumps(row, ensure_ascii=False, default=str))

        # 复验门禁候选（新代码 + 真实数据）
        gateway._get_model_router.cache_clear()
        router = gateway._get_model_router()
        models = session.query(LLMModel).filter(LLMModel.status == "active").all()
        providers_by_id = {str(provider.id): provider for provider in session.query(Provider).all()}
        candidates, skipped = gateway._build_model_candidates(models, providers_by_id, router)
        print(f"=== [门禁] 候选 {len(candidates)} 个；跳过 {skipped} 个 ===")
        for candidate in candidates:
            print(f"  code={candidate.model_code} health={candidate.health_status} fail_count={candidate.fail_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
