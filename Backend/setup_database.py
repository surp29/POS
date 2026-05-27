#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHẦN MỀM KẾ TOÁN - SETUP DATABASE TỰ ĐỘNG
===========================================

Script này tạo tự động tất cả các bảng cần thiết cho ứng dụng.
Có thể chạy trên máy khác để setup database mới.

Sử dụng:
    python setup_database.py

Yêu cầu:
    - Python 3.8+
    - SQLAlchemy
    - psycopg2 (PostgreSQL)
    - Database đã được tạo và cấu hình trong app/config.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.database import engine, Base, SessionLocal
from app.models import *  # Import tất cả models để đảm bảo được đăng ký
from werkzeug.security import generate_password_hash

def setup_database():
    """Tạo tất cả bảng trong database"""
    try:
        print("🚀 Bắt đầu tạo database...")
        print("📊 Đang tạo các bảng:")
        
        # Lấy danh sách tất cả bảng sẽ được tạo
        tables = Base.metadata.tables.keys()
        for table_name in sorted(tables):
            print(f"  - {table_name}")
        
        # Tạo tất cả bảng
        Base.metadata.create_all(bind=engine)
        
        print(f"✅ Hoàn thành! Đã tạo {len(tables)} bảng.")
        print("🌐 Database đã sẵn sàng sử dụng.")
        
    except SQLAlchemyError as e:
        print(f"❌ Lỗi database: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")
        sys.exit(1)

def ensure_default_admin(username: str = "admin", password: str = "admin123"):
    """Tạo sẵn tài khoản admin nếu chưa tồn tại."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"ℹ️  Tài khoản '{username}' đã tồn tại. Bỏ qua tạo mới.")
            return
        hashed = generate_password_hash(password)
        user = User(
            username=username,
            password=hashed,
            name="Administrator",
            email=None,
            phone=None,
            position="Admin",
            department="System",
            status=True,
        )
        db.add(user)
        db.commit()
        print("✅ Đã tạo tài khoản admin mặc định: username=admin, password=admin123")
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi tạo tài khoản admin mặc định: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    setup_database()
    ensure_default_admin()
