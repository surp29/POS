"""
Test cho POST /api/integration/orders — endpoint duy nhat Ecommerce Backend goi
vao de tao don hang ben POS.

3 tinh chat bat buoc phai dung (moi tinh chat la 1 "van de thuc te TMDT" cu the):
  1. Idempotent theo external_ref — retry khong tao don trung, khong tru kho 2 lan.
  2. Row lock + tu choi (409) khi khong du hang — khong ban vuot ton kho.
  3. Khop khach hang theo email/phone (khong theo ten text) — tranh lap lai bug
     "gop nham khach trung ten" da ghi trong README cua chinh project nay.
"""
from app.config import Config
from app import models


def _set_integration_key(key="test-integration-key"):
    Config.INTEGRATION_API_KEY = key
    return {"X-API-Key": key}


def test_missing_api_key_rejected(client, sample_product):
    _set_integration_key()
    resp = client.post("/api/integration/orders", json={
        "external_ref": "ECOM-1",
        "customer": {"name": "Khach A"},
        "items": [{"sku": sample_product.ma_sp, "quantity": 1, "unit_price": 10000}],
    })
    assert resp.status_code == 401


def test_create_order_idempotent_retry_does_not_double_deduct_stock(client, db, sample_product):
    headers = _set_integration_key()
    initial_qty = sample_product.so_luong  # chụp giá trị TRƯỚC khi gọi API — sample_product
    # va db dung chung 1 session, expire_all() sau nay se lam no phan anh gia tri MOI
    # nhat neu doc lai truc tiep tu attribute.
    payload = {
        "external_ref": "ECOM-1001",
        "customer": {"name": "Khach A", "email": "a@example.com"},
        "items": [{"sku": sample_product.ma_sp, "quantity": 5, "unit_price": 10000}],
    }

    first = client.post("/api/integration/orders", json=payload, headers=headers)
    assert first.status_code == 200, first.text
    body1 = first.json()
    assert body1["created"] is True

    db.expire_all()
    qty_after_first = db.get(models.Product, sample_product.id).so_luong
    assert qty_after_first == initial_qty - 5  # 100 -> 95

    # Retry voi CUNG external_ref (mo phong client mat ket noi giua chung, goi lai) —
    # phai tra ve dung don cu, KHONG tao don moi, KHONG tru kho lan 2.
    second = client.post("/api/integration/orders", json=payload, headers=headers)
    assert second.status_code == 200, second.text
    body2 = second.json()
    assert body2["created"] is False
    assert body2["id"] == body1["id"]

    db.expire_all()
    qty_after_retry = db.get(models.Product, sample_product.id).so_luong
    assert qty_after_retry == qty_after_first  # khong doi them lan nua

    orders_count = db.query(models.Order).filter(
        models.Order.external_ref == "ECOM-1001"
    ).count()
    assert orders_count == 1


def test_create_order_insufficient_stock_returns_409_and_does_not_touch_stock(client, db, sample_product):
    headers = _set_integration_key()
    initial_qty = sample_product.so_luong
    resp = client.post("/api/integration/orders", json={
        "external_ref": "ECOM-2001",
        "customer": {"name": "Khach B"},
        "items": [{"sku": sample_product.ma_sp, "quantity": 999, "unit_price": 10000}],
    }, headers=headers)
    assert resp.status_code == 409

    db.expire_all()
    assert db.get(models.Product, sample_product.id).so_luong == initial_qty

    assert db.query(models.Order).filter(models.Order.external_ref == "ECOM-2001").count() == 0


def test_create_order_matches_existing_customer_by_email_not_by_name(client, db, sample_product, sample_account):
    """sample_account co email test@example.com, ten 'Nguyễn Văn Test'. Don ecommerce
    gui ten KHAC nhung CUNG email -> phai duoc gan vao dung account do, khong tao
    account moi (day chinh la loi POS tung mac phai khi so khop theo ten text)."""
    headers = _set_integration_key()
    resp = client.post("/api/integration/orders", json={
        "external_ref": "ECOM-3001",
        "customer": {"name": "Ten Khac Hoan Toan", "email": sample_account.email},
        "items": [{"sku": sample_product.ma_sp, "quantity": 1, "unit_price": 10000}],
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["customer_id"] == sample_account.id

    accounts_with_email = db.query(models.Account).filter(
        models.Account.email == sample_account.email
    ).count()
    assert accounts_with_email == 1  # khong tao account trung


def test_create_order_sets_source_ecommerce(client, db, sample_product):
    headers = _set_integration_key()
    resp = client.post("/api/integration/orders", json={
        "external_ref": "ECOM-4001",
        "customer": {"name": "Khach C"},
        "items": [{"sku": sample_product.ma_sp, "quantity": 1, "unit_price": 10000}],
    }, headers=headers)
    assert resp.status_code == 200
    order = db.get(models.Order, resp.json()["id"])
    assert order.source == "ecommerce"
    assert order.external_ref == "ECOM-4001"


def test_get_integration_order_returns_current_state(client, db, sample_product):
    headers = _set_integration_key()
    create_resp = client.post("/api/integration/orders", json={
        "external_ref": "ECOM-6001",
        "customer": {"name": "Khach E"},
        "items": [{"sku": sample_product.ma_sp, "quantity": 2, "unit_price": 10000}],
    }, headers=headers)
    order_id = create_resp.json()["id"]

    resp = client.get(f"/api/integration/orders/{order_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == order_id
    assert body["external_ref"] == "ECOM-6001"
    assert body["source"] == "ecommerce"
    assert body["tong_tien"] == 20000
    assert len(body["items"]) == 1
    assert body["items"][0]["sku"] == sample_product.ma_sp
    assert body["items"][0]["quantity"] == 2
    assert body["items"][0]["returned_qty"] == 0


def test_get_integration_order_nonexistent_returns_404(client):
    headers = _set_integration_key()
    resp = client.get("/api/integration/orders/999999", headers=headers)
    assert resp.status_code == 404


def test_get_integration_order_for_pos_local_order_returns_404(client, db):
    """Đơn tạo tại quầy (source='pos', mặc định) không thuộc phạm vi integration
    API — không được lộ ra qua bề mặt này (chỉ đơn 'ecommerce' mới hợp lệ)."""
    from datetime import date
    pos_order = models.Order(
        ma_don_hang="POS-LOCAL-GET-001", thong_tin_kh="Khach Tai Quay",
        ngay_tao=date.today(), so_luong=1, tong_tien=10000.0,
    )
    db.add(pos_order)
    db.commit()
    db.refresh(pos_order)

    headers = _set_integration_key()
    resp = client.get(f"/api/integration/orders/{pos_order.id}", headers=headers)
    assert resp.status_code == 404


def test_cancel_integration_order_restocks(client, db, sample_product):
    headers = _set_integration_key()
    initial_qty = sample_product.so_luong
    create_resp = client.post("/api/integration/orders", json={
        "external_ref": "ECOM-5001",
        "customer": {"name": "Khach D"},
        "items": [{"sku": sample_product.ma_sp, "quantity": 3, "unit_price": 10000}],
    }, headers=headers)
    order_id = create_resp.json()["id"]

    db.expire_all()
    qty_after_order = db.get(models.Product, sample_product.id).so_luong
    assert qty_after_order == initial_qty - 3

    cancel_resp = client.post(f"/api/integration/orders/{order_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200, cancel_resp.text

    db.expire_all()
    assert db.get(models.Product, sample_product.id).so_luong == initial_qty
    assert db.get(models.Order, order_id).trang_thai == "da_huy"
