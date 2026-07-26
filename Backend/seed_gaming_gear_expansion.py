#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - SEED: mo rong moi danh muc con trong "Linh kien PC" len 30+ SKU
================================================================================
Bo sung cho seed_gaming_gear_catalog.py — muc tieu la MOI danh muc con (CPU,
VGA, RAM, Mainboard, PSU, Case, Tan nhiet, SSD, HDD) co >= 30 san pham khac
nhau de dropdown facet (xem PcPartsMenu.tsx / pcPartsFacets.ts o Storefront)
co du bien the that su duyet duoc thay vi chi vai muc.

Ten model la TEN PHAN CUNG THAT (model number cong khai, vd "RTX 5070",
"Ryzen 9 9950X3D", "WD Black SN850X") — tra cuu qua tim kiem de co danh sach
dung/hien hanh, khong phai noi dung sang tao rieng cua bat ky nha ban le nao.
Cung boi canh do: KHONG hotlink anh tu website ban le that (giu nguyen
image_url=None, dung fallback tren storefront) — xem giai thich day du trong
docstring cua seed_gaming_gear_catalog.py.

Idempotent — chay lai nhieu lan an toan. Chay SAU seed_gaming_gear_catalog.py
(dung chung GROUPS "Linh kien PC" da duoc tao boi script do).

Su dung:
    cd Backend
    python seed_gaming_gear_expansion.py
"""
import sys, os, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Product, ProductGroup
from app.services.integration_events import emit_event, product_snapshot

GROUP_NAME = "Linh kiện PC"

# (ma_sp, ten_sp, don_vi, so_luong, gia_ban, gia_von, mo_ta)
PRODUCTS = [
    # ── CPU (thêm 24 — thế hệ mới AMD 9000/Intel Core Ultra 200, đời cũ AM4, APU) ──
    ("CPU009", "CPU AMD Ryzen 5 9600X", "Cái", 20, 5_990_000, 5_000_000, "6 nhân 12 luồng, socket AM5, Zen 5"),
    ("CPU010", "CPU AMD Ryzen 7 9700X", "Cái", 16, 8_190_000, 6_900_000, "8 nhân 16 luồng, Zen 5"),
    ("CPU011", "CPU AMD Ryzen 7 9800X3D", "Cái", 6, 12_990_000, 11_000_000, "3D V-Cache thế hệ mới, hàng đầu gaming"),
    ("CPU012", "CPU AMD Ryzen 9 9900X", "Cái", 8, 13_990_000, 11_900_000, "12 nhân 24 luồng, Zen 5"),
    ("CPU013", "CPU AMD Ryzen 9 9950X", "Cái", 4, 18_990_000, 16_200_000, "16 nhân 32 luồng, flagship Zen 5"),
    ("CPU014", "CPU AMD Ryzen 9 9950X3D", "Cái", 2, 22_990_000, 19_700_000, "16 nhân, 3D V-Cache, đầu bảng"),
    ("CPU015", "CPU AMD Ryzen 5 5500", "Cái", 40, 1_990_000, 1_650_000, "6 nhân 12 luồng, socket AM4, phổ thông"),
    ("CPU016", "CPU AMD Ryzen 5 5600", "Cái", 30, 2_690_000, 2_250_000, "6 nhân 12 luồng, AM4"),
    ("CPU017", "CPU AMD Ryzen 5 5600X", "Cái", 22, 3_190_000, 2_650_000, "6 nhân 12 luồng, AM4, xung nhịp cao"),
    ("CPU018", "CPU AMD Ryzen 7 5700X", "Cái", 15, 3_990_000, 3_300_000, "8 nhân 16 luồng, AM4"),
    ("CPU019", "CPU AMD Ryzen 7 5800X3D", "Cái", 9, 6_490_000, 5_400_000, "3D V-Cache trên AM4, vẫn rất mạnh gaming"),
    ("CPU020", "CPU Intel Core i3-12100F", "Cái", 35, 1_990_000, 1_650_000, "4 nhân 8 luồng, socket 1700, giá rẻ"),
    ("CPU021", "CPU Intel Core i5-12400F", "Cái", 30, 2_990_000, 2_450_000, "6 nhân 12 luồng, socket 1700"),
    ("CPU022", "CPU Intel Core i5-13400", "Cái", 25, 4_390_000, 3_650_000, "10 nhân 16 luồng, có iGPU"),
    ("CPU023", "CPU Intel Core i5-13600K", "Cái", 12, 6_990_000, 5_900_000, "14 nhân 20 luồng, không khóa xung"),
    ("CPU024", "CPU Intel Core i7-13700K", "Cái", 8, 9_990_000, 8_400_000, "16 nhân 24 luồng, không khóa xung"),
    ("CPU025", "CPU Intel Core i9-13900K", "Cái", 3, 14_990_000, 12_700_000, "24 nhân 32 luồng, flagship thế hệ 13"),
    ("CPU026", "CPU Intel Core Ultra 5 245K", "Cái", 10, 8_490_000, 7_200_000, "Kiến trúc Arrow Lake, socket 1851"),
    ("CPU027", "CPU Intel Core Ultra 7 265K", "Cái", 6, 11_990_000, 10_200_000, "Arrow Lake, hiệu năng đa nhiệm cao"),
    ("CPU028", "CPU Intel Core Ultra 9 285K", "Cái", 3, 17_990_000, 15_400_000, "Arrow Lake, flagship, NPU tích hợp AI"),
    ("CPU029", "CPU AMD Ryzen 5 8500G", "Cái", 18, 4_190_000, 3_500_000, "APU, iGPU Radeon mạnh, không cần VGA rời"),
    ("CPU030", "CPU AMD Ryzen 7 8700G", "Cái", 10, 6_290_000, 5_300_000, "APU cao cấp, chơi game không cần VGA rời"),
    ("CPU031", "CPU Intel Core i3-13100F", "Cái", 28, 2_490_000, 2_050_000, "4 nhân 8 luồng, socket 1700"),
    ("CPU032", "CPU Intel Core i5-14600K", "Cái", 9, 7_990_000, 6_750_000, "14 nhân 20 luồng, thế hệ 14 không khóa xung"),

    # ── VGA (thêm 22 — RTX 50/RX 9000 series mới, đời cũ, thêm hãng AIB) ─────
    ("VGA011", "VGA ASUS Dual GeForce RTX 5060 8GB", "Cái", 18, 9_990_000, 8_400_000, "8GB GDDR7, kiến trúc Blackwell"),
    ("VGA012", "VGA MSI Ventus GeForce RTX 5060 Ti 16GB", "Cái", 12, 13_490_000, 11_400_000, "16GB GDDR7, gaming 1440p"),
    ("VGA013", "VGA Gigabyte Windforce GeForce RTX 5070 12GB", "Cái", 10, 18_990_000, 16_100_000, "12GB GDDR7, gaming 1440p cao"),
    ("VGA014", "VGA ASUS TUF GeForce RTX 5070 Ti 16GB", "Cái", 6, 26_990_000, 22_900_000, "16GB GDDR7, hiệu năng vượt trội"),
    ("VGA015", "VGA MSI Gaming X GeForce RTX 5080 16GB", "Cái", 3, 38_990_000, 33_200_000, "16GB GDDR7, gaming 4K"),
    ("VGA016", "VGA ASUS ROG Astral GeForce RTX 5090 32GB", "Cái", 1, 62_990_000, 54_500_000, "32GB GDDR7, flagship tuyệt đối"),
    ("VGA017", "VGA Sapphire Pulse Radeon RX 9070 16GB", "Cái", 9, 16_990_000, 14_400_000, "16GB GDDR6, kiến trúc RDNA 4"),
    ("VGA018", "VGA XFX Radeon RX 9070 XT 16GB", "Cái", 6, 19_990_000, 16_900_000, "16GB GDDR6, FSR 4"),
    ("VGA019", "VGA ASRock Radeon RX 9060 XT 16GB", "Cái", 14, 11_490_000, 9_700_000, "16GB GDDR6, gaming 1440p giá tốt"),
    ("VGA020", "VGA Gigabyte GeForce RTX 3050 8GB", "Cái", 20, 5_490_000, 4_600_000, "8GB GDDR6, phổ thông, thế hệ cũ"),
    ("VGA021", "VGA ASUS GeForce GTX 1650 4GB", "Cái", 25, 3_490_000, 2_900_000, "4GB GDDR6, văn phòng/eSports nhẹ"),
    ("VGA022", "VGA MSI GeForce RTX 3060 12GB", "Cái", 16, 6_990_000, 5_900_000, "12GB GDDR6, gaming Full HD/1440p"),
    ("VGA023", "VGA Palit GeForce RTX 4060 8GB", "Cái", 22, 8_290_000, 6_950_000, "8GB GDDR6, gaming Full HD"),
    ("VGA024", "VGA Zotac GeForce RTX 4070 Super 12GB", "Cái", 7, 17_690_000, 15_000_000, "12GB GDDR6X"),
    ("VGA025", "VGA Inno3D GeForce RTX 4060 Ti 16GB", "Cái", 10, 11_990_000, 10_100_000, "16GB GDDR6, cho video/AI nhẹ"),
    ("VGA026", "VGA PowerColor Radeon RX 7600 XT 16GB", "Cái", 12, 9_490_000, 8_000_000, "16GB GDDR6"),
    ("VGA027", "VGA Gigabyte Radeon RX 7900 GRE 16GB", "Cái", 5, 16_490_000, 13_950_000, "16GB GDDR6, gaming 1440p/4K"),
    ("VGA028", "VGA ASUS ROG Strix Radeon RX 7900 XTX 24GB", "Cái", 2, 28_990_000, 24_700_000, "24GB GDDR6, flagship AMD thế hệ trước"),
    ("VGA029", "VGA Gainward GeForce RTX 4070 Ti Super 16GB", "Cái", 4, 21_990_000, 18_700_000, "16GB GDDR6X"),
    ("VGA030", "VGA Colorful GeForce RTX 4060 8GB", "Cái", 19, 8_190_000, 6_850_000, "8GB GDDR6, giá tốt"),
    ("VGA031", "VGA Sapphire Nitro+ Radeon RX 7800 XT 16GB", "Cái", 6, 17_490_000, 14_800_000, "16GB GDDR6, tản nhiệt lớn"),
    ("VGA032", "VGA Gigabyte Aorus GeForce RTX 5070 Ti 16GB", "Cái", 3, 28_490_000, 24_200_000, "16GB GDDR7, cao cấp"),

    # ── RAM (thêm 26 — thêm hãng TeamGroup/ADATA/Crucial, DDR4 mở rộng, 8-64GB) ──
    ("RAM007", "RAM TeamGroup T-Force Delta RGB DDR5 16GB 6000MHz", "Bộ", 30, 1_490_000, 1_240_000, "1x16GB, RGB"),
    ("RAM008", "RAM TeamGroup T-Force Vulcan DDR5 32GB (2x16GB) 6000MHz", "Bộ", 20, 2_790_000, 2_330_000, "Kit 2 thanh"),
    ("RAM009", "RAM ADATA XPG Lancer DDR5 16GB 5600MHz", "Bộ", 35, 1_290_000, 1_070_000, "1x16GB, tản nhiệt nhôm"),
    ("RAM010", "RAM ADATA XPG Lancer DDR5 32GB (2x16GB) 6000MHz", "Bộ", 18, 2_590_000, 2_150_000, "Kit 2 thanh"),
    ("RAM011", "RAM Crucial DDR5 16GB 5600MHz", "Bộ", 40, 1_190_000, 990_000, "1x16GB, ổn định"),
    ("RAM012", "RAM Crucial DDR5 32GB (2x16GB) 5600MHz", "Bộ", 22, 2_490_000, 2_070_000, "Kit 2 thanh"),
    ("RAM013", "RAM Kingston Fury Renegade DDR5 32GB (2x16GB) 6400MHz", "Bộ", 10, 3_690_000, 3_100_000, "Hiệu năng cao, RGB"),
    ("RAM014", "RAM Kingston Fury Beast DDR5 64GB (2x32GB) 5600MHz", "Bộ", 6, 5_990_000, 5_050_000, "Cho workstation/render"),
    ("RAM015", "RAM Corsair Vengeance DDR5 64GB (2x32GB) 6000MHz", "Bộ", 5, 6_490_000, 5_500_000, "Cho workstation/render"),
    ("RAM016", "RAM G.Skill Ripjaws S5 DDR5 16GB 5600MHz", "Bộ", 28, 1_290_000, 1_070_000, "1x16GB"),
    ("RAM017", "RAM G.Skill Trident Z5 RGB DDR5 32GB (2x16GB) 7200MHz", "Bộ", 8, 4_190_000, 3_530_000, "Xung nhịp rất cao, RGB"),
    ("RAM018", "RAM Corsair Dominator Titanium DDR5 32GB (2x16GB) 6600MHz", "Bộ", 4, 5_290_000, 4_460_000, "Cao cấp nhất dòng Dominator"),
    ("RAM019", "RAM TeamGroup T-Force Vulcan DDR4 16GB 3200MHz", "Bộ", 30, 720_000, 590_000, "1x16GB"),
    ("RAM020", "RAM ADATA XPG Gammix D10 DDR4 16GB 3200MHz", "Bộ", 32, 690_000, 570_000, "1x16GB, tản nhiệt"),
    ("RAM021", "RAM Corsair Vengeance LPX DDR4 16GB 3200MHz", "Bộ", 45, 750_000, 620_000, "1x16GB, thấp gọn"),
    ("RAM022", "RAM Corsair Vengeance LPX DDR4 32GB (2x16GB) 3200MHz", "Bộ", 20, 1_450_000, 1_200_000, "Kit 2 thanh"),
    ("RAM023", "RAM G.Skill Ripjaws V DDR4 16GB 3200MHz", "Bộ", 38, 700_000, 580_000, "1x16GB"),
    ("RAM024", "RAM Kingston ValueRAM DDR4 8GB 2666MHz", "Bộ", 60, 390_000, 320_000, "1x8GB, phổ thông văn phòng"),
    ("RAM025", "RAM Crucial DDR4 8GB 3200MHz", "Bộ", 55, 410_000, 340_000, "1x8GB"),
    ("RAM026", "RAM Crucial DDR4 16GB 2666MHz", "Bộ", 40, 690_000, 570_000, "1x16GB"),
    ("RAM027", "RAM Kingston Fury Beast DDR5 8GB 5200MHz", "Bộ", 42, 690_000, 570_000, "1x8GB, giá rẻ"),
    ("RAM028", "RAM ADATA XPG Lancer DDR5 8GB 5200MHz", "Bộ", 38, 650_000, 540_000, "1x8GB"),
    ("RAM029", "RAM TeamGroup Elite DDR4 8GB 2666MHz", "Bộ", 65, 370_000, 300_000, "1x8GB, phổ thông"),
    ("RAM030", "RAM Corsair Vengeance DDR5 48GB (2x24GB) 6000MHz", "Bộ", 9, 3_290_000, 2_750_000, "Kit dung lượng lẻ mới, tối ưu giá/hiệu năng"),
    ("RAM031", "RAM G.Skill Trident Z5 Neo DDR5 32GB (2x16GB) 6000MHz", "Bộ", 14, 2_890_000, 2_410_000, "Tối ưu AMD EXPO"),
    ("RAM032", "RAM Kingston Fury Renegade DDR5 16GB 6400MHz", "Bộ", 16, 1_890_000, 1_580_000, "1x16GB, xung nhịp cao"),

    # ── Mainboard (thêm 24 — Intel H610/Z790/Z890, AMD A520/X670/X870, ITX) ──
    ("MB007", "Mainboard ASRock H610M-HDV", "Cái", 30, 1_690_000, 1_400_000, "Socket 1700, DDR4, phổ thông"),
    ("MB008", "Mainboard Gigabyte H610M H DDR4", "Cái", 28, 1_790_000, 1_470_000, "Socket 1700, DDR4"),
    ("MB009", "Mainboard MSI PRO H610M-E DDR4", "Cái", 25, 1_850_000, 1_520_000, "Socket 1700, DDR4"),
    ("MB010", "Mainboard ASUS Prime Z790-P WiFi", "Cái", 10, 6_990_000, 5_900_000, "Socket 1700, DDR5, ép xung"),
    ("MB011", "Mainboard MSI MAG Z790 Tomahawk WiFi", "Cái", 8, 7_690_000, 6_500_000, "Socket 1700, DDR5, VRM khỏe"),
    ("MB012", "Mainboard Gigabyte Z790 Aorus Elite AX", "Cái", 9, 6_490_000, 5_450_000, "Socket 1700, DDR5, WiFi 6E"),
    ("MB013", "Mainboard ASUS ROG Maximus Z890 Hero", "Cái", 2, 16_990_000, 14_400_000, "Socket 1851, cho Core Ultra 200"),
    ("MB014", "Mainboard MSI PRO Z890-A WiFi", "Cái", 5, 8_490_000, 7_150_000, "Socket 1851, DDR5"),
    ("MB015", "Mainboard Gigabyte B860M Aorus Elite WiFi", "Cái", 7, 5_490_000, 4_600_000, "Socket 1851, DDR5"),
    ("MB016", "Mainboard ASRock A520M-HDV", "Cái", 32, 1_390_000, 1_140_000, "Socket AM4, phổ thông"),
    ("MB017", "Mainboard Gigabyte A520M H", "Cái", 30, 1_450_000, 1_190_000, "Socket AM4, DDR4"),
    ("MB018", "Mainboard ASUS Prime B550M-A WiFi", "Cái", 20, 2_690_000, 2_200_000, "Socket AM4, DDR4, WiFi"),
    ("MB019", "Mainboard MSI B650 Gaming Plus WiFi", "Cái", 14, 3_990_000, 3_350_000, "Socket AM5, DDR5, WiFi"),
    ("MB020", "Mainboard ASRock B650M Pro RS WiFi", "Cái", 12, 3_690_000, 3_100_000, "Socket AM5, DDR5, WiFi"),
    ("MB021", "Mainboard ASUS ROG Crosshair X670E Hero", "Cái", 2, 15_990_000, 13_600_000, "Socket AM5, cao cấp, PCIe 5.0"),
    ("MB022", "Mainboard Gigabyte X670E Aorus Master", "Cái", 3, 13_490_000, 11_400_000, "Socket AM5, PCIe 5.0"),
    ("MB023", "Mainboard MSI MPG X870E Carbon WiFi", "Cái", 4, 11_990_000, 10_100_000, "Socket AM5, chipset mới nhất"),
    ("MB024", "Mainboard ASRock X870 Steel Legend WiFi", "Cái", 6, 7_990_000, 6_750_000, "Socket AM5, DDR5, WiFi"),
    ("MB025", "Mainboard ASUS ROG Strix B650E-I Gaming WiFi", "Cái", 5, 8_990_000, 7_600_000, "Mini-ITX, Socket AM5"),
    ("MB026", "Mainboard Gigabyte B760I Aorus Pro DDR4", "Cái", 6, 5_990_000, 5_050_000, "Mini-ITX, Socket 1700"),
    ("MB027", "Mainboard Biostar A520MH", "Cái", 25, 1_190_000, 970_000, "Socket AM4, giá rẻ nhất phân khúc"),
    ("MB028", "Mainboard Biostar B450MH", "Cái", 22, 1_390_000, 1_140_000, "Socket AM4, phổ thông"),
    ("MB029", "Mainboard ASRock Z790 Pro RS", "Cái", 8, 5_290_000, 4_450_000, "Socket 1700, DDR5"),
    ("MB030", "Mainboard MSI PRO B760M-A WiFi", "Cái", 16, 3_290_000, 2_730_000, "Socket 1700, DDR5, WiFi"),

    # ── PSU / Nguồn (thêm 24 — thêm hãng Seasonic/Super Flower/Antec/Thermaltake/Segotep) ──
    ("PSU007", "Nguồn Seasonic Focus GX-550 550W 80 Plus Gold", "Cái", 20, 2_190_000, 1_820_000, "Full modular, độ bền cao"),
    ("PSU008", "Nguồn Seasonic Focus GX-750 750W 80 Plus Gold", "Cái", 14, 2_790_000, 2_330_000, "Full modular"),
    ("PSU009", "Nguồn Super Flower Leadex III 650W 80 Plus Gold", "Cái", 12, 2_290_000, 1_910_000, "Full modular, linh kiện Nhật"),
    ("PSU010", "Nguồn Super Flower Leadex Platinum 850W", "Cái", 5, 4_490_000, 3_780_000, "80 Plus Platinum, cao cấp"),
    ("PSU011", "Nguồn Antec NE650G 650W 80 Plus Gold", "Cái", 18, 1_890_000, 1_570_000, "Non-modular, giá tốt"),
    ("PSU012", "Nguồn Antec HCG850 Gold Extreme 850W", "Cái", 6, 3_690_000, 3_100_000, "Full modular"),
    ("PSU013", "Nguồn Thermaltake Smart 500W 80 Plus White", "Cái", 30, 890_000, 720_000, "Non-modular, phổ thông"),
    ("PSU014", "Nguồn Thermaltake Toughpower GF3 750W 80 Plus Gold", "Cái", 10, 2_890_000, 2_420_000, "Full modular"),
    ("PSU015", "Nguồn Segotep 500W 80 Plus", "Cái", 35, 590_000, 470_000, "Giá rẻ, văn phòng"),
    ("PSU016", "Nguồn Segotep 650W 80 Plus Bronze", "Cái", 25, 890_000, 720_000, "Non-modular"),
    ("PSU017", "Nguồn Cooler Master Elite 450W", "Cái", 40, 590_000, 470_000, "Non-modular, phổ thông"),
    ("PSU018", "Nguồn Cooler Master V750 SFX Gold 750W", "Cái", 6, 3_490_000, 2_930_000, "SFX nhỏ gọn, cho case mini"),
    ("PSU019", "Nguồn DeepCool PK550D 550W 80 Plus Bronze", "Cái", 22, 990_000, 810_000, "Non-modular"),
    ("PSU020", "Nguồn DeepCool PX1000G 1000W 80 Plus Gold", "Cái", 4, 4_990_000, 4_200_000, "Full modular, cho cấu hình dual VGA"),
    ("PSU021", "Nguồn ASUS TUF Gaming 650W Bronze", "Cái", 16, 1_690_000, 1_400_000, "Non-modular, bảo hành dài"),
    ("PSU022", "Nguồn ASUS ROG Thor 1200W Platinum", "Cái", 1, 8_990_000, 7_650_000, "Cao cấp nhất, màn hình OLED công suất"),
    ("PSU023", "Nguồn Xigmatek X-Power III 750W", "Cái", 20, 1_290_000, 1_050_000, "Non-modular"),
    ("PSU024", "Nguồn Xigmatek NRP 450W", "Cái", 30, 590_000, 470_000, "Giá rẻ, văn phòng"),
    ("PSU025", "Nguồn Corsair CV550 550W 80 Plus Bronze", "Cái", 28, 1_090_000, 890_000, "Non-modular, phổ thông"),
    ("PSU026", "Nguồn Corsair SF750 SFX 750W Platinum", "Cái", 5, 4_290_000, 3_620_000, "SFX, cho case mini cao cấp"),
    ("PSU027", "Nguồn Gigabyte UD850GM 850W 80 Plus Gold", "Cái", 8, 2_690_000, 2_250_000, "Full modular"),
    ("PSU028", "Nguồn MSI MAG A650BN 650W 80 Plus Bronze", "Cái", 18, 1_390_000, 1_150_000, "Non-modular"),
    ("PSU029", "Nguồn MSI MPG A1000G 1000W 80 Plus Gold", "Cái", 3, 5_290_000, 4_460_000, "Full modular, cao cấp"),
    ("PSU030", "Nguồn Corsair RM850x 850W 80 Plus Gold", "Cái", 9, 3_190_000, 2_680_000, "Full modular, phổ biến nhất phân khúc"),

    # ── Case (thêm 24 — thêm hãng Antec/Montech/Thermaltake/Jonsbo/Gamdias) ──
    ("CASE007", "Case Antec NX410", "Cái", 20, 1_390_000, 1_140_000, "Airflow, giá tốt"),
    ("CASE008", "Case Antec DP503", "Cái", 12, 2_290_000, 1_890_000, "3 mặt kính, RGB"),
    ("CASE009", "Case Montech Air 100", "Cái", 25, 1_090_000, 890_000, "Mesh airflow, giá rẻ"),
    ("CASE010", "Case Montech X3 Mesh", "Cái", 15, 1_890_000, 1_550_000, "Mesh, hỗ trợ radiator 360mm"),
    ("CASE011", "Case Thermaltake Versa H18", "Cái", 22, 990_000, 810_000, "Mini-Tower, giá rẻ"),
    ("CASE012", "Case Thermaltake View 270 TG ARGB", "Cái", 9, 2_490_000, 2_050_000, "Kính cường lực, ARGB"),
    ("CASE013", "Case Jonsbo D31 Mesh", "Cái", 10, 2_190_000, 1_800_000, "Thiết kế Nhật, mesh airflow"),
    ("CASE014", "Case Jonsbo TR40 Pro", "Cái", 6, 3_490_000, 2_930_000, "Full mesh, cao cấp"),
    ("CASE015", "Case Gamdias Talos E1 Elite", "Cái", 14, 1_290_000, 1_060_000, "RGB, giá tốt"),
    ("CASE016", "Case MSI MAG Forge 100M", "Cái", 18, 1_490_000, 1_220_000, "Mesh front, airflow"),
    ("CASE017", "Case MSI MPG Gungnir 110R", "Cái", 8, 2_890_000, 2_410_000, "4 quạt ARGB sẵn"),
    ("CASE018", "Case Gigabyte C200 Glass", "Cái", 16, 1_190_000, 970_000, "Kính cường lực, giá rẻ"),
    ("CASE019", "Case ASUS TUF Gaming GT301", "Cái", 10, 2_390_000, 1_970_000, "Airflow, độ bền quân đội"),
    ("CASE020", "Case ASUS ROG Strix Helios", "Cái", 2, 6_990_000, 5_900_000, "Full-Tower cao cấp"),
    ("CASE021", "Case Corsair 5000D Airflow", "Cái", 9, 3_190_000, 2_680_000, "Airflow, dễ đi dây"),
    ("CASE022", "Case Corsair iCUE 4000X RGB", "Cái", 11, 2_690_000, 2_230_000, "3 quạt RGB sẵn"),
    ("CASE023", "Case NZXT H7 Flow", "Cái", 13, 2_990_000, 2_480_000, "Airflow, thiết kế tối giản"),
    ("CASE024", "Case NZXT H9 Elite", "Cái", 5, 4_990_000, 4_200_000, "Kính 2 mặt, cao cấp"),
    ("CASE025", "Case Cooler Master MasterBox NR200", "Cái", 8, 1_990_000, 1_630_000, "Mini-ITX nhỏ gọn"),
    ("CASE026", "Case Cooler Master HAF 700", "Cái", 1, 8_990_000, 7_650_000, "Full-Tower siêu lớn, server/workstation"),
    ("CASE027", "Case DeepCool CC560", "Cái", 17, 1_390_000, 1_140_000, "4 mặt kính, giá tốt"),
    ("CASE028", "Case DeepCool Matrexx 55", "Cái", 20, 1_190_000, 970_000, "Airflow, phổ thông"),
    ("CASE029", "Case Xigmatek Astro X", "Cái", 24, 890_000, 720_000, "Giá rẻ nhất phân khúc"),
    ("CASE030", "Case Lian Li O11 Dynamic", "Cái", 4, 4_490_000, 3_780_000, "Dual-chamber, cao cấp, hiển thị đẹp"),

    # ── Tản nhiệt (thêm 25 — thêm hãng Noctua/Thermalright/Jonsbo, khí+nước) ──
    ("COOL006", "Tản nhiệt khí Noctua NH-D15", "Cái", 8, 2_990_000, 2_500_000, "Dual-tower, hiệu năng đầu bảng tản khí"),
    ("COOL007", "Tản nhiệt khí Noctua NH-U12S", "Cái", 12, 1_890_000, 1_570_000, "Đơn tháp, êm, bền"),
    ("COOL008", "Tản nhiệt khí Noctua NH-L9i", "Cái", 10, 1_490_000, 1_230_000, "Low-profile, cho case nhỏ"),
    ("COOL009", "Tản nhiệt khí Thermalright Peerless Assassin 120 SE", "Cái", 30, 690_000, 560_000, "Dual-tower, giá/hiệu năng tốt nhất"),
    ("COOL010", "Tản nhiệt khí Thermalright Frozen Warframe 120 ARGB", "Cái", 20, 790_000, 640_000, "Dual-tower, ARGB"),
    ("COOL011", "Tản nhiệt khí Thermalright Phantom Spirit 120 EVO", "Cái", 18, 890_000, 720_000, "Dual-tower, hiệu năng cao"),
    ("COOL012", "Tản nhiệt khí Jonsbo CR-1200 EVO", "Cái", 15, 590_000, 470_000, "Đơn tháp, ARGB"),
    ("COOL013", "Tản nhiệt khí Jonsbo TW6 White", "Cái", 14, 990_000, 810_000, "Dual-tower, màu trắng"),
    ("COOL014", "Tản nhiệt khí DeepCool AK620", "Cái", 22, 990_000, 810_000, "Dual-tower, phổ biến"),
    ("COOL015", "Tản nhiệt khí DeepCool Gammaxx AG400", "Cái", 35, 390_000, 310_000, "Đơn tháp, giá rẻ"),
    ("COOL016", "Tản nhiệt nước DeepCool LT720 360mm", "Cái", 5, 3_290_000, 2_750_000, "AIO 360mm, màn LCD"),
    ("COOL017", "Tản nhiệt nước DeepCool LS520 240mm", "Cái", 10, 1_890_000, 1_570_000, "AIO 240mm"),
    ("COOL018", "Tản nhiệt khí Cooler Master Hyper 212 Halo", "Cái", 25, 790_000, 640_000, "Đơn tháp, ARGB Halo"),
    ("COOL019", "Tản nhiệt nước Cooler Master MasterLiquid ML240L", "Cái", 12, 1_690_000, 1_390_000, "AIO 240mm, giá tốt"),
    ("COOL020", "Tản nhiệt nước Cooler Master MasterLiquid 360 Atmos", "Cái", 3, 4_290_000, 3_620_000, "AIO 360mm, cao cấp"),
    ("COOL021", "Tản nhiệt nước Corsair iCUE H150i Elite 360mm", "Cái", 4, 4_690_000, 3_950_000, "AIO 360mm, RGB"),
    ("COOL022", "Tản nhiệt nước Corsair iCUE Link H100i 240mm", "Cái", 7, 3_290_000, 2_750_000, "AIO 240mm, hệ sinh thái iCUE Link"),
    ("COOL023", "Tản nhiệt khí ID-Cooling SE-207-XT Slim", "Cái", 20, 490_000, 390_000, "Mỏng, cho case nhỏ"),
    ("COOL024", "Tản nhiệt nước ID-Cooling FROSTFLOW 240 VGA", "Cái", 4, 2_190_000, 1_820_000, "AIO cho VGA"),
    ("COOL025", "Tản nhiệt nước ASUS ROG Strix LC II 360", "Cái", 3, 4_490_000, 3_780_000, "AIO 360mm, cao cấp"),
    ("COOL026", "Tản nhiệt nước NZXT Kraken Elite 280", "Cái", 4, 4_990_000, 4_200_000, "AIO 280mm, màn LCD tròn"),
    ("COOL027", "Tản nhiệt khí NZXT T120", "Cái", 16, 990_000, 810_000, "Đơn tháp, thiết kế tối giản"),
    ("COOL028", "Tản nhiệt khí Xigmatek Windpower II 120", "Cái", 40, 290_000, 230_000, "Giá rẻ nhất phân khúc"),
    ("COOL029", "Tản nhiệt khí Thermaltake TOUGHAIR 510", "Cái", 14, 890_000, 720_000, "Dual-tower, ARGB"),
    ("COOL030", "Tản nhiệt nước Thermaltake TH360 V2 Ultra", "Cái", 3, 2_990_000, 2_500_000, "AIO 360mm, ARGB"),

    # ── SSD (thêm 25 — thêm hãng TeamGroup/ADATA/Lexar, dung lượng 240GB-4TB) ──
    ("SSD006", "SSD Samsung 980 Pro 2TB NVMe PCIe 4.0", "Cái", 10, 4_490_000, 3_780_000, "Tốc độ cao, dung lượng lớn"),
    ("SSD007", "SSD Samsung 970 EVO Plus 1TB NVMe", "Cái", 20, 2_190_000, 1_820_000, "PCIe 3.0, ổn định"),
    ("SSD008", "SSD Samsung 870 EVO 500GB SATA", "Cái", 30, 990_000, 810_000, "SATA, phổ thông"),
    ("SSD009", "SSD Samsung 990 Pro 2TB NVMe PCIe 4.0", "Cái", 8, 4_890_000, 4_120_000, "Tốc độ cao nhất dòng Samsung"),
    ("SSD010", "SSD WD Black SN850X 1TB NVMe", "Cái", 18, 2_390_000, 1_990_000, "Gaming cao cấp, PCIe 4.0"),
    ("SSD011", "SSD WD Black SN850X 2TB NVMe", "Cái", 8, 4_390_000, 3_690_000, "Gaming cao cấp, dung lượng lớn"),
    ("SSD012", "SSD WD Green 480GB SATA", "Cái", 35, 650_000, 530_000, "SATA, giá rẻ"),
    ("SSD013", "SSD WD Blue SN580 500GB NVMe", "Cái", 28, 990_000, 810_000, "NVMe phổ thông"),
    ("SSD014", "SSD Kingston NV2 1TB NVMe", "Cái", 25, 1_490_000, 1_230_000, "PCIe 4.0, giá tốt"),
    ("SSD015", "SSD Kingston KC3000 1TB NVMe", "Cái", 12, 2_290_000, 1_910_000, "PCIe 4.0, hiệu năng cao"),
    ("SSD016", "SSD Kingston A400 240GB SATA", "Cái", 40, 490_000, 390_000, "SATA, dung lượng nhỏ giá rẻ"),
    ("SSD017", "SSD Crucial MX500 500GB SATA", "Cái", 30, 950_000, 780_000, "SATA, độ bền cao"),
    ("SSD018", "SSD Crucial P5 Plus 1TB NVMe", "Cái", 18, 1_990_000, 1_650_000, "PCIe 4.0"),
    ("SSD019", "SSD Crucial T500 2TB NVMe", "Cái", 6, 3_990_000, 3_350_000, "PCIe 4.0, hiệu năng cao"),
    ("SSD020", "SSD TeamGroup MP44 1TB NVMe", "Cái", 20, 1_690_000, 1_400_000, "PCIe 4.0, giá tốt"),
    ("SSD021", "SSD TeamGroup GX2 256GB SATA", "Cái", 35, 490_000, 390_000, "SATA, giá rẻ"),
    ("SSD022", "SSD ADATA Legend 900 1TB NVMe", "Cái", 16, 1_590_000, 1_310_000, "PCIe 4.0"),
    ("SSD023", "SSD ADATA XPG SX8200 Pro 512GB NVMe", "Cái", 24, 890_000, 720_000, "PCIe 3.0, phổ thông"),
    ("SSD024", "SSD ADATA Ultimate SU650 240GB SATA", "Cái", 38, 450_000, 360_000, "SATA, giá rẻ nhất phân khúc"),
    ("SSD025", "SSD Lexar NM790 1TB NVMe", "Cái", 15, 1_590_000, 1_310_000, "PCIe 4.0, giá tốt"),
    ("SSD026", "SSD Lexar NS100 512GB SATA", "Cái", 26, 620_000, 500_000, "SATA, phổ thông"),
    ("SSD027", "SSD Samsung 990 Pro 4TB NVMe PCIe 4.0", "Cái", 2, 8_990_000, 7_650_000, "Dung lượng lớn nhất dòng Samsung"),
    ("SSD028", "SSD WD Black SN850X 4TB NVMe", "Cái", 2, 8_490_000, 7_200_000, "Gaming cao cấp, 4TB"),
    ("SSD029", "SSD Kingston Fury Renegade 2TB NVMe", "Cái", 5, 4_690_000, 3_950_000, "PCIe 4.0, hiệu năng cao"),
    ("SSD030", "SSD Crucial P3 500GB NVMe", "Cái", 32, 890_000, 720_000, "PCIe 3.0, giá tốt"),

    # ── HDD (thêm 25 — thêm hãng WD/Seagate/Toshiba đủ dòng, 500GB-16TB) ─────
    ("HDD006", "Ổ cứng WD Blue 1TB HDD 3.5\"", "Cái", 30, 890_000, 720_000, "Lưu trữ phổ thông"),
    ("HDD007", "Ổ cứng WD Blue 4TB HDD 3.5\"", "Cái", 15, 2_390_000, 1_990_000, "Dung lượng lớn, giá tốt"),
    ("HDD008", "Ổ cứng WD Black 1TB HDD 3.5\"", "Cái", 12, 1_690_000, 1_390_000, "Hiệu năng cao, 7200rpm"),
    ("HDD009", "Ổ cứng WD Black 2TB HDD 3.5\"", "Cái", 8, 2_390_000, 1_990_000, "Hiệu năng cao"),
    ("HDD010", "Ổ cứng WD Red Plus 2TB HDD NAS 3.5\"", "Cái", 14, 2_090_000, 1_730_000, "Chuyên dụng NAS"),
    ("HDD011", "Ổ cứng WD Red Plus 4TB HDD NAS 3.5\"", "Cái", 9, 3_190_000, 2_650_000, "Chuyên dụng NAS"),
    ("HDD012", "Ổ cứng WD Purple 2TB HDD 3.5\" (Camera an ninh)", "Cái", 16, 1_790_000, 1_480_000, "Chạy 24/7 cho đầu ghi"),
    ("HDD013", "Ổ cứng WD Purple 8TB HDD 3.5\" (Camera an ninh)", "Cái", 4, 4_990_000, 4_200_000, "Dung lượng lớn cho camera"),
    ("HDD014", "Ổ cứng Seagate Barracuda 2TB HDD 3.5\"", "Cái", 20, 1_490_000, 1_230_000, "Phổ thông"),
    ("HDD015", "Ổ cứng Seagate Barracuda 4TB HDD 3.5\"", "Cái", 12, 2_490_000, 2_070_000, "Dung lượng lớn"),
    ("HDD016", "Ổ cứng Seagate SkyHawk 2TB HDD Camera an ninh", "Cái", 10, 1_890_000, 1_570_000, "Tối ưu cho đầu ghi hình"),
    ("HDD017", "Ổ cứng Seagate SkyHawk 4TB HDD Camera an ninh", "Cái", 7, 2_990_000, 2_480_000, "Tối ưu cho đầu ghi hình"),
    ("HDD018", "Ổ cứng Seagate IronWolf 2TB HDD NAS 3.5\"", "Cái", 12, 2_090_000, 1_730_000, "Chuyên dụng NAS"),
    ("HDD019", "Ổ cứng Seagate IronWolf 8TB HDD NAS 3.5\"", "Cái", 3, 5_990_000, 5_050_000, "NAS dung lượng lớn"),
    ("HDD020", "Ổ cứng Seagate IronWolf Pro 6TB HDD NAS 3.5\"", "Cái", 4, 4_990_000, 4_200_000, "NAS chuyên nghiệp"),
    ("HDD021", "Ổ cứng Seagate Exos 8TB HDD Enterprise 3.5\"", "Cái", 3, 6_490_000, 5_500_000, "Cấp độ doanh nghiệp, chạy liên tục"),
    ("HDD022", "Ổ cứng Toshiba P300 1TB HDD 3.5\"", "Cái", 25, 850_000, 690_000, "Phổ thông, giá rẻ"),
    ("HDD023", "Ổ cứng Toshiba P300 4TB HDD 3.5\"", "Cái", 10, 2_490_000, 2_070_000, "Dung lượng lớn"),
    ("HDD024", "Ổ cứng Toshiba X300 6TB HDD hiệu năng cao", "Cái", 5, 4_290_000, 3_620_000, "7200rpm, cho workstation"),
    ("HDD025", "Ổ cứng Toshiba N300 4TB HDD NAS", "Cái", 8, 3_090_000, 2_570_000, "Chuyên dụng NAS"),
    ("HDD026", "Ổ cứng WD Blue 500GB HDD 3.5\"", "Cái", 35, 650_000, 530_000, "Dung lượng nhỏ, giá rẻ nhất phân khúc"),
    ("HDD027", "Ổ cứng Seagate Barracuda 500GB HDD 3.5\"", "Cái", 32, 620_000, 500_000, "Dung lượng nhỏ, giá rẻ"),
    ("HDD028", "Ổ cứng WD Black 4TB HDD 3.5\"", "Cái", 5, 3_690_000, 3_100_000, "Hiệu năng cao, dung lượng lớn"),
    ("HDD029", "Ổ cứng Toshiba N300 8TB HDD NAS", "Cái", 3, 5_490_000, 4_620_000, "NAS dung lượng lớn"),
    ("HDD030", "Ổ cứng Seagate Exos 16TB HDD Enterprise 3.5\"", "Cái", 1, 11_990_000, 10_200_000, "Doanh nghiệp, dung lượng lớn nhất catalog"),
]


def seed_expansion():
    db = SessionLocal()
    try:
        print("\n🔧 Mở rộng danh mục con Linh kiện PC lên 30+ SKU mỗi loại...\n")

        group = db.query(ProductGroup).filter(ProductGroup.ten_nhom == GROUP_NAME).first()
        if not group:
            group = ProductGroup(ten_nhom=GROUP_NAME)
            db.add(group)
            db.flush()

        created, updated = 0, 0
        for ma_sp, ten_sp, don_vi, so_luong, gia_ban, gia_von, mo_ta in PRODUCTS:
            p = db.query(Product).filter(Product.ma_sp == ma_sp).first()
            if p:
                p.ten_sp, p.nhom_sp, p.nhom_id = ten_sp, GROUP_NAME, group.id
                p.don_vi, p.so_luong = don_vi, so_luong
                p.gia_ban, p.gia_chung, p.gia_von = gia_ban, gia_ban, gia_von
                p.mo_ta = mo_ta
                p.trang_thai = 'Còn hàng' if so_luong > 0 else 'Hết hàng'
                updated += 1
            else:
                p = Product(
                    ma_sp=ma_sp, ten_sp=ten_sp, nhom_sp=GROUP_NAME, nhom_id=group.id,
                    don_vi=don_vi, so_luong=so_luong,
                    gia_ban=gia_ban, gia_chung=gia_ban, gia_von=gia_von,
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
    seed_expansion()
