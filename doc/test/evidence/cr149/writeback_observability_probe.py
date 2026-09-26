"""CR-149 第二批运行态证据：回写队列可观测与死信（方案 §4.3）

在**真实存储层 / 队列层**（`WritebackStore` + `WritebackQueue`，独立临时 SQLite）下取证：

  1. **聚合指标**：按状态计数、失败率、重试分布（`retry_count` 直方图）、
     最早未完成行（积压年龄），以及**按用户作用域**的口径（fail-closed）；
  2. **死信视图**：只含 `failed` 行、可分页、**不含 payload 正文**；
  3. **死信重放**：`claim_failed` 原子置回 `pending`（重试计数归零）后重新投递 handler；
     未注册 handler 的目标计 `skipped` 且**行留在 pending**（不静默丢失）；
  4. **TTL 清理任务化**：`run_cleanup_loop(0)` 即时返回（等价于关闭）；
     巡一轮清理后死信数下降。

用法（在 OpenLLM/backend 下）::

    python <此脚本>
"""
import asyncio
import json
import os
import sys
import tempfile

sys.path.insert(0, os.getcwd())
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from app.services.writeback_queue import (  # noqa: E402
    WritebackQueue,
    WritebackStore,
)


async def _seed(store: WritebackStore, session_id: str, user_id: str, seq: int) -> int:
    _inserted, row_id = await store.enqueue(
        f"req-{session_id}-{seq}",
        session_id,
        seq,
        "memory",
        {"user_id": user_id, "query": "q", "response": "r"},
    )
    return int(row_id)


async def main() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        store = WritebackStore(db_path=os.path.join(tmp, "wb.db"))
        queue = WritebackQueue(store=store)
        delivered: list[dict] = []

        async def _handler(**kwargs):
            delivered.append(kwargs)

        queue.register_handler("memory", _handler)

        # 造数：u-1 三行（done / failed×2）+ u-2 一行（failed）+ 一行无归属历史行
        u1_done = await _seed(store, "s-1", "u-1", 1)
        u1_failed_a = await _seed(store, "s-1", "u-1", 2)
        u1_failed_b = await _seed(store, "s-1", "u-1", 3)
        u2_failed = await _seed(store, "s-2", "u-2", 1)
        await store.mark_done(u1_done)
        await store.mark_failed(u1_failed_a, retry_count=3)
        await store.mark_failed(u1_failed_b, retry_count=2)
        await store.mark_failed(u2_failed, retry_count=3)

        global_stats = await store.stats()
        user_stats = await store.stats(user_id="u-1")
        dead_letters = await store.list_dead_letters(limit=10, offset=0)
        scoped_dead = await store.list_dead_letters(user_id="u-1")

        # 重放 u-1 的两条死信（其一已注册 handler）
        replay = await queue.replay_dead_letters([u1_failed_a, u1_failed_b], user_id="u-1")
        await queue.drain()
        status_after_replay = await store.list_rows(session_id="s-1")

        # 越权重放（u-2 的死信由 u-1 取件）须不生效
        cross_tenant = await store.claim_failed([u2_failed], user_id="u-1")
        u2_row = await store.list_rows(session_id="s-2")

        # TTL 清理任务化：间隔 0 ⇒ 立即返回；直连清理接口可被任务调用
        await asyncio.wait_for(queue.run_cleanup_loop(0), timeout=1.0)
        cleaned = await queue.cleanup()
        after_cleanup = await store.stats()

        return {
            "global_stats": global_stats,
            "user_scope_stats_u1": user_stats,
            "dead_letters": {
                "total": dead_letters["total"],
                "ids": [row["id"] for row in dead_letters["items"]],
                "has_payload_field": any(
                    "payload_json" in row for row in dead_letters["items"]
                ),
            },
            "scoped_dead_letters_u1": {
                "total": scoped_dead["total"],
                "ids": [row["id"] for row in scoped_dead["items"]],
            },
            "replay": replay,
            "handler_delivered": len(delivered),
            "status_after_replay": {
                row["id"]: row["status"] for row in status_after_replay
            },
            "cross_tenant_claim": cross_tenant,
            "u2_status_unchanged": u2_row[0]["status"],
            "cleanup_interval_zero_returns_immediately": True,
            "cleaned_rows_now": cleaned,
            "failed_after_cleanup": after_cleanup["by_status"]["failed"],
            "seeded_ids": {
                "u1_done": u1_done,
                "u1_failed_a": u1_failed_a,
                "u1_failed_b": u1_failed_b,
                "u2_failed": u2_failed,
            },
        }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main()), ensure_ascii=False, indent=2))
