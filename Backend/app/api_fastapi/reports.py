"""
Reports API — doanh thu tính theo tiền thực thu (Invoice.tong_tien),
không dùng InvoiceItem.total_price (giá chưa giảm).

Fix: khi khách được giảm giá, doanh thu = tong_tien hóa đơn (đã giảm),
     không phải tổng don_gia × so_luong (chưa giảm).
"""
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from sqlalchemy import func
from datetime import datetime, date
from typing import Optional

from ..database import get_db
from ..models import User, Invoice, InvoiceItem, Product
from ..tasks.report_tasks import generate_revenue_report, generate_debt_report
from ..celery_app import celery_app

router = APIRouter(prefix="/reports", tags=["reports"])


def _build_invoice_query(db: Session, from_date: Optional[str], to_date: Optional[str]):
    """Query hóa đơn đã thanh toán với filter ngày."""
    query = db.query(Invoice).filter(
        Invoice.trang_thai.ilike('%đã thanh toán%')
    )
    if from_date:
        try:
            query = query.filter(
                Invoice.ngay_hd >= datetime.strptime(from_date, '%Y-%m-%d').date()
            )
        except ValueError:
            pass
    if to_date:
        try:
            query = query.filter(
                Invoice.ngay_hd <= datetime.strptime(to_date, '%Y-%m-%d').date()
            )
        except ValueError:
            pass
    return query


# ── Sync endpoint: revenue ────────────────────────────────────────────────────

@router.get("/revenue")
def revenue_report(
    from_date: Optional[str] = Query(None),
    to_date:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission('reports.view')),
):
    """
    Báo cáo doanh thu — dùng Invoice.tong_tien (tiền thực thu sau giảm giá).

    Logic phân bổ discount:
    - Lấy tất cả hóa đơn đã thanh toán
    - Với mỗi hóa đơn: tính tỷ lệ từng item (theo don_gia × so_luong / tổng giá gốc)
    - Doanh thu thực của item = tỷ lệ đó × tong_tien hóa đơn
    → Đảm bảo tổng doanh thu = tổng tong_tien hóa đơn (tiền thực thu)
    """
    paid_invoices = _build_invoice_query(db, from_date, to_date).all()

    total_revenue  = 0.0
    total_qty_sold = 0
    product_revenue: dict = {}
    total_discount = 0.0  # Tổng giảm giá

    for inv in paid_invoices:
        actual_total   = float(inv.tong_tien or 0)   # Tiền thực thu
        total_revenue += actual_total

        # Lấy items của hóa đơn này
        items = db.query(InvoiceItem).filter(
            InvoiceItem.invoice_id == inv.id
        ).all()

        if not items:
            continue

        # Tổng giá gốc (chưa giảm) của hóa đơn
        raw_total = sum(float(it.total_price or 0) for it in items)

        # Giảm giá của hóa đơn này
        inv_discount = raw_total - actual_total
        total_discount += inv_discount

        for item in items:
            code    = item.product_code or 'N/A'
            raw_amt = float(item.total_price or 0)
            qty     = int(item.so_luong or 0)

            # Phân bổ doanh thu thực theo tỷ lệ giá gốc
            if raw_total > 0:
                actual_item_revenue = (raw_amt / raw_total) * actual_total
            else:
                actual_item_revenue = raw_amt

            total_qty_sold += qty

            if code not in product_revenue:
                product_revenue[code] = {
                    'ma_sp':         code,
                    'ten_sp':        item.product_name or 'N/A',
                    'so_luong_ban':  0,
                    'gia_ban':       float(item.don_gia or 0),   # Giá gốc
                    'doanh_thu':     0.0,    # Doanh thu thực (sau giảm giá)
                    'gia_goc_tong':  0.0,    # Tổng giá gốc (trước giảm giá)
                    'tiet_kiem':     0.0,    # Số tiền đã giảm
                }
            product_revenue[code]['so_luong_ban'] += qty
            product_revenue[code]['doanh_thu']    += actual_item_revenue
            product_revenue[code]['gia_goc_tong'] += raw_amt
            product_revenue[code]['tiet_kiem']    += (raw_amt - actual_item_revenue)

    total_qty_remaining = db.query(func.sum(Product.so_luong)).scalar() or 0
    total_products      = db.query(func.count(Product.id)).scalar() or 0

    items_out = []
    for code, data in product_revenue.items():
        ty_le = (data['doanh_thu'] / total_revenue * 100) if total_revenue > 0 else 0.0
        items_out.append({
            **data,
            'ty_le':     round(ty_le, 2),
            'doanh_thu': round(data['doanh_thu'], 2),
            'tiet_kiem': round(data['tiet_kiem'], 2),
        })
    items_out.sort(key=lambda x: x['doanh_thu'], reverse=True)

    return {
        "summary": {
            "total_revenue":           round(total_revenue, 2),      # Tiền thực thu
            "total_discount":          round(total_discount, 2),     # Tổng giảm giá
            "total_quantity_sold":     total_qty_sold,
            "total_quantity_remaining": int(total_qty_remaining),
            "total_products":           total_products,
            "total_invoices":          len(paid_invoices),
        },
        "items": items_out,
    }


# ── Sync endpoint: debt ───────────────────────────────────────────────────────

@router.get("/debt")
def debt_report(db: Session = Depends(get_db),
    _: User = Depends(require_permission('reports.debt'))):
    unpaid     = db.query(Invoice).filter(~Invoice.trang_thai.ilike('%đã thanh toán%')).all()
    today      = date.today()
    total_debt = sum(float(inv.tong_tien or 0) for inv in unpaid)
    overdue_debt = 0.0

    for inv in unpaid:
        if inv.ngay_hd and (today - inv.ngay_hd).days > 30:
            overdue_debt += float(inv.tong_tien or 0)

    debt_customers = len({inv.nguoi_mua for inv in unpaid if inv.nguoi_mua})
    avg_debt       = (total_debt / debt_customers) if debt_customers > 0 else 0

    items = []
    for inv in unpaid:
        days = (today - inv.ngay_hd).days if inv.ngay_hd else 0
        items.append({
            'khach_hang': inv.nguoi_mua or 'N/A',
            'so_hoa_don': inv.so_hd or 'N/A',
            'ngay_tao':   inv.ngay_hd.isoformat() if inv.ngay_hd else '',
            'so_tien_no': float(inv.tong_tien or 0),
            'trang_thai': 'overdue' if days > 30 else 'normal',
            'ghi_chu':    f'Còn nợ {days} ngày' if days > 0 else 'Chưa thanh toán',
        })
    items.sort(key=lambda x: x['so_tien_no'], reverse=True)

    return {
        "summary": {
            "total_debt":    round(total_debt, 2),
            "overdue_debt":  round(overdue_debt, 2),
            "debt_customers": debt_customers,
            "avg_debt":      round(avg_debt, 2),
        },
        "items": items,
    }


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
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")