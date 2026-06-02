#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - SETUP DATABASE
=======================
Tạo tất cả bảng DB + tài khoản admin mặc định.

Sử dụng:
    cd Backend
    python setup_database.py

Nếu bị lỗi kết nối, tạo file Backend/.env với nội dung:
    DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/pos
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env trước khi import bất cứ thứ gì
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))


def check_connection():
    """Kiểm tra kết nối DB và hướng dẫn nếu lỗi."""
    from app.config import Config
    db_url = Config.SQLALCHEMY_DATABASE_URI

    # Che password khi hiển thị
    import re
    safe_url = re.sub(r':([^@]+)@', ':***@', db_url)
    print(f"   Connecting: {safe_url}")

    try:
        import psycopg2
        from urllib.parse import urlparse
        u = urlparse(db_url)

        # Thử kết nối đến postgres DB trước (để tạo DB pos nếu chưa có)
        conn = psycopg2.connect(
            host=u.hostname, port=u.port or 5432,
            dbname='postgres',
            user=u.username, password=u.password,
            connect_timeout=5,
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Tạo DB nếu chưa có
        dbname = u.path.lstrip('/')
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{dbname}'")
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{dbname}"')
            print(f"   ✅ Đã tạo database '{dbname}'")
        else:
            print(f"   ✅ Database '{dbname}' đã tồn tại")
        cur.close(); conn.close()
        return True

    except psycopg2.OperationalError as e:
        err = str(e).strip()
        print(f"\n❌ Không thể kết nối PostgreSQL!")
        print(f"   Lỗi: {err}\n")

        if 'password authentication failed' in err:
            print("  ┌─ NGUYÊN NHÂN: Sai mật khẩu PostgreSQL")
            print("  │")
            print("  │  Tạo file Backend/.env với nội dung:")
            print("  │")
            print("  │    DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/pos")
            print("  │")
            print("  │  Thay YOUR_PASSWORD bằng mật khẩu PostgreSQL của bạn.")
            print("  │  (Mật khẩu bạn đặt khi cài PostgreSQL)")
            print("  └─────────────────────────────────────────────────────\n")
        elif 'Connection refused' in err or 'could not connect' in err:
            print("  ┌─ NGUYÊN NHÂN: PostgreSQL chưa chạy")
            print("  │  Khởi động PostgreSQL:")
            print("  │    Windows: Vào Services → PostgreSQL → Start")
            print("  │    Linux:   sudo systemctl start postgresql")
            print("  └─────────────────────────────────────────────────────\n")
        return False

    except Exception as e:
        print(f"\n❌ Lỗi không xác định: {e}")
        return False


def setup_tables():
    """Tạo tất cả bảng từ models."""
    from sqlalchemy.exc import SQLAlchemyError
    from app.database import engine, Base
    import app.models  # noqa — import để register tất cả models

    try:
        tables = sorted(Base.metadata.tables.keys())
        print(f"\n📋 Bảng sẽ được tạo ({len(tables)}):")
        for t in tables:
            print(f"   ✅ {t}")

        print(f"\n🚀 Đang tạo {len(tables)} bảng...")
        Base.metadata.create_all(bind=engine)
        print(f"✅ Tạo xong {len(tables)} bảng!")
        return True
    except SQLAlchemyError as e:
        print(f"❌ Lỗi tạo bảng: {e}")
        return False


def ensure_admin():
    """Tạo tài khoản admin mặc định nếu chưa có."""
    from werkzeug.security import generate_password_hash
    from app.database import SessionLocal
    from app.models import User

    username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            print(f"\nℹ️  Tài khoản '{username}' đã tồn tại — bỏ qua.")
            return
        db.add(User(
            username=username,
            password=generate_password_hash(password),
            name="Administrator",
            position="Admin",
            department="System",
            status=True,
        ))
        db.commit()
        print(f"\n✅ Tạo tài khoản admin:")
        print(f"   Username : {username}")
        print(f"   Password : {password}")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Lỗi tạo admin: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  POSPOS — SETUP DATABASE")
    print("=" * 60)

    # B1: Kiểm tra & kết nối
    print("\n🔌 Kiểm tra kết nối database...")
    if not check_connection():
        sys.exit(1)

    # B2: Tạo bảng
    if not setup_tables():
        sys.exit(1)

    # B3: Tạo admin
    ensure_admin()

    print("\n" + "=" * 60)
    print("  ✅ SETUP HOÀN TẤT!")
    print("=" * 60)
    print("\n📌 Bước tiếp theo:")
    print("   python create_sample_data.py   ← tạo dữ liệu mẫu")
    print("   python main.py                 ← khởi động backend\n")