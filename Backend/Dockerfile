# ── Stage 1: Builder ─────────────────────────────────────────────────────────
# Cài dependencies vào virtualenv riêng, không lẫn vào image cuối
FROM python:3.11-slim AS builder

WORKDIR /build

# Cài build tools (cần cho psycopg2, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements trước (layer caching — chỉ rebuild khi requirements thay đổi)
COPY requirements.txt .

# Tạo virtualenv và cài packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip --quiet && \
    pip install --no-cache-dir -r requirements.txt --quiet


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
# Image nhỏ hơn: không có gcc, không có build cache
FROM python:3.11-slim AS runtime

# Security: chạy với non-root user
RUN groupadd -r posapp && useradd -r -g posapp posapp

WORKDIR /app

# Chỉ cần libpq runtime (không cần -dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv từ builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code
COPY --chown=posapp:posapp . .

# Tạo thư mục static với đúng quyền
RUN mkdir -p static/images/products && \
    chown -R posapp:posapp static/

# Switch sang non-root user
USER posapp

# Expose port
EXPOSE 5001

# Health check — Docker tự restart container nếu unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Start command — dùng gunicorn cho production
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:5001", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]