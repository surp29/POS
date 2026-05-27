"""
Celery tasks cho báo cáo nặng.

Tách logic thuần vào _do_*() functions để:
1. Test trực tiếp mà không cần Celery broker
2. Tránh vấn đề self.update_state() cần task_id thật
"""
from celery import shared_task
from sqlalchemy import func
from datetime import datetime, date


# ── Pure logic functions (testable) ──────────────────────────────────────────

def _do_revenue_report(from_date=None, to_date=None) -> dict:
    """Logic báo cáo doanh thu — không phụ thuộc Celery."""
    # Import trong function để tránh circular import khi test
    from app.database import SessionLocal
    from app.models import Invoice, InvoiceItem, Product

    db = SessionLocal()
    try:
        query = db.query(Invoice, InvoiceItem).join(
            InvoiceItem, Invoice.id == InvoiceItem.invoice_id
        ).filter(Invoice.trang_thai.ilike('%đã thanh toán%'))

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

        paid_items     = query.all()
        total_revenue  = 0.0
        total_qty_sold = 0
        product_revenue: dict = {}

        for invoice, item in paid_items:
            total_revenue  += float(item.total_price or 0)
            total_qty_sold += int(item.so_luong or 0)
            code = item.product_code or 'N/A'
            if code not in product_revenue:
                product_revenue[code] = {
                    'ma_sp': code, 'ten_sp': item.product_name or 'N/A',
                    'so_luong_ban': 0, 'gia_ban': float(item.don_gia or 0),
                    'doanh_thu': 0.0,
                }
            product_revenue[code]['so_luong_ban'] += int(item.so_luong or 0)
            product_revenue[code]['doanh_thu']   += float(item.total_price or 0)

        total_qty_remaining = db.query(func.sum(Product.so_luong)).scalar() or 0
        total_products      = db.query(func.count(Product.id)).scalar() or 0

        items = []
        for code, data in product_revenue.items():
            ty_le = (data['doanh_thu'] / total_revenue * 100) if total_revenue > 0 else 0.0
            items.append({**data, 'ty_le': round(ty_le, 2)})
        items.sort(key=lambda x: x['doanh_thu'], reverse=True)

        return {
            "status":       "completed",
            "generated_at": datetime.now().isoformat(),
            "filters":      {"from_date": from_date, "to_date": to_date},
            "summary": {
                "total_revenue":           round(total_revenue, 2),
                "total_quantity_sold":      total_qty_sold,
                "total_quantity_remaining": int(total_qty_remaining),
                "total_products":           total_products,
            },
            "items": items,
        }
    finally:
        db.close()


def _do_debt_report() -> dict:
    """Logic báo cáo công nợ — không phụ thuộc Celery."""
    from app.database import SessionLocal
    from app.models import Invoice

    db = SessionLocal()
    try:
        unpaid      = db.query(Invoice).filter(
            ~Invoice.trang_thai.ilike('%đã thanh toán%')
        ).all()
        today       = date.today()
        total_debt  = sum(float(inv.tong_tien or 0) for inv in unpaid)
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
            "status":       "completed",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_debt":     round(total_debt, 2),
                "overdue_debt":   round(overdue_debt, 2),
                "debt_customers": debt_customers,
                "avg_debt":       round(avg_debt, 2),
            },
            "items": items,
        }
    finally:
        db.close()


# ── Celery task wrappers ──────────────────────────────────────────────────────

@shared_task(
    bind=True,
    name="app.tasks.report_tasks.generate_revenue_report",
    max_retries=3,
    default_retry_delay=10,
)
def generate_revenue_report(self, from_date=None, to_date=None):
    try:
        return _do_revenue_report(from_date, to_date)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@shared_task(
    bind=True,
    name="app.tasks.report_tasks.generate_debt_report",
    max_retries=3,
    default_retry_delay=10,
)
def generate_debt_report(self):
    try:
        return _do_debt_report()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)