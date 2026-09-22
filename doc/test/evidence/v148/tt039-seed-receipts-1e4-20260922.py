"""TT-039 回执 1e4 行档位：受控播种与精确清理（SQLite 回写队列）

口径（《非功能设计说明-v1.4.8》v1.1.0 §1.1.2 P-7 / §1.1.3）：
  - 在**同一** SQLite 回写队列（`backend/data/writeback.db`）中播种 1e4 行，
    `payload_json.user_id` 一律指向性能账号，使端点过滤走**最坏情况**（命中该用户的最大集）；
  - 播种/清理均以 `session_id LIKE 'perf-tt039-%'` **精确界定**，不触碰既有 140 行；
  - 用法：`python seed_receipts_1e4.py --rows 10000`（播种） / `--cleanup`（清理）。

退出码：0＝成功；1＝失败。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

_BACKEND_ROOT = Path(r"D:\Trae CN\myproject\Dev\OpenLLM\backend")
QUEUE_DB = str(_BACKEND_ROOT / "data" / "writeback.db")
SESSION_PREFIX = "perf-tt039-"
PERF_USER_ID = "3ef164f4-6c1b-4469-a4b7-369aa2a17042"
TARGETS = ("memory", "rag", "profile")


def _count(conn: sqlite3.Connection, like: str | None = None) -> int:
    if like is None:
        return conn.execute("SELECT count(*) FROM writeback_queue").fetchone()[0]
    return conn.execute(
        "SELECT count(*) FROM writeback_queue WHERE session_id LIKE ?", (like,)
    ).fetchone()[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=int, default=10000, help="播种行数（TT-039 档位：10000）")
    parser.add_argument("--cleanup", action="store_true", help="清理本脚本播种的行")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(QUEUE_DB, timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=15000")
        if args.cleanup:
            before = _count(conn)
            deleted = conn.execute(
                "DELETE FROM writeback_queue WHERE session_id LIKE ?", (f"{SESSION_PREFIX}%",)
            ).rowcount
            conn.commit()
            print(f"[cleanup] 删除 {deleted} 行；总数 {before} → {_count(conn)}（播种残留={_count(conn, SESSION_PREFIX + '%')}）")
            return 0

        now = datetime.now().isoformat()
        rows = []
        for index in range(args.rows):
            target = TARGETS[index % len(TARGETS)]
            rows.append(
                (
                    f"perf-tt039-req-{index}",
                    f"{SESSION_PREFIX}{index % 500}",
                    index + 1,
                    target,
                    json.dumps(
                        {
                            "user_id": PERF_USER_ID,
                            "session_id": f"{SESSION_PREFIX}{index % 500}",
                            "seq": index + 1,
                            "target": target,
                            "probe": "tt039-scale-fixture",
                        },
                        ensure_ascii=False,
                    ),
                    "done",
                    0,
                    None,
                    now,
                    now,
                )
            )
        started = time.perf_counter()
        conn.executemany(
            "INSERT OR IGNORE INTO writeback_queue "
            "(request_id, session_id, seq, target, payload_json, status, retry_count, next_retry_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        elapsed = time.perf_counter() - started
        print(
            f"[seed] 插入 {len(rows)} 行（{elapsed:.2f}s）；总数={_count(conn)}；"
            f"本批={_count(conn, SESSION_PREFIX + '%')}"
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
