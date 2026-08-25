"""模块独立版本生成脚本：扫描 openbase/modules 下各模块 __version__，生成 versions.json.

用法:
    python scripts/gen_versions.py

产出:
    openbase/modules/versions.json（{module: {"version": "x.y.z"}}）
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MODULES_DIR = Path(__file__).resolve().parent.parent / "openbase" / "modules"
OUTPUT = MODULES_DIR / "versions.json"
VERSION_RE = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')


def scan() -> dict:
    versions: dict = {}
    for init in sorted(MODULES_DIR.glob("*/__init__.py")):
        module = init.parent.name
        m = VERSION_RE.search(init.read_text(encoding="utf-8"))
        version = m.group(1) if m else "0.0.0"
        versions[module] = {"version": version}
    return versions


def main() -> int:
    versions = scan()
    OUTPUT.write_text(
        json.dumps({"generated": "openbase-cli gen-versions", "modules": versions}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"versions.json generated: {len(versions)} modules -> {OUTPUT}")
    for name, info in versions.items():
        print(f"  {name}: {info['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
