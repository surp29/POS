#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - BACKFILL: product_groups + products.nhom_id cho du lieu da co san
=============================================================================
products.py/product_groups.py truoc day chi ghi products.nhom_sp (text), khong bao
gio set nhom_id (FK that sang product_groups). Script nay, cho moi gia tri
products.nhom_sp khac null da co san ma chua co ProductGroup tuong ung:
  1. Tao 1 ProductGroup moi (neu chua co, so khop khong phan biet hoa/thuong)
  2. Gan nhom_id cho tat ca san pham co nhom_sp trung ten do

Idempotent — chay lai nhieu lan khong tao trung ProductGroup.

Su dung:
    cd Backend
    python backfill_product_groups.py
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Product, ProductGroup

if __name__ == "__main__":
    print("=" * 60)
    print("  BACKFILL: product_groups / products.nhom_id")
    print("=" * 60)

    db = SessionLocal()
    try:
        distinct_names = [
            row[0].strip()
            for row in db.query(Product.nhom_sp).distinct().all()
            if row[0] and row[0].strip()
        ]
        print(f"\nTìm thấy {len(distinct_names)} tên nhóm khác nhau trong products.nhom_sp")

        created, linked = 0, 0
        for name in distinct_names:
            group = db.query(ProductGroup).filter(ProductGroup.ten_nhom.ilike(name)).first()
            if not group:
                group = ProductGroup(ten_nhom=name)
                db.add(group)
                db.flush()
                created += 1
                print(f"  + Tạo ProductGroup: '{name}' (id={group.id})")

            updated = (
                db.query(Product)
                .filter(Product.nhom_sp == name, Product.nhom_id.is_(None))
                .update({Product.nhom_id: group.id})
            )
            linked += updated

        db.commit()
        print(f"\n✅ Hoàn tất — tạo mới {created} nhóm, gán nhom_id cho {linked} sản phẩm.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Lỗi: {e}")
        sys.exit(1)
    finally:
        db.close()
