"""
Regression test cho bug: POST /api/chatbot/create-order (tinh nang "dat lai hang"
cua Thu ky ao AI) truoc day tao Order/OrderItem TRUC TIEP, khong di qua
create_order_service — khong khoa dong Product (.with_for_update()), khong
kiem tra ton kho, va khong tru so_luong. Hau qua: 1) co the dat vuot xa ton
kho thuc te ma khong bi tu choi, 2) so_luong trong DB khong bao gio phan anh
dung cac don da dat qua kenh chatbot nay (khac voi POST /api/orders/ da tru
kho dung tu truoc).

Da xac nhan bang 2 request POST /api/chatbot/create-order DONG THOI THAT
(khong qua pytest — TestClient dung chung 1 session nen khong mo phong dung
concurrency o muc DB) nham vao 1 san pham ton kho = 1:

    truoc khi sua: request nao cung tra ve success, so_luong khong doi
    sau khi sua:   1 request success va tru dung so_luong, request con lai
                   bi tu choi 400 "khong du hang"

Test duoi day xac nhan lai logic kiem tra + tru ton kho (chay TUAN TU, khong
phai concurrency) hoat dong dung sau khi them .with_for_update() + tru kho —
dam bao sua khoa khong lam gay logic tao don goc.
"""


def test_reorder_rejects_when_stock_insufficient(client, auth_headers, sample_product, db):
    sample_product.so_luong = 1
    db.commit()

    resp1 = client.post(
        "/api/chatbot/create-order",
        json={"product_code": sample_product.ma_sp, "quantity": 1},
        headers=auth_headers,
    )
    assert resp1.status_code == 200, resp1.text

    db.refresh(sample_product)
    assert sample_product.so_luong == 0, "Don thanh cong phai tru dung so_luong"

    # Kho da het — don thu 2 phai bi tu choi ro rang, khong duoc "thanh cong"
    # tren so lieu am/vuot ton kho (day chinh la bug da fix).
    resp2 = client.post(
        "/api/chatbot/create-order",
        json={"product_code": sample_product.ma_sp, "quantity": 1},
        headers=auth_headers,
    )
    assert resp2.status_code == 400, resp2.text
    assert "không đủ" in resp2.json()["error"]

    db.refresh(sample_product)
    assert sample_product.so_luong == 0, "Request bi tu choi khong duoc phep tru them kho"


def test_reorder_succeeds_and_decrements_stock(client, auth_headers, sample_product, db):
    sample_product.so_luong = 10
    db.commit()

    resp = client.post(
        "/api/chatbot/create-order",
        json={"product_code": sample_product.ma_sp, "quantity": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True

    db.refresh(sample_product)
    assert sample_product.so_luong == 7
