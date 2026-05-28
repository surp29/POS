#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - CLEAR DATA
===================
Xóa toàn bộ dữ liệu nghiệp vụ, giữ lại tài khoản admin.

Thứ tự xóa (tránh lỗi foreign key):
  1. shipment_history   (FK → shipments)
  2. shipments
  3. audit_logs
  4. user_permissions   (FK → users)
  5. schedules          (FK → users)
  6. invoice_items      (FK → invoices, products)
  7. invoices
  8. order_items        (FK → orders, products)
  9. orders
  10. general_diary
  11. discount_codes
  12. warehouses
  13. products
  14. product_groups
  15. prices
  16. accounts          (khách hàng — không phải users)
  17. shops             (FK → areas)
  18. areas
  19. users             (giữ lại admin)

Sử dụng:
    cd Backend
    python clear_data.py
"""

import sys
import os
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import (
    ShipmentHistory, Shipment,
    AuditLog,
    UserPermission, Schedule,
    InvoiceItem, Invoice,
    OrderItem, Order,
    GeneralDiary,
    DiscountCode,
    Warehouse,
    Product, ProductGroup,
    Price,
    Account,
    Shop, Area,
    User,
)


def clear_data(keep_admin: bool = True):
    db = SessionLocal()
    try:
        print("=" * 60)
        print("  POSPOS — XÓA DỮ LIỆU")
        print("=" * 60)
        print("\n⚠️  Thao tác này sẽ xóa TẤT CẢ dữ liệu nghiệp vụ!")
        if keep_admin:
            print("   Tài khoản 'admin' sẽ được giữ lại.\n")

        # Xác nhận
        if sys.stdin.isatty():
            confirm = input("Bạn có chắc muốn tiếp tục? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print("❌ Đã hủy."); return
        else:
            print("Chạy tự động — tự xác nhận...")

        print("\n🗑️  Đang xóa...")

        steps = [
            (ShipmentHistory, "ShipmentHistory"),
            (Shipment,        "Shipment"),
            (AuditLog,        "AuditLog"),
            (UserPermission,  "UserPermission"),
            (Schedule,        "Schedule"),
            (InvoiceItem,     "InvoiceItem"),
            (Invoice,         "Invoice"),
            (OrderItem,       "OrderItem"),
            (Order,           "Order"),
            (GeneralDiary,    "GeneralDiary"),
            (DiscountCode,    "DiscountCode"),
            (Warehouse,       "Warehouse"),
            (Product,         "Product"),
            (ProductGroup,    "ProductGroup"),
            (Price,           "Price"),
            (Account,         "Account"),
            (Shop,            "Shop"),
            (Area,            "Area"),
        ]

        for Model, label in steps:
            n = db.query(Model).delete()
            print(f"   ✓ {label:<20} {n} bản ghi")

        # Xóa users — giữ lại admin
        if keep_admin:
            n_other = db.query(User).filter(User.username != 'admin').delete()
            print(f"   ✓ User (non-admin)   {n_other} bản ghi (admin giữ lại)")
        else:
            n_all = db.query(User).delete()
            print(f"   ✓ User (tất cả)      {n_all} bản ghi")

        db.commit()
        print("\n✅ Xóa xong!")
        if keep_admin:
            print("   Tài khoản 'admin' vẫn còn.")
        print("   Chạy create_sample_data.py để tạo dữ liệu mới.\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Lỗi: {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    clear_data(keep_admin=True)