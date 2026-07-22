"""
Regression test cho bug: cong no khach hang truoc day khop theo Invoice.nguoi_mua
(text) thay vi customer_id (FK that). 2 hoa don cung 1 khach nhung ten ghi khac nhau
(sai chinh ta/khac cach viet) truoc day se bi tach thanh 2 dong cong no rieng biet
thay vi cong don dung vao 1 khach.
"""


def _create_invoice(client, auth_headers, **overrides):
    payload = {
        "so_hd": "TEST-HD-DEFAULT",
        "ngay_hd": "2026-01-01",
        "nguoi_mua": "Khách test",
        "tong_tien": 100000,
        "trang_thai": "Chưa thanh toán",
    }
    payload.update(overrides)
    resp = client.post("/api/invoices/", json=payload, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_debt_merges_by_customer_id_despite_name_variation(client, auth_headers, sample_account):
    _create_invoice(
        client, auth_headers,
        so_hd="TEST-HD-001", ngay_hd="2026-01-01",
        nguoi_mua=sample_account.ten_tk, customer_id=sample_account.id,
        tong_tien=100000, trang_thai="Chưa thanh toán",
    )
    _create_invoice(
        client, auth_headers,
        so_hd="TEST-HD-002", ngay_hd="2026-01-02",
        nguoi_mua="nguyen van test",  # co tinh ghi khac accents/case so voi account
        customer_id=sample_account.id,
        tong_tien=50000, trang_thai="Chưa thanh toán",
    )

    resp = client.get("/api/reports/debts")
    assert resp.status_code == 200, resp.text
    debts = resp.json()

    matching = [d for d in debts if d.get("customerId") == sample_account.id]
    assert len(matching) == 1, f"Kỳ vọng 1 dòng công nợ gộp theo customer_id, nhận được: {matching}"
    assert matching[0]["totalDebt"] == 150000
    assert matching[0]["invoiceCount"] == 2


def test_debt_without_customer_id_falls_back_to_name(client, auth_headers):
    """Hóa đơn không có customer_id (khách vãng lai / dữ liệu cũ) vẫn hoạt động như
    trước — gộp theo tên, không bị lỗi vì thiếu customer_id."""
    _create_invoice(
        client, auth_headers,
        so_hd="TEST-HD-003", ngay_hd="2026-01-03",
        nguoi_mua="Khách vãng lai", customer_id=None,
        tong_tien=20000, trang_thai="Chưa thanh toán",
    )

    resp = client.get("/api/reports/debts")
    assert resp.status_code == 200, resp.text
    debts = resp.json()
    matching = [d for d in debts if d.get("customerName") == "Khách vãng lai"]
    assert len(matching) == 1
    assert matching[0]["totalDebt"] == 20000


def test_debt_merges_legacy_name_only_row_with_new_customer_id_row(client, auth_headers, sample_account):
    """Kich ban chuyen tiep thuc te: 1 hoa don CU (chua co customer_id, chi co ten
    khop dung voi account) va 1 hoa don MOI (co customer_id) cua CUNG 1 khach phai gop
    chung vao 1 dong duy nhat — khong duoc ra 2 dong cung customerId."""
    _create_invoice(
        client, auth_headers,
        so_hd="TEST-HD-006", ngay_hd="2026-01-06",
        nguoi_mua=sample_account.ten_tk, customer_id=None,  # hoa don "cu", chua gan id
        tong_tien=40000, trang_thai="Chưa thanh toán",
    )
    _create_invoice(
        client, auth_headers,
        so_hd="TEST-HD-007", ngay_hd="2026-01-07",
        nguoi_mua=sample_account.ten_tk, customer_id=sample_account.id,  # hoa don "moi"
        tong_tien=60000, trang_thai="Chưa thanh toán",
    )

    resp = client.get("/api/reports/debts")
    assert resp.status_code == 200, resp.text
    debts = resp.json()

    matching = [d for d in debts if d.get("customerId") == sample_account.id]
    assert len(matching) == 1, f"Kỳ vọng gộp chung 1 dòng, nhận được: {matching}"
    assert matching[0]["totalDebt"] == 100000
    assert matching[0]["invoiceCount"] == 2


def test_leaderboard_merges_paid_invoices_by_customer_id(client, auth_headers, sample_account):
    _create_invoice(
        client, auth_headers,
        so_hd="TEST-HD-004", ngay_hd="2026-01-04",
        nguoi_mua=sample_account.ten_tk, customer_id=sample_account.id,
        tong_tien=300000, trang_thai="Đã thanh toán",
    )
    _create_invoice(
        client, auth_headers,
        so_hd="TEST-HD-005", ngay_hd="2026-01-05",
        nguoi_mua="NGUYEN VAN TEST",  # cung khach, ghi hoa toan bo
        customer_id=sample_account.id,
        tong_tien=200000, trang_thai="Đã thanh toán",
    )

    resp = client.get("/api/reports/leaderboard")
    assert resp.status_code == 200, resp.text
    board = resp.json()

    matching = [row for row in board if row.get("customerId") == sample_account.id]
    assert len(matching) == 1, f"Kỳ vọng 1 dòng leaderboard gộp theo customer_id, nhận được: {matching}"
    assert matching[0]["totalAmount"] == 500000
    assert matching[0]["invoiceCount"] == 2
