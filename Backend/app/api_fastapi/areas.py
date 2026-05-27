from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from sqlalchemy import func
from typing import List, Optional
from ..database import get_db
from ..models import User, Area, Shop
from ..schemas_fastapi import AreaCreate, AreaUpdate, AreaOut
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request

router = APIRouter(prefix="/areas", tags=["areas"])

@router.get("/", response_model=List[AreaOut])
def read_areas(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Area)
    if search:
        query = query.filter(
            Area.name.ilike(f"%{search}%") |
            Area.code.ilike(f"%{search}%") |
            Area.province.ilike(f"%{search}%") |
            Area.district.ilike(f"%{search}%")
        )
    if type_filter:
        query = query.filter(Area.type == type_filter)
    if status_filter:
        query = query.filter(Area.status == status_filter)
    if priority_filter:
        query = query.filter(Area.priority == priority_filter)
    areas = query.offset(skip).limit(limit).all()
    result = []
    for area in areas:
        shop_count = db.query(func.count(Shop.id)).filter(Shop.area_id == area.id).scalar()
        # Use Pydantic schema for proper serialization
        area_dict = AreaOut.model_validate(area).model_dump()
        area_dict['shop_count'] = shop_count
        result.append(area_dict)
    return result

@router.get("/{area_id}", response_model=AreaOut)
def read_area(area_id: int, db: Session = Depends(get_db)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    shop_count = db.query(func.count(Shop.id)).filter(Shop.area_id == area.id).scalar()
    area_dict = AreaOut.model_validate(area).model_dump()
    area_dict['shop_count'] = shop_count
    return area_dict

@router.post("/", response_model=AreaOut)
def create_new_area(area: AreaCreate, db: Session = Depends(get_db),
    _: User = Depends(require_permission('areas.create'))):
    existing_area = db.query(Area).filter(Area.code == area.code).first()
    if existing_area:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Area code already exists")
    existing_name = db.query(Area).filter(Area.name == area.name).first()
    if existing_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Area name already exists")
    db_area = Area(**area.dict())
    db.add(db_area)
    db.commit()
    db.refresh(db_area)
    shop_count = db.query(func.count(Shop.id)).filter(Shop.area_id == db_area.id).scalar()
    area_dict = AreaOut.model_validate(db_area).model_dump()
    area_dict['shop_count'] = shop_count
    return area_dict

@router.put("/{area_id}", response_model=AreaOut)
def update_existing_area(area_id: int, area: AreaUpdate, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('areas.edit'))):
    db_area = db.query(Area).filter(Area.id == area_id).first()
    if db_area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    if area.code and area.code != db_area.code:
        existing_code = db.query(Area).filter(Area.code == area.code, Area.id != area_id).first()
        if existing_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Area code already exists")
    if area.name and area.name != db_area.name:
        existing_name = db.query(Area).filter(Area.name == area.name, Area.id != area_id).first()
        if existing_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Area name already exists")
    for field, value in area.dict(exclude_unset=True).items():
        setattr(db_area, field, value)
    
    db.flush()  # Flush để đảm bảo update được thực hiện
    
    # Ghi vào general_diary
    try:
        description_text = f"Sửa khu vực: {db_area.name} - Mã: {db_area.code}"
        create_general_diary_entry(
            db=db,
            source="Area",
            total_amount=0.0,
            quantity_out=0,
            quantity_in=0,
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        from ..logger import log_error
        log_error("UPDATE_AREA_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()  # Vẫn commit việc update khu vực
    
    db.refresh(db_area)
    shop_count = db.query(func.count(Shop.id)).filter(Shop.area_id == db_area.id).scalar()
    area_dict = AreaOut.model_validate(db_area).model_dump()
    area_dict['shop_count'] = shop_count
    return area_dict

@router.delete("/{area_id}")
def delete_existing_area(area_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('areas.delete'))):
    db_area = db.query(Area).filter(Area.id == area_id).first()
    if db_area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    shop_count = db.query(func.count(Shop.id)).filter(Shop.area_id == area_id).scalar()
    if shop_count > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot delete area. It has {shop_count} shop(s). Please delete shops first.")
    
    # Lưu thông tin khu vực trước khi xóa
    area_info = f"{db_area.name} - Mã: {db_area.code}"
    
    db.delete(db_area)
    db.flush()  # Flush để đảm bảo xóa được thực hiện
    
    # Ghi vào general_diary
    try:
        description_text = f"Xóa khu vực: {area_info}"
        create_general_diary_entry(
            db=db,
            source="Area",
            total_amount=0.0,
            quantity_out=0,
            quantity_in=0,
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        from ..logger import log_error
        log_error("DELETE_AREA_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()  # Vẫn commit việc xóa khu vực
    
    return {"message": "Area deleted successfully"}

@router.get("/{area_id}/shops")
def get_area_shops(area_id: int, db: Session = Depends(get_db)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    shops = db.query(Shop).filter(Shop.area_id == area_id).all()
    return shops