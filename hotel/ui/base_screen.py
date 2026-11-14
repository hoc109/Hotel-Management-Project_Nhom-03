"""Lớp cơ sở cho các màn hình (nhóm chức năng) của giao diện Console."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from hotel.ui.menu import Menu, MenuItem, MenuSignal
from hotel.utils.exceptions import ValidationError
from hotel.utils.input_helper import ask

if TYPE_CHECKING:
    from hotel.managers.base_manager import BaseManager
    from hotel.managers.hotel_manager import HotelManager


class BaseScreen(ABC):
    """Mỗi màn hình con kế thừa lớp này và khai báo danh sách chức năng."""

    TITLE = ""

    def __init__(self, hotel: "HotelManager") -> None:
        self._hotel = hotel

    @abstractmethod
    def menu_items(self) -> list[MenuItem]:
        """Danh sách chức năng của màn hình."""

    def header(self) -> str:
        user = self._hotel.current_user
        return f"Người dùng: {user}" if user else ""

    def run(self) -> MenuSignal | None:
        """Mở menu con; khi quay lại thì trả ``None`` để menu cha tiếp tục."""
        signal = Menu(self.TITLE, self.menu_items(), self._hotel.can, header=self.header).run()
        return signal if signal != MenuSignal.BACK else None

    # ------------------------------------------------------ tiện ích nhập
    @staticmethod
    def ask_existing(manager: "BaseManager", prompt: str,
                     condition: Callable[[Any], str | None] | None = None) -> Any:
        """Nhập mã và trả về đối tượng đang tồn tại (nhập lại nếu không thấy).

        ``condition(obj)`` trả về chuỗi lỗi nếu đối tượng không phù hợp.
        """
        def validator(raw: str) -> Any:
            obj = manager.find(raw)
            if obj is None:
                raise ValidationError(f"Không tìm thấy {manager.entity_name} có mã '{raw}'.")
            if condition:
                error = condition(obj)
                if error:
                    raise ValidationError(error)
            return obj
        return ask(prompt, validator=validator)

    @staticmethod
    def ask_new_id(manager: "BaseManager", prompt: str, prefix: str,
                   id_validator: Callable[[str], str]) -> str:
        """Nhập mã mới (gợi ý mã kế tiếp), báo lỗi ngay nếu trùng."""
        suggestion = manager.next_id(prefix)

        def validator(raw: str) -> str:
            new_id = id_validator(raw)
            if manager.exists(new_id):
                raise ValidationError(f"Mã {manager.entity_name} '{new_id}' đã tồn tại.")
            return new_id
        return ask(prompt, validator=validator, default=suggestion)
