# Backend/app/services/customers.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Account, Order, Invoice, InvoiceItem

def safe_name(name: str | None) -> str:
    return (name or '').strip() or 'Khách vãng lai'


def _consolidate_by_account(rows, id_field: str, name_field: str, value_fields: list[str],
                              account_by_id: dict, account_by_name: dict):
    """Gom cac dong (tu 1 SQL group by id_field, name_field) ve dung 1 khach hang that,
    bat ke dong nao co customer_id, dong nao chi co ten text (du lieu cu / khach chua
    gan tai khoan luc ban). Neu 2 dong khac nhau (vd 1 dong co customer_id=6, 1 dong
    khong co nhung ten khop voi account id=6) deu quy ve cung 1 Account, chung se duoc
    cong don vao CUNG 1 bucket — day la diem khac biet quan trong so voi chi merge theo
    (customer_id, ten) tho, tranh tao 2 dong ket qua trung nhau cho cung 1 khach trong
    giai doan chuyen tiep (du lieu cu chua co customer_id, du lieu moi da co).

    Tra ve list dict: {'account': Account|None, 'customer_name': str, **sums}.
    """
    buckets: dict = {}
    for r in rows:
        cid  = getattr(r, id_field)
        name = safe_name(getattr(r, name_field))
        account = account_by_id.get(cid) if cid is not None else account_by_name.get(name)
        identity = ('account', account.id) if account else ('name', name)

        b = buckets.get(identity)
        if b is None:
            b = {'account': account, 'customer_name': account.ten_tk if account else name}
            for f in value_fields:
                b[f] = 0.0
            buckets[identity] = b
        elif account and name != 'Khách vãng lai':
            b['customer_name'] = name
        for f in value_fields:
            b[f] += float(getattr(r, f) or 0)
    return list(buckets.values())


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
    """Trả về tổng hợp theo khách hàng: orders count, total quantity, total amount, debt.

    Gom theo tài khoản THẬT đã khớp được (qua Order.customer_id / Invoice.customer_id
    khi có, hoặc qua so tên khi hóa đơn/đơn hàng cũ chưa có customer_id) — 1 khách luôn
    ra đúng 1 dòng kết quả dù có hay không có customer_id ở từng hóa đơn/đơn hàng.
    """
    accounts = db.query(Account).all()
    account_by_id   = {acc.id: acc for acc in accounts}
    account_by_name = {acc.ten_tk: acc for acc in accounts}

    order_rows = (
        db.query(
            Order.customer_id.label('customer_id'),
            Order.thong_tin_kh.label('customer_name'),
            func.count(Order.id).label('order_count'),
            func.coalesce(func.sum(Order.so_luong), 0).label('total_quantity'),
            func.coalesce(func.sum(Order.tong_tien), 0.0).label('total_amount'),
        ).group_by(Order.customer_id, Order.thong_tin_kh)
         .all()
    )
    paid_rows = (
        db.query(
            Invoice.customer_id.label('customer_id'),
            Invoice.nguoi_mua.label('customer_name'),
            func.coalesce(func.sum(Invoice.tong_tien), 0.0).label('paid_amount')
        ).filter(Invoice.trang_thai.ilike('%đã thanh toán%'))
         .group_by(Invoice.customer_id, Invoice.nguoi_mua)
         .all()
    )

    orders_consolidated = _consolidate_by_account(
        order_rows, 'customer_id', 'customer_name',
        ['order_count', 'total_quantity', 'total_amount'],
        account_by_id, account_by_name,
    )
    paid_consolidated = _consolidate_by_account(
        paid_rows, 'customer_id', 'customer_name', ['paid_amount'],
        account_by_id, account_by_name,
    )
    paid_by_identity = {
        (('account', b['account'].id) if b['account'] else ('name', b['customer_name'])): b['paid_amount']
        for b in paid_consolidated
    }

    results = []
    for b in orders_consolidated:
        account = b['account']
        identity = ('account', account.id) if account else ('name', b['customer_name'])
        paid = paid_by_identity.get(identity, 0.0)
        total_amount = b['total_amount']
        debt = max(total_amount - paid, 0.0)
        results.append({
            'customerName': b['customer_name'],
            'customerId': account.id if account else None,
            'orderCount': int(b['order_count']),
            'totalQuantity': int(b['total_quantity']),
            'totalAmount': total_amount,
            'totalDebt': debt,
        })
    return results

def customer_leaderboard(db: Session, limit: int = 100):
    """Leaderboard by total amount spent from paid invoices, combined with customer info
    from Account. Chỉ hiển thị khách hàng có tài khoản trong Account (loại bỏ khách vãng
    lai) — khớp qua Invoice.customer_id khi có, fallback so tên cho hóa đơn cũ, và gom
    về đúng 1 dòng / tài khoản dù 2 nguồn khớp đó trộn lẫn nhau."""
    accounts = db.query(Account).all()
    account_by_id   = {acc.id: acc for acc in accounts}
    account_by_name = {acc.ten_tk: acc for acc in accounts}

    paid_invoices = (
        db.query(
            Invoice.customer_id.label('customer_id'),
            Invoice.nguoi_mua.label('customer_name'),
            func.coalesce(func.sum(Invoice.tong_tien), 0.0).label('total_amount'),
            func.coalesce(func.sum(InvoiceItem.so_luong), 0).label('total_quantity'),
            func.count(Invoice.id).label('invoice_count'),
        )
        .outerjoin(InvoiceItem, Invoice.id == InvoiceItem.invoice_id)
        .filter(Invoice.trang_thai.ilike('%đã thanh toán%'))
        .group_by(Invoice.customer_id, Invoice.nguoi_mua)
        .all()
    )

    consolidated = _consolidate_by_account(
        paid_invoices, 'customer_id', 'customer_name',
        ['total_amount', 'total_quantity', 'invoice_count'],
        account_by_id, account_by_name,
    )

    results = []
    for b in consolidated:
        account = b['account']
        if not account:
            continue  # khách vãng lai / chưa có account — không lên leaderboard

        total_spent = b['total_amount']
        tier_info = calc_customer_tier(total_spent)
        tier_level = tier_info.get('tierLevel', 1)
        tier_min = tier_info.get('tierMinAmount', 0)

        if tier_level < 5:  # Chưa phải kim cương
            next_tier_min = tier_min + 10_000_000 + int(tier_min * 0.5)
            credit_limit = next_tier_min - tier_min
        else:  # Kim cương - hạn mức cao
            credit_limit = tier_min * 2

        results.append({
            'customerName': account.ten_tk,
            'customerId': account.id,
            'customerCode': account.ma_khach_hang,
            'email': account.email,
            'phone': account.so_dt,
            'totalAmount': total_spent,
            'totalQuantity': int(b['total_quantity']),
            'invoiceCount': int(b['invoice_count']),
            'creditLimit': credit_limit,
            'tierName': tier_info.get('tierName', 'Đồng'),
            'tierColor': tier_info.get('tierColor', '#cd7f32'),
            'tierLevel': tier_level,
        })

    results.sort(key=lambda x: x['totalAmount'], reverse=True)
    return results[:limit]

def customer_debts_from_invoices(db: Session):
    """Lấy công nợ từ các hóa đơn chưa thanh toán, kết hợp với thông tin khách hàng từ
    Account — khớp qua Invoice.customer_id khi có, fallback so tên cho hóa đơn cũ, gom
    về đúng 1 dòng / khách hàng dù 2 nguồn khớp đó trộn lẫn nhau."""
    unpaid_invoices = (
        db.query(
            Invoice.customer_id.label('customer_id'),
            Invoice.nguoi_mua.label('customer_name'),
            func.count(Invoice.id).label('invoice_count'),
            func.coalesce(func.sum(Invoice.tong_tien), 0.0).label('total_debt'),
            func.coalesce(func.sum(InvoiceItem.so_luong), 0).label('total_quantity'),
        )
        .outerjoin(InvoiceItem, Invoice.id == InvoiceItem.invoice_id)
        .filter(~Invoice.trang_thai.ilike('%đã thanh toán%'))
        .group_by(Invoice.customer_id, Invoice.nguoi_mua)
        .all()
    )

    accounts = db.query(Account).all()
    account_by_id   = {acc.id: acc for acc in accounts}
    account_by_name = {acc.ten_tk: acc for acc in accounts}

    consolidated = _consolidate_by_account(
        unpaid_invoices, 'customer_id', 'customer_name',
        ['invoice_count', 'total_debt', 'total_quantity'],
        account_by_id, account_by_name,
    )

    results = []
    for b in consolidated:
        account = b['account']
        total_debt = b['total_debt']

        if total_debt <= 0:
            continue

        results.append({
            'customerName': account.ten_tk if account else b['customer_name'],
            'customerId': account.id if account else None,
            'customerCode': account.ma_khach_hang if account else None,
            'email': account.email if account else None,
            'phone': account.so_dt if account else None,
            'address': account.dia_chi if account else None,
            'invoiceCount': int(b['invoice_count']),
            'totalDebt': total_debt,
        })

    results.sort(key=lambda x: x['totalDebt'], reverse=True)
    return results
