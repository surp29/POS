#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - MIGRATE: tich hop voi Ecommerce Backend
=================================================
Them cot `source`/`external_ref` vao bang `orders` (ALTER — Base.metadata.create_all()
khong dong bo cot moi cho bang da ton tai, giong ly do co script
migrate_add_customer_id.py). Idempotent — an toan chay lai nhieu lan.

Bang `integration_events` la bang MOI hoan toan nen KHONG can trong script nay —
Base.metadata.create_all() (chay tu dong khi start backend, xem app/main.py
startup_event()) da tu tao no.

Su dung:
    cd Backend
    python migrate_add_integration_tables.py
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine

STATEMENTS = [
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'pos'",
    "CREATE INDEX IF NOT EXISTS ix_orders_source ON orders (source)",

    # Postgres UNIQUE index cho phep nhieu NULL (khong coi NULL = NULL la trung),
    # nen khong can partial index — khop dung voi Column(unique=True, nullable=True)
    # trong app/models.py.
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS external_ref VARCHAR(100)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_external_ref ON orders (external_ref)",

    # Don da ton tai truoc khi co migration nay deu la don tao tai quay
    "UPDATE orders SET source = 'pos' WHERE source IS NULL",
]

if __name__ == "__main__":
    print("=" * 60)
    print("  MIGRATE: orders.source / orders.external_ref (tich hop Ecommerce)")
    print("=" * 60)
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"\n> {stmt}")
            conn.execute(text(stmt))
    print("\n✅ Hoàn tất.")
