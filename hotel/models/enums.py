"""Các kiểu liệt kê (Enum): trạng thái phòng, trạng thái đặt phòng, vai trò, quyền."""

from enum import Enum

from hotel.utils.exceptions import ValidationError


class _LabeledEnum(Enum):
    """Enum có nhãn tiếng Việt và hàm chuyển đổi an toàn từ chuỗi."""

    @property
    def label(self) -> str:  # được ghi đè ở lớp con qua _LABELS
        return self._labels()[self]

    @classmethod
    def _labels(cls) -> dict:
        raise NotImplementedError

    @classmethod
    def parse(cls, value):
        """Chuyển chuỗi (value) hoặc chính Enum thành thành viên Enum."""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            valid = ", ".join(m.value for m in cls)
            raise ValidationError(f"Giá trị '{value}' không hợp lệ (cho phép: {valid}).") from None


class RoomStatus(_LabeledEnum):
    """Trạng thái hiện tại của phòng."""

    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"

    @classmethod
    def _labels(cls) -> dict:
        return {cls.AVAILABLE: "Trống", cls.OCCUPIED: "Đang ở", cls.MAINTENANCE: "Bảo trì"}


class BookingStatus(_LabeledEnum):
    """Vòng đời đặt phòng: Đã đặt -> Đang ở -> Đã trả (hoặc Đã đặt -> Đã hủy)."""

    BOOKED = "booked"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"

    @classmethod
    def _labels(cls) -> dict:
        return {cls.BOOKED: "Đã đặt", cls.CHECKED_IN: "Đang ở",
                cls.CHECKED_OUT: "Đã trả", cls.CANCELLED: "Đã hủy"}

    @property
    def is_active(self) -> bool:
        """Đặt phòng còn hiệu lực (đang giữ phòng)."""
        return self in (BookingStatus.BOOKED, BookingStatus.CHECKED_IN)


class Role(_LabeledEnum):
    """Vai trò người dùng."""

    ADMIN = "admin"
    RECEPTIONIST = "receptionist"

    @classmethod
    def _labels(cls) -> dict:
        return {cls.ADMIN: "Quản trị viên", cls.RECEPTIONIST: "Lễ tân"}


class Permission(Enum):
    """Các quyền thao tác trong hệ thống."""

    VIEW_ROOMS = "Xem phòng"
    MANAGE_ROOMS = "Thêm/sửa/xóa phòng"
    MANAGE_GUESTS = "Quản lý khách hàng"
    MANAGE_BOOKINGS = "Quản lý đặt phòng"
    VIEW_SERVICES = "Xem dịch vụ"
    MANAGE_SERVICES = "Thêm/sửa/xóa dịch vụ"
    VIEW_REPORTS = "Xem thống kê"
    EXPORT_REPORTS = "Xuất báo cáo CSV"
    MANAGE_USERS = "Quản lý tài khoản"
