"""core/deps：通用依赖注入."""

from openbase.core.db.session import get_db
from openbase.core.deps.auth import get_current_tenant, get_current_user

__all__ = ["get_db", "get_current_user", "get_current_tenant"]
