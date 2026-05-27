"""
Role-Based Access Control (RBAC).

Role suy ra từ field `position` trong bảng users.
Không import từ api_fastapi.auth để tránh circular import.
get_current_user được định nghĩa lại ở đây hoặc import trực tiếp.
"""
from enum import Enum
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .logger import log_warning

security = HTTPBearer()


class Role(str, Enum):
    ADMIN  = "admin"
    STAFF  = "staff"
    VIEWER = "viewer"


POSITION_ROLE_MAP: dict[str, Role] = {
    "admin":         Role.ADMIN,
    "administrator": Role.ADMIN,
    "quản trị":      Role.ADMIN,
    "manager":       Role.ADMIN,
    "staff":         Role.STAFF,
    "nhân viên":     Role.STAFF,
    "employee":      Role.STAFF,
    "cashier":       Role.STAFF,
    "thu ngân":      Role.STAFF,
    "viewer":        Role.VIEWER,
    "guest":         Role.VIEWER,
}


def get_role(user: User) -> Role:
    position = (user.position or "").strip().lower()
    return POSITION_ROLE_MAP.get(position, Role.STAFF)


def _get_current_user_for_rbac(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency lấy current user — copy từ auth.py để tránh circular import.
    auth.py và rbac.py đều độc lập, không import lẫn nhau.
    """
    import jwt
    from .config import Config
    from .cache import is_token_blacklisted

    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(credentials.credentials, Config.JWT_SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        jti      = payload.get("jti")
        if not username:
            raise cred_exc
        if jti and is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token đã bị thu hồi. Vui lòng đăng nhập lại.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise cred_exc

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.status:
        raise cred_exc
    return user


def require_admin(
    current_user: User = Depends(_get_current_user_for_rbac),
) -> User:
    """Chỉ cho phép ADMIN."""
    role = get_role(current_user)
    if role != Role.ADMIN:
        log_warning("RBAC", f"User '{current_user.username}' (role={role}) bị từ chối ADMIN endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Yêu cầu quyền Admin. Role hiện tại: {role.value}",
        )
    return current_user


def require_staff(
    current_user: User = Depends(_get_current_user_for_rbac),
) -> User:
    """Cho phép ADMIN và STAFF."""
    role = get_role(current_user)
    if role == Role.VIEWER:
        log_warning("RBAC", f"User '{current_user.username}' (role={role}) bị từ chối STAFF endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yêu cầu quyền Staff trở lên.",
        )
    return current_user


def get_user_role_info(user: User) -> dict:
    role = get_role(user)
    return {
        "role":        role.value,
        "permissions": _get_permissions(role),
    }


def _get_permissions(role: Role) -> list[str]:
    if role == Role.ADMIN:
        return ["read", "create", "update", "delete", "manage_users"]
    if role == Role.STAFF:
        return ["read", "create", "update"]
    return ["read"]