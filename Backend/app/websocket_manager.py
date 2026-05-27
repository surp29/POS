"""
WebSocket Connection Manager.

Quản lý tất cả WebSocket connections đang active.
Hỗ trợ:
  - Broadcast: gửi đến TẤT CẢ clients đang kết nối
  - Room broadcast: gửi đến nhóm clients theo "room" (vd: "orders", "inventory")
  - Direct send: gửi đến 1 client cụ thể

Tại sao cần WebSocket cho POS?
  - Thu ngân tạo đơn → màn hình bếp/kho cập nhật ngay (không cần refresh)
  - Tồn kho thay đổi → dashboard admin thấy ngay
  - Nhiều tab/màn hình cùng nhìn vào 1 hệ thống → đồng bộ real-time
"""
import json
import asyncio
from typing import Optional
from fastapi import WebSocket
from .logger import log_info, log_warning, log_error


class ConnectionManager:
    """
    Quản lý WebSocket connections theo room.

    Room là nhóm logic để broadcast có chọn lọc:
      - "orders"    : các màn hình theo dõi đơn hàng
      - "inventory" : màn hình kho hàng
      - "dashboard" : màn hình tổng quan admin
      - "global"    : mọi client (broadcast toàn bộ)
    """

    def __init__(self):
        # Dict[room_name, List[WebSocket]]
        self._rooms: dict[str, list[WebSocket]] = {}
        # Dict[WebSocket, set[room_name]] — biết 1 client đang ở rooms nào
        self._client_rooms: dict[int, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room: str = "global") -> None:
        """Chấp nhận kết nối và thêm vào room."""
        await websocket.accept()

        async with self._lock:
            if room not in self._rooms:
                self._rooms[room] = []
            self._rooms[room].append(websocket)

            client_id = id(websocket)
            if client_id not in self._client_rooms:
                self._client_rooms[client_id] = set()
            self._client_rooms[client_id].add(room)

        log_info("WS", f"Client {id(websocket)} kết nối vào room '{room}'. "
                       f"Tổng: {self.count(room)} clients trong room.")

    async def disconnect(self, websocket: WebSocket, room: str = "global") -> None:
        """Xóa client khỏi room khi disconnect."""
        async with self._lock:
            if room in self._rooms and websocket in self._rooms[room]:
                self._rooms[room].remove(websocket)
                if not self._rooms[room]:
                    del self._rooms[room]

            client_id = id(websocket)
            if client_id in self._client_rooms:
                self._client_rooms[client_id].discard(room)
                if not self._client_rooms[client_id]:
                    del self._client_rooms[client_id]

        log_info("WS", f"Client {id(websocket)} ngắt kết nối khỏi room '{room}'.")

    async def disconnect_all(self, websocket: WebSocket) -> None:
        """Xóa client khỏi tất cả rooms."""
        client_id = id(websocket)
        rooms = list(self._client_rooms.get(client_id, set()))
        for room in rooms:
            await self.disconnect(websocket, room)

    async def broadcast(self, message: dict, room: str = "global") -> int:
        """
        Gửi message đến tất cả clients trong room.
        Trả về số clients nhận được.
        """
        if room not in self._rooms:
            return 0

        payload    = json.dumps(message, ensure_ascii=False, default=str)
        dead_socks = []
        sent_count = 0

        for websocket in list(self._rooms.get(room, [])):
            try:
                await websocket.send_text(payload)
                sent_count += 1
            except Exception:
                dead_socks.append(websocket)

        # Cleanup dead connections
        for ws in dead_socks:
            await self.disconnect(ws, room)
            log_warning("WS", f"Đã xóa dead connection khỏi room '{room}'")

        return sent_count

    async def broadcast_all_rooms(self, message: dict) -> int:
        """Gửi message đến TẤT CẢ clients ở mọi room."""
        total = 0
        for room in list(self._rooms.keys()):
            total += await self.broadcast(message, room)
        return total

    async def send_personal(self, message: dict, websocket: WebSocket) -> bool:
        """Gửi message đến 1 client cụ thể."""
        try:
            payload = json.dumps(message, ensure_ascii=False, default=str)
            await websocket.send_text(payload)
            return True
        except Exception as e:
            log_error("WS", f"Lỗi gửi personal message: {e}")
            return False

    def count(self, room: str = "global") -> int:
        """Số clients đang kết nối trong room."""
        return len(self._rooms.get(room, []))

    def count_all(self) -> int:
        """Tổng số clients đang kết nối."""
        return sum(len(clients) for clients in self._rooms.values())

    def get_rooms(self) -> list[str]:
        """Danh sách rooms đang có client."""
        return list(self._rooms.keys())

    def get_stats(self) -> dict:
        """Thống kê connections cho /health và /metrics."""
        return {
            "total_connections": self.count_all(),
            "rooms": {room: len(clients) for room, clients in self._rooms.items()},
        }


# ── Singleton instance ────────────────────────────────────────────────────────
# Dùng chung toàn app — import từ đây thay vì tạo instance mới
manager = ConnectionManager()


# ── Event builders ────────────────────────────────────────────────────────────
# Chuẩn hóa format message để FE dễ parse

def order_event(event_type: str, order_data: dict) -> dict:
    """
    Tạo WebSocket event cho đơn hàng.

    event_type: "created" | "updated" | "deleted" | "status_changed"
    """
    return {
        "type":    f"order.{event_type}",
        "payload": order_data,
    }


def inventory_event(event_type: str, product_data: dict) -> dict:
    """
    Tạo WebSocket event cho tồn kho.

    event_type: "updated" | "low_stock" | "out_of_stock"
    """
    return {
        "type":    f"inventory.{event_type}",
        "payload": product_data,
    }


def system_event(message: str, level: str = "info") -> dict:
    """Event hệ thống: thông báo, cảnh báo."""
    return {
        "type":    "system.notification",
        "payload": {"message": message, "level": level},
    }