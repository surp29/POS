from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from ..database import get_db
from ..models import User, Warehouse
from ..schemas_fastapi import WarehouseOut, WarehouseCreate, WarehouseUpdate
from ..logger import log_info, log_success, log_error, log_warning
from ..services.general_diary import create_general_diary_entry
from ..services.auth_helper import get_username_from_request


router = APIRouter(prefix="/warehouse", tags=["warehouse"])


@router.get("/", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db),
    _: User = Depends(require_permission('warehouse.view'))):
    """Lấy danh sách tất cả kho hàng"""
    try:
        warehouses = db.query(Warehouse).all()
        log_info("LIST_WAREHOUSES", f"Đã lấy {len(warehouses)} kho hàng")
        return [WarehouseOut.model_validate(w).model_dump() for w in warehouses]
    except Exception as e:
        log_error("LIST_WAREHOUSES", "Lỗi khi lấy danh sách kho hàng", error=e)
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách kho hàng: {str(e)}")


@router.get("/{warehouse_id}", response_model=WarehouseOut)
def get_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin một kho hàng theo ID"""
    wh = db.query(Warehouse).get(warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Không tìm thấy kho hàng")
    return WarehouseOut.model_validate(wh).model_dump()


@router.post("/")
def add_warehouse(payload: WarehouseCreate, db: Session = Depends(get_db),
    _: User = Depends(require_permission('warehouse.import'))):
    """Tạo kho hàng mới"""
    log_info("CREATE_WAREHOUSE", f"Tạo kho hàng mới: {payload.ma_kho} - {payload.ten_kho}")
    
    try:
        # Map compatibility fields
        so_luong = payload.so_luong if payload.so_luong else (payload.so_luong_sp or 0)
        ghi_chu = payload.ghi_chu if payload.ghi_chu else (payload.mo_ta or None)
        
        # Validate ma_sp is required (model constraint)
        if not payload.ma_sp or not payload.ma_sp.strip():
            raise HTTPException(status_code=400, detail="Mã sản phẩm (ma_sp) là bắt buộc")
        
        wh = Warehouse(
            ma_kho=payload.ma_kho,
            ten_kho=payload.ten_kho,
            dia_chi=payload.dia_chi,
            dien_thoai=payload.dien_thoai,
            ma_sp=payload.ma_sp.strip(),
            gia_nhap=payload.gia_nhap or 0.0,
            so_luong=so_luong,
            ghi_chu=ghi_chu,
            trang_thai=payload.trang_thai or 'Hoạt động',
        )
        # Tạo warehouse và diary entry trong cùng một transaction
        db.add(wh)
        db.flush()  # Flush để lấy ID nhưng chưa commit
        
        # Tự động ghi vào General Diary trước khi commit
        entry = None
        description = ""
        try:
            ma_sp_display = payload.ma_sp if payload.ma_sp else "N/A"
            description = f"Thêm kho hàng mới: {payload.ma_kho} - {payload.ten_kho} - Sản phẩm: {ma_sp_display} - Nhập {so_luong} sản phẩm"
            # Giới hạn độ dài description (255 ký tự)
            if len(description) > 255:
                description = description[:252] + "..."
            
            entry = create_general_diary_entry(
                db=db,
                source="Warehouse",
                total_amount=0.0,
                quantity_out=0,
                quantity_in=so_luong or 0,
                description=description
            )
            
            if entry:
                log_info("CREATE_WAREHOUSE_DIARY", f"Đã tạo entry trong General Diary: Warehouse - {description}")
            else:
                log_warning("CREATE_WAREHOUSE_DIARY", "Không thể tạo entry trong General Diary (entry = None)")
        except Exception as diary_error:
            # Log lỗi chi tiết nhưng không làm gián đoạn việc tạo warehouse
            import traceback
            error_trace = traceback.format_exc()
            log_error("CREATE_WAREHOUSE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
            log_error("CREATE_WAREHOUSE_DIARY", f"Traceback: {error_trace}")
            # Tiếp tục commit warehouse dù có lỗi diary
        
        # Commit cả warehouse và diary entry cùng lúc
        try:
            db.commit()
            db.refresh(wh)
            
            if entry:
                log_success("CREATE_WAREHOUSE_DIARY", f"Đã commit entry vào General Diary: Warehouse - {description}")
            else:
                log_warning("CREATE_WAREHOUSE_DIARY", "Warehouse đã được tạo nhưng không có diary entry")
        except Exception as commit_error:
            db.rollback()
            log_error("CREATE_WAREHOUSE", f"Lỗi khi commit: {str(commit_error)}", error=commit_error)
            raise
        
        log_success("CREATE_WAREHOUSE", f"Tạo kho hàng thành công: {payload.ma_kho} (ID: {wh.id})")
        return {"success": True, "id": wh.id}
    except Exception as e:
        db.rollback()
        log_error("CREATE_WAREHOUSE", f"Lỗi khi tạo kho hàng {payload.ma_kho}", error=e)
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo kho hàng: {str(e)}")


@router.put("/{warehouse_id}")
def update_warehouse(warehouse_id: int, payload: WarehouseUpdate, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('warehouse.edit'))):
    """Cập nhật thông tin kho hàng"""
    log_info("UPDATE_WAREHOUSE", f"Cập nhật kho hàng ID: {warehouse_id}")
    
    wh = db.query(Warehouse).get(warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Không tìm thấy kho hàng")
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    try:
        # Update fields if provided
        if payload.ma_kho is not None:
            wh.ma_kho = payload.ma_kho
        if payload.ten_kho is not None:
            wh.ten_kho = payload.ten_kho
        if payload.dia_chi is not None:
            wh.dia_chi = payload.dia_chi
        if payload.dien_thoai is not None:
            wh.dien_thoai = payload.dien_thoai
        if payload.ma_sp is not None:
            wh.ma_sp = payload.ma_sp
        if payload.gia_nhap is not None:
            wh.gia_nhap = payload.gia_nhap
        if payload.so_luong is not None:
            wh.so_luong = payload.so_luong
        if payload.ghi_chu is not None:
            wh.ghi_chu = payload.ghi_chu
        if payload.trang_thai is not None:
            wh.trang_thai = payload.trang_thai
        
        db.flush()  # Flush để đảm bảo update được thực hiện
        
        # Ghi vào general_diary
        try:
            description_text = f"Sửa kho hàng: {wh.ma_kho} - {wh.ten_kho} - SP: {wh.ma_sp or 'N/A'}"
            create_general_diary_entry(
                db=db,
                source="Warehouse",
                total_amount=0.0,
                quantity_out=0,
                quantity_in=0,
                description=description_text[:255],
                username=username
            )
            db.commit()
        except Exception as diary_error:
            log_error("UPDATE_WAREHOUSE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
            db.commit()  # Vẫn commit việc update kho hàng
        
        db.refresh(wh)
        
        log_success("UPDATE_WAREHOUSE", f"Cập nhật kho hàng thành công: {wh.ma_kho} (ID: {warehouse_id})")
        return {"success": True, "id": wh.id}
    except Exception as e:
        db.rollback()
        log_error("UPDATE_WAREHOUSE", f"Lỗi khi cập nhật kho hàng {warehouse_id}", error=e)
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật kho hàng: {str(e)}")


@router.delete("/{warehouse_id}")
def delete_warehouse(warehouse_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('warehouse.export'))):
    """Xóa kho hàng"""
    log_info("DELETE_WAREHOUSE", f"Xóa kho hàng ID: {warehouse_id}")
    
    wh = db.query(Warehouse).get(warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Không tìm thấy kho hàng")
    
    # Lấy username từ token
    username = get_username_from_request(request)
    
    # Lưu thông tin kho hàng trước khi xóa
    warehouse_info = f"{wh.ma_kho} - {wh.ten_kho} - SP: {wh.ma_sp or 'N/A'}"
    
    try:
        db.delete(wh)
        db.flush()  # Flush để đảm bảo xóa được thực hiện
        
        # Ghi vào general_diary
        try:
            description_text = f"Xóa kho hàng: {warehouse_info}"
            create_general_diary_entry(
                db=db,
                source="Warehouse",
                total_amount=0.0,
                quantity_out=0,
                quantity_in=0,
                description=description_text[:255],
                username=username
            )
            db.commit()
        except Exception as diary_error:
            log_error("DELETE_WAREHOUSE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
            db.commit()  # Vẫn commit việc xóa kho hàng
        
        log_success("DELETE_WAREHOUSE", f"Xóa kho hàng thành công: {wh.ma_kho} (ID: {warehouse_id})")
        return {"success": True}
    except Exception as e:
        db.rollback()
        log_error("DELETE_WAREHOUSE", f"Lỗi khi xóa kho hàng {warehouse_id}", error=e)
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa kho hàng: {str(e)}")