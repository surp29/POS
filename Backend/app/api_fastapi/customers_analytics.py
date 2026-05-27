from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.customers import calc_customer_tier, customer_aggregates, customer_leaderboard, customer_debts_from_invoices

router = APIRouter(prefix="/customers-analytics", tags=["customers-analytics"])

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


