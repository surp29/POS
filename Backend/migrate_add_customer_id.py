#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - MIGRATE: them cot customer_id vao invoices/orders
=============================================================
Project khong dung Alembic — Base.metadata.create_all() chi tao bang con thieu,
khong ALTER bang da ton tai. Script nay them cot customer_id (FK sang accounts.id)
vao 2 bang invoices/orders mot cach idempotent (an toan chay lai nhieu lan).

Su dung:
    cd Backend
    python migrate_add_customer_id.py
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine

STATEMENTS = [
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS customer_id INTEGER "
    "REFERENCES accounts(id) ON DELETE SET NULL",
    "CREATE INDEX IF NOT EXISTS ix_invoices_customer_id ON invoices (customer_id)",

    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_id INTEGER "
    "REFERENCES accounts(id) ON DELETE SET NULL",
    "CREATE INDEX IF NOT EXISTS ix_orders_customer_id ON orders (customer_id)",
]

if __name__ == "__main__":
    print("=" * 60)
    print("  MIGRATE: invoices.customer_id / orders.customer_id")
    print("=" * 60)
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"\n> {stmt}")
            conn.execute(text(stmt))
    print("\n✅ Hoàn tất.")
