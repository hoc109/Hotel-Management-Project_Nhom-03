"""Lớp thực thể đặt phòng (Booking) và vòng đời trạng thái của nó."""

from datetime import date, timedelta
from typing import Any

from hotel.models.enums import BookingStatus
from hotel.models.service import ServiceUsage
from hotel.utils.exceptions import BusinessRuleError, ValidationError
from hotel.utils.formatter import format_date, format_money
from hotel.utils.validators import parse_date, validate_date_range, validate_id


class Booking:
    """Một lượt đặt phòng của khách.

    Vòng đời: ``BOOKED`` (Đã đặt) -> ``CHECKED_IN`` (Đang ở) -> ``CHECKED_OUT`` (Đã trả),
    hoặc ``BOOKED`` -> ``CANCELLED`` (Đã hủy). Các phương thức chuyển trạng thái
    tự kiểm tra tính hợp lệ, bảo đảm không thể nhảy cóc trạng thái.

    Số đêm tối thiểu là 1: nhận và trả cùng ngày vẫn tính 1 đêm.
    """

    def __init__(self, booking_id: str, guest_id: str, room_id: str,
                 check_in: date | str, check_out: date | str, *,
                 status: BookingStatus | str = BookingStatus.BOOKED,
                 created_on: date | str | None = None,
                 room_number: str = "", room_type: str = "",
                 room_cost: float = 0.0, discount_rate: float = 0.0,
                 services: list[ServiceUsage] | None = None,
                 checked_in_on: date | str | None = None,
                 checked_out_on: date | str | None = None) -> None:
        self.__booking_id = validate_id(booking_id, "Mã đặt phòng")
        self.__guest_id = validate_id(guest_id, "Mã khách hàng")
        self.__room_id = validate_id(room_id, "Mã phòng")
        self.__check_in = parse_date(check_in, "Ngày nhận phòng")
        self.__check_out = parse_date(check_out, "Ngày trả phòng")
        validate_date_range(self.__check_in, self.__check_out)
        self.__status = BookingStatus.parse(status)
        self.__created_on = parse_date(created_on) if created_on else date.today()
        self.__room_number = room_number
        self.__room_type = room_type
        self.__room_cost = 0.0
        self.__discount_rate = 0.0
        self.set_pricing(room_cost, discount_rate)
        self.__services: list[ServiceUsage] = list(services or [])
        self.__checked_in_on = parse_date(checked_in_on) if checked_in_on else None
        self.__checked_out_on = parse_date(checked_out_on) if checked_out_on else None

    # ------------------------------------------------------------ properties
    @property
    def booking_id(self) -> str:
        return self.__booking_id

    @property
    def guest_id(self) -> str:
        return self.__guest_id

    @property
    def room_id(self) -> str:
        return self.__room_id

    @property
    def check_in(self) -> date:
        return self.__check_in

    @property
    def check_out(self) -> date:
        return self.__check_out

    @property
    def status(self) -> BookingStatus:
        return self.__status

    @property
    def created_on(self) -> date:
        return self.__created_on

    @property
    def room_number(self) -> str:
        """Số phòng tại thời điểm đặt (giữ lại để xem lịch sử nếu phòng bị xóa)."""
        return self.__room_number

    @property
    def room_type(self) -> str:
        """Tên loại phòng tại thời điểm đặt."""
        return self.__room_type

    @property
    def room_cost(self) -> float:
        """Tiền phòng (tạm tính khi đặt, chốt lại khi trả phòng)."""
        return self.__room_cost

    @property
    def discount_rate(self) -> float:
        return self.__discount_rate

    @property
    def discount_amount(self) -> float:
        """Số tiền giảm giá (chỉ áp dụng trên tiền phòng)."""
        return round(self.__room_cost * self.__discount_rate)

    @property
    def services(self) -> list[ServiceUsage]:
        """Bản sao danh sách dịch vụ đã dùng (tránh sửa trực tiếp từ bên ngoài)."""
        return list(self.__services)

    @property
    def service_total(self) -> float:
        return sum(usage.subtotal for usage in self.__services)

    @property
    def amount_due(self) -> float:
        """Tổng thanh toán = tiền phòng − giảm giá + dịch vụ."""
        return self.__room_cost - self.discount_amount + self.service_total

    @property
    def checked_in_on(self) -> date | None:
        return self.__checked_in_on

    @property
    def checked_out_on(self) -> date | None:
        return self.__checked_out_on

    @property
    def is_active(self) -> bool:
        """Còn hiệu lực (Đã đặt hoặc Đang ở)."""
        return self.__status.is_active

    # ------------------------------------------------------- tính toán ngày
    @staticmethod
    def count_nights(check_in: date, check_out: date) -> int:
        """Số đêm, tối thiểu 1 (nhận/trả cùng ngày vẫn tính 1 đêm)."""
        return max(1, (check_out - check_in).days)

    @staticmethod
    def occupied_until(check_in: date, check_out: date) -> date:
        """Ngày phòng được giải phóng; lượt ở trong ngày chiếm phòng tới hôm sau."""
        return check_in + timedelta(days=Booking.count_nights(check_in, check_out))

    @property
    def nights(self) -> int:
        return self.count_nights(self.__check_in, self.__check_out)

    @property
    def effective_end(self) -> date:
        return self.occupied_until(self.__check_in, self.__check_out)

    def overlaps(self, start: date, end: date) -> bool:
        """Khoảng [start, end) có giao với thời gian lưu trú của đặt phòng này không.

        Hai khoảng [a1, a2) và [b1, b2) giao nhau khi a1 < b2 và b1 < a2,
        nên khách mới được nhận phòng đúng ngày khách cũ trả.
        """
        other_end = self.occupied_until(start, end)
        return self.__check_in < other_end and start < self.effective_end

    def covers(self, day: date) -> bool:
        """Khách đang lưu trú (chiếm phòng) vào ngày ``day``."""
        return self.__check_in <= day < self.effective_end

    # ------------------------------------------------ thay đổi dữ liệu/trạng thái
    def _require_status(self, *allowed: BookingStatus, action: str) -> None:
        if self.__status not in allowed:
            raise BusinessRuleError(
                f"Không thể {action}: đặt phòng {self.booking_id} đang ở trạng thái "
                f"'{self.__status.label}'.")

    def set_pricing(self, room_cost: float, discount_rate: float) -> None:
        """Cập nhật tiền phòng và tỷ lệ giảm giá."""
        if room_cost < 0:
            raise ValidationError("Tiền phòng không được âm.")
        if not 0 <= discount_rate < 1:
            raise ValidationError("Tỷ lệ giảm giá phải trong khoảng [0, 1).")
        self.__room_cost = float(room_cost)
        self.__discount_rate = float(discount_rate)

    def update_stay(self, check_in: date, check_out: date) -> None:
        """Đổi ngày nhận/trả (chỉ khi Đã đặt)."""
        self._require_status(BookingStatus.BOOKED, action="sửa ngày lưu trú")
        validate_date_range(check_in, check_out)
        self.__check_in, self.__check_out = check_in, check_out

    def assign_room(self, room_id: str, room_number: str, room_type: str) -> None:
        """Đổi phòng (chỉ khi Đã đặt)."""
        self._require_status(BookingStatus.BOOKED, action="đổi phòng")
        self.__room_id = validate_id(room_id, "Mã phòng")
        self.__room_number, self.__room_type = room_number, room_type

    def mark_checked_in(self, on_date: date) -> None:
        """Chuyển sang Đang ở."""
        self._require_status(BookingStatus.BOOKED, action="nhận phòng")
        self.__status = BookingStatus.CHECKED_IN
        self.__checked_in_on = on_date

    def mark_checked_out(self, on_date: date) -> None:
        """Chuyển sang Đã trả."""
        self._require_status(BookingStatus.CHECKED_IN, action="trả phòng")
        self.__status = BookingStatus.CHECKED_OUT
        self.__checked_out_on = on_date

    def cancel(self) -> None:
        """Hủy đặt phòng (chỉ khi Đã đặt, chưa nhận phòng)."""
        self._require_status(BookingStatus.BOOKED, action="hủy")
        self.__status = BookingStatus.CANCELLED

    def add_service(self, usage: ServiceUsage) -> None:
        """Ghi nhận dịch vụ phát sinh (chỉ khi khách Đang ở)."""
        self._require_status(BookingStatus.CHECKED_IN, action="thêm dịch vụ")
        self.__services.append(usage)

    # ------------------------------------------------------ chuyển đổi dữ liệu
    def to_dict(self) -> dict[str, Any]:
        return {
            "booking_id": self.booking_id,
            "guest_id": self.guest_id,
            "room_id": self.room_id,
            "check_in": self.check_in.isoformat(),
            "check_out": self.check_out.isoformat(),
            "status": self.status.value,
            "created_on": self.created_on.isoformat(),
            "room_number": self.room_number,
            "room_type": self.room_type,
            "room_cost": self.room_cost,
            "discount_rate": self.discount_rate,
            "services": [usage.to_dict() for usage in self.__services],
            "checked_in_on": self.checked_in_on.isoformat() if self.checked_in_on else None,
            "checked_out_on": self.checked_out_on.isoformat() if self.checked_out_on else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Booking":
        return cls(
            data["booking_id"], data["guest_id"], data["room_id"],
            data["check_in"], data["check_out"],
            status=data.get("status", BookingStatus.BOOKED.value),
            created_on=data.get("created_on"),
            room_number=data.get("room_number", ""),
            room_type=data.get("room_type", ""),
            room_cost=data.get("room_cost", 0.0),
            discount_rate=data.get("discount_rate", 0.0),
            services=[ServiceUsage.from_dict(s) for s in data.get("services", [])],
            checked_in_on=data.get("checked_in_on"),
            checked_out_on=data.get("checked_out_on"),
        )

    def to_row(self, guest_name: str = "") -> list:
        return [self.booking_id, guest_name or self.guest_id,
                f"{self.room_number} ({self.room_id})", self.room_type,
                format_date(self.check_in), format_date(self.check_out), self.nights,
                self.status.label, format_money(self.amount_due)]

    def __str__(self) -> str:
        return (f"Đặt phòng {self.booking_id}: khách {self.guest_id}, phòng {self.room_number} "
                f"({self.room_id}), {format_date(self.check_in)} → {format_date(self.check_out)} "
                f"({self.nights} đêm) - {self.status.label} - {format_money(self.amount_due)}")
