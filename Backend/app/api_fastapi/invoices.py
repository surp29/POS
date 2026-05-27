from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from ..database import get_db
from ..models import User, Invoice, InvoiceItem, Product, Warehouse
from ..schemas_fastapi import InvoiceOut, InvoiceCreate, InvoiceUpdate, InvoiceItemOut
from ..logger import log_info, log_success, log_error, log_warning
from ..services.invoices import update_debt_for_customer
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request
from datetime import datetime


router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db),
    _: User = Depends(require_permission('invoices.view'))):
    invoices = db.query(Invoice).all()
    return [InvoiceOut.model_validate(inv).model_dump() for inv in invoices]


@router.post("/")
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db),
    _: User = Depends(require_permission('invoices.create'))):
    """Tạo hóa đơn mới"""
    log_info("CREATE_INVOICE", f"Tạo hóa đơn mới: {payload.so_hd} - Khách hàng: {payload.nguoi_mua} - Tổng tiền: {payload.tong_tien:,.0f} VND")
    
    try:
        # Tạo hóa đơn mới
        inv = Invoice(
            so_hd=payload.so_hd,
            ngay_hd=payload.ngay_hd,
            nguoi_mua=payload.nguoi_mua,
            tong_tien=payload.tong_tien,
            trang_thai=payload.trang_thai,
            hinh_thuc_tt=payload.hinh_thuc_tt,
        )
        db.add(inv)
        db.flush()  # Flush để lấy ID
        
        # Xử lý các items và cập nhật số lượng sản phẩm
        if payload.items:
            for item_data in payload.items:
                # Tạo invoice item
                invoice_item = InvoiceItem(
                    invoice_id=inv.id,
                    product_id=item_data.product_id,
                    product_code=item_data.product_code,
                    product_name=item_data.product_name,
                    so_luong=item_data.so_luong,
                    don_gia=item_data.don_gia,
                    total_price=item_data.total_price
                )
                db.add(invoice_item)
                
                # Cập nhật số lượng sản phẩm trong bảng products
                product = db.query(Product).filter(Product.id == item_data.product_id).first()
                if product:
                    current_qty = product.so_luong or 0
                    new_qty = max(0, current_qty - item_data.so_luong)
                    product.so_luong = new_qty
                    product.trang_thai = 'Còn hàng' if new_qty > 0 else 'Hết hàng'
                    log_info("UPDATE_STOCK", f"Đã cập nhật số lượng sản phẩm {item_data.product_code}: {current_qty} -> {new_qty}")
                
                # Cập nhật số lượng trong warehouse (nếu có)
                warehouse = db.query(Warehouse).filter(Warehouse.ma_sp == item_data.product_code).first()
                if warehouse:
                    current_wh_qty = warehouse.so_luong or 0
                    new_wh_qty = max(0, current_wh_qty - item_data.so_luong)
                    warehouse.so_luong = new_wh_qty
                    warehouse.trang_thai = 'Còn hàng' if new_wh_qty > 0 else 'Hết hàng'
                    log_info("UPDATE_WAREHOUSE_STOCK", f"Đã cập nhật số lượng kho {warehouse.ma_kho} - SP {item_data.product_code}: {current_wh_qty} -> {new_wh_qty}")
        
        db.commit()
        db.refresh(inv)
        
        # Cập nhật bảng công nợ
        update_debt_for_customer(payload.nguoi_mua, db)
        
        # Tính tổng số lượng xuất từ các items
        total_quantity_out = sum(item.so_luong for item in payload.items) if payload.items else 0
        
        # Phân biệt nguồn: nếu có items thì từ POS, không có items thì từ Invoice form
        source = "Pos" if payload.items and len(payload.items) > 0 else "Invoice"
        
        # Tự động ghi vào General Diary
        try:
            description = f"{'Bán hàng' if source == 'Pos' else 'Hóa đơn'} {payload.so_hd} - Khách hàng: {payload.nguoi_mua} - Xuất {total_quantity_out} sản phẩm"
            create_general_diary_entry(
                db=db,
                source=source,
                total_amount=payload.tong_tien or 0.0,
                quantity_out=total_quantity_out,
                quantity_in=0,
                description=description
            )
            db.commit()
        except Exception as diary_error:
            # Log lỗi nhưng không làm gián đoạn việc tạo invoice
            log_error("CREATE_INVOICE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
            # Không rollback vì invoice đã được tạo thành công
        
        log_success("CREATE_INVOICE", f"Tạo hóa đơn thành công: {payload.so_hd} (ID: {inv.id})")
        return {"success": True, "id": inv.id}
    except Exception as e:
        log_error("CREATE_INVOICE", f"Lỗi khi tạo hóa đơn {payload.so_hd}", error=e)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi tạo hóa đơn: {str(e)}")


@router.put("/{invoice_id:int}")
def update_invoice(invoice_id: int, payload: InvoiceUpdate, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('invoices.edit'))):
    try:
        inv = db.query(Invoice).get(invoice_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
        
        # Lấy username từ token
        username = get_username_from_request(request)
        
        # Lưu tên khách hàng cũ để cập nhật công nợ
        old_customer_name = inv.nguoi_mua
        
        # Cập nhật hóa đơn
        if payload.so_hd is not None: setattr(inv, 'so_hd', payload.so_hd)
        if payload.ngay_hd is not None: setattr(inv, 'ngay_hd', payload.ngay_hd)
        if payload.nguoi_mua is not None: setattr(inv, 'nguoi_mua', payload.nguoi_mua)
        if payload.tong_tien is not None: setattr(inv, 'tong_tien', payload.tong_tien)
        if payload.trang_thai is not None: setattr(inv, 'trang_thai', payload.trang_thai)
        if payload.hinh_thuc_tt is not None: setattr(inv, 'hinh_thuc_tt', payload.hinh_thuc_tt)
        
        db.flush()  # Flush để đảm bảo update được thực hiện
        
        # Ghi vào general_diary
        try:
            description_text = f"Sửa hóa đơn: {inv.so_hd} - Khách hàng: {inv.nguoi_mua}"
            create_general_diary_entry(
                db=db,
                source="Invoice",
                total_amount=float(inv.tong_tien or 0),
                quantity_out=0,
                quantity_in=0,
                description=description_text[:255],
                username=username
            )
            db.commit()
        except Exception as diary_error:
            log_error("UPDATE_INVOICE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
            db.commit()  # Vẫn commit việc update hóa đơn
        
        # Cập nhật công nợ cho khách hàng cũ (nếu có thay đổi)
        if old_customer_name:
            update_debt_for_customer(old_customer_name, db)
        
        # Cập nhật công nợ cho khách hàng mới
        new_customer_name = payload.nguoi_mua if payload.nguoi_mua is not None else old_customer_name
        if new_customer_name and new_customer_name != old_customer_name:
            update_debt_for_customer(new_customer_name, db)
        
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật hóa đơn: {str(e)}")


@router.get("/{invoice_id:int}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.query(Invoice).get(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
    return InvoiceOut.model_validate(inv).model_dump()


@router.get("/{invoice_id:int}/details")
def get_invoice_details(invoice_id: int, db: Session = Depends(get_db)):
    """Lấy chi tiết hóa đơn bao gồm các sản phẩm"""
    try:
        inv = db.query(Invoice).get(invoice_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
        
        # Lấy tất cả items của invoice
        items = []
        try:
            # Kiểm tra xem bảng có tồn tại không bằng cách query
            items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()
        except Exception as table_error:
            # Nếu bảng chưa tồn tại hoặc có lỗi, log và trả về empty list
            log_warning("GET_INVOICE_DETAILS", f"Có thể bảng invoice_items chưa tồn tại: {str(table_error)}")
            items = []
        
        log_info("GET_INVOICE_DETAILS", f"Lấy chi tiết hóa đơn ID: {invoice_id}, số items: {len(items)}")
        
        # Format date để JSON serializable
        ngay_hd = None
        if inv.ngay_hd:
            if isinstance(inv.ngay_hd, str):
                ngay_hd = inv.ngay_hd
            else:
                ngay_hd = inv.ngay_hd.isoformat()
        
        return {
            "invoice": {
                "id": inv.id,
                "so_hd": inv.so_hd,
                "ngay_hd": ngay_hd,
                "nguoi_mua": inv.nguoi_mua,
                "tong_tien": float(inv.tong_tien) if inv.tong_tien else 0.0,
                "trang_thai": inv.trang_thai
            },
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_code": item.product_code,
                    "product_name": item.product_name,
                    "so_luong": item.so_luong,
                    "don_gia": float(item.don_gia) if item.don_gia else 0.0,
                    "total_price": float(item.total_price) if item.total_price else 0.0
                }
                for item in items
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_error("GET_INVOICE_DETAILS", f"Lỗi khi lấy chi tiết hóa đơn {invoice_id}", error=e)
        log_error("GET_INVOICE_DETAILS", f"Chi tiết lỗi: {error_details}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy chi tiết hóa đơn: {str(e)}")


@router.delete("/{invoice_id:int}")
def delete_invoice(invoice_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('invoices.delete'))):
    try:
        inv = db.query(Invoice).get(invoice_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn")
        
        # Lấy username từ token
        username = get_username_from_request(request)
        
        # Lưu thông tin hóa đơn trước khi xóa
        invoice_info = f"{inv.so_hd} - Khách hàng: {inv.nguoi_mua}"
        customer_name = inv.nguoi_mua
        
        # Xóa hóa đơn
        db.delete(inv)
        db.flush()  # Flush để đảm bảo xóa được thực hiện
        
        # Ghi vào general_diary
        try:
            description_text = f"Xóa hóa đơn: {invoice_info}"
            create_general_diary_entry(
                db=db,
                source="Invoice",
                total_amount=float(inv.tong_tien or 0),
                quantity_out=0,
                quantity_in=0,
                description=description_text[:255],
                username=username
            )
            db.commit()
        except Exception as diary_error:
            log_error("DELETE_INVOICE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
            db.commit()  # Vẫn commit việc xóa hóa đơn
        
        # Cập nhật công nợ cho khách hàng
        if customer_name:
            update_debt_for_customer(customer_name, db)
        
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi xóa hóa đơn: {str(e)}")


@router.get("/next-number")
def next_invoice_number(db: Session = Depends(get_db)):
    """Tạo số thứ tự hóa đơn tiếp theo theo format: HĐ-ddmmyy-XXX (001-999)"""
    from datetime import date
    
    today = date.today()
    date_str = today.strftime("%d%m%y")  # Format: ddmmyy (ví dụ: 061125)
    
    # Tìm tất cả hóa đơn có mã bắt đầu bằng HĐ-{date_str}-
    pattern = f"HĐ-{date_str}-"
    
    # Lấy tất cả hóa đơn có mã chứa pattern này
    invoices_today = db.query(Invoice).filter(Invoice.so_hd.like(f"{pattern}%")).all()
    
    if not invoices_today:
        # Nếu chưa có hóa đơn nào trong ngày, bắt đầu từ 001
        return {
            "next_number": 1,
            "date_str": date_str,
            "full_invoice_number": f"HĐ-{date_str}-001"
        }
    
    # Tìm số thứ tự cao nhất trong ngày
    max_number = 0
    for inv in invoices_today:
        so_hd_value = getattr(inv, "so_hd", None)
        if so_hd_value and so_hd_value.startswith(pattern):
            try:
                # Extract số thứ tự từ cuối mã (sau dấu -)
                number_part = so_hd_value.replace(pattern, "")
                if number_part.isdigit():
                    num = int(number_part)
                    if num > max_number:
                        max_number = num
            except (ValueError, AttributeError):
                continue
    
    # Tăng lên 1, giới hạn tối đa 999
    next_number = min(max_number + 1, 999)
    
    # Format số thứ tự với 3 chữ số (001, 002, ..., 999)
    next_number_str = f"{next_number:03d}"
    
    return {
        "next_number": next_number,
        "date_str": date_str,
        "full_invoice_number": f"HĐ-{date_str}-{next_number_str}"
    }


@router.post("/search")
def search_invoices(criteria: dict, db: Session = Depends(get_db)):
    q = db.query(Invoice)
    from_date = criteria.get("fromDate")
    to_date = criteria.get("toDate")
    invoice_number = criteria.get("invoiceNumber")
    customer_info = criteria.get("customerInfo")

    if from_date and to_date:
        q = q.filter(Invoice.ngay_hd.between(from_date, to_date))
    if invoice_number:
        like = f"%{invoice_number}%"
        q = q.filter(Invoice.so_hd.ilike(like))
    if customer_info:
        like = f"%{customer_info}%"
        q = q.filter(Invoice.nguoi_mua.ilike(like))

    rows = q.all()
    return {"success": True, "data": rows}