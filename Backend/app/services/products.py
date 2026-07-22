# Backend/app/services/products.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
import os, shutil
import uuid
from ..models import Product, ProductGroup
UPLOAD_DIR = "static/images/products"
os.makedirs(UPLOAD_DIR, exist_ok=True)
def save_uploaded_file(file: UploadFile) -> str|None:
    if not file:
        return None
    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return f"/static/images/products/{filename}"
def validate_product_fields(code, name):
    if not code:
        raise HTTPException(status_code=400, detail="Mã sản phẩm không được để trống")
    if not name:
        raise HTTPException(status_code=400, detail="Tên sản phẩm không được để trống")


def get_or_create_product_group(db: Session, name: str | None) -> ProductGroup | None:
    """Tìm ProductGroup theo tên (không phân biệt hoa/thường sau khi trim), tạo mới nếu
    chưa có. Trả về None nếu name rỗng — dùng để set Product.nhom_id khi tạo/sửa sản
    phẩm, thay vì chỉ lưu `nhom_sp` (text) như trước."""
    clean = (name or '').strip()
    if not clean:
        return None
    group = db.query(ProductGroup).filter(
        ProductGroup.ten_nhom.ilike(clean)
    ).first()
    if group:
        return group
    group = ProductGroup(ten_nhom=clean)
    db.add(group)
    db.flush()  # lấy id ngay để gán cho product trong cùng transaction
    return group
