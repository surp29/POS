# Backend/app/services/invoices.py
from sqlalchemy.orm import Session
from ..models import Invoice, Account, Product
from datetime import datetime

def update_debt_for_customer(customer_name: str, db: Session):
    """Cập nhật bảng công nợ cho khách hàng."""
    try:
        invoices = db.query(Invoice).filter(Invoice.nguoi_mua == customer_name).all()
        if not invoices:
            return
        total_debt = sum(float(invoice.tong_tien or 0) for invoice in invoices)
        paid_amount = sum(
            float(invoice.tong_tien or 0)
            for invoice in invoices
            if str(invoice.trang_thai or "") == "Đã thanh toán"
        )
        remaining_debt = total_debt - paid_amount
        # The following lines were related to Debt model and are removed as per the edit hint.
        # debt_record = db.query(Debt).filter(Debt.customer_name == customer_name).first()
        # if debt_record:
        #     debt_record.total_debt = total_debt
        #     debt_record.paid_amount = paid_amount
        #     debt_record.remaining_debt = remaining_debt
        #     debt_record.status = "Hết nợ" if remaining_debt <= 0 else "Còn nợ"
        #     if paid_amount > 0:
        #         debt_record.last_payment_date = datetime.now()
        # else:
        #     debt_record = Debt(
        #         customer_name=customer_name,
        #         total_debt=total_debt,
        #         paid_amount=paid_amount,
        #         remaining_debt=remaining_debt,
        #         status="Hết nợ" if remaining_debt <= 0 else "Còn nợ",
        #         created_at=datetime.now(),
        #     )
        #     db.add(debt_record)
        db.commit()
        print(f"✓ Đã cập nhật công nợ cho {customer_name}: Tổng={total_debt:,.0f}, Đã trả={paid_amount:,.0f}, Còn nợ={remaining_debt:,.0f}")
    except Exception as e:
        print(f"× Lỗi cập nhật công nợ cho {customer_name}: {e}")
        db.rollback()
