#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sinh THEM du lieu hoa don lich su, chi phuc vu demo lop phan tich (dbt star schema +
Metabase). Dung chinh xac cac gia tri trang_thai/hinh_thuc_tt nhu create_sample_data.py
de dbt models loc dung. Khong dung lam du lieu nghiep vu that.

Idempotent: xoa cac invoice co prefix DEMO- roi tao lai.
"""
import sys, os, random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Product, Account, Invoice, InvoiceItem

random.seed(42)

db = SessionLocal()

old_items = db.query(InvoiceItem).join(Invoice).filter(Invoice.so_hd.like('DEMO-%')).all()
for it in old_items:
    db.delete(it)
db.query(Invoice).filter(Invoice.so_hd.like('DEMO-%')).delete(synchronize_session=False)
db.commit()

products = db.query(Product).all()
accounts = db.query(Account).all()
payment_methods = ['Tiền mặt', 'Banking', 'MoMo']
walkin_names = ['Khách vãng lai', 'Khách lẻ', 'Khách vãng lai']

if not products or not accounts:
    print('No products/accounts found - run create_sample_data.py first')
    sys.exit(1)

today = date.today()
start = today - timedelta(days=119)

count = 0
d = start
while d <= today:
    n_invoices = random.choice([0, 1, 1, 2, 2, 3])
    for seq in range(1, n_invoices + 1):
        use_known_customer = random.random() < 0.7
        buyer_name = random.choice(accounts).ten_tk if use_known_customer else random.choice(walkin_names)

        so_hd = f"DEMO-{d.strftime('%y%m%d')}-{seq:03d}"
        pay = random.choice(payment_methods)
        is_paid = random.random() < 0.92
        status = 'Đã thanh toán' if is_paid else 'Chưa thanh toán'

        inv = Invoice(
            so_hd=so_hd,
            ngay_hd=d,
            nguoi_mua=buyer_name,
            tong_tien=0.0,
            trang_thai=status,
            hinh_thuc_tt=pay if is_paid else None,
        )
        db.add(inv)
        db.flush()

        n_lines = random.choice([1, 1, 2, 2, 3])
        chosen_products = random.sample(products, k=min(n_lines, len(products)))
        total = 0.0
        for p in chosen_products:
            qty = random.randint(1, 4)
            unit_price = p.gia_ban
            line_total = qty * unit_price
            total += line_total
            db.add(InvoiceItem(
                invoice_id=inv.id,
                product_id=p.id,
                product_code=p.ma_sp,
                product_name=p.ten_sp,
                so_luong=qty,
                don_gia=unit_price,
                total_price=line_total,
            ))
        inv.tong_tien = total
        count += 1
    d += timedelta(days=1)

db.commit()
db.close()
print(f"Generated {count} demo invoices from {start} to {today}")
