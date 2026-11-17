"""Class riêng thực hiện chức năng F5: Xóa (Delete) – Phần công việc của Đạt.

Quy trình chuẩn của F5 cho mọi đối tượng:
1. Tìm đối tượng theo mã (chuẩn hóa mã, không phân biệt hoa/thường).
2. Kiểm tra ràng buộc liên quan:
   - Phòng: không xóa nếu còn đặt phòng ở trạng thái 'Đã đặt' (BOOKED) hoặc 'Đang ở' (CHECKED_IN).
   - Khách hàng: không xóa nếu khách còn đặt phòng còn hiệu lực (BOOKED / CHECKED_IN).
   - Dịch vụ: cho phép xóa khỏi danh mục (các hóa đơn cũ đã lưu snapshot riêng).
   - Tài khoản: không xóa tài khoản đang đăng nhập và không xóa Admin cuối cùng.
3. Xác nhận trước khi xóa (qua tham số ``confirmed`` hoặc hàm ``confirm_fn``).
4. Thực hiện xóa và lưu dữ liệu (nếu cấu hình ``data_dir``).
"""

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from entities import (
    Booking,
    BookingStatus,
    BusinessRuleError,
    DeletionCancelled,
    Guest,
    NotFoundError,
    Role,
    Room,
    RoomStatus,
    Service,
    User,
)

T = TypeVar("T")


class DeleteManager:
    """Lớp độc lập quản lý nghiệp vụ Xóa (F5) trong hệ thống quản lý khách sạn."""

    def __init__(
        self,
        rooms: list[Room] | None = None,
        guests: list[Guest] | None = None,
        services: list[Service] | None = None,
        bookings: list[Booking] | None = None,
        users: list[User] | None = None,
        *,
        data_dir: str | Path | None = None,
    ) -> None:
        self.__data_dir = Path(data_dir) if data_dir is not None else None
        self.__rooms: dict[str, Room] = {}
        self.__guests: dict[str, Guest] = {}
        self.__services: dict[str, Service] = {}
        self.__bookings: dict[str, Booking] = {}
        self.__users: dict[str, User] = {}

        if self.__data_dir is not None and all(
            v is None for v in (rooms, guests, services, bookings, users)
        ):
            self.load_or_seed()
        else:
            self._populate_dicts(
                rooms or [],
                guests or [],
                services or [],
                bookings or [],
                users or [],
            )

    # ------------------------------------------------------------ Chuẩn hóa & truy cập
    @staticmethod
    def normalize_id(raw_id: str) -> str:
        """Chuẩn hóa mã định danh (bỏ khoảng trắng thừa, viết hoa)."""
        return str(raw_id).strip().upper()

    @property
    def rooms(self) -> list[Room]:
        return list(self.__rooms.values())

    @property
    def guests(self) -> list[Guest]:
        return list(self.__guests.values())

    @property
    def services(self) -> list[Service]:
        return list(self.__services.values())

    @property
    def bookings(self) -> list[Booking]:
        return list(self.__bookings.values())

    @property
    def users(self) -> list[User]:
        return list(self.__users.values())

    def _populate_dicts(
        self,
        rooms: list[Room],
        guests: list[Guest],
        services: list[Service],
        bookings: list[Booking],
        users: list[User],
    ) -> None:
        self.__rooms = {self.normalize_id(r.room_id): r for r in rooms}
        self.__guests = {self.normalize_id(g.guest_id): g for g in guests}
        self.__services = {self.normalize_id(s.service_id): s for s in services}
        self.__bookings = {self.normalize_id(b.booking_id): b for b in bookings}
        self.__users = {self.normalize_id(u.username): u for u in users}

    # ------------------------------------------------------------ 1. Tìm theo mã
    def find_room(self, room_id: str) -> Room:
        key = self.normalize_id(room_id)
        room = self.__rooms.get(key)
        if room is None:
            raise NotFoundError(f"Không tìm thấy phòng có mã '{room_id}'.")
        return room

    def find_guest(self, guest_id: str) -> Guest:
        key = self.normalize_id(guest_id)
        guest = self.__guests.get(key)
        if guest is None:
            raise NotFoundError(f"Không tìm thấy khách hàng có mã '{guest_id}'.")
        return guest

    def find_service(self, service_id: str) -> Service:
        key = self.normalize_id(service_id)
        service = self.__services.get(key)
        if service is None:
            raise NotFoundError(f"Không tìm thấy dịch vụ có mã '{service_id}'.")
        return service

    def find_user(self, username: str) -> User:
        key = self.normalize_id(username)
        user = self.__users.get(key)
        if user is None:
            raise NotFoundError(f"Không tìm thấy tài khoản '{username}'.")
        return user

    # ------------------------------------------------- 2. Kiểm tra ràng buộc
    def active_bookings_for_room(self, room_id: str) -> list[Booking]:
        """Các đặt phòng còn hiệu lực (Đã đặt / Đang ở) của một phòng."""
        key = self.normalize_id(room_id)
        return [
            b for b in self.__bookings.values()
            if self.normalize_id(b.room_id) == key and b.status.is_active
        ]

    def active_bookings_for_guest(self, guest_id: str) -> list[Booking]:
        """Các đặt phòng còn hiệu lực (Đã đặt / Đang ở) của một khách hàng."""
        key = self.normalize_id(guest_id)
        return [
            b for b in self.__bookings.values()
            if self.normalize_id(b.guest_id) == key and b.status.is_active
        ]

    def can_delete_room(self, room_id: str) -> tuple[bool, str]:
        """Kiểm tra phòng có đủ điều kiện xóa không."""
        room = self.find_room(room_id)
        active = self.active_bookings_for_room(room.room_id)
        if active:
            detail = ", ".join(f"{b.booking_id} ({b.status.label})" for b in active)
            return (
                False,
                f"Không thể xóa phòng {room.room_number} ({room.room_id}): "
                f"còn đặt phòng hiệu lực {detail}.",
            )
        return True, ""

    def can_delete_guest(self, guest_id: str) -> tuple[bool, str]:
        """Kiểm tra khách hàng có đủ điều kiện xóa không."""
        guest = self.find_guest(guest_id)
        active = self.active_bookings_for_guest(guest.guest_id)
        if active:
            detail = ", ".join(f"{b.booking_id} ({b.status.label})" for b in active)
            return (
                False,
                f"Không thể xóa khách {guest.full_name} ({guest.guest_id}): "
                f"còn đặt phòng hiệu lực {detail}.",
            )
        return True, ""

    def can_delete_service(self, service_id: str) -> tuple[bool, str]:
        """Kiểm tra dịch vụ (luôn cho phép xóa khỏi danh mục nếu tồn tại)."""
        self.find_service(service_id)
        return True, ""

    def can_delete_user(
        self, username: str, *, current_username: str | None = None
    ) -> tuple[bool, str]:
        """Kiểm tra tài khoản có đủ điều kiện xóa không."""
        user = self.find_user(username)
        if current_username and self.normalize_id(current_username) == self.normalize_id(user.username):
            return False, "Không thể xóa tài khoản đang đăng nhập."
        admins = [u for u in self.__users.values() if u.role == Role.ADMIN]
        if user.role == Role.ADMIN and len(admins) <= 1:
            return False, "Phải còn ít nhất một tài khoản quản trị viên (Admin)."
        return True, ""

    # ------------------------------------------ 3. Xác nhận & Thực thi xóa
    @staticmethod
    def _verify_confirmation(
        item: T,
        *,
        confirmed: bool = True,
        confirm_fn: Callable[[T], bool] | None = None,
    ) -> None:
        """Xác nhận trước khi xóa: ưu tiên ``confirm_fn`` nếu được truyền vào."""
        accepted = confirm_fn(item) if confirm_fn is not None else confirmed
        if not accepted:
            raise DeletionCancelled("Người dùng đã hủy thao tác xóa.")

    def delete_room(
        self,
        room_id: str,
        *,
        confirmed: bool = True,
        confirm_fn: Callable[[Room], bool] | None = None,
    ) -> Room:
        """Xóa phòng theo mã: tìm -> kiểm tra ràng buộc booked -> xác nhận -> xóa."""
        room = self.find_room(room_id)
        allowed, reason = self.can_delete_room(room.room_id)
        if not allowed:
            raise BusinessRuleError(reason)
        self._verify_confirmation(room, confirmed=confirmed, confirm_fn=confirm_fn)
        del self.__rooms[self.normalize_id(room.room_id)]
        self.save()
        return room

    def delete_guest(
        self,
        guest_id: str,
        *,
        confirmed: bool = True,
        confirm_fn: Callable[[Guest], bool] | None = None,
    ) -> Guest:
        """Xóa khách hàng theo mã: tìm -> kiểm tra ràng buộc -> xác nhận -> xóa."""
        guest = self.find_guest(guest_id)
        allowed, reason = self.can_delete_guest(guest.guest_id)
        if not allowed:
            raise BusinessRuleError(reason)
        self._verify_confirmation(guest, confirmed=confirmed, confirm_fn=confirm_fn)
        del self.__guests[self.normalize_id(guest.guest_id)]
        self.save()
        return guest

    def delete_service(
        self,
        service_id: str,
        *,
        confirmed: bool = True,
        confirm_fn: Callable[[Service], bool] | None = None,
    ) -> Service:
        """Xóa dịch vụ theo mã: tìm -> xác nhận -> xóa."""
        service = self.find_service(service_id)
        self._verify_confirmation(service, confirmed=confirmed, confirm_fn=confirm_fn)
        del self.__services[self.normalize_id(service.service_id)]
        self.save()
        return service

    def delete_user(
        self,
        username: str,
        *,
        current_username: str | None = None,
        confirmed: bool = True,
        confirm_fn: Callable[[User], bool] | None = None,
    ) -> User:
        """Xóa tài khoản: tìm -> kiểm tra không tự xóa / không xóa admin cuối -> xác nhận -> xóa."""
        user = self.find_user(username)
        allowed, reason = self.can_delete_user(user.username, current_username=current_username)
        if not allowed:
            raise BusinessRuleError(reason)
        self._verify_confirmation(user, confirmed=confirmed, confirm_fn=confirm_fn)
        del self.__users[self.normalize_id(user.username)]
        self.save()
        return user

    # ------------------------------------------------------------ Lưu trữ độc lập
    def load_or_seed(self) -> None:
        """Nạp dữ liệu từ thư mục riêng ``data_dir``; nếu chưa có thì tạo dữ liệu mẫu."""
        if self.__data_dir is None:
            return
        files = {
            "rooms": self.__data_dir / "rooms.json",
            "guests": self.__data_dir / "guests.json",
            "services": self.__data_dir / "services.json",
            "bookings": self.__data_dir / "bookings.json",
            "users": self.__data_dir / "users.json",
        }
        if not any(path.is_file() for path in files.values()):
            self.reset_sample_data()
            return

        def read_json(path: Path) -> list[dict[str, Any]]:
            if not path.is_file():
                return []
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []

        self._populate_dicts(
            [Room.from_dict(r) for r in read_json(files["rooms"])],
            [Guest.from_dict(g) for g in read_json(files["guests"])],
            [Service.from_dict(s) for s in read_json(files["services"])],
            [Booking.from_dict(b) for b in read_json(files["bookings"])],
            [User.from_dict(u) for u in read_json(files["users"])],
        )

    def save(self) -> None:
        """Ghi an toàn dữ liệu riêng ra JSON (chỉ khi ``data_dir`` được cấu hình)."""
        if self.__data_dir is None:
            return
        self.__data_dir.mkdir(parents=True, exist_ok=True)
        datasets = {
            "rooms": [r.to_dict() for r in self.__rooms.values()],
            "guests": [g.to_dict() for g in self.__guests.values()],
            "services": [s.to_dict() for s in self.__services.values()],
            "bookings": [b.to_dict() for b in self.__bookings.values()],
            "users": [u.to_dict() for u in self.__users.values()],
        }
        for name, records in datasets.items():
            fd, tmp_path = tempfile.mkstemp(dir=self.__data_dir, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.__data_dir / f"{name}.json")

    def reset_sample_data(self) -> None:
        """Khởi tạo bộ dữ liệu mẫu độc lập để test/demo đầy đủ các trường hợp F5."""
        rooms = [
            Room("R001", "101", "Tiêu chuẩn", 500_000, RoomStatus.AVAILABLE),
            Room("R002", "102", "Tiêu chuẩn", 550_000, RoomStatus.AVAILABLE),
            Room("R003", "103", "Tiêu chuẩn", 600_000, RoomStatus.OCCUPIED),
            Room("R004", "201", "Cao cấp", 1_200_000, RoomStatus.AVAILABLE),
            Room("R005", "202", "Cao cấp", 1_300_000, RoomStatus.AVAILABLE),
            Room("R006", "203", "Cao cấp", 1_500_000, RoomStatus.MAINTENANCE),
        ]
        guests = [
            Guest("G001", "Nguyễn Văn An", "0901234567", "001090012345"),
            Guest("G002", "Trần Thị Bình", "0912345678", "079185001234"),
            Guest("G003", "Lê Hoàng Cường", "0987654321"),
            Guest("G004", "Phạm Thị Dung", "0934567890", "B1234567"),
        ]
        services = [
            Service("S001", "Minibar", 50_000, "lần"),
            Service("S002", "Giặt ủi", 30_000, "kg"),
            Service("S003", "Ăn sáng buffet", 150_000, "suất"),
        ]
        bookings = [
            Booking("B001", "G001", "R001", "2026-10-01", "2026-10-03", BookingStatus.CHECKED_OUT),
            Booking("B002", "G002", "R002", "2026-11-10", "2026-11-12", BookingStatus.CANCELLED),
            Booking("B003", "G003", "R003", "2026-11-16", "2026-11-19", BookingStatus.CHECKED_IN),
            Booking("B004", "G004", "R005", "2026-11-20", "2026-11-23", BookingStatus.BOOKED),
        ]
        users = [
            User("admin", "Quản Trị Viên", Role.ADMIN),
            User("admin2", "Quản Trị Dự Phòng", Role.ADMIN),
            User("letan", "Nhân Viên Lễ Tân", Role.RECEPTIONIST),
        ]
        self._populate_dicts(rooms, guests, services, bookings, users)
        self.save()
