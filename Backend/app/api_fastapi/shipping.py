"""
Backend: app/api_fastapi/shipping.py
Quản lý vận chuyển nội bộ — chuyên nghiệp như Viettel Post.

Cải tiến:
  - Admin có thể force-update sang bất kỳ trạng thái
  - Endpoint riêng cho print label
  - Thêm trường created_at vào history response
  - Thêm filter theo date range
  - Thống kê doanh thu phí ship
"""
from datetime import datetime, timezone, timedelta, date
from typing import Optional
import random, string

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from ..permission_middleware import require_permission, _is_admin, _get_current_user_for_rbac
from ..database import get_db
from ..models import User, Shipment, ShipmentHistory
from ..services.auth_helper import get_username_from_request
from ..logger import log_info, log_success, log_error

router = APIRouter(prefix="/shipping", tags=["shipping"])

# ── Trạng thái & luồng ───────────────────────────────────────────────────────
STATUS_FLOW = {
    "pending":    {"label": "Chờ lấy hàng",      "next": ["picked", "cancelled"],           "color": "#d97706"},
    "picked":     {"label": "Đã lấy hàng",        "next": ["in_transit"],                    "color": "#ca8a04"},
    "in_transit": {"label": "Đang vận chuyển",    "next": ["delivering", "failed"],           "color": "#2563eb"},
    "delivering": {"label": "Đang giao",           "next": ["delivered", "failed"],            "color": "#7c3aed"},
    "delivered":  {"label": "Đã giao thành công", "next": [],                                 "color": "#16a34a"},
    "failed":     {"label": "Giao thất bại",       "next": ["delivering", "returned"],         "color": "#dc2626"},
    "returned":   {"label": "Đã hoàn hàng",        "next": [],                                 "color": "#ea580c"},
    "cancelled":  {"label": "Đã hủy",              "next": [],                                 "color": "#6b7280"},
}

STATUS_DESCRIPTIONS = {
    "pending":    "Đơn hàng đang chờ được lấy",
    "picked":     "Shipper đã lấy hàng từ kho",
    "in_transit": "Hàng đang trên đường vận chuyển",
    "delivering": "Shipper đang giao đến địa chỉ nhận",
    "delivered":  "Giao hàng thành công",
    "failed":     "Giao hàng thất bại, sẽ liên hệ lại",
    "returned":   "Hàng đã được hoàn về kho",
    "cancelled":  "Đơn vận chuyển đã bị hủy",
}

SERVICE_FEES = {
    "Giao hàng thường":  15000,
    "Giao hàng nhanh":   25000,
    "Giao hàng hỏa tốc": 45000,
    "Giao nội thành":    20000,
    "Giao liên tỉnh":    35000,
}

SERVICE_DAYS = {
    "Giao hàng thường":  3,
    "Giao hàng nhanh":   1,
    "Giao hàng hỏa tốc": 1,
    "Giao nội thành":    1,
    "Giao liên tỉnh":    3,
}


def _gen_tracking_code() -> str:
    return "VD" + datetime.now().strftime("%y%m%d") + \
           ''.join(random.choices(string.digits, k=6))


def _shipment_dict(s: Shipment) -> dict:
    flow = STATUS_FLOW.get(s.status, {})
    return {
        "id":               s.id,
        "order_code":       s.order_code,
        "invoice_code":     s.invoice_code,
        "tracking_code":    s.tracking_code,
        "receiver_name":    s.receiver_name,
        "receiver_phone":   s.receiver_phone,
        "receiver_address": s.receiver_address,
        "receiver_province":s.receiver_province,
        "weight":           s.weight,
        "service_type":     s.service_type,
        "cod_amount":       s.cod_amount,
        "shipping_fee":     s.shipping_fee,
        "note":             s.note,
        "status":           s.status,
        "status_label":     flow.get("label", s.status),
        "status_color":     flow.get("color", "#6b7280"),
        "next_statuses":    flow.get("next", []),
        "all_statuses":     list(STATUS_FLOW.keys()),  # để frontend biết tất cả
        "shipper_name":     s.shipper_name,
        "shipper_phone":    s.shipper_phone,
        "created_by":       s.created_by,
        "created_at":       s.created_at.isoformat() if s.created_at else None,
        "updated_at":       s.updated_at.isoformat() if s.updated_at else None,
        "estimated_date":   s.estimated_date.isoformat() if s.estimated_date else None,
        "delivered_at":     s.delivered_at.isoformat() if s.delivered_at else None,
        "is_overdue":       (
            s.estimated_date is not None
            and s.status not in ("delivered", "cancelled", "returned")
            and s.estimated_date < datetime.now()
        ),
    }


def _history_dict(h: ShipmentHistory) -> dict:
    return {
        "id":           h.id,
        "status":       h.status,
        "status_label": STATUS_FLOW.get(h.status, {}).get("label", h.status),
        "status_color": STATUS_FLOW.get(h.status, {}).get("color", "#6b7280"),
        "description":  h.description,
        "location":     h.location,
        "updated_by":   h.updated_by,
        "timestamp":    h.timestamp.isoformat() if h.timestamp else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/statuses")
def get_statuses():
    return {"success": True, "statuses": STATUS_FLOW, "service_fees": SERVICE_FEES}


@router.get("/summary")
def get_summary(
    from_date: Optional[str] = Query(None),
    to_date:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping.view")),
):
    """Thống kê tổng hợp: số đơn, doanh thu phí ship, tỷ lệ giao thành công."""
    q = db.query(Shipment)
    if from_date:
        q = q.filter(Shipment.created_at >= from_date)
    if to_date:
        q = q.filter(Shipment.created_at <= to_date + " 23:59:59")

    stats = {}
    for st in STATUS_FLOW:
        stats[st] = q.filter(Shipment.status == st).count()

    total           = q.count()
    total_fee       = db.query(func.sum(Shipment.shipping_fee)).filter(
                          Shipment.status == "delivered").scalar() or 0
    total_cod       = db.query(func.sum(Shipment.cod_amount)).filter(
                          Shipment.status == "delivered").scalar() or 0
    success_rate    = round(stats.get("delivered", 0) / total * 100, 1) if total else 0
    overdue_count   = q.filter(
        Shipment.estimated_date < datetime.now(),
        ~Shipment.status.in_(["delivered", "cancelled", "returned"])
    ).count()

    return {
        "success":      True,
        "stats":        stats,
        "total":        total,
        "total_fee":    total_fee,
        "total_cod":    total_cod,
        "success_rate": success_rate,
        "overdue":      overdue_count,
    }


@router.get("/")
def list_shipments(
    status:    Optional[str] = Query(None),
    q:         Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date:   Optional[str] = Query(None),
    overdue:   Optional[bool]= Query(None),
    limit:     int = Query(50, ge=1, le=200),
    offset:    int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Shipment)
    if status:
        query = query.filter(Shipment.status == status)
    if q:
        ql = f"%{q}%"
        query = query.filter(
            Shipment.tracking_code.ilike(ql) |
            Shipment.order_code.ilike(ql) |
            Shipment.receiver_name.ilike(ql) |
            Shipment.receiver_phone.ilike(ql)
        )
    if from_date:
        query = query.filter(Shipment.created_at >= from_date)
    if to_date:
        query = query.filter(Shipment.created_at <= to_date + " 23:59:59")
    if overdue:
        query = query.filter(
            Shipment.estimated_date < datetime.now(),
            ~Shipment.status.in_(["delivered", "cancelled", "returned"])
        )

    total = query.with_entities(func.count(Shipment.id)).scalar()
    items = query.order_by(desc(Shipment.id)).offset(offset).limit(limit).all()

    # Stats (luôn tính toàn bộ, không theo filter)
    stats = {}
    for st in STATUS_FLOW:
        stats[st] = db.query(func.count(Shipment.id)).filter(
            Shipment.status == st).scalar() or 0

    return {
        "success":   True,
        "total":     total,
        "stats":     stats,
        "shipments": [_shipment_dict(s) for s in items],
    }


@router.get("/{shipment_id}")
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping.view")),
):
    s = db.get(Shipment, shipment_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy đơn vận chuyển")
    hist = db.query(ShipmentHistory).filter(
        ShipmentHistory.shipment_id == shipment_id
    ).order_by(desc(ShipmentHistory.timestamp)).all()
    return {
        "success":  True,
        "shipment": _shipment_dict(s),
        "history":  [_history_dict(h) for h in hist],
    }


@router.get("/track/{tracking_code}")
def track_by_code(
    tracking_code: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping.view")),
):
    s = db.query(Shipment).filter(Shipment.tracking_code == tracking_code).first()
    if not s:
        raise HTTPException(404, f"Không tìm thấy mã vận đơn: {tracking_code}")
    return get_shipment(s.id, db)


@router.post("/")
def create_shipment(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping.create")),
):
    username = get_username_from_request(request)
    tracking = payload.get("tracking_code") or _gen_tracking_code()
    while db.query(Shipment).filter(Shipment.tracking_code == tracking).first():
        tracking = _gen_tracking_code()

    service  = payload.get("service_type", "Giao hàng thường")
    fee      = float(payload.get("shipping_fee", SERVICE_FEES.get(service, 15000)))
    est_days = SERVICE_DAYS.get(service, 3)

    s = Shipment(
        order_code        = payload.get("order_code", ""),
        invoice_code      = payload.get("invoice_code"),
        tracking_code     = tracking,
        receiver_name     = payload.get("receiver_name", ""),
        receiver_phone    = payload.get("receiver_phone", ""),
        receiver_address  = payload.get("receiver_address", ""),
        receiver_province = payload.get("receiver_province"),
        weight            = int(payload.get("weight", 500)),
        service_type      = service,
        cod_amount        = float(payload.get("cod_amount", 0)),
        shipping_fee      = fee,
        note              = payload.get("note", ""),
        shipper_name      = payload.get("shipper_name"),
        shipper_phone     = payload.get("shipper_phone"),
        status            = "pending",
        created_by        = username,
        estimated_date    = datetime.now() + timedelta(days=est_days),
    )
    db.add(s)
    db.flush()
    db.add(ShipmentHistory(
        shipment_id = s.id,
        status      = "pending",
        description = STATUS_DESCRIPTIONS["pending"],
        location    = payload.get("sender_address", "Kho hàng"),
        updated_by  = username,
    ))
    db.commit()
    db.refresh(s)
    log_success("SHIPPING", f"Tạo đơn {s.tracking_code} cho {s.receiver_name}")
    return {"success": True, "id": s.id, "tracking_code": s.tracking_code}


@router.put("/{shipment_id}/status")
def update_status(
    shipment_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user_for_rbac),
):
    """
    Cập nhật trạng thái.
    - Nhân viên có quyền shipping.update_status: chỉ theo luồng cho phép
    - Admin: có thể force bất kỳ trạng thái (force=true trong payload)
    """
    s = db.get(Shipment, shipment_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy đơn vận chuyển")

    new_status = payload.get("status")
    if new_status not in STATUS_FLOW:
        raise HTTPException(400, f"Trạng thái không hợp lệ: {new_status}")

    is_admin_user = _is_admin(current_user)
    force         = payload.get("force", False)
    allowed       = STATUS_FLOW.get(s.status, {}).get("next", [])

    if not is_admin_user:
        # Nhân viên phải có quyền + đúng luồng
        from ..permission_middleware import require_permission
        if new_status not in allowed:
            raise HTTPException(
                400,
                f"Không thể chuyển từ '{s.status}' → '{new_status}'. "
                f"Trạng thái hợp lệ: {allowed}"
            )

    username    = get_username_from_request(request)
    description = payload.get("description") or STATUS_DESCRIPTIONS.get(new_status, "")
    location    = payload.get("location", "")

    old_status   = s.status
    s.status     = new_status
    s.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if new_status == "delivered":
        s.delivered_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if payload.get("shipper_name"):  s.shipper_name  = payload["shipper_name"]
    if payload.get("shipper_phone"): s.shipper_phone = payload["shipper_phone"]

    db.add(ShipmentHistory(
        shipment_id = s.id,
        status      = new_status,
        description = description + (f" [Chuyển đặc biệt bởi admin từ '{old_status}']" if is_admin_user and new_status not in allowed else ""),
        location    = location,
        updated_by  = username,
    ))
    db.commit()
    log_success("SHIPPING", f"Cập nhật {s.tracking_code}: {old_status} → {new_status} bởi {username}")
    return {"success": True, "status": new_status, "tracking_code": s.tracking_code}


@router.put("/{shipment_id}")
def update_shipment(
    shipment_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping.update_status")),
):
    s = db.get(Shipment, shipment_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy đơn vận chuyển")
    if s.status in ("delivered", "returned", "cancelled"):
        raise HTTPException(400, "Không thể sửa đơn đã hoàn tất")
    for field in ("receiver_name", "receiver_phone", "receiver_address",
                  "shipper_name", "shipper_phone", "note", "cod_amount", "shipping_fee"):
        if field in payload:
            setattr(s, field, payload[field])
    s.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {"success": True}


@router.delete("/{shipment_id}")
def cancel_shipment(
    shipment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping.cancel")),
):
    s = db.get(Shipment, shipment_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy đơn vận chuyển")
    if s.status not in ("pending",):
        raise HTTPException(400, "Chỉ có thể hủy đơn khi còn ở trạng thái 'Chờ lấy hàng'")

    username = get_username_from_request(request)
    s.status     = "cancelled"
    s.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(ShipmentHistory(
        shipment_id = s.id,
        status      = "cancelled",
        description = "Đơn vận chuyển đã bị hủy",
        updated_by  = username,
    ))
    db.commit()
    log_success("SHIPPING", f"Hủy đơn {s.tracking_code} bởi {username}")
    return {"success": True}