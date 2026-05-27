from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Account
from ..schemas_fastapi import AccountOut, AccountCreate, AccountUpdate
from ..logger import log_info, log_success, log_error, log_warning
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    rows = db.query(Account).all()
    return [AccountOut.model_validate(row) for row in rows]


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    row = db.query(Account).get(account_id)
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách hàng")
    return AccountOut.model_validate(row)


@router.post("/")
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    """Tạo tài khoản khách hàng mới"""
    log_info("CREATE_ACCOUNT", f"Tạo tài khoản mới: {payload.ten_tk} - Email: {payload.email}")
    
    try:
        acc = Account(
            ten_tk=payload.ten_tk,
            ma_khach_hang=payload.ma_khach_hang,
            ngay_sinh=payload.ngay_sinh,
            email=payload.email,
            so_dt=payload.so_dt,
            dia_chi=payload.dia_chi,
            trang_thai=payload.trang_thai,
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)
        
        log_success("CREATE_ACCOUNT", f"Tạo tài khoản thành công: {payload.ten_tk} (ID: {acc.id})")
        # Return AccountOut format để frontend có thể sử dụng trực tiếp
        return AccountOut.model_validate(acc)
    except Exception as e:
        log_error("CREATE_ACCOUNT", f"Lỗi khi tạo tài khoản {payload.ten_tk}", error=e)
        raise HTTPException(status_code=500, detail=f"Lỗi tạo tài khoản: {str(e)}")


@router.put("/{account_id}")
def update_account(account_id: int, payload: AccountUpdate, request: Request, db: Session = Depends(get_db)):
    acc = db.query(Account).get(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách hàng")
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    if payload.ten_tk is not None:
        acc.ten_tk = payload.ten_tk
    if payload.ma_khach_hang is not None:
        acc.ma_khach_hang = payload.ma_khach_hang
    if payload.ngay_sinh is not None:
        acc.ngay_sinh = payload.ngay_sinh
    if payload.email is not None:
        acc.email = payload.email
    if payload.so_dt is not None:
        acc.so_dt = payload.so_dt
    if payload.dia_chi is not None:
        acc.dia_chi = payload.dia_chi
    if payload.trang_thai is not None:
        acc.trang_thai = payload.trang_thai
    
    db.flush()  # Flush để đảm bảo update được thực hiện
    
    # Ghi vào general_diary
    try:
        description_text = f"Sửa khách hàng: {acc.ten_tk} - Mã KH: {acc.ma_khach_hang or 'N/A'}"
        create_general_diary_entry(
            db=db,
            source="Customer",
            total_amount=0.0,
            quantity_out=0,
            quantity_in=0,
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        log_error("UPDATE_ACCOUNT_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()  # Vẫn commit việc update khách hàng
    
    return {"success": True}


@router.delete("/{account_id}")
def delete_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    acc = db.query(Account).get(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách hàng")
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    # Lưu thông tin khách hàng trước khi xóa
    customer_info = f"{acc.ten_tk} - Mã KH: {acc.ma_khach_hang or 'N/A'}"
    
    db.delete(acc)
    db.flush()  # Flush để đảm bảo xóa được thực hiện
    
    # Ghi vào general_diary
    try:
        description_text = f"Xóa khách hàng: {customer_info}"
        create_general_diary_entry(
            db=db,
            source="Customer",
            total_amount=0.0,
            quantity_out=0,
            quantity_in=0,
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        log_error("DELETE_ACCOUNT_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()  # Vẫn commit việc xóa khách hàng
    
    return {"success": True}


