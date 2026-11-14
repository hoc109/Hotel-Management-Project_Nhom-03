"""Ứng dụng Console: đăng nhập -> menu chính -> thoát an toàn."""

import colorama

from hotel.managers.hotel_manager import HotelManager
from hotel.ui.account_screen import AccountScreen, ask_password
from hotel.ui.booking_screen import BookingScreen
from hotel.ui.guest_screen import GuestScreen
from hotel.ui.menu import Menu, MenuItem, MenuSignal
from hotel.ui.report_screen import ReportScreen
from hotel.ui.room_screen import RoomScreen
from hotel.ui.service_screen import ServiceScreen
from hotel.utils.exceptions import AuthenticationError, HotelError, InputCancelled
from hotel.utils.formatter import (color_title, format_date, print_error, print_info,
                                   print_success, print_warning)
from hotel.utils.input_helper import confirm

MAX_LOGIN_ATTEMPTS = 3

BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║          HỆ THỐNG QUẢN LÝ KHÁCH SẠN - PYTHON HOTEL       ║
║                 Hotel Management System                  ║
╚══════════════════════════════════════════════════════════╝"""


class HotelApp:
    """Điều khiển luồng chính của chương trình."""

    def __init__(self, hotel: HotelManager) -> None:
        self.__hotel = hotel

    def run(self) -> None:
        colorama.just_fix_windows_console()
        print(color_title(BANNER))
        try:
            for warning in self.__hotel.load():
                print_warning(warning)
            print_info(f"Hôm nay: {format_date(self.__hotel.today())}. "
                       f"Gõ 'q' ở ô nhập liệu bất kỳ để hủy thao tác.")
            while True:
                if not self._login():
                    break
                signal = self._main_menu().run()
                if signal == MenuSignal.EXIT:
                    break
                self.__hotel.logout()
                print_info("Đã đăng xuất.")
        except (KeyboardInterrupt, EOFError):
            print()
            print_warning("Nhận tín hiệu dừng chương trình (Ctrl+C / hết dữ liệu nhập).")
        finally:
            self._shutdown()

    def _login(self) -> bool:
        """Đăng nhập, tối đa 3 lần. Trả về False nếu người dùng thoát hoặc sai quá số lần."""
        print("\n" + color_title("ĐĂNG NHẬP") + "  (gõ 'q' ở tên đăng nhập để thoát)")
        for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
            username = input("Tên đăng nhập: ").strip()
            if username.lower() == "q":
                return False
            try:
                password = ask_password("Mật khẩu")
                user = self.__hotel.login(username, password)
            except InputCancelled:
                return False
            except AuthenticationError as exc:
                left = MAX_LOGIN_ATTEMPTS - attempt
                print_error(f"{exc} Còn {left} lần thử." if left else str(exc))
                continue
            print_success(f"Xin chào {user.full_name} – vai trò: {user.role.label}.")
            return True
        print_error("Đăng nhập sai quá 3 lần. Chương trình sẽ thoát.")
        return False

    def _confirm_exit(self) -> MenuSignal | None:
        return MenuSignal.EXIT if confirm("Bạn có chắc muốn thoát chương trình?") else None

    def _main_menu(self) -> Menu:
        hotel = self.__hotel
        items = [
            MenuItem("1", "Quản lý phòng", RoomScreen(hotel).run, pause_after=False),
            MenuItem("2", "Quản lý khách hàng", GuestScreen(hotel).run, pause_after=False),
            MenuItem("3", "Đặt phòng & lưu trú", BookingScreen(hotel).run, pause_after=False),
            MenuItem("4", "Danh mục dịch vụ", ServiceScreen(hotel).run, pause_after=False),
            MenuItem("5", "Thống kê & báo cáo", ReportScreen(hotel).run, pause_after=False),
            MenuItem("6", "Tài khoản", AccountScreen(hotel).run, pause_after=False),
            MenuItem("7", "Đăng xuất", lambda: MenuSignal.LOGOUT, pause_after=False),
        ]
        user = hotel.current_user
        return Menu("Menu chính", items, hotel.can,
                    header=lambda: f"Người dùng: {user}",
                    zero_label="Thoát chương trình", on_zero=self._confirm_exit)

    def _shutdown(self) -> None:
        """Lưu dữ liệu trước khi thoát."""
        try:
            self.__hotel.save()
            print_success("Đã lưu dữ liệu.")
        except HotelError as exc:
            print_error(f"Lưu dữ liệu thất bại: {exc}")
        print(color_title("Cảm ơn bạn đã sử dụng chương trình. Tạm biệt!"))
