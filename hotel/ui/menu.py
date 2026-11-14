"""Menu dùng chung cho toàn bộ chương trình.

* Hiển thị danh sách chức năng, mục không đủ quyền được đánh dấu 🔒.
* Nhập sai lựa chọn -> báo lỗi và cho nhập lại.
* Bắt mọi lỗi nghiệp vụ (``HotelError``) để chương trình không bị dừng.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from hotel.models.enums import Permission
from hotel.utils.exceptions import HotelError, InputCancelled
from hotel.utils.formatter import (color_dim, color_title, print_error, print_warning)
from hotel.utils.input_helper import pause


class MenuSignal(Enum):
    """Tín hiệu một chức năng trả về để điều khiển vòng lặp menu."""

    BACK = "back"
    LOGOUT = "logout"
    EXIT = "exit"


@dataclass
class MenuItem:
    """Một dòng trong menu."""

    key: str
    label: str
    action: Callable[[], MenuSignal | None]
    permission: Permission | None = None
    pause_after: bool = True  # menu con thì không cần dừng màn hình


class Menu:
    """Menu Console có kiểm tra quyền và xử lý lỗi tập trung."""

    def __init__(self, title: str, items: list[MenuItem],
                 can: Callable[[Permission], bool],
                 header: Callable[[], str] | None = None,
                 zero_label: str = "Quay lại",
                 on_zero: Callable[[], MenuSignal | None] | None = None) -> None:
        self.__title = title
        self.__items = {item.key: item for item in items}
        self.__can = can
        self.__header = header
        self.__zero_label = zero_label
        self.__on_zero = on_zero

    def _allowed(self, item: MenuItem) -> bool:
        return item.permission is None or self.__can(item.permission)

    def display(self) -> None:
        width = 60
        print("\n" + "═" * width)
        print(color_title(self.__title.upper().center(width)))
        if self.__header:
            print(self.__header().center(width))
        print("═" * width)
        for item in self.__items.values():
            text = f"  {item.key:>2}. {item.label}"
            print(text if self._allowed(item) else color_dim(f"{text}  [Khóa - chỉ Admin]"))
        print(f"   0. {self.__zero_label}")
        print("─" * width)

    def run(self) -> MenuSignal:
        """Vòng lặp menu. Trả về tín hiệu khi người dùng thoát khỏi menu."""
        while True:
            self.display()
            choice = input("Chọn chức năng: ").strip()
            if choice == "0":
                signal = self.__on_zero() if self.__on_zero else MenuSignal.BACK
                if signal is not None:
                    return signal
                continue
            item = self.__items.get(choice)
            if item is None:
                valid = ", ".join(["0", *self.__items])
                print_error(f"Lựa chọn '{choice}' không hợp lệ. Vui lòng chọn một trong: {valid}.")
                continue
            if not self._allowed(item):
                print_error(f"Bạn không có quyền sử dụng chức năng '{item.label}'.")
                pause()
                continue
            signal = self._execute(item)
            if signal in (MenuSignal.LOGOUT, MenuSignal.EXIT):
                return signal

    @staticmethod
    def _execute(item: MenuItem) -> MenuSignal | None:
        """Chạy một chức năng, bắt lỗi nghiệp vụ và lệnh hủy."""
        signal = None
        try:
            signal = item.action()
        except InputCancelled:
            print_warning("Đã hủy thao tác.")
        except HotelError as exc:
            print_error(str(exc))
        if item.pause_after and signal is None:
            pause()
        return signal
