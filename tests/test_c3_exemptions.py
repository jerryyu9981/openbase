"""C3 豁免治理统一（第二阶段）：k03 豁免 R2「到期即失效」+ R1「影子期登记」.

上游契约：`config/identity_exemptions.json`（统一必填 target/ticket/approver/expires_at；
R2 到期即失效；R1 过渡段须显式登记且不改变放行行为）。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from openbase.modules.proxy import _k03_bypass_matches
from openbase.settings import Settings


def _entry(**overrides) -> dict:
    base = {"id": "e1", "system": "*", "method": "*", "path_pattern": "*"}
    base.update(overrides)
    return base


def _iso(delta_hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=delta_hours)).isoformat()


class TestK03ExpiryEnforced:
    """R2：expires_at 到期即不生效（修复此前「声明但未生效」的死字段）"""

    def test_expired_entry_not_matched(self):
        entry = _entry(expires_at=_iso(-1))
        assert _k03_bypass_matches(entry, system="s", method="POST", path="chat") is False

    def test_future_entry_matched(self):
        entry = _entry(expires_at=_iso(24))
        assert _k03_bypass_matches(entry, system="s", method="POST", path="chat") is True

    def test_invalid_expires_at_fail_closed(self):
        entry = _entry(expires_at="not-a-time")
        assert _k03_bypass_matches(entry, system="s", method="POST", path="chat") is False

    def test_missing_expires_at_still_matched_shadow(self):
        # R1 过渡段：缺 expires_at 仍生效（解析期 WARN 留痕），保持向后兼容
        assert _k03_bypass_matches(_entry(), system="s", method="POST", path="chat") is True


class TestK03TransitionWarn:
    """R1 影子期：缺统一契约必填字段的条目须 WARN 留痕，且不改变放行行为"""

    def test_missing_fields_logged_but_entries_kept(self, caplog, monkeypatch):
        raw = json.dumps([{"id": "a", "system": "*", "method": "*", "path_pattern": "*"}])
        settings = Settings(k03_bypass_whitelist=raw)
        with caplog.at_level(logging.WARNING):
            entries = settings.parse_k03_bypass_whitelist()
        assert len(entries) == 1  # 影子期不改变行为：条目仍保留
        assert any(
            "missing unified-contract fields" in record.getMessage()
            for record in caplog.records
        )

    def test_complete_entry_no_warn(self, caplog, monkeypatch):
        raw = json.dumps([{
            "id": "b", "system": "*", "method": "*", "path_pattern": "*",
            "ticket": "T-1", "approver": "alice", "expires_at": _iso(24),
        }])
        settings = Settings(k03_bypass_whitelist=raw)
        with caplog.at_level(logging.WARNING):
            entries = settings.parse_k03_bypass_whitelist()
        assert len(entries) == 1
        assert not [
            r for r in caplog.records if "missing unified-contract fields" in r.getMessage()
        ]