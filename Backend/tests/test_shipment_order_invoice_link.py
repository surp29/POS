"""
Regression test cho bug: tao don van chuyen (POST /api/shipping/) truoc day chi luu
order_code/invoice_code (text) nhung khong bao gio set order_id/invoice_id (FK that
da co san tren model Shipment) — cung 1 kieu loi da gap o warehouses.product_id va
invoices/orders.customer_id.
"""


def test_create_shipment_resolves_order_and_invoice_fk(client, auth_headers, db):
    from app import models

    order = models.Order(
        ma_don_hang="TEST-SHIP-DH-001",
        thong_tin_kh="Khách test ship",
        ngay_tao="2026-01-01",
        so_luong=1,
        tong_tien=100000,
        trang_thai="hoan_thanh",
    )
    invoice = models.Invoice(
        so_hd="TEST-SHIP-HD-001",
        ngay_hd="2026-01-01",
        nguoi_mua="Khách test ship",
        tong_tien=100000,
        trang_thai="Đã thanh toán",
    )
    db.add(order)
    db.add(invoice)
    db.commit()
    db.refresh(order)
    db.refresh(invoice)

    resp = client.post(
        "/api/shipping/",
        json={
            "order_code": order.ma_don_hang,
            "invoice_code": invoice.so_hd,
            "receiver_name": "Khách test ship",
            "receiver_phone": "0900000000",
            "receiver_address": "123 Test St",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    shipment_id = resp.json()["id"]

    shipment = db.get(models.Shipment, shipment_id)
    assert shipment.order_id == order.id
    assert shipment.invoice_id == invoice.id

    get_resp = client.get(f"/api/shipping/{shipment_id}", headers=auth_headers)
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()["shipment"]
    assert body["order_id"] == order.id
    assert body["invoice_id"] == invoice.id


def test_create_shipment_with_unmatched_codes_leaves_fk_null(client, auth_headers):
    """ma khong khop don/hoa don nao van tao duoc, chi khac la order_id/invoice_id
    la null thay vi bao loi — dung hanh vi da ap dung cho warehouses.product_id."""
    resp = client.post(
        "/api/shipping/",
        json={
            "order_code": "DH-KHONG-TON-TAI",
            "invoice_code": "HD-KHONG-TON-TAI",
            "receiver_name": "Khách test ship 2",
            "receiver_phone": "0900000001",
            "receiver_address": "456 Test St",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    shipment_id = resp.json()["id"]

    resp2 = client.get(f"/api/shipping/{shipment_id}", headers=auth_headers)
    assert resp2.status_code == 200, resp2.text
    body = resp2.json()["shipment"]
    assert body["order_id"] is None
    assert body["invoice_id"] is None
