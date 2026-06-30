# PosPos — Point of Sale System

> Hệ thống quản lý bán hàng nội bộ, xây dựng với kiến trúc tách biệt FastAPI backend + Flask frontend.  
> Dự án thực tập tại **Công ty TNHH MTV TM-DV Tin học Phan Huyện** tiếp tục phát triển thành dự án cá nhân (07/2025 – 06/2026).

---

## Mục lục

- [Tổng quan](#tổng-quan)
- [Kiến trúc](#kiến-trúc)
- [Chức năng](#chức-năng)
- [Giao diện](#giao-diện)
- [Công nghệ](#công-nghệ)
- [Cài đặt & Chạy](#cài-đặt--chạy)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [API Documentation](#api-documentation)
- [Biến môi trường](#biến-môi-trường)
- [Database](#database)
- [Landing Page](#landing-page)

---

## Tổng quan

**PosPos** là phần mềm POS (Point of Sale) web-based phục vụ quản lý bán hàng, kho, nhân viên và báo cáo cho cửa hàng máy tính/điện tử.

Hệ thống gồm 3 phần chạy độc lập:

| Service | Framework | Port | Mô tả |
|---------|-----------|------|-------|
| Backend | FastAPI | 5001 | REST API, xử lý nghiệp vụ, JWT auth |
| Frontend | Flask + Jinja2 | 5000 | Giao diện web, render HTML |
| Landing | HTML/CSS/JS thuần | — | Trang giới thiệu sản phẩm, deploy Render Static Site |

---

## Kiến trúc

```
Browser
   │
   ├─► Flask (port 5000) ──── render HTML/CSS/JS ──► User
   │        │
   │        └─► Fetch API ──► FastAPI (port 5001) ──► PostgreSQL
   │                                    │
   │                                    ├─► Redis (cache + token blacklist)
   │                                    └─► Celery (async tasks - optional)
```

**Luồng xác thực:**
1. User đăng nhập → Flask gọi `POST /api/auth/login` → nhận JWT
2. JWT lưu vào `sessionStorage`
3. Mọi API call kèm header `Authorization: Bearer <token>`
4. Backend decode JWT → kiểm tra quyền (UserPermission table) → trả dữ liệu

---

## Chức năng

### Bán hàng
- **POS** — Giao diện bán hàng trực tiếp, thêm sản phẩm vào giỏ, áp mã giảm giá, thanh toán
- **Đơn hàng** — Tạo và theo dõi đơn hàng, hỗ trợ nhiều trạng thái
- **Hóa đơn** — Tạo hóa đơn từ POS, in hóa đơn, theo dõi thanh toán
- **Mã giảm giá** — Tạo và quản lý mã giảm theo % hoặc số tiền cố định

### Kho & Sản phẩm
- **Sản phẩm** — CRUD sản phẩm, upload ảnh, phân nhóm, theo dõi tồn kho
- **Nhóm sản phẩm** — Phân loại sản phẩm theo danh mục
- **Kho hàng** — Nhập/xuất kho, theo dõi số lượng từng kho
- **Bảng giá** — Quản lý giá dịch vụ độc lập với giá sản phẩm

### Vận chuyển
- **Đơn vận chuyển** — Tạo và theo dõi hành trình giao hàng
- **Lịch sử trạng thái** — Timeline từng bước: pending → picked → in_transit → delivering → delivered/failed
- **Tracking code** — Tự sinh mã vận đơn dạng `VD{yymmdd}{6digits}`

### Quản lý nhân viên
- **Nhân viên** — CRUD tài khoản nhân viên
- **Ca làm việc** — Lập lịch ca theo ngày
- **Phân quyền** — Cấp quyền chi tiết từng module/action cho từng nhân viên

### Địa lý & Cửa hàng
- **Khu vực** — Quản lý theo tỉnh/thành phố
- **Cửa hàng** — Quản lý chi nhánh, gắn với khu vực

### Khách hàng
- **Danh sách khách hàng** — CRM đơn giản
- **Công nợ** — Theo dõi khách hàng chưa thanh toán
- **Xếp hạng** — Phân loại khách theo doanh thu

### Tài chính & Báo cáo
- **Nhật ký chung** — Tự động ghi log mọi giao dịch tài chính
- **Báo cáo doanh thu** — Thống kê theo khoảng thời gian
- **Báo cáo công nợ** — Danh sách hóa đơn chưa thanh toán

### Hệ thống
- **Audit log** — Ghi lại mọi thao tác CRUD (ai làm gì, lúc nào)
- **Chatbot AI** — Hỗ trợ tra cứu tồn kho, phân tích bán hàng
- **WebSocket** — Cập nhật real-time khi có đơn hàng mới
- **Session management** — Auto-refresh token, idle logout sau 60 phút

---

## Giao diện

Toàn bộ giao diện được thiết kế nhất quán theo design system chung:

- **Login** — Split-screen: panel trái brand (gradient xanh, logo, feature list), panel phải form đăng nhập clean
- **POS** — Panel trái lưới sản phẩm (hover border animation), panel phải giỏ hàng 320px cố định, modal thanh toán đầy đủ (tiền mặt / QR), xác nhận tiền thừa
- **Báo cáo** — Stat card màu riêng biệt, tab icon, sidebar thay readonly input bằng stat-row có màu highlight
- **Tất cả modal nhập/sửa** — Cấu trúc `form-section` (icon + label phân nhóm), trường `required` đánh dấu `*`, emoji trong select options, icon footer buttons

### Palette chính

| Biến CSS | Giá trị | Dùng cho |
|----------|---------|---------|
| `--primary-color` | `#2563eb` | Buttons, links, focus ring |
| `--gray-50` | `#f9fafb` | Table row, card background |
| `--success` | `#16a34a` | Trạng thái hoàn thành |
| `--danger` | `#ef4444` | Xóa, hủy, lỗi |
| `--warning` | `#f59e0b` | Cảnh báo, chờ xử lý |

---

## Công nghệ

### Backend
| Thư viện | Phiên bản | Mục đích |
|----------|-----------|---------|
| FastAPI | latest | Web framework |
| SQLAlchemy | 2.x | ORM |
| PostgreSQL | 15+ | Database chính |
| psycopg2 | latest | PostgreSQL adapter |
| PyJWT | 2.10.1 | JWT authentication |
| werkzeug | latest | Password hashing |
| Redis | latest | Cache + token blacklist |
| Celery | latest | Async tasks (optional) |
| prometheus-client | latest | Metrics `/metrics` |
| uvicorn | latest | ASGI server |

### Frontend
| Thư viện | Mục đích |
|----------|---------|
| Flask | Web framework |
| Jinja2 | Template engine |
| Font Awesome 6 | Icons |
| Vanilla JS | Frontend logic |

---

## Cài đặt & Chạy

### Yêu cầu
- Python 3.10+
- PostgreSQL 15+
- Redis (optional — app vẫn chạy nếu không có Redis)

### 1. Clone repo
```bash
git clone https://github.com/surp29/POS.git
cd POS
```

### 2. Cấu hình Backend
```bash
cd Backend

# Tạo virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Cài dependencies
pip install -r requirements.txt

# Tạo file .env từ mẫu
copy env.example .env         # Windows
# cp env.example .env         # Linux/Mac

# Chỉnh DATABASE_URL, JWT_SECRET_KEY trong .env
```

### 3. Khởi tạo Database
```bash
cd Backend

# Tạo tất cả bảng + tài khoản admin
python setup_database.py

# (Tuỳ chọn) Tạo dữ liệu mẫu
python create_sample_data.py

# (Tuỳ chọn) Xóa data, giữ admin
python clear_data.py
```

### 4. Cấu hình Frontend
```bash
cd Frontend

pip install -r requirements.txt
copy env.example .env
# Chỉnh BACKEND_URL=http://localhost:5001
```

### 5. Chạy hệ thống

**Terminal 1 — Backend:**
```bash
cd Backend
python main.py
# → http://localhost:5001
# → http://localhost:5001/docs  (Swagger UI)
```

**Terminal 2 — Frontend:**
```bash
cd Frontend
python app.py
# → http://localhost:5000
```

### Đăng nhập mặc định
| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Quản trị viên (toàn quyền) |

---

## Cấu trúc thư mục

```
POS/
├── Backend/
│   ├── app/
│   │   ├── api_fastapi/           # Tất cả API endpoints
│   │   │   ├── auth.py            # Đăng nhập, logout, refresh token
│   │   │   ├── products.py        # Sản phẩm
│   │   │   ├── orders.py          # Đơn hàng
│   │   │   ├── invoices.py        # Hóa đơn
│   │   │   ├── warehouses.py      # Kho hàng
│   │   │   ├── shipping.py        # Vận chuyển
│   │   │   ├── permissions.py     # Phân quyền nhân viên
│   │   │   ├── discount_codes.py  # Mã giảm giá
│   │   │   ├── reports.py         # Báo cáo
│   │   │   ├── chatbot.py         # Chatbot AI
│   │   │   ├── schedules.py       # Ca làm việc
│   │   │   ├── areas.py           # Khu vực
│   │   │   ├── shops.py           # Cửa hàng
│   │   │   ├── accounts.py        # Khách hàng
│   │   │   ├── users.py           # Nhân viên
│   │   │   ├── prices.py          # Bảng giá dịch vụ
│   │   │   ├── product_groups.py  # Nhóm sản phẩm
│   │   │   ├── general_diary.py   # Nhật ký chung
│   │   │   ├── audit_api.py       # Audit log
│   │   │   ├── customers_analytics.py # Phân tích khách hàng
│   │   │   └── websocket.py       # WebSocket real-time
│   │   ├── services/              # Business logic (tách khỏi endpoint)
│   │   │   ├── auth_helper.py     # Decode JWT, lấy username từ request
│   │   │   ├── general_diary.py   # Auto-log nhật ký kế toán
│   │   │   ├── discounts.py       # Tính toán mã giảm giá
│   │   │   ├── invoices.py        # Cập nhật công nợ khách hàng
│   │   │   ├── orders.py          # Tạo đơn hàng (dùng trong WebSocket)
│   │   │   ├── products.py        # Upload ảnh, validate sản phẩm
│   │   │   └── customers.py       # Phân tích, xếp hạng khách hàng
│   │   ├── middleware/            # Request middleware
│   │   │   ├── rate_limit.py      # Giới hạn request/phút
│   │   │   ├── security.py        # Security headers
│   │   │   └── metrics.py         # Prometheus metrics
│   │   ├── tasks/                 # Celery async tasks (optional)
│   │   │   ├── report_tasks.py    # Báo cáo nặng chạy background
│   │   │   └── notification_tasks.py # Gửi email thông báo
│   │   ├── models.py              # SQLAlchemy models (19 bảng)
│   │   ├── schemas_fastapi.py     # Pydantic request/response schemas
│   │   ├── permission_middleware.py # Dependency: kiểm tra quyền
│   │   ├── rbac.py                # Re-export từ permission_middleware
│   │   ├── audit.py               # AuditMiddleware — ghi log thao tác
│   │   ├── cache.py               # Redis cache helper
│   │   ├── celery_app.py          # Celery app instance
│   │   ├── config.py              # Cấu hình từ .env
│   │   ├── database.py            # SQLAlchemy engine + session
│   │   ├── logger.py              # Custom logger
│   │   ├── main.py                # FastAPI app, middleware, routers
│   │   └── websocket_manager.py   # WebSocket connection manager
│   ├── main.py                    # Entry point: python main.py
│   ├── setup_database.py          # Tạo DB + tài khoản admin
│   ├── create_sample_data.py      # Tạo dữ liệu mẫu
│   ├── clear_data.py              # Xóa data (giữ admin)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── env.example
│   ├── start.bat                  # Windows quick-start
│   └── start.sh                   # Linux/Mac quick-start
│
├── Frontend/
│   ├── templates/                 # Jinja2 HTML templates
│   │   ├── base.html              # Layout chung: sidebar, navbar, chatbot
│   │   ├── login.html             # Đăng nhập
│   │   ├── pos.html               # Giao diện bán hàng POS
│   │   ├── orders.html            # Quản lý đơn hàng
│   │   ├── invoices.html          # Quản lý hóa đơn
│   │   ├── products.html          # Quản lý sản phẩm
│   │   ├── product_groups.html    # Nhóm sản phẩm
│   │   ├── prices.html            # Bảng giá dịch vụ
│   │   ├── warehouse.html         # Kho hàng
│   │   ├── shipping.html          # Vận chuyển
│   │   ├── permissions.html       # Phân quyền nhân viên
│   │   ├── discount_codes.html    # Mã giảm giá
│   │   ├── general_diary.html     # Nhật ký chung
│   │   ├── reports.html           # Báo cáo
│   │   ├── areas_management.html  # Khu vực
│   │   ├── shops_management.html  # Cửa hàng
│   │   ├── employees.html         # Nhân viên
│   │   ├── employees_schedules.html # Ca làm việc
│   │   ├── customers.html         # Danh sách khách hàng
│   │   ├── customers_debts.html   # Công nợ
│   │   └── customers_leaderboard.html # Xếp hạng khách hàng
│   ├── static/
│   │   ├── css/
│   │   │   ├── style.css          # Stylesheet chính
│   │   │   ├── responsive.css     # Responsive breakpoints
│   │   │   └── phone.css          # Phone input component
│   │   ├── js/
│   │   │   ├── utils.js           # Helpers: debounce, formatMoney, formatDate...
│   │   │   ├── permissions.js     # Load quyền, ẩn/hiện menu, redirect
│   │   │   ├── session_manager.js # Idle logout, auto-refresh token
│   │   │   └── phone.js           # International phone input
│   │   └── images/
│   │       ├── logo.png
│   │       ├── LogoPoS.png
│   │       └── products/default.png
│   ├── app.py                     # Flask routes
│   ├── config.py                  # BACKEND_URL, SECRET_KEY
│   ├── requirements.txt
│   ├── env.example
│   ├── start.bat
│   └── start.sh
│
├── Landing/
│   ├── css/
│   │   └── style.css              # CSS variables, dark mode, responsive
│   ├── js/
│   │   └── main.js                # Dark mode toggle, scroll reveal, chatbot, form
│   ├── index.html                 # Trang landing chính
│   ├── render.yaml                # Render static site config (cache headers)
│   └── _redirects                 # SPA fallback: /* /index.html 200
│
└── README.md
```

---

## API Documentation

Swagger UI tự động sinh khi chạy backend:

```
http://localhost:5001/docs       # Swagger UI
http://localhost:5001/redoc      # ReDoc
```

### Danh sách endpoints chính

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/auth/login` | Đăng nhập, nhận JWT |
| `POST` | `/api/auth/logout` | Đăng xuất, blacklist token |
| `POST` | `/api/auth/refresh` | Làm mới token |
| `GET`  | `/api/auth/me` | Thông tin user hiện tại |
| `GET`  | `/api/products/` | Danh sách sản phẩm |
| `POST` | `/api/products/` | Thêm sản phẩm |
| `GET`  | `/api/orders/` | Danh sách đơn hàng |
| `POST` | `/api/orders/` | Tạo đơn hàng |
| `GET`  | `/api/invoices/` | Danh sách hóa đơn |
| `POST` | `/api/invoices/` | Tạo hóa đơn (từ POS) |
| `GET`  | `/api/shipping/` | Danh sách vận chuyển |
| `POST` | `/api/shipping/` | Tạo đơn vận chuyển |
| `GET`  | `/api/permissions/my` | Quyền của user hiện tại |
| `PUT`  | `/api/permissions/{user_id}` | Cập nhật quyền nhân viên |
| `GET`  | `/api/reports/revenue` | Báo cáo doanh thu |
| `GET`  | `/api/discount-codes/` | Danh sách mã giảm giá |
| `GET`  | `/api/schedules/` | Lịch làm việc |
| `GET`  | `/api/accounts/` | Danh sách khách hàng |
| `GET`  | `/health` | Health check |
| `GET`  | `/metrics` | Prometheus metrics |
| `WS`   | `/api/ws/{room}` | WebSocket real-time |

### Xác thực

Tất cả endpoint (trừ `/api/auth/login`, `/health`) yêu cầu:
```http
Authorization: Bearer <access_token>
```

---

## Biến môi trường

### Backend (`Backend/.env`)
```env
# Database (bắt buộc)
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/pos

# JWT (bắt buộc — đổi trong production)
JWT_SECRET_KEY=your-random-secret-key-at-least-32-chars
JWT_ACCESS_TOKEN_EXPIRES=1800   # giây, mặc định 30 phút

# Server
BACKEND_PORT=5001
FLASK_ENV=development           # hoặc production

# Redis (optional — app vẫn chạy không có Redis)
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_PRODUCTS=300
CACHE_TTL_PRICES=300

# Admin mặc định (tạo khi startup nếu chưa có)
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123
DEFAULT_ADMIN_ENABLED=true

# Email (optional — dùng cho Celery notification tasks)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-app-password
ADMIN_EMAIL=admin@your-domain.com
```

### Frontend (`Frontend/.env`)
```env
BACKEND_URL=http://localhost:5001
SECRET_KEY=your-flask-secret-key
DEBUG=True
HOST=0.0.0.0
PORT=5000
```

---

## Database

### Thiết kế schema

- **Primary Key**: `id INTEGER` tự tăng trên tất cả 19 bảng
- **Foreign Key + cascade**: CASCADE cho dữ liệu con (items, history, permissions), SET NULL cho tham chiếu mềm (shipment → order/invoice), RESTRICT cho tham chiếu sản phẩm
- **Bi-directional relationship**: Tất cả quan hệ đều có `back_populates` 2 chiều
- **Index**: Tất cả cột thường query được index; composite index trên `schedules(employee_id, work_date)` và `audit_logs(username, timestamp)`
- **Snapshot fields**: `InvoiceItem` lưu `product_code`, `product_name` tại thời điểm bán — không bị ảnh hưởng khi sản phẩm đổi tên sau này

### 19 bảng trong hệ thống

| Bảng | Mô tả |
|------|-------|
| `users` | Tài khoản nhân viên, thông tin đăng nhập |
| `user_permissions` | Quyền chi tiết từng nhân viên (module.action) |
| `accounts` | Khách hàng |
| `product_groups` | Nhóm/danh mục sản phẩm |
| `products` | Sản phẩm, tồn kho, ảnh |
| `prices` | Bảng giá dịch vụ độc lập |
| `invoices` | Hóa đơn |
| `invoice_items` | Chi tiết từng dòng hóa đơn |
| `orders` | Đơn hàng |
| `order_items` | Chi tiết từng dòng đơn hàng |
| `warehouses` | Kho hàng, nhập/xuất |
| `areas` | Khu vực địa lý |
| `shops` | Cửa hàng/chi nhánh |
| `discount_codes` | Mã giảm giá |
| `schedules` | Ca làm việc nhân viên |
| `general_diary` | Nhật ký kế toán (auto-log) |
| `audit_logs` | Lịch sử thao tác hệ thống |
| `shipments` | Đơn vận chuyển |
| `shipment_history` | Lịch sử trạng thái vận chuyển |

### Khởi tạo nhanh

```bash
cd Backend
python setup_database.py      # Tạo bảng + admin
python create_sample_data.py  # Dữ liệu mẫu (optional)
```

---

## Hệ thống phân quyền

Mỗi nhân viên được cấp quyền theo dạng `module.action`:

```
pos.view          pos.sell
invoices.view     invoices.create    invoices.edit    invoices.delete
orders.view       orders.create      orders.edit      orders.delete
products.view     products.create    products.edit    products.delete
warehouse.view    warehouse.import   warehouse.edit   warehouse.export
shipping.view     shipping.create    shipping.update_status  shipping.cancel
reports.view      reports.debt
schedules.view    schedules.create   schedules.edit   schedules.delete
general_diary.view ...
discount_codes.view  discount_codes.use  discount_codes.create ...
areas.view  areas.create  areas.edit  areas.delete
shops.view  shops.create  shops.edit  shops.delete
```

Admin (position = "Admin") có toàn quyền — không cần cấu hình permission.

---

## Landing Page

Trang giới thiệu sản phẩm PosPos tại **[pospos-landing.onrender.com](https://pospos-landing.onrender.com)**, xây bằng HTML/CSS/JS thuần — không framework, tối ưu PageSpeed.

### Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| Dark / Light mode | Toggle lưu `localStorage`, mặc định sáng. CSS variables tự điều chỉnh toàn bộ màu sắc |
| Scroll reveal | IntersectionObserver làm hiện section khi cuộn đến |
| Counter animation | Các số thống kê chạy đếm khi vào viewport |
| Scrollytelling | Section "Hành trình" cập nhật nội dung theo vị trí cuộn |
| AI demo chat | Đoạn hội thoại tự phát với typing delay, hiện khi vào section |
| Chatbot widget | Hỗ trợ tư vấn sản phẩm với 10 chủ đề, quick-reply buttons |
| Subscribe form | Thu thập tên / email / số điện thoại / loại cửa hàng qua Web3Forms |
| Responsive | Mobile-first, hamburger menu với animation X, tap targets ≥ 44px |

### Web3Forms — nhận email đăng ký thật

Khi có khách đăng ký dùng thử, email được gửi về hộp thư qua Web3Forms (250 lượt/tháng miễn phí).

**Cấu hình:**

1. Đăng ký tại [web3forms.com](https://web3forms.com) → lấy **Access Key**
2. Mở `Landing/js/main.js`, tìm dòng:
   ```js
   const WEB3FORMS_KEY = '...';
   ```
3. Thay bằng Access Key của bạn

Email nhận được gồm: tên, email, số điện thoại, loại cửa hàng, thời gian đăng ký.

### Deploy lên Render (Static Site)

1. Push code lên GitHub
2. Vào [render.com](https://render.com) → **New → Static Site**
3. Chọn repo, cấu hình:

   | Trường | Giá trị |
   |--------|---------|
   | Root Directory | `Landing` |
   | Build Command | *(để trống)* |
   | Publish Directory | `.` |

4. Deploy — Render tự cấp domain `*.onrender.com`

Cache headers được cấu hình sẵn trong `Landing/render.yaml`:
- CSS / JS: `immutable, 1 năm` (tên file đổi khi nội dung thay đổi)
- Các trang khác: `public, 1 giờ`

---

## Ghi chú

- **Hóa đơn điện tử**: Hệ thống chưa tích hợp API cơ quan thuế (chưa có quyền truy cập API chính thức). Hóa đơn hiện tại là hóa đơn nội bộ.
- **Redis**: Optional. Nếu không có Redis, cache sẽ bị bỏ qua và token không được blacklist khi logout (token vẫn hết hạn tự nhiên theo TTL).
- **Celery**: Optional. Nếu không có Celery/Redis, email notification và báo cáo async sẽ không hoạt động. API báo cáo đồng bộ vẫn hoạt động bình thường.

---

## Tác giả

**Nguyễn Hoàng Thành** — Backend Lead  
Email: hoangthanh29042003@gmail.com  
GitHub: [github.com/surp29](https://github.com/surp29)  
Trường: Van Lang University — Information Technology (2022–2026)