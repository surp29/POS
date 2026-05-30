from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from ..database import get_db
from ..models import User, Price
from ..schemas_fastapi import PriceCreate, PriceUpdate, PriceOut
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request

router = APIRouter(prefix="/prices", tags=["prices"])

@router.get("/", response_model=list[PriceOut])
def list_prices(db: Session = Depends(get_db)):
    prices = db.query(Price).all()
    return [PriceOut.model_validate(p).model_dump() for p in prices]

@router.post("/")
def create_price(payload: PriceCreate, db: Session = Depends(get_db),
    _: User = Depends(require_permission('prices.create'))):
    price = Price(
        ma_sp=payload.ma_sp,
        ten_sp=payload.ten_sp,
        gia_chung=payload.gia_chung,
        ghi_chu=payload.ghi_chu,
    )
    try:
        db.add(price)
        db.commit()
        db.refresh(price)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Lỗi tạo bảng giá: {str(e)}')
    
    # Tự động ghi vào General Diary
    try:
        ma_sp_display = payload.ma_sp if payload.ma_sp else "N/A"
        ten_sp_display = payload.ten_sp if payload.ten_sp else "N/A"
        gia_chung_value = payload.gia_chung or 0.0
        description = f"Thêm bảng giá mới: {ma_sp_display} - {ten_sp_display} - Giá: {gia_chung_value:,.0f} VNĐ"
        create_general_diary_entry(
            db=db,
            source="Prices",
            total_amount=gia_chung_value,
            quantity_out=0,
            quantity_in=0,
            description=description
        )
        db.commit()
    except Exception as diary_error:
        # Log lỗi nhưng không làm gián đoạn việc tạo price
        from ..logger import log_error
        log_error("CREATE_PRICE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        # Không rollback vì price đã được tạo thành công
    
    return {"success": True, "id": price.id}

@router.put("/{price_id}")
def update_price(price_id: int, payload: PriceUpdate, request: Request, db: Session = Depends(get_db)):
    price = db.get(Price, price_id)
    if not price:
        raise HTTPException(status_code=404, detail="Không tìm thấy bảng giá")
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    if payload.ma_sp is not None:
        price.ma_sp = payload.ma_sp
    if payload.ten_sp is not None:
        price.ten_sp = payload.ten_sp
    if payload.gia_chung is not None:
        price.gia_chung = payload.gia_chung
    if payload.ghi_chu is not None:
        price.ghi_chu = payload.ghi_chu
    
    db.flush()  # Flush để đảm bảo update được thực hiện
    
    # Ghi vào general_diary
    try:
        description_text = f"Sửa bảng giá: {price.ma_sp} - {price.ten_sp} - Giá: {(price.gia_chung or 0):,.0f} VNĐ"
        create_general_diary_entry(
            db=db,
            source="Prices",
            total_amount=float(price.gia_chung or 0),
            quantity_out=0,
            quantity_in=0,
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        from ..logger import log_error
        log_error("UPDATE_PRICE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()  # Vẫn commit việc update bảng giá
    
    return {"success": True}

@router.delete("/{price_id}")
def delete_price(price_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('prices.delete'))):
    price = db.get(Price, price_id)
    if not price:
        raise HTTPException(status_code=404, detail="Không tìm thấy bảng giá")
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    # Lưu thông tin bảng giá trước khi xóa
    price_info = f"{price.ma_sp} - {price.ten_sp}"
    
    db.delete(price)
    db.flush()  # Flush để đảm bảo xóa được thực hiện
    
    # Ghi vào general_diary
    try:
        description_text = f"Xóa bảng giá: {price_info}"
        create_general_diary_entry(
            db=db,
            source="Prices",
            total_amount=float(price.gia_chung or 0),
            quantity_out=0,
            quantity_in=0,
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        from ..logger import log_error
        log_error("DELETE_PRICE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()  # Vẫn commit việc xóa bảng giá
    
    return {"success": True}