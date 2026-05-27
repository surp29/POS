"""
Audit Log API — xem lịch sử thao tác.

Endpoints:
  GET /audit/          → danh sách audit logs (có filter + pagination)
  GET /audit/{id}      → chi tiết 1 record
  GET /audit/summary   → thống kê theo entity/user/action

Chỉ admin mới được xem audit log.
"""
from datetime import datetime, date
from typing import Optional
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from ..database import get_db
from ..models import AuditLog
from ..rbac import require_admin
from ..models import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/")
def list_audit_logs(
    action:    Optional[str] = Query(None, description="CREATE/UPDATE/DELETE/LOGIN"),
    entity:    Optional[str] = Query(None, description="Product/Order/User/..."),
    username:  Optional[str] = Query(None, description="Lọc theo user"),
    status:    Optional[str] = Query(None, description="success/failed"),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit:     int = Query(default=50, ge=1, le=200),
    offset:    int = Query(default=0,  ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Danh sách audit logs với filter linh hoạt.
    Chỉ admin mới được xem.
    """
    query = db.query(AuditLog)

    if action:   query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity:   query = query.filter(AuditLog.entity.ilike(f"%{entity}%"))
    if username: query = query.filter(AuditLog.username.ilike(f"%{username}%"))
    if status:   query = query.filter(AuditLog.status == status)

    if from_date:
        try:
            dt = datetime.strptime(from_date, "%Y-%m-%d")
            query = query.filter(AuditLog.timestamp >= dt)
        except ValueError:
            pass
    if to_date:
        try:
            dt = datetime.strptime(to_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            query = query.filter(AuditLog.timestamp <= dt)
        except ValueError:
            pass

    total   = query.with_entities(func.count(AuditLog.id)).scalar()
    records = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit).all()

    def _parse(json_str):
        if not json_str:
            return None
        try:
            return json.loads(json_str)
        except Exception:
            return json_str

    return {
        "success": True,
        "total":   total,
        "limit":   limit,
        "offset":  offset,
        "logs": [
            {
                "id":          r.id,
                "timestamp":   r.timestamp.isoformat() if r.timestamp else None,
                "action":      r.action,
                "entity":      r.entity,
                "entity_id":   r.entity_id,
                "username":    r.username,
                "ip_address":  r.ip_address,
                "description": r.description,
                "status":      r.status,
                "before":      _parse(r.before_data),
                "after":       _parse(r.after_data),
            }
            for r in records
        ],
    }


@router.get("/summary")
def audit_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Thống kê audit log theo action, entity, user."""
    by_action = db.query(
        AuditLog.action,
        func.count(AuditLog.id).label("count"),
    ).group_by(AuditLog.action).all()

    by_entity = db.query(
        AuditLog.entity,
        func.count(AuditLog.id).label("count"),
    ).group_by(AuditLog.entity).order_by(desc("count")).limit(10).all()

    by_user = db.query(
        AuditLog.username,
        func.count(AuditLog.id).label("count"),
    ).group_by(AuditLog.username).order_by(desc("count")).limit(10).all()

    failed = db.query(func.count(AuditLog.id)).filter(
        AuditLog.status == "failed"
    ).scalar()

    total = db.query(func.count(AuditLog.id)).scalar()

    return {
        "success":    True,
        "total":      total,
        "failed":     failed,
        "by_action":  [{"action": r.action, "count": r.count} for r in by_action],
        "by_entity":  [{"entity": r.entity, "count": r.count} for r in by_entity],
        "by_user":    [{"username": r.username, "count": r.count} for r in by_user],
    }


@router.get("/{log_id}")
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Chi tiết 1 audit log record."""
    import json as _json
    record = db.query(AuditLog).get(log_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Không tìm thấy audit log")

    def _parse(s):
        if not s:
            return None
        try:
            return _json.loads(s)
        except Exception:
            return s

    return {
        "id":          record.id,
        "timestamp":   record.timestamp.isoformat() if record.timestamp else None,
        "action":      record.action,
        "entity":      record.entity,
        "entity_id":   record.entity_id,
        "username":    record.username,
        "ip_address":  record.ip_address,
        "description": record.description,
        "status":      record.status,
        "before":      _parse(record.before_data),
        "after":       _parse(record.after_data),
    }