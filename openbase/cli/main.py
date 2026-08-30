"""openbase-cli：create-project / create-module / create-crud 命令行工具."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 模块代码模板（v1.4.1 R-371：5 文件骨架，对齐模块规范）
MODULE_TEMPLATES: dict[str, str] = {
    "__init__.py": '''"""{name} 模块（openbase-cli 生成）."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/{route}", tags=["{name}"])

__all__ = ["router"]
''',
    "router.py": '''"""路由定义（openbase-cli 生成骨架）."""

from fastapi import APIRouter, Depends

from openbase.core.deps.auth import get_current_user

router = APIRouter(prefix="/api/v1/{route}", tags=["{name}"])


@router.get("/health", response_model=dict)
async def health(user: dict = Depends(get_current_user)) -> dict:
    """模块健康检查."""
    return {{"status": "ok"}}
''',
    "schemas.py": '''"""Pydantic 模式（openbase-cli 生成骨架）."""

from pydantic import BaseModel


class {Title}Create(BaseModel):
    """创建请求."""

    name: str


class {Title}Out(BaseModel):
    """响应."""

    id: int
    name: str
''',
    "service.py": '''"""数据服务（openbase-cli 生成骨架，对接 BaseDBService）."""

from openbase.core.db.services import BaseDBService


class {Title}Service(BaseDBService):
    """{Title} 数据服务."""
''',
    "tests/test_router.py": '''"""模块测试骨架（openbase-cli 生成）."""

from fastapi.testclient import TestClient

from openbase.demo_app import app

client = TestClient(app)


def test_health_requires_auth() -> None:
    """未登录访问模块健康检查 → 401."""
    assert client.get("/api/v1/{route}/health").status_code == 401
''',
}

CRUD_TEMPLATE = '''"""{Title} CRUD 路由（openbase-cli 生成，引用 BaseCRUDRouter）."""

from openbase.core.crud import BaseCRUDRouter

from {module}.schemas import {Title}Create, {Title}Update, {Title}Out
from {module}.service import {Title}Service

router = BaseCRUDRouter(
    prefix="/api/v1/{route}",
    service={Title}Service(),
    create_schema={Title}Create,
    update_schema={Title}Update,
    out_schema={Title}Out,
)

__all__ = ["router"]
'''

PROJECT_TEMPLATE = '''# {name}

由 openbase-cli 生成的 OpenBase 标准工程。

## 快速开始

```bash
pip install -e .
uvicorn app.main:app --reload
```

## 结构

- `app/main.py` - 应用入口（init_app 装配）
- `openbase/` - 公共底座（依赖 openbase 包）
- `tests/` - 测试目录
'''

MAIN_TEMPLATE = '''"""应用入口."""

from openbase import init_app, settings

settings.enable_module("auth")
settings.enable_module("tenant")
settings.enable_module("audit")
settings.enable_module("config")
settings.enable_module("observability")

app = init_app(settings)
'''

PYPROJECT_TEMPLATE = '''[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["openbase>=1.4.1", "uvicorn[standard]"]

[tool.setuptools.packages.find]
include = ["app*"]
'''


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  created {path}")


def _pascal(name: str) -> str:
    """snake_case → PascalCase."""
    return "".join(part.capitalize() for part in name.replace("-", "_").split("_"))


def _render(template: str, name: str) -> str:
    """渲染模板（名称占位替换）."""
    title = _pascal(name)
    route = name.replace("_", "-")
    return (
        template.replace("{name}", name)
        .replace("{route}", route)
        .replace("{Title}", title)
        .replace("{{", "{")
        .replace("}}", "}")
    )


def create_project(target: str, name: str) -> list[Path]:
    """create-project: 生成标准工程结构（返回产出文件列表）.

    Args:
        target: 工程父目录。
        name: 工程名。

    Returns:
        生成的工程根目录（含 5 文件）。
    """
    root = Path(target) / name
    files = [
        root / "README.md",
        root / "pyproject.toml",
        root / "app" / "main.py",
        root / "app" / "__init__.py",
        root / "tests" / "__init__.py",
        root / ".env.example",
    ]
    contents = [
        PROJECT_TEMPLATE.format(name=name),
        PYPROJECT_TEMPLATE.format(name=name),
        MAIN_TEMPLATE,
        "",
        "",
        "OPENBASE_DB_URL=postgresql+asyncpg://...\n",
    ]
    for path, content in zip(files, contents, strict=True):
        _write(path, content)
    print(f"Project {name} created at {root}")
    return files


def create_module(target: str, name: str, description: str = "") -> list[Path]:
    """create-module: 生成模块骨架（5 文件）.

    Args:
        target: 目标目录（openbase/modules 或 openbase-ui/src/modules）。
        name: 模块名（snake_case）。
        description: 模块描述（写入 __init__.py docstring，可空）。

    Returns:
        产出文件列表。
    """
    module_dir = Path(target) / name
    outputs: list[Path] = []
    for relative, template in MODULE_TEMPLATES.items():
        content = _render(template, name)
        if description and relative == "__init__.py":
            content = content.replace(
                f'"""{name} 模块（openbase-cli 生成）."""',
                f'"""{name} 模块（openbase-cli 生成）：{description}."""',
            )
        path = module_dir / relative
        _write(path, content)
        outputs.append(path)
    print(f"Module {name} created at {module_dir}. Add to AVAILABLE_MODULES in settings.py if new.")
    return outputs


def create_crud(target: str, name: str) -> list[Path]:
    """create-crud: 生成 CRUD 路由（引用 BaseCRUDRouter）.

    Args:
        target: 目标目录。
        name: 资源名（snake_case，如 dict_item）。

    Returns:
        产出文件列表。
    """
    module_name = name.split("_")[0] if "_" in name else name
    path = Path(target) / f"{name}_crud.py"
    _write(path, _render(CRUD_TEMPLATE, name).replace("{module}", module_name))
    print(f"CRUD router created at {path}. Include: app.include_router(router)")
    return [path]


def cmd_create_project(args: argparse.Namespace) -> int:
    """CLI 命令包装：create-project."""
    create_project(str(Path.cwd()), args.name)
    return 0


def cmd_create_module(args: argparse.Namespace) -> int:
    """CLI 命令包装：create-module."""
    target = Path.cwd() / "openbase" / "modules"
    create_module(str(target), args.name, getattr(args, "description", ""))
    return 0


def cmd_create_crud(args: argparse.Namespace) -> int:
    """CLI 命令包装：create-crud."""
    create_crud(str(Path.cwd()), args.resource)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器."""
    parser = argparse.ArgumentParser(prog="openbase-cli", description="OpenBase 开发工具链")
    sub = parser.add_subparsers(dest="command", required=True)

    p_project = sub.add_parser("create-project", help="创建标准工程")
    p_project.add_argument("name", help="工程名")
    p_project.set_defaults(func=cmd_create_project)

    p_module = sub.add_parser("create-module", help="创建模块骨架")
    p_module.add_argument("name", help="模块名")
    p_module.add_argument("--description", default="")
    p_module.set_defaults(func=cmd_create_module)

    p_crud = sub.add_parser("create-crud", help="生成 CRUD 路由")
    p_crud.add_argument("resource", help="资源名（如 books）")
    p_crud.set_defaults(func=cmd_create_crud)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

