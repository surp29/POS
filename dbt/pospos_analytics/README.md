# PosPos Analytics — dbt project

Lop Transform (chu T trong ELT) cho PosPos: bien doi cac bang OLTP (`products`,
`invoices`, `accounts`, ...) thanh mo hinh **Star Schema** (Fact / Dimension) phuc vu
bao cao va dashboard, thay vi query truc tiep vao bang nghiep vu.

## Kien truc

```
public.*  (OLTP, do FastAPI backend ghi)
    │
    ▼
staging  (models/staging/*.sql — 1-1 voi bang nguon, chi doi ten cot / chuan hoa kieu)
    │
    ▼
marts/core  (models/marts/core/*.sql — dim_date, dim_product, dim_customer,
             fact_sales, fact_orders)
    │
    ▼
marts/reporting  (models/marts/reporting/*.sql — mart_revenue_daily,
                  mart_revenue_by_product, mart_customer_ranking)
    │
    ▼
Metabase / Power BI
```

## Quyet dinh thiet ke dang chu y

- **fact_sales dung `invoices` + `invoice_items`, khong dung `orders`.** Trong schema
  goc, `orders` la yeu cau/phieu tu khach (co the huy, chua thanh toan), con `invoices`
  moi la giao dich da phat sinh tai POS. Dung `orders` lam fact doanh thu se lam sai
  lech so lieu. `fact_orders` van duoc tao rieng de theo doi pipeline don hang.

- **dim_customer xu ly viec thieu foreign key giua invoices va accounts (da fix o
  OLTP, van giu fallback cho du lieu cu).** Phat hien ban dau: schema OLTP khong rang
  buoc `invoices.nguoi_mua` (text nhan vien go tay) voi `accounts`, dan den 1 khach da
  co ho so van co the "roi khoi" bao cao neu ten ghi luc ban hang khac di. Da xu ly tan
  goc o Backend: them cot `invoices.customer_id` / `orders.customer_id` (FK that sang
  `accounts.id`, xem `Backend/migrate_add_customer_id.py`) va sua logic tao hoa
  don/don hang de ghi cot nay. `stg_invoices.sql`/`stg_orders.sql` doc them
  `buyer_customer_id`; `fact_sales.sql`/`fact_orders.sql` uu tien join qua id that
  nay, **chi fallback ve match-key theo ten** cho cac hoa don/don hang tao TRUOC khi co
  cot customer_id (van con nhieu trong du lieu mau — 175 hoa don demo sinh truoc migration
  nay chua co customer_id). Chay thu `select * from analytics.mart_customer_ranking`
  van con thay ty le doanh thu tu nhom "khach le / chua dinh danh" (chu yeu la du lieu
  demo cu) — dung loai van de "chuan hoa danh muc khach hang" trong JD, gio da co ca
  ban ghi lai qua trinh: phat hien qua dbt → fix tan goc o OLTP → dbt tu dong uu tien
  du lieu moi hon, van an toan voi du lieu cu.

## Chay thu (local)

Yeu cau: docker-compose cua `Backend/` dang chay (it nhat service `postgres`).

```bash
cd Backend
docker compose up -d postgres

cd ../dbt
pip install -r requirements.txt
cd pospos_analytics
export DBT_PROFILES_DIR=.          # hoac copy profiles.yml vao ~/.dbt/
dbt deps
dbt run
dbt test
```

Mac dinh profiles.yml tro vao `localhost:5432` — neu port 5432 tren may ban da bi 1
PostgreSQL native khac chiem dung (rat hay gap tren Windows), chay dbt trong 1
container gan vao network `backend_pos_network` va tro host toi service `postgres`
thay vi `localhost`:

```bash
docker run --rm --network backend_pos_network \
  -v "$(pwd)/..:/dbt" -w /dbt/pospos_analytics \
  -e DBT_PROFILES_DIR=. -e DBT_POSTGRES_HOST=postgres \
  python:3.11-slim bash -lc "pip install -q -r ../requirements.txt && dbt deps && dbt run && dbt test"
```

Ket qua da duoc xac nhan chay that: **16 models, 49 tests, PASS=49/49** tren du lieu
mau cua project (bao gom 180 hoa don rai tren ~4 thang).

## Cau truc

| Thu muc | Noi dung |
|---|---|
| `models/staging/` | 1 view / 1 bang nguon, chi doi ten cot sang tieng Anh + chuan hoa kieu du lieu |
| `models/marts/core/` | `dim_date`, `dim_product`, `dim_customer`, `fact_sales`, `fact_orders` |
| `models/marts/reporting/` | Data mart tong hop san sang cho Metabase: doanh thu theo ngay/san pham, xep hang khach hang |
