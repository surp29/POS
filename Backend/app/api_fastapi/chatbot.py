"""
Backend: app/api_fastapi/chatbot.py — Fixed version
Fix:
 - "Sản phẩm sắp hết" dùng ngưỡng 1/3 lượng nhập ban đầu (không phải cố định <= 20)
 - "Phân tích tồn kho" tách riêng khỏi "sắp hết"
 - "Đề xuất đặt hàng" dựa đúng tốc độ bán + ngưỡng 1/3
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, timedelta, date
from ..database import get_db
from ..models import Product, Warehouse, Order, OrderItem, Invoice, InvoiceItem
from ..logger import log_info, log_error, log_success
from typing import Optional

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sales_data(product_code: str, days: int, db: Session) -> dict:
    end = date.today()
    start = end - timedelta(days=days)
    qty = db.query(func.sum(InvoiceItem.so_luong)).join(
        Invoice, InvoiceItem.invoice_id == Invoice.id
    ).filter(and_(
        Invoice.ngay_hd >= start,
        Invoice.ngay_hd <= end,
        Invoice.trang_thai.ilike('%đã thanh toán%'),
        InvoiceItem.product_code == product_code
    )).scalar() or 0
    return {"qty": int(qty), "rate": round(int(qty) / days, 3) if days > 0 else 0}


def _initial_stock(product_code: str, db: Session) -> int:
    """Tổng đã nhập = tồn kho hiện tại + tổng đã bán."""
    p = db.query(Product).filter(Product.ma_sp == product_code).first()
    w = db.query(Warehouse).filter(Warehouse.ma_sp == product_code).first()
    current = int((w.so_luong if w else (p.so_luong if p else 0)) or 0)
    sold = int(db.query(func.sum(InvoiceItem.so_luong)).join(
        Invoice, InvoiceItem.invoice_id == Invoice.id
    ).filter(and_(
        Invoice.trang_thai.ilike('%đã thanh toán%'),
        InvoiceItem.product_code == product_code
    )).scalar() or 0)
    return current + sold


def _build_suggestion(p: Product, w: Optional[Warehouse], db: Session) -> dict:
    current = int((w.so_luong if w else p.so_luong or 0))
    s7  = _sales_data(p.ma_sp, 7,  db)
    s30 = _sales_data(p.ma_sp, 30, db)
    rate = s7["rate"] if s7["rate"] > 0 else s30["rate"]
    days_left = int(current / rate) if rate > 0 else (0 if current <= 0 else 9999)
    initial = _initial_stock(p.ma_sp, db)
    rec = max(int(rate * 45 * 1.2), 5) if rate > 0 else max(initial, 20)
    priority = "high" if days_left <= 7 or current <= 0 else "normal"
    return {
        "ma_sp": p.ma_sp,
        "product_name": p.ten_sp,
        "current_stock": current,
        "initial_stock": initial,
        "sales_rate": round(rate, 2),
        "days_until_out": days_left if days_left < 9999 else "N/A",
        "recommended_quantity": rec,
        "priority": priority,
        "gia_nhap": float(w.gia_nhap if w else p.gia_von or 0),
        "is_best_seller": False,
    }


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/analyze")
def analyze_and_suggest(message: dict, db: Session = Depends(get_db)):
    msg = message.get("message", "").lower().strip()
    log_info("CHATBOT", f"msg: {msg}")

    # ── ĐỀ XUẤT ĐẶT HÀNG ─────────────────────────────────────────────────────
    if any(k in msg for k in ["đề xuất", "đặt hàng", "reorder", "suggest"]):
        products = db.query(Product).all()
        results = []
        for p in products:
            w = db.query(Warehouse).filter(Warehouse.ma_sp == p.ma_sp).first()
            s = _build_suggestion(p, w, db)
            current = s["current_stock"]
            initial = s["initial_stock"]
            rate    = s["sales_rate"]
            days    = s["days_until_out"]
            # Đề xuất khi: sắp hết trong 30 ngày, hoặc tồn < 1/3 ban đầu, hoặc hết hàng
            if (isinstance(days, int) and days <= 30) or \
               (initial > 0 and current < initial / 3) or \
               current <= 0:
                results.append(s)

        results.sort(key=lambda x: (
            0 if x["priority"] == "high" else 1,
            x["days_until_out"] if isinstance(x["days_until_out"], int) else 999
        ))
        results = results[:6]

        if results:
            urgent = sum(1 for r in results if r["priority"] == "high")
            txt = f"Đã phân tích tồn kho và tìm thấy {len(results)} sản phẩm cần đặt hàng"
            if urgent:
                txt += f" ({urgent} khẩn cấp)"
            txt += ".\n\nDựa trên tốc độ bán và tồn kho hiện tại:"
        else:
            txt = "Tất cả sản phẩm đều đủ tồn kho. Không cần đặt hàng khẩn cấp lúc này."
        return {"response": txt, "suggestions": results, "type": "reorder"}

    # ── SẮP HẾT — dùng ngưỡng 1/3 ───────────────────────────────────────────
    elif any(k in msg for k in ["sắp hết", "hết hàng", "nhập hàng", "low stock", "tồn thấp"]):
        products = db.query(Product).all()
        low = []
        for p in products:
            w = db.query(Warehouse).filter(Warehouse.ma_sp == p.ma_sp).first()
            current = int((w.so_luong if w else p.so_luong or 0))
            initial = _initial_stock(p.ma_sp, db)
            threshold = initial / 3 if initial > 0 else 10
            if current < threshold or current <= 0:
                s = _build_suggestion(p, w, db)
                pct = round(current / initial * 100, 1) if initial > 0 else 0
                s["pct_remaining"] = pct
                s["threshold_1_3"] = int(threshold)
                low.append(s)

        low.sort(key=lambda x: (0 if x["current_stock"] <= 0 else 1, x.get("pct_remaining", 100)))
        low = low[:6]

        if low:
            out = sum(1 for l in low if l["current_stock"] <= 0)
            txt = f"Tìm thấy {len(low)} sản phẩm có tồn kho dưới 1/3 lượng nhập ban đầu"
            if out:
                txt += f" ({out} sản phẩm đã hết hàng hoàn toàn)"
            txt += ".\n\nGợi ý: nhập thêm hàng để tránh mất doanh thu."
        else:
            txt = "Tất cả sản phẩm đều còn trên 1/3 tồn kho. Không có sản phẩm nào sắp hết."
        return {"response": txt, "suggestions": low, "type": "low_stock"}

    # ── PHÂN TÍCH TỒN KHO ────────────────────────────────────────────────────
    elif any(k in msg for k in ["phân tích", "tồn kho", "analysis", "thống kê", "inventory"]):
        products = db.query(Product).all()
        analysis = []
        for p in products:
            w = db.query(Warehouse).filter(Warehouse.ma_sp == p.ma_sp).first()
            s = _build_suggestion(p, w, db)
            current  = s["current_stock"]
            initial  = s["initial_stock"]
            rate     = s["sales_rate"]
            days     = s["days_until_out"]

            if current <= 0:
                status = "❌ Hết hàng"; order = 0
            elif rate == 0 and current > 0:
                status = "📦 Tồn chậm (chưa bán)"; order = 4
            elif isinstance(days, int) and days < 7:
                status = "🔴 Sắp hết (< 7 ngày)"; order = 1
            elif isinstance(days, int) and days < 30:
                status = "🟡 Cần nhập thêm"; order = 2
            elif rate > 0:
                status = "🟢 Bán tốt"; order = 3
            else:
                status = "⚪ Ổn định"; order = 5

            s["status"] = status
            s["priority_order"] = order
            analysis.append(s)

        analysis.sort(key=lambda x: (x["priority_order"], -x["sales_rate"]))

        total = len(analysis)
        out   = sum(1 for a in analysis if a["current_stock"] <= 0)
        slow  = sum(1 for a in analysis if "Tồn chậm" in a.get("status",""))
        hot   = sum(1 for a in analysis if "Bán tốt" in a.get("status",""))
        need  = sum(1 for a in analysis if a["priority_order"] <= 2)

        txt  = f"Phân tích tổng quan kho hàng:\n\n"
        txt += f"• Tổng sản phẩm: {total}\n"
        txt += f"• Đang bán tốt: {hot}\n"
        txt += f"• Cần nhập thêm: {need}\n"
        txt += f"• Hết hàng: {out}\n"
        txt += f"• Tồn chậm (chưa bán): {slow}\n\n"
        txt += "Chi tiết từng sản phẩm hiển thị bên dưới."
        return {"response": txt, "suggestions": analysis[:8], "type": "inventory"}

    # ── BÁO CÁO DOANH THU ────────────────────────────────────────────────────
    elif any(k in msg for k in ["doanh thu", "revenue", "báo cáo", "report", "tài chính"]):
        today = date.today()
        def rev(days):
            return float(db.query(func.sum(Invoice.tong_tien)).filter(and_(
                Invoice.ngay_hd >= today - timedelta(days=days),
                Invoice.trang_thai.ilike('%đã thanh toán%')
            )).scalar() or 0)

        r7, r30, r90 = rev(7), rev(30), rev(90)
        n_paid = db.query(func.count(Invoice.id)).filter(and_(
            Invoice.ngay_hd >= today - timedelta(30),
            Invoice.trang_thai.ilike('%đã thanh toán%')
        )).scalar() or 0
        unpaid = db.query(Invoice).filter(~Invoice.trang_thai.ilike('%đã thanh toán%')).all()
        debt   = sum(float(i.tong_tien or 0) for i in unpaid)

        txt  = f"Báo cáo doanh thu:\n\n"
        txt += f"• 7 ngày qua:  {r7:,.0f} VNĐ\n"
        txt += f"• 30 ngày qua: {r30:,.0f} VNĐ\n"
        txt += f"• 90 ngày qua: {r90:,.0f} VNĐ\n"
        txt += f"• HĐ đã thanh toán (30 ngày): {n_paid}\n"
        txt += f"• Tổng công nợ: {debt:,.0f} VNĐ ({len(unpaid)} hóa đơn)\n"
        return {"response": txt, "suggestions": [], "type": "revenue"}

    # ── BÁN CHẠY ─────────────────────────────────────────────────────────────
    elif any(k in msg for k in ["bán chạy", "best sell", "top", "nhiều nhất", "hot"]):
        today = date.today()
        rows = db.query(
            InvoiceItem.product_code,
            InvoiceItem.product_name,
            func.sum(InvoiceItem.so_luong).label("qty"),
            func.sum(InvoiceItem.total_price).label("rev"),
        ).join(Invoice, InvoiceItem.invoice_id == Invoice.id).filter(and_(
            Invoice.ngay_hd >= today - timedelta(30),
            Invoice.trang_thai.ilike('%đã thanh toán%')
        )).group_by(InvoiceItem.product_code, InvoiceItem.product_name).order_by(desc("qty")).limit(8).all()

        if rows:
            txt = f"Top {len(rows)} sản phẩm bán chạy trong 30 ngày qua:\n\n"
            sugg = []
            for i, r in enumerate(rows, 1):
                p = db.query(Product).filter(Product.ma_sp == r.product_code).first()
                w = db.query(Warehouse).filter(Warehouse.ma_sp == r.product_code).first()
                stock = int((w.so_luong if w else p.so_luong if p else 0) or 0)
                txt += f"{i}. {r.product_name} — Bán: {int(r.qty)} | DT: {float(r.rev):,.0f} VNĐ | Tồn: {stock}\n"
                if stock < 20 and p:
                    s = _build_suggestion(p, w, db)
                    s["is_best_seller"] = True
                    sugg.append(s)
            if sugg:
                txt += f"\n{len(sugg)} sản phẩm bán chạy đang tồn kho thấp!"
        else:
            txt = "Chưa có dữ liệu bán hàng trong 30 ngày qua."
            sugg = []
        return {"response": txt, "suggestions": sugg, "type": "best_seller"}

    # ── DEFAULT ───────────────────────────────────────────────────────────────
    else:
        txt  = "Xin chào! Tôi là Thư ký ảo AI. Tôi có thể giúp bạn:\n\n"
        txt += "• Đề xuất đặt hàng — phân tích tốc độ bán\n"
        txt += "• Sản phẩm sắp hết — cảnh báo tồn < 1/3 lượng nhập\n"
        txt += "• Phân tích tồn kho — toàn cảnh kho hàng\n"
        txt += "• Sản phẩm bán chạy — top doanh thu\n"
        txt += "• Báo cáo doanh thu — tổng hợp 7/30/90 ngày\n\n"
        txt += "Hãy bấm các nút gợi ý hoặc nhập câu hỏi!"
        return {"response": txt, "suggestions": [], "type": "help"}


@router.post("/create-order")
def create_reorder(payload: dict, db: Session = Depends(get_db)):
    product_code = payload.get("product_code")
    quantity     = payload.get("quantity")
    if not product_code or not quantity:
        raise HTTPException(400, "Thiếu thông tin sản phẩm hoặc số lượng")
    p = db.query(Product).filter(Product.ma_sp == product_code).first()
    if not p:
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    w = db.query(Warehouse).filter(Warehouse.ma_sp == product_code).first()
    price = float(w.gia_nhap if w else p.gia_von or 0)
    code  = f"CHATBOT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        order = Order(ma_don_hang=code,
                      thong_tin_kh="Đơn đặt hàng từ Thư ký ảo AI",
                      ngay_tao=datetime.now().date(),
                      so_luong=quantity, tong_tien=quantity*price, trang_thai="Chờ xử lý")
        db.add(order); db.flush()
        db.add(OrderItem(order_id=order.id, product_id=p.id,
                         so_luong=quantity, don_gia=price, total_price=quantity*price))
        db.commit(); db.refresh(order)
        log_success("CHATBOT", f"Đơn {code} cho {product_code} x{quantity}")
        return {"success": True, "order_code": code, "order_id": order.id,
                "message": f"Đã tạo đơn {code} cho {quantity} sản phẩm {p.ten_sp}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Lỗi tạo đơn: {str(e)}")