"""Lớp phòng: lớp trừu tượng ``Room`` và các loại phòng cụ thể.

Sơ đồ kế thừa::

    Room (ABC)
    ├── StandardRoom
    └── DeluxeRoom
        └── SuiteRoom

Đa hình: mỗi lớp con ghi đè ``calculate_cost()``, ``get_room_type()``,
``get_extra_info()``, ``cost_breakdown()`` và ``__str__()``.
"""

from abc import ABC, abstractmethod
from typing import Any

from hotel.models.enums import RoomStatus
from hotel.utils.exceptions import ValidationError
from hotel.utils.formatter import format_money
from hotel.utils.validators import (validate_id, validate_non_negative_money,
                                    validate_positive_money, validate_required,
                                    validate_room_number)


class Room(ABC):
    """Lớp cha trừu tượng cho mọi loại phòng.

    Thuộc tính:
        - ``__room_id`` (private): mã phòng, chỉ đọc sau khi tạo.
        - ``__room_number`` (private): số phòng.
        - ``_price_per_night`` (protected): giá mỗi đêm, lớp con dùng để tính tiền.
        - ``__status`` (private): trạng thái phòng.
    """

    ROOM_TYPE: str = ""  # khóa lưu trong JSON, lớp con bắt buộc khai báo

    def __init__(self, room_id: str, room_number: str, price_per_night: float,
                 status: RoomStatus | str = RoomStatus.AVAILABLE) -> None:
        self.__room_id = validate_id(room_id, "Mã phòng")
        self.__room_number = ""
        self._price_per_night = 0.0
        self.__status = RoomStatus.AVAILABLE
        # Gán qua setter để kiểm tra dữ liệu
        self.room_number = room_number
        self.price_per_night = price_per_night
        self.status = status

    # ------------------------------------------------------------ properties
    @property
    def room_id(self) -> str:
        """Mã phòng (chỉ đọc)."""
        return self.__room_id

    @property
    def room_number(self) -> str:
        return self.__room_number

    @room_number.setter
    def room_number(self, value: str) -> None:
        self.__room_number = validate_room_number(value)

    @property
    def price_per_night(self) -> float:
        return self._price_per_night

    @price_per_night.setter
    def price_per_night(self, value: float) -> None:
        self._price_per_night = validate_positive_money(value, "Giá phòng/đêm")

    @property
    def status(self) -> RoomStatus:
        return self.__status

    @status.setter
    def status(self, value: RoomStatus | str) -> None:
        self.__status = RoomStatus.parse(value)

    # ---------------------------------------------------- phương thức chung
    def is_available(self) -> bool:
        """Phòng đang trống, sẵn sàng nhận khách."""
        return self.__status == RoomStatus.AVAILABLE

    def is_bookable(self) -> bool:
        """Phòng có thể nhận đặt trước (không bảo trì)."""
        return self.__status != RoomStatus.MAINTENANCE

    @staticmethod
    def _normalize_nights(nights: int) -> int:
        """Kiểm tra số đêm; bảo đảm tối thiểu 1 đêm (nhận/trả cùng ngày)."""
        if isinstance(nights, bool) or not isinstance(nights, int):
            raise ValidationError("Số đêm phải là số nguyên.")
        if nights < 0:
            raise ValidationError("Số đêm không được âm.")
        return max(1, nights)

    def _room_charge(self, nights: int) -> float:
        """Tiền phòng cơ bản = giá/đêm × số đêm (dùng chung cho lớp con)."""
        return self._price_per_night * self._normalize_nights(nights)

    # ---------------------------------------------- phương thức trừu tượng
    @abstractmethod
    def calculate_cost(self, nights: int) -> float:
        """Tính tổng tiền phòng cho ``nights`` đêm (đa hình)."""

    @abstractmethod
    def get_room_type(self) -> str:
        """Tên loại phòng hiển thị."""

    @abstractmethod
    def get_extra_info(self) -> str:
        """Mô tả tiện ích/phụ phí riêng của loại phòng."""

    @abstractmethod
    def cost_breakdown(self, nights: int) -> list[tuple[str, float]]:
        """Danh sách các khoản tiền cấu thành ``calculate_cost`` (dùng cho hóa đơn)."""

    # ------------------------------------------------------ chuyển đổi dữ liệu
    def to_dict(self) -> dict[str, Any]:
        """Chuyển sang dict để lưu JSON. Lớp con mở rộng thêm thuộc tính riêng."""
        return {
            "type": self.ROOM_TYPE,
            "room_id": self.room_id,
            "room_number": self.room_number,
            "price_per_night": self.price_per_night,
            "status": self.status.value,
        }

    def to_row(self) -> list:
        """Một dòng dữ liệu để in bảng."""
        return [self.room_id, self.room_number, self.get_room_type(),
                format_money(self.price_per_night), self.status.label,
                self.get_extra_info()]

    def __str__(self) -> str:
        return (f"[{self.get_room_type()}] Phòng {self.room_number} ({self.room_id}) - "
                f"{format_money(self.price_per_night)}/đêm - {self.status.label}")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(room_id={self.room_id!r}, room_number={self.room_number!r})"


class StandardRoom(Room):
    """Phòng tiêu chuẩn: chỉ tính giá phòng, kèm dịch vụ cơ bản miễn phí."""

    ROOM_TYPE = "standard"
    DEFAULT_BASIC_SERVICE = "Wifi, nước suối"

    def __init__(self, room_id: str, room_number: str, price_per_night: float,
                 status: RoomStatus | str = RoomStatus.AVAILABLE,
                 basic_service: str = DEFAULT_BASIC_SERVICE) -> None:
        super().__init__(room_id, room_number, price_per_night, status)
        self.__basic_service = ""
        self.basic_service = basic_service

    @property
    def basic_service(self) -> str:
        return self.__basic_service

    @basic_service.setter
    def basic_service(self, value: str) -> None:
        self.__basic_service = validate_required(value, "Dịch vụ cơ bản")

    def calculate_cost(self, nights: int) -> float:
        """Standard: giá × số đêm."""
        return self._room_charge(nights)

    def get_room_type(self) -> str:
        return "Tiêu chuẩn"

    def get_extra_info(self) -> str:
        return f"Miễn phí: {self.basic_service}"

    def cost_breakdown(self, nights: int) -> list[tuple[str, float]]:
        n = self._normalize_nights(nights)
        return [(f"Tiền phòng {format_money(self.price_per_night)} × {n} đêm",
                 self._room_charge(n))]

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["basic_service"] = self.basic_service
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "StandardRoom":
        return cls(data["room_id"], data["room_number"], data["price_per_night"],
                   data.get("status", RoomStatus.AVAILABLE.value),
                   data.get("basic_service", cls.DEFAULT_BASIC_SERVICE))

    def __str__(self) -> str:
        return f"{super().__str__()} - Miễn phí: {self.basic_service}"


class DeluxeRoom(Room):
    """Phòng cao cấp: giá phòng + phụ phí dịch vụ cao cấp mỗi đêm."""

    ROOM_TYPE = "deluxe"

    def __init__(self, room_id: str, room_number: str, price_per_night: float,
                 status: RoomStatus | str = RoomStatus.AVAILABLE,
                 extra_service_fee: float = 0) -> None:
        super().__init__(room_id, room_number, price_per_night, status)
        self._extra_service_fee = 0.0
        self.extra_service_fee = extra_service_fee

    @property
    def extra_service_fee(self) -> float:
        return self._extra_service_fee

    @extra_service_fee.setter
    def extra_service_fee(self, value: float) -> None:
        self._extra_service_fee = validate_non_negative_money(value, "Phụ phí dịch vụ/đêm")

    def calculate_cost(self, nights: int) -> float:
        """Deluxe: (giá + phụ phí dịch vụ) × số đêm."""
        n = self._normalize_nights(nights)
        return self._room_charge(n) + self._extra_service_fee * n

    def get_room_type(self) -> str:
        return "Cao cấp"

    def get_extra_info(self) -> str:
        return f"Phụ phí DV: {format_money(self.extra_service_fee)}/đêm"

    def cost_breakdown(self, nights: int) -> list[tuple[str, float]]:
        n = self._normalize_nights(nights)
        return [
            (f"Tiền phòng {format_money(self.price_per_night)} × {n} đêm", self._room_charge(n)),
            (f"Phụ phí DV cao cấp {format_money(self.extra_service_fee)} × {n} đêm",
             self._extra_service_fee * n),
        ]

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["extra_service_fee"] = self.extra_service_fee
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "DeluxeRoom":
        return cls(data["room_id"], data["room_number"], data["price_per_night"],
                   data.get("status", RoomStatus.AVAILABLE.value),
                   data.get("extra_service_fee", 0))

    def __str__(self) -> str:
        return f"{super().__str__()} - {self.get_extra_info()}"


class SuiteRoom(DeluxeRoom):
    """Phòng Suite (mở rộng): như Deluxe + phí quản gia tính một lần mỗi lượt ở.

    Minh họa kế thừa nhiều cấp: ``Room`` -> ``DeluxeRoom`` -> ``SuiteRoom``.
    """

    ROOM_TYPE = "suite"

    def __init__(self, room_id: str, room_number: str, price_per_night: float,
                 status: RoomStatus | str = RoomStatus.AVAILABLE,
                 extra_service_fee: float = 0, butler_fee: float = 0) -> None:
        super().__init__(room_id, room_number, price_per_night, status, extra_service_fee)
        self.__butler_fee = 0.0
        self.butler_fee = butler_fee

    @property
    def butler_fee(self) -> float:
        return self.__butler_fee

    @butler_fee.setter
    def butler_fee(self, value: float) -> None:
        self.__butler_fee = validate_non_negative_money(value, "Phí quản gia")

    def calculate_cost(self, nights: int) -> float:
        """Suite: chi phí như Deluxe + phí quản gia (một lần)."""
        return super().calculate_cost(nights) + self.__butler_fee

    def get_room_type(self) -> str:
        return "Suite"

    def get_extra_info(self) -> str:
        return f"{super().get_extra_info()}; Quản gia: {format_money(self.butler_fee)}/lượt"

    def cost_breakdown(self, nights: int) -> list[tuple[str, float]]:
        return super().cost_breakdown(nights) + [("Phí quản gia (1 lần)", self.__butler_fee)]

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["butler_fee"] = self.butler_fee
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "SuiteRoom":
        return cls(data["room_id"], data["room_number"], data["price_per_night"],
                   data.get("status", RoomStatus.AVAILABLE.value),
                   data.get("extra_service_fee", 0), data.get("butler_fee", 0))


class RoomFactory:
    """Factory tạo đối tượng phòng đúng lớp con dựa vào khóa loại phòng."""

    _REGISTRY: dict[str, type[Room]] = {
        StandardRoom.ROOM_TYPE: StandardRoom,
        DeluxeRoom.ROOM_TYPE: DeluxeRoom,
        SuiteRoom.ROOM_TYPE: SuiteRoom,
    }

    @classmethod
    def room_types(cls) -> dict[str, type[Room]]:
        """Danh sách khóa loại phòng -> lớp."""
        return dict(cls._REGISTRY)

    @classmethod
    def type_label(cls, room_type: str) -> str:
        """Tên hiển thị của một khóa loại phòng."""
        labels = {"standard": "Tiêu chuẩn", "deluxe": "Cao cấp", "suite": "Suite"}
        return labels.get(room_type, room_type)

    @classmethod
    def from_dict(cls, data: dict) -> Room:
        """Tạo phòng từ dict (đọc JSON)."""
        room_type = str(data.get("type", "")).lower()
        room_cls = cls._REGISTRY.get(room_type)
        if room_cls is None:
            raise ValidationError(f"Loại phòng '{room_type}' không hợp lệ.")
        try:
            return room_cls.from_dict(data)
        except KeyError as exc:
            raise ValidationError(f"Thiếu trường dữ liệu phòng: {exc}.") from None
