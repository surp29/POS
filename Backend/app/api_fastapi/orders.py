"""
Orders API — tích hợp WebSocket real-time broadcast.

Khi tạo/cập nhật/xóa đơn hàng:
  → Broadcast event đến room "orders"
  → Tất cả client đang xem orders nhận được update ngay lập tức

Khi tồn kho xuống thấp:
  → Broadcast event đến room "inventory"
"""
import asyncio
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from sqlalchemy import or_, func

from ..database import get_db
from ..models import User, Order, OrderItem, Product, Account, Warehouse
from ..schemas_fastapi import OrderOut, OrderCreate, OrderUpdate
from ..logger import log_info, log_success, log_error, log_warning
from ..services.orders import create_order_service
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request
from ..websocket_manager import manager, order_event, inventory_event

router = APIRouter(prefix="/orders", tags=["orders"])

LOW_STOCK_THRESHOLD = 10   # Ngưỡng cảnh báo tồn kho


async def _broadcast_order_event(event_type: str, order_data: dict) -> None:
    """Helper broadcast order event — không block response."""
    try:
        event = order_event(event_type, order_data)
        await manager.broadcast(event, room="orders")
        await manager.broadcast(event, room="global")
    except Exception as e:
        log_warning("WS_BROADCAST", f"Lỗi broadcast order event: {e}")


async def _broadcast_inventory_event(product: Product) -> None:
    """Broadcast inventory update, kèm cảnh báo nếu tồn kho thấp."""
    try:
        qty = int(product.so_luong or 0)
        event_type = "out_of_stock" if qty == 0 else (
            "low_stock" if qty < LOW_STOCK_THRESHOLD else "updated"
        )
        event = inventory_event(event_type, {
            "ma_sp":      product.ma_sp,
            "ten_sp":     product.ten_sp,
            "so_luong":   qty,
            "trang_thai": product.trang_thai,
            "threshold":  LOW_STOCK_THRESHOLD,
        })
        await manager.broadcast(event, room="inventory")
        await manager.broadcast(event, room="global")

        if qty < LOW_STOCK_THRESHOLD:
            await manager.broadcast(event, room="dashboard")
    except Exception as e:
        log_warning("WS_BROADCAST", f"Lỗi broadcast inventory event: {e}")


@router.get("/check-duplicate")
def check_duplicate(
    ma_don_hang: str = Query(...),
    db: Session = Depends(get_db),
):
    code   = (ma_don_hang or "").strip()
    exists = bool(code) and db.query(Order).filter(
        Order.ma_don_hang == code
    ).first() is not None
    return {"exists": exists}


@router.get("/", response_model=dict)
def list_orders(
    limit:  int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0,  ge=0),
    db: Session = Depends(get_db),
):
    """Danh sách đơn hàng có pagination."""
    total  = db.query(func.count(Order.id)).scalar()
    orders = db.query(Order).order_by(Order.id.desc()).offset(offset).limit(limit).all()
    return {
        "success": True,
        "total":   total,
        "limit":   limit,
        "offset":  offset,
        "orders":  [OrderOut.model_validate(o).model_dump() for o in orders],
    }


@router.get("/search")
def search_orders(
    customer_id:   Optional[int] = None,
    customer_name: Optional[str] = None,
    q:             Optional[str] = None,
    limit:  int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0,   ge=0),
    db: Session = Depends(get_db),
):
    """Tìm kiếm đơn hàng — N+1 fix."""
    query = db.query(Order)

    customer_filters = []
    if customer_name:
        name_clean = customer_name.strip()
        if name_clean and name_clean != 'Khách vãng lai':
            customer_filters.append(Order.thong_tin_kh.ilike(f"%{name_clean}%"))

    if customer_id is not None:
        try:
            acc = db.get(Account, int(customer_id))
        except Exception:
            acc = None
        if acc:
            if acc.ten_tk:
                customer_filters.append(Order.thong_tin_kh.ilike(f"%{acc.ten_tk.strip()}%"))
            if acc.ma_khach_hang:
                customer_filters.append(Order.thong_tin_kh.ilike(f"%{acc.ma_khach_hang.strip()}%"))

    if customer_filters:
        query = query.filter(or_(*customer_filters))

    if q:
        ql = f"%{q}%"
        query = query.filter(
            (Order.ma_don_hang.ilike(ql)) | (Order.trang_thai.ilike(ql))
        )

    query = query.filter(or_(
        Order.trang_thai.ilike('%hoan_thanh%'),
        Order.trang_thai.ilike('%Hoàn thành%'),
        Order.trang_thai.ilike('%hoàn thành%'),
        Order.trang_thai.ilike('%hoan thanh%'),
    ))

    total   = query.with_entities(func.count(Order.id)).scalar()
    results = query.order_by(Order.id.desc()).offset(offset).limit(limit).all()

    # Fix N+1: load product set 1 lần
    sp_codes = {o.sp_banggia for o in results if o.sp_banggia}
    product_set: set[str] = set()
    if sp_codes:
        rows = db.query(Product.ma_sp).filter(Product.ma_sp.in_(sp_codes)).all()
        product_set = {row.ma_sp for row in rows}

    out = []
    for o in results:
        if o.sp_banggia:
            loai = 'Sản phẩm' if o.sp_banggia in product_set else 'Hành động (Bảng giá)'
        else:
            loai = 'Khác'
        out.append({
            'id':            o.id,
            'ma_don_hang':   o.ma_don_hang,
            'tong_tien':     o.tong_tien,
            'trang_thai':    o.trang_thai,
            'sp_banggia':    o.sp_banggia,
            'loai_suy_luan': loai,
        })

    return {"success": True, "total": total, "orders": out}


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    return OrderOut.model_validate(o).model_dump()


@router.post("/")
async def create_order(payload: OrderCreate, db: Session = Depends(get_db),
    _: User = Depends(require_permission('orders.create'))):
    """Tạo đơn hàng + broadcast WebSocket event."""
    log_info("CREATE_ORDER", f"Tạo đơn hàng: {payload.ma_don_hang}")
    try:
        if not (payload.ma_don_hang or "").strip():
            raise HTTPException(status_code=400, detail="Mã đơn hàng không được để trống")
        if not (payload.thong_tin_kh or "").strip():
            raise HTTPException(status_code=400, detail="Thông tin khách hàng không được để trống")

        ngay_tao       = payload.ngay_tao if payload.ngay_tao else date.today()
        service_res    = create_order_service(payload, db)
        computed_total = service_res['computed_total']
        is_product     = service_res['is_product']
        product        = service_res['product']

        if db.query(Order).filter(Order.ma_don_hang == payload.ma_don_hang).first():
            raise HTTPException(
                status_code=400,
                detail=f"Mã đơn hàng '{payload.ma_don_hang}' đã tồn tại!",
            )

        o = Order(
            ma_don_hang=payload.ma_don_hang,
            thong_tin_kh=payload.thong_tin_kh,
            sp_banggia=payload.sp_banggia,
            ngay_tao=ngay_tao,
            ma_co_quan_thue=payload.ma_co_quan_thue,
            so_luong=payload.so_luong or 1,
            tong_tien=computed_total,
            trang_thai=payload.trang_thai or 'cho_xu_ly',
        )
        db.add(o)
        db.commit()
        db.refresh(o)

        quantity_out = 0
        if is_product and product and payload.so_luong:
            current_qty  = int(getattr(product, 'so_luong', 0) or 0)
            quantity_out = int(payload.so_luong or 0)
            new_qty      = max(current_qty - quantity_out, 0)
            product.so_luong   = new_qty
            product.trang_thai = 'Còn hàng' if new_qty > 0 else 'Hết hàng'

            wh = db.query(Warehouse).filter(Warehouse.ma_sp == payload.sp_banggia).first()
            if wh:
                wh.so_luong   = max(0, (wh.so_luong or 0) - quantity_out)
                wh.trang_thai = 'Còn hàng' if wh.so_luong > 0 else 'Hết hàng'
            db.commit()

            # ── Broadcast inventory update ─────────────────────────────────
            await _broadcast_inventory_event(product)

        try:
            create_general_diary_entry(
                db=db, source="Order", total_amount=computed_total or 0.0,
                quantity_out=quantity_out, quantity_in=0,
                description=(
                    f"Đơn {payload.ma_don_hang} - KH: {payload.thong_tin_kh}"
                    f" - SP: {payload.sp_banggia or 'N/A'}"
                ),
            )
            db.commit()
        except Exception as e:
            db.rollback()
            log_error("CREATE_ORDER_DIARY", "Lỗi ghi General Diary", error=e)

        # ── Broadcast order created event ──────────────────────────────────
        await _broadcast_order_event("created", {
            "id":          o.id,
            "ma_don_hang": o.ma_don_hang,
            "thong_tin_kh": o.thong_tin_kh,
            "sp_banggia":  o.sp_banggia,
            "tong_tien":   o.tong_tien,
            "trang_thai":  o.trang_thai,
            "ngay_tao":    str(o.ngay_tao),
        })

        log_success("CREATE_ORDER", f"Tạo thành công: {payload.ma_don_hang}")
        return {"success": True, "id": o.id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_error("CREATE_ORDER", f"Lỗi tạo đơn {payload.ma_don_hang}", error=e)
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo đơn hàng: {str(e)}")


@router.put("/{order_id}")
async def update_order(
    order_id: int,
    payload:  OrderUpdate,
    request:  Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission('orders.edit')),
):
    """Cập nhật đơn hàng + broadcast WebSocket event."""
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")

    username   = get_username_from_request(request)
    old_status = o.trang_thai

    if payload.trang_thai is not None:   o.trang_thai   = payload.trang_thai
    if payload.thong_tin_kh is not None: o.thong_tin_kh = payload.thong_tin_kh
    if payload.tong_tien is not None:    o.tong_tien    = payload.tong_tien

    db.commit()
    db.refresh(o)

    try:
        create_general_diary_entry(
            db=db, source="Order", total_amount=o.tong_tien or 0.0,
            quantity_out=0, quantity_in=0,
            description=f"Cập nhật đơn {o.ma_don_hang}: {old_status} → {o.trang_thai}"[:255],
            username=username,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        log_error("UPDATE_ORDER_DIARY", "Lỗi ghi General Diary", error=e)

    # ── Broadcast order updated / status_changed ───────────────────────────
    event_type = "status_changed" if old_status != o.trang_thai else "updated"
    await _broadcast_order_event(event_type, {
        "id":          o.id,
        "ma_don_hang": o.ma_don_hang,
        "trang_thai":  o.trang_thai,
        "old_status":  old_status,
        "tong_tien":   o.tong_tien,
    })

    log_success("UPDATE_ORDER", f"Cập nhật đơn {o.ma_don_hang} thành công")
    return {"success": True, "id": o.id}


@router.delete("/{order_id}")
async def delete_order(order_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('orders.delete'))):
    """Xóa đơn hàng + broadcast WebSocket event."""
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")

    username  = get_username_from_request(request)
    ma        = o.ma_don_hang
    order_data = {"id": order_id, "ma_don_hang": ma}

    db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()
    db.delete(o)
    db.flush()

    try:
        create_general_diary_entry(
            db=db, source="Order", total_amount=0.0,
            quantity_out=0, quantity_in=0,
            description=f"Xóa đơn hàng: {ma}"[:255],
            username=username,
        )
        db.commit()
    except Exception as e:
        log_error("DELETE_ORDER_DIARY", "Lỗi ghi General Diary", error=e)
        db.commit()

    # ── Broadcast order deleted ────────────────────────────────────────────
    await _broadcast_order_event("deleted", order_data)

    log_success("DELETE_ORDER", f"Xóa đơn {ma} thành công")
    return {"success": True}