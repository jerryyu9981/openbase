"""采集 TT-038 判定所需的库内真实规模（复核要求 §1.1.3「记录行数」）"""
import sqlite3
import sys

DB = r"D:\Trae CN\myproject\Dev\OpenLLM\backend\data\writeback.db"


def main() -> int:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    for table in ("writeback_queue", "writeback_receipts", "messages", "conversations"):
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"{table}: {cur.fetchone()[0]}")
        except Exception as exc:  # noqa: BLE001
            print(f"{table}: <不可用: {exc}>")
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        print("tables:", [row[0] for row in cur.fetchall()])
    except Exception as exc:  # noqa: BLE001
        print("tables 读取失败:", exc)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
