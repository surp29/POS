# Backend/app/services/orders.py
from sqlalchemy.orm import Session
from ..models import Order, Product, Account
from fastapi import HTTPException

def create_order_service(payload, db: Session):
    is_product = False
    is_action = False
    product = None
    price_item = None
    if payload.sp_banggia:
        product = db.query(Product).filter(Product.ma_sp == payload.sp_banggia).first()
        if product:
            is_product = True
        else:
            is_action = True
    # Ưu tiên sử dụng tong_tien từ payload nếu có và > 0
    computed_total = 0
    if payload.tong_tien and payload.tong_tien > 0:
        computed_total = float(payload.tong_tien)
    elif payload.so_luong:
        if is_product and product:
            # Try gia_ban first, then gia_chung
            unit_price = float(getattr(product, 'gia_ban', 0) or 0)
            if unit_price == 0:
                unit_price = float(getattr(product, 'gia_chung', 0) or 0)
            computed_total = unit_price * int(payload.so_luong or 0)
        elif is_action:
            # Với hành động, nếu có tong_tien thì dùng, nếu không thì tính từ so_luong
            if payload.tong_tien and payload.tong_tien > 0:
                computed_total = float(payload.tong_tien)
            else:
                # Fallback: tính từ giá mặc định nếu có
                unit_price = float(payload.tong_tien or 0) / max(int(payload.so_luong or 1), 1)
                computed_total = unit_price * int(payload.so_luong or 0)
    if is_product and product and payload.so_luong:
        current_qty = int(getattr(product, 'so_luong', 0) or 0)
        if current_qty < payload.so_luong:
            raise HTTPException(status_code=400, detail=f"Số lượng sản phẩm {payload.sp_banggia} không đủ! Hiện có: {current_qty}, yêu cầu: {payload.so_luong}")
    return {
        'is_product': is_product,
        'is_action': is_action,
        'product': product,
        'price_item': price_item,
        'computed_total': computed_total,
    }
