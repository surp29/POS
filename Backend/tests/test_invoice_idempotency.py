"""
Regression test cho bug: bam "Xac nhan thanh toan" 2 lan cho CUNG 1 giao dich
(mang lag khien request truoc tuong nhu that bai, hoac double-click) truoc day co
the tao ra 2 hoa don rieng biet — tinh tien 2 lan cho 1 lan mua. Da xac nhan bang
2 request POST /api/invoices/ dong thoi that (khong phai gia dinh) truoc khi sua.
"""


def test_duplicate_idempotency_key_returns_existing_invoice_not_a_new_one(client, auth_headers):
    key = "test-idem-key-001"
    payload = {
        "so_hd": "IDEM-HD-001",
        "ngay_hd": "2026-01-01",
        "nguoi_mua": "Khách idempotency",
        "idempotency_key": key,
        "tong_tien": 50000,
        "trang_thai": "Đã thanh toán",
    }

    resp1 = client.post("/api/invoices/", json=payload, headers=auth_headers)
    assert resp1.status_code == 200, resp1.text
    first_id = resp1.json()["id"]

    # Gia lap bam lai (client gui lai idempotency_key giong het, vd so_hd cung co
    # the khac neu client da lay so hoa don moi trong luc cho) — van phai tra ve
    # DUNG hoa don da tao, khong tao them cai moi.
    payload_retry = dict(payload, so_hd="IDEM-HD-001-RETRY")
    resp2 = client.post("/api/invoices/", json=payload_retry, headers=auth_headers)
    assert resp2.status_code == 200, resp2.text
    second_id = resp2.json()["id"]

    assert second_id == first_id, "Ky gui lai phai tra ve hoa don cu, khong tao hoa don moi"
    assert resp2.json().get("duplicate") is True

    resp_list = client.get("/api/invoices/", headers=auth_headers)
    matching = [i for i in resp_list.json() if i.get("so_hd") in ("IDEM-HD-001", "IDEM-HD-001-RETRY")]
    assert len(matching) == 1, f"Phai chi co dung 1 hoa don duoc tao, thay vi: {matching}"


def test_different_idempotency_keys_create_separate_invoices(client, auth_headers):
    """2 giao dich THAT SU khac nhau (key khac nhau) van phai tao 2 hoa don rieng —
    co che nay khong duoc lam gop nham cac don hang khac nhau lai voi nhau."""
    payload_a = {
        "so_hd": "IDEM-HD-A", "ngay_hd": "2026-01-01", "nguoi_mua": "Khách A",
        "idempotency_key": "key-a", "tong_tien": 10000, "trang_thai": "Đã thanh toán",
    }
    payload_b = {
        "so_hd": "IDEM-HD-B", "ngay_hd": "2026-01-01", "nguoi_mua": "Khách B",
        "idempotency_key": "key-b", "tong_tien": 20000, "trang_thai": "Đã thanh toán",
    }
    resp_a = client.post("/api/invoices/", json=payload_a, headers=auth_headers)
    resp_b = client.post("/api/invoices/", json=payload_b, headers=auth_headers)
    assert resp_a.status_code == 200 and resp_b.status_code == 200
    assert resp_a.json()["id"] != resp_b.json()["id"]


def test_invoice_without_idempotency_key_still_works(client, auth_headers):
    """Hoa don khong gui idempotency_key (client cu / kenh khac) van tao binh
    thuong nhu truoc — field nay hoan toan optional."""
    payload = {
        "so_hd": "IDEM-HD-NOKEY", "ngay_hd": "2026-01-01", "nguoi_mua": "Khách không key",
        "tong_tien": 30000, "trang_thai": "Đã thanh toán",
    }
    resp = client.post("/api/invoices/", json=payload, headers=auth_headers)
    assert resp.status_code == 200, resp.text
