"""测试 v1.4.1 R-371 openbase-cli（create-module/create-crud 模板生成）."""

import importlib.util
import sys
from pathlib import Path

from openbase.cli import create_crud, create_module


def _module_paths(target: Path, name: str) -> list[Path]:
    """生成模块应产出的文件清单."""
    return [
        target / f"{name}" / "__init__.py",
        target / f"{name}" / "router.py",
        target / f"{name}" / "schemas.py",
        target / f"{name}" / "service.py",
        target / f"{name}" / "tests" / "test_router.py",
    ]


def test_create_module_generates_files(tmp_path: Path) -> None:
    """create-module 生成可导入的模块骨架."""
    name = "demo_module"
    create_module(str(tmp_path), name)

    for path in _module_paths(tmp_path, name):
        assert path.exists(), f"missing {path}"

    # 模块可导入
    sys.path.insert(0, str(tmp_path))
    try:
        spec = importlib.util.spec_from_file_location(
            "demo_module", tmp_path / name / "__init__.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "router")
    finally:
        sys.path.pop(0)


def test_create_crud_generates_files(tmp_path: Path) -> None:
    """create-crud 生成 CRUD 路由文件（引用 BaseCRUDRouter）."""
    name = "dict_item"
    create_crud(str(tmp_path), name)

    router_file = tmp_path / f"{name}_crud.py"
    assert router_file.exists()
    content = router_file.read_text(encoding="utf-8")
    assert "BaseCRUDRouter" in content
    assert "prefix" in content


def test_create_project_generates_standard_engine(tmp_path: Path) -> None:
    """create-project 生成标准工程（README/pyproject/app/main/tests/.env）."""
    from openbase.cli import create_project

    name = "demo_proj"
    outputs = create_project(str(tmp_path), name)
    assert len(outputs) == 6
    for path in outputs:
        assert path.exists(), f"missing {path}"
    assert "openbase>=1.4.1" in (tmp_path / name / "pyproject.toml").read_text(encoding="utf-8")
    assert "init_app" in (tmp_path / name / "app" / "main.py").read_text(encoding="utf-8")


def test_cli_main_entry(tmp_path: Path, monkeypatch) -> None:
    """CLI 入口（argparse）create-module/create-crud 命令可用."""
    from openbase.cli import main

    monkeypatch.chdir(tmp_path)
    # create-module 入口（cwd/openbase/modules 下生成）
    (tmp_path / "openbase" / "modules").mkdir(parents=True)
    assert main(["create-module", "demo_cli_mod"]) == 0
    assert (tmp_path / "openbase" / "modules" / "demo_cli_mod" / "__init__.py").exists()

    # create-crud 入口
    assert main(["create-crud", "demo_item"]) == 0
    assert (tmp_path / "demo_item_crud.py").exists()

    # create-project 入口
    assert main(["create-project", "demo_proj2"]) == 0
    assert (tmp_path / "demo_proj2" / "pyproject.toml").exists()
