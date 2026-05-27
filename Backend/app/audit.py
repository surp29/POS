"""
Audit Log Service — ghi lại mọi thao tác CRUD.
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.orm import Session
from fastapi import Request

from .logger import log_warning
# Import AuditLog ở module level để patch được trong test
from .models import AuditLog


def _serialize(data: Any) -> Optional[str]:
    if data is None:
        return None
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return str(data)


def _get_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def audit_log(
    db:          Session,
    action:      str,
    entity:      str,
    entity_id:   Optional[str]  = None,
    username:    Optional[str]  = None,
    before:      Optional[dict] = None,
    after:       Optional[dict] = None,
    description: Optional[str]  = None,
    request:     Optional[Request] = None,
    status:      str = "success",
) -> bool:
    """
    Ghi một audit log entry vào DB.
    Trả về True nếu thành công, False nếu lỗi (không raise exception).
    """
    try:
        entry = AuditLog(
            timestamp   = datetime.now(timezone.utc).replace(tzinfo=None),
            action      = action.upper()[:20],
            entity      = entity[:50],
            entity_id   = str(entity_id)[:50] if entity_id else None,
            username    = (username or "system")[:50],
            ip_address  = _get_ip(request),
            before_data = _serialize(before),
            after_data  = _serialize(after),
            description = description[:500] if description else None,
            status      = status[:20],
        )
        db.add(entry)
        db.flush()
        return True
    except Exception as e:
        log_warning("AUDIT", f"Không thể ghi audit log ({action} {entity}): {e}")
        return False


def audit_log_commit(
    db:          Session,
    action:      str,
    entity:      str,
    entity_id:   Optional[str]  = None,
    username:    Optional[str]  = None,
    before:      Optional[dict] = None,
    after:       Optional[dict] = None,
    description: Optional[str]  = None,
    request:     Optional[Request] = None,
) -> bool:
    success = audit_log(
        db=db, action=action, entity=entity,
        entity_id=entity_id, username=username,
        before=before, after=after,
        description=description, request=request,
    )
    if success:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            log_warning("AUDIT", f"Lỗi commit audit log: {e}")
            return False
    return success


def _path_to_entity(path: str) -> str:
    parts = [p for p in path.strip("/").split("/") if p and not p.isdigit()]
    if len(parts) >= 2:
        return parts[1].rstrip("s").capitalize()
    return "Unknown"


# ── Middleware ────────────────────────────────────────────────────────────────

from fastapi import Request as FastAPIRequest
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware


class AuditMiddleware(BaseHTTPMiddleware):
    SKIP_PATHS   = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json"}
    AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: FastAPIRequest, call_next) -> Response:
        if (request.method not in self.AUDIT_METHODS
                or request.url.path in self.SKIP_PATHS
                or request.url.path.startswith("/static")
                or request.url.path.startswith("/api/ws")):
            return await call_next(request)

        start_time = time.perf_counter()
        response   = await call_next(request)
        duration   = time.perf_counter() - start_time

        username = None
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                import jwt
                from .config import Config
                payload  = jwt.decode(
                    auth_header[7:], Config.JWT_SECRET_KEY,
                    algorithms=["HS256"],
                    options={"verify_exp": False},
                )
                username = payload.get("sub")
        except Exception:
            pass

        try:
            from .database import SessionLocal
            db = SessionLocal()
            try:
                status = "success" if response.status_code < 400 else "failed"
                audit_log(
                    db=db,
                    action=request.method,
                    entity=_path_to_entity(request.url.path),
                    username=username,
                    request=request,
                    description=(
                        f"{request.method} {request.url.path} "
                        f"→ {response.status_code} ({duration:.3f}s)"
                    ),
                    status=status,
                )
                db.commit()
            finally:
                db.close()
        except Exception as e:
            log_warning("AUDIT_MW", f"Lỗi ghi audit middleware: {e}")

        return response