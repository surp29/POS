"""
Service-to-service auth cho endpoint tích hợp POS ↔ Ecommerce.

Project trước đây chỉ có JWT đăng nhập user (auth.py) — không phù hợp cho gọi máy-
đến-máy (Ecommerce Backend gọi POS, không có "người dùng" đăng nhập). Dùng shared
secret đơn giản qua header `X-API-Key`, so sánh bằng `secrets.compare_digest` để
tránh timing attack. Không dùng chung cơ chế JWT user vì 2 khái niệm auth khác nhau:
JWT user gắn với quyền hạn nhân viên (module.action), còn integration key chỉ xác
định "đúng là Ecommerce Backend đang gọi", không có khái niệm quyền hạn phía trong.
"""
import secrets

from fastapi import Header, HTTPException

from .config import Config


def require_integration_key(x_api_key: str = Header(default=None, alias="X-API-Key")) -> bool:
    expected = Config.INTEGRATION_API_KEY
    if not expected:
        # Chưa cấu hình secret trong .env → chặn hẳn, không fail-open (khác rate-limit
        # middleware vốn fail-open khi Redis down — ở đây fail-open đồng nghĩa mở toang
        # endpoint tạo đơn/trừ kho ra internet).
        raise HTTPException(status_code=503, detail="Integration API chưa được cấu hình")
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="X-API-Key không hợp lệ")
    return True
