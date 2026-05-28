from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from sqlalchemy import func
from typing import List, Optional
from ..database import get_db
from ..models import User, Shop, Area
from ..schemas_fastapi import ShopCreate, ShopUpdate, ShopOut
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request

router = APIRouter(prefix="/shops", tags=["shops"])

@router.get("/", response_model=List[ShopOut])
def read_shops(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    area_filter: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Shop)
    if search:
        query = query.filter(
            Shop.name.ilike(f"%{search}%") |
            Shop.code.ilike(f"%{search}%") |
            Shop.address.ilike(f"%{search}%") |
            Shop.manager.ilike(f"%{search}%")
        )
    if area_filter:
        query = query.filter(Shop.area_id == area_filter)
    if status_filter:
        query = query.filter(Shop.status == status_filter)
    shops = query.offset(skip).limit(limit).all()
    result = []
    for shop in shops:
        area = db.query(Area).filter(Area.id == shop.area_id).first()
        # Use Pydantic schema for proper serialization
        shop_dict = ShopOut.model_validate(shop).model_dump()
        shop_dict['area_name'] = area.name if area else None
        result.append(shop_dict)
    return result

@router.get("/{shop_id}", response_model=ShopOut)
def read_shop(shop_id: int, db: Session = Depends(get_db)):
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
    area = db.query(Area).filter(Area.id == shop.area_id).first()
    shop_dict = ShopOut.model_validate(shop).model_dump()
    shop_dict['area_name'] = area.name if area else None
    return shop_dict

@router.post("/", response_model=ShopOut)
def create_new_shop(shop: ShopCreate, db: Session = Depends(get_db),
    _: User = Depends(require_permission('shops.create'))):
    existing_shop = db.query(Shop).filter(Shop.code == shop.code).first()
    if existing_shop:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shop code already exists")
    existing_name = db.query(Shop).filter(Shop.name == shop.name).first()
    if existing_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shop name already exists")
    area = db.query(Area).filter(Area.id == shop.area_id).first()
    if not area:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Area not found")
    db_shop = Shop(**shop.dict())
    try:
        db.add(db_shop)
        db.commit()
        db.refresh(db_shop)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Lỗi tạo shop: {str(e)}')
    shop_dict = ShopOut.model_validate(db_shop).model_dump()
    shop_dict['area_name'] = area.name
    return shop_dict

@router.put("/{shop_id}", response_model=ShopOut)
def update_existing_shop(shop_id: int, shop: ShopUpdate, request: Request, db: Session = Depends(get_db)):
    db_shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if db_shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    if shop.code and shop.code != db_shop.code:
        existing_code = db.query(Shop).filter(Shop.code == shop.code, Shop.id != shop_id).first()
        if existing_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shop code already exists")
    if shop.name and shop.name != db_shop.name:
        existing_name = db.query(Shop).filter(Shop.name == shop.name, Shop.id != shop_id).first()
        if existing_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shop name already exists")
    if shop.area_id and shop.area_id != db_shop.area_id:
        area = db.query(Area).filter(Area.id == shop.area_id).first()
        if not area:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Area not found")
    for field, value in shop.dict(exclude_unset=True).items():
        setattr(db_shop, field, value)
    
    db.flush()  # Flush để đảm bảo update được thực hiện
    
    # Ghi vào general_diary
    try:
        description_text = f"Sửa shop: {db_shop.name} - Mã: {db_shop.code}"
        create_general_diary_entry(
            db=db,
            source="Shop",
            total_amount=0.0,
            quantity_out=0,
            quantity_in=0,
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        from ..logger import log_error
        log_error("UPDATE_SHOP_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()  # Vẫn commit việc update shop
    
    db.refresh(db_shop)
    area = db.query(Area).filter(Area.id == db_shop.area_id).first()
    shop_dict = ShopOut.model_validate(db_shop).model_dump()
    shop_dict['area_name'] = area.name if area else None
    return shop_dict

@router.delete("/{shop_id}")
def delete_existing_shop(shop_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('shops.delete'))):
    db_shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if db_shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    # Lưu thông tin shop trước khi xóa
    shop_info = f"{db_shop.name} - Mã: {db_shop.code}"
    
    db.delete(db_shop)
    db.flush()  # Flush để đảm bảo xóa được thực hiện
    
    # Ghi vào general_diary
    try:
        description_text = f"Xóa shop: {shop_info}"
        create_general_diary_entry(
            db=db,
            source="Shop",
            total_amount=0.0,
            quantity_out=0,
            quantity_in=0,
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        from ..logger import log_error
        log_error("DELETE_SHOP_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()  # Vẫn commit việc xóa shop
    
    return {"message": "Shop deleted successfully"}

@router.get("/by-area/{area_id}")
def get_shops_by_area(area_id: int, db: Session = Depends(get_db)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    shops = db.query(Shop).filter(Shop.area_id == area_id).all()
    return shops

@router.get("/stats/summary")
def get_shops_summary(db: Session = Depends(get_db)):
    total_shops = db.query(func.count(Shop.id)).scalar()
    active_shops = db.query(func.count(Shop.id)).filter(Shop.status == 'active').scalar()
    inactive_shops = db.query(func.count(Shop.id)).filter(Shop.status == 'inactive').scalar()
    pending_shops = db.query(func.count(Shop.id)).filter(Shop.status == 'pending').scalar()
    suspended_shops = db.query(func.count(Shop.id)).filter(Shop.status == 'suspended').scalar()
    return {
        "total_shops": total_shops,
        "active_shops": active_shops,
        "inactive_shops": inactive_shops,
        "pending_shops": pending_shops,
        "suspended_shops": suspended_shops
    }