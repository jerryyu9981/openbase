"""openbase-cli 命令行测试."""

import os
import subprocess
import sys
from pathlib import Path


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "openbase.cli.main", *args],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
        timeout=30,
    )


def test_cli_create_crud_generates_file(tmp_path: Path):
    # 在临时目录验证 create-crud 生成
    result = subprocess.run(
        [sys.executable, "-m", "openbase.cli.main", "create-crud", "books"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=30,
    )
    assert result.returncode == 0
    generated = tmp_path / "crud_books.py"
    assert generated.exists()
    assert "BaseCRUDRouter" in generated.read_text(encoding="utf-8")


def test_cli_create_module_generates_skeleton(tmp_path: Path):
    module_dir = tmp_path / "openbase" / "modules" / "demo"
    module_dir.mkdir(parents=True)
    result = subprocess.run(
        [sys.executable, "-m", "openbase.cli.main", "create-module", "demo"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=30,
    )
    assert result.returncode == 0
    target = module_dir / "__init__.py"
    assert target.exists()
    assert "APIRouter" in target.read_text(encoding="utf-8")


def test_cli_create_project_generates_structure(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, "-m", "openbase.cli.main", "create-project", "demo-app"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=30,
    )
    assert result.returncode == 0
    root = tmp_path / "demo-app"
    assert (root / "app" / "main.py").exists()
    assert (root / "pyproject.toml").exists()
    assert (root / "README.md").exists()
