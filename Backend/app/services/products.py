# Backend/app/services/products.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
import os, shutil
import uuid
from ..models import Product
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
