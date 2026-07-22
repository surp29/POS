# PosPos — n8n (Extract & Load)

Lop Extract & Load (2 chu dau trong ELT) cho PosPos: dung n8n keo du lieu tu 1 nguon
ngoai (mo phong 1 he thong doi tac dung Google Sheet de bao ton kho — dung the loai
nguon "Google Sheets" nhu JD mo ta) va do vao **vung dem staging** tren PostgreSQL,
truoc khi dbt (xem `../dbt/`) doc vao va transform.

```
Google Sheet (doi tac bao ton kho)
        │  HTTP Request (CSV da publish to web)
        ▼
   n8n workflow  ── Parse CSV (Code node) ──▶  Postgres: raw_staging.stg_external_inventory
        │
        ▼
   dbt (lop staging/marts doc tiep tu day — xem ../dbt/)
```

## Workflow: `workflows/pos_extract_inventory_sheet.json`

4 node:
1. **Manual Trigger (test)** / **Schedule Trigger (daily 06:00)** — 2 cach kich hoat,
   dung 1 trong 2 (thu bang tay hoac chay tu dong theo lich).
2. **Get Inventory Sheet (CSV)** — HTTP Request GET vao URL CSV da publish cua Google
   Sheet.
3. **Parse CSV** — Code node, tach text CSV thanh JSON.
4. **Insert into staging.stg_external_inventory** — Postgres node, ghi vao bang staging.

## Da kiem thu that (khong chi viet file roi doan no chay)

Workflow nay da duoc **import va chay thu that** tren local qua n8n CLI/API (khong
qua thao tac UI):

1. Dung 1 container tam serve file `sample_data/inventory_sheet_sample.csv` qua HTTP
   (mo phong URL CSV da publish cua Google Sheet — vi khong the tao Google Sheet that
   thay ban trong buoc nay).
2. Tro node "Get Inventory Sheet (CSV)" vao URL do, import credential + workflow bang
   `n8n import:credentials` / `n8n import:workflow`, roi goi
   `POST /rest/workflows/:id/run` de chay thu.
3. Ket qua: execution **status = success**, va 5 dong da xuat hien that trong
   `raw_staging.stg_external_inventory` (kiem tra lai bang `psql`).

File `workflows/pos_extract_inventory_sheet.json` trong repo da duoc **doi URL ve
placeholder** — ban can thay bang URL CSV publish that cua Google Sheet cua minh
truoc khi chay (xem buoc 2 ben duoi). Co che parse/insert thi giu nguyen, da xac nhan
chay dung.

## Cach chay voi Google Sheet that

1. Tao 1 Google Sheet voi 4 cot: `product_code, warehouse_name, qty_on_hand, updated_at`
   (xem `sample_data/inventory_sheet_sample.csv` de co vi du).
2. **File → Share → Publish to web** → chon sheet → dinh dang **CSV** → copy URL.
3. Mo n8n UI (`http://localhost:5678`), mo workflow "POS - Extract Inventory Sheet to
   Postgres Staging", sua URL trong node "Get Inventory Sheet (CSV)" thanh URL vua
   copy.
4. Chay thu bang node "Manual Trigger (test)", kiem tra lai bang
   `raw_staging.stg_external_inventory`.
5. Muon chay tu dong theo lich: bat (activate) workflow — luc do
   "Schedule Trigger (daily 06:00)" se tu kich hoat moi ngay luc 6h sang. Doi lich
   trong node neu can (cron expression `0 6 * * *`).

## Setup local

```bash
cd Backend
docker compose -f docker-compose.yml -f docker-compose.n8n.yml up -d n8n
```

n8n UI: http://localhost:5678 — lan dau se yeu cau tao tai khoan owner (email +
password bat ky, chi luu tren volume local `n8n_data`, khong anh huong gi ben ngoai
may ban). Sau do vao **Settings → Import from File** de import
`workflows/pos_extract_inventory_sheet.json`, hoac dung CLI:

```bash
docker cp n8n/workflows/pos_extract_inventory_sheet.json pos_n8n:/tmp/wf.json
docker exec pos_n8n n8n import:workflow --input=/tmp/wf.json
```

Credential Postgres can tao thu cong trong UI (Postgres, host=`postgres`,
port=`5432`, database=`posdb`, user=`posuser`, password=`pospassword`, SSL=disable) —
day la cac gia tri dev local giong het trong `Backend/docker-compose.yml`, khong phai
bi mat.

## Gioi han da biet (huong cai tien tiep theo)

Postgres node hien dang dung `insert` thuan — chay lai workflow nhieu lan se **cong
don** them dong thay vi ghi de. Cho 1 pipeline that, nen doi sang:
- `ON CONFLICT (product_code, warehouse_name) DO UPDATE` (upsert), hoac
- `TRUNCATE` bang staging truoc moi lan load (phu hop neu nguon la full snapshot,
  khong phai incremental).

Day la 1 quyet dinh thiet ke can can nhac theo tan suat chay va khoi luong du lieu
that, khong phai loi — de nguyen o day de show ro y thuc ve idempotency khi trinh
bay project.
