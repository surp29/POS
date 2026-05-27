from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from typing import List, Optional
from datetime import datetime, date

from ..database import get_db
from ..models import User, DiscountCode
from ..schemas_fastapi import DiscountCodeCreate, DiscountCodeUpdate, DiscountCodeOut
from ..logger import log_info, log_success, log_error, log_warning
from ..services.discounts import is_expired, is_active, can_use_discount, compute_discount_amount
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request

router = APIRouter(tags=["discount-codes"])


@router.get("/", response_model=List[DiscountCodeOut])
def get_discount_codes(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    discount_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lấy danh sách mã giảm giá"""
    log_info("DISCOUNT_CODES", f"Fetching discount codes (skip={skip}, limit={limit})")
    
    query = db.query(DiscountCode)
    
    # Filter by status
    if status:
        query = query.filter(DiscountCode.status == status)
    
    # Filter by discount type
    if discount_type:
        query = query.filter(DiscountCode.discount_type == discount_type)
    
    # Update status based on dates
    now = datetime.now()
    expired_codes = query.filter(DiscountCode.end_date < now).all()
    for code in expired_codes:
        if code.status == 'active':
            code.status = 'expired'
            log_info("DISCOUNT_CODES", f"Auto-expired code: {code.code}")
    
    db.commit()
    
    codes = query.offset(skip).limit(limit).all()
    log_success("DISCOUNT_CODES", f"Retrieved {len(codes)} discount codes")
    
    return [DiscountCodeOut.model_validate(c).model_dump() for c in codes]


@router.get("/{code_id}", response_model=DiscountCodeOut)
def get_discount_code(code_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin chi tiết mã giảm giá"""
    log_info("DISCOUNT_CODES", f"Fetching discount code ID: {code_id}")
    
    code = db.query(DiscountCode).filter(DiscountCode.id == code_id).first()
    if not code:
        log_error("DISCOUNT_CODES", f"Discount code not found: {code_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mã giảm giá không tồn tại"
        )
    
    log_success("DISCOUNT_CODES", f"Retrieved discount code: {code.code}")
    return DiscountCodeOut.model_validate(code).model_dump()


@router.post("/", response_model=DiscountCodeOut)
def create_discount_code(code_data: DiscountCodeCreate, db: Session = Depends(get_db),
    _: User = Depends(require_permission('discount_codes.create'))):
    """Tạo mã giảm giá mới"""
    log_info("DISCOUNT_CODES", f"Creating new discount code: {code_data.code}")
    
    # Check if code already exists
    existing_code = db.query(DiscountCode).filter(DiscountCode.code == code_data.code).first()
    if existing_code:
        log_error("DISCOUNT_CODES", f"Code already exists: {code_data.code}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã giảm giá đã tồn tại"
        )
    
    # Validate discount type and value
    if code_data.discount_type not in ['percentage', 'fixed']:
        log_error("DISCOUNT_CODES", f"Invalid discount type: {code_data.discount_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loại giảm giá không hợp lệ"
        )
    
    if code_data.discount_value <= 0:
        log_error("DISCOUNT_CODES", f"Invalid discount value: {code_data.discount_value}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giá trị giảm giá phải lớn hơn 0"
        )
    
    if code_data.discount_type == 'percentage' and code_data.discount_value > 100:
        log_error("DISCOUNT_CODES", f"Percentage discount too high: {code_data.discount_value}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giảm giá phần trăm không được vượt quá 100%"
        )
    
    # Validate dates
    if code_data.start_date >= code_data.end_date:
        log_error("DISCOUNT_CODES", f"Invalid date range: {code_data.start_date} >= {code_data.end_date}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ngày bắt đầu phải trước ngày kết thúc"
        )
    
    # Set status based on current date
    now = datetime.now()
    if code_data.end_date < now:
        status_value = 'expired'
    elif code_data.start_date > now:
        status_value = 'inactive'
    else:
        status_value = 'active'
    
    # Create new discount code
    db_code = DiscountCode(
        code=code_data.code,
        name=code_data.name,
        description=code_data.description,
        discount_type=code_data.discount_type,
        discount_value=code_data.discount_value,
        start_date=code_data.start_date,
        end_date=code_data.end_date,
        max_uses=code_data.max_uses,
        min_order_value=code_data.min_order_value,
        status=status_value
    )
    
    try:
        db.add(db_code)
        db.commit()
        db.refresh(db_code)
        log_success("DISCOUNT_CODES", f"Created discount code: {db_code.code} (ID: {db_code.id})")
        return db_code
    except Exception as e:
        db.rollback()
        log_error("DISCOUNT_CODES", f"Failed to create discount code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tạo mã giảm giá"
        )


@router.put("/{code_id}", response_model=DiscountCodeOut)
def update_discount_code(
    code_id: int,
    code_data: DiscountCodeUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Cập nhật mã giảm giá"""
    log_info("DISCOUNT_CODES", f"Updating discount code ID: {code_id}")
    
    db_code = db.query(DiscountCode).filter(DiscountCode.id == code_id).first()
    if not db_code:
        log_error("DISCOUNT_CODES", f"Discount code not found: {code_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mã giảm giá không tồn tại"
        )
    
    # Check if new code already exists (if code is being changed)
    if code_data.code and code_data.code != db_code.code:
        existing_code = db.query(DiscountCode).filter(
            DiscountCode.code == code_data.code,
            DiscountCode.id != code_id
        ).first()
        if existing_code:
            log_error("DISCOUNT_CODES", f"Code already exists: {code_data.code}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã giảm giá đã tồn tại"
            )
    
    # Validate discount type and value if provided
    if code_data.discount_type:
        if code_data.discount_type not in ['percentage', 'fixed']:
            log_error("DISCOUNT_CODES", f"Invalid discount type: {code_data.discount_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Loại giảm giá không hợp lệ"
            )
    
    if code_data.discount_value is not None:
        if code_data.discount_value <= 0:
            log_error("DISCOUNT_CODES", f"Invalid discount value: {code_data.discount_value}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Giá trị giảm giá phải lớn hơn 0"
            )
        
        discount_type = code_data.discount_type or db_code.discount_type
        if discount_type == 'percentage' and code_data.discount_value > 100:
            log_error("DISCOUNT_CODES", f"Percentage discount too high: {code_data.discount_value}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Giảm giá phần trăm không được vượt quá 100%"
            )
    
    # Validate dates if provided
    start_date = code_data.start_date or db_code.start_date
    end_date = code_data.end_date or db_code.end_date
    
    if start_date >= end_date:
        log_error("DISCOUNT_CODES", f"Invalid date range: {start_date} >= {end_date}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ngày bắt đầu phải trước ngày kết thúc"
        )
    
    # Update fields
    update_data = code_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_code, field, value)
    
    # Update status based on current date
    now = datetime.now()
    if end_date < now:
        db_code.status = 'expired'
    elif start_date > now:
        db_code.status = 'inactive'
    else:
        db_code.status = 'active'
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    try:
        db.flush()  # Flush để đảm bảo update được thực hiện
        
        # Ghi vào general_diary
        try:
            description_text = f"Sửa mã giảm giá: {db_code.code}"
            create_general_diary_entry(
                db=db,
                source="DiscountCode",
                total_amount=0.0,
                quantity_out=0,
                quantity_in=0,
                description=description_text[:255],
                username=username
            )
            db.commit()
        except Exception as diary_error:
            log_error("UPDATE_DISCOUNT_CODE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
            db.commit()  # Vẫn commit việc update mã giảm giá
        
        db.refresh(db_code)
        log_success("DISCOUNT_CODES", f"Updated discount code: {db_code.code} (ID: {db_code.id})")
        return db_code
    except Exception as e:
        db.rollback()
        log_error("DISCOUNT_CODES", f"Failed to update discount code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể cập nhật mã giảm giá"
        )


@router.delete("/{code_id}")
def delete_discount_code(code_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('discount_codes.delete'))):
    """Xóa mã giảm giá"""
    log_info("DISCOUNT_CODES", f"Deleting discount code ID: {code_id}")
    
    db_code = db.query(DiscountCode).filter(DiscountCode.id == code_id).first()
    if not db_code:
        log_error("DISCOUNT_CODES", f"Discount code not found: {code_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mã giảm giá không tồn tại"
        )
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    # Lưu thông tin mã giảm giá trước khi xóa
    code_info = db_code.code
    
    try:
        db.delete(db_code)
        db.flush()  # Flush để đảm bảo xóa được thực hiện
        
        # Ghi vào general_diary
        try:
            description_text = f"Xóa mã giảm giá: {code_info}"
            create_general_diary_entry(
                db=db,
                source="DiscountCode",
                total_amount=0.0,
                quantity_out=0,
                quantity_in=0,
                description=description_text[:255],
                username=username
            )
            db.commit()
        except Exception as diary_error:
            log_error("DELETE_DISCOUNT_CODE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
            db.commit()  # Vẫn commit việc xóa mã giảm giá
        
        log_success("DISCOUNT_CODES", f"Deleted discount code: {db_code.code} (ID: {code_id})")
        return {"message": "Xóa mã giảm giá thành công"}
    except Exception as e:
        db.rollback()
        log_error("DISCOUNT_CODES", f"Failed to delete discount code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể xóa mã giảm giá"
        )


@router.post("/{code_id}/use")
def use_discount_code(
    code_id: int,
    order_value: float,
    db: Session = Depends(get_db)
):
    """Sử dụng mã giảm giá (endpoint cho FE)."""
    log_info("DISCOUNT_CODES", f"Using discount code ID: {code_id} for order value: {order_value}")
    db_code = db.query(DiscountCode).filter(DiscountCode.id == code_id).first()
    if not db_code:
        log_error("DISCOUNT_CODES", f"Discount code not found: {code_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mã giảm giá không tồn tại")
    err = can_use_discount(db_code, order_value)
    if err:
        log_error("DISCOUNT_CODES", f"Cannot use code: {err}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    discount_amount = compute_discount_amount(db_code, order_value)
    db_code.used_count += 1
    db_code.total_savings += discount_amount
    try:
        db.commit()
        log_success("DISCOUNT_CODES", f"Used discount code: {db_code.code}, discount: {discount_amount}")
        return {
            "discount_amount": discount_amount,
            "final_amount": order_value - discount_amount,
            "code": db_code.code,
            "name": db_code.name
        }
    except Exception as e:
        db.rollback()
        log_error("DISCOUNT_CODES", f"Failed to use discount code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể sử dụng mã giảm giá"
        )