"""
Integration Events — Transactional Outbox cho đồng bộ với Ecommerce Backend.

`emit_event()` chỉ `db.add()` + `db.flush()` — KHÔNG tự commit. Bên gọi phải nằm
trong transaction đang mở của thao tác nghiệp vụ (tạo/sửa sản phẩm, trừ kho...) và
commit cùng lúc. Nhờ vậy nếu transaction rollback (vd hết hàng giữa chừng), event
cũng không bao giờ được ghi — tránh tình trạng Ecommerce nhận event cho 1 thay đổi
thực ra chưa từng xảy ra.
"""
from typing import Optional
from sqlalchemy.orm import Session

from ..models import IntegrationEvent
from ..logger import log_warning


def emit_event(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id,
    payload: dict,
) -> Optional[IntegrationEvent]:
    """Ghi 1 event vào outbox. Lỗi ở đây KHÔNG được làm hỏng thao tác nghiệp vụ
    chính — chỉ log warning và trả None (giống triết lý của general_diary /
    audit_log trong project: nghiệp vụ chính luôn ưu tiên hơn tác vụ phụ trợ)."""
    try:
        event = IntegrationEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            payload=payload,
        )
        db.add(event)
        db.flush()
        return event
    except Exception as e:
        log_warning(
            "INTEGRATION_EVENT",
            f"Không thể ghi integration event ({event_type} {entity_type}={entity_id}): {e}",
        )
        return None


def product_snapshot(product) -> dict:
    """Payload chuẩn hoá cho 1 sản phẩm — dùng lại y hệt ở cả event lẫn API
    snapshot /integration/products, tránh 2 nơi định nghĩa khác nhau rồi lệch field."""
    return {
        "id":         product.id,
        "sku":        product.ma_sp,
        "name":       product.ten_sp,
        "group":      product.nhom_sp,
        "stock_qty":  int(product.so_luong or 0),
        "price":      float(product.gia_ban or 0.0),
        "list_price": float(product.gia_chung or 0.0),
        "unit":       product.don_vi,
        "status":     product.trang_thai,
        "image_url":  product.image_url,
        "description": product.mo_ta,
    }
