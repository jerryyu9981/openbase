"""DT-148-015 数据修正 + 进程内门禁验证（真实 DB + 新代码）

① 数据修正：把**未部署**的 `qwen3:0.6b` active 行置为 `inactive`
   （该模型在 ollama provider 下不可达 → 定点探测 HTTP 500/5001；同模型另有 6 行已是 inactive）
   回滚 SQL：UPDATE llm_models SET status='active' WHERE model_code='qwen3:0.6b' AND status='inactive';
   （注：回滚会同时激活其余 inactive 行，如需精确回滚请按 id 定位）

② 门禁验证（新代码）：
   - 用真实 `llm_models`/`llm_providers` 构建候选 → 打印 provider 门禁与真实健康透传结果；
   - 对选中模型连续记 3 次失败 → 再次构建候选 → 该模型应被**健康过滤排除**。
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


def _print_models(session, title: str) -> None:
    rows = session.execute(
        text(
            "SELECT m.model_code, m.status, p.provider_code, p.status AS provider_status, p.health_status "
            "FROM llm_models m LEFT JOIN llm_providers p ON p.id = m.provider_id "
            "WHERE m.status = 'active' ORDER BY m.model_code"
        )
    ).mappings().all()
    print(f"=== {title}（active 模型 {len(rows)} 行）===")
    for row in rows:
        print("  " + json.dumps(dict(row), ensure_ascii=False, default=str))


def main() -> int:
    with SessionLocal() as session:
        _print_models(session, "修正前")

        result = session.execute(
            text("UPDATE llm_models SET status = 'inactive' WHERE model_code = 'qwen3:0.6b' AND status = 'active'")
        )
        session.commit()
        print(f"=== [数据修正] 未部署模型置 inactive：affected_rows={result.rowcount} ===")
        _print_models(session, "修正后")

        # ---- 门禁验证（新代码，真实数据） ----
        gateway._get_model_router.cache_clear()
        router = gateway._get_model_router()
        models = session.query(LLMModel).filter(LLMModel.status == "active").all()
        providers_by_id = {str(provider.id): provider for provider in session.query(Provider).all()}
        candidates, skipped = gateway._build_model_candidates(models, providers_by_id, router)
        print(f"=== [门禁] 候选 {len(candidates)} 个；因 provider 不可用跳过 {skipped} 个 ===")
        for candidate in candidates:
            print(
                f"  code={candidate.model_code} health={candidate.health_status} "
                f"fail_count={candidate.fail_count} price_in={candidate.input_price}"
            )

        decision = router.select_model(
            request_context=None,
            candidates=candidates,
            config={"required_capabilities": ["chat"], "cost_weight": 0.4, "latency_weight": 0.3},
        )
        selected_id = (decision or {}).get("selected_model")
        code_by_id = {candidate.model_id: candidate.model_code for candidate in candidates}
        print(f"=== [门禁] 首次选中: {code_by_id.get(selected_id)}（reason={decision.get('reason', '')[:90]}…）===")

        # 模拟该模型连续 3 次调用失败 → 熔断 open → 应被排除
        for _ in range(3):
            router.record_failure(selected_id)
        candidates_after, _skipped2 = gateway._build_model_candidates(models, providers_by_id, router)
        decision_after = router.select_model(
            request_context=None,
            candidates=candidates_after,
            config={"required_capabilities": ["chat"], "cost_weight": 0.4, "latency_weight": 0.3},
        )
        selected_after = (decision_after or {}).get("selected_model")
        print(
            f"=== [门禁] 对选中模型记 3 次失败后 → 再选: {code_by_id.get(selected_after)}"
            f"（熔断排除生效={selected_after != selected_id}）==="
        )
        router.reset_stats()
        print("=== [门禁] 已重置统计（清理验证过程产生的失败计数）===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
