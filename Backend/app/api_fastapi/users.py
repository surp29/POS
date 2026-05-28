"""
Users API — áp dụng RBAC:

  GET    /users/       → tất cả user đã đăng nhập (require_staff)
  GET    /users/{id}   → tất cả user đã đăng nhập (require_staff)
  POST   /users/       → chỉ ADMIN (require_admin)
  PUT    /users/{id}   → chỉ ADMIN (require_admin)
  DELETE /users/{id}   → chỉ ADMIN (require_admin)

Thay đổi so với bản cũ: thêm Depends(require_admin / require_staff).
Logic nghiệp vụ giữ nguyên 100%.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from ..database import get_db
from ..models import User
from ..schemas_fastapi import UserOut, UserCreate, UserUpdate
from ..services.general_diary import create_general_diary_entry
from ..logger import log_error
from ..rbac import require_admin, require_staff

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),       # staff trở lên mới xem được
):
    users = db.query(User).all()
    return [UserOut.model_validate(u).model_dump() for u in users]


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")
    return UserOut.model_validate(user).model_dump()


@router.post("/")
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),   # CHỈ ADMIN
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")

    user = User(
        username=payload.username,
        password=generate_password_hash(payload.password),
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        position=payload.position,
        department=payload.department,
        status=payload.status,
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Lỗi tạo nhân viên: {str(e)}')
    return {"success": True, "id": user.id}


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),   # CHỈ ADMIN
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")

    if payload.username is not None:
        if (payload.username != user.username and
                db.query(User).filter(User.username == payload.username).first()):
            raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")
        user.username = payload.username
    if payload.password:        user.password   = generate_password_hash(payload.password)
    if payload.name is not None:       user.name       = payload.name
    if payload.email is not None:      user.email      = payload.email
    if payload.phone is not None:      user.phone      = payload.phone
    if payload.position is not None:   user.position   = payload.position
    if payload.department is not None: user.department = payload.department
    if payload.status is not None:     user.status     = payload.status

    db.flush()
    try:
        create_general_diary_entry(
            db=db, source="User", total_amount=0.0,
            quantity_out=0, quantity_in=0,
            description=f"Sửa nhân viên: {user.username} - {user.name or 'N/A'}"[:255],
            username=current_user.username,
        )
        db.commit()
    except Exception as e:
        log_error("UPDATE_USER_DIARY", "Lỗi ghi General Diary", error=e)
        db.commit()

    return {"success": True}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),   # CHỈ ADMIN
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")
    if user.username == 'admin':
        raise HTTPException(status_code=400, detail="Không thể xóa tài khoản admin")

    user_info = f"{user.username} - {user.name or 'N/A'}"
    db.delete(user)
    db.flush()

    try:
        create_general_diary_entry(
            db=db, source="User", total_amount=0.0,
            quantity_out=0, quantity_in=0,
            description=f"Xóa nhân viên: {user_info}"[:255],
            username=current_user.username,
        )
        db.commit()
    except Exception as e:
        log_error("DELETE_USER_DIARY", "Lỗi ghi General Diary", error=e)
        db.commit()

    return {"success": True}