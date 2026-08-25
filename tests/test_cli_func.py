"""openbase-cli 函数级测试（直接调用，覆盖 main.py）."""

import argparse
from pathlib import Path


def _ns(**kwargs) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def test_build_parser_has_commands():
    """解析器包含三个子命令."""
    from openbase.cli.main import build_parser

    parser = build_parser()
    sub = parser._subparsers._group_actions[0].choices  # noqa: SLF001
    assert "create-project" in sub
    assert "create-module" in sub
    assert "create-crud" in sub


def test_cmd_create_project_generates_files(tmp_path: Path, monkeypatch):
    """create-project 生成标准工程结构（函数级）."""
    from openbase.cli.main import cmd_create_project

    monkeypatch.chdir(tmp_path)
    rc = cmd_create_project(_ns(name="demo-app"))
    assert rc == 0
    root = tmp_path / "demo-app"
    assert (root / "README.md").exists()
    assert (root / "pyproject.toml").exists()
    assert (root / "app" / "main.py").exists()
    assert "init_app" in (root / "app" / "main.py").read_text(encoding="utf-8")


def test_cmd_create_module_generates_skeleton(tmp_path: Path, monkeypatch):
    """create-module 生成模块骨架（函数级）."""
    from openbase.cli.main import cmd_create_module

    target = tmp_path / "openbase" / "modules" / "demo"
    target.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    rc = cmd_create_module(_ns(name="demo", description="测试模块"))
    assert rc == 0
    content = (target / "__init__.py").read_text(encoding="utf-8")
    assert "APIRouter" in content
    assert "测试模块" in content


def test_cmd_create_crud_generates_router(tmp_path: Path, monkeypatch):
    """create-crud 生成 CRUD 路由（函数级）."""
    from openbase.cli.main import cmd_create_crud

    monkeypatch.chdir(tmp_path)
    rc = cmd_create_crud(_ns(resource="books"))
    assert rc == 0
    content = (tmp_path / "crud_books.py").read_text(encoding="utf-8")
    assert "BaseCRUDRouter" in content
    assert 'prefix="/api/v1/books"' in content


def test_main_dispatch_unknown_command():
    """main 分发：未知命令由 argparse 拒绝（SystemExit）."""
    import pytest as _pytest

    from openbase.cli.main import build_parser

    with _pytest.raises(SystemExit):
        build_parser().parse_args(["unknown-cmd"])
