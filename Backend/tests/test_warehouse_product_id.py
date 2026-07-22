"""
Regression test cho bug: warehouses.py truoc day chi luu ma_sp (text) khi tao kho
hang qua API, khong bao gio set product_id (FK that sang products.id) — chi co
create_sample_data.py la lam dung. product_id luon null tru du lieu seed san.
"""


def test_create_warehouse_sets_product_id(client, auth_headers, sample_product):
    resp = client.post(
        "/api/warehouse/",
        json={
            "ma_kho": "KHO-TEST-01",
            "ten_kho": "Kho test",
            "dia_chi": "123 Test St",
            "ma_sp": sample_product.ma_sp,
            "so_luong": 10,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    warehouse_id = resp.json()["id"]

    wh = client.get(f"/api/warehouse/{warehouse_id}").json()
    assert wh["product_id"] == sample_product.id
    assert wh["ma_sp"] == sample_product.ma_sp


def test_create_warehouse_with_unmatched_ma_sp_leaves_product_id_null(client, auth_headers):
    """ma_sp khong khop san pham nao van tao duoc kho hang binh thuong (khong chan) —
    chi khac la product_id se la null thay vi bao loi."""
    resp = client.post(
        "/api/warehouse/",
        json={
            "ma_kho": "KHO-TEST-02",
            "ten_kho": "Kho test 2",
            "dia_chi": "456 Test St",
            "ma_sp": "SP-KHONG-TON-TAI",
            "so_luong": 5,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    warehouse_id = resp.json()["id"]

    wh = client.get(f"/api/warehouse/{warehouse_id}").json()
    assert wh["product_id"] is None


def test_update_warehouse_ma_sp_reresolves_product_id(client, auth_headers, sample_product):
    create_resp = client.post(
        "/api/warehouse/",
        json={
            "ma_kho": "KHO-TEST-03",
            "ten_kho": "Kho test 3",
            "dia_chi": "789 Test St",
            "ma_sp": "SP-KHONG-TON-TAI",
            "so_luong": 1,
        },
        headers=auth_headers,
    )
    warehouse_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/warehouse/{warehouse_id}",
        json={"ma_sp": sample_product.ma_sp},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200, update_resp.text

    wh = client.get(f"/api/warehouse/{warehouse_id}").json()
    assert wh["product_id"] == sample_product.id
