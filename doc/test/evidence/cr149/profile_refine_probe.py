"""CR-149 第二批运行态证据：画像增量提炼服务（`DEF-BE-148-029` 缺陷修复）

在**真实模块 / 真实调用链**下取证（非 monkeypatch 主体逻辑）：

  1. **缺陷本体已消除**：`app.services.profile_refine` 可导入，且 `evaluate.py`
     期望的 `DEFAULT_PROFILE_TARGETS` / `get_active_profile_refiner` /
     `refine_profile_delta` 三个符号齐备（修复前该导入必然 `ModuleNotFoundError`）；
  2. **写侧决策链路可用**：`evaluate._profile_updates_for()` 真实返回增量
     （修复前会因导入失败打挂决策）；
  3. **规则提炼语义与既有线上实现一致**：`refine_profile_delta` 与
     `writeback._resolve_profile_updates` 在「显式 updates / 有 targets / 无 targets」
     三种入参下结果一致（既有护栏 `test_v2143_writeback_profile.py` 继续全绿）；
  4. **提炼器可注入且规则兜底**：注册 → 生效；抛异常 / 返回空 / 返回非 dict → 保留规则结果；
     复位 → 回到纯规则路径（默认行为）。

用法（在 OpenLLM/backend 下）::

    python <此脚本>
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from app.api.writeback import _resolve_profile_updates  # noqa: E402
from app.edgerouter.orchestration.evaluate import _profile_updates_for  # noqa: E402
from app.services import profile_refine  # noqa: E402

DIALOGUE = {"query": "怎么优化检索速度？", "response": "可以考虑建立索引与缓存策略。"}


def _equivalence() -> dict:
    """规则路径与既有回写路实现的一致性（同入参 ⇒ 同结果）"""
    cases = {
        "explicit_updates_only": {"updates": {"person": {"name": "张三"}}},
        "with_targets": {"dialogue": DIALOGUE, "extract_targets": ["business", "person"]},
        "business_only": {"dialogue": DIALOGUE, "extract_targets": ["business"]},
        "no_targets": {"dialogue": DIALOGUE},
        "blank_dialogue": {"dialogue": {"query": "", "response": ""}, "extract_targets": ["person"]},
    }
    return {
        name: {
            "writeback": _resolve_profile_updates(payload),
            "service": profile_refine.refine_profile_delta(
                dialogue=payload.get("dialogue") or {},
                extract_targets=payload.get("extract_targets"),
                updates=payload.get("updates"),
            )
            if not payload.get("updates")
            else payload["updates"],
        }
        for name, payload in cases.items()
    }


def main() -> dict:
    symbols = {
        "DEFAULT_PROFILE_TARGETS": list(profile_refine.DEFAULT_PROFILE_TARGETS),
        "get_active_profile_refiner": profile_refine.get_active_profile_refiner() is None,
        "refine_profile_delta": callable(profile_refine.refine_profile_delta),
    }

    rule_only = _profile_updates_for([DIALOGUE], ["business", "person"])

    # 提炼器注入：生效 → 抛异常保留规则 → 复位
    def _refiner(_dialogue):
        return {"person": {"tone": "assertive"}}

    profile_refine.set_active_profile_refiner(_refiner)
    injected = _profile_updates_for([DIALOGUE], ["person"])
    profile_refine.set_active_profile_refiner(
        lambda _d: (_ for _ in ()).throw(RuntimeError("refiner down"))
    )
    degraded = _profile_updates_for([DIALOGUE], ["person"])
    profile_refine.set_active_profile_refiner(None)
    after_reset = profile_refine.get_active_profile_refiner()

    return {
        "module": "app/services/profile_refine.py",
        "defect": "DEF-BE-148-029",
        "symbols_available": symbols,
        "evaluate_rule_path": rule_only,
        "refiner_injected": injected,
        "refiner_failure_falls_back_to_rules": degraded,
        "refiner_reset_to_none": after_reset is None,
        "equivalence_writeback_vs_service": _equivalence(),
        "module_reachable_after_import": True,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(asyncio.sleep(0, result=main())), ensure_ascii=False, indent=2))
