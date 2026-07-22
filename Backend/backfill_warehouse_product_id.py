#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - BACKFILL: warehouses.product_id cho du lieu da co san
==================================================================
warehouses.py truoc day chi luu ma_sp (text), khong bao gio set product_id (FK that
sang products.id) khi tao qua API — chi co create_sample_data.py la set dung. Script
nay khop warehouses.ma_sp voi products.ma_sp cho cac dong con thieu product_id.

Idempotent — chi cap nhat dong dang product_id IS NULL.

Su dung:
    cd Backend
    python backfill_warehouse_product_id.py
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Warehouse, Product

if __name__ == "__main__":
    print("=" * 60)
    print("  BACKFILL: warehouses.product_id")
    print("=" * 60)

    db = SessionLocal()
    try:
        missing = db.query(Warehouse).filter(Warehouse.product_id.is_(None)).all()
        print(f"\n{len(missing)} kho hàng chưa có product_id")

        product_by_code = {p.ma_sp: p for p in db.query(Product).all()}

        linked, unmatched = 0, 0
        for wh in missing:
            product = product_by_code.get(wh.ma_sp)
            if product:
                wh.product_id = product.id
                linked += 1
            else:
                unmatched += 1
                print(f"  ! Không khớp: warehouse id={wh.id} ma_sp='{wh.ma_sp}'")

        db.commit()
        print(f"\n✅ Hoàn tất — gán product_id cho {linked} kho hàng, {unmatched} không khớp product nào.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Lỗi: {e}")
        sys.exit(1)
    finally:
        db.close()
