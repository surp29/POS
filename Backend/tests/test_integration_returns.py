"""
Test cho POST /api/integration/orders/{id}/returns — hoan kho TUNG PHAN cho don
ecommerce da giao (khac .../cancel: khong huy ca don, don giu nguyen trang thai).

3 tinh chat bat buoc:
  1. Idempotent theo return_ref — retry khong hoan kho 2 lan cho cung 1 lot tra.
  2. Tu choi (409) khi tra vuot so luong da mua (chong lam dung de "tao" ton kho ao).
  3. Tra hang KHONG lam thay doi trang thai don (khac voi cancel).
"""
from datetime import date

from app.config import Config
from app import models


def _set_integration_key(key="test-integration-key"):
    Config.INTEGRATION_API_KEY = key
    return {"X-API-Key": key}


def _create_ecommerce_order(client, headers, sample_product, external_ref, quantity=5, unit_price=10000):
    resp = client.post("/api/integration/orders", json={
        "external_ref": external_ref,
        "customer": {"name": "Khach Tra Hang", "email": "trahang@example.com"},
        "items": [{"sku": sample_product.ma_sp, "quantity": quantity, "unit_price": unit_price}],
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_return_items_restocks_and_records_refund_amount(client, db, sample_product):
    headers = _set_integration_key()
    initial_qty = sample_product.so_luong
    order_id = _create_ecommerce_order(client, headers, sample_product, "ECOM-R001", quantity=5, unit_price=10000)

    db.expire_all()
    qty_after_order = db.get(models.Product, sample_product.id).so_luong
    assert qty_after_order == initial_qty - 5

    resp = client.post(f"/api/integration/orders/{order_id}/returns", json={
        "return_ref": "RET-R001",
        "items": [{"sku": sample_product.ma_sp, "quantity": 2}],
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] is True
    assert body["refund_amount"] == 2 * 10000

    db.expire_all()
    assert db.get(models.Product, sample_product.id).so_luong == qty_after_order + 2

    # Đơn vẫn giữ nguyên trạng thái — trả hàng KHÔNG hủy đơn (khác /cancel).
    order = db.get(models.Order, order_id)
    assert order.trang_thai != "da_huy"


def test_return_idempotent_retry_does_not_double_restock(client, db, sample_product):
    headers = _set_integration_key()
    order_id = _create_ecommerce_order(client, headers, sample_product, "ECOM-R002", quantity=5)

    payload = {"return_ref": "RET-R002", "items": [{"sku": sample_product.ma_sp, "quantity": 2}]}
    first = client.post(f"/api/integration/orders/{order_id}/returns", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["created"] is True

    db.expire_all()
    qty_after_first_return = db.get(models.Product, sample_product.id).so_luong

    second = client.post(f"/api/integration/orders/{order_id}/returns", json=payload, headers=headers)
    assert second.status_code == 200
    body2 = second.json()
    assert body2["created"] is False
    assert body2["id"] == first.json()["id"]

    db.expire_all()
    # Khong hoan kho lan 2.
    assert db.get(models.Product, sample_product.id).so_luong == qty_after_first_return


def test_return_more_than_purchased_returns_409_and_does_not_touch_stock(client, db, sample_product):
    headers = _set_integration_key()
    order_id = _create_ecommerce_order(client, headers, sample_product, "ECOM-R003", quantity=3)

    db.expire_all()
    qty_before_return = db.get(models.Product, sample_product.id).so_luong

    resp = client.post(f"/api/integration/orders/{order_id}/returns", json={
        "return_ref": "RET-R003",
        "items": [{"sku": sample_product.ma_sp, "quantity": 4}],  # > 3 da mua
    }, headers=headers)
    assert resp.status_code == 409

    db.expire_all()
    assert db.get(models.Product, sample_product.id).so_luong == qty_before_return
    assert db.query(models.OrderReturn).filter(models.OrderReturn.return_ref == "RET-R003").count() == 0


def test_return_exceeding_remaining_after_partial_return_returns_409(client, db, sample_product):
    """Tra 2 lan hop le (tong = 3, dung bang so luong da mua), lan 3 tra them 1 ->
    vuot phan con lai (0) -> 409, du tung lan rieng le deu <= so_luong goc."""
    headers = _set_integration_key()
    order_id = _create_ecommerce_order(client, headers, sample_product, "ECOM-R004", quantity=3)

    first = client.post(f"/api/integration/orders/{order_id}/returns", json={
        "return_ref": "RET-R004-A", "items": [{"sku": sample_product.ma_sp, "quantity": 2}],
    }, headers=headers)
    assert first.status_code == 200

    second = client.post(f"/api/integration/orders/{order_id}/returns", json={
        "return_ref": "RET-R004-B", "items": [{"sku": sample_product.ma_sp, "quantity": 1}],
    }, headers=headers)
    assert second.status_code == 200  # 2 + 1 = 3, vua du

    third = client.post(f"/api/integration/orders/{order_id}/returns", json={
        "return_ref": "RET-R004-C", "items": [{"sku": sample_product.ma_sp, "quantity": 1}],
    }, headers=headers)
    assert third.status_code == 409  # da tra het, khong con gi de tra


def test_return_unknown_sku_returns_404(client, db, sample_product):
    headers = _set_integration_key()
    order_id = _create_ecommerce_order(client, headers, sample_product, "ECOM-R005", quantity=1)

    resp = client.post(f"/api/integration/orders/{order_id}/returns", json={
        "return_ref": "RET-R005",
        "items": [{"sku": "SKU-KHONG-TON-TAI", "quantity": 1}],
    }, headers=headers)
    assert resp.status_code == 404


def test_return_for_non_ecommerce_order_returns_404(client, db, sample_product):
    """Đơn tạo tại quầy (source='pos', mặc định) — không được phép trả hàng qua
    integration API này (chỉ dành cho đơn có source='ecommerce')."""
    pos_order = models.Order(
        ma_don_hang="POS-LOCAL-001", thong_tin_kh="Khach Tai Quay",
        ngay_tao=date.today(), so_luong=1, tong_tien=10000.0,
    )
    db.add(pos_order)
    db.commit()
    db.refresh(pos_order)

    headers = _set_integration_key()
    resp = client.post(f"/api/integration/orders/{pos_order.id}/returns", json={
        "return_ref": "RET-R006",
        "items": [{"sku": sample_product.ma_sp, "quantity": 1}],
    }, headers=headers)
    assert resp.status_code == 404
