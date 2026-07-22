"""
Regression test cho bug: product_groups.py truoc day tinh "id" tu vi tri trong 1
query DISTINCT products.nhom_sp moi lan goi (khong on dinh giua cac lan goi), va
create/update/delete khong thao tac tren du lieu that (create tra ve id gia, khong
luu gi; delete/update doan sai nhom neu thu tu DISTINCT doi giua 2 lan goi).
"""


def test_group_list_ids_are_stable_across_calls(client, auth_headers):
    r1 = client.post("/api/product-groups/", json={"ten_nhom": "Nhóm A"}, headers=auth_headers)
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/product-groups/", json={"ten_nhom": "Nhóm B"}, headers=auth_headers)
    assert r2.status_code == 200, r2.text

    list1 = client.get("/api/product-groups/").json()["groups"]
    list2 = client.get("/api/product-groups/").json()["groups"]

    ids1 = {g["ten_nhom"]: g["id"] for g in list1}
    ids2 = {g["ten_nhom"]: g["id"] for g in list2}
    assert ids1 == ids2, f"ID nhóm không ổn định giữa 2 lần gọi: {ids1} != {ids2}"
    assert ids1["Nhóm A"] != ids1["Nhóm B"]


def test_create_group_actually_persists(client, auth_headers):
    resp = client.post("/api/product-groups/", json={"ten_nhom": "Nhóm Thật"}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    group_id = resp.json()["id"]
    assert group_id != 999, "create_product_group không còn được trả về id giả cố định"

    groups = client.get("/api/product-groups/").json()["groups"]
    assert any(g["id"] == group_id and g["ten_nhom"] == "Nhóm Thật" for g in groups)

    # Gọi lại với cùng tên phải trả về đúng id cũ (idempotent), không tạo trùng
    resp2 = client.post("/api/product-groups/", json={"ten_nhom": "Nhóm Thật"}, headers=auth_headers)
    assert resp2.json()["id"] == group_id


def test_rename_and_delete_group_by_stable_id(client, auth_headers):
    create_resp = client.post("/api/product-groups/", json={"ten_nhom": "Linh kiện test"}, headers=auth_headers)
    group_id = create_resp.json()["id"]

    product_resp = client.post(
        "/api/products/",
        data={"code": "TESTGRP01", "name": "SP nhóm test", "group": "Linh kiện test", "price": "1000"},
    )
    assert product_resp.status_code == 200, product_resp.text
    product_id = product_resp.json()["id"]

    # Đổi tên nhóm qua id thật — sản phẩm trong nhóm phải theo tên mới
    rename_resp = client.put(
        f"/api/product-groups/{group_id}",
        json={"ten_nhom": "Linh kiện đã đổi tên"},
    )
    assert rename_resp.status_code == 200, rename_resp.text
    assert rename_resp.json()["updated_count"] == 1

    product = client.get(f"/api/products/{product_id}").json()
    assert product["nhom_sp"] == "Linh kiện đã đổi tên"

    # Xóa nhóm qua id thật — sản phẩm trong nhóm bị xóa theo (đúng hành vi cũ),
    # nhưng lần này dựa trên id ổn định thay vì đoán theo vị trí.
    delete_resp = client.delete(f"/api/product-groups/{group_id}", headers=auth_headers)
    assert delete_resp.status_code == 200, delete_resp.text
    assert delete_resp.json()["deleted_count"] == 1

    assert client.get(f"/api/products/{product_id}").status_code == 404
    groups_after = client.get("/api/product-groups/").json()["groups"]
    assert not any(g["id"] == group_id for g in groups_after)
