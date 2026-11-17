"""Menu dùng chung cho toàn bộ chương trình (Console Menu Framework).

* Hiển thị danh sách chức năng theo phân cấp (Menu chính, Menu con).
* Kiểm soát quyền truy cập theo vai trò (RBAC): mục không đủ quyền sẽ bị khóa/làm mờ.
* Kiểm tra tính hợp lệ khi nhập (nhập sai báo lỗi và yêu cầu nhập lại).
* Bắt ngoại lệ tập trung (HotelError, InputCancelled) để chương trình không bị gián đoạn hoặc crash.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from hotel.models.enums import Permission
from hotel.utils.exceptions import HotelError, InputCancelled
from hotel.utils.formatter import (color_dim, color_title, print_error, print_warning)
from hotel.utils.input_helper import pause


# ==============================================================================
# 1. ĐIỀU KHIỂN LUỒNG CHƯƠNG TRÌNH (MENU SIGNALS)
# ==============================================================================
class MenuSignal(Enum):
    """Tín hiệu một chức năng trả về để điều khiển vòng lặp menu.
    
    - BACK: Quay lại menu cha trước đó.
    - LOGOUT: Đăng xuất tài khoản hiện tại về màn hình đăng nhập.
    - EXIT: Thoát toàn bộ ứng dụng an toàn.
    """

    BACK = "back"
    LOGOUT = "logout"
    EXIT = "exit"


# ==============================================================================
# 2. CẤU TRÚC MỘT DÒNG CHỨC NĂNG (MENU ITEM)
# ==============================================================================
@dataclass
class MenuItem:
    """Đại diện cho một mục/lựa chọn trong menu.
    
    Thuộc tính:
        key: Ký tự hoặc số phím tắt để chọn (ví dụ: '1', '2', 'A').
        label: Tên chức năng hiển thị trên màn hình.
        action: Hàm callback được thực thi khi chọn mục này.
        permission: Quyền hạn cần có (None nghĩa là ai cũng dùng được).
        pause_after: Có dừng màn hình chờ bấm phím sau khi thực hiện xong hay không
                     (với menu con mở ra màn hình mới thì đặt là False).
    """

    key: str
    label: str
    action: Callable[[], MenuSignal | None]
    permission: Permission | None = None
    pause_after: bool = True  # menu con thì không cần dừng màn hình


# ==============================================================================
# 3. LỚP ĐIỀU HÀNH VÀ HIỂN THỊ MENU (MENU ENGINE)
# ==============================================================================
class Menu:
    """Menu Console có kiểm tra quyền (RBAC) và xử lý lỗi tập trung."""

    def __init__(self, title: str, items: list[MenuItem],
                 can: Callable[[Permission], bool],
                 header: Callable[[], str] | None = None,
                 zero_label: str = "Quay lại",
                 on_zero: Callable[[], MenuSignal | None] | None = None) -> None:
        """Khởi tạo menu.
        
        Args:
            title: Tiêu đề menu hiển thị ở đầu bảng.
            items: Danh sách các MenuItem chức năng.
            can: Hàm kiểm tra quyền của người dùng hiện tại (trả về True/False).
            header: Hàm động tạo nội dung thông tin phụ (ví dụ: tên user, thời gian).
            zero_label: Nhãn hiển thị cho phím '0' (mặc định là 'Quay lại' hoặc 'Đăng xuất / Thoát').
            on_zero: Hàm hành động tùy chỉnh khi bấm phím 0.
        """
        self.__title = title
        self.__items = {item.key: item for item in items}
        self.__can = can
        self.__header = header
        self.__zero_label = zero_label
        self.__on_zero = on_zero

    def _allowed(self, item: MenuItem) -> bool:
        """Kiểm tra xem người dùng hiện tại có đủ quyền thực hiện mục này không."""
        return item.permission is None or self.__can(item.permission)

    def display(self) -> None:
        """Vẽ giao diện khung menu ra màn hình Console.
        
        - Tạo khung viền trang trí.
        - Căn giữa tiêu đề và hiển thị header phụ nếu có.
        - Hiển thị danh sách các chức năng: các mục không đủ quyền sẽ bị làm mờ (dim)
          kèm thông báo [Khóa - chỉ Admin] để bảo đảm tính phân quyền trực quan.
        """
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
        """Vòng lặp tương tác chính của menu.
        
        Quy trình xử lý:
        1. Hiển thị menu danh sách chức năng.
        2. Nhận lựa chọn từ bàn phím.
        3. Kiểm tra phím 0 (quay lại / thoát).
        4. Kiểm tra mã phím hợp lệ (nếu sai -> báo lỗi và cho nhập lại).
        5. Kiểm tra phân quyền truy cập (nếu bị khóa -> từ chối thực hiện).
        6. Chạy chức năng và điều hướng theo tín hiệu nhận được (MenuSignal).
        """
        while True:
            self.display()
            choice = input("Chọn chức năng: ").strip()
            
            # Xử lý khi chọn phím 0 (Quay lại / Thoát)
            if choice == "0":
                signal = self.__on_zero() if self.__on_zero else MenuSignal.BACK
                if signal is not None:
                    return signal
                continue
                
            item = self.__items.get(choice)
            
            # Kiểm tra lựa chọn không tồn tại trong danh sách
            if item is None:
                valid = ", ".join(["0", *self.__items])
                print_error(f"Lựa chọn '{choice}' không hợp lệ. Vui lòng chọn một trong: {valid}.")
                continue
                
            # Kiểm tra quyền hạn của người dùng (RBAC)
            if not self._allowed(item):
                print_error(f"Bạn không có quyền sử dụng chức năng '{item.label}'.")
                pause()
                continue
                
            # Thực thi chức năng đã chọn
            signal = self._execute(item)
            
            # Nếu nhận được tín hiệu đăng xuất hoặc thoát ứng dụng thì truyền tín hiệu lên menu cha
            if signal in (MenuSignal.LOGOUT, MenuSignal.EXIT):
                return signal

    @staticmethod
    def _execute(item: MenuItem) -> MenuSignal | None:
        """Thực thi action của mục đã chọn với cơ chế bắt lỗi tập trung.
        
        - InputCancelled: Bắt sự kiện người dùng bấm 'q' để hủy thao tác nhập.
        - HotelError: Bắt tất cả các lỗi nghiệp vụ (trùng mã, ngày không hợp lệ,...)
          và in thông báo rõ ràng bằng màu đỏ thay vì làm dừng chương trình.
        """
        signal = None
        try:
            signal = item.action()
        except InputCancelled:
            print_warning("Đã hủy thao tác.")
        except HotelError as exc:
            print_error(str(exc))
            
        # Dừng màn hình để người dùng đọc kết quả trước khi xóa màn hình hoặc vẽ lại menu
        if item.pause_after and signal is None:
            pause()
        return signal
