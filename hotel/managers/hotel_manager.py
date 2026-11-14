"""Lớp điều phối trung tâm ``HotelManager`` (mẫu Facade).

Giữ tất cả các manager, kiểm tra quyền, kiểm tra ràng buộc liên đối tượng
(vd: không xóa phòng đang có đặt phòng) và tự động lưu dữ liệu sau mỗi thay đổi.
Tầng giao diện chỉ gọi các phương thức ở đây cho thao tác ghi dữ liệu.
"""

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from hotel.managers.auth_manager import AuthManager
from hotel.managers.booking_manager import BookingManager
from hotel.managers.guest_manager import GuestManager
from hotel.managers.report_manager import ReportManager
from hotel.managers.room_manager import RoomManager
from hotel.managers.service_manager import ServiceManager
from hotel.models.booking import Booking
from hotel.models.enums import Permission, Role, RoomStatus
from hotel.models.guest import Guest
from hotel.models.invoice import Invoice
from hotel.models.room import Room
from hotel.models.service import Service, ServiceUsage
from hotel.models.user import User
from hotel.storage.json_storage import JsonStorage
from hotel.utils.exceptions import BusinessRuleError
from hotel.utils.formatter import format_date

DEFAULT_USERS = [
    (Role.ADMIN, "admin", "admin123", "Quản Trị Viên"),
    (Role.RECEPTIONIST, "letan", "letan123", "Nhân Viên Lễ Tân"),
]


class HotelManager:
    """Điểm truy cập duy nhất tới nghiệp vụ khách sạn."""

    DATASETS = ("rooms", "guests", "services", "bookings", "users")

    def __init__(self, data_dir: str | Path = "data", invoice_dir: str | Path = "invoices",
                 export_dir: str | Path = "exports",
                 today_provider: Callable[[], date] = date.today,
                 auto_save: bool = True) -> None:
        self.__storage = JsonStorage(data_dir)
        self.__invoice_dir = Path(invoice_dir)
        self.__export_dir = Path(export_dir)
        self.__today = today_provider
        self.__auto_save = auto_save
        self.__rooms = RoomManager()
        self.__guests = GuestManager()
        self.__services = ServiceManager()
        self.__bookings = BookingManager(self.__rooms, self.__guests, self.__services,
                                         today_provider=today_provider)
        self.__reports = ReportManager(self.__rooms, self.__guests, self.__bookings,
                                       today_provider=today_provider)
        self.__auth = AuthManager()

    # ------------------------------------------------------------ properties
    @property
    def rooms(self) -> RoomManager:
        return self.__rooms

    @property
    def guests(self) -> GuestManager:
        return self.__guests

    @property
    def services(self) -> ServiceManager:
        return self.__services

    @property
    def bookings(self) -> BookingManager:
        return self.__bookings

    @property
    def reports(self) -> ReportManager:
        return self.__reports

    @property
    def auth(self) -> AuthManager:
        return self.__auth

    @property
    def current_user(self) -> User | None:
        return self.__auth.current_user

    def today(self) -> date:
        return self.__today()

    # ---------------------------------------------------------- lưu trữ
    def _managers(self) -> dict[str, Any]:
        return {"rooms": self.__rooms, "guests": self.__guests, "services": self.__services,
                "bookings": self.__bookings, "users": self.__auth}

    def load(self, seed_if_empty: bool = True) -> list[str]:
        """Nạp dữ liệu từ JSON. Lần chạy đầu tiên sẽ tạo dữ liệu mẫu.

        Returns:
            Danh sách cảnh báo (file hỏng, bản ghi lỗi, trạng thái được sửa...).
        """
        self.__storage.clear_warnings()
        warnings: list[str] = []
        loaded = {name: self.__storage.load(name) for name in self.DATASETS}
        warnings += self.__storage.warnings
        for name, manager in self._managers().items():
            warnings += manager.load_dicts(loaded[name] or [])

        business_data = [loaded[n] for n in ("rooms", "guests", "services", "bookings")]
        if seed_if_empty and all(data is None for data in business_data):
            from hotel.storage.seed_data import populate  # tránh import vòng
            populate(self)
            warnings.append("Chưa có dữ liệu – đã tạo dữ liệu mẫu.")
        if len(self.__auth) == 0:
            for role, username, password, full_name in DEFAULT_USERS:
                self.__auth.add_user(role, username, password, full_name)
            warnings.append("Đã tạo tài khoản mặc định: admin/admin123, letan/letan123.")
        warnings += self._sync_room_status()
        self.save()
        return warnings

    def _sync_room_status(self) -> list[str]:
        """Đồng bộ trạng thái phòng với các đặt phòng Đang ở (phòng khi dữ liệu bị sửa tay)."""
        fixes = []
        staying = {b.room_id for b in self.__bookings.list_all()
                   if b.status.value == "checked_in"}
        for room in self.__rooms.list_all():
            if room.room_id in staying and room.status != RoomStatus.OCCUPIED:
                room.status = RoomStatus.OCCUPIED
                fixes.append(f"Phòng {room.room_number} có khách đang ở → chuyển 'Đang ở'.")
            elif room.room_id not in staying and room.status == RoomStatus.OCCUPIED:
                room.status = RoomStatus.AVAILABLE
                fixes.append(f"Phòng {room.room_number} không có khách đang ở → chuyển 'Trống'.")
        return fixes

    def save(self) -> None:
        """Ghi toàn bộ dữ liệu ra JSON."""
        for name, manager in self._managers().items():
            self.__storage.save(name, manager.to_dicts())

    def _commit(self) -> None:
        if self.__auto_save:
            self.save()

    # ---------------------------------------------------------- đăng nhập
    def login(self, username: str, password: str) -> User:
        return self.__auth.login(username, password)

    def logout(self) -> None:
        self.__auth.logout()

    def require(self, permission: Permission) -> None:
        self.__auth.require(permission)

    def can(self, permission: Permission) -> bool:
        user = self.current_user
        return user is not None and user.has_permission(permission)

    # ---------------------------------------------------------------- phòng
    def add_room(self, room: Room) -> Room:
        self.require(Permission.MANAGE_ROOMS)
        self.__rooms.add(room)
        self._commit()
        return room

    def update_room(self, room_id: str, **changes: Any) -> tuple[Room, list[str]]:
        """Cập nhật phòng. Trả về (phòng mới, cảnh báo)."""
        self.require(Permission.MANAGE_ROOMS)
        room = self.__rooms.get(room_id)
        warnings: list[str] = []
        if "status" in changes:
            new_status = RoomStatus.parse(changes["status"])
            if new_status != room.status:
                if room.status == RoomStatus.OCCUPIED:
                    raise BusinessRuleError(
                        f"Phòng {room.room_number} đang có khách, chỉ đổi trạng thái qua trả phòng.")
                if new_status == RoomStatus.OCCUPIED:
                    raise BusinessRuleError(
                        "Chỉ chuyển sang 'Đang ở' thông qua nghiệp vụ nhận phòng.")
                if new_status == RoomStatus.MAINTENANCE:
                    upcoming = self.__bookings.active_for_room(room.room_id)
                    if upcoming:
                        ids = ", ".join(b.booking_id for b in upcoming)
                        warnings.append(f"Phòng còn các đặt phòng sắp tới: {ids}. "
                                        "Hãy đổi phòng cho khách trước ngày nhận.")
            changes["status"] = new_status.value
        updated = self.__rooms.update(room_id, **changes)
        self._commit()
        return updated, warnings

    def delete_room(self, room_id: str) -> Room:
        """Xóa phòng – không cho xóa khi còn đặt phòng hiệu lực."""
        self.require(Permission.MANAGE_ROOMS)
        room = self.__rooms.get(room_id)
        active = self.__bookings.active_for_room(room.room_id)
        if active:
            detail = ", ".join(f"{b.booking_id} ({b.status.label})" for b in active)
            raise BusinessRuleError(
                f"Không thể xóa phòng {room.room_number}: còn đặt phòng hiệu lực {detail}.")
        self.__rooms.remove(room.room_id)
        self._commit()
        return room

    # ------------------------------------------------------------ khách hàng
    def add_guest(self, guest: Guest) -> Guest:
        self.require(Permission.MANAGE_GUESTS)
        self.__guests.add(guest)
        self._commit()
        return guest

    def update_guest(self, guest_id: str, **changes: Any) -> Guest:
        self.require(Permission.MANAGE_GUESTS)
        guest = self.__guests.update(guest_id, **changes)
        self._commit()
        return guest

    def delete_guest(self, guest_id: str) -> Guest:
        """Xóa khách – không cho xóa khi khách còn đặt phòng hiệu lực."""
        self.require(Permission.MANAGE_GUESTS)
        guest = self.__guests.get(guest_id)
        active = self.__bookings.active_for_guest(guest.guest_id)
        if active:
            detail = ", ".join(f"{b.booking_id} ({b.status.label})" for b in active)
            raise BusinessRuleError(
                f"Không thể xóa khách {guest.full_name}: còn đặt phòng hiệu lực {detail}.")
        self.__guests.remove(guest.guest_id)
        self._commit()
        return guest

    # --------------------------------------------------------------- dịch vụ
    def add_service(self, service: Service) -> Service:
        self.require(Permission.MANAGE_SERVICES)
        self.__services.add(service)
        self._commit()
        return service

    def update_service(self, service_id: str, **changes: Any) -> Service:
        self.require(Permission.MANAGE_SERVICES)
        service = self.__services.update(service_id, **changes)
        self._commit()
        return service

    def delete_service(self, service_id: str) -> Service:
        """Xóa dịch vụ khỏi danh mục (lượt đã dùng vẫn giữ tên và giá trong booking)."""
        self.require(Permission.MANAGE_SERVICES)
        service = self.__services.remove(service_id)
        self._commit()
        return service

    # ------------------------------------------------------------ đặt phòng
    def create_booking(self, booking_id: str, guest_id: str, room_id: str,
                       check_in: date, check_out: date) -> Booking:
        self.require(Permission.MANAGE_BOOKINGS)
        booking = self.__bookings.create_booking(booking_id, guest_id, room_id,
                                                 check_in, check_out)
        self._commit()
        return booking

    def update_booking(self, booking_id: str, **changes: Any) -> Booking:
        self.require(Permission.MANAGE_BOOKINGS)
        booking = self.__bookings.update_booking(booking_id, **changes)
        self._commit()
        return booking

    def cancel_booking(self, booking_id: str) -> Booking:
        self.require(Permission.MANAGE_BOOKINGS)
        booking = self.__bookings.cancel_booking(booking_id)
        self._commit()
        return booking

    def check_in(self, booking_id: str) -> Booking:
        self.require(Permission.MANAGE_BOOKINGS)
        booking = self.__bookings.check_in(booking_id)
        self._commit()
        return booking

    def add_service_to_booking(self, booking_id: str, service_id: str,
                               quantity: int) -> ServiceUsage:
        self.require(Permission.MANAGE_BOOKINGS)
        usage = self.__bookings.add_service_usage(booking_id, service_id, quantity)
        self._commit()
        return usage

    def build_invoice(self, booking_id: str) -> Invoice:
        """Tạo hóa đơn cho một đặt phòng (đã trả hoặc đang ở – để xem trước)."""
        booking = self.__bookings.get(booking_id)
        return Invoice(booking, self.__guests.find(booking.guest_id),
                       self.__rooms.find(booking.room_id),
                       self.__bookings.discount_details(booking))

    def check_out(self, booking_id: str) -> tuple[Booking, Invoice, Path]:
        """Trả phòng, tạo hóa đơn và lưu file. Trả về (booking, hóa đơn, đường dẫn)."""
        self.require(Permission.MANAGE_BOOKINGS)
        booking = self.__bookings.check_out(booking_id)
        self._commit()
        invoice = self.build_invoice(booking.booking_id)
        path = invoice.save(self.__invoice_dir)
        return booking, invoice, path

    # ------------------------------------------------------------- báo cáo
    def export_csv(self, kind: str) -> Path:
        self.require(Permission.EXPORT_REPORTS)
        return self.__reports.export_csv(kind, self.__export_dir)

    # ------------------------------------------------------------ tài khoản
    def add_user(self, role: Role | str, username: str, password: str, full_name: str) -> User:
        self.require(Permission.MANAGE_USERS)
        user = self.__auth.add_user(role, username, password, full_name)
        self._commit()
        return user

    def delete_user(self, username: str) -> User:
        self.require(Permission.MANAGE_USERS)
        user = self.__auth.delete_user(username)
        self._commit()
        return user

    def change_password(self, old_password: str, new_password: str) -> None:
        self.__auth.change_password(old_password, new_password)
        self._commit()

    def describe_stay(self, booking: Booking) -> str:
        """Mô tả ngắn một đặt phòng kèm tên khách (dùng cho thông báo)."""
        guest = self.__guests.find(booking.guest_id)
        name = guest.full_name if guest else booking.guest_id
        return (f"{booking.booking_id} – {name} – phòng {booking.room_number} – "
                f"{format_date(booking.check_in)} → {format_date(booking.check_out)} "
                f"({booking.nights} đêm)")
