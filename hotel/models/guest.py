"""Lớp thực thể khách hàng."""

from typing import Any

from hotel.utils.validators import (validate_id, validate_id_card, validate_name,
                                    validate_phone)


class Guest:
    """Khách hàng lưu trú.

    Thuộc tính (private, truy cập qua property có kiểm tra):
        guest_id (chỉ đọc), full_name, phone, id_card (CCCD/hộ chiếu – bổ sung so với đề).
    """

    def __init__(self, guest_id: str, full_name: str, phone: str, id_card: str = "") -> None:
        self.__guest_id = validate_id(guest_id, "Mã khách hàng")
        self.__full_name = ""
        self.__phone = ""
        self.__id_card = ""
        self.full_name = full_name
        self.phone = phone
        self.id_card = id_card

    @property
    def guest_id(self) -> str:
        """Mã khách hàng (chỉ đọc)."""
        return self.__guest_id

    @property
    def full_name(self) -> str:
        return self.__full_name

    @full_name.setter
    def full_name(self, value: str) -> None:
        self.__full_name = validate_name(value)

    @property
    def phone(self) -> str:
        return self.__phone

    @phone.setter
    def phone(self, value: str) -> None:
        self.__phone = validate_phone(value)

    @property
    def id_card(self) -> str:
        return self.__id_card

    @id_card.setter
    def id_card(self, value: str) -> None:
        self.__id_card = validate_id_card(value)

    @property
    def given_name(self) -> str:
        """Tên (chữ cuối cùng của họ tên) – dùng để sắp xếp kiểu Việt Nam."""
        return self.__full_name.split()[-1]

    def to_dict(self) -> dict[str, Any]:
        return {"guest_id": self.guest_id, "full_name": self.full_name,
                "phone": self.phone, "id_card": self.id_card}

    @classmethod
    def from_dict(cls, data: dict) -> "Guest":
        return cls(data["guest_id"], data["full_name"], data["phone"], data.get("id_card", ""))

    def to_row(self) -> list:
        return [self.guest_id, self.full_name, self.phone, self.id_card or "-"]

    def __str__(self) -> str:
        return f"Khách {self.full_name} ({self.guest_id}) - SĐT: {self.phone}"

    def __repr__(self) -> str:
        return f"Guest(guest_id={self.guest_id!r}, full_name={self.full_name!r})"
