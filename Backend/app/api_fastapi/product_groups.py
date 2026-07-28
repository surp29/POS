from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..permission_middleware import require_permission
from ..database import get_db
from ..models import User, Product, ProductGroup
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request
from ..logger import log_error
from ..cache import cache_delete_pattern

router = APIRouter(prefix="/product-groups", tags=["product_groups"])


@router.get("/")
def list_product_groups(db: Session = Depends(get_db)):
    """Lấy danh sách nhóm sản phẩm từ bảng product_groups (FK thật qua Product.nhom_id) —
    id ổn định giữa các lần gọi, không còn tính theo vị trí trong danh sách như trước."""
    rows = (
        db.query(
            ProductGroup,
            func.coalesce(func.sum(Product.so_luong), 0).label('tong_so_luong'),
        )
        .outerjoin(Product, Product.nhom_id == ProductGroup.id)
        .group_by(ProductGroup.id)
        .order_by(ProductGroup.ten_nhom)
        .all()
    )

    groups = [
        {
            "id": group.id,
            "ten_nhom": group.ten_nhom,
            "so_luong": int(tong_so_luong or 0),
            "mo_ta": group.mo_ta or f"Nhóm sản phẩm: {group.ten_nhom}",
        }
        for group, tong_so_luong in rows
    ]

    return {"success": True, "groups": groups}


@router.post("/")
def create_product_group(payload: dict, db: Session = Depends(get_db),
    _: User = Depends(require_permission('product_groups.create'))):
    """Tạo nhóm sản phẩm mới — lưu thật vào bảng product_groups (trước đây endpoint này
    không ghi gì vào DB, chỉ trả về id giả)."""
    name = (payload.get("ten_nhom") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Thiếu tên nhóm")

    existing = db.query(ProductGroup).filter(ProductGroup.ten_nhom.ilike(name)).first()
    if existing:
        return {"success": True, "id": existing.id, "ten_nhom": existing.ten_nhom}

    group = ProductGroup(ten_nhom=name, mo_ta=payload.get("mo_ta"))
    db.add(group)
    db.commit()
    db.refresh(group)
    return {"success": True, "id": group.id, "ten_nhom": group.ten_nhom}


@router.put("/{group_id}")
def update_product_group(group_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    """Đổi tên nhóm sản phẩm theo id thật — cập nhật cả product_groups.ten_nhom lẫn
    products.nhom_sp (denormalized display, giữ đồng bộ) cho mọi sản phẩm thuộc nhóm."""
    group = db.get(ProductGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhóm sản phẩm")

    username = get_username_from_request(request)

    new_name = (payload.get("ten_nhom") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Thiếu tên nhóm mới")

    old_name = group.ten_nhom
    try:
        group.ten_nhom = new_name
        updated = db.query(Product).filter(Product.nhom_id == group_id).update(
            {Product.nhom_sp: new_name}
        )
        db.flush()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Lỗi cập nhật nhóm sản phẩm: {str(e)}')

    try:
        description_text = f"Sửa nhóm sản phẩm: {old_name} -> {new_name} - Đã cập nhật {updated} sản phẩm"
        create_general_diary_entry(
            db=db,
            source="ProductGroup",
            total_amount=0.0,
            quantity_out=0,
            quantity_in=0,
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        log_error("UPDATE_PRODUCT_GROUP_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()

    if updated:
        # Doi ten nhom lam thay doi products.nhom_sp cua moi san pham trong nhom —
        # phai xoa cache products:* neu khong /api/products/ se tra ve ten nhom cu
        # toi 5 phut (CACHE_TTL_PRODUCTS).
        cache_delete_pattern("products:*")

    return {"success": True, "updated_count": updated}


@router.delete("/{group_id}")
def delete_product_group(group_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('product_groups.delete'))):
    """Xóa nhóm sản phẩm theo id thật (xóa tất cả sản phẩm trong nhóm, giữ nguyên hành
    vi cascade như trước — chỉ khác là group_id giờ ổn định, không còn suy ra từ vị trí
    trong 1 query DISTINCT có thể đổi thứ tự giữa các lần gọi)."""
    group = db.get(ProductGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhóm sản phẩm")

    username = get_username_from_request(request)
    group_name = group.ten_nhom

    products_to_delete = db.query(Product).filter(Product.nhom_id == group_id).all()
    deleted_count = len(products_to_delete)

    deleted = db.query(Product).filter(Product.nhom_id == group_id).delete()
    db.delete(group)
    db.flush()

    try:
        description_text = f"Xóa nhóm sản phẩm: {group_name} - Đã xóa {deleted_count} sản phẩm"
        create_general_diary_entry(
            db=db,
            source="ProductGroup",
            total_amount=0.0,
            quantity_out=0,
            quantity_in=0,
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        log_error("DELETE_PRODUCT_GROUP_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()

    if deleted:
        # Xoa nhom xoa luon san pham trong nhom — phai xoa cache products:*, tuong
        # tu DELETE /api/products/{id} (xem products.py) da lam.
        cache_delete_pattern("products:*")

    return {"success": True, "deleted_count": deleted}
