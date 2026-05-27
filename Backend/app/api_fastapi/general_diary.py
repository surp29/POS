from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from ..database import get_db
from ..models import User, GeneralDiary
from .. import schemas_fastapi

router = APIRouter(prefix="/general-diary", tags=["general-diary"])

@router.get("/")
def get_general_diary_entries(db: Session = Depends(get_db),
    _: User = Depends(require_permission('general_diary.view'))):
    """Lấy danh sách tất cả các entry trong General Diary"""
    try:
        entries = db.query(GeneralDiary).order_by(GeneralDiary.ngay_nhap.desc(), GeneralDiary.id.desc()).all()
        entries_data = [schemas_fastapi.GeneralDiaryOut.model_validate(e).model_dump() for e in entries]
        return {"success": True, "data": entries_data}
    except Exception as e:
        return {"success": False, "message": f"Lỗi khi lấy danh sách: {str(e)}", "data": []}

@router.get("/{entry_id}", response_model=schemas_fastapi.GeneralDiaryOut)
def get_general_diary_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(GeneralDiary).filter(GeneralDiary.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return schemas_fastapi.GeneralDiaryOut.model_validate(entry).model_dump()

@router.post("/")
def create_general_diary_entry(gd: schemas_fastapi.GeneralDiaryCreate, db: Session = Depends(get_db),
    _: User = Depends(require_permission('general_diary.create'))):
    try:
        from datetime import date
        
        # Validate required fields
        if not gd.ngay_nhap:
            gd.ngay_nhap = date.today()
        if not gd.so_hieu or not gd.so_hieu.strip():
            raise HTTPException(status_code=400, detail="Mã kí hiệu không được để trống")
        
        entry = GeneralDiary(
            ngay_nhap=gd.ngay_nhap,
            so_hieu=gd.so_hieu.strip(),
            dien_giai=gd.dien_giai or "",
            so_luong_nhap=gd.so_luong_nhap or 0,
            so_luong_xuat=gd.so_luong_xuat or 0,
            so_tien=gd.so_tien or 0.0
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        entry_dict = schemas_fastapi.GeneralDiaryOut.model_validate(entry).model_dump()
        return {"success": True, "data": entry_dict}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        error_trace = traceback.format_exc()
        from ..logger import log_error
        log_error("CREATE_GENERAL_DIARY", f"Lỗi khi tạo entry: {str(e)}", error=e)
        log_error("CREATE_GENERAL_DIARY", f"Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo entry: {str(e)}")

@router.put("/{entry_id}")
def update_general_diary_entry(entry_id: int, gd: schemas_fastapi.GeneralDiaryCreate, db: Session = Depends(get_db),
    _: User = Depends(require_permission('general_diary.edit'))):
    try:
        entry = db.query(GeneralDiary).filter(GeneralDiary.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        for name, value in gd.model_dump().items():
            setattr(entry, name, value)
        db.commit()
        db.refresh(entry)
        entry_dict = schemas_fastapi.GeneralDiaryOut.model_validate(entry).model_dump()
        return {"success": True, "data": entry_dict}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật entry: {str(e)}")

@router.delete("/{entry_id}")
def delete_general_diary_entry(entry_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_permission('general_diary.delete'))):
    entry = db.query(GeneralDiary).filter(GeneralDiary.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
    return {"success": True}