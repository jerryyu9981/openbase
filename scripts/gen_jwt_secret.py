"""OpenBase JWT 共享密钥生成/校验工具（v1.7.0）.

生成强随机 HS256 签名密钥（≥32 字符，URL-safe）用于 OPENBASE_JWT_SECRET
与 OpenMemory OPENMEMORY_GATEWAY__JWT_SECRET（同源共享）。

用法:
    python scripts/gen_jwt_secret.py            # 打印新密钥（人工配置）
    python scripts/gen_jwt_secret.py --check    # 校验当前 .env 密钥强度
"""
from __future__ import annotations

import argparse
import pathlib
import secrets
import sys

MIN_LEN = 32
WEAK = {"", "change-me-in-production", "test-jwt-secret-for-v680"}


def generate() -> str:
    return secrets.token_urlsafe(48)


def is_strong(secret: str) -> bool:
    return len(secret or "") >= MIN_LEN and (secret or "") not in WEAK


def _current_env_secret(root: pathlib.Path) -> str:
    env_file = root / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("OPENBASE_JWT_SECRET="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenBase JWT 密钥工具")
    parser.add_argument("--check", action="store_true", help="校验当前 .env 密钥强度")
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parent.parent

    if args.check:
        secret = _current_env_secret(root)
        if is_strong(secret):
            print(f"[ok] .env OPENBASE_JWT_SECRET 为强密钥（长度 {len(secret)}）")
            return 0
        print(
            f"[warn] .env OPENBASE_JWT_SECRET 缺失或过弱（长度 {len(secret)}）；"
            f"生产模式启动将拒绝。用本工具生成后同步 OPENMEMORY_GATEWAY__JWT_SECRET"
        )
        return 1

    secret = generate()
    print("=== 新 JWT 共享密钥（HS256） ===")
    print(secret)
    print()
    print("配置步骤：")
    print("  1) OpenBase .env      : OPENBASE_JWT_SECRET=<上述值>")
    print("  2) OpenMemory .env    : OPENMEMORY_GATEWAY__JWT_SECRET=<上述值>")
    print("  3) 轮换（可选，零中断）：旧密钥写入 OPENBASE_JWT_SECRET_PREVIOUS 过渡后移除")
    return 0


if __name__ == "__main__":
    sys.exit(main())
