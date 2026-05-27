"""
Backend: app/api_fastapi/permissions.py — Phiên bản 2
Sub-permissions chi tiết cho từng module.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, UserPermission
from ..rbac import require_admin, _get_current_user_for_rbac
from ..logger import log_success, log_warning

router = APIRouter(prefix="/permissions", tags=["permissions"])

ADMIN_POSITIONS = {"admin", "administrator", "quản trị"}

PERMISSION_TREE = {
    "Bán hàng": {
        "pos": {"label":"POS - Bán hàng","sub":{
            "pos.view":"Xem giao diện POS",
            "pos.sell":"Thực hiện bán hàng / tạo đơn",
            "pos.refund":"Hoàn tiền / hủy đơn tại POS",
        }},
        "discount_codes": {"label":"Mã giảm giá","sub":{
            "discount_codes.view":"Xem danh sách mã giảm giá",
            "discount_codes.use":"Áp dụng mã khi bán",
            "discount_codes.create":"Tạo mã giảm giá mới",
            "discount_codes.edit":"Sửa mã giảm giá",
            "discount_codes.delete":"Xóa mã giảm giá",
        }},
    },
    "Sản phẩm & Kho": {
        "products": {"label":"Quản lý sản phẩm","sub":{
            "products.view":"Xem danh sách sản phẩm",
            "products.create":"Thêm sản phẩm mới",
            "products.edit":"Sửa thông tin sản phẩm",
            "products.delete":"Xóa sản phẩm",
        }},
        "prices": {"label":"Bảng giá","sub":{
            "prices.view":"Xem bảng giá",
            "prices.create":"Tạo bảng giá",
            "prices.edit":"Sửa bảng giá",
            "prices.delete":"Xóa bảng giá",
        }},
        "warehouse": {"label":"Kho hàng","sub":{
            "warehouse.view":"Xem tồn kho",
            "warehouse.import":"Nhập hàng vào kho",
            "warehouse.export":"Xuất hàng khỏi kho",
            "warehouse.edit":"Sửa thông tin kho",
        }},
    },
    "Giao dịch": {
        "orders": {"label":"Đơn hàng","sub":{
            "orders.view":"Xem danh sách đơn hàng",
            "orders.create":"Tạo đơn hàng mới",
            "orders.edit":"Sửa đơn hàng",
            "orders.delete":"Xóa đơn hàng",
            "orders.update_status":"Cập nhật trạng thái đơn",
        }},
        "invoices": {"label":"Hóa đơn","sub":{
            "invoices.view":"Xem danh sách hóa đơn",
            "invoices.create":"Tạo hóa đơn mới",
            "invoices.edit":"Sửa hóa đơn",
            "invoices.delete":"Xóa hóa đơn",
            "invoices.print":"In hóa đơn",
        }},
        "shipping": {"label":"Vận chuyển","sub":{
            "shipping.view":"Xem đơn vận chuyển",
            "shipping.create":"Tạo đơn vận chuyển",
            "shipping.update_status":"Cập nhật trạng thái giao hàng",
            "shipping.cancel":"Hủy đơn vận chuyển",
        }},
        "general_diary": {"label":"Nhật ký chung","sub":{
            "general_diary.view":"Xem nhật ký",
            "general_diary.create":"Thêm phát sinh",
            "general_diary.edit":"Sửa phát sinh",
            "general_diary.delete":"Xóa phát sinh",
        }},
    },
    "Báo cáo": {
        "reports": {"label":"Báo cáo & Thống kê","sub":{
            "reports.view":"Xem báo cáo doanh thu",
            "reports.debt":"Xem báo cáo công nợ",
            "reports.export":"Xuất báo cáo",
        }},
    },
    "Địa điểm": {
        "areas": {"label":"Quản lý khu vực","sub":{
            "areas.view":"Xem khu vực",
            "areas.create":"Thêm khu vực",
            "areas.edit":"Sửa khu vực",
            "areas.delete":"Xóa khu vực",
        }},
        "shops": {"label":"Quản lý shop","sub":{
            "shops.view":"Xem shop",
            "shops.create":"Thêm shop",
            "shops.edit":"Sửa shop",
            "shops.delete":"Xóa shop",
        }},
    },
    "Nhân viên": {
        "schedules": {"label":"Ca làm việc","sub":{
            "schedules.view":"Xem lịch ca làm việc",
            "schedules.create":"Tạo ca làm việc",
            "schedules.edit":"Sửa ca làm việc",
            "schedules.delete":"Xóa ca làm việc",
        }},
    },
}

def _flatten():
    r = {}
    for grp, mods in PERMISSION_TREE.items():
        for mk, mi in mods.items():
            for pk, pl in mi["sub"].items():
                r[pk] = {"label":pl,"group":grp,"module":mk,"module_label":mi["label"]}
    return r

ALL_PERMISSIONS = _flatten()

def _is_admin(u): return (u.position or "").strip().lower() in ADMIN_POSITIONS
def _get_perms(db, uid): return [r.permission for r in db.query(UserPermission).filter(UserPermission.user_id==uid).all()]


@router.get("/tree")
def get_tree():
    return {"success":True,"tree":PERMISSION_TREE}

@router.get("/list")
def get_list():
    return {"success":True,"permissions":ALL_PERMISSIONS}

@router.get("/users")
def get_users(db:Session=Depends(get_db),_:User=Depends(require_admin)):
    users = db.query(User).filter(User.status==True).all()
    return {"success":True,"users":[{
        "id":u.id,"username":u.username,"name":u.name or u.username,
        "position":u.position or "","department":u.department or "",
        "is_admin":_is_admin(u),"status":u.status,
        "permissions":list(ALL_PERMISSIONS.keys()) if _is_admin(u) else _get_perms(db,u.id),
    } for u in users]}

@router.put("/user/{uid}")
def set_perms(uid:int,payload:dict,db:Session=Depends(get_db),admin:User=Depends(require_admin)):
    u=db.query(User).get(uid)
    if not u: raise HTTPException(404,"Không tìm thấy user")
    if _is_admin(u): raise HTTPException(400,"Không thể thay đổi quyền Admin")
    new=payload.get("permissions",[])
    bad=[p for p in new if p not in ALL_PERMISSIONS]
    if bad: raise HTTPException(400,f"Quyền không hợp lệ: {bad}")
    db.query(UserPermission).filter(UserPermission.user_id==uid).delete()
    for p in new:
        db.add(UserPermission(user_id=uid,permission=p,granted_by=admin.username,
                              granted_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    db.commit()
    log_success("PERM",f"{admin.username} set {len(new)} quyền cho {u.username}")
    return {"success":True,"permissions":new}

@router.post("/deactivate/{uid}")
def deactivate(uid:int,db:Session=Depends(get_db),admin:User=Depends(require_admin)):
    u=db.query(User).get(uid)
    if not u: raise HTTPException(404,"Không tìm thấy")
    if _is_admin(u): raise HTTPException(400,"Không thể vô hiệu hóa Admin")
    u.status=False; db.commit()
    return {"success":True,"message":f"Đã vô hiệu hóa: {u.username}"}

@router.post("/activate/{uid}")
def activate(uid:int,db:Session=Depends(get_db),admin:User=Depends(require_admin)):
    u=db.query(User).get(uid)
    if not u: raise HTTPException(404,"Không tìm thấy")
    u.status=True; db.commit()
    return {"success":True,"message":f"Đã kích hoạt: {u.username}"}

@router.get("/my")
def my_perms(db:Session=Depends(get_db),cu:User=Depends(_get_current_user_for_rbac)):
    if _is_admin(cu): return {"success":True,"is_admin":True,"permissions":list(ALL_PERMISSIONS.keys())}
    f=db.query(User).get(cu.id)
    if not f or not f.status: raise HTTPException(401,"Tài khoản đã bị vô hiệu hóa")
    return {"success":True,"is_admin":False,"permissions":_get_perms(db,f.id)}

@router.get("/check/{permission}")
def check(permission:str,db:Session=Depends(get_db),cu:User=Depends(_get_current_user_for_rbac)):
    f=db.query(User).get(cu.id)
    if not f or not f.status: raise HTTPException(401,"Tài khoản đã bị vô hiệu hóa")
    if _is_admin(f): return {"success":True,"allowed":True}
    ok=permission in _get_perms(db,f.id)
    if not ok: log_warning("PERM",f"'{f.username}' bị từ chối '{permission}'")
    return {"success":True,"allowed":ok,
            "message":"" if ok else f"Bạn không có quyền: {ALL_PERMISSIONS.get(permission,{}).get('label',permission)}"}