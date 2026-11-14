"""Dịch vụ phát sinh (chức năng mở rộng): danh mục dịch vụ và lượt sử dụng."""

from datetime import date
from typing import Any

from hotel.utils.formatter import format_date, format_money
from hotel.utils.validators import (parse_date, validate_id, validate_int,
                                    validate_positive_money, validate_required)


class Service:
    """Một dịch vụ trong danh mục (minibar, giặt ủi, ăn sáng...)."""

    def __init__(self, service_id: str, name: str, price: float, unit: str = "lần") -> None:
        self.__service_id = validate_id(service_id, "Mã dịch vụ")
        self.__name = ""
        self.__price = 0.0
        self.__unit = ""
        self.name = name
        self.price = price
        self.unit = unit

    @property
    def service_id(self) -> str:
        return self.__service_id

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, value: str) -> None:
        self.__name = validate_required(value, "Tên dịch vụ", max_length=50)

    @property
    def price(self) -> float:
        return self.__price

    @price.setter
    def price(self, value: float) -> None:
        self.__price = validate_positive_money(value, "Đơn giá dịch vụ")

    @property
    def unit(self) -> str:
        return self.__unit

    @unit.setter
    def unit(self, value: str) -> None:
        self.__unit = validate_required(value, "Đơn vị tính", max_length=20)

    def to_dict(self) -> dict[str, Any]:
        return {"service_id": self.service_id, "name": self.name,
                "price": self.price, "unit": self.unit}

    @classmethod
    def from_dict(cls, data: dict) -> "Service":
        return cls(data["service_id"], data["name"], data["price"], data.get("unit", "lần"))

    def to_row(self) -> list:
        return [self.service_id, self.name, format_money(self.price), self.unit]

    def __str__(self) -> str:
        return f"Dịch vụ {self.name} ({self.service_id}) - {format_money(self.price)}/{self.unit}"


class ServiceUsage:
    """Một lần sử dụng dịch vụ gắn với đặt phòng.

    Lưu lại tên và đơn giá tại thời điểm dùng, để hóa đơn không bị thay đổi
    khi danh mục dịch vụ được sửa hoặc xóa sau này.
    """

    def __init__(self, service_id: str, service_name: str, unit_price: float,
                 quantity: int, used_on: date | str) -> None:
        self.__service_id = validate_id(service_id, "Mã dịch vụ")
        self.__service_name = validate_required(service_name, "Tên dịch vụ")
        self.__unit_price = validate_positive_money(unit_price, "Đơn giá")
        self.__quantity = validate_int(quantity, "Số lượng", min_value=1, max_value=1000)
        self.__used_on = parse_date(used_on, "Ngày sử dụng")

    @property
    def service_id(self) -> str:
        return self.__service_id

    @property
    def service_name(self) -> str:
        return self.__service_name

    @property
    def unit_price(self) -> float:
        return self.__unit_price

    @property
    def quantity(self) -> int:
        return self.__quantity

    @property
    def used_on(self) -> date:
        return self.__used_on

    @property
    def subtotal(self) -> float:
        """Thành tiền = đơn giá × số lượng."""
        return self.__unit_price * self.__quantity

    def to_dict(self) -> dict[str, Any]:
        return {"service_id": self.service_id, "service_name": self.service_name,
                "unit_price": self.unit_price, "quantity": self.quantity,
                "used_on": self.used_on.isoformat()}

    @classmethod
    def from_dict(cls, data: dict) -> "ServiceUsage":
        return cls(data["service_id"], data["service_name"], data["unit_price"],
                   data["quantity"], data["used_on"])

    def to_row(self) -> list:
        return [format_date(self.used_on), self.service_name, self.quantity,
                format_money(self.unit_price), format_money(self.subtotal)]

    def __str__(self) -> str:
        return f"{self.service_name} × {self.quantity} = {format_money(self.subtotal)}"
