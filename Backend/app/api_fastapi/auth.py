"""
Authentication endpoints.
Thay đổi so với bản trước:
  - Token payload giờ có thêm field 'role' → endpoint tự biết quyền mà không cần query DB
  - /me trả về thêm role + permissions
  - get_current_user() là dependency chuẩn, dùng Depends()
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash

from ..config import Config
from ..database import get_db
from ..models import User
from ..schemas_fastapi import UserLogin, UserResponse
from ..logger import log_info, log_success, log_error, log_warning
from ..cache import blacklist_token, is_token_blacklisted

router   = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

SECRET_KEY = Config.JWT_SECRET_KEY
ALGORITHM  = "HS256"
TOKEN_TTL  = Config.JWT_ACCESS_TOKEN_EXPIRES


# ── Role helper (import tại đây để tránh circular import) ────────────────────

def _resolve_role(user: User) -> str:
    """Suy ra role từ position — đồng bộ với rbac.py."""
    position = (user.position or "").strip().lower()
    admin_positions = {"admin", "administrator", "quản trị", "manager"}
    viewer_positions = {"viewer", "guest"}
    if position in admin_positions:
        return "admin"
    if position in viewer_positions:
        return "viewer"
    return "staff"


# ── Token helpers ─────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now    = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(seconds=TOKEN_TTL))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ── Core dependency ───────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — dùng trong mọi endpoint cần xác thực:
        current_user = Depends(get_current_user)

    Kiểm tra:
      1. Token hợp lệ, chưa hết hạn
      2. Token chưa bị blacklist (logout)
      3. User tồn tại và đang active
    """
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        jti: str      = payload.get("jti")
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=dict)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Đăng nhập — trả về JWT có chứa role."""
    try:
        user = db.query(User).filter(User.username == user_credentials.username).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Tài khoản không tồn tại")
        if not user.status:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Tài khoản đã bị vô hiệu hóa")
        if not check_password_hash(str(user.password), user_credentials.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Sai tài khoản hoặc mật khẩu")

        role  = _resolve_role(user)
        token = create_access_token(
            data={"sub": user.username, "role": role},
            expires_delta=timedelta(seconds=TOKEN_TTL),
        )

        log_success("LOGIN", f"Đăng nhập thành công: {user.username} (role={role})")
        return {
            "access_token": token,
            "token_type":   "bearer",
            "expires_in":   TOKEN_TTL,
            "user": {
                "username":    user.username,
                "name":        user.name,
                "position":    user.position,
                "department":  user.department,
                "role":        role,          # MỚI
                "permissions": _role_permissions(role),  # MỚI
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_error("LOGIN", "Lỗi đăng nhập", error=e)
        raise HTTPException(status_code=500, detail="Lỗi server khi đăng nhập")


@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Đăng xuất — blacklist token hiện tại."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        if not jti:
            return {"message": "Đăng xuất thành công"}
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 1) if exp else TOKEN_TTL
        blacklist_token(jti, ttl_seconds=ttl)
        log_info("LOGOUT", f"Token {jti[:8]}... blacklisted (TTL={ttl}s)")
        return {"message": "Đăng xuất thành công"}
    except jwt.ExpiredSignatureError:
        return {"message": "Đăng xuất thành công"}
    except Exception as e:
        db.rollback()
        log_error("LOGOUT", "Lỗi logout", error=e)
        raise HTTPException(status_code=500, detail="Lỗi server khi đăng xuất")



@router.post("/refresh")
def refresh_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
):
    """
    Cấp token mới từ token còn hiệu lực.
    Frontend gọi khi user đang active để gia hạn session.
    Token cũ bị blacklist, token mới TTL đầy đủ.
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        username = payload.get("sub")
        jti_old  = payload.get("jti")
        exp_old  = payload.get("exp")

        if not username:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")

        user = db.query(User).filter(User.username == username).first()
        if not user or not user.status:
            raise HTTPException(
                status_code=401,
                detail="Tài khoản không tồn tại hoặc đã bị vô hiệu hóa"
            )

        # Blacklist token cũ
        if jti_old and exp_old:
            ttl = max(int(exp_old - datetime.now(timezone.utc).timestamp()), 1)
            blacklist_token(jti_old, ttl_seconds=ttl)

        # Cấp token mới
        role      = _resolve_role(user)
        new_token = create_access_token(
            data={"sub": user.username, "role": role},
            expires_delta=timedelta(seconds=TOKEN_TTL),
        )
        log_info("REFRESH", f"Token refreshed: {username}")
        return {
            "access_token": new_token,
            "token_type":   "bearer",
            "expires_in":   TOKEN_TTL,
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token đã hết hạn, vui lòng đăng nhập lại"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_error("REFRESH", "Lỗi refresh token", error=e)
        raise HTTPException(status_code=500, detail="Lỗi server khi refresh token")

@router.get("/me", response_model=dict)
def get_me(current_user: User = Depends(get_current_user)):
    """Thông tin user hiện tại kèm role và permissions."""
    role = _resolve_role(current_user)
    return {
        "username":    current_user.username,
        "name":        current_user.name,
        "email":       current_user.email,
        "phone":       current_user.phone,
        "position":    current_user.position,
        "department":  current_user.department,
        "status":      current_user.status,
        "role":        role,
        "permissions": _role_permissions(role),
    }


@router.post("/verify")
def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
):
    """Kiểm tra token còn hợp lệ không."""
    user = get_current_user(credentials=credentials, db=db)
    return {"valid": True, "username": user.username, "role": _resolve_role(user)}


# ── Internal helper ───────────────────────────────────────────────────────────

def _role_permissions(role: str) -> list[str]:
    if role == "admin":
        return ["read", "create", "update", "delete", "manage_users"]
    if role == "staff":
        return ["read", "create", "update"]
    return ["read"]