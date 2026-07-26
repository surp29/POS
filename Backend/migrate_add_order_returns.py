#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - MIGRATE: tra hang cho don ecommerce
=============================================
Them cot `order_items.returned_qty` (ALTER — Base.metadata.create_all() khong
dong bo cot moi cho bang da ton tai). Bang `order_returns` la bang MOI hoan
toan nen KHONG can trong script nay — create_all() (chay tu dong khi start
backend, xem app/main.py startup_event()) da tu tao no. Idempotent — an toan
chay lai nhieu lan.

Su dung:
    cd Backend
    python migrate_add_order_returns.py
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine

STATEMENTS = [
    "ALTER TABLE order_items ADD COLUMN IF NOT EXISTS returned_qty INTEGER NOT NULL DEFAULT 0",
]

if __name__ == "__main__":
    print("=" * 60)
    print("  MIGRATE: order_items.returned_qty (tra hang Ecommerce)")
    print("=" * 60)
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"\n> {stmt}")
            conn.execute(text(stmt))
    print("\n✅ Hoàn tất.")
