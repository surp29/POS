"""
rbac.py — Backward-compatibility shim.
Tất cả logic đã được chuyển vào permission_middleware.py.
File này chỉ re-export để không break các file đã import.
"""
from .permission_middleware import (
    require_permission,
    require_admin,
    require_staff,
    get_role,
    get_user_role_info,
    _get_user_from_credentials,
    _is_admin,
)

__all__ = [
    "require_permission",
    "require_admin",
    "require_staff",
    "get_role",
    "get_user_role_info",
]