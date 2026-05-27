"""
Service để tự động ghi lại các thao tác vào General Diary
"""
from datetime import date
from sqlalchemy.orm import Session
from ..models import GeneralDiary
from ..logger import log_info, log_success, log_error


def create_general_diary_entry(
    db: Session,
    source: str,  # Nguồn thao tác: "Pos", "Invoice", "Order", "Prices", "Warehouse", "Product", etc.
    total_amount: float = 0.0,
    quantity_out: int = 0,  # Số lượng xuất
    quantity_in: int = 0,  # Số lượng nhập
    description: str = None,  # Ghi chú mô tả chi tiết
    username: str = None  # Tên tài khoản thực hiện hành động
):
    """
    Tự động tạo entry trong General Diary
    
    Args:
        db: Database session
        source: Nguồn thao tác (Pos, Invoice, Order, Prices, Warehouse, Product, Customer, Discount, etc.)
        total_amount: Tổng tiền (từ hóa đơn hoặc đơn hàng)
        quantity_out: Số lượng xuất (khi bán hàng)
        quantity_in: Số lượng nhập (khi nhập hàng)
        description: Ghi chú chi tiết (tùy chọn)
    """
    try:
        today = date.today()
        
        # Tạo mã kí hiệu dựa trên source (giới hạn 50 ký tự)
        so_hieu = str(source)[:50] if source else "Unknown"  # Ví dụ: "Pos", "Invoice", "Order", etc.
        
        # Tạo ghi chú mặc định nếu không có
        if not description:
            if quantity_out > 0:
                description = f"Xuất {quantity_out} sản phẩm từ {source}"
            elif quantity_in > 0:
                description = f"Nhập {quantity_in} sản phẩm vào {source}"
            elif total_amount > 0:
                description = f"Giao dịch từ {source} - Tổng tiền: {total_amount:,.0f} VNĐ"
            else:
                description = f"Thao tác từ {source}"
        
        # Thêm thông tin user vào description nếu có
        if username:
            user_info = f" - Thực hiện bởi: {username}"
            # Đảm bảo không vượt quá 255 ký tự
            if len(description) + len(user_info) <= 255:
                description = description + user_info
            else:
                # Cắt description và thêm user info
                max_desc_len = 255 - len(user_info)
                description = description[:max_desc_len] + user_info
        
        # Giới hạn độ dài description (255 ký tự)
        if description and len(description) > 255:
            description = description[:252] + "..."
        
        # Tạo entry
        entry = GeneralDiary(
            ngay_nhap=today,
            so_hieu=so_hieu,
            dien_giai=description or "",
            so_luong_nhap=quantity_in or 0,
            so_luong_xuat=quantity_out or 0,
            so_tien=total_amount or 0.0
        )
        
        db.add(entry)
        db.flush()  # Flush để lấy ID, commit sẽ được gọi ở ngoài
        
        log_success("CREATE_GENERAL_DIARY", f"Đã ghi lại thao tác: {source} - {description}")
        return entry
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        log_error("CREATE_GENERAL_DIARY", f"Lỗi khi ghi lại thao tác từ {source}: {str(e)}", error=e)
        log_error("CREATE_GENERAL_DIARY", f"Traceback: {error_trace}")
        # Raise exception để caller có thể xử lý
        raise

