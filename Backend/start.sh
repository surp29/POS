#!/bin/bash
# PosPos Backend Startup Script - Mac/Linux

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "========================================"
echo "  PosPos Backend Server"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 chưa được cài đặt${NC}"
    exit 1
fi

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}[INFO] Tạo virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}[INFO] Kiểm tra dependencies...${NC}"
pip install -r requirements.txt -q

# Copy .env if not exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[WARNING] File .env chưa tồn tại${NC}"
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${YELLOW}[INFO] Đã copy env.example → .env${NC}"
        echo -e "${YELLOW}[INFO] Hãy sửa file .env trước khi tiếp tục${NC}"
        echo "Nhấn Enter để tiếp tục sau khi sửa .env..."
        read
    fi
fi

# Start Redis via Docker
if command -v docker &> /dev/null; then
    if ! docker ps --filter "name=redis-pos" --format "{{.Names}}" | grep -q "redis-pos"; then
        echo -e "${YELLOW}[INFO] Khởi động Redis...${NC}"
        docker run -d --name redis-pos -p 6379:6379 redis:7-alpine > /dev/null 2>&1 || \
        docker start redis-pos > /dev/null 2>&1
        echo -e "${GREEN}[INFO] Redis đã khởi động${NC}"
    else
        echo -e "${GREEN}[INFO] Redis đang chạy${NC}"
    fi
else
    echo -e "${YELLOW}[WARNING] Docker không khả dụng - đảm bảo Redis đang chạy thủ công${NC}"
fi

# Setup database
echo -e "${YELLOW}[INFO] Kiểm tra database...${NC}"
python setup_database.py

# Start server
echo ""
echo -e "${GREEN}[SUCCESS] Khởi động FastAPI server...${NC}"
echo -e "${GREEN}[INFO] API:     http://localhost:5001${NC}"
echo -e "${GREEN}[INFO] Docs:    http://localhost:5001/docs${NC}"
echo -e "${GREEN}[INFO] Metrics: http://localhost:5001/metrics${NC}"
echo -e "${GREEN}[INFO] WS:      ws://localhost:5001/api/ws/orders${NC}"
echo -e "${YELLOW}[INFO] Nhấn Ctrl+C để dừng server${NC}"
echo ""

python main.py