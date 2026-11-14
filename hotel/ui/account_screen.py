"""Màn hình tài khoản: đổi mật khẩu, quản lý người dùng (Admin)."""

import getpass
import sys

from hotel.models.enums import Permission, Role
from hotel.ui.base_screen import BaseScreen
from hotel.ui.menu import MenuItem
from hotel.ui.views import show_users
from hotel.utils.exceptions import InputCancelled, ValidationError
from hotel.utils.formatter import print_error, print_info, print_success, print_warning
from hotel.utils.input_helper import CANCEL_KEYWORD, ask, ask_choice, confirm
from hotel.utils.validators import validate_name, validate_password, validate_username


def ask_password(prompt: str) -> str:
    """Nhập mật khẩu ẩn ký tự khi chạy trong terminal thật."""
    if sys.stdin.isatty():
        value = getpass.getpass(f"{prompt}: ")
    else:  # chạy tự động / chuyển hướng đầu vào
        value = input(f"{prompt}: ")
    if value.strip().lower() == CANCEL_KEYWORD:
        raise InputCancelled()
    return value


class AccountScreen(BaseScreen):
    """Quản lý tài khoản người dùng."""

    TITLE = "Tài khoản"

    def menu_items(self) -> list[MenuItem]:
        manage = Permission.MANAGE_USERS
        return [
            MenuItem("1", "Thông tin tài khoản đang đăng nhập", self.show_me),
            MenuItem("2", "Đổi mật khẩu", self.change_password),
            MenuItem("3", "Danh sách tài khoản", self.list_users, manage),
            MenuItem("4", "Thêm tài khoản", self.add_user, manage),
            MenuItem("5", "Xóa tài khoản", self.delete_user, manage),
        ]

    def show_me(self) -> None:
        user = self._hotel.current_user
        show_users([user], title="TÀI KHOẢN HIỆN TẠI")
        print("Quyền được cấp:")
        for permission in Permission:
            mark = "✔" if user.has_permission(permission) else "✘"
            print(f"  {mark} {permission.value}")

    def change_password(self) -> None:
        old = ask_password("Mật khẩu hiện tại")
        while True:
            new = ask_password("Mật khẩu mới (≥ 6 ký tự)")
            try:
                validate_password(new)
            except ValidationError as exc:
                print_error(str(exc))
                continue
            if ask_password("Nhập lại mật khẩu mới") == new:
                break
            print_error("Mật khẩu nhập lại không khớp.")
        self._hotel.change_password(old, new)
        print_success("Đổi mật khẩu thành công.")

    def list_users(self) -> None:
        show_users(self._hotel.auth.sort_by(lambda u: (u.role.value, u.username)))

    def add_user(self) -> None:
        print_info("Thêm tài khoản mới (gõ 'q' để hủy).")

        def unique(raw: str) -> str:
            username = validate_username(raw)
            if self._hotel.auth.exists(username):
                raise ValidationError(f"Tên đăng nhập '{username}' đã tồn tại.")
            return username
        username = ask("Tên đăng nhập", validator=unique)
        full_name = ask("Họ tên", validator=validate_name)
        role = Role.ADMIN if ask_choice("Vai trò", {"1": Role.ADMIN.label,
                                                    "2": Role.RECEPTIONIST.label}) == "1" \
            else Role.RECEPTIONIST
        while True:
            password = ask_password("Mật khẩu (≥ 6 ký tự)")
            try:
                validate_password(password)
                break
            except ValidationError as exc:
                print_error(str(exc))
        user = self._hotel.add_user(role, username, password, full_name)
        print_success(f"Đã tạo tài khoản {user}.")

    def delete_user(self) -> None:
        user = self.ask_existing(self._hotel.auth, "Tên đăng nhập cần xóa")
        show_users([user], title="Tài khoản sẽ bị xóa")
        if not confirm(f"Bạn chắc chắn muốn xóa tài khoản {user.username}?"):
            print_warning("Đã hủy xóa.")
            return
        self._hotel.delete_user(user.username)
        print_success(f"Đã xóa tài khoản {user.username}.")
