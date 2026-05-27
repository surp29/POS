# Backend/app/services/customers.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Account, Order, Invoice, InvoiceItem

def safe_name(name: str | None) -> str:
    return (name or '').strip() or 'Khách vãng lai'

def calc_customer_tier(total_amount: float) -> dict:
    """Tính phân hạng tier cho khách hàng dựa trên tổng chi tiêu."""
    labels = [
        {'name': 'Đồng', 'color': '#cd7f32'},
        {'name': 'Bạc', 'color': '#bcc6cc'},
        {'name': 'Vàng', 'color': '#ffd700'},
        {'name': 'Bạch kim', 'color': '#e5e4e2'},
        {'name': 'Kim cương', 'color': '#00e5ee'},
    ]
    thresholds = [0, 30000000]
    for i in range(2, len(labels)):
        prev = thresholds[i-1]
        thresholds.append(prev + 10_000_000 + int(prev * 0.5))
    for i in reversed(range(len(thresholds))):
        if total_amount >= thresholds[i]:
            return { 'tierName': labels[i]['name'], 'tierColor': labels[i]['color'], 'tierLevel': i+1, 'tierMinAmount': thresholds[i] }
    return { 'tierName': labels[0]['name'], 'tierColor': labels[0]['color'], 'tierLevel': 1, 'tierMinAmount': thresholds[0] }

def customer_aggregates(db: Session):
    """Trả về tổng hợp theo khách hàng: orders count, total quantity, total amount, debt..."""
    order_rows = (
        db.query(
            Order.thong_tin_kh.label('customer_name'),
            func.count(Order.id).label('order_count'),
            func.coalesce(func.sum(Order.so_luong), 0).label('total_quantity'),
            func.coalesce(func.sum(Order.tong_tien), 0.0).label('total_amount'),
        ).group_by(Order.thong_tin_kh)
         .all()
    )
    paid_rows = (
        db.query(
            Invoice.nguoi_mua.label('customer_name'),
            func.coalesce(func.sum(Invoice.tong_tien), 0.0).label('paid_amount')
        ).filter(Invoice.trang_thai.ilike('%đã thanh toán%'))
         .group_by(Invoice.nguoi_mua)
         .all()
    )
    paid_map = { safe_name(r.customer_name): float(r.paid_amount or 0) for r in paid_rows }
    results = []
    for r in order_rows:
        name = safe_name(r.customer_name)
        total_amount = float(r.total_amount or 0)
        paid = paid_map.get(name, 0.0)
        debt = max(total_amount - paid, 0.0)
        results.append({
            'customerName': name,
            'orderCount': int(r.order_count or 0),
            'totalQuantity': int(r.total_quantity or 0),
            'totalAmount': total_amount,
            'totalDebt': debt,
        })
    return results

def customer_leaderboard(db: Session, limit: int = 100):
    """Leaderboard by total amount spent from paid invoices, combined with customer info from Account.
    Chỉ hiển thị khách hàng có tài khoản trong Account (loại bỏ khách vãng lai)."""
    # Lấy tất cả khách hàng từ Account trước
    accounts = db.query(Account).all()
    account_map = {acc.ten_tk: acc for acc in accounts}
    
    # Chỉ lấy các tên khách hàng có trong Account
    valid_customer_names = set(account_map.keys())
    
    # Lấy dữ liệu từ các hóa đơn đã thanh toán, chỉ lấy khách hàng có trong Account
    paid_invoices = (
        db.query(
            Invoice.nguoi_mua.label('customer_name'),
            func.coalesce(func.sum(Invoice.tong_tien), 0.0).label('total_amount'),
            func.coalesce(func.sum(InvoiceItem.so_luong), 0).label('total_quantity'),
            func.count(Invoice.id).label('invoice_count'),
        )
        .outerjoin(InvoiceItem, Invoice.id == InvoiceItem.invoice_id)
        .filter(Invoice.trang_thai.ilike('%đã thanh toán%'))
        .filter(Invoice.nguoi_mua.in_(valid_customer_names))  # Chỉ lấy khách hàng có trong Account
        .group_by(Invoice.nguoi_mua)
        .order_by(func.coalesce(func.sum(Invoice.tong_tien), 0.0).desc())
        .limit(limit)
        .all()
    )
    
    results = []
    for inv in paid_invoices:
        customer_name = safe_name(inv.customer_name)
        
        # Bỏ qua nếu là "Khách vãng lai" hoặc không có trong Account
        if customer_name == 'Khách vãng lai' or customer_name not in account_map:
            continue
        
        account = account_map.get(customer_name)
        if not account:  # Đảm bảo account tồn tại
            continue
        
        total_spent = float(inv.total_amount or 0)
        
        # Tính hạn mức thành viên dựa trên tier
        tier_info = calc_customer_tier(total_spent)
        tier_level = tier_info.get('tierLevel', 1)
        tier_min = tier_info.get('tierMinAmount', 0)
        
        # Tính hạn mức: tier tiếp theo - tier hiện tại
        if tier_level < 5:  # Chưa phải kim cương
            next_tier_min = tier_min + 10_000_000 + int(tier_min * 0.5)
            credit_limit = next_tier_min - tier_min
        else:  # Kim cương - hạn mức cao
            credit_limit = tier_min * 2
        
        results.append({
            'customerName': customer_name,
            'customerId': account.id,
            'customerCode': account.ma_khach_hang if account else None,
            'email': account.email if account else None,
            'phone': account.so_dt if account else None,
            'totalAmount': total_spent,
            'totalQuantity': int(inv.total_quantity or 0),
            'invoiceCount': int(inv.invoice_count or 0),
            'creditLimit': credit_limit,
            'tierName': tier_info.get('tierName', 'Đồng'),
            'tierColor': tier_info.get('tierColor', '#cd7f32'),
            'tierLevel': tier_level,
        })
    
    return results

def customer_debts_from_invoices(db: Session):
    """Lấy công nợ từ các hóa đơn chưa thanh toán, kết hợp với thông tin khách hàng từ Account."""
    # Lấy các hóa đơn chưa thanh toán
    unpaid_invoices = (
        db.query(
            Invoice.nguoi_mua.label('customer_name'),
            func.count(Invoice.id).label('invoice_count'),
            func.coalesce(func.sum(Invoice.tong_tien), 0.0).label('total_debt'),
            func.coalesce(func.sum(InvoiceItem.so_luong), 0).label('total_quantity'),
        )
        .outerjoin(InvoiceItem, Invoice.id == InvoiceItem.invoice_id)
        .filter(~Invoice.trang_thai.ilike('%đã thanh toán%'))
        .group_by(Invoice.nguoi_mua)
        .all()
    )
    
    # Lấy tất cả khách hàng từ Account
    accounts = db.query(Account).all()
    account_map = {acc.ten_tk: acc for acc in accounts}
    
    # Tính tổng chi tiêu từ các hóa đơn đã thanh toán để tính hạn mức
    paid_invoices = (
        db.query(
            Invoice.nguoi_mua.label('customer_name'),
            func.coalesce(func.sum(Invoice.tong_tien), 0.0).label('total_spent')
        )
        .filter(Invoice.trang_thai.ilike('%đã thanh toán%'))
        .group_by(Invoice.nguoi_mua)
        .all()
    )
    spent_map = {safe_name(r.customer_name): float(r.total_spent or 0) for r in paid_invoices}
    
    results = []
    for inv in unpaid_invoices:
        customer_name = safe_name(inv.customer_name)
        account = account_map.get(customer_name)
        total_debt = float(inv.total_debt or 0)
        
        # Chỉ thêm khách hàng có công nợ > 0
        if total_debt <= 0:
            continue
        
        results.append({
            'customerName': customer_name,
            'customerId': account.id if account else None,
            'customerCode': account.ma_khach_hang if account else None,
            'email': account.email if account else None,
            'phone': account.so_dt if account else None,
            'address': account.dia_chi if account else None,
            'invoiceCount': int(inv.invoice_count or 0),
            'totalDebt': total_debt,
        })
    
    # Sắp xếp theo công nợ giảm dần
    results.sort(key=lambda x: x['totalDebt'], reverse=True)
    
    return results
