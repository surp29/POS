"""
Test cleanup_integration_events.py — job dọn dẹp outbox event cũ (retention
90 ngày mặc định), chạy độc lập qua cron ngoài (KHÔNG phải scheduler trong
process — xem docstring script để biết lý do: POS chạy gunicorn --workers 2,
scheduler trong-process sẽ chạy trùng ở mỗi worker).
"""
from datetime import datetime, timedelta

from app.models import IntegrationEvent
from cleanup_integration_events import cleanup_integration_events


def _make_event(db, created_at, event_type="product.updated"):
    event = IntegrationEvent(
        event_type=event_type, entity_type="product", entity_id="1",
        payload={"sku": "X"}, created_at=created_at,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def test_deletes_only_events_older_than_retention(db):
    # Lấy id ra biến thường TRƯỚC khi cleanup — cleanup dùng
    # query.delete(synchronize_session=False) (bulk delete, không đồng bộ lại
    # identity map ORM), nên object Python cũ truy cập .id SAU khi hàng đã bị
    # xóa sẽ ObjectDeletedError.
    old_event_id = _make_event(db, datetime.utcnow() - timedelta(days=95)).id
    recent_event_id = _make_event(db, datetime.utcnow() - timedelta(days=10)).id

    deleted_count = cleanup_integration_events(retention_days=90, db=db)

    assert deleted_count == 1
    assert db.query(IntegrationEvent).filter(IntegrationEvent.id == old_event_id).first() is None
    assert db.query(IntegrationEvent).filter(IntegrationEvent.id == recent_event_id).first() is not None


def test_dry_run_counts_but_does_not_delete(db):
    old_event = _make_event(db, datetime.utcnow() - timedelta(days=95))

    counted = cleanup_integration_events(retention_days=90, dry_run=True, db=db)

    assert counted == 1
    assert db.query(IntegrationEvent).filter(IntegrationEvent.id == old_event.id).first() is not None


def test_custom_retention_days_respected(db):
    event_id = _make_event(db, datetime.utcnow() - timedelta(days=35)).id

    deleted_count = cleanup_integration_events(retention_days=30, db=db)

    assert deleted_count == 1
    assert db.query(IntegrationEvent).filter(IntegrationEvent.id == event_id).first() is None


def test_no_old_events_deletes_nothing(db):
    recent_event = _make_event(db, datetime.utcnow() - timedelta(days=1))

    deleted_count = cleanup_integration_events(retention_days=90, db=db)

    assert deleted_count == 0
    assert db.query(IntegrationEvent).filter(IntegrationEvent.id == recent_event.id).first() is not None
