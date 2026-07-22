"""
Test fixtures — dung 1 database Postgres RIENG (posdb_test), khong dung chung voi
posdb (du lieu dev/demo da seed cho dbt/Metabase). Tao 1 lan:

    docker exec pos_postgres psql -U posuser -d postgres -c "CREATE DATABASE posdb_test;"

Chay test (tu trong container backend, de co dung network toi 'postgres'):

    docker compose exec backend pytest tests/ -v

TestClient KHONG duoc dung trong "with" block co chu y — startup_event() cua app
(tao admin, auto-seed demo data) chi chay khi lifespan duoc kich hoat qua "with", va
no dung SessionLocal that (tro toi posdb, KHONG phai posdb_test qua get_db override).
Giu TestClient(app) o dang plain instance de tranh vo tinh ghi vao DB dev that.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://posuser:pospassword@postgres:5432/posdb_test",
)

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from app.database import Base, get_db
from app.main import app
from app.config import Config
import app.models as models  # noqa: F401 — dam bao tat ca model duoc dang ky vao Base


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    from werkzeug.security import generate_password_hash
    user = models.User(
        username="test_admin",
        password=generate_password_hash("test123"),
        name="Test Admin",
        position="Admin",
        department="System",
        status=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(admin_user):
    token = jwt.encode({"sub": admin_user.username}, Config.JWT_SECRET_KEY, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_account(db):
    account = models.Account(
        ten_tk="Nguyễn Văn Test",
        ma_khach_hang="TESTKH001",
        email="test@example.com",
        so_dt="0900000000",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def sample_product(db):
    product = models.Product(
        ma_sp="TESTSP001",
        ten_sp="Sản phẩm Test",
        so_luong=100,
        gia_ban=10000.0,
        trang_thai="active",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
