"""
Backend: app/permission_middleware.py

Dependency factory kiểm tra sub-permissions.
Dùng bằng cách thêm vào endpoint:

    from ..permission_middleware import require_permission

    @router.delete("/{id}")
    def delete_invoice(id: int, db=Depends(get_db),
                       _=Depends(require_permission("invoices.delete"))):
        ...
"""
import jwt
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserPermission
from .config import Config
from .cache import is_token_blacklisted

_security = HTTPBearer(auto_error=False)

ADMIN_POSITIONS = {"admin", "administrator", "quản trị"}


def _is_admin(user: User) -> bool:
    return (user.position or "").strip().lower() in ADMIN_POSITIONS


def _get_user_from_credentials(
    credentials: HTTPAuthorizationCredentials,
    db: Session,
) -> User:
    """Decode token → lấy user, giống _get_current_user_for_rbac trong rbac.py."""
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa đăng nhập",
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
    if user is None:
        raise cred_exc
    # Kiểm tra tài khoản còn active không (quan trọng: phát hiện bị vô hiệu hóa)
    if not user.status:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_permission(permission: str):
    """
    Dependency factory — kiểm tra sub-permission cụ thể.
    Admin (position in ADMIN_POSITIONS) luôn pass.
    Nhân viên cần có đúng permission trong bảng user_permissions.
    """
    def checker(
        credentials: HTTPAuthorizationCredentials = Security(_security),
        db: Session = Depends(get_db),
    ) -> User:
        user = _get_user_from_credentials(credentials, db)

        # Admin có toàn quyền
        if _is_admin(user):
            return user

        # Kiểm tra permission trong DB (luôn query tươi, không dùng cache)
        has_perm = db.query(UserPermission).filter(
            UserPermission.user_id == user.id,
            UserPermission.permission == permission
        ).first() is not None

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bạn không có quyền thực hiện chức năng này. Yêu cầu: {permission}",
            )
        return user

    return checker

# ── Backward-compatibility aliases (rbac.py đã được hợp nhất vào đây) ─────────
# Các file cũ import từ rbac sẽ vẫn hoạt động qua permission_middleware

def get_role(user: "User") -> str:
    """Trả về role string của user."""
    return _is_admin(user) and "admin" or "staff"


def require_admin(
    credentials: "HTTPAuthorizationCredentials" = Security(_security),
    db: "Session" = Depends(get_db),
) -> "User":
    """Dependency: chỉ cho phép admin."""
    user = _get_user_from_credentials(credentials, db)
    if not _is_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Chỉ quản trị viên mới có quyền thực hiện thao tác này.",
        )
    return user


def require_staff(
    credentials: "HTTPAuthorizationCredentials" = Security(_security),
    db: "Session" = Depends(get_db),
) -> "User":
    """Dependency: cho phép mọi user đã đăng nhập (admin + staff)."""
    return _get_user_from_credentials(credentials, db)


def get_user_role_info(user: "User") -> dict:
    """Trả về thông tin role của user."""
    return {
        "is_admin": _is_admin(user),
        "role": get_role(user),
        "position": user.position or "",
    }

# ── FastAPI Depends-compatible wrapper ────────────────────────────────────────
def _get_current_user_for_rbac(
    credentials: HTTPAuthorizationCredentials = Security(_security),
    db: Session = Depends(get_db),
) -> User:
    """Depends-compatible: Decode token → trả về User hiện tại."""
    return _get_user_from_credentials(credentials, db)