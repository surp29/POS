"""
Backend: app/api_fastapi/shipping.py
Trang vận chuyển tự xây dựng — theo dõi đơn hàng nội bộ.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import random, string

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from sqlalchemy import func, desc

from ..database import get_db
from ..models import User, Shipment, ShipmentHistory
from ..services.auth_helper import get_username_from_request
from ..logger import log_info, log_success, log_error

router = APIRouter(prefix="/shipping", tags=["shipping"])

# ── Trạng thái và luồng chuyển trạng thái ────────────────────────────────────
STATUS_FLOW = {
    "pending":    {"label": "Chờ lấy hàng",      "next": ["picked", "cancelled"]},
    "picked":     {"label": "Đã lấy hàng",        "next": ["in_transit"]},
    "in_transit": {"label": "Đang vận chuyển",    "next": ["delivering", "failed"]},
    "delivering": {"label": "Đang giao",           "next": ["delivered", "failed"]},
    "delivered":  {"label": "Đã giao thành công", "next": []},
    "failed":     {"label": "Giao thất bại",       "next": ["delivering", "returned"]},
    "returned":   {"label": "Đã hoàn hàng",        "next": []},
    "cancelled":  {"label": "Đã hủy",              "next": []},
}

STATUS_DESCRIPTIONS = {
    "pending":    "Đơn hàng đang chờ được lấy",
    "picked":     "Shipper đã lấy hàng từ kho",
    "in_transit": "Hàng đang trên đường vận chuyển",
    "delivering": "Shipper đang giao đến địa chỉ nhận",
    "delivered":  "Giao hàng thành công",
    "failed":     "Giao hàng thất bại",
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

def _gen_tracking_code():
    return "VD" + datetime.now().strftime("%y%m%d") + \
           ''.join(random.choices(string.digits, k=6))


def _shipment_dict(s: Shipment) -> dict:
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
        "status_label":     STATUS_FLOW.get(s.status, {}).get("label", s.status),
        "next_statuses":    STATUS_FLOW.get(s.status, {}).get("next", []),
        "shipper_name":     s.shipper_name,
        "shipper_phone":    s.shipper_phone,
        "created_by":       s.created_by,
        "created_at":       s.created_at.isoformat() if s.created_at else None,
        "updated_at":       s.updated_at.isoformat() if s.updated_at else None,
        "estimated_date":   s.estimated_date.isoformat() if s.estimated_date else None,
        "delivered_at":     s.delivered_at.isoformat() if s.delivered_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/statuses")
def get_statuses():
    """Trả về danh sách trạng thái + luồng chuyển."""
    return {"success": True, "statuses": STATUS_FLOW, "service_fees": SERVICE_FEES}


@router.get("/")
def list_shipments(
    status:   Optional[str] = Query(None),
    q:        Optional[str] = Query(None),
    limit:    int = Query(50, ge=1, le=200),
    offset:   int = Query(0,  ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Shipment)
    if status: query = query.filter(Shipment.status == status)
    if q:
        ql = f"%{q}%"
        query = query.filter(
            Shipment.tracking_code.ilike(ql) |
            Shipment.order_code.ilike(ql) |
            Shipment.receiver_name.ilike(ql) |
            Shipment.receiver_phone.ilike(ql)
        )
    total = query.with_entities(func.count(Shipment.id)).scalar()
    items = query.order_by(desc(Shipment.id)).offset(offset).limit(limit).all()

    # Stats
    stats = {}
    for st in STATUS_FLOW:
        stats[st] = db.query(func.count(Shipment.id)).filter(Shipment.status == st).scalar() or 0

    return {
        "success":   True,
        "total":     total,
        "stats":     stats,
        "shipments": [_shipment_dict(s) for s in items],
    }


@router.get("/{shipment_id}")
def get_shipment(shipment_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_permission('shipping.view'))
):
    s = db.query(Shipment).get(shipment_id)
    if not s: raise HTTPException(404, "Không tìm thấy đơn vận chuyển")
    hist = db.query(ShipmentHistory).filter(
        ShipmentHistory.shipment_id == shipment_id
    ).order_by(desc(ShipmentHistory.timestamp)).all()
    return {
        "success":  True,
        "shipment": _shipment_dict(s),
        "history":  [
            {
                "status":      h.status,
                "status_label": STATUS_FLOW.get(h.status, {}).get("label", h.status),
                "description": h.description,
                "location":    h.location,
                "updated_by":  h.updated_by,
                "timestamp":   h.timestamp.isoformat() if h.timestamp else None,
            }
            for h in hist
        ],
    }


@router.get("/track/{tracking_code}")
def track_by_code(tracking_code: str, db: Session = Depends(get_db),
    _: User = Depends(require_permission('shipping.view'))
):
    s = db.query(Shipment).filter(Shipment.tracking_code == tracking_code).first()
    if not s: raise HTTPException(404, f"Không tìm thấy mã vận đơn: {tracking_code}")
    return get_shipment(s.id, db)


@router.post("/")
def create_shipment(payload: dict, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('shipping.create'))
):
    username = get_username_from_request(request)

    # Tự sinh tracking code
    tracking = payload.get("tracking_code") or _gen_tracking_code()
    # Đảm bảo unique
    while db.query(Shipment).filter(Shipment.tracking_code == tracking).first():
        tracking = _gen_tracking_code()

    service  = payload.get("service_type", "Giao hàng thường")
    fee      = SERVICE_FEES.get(service, 15000)
    est_days = 1 if "hỏa tốc" in service.lower() else (
               1 if "nhanh" in service.lower() else 3
    )

    s = Shipment(
        order_code       = payload.get("order_code", ""),
        invoice_code     = payload.get("invoice_code"),
        tracking_code    = tracking,
        receiver_name    = payload.get("receiver_name", ""),
        receiver_phone   = payload.get("receiver_phone", ""),
        receiver_address = payload.get("receiver_address", ""),
        receiver_province= payload.get("receiver_province"),
        weight           = int(payload.get("weight", 500)),
        service_type     = service,
        cod_amount       = float(payload.get("cod_amount", 0)),
        shipping_fee     = float(payload.get("shipping_fee", fee)),
        note             = payload.get("note", ""),
        shipper_name     = payload.get("shipper_name"),
        shipper_phone    = payload.get("shipper_phone"),
        status           = "pending",
        created_by       = username,
        estimated_date   = datetime.now() + timedelta(days=est_days),
    )
    db.add(s)
    db.flush()

    # Tạo history đầu tiên
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
def update_status(shipment_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('shipping.update_status'))
):
    """Cập nhật trạng thái đơn vận chuyển."""
    s = db.query(Shipment).get(shipment_id)
    if not s: raise HTTPException(404, "Không tìm thấy đơn vận chuyển")

    new_status = payload.get("status")
    allowed    = STATUS_FLOW.get(s.status, {}).get("next", [])

    if new_status not in allowed:
        raise HTTPException(400, f"Không thể chuyển từ '{s.status}' sang '{new_status}'. "
                                 f"Cho phép: {allowed}")

    username    = get_username_from_request(request)
    description = payload.get("description") or STATUS_DESCRIPTIONS.get(new_status, "")
    location    = payload.get("location", "")

    s.status     = new_status
    s.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if new_status == "delivered":
        s.delivered_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if payload.get("shipper_name"): s.shipper_name  = payload["shipper_name"]
    if payload.get("shipper_phone"): s.shipper_phone = payload["shipper_phone"]

    db.add(ShipmentHistory(
        shipment_id = s.id,
        status      = new_status,
        description = description,
        location    = location,
        updated_by  = username,
    ))
    db.commit()
    log_success("SHIPPING", f"Cập nhật {s.tracking_code}: {new_status}")
    return {"success": True, "status": new_status, "tracking_code": s.tracking_code}


@router.put("/{shipment_id}")
def update_shipment(shipment_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('shipping.update_status'))
):
    """Cập nhật thông tin đơn (shipper, ghi chú...)."""
    s = db.query(Shipment).get(shipment_id)
    if not s: raise HTTPException(404, "Không tìm thấy đơn vận chuyển")
    if s.status in ("delivered", "returned", "cancelled"):
        raise HTTPException(400, "Không thể sửa đơn đã hoàn tất")

    for field in ("receiver_name","receiver_phone","receiver_address","shipper_name","shipper_phone","note","cod_amount","shipping_fee"):
        if field in payload:
            setattr(s, field, payload[field])
    db.commit()
    return {"success": True}


@router.delete("/{shipment_id}")
def cancel_shipment(shipment_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('shipping.cancel'))
):
    s = db.query(Shipment).get(shipment_id)
    if not s: raise HTTPException(404, "Không tìm thấy đơn vận chuyển")
    if s.status not in ("pending",):
        raise HTTPException(400, "Chỉ có thể hủy đơn khi còn ở trạng thái 'Chờ lấy hàng'")

    username = get_username_from_request(request)
    s.status = "cancelled"
    db.add(ShipmentHistory(shipment_id=s.id, status="cancelled",
                           description="Đơn vận chuyển đã bị hủy", updated_by=username))
    db.commit()
    return {"success": True}