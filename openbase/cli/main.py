"""openbase-cli：create-project / create-module / create-crud 命令行工具."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 模块代码模板
MODULE_TEMPLATE = '''"""{name} 模块：{description}."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/{route}", tags=["{name}"])


class {Title}Create(BaseModel):
    """创建请求."""

    name: str


@router.get("", response_model=list[dict])
async def list_items() -> list[dict]:
    """列表."""
    return []


@router.post("", response_model=dict)
async def create_item(payload: {Title}Create) -> dict:
    """创建."""
    return {{"id": 1, "name": payload.name}}
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
dependencies = ["openbase>=1.0", "uvicorn[standard]"]

[tool.setuptools.packages.find]
include = ["app*"]
'''


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  created {path}")


def cmd_create_project(args: argparse.Namespace) -> int:
    """create-project: 生成标准工程结构."""
    name = args.name
    root = Path.cwd() / name
    print(f"Creating project {name} at {root}")

    _write(root / "README.md", PROJECT_TEMPLATE.format(name=name))
    _write(root / "pyproject.toml", PYPROJECT_TEMPLATE.format(name=name))
    _write(root / "app" / "main.py", MAIN_TEMPLATE)
    _write(root / "app" / "__init__.py", "")
    _write(root / "tests" / "__init__.py", "")
    _write(root / ".env.example", "OPENBASE_DB_URL=postgresql+asyncpg://...\n")
    print("Project created. Run: pip install -e . && uvicorn app.main:app --reload")
    return 0


def cmd_create_module(args: argparse.Namespace) -> int:
    """create-module: 生成 openbase 模块骨架."""
    name = args.name
    title = name.title().replace("_", "")
    route = name.replace("_", "-")
    target = Path.cwd() / "openbase" / "modules" / name / "__init__.py"
    _write(target, MODULE_TEMPLATE.format(name=name, Title=title, route=route, description=args.description or name))
    print(f"Module {name} created. Add to AVAILABLE_MODULES in settings.py if new.")
    return 0


def cmd_create_crud(args: argparse.Namespace) -> int:
    """create-crud: 生成 CRUD 路由（对接 BaseCRUDRouter）."""
    resource = args.resource
    title = resource.title().replace("_", "")
    target = Path.cwd() / f"crud_{resource}.py"
    content = f'''"""CRUD 路由：{resource}（由 openbase-cli 生成）."""

from pydantic import BaseModel

from openbase.crud import BaseCRUDRouter


class {title}Create(BaseModel):
    """创建请求."""

    name: str


class {title}Out(BaseModel):
    """响应."""

    id: int
    name: str


# 数据存储（生产接数据库，此处为示例）
_store: dict[int, dict] = {{}}

router = BaseCRUDRouter(
    prefix="/api/v1/{resource}",
    create_schema={title}Create,
    out_schema={title}Out,
    store=_store,
    search_fields=["name"],
)
'''
    _write(target, content)
    print(f"CRUD router created at {target}. Include router in your app: app.include_router(router)")
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
