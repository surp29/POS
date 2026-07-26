"""
Integration API — bề mặt tích hợp DUY NHẤT mà Ecommerce Backend được phép gọi vào
POS. Toàn bộ endpoint dùng `require_integration_key` (X-API-Key), KHÔNG dùng JWT
user/`require_permission` như các router nghiệp vụ khác — đây là API máy-đến-máy.

4 nhóm endpoint:
  - GET  /integration/events    poll outbox (Transactional Outbox Pattern) — đồng bộ
                                 gần-thời-gian-thực, checkpoint bằng `after_id`.
  - GET  /integration/products  snapshot đầy đủ — dùng cho full-resync định kỳ/khởi
                                 động (lưới an toàn nếu poll events bị lệch checkpoint).
  - POST /integration/orders    nhận đơn từ Ecommerce, idempotent qua `external_ref`.
         .../{id}/cancel        hoàn kho khi đơn ecommerce bị hủy sau khi đã đồng bộ.
    GET  .../{id}               đọc lại trạng thái hiện tại — dùng cho đối soát công
                                 nợ định kỳ (reconcile_orders.py bên Ecommerce), không
                                 dùng trong luồng checkout/push bình thường.
  - POST /integration/orders/{id}/returns
                                 hoàn kho TỪNG PHẦN cho đơn đã giao (trả hàng sau khi
                                 nhận, khác `.../cancel`), idempotent qua `return_ref`.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..integration_auth import require_integration_key
from ..models import Account, IntegrationEvent, Order, OrderItem, OrderReturn, Product, Warehouse
from ..schemas_fastapi import (
    IntegrationCustomer,
    IntegrationEventOut,
    IntegrationOrderCreate,
    IntegrationOrderDetailOut,
    IntegrationOrderItemOut,
    IntegrationOrderOut,
    IntegrationReturnCreate,
    IntegrationReturnOut,
)
from ..services.general_diary import create_general_diary_entry
from ..services.integration_events import emit_event, product_snapshot
from ..audit import audit_log
from ..logger import log_error, log_info, log_success

router = APIRouter(
    prefix="/integration",
    tags=["integration"],
    dependencies=[Depends(require_integration_key)],
)


def _apply_stock_delta(db: Session, product: Product, delta: int) -> None:
    """Cộng/trừ tồn kho của Product VÀ Warehouse tương ứng (đồng bộ lại
    trang_thai 'Còn hàng'/'Hết hàng'), rồi emit event stock.changed — dùng
    chung cho cả 3 endpoint dưới đây (tạo đơn: delta âm để trừ kho; hủy đơn/
    trả hàng: delta dương để hoàn kho), tránh chép lại cùng 1 khối logic 3 lần.
    `product` phải đã được `.with_for_update()` khóa từ trước bởi caller."""
    new_qty = max(int(product.so_luong or 0) + delta, 0)
    product.so_luong = new_qty
    product.trang_thai = 'Còn hàng' if new_qty > 0 else 'Hết hàng'

    wh = db.query(Warehouse).filter(Warehouse.product_id == product.id).with_for_update().first()
    if wh:
        wh.so_luong = max(0, (wh.so_luong or 0) + delta)
        wh.trang_thai = 'Còn hàng' if wh.so_luong > 0 else 'Hết hàng'

    emit_event(db, "stock.changed", "product", product.id, product_snapshot(product))


# ══════════════════════════════════════════════════════════════════════════════
# EVENTS (outbox poll) & PRODUCT SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/events", response_model=list[IntegrationEventOut])
def list_events(
    after_id: int = Query(default=0, ge=0),
    limit:    int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Trả về các event outbox có id > after_id, sắp xếp tăng dần. Consumer lưu
    `id` của event cuối cùng đã xử lý làm checkpoint cho lần poll kế tiếp."""
    events = (
        db.query(IntegrationEvent)
        .filter(IntegrationEvent.id > after_id)
        .order_by(IntegrationEvent.id.asc())
        .limit(limit)
        .all()
    )
    return [IntegrationEventOut.model_validate(e).model_dump() for e in events]


@router.get("/products")
def list_products_snapshot(
    after_id: int = Query(default=0, ge=0),
    limit:    int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    """Snapshot toàn bộ sản phẩm, phân trang theo id — dùng cho full-resync (khởi
    động Ecommerce Backend lần đầu, hoặc định kỳ làm lưới an toàn cho poll events)."""
    products = (
        db.query(Product)
        .filter(Product.id > after_id)
        .order_by(Product.id.asc())
        .limit(limit)
        .all()
    )
    return {
        "products": [product_snapshot(p) for p in products],
        "last_id": products[-1].id if products else after_id,
        "has_more": len(products) == limit,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ORDERS (idempotent ingestion)
# ══════════════════════════════════════════════════════════════════════════════

def _find_or_create_account(db: Session, customer: IntegrationCustomer):
    """Khớp khách hàng theo email/phone — KHÔNG theo tên text. Đây chính là bài học
    từ bug thực tế đã ghi trong README của project (services/customers.py trước đây
    so khớp theo `nguoi_mua == customer_name`, khiến 2 khách trùng tên bị gộp nhầm và
    cùng 1 khách ghi tên khác nhau giữa các lần mua bị tách nợ sai). Đơn từ ecommerce
    không có customer_id sẵn như đơn tạo trong POS, nên endpoint này PHẢI tự định
    danh khách hàng — làm đúng ngay từ đầu thay vì lặp lại lỗi cũ."""
    if customer.email:
        acc = db.query(Account).filter(Account.email == customer.email).first()
        if acc:
            return acc
    if customer.phone:
        acc = db.query(Account).filter(Account.so_dt == customer.phone).first()
        if acc:
            return acc
    if not customer.email and not customer.phone:
        # Không có định danh nào — coi như khách vãng lai, không tạo Account mới
        # (tránh tạo hàng loạt account rác không thể phân biệt được với nhau).
        return None
    acc = Account(
        ten_tk=customer.name,
        email=customer.email,
        so_dt=customer.phone,
        dia_chi=customer.address,
        trang_thai=True,
    )
    db.add(acc)
    db.flush()
    return acc


@router.post("/orders", response_model=IntegrationOrderOut)
def create_integration_order(payload: IntegrationOrderCreate, db: Session = Depends(get_db)):
    external_ref = (payload.external_ref or "").strip()
    if not external_ref:
        raise HTTPException(status_code=400, detail="external_ref không được để trống")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Đơn hàng phải có ít nhất 1 sản phẩm")

    # ── Idempotent replay: đã xử lý external_ref này rồi → trả lại kết quả cũ,
    # KHÔNG tạo đơn mới / KHÔNG trừ kho lần 2. Đây là điểm mấu chốt chống đơn trùng
    # khi Ecommerce retry (mất kết nối giữa lúc gọi, worker chạy lại job...).
    existing = db.query(Order).filter(Order.external_ref == external_ref).first()
    if existing:
        log_info("INTEGRATION_ORDER", f"Replay idempotent cho external_ref={external_ref} → order #{existing.id}")
        return IntegrationOrderOut(
            id=existing.id, ma_don_hang=existing.ma_don_hang,
            external_ref=existing.external_ref, trang_thai=existing.trang_thai,
            tong_tien=existing.tong_tien or 0.0, customer_id=existing.customer_id,
            created=False,
        )

    try:
        account = _find_or_create_account(db, payload.customer)

        skus = sorted({item.sku for item in payload.items})
        # Lock theo thứ tự SKU đã sort — tránh deadlock khi 2 đơn tranh chấp cùng lúc
        # 2 sản phẩm theo thứ tự ngược nhau (đúng pattern đã dùng ở invoices.py, KHÔNG
        # theo pattern thiếu lock của orders.py nội bộ — orders.py có race condition
        # đã biết vì chỉ pre-check tồn kho mà không SELECT FOR UPDATE trước khi trừ).
        locked_products = {
            p.ma_sp: p
            for p in db.query(Product).filter(Product.ma_sp.in_(skus)).with_for_update().all()
        }

        missing = [sku for sku in skus if sku not in locked_products]
        if missing:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm: {', '.join(missing)}")

        for item in payload.items:
            product = locked_products[item.sku]
            available = int(product.so_luong or 0)
            if available < item.quantity:
                db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail=f"Sản phẩm '{item.sku}' chỉ còn {available}, không đủ để bán {item.quantity}.",
                )

        computed_total = payload.total_amount if payload.total_amount else sum(
            item.unit_price * item.quantity for item in payload.items
        )
        ma_don_hang = f"EC-{external_ref}"[:50]

        order = Order(
            ma_don_hang=ma_don_hang,
            thong_tin_kh=payload.customer.name,
            customer_id=account.id if account else None,
            sp_banggia=payload.items[0].sku if len(payload.items) == 1 else None,
            ngay_tao=date.today(),
            so_luong=sum(item.quantity for item in payload.items),
            tong_tien=computed_total,
            trang_thai='cho_xu_ly',
            source='ecommerce',
            external_ref=external_ref,
        )
        db.add(order)
        db.flush()

        total_qty_out = 0
        for item in payload.items:
            product = locked_products[item.sku]
            db.add(OrderItem(
                order_id=order.id, product_id=product.id,
                so_luong=item.quantity, don_gia=item.unit_price,
                total_price=item.unit_price * item.quantity,
            ))

            _apply_stock_delta(db, product, -item.quantity)
            total_qty_out += item.quantity

        audit_log(
            db, action="CREATE", entity="IntegrationOrder", entity_id=order.id,
            username="ecommerce-integration",
            after={"ma_don_hang": order.ma_don_hang, "external_ref": external_ref,
                   "tong_tien": computed_total},
            description=f"Đơn từ Ecommerce: {ma_don_hang} (external_ref={external_ref})",
        )

        try:
            create_general_diary_entry(
                db=db, source="Ecommerce", total_amount=computed_total or 0.0,
                quantity_out=total_qty_out, quantity_in=0,
                description=f"Đơn ecommerce {ma_don_hang} - KH: {payload.customer.name}",
            )
        except Exception as diary_error:
            log_error("INTEGRATION_ORDER_DIARY", "Lỗi ghi General Diary", error=diary_error)

        db.commit()
        db.refresh(order)

        log_success("INTEGRATION_ORDER", f"Tạo đơn từ Ecommerce thành công: {ma_don_hang} (id={order.id})")
        return IntegrationOrderOut(
            id=order.id, ma_don_hang=order.ma_don_hang, external_ref=order.external_ref,
            trang_thai=order.trang_thai, tong_tien=order.tong_tien or 0.0,
            customer_id=order.customer_id, created=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_error("INTEGRATION_ORDER", f"Lỗi tạo đơn từ Ecommerce (external_ref={external_ref})", error=e)
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo đơn hàng: {str(e)}")


@router.get("/orders/{order_id}", response_model=IntegrationOrderDetailOut)
def get_integration_order(order_id: int, db: Session = Depends(get_db)):
    """Đọc lại trạng thái đơn hiện tại — dùng cho đối soát công nợ định kỳ giữa
    Ecommerce và POS (xem `reconcile_orders.py` bên Ecommerce Backend), KHÔNG
    dùng trong luồng checkout/push bình thường (những luồng đó chỉ ghi, không
    cần đọc lại). Chỉ trả về đơn có `source='ecommerce'` — đơn tạo tại quầy
    không thuộc phạm vi đối soát 2 hệ thống."""
    order = db.get(Order, order_id)
    if not order or order.source != 'ecommerce':
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng ecommerce")

    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    sku_by_product_id = {
        p.id: p.ma_sp
        for p in db.query(Product).filter(Product.id.in_([i.product_id for i in items])).all()
    }
    return IntegrationOrderDetailOut(
        id=order.id, ma_don_hang=order.ma_don_hang, external_ref=order.external_ref,
        trang_thai=order.trang_thai, tong_tien=order.tong_tien or 0.0, source=order.source,
        items=[
            IntegrationOrderItemOut(
                sku=sku_by_product_id.get(i.product_id, "?"), quantity=i.so_luong,
                unit_price=i.don_gia, total_price=i.total_price, returned_qty=i.returned_qty or 0,
            )
            for i in items
        ],
    )


@router.post("/orders/{order_id}/cancel")
def cancel_integration_order(order_id: int, db: Session = Depends(get_db)):
    """Hoàn kho khi đơn ecommerce bị hủy SAU KHI đã đồng bộ sang POS. Chỉ áp dụng
    cho đơn có source='ecommerce' — hủy đơn tạo tại quầy vẫn qua API orders.py bình
    thường (khác luồng, không phải mối quan tâm của integration API)."""
    order = db.get(Order, order_id)
    if not order or order.source != 'ecommerce':
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng ecommerce")

    if order.trang_thai == 'da_huy':
        return {"success": True, "id": order.id, "already_cancelled": True}

    try:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        product_ids = sorted({item.product_id for item in items})
        locked_products = {
            p.id: p
            for p in db.query(Product).filter(Product.id.in_(product_ids)).with_for_update().all()
        }

        for item in items:
            product = locked_products.get(item.product_id)
            if product:
                _apply_stock_delta(db, product, item.so_luong)

        order.trang_thai = 'da_huy'
        db.commit()

        log_success("INTEGRATION_ORDER_CANCEL", f"Hủy đơn ecommerce #{order.id}, hoàn kho {len(items)} dòng")
        return {"success": True, "id": order.id}
    except Exception as e:
        db.rollback()
        log_error("INTEGRATION_ORDER_CANCEL", f"Lỗi hủy đơn #{order_id}", error=e)
        raise HTTPException(status_code=500, detail=f"Lỗi khi hủy đơn hàng: {str(e)}")


@router.post("/orders/{order_id}/returns", response_model=IntegrationReturnOut)
def return_integration_order_items(order_id: int, payload: IntegrationReturnCreate, db: Session = Depends(get_db)):
    """Trả hàng TỪNG PHẦN cho đơn ecommerce đã giao — khác `.../cancel` (hủy
    TOÀN BỘ đơn trước khi giao). Đơn vẫn giữ nguyên trạng thái, chỉ hoàn kho
    đúng số lượng được trả và ghi nhận `refund_amount` để đối soát công nợ.

    Idempotent qua `return_ref`: gọi lại cùng return_ref (Ecommerce Backend
    retry khi mất kết nối giữa chừng) trả lại đúng kết quả cũ, KHÔNG hoàn kho
    2 lần cho cùng 1 lượt trả hàng."""
    return_ref = (payload.return_ref or "").strip()
    if not return_ref:
        raise HTTPException(status_code=400, detail="return_ref không được để trống")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Yêu cầu trả hàng phải có ít nhất 1 sản phẩm")

    existing = db.query(OrderReturn).filter(OrderReturn.return_ref == return_ref).first()
    if existing:
        log_info("INTEGRATION_RETURN", f"Replay idempotent cho return_ref={return_ref} → return #{existing.id}")
        return IntegrationReturnOut(
            id=existing.id, order_id=existing.order_id, return_ref=existing.return_ref,
            refund_amount=existing.refund_amount or 0.0, created=False,
        )

    order = db.get(Order, order_id)
    if not order or order.source != 'ecommerce':
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng ecommerce")

    try:
        skus = sorted({item.sku for item in payload.items})
        # OrderItem không có cột sku trực tiếp — khớp qua Product.ma_sp (giống
        # cách /integration/orders tạo dòng đơn từ sku ban đầu).
        locked_products = {
            p.ma_sp: p
            for p in db.query(Product).filter(Product.ma_sp.in_(skus)).with_for_update().all()
        }
        missing = [sku for sku in skus if sku not in locked_products]
        if missing:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm: {', '.join(missing)}")

        order_items = {
            oi.product_id: oi
            for oi in db.query(OrderItem).filter(OrderItem.order_id == order.id).with_for_update().all()
        }

        refund_amount = 0.0
        for item in payload.items:
            product = locked_products[item.sku]
            order_item = order_items.get(product.id)
            if not order_item:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm '{item.sku}' không thuộc đơn hàng #{order_id}",
                )
            remaining = order_item.so_luong - (order_item.returned_qty or 0)
            if item.quantity > remaining:
                db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail=f"Sản phẩm '{item.sku}' chỉ còn {remaining} có thể trả (đã mua "
                           f"{order_item.so_luong}, đã trả {order_item.returned_qty or 0}).",
                )

            order_item.returned_qty = (order_item.returned_qty or 0) + item.quantity
            refund_amount += item.quantity * order_item.don_gia

            _apply_stock_delta(db, product, item.quantity)

        order_return = OrderReturn(
            order_id=order.id, return_ref=return_ref,
            items=[{"sku": i.sku, "quantity": i.quantity} for i in payload.items],
            refund_amount=refund_amount,
        )
        db.add(order_return)
        db.flush()

        audit_log(
            db, action="CREATE", entity="OrderReturn", entity_id=order_return.id,
            username="ecommerce-integration",
            after={"order_id": order.id, "return_ref": return_ref, "refund_amount": refund_amount},
            description=f"Trả hàng từ Ecommerce cho đơn #{order.id} (return_ref={return_ref})",
        )

        db.commit()
        db.refresh(order_return)

        log_success("INTEGRATION_RETURN", f"Hoàn kho trả hàng đơn #{order.id}: {len(payload.items)} dòng, refund={refund_amount}")
        return IntegrationReturnOut(
            id=order_return.id, order_id=order.id, return_ref=return_ref,
            refund_amount=refund_amount, created=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_error("INTEGRATION_RETURN", f"Lỗi trả hàng đơn #{order_id}", error=e)
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý trả hàng: {str(e)}")
