#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - SETUP DATABASE
=======================
Tạo tất cả bảng DB từ models.py và tạo tài khoản admin mặc định.

Bảng được tạo:
  users              - Nhân viên / tài khoản đăng nhập
  user_permissions   - Phân quyền chi tiết cho từng nhân viên
  accounts           - Khách hàng
  product_groups     - Nhóm sản phẩm
  products           - Sản phẩm
  prices             - Bảng giá dịch vụ
  invoices           - Hóa đơn
  invoice_items      - Chi tiết hóa đơn
  orders             - Đơn hàng
  order_items        - Chi tiết đơn hàng
  warehouses         - Kho hàng
  areas              - Khu vực
  shops              - Cửa hàng / chi nhánh
  discount_codes     - Mã giảm giá
  schedules          - Ca làm việc nhân viên
  general_diary      - Nhật ký kế toán (auto-log)
  audit_logs         - Lịch sử thao tác hệ thống
  shipments          - Đơn vận chuyển
  shipment_history   - Lịch sử trạng thái vận chuyển

Sử dụng:
    cd Backend
    python setup_database.py
"""

import sys
import os
import codecs

# Fix encoding Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from app.database import engine, Base, SessionLocal
from app.models import (
    User, UserPermission,
    Account,
    ProductGroup, Product,
    Price,
    Invoice, InvoiceItem,
    Order, OrderItem,
    Warehouse,
    Area, Shop,
    DiscountCode,
    Schedule,
    GeneralDiary,
    AuditLog,
    Shipment, ShipmentHistory,
)


TABLES_EXPECTED = [
    "users", "user_permissions",
    "accounts",
    "product_groups", "products",
    "prices",
    "invoices", "invoice_items",
    "orders", "order_items",
    "warehouses",
    "areas", "shops",
    "discount_codes",
    "schedules",
    "general_diary",
    "audit_logs",
    "shipments", "shipment_history",
]


def setup_database():
    """Tạo tất cả bảng từ metadata."""
    print("=" * 60)
    print("  POSPOS — SETUP DATABASE")
    print("=" * 60)

    try:
        print("\n📋 Danh sách bảng sẽ được tạo:")
        actual_tables = sorted(Base.metadata.tables.keys())
        for t in actual_tables:
            mark = "✅" if t in TABLES_EXPECTED else "➕"
            print(f"   {mark} {t}")

        missing = [t for t in TABLES_EXPECTED if t not in actual_tables]
        if missing:
            print(f"\n⚠️  Bảng trong danh sách nhưng chưa có model: {missing}")

        print(f"\n🚀 Đang tạo {len(actual_tables)} bảng...")
        Base.metadata.create_all(bind=engine)

        print(f"✅ Tạo xong {len(actual_tables)} bảng!")

    except SQLAlchemyError as e:
        print(f"❌ Lỗi database: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


def ensure_default_admin(username: str = "admin", password: str = "admin123"):
    """Tạo tài khoản admin mặc định nếu chưa tồn tại."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"\nℹ️  Tài khoản '{username}' đã tồn tại — bỏ qua.")
            return
        user = User(
            username   = username,
            password   = generate_password_hash(password),
            name       = "Administrator",
            email      = None,
            phone      = None,
            position   = "Admin",
            department = "System",
            status     = True,
        )
        db.add(user)
        db.commit()
        print(f"\n✅ Tạo tài khoản admin: username={username}  password={password}")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Lỗi tạo admin: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    setup_database()
    ensure_default_admin()
    print("\n🌐 Database sẵn sàng sử dụng!")
    print("   Bước tiếp: python create_sample_data.py\n")