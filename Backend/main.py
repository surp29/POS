"""
Launcher — chạy file này để khởi động server:
    python main.py
"""
import uvicorn
import sys
import logging
import logging.config
from app.config import Config

# Tắt log thừa
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": True,
    "root": {"level": "CRITICAL", "handlers": []},
    "loggers": {
        "sqlalchemy":      {"level": "CRITICAL", "propagate": False},
        "uvicorn":         {"level": "CRITICAL", "propagate": False},
        "uvicorn.access":  {"level": "CRITICAL", "propagate": False},
        "fastapi":         {"level": "CRITICAL", "propagate": False},
    },
})


class _Filter:
    """Chỉ hiển thị log của app, bỏ qua log của uvicorn/sqlalchemy."""
    SHOW = [
        "STARTUP", "LOGIN", "LOGOUT", "REQUEST", "RESPONSE",
        "CACHE", "RATE_LIMIT", "AUDIT", "WS", "ERROR",
        "CRITICAL", "Exception", "Traceback",
    ]

    def __init__(self, stream):
        self._s = stream

    def write(self, text):
        if not text.strip():
            self._s.write(text)
        elif any(k in text for k in self.SHOW):
            self._s.write(text)

    def flush(self):        self._s.flush()
    def isatty(self):       return self._s.isatty()
    def __getattr__(self, n): return getattr(self._s, n)


sys.stdout = _Filter(sys.stdout)

if __name__ == "__main__":
    print(f"Starting PosPos Backend on port {Config.BACKEND_PORT}")
    print(f"API:     http://localhost:{Config.BACKEND_PORT}")
    print(f"Docs:    http://localhost:{Config.BACKEND_PORT}/docs")
    print(f"Metrics: http://localhost:{Config.BACKEND_PORT}/metrics")
    print(f"WS:      ws://localhost:{Config.BACKEND_PORT}/api/ws/orders")
    print(f"Use Ctrl+C to stop")
    print()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=Config.BACKEND_PORT,
        reload=True,
        log_level="critical",
        access_log=False,
        log_config=None,
    )