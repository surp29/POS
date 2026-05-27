#!/usr/bin/env python3
"""
Script để xóa tất cả dữ liệu trừ tài khoản admin
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import (
    User, InvoiceItem, Invoice, OrderItem, Order, Price, Product, ProductGroup,
    Warehouse, Shop, Area, Account, GeneralDiary, DiscountCode, Schedule
)
import codecs

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def clear_data():
    """Xóa tất cả dữ liệu trừ tài khoản admin"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("XÓA DỮ LIỆU (GIỮ LẠI TÀI KHOẢN ADMIN)")
        print("=" * 60)
        print("\n⚠️  CẢNH BÁO: Thao tác này sẽ xóa TẤT CẢ dữ liệu!")
        print("   Chỉ tài khoản 'admin' sẽ được giữ lại.\n")
        
        # Auto-confirm if running non-interactively
        if not sys.stdin.isatty():
            confirm = 'yes'
            print("Chạy trong môi trường không tương tác, tự động xác nhận...")
        else:
            confirm = input("Bạn có chắc muốn tiếp tục? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Đã hủy thao tác.")
            return
        
        print("\n🗑️  Đang xóa dữ liệu cũ...")
        
        # Xóa theo thứ tự để tránh lỗi foreign key
        db.query(InvoiceItem).delete()
        print("  ✓ Đã xóa InvoiceItem")
        
        db.query(Invoice).delete()
        print("  ✓ Đã xóa Invoice")
        
        db.query(OrderItem).delete()
        print("  ✓ Đã xóa OrderItem")
        
        db.query(Order).delete()
        print("  ✓ Đã xóa Order")
        
        db.query(Price).delete()
        print("  ✓ Đã xóa Price")
        
        db.query(Product).delete()
        print("  ✓ Đã xóa Product")
        
        db.query(ProductGroup).delete()
        print("  ✓ Đã xóa ProductGroup")
        
        db.query(Warehouse).delete()
        print("  ✓ Đã xóa Warehouse")
        
        db.query(Shop).delete()
        print("  ✓ Đã xóa Shop")
        
        db.query(Area).delete()
        print("  ✓ Đã xóa Area")
        
        # Xóa Account (Account là khách hàng, không phải user)
        db.query(Account).delete()
        print("  ✓ Đã xóa Account")
        
        # Xóa Schedule trước khi xóa User (vì Schedule có foreign key đến User)
        db.query(Schedule).delete()
        print("  ✓ Đã xóa Schedule")
        
        # Giữ lại User admin
        admin_user = db.query(User).filter(User.username == 'admin').first()
        if admin_user:
            # Xóa tất cả user khác
            db.query(User).filter(User.username != 'admin').delete()
            print("  ✓ Đã xóa User (giữ lại admin)")
        else:
            db.query(User).delete()
            print("  ✓ Đã xóa User (không tìm thấy admin)")
        
        db.query(GeneralDiary).delete()
        print("  ✓ Đã xóa GeneralDiary")
        
        db.query(DiscountCode).delete()
        print("  ✓ Đã xóa DiscountCode")
        
        db.commit()
        
        print("\n✅ Đã xóa tất cả dữ liệu thành công (trừ tài khoản admin).")
        print("\n📋 Tóm tắt:")
        print("  - Tất cả dữ liệu đã được xóa")
        print("  - Tài khoản 'admin' đã được giữ lại")
        print("  - Database sẵn sàng để nhập dữ liệu mới theo lộ trình của bạn")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Lỗi khi xóa dữ liệu: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    clear_data()

