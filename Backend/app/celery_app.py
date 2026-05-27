"""
Celery application instance.
Dùng Redis db=1 cho broker/backend (db=0 dành cho cache app).
"""
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Fix: dùng rsplit để không bị lỗi nếu URL có nhiều "/0"
# "redis://redis:6379/0" -> "redis://redis:6379" + "/1"
_base = REDIS_URL.rsplit("/", 1)[0]
CELERY_BROKER  = _base + "/1"
CELERY_BACKEND = _base + "/1"

celery_app = Celery(
    "pos_tasks",
    broker=CELERY_BROKER,
    backend=CELERY_BACKEND,
    include=[
        "app.tasks.report_tasks",
        "app.tasks.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_max_retries=3,
    task_default_retry_delay=5,
    task_annotations={
        "app.tasks.report_tasks.generate_revenue_report": {"rate_limit": "10/m"},
        "app.tasks.notification_tasks.send_order_confirmation": {"rate_limit": "60/m"},
    },
)