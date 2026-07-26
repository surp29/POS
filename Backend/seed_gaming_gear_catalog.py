#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - SEED: mo rong catalog linh kien PC / gaming gear (theo huong GearVN)
================================================================================
Bo sung ~80 san pham thuoc cac nhom PC-parts/gaming ma catalog cu (dua theo
CellphoneS) khong co: CPU, VGA, RAM, Mainboard, PSU, Case, Tan nhiet, SSD/HDD,
man hinh, ban ghe gaming — cong voi mo rong Laptop/Am thanh/Phu kien theo huong
gaming gear. Ten san pham la TEN MODEL PHAN CUNG THAT (vd "RTX 4070", "Ryzen 5
7600") — day la danh tu chung/model number, khong phai noi dung sang tao co ban
quyen cua rieng nha ban le nao.

KHONG hotlink anh tu bat ky website ban le that nao (khac voi seed_tech_catalog.py
truoc day dung anh CellphoneS cho 1 tap du lieu nho) — moi san pham trong file
nay co image_url=None, dung fallback "Khong co anh" co san tren storefront. Day
la lua chon co chu dich: file nay phuc vu du lieu demo/dev quy mo lon, KHONG
phai catalog that san sang ban that (du an chua co nha cung cap/ton kho that).

Idempotent — chay lai nhieu lan an toan (update neu ma_sp da ton tai).

Su dung:
    cd Backend
    python seed_gaming_gear_catalog.py
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Product, ProductGroup
from app.services.integration_events import emit_event, product_snapshot

GROUPS = [
    ("Linh kiện PC", "CPU, VGA, RAM, Mainboard, PSU, Case, tản nhiệt, ổ cứng"),
    ("Màn hình", "Màn hình máy tính, màn hình gaming"),
    ("Bàn ghế Gaming", "Bàn, ghế công thái học và gaming"),
]

# ma_sp -> gia niem yet truoc khuyen mai (mo phong sale, giong quy uoc trong
# seed_tech_catalog.py — chi ap dung cho 1 so san pham cu the)
SALE_LIST_PRICES = {
    "VGA003": 16_990_000,
    "CPU004": 11_990_000,
    "MB003": 5_990_000,
    "MON002": 6_990_000,
    "GHE001": 5_990_000,
    "LT101": 29_990_000,
    "PK101": 2_290_000,
}

# (ma_sp, ten_sp, nhom, don_vi, so_luong, gia_ban, gia_von, mo_ta)
PRODUCTS = [
    # ── CPU ───────────────────────────────────────────────────────────────
    ("CPU001", "CPU AMD Ryzen 5 7500F", "Linh kiện PC", "Cái", 30, 3_490_000, 2_900_000, "6 nhân 12 luồng, socket AM5"),
    ("CPU002", "CPU AMD Ryzen 5 7600", "Linh kiện PC", "Cái", 25, 4_690_000, 3_900_000, "6 nhân 12 luồng, kèm iGPU"),
    ("CPU003", "CPU AMD Ryzen 7 7700", "Linh kiện PC", "Cái", 18, 6_490_000, 5_400_000, "8 nhân 16 luồng, hiệu năng cao"),
    ("CPU004", "CPU AMD Ryzen 7 7800X3D", "Linh kiện PC", "Cái", 10, 9_990_000, 8_400_000, "3D V-Cache, tối ưu game thủ"),
    ("CPU005", "CPU Intel Core i5-13400F", "Linh kiện PC", "Cái", 35, 3_990_000, 3_300_000, "10 nhân 16 luồng, socket 1700"),
    ("CPU006", "CPU Intel Core i5-14400F", "Linh kiện PC", "Cái", 28, 4_590_000, 3_800_000, "10 nhân 16 luồng, thế hệ 14"),
    ("CPU007", "CPU Intel Core i7-14700F", "Linh kiện PC", "Cái", 14, 8_990_000, 7_500_000, "20 nhân 28 luồng, hiệu năng cao"),
    ("CPU008", "CPU Intel Core i9-14900KF", "Linh kiện PC", "Cái", 4, 14_990_000, 12_800_000, "24 nhân, flagship, không tích hợp iGPU"),

    # ── VGA / Card đồ họa ─────────────────────────────────────────────────
    ("VGA001", "VGA ASUS Dual GeForce RTX 4060 8GB", "Linh kiện PC", "Cái", 20, 8_490_000, 7_100_000, "8GB GDDR6, gaming Full HD"),
    ("VGA002", "VGA MSI Gaming X GeForce RTX 4060 Ti 8GB", "Linh kiện PC", "Cái", 15, 10_990_000, 9_300_000, "8GB GDDR6, gaming 1440p"),
    ("VGA003", "VGA Gigabyte Gaming OC GeForce RTX 4070 12GB", "Linh kiện PC", "Cái", 12, 14_990_000, 12_700_000, "12GB GDDR6X, gaming 1440p cao"),
    ("VGA004", "VGA ASUS TUF GeForce RTX 4070 Super 12GB", "Linh kiện PC", "Cái", 8, 17_990_000, 15_300_000, "12GB GDDR6X, hiệu năng vượt trội"),
    ("VGA005", "VGA MSI Suprim GeForce RTX 4070 Ti Super 16GB", "Linh kiện PC", "Cái", 5, 22_990_000, 19_600_000, "16GB GDDR6X, cao cấp"),
    ("VGA006", "VGA ASUS ROG Strix GeForce RTX 4080 Super 16GB", "Linh kiện PC", "Cái", 3, 32_990_000, 28_200_000, "16GB GDDR6X, gaming 4K"),
    ("VGA007", "VGA Gigabyte Aorus GeForce RTX 4090 24GB", "Linh kiện PC", "Cái", 2, 52_990_000, 45_800_000, "24GB GDDR6X, flagship 4K/AI"),
    ("VGA008", "VGA Sapphire Pulse Radeon RX 7600 8GB", "Linh kiện PC", "Cái", 22, 7_490_000, 6_300_000, "8GB GDDR6, gaming Full HD giá tốt"),
    ("VGA009", "VGA ASRock Radeon RX 7700 XT 12GB", "Linh kiện PC", "Cái", 10, 12_990_000, 11_000_000, "12GB GDDR6, gaming 1440p"),
    ("VGA010", "VGA XFX Radeon RX 7800 XT 16GB", "Linh kiện PC", "Cái", 7, 15_990_000, 13_600_000, "16GB GDDR6, gaming 1440p/4K"),

    # ── RAM ───────────────────────────────────────────────────────────────
    ("RAM001", "RAM Corsair Vengeance DDR5 16GB 6000MHz", "Linh kiện PC", "Bộ", 60, 1_390_000, 1_150_000, "1x16GB, tản nhiệt nhôm"),
    ("RAM002", "RAM Corsair Vengeance DDR5 32GB (2x16GB) 6000MHz", "Linh kiện PC", "Bộ", 40, 2_690_000, 2_250_000, "Kit 2 thanh, tối ưu dual-channel"),
    ("RAM003", "RAM Kingston Fury Beast DDR5 16GB 5200MHz", "Linh kiện PC", "Bộ", 55, 1_190_000, 990_000, "1x16GB, giá tốt"),
    ("RAM004", "RAM G.Skill Trident Z5 DDR5 32GB (2x16GB) 6400MHz", "Linh kiện PC", "Bộ", 15, 3_390_000, 2_850_000, "RGB, hiệu năng cao"),
    ("RAM005", "RAM Corsair Dominator Platinum DDR5 32GB 6200MHz", "Linh kiện PC", "Bộ", 8, 3_990_000, 3_350_000, "Cao cấp, RGB Capellix"),
    ("RAM006", "RAM Kingston Fury Beast DDR4 16GB 3200MHz", "Linh kiện PC", "Bộ", 70, 750_000, 620_000, "1x16GB, phổ thông"),

    # ── Mainboard ─────────────────────────────────────────────────────────
    ("MB001", "Mainboard ASUS TUF Gaming B760M-PLUS WiFi", "Linh kiện PC", "Cái", 20, 3_990_000, 3_300_000, "Socket 1700, DDR5, WiFi 6"),
    ("MB002", "Mainboard MSI PRO B650M-A WiFi", "Linh kiện PC", "Cái", 18, 3_690_000, 3_050_000, "Socket AM5, DDR5, WiFi"),
    ("MB003", "Mainboard Gigabyte B760M Gaming X DDR4", "Linh kiện PC", "Cái", 25, 2_690_000, 2_200_000, "Socket 1700, DDR4"),
    ("MB004", "Mainboard ASUS ROG Strix B650E-F Gaming WiFi", "Linh kiện PC", "Cái", 6, 6_990_000, 5_900_000, "Socket AM5, PCIe 5.0"),
    ("MB005", "Mainboard MSI MAG B550 Tomahawk", "Linh kiện PC", "Cái", 15, 3_190_000, 2_650_000, "Socket AM4, VRM khỏe"),
    ("MB006", "Mainboard ASRock B760M Steel Legend WiFi", "Linh kiện PC", "Cái", 12, 3_390_000, 2_800_000, "Socket 1700, DDR5, WiFi"),

    # ── PSU / Nguồn ───────────────────────────────────────────────────────
    ("PSU001", "Nguồn Corsair RM750e 750W 80 Plus Gold", "Linh kiện PC", "Cái", 25, 2_390_000, 1_980_000, "Full modular, 80 Plus Gold"),
    ("PSU002", "Nguồn Cooler Master MWE 650W 80 Plus Bronze", "Linh kiện PC", "Cái", 30, 1_390_000, 1_150_000, "Non-modular, giá tốt"),
    ("PSU003", "Nguồn Xigmatek X-Power II 650W", "Linh kiện PC", "Cái", 35, 990_000, 810_000, "Phổ thông, ổn định"),
    ("PSU004", "Nguồn ASUS ROG Strix 850W 80 Plus Gold", "Linh kiện PC", "Cái", 8, 3_990_000, 3_350_000, "Full modular, cho cấu hình cao"),
    ("PSU005", "Nguồn Corsair RM1000x 1000W 80 Plus Gold", "Linh kiện PC", "Cái", 5, 4_690_000, 3_950_000, "Cho VGA flagship"),
    ("PSU006", "Nguồn DeepCool PF600 600W 80 Plus", "Linh kiện PC", "Cái", 40, 890_000, 720_000, "Cấu hình văn phòng/gaming nhẹ"),

    # ── Case ──────────────────────────────────────────────────────────────
    ("CASE001", "Case NZXT H5 Flow", "Linh kiện PC", "Cái", 18, 1_990_000, 1_650_000, "Airflow tối ưu, tempered glass"),
    ("CASE002", "Case Lian Li Lancool 216", "Linh kiện PC", "Cái", 12, 2_490_000, 2_050_000, "Airflow cao, 2 quạt 160mm sẵn"),
    ("CASE003", "Case Corsair 4000D Airflow", "Linh kiện PC", "Cái", 20, 2_190_000, 1_800_000, "Phổ biến, dễ đi dây"),
    ("CASE004", "Case Xigmatek Aquarius Pro", "Linh kiện PC", "Cái", 25, 990_000, 800_000, "Giá tốt, kính cường lực"),
    ("CASE005", "Case Cooler Master MasterBox TD500 Mesh", "Linh kiện PC", "Cái", 10, 2_290_000, 1_900_000, "Mặt lưới kim cương, RGB"),
    ("CASE006", "Case DeepCool CH510", "Linh kiện PC", "Cái", 15, 1_590_000, 1_300_000, "Airflow, hỗ trợ radiator lớn"),

    # ── Tản nhiệt ─────────────────────────────────────────────────────────
    ("COOL001", "Tản nhiệt khí Cooler Master Hyper 212 Black", "Linh kiện PC", "Cái", 40, 690_000, 560_000, "Tản khí phổ thông, hiệu quả cao"),
    ("COOL002", "Tản nhiệt khí DeepCool AK400", "Linh kiện PC", "Cái", 30, 590_000, 470_000, "Đơn tháp, giá tốt"),
    ("COOL003", "Tản nhiệt nước ASUS ROG Ryujin III 240", "Linh kiện PC", "Cái", 4, 5_990_000, 5_050_000, "AIO 240mm, màn LCD"),
    ("COOL004", "Tản nhiệt nước Corsair iCUE H100i Elite", "Linh kiện PC", "Cái", 8, 3_990_000, 3_350_000, "AIO 240mm, RGB"),
    ("COOL005", "Tản nhiệt khí ID-Cooling SE-224-XT", "Linh kiện PC", "Cái", 45, 390_000, 310_000, "Giá rẻ, phù hợp CPU tầm trung"),

    # ── SSD / Ổ cứng ──────────────────────────────────────────────────────
    ("SSD001", "SSD Samsung 990 Pro 1TB NVMe PCIe 4.0", "Linh kiện PC", "Cái", 22, 2_690_000, 2_250_000, "Tốc độ cao, tản nhiệt tích hợp"),
    ("SSD002", "SSD WD Black SN770 1TB NVMe", "Linh kiện PC", "Cái", 30, 1_890_000, 1_580_000, "Gaming, PCIe 4.0"),
    ("SSD003", "SSD Kingston NV2 500GB NVMe", "Linh kiện PC", "Cái", 50, 890_000, 720_000, "Phổ thông, giá tốt"),
    ("SSD004", "SSD Samsung 870 EVO 1TB SATA", "Linh kiện PC", "Cái", 35, 1_690_000, 1_400_000, "SATA, độ bền cao"),
    ("SSD005", "SSD Crucial P3 Plus 1TB NVMe", "Linh kiện PC", "Cái", 28, 1_490_000, 1_240_000, "PCIe 4.0, giá tốt"),
    ("HDD001", "Ổ cứng WD Blue 2TB HDD 3.5\"", "Linh kiện PC", "Cái", 20, 1_390_000, 1_150_000, "Lưu trữ dung lượng lớn"),
    ("HDD002", "Ổ cứng Seagate Barracuda 1TB HDD 3.5\"", "Linh kiện PC", "Cái", 25, 1_090_000, 890_000, "Lưu trữ phổ thông, giá tốt"),
    ("HDD003", "Ổ cứng Toshiba P300 2TB HDD 3.5\"", "Linh kiện PC", "Cái", 18, 1_590_000, 1_300_000, "Hiệu năng ổn định, bảo hành dài"),
    ("HDD004", "Ổ cứng WD Purple 4TB HDD 3.5\" (Camera an ninh)", "Linh kiện PC", "Cái", 10, 2_690_000, 2_250_000, "Tối ưu cho đầu ghi camera, chạy 24/7"),
    ("HDD005", "Ổ cứng Seagate IronWolf 4TB HDD NAS 3.5\"", "Linh kiện PC", "Cái", 8, 3_190_000, 2_650_000, "Chuyên dụng cho NAS, chạy liên tục"),

    # ── Màn hình ──────────────────────────────────────────────────────────
    ("MON001", "Màn hình LG UltraGear 27GP850 27\" 2K 165Hz", "Màn hình", "Cái", 15, 7_990_000, 6_700_000, "IPS 2K, 165Hz, Gsync Compatible"),
    ("MON002", "Màn hình ASUS TUF Gaming VG27AQ 27\" 2K 165Hz", "Màn hình", "Cái", 12, 5_990_000, 5_000_000, "IPS 2K, 165Hz"),
    ("MON003", "Màn hình Dell S2721DGF 27\" 2K 165Hz", "Màn hình", "Cái", 10, 6_490_000, 5_450_000, "IPS 2K, 165Hz, viền mỏng"),
    ("MON004", "Màn hình Samsung Odyssey G5 27\" 2K 165Hz Cong", "Màn hình", "Cái", 8, 5_490_000, 4_600_000, "VA cong 1000R, 2K 165Hz"),
    ("MON005", "Màn hình AOC 24G2 24\" Full HD 144Hz", "Màn hình", "Cái", 30, 2_990_000, 2_450_000, "IPS Full HD, giá tốt"),
    ("MON006", "Màn hình MSI Optix G273QPF 27\" 2K 165Hz", "Màn hình", "Cái", 9, 5_790_000, 4_850_000, "Rapid IPS, 2K 165Hz"),
    ("MON007", "Màn hình ViewSonic VX2758 27\" Full HD 165Hz", "Màn hình", "Cái", 18, 3_490_000, 2_900_000, "Fast IPS, Full HD"),
    ("MON008", "Màn hình Gigabyte M27Q 27\" 2K 170Hz", "Màn hình", "Cái", 7, 6_190_000, 5_200_000, "SS IPS, 2K 170Hz, KVM"),
    ("MON009", "Màn hình LG UltraWide 34WP65C 34\" Cong", "Màn hình", "Cái", 6, 8_990_000, 7_550_000, "21:9 Ultrawide, IPS, cong"),
    ("MON010", "Màn hình Samsung Odyssey G9 49\" DQHD 240Hz", "Màn hình", "Cái", 2, 24_990_000, 21_200_000, "Super Ultrawide, flagship"),

    # ── Bàn ghế Gaming ────────────────────────────────────────────────────
    ("GHE001", "Ghế Gaming DXRacer Formula Series", "Bàn ghế Gaming", "Cái", 12, 4_990_000, 4_150_000, "Da PU, tựa lưng ngả 135°"),
    ("GHE002", "Ghế Gaming AKRacing Core Series", "Bàn ghế Gaming", "Cái", 10, 4_490_000, 3_750_000, "Khung thép, đệm mút cao cấp"),
    ("GHE003", "Ghế Gaming E-Dra Hercules EGC211", "Bàn ghế Gaming", "Cái", 20, 2_690_000, 2_200_000, "Giá tốt, đầy đủ tính năng"),
    ("BAN001", "Bàn Gaming E-Dra Mars EGD101", "Bàn ghế Gaming", "Cái", 15, 1_990_000, 1_650_000, "Khung thép, mặt bàn chống nước"),
    ("BAN002", "Bàn nâng hạ điện Warrior Standing Desk", "Bàn ghế Gaming", "Cái", 6, 4_990_000, 4_200_000, "Motor kép, chỉnh độ cao điện"),
    ("GHE004", "Ghế công thái học ErgoChair Pro", "Bàn ghế Gaming", "Cái", 8, 5_990_000, 5_050_000, "Lưới thoáng khí, hỗ trợ cột sống"),

    # ── Mở rộng Laptop gaming ─────────────────────────────────────────────
    ("LT101", "Laptop Gaming ASUS ROG Strix G16 G614", "Laptop", "Cái", 6, 34_990_000, 29_500_000, "RTX 4060, Core i7, 165Hz"),
    ("LT102", "Laptop Gaming Lenovo Legion 5", "Laptop", "Cái", 8, 29_990_000, 25_200_000, "RTX 4060, Ryzen 7, 165Hz"),
    ("LT103", "Laptop Gaming MSI Cyborg 15", "Laptop", "Cái", 12, 22_990_000, 19_300_000, "RTX 4050, Core i5, 144Hz"),
    ("LT104", "Laptop Gaming Acer Predator Helios Neo 16", "Laptop", "Cái", 5, 36_990_000, 31_200_000, "RTX 4070, Core i7, Mini LED"),
    ("LT105", "Laptop Gaming Dell G15 5530", "Laptop", "Cái", 10, 24_990_000, 21_000_000, "RTX 4050, Core i5, 120Hz"),
    ("LT106", "Laptop Gaming HP Victus 16", "Laptop", "Cái", 9, 21_990_000, 18_500_000, "RTX 4050, Ryzen 5, 144Hz"),

    # ── Mở rộng Phụ kiện (gaming gear) ────────────────────────────────────
    ("PK101", "Bàn phím cơ Logitech G Pro X TKL", "Phụ kiện", "Cái", 15, 2_990_000, 2_500_000, "Hotswap switch, thi đấu chuyên nghiệp"),
    ("PK102", "Bàn phím cơ Corsair K70 RGB Pro", "Phụ kiện", "Cái", 10, 3_490_000, 2_900_000, "RGB per-key, khung nhôm"),
    ("PK103", "Chuột Gaming Razer DeathAdder V3", "Phụ kiện", "Cái", 30, 1_390_000, 1_150_000, "Cảm biến 30K DPI, siêu nhẹ"),
    ("PK104", "Chuột Gaming Logitech G Pro X Superlight 2", "Phụ kiện", "Cái", 20, 3_290_000, 2_750_000, "Không dây, 60g, thi đấu"),
    ("PK105", "Lót chuột Gaming cỡ lớn XL 900x400mm", "Phụ kiện", "Cái", 60, 290_000, 220_000, "Bề mặt vải, chống trượt"),
    ("PK106", "Tay cầm chơi game Xbox Wireless Controller", "Phụ kiện", "Cái", 25, 1_490_000, 1_230_000, "Không dây, tương thích PC"),
    ("PK107", "Webcam Logitech C920 Full HD", "Phụ kiện", "Cái", 18, 1_690_000, 1_400_000, "1080p, tự động lấy nét"),
    ("PK108", "Micro thu âm HyperX SoloCast", "Phụ kiện", "Cái", 22, 1_290_000, 1_050_000, "USB, cắm là dùng, cho stream"),
    ("PK109", "Hub chia USB Gaming 7 cổng", "Phụ kiện", "Cái", 40, 350_000, 270_000, "USB 3.0, có đèn LED"),
    ("PK110", "Giá đỡ Laptop tản nhiệt gấp gọn", "Phụ kiện", "Cái", 45, 390_000, 300_000, "Nhôm, điều chỉnh góc nghiêng"),

    # ── Mở rộng Âm thanh (gaming) ─────────────────────────────────────────
    ("TN101", "Tai nghe Gaming Logitech G435 Lightspeed", "Âm thanh", "Cái", 20, 1_490_000, 1_230_000, "Không dây, siêu nhẹ, RGB"),
    ("TN102", "Tai nghe Gaming HyperX Cloud III", "Âm thanh", "Cái", 15, 2_190_000, 1_820_000, "Driver 53mm, đệm tai êm"),
    ("TN103", "Tai nghe Gaming Razer BlackShark V2", "Âm thanh", "Cái", 18, 1_990_000, 1_650_000, "Âm thanh vòm THX, mic tháo rời"),
    ("TN104", "Loa Gaming Logitech G560 2.1", "Âm thanh", "Cái", 8, 3_990_000, 3_350_000, "RGB đồng bộ màn hình, Bluetooth"),
    ("TN105", "Tai nghe Gaming SteelSeries Arctis Nova 5", "Âm thanh", "Cái", 10, 2_890_000, 2_400_000, "Không dây, Hi-Res Audio"),
    ("TN106", "Loa vi tính 2.1 Logitech Z623", "Âm thanh", "Cái", 12, 2_490_000, 2_050_000, "THX certified, bass mạnh"),
]


def seed_gaming_gear_catalog():
    db = SessionLocal()
    try:
        print("\n🖥️  Seed catalog linh kiện PC / gaming gear (không hotlink ảnh)...\n")

        groups = {}
        for name, desc in GROUPS:
            g = db.query(ProductGroup).filter(ProductGroup.ten_nhom == name).first()
            if not g:
                g = ProductGroup(ten_nhom=name, mo_ta=desc)
                db.add(g)
                db.flush()
            groups[name] = g
        print(f"   ✅ {len(groups)} nhóm mới sẵn sàng")

        created, updated = 0, 0
        for ma_sp, ten_sp, nhom, don_vi, so_luong, gia_ban, gia_von, mo_ta in PRODUCTS:
            # Nhóm co the la nhom moi (Linh kien PC/Man hinh/Ban ghe Gaming) hoac
            # nhom da co san (Laptop/Phu kien/Am thanh) tu seed_tech_catalog.py —
            # can lookup trong DB thay vi chi trong `groups` cuc bo cho nhom cu.
            g = groups.get(nhom) or db.query(ProductGroup).filter(ProductGroup.ten_nhom == nhom).first()
            if not g:
                g = ProductGroup(ten_nhom=nhom)
                db.add(g)
                db.flush()
            groups[nhom] = g

            gia_chung = SALE_LIST_PRICES.get(ma_sp, gia_ban)
            p = db.query(Product).filter(Product.ma_sp == ma_sp).first()
            if p:
                p.ten_sp, p.nhom_sp, p.nhom_id = ten_sp, nhom, g.id
                p.don_vi, p.so_luong = don_vi, so_luong
                p.gia_ban, p.gia_chung, p.gia_von = gia_ban, gia_chung, gia_von
                p.mo_ta = mo_ta
                p.trang_thai = 'Còn hàng' if so_luong > 0 else 'Hết hàng'
                updated += 1
            else:
                p = Product(
                    ma_sp=ma_sp, ten_sp=ten_sp, nhom_sp=nhom, nhom_id=g.id,
                    don_vi=don_vi, so_luong=so_luong,
                    gia_ban=gia_ban, gia_chung=gia_chung, gia_von=gia_von,
                    image_url=None, mo_ta=mo_ta,
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
    seed_gaming_gear_catalog()
