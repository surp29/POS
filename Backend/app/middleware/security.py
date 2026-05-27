"""
Security headers middleware.

Thêm các HTTP security headers vào mọi response.
Đây là best practice bắt buộc cho production API —
giúp chống XSS, clickjacking, MIME sniffing, và information disclosure.

Tham khảo: https://owasp.org/www-project-secure-headers/
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Tự động thêm security headers vào mọi HTTP response.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Ngăn browser đoán MIME type (chống MIME confusion attack)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Chống clickjacking — không cho nhúng app vào iframe của site khác
        response.headers["X-Frame-Options"] = "DENY"

        # Bật XSS filter của browser (legacy nhưng vẫn nên có)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Buộc HTTPS trong 1 năm (chỉ bật khi deploy production với HTTPS)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy — giới hạn nguồn script/style
        # API-only nên đơn giản: chỉ cho phép same-origin
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # Không gửi Referrer header khi navigate ra ngoài
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy — tắt các browser API nhạy cảm không cần dùng
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # Ẩn thông tin server (mặc định uvicorn trả về "Server: uvicorn")
        # Không để lộ stack ra ngoài
        response.headers["Server"] = "POS-API"

        return response