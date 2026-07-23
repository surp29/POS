#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - SEED: catalog thiết bị công nghệ thật (tên/giá/ảnh lấy từ CellphoneS)
================================================================================
Dữ liệu tên sản phẩm, giá bán (VND) và URL ảnh lấy THẬT từ các trang danh mục
công khai của cellphones.com.vn (laptop, mobile, tai nghe, phụ kiện, đồng hồ
thông minh) — tham chiếu ảnh trực tiếp (hotlink) tới CDN của họ, KHÔNG tải về
và lưu bản sao trong repo này (tránh vấn đề bản quyền khi redistribute ảnh sản
phẩm của bên thứ ba). `so_luong` (tồn kho) là số TỰ ĐẶT có chủ đích để phục vụ
test — không phải tồn kho thật của CellphoneS:

  - DT001 (iPhone 17 Pro Max)      so_luong=1   → sản phẩm "hot" tồn kho 1,
                                                    dùng để test race condition
                                                    oversell khi nhiều khách
                                                    tranh mua cùng lúc.
  - LT007 (MSI Katana 15)          so_luong=3   → tồn kho thấp, gần hết hàng.
  - TN005 (JBL Wave Beam)          so_luong=2   → tồn kho thấp.
  - DH005 (Apple Watch Ultra 3)    so_luong=1, KHÔNG có ảnh → kết hợp 2 edge
                                                    case: tồn kho 1 + fallback
                                                    ảnh mặc định.
  - LT008 (Acer Aspire Lite 16)    so_luong=0   → hết hàng, test hiển thị/
                                                    chặn checkout.
  - DT008 (POCO X8 Pro Max)        so_luong=0   → hết hàng.
  - DT005 (Samsung Z Fold7)        41.990.000đ  → giá cao nhất, test
                                                    fraud/velocity check với
                                                    đơn giá trị lớn.
  - Nhóm "Đồng hồ thông minh"      không có image_url → test fallback "Không
                                                    có ảnh" trên storefront với
                                                    sản phẩm thật (không phải
                                                    do quên nhập ảnh).

Idempotent — chạy lại nhiều lần an toàn (update nếu ma_sp đã tồn tại thay vì
tạo trùng). Mỗi sản phẩm tạo/cập nhật đều emit integration event — Ecommerce
Backend poll events (5s) sẽ tự đồng bộ ngay, không cần đợi full-resync hàng giờ.

Sử dụng:
    cd Backend
    python seed_tech_catalog.py
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Product, ProductGroup
from app.services.integration_events import emit_event, product_snapshot

CDN = "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product"

GROUPS = [
    ("Laptop", "Máy tính xách tay"),
    ("Điện thoại", "Điện thoại thông minh"),
    ("Âm thanh", "Tai nghe, loa"),
    ("Phụ kiện", "Chuột, bàn phím, phụ kiện máy tính"),
    ("Đồng hồ thông minh", "Smartwatch"),
]

# ma_sp -> giá niêm yết (gia_chung) TRƯỚC KHUYẾN MÃI, cao hơn gia_ban — mô
# phỏng chương trình giảm giá thật (10-23%) cho 1 số sản phẩm cụ thể, KHÔNG
# phải toàn bộ catalog (giống thực tế: không phải sản phẩm nào cũng đang sale).
# Sản phẩm không có trong dict này giữ gia_chung = gia_ban (không giảm giá).
# Dùng để hiển thị badge SALE + giá gạch ngang + section Flash Sale ở storefront.
SALE_LIST_PRICES = {
    "LT004": 32_990_000,
    "LT007": 39_990_000,
    "DT001": 39_990_000,
    "DT004": 34_990_000,
    "DT006": 7_990_000,
    "TN001": 11_990_000,
    "TN005": 1_290_000,
    "PK002": 890_000,
    "PK006": 349_000,
    "DH003": 4_290_000,
}

# (ma_sp, ten_sp, nhom, don_vi, so_luong, gia_ban, gia_von, image_path_or_None, mo_ta)
PRODUCTS = [
    # ── Laptop ────────────────────────────────────────────────────────────
    ("LT001", "Laptop ASUS TUF Gaming A15 FA506NCG-HN329W", "Laptop", "Cái", 15,
     27_990_000, 22_500_000, "/t/e/text_d_i_9_14.png", "Laptop gaming AMD Ryzen, RTX, màn 144Hz"),
    ("LT002", "Laptop Dell 14 DC14250 DC4C5375W1", "Laptop", "Cái", 10,
     31_390_000, 25_800_000, "/g/r/group_945_1_21.png", "Laptop văn phòng Dell, thiết kế mỏng nhẹ"),
    ("LT003", "Laptop MSI Modern 15 F1MG-1225VN", "Laptop", "Cái", 25,
     18_990_000, 15_200_000, "/g/r/group_945_29.png", "Laptop văn phòng phổ thông, mỏng nhẹ"),
    ("LT004", "Laptop Acer Gaming Nitro ProPanel ANV15-52-50VA", "Laptop", "Cái", 8,
     27_990_000, 22_800_000, "/g/r/group_975_17.png", "Laptop gaming Intel Core, RTX series"),
    ("LT005", "Laptop Lenovo IdeaPad Slim 3 14IWC11 83RQ002NVN", "Laptop", "Cái", 20,
     24_190_000, 19_500_000, "/g/r/group_945_1_20.png", "Laptop mỏng nhẹ Lenovo IdeaPad"),
    ("LT006", "MacBook Neo 13 inch A18 Pro 2026 8GB 256GB", "Laptop", "Cái", 5,
     18_790_000, 15_600_000, "/m/a/macbook_13_19.png", "MacBook 13 inch, chip A18 Pro"),
    ("LT007", "Laptop MSI Katana 15 B13VEK-2440VN", "Laptop", "Cái", 3,
     34_990_000, 28_900_000, "/t/e/text_d_i_1__4_62.png", "Laptop gaming MSI Katana, RTX, 144Hz — sắp hết hàng"),
    ("LT008", "Laptop Acer Aspire Lite 16 GEN 2 AL16-52P-76DU", "Laptop", "Cái", 0,
     17_690_000, 14_300_000, "/g/r/group_659_1__12.png", "Laptop mỏng nhẹ Acer Aspire Lite — hiện hết hàng"),

    # ── Điện thoại ────────────────────────────────────────────────────────
    ("DT001", "iPhone 17 Pro Max 256GB", "Điện thoại", "Cái", 1,
     35_990_000, 30_500_000, "/i/p/iphone-17-pro-max_3.jpg", "iPhone 17 Pro Max 256GB — hàng hot, chỉ còn 1"),
    ("DT002", "iPhone 17 Pro 256GB", "Điện thoại", "Cái", 12,
     33_890_000, 28_700_000, "/i/p/iphone-17-pro-256-gb.png", "iPhone 17 Pro 256GB chính hãng"),
    ("DT003", "iPhone 17 256GB", "Điện thoại", "Cái", 30,
     23_990_000, 20_100_000, "/i/p/iphone_17_256gb-3_2.jpg", "iPhone 17 256GB chính hãng"),
    ("DT004", "Samsung Galaxy S26 Ultra 5G 12GB 256GB", "Điện thoại", "Cái", 9,
     30_890_000, 25_900_000, "/s/a/samsung-galaxy-s26-ultra-1.jpg", "Samsung Galaxy S26 Ultra, S Pen, camera 200MP"),
    ("DT005", "Samsung Galaxy Z Fold7 12GB 256GB", "Điện thoại", "Cái", 4,
     41_990_000, 35_200_000, "/s/a/samsung-galaxy-z-fold-7.jpg", "Samsung Galaxy Z Fold7 — điện thoại gập, giá cao nhất catalog"),
    ("DT006", "Samsung Galaxy A17 5G 8GB 128GB", "Điện thoại", "Cái", 60,
     6_790_000, 5_600_000, "/s/a/samsung-galaxy-a17-5g-back.jpg", "Samsung Galaxy A17 5G tầm trung"),
    ("DT007", "Xiaomi Redmi Note 14 Pro Plus 5G 8GB 256GB", "Điện thoại", "Cái", 40,
     8_490_000, 7_000_000, "/x/i/xiaomi-redmi-note-14-pro-plus.jpg", "Xiaomi Redmi Note 14 Pro Plus 5G"),
    ("DT008", "POCO X8 Pro Max 12GB 256GB", "Điện thoại", "Cái", 0,
     13_790_000, 11_400_000, "/x/i/xiaomi-poco-x8-pro-max_2.jpg", "POCO X8 Pro Max — hiện hết hàng"),

    # ── Âm thanh ──────────────────────────────────────────────────────────
    ("TN001", "Tai nghe Bluetooth chụp tai Sony WH-1000XM6", "Âm thanh", "Cái", 18,
     9_990_000, 8_200_000, "/x/m/xm6.png", "Tai nghe chống ồn Sony flagship"),
    ("TN002", "Tai nghe Bluetooth Apple AirPods 4", "Âm thanh", "Cái", 50,
     3_090_000, 2_500_000, "/a/p/apple-airpods-4-thumb.png", "AirPods 4 chính hãng Apple"),
    ("TN003", "Tai nghe Samsung Galaxy Buds 4", "Âm thanh", "Cái", 22,
     4_490_000, 3_650_000, "/s/a/samsung_buds4_17_.png", "Tai nghe true wireless Samsung"),
    ("TN004", "Tai nghe không dây JBL Wave Buds 2", "Âm thanh", "Cái", 70,
     1_100_000, 850_000, "/t/a/tai-nghe-khong-day-jbl-wave-buds-2-_14_.png", "Tai nghe JBL giá rẻ, pin trâu"),
    ("TN005", "Tai nghe Bluetooth True Wireless JBL Wave Beam", "Âm thanh", "Cái", 2,
     990_000, 750_000, "/t/a/tai-nghe-khong-day-jbl-wave-beam-0000.png", "Tai nghe JBL Wave Beam — sắp hết hàng"),
    ("TN006", "Tai nghe Bluetooth chụp tai Marshall Major 5", "Âm thanh", "Cái", 15,
     3_450_000, 2_800_000, "/t/a/tai-nghe-chup-tai-marshall-major-5_1_.png", "Tai nghe Marshall thiết kế cổ điển"),

    # ── Phụ kiện ──────────────────────────────────────────────────────────
    ("PK001", "Bàn phím không dây Logitech MX Keys mini", "Phụ kiện", "Cái", 20,
     2_450_000, 1_950_000, "/g/a/gaming_8_15__1.png", "Bàn phím không dây cao cấp Logitech"),
    ("PK002", "Chuột Gaming không dây Logitech G304 Lightspeed", "Phụ kiện", "Cái", 45,
     725_000, 570_000, "/c/h/chuot-gaming-khong-day-logitech-g304-lightspeed_1_1.png", "Chuột gaming không dây Logitech"),
    ("PK003", "Chuột có dây Gaming Logitech G102 LightSync Gen 2", "Phụ kiện", "Cái", 100,
     400_000, 300_000, "/c/h/chuot-choi-game-co-day-logitech-g102-lightsync-8000dpi_1__2.png", "Chuột gaming có dây giá rẻ"),
    ("PK004", "Bàn phím cơ E-DRA EK375 V2 Beta Blue Black", "Phụ kiện", "Cái", 35,
     490_000, 380_000, "/g/a/gaming_8_43_.png", "Bàn phím cơ giá rẻ E-DRA"),
    ("PK005", "Chuột không dây Logitech MX Anywhere 3S", "Phụ kiện", "Cái", 12,
     1_550_000, 1_250_000, "/c/h/chuot-khong-day-logitech-mx-anywhere-3s_2.png", "Chuột không dây cao cấp, đa thiết bị"),
    ("PK006", "Chuột không dây Bluetooth Logitech M196", "Phụ kiện", "Cái", 150,
     279_000, 210_000, "/c/h/chuot-khong-day-bluetooth-logitech-m196.png", "Chuột bluetooth giá rẻ, văn phòng"),

    # ── Đồng hồ thông minh (không có ảnh — test fallback) ───────────────────
    ("DH001", "Samsung Galaxy Watch 7", "Đồng hồ thông minh", "Cái", 25,
     4_490_000, 3_650_000, None, "Smartwatch Samsung Galaxy Watch 7"),
    ("DH002", "Apple Watch Series 11", "Đồng hồ thông minh", "Cái", 10,
     9_990_000, 8_300_000, None, "Apple Watch Series 11 chính hãng"),
    ("DH003", "Xiaomi Watch S4", "Đồng hồ thông minh", "Cái", 30,
     3_620_000, 2_900_000, None, "Smartwatch Xiaomi giá tốt"),
    ("DH004", "Huawei Watch GT 5 Pro", "Đồng hồ thông minh", "Cái", 6,
     5_490_000, 4_500_000, None, "Smartwatch Huawei thể thao"),
    ("DH005", "Apple Watch Ultra 3", "Đồng hồ thông minh", "Cái", 1,
     22_990_000, 19_500_000, None, "Apple Watch Ultra 3 — hàng cao cấp, chỉ còn 1"),
]


def seed_tech_catalog():
    db = SessionLocal()
    try:
        print("\n📱 Seed catalog thiết bị công nghệ (dữ liệu thật từ CellphoneS)...\n")

        groups = {}
        for name, desc in GROUPS:
            g = db.query(ProductGroup).filter(ProductGroup.ten_nhom == name).first()
            if not g:
                g = ProductGroup(ten_nhom=name, mo_ta=desc)
                db.add(g)
                db.flush()
            groups[name] = g
        print(f"   ✅ {len(groups)} nhóm sản phẩm")

        created, updated = 0, 0
        for ma_sp, ten_sp, nhom, don_vi, so_luong, gia_ban, gia_von, img_path, mo_ta in PRODUCTS:
            image_url = f"{CDN}{img_path}" if img_path else None
            gia_chung = SALE_LIST_PRICES.get(ma_sp, gia_ban)
            p = db.query(Product).filter(Product.ma_sp == ma_sp).first()
            if p:
                p.ten_sp, p.nhom_sp, p.nhom_id = ten_sp, nhom, groups[nhom].id
                p.don_vi, p.so_luong = don_vi, so_luong
                p.gia_ban, p.gia_chung, p.gia_von = gia_ban, gia_chung, gia_von
                p.image_url, p.mo_ta = image_url, mo_ta
                p.trang_thai = 'Còn hàng' if so_luong > 0 else 'Hết hàng'
                updated += 1
            else:
                p = Product(
                    ma_sp=ma_sp, ten_sp=ten_sp, nhom_sp=nhom, nhom_id=groups[nhom].id,
                    don_vi=don_vi, so_luong=so_luong,
                    gia_ban=gia_ban, gia_chung=gia_chung, gia_von=gia_von,
                    image_url=image_url, mo_ta=mo_ta,
                    trang_thai='Còn hàng' if so_luong > 0 else 'Hết hàng',
                )
                db.add(p)
                created += 1
            db.flush()
            emit_event(db, "product.updated", "product", p.id, product_snapshot(p))

        db.commit()
        print(f"   ✅ {created} sản phẩm mới, {updated} sản phẩm cập nhật ({len(PRODUCTS)} tổng)")
        print("\n✅ Hoàn tất — Ecommerce Backend sẽ tự đồng bộ trong vài giây (poll events).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_tech_catalog()
