"""
Reports API — doanh thu tính theo tiền thực thu (Invoice.tong_tien),
không dùng InvoiceItem.total_price (giá chưa giảm).

Fix: khi khách được giảm giá, doanh thu = tong_tien hóa đơn (đã giảm),
     không phải tổng don_gia × so_luong (chưa giảm).
"""
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from ..permission_middleware import require_permission
from datetime import datetime, date
from typing import Optional

from ..database import get_db
from ..services.customers import calc_customer_tier, customer_aggregates, customer_leaderboard, customer_debts_from_invoices
from ..models import User, Invoice, InvoiceItem, Product
from ..tasks.report_tasks import generate_revenue_report, generate_debt_report
from ..celery_app import celery_app
from ..cache import cache_get, cache_set

router = APIRouter(prefix="/reports", tags=["reports"])


def _date_params(from_date: Optional[str], to_date: Optional[str]):
    """Parse date strings, return (date|None, date|None)."""
    fd = td = None
    if from_date:
        try: fd = datetime.strptime(from_date, '%Y-%m-%d').date()
        except ValueError: pass
    if to_date:
        try: td = datetime.strptime(to_date, '%Y-%m-%d').date()
        except ValueError: pass
    return fd, td


# ── Sync endpoint: revenue ────────────────────────────────────────────────────

@router.get("/revenue")
def revenue_report(
    from_date: Optional[str] = Query(None),
    to_date:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission('reports.view')),
):
    """
    Báo cáo doanh thu — single JOIN query thay vì N+1 queries.
    Doanh thu thực = Invoice.tong_tien (sau giảm giá), phân bổ theo tỷ lệ giá gốc.
    Kết quả cache 5 phút.
    """
    cache_key = f"reports:revenue:{from_date}:{to_date}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    fd, td = _date_params(from_date, to_date)

    # Điều kiện ngày cho WHERE clause
    date_conditions = "AND i.trang_thai ILIKE '%đã thanh toán%'"
    params: dict = {}
    if fd:
        date_conditions += " AND i.ngay_hd >= :from_date"
        params["from_date"] = fd
    if td:
        date_conditions += " AND i.ngay_hd <= :to_date"
        params["to_date"] = td

    # ── 1. Tổng quan (1 query) ───────────────────────────────────────────────
    summary_sql = text(f"""
        SELECT
            COALESCE(SUM(i.tong_tien), 0)                          AS total_revenue,
            COALESCE(SUM(raw.raw_total - i.tong_tien), 0)          AS total_discount,
            COALESCE(SUM(ii.so_luong), 0)                          AS total_qty_sold,
            COUNT(DISTINCT i.id)                                    AS total_invoices
        FROM invoices i
        JOIN invoice_items ii   ON ii.invoice_id = i.id
        JOIN (
            SELECT invoice_id, SUM(total_price) AS raw_total
            FROM invoice_items
            GROUP BY invoice_id
        ) raw ON raw.invoice_id = i.id
        WHERE 1=1 {date_conditions}
    """)
    s_row = db.execute(summary_sql, params).mappings().one()

    total_revenue  = float(s_row["total_revenue"]  or 0)
    total_discount = float(s_row["total_discount"] or 0)
    total_qty_sold = int(s_row["total_qty_sold"]   or 0)
    total_invoices = int(s_row["total_invoices"]   or 0)

    # ── 2. Doanh thu theo sản phẩm (1 query) ────────────────────────────────
    items_sql = text(f"""
        SELECT
            ii.product_code,
            MIN(ii.product_name)  AS ten_sp,
            MIN(ii.don_gia)       AS gia_ban,
            SUM(ii.so_luong)      AS so_luong_ban,
            SUM(ii.total_price)   AS gia_goc_tong,
            SUM(
                CASE WHEN raw.raw_total > 0
                     THEN ii.total_price * i.tong_tien / raw.raw_total
                     ELSE ii.total_price END
            )                     AS doanh_thu
        FROM invoices i
        JOIN invoice_items ii   ON ii.invoice_id = i.id
        JOIN (
            SELECT invoice_id, SUM(total_price) AS raw_total
            FROM invoice_items
            GROUP BY invoice_id
        ) raw ON raw.invoice_id = i.id
        WHERE 1=1 {date_conditions}
        GROUP BY ii.product_code
        ORDER BY doanh_thu DESC
    """)
    rows = db.execute(items_sql, params).mappings().all()

    items_out = []
    for r in rows:
        doanh_thu   = float(r["doanh_thu"]    or 0)
        gia_goc     = float(r["gia_goc_tong"] or 0)
        tiet_kiem   = round(gia_goc - doanh_thu, 2)
        ty_le       = round(doanh_thu / total_revenue * 100, 2) if total_revenue > 0 else 0.0
        items_out.append({
            "ma_sp":        r["product_code"] or "N/A",
            "ten_sp":       r["ten_sp"]       or "N/A",
            "gia_ban":      float(r["gia_ban"] or 0),
            "so_luong_ban": int(r["so_luong_ban"] or 0),
            "gia_goc_tong": round(gia_goc, 2),
            "doanh_thu":    round(doanh_thu, 2),
            "tiet_kiem":    tiet_kiem,
            "ty_le":        ty_le,
        })

    # ── 3. Tồn kho (2 queries nhẹ) ──────────────────────────────────────────
    total_qty_remaining = db.query(func.sum(Product.so_luong)).scalar() or 0
    total_products      = db.query(func.count(Product.id)).scalar()     or 0

    result = {
        "summary": {
            "total_revenue":            round(total_revenue, 2),
            "total_discount":           round(total_discount, 2),
            "total_quantity_sold":      total_qty_sold,
            "total_quantity_remaining": int(total_qty_remaining),
            "total_products":           int(total_products),
            "total_invoices":           total_invoices,
        },
        "items": items_out,
    }
    cache_set(cache_key, result, ttl=300)
    return result


# ── Sync endpoint: debt ───────────────────────────────────────────────────────

@router.get("/debt")
def debt_report(
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission('reports.debt')),
):
    cache_key = f"reports:debt:{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    from datetime import timedelta
    today       = date.today()
    cutoff_date = today - timedelta(days=30)

    rows_agg = db.execute(text("""
        SELECT
            COALESCE(SUM(tong_tien), 0)                                                    AS total_debt,
            COALESCE(SUM(CASE WHEN ngay_hd IS NOT NULL AND ngay_hd < :cutoff THEN tong_tien ELSE 0 END), 0) AS overdue_debt,
            COUNT(DISTINCT CASE WHEN nguoi_mua IS NOT NULL THEN nguoi_mua END)             AS debt_customers
        FROM invoices
        WHERE trang_thai NOT ILIKE '%đã thanh toán%'
    """), {"cutoff": cutoff_date}).mappings().one()

    total_debt     = float(rows_agg["total_debt"]     or 0)
    overdue_debt   = float(rows_agg["overdue_debt"]   or 0)
    debt_customers = int(rows_agg["debt_customers"]   or 0)
    avg_debt       = (total_debt / debt_customers) if debt_customers > 0 else 0

    # Detail rows với pagination
    detail_rows = db.execute(text("""
        SELECT nguoi_mua, so_hd, ngay_hd, tong_tien
        FROM invoices
        WHERE trang_thai NOT ILIKE '%đã thanh toán%'
        ORDER BY tong_tien DESC
        LIMIT :lim
    """), {"lim": limit}).mappings().all()

    items = []
    for r in detail_rows:
        ngay = r["ngay_hd"]
        days = (today - ngay).days if ngay else 0
        items.append({
            "khach_hang": r["nguoi_mua"] or "N/A",
            "so_hoa_don": r["so_hd"]     or "N/A",
            "ngay_tao":   ngay.isoformat() if ngay else "",
            "so_tien_no": float(r["tong_tien"] or 0),
            "trang_thai": "overdue" if days > 30 else "normal",
            "ghi_chu":    f"Còn nợ {days} ngày" if days > 0 else "Chưa thanh toán",
        })

    result = {
        "summary": {
            "total_debt":     round(total_debt, 2),
            "overdue_debt":   round(overdue_debt, 2),
            "debt_customers": debt_customers,
            "avg_debt":       round(avg_debt, 2),
        },
        "items": items,
    }
    cache_set(cache_key, result, ttl=120)
    return result


# ── Async endpoints ───────────────────────────────────────────────────────────

@router.post("/revenue/async")
def revenue_report_async(
    from_date: Optional[str] = Query(None),
    to_date:   Optional[str] = Query(None),
):
    try:
        task = generate_revenue_report.delay(from_date=from_date, to_date=to_date)
        return {
            "success":  True,
            "task_id":  task.id,
            "status":   "queued",
            "message":  "Báo cáo đang được tạo nền.",
            "poll_url": f"/api/reports/task/{task.id}",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=503, detail=f"Celery không khả dụng: {str(e)}")


@router.post("/debt/async")
def debt_report_async():
    try:
        task = generate_debt_report.delay()
        return {
            "success":  True,
            "task_id":  task.id,
            "status":   "queued",
            "poll_url": f"/api/reports/task/{task.id}",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=503, detail=f"Celery không khả dụng: {str(e)}")


@router.get("/task/{task_id}")
def get_task_result(task_id: str):
    try:
        result = AsyncResult(task_id, app=celery_app)
        if result.state == "PENDING":
            return {"task_id": task_id, "status": "PENDING", "message": "Đang chờ worker..."}
        if result.state == "PROGRESS":
            return {"task_id": task_id, "status": "PROGRESS", "meta": result.info}
        if result.state == "SUCCESS":
            return {"task_id": task_id, "status": "SUCCESS", "result": result.result}
        if result.state == "FAILURE":
            return {"task_id": task_id, "status": "FAILURE", "error": str(result.result)}
        return {"task_id": task_id, "status": result.state}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")

# ── Customers Analytics (merged from customers_analytics.py) ──

@router.get("/aggregates")
def api_customer_aggregates(db: Session = Depends(get_db)):
    return customer_aggregates(db)

@router.get("/leaderboard")
def api_customer_leaderboard(limit: int = 100, db: Session = Depends(get_db)):
    return customer_leaderboard(db, limit=limit)

@router.get("/debts")
def api_customer_debts(db: Session = Depends(get_db)):
    """Lấy danh sách công nợ từ các hóa đơn chưa thanh toán, kèm thông tin khách hàng và hạn mức thành viên."""
    return customer_debts_from_invoices(db)