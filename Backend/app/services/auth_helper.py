"""
Helper lấy thông tin user từ JWT token trong Request.
Dùng cho các endpoint chưa migrate sang Depends(get_current_user).
Các endpoint mới nên dùng get_current_user() trong auth.py thay thế.
"""
from typing import Optional

import jwt
from fastapi import Request

from ..config import Config
from ..cache import is_token_blacklisted

SECRET_KEY = Config.JWT_SECRET_KEY
ALGORITHM  = "HS256"


def _decode_token(token: str) -> Optional[dict]:
    """Decode và trả về payload, None nếu token không hợp lệ."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_username_from_request(request: Request) -> Optional[str]:
    """
    Lấy username từ Authorization header.
    Trả về None nếu không có token, token lỗi, hoặc token đã bị blacklist.
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None

    token = authorization.removeprefix("Bearer ").strip()
    payload = _decode_token(token)
    if payload is None:
        return None

    # Kiểm tra blacklist (token đã logout chưa)
    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        return None

    return payload.get("sub")


def get_payload_from_request(request: Request) -> Optional[dict]:
    """
    Trả về toàn bộ JWT payload.
    Dùng khi cần thêm thông tin ngoài username (vd: role, jti).
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None

    token = authorization.removeprefix("Bearer ").strip()
    payload = _decode_token(token)
    if payload is None:
        return None

    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        return None

    return payload