import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from sqlalchemy import text

from ..database import get_db
from ..models import User, Product, ProductGroup, OrderItem
from ..schemas_fastapi import ProductOut, ProductCreate, ProductUpdate
from ..logger import log_info, log_success, log_error, log_warning
from ..services.products import save_uploaded_file, validate_product_fields
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request
from ..cache import cache_get, cache_set, cache_delete_pattern
from ..config import Config

router = APIRouter(prefix="/products", tags=["products"])

UPLOAD_DIR = "static/images/products"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Cache key dùng chung
PRODUCTS_CACHE_KEY = "products:list"


@router.get("/")
def list_products(db: Session = Depends(get_db),
    _: User = Depends(require_permission('products.view'))):
    """
    Trả về danh sách sản phẩm.
    Kết quả được cache Redis trong Config.CACHE_TTL_PRODUCTS giây.
    Khi có thay đổi (create/update/delete), cache tự động bị invalidate.
    """
    # ── 1. Thử đọc từ cache ──────────────────────────────────────────────
    cached = cache_get(PRODUCTS_CACHE_KEY)
    if cached is not None:
        log_info("LIST_PRODUCTS", "Cache HIT — trả về từ Redis")
        return cached

    # ── 2. Cache MISS — truy vấn DB ──────────────────────────────────────
    log_info("LIST_PRODUCTS", "Cache MISS — truy vấn database")
    result = db.execute(text(
        """
        SELECT id, ma_sp, ten_sp, nhom_sp, so_luong, gia_ban, gia_chung,
               gia_von, don_vi, trang_thai, mo_ta, image_url
        FROM products
        ORDER BY id ASC
        """
    ))

    products = []
    for row in result.mappings():
        nhom_sp = row.get("nhom_sp")
        if nhom_sp and nhom_sp.startswith('{') and nhom_sp.endswith('}'):
            try:
                nhom_sp = json.loads(nhom_sp).get('ten_nhom', nhom_sp)
            except Exception:
                pass

        products.append({
            "id":         row.get("id"),
            "ma_sp":      row.get("ma_sp"),
            "ten_sp":     row.get("ten_sp"),
            "nhom_sp":    nhom_sp,
            "so_luong":   int(row.get("so_luong") or 0),
            "gia_ban":    float(row.get("gia_ban") or 0.0),
            "gia_chung":  float(row.get("gia_chung") or 0.0),
            "gia_von":    float(row.get("gia_von") or 0.0),
            "don_vi":     row.get("don_vi") or "cái",
            "trang_thai": row.get("trang_thai"),
            "mo_ta":      row.get("mo_ta"),
            "image_url":  row.get("image_url"),
            "cost_price": float(row.get("gia_von") or 0.0),
        })

    response = {"success": True, "products": products}

    # ── 3. Lưu vào cache ─────────────────────────────────────────────────
    cache_set(PRODUCTS_CACHE_KEY, response, ttl=Config.CACHE_TTL_PRODUCTS)

    return response


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    return ProductOut.model_validate(product).model_dump()


@router.get("/search")
def search_products(q: str, db: Session = Depends(get_db)):
    rows = db.query(Product).filter(Product.ten_sp.ilike(f"%{q}%")).all()
    return {"products": rows}


@router.post("/")
async def create_product(
    code: Optional[str]  = Form(None),
    name: Optional[str]  = Form(None),
    group: Optional[str] = Form(None),
    cost_price: Optional[float] = Form(None),
    price:      Optional[float] = Form(None),
    quantity:   Optional[int]   = Form(None),
    unit:       Optional[str]   = Form(None),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    log_info("CREATE_PRODUCT", f"Tạo sản phẩm mới: {code} - {name}")
    try:
        validate_product_fields(code, name)
        image_url = None
        if image:
            image_url = save_uploaded_file(image)

        p = Product(
            ma_sp=code, ten_sp=name, nhom_sp=group or '',
            so_luong=quantity or 0, gia_ban=price or 0,
            gia_chung=0, gia_von=cost_price or 0.0,
            don_vi=unit or 'cái', trang_thai="active",
            mo_ta=description or '', image_url=image_url,
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        try:
            create_general_diary_entry(
                db=db, source="Product", total_amount=0.0,
                quantity_out=0, quantity_in=quantity or 0,
                description=f"Thêm sản phẩm mới: {code} - {name}",
            )
            db.commit()
        except Exception as diary_error:
            db.rollback()
            log_error("CREATE_PRODUCT_DIARY", "Lỗi ghi General Diary", error=diary_error)

        # ── Invalidate cache sau khi tạo mới ─────────────────────────────
        cache_delete_pattern("products:*")
        log_info("CREATE_PRODUCT", "Đã xóa cache products")

        log_success("CREATE_PRODUCT", f"Tạo thành công: {code} - {name} (ID: {p.id})")
        return {"success": True, "id": p.id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_error("CREATE_PRODUCT", f"Lỗi khi tạo sản phẩm {code}", error=e)
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo sản phẩm: {str(e)}")


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    request: Request,
    code: Optional[str]  = Form(None),
    name: Optional[str]  = Form(None),
    group: Optional[str] = Form(None),
    cost_price: Optional[float] = Form(None),
    price:      Optional[float] = Form(None),
    quantity:   Optional[int]   = Form(None),
    unit:       Optional[str]   = Form(None),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")

    username = get_username_from_request(request)

    if code        is not None: p.ma_sp   = code
    if name        is not None: p.ten_sp  = name
    if group       is not None: p.nhom_sp = group
    if cost_price  is not None: p.gia_von = cost_price
    if price       is not None: p.gia_ban = price
    if quantity    is not None: p.so_luong = quantity
    if unit        is not None: p.don_vi  = unit
    if description is not None: p.mo_ta   = description

    if image:
        image_url = save_uploaded_file(image)
        if image_url:
            p.image_url = image_url

    db.flush()

    try:
        create_general_diary_entry(
            db=db, source="Product", total_amount=0.0,
            quantity_out=0, quantity_in=0,
            description=f"Sửa sản phẩm: {p.ma_sp} - {p.ten_sp}"[:255],
            username=username,
        )
        db.commit()
    except Exception as diary_error:
        log_error("UPDATE_PRODUCT_DIARY", "Lỗi ghi General Diary", error=diary_error)
        db.commit()

    db.refresh(p)

    # ── Invalidate cache sau khi cập nhật ────────────────────────────────
    cache_delete_pattern("products:*")
    log_info("UPDATE_PRODUCT", f"Đã xóa cache products (product_id={product_id})")

    log_success("UPDATE_PRODUCT", f"Cập nhật thành công: {p.ma_sp} (ID: {product_id})")
    return {"success": True, "id": p.id}


@router.delete("/{product_id}")
def delete_product(product_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('products.delete'))):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")

    username = get_username_from_request(request)
    product_info = f"{p.ma_sp} - {p.ten_sp}"

    try:
        db.query(OrderItem).filter(OrderItem.product_id == product_id).delete()
    except Exception:
        pass

    db.delete(p)
    db.flush()

    try:
        create_general_diary_entry(
            db=db, source="Product", total_amount=0.0,
            quantity_out=0, quantity_in=0,
            description=f"Xóa sản phẩm: {product_info}"[:255],
            username=username,
        )
        db.commit()
    except Exception as diary_error:
        log_error("DELETE_PRODUCT_DIARY", "Lỗi ghi General Diary", error=diary_error)
        db.commit()

    # ── Invalidate cache sau khi xóa ─────────────────────────────────────
    cache_delete_pattern("products:*")
    log_info("DELETE_PRODUCT", f"Đã xóa cache products (product_id={product_id})")

    return {"success": True}