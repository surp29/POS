"""
Regression test cho bug: tao don hang (POST /api/orders/) truoc day doc/ghi
Product.so_luong KHONG khoa dong (khong co .with_for_update()), khac voi
invoices.py da lam dung tu truoc. Da xac nhan bang 2 request POST /api/orders/
DONG THOI THAT (khong qua pytest — TestClient dung chung 1 session nen khong mo
phong dung concurrency o muc DB) nham vao 1 san pham ton kho = 1:

    truoc khi sua: ca 2 request deu tra ve success (ban vuot ton kho — oversell)
    sau khi sua:   1 request success, request con lai bi tu choi 400 "khong du hang"

Xem lai bang cach chay docker-compose that roi ban 2 curl dong thoi (dbt/README.md
va lich su commit co ghi chi tiet). Test duoi day xac nhan lai phan logic kiem tra
ton kho (chay TUAN TU, khong phai concurrency) van dung sau khi sua — dam bao
sua khoa khong lam gay logic goc.
"""


def test_order_rejects_when_stock_insufficient(client, auth_headers, sample_product, db):
    from app import models
    sample_product.so_luong = 1
    db.commit()

    resp1 = client.post(
        "/api/orders/",
        json={
            "ma_don_hang": "LOCK-TEST-ORDER-1",
            "thong_tin_kh": "Khách A",
            "sp_banggia": sample_product.ma_sp,
            "ngay_tao": "2026-01-01",
            "so_luong": 1,
            "trang_thai": "cho_xu_ly",
        },
        headers=auth_headers,
    )
    assert resp1.status_code == 200, resp1.text

    # Kho da het (0) — don thu 2 phai bi tu choi ro rang, khong duoc "thanh cong"
    # tren so lieu am/vuot ton kho.
    resp2 = client.post(
        "/api/orders/",
        json={
            "ma_don_hang": "LOCK-TEST-ORDER-2",
            "thong_tin_kh": "Khách B",
            "sp_banggia": sample_product.ma_sp,
            "ngay_tao": "2026-01-01",
            "so_luong": 1,
            "trang_thai": "cho_xu_ly",
        },
        headers=auth_headers,
    )
    assert resp2.status_code == 400, resp2.text
    # main.py override HTTPException handler tra ve {"error": ...}, khong phai
    # {"detail": ...} mac dinh cua FastAPI.
    assert "không đủ" in resp2.json()["error"]

    db.refresh(sample_product)
    assert sample_product.so_luong == 0
