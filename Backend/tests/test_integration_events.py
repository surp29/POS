"""
Test cho outbox events (/api/integration/events, /api/integration/products) — co
che dong bo ma Ecommerce Backend poll dinh ky de cap nhat cache ton kho/san pham.
"""
from app.config import Config


def _headers(key="test-integration-key"):
    Config.INTEGRATION_API_KEY = key
    return {"X-API-Key": key}


def test_creating_product_emits_product_created_event(client):
    headers = _headers()
    resp = client.post(
        "/api/products/",
        data={"code": "EVT-SP-01", "name": "SP Event Test", "quantity": "20", "price": "5000"},
    )
    assert resp.status_code == 200, resp.text

    events = client.get("/api/integration/events?after_id=0", headers=headers).json()
    matching = [e for e in events if e["event_type"] == "product.created" and e["entity_id"] == str(resp.json()["id"])]
    assert len(matching) == 1
    assert matching[0]["payload"]["sku"] == "EVT-SP-01"
    assert matching[0]["payload"]["stock_qty"] == 20


def test_order_creation_emits_stock_changed_event(client, db, sample_product):
    headers = _headers()
    initial_qty = sample_product.so_luong
    resp = client.post("/api/integration/orders", json={
        "external_ref": "ECOM-EVT-1",
        "customer": {"name": "Khach Event"},
        "items": [{"sku": sample_product.ma_sp, "quantity": 2, "unit_price": 10000}],
    }, headers=headers)
    assert resp.status_code == 200, resp.text

    events = client.get("/api/integration/events?after_id=0", headers=headers).json()
    matching = [
        e for e in events
        if e["event_type"] == "stock.changed" and e["entity_id"] == str(sample_product.id)
    ]
    assert len(matching) == 1
    assert matching[0]["payload"]["stock_qty"] == initial_qty - 2


def test_events_after_id_checkpoint_excludes_older_events(client, sample_product):
    headers = _headers()
    client.post("/api/integration/orders", json={
        "external_ref": "ECOM-EVT-2",
        "customer": {"name": "Khach Event 2"},
        "items": [{"sku": sample_product.ma_sp, "quantity": 1, "unit_price": 10000}],
    }, headers=headers)

    all_events = client.get("/api/integration/events?after_id=0", headers=headers).json()
    assert len(all_events) >= 1
    last_id = all_events[-1]["id"]

    none_after = client.get(f"/api/integration/events?after_id={last_id}", headers=headers).json()
    assert none_after == []


def test_products_snapshot_returns_current_stock(client, sample_product):
    headers = _headers()
    resp = client.get("/api/integration/products?after_id=0", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    skus = {p["sku"]: p for p in body["products"]}
    assert sample_product.ma_sp in skus
    assert skus[sample_product.ma_sp]["stock_qty"] == sample_product.so_luong
