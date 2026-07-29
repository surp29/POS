#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSPOS - CLEANUP: don dep integration_events cu hon N ngay (mac dinh 90)
================================================================================
Bang `integration_events` la outbox ghi lai MOI thay doi san pham/ton kho de
Ecommerce Backend poll dong bo (xem app/services/integration_events.py) -
KHONG BAO GIO tu dong xoa, tang truong vo han neu he thong chay lau dai.

An toan de xoa event cu vi Ecommerce Backend chi can vai gio gan nhat de dong
bo binh thuong (poll_events moi 5s + full_resync moi gio la luoi an toan DOC
LAP, doc thang tu POS chu khong phu thuoc event cu con hay mat) - giu 90 ngay
la du du cho debug/audit ma khong giu mai mai.

KHONG dung APScheduler chay trong process app: POS chay gunicorn --workers 2
(xem Dockerfile), 1 scheduler trong-process se chay TRUNG o CA 2 worker moi
lan - dung dung bug da tung xay ra va duoc sua ben Ecommerce Backend (xem
docstring app/celery_app.py). Thay vao do, script nay chay DOC LAP qua
cron/scheduled task ben ngoai, giong cach dung reconcile_orders.py ben
Ecommerce Backend.

Su dung:
    cd Backend
    python cleanup_integration_events.py                        # xoa qua han 90 ngay
    python cleanup_integration_events.py --retention-days 30     # tuy chinh so ngay
    python cleanup_integration_events.py --dry-run                # chi dem, khong xoa

Vi du crontab (chay 3h sang moi ngay, tren may host chay docker compose):
    0 3 * * * docker compose -f /path/to/Backend/docker-compose.yml exec -T backend python cleanup_integration_events.py >> /var/log/pos_cleanup.log 2>&1
"""
import argparse
import sys, os, codecs
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import IntegrationEvent

DEFAULT_RETENTION_DAYS = 90


def cleanup_integration_events(retention_days: int = DEFAULT_RETENTION_DAYS, dry_run: bool = False, db=None) -> int:
    """`db` cho phép truyền session ngoài (dùng khi unit-test với DB test riêng
    — POS không có cơ chế override SessionLocal chung cho script gọi trực
    tiếp như FastAPI Depends(get_db), nên gọi SessionLocal() mặc định ở đây
    sẽ luôn trỏ tới DB THẬT, không phải DB test). Khi tự mở session (CLI thật
    sự), tự đóng lại; khi được truyền vào, để caller tự quản lý vòng đời."""
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    try:
        query = db.query(IntegrationEvent).filter(IntegrationEvent.created_at < cutoff)
        count = query.count()

        if dry_run:
            print(f"[DRY RUN] Sẽ xóa {count} event cũ hơn {retention_days} ngày (trước {cutoff.isoformat()})")
            return count

        if count:
            # bulk delete — không cần load từng object, bảng có thể rất lớn
            query.delete(synchronize_session=False)
            db.commit()
        print(f"✅ Đã xóa {count} integration_events cũ hơn {retention_days} ngày (trước {cutoff.isoformat()})")
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS,
                         help=f"Số ngày giữ lại (mặc định {DEFAULT_RETENTION_DAYS})")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ đếm, không xóa thật")
    args = parser.parse_args()

    cleanup_integration_events(retention_days=args.retention_days, dry_run=args.dry_run)
