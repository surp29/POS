import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for the application"""

    # Database — FIX: Render dùng "postgres://" nhưng SQLAlchemy cần "postgresql://"
    _db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/pos')
    SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-this-in-production')
    # Thêm: thời gian sống của access token (giây). Mặc định 30 phút.
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 1800))

    # Server
    BACKEND_PORT = int(os.getenv('BACKEND_PORT', 5001))

    # CORS
    CORS_ORIGINS = os.getenv(
        'CORS_ORIGINS',
        'http://127.0.0.1:5000,http://localhost:5000'
    ).split(',')

    # Environment
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = False

    # ── Redis (MỚI) ────────────────────────────────────────────────────────
    # Mặc định kết nối Redis local. Đổi thành biến môi trường khi deploy.
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # TTL mặc định cho từng loại cache (giây)
    CACHE_TTL_PRODUCTS = int(os.getenv('CACHE_TTL_PRODUCTS', 300))   # 5 phút
    CACHE_TTL_PRICES   = int(os.getenv('CACHE_TTL_PRICES',   300))   # 5 phút