"""Quản lý tài khoản, đăng nhập và kiểm tra quyền."""

from hotel.managers.base_manager import BaseManager
from hotel.models.enums import Permission, Role
from hotel.models.user import User, UserFactory
from hotel.utils.exceptions import (AuthenticationError, BusinessRuleError,
                                    PermissionDeniedError)


class AuthManager(BaseManager[User]):
    """Quản lý ``User`` (mã định danh là tên đăng nhập) và phiên đăng nhập."""

    def __init__(self) -> None:
        super().__init__()
        self.__current_user: User | None = None

    @property
    def entity_name(self) -> str:
        return "tài khoản"

    def get_id(self, item: User) -> str:
        return item.username.upper()

    def create_from_dict(self, data: dict) -> User:
        return UserFactory.from_dict(data)

    # ------------------------------------------------------------- phiên
    @property
    def current_user(self) -> User | None:
        return self.__current_user

    def login(self, username: str, password: str) -> User:
        """Đăng nhập; sai tài khoản hoặc mật khẩu ném ``AuthenticationError``."""
        user = self.find(username or "")
        if user is None or not user.check_password(password or ""):
            raise AuthenticationError("Sai tên đăng nhập hoặc mật khẩu.")
        self.__current_user = user
        return user

    def logout(self) -> None:
        self.__current_user = None

    def require(self, permission: Permission) -> None:
        """Ném ``PermissionDeniedError`` nếu người dùng hiện tại không có quyền."""
        user = self.__current_user
        if user is None:
            raise PermissionDeniedError("Bạn cần đăng nhập để thực hiện thao tác này.")
        if not user.has_permission(permission):
            raise PermissionDeniedError(
                f"Tài khoản {user.role.label} không có quyền '{permission.value}'.")

    # ------------------------------------------------------- quản lý tài khoản
    def add_user(self, role: Role | str, username: str, password: str, full_name: str) -> User:
        return self.add(UserFactory.create(role, username, password, full_name))

    def delete_user(self, username: str) -> User:
        """Xóa tài khoản: không xóa chính mình và không xóa admin cuối cùng."""
        user = self.get(username)
        if self.__current_user and user.username == self.__current_user.username:
            raise BusinessRuleError("Không thể xóa tài khoản đang đăng nhập.")
        admins = [u for u in self._items.values() if u.role == Role.ADMIN]
        if user.role == Role.ADMIN and len(admins) <= 1:
            raise BusinessRuleError("Phải còn ít nhất một tài khoản quản trị viên.")
        return self.remove(username)

    def change_password(self, old_password: str, new_password: str) -> None:
        """Đổi mật khẩu cho người dùng đang đăng nhập."""
        user = self.__current_user
        if user is None:
            raise PermissionDeniedError("Bạn cần đăng nhập.")
        if not user.check_password(old_password):
            raise AuthenticationError("Mật khẩu hiện tại không đúng.")
        if old_password == new_password:
            raise BusinessRuleError("Mật khẩu mới phải khác mật khẩu cũ.")
        user.set_password(new_password)
