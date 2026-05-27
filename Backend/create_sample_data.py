#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để tạo dữ liệu mẫu theo trình tự:
1. employees.html (User)
2. employees_schedules.html (Schedule)
3. warehouse.html (Warehouse) - nhập hàng có stock
4. products.html (Product)
5. prices.html (Price) - dịch vụ như thay keo giữ nhiệt, vệ sinh máy với giá cố định
6. discount_codes.html (DiscountCode)
7. pos.html - bán hàng (2 trường hợp: khách vãng lai và khách có tài khoản) - tạo Invoice
8. invoices.html hoặc orders.html rồi invoices.html
9. areas_management.html (Area)
10. shops_management.html (Shop)
"""
import sys
import os
import codecs
from datetime import datetime, date, timedelta
from app.database import SessionLocal
from app.models import (
    User, Account, Product, ProductGroup, Price, Order, OrderItem,
    Invoice, InvoiceItem, Warehouse, Area, Shop, GeneralDiary, DiscountCode, Schedule
)
from werkzeug.security import generate_password_hash

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def create_sample_data():
    """Tạo dữ liệu mẫu theo trình tự"""
    db = SessionLocal()
    try:
        print("\n📦 Đang tạo dữ liệu mẫu theo trình tự...")
        
        # 1. Tạo Employees (User) - employees.html
        print("\n1️⃣  Tạo nhân viên (employees.html)...")
        employee_data = [
            {
                'username': 'nhanvien1',
                'password': generate_password_hash('123456'),
                'name': 'Nguyễn Văn An',
                'email': 'nhanvien1@example.com',
                'phone': '0901111111',
                'position': 'Nhân viên bán hàng',
                'department': 'Bán hàng',
                'status': True
            },
            {
                'username': 'nhanvien2',
                'password': generate_password_hash('123456'),
                'name': 'Trần Thị Bình',
                'email': 'nhanvien2@example.com',
                'phone': '0902222222',
                'position': 'Nhân viên kho',
                'department': 'Kho',
                'status': True
            },
            {
                'username': 'nhanvien3',
                'password': generate_password_hash('123456'),
                'name': 'Lê Văn Cường',
                'email': 'nhanvien3@example.com',
                'phone': '0903333333',
                'position': 'Kỹ thuật viên',
                'department': 'Kỹ thuật',
                'status': True
            },
        ]
        employees = []
        for emp_data in employee_data:
            # Kiểm tra xem user đã tồn tại chưa
            existing_user = db.query(User).filter(User.username == emp_data['username']).first()
            if existing_user:
                print(f"  ⚠️  User '{emp_data['username']}' đã tồn tại, bỏ qua")
                employees.append(existing_user)
            else:
                emp = User(**emp_data)
                db.add(emp)
                employees.append(emp)
        db.flush()
        print(f"  ✅ Đã tạo/thêm {len(employees)} nhân viên")
        
        # 2. Tạo Schedules - employees_schedules.html
        print("\n2️⃣  Tạo lịch làm việc (employees_schedules.html)...")
        # Xóa các schedule cũ trước khi tạo mới
        db.query(Schedule).delete()
        db.flush()
        
        today = date.today()
        schedules = [
            Schedule(employee_id=employees[0].id, work_date=today + timedelta(days=1), shift_type='Ca sáng', notes='Ca làm việc buổi sáng'),
            Schedule(employee_id=employees[0].id, work_date=today + timedelta(days=2), shift_type='Ca chiều', notes='Ca làm việc buổi chiều'),
            Schedule(employee_id=employees[1].id, work_date=today + timedelta(days=1), shift_type='Ca 1', notes='Ca làm việc đầu tiên'),
            Schedule(employee_id=employees[2].id, work_date=today + timedelta(days=3), shift_type='Ca tối', notes='Ca làm việc buổi tối'),
        ]
        for sched in schedules:
            db.add(sched)
        db.flush()
        print(f"  ✅ Đã tạo {len(schedules)} lịch làm việc")
        
        # 3. Tạo Warehouse (nhập hàng có stock) - warehouse.html
        print("\n3️⃣  Tạo kho hàng với hàng tồn kho (warehouse.html)...")
        warehouses = [
            Warehouse(
                ma_kho='KHO001',
                ten_kho='Kho chính HCM',
                ma_sp='SP001',
                gia_nhap=12000000,
                so_luong=50,
                dia_chi='123 Đường Nguyễn Văn Linh, Quận 7, HCM',
                dien_thoai='0901234567',
                trang_thai='Còn hàng',
                ghi_chu='Kho chính tại HCM'
            ),
            Warehouse(
                ma_kho='KHO002',
                ten_kho='Kho phụ HCM',
                ma_sp='SP002',
                gia_nhap=20000000,
                so_luong=30,
                dia_chi='456 Đường Lê Văn Việt, Quận 9, HCM',
                dien_thoai='0902345678',
                trang_thai='Còn hàng',
                ghi_chu='Kho phụ tại HCM'
            ),
            Warehouse(
                ma_kho='KHO003',
                ten_kho='Kho linh kiện',
                ma_sp='SP003',
                gia_nhap=500000,
                so_luong=100,
                dia_chi='789 Đường Võ Văn Tần, Quận 3, HCM',
                dien_thoai='0903456789',
                trang_thai='Còn hàng',
                ghi_chu='Kho linh kiện máy tính'
            ),
            Warehouse(
                ma_kho='KHO004',
                ten_kho='Kho phụ kiện',
                ma_sp='SP004',
                gia_nhap=150000,
                so_luong=80,
                dia_chi='321 Đường Điện Biên Phủ, Quận Bình Thạnh, HCM',
                dien_thoai='0904567890',
                trang_thai='Còn hàng',
                ghi_chu='Kho phụ kiện máy tính'
            ),
        ]
        for wh in warehouses:
            db.add(wh)
        db.flush()
        print(f"  ✅ Đã tạo {len(warehouses)} kho hàng với tồn kho")
        
        # 4. Tạo Product Groups và Products - products.html
        print("\n4️⃣  Tạo nhóm sản phẩm và sản phẩm (products.html)...")
        groups = [
            ProductGroup(ten_nhom='Laptop', mo_ta='Máy tính xách tay'),
            ProductGroup(ten_nhom='Điện thoại', mo_ta='Điện thoại thông minh'),
            ProductGroup(ten_nhom='Linh kiện', mo_ta='Linh kiện máy tính'),
            ProductGroup(ten_nhom='Phụ kiện', mo_ta='Phụ kiện máy tính'),
        ]
        for group in groups:
            db.add(group)
        db.flush()
        
        products = [
            Product(
                ma_sp='SP001',
                ten_sp='Laptop Dell Inspiron 15',
                nhom_sp='Laptop',
                don_vi='Cái',
                so_luong=50,
                gia_ban=15000000,
                gia_von=12000000,
                trang_thai='Còn hàng',
                mo_ta='Laptop Dell Inspiron 15 inch, RAM 8GB, SSD 256GB'
            ),
            Product(
                ma_sp='SP002',
                ten_sp='iPhone 15 Pro Max',
                nhom_sp='Điện thoại',
                don_vi='Cái',
                so_luong=30,
                gia_ban=25000000,
                gia_von=20000000,
                trang_thai='Còn hàng',
                mo_ta='iPhone 15 Pro Max 256GB'
            ),
            Product(
                ma_sp='SP003',
                ten_sp='RAM DDR4 8GB',
                nhom_sp='Linh kiện',
                don_vi='Thanh',
                so_luong=100,
                gia_ban=800000,
                gia_von=500000,
                trang_thai='Còn hàng',
                mo_ta='RAM DDR4 8GB 3200MHz'
            ),
            Product(
                ma_sp='SP004',
                ten_sp='Ổ cứng SSD 512GB',
                nhom_sp='Linh kiện',
                don_vi='Cái',
                so_luong=80,
                gia_ban=2000000,
                gia_von=1500000,
                trang_thai='Còn hàng',
                mo_ta='SSD 512GB SATA III'
            ),
        ]
        for product in products:
            db.add(product)
        db.flush()
        print(f"  ✅ Đã tạo {len(groups)} nhóm sản phẩm và {len(products)} sản phẩm")
        
        # 5. Tạo Prices (dịch vụ như thay keo giữ nhiệt, vệ sinh máy với giá cố định) - prices.html
        print("\n5️⃣  Tạo bảng giá dịch vụ (prices.html)...")
        prices = [
            Price(
                ma_sp='DV001',
                ten_sp='Thay keo tản nhiệt CPU',
                gia_chung=200000,
                ghi_chu='Dịch vụ thay keo tản nhiệt cho CPU, bao gồm vật liệu và công'
            ),
            Price(
                ma_sp='DV002',
                ten_sp='Vệ sinh máy tính',
                gia_chung=150000,
                ghi_chu='Vệ sinh máy tính laptop/desktop, làm sạch bụi bẩn, bảo dưỡng'
            ),
            Price(
                ma_sp='DV003',
                ten_sp='Cài đặt Windows',
                gia_chung=300000,
                ghi_chu='Cài đặt Windows 10/11, bao gồm driver và phần mềm cơ bản'
            ),
            Price(
                ma_sp='DV004',
                ten_sp='Nâng cấp RAM',
                gia_chung=500000,
                ghi_chu='Dịch vụ nâng cấp RAM, bao gồm lắp đặt và test'
            ),
            Price(
                ma_sp='DV005',
                ten_sp='Thay màn hình laptop',
                gia_chung=2500000,
                ghi_chu='Thay màn hình laptop, bao gồm màn hình và công lắp đặt'
            ),
        ]
        for price in prices:
            db.add(price)
        db.flush()
        print(f"  ✅ Đã tạo {len(prices)} dịch vụ với giá cố định")
        
        # 6. Tạo Discount Codes - discount_codes.html
        print("\n6️⃣  Tạo mã giảm giá (discount_codes.html)...")
        discounts = [
            DiscountCode(
                code='GIAM10',
                name='Giảm 10%',
                description='Giảm 10% cho đơn hàng từ 1 triệu',
                discount_type='percentage',
                discount_value=10,
                start_date=datetime.combine(date.today() - timedelta(days=30), datetime.min.time()),
                end_date=datetime.combine(date.today() + timedelta(days=30), datetime.max.time()),
                max_uses=100,
                used_count=5,
                min_order_value=1000000,
                status='active'
            ),
            DiscountCode(
                code='GIAM50K',
                name='Giảm 50k',
                description='Giảm 50,000 VNĐ cho đơn hàng',
                discount_type='fixed',
                discount_value=50000,
                start_date=datetime.combine(date.today() - timedelta(days=15), datetime.min.time()),
                end_date=datetime.combine(date.today() + timedelta(days=15), datetime.max.time()),
                max_uses=50,
                used_count=10,
                min_order_value=500000,
                status='active'
            ),
            DiscountCode(
                code='KHUYENMAI20',
                name='Khuyến mãi 20%',
                description='Giảm 20% cho đơn hàng từ 5 triệu',
                discount_type='percentage',
                discount_value=20,
                start_date=datetime.combine(date.today() - timedelta(days=10), datetime.min.time()),
                end_date=datetime.combine(date.today() + timedelta(days=20), datetime.max.time()),
                max_uses=30,
                used_count=2,
                min_order_value=5000000,
                status='active'
            ),
        ]
        for discount in discounts:
            db.add(discount)
        db.flush()
        print(f"  ✅ Đã tạo {len(discounts)} mã giảm giá")
        
        # 7. Tạo Accounts (Customers) - một số có tài khoản, một số là khách vãng lai
        print("\n7️⃣  Tạo khách hàng (một số có tài khoản, một số là khách vãng lai)...")
        accounts = [
            Account(
                ten_tk='Nguyễn Văn Khách',
                ma_khach_hang='KH-HCM01',
                ngay_sinh=date(1990, 5, 15),
                email='nguyenkhach@example.com',
                so_dt='0901111111',
                dia_chi='123 Đường ABC, Quận 1, HCM',
                trang_thai=True
            ),
            Account(
                ten_tk='Trần Thị Khách',
                ma_khach_hang='KH-HCM02',
                ngay_sinh=date(1985, 8, 20),
                email='trankhach@example.com',
                so_dt='0902222222',
                dia_chi='456 Đường XYZ, Quận 3, HCM',
                trang_thai=True
            ),
            Account(
                ten_tk='Lê Văn Khách',
                ma_khach_hang='KH-HN01',
                ngay_sinh=date(1992, 3, 10),
                email='levankhach@example.com',
                so_dt='0903333333',
                dia_chi='789 Đường DEF, Quận Hoàn Kiếm, Hà Nội',
                trang_thai=True
            ),
        ]
        for account in accounts:
            db.add(account)
        db.flush()
        print(f"  ✅ Đã tạo {len(accounts)} khách hàng có tài khoản")
        
        # 8. Tạo Areas - areas_management.html
        print("\n8️⃣  Tạo khu vực (areas_management.html)...")
        areas = [
            Area(
                name='Hồ Chí Minh',
                code='HCM',
                type='Thành phố',
                province='Hồ Chí Minh',
                district='Quận 1',
                ward='Phường Bến Nghé',
                address='123 Đường Nguyễn Huệ, Quận 1, HCM',
                phone='0901234567',
                email='hcm@example.com',
                manager='Nguyễn Văn Quản Lý',
                description='Khu vực Hồ Chí Minh',
                status='active',
                priority='high'
            ),
            Area(
                name='Hà Nội',
                code='HN',
                type='Thành phố',
                province='Hà Nội',
                district='Quận Hoàn Kiếm',
                ward='Phường Tràng Tiền',
                address='456 Đường Lý Thái Tổ, Quận Hoàn Kiếm, Hà Nội',
                phone='0907654321',
                email='hn@example.com',
                manager='Trần Thị Quản Lý',
                description='Khu vực Hà Nội',
                status='active',
                priority='medium'
            ),
            Area(
                name='Đà Nẵng',
                code='DN',
                type='Thành phố',
                province='Đà Nẵng',
                district='Quận Hải Châu',
                ward='Phường Thanh Bình',
                address='789 Đường Trần Phú, Quận Hải Châu, Đà Nẵng',
                phone='0909876543',
                email='dn@example.com',
                manager='Lê Văn Quản Lý',
                description='Khu vực Đà Nẵng',
                status='active',
                priority='medium'
            ),
        ]
        for area in areas:
            db.add(area)
        db.flush()
        print(f"  ✅ Đã tạo {len(areas)} khu vực")
        
        # 9. Tạo Shops - shops_management.html
        print("\n9️⃣  Tạo shop (shops_management.html)...")
        shops = [
            Shop(
                name='Shop HCM Quận 1',
                code='SHOP001',
                area_id=areas[0].id,
                address='123 Đường Nguyễn Huệ, Quận 1, HCM',
                phone='0912345678',
                email='shop1@example.com',
                manager='Nguyễn Văn Quản Lý Shop',
                description='Shop chính tại HCM',
                status='active'
            ),
            Shop(
                name='Shop HCM Quận 7',
                code='SHOP002',
                area_id=areas[0].id,
                address='456 Đường Nguyễn Văn Linh, Quận 7, HCM',
                phone='0923456789',
                email='shop2@example.com',
                manager='Trần Thị Quản Lý Shop',
                description='Shop phụ tại HCM',
                status='active'
            ),
            Shop(
                name='Shop Hà Nội',
                code='SHOP003',
                area_id=areas[1].id,
                address='789 Đường Lý Thái Tổ, Quận Hoàn Kiếm, Hà Nội',
                phone='0934567890',
                email='shop3@example.com',
                manager='Lê Văn Quản Lý Shop',
                description='Shop tại Hà Nội',
                status='active'
            ),
        ]
        for shop in shops:
            db.add(shop)
        db.flush()
        print(f"  ✅ Đã tạo {len(shops)} shop")
        
        db.commit()
        print("\n✅ Đã tạo xong tất cả dữ liệu mẫu!")
        print("\n📊 Tóm tắt:")
        print(f"  - Nhân viên: {len(employees)}")
        print(f"  - Lịch làm việc: {len(schedules)}")
        print(f"  - Kho hàng: {len(warehouses)}")
        print(f"  - Nhóm sản phẩm: {len(groups)}")
        print(f"  - Sản phẩm: {len(products)}")
        print(f"  - Dịch vụ/Bảng giá: {len(prices)}")
        print(f"  - Mã giảm giá: {len(discounts)}")
        print(f"  - Khách hàng: {len(accounts)}")
        print(f"  - Khu vực: {len(areas)}")
        print(f"  - Shop: {len(shops)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi tạo dữ liệu mẫu: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == '__main__':
    print("=" * 60)
    print("TẠO DỮ LIỆU MẪU CHO PHẦN MỀM KẾ TOÁN")
    print("=" * 60)
    print("\n⚠️  Lưu ý: Script này chỉ tạo dữ liệu mẫu.")
    print("   Để xóa dữ liệu cũ, vui lòng chạy clear_data.py trước.\n")
    
    # Xác nhận
    if sys.stdin.isatty():
        confirm = input("Bạn có chắc muốn tạo dữ liệu mẫu? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Đã hủy")
            sys.exit(0)
    
    try:
        create_sample_data()
        print("\n" + "=" * 60)
        print("✅ Hoàn thành!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        sys.exit(1)
