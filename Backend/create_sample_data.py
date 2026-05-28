#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - CREATE SAMPLE DATA
============================
Tạo dữ liệu mẫu đầy đủ cho toàn bộ chức năng:

  1.  users            — Nhân viên (3 nhân viên + admin đã có)
  2.  user_permissions — Phân quyền mẫu cho từng nhân viên
  3.  schedules        — Ca làm việc
  4.  accounts         — Khách hàng
  5.  product_groups   — Nhóm sản phẩm
  6.  products         — Sản phẩm
  7.  warehouses       — Kho hàng (1 kho / 1 sản phẩm)
  8.  prices           — Bảng giá dịch vụ
  9.  discount_codes   — Mã giảm giá
  10. areas            — Khu vực
  11. shops            — Cửa hàng
  12. orders           — Đơn hàng mẫu
  13. invoices         — Hóa đơn mẫu (từ POS)
  14. general_diary    — Nhật ký tự động (phản ánh giao dịch)
  15. shipments        — Đơn vận chuyển mẫu
  16. shipment_history — Lịch sử vận chuyển

Sử dụng:
    cd Backend
    python clear_data.py      # xóa data cũ (tuỳ chọn)
    python create_sample_data.py
"""

import sys
import os
import codecs
from datetime import datetime, date, timedelta, timezone
import random
import string

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import (
    User, UserPermission,
    Account,
    ProductGroup, Product,
    Price,
    Order, OrderItem,
    Invoice, InvoiceItem,
    Warehouse,
    Area, Shop,
    DiscountCode,
    Schedule,
    GeneralDiary,
    Shipment, ShipmentHistory,
)
from werkzeug.security import generate_password_hash


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _gen_tracking():
    return "VD" + datetime.now().strftime("%y%m%d") + \
           ''.join(random.choices(string.digits, k=6))


def create_sample_data():
    db = SessionLocal()
    stats = {}
    try:
        print("\n📦 Tạo dữ liệu mẫu...\n")

        # ── 1. NHÂN VIÊN ──────────────────────────────────────────────
        print("1️⃣  Nhân viên...")
        emp_data = [
            dict(username='nv1',       password='123456', name='thành',
                 email='nv1@example.com',      phone='0901111111',
                 position='Nhân viên bán hàng', department='Bán hàng', status=True),
            dict(username='nhanvien1', password='123456', name='Nguyễn Văn An',
                 email='nhanvien1@example.com', phone='0901111112',
                 position='Nhân viên bán hàng', department='Bán hàng', status=True),
            dict(username='nhanvien2', password='123456', name='Trần Thị Bình',
                 email='nhanvien2@example.com', phone='0902222222',
                 position='Nhân viên kho',      department='Kho',      status=True),
            dict(username='nhanvien3', password='123456', name='Lê Văn Cường',
                 email='nhanvien3@example.com', phone='0903333333',
                 position='Kỹ thuật viên',      department='Kỹ thuật', status=True),
        ]
        employees = []
        for d in emp_data:
            u = db.query(User).filter(User.username == d['username']).first()
            if not u:
                u = User(username=d['username'],
                         password=generate_password_hash(d['password']),
                         name=d['name'], email=d['email'], phone=d['phone'],
                         position=d['position'], department=d['department'],
                         status=d['status'])
                db.add(u)
            employees.append(u)
        db.flush()
        stats['users'] = len(employees)
        print(f"   ✅ {stats['users']} nhân viên")

        # ── 2. PHÂN QUYỀN ─────────────────────────────────────────────
        print("2️⃣  Phân quyền...")
        # Xóa quyền cũ của các nhân viên (không phải admin)
        for emp in employees:
            db.query(UserPermission).filter(UserPermission.user_id == emp.id).delete()
        db.flush()

        # nv1 + nhanvien1: bán hàng + hóa đơn + đơn hàng
        sales_perms = [
            'pos.view', 'pos.sell',
            'invoices.view', 'invoices.create', 'invoices.print',
            'orders.view', 'orders.create', 'orders.update_status',
            'discount_codes.view', 'discount_codes.use',
            'products.view',
            'shipping.view', 'shipping.create', 'shipping.update_status',
            'schedules.view',
        ]
        # nhanvien2: kho + sản phẩm
        warehouse_perms = [
            'warehouse.view', 'warehouse.import', 'warehouse.export', 'warehouse.edit',
            'products.view', 'products.create', 'products.edit',
            'schedules.view',
            'general_diary.view',
        ]
        # nhanvien3: kỹ thuật — xem + báo cáo
        tech_perms = [
            'products.view',
            'orders.view', 'orders.create',
            'reports.view',
            'schedules.view',
            'general_diary.view',
        ]

        perm_map = {
            employees[0].id: sales_perms,     # nv1
            employees[1].id: sales_perms,     # nhanvien1
            employees[2].id: warehouse_perms, # nhanvien2
            employees[3].id: tech_perms,      # nhanvien3
        }

        perm_count = 0
        for uid, perms in perm_map.items():
            for p in perms:
                db.add(UserPermission(user_id=uid, permission=p,
                                      granted_by='admin', granted_at=_now()))
                perm_count += 1
        db.flush()
        stats['user_permissions'] = perm_count
        print(f"   ✅ {perm_count} quyền phân cho {len(perm_map)} nhân viên")

        # ── 3. CA LÀM VIỆC ────────────────────────────────────────────
        print("3️⃣  Ca làm việc...")
        db.query(Schedule).delete(); db.flush()
        today = date.today()
        shift_data = [
            (employees[0].id, 0,  'Ca sáng',   'Buổi sáng'),
            (employees[0].id, 1,  'Ca chiều',  'Buổi chiều'),
            (employees[1].id, 0,  'Ca 1',      'Ca làm việc 1'),
            (employees[1].id, 2,  'Ca sáng',   'Buổi sáng'),
            (employees[2].id, 1,  'Ca tối',    'Buổi tối'),
            (employees[3].id, 3,  'Ca chiều',  'Buổi chiều'),
            (employees[0].id, -1, 'Ca sáng',   'Hôm qua'),
            (employees[1].id, -1, 'Ca chiều',  'Hôm qua'),
        ]
        schedules = [Schedule(employee_id=eid,
                              work_date=today + timedelta(days=d),
                              shift_type=st, notes=note)
                     for eid, d, st, note in shift_data]
        for s in schedules: db.add(s)
        db.flush()
        stats['schedules'] = len(schedules)
        print(f"   ✅ {len(schedules)} lịch làm việc")

        # ── 4. KHÁCH HÀNG ─────────────────────────────────────────────
        print("4️⃣  Khách hàng...")
        accounts = [
            Account(ten_tk='Nguyễn Văn Khách',  ma_khach_hang='KH001',
                    ngay_sinh=date(1990, 5, 15),
                    email='nguyenkhach@example.com', so_dt='0901111111',
                    dia_chi='123 Đường ABC, Quận 1, HCM', trang_thai=True),
            Account(ten_tk='Trần Thị Khách',    ma_khach_hang='KH002',
                    ngay_sinh=date(1985, 8, 20),
                    email='trankhach@example.com',    so_dt='0902222222',
                    dia_chi='456 Đường XYZ, Quận 3, HCM', trang_thai=True),
            Account(ten_tk='Lê Văn Khách',      ma_khach_hang='KH003',
                    ngay_sinh=date(1992, 3, 10),
                    email='lekhach@example.com',      so_dt='0903333333',
                    dia_chi='789 Đường DEF, Hoàn Kiếm, HN', trang_thai=True),
            Account(ten_tk='Phạm Thị Mua',      ma_khach_hang='KH004',
                    ngay_sinh=date(1995, 11, 25),
                    email='phamthi@example.com',      so_dt='0904444444',
                    dia_chi='321 Đường GHI, Quận 5, HCM', trang_thai=True),
        ]
        for a in accounts: db.add(a)
        db.flush()
        stats['accounts'] = len(accounts)
        print(f"   ✅ {len(accounts)} khách hàng")

        # ── 5. NHÓM SẢN PHẨM ─────────────────────────────────────────
        print("5️⃣  Nhóm sản phẩm...")
        group_data = [
            ('Laptop',    'Máy tính xách tay'),
            ('Điện thoại','Điện thoại thông minh'),
            ('Linh kiện', 'Linh kiện máy tính'),
            ('Phụ kiện',  'Phụ kiện máy tính'),
            ('Thiết bị',  'Thiết bị điện tử'),
        ]
        groups = []
        for name, desc in group_data:
            g = db.query(ProductGroup).filter(ProductGroup.ten_nhom == name).first()
            if not g:
                g = ProductGroup(ten_nhom=name, mo_ta=desc)
                db.add(g)
            groups.append(g)
        db.flush()
        stats['product_groups'] = len(groups)
        print(f"   ✅ {len(groups)} nhóm sản phẩm")

        # ── 6. SẢN PHẨM ───────────────────────────────────────────────
        print("6️⃣  Sản phẩm...")
        product_data = [
            dict(ma_sp='SP001', ten_sp='Laptop Dell Inspiron 15',
                 nhom_sp='Laptop',    don_vi='Cái',   so_luong=50,
                 gia_ban=15000000,   gia_von=12000000, trang_thai='active',
                 mo_ta='Laptop Dell 15 inch, RAM 8GB, SSD 256GB'),
            dict(ma_sp='SP002', ten_sp='iPhone 15 Pro Max',
                 nhom_sp='Điện thoại', don_vi='Cái', so_luong=30,
                 gia_ban=25000000,   gia_von=20000000, trang_thai='active',
                 mo_ta='iPhone 15 Pro Max 256GB'),
            dict(ma_sp='SP003', ten_sp='RAM DDR4 8GB',
                 nhom_sp='Linh kiện', don_vi='Thanh', so_luong=100,
                 gia_ban=800000,     gia_von=500000,   trang_thai='active',
                 mo_ta='RAM DDR4 8GB 3200MHz'),
            dict(ma_sp='SP004', ten_sp='Ổ cứng SSD 512GB',
                 nhom_sp='Linh kiện', don_vi='Cái',   so_luong=80,
                 gia_ban=2000000,    gia_von=1500000,  trang_thai='active',
                 mo_ta='SSD 512GB SATA III'),
            dict(ma_sp='TB001', ten_sp='thiết bị 01',
                 nhom_sp='Thiết bị',  don_vi='Cái',   so_luong=20,
                 gia_ban=250000,     gia_von=200000,   trang_thai='active',
                 mo_ta='Thiết bị điện tử mẫu'),
        ]
        products = []
        for d in product_data:
            p = db.query(Product).filter(Product.ma_sp == d['ma_sp']).first()
            if not p:
                p = Product(**d)
                db.add(p)
            products.append(p)
        db.flush()
        stats['products'] = len(products)
        print(f"   ✅ {len(products)} sản phẩm")

        # ── 7. KHO HÀNG ───────────────────────────────────────────────
        print("7️⃣  Kho hàng...")
        warehouse_data = [
            dict(ma_kho='KHO001', ten_kho='Kho chính HCM',   ma_sp='SP001',
                 gia_nhap=12000000, so_luong=50,
                 dia_chi='123 Nguyễn Văn Linh, Q7, HCM',
                 dien_thoai='0901234567', trang_thai='active',
                 ghi_chu='Kho chính'),
            dict(ma_kho='KHO002', ten_kho='Kho phụ HCM',     ma_sp='SP002',
                 gia_nhap=20000000, so_luong=30,
                 dia_chi='456 Lê Văn Việt, Q9, HCM',
                 dien_thoai='0902345678', trang_thai='active',
                 ghi_chu='Kho phụ HCM'),
            dict(ma_kho='KHO003', ten_kho='Kho linh kiện',   ma_sp='SP003',
                 gia_nhap=500000,   so_luong=100,
                 dia_chi='789 Võ Văn Tần, Q3, HCM',
                 dien_thoai='0903456789', trang_thai='active',
                 ghi_chu='Linh kiện máy tính'),
            dict(ma_kho='KHO004', ten_kho='Kho phụ kiện',    ma_sp='SP004',
                 gia_nhap=1500000,  so_luong=80,
                 dia_chi='321 Điện Biên Phủ, Bình Thạnh, HCM',
                 dien_thoai='0904567890', trang_thai='active',
                 ghi_chu='Phụ kiện máy tính'),
            dict(ma_kho='KHO005', ten_kho='Kho thiết bị',    ma_sp='TB001',
                 gia_nhap=200000,   so_luong=20,
                 dia_chi='654 Nguyễn Trãi, Q5, HCM',
                 dien_thoai='0905678901', trang_thai='active',
                 ghi_chu='Thiết bị điện tử'),
        ]
        warehouses = []
        for d in warehouse_data:
            w = db.query(Warehouse).filter(Warehouse.ma_kho == d['ma_kho']).first()
            if not w:
                w = Warehouse(**d)
                db.add(w)
            warehouses.append(w)
        db.flush()
        stats['warehouses'] = len(warehouses)
        print(f"   ✅ {len(warehouses)} kho hàng")

        # ── 8. BẢNG GIÁ DỊCH VỤ ──────────────────────────────────────
        print("8️⃣  Bảng giá dịch vụ...")
        price_data = [
            ('DV001', 'Thay keo tản nhiệt CPU',  200000,  'Thay keo + công'),
            ('DV002', 'Vệ sinh máy tính',         150000,  'Vệ sinh, hút bụi'),
            ('DV003', 'Cài đặt Windows',           300000,  'Win 10/11 + driver'),
            ('DV004', 'Nâng cấp RAM',              500000,  'Lắp đặt + test'),
            ('DV005', 'Thay màn hình laptop',     2500000, 'Màn hình + công lắp'),
            ('DV006', 'Sửa bàn phím laptop',       400000,  'Thay phím/bàn phím'),
            ('DV007', 'Thay pin laptop',            600000,  'Pin + công thay'),
        ]
        prices = []
        for ma, ten, gia, ghi in price_data:
            p = db.query(Price).filter(Price.ma_sp == ma).first()
            if not p:
                p = Price(ma_sp=ma, ten_sp=ten, gia_chung=gia, ghi_chu=ghi)
                db.add(p)
            prices.append(p)
        db.flush()
        stats['prices'] = len(prices)
        print(f"   ✅ {len(prices)} dịch vụ")

        # ── 9. MÃ GIẢM GIÁ ───────────────────────────────────────────
        print("9️⃣  Mã giảm giá...")
        def _dt(d): return datetime.combine(today + timedelta(days=d), datetime.min.time())
        discount_data = [
            dict(code='GIAM10',      name='Giảm 10%',
                 description='Giảm 10% cho đơn từ 1 triệu',
                 discount_type='percent', discount_value=10,
                 start_date=_dt(-30), end_date=_dt(30),
                 max_uses=100, used_count=5, min_order_value=1000000, status='active'),
            dict(code='GIAM50K',     name='Giảm 50,000đ',
                 description='Giảm cố định 50k',
                 discount_type='fixed', discount_value=50000,
                 start_date=_dt(-15), end_date=_dt(15),
                 max_uses=50,  used_count=10, min_order_value=500000,  status='active'),
            dict(code='KHUYENMAI20', name='Khuyến mãi 20%',
                 description='Giảm 20% đơn từ 5 triệu',
                 discount_type='percent', discount_value=20,
                 start_date=_dt(-10), end_date=_dt(20),
                 max_uses=30,  used_count=2,  min_order_value=5000000, status='active'),
            dict(code='NEWCUS100K',  name='Khách mới giảm 100k',
                 description='Ưu đãi khách hàng mới',
                 discount_type='fixed', discount_value=100000,
                 start_date=_dt(-5),  end_date=_dt(60),
                 max_uses=200, used_count=0,  min_order_value=300000,  status='active'),
            dict(code='FLASH30',     name='Flash sale 30%',
                 description='Giảm 30% cuối tuần',
                 discount_type='percent', discount_value=30,
                 start_date=_dt(-2),  end_date=_dt(5),
                 max_uses=20,  used_count=8,  min_order_value=2000000, status='active'),
        ]
        discounts = []
        for d in discount_data:
            dc = db.query(DiscountCode).filter(DiscountCode.code == d['code']).first()
            if not dc:
                dc = DiscountCode(**d)
                db.add(dc)
            discounts.append(dc)
        db.flush()
        stats['discount_codes'] = len(discounts)
        print(f"   ✅ {len(discounts)} mã giảm giá")

        # ── 10. KHU VỰC ──────────────────────────────────────────────
        print("🔟  Khu vực...")
        area_data = [
            dict(name='Hồ Chí Minh', code='HCM', type='Thành phố',
                 province='Hồ Chí Minh', district='Quận 1', ward='Bến Nghé',
                 address='123 Nguyễn Huệ, Q1, HCM',
                 phone='0901234567', email='hcm@pos.vn',
                 manager='Nguyễn Văn Quản', description='Khu vực HCM',
                 status='active', priority='high'),
            dict(name='Hà Nội',      code='HN',  type='Thành phố',
                 province='Hà Nội',       district='Hoàn Kiếm', ward='Tràng Tiền',
                 address='456 Lý Thái Tổ, Hoàn Kiếm, HN',
                 phone='0907654321', email='hn@pos.vn',
                 manager='Trần Thị Quản', description='Khu vực HN',
                 status='active', priority='medium'),
            dict(name='Đà Nẵng',     code='DN',  type='Thành phố',
                 province='Đà Nẵng',      district='Hải Châu', ward='Thanh Bình',
                 address='789 Trần Phú, Hải Châu, ĐN',
                 phone='0909876543', email='dn@pos.vn',
                 manager='Lê Văn Quản', description='Khu vực ĐN',
                 status='active', priority='medium'),
        ]
        areas = []
        for d in area_data:
            a = db.query(Area).filter(Area.code == d['code']).first()
            if not a:
                a = Area(**d)
                db.add(a)
            areas.append(a)
        db.flush()
        stats['areas'] = len(areas)
        print(f"   ✅ {len(areas)} khu vực")

        # ── 11. CỬA HÀNG ─────────────────────────────────────────────
        print("1️⃣1️⃣  Cửa hàng...")
        shop_data = [
            dict(name='PosPos HCM Q1',   code='SHOP001', area_id=areas[0].id,
                 address='123 Nguyễn Huệ, Q1, HCM',
                 phone='0912345678', email='q1@pos.vn',
                 manager='Nguyễn Văn Shop', description='Chi nhánh Q1', status='active'),
            dict(name='PosPos HCM Q7',   code='SHOP002', area_id=areas[0].id,
                 address='456 Nguyễn Văn Linh, Q7, HCM',
                 phone='0923456789', email='q7@pos.vn',
                 manager='Trần Thị Shop', description='Chi nhánh Q7', status='active'),
            dict(name='PosPos Hà Nội',   code='SHOP003', area_id=areas[1].id,
                 address='789 Lý Thái Tổ, Hoàn Kiếm, HN',
                 phone='0934567890', email='hn@pos.vn',
                 manager='Lê Văn Shop', description='Chi nhánh HN', status='active'),
            dict(name='PosPos Đà Nẵng',  code='SHOP004', area_id=areas[2].id,
                 address='321 Trần Phú, Hải Châu, ĐN',
                 phone='0945678901', email='dn@pos.vn',
                 manager='Phạm Thị Shop', description='Chi nhánh ĐN', status='active'),
        ]
        shops = []
        for d in shop_data:
            s = db.query(Shop).filter(Shop.code == d['code']).first()
            if not s:
                s = Shop(**d)
                db.add(s)
            shops.append(s)
        db.flush()
        stats['shops'] = len(shops)
        print(f"   ✅ {len(shops)} cửa hàng")

        # ── 12. ĐƠN HÀNG ─────────────────────────────────────────────
        print("1️⃣2️⃣  Đơn hàng...")
        orders = []
        order_specs = [
            ('DH260526001', accounts[0].ten_tk, products[0], 1, 15000000, today - timedelta(3), 'hoan_thanh'),
            ('DH260526002', accounts[1].ten_tk, products[1], 2, 50000000, today - timedelta(2), 'dang_xu_ly'),
            ('DH260526003', 'Khách vãng lai',   products[2], 3, 2400000,  today - timedelta(1), 'cho_xu_ly'),
            ('DH260526004', accounts[2].ten_tk, products[3], 1, 2000000,  today,               'cho_xu_ly'),
        ]
        for ma, kh, prod, qty, total, ngay, status in order_specs:
            o = db.query(Order).filter(Order.ma_don_hang == ma).first()
            if not o:
                o = Order(ma_don_hang=ma, thong_tin_kh=kh,
                          sp_banggia=prod.ma_sp, ngay_tao=ngay,
                          so_luong=qty, tong_tien=total,
                          trang_thai=status)
                db.add(o)
                db.flush()
                db.add(OrderItem(order_id=o.id, product_id=prod.id,
                                 so_luong=qty, don_gia=prod.gia_ban,
                                 total_price=prod.gia_ban * qty))
            orders.append(o)
        db.flush()
        stats['orders'] = len(orders)
        print(f"   ✅ {len(orders)} đơn hàng")

        # ── 13. HÓA ĐƠN ──────────────────────────────────────────────
        print("1️⃣3️⃣  Hóa đơn...")
        invoice_specs = [
            ('HĐ-260523-001', accounts[0].ten_tk, products[0], 1, 15000000,
             date(2026,5,23), 'Đã thanh toán', 'Tiền mặt'),
            ('HĐ-260524-001', accounts[1].ten_tk, products[1], 1, 25000000,
             date(2026,5,24), 'Đã thanh toán', 'Banking'),
            ('HĐ-260525-001', 'Khách vãng lai',   products[2], 5, 4000000,
             date(2026,5,25), 'Đã thanh toán', 'MoMo'),
            ('HĐ-260526-001', accounts[2].ten_tk, products[3], 2, 4000000,
             date(2026,5,26), 'Đã thanh toán', 'Tiền mặt'),
            ('HĐ-260526-002', accounts[3].ten_tk, products[0], 1, 14550000,
             date(2026,5,26), 'Chưa thanh toán', None),
        ]
        invoices = []
        for so_hd, nguoi, prod, qty, total, ngay, trang_thai, httt in invoice_specs:
            inv = db.query(Invoice).filter(Invoice.so_hd == so_hd).first()
            if not inv:
                inv = Invoice(so_hd=so_hd, ngay_hd=ngay, nguoi_mua=nguoi,
                              tong_tien=total, trang_thai=trang_thai,
                              hinh_thuc_tt=httt)
                db.add(inv)
                db.flush()
                db.add(InvoiceItem(invoice_id=inv.id, product_id=prod.id,
                                   product_code=prod.ma_sp, product_name=prod.ten_sp,
                                   so_luong=qty, don_gia=prod.gia_ban,
                                   total_price=prod.gia_ban * qty))
            invoices.append(inv)
        db.flush()
        stats['invoices'] = len(invoices)
        print(f"   ✅ {len(invoices)} hóa đơn")

        # ── 14. NHẬT KÝ CHUNG ─────────────────────────────────────────
        print("1️⃣4️⃣  Nhật ký chung...")
        diary_entries = [
            GeneralDiary(ngay_nhap=date(2026,5,23), so_hieu='KHO001',
                         dien_giai='Nhập kho SP001 - Laptop Dell', so_luong_nhap=50, so_luong_xuat=0,  so_tien=600000000),
            GeneralDiary(ngay_nhap=date(2026,5,24), so_hieu='BAN001',
                         dien_giai='Bán hàng HĐ-260523-001',       so_luong_nhap=0,  so_luong_xuat=1,  so_tien=15000000),
            GeneralDiary(ngay_nhap=date(2026,5,25), so_hieu='BAN002',
                         dien_giai='Bán hàng HĐ-260524-001',       so_luong_nhap=0,  so_luong_xuat=1,  so_tien=25000000),
            GeneralDiary(ngay_nhap=date(2026,5,26), so_hieu='BAN003',
                         dien_giai='Bán hàng HĐ-260526-001',       so_luong_nhap=0,  so_luong_xuat=2,  so_tien=4000000),
            GeneralDiary(ngay_nhap=date(2026,5,26), so_hieu='DiscountCode',
                         dien_giai='Áp mã GIAM10 - HĐ-260526-002', so_luong_nhap=0,  so_luong_xuat=0,  so_tien=-450000),
            GeneralDiary(ngay_nhap=date(2026,5,26), so_hieu='User',
                         dien_giai='Sửa nhân viên: nv1 - thành',   so_luong_nhap=0,  so_luong_xuat=0,  so_tien=0),
        ]
        for e in diary_entries: db.add(e)
        db.flush()
        stats['general_diary'] = len(diary_entries)
        print(f"   ✅ {len(diary_entries)} phát sinh nhật ký")

        # ── 15. VẬN CHUYỂN ───────────────────────────────────────────
        print("1️⃣5️⃣  Đơn vận chuyển...")
        ship_specs = [
            ('DH260526001', 'HĐ-260523-001', 'VD260523001001',
             accounts[0].ten_tk, '0901111111', '123 Đường ABC, Q1, HCM',
             'Hồ Chí Minh', 1200, 'Giao hàng nhanh', 0, 25000,
             'delivered', employees[0].username,
             today - timedelta(3), today - timedelta(1)),
            ('DH260526002', 'HĐ-260524-001', 'VD260524001002',
             accounts[1].ten_tk, '0902222222', '456 Đường XYZ, Q3, HCM',
             'Hồ Chí Minh', 800,  'Giao hàng thường', 0, 15000,
             'delivering', employees[1].username,
             today - timedelta(2), None),
            ('DH260526003', None,             'VD260525001003',
             'Khách vãng lai', '0909090909', '789 Đường DEF, Q5, HCM',
             'Hồ Chí Minh', 500,  'Giao nội thành', 0, 20000,
             'in_transit', None,
             today - timedelta(1), None),
            ('DH260526004', 'HĐ-260526-001', 'VD260526001004',
             accounts[2].ten_tk, '0903333333', '789 Đường DEF, HK, HN',
             'Hà Nội', 600, 'Giao liên tỉnh', 0, 35000,
             'pending', None,
             today, None),
        ]
        shipments = []
        status_descs = {
            'pending':    'Đơn hàng đang chờ được lấy',
            'picked':     'Shipper đã lấy hàng từ kho',
            'in_transit': 'Hàng đang trên đường vận chuyển',
            'delivering': 'Shipper đang giao đến địa chỉ nhận',
            'delivered':  'Giao hàng thành công',
        }
        for (oc, ic, tc, rn, rp, ra, rpv,
             wt, svc, cod, fee, st, cb,
             created, delivered) in ship_specs:
            s = db.query(Shipment).filter(Shipment.tracking_code == tc).first()
            if not s:
                est = (created + timedelta(days=3)) if created else None
                s = Shipment(
                    order_code=oc, invoice_code=ic, tracking_code=tc,
                    receiver_name=rn, receiver_phone=rp, receiver_address=ra,
                    receiver_province=rpv, weight=wt, service_type=svc,
                    cod_amount=cod, shipping_fee=fee, status=st,
                    created_by=cb, estimated_date=est, delivered_at=delivered,
                    created_at=_now(), updated_at=_now()
                )
                db.add(s)
                db.flush()
                # Tạo history
                db.add(ShipmentHistory(
                    shipment_id=s.id, status='pending',
                    description=status_descs['pending'],
                    location='Kho hàng', updated_by=cb or 'system',
                    timestamp=_now()
                ))
                if st in ('picked','in_transit','delivering','delivered'):
                    db.add(ShipmentHistory(
                        shipment_id=s.id, status='picked',
                        description=status_descs['picked'],
                        location='Điểm lấy hàng', updated_by=cb or 'system',
                        timestamp=_now()
                    ))
                if st in ('in_transit','delivering','delivered'):
                    db.add(ShipmentHistory(
                        shipment_id=s.id, status='in_transit',
                        description=status_descs['in_transit'],
                        location='Đang trên đường', updated_by=cb or 'system',
                        timestamp=_now()
                    ))
                if st in ('delivering','delivered'):
                    db.add(ShipmentHistory(
                        shipment_id=s.id, status='delivering',
                        description=status_descs['delivering'],
                        location='Gần địa chỉ nhận', updated_by=cb or 'system',
                        timestamp=_now()
                    ))
                if st == 'delivered':
                    db.add(ShipmentHistory(
                        shipment_id=s.id, status='delivered',
                        description=status_descs['delivered'],
                        location=ra, updated_by=cb or 'system',
                        timestamp=_now()
                    ))
            shipments.append(s)
        db.flush()
        stats['shipments'] = len(shipments)
        print(f"   ✅ {len(shipments)} đơn vận chuyển + lịch sử")

        # ── COMMIT ─────────────────────────────────────────────────────
        db.commit()

        print("\n" + "=" * 60)
        print("  ✅ HOÀN THÀNH TẠO DỮ LIỆU MẪU")
        print("=" * 60)
        print("\n📊 Tóm tắt:")
        for k, v in stats.items():
            print(f"   {k:<22} {v} bản ghi")
        print()

    except Exception as e:
        db.rollback()
        print(f"\n❌ Lỗi: {e}")
        import traceback; traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    print("=" * 60)
    print("  POSPOS — TẠO DỮ LIỆU MẪU")
    print("=" * 60)
    print("\n⚠️  Script này tạo dữ liệu mẫu vào DB hiện tại.")
    print("   Chạy clear_data.py trước để xóa data cũ (tuỳ chọn).\n")

    if sys.stdin.isatty():
        c = input("Tiếp tục? (yes/no): ").strip().lower()
        if c != 'yes':
            print("❌ Đã hủy"); sys.exit(0)

    try:
        create_sample_data()
    except Exception as e:
        print(f"\n❌ Lỗi: {e}"); sys.exit(1)