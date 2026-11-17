"""Các thực thể, trạng thái và ngoại lệ tối giản dùng riêng cho module F5 (Chức năng Xóa).

Hoàn toàn độc lập, không phụ thuộc hay import từ dự án chính.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


# ===================================================================== Ngoại lệ
class DeleteError(Exception):
    """Lớp cha cho các lỗi trong module chức năng Xóa."""


class NotFoundError(DeleteError):
    """Không tìm thấy đối tượng theo mã."""


class BusinessRuleError(DeleteError):
    """Vi phạm ràng buộc nghiệp vụ (còn dữ liệu liên quan, admin cuối cùng...)."""


class DeletionCancelled(DeleteError):
    """Người dùng hủy thao tác xác nhận xóa."""


# ===================================================================== Enum
class RoomStatus(Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"

    @property
    def label(self) -> str:
        return {
            RoomStatus.AVAILABLE: "Trống",
            RoomStatus.OCCUPIED: "Đang ở",
            RoomStatus.MAINTENANCE: "Bảo trì",
        }[self]


class BookingStatus(Enum):
    BOOKED = "booked"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"

    @property
    def label(self) -> str:
        return {
            BookingStatus.BOOKED: "Đã đặt",
            BookingStatus.CHECKED_IN: "Đang ở",
            BookingStatus.CHECKED_OUT: "Đã trả",
            BookingStatus.CANCELLED: "Đã hủy",
        }[self]

    @property
    def is_active(self) -> bool:
        """Đặt phòng còn hiệu lực (đang giữ hoặc đang sử dụng phòng)."""
        return self in (BookingStatus.BOOKED, BookingStatus.CHECKED_IN)


class Role(Enum):
    ADMIN = "admin"
    RECEPTIONIST = "receptionist"

    @property
    def label(self) -> str:
        return {
            Role.ADMIN: "Quản trị viên",
            Role.RECEPTIONIST: "Lễ tân",
        }[self]


# ===================================================================== Thực thể
@dataclass
class Room:
    room_id: str
    room_number: str
    room_type: str
    price_per_night: float
    status: RoomStatus = RoomStatus.AVAILABLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "room_number": self.room_number,
            "room_type": self.room_type,
            "price_per_night": self.price_per_night,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Room":
        return cls(
            room_id=str(data["room_id"]).strip().upper(),
            room_number=str(data["room_number"]).strip(),
            room_type=str(data["room_type"]).strip(),
            price_per_night=float(data["price_per_night"]),
            status=RoomStatus(data.get("status", RoomStatus.AVAILABLE.value)),
        )


@dataclass
class Guest:
    guest_id: str
    full_name: str
    phone: str
    id_card: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "guest_id": self.guest_id,
            "full_name": self.full_name,
            "phone": self.phone,
            "id_card": self.id_card,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Guest":
        return cls(
            guest_id=str(data["guest_id"]).strip().upper(),
            full_name=str(data["full_name"]).strip(),
            phone=str(data["phone"]).strip(),
            id_card=str(data.get("id_card", "")).strip(),
        )


@dataclass
class Service:
    service_id: str
    name: str
    price: float
    unit: str = "lần"

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "name": self.name,
            "price": self.price,
            "unit": self.unit,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Service":
        return cls(
            service_id=str(data["service_id"]).strip().upper(),
            name=str(data["name"]).strip(),
            price=float(data["price"]),
            unit=str(data.get("unit", "lần")).strip(),
        )


@dataclass
class Booking:
    booking_id: str
    guest_id: str
    room_id: str
    check_in: str
    check_out: str
    status: BookingStatus = BookingStatus.BOOKED

    def to_dict(self) -> dict[str, Any]:
        return {
            "booking_id": self.booking_id,
            "guest_id": self.guest_id,
            "room_id": self.room_id,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Booking":
        return cls(
            booking_id=str(data["booking_id"]).strip().upper(),
            guest_id=str(data["guest_id"]).strip().upper(),
            room_id=str(data["room_id"]).strip().upper(),
            check_in=str(data["check_in"]),
            check_out=str(data["check_out"]),
            status=BookingStatus(data.get("status", BookingStatus.BOOKED.value)),
        )


@dataclass
class User:
    username: str
    full_name: str
    role: Role

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        return cls(
            username=str(data["username"]).strip().lower(),
            full_name=str(data["full_name"]).strip(),
            role=Role(data["role"]),
        )
