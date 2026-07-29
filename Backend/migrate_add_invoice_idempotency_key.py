#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - MIGRATE: them cot idempotency_key vao invoices
===========================================================
Chong tao hoa don trung khi client bam "xac nhan thanh toan" nhieu lan cho
CUNG 1 giao dich (mang lag, double-click...). Xem models.py / services/invoices.py
de biet cach dung.

Su dung:
    cd Backend
    python migrate_add_invoice_idempotency_key.py
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine

STATEMENTS = [
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(64)",
    # Postgres: UNIQUE cho phep nhieu dong cung la NULL (khong coi NULL = NULL),
    # nen hoa don cu / khong dung co che nay van khong bi anh huong gi.
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_invoices_idempotency_key ON invoices (idempotency_key)",
]

if __name__ == "__main__":
    print("=" * 60)
    print("  MIGRATE: invoices.idempotency_key")
    print("=" * 60)
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"\n> {stmt}")
            conn.execute(text(stmt))
    print("\n✅ Hoàn tất.")
