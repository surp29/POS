# Backend/app/services/discounts.py
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import DiscountCode

def is_expired(code: DiscountCode) -> bool:
    return code.end_date and code.end_date < datetime.now()

def is_active(code: DiscountCode) -> bool:
    now = datetime.now()
    return (not is_expired(code)) and (code.start_date <= now)

def can_use_discount(code: DiscountCode, order_value: float) -> str | None:
    now = datetime.now()
    if is_expired(code):
        return "Mã giảm giá đã hết hạn"
    if code.status != 'active':
        return "Mã giảm giá không hoạt động"
    if code.start_date > now:
        return "Mã giảm giá chưa có hiệu lực"
    if code.max_uses and code.used_count >= code.max_uses:
        return "Mã giảm giá đã hết lượt sử dụng"
    if order_value < code.min_order_value:
        return f"Giá trị đơn hàng tối thiểu là {code.min_order_value:,.0f} VNĐ"
    return None

def compute_discount_amount(code: DiscountCode, order_value: float) -> float:
    if code.discount_type == 'percentage':
        return order_value * (code.discount_value / 100)
    return min(float(code.discount_value), float(order_value))
