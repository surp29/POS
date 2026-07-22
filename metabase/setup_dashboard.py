#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dung script nay de dung lai dashboard Metabase "PosPos - Bao cao doanh thu" tren 1
instance Metabase da co san tai khoan admin (khong tao instance moi tu dau).

Yeu cau: da chay `dbt run` xong (cac bang analytics.mart_* da ton tai trong posdb),
va da dang nhap Metabase lan dau (tao tai khoan owner qua UI http://localhost:3000).

Su dung:
    pip install requests
    METABASE_URL=http://localhost:3000 \
    METABASE_USER=admin@example.com \
    METABASE_PASSWORD=xxxx \
    python setup_dashboard.py
"""
import os
import sys
import requests

MB_URL = os.getenv("METABASE_URL", "http://localhost:3000")
MB_USER = os.getenv("METABASE_USER")
MB_PASSWORD = os.getenv("METABASE_PASSWORD")

if not MB_USER or not MB_PASSWORD:
    print("Thieu METABASE_USER / METABASE_PASSWORD trong bien moi truong.")
    sys.exit(1)

session = requests.Session()

resp = session.post(f"{MB_URL}/api/session", json={"username": MB_USER, "password": MB_PASSWORD})
resp.raise_for_status()
print("Dang nhap Metabase thanh cong.")

# 1. Tim hoac tao database connection toi posdb
databases = session.get(f"{MB_URL}/api/database").json()["data"]
db = next((d for d in databases if d.get("name") == "PosPos (posdb)"), None)
if db is None:
    resp = session.post(f"{MB_URL}/api/database", json={
        "engine": "postgres",
        "name": "PosPos (posdb)",
        "details": {
            "host": "postgres", "port": 5432, "dbname": "posdb",
            "user": "posuser", "password": "pospassword",
            "ssl": False, "tunnel-enabled": False,
        },
        "is_full_sync": True,
    })
    resp.raise_for_status()
    db = resp.json()
    print(f"Da tao database connection id={db['id']}")
else:
    print(f"Database connection da ton tai id={db['id']}")

db_id = db["id"]
session.post(f"{MB_URL}/api/database/{db_id}/sync_schema")

CARDS = [
    {
        "name": "Tong doanh thu (da thanh toan)",
        "query": "select sum(revenue) as tong_doanh_thu from analytics.mart_revenue_daily",
        "display": "scalar",
        "viz": {},
    },
    {
        "name": "Ty le doanh thu tu khach chua dinh danh (%)",
        "query": (
            "select round((100.0 * sum(case when customer_id = -1 then total_revenue "
            "else 0 end) / nullif(sum(total_revenue),0))::numeric, 1) as ty_le_khach_le_pct "
            "from analytics.mart_customer_ranking"
        ),
        "display": "scalar",
        "viz": {},
    },
    {
        "name": "Doanh thu theo ngay",
        "query": "select date_key, revenue, invoice_count from analytics.mart_revenue_daily order by date_key",
        "display": "line",
        "viz": {"graph.dimensions": ["date_key"], "graph.metrics": ["revenue"]},
    },
    {
        "name": "Doanh thu theo san pham",
        "query": "select product_name, revenue, units_sold from analytics.mart_revenue_by_product order by revenue desc",
        "display": "bar",
        "viz": {"graph.dimensions": ["product_name"], "graph.metrics": ["revenue"]},
    },
    {
        "name": "Xep hang khach hang theo doanh thu",
        "query": (
            "select customer_name, invoice_count, total_revenue, avg_invoice_value "
            "from analytics.mart_customer_ranking order by total_revenue desc"
        ),
        "display": "table",
        "viz": {},
    },
]

existing_cards = session.get(f"{MB_URL}/api/card").json()
card_ids = {}
for spec in CARDS:
    found = next((c for c in existing_cards if c["name"] == spec["name"]), None)
    if found:
        session.put(f"{MB_URL}/api/card/{found['id']}", json={
            "dataset_query": {"type": "native", "native": {"query": spec["query"]}, "database": db_id},
        })
        card_ids[spec["name"]] = found["id"]
        print(f"Da cap nhat card '{spec['name']}' id={found['id']}")
    else:
        resp = session.post(f"{MB_URL}/api/card", json={
            "name": spec["name"],
            "dataset_query": {"type": "native", "native": {"query": spec["query"]}, "database": db_id},
            "display": spec["display"],
            "visualization_settings": spec["viz"],
            "collection_id": None,
        })
        resp.raise_for_status()
        card_ids[spec["name"]] = resp.json()["id"]
        print(f"Da tao card '{spec['name']}' id={card_ids[spec['name']]}")

# 2. Tim hoac tao dashboard
dashboards = session.get(f"{MB_URL}/api/dashboard").json()
dash = next((d for d in dashboards if d["name"] == "PosPos - Bao cao doanh thu"), None)
if dash is None:
    resp = session.post(f"{MB_URL}/api/dashboard", json={
        "name": "PosPos - Bao cao doanh thu",
        "description": "Dashboard dung tren cac bang analytics.mart_* (dbt star schema)",
        "collection_id": None,
    })
    resp.raise_for_status()
    dash = resp.json()
    print(f"Da tao dashboard id={dash['id']}")
else:
    print(f"Dashboard da ton tai id={dash['id']}")

dash_id = dash["id"]

layout = [
    ("Tong doanh thu (da thanh toan)", 0, 0, 6, 3),
    ("Ty le doanh thu tu khach chua dinh danh (%)", 0, 6, 6, 3),
    ("Doanh thu theo ngay", 3, 0, 12, 6),
    ("Doanh thu theo san pham", 9, 0, 9, 6),
    ("Xep hang khach hang theo doanh thu", 9, 9, 9, 6),
]

dashcards = []
for i, (name, row, col, size_x, size_y) in enumerate(layout, start=1):
    dashcards.append({
        "id": -i,
        "card_id": card_ids[name],
        "row": row, "col": col, "size_x": size_x, "size_y": size_y,
    })

resp = session.put(f"{MB_URL}/api/dashboard/{dash_id}", json={"dashcards": dashcards})
resp.raise_for_status()

print(f"\nHoan tat. Mo dashboard tai: {MB_URL}/dashboard/{dash_id}")
