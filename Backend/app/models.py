"""
PosPos — Database Models
========================
19 tables với đầy đủ:
  - Primary Key trên mọi table
  - Foreign Key + ondelete cascade nơi cần thiết
  - Relationship 2 chiều (back_populates) giữa các table liên quan
  - Index trên các cột query thường xuyên
  - Composite index cho query phức tạp
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship
from .database import Base


# ── Helpers ───────────────────────────────────────────────────────────────────
def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ══════════════════════════════════════════════════════════════════════════════
# USERS & PERMISSIONS
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    """Tài khoản nhân viên — dùng để đăng nhập và phân quyền."""
    __tablename__ = 'users'

    id         = Column(Integer, primary_key=True)
    username   = Column(String(50),  unique=True, nullable=False, index=True)
    password   = Column(String(255), nullable=False)
    name       = Column(String(100))
    email      = Column(String(120))
    phone      = Column(String(20))
    position   = Column(String(100))   # "Admin" → toàn quyền
    department = Column(String(100))
    status     = Column(Boolean, default=True)  # False = tài khoản bị vô hiệu hóa

    # Relationships
    permissions = relationship(
        'UserPermission', back_populates='user',
        cascade='all, delete-orphan',
    )
    schedules = relationship(
        'Schedule', back_populates='employee',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f"<User(username='{self.username}', name='{self.name}')>"


class UserPermission(Base):
    """Quyền chi tiết từng nhân viên — dạng module.action (vd: invoices.create)."""
    __tablename__ = 'user_permissions'

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=False, index=True)
    permission = Column(String(50), nullable=False, index=True)
    granted_by = Column(String(50))
    granted_at = Column(DateTime, default=_now)

    # Relationships
    user = relationship('User', back_populates='permissions')

    __table_args__ = (
        UniqueConstraint('user_id', 'permission', name='uq_user_permission'),
    )

    def __repr__(self):
        return f"<UserPermission(user={self.user_id}, perm='{self.permission}')>"


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMERS
# ══════════════════════════════════════════════════════════════════════════════

class Account(Base):
    """Khách hàng của cửa hàng."""
    __tablename__ = 'accounts'

    id             = Column(Integer, primary_key=True)
    ten_tk         = Column(String(100), nullable=False, index=True)
    ma_khach_hang  = Column(String(20),  unique=True, index=True)
    ngay_sinh      = Column(Date)
    email          = Column(String(120), index=True)
    so_dt          = Column(String(20),  index=True)
    dia_chi        = Column(String(255))
    trang_thai     = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Account(ten_tk='{self.ten_tk}', ma='{self.ma_khach_hang}')>"


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTS
# ══════════════════════════════════════════════════════════════════════════════

class ProductGroup(Base):
    """Nhóm / danh mục sản phẩm."""
    __tablename__ = 'product_groups'

    id       = Column(Integer, primary_key=True)
    ten_nhom = Column(String(100), nullable=False, unique=True, index=True)
    mo_ta    = Column(String(255))

    # Relationships
    products = relationship('Product', back_populates='group',
                            foreign_keys='Product.nhom_id')

    def __repr__(self):
        return f"<ProductGroup(ten_nhom='{self.ten_nhom}')>"


class Product(Base):
    """Sản phẩm — lưu tồn kho, giá, ảnh."""
    __tablename__ = 'products'

    id         = Column(Integer, primary_key=True)
    ma_sp      = Column(String(20),  unique=True, nullable=False, index=True)
    ten_sp     = Column(String(100), nullable=False, index=True)
    nhom_sp    = Column(String(100), index=True)   # tên nhóm (denormalized để tương thích)
    nhom_id    = Column(Integer, ForeignKey('product_groups.id', ondelete='SET NULL'),
                        nullable=True, index=True)
    so_luong   = Column(Integer, default=0)
    gia_ban    = Column(Float,   default=0.0)
    gia_chung  = Column(Float,   default=0.0)
    gia_von    = Column(Float,   default=0.0)
    don_vi     = Column(String(50), default='Cái')
    trang_thai = Column(String(50), default='active', index=True)
    mo_ta      = Column(String(255))
    image_url  = Column(String(255))

    # Relationships
    group       = relationship('ProductGroup', back_populates='products',
                               foreign_keys=[nhom_id])
    invoice_items = relationship('InvoiceItem', back_populates='product')
    order_items   = relationship('OrderItem',   back_populates='product')
    warehouses    = relationship('Warehouse',   back_populates='product',
                                 foreign_keys='Warehouse.product_id')

    def __repr__(self):
        return f"<Product(ma_sp='{self.ma_sp}', ten_sp='{self.ten_sp}')>"


class Price(Base):
    """Bảng giá dịch vụ — độc lập với sản phẩm (dùng cho dịch vụ sửa chữa...)."""
    __tablename__ = 'prices'

    id         = Column(Integer, primary_key=True)
    ma_sp      = Column(String(20),  nullable=False, unique=True, index=True)
    ten_sp     = Column(String(100), nullable=False)
    gia_chung  = Column(Float, default=0.0)
    ghi_chu    = Column(Text)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    def __repr__(self):
        return f"<Price(ma_sp='{self.ma_sp}', gia={self.gia_chung})>"


# ══════════════════════════════════════════════════════════════════════════════
# WAREHOUSE
# ══════════════════════════════════════════════════════════════════════════════

class Warehouse(Base):
    """Kho hàng — mỗi record là 1 lô nhập kho của 1 sản phẩm."""
    __tablename__ = 'warehouses'

    id         = Column(Integer, primary_key=True)
    ma_kho     = Column(String(50), unique=True, nullable=False, index=True)
    ten_kho    = Column(String(100), nullable=False)
    # FK đến products (thay thế string ma_sp)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='SET NULL'),
                        nullable=True, index=True)
    ma_sp      = Column(String(20), nullable=False, index=True)  # giữ để tương thích
    gia_nhap   = Column(Float,   default=0.0)
    so_luong   = Column(Integer, default=0)
    dia_chi    = Column(String(255))
    dien_thoai = Column(String(20))
    ghi_chu    = Column(Text)
    trang_thai = Column(String(50), default='active', index=True)

    # Relationships
    product = relationship('Product', back_populates='warehouses',
                           foreign_keys=[product_id])

    def __repr__(self):
        return f"<Warehouse(ma_kho='{self.ma_kho}', ma_sp='{self.ma_sp}')>"


# ══════════════════════════════════════════════════════════════════════════════
# ORDERS & INVOICES
# ══════════════════════════════════════════════════════════════════════════════

class Order(Base):
    """Đơn hàng — phiếu yêu cầu từ khách, có thể chưa thanh toán."""
    __tablename__ = 'orders'

    id            = Column(Integer, primary_key=True)
    ma_don_hang   = Column(String(50), unique=True, nullable=False, index=True)
    thong_tin_kh  = Column(String(255), index=True)   # Tên khách hàng
    sp_banggia    = Column(String(100))                # Mã SP hoặc mã bảng giá
    ngay_tao      = Column(Date, nullable=False, index=True)
    so_luong      = Column(Integer, default=1)
    tong_tien     = Column(Float,   default=0.0)
    ma_co_quan_thue = Column(String(50))
    trang_thai    = Column(String(50), default='cho_xu_ly', index=True)

    # Relationships
    items = relationship(
        'OrderItem', back_populates='order',
        cascade='all, delete-orphan',
    )
    shipments = relationship('Shipment', back_populates='order',
                             foreign_keys='Shipment.order_id')

    def __repr__(self):
        return f"<Order(ma_don_hang='{self.ma_don_hang}', trang_thai='{self.trang_thai}')>"


class OrderItem(Base):
    """Chi tiết từng dòng trong đơn hàng."""
    __tablename__ = 'order_items'

    id          = Column(Integer, primary_key=True)
    order_id    = Column(Integer, ForeignKey('orders.id',   ondelete='CASCADE'),
                         nullable=False, index=True)
    product_id  = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'),
                         nullable=False, index=True)
    so_luong    = Column(Integer, nullable=False)
    don_gia     = Column(Float,   nullable=False)
    total_price = Column(Float,   nullable=False)

    # Relationships
    order   = relationship('Order',   back_populates='items')
    product = relationship('Product', back_populates='order_items')

    def __repr__(self):
        return f"<OrderItem(order_id={self.order_id}, product_id={self.product_id})>"


class Invoice(Base):
    """Hóa đơn — phát sinh sau khi thanh toán tại POS."""
    __tablename__ = 'invoices'

    id            = Column(Integer, primary_key=True)
    so_hd         = Column(String(50), unique=True, nullable=False, index=True)
    ngay_hd       = Column(Date, nullable=False, index=True)
    nguoi_mua     = Column(String(100), nullable=False, index=True)
    tong_tien     = Column(Float, nullable=False)
    trang_thai    = Column(String(50), default='Chưa thanh toán', index=True)
    hinh_thuc_tt  = Column(String(50))  # Tiền mặt / MoMo / Banking

    # Relationships
    items = relationship(
        'InvoiceItem', back_populates='invoice',
        cascade='all, delete-orphan',
    )
    shipments = relationship('Shipment', back_populates='invoice',
                             foreign_keys='Shipment.invoice_id')

    def __repr__(self):
        return f"<Invoice(so_hd='{self.so_hd}', trang_thai='{self.trang_thai}')>"


class InvoiceItem(Base):
    """Chi tiết từng dòng trong hóa đơn."""
    __tablename__ = 'invoice_items'

    id           = Column(Integer, primary_key=True)
    invoice_id   = Column(Integer, ForeignKey('invoices.id',  ondelete='CASCADE'),
                          nullable=False, index=True)
    product_id   = Column(Integer, ForeignKey('products.id',  ondelete='RESTRICT'),
                          nullable=False, index=True)
    product_code = Column(String(20),  nullable=False)  # snapshot tại thời điểm bán
    product_name = Column(String(100), nullable=False)  # snapshot tại thời điểm bán
    so_luong     = Column(Integer, nullable=False)
    don_gia      = Column(Float,   nullable=False)
    total_price  = Column(Float,   nullable=False)

    # Relationships
    invoice = relationship('Invoice', back_populates='items')
    product = relationship('Product', back_populates='invoice_items')

    def __repr__(self):
        return f"<InvoiceItem(invoice_id={self.invoice_id}, ma='{self.product_code}')>"


# ══════════════════════════════════════════════════════════════════════════════
# DISCOUNT CODES
# ══════════════════════════════════════════════════════════════════════════════

class DiscountCode(Base):
    """Mã giảm giá — theo % hoặc số tiền cố định."""
    __tablename__ = 'discount_codes'

    id              = Column(Integer, primary_key=True)
    code            = Column(String(50), unique=True, nullable=False, index=True)
    name            = Column(String(100), nullable=False)
    description     = Column(Text)
    discount_type   = Column(String(20), nullable=False)  # 'percent' | 'fixed'
    discount_value  = Column(Float, nullable=False)
    start_date      = Column(DateTime, nullable=False, index=True)
    end_date        = Column(DateTime, nullable=False, index=True)
    max_uses        = Column(Integer)         # None = không giới hạn
    used_count      = Column(Integer, default=0)
    min_order_value = Column(Float, default=0.0)
    status          = Column(String(20), default='active', index=True)
    total_savings   = Column(Float, default=0.0)
    created_at      = Column(DateTime, default=_now)
    updated_at      = Column(DateTime, default=_now, onupdate=_now)

    def __repr__(self):
        return f"<DiscountCode(code='{self.code}', type='{self.discount_type}')>"


# ══════════════════════════════════════════════════════════════════════════════
# AREAS & SHOPS
# ══════════════════════════════════════════════════════════════════════════════

class Area(Base):
    """Khu vực địa lý (tỉnh/thành phố)."""
    __tablename__ = 'areas'

    id          = Column(Integer, primary_key=True)
    name        = Column(String(100), nullable=False, index=True)
    code        = Column(String(20),  unique=True, nullable=False, index=True)
    type        = Column(String(50),  nullable=False)
    province    = Column(String(100), nullable=False)
    district    = Column(String(100))
    ward        = Column(String(100))
    address     = Column(Text)
    postal_code = Column(String(10))
    phone       = Column(String(20))
    email       = Column(String(120))
    manager     = Column(String(100))
    description = Column(Text)
    status      = Column(String(20), default='active', index=True)
    priority    = Column(String(20), default='medium')
    created_at  = Column(DateTime, default=_now)
    updated_at  = Column(DateTime, default=_now, onupdate=_now)

    # Relationships
    shops = relationship('Shop', back_populates='area',
                         cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Area(name='{self.name}', code='{self.code}')>"


class Shop(Base):
    """Cửa hàng / chi nhánh — thuộc về 1 khu vực."""
    __tablename__ = 'shops'

    id          = Column(Integer, primary_key=True)
    name        = Column(String(100), nullable=False, index=True)
    code        = Column(String(20),  unique=True, nullable=False, index=True)
    area_id     = Column(Integer, ForeignKey('areas.id', ondelete='RESTRICT'),
                         nullable=False, index=True)
    address     = Column(Text, nullable=False)
    phone       = Column(String(20))
    email       = Column(String(120))
    manager     = Column(String(100))
    description = Column(Text)
    status      = Column(String(20), default='active', index=True)
    created_at  = Column(DateTime, default=_now)
    updated_at  = Column(DateTime, default=_now, onupdate=_now)

    # Relationships
    area = relationship('Area', back_populates='shops')

    def __repr__(self):
        return f"<Shop(name='{self.name}', code='{self.code}')>"


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULES
# ══════════════════════════════════════════════════════════════════════════════

class Schedule(Base):
    """Ca làm việc của nhân viên."""
    __tablename__ = 'schedules'

    id          = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'),
                         nullable=False, index=True)
    work_date   = Column(Date,    nullable=False, index=True)
    shift_type  = Column(String(50), nullable=False)
    notes       = Column(Text)
    created_at  = Column(DateTime, default=_now)
    updated_at  = Column(DateTime, default=_now, onupdate=_now)

    # Relationships
    employee = relationship('User', back_populates='schedules')

    __table_args__ = (
        Index('ix_schedules_employee_date', 'employee_id', 'work_date'),
    )

    def __repr__(self):
        return f"<Schedule(emp={self.employee_id}, date='{self.work_date}', shift='{self.shift_type}')>"


# ══════════════════════════════════════════════════════════════════════════════
# GENERAL DIARY & AUDIT
# ══════════════════════════════════════════════════════════════════════════════

class GeneralDiary(Base):
    """Nhật ký kế toán — tự động ghi khi có giao dịch tài chính."""
    __tablename__ = 'general_diary'

    id             = Column(Integer, primary_key=True)
    ngay_nhap      = Column(Date,        nullable=False, index=True)
    so_hieu        = Column(String(50),  nullable=False, index=True)
    dien_giai      = Column(String(255))
    so_luong_nhap  = Column(Integer, default=0)
    so_luong_xuat  = Column(Integer, default=0)
    so_tien        = Column(Float,   default=0.0)

    def __repr__(self):
        return f"<GeneralDiary(so_hieu='{self.so_hieu}', ngay='{self.ngay_nhap}')>"


class AuditLog(Base):
    """Lịch sử thao tác hệ thống — ai làm gì, lúc nào, thay đổi gì."""
    __tablename__ = 'audit_logs'

    id          = Column(Integer, primary_key=True)
    timestamp   = Column(DateTime, nullable=False, index=True, default=_now)
    action      = Column(String(20),  nullable=False, index=True)  # CREATE/UPDATE/DELETE/LOGIN
    entity      = Column(String(50),  nullable=False, index=True)  # Product/Order/User/...
    entity_id   = Column(String(50))
    username    = Column(String(50),  index=True)
    ip_address  = Column(String(45))
    before_data = Column(Text)   # JSON state trước thay đổi
    after_data  = Column(Text)   # JSON state sau thay đổi
    description = Column(String(500))
    status      = Column(String(20), default='success')

    __table_args__ = (
        Index('ix_audit_logs_user_time', 'username', 'timestamp'),
    )

    def __repr__(self):
        return f"<AuditLog({self.action} {self.entity}#{self.entity_id} by {self.username})>"


# ══════════════════════════════════════════════════════════════════════════════
# SHIPPING
# ══════════════════════════════════════════════════════════════════════════════

class Shipment(Base):
    """Đơn vận chuyển — theo dõi hành trình giao hàng."""
    __tablename__ = 'shipments'

    id                = Column(Integer, primary_key=True)
    # FK đến orders và invoices
    order_id          = Column(Integer, ForeignKey('orders.id',   ondelete='SET NULL'),
                               nullable=True, index=True)
    invoice_id        = Column(Integer, ForeignKey('invoices.id', ondelete='SET NULL'),
                               nullable=True, index=True)
    # Giữ string code để hiển thị (không bị ảnh hưởng khi order/invoice bị xóa)
    order_code        = Column(String(50), nullable=False, index=True)
    invoice_code      = Column(String(50))
    tracking_code     = Column(String(50), unique=True, nullable=False, index=True)
    # Thông tin người nhận
    receiver_name     = Column(String(100), nullable=False)
    receiver_phone    = Column(String(20),  nullable=False)
    receiver_address  = Column(Text,        nullable=False)
    receiver_province = Column(String(100))
    # Gói hàng
    weight            = Column(Integer, default=500)      # gram
    service_type      = Column(String(30), default='Giao hàng thường')
    cod_amount        = Column(Float, default=0.0)
    shipping_fee      = Column(Float, default=0.0)
    note              = Column(String(255))
    # Trạng thái
    status            = Column(String(30), default='pending', index=True)
    # Người thực hiện
    created_by        = Column(String(50))
    shipper_name      = Column(String(100))
    shipper_phone     = Column(String(20))
    # Thời gian
    created_at        = Column(DateTime, default=_now)
    updated_at        = Column(DateTime, default=_now, onupdate=_now)
    estimated_date    = Column(DateTime)
    delivered_at      = Column(DateTime)

    # Relationships
    order    = relationship('Order',   back_populates='shipments', foreign_keys=[order_id])
    invoice  = relationship('Invoice', back_populates='shipments', foreign_keys=[invoice_id])
    history  = relationship(
        'ShipmentHistory', back_populates='shipment',
        cascade='all, delete-orphan',
        order_by='ShipmentHistory.timestamp',
    )

    def __repr__(self):
        return f"<Shipment({self.tracking_code}, {self.status})>"


class ShipmentHistory(Base):
    """Lịch sử trạng thái đơn vận chuyển — mỗi lần update tạo 1 record."""
    __tablename__ = 'shipment_history'

    id          = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey('shipments.id', ondelete='CASCADE'),
                         nullable=False, index=True)
    status      = Column(String(30),  nullable=False)
    description = Column(String(255), nullable=False)
    location    = Column(String(200))
    updated_by  = Column(String(50))
    timestamp   = Column(DateTime, default=_now, index=True)

    # Relationships
    shipment = relationship('Shipment', back_populates='history')

    def __repr__(self):
        return f"<ShipmentHistory(shipment={self.shipment_id}, status='{self.status}')>"