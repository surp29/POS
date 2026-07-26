#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - UPDATE: gan anh that (do user tu cung cap) cho cac san pham dang
thieu anh, luu tap trung tai Ecommerce Backend (EcomPos/Backend/media/products/
{ma_sp}.{ext}, phuc vu qua static mount /media — xem app/main.py ben Ecommerce
Backend). Day la anh NGUOI DUNG TU CUNG CAP (khong phai anh scrape/hotlink tu
web). image_url luu duong dan TUONG DOI "/media/products/..." (khong nhung
cung domain/host) — Storefront tu ghep voi NEXT_PUBLIC_API_URL luc render
(xem Storefront/lib/api.ts::resolveImageUrl), nen doi host luc deploy chi can
doi 1 bien moi truong, khong phai sua lai du lieu da luu trong DB. Truoc day
anh nam trong Storefront/public/images/products/ (gan voi frontend) - da doi
sang cho Ecommerce Backend so huu de tach rieng khoi vong doi build/deploy
cua frontend, va la noi tu nhien de sau nay them tinh nang upload qua admin.

Idempotent — chay lai an toan, chi update image_url + emit integration event.

Su dung:
    cd Backend
    python update_product_images.py
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Product
from app.services.integration_events import emit_event, product_snapshot

# ma_sp -> ten file (duoi file, khop voi EcomPos/Backend/media/products/)
IMAGES = {
    "BAN001": "BAN001.webp",
    "BAN002": "BAN002.webp",
    "DH001": "DH001.webp",
    "DH002": "DH002.webp",
    "DH003": "DH003.webp",
    "DH004": "DH004.webp",
    "DH005": "DH005.webp",
    "GHE001": "GHE001.webp",
    "GHE002": "GHE002.webp",
    "GHE003": "GHE003.webp",
    "GHE004": "GHE004.webp",
    "LT101": "LT101.webp",
    "LT102": "LT102.webp",
    "LT103": "LT103.webp",
    "LT104": "LT104.webp",
    "LT105": "LT105.webp",
    "LT106": "LT106.webp",
    "MON001": "MON001.webp",
    "MON002": "MON002.webp",
    "MON003": "MON003.webp",
    "MON004": "MON004.webp",
    "MON005": "MON005.webp",
    "MON006": "MON006.webp",
    "MON007": "MON007.webp",
    "MON008": "MON008.webp",
    "MON009": "MON009.webp",
    "MON010": "MON010.webp",
    "PK101": "PK101.webp",
    "PK102": "PK102.webp",
    "PK103": "PK103.webp",
    "PK104": "PK104.webp",
    "PK105": "PK105.webp",
    "PK106": "PK106.webp",
    "PK107": "PK107.webp",
    "PK108": "PK108.webp",
    "PK109": "PK109.webp",
    "PK110": "PK110.webp",
    "SP001": "SP001.avif",
    "SP002": "SP002.webp",
    "TN101": "TN101.webp",
    "TN102": "TN102.webp",
    "TN103": "TN103.webp",
    "TN104": "TN104.webp",
    "TN105": "TN105.webp",
    "TN106": "TN106.webp",
}


def update_product_images():
    db = SessionLocal()
    try:
        print("\n🖼️  Gán ảnh do người dùng cung cấp cho sản phẩm còn thiếu ảnh...\n")
        updated, not_found = 0, []
        for ma_sp, filename in IMAGES.items():
            p = db.query(Product).filter(Product.ma_sp == ma_sp).first()
            if not p:
                not_found.append(ma_sp)
                continue
            p.image_url = f"/media/products/{filename}"
            db.flush()
            emit_event(db, "product.updated", "product", p.id, product_snapshot(p))
            updated += 1
        db.commit()
        print(f"   ✅ {updated} sản phẩm được gán ảnh")
        if not_found:
            print(f"   ⚠️  Không tìm thấy {len(not_found)} SKU trong DB: {', '.join(not_found)}")
        print("\n✅ Hoàn tất — Ecommerce Backend sẽ tự đồng bộ trong vài giây (poll events).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_product_images()
