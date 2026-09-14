"""testing 模块 Pydantic 请求模型（C-10 人工测试结论记录 API）.

对齐方案《OpenBase-人工端到端测试日志记录方案》§4.3 事件字典与 §5 批 2 C-10：
- run 轮次 / record 单条结论 / update 改判 / summary 汇总；
- FAIL/BLOCKED 强制 reason（方案 §7 主观性约束）；
- step_id 归一化（纯数字 → int，便于聚合排序）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# 用例/步骤结论（方案 §4.2 字段字典 result 取值）
TestResult = Literal["PASS", "FAIL", "BLOCKED", "SKIPPED"]

# FAIL / BLOCKED 必须填写理由（方案 §7：人判定主观性约束）
RESULT_REQUIRES_REASON: frozenset[str] = frozenset({"FAIL", "BLOCKED"})

VALID_RESULTS: tuple[str, ...] = ("PASS", "FAIL", "BLOCKED", "SKIPPED")


class TestRunRequest(BaseModel):
    """开轮请求（POST /api/v1/test-runs）.

    run_id 缺省自动生成（``run-<UTC:YYYYMMDD-HHMM>``）；也可由测试者显式提供，
    便于在启动时统一注入（对齐 ``OPENBASE_TEST_RUN_ID``）。
    """

    run_id: str | None = Field(
        None, max_length=64, description="测试轮次号；缺省自动生成"
    )
    title: str | None = Field(None, max_length=128, description="本轮标题/说明")
    scope: str | None = Field(None, max_length=255, description="本轮范围（页面清单/用例集）")
    request_id: str | None = Field(None, max_length=64, description="本轮关联请求 ID")


class TestRecordRequest(BaseModel):
    """单条结论请求（POST /api/v1/test-records）."""

    run_id: str = Field(..., max_length=64, description="所属测试轮次")
    case_id: str = Field(..., min_length=1, max_length=64, description="用例编号（复用既有编号体系）")
    step_id: int | str | None = Field(
        None, description="用例内步骤序号（纯数字归一为 int）"
    )
    result: TestResult = Field(..., description="结论：PASS/FAIL/BLOCKED/SKIPPED")
    title: str | None = Field(None, max_length=128, description="步骤标题")
    expected: str | None = Field(None, max_length=512, description="预期结果")
    observed: str | None = Field(None, max_length=512, description="实际观测")
    reason: str | None = Field(
        None, max_length=512, description="判定理由（FAIL/BLOCKED 必填）"
    )
    request_id: str | None = Field(None, max_length=64, description="关联请求 ID（客观证据）")
    duration_ms: int | None = Field(None, ge=0, description="步骤耗时毫秒")


class TestRecordUpdate(BaseModel):
    """改判请求（PATCH /api/v1/test-records/{id}）.

    改判追加审计（action=test.record.update），保留原结论可追溯性。
    """

    result: TestResult = Field(..., description="新结论")
    reason: str | None = Field(None, max_length=512, description="改判理由（新结论 FAIL/BLOCKED 必填）")
    observed: str | None = Field(None, max_length=512, description="更新后的观测")
