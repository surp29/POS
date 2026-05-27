"""
Celery tasks cho notifications — gửi email async.
"""
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from celery import shared_task

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict:
    return {
        "host":     os.getenv("SMTP_HOST",     "smtp.gmail.com"),
        "port":     int(os.getenv("SMTP_PORT", "587")),
        "user":     os.getenv("SMTP_USER",     ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from":     os.getenv("SMTP_FROM",     "POS System <noreply@pos.local>"),
    }


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Gửi email qua SMTP. Trả về True nếu thành công."""
    config = _get_smtp_config()
    if not config["user"] or not config["password"]:
        logger.warning("SMTP chưa cấu hình — bỏ qua gửi email (set SMTP_USER và SMTP_PASSWORD)")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = config["from"]
    msg["To"]      = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(config["host"], config["port"]) as server:
        server.ehlo()
        server.starttls()
        server.login(config["user"], config["password"])
        server.sendmail(config["from"], to, msg.as_string())
    return True


@shared_task(
    bind=True,
    name="app.tasks.notification_tasks.send_order_confirmation",
    max_retries=3,
    default_retry_delay=30,
)
def send_order_confirmation(
    self,
    order_id:     int,
    ma_don_hang:  str,
    thong_tin_kh: str,
    tong_tien:    float,
    email:        str,
) -> dict:
    """Gửi email xác nhận đơn hàng cho khách."""
    try:
        subject = f"Xác nhận đơn hàng {ma_don_hang}"
        html_body = f"""
        <html><body style="font-family: Arial, sans-serif; color: #333;">
          <div style="max-width:600px;margin:0 auto;padding:20px;">
            <h2 style="color:#2c7a4b;">✅ Đơn hàng đã được xác nhận</h2>
            <p>Xin chào <strong>{thong_tin_kh}</strong>,</p>
            <p>Đơn hàng của bạn đã được tiếp nhận thành công.</p>
            <div style="background:#f5f5f5;padding:16px;border-radius:8px;margin:16px 0;">
              <table style="width:100%;">
                <tr><td><strong>Mã đơn hàng:</strong></td><td>{ma_don_hang}</td></tr>
                <tr><td><strong>Tổng tiền:</strong></td>
                    <td style="color:#e53e3e;font-weight:bold;">{tong_tien:,.0f} VND</td></tr>
                <tr><td><strong>Thời gian:</strong></td>
                    <td>{datetime.now().strftime('%H:%M %d/%m/%Y')}</td></tr>
              </table>
            </div>
            <p>Chúng tôi sẽ xử lý đơn hàng trong thời gian sớm nhất.</p>
          </div>
        </body></html>
        """
        success = _send_email(email, subject, html_body)
        result = {
            "status":   "sent" if success else "skipped_no_smtp",
            "order_id": order_id,
            "email":    email,
            "sent_at":  datetime.now().isoformat(),
        }
        logger.info(f"Email for order {ma_don_hang}: {result['status']}")
        return result

    except smtplib.SMTPException as exc:
        logger.error(f"SMTP error for order {ma_don_hang}: {exc}")
        raise self.retry(exc=exc, countdown=30)
    except Exception as exc:
        logger.error(f"Unexpected error for {ma_don_hang}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    bind=True,
    name="app.tasks.notification_tasks.send_low_stock_alert",
    max_retries=2,
)
def send_low_stock_alert(
    self,
    product_code: str,
    product_name: str,
    current_qty:  int,
    threshold:    int = 10,
    admin_email:  str = "",
) -> dict:
    """Gửi cảnh báo tồn kho thấp cho admin."""
    try:
        email = admin_email or os.getenv("ADMIN_EMAIL", "")
        if not email:
            return {"status": "skipped", "reason": "no admin email configured"}

        subject   = f"⚠️ Cảnh báo tồn kho thấp: {product_name}"
        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;">
          <div style="max-width:600px;margin:0 auto;padding:20px;">
            <h2 style="color:#e53e3e;">⚠️ Tồn kho thấp</h2>
            <p>Sản phẩm <strong>{product_name}</strong> ({product_code})
               chỉ còn <strong style="color:#e53e3e;">{current_qty}</strong> đơn vị.</p>
            <p>Ngưỡng cảnh báo: {threshold} đơn vị. Vui lòng nhập thêm hàng.</p>
          </div>
        </body></html>
        """
        success = _send_email(email, subject, html_body)
        return {
            "status":      "sent" if success else "skipped_no_smtp",
            "product":     product_code,
            "current_qty": current_qty,
            "sent_at":     datetime.now().isoformat(),
        }
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)