from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from ..database import get_db
from ..models import User, ProductGroup
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request
from ..logger import log_error

router = APIRouter(prefix="/product-groups", tags=["product_groups"])


@router.get("/")
def list_product_groups(db: Session = Depends(get_db)):
    """Lấy danh sách nhóm sản phẩm từ bảng products với tổng số lượng"""
    from ..models import User, Product
    from sqlalchemy import func
    
    # Lấy tất cả nhóm sản phẩm và tổng số lượng từ field nhom_sp của bảng products
    product_groups = db.query(
        Product.nhom_sp,
        func.sum(Product.so_luong).label('tong_so_luong')
    ).filter(
        Product.nhom_sp.isnot(None)
    ).group_by(
        Product.nhom_sp
    ).all()
    
    # Chuyển đổi thành list các nhóm
    groups = []
    for i, (nhom_sp, tong_so_luong) in enumerate(product_groups):
        if nhom_sp and nhom_sp.strip():  # Chỉ lấy nhóm không rỗng
            groups.append({
                "id": i + 1,  # Tạo ID giả
                "ten_nhom": nhom_sp.strip(),
                "so_luong": int(tong_so_luong) if tong_so_luong else 0,  # Tổng số lượng
                "mo_ta": f"Nhóm sản phẩm: {nhom_sp.strip()}"
            })
    
    # Sắp xếp theo tên nhóm
    groups.sort(key=lambda x: x["ten_nhom"])
    
    return {
        "success": True,
        "groups": groups
    }


@router.post("/")
def create_product_group(payload: dict, db: Session = Depends(get_db),
    _: User = Depends(require_permission('product_groups.create'))):
    """Tạo nhóm sản phẩm mới (chỉ trả về thông tin, không lưu vào database)"""
    name = (payload.get("ten_nhom") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Thiếu tên nhóm")
    
    # Kiểm tra xem nhóm đã tồn tại trong products chưa
    from ..models import User, Product
    exists = db.query(Product).filter(Product.nhom_sp == name).first()
    if exists:
        return {"success": True, "id": 1, "ten_nhom": name}
    
    # Trả về thông tin nhóm mới (không lưu vào database)
    return {"success": True, "id": 999, "ten_nhom": name}


@router.put("/{group_id}")
def update_product_group(group_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    """Cập nhật nhóm sản phẩm (cập nhật tất cả sản phẩm trong nhóm)"""
    from ..models import User, Product
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    new_name = (payload.get("ten_nhom") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Thiếu tên nhóm mới")
    
    # Cập nhật tất cả sản phẩm có nhom_sp cũ thành nhom_sp mới
    # (Cần biết tên nhóm cũ để cập nhật)
    old_name = payload.get("old_ten_nhom", "")
    if old_name:
        updated = db.query(Product).filter(Product.nhom_sp == old_name).update({Product.nhom_sp: new_name})
        db.flush()  # Flush để đảm bảo update được thực hiện
        
        # Ghi vào general_diary
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
            db.commit()  # Vẫn commit việc update nhóm sản phẩm
        
        return {"success": True, "updated_count": updated}
    
    return {"success": True}


@router.delete("/{group_id}")
def delete_product_group(group_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('product_groups.delete'))):
    """Xóa nhóm sản phẩm (xóa tất cả sản phẩm trong nhóm)"""
    from ..models import User, Product
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    # Cần biết tên nhóm để xóa
    group_name = db.query(Product.nhom_sp).distinct().filter(Product.nhom_sp.isnot(None)).all()
    if group_id <= len(group_name):
        nhom_sp = group_name[group_id - 1][0]  # Lấy tên nhóm theo ID
        if nhom_sp:
            # Đếm số sản phẩm trước khi xóa
            products_to_delete = db.query(Product).filter(Product.nhom_sp == nhom_sp).all()
            deleted_count = len(products_to_delete)
            
            # Xóa tất cả sản phẩm trong nhóm này
            deleted = db.query(Product).filter(Product.nhom_sp == nhom_sp).delete()
            db.flush()  # Flush để đảm bảo xóa được thực hiện
            
            # Ghi vào general_diary
            try:
                description_text = f"Xóa nhóm sản phẩm: {nhom_sp} - Đã xóa {deleted_count} sản phẩm"
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
                db.commit()  # Vẫn commit việc xóa nhóm sản phẩm
            
            return {"success": True, "deleted_count": deleted}
    
    return {"success": True}