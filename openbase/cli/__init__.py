"""openbase-cli 包."""

from openbase.cli.main import (
    create_crud,
    create_module,
    create_project,
    main,
)

__all__ = ["main", "create_project", "create_module", "create_crud"]
