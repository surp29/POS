from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from .database import Base, engine, SessionLocal
from .models import User
from werkzeug.security import generate_password_hash
from .config import Config
from .logger import (
    log_request, log_response, log_error, log_info,
    log_success, log_warning, logger
)
import os
import time
from .api_fastapi import (
    products, prices, orders, invoices, users,
    accounts, product_groups, warehouses,
    auth, general_diary, areas, shops,
    discount_codes, reports, schedules, chatbot
    # customers_analytics đã được gộp vào reports.py
)
from .api_fastapi import websocket as ws_router
from .api_fastapi import audit_api
from .api_fastapi import permissions as permissions_api
from .api_fastapi import shipping as shipping_api
from .audit import AuditMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.security import SecurityHeadersMiddleware
from .middleware.metrics import MetricsMiddleware

app = FastAPI(
    title="PhanMemKeToan API",
    description="API cho phần mềm kế toán chuyên nghiệp",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Tables are created in startup_event()

app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,  # Đọc từ config, không dùng wildcard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining",
                    "X-RateLimit-Window", "X-Response-Time"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(AuditMiddleware)


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    log_request(method=request.method, path=request.url.path,
                query_params=str(request.query_params))
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        log_response(status_code=response.status_code,
                     path=request.url.path,
                     process_time=f"{process_time:.3f}s")
        return response
    except Exception as e:
        log_error("REQUEST", f"Lỗi {request.method} {request.url.path}", error=e)
        response = JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "message": str(e)},
        )
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    log_error("VALIDATION", f"Lỗi validate ở {request.url.path}", error=exc)
    r = JSONResponse(status_code=422,
                     content={"error": "Validation Error", "details": exc.errors()})
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    log_warning("HTTP_ERROR", f"HTTP {exc.status_code} ở {request.url.path}: {exc.detail}")
    r = JSONResponse(status_code=exc.status_code,
                     content={"error": exc.detail, "status_code": exc.status_code})
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    log_error("EXCEPTION", f"Lỗi không xác định ở {request.url.path}", error=exc)
    r = JSONResponse(status_code=500,
                     content={"error": "Internal Server Error", "message": str(exc)})
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r


if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(products.router,            prefix="/api")
app.include_router(prices.router,              prefix="/api")
app.include_router(orders.router,              prefix="/api")
app.include_router(invoices.router,            prefix="/api")
app.include_router(users.router,               prefix="/api")
app.include_router(accounts.router,            prefix="/api")
app.include_router(product_groups.router,      prefix="/api")
app.include_router(warehouses.router,          prefix="/api")
app.include_router(shops.router,               prefix="/api")
app.include_router(areas.router,               prefix="/api")
app.include_router(auth.router,                prefix="/api")
app.include_router(general_diary.router,       prefix="/api")
# customers_analytics.router đã được gộp vào reports.py
app.include_router(discount_codes.router,      prefix="/api/discount-codes")
app.include_router(reports.router,             prefix="/api")
app.include_router(schedules.router,           prefix="/api")
app.include_router(chatbot.router,             prefix="/api")
app.include_router(ws_router.router,           prefix="/api")
app.include_router(audit_api.router,           prefix="/api")
app.include_router(permissions_api.router,     prefix="/api")
app.include_router(shipping_api.router,        prefix="/api")

# NOTE: @app.on_event is deprecated in FastAPI >= 0.93
# Được giữ lại để tương thích. Chuyển sang lifespan khi nâng cấp.
@app.on_event("startup")
async def startup_event():
    try:
        Base.metadata.create_all(bind=engine)
        log_info("STARTUP", "🗄️ Đã kiểm tra và tạo các bảng database.")
    except Exception as e:
        log_warning("STARTUP", f"Không thể tạo bảng: {e}")

    try:
        username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
        password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
        if os.getenv("DEFAULT_ADMIN_ENABLED", "true").lower() in ("1", "true", "yes"):
            db = SessionLocal()
            try:
                if not db.query(User).filter(User.username == username).first():
                    db.add(User(
                        username=username,
                        password=generate_password_hash(password),
                        name="Administrator", position="Admin",
                        department="System", status=True,
                    ))
                    db.commit()
                    log_success("STARTUP", f"Tạo tài khoản mặc định '{username}'")
            finally:
                db.close()
    except Exception as e:
        log_warning("STARTUP", f"Không thể tạo admin: {e}")

    # Auto-seed dữ liệu demo khi DB trống (dùng cho môi trường demo/staging)
    # Bật bằng biến môi trường: SEED_DEMO_DATA=true
    if os.getenv("SEED_DEMO_DATA", "false").lower() in ("1", "true", "yes"):
        try:
            from .models import Product as _Product
            _db = SessionLocal()
            try:
                if _db.query(_Product).count() == 0:
                    log_info("STARTUP", "📦 DB trống — đang seed dữ liệu demo...")
                    import importlib.util as _ilu
                    _seed_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "create_sample_data.py",
                    )
                    _spec = _ilu.spec_from_file_location("_seed_mod", _seed_path)
                    _mod = _ilu.module_from_spec(_spec)
                    _spec.loader.exec_module(_mod)
                    _mod.create_sample_data()
                    log_success("STARTUP", "✅ Seed dữ liệu demo hoàn tất!")
                else:
                    log_info("STARTUP", "📦 DB đã có dữ liệu — bỏ qua seed.")
            finally:
                _db.close()
        except Exception as e:
            log_warning("STARTUP", f"Seed demo thất bại (không ảnh hưởng hoạt động): {e}")

    log_success("STARTUP", "🚀 PosPos Backend đã khởi động thành công!")
    log_info("STARTUP", f"📡 http://localhost:{Config.BACKEND_PORT}")
    log_info("STARTUP", "🛡️  Rate limiting:    ACTIVE")
    log_info("STARTUP", "🔒  Security headers: ACTIVE")
    log_info("STARTUP", "📊  Prometheus:       ACTIVE → /metrics")
    log_info("STARTUP", "🔌  WebSocket:        ACTIVE → /api/ws/{room}")
    log_info("STARTUP", "📋  Audit Log:        ACTIVE → /api/audit/")


@app.get("/", tags=["root"])
def read_root():
    return {"message": "PhanMemKeToan API is running", "version": "1.0.0"}


@app.get("/health", tags=["health"])
def health_check():
    from .cache import is_available as redis_ok
    from .websocket_manager import manager as ws_manager
    return {
        "status":         "healthy",
        "version":        "1.0.0",
        "redis":          "connected" if redis_ok() else "unavailable",
        "ws_connections": ws_manager.count_all(),
    }


@app.get("/metrics", tags=["monitoring"], include_in_schema=False)
def metrics_endpoint():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)