"""C1-d / C2 码值规范化（通用能力）单元用例.

上游：DPS `src/middleware/tenant_middleware.py:287-319`（码↔UUID 双形态解析 + 回填）。
"""
from __future__ import annotations

from openbase.core.code_normalize import (
    LOOKUP_BY_CODE,
    LOOKUP_BY_ID,
    canonical_uuid,
    is_uuid_like,
    normalize_code_or_id,
    pick_lookup_column,
)

UUID_A = "3f1a8c22-9b4d-4e57-9a6c-0d2f4b7e1c93"


class TestUuidLike:
    def test_uuid_forms(self):
        assert is_uuid_like(UUID_A) is True
        assert is_uuid_like(UUID_A.upper()) is True
        assert is_uuid_like(f"  {UUID_A}  ") is True

    def test_non_uuid_forms(self):
        for value in ("tenant-1", "default", "", None, "3f1a8c22-9b4d"):
            assert is_uuid_like(value) is False

    def test_pick_column(self):
        assert pick_lookup_column(UUID_A) == LOOKUP_BY_ID
        assert pick_lookup_column("tenant-1") == LOOKUP_BY_CODE

    def test_canonical_uuid(self):
        assert canonical_uuid(UUID_A.upper()) == UUID_A
        assert canonical_uuid("tenant-1") is None


class TestNormalizeCodeOrId:
    def test_code_form_backfills_uuid(self):
        seen = []

        def resolver(column, value):
            seen.append((column, value))
            return UUID_A if (column, value) == (LOOKUP_BY_CODE, "tenant-1") else None

        assert normalize_code_or_id("tenant-1", resolver) == UUID_A
        assert seen == [(LOOKUP_BY_CODE, "tenant-1")]

    def test_uuid_form_looked_up_by_id(self):
        seen = []

        def resolver(column, value):
            seen.append((column, value))
            return UUID_A

        assert normalize_code_or_id(UUID_A, resolver) == UUID_A
        assert seen == [(LOOKUP_BY_ID, UUID_A)]

    def test_unresolved_returns_none_fail_closed(self):
        assert normalize_code_or_id("ghost", lambda column, value: None) is None
        assert normalize_code_or_id(None, lambda column, value: UUID_A) is None
        assert normalize_code_or_id("", lambda column, value: UUID_A) is None