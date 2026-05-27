"""
WebSocket endpoints cho POS real-time.

Endpoints:
  WS  /ws/{room}           → kết nối vào room cụ thể
  GET /ws/stats            → số connections hiện tại
  POST /ws/broadcast       → admin gửi broadcast (test/debug)

Rooms:
  - orders    : theo dõi đơn hàng mới/cập nhật
  - inventory : theo dõi tồn kho
  - dashboard : tổng quan real-time
  - global    : nhận mọi event

Flow FE:
  const ws = new WebSocket("ws://localhost:5001/api/ws/orders");
  ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      if (event.type === "order.created") updateOrderList(event.payload);
      if (event.type === "inventory.low_stock") showAlert(event.payload);
  };
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..websocket_manager import manager, system_event
from ..logger import log_info, log_error

router = APIRouter(prefix="/ws", tags=["websocket"])

VALID_ROOMS = {"orders", "inventory", "dashboard", "global"}


@router.websocket("/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    """
    WebSocket endpoint — client kết nối vào room.

    Khi kết nối thành công:
      1. Server gửi welcome message với stats
      2. Client ping mỗi 30s → server pong (keep-alive)
      3. Khi có event (tạo đơn, cập nhật kho...) → server broadcast

    Message format từ server:
      {"type": "order.created", "payload": {...}}
      {"type": "inventory.low_stock", "payload": {...}}
      {"type": "system.notification", "payload": {"message": "...", "level": "info"}}

    Message format từ client (ping):
      {"type": "ping"}
    """
    # Validate room
    if room not in VALID_ROOMS:
        await websocket.close(code=4004, reason=f"Room '{room}' không tồn tại. Rooms hợp lệ: {VALID_ROOMS}")
        return

    await manager.connect(websocket, room)

    try:
        # Gửi welcome message
        await manager.send_personal({
            "type": "connection.established",
            "payload": {
                "room":    room,
                "message": f"Đã kết nối vào room '{room}'",
                "stats":   manager.get_stats(),
            },
        }, websocket)

        # Message loop
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0,   # 60s timeout nếu không có gì
                )
                # Xử lý ping từ client
                import json
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await manager.send_personal({"type": "pong"}, websocket)
                except Exception:
                    pass

            except asyncio.TimeoutError:
                # Gửi ping để kiểm tra client còn sống không
                try:
                    await manager.send_personal({"type": "ping"}, websocket)
                except Exception:
                    break

    except WebSocketDisconnect:
        log_info("WS", f"Client ngắt kết nối khỏi room '{room}'")
    except Exception as e:
        log_error("WS", f"Lỗi WebSocket room '{room}': {e}")
    finally:
        await manager.disconnect(websocket, room)


@router.get("/stats")
async def websocket_stats():
    """Xem số connections hiện tại — dùng cho monitoring."""
    return {
        "success": True,
        "data":    manager.get_stats(),
    }


@router.post("/broadcast")
async def broadcast_message(
    room:    str,
    message: str,
    level:   str = "info",
):
    """
    Gửi broadcast message đến room — dùng để test.
    Trong production: chỉ admin mới được dùng.
    """
    if room not in VALID_ROOMS and room != "all":
        raise HTTPException(status_code=400, detail=f"Room không hợp lệ: {room}")

    event = system_event(message, level)

    if room == "all":
        sent = await manager.broadcast_all_rooms(event)
    else:
        sent = await manager.broadcast(event, room)

    return {
        "success":    True,
        "sent_to":    sent,
        "room":       room,
        "message":    message,
    }