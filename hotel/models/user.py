"""Người dùng hệ thống (chức năng mở rộng: đăng nhập, phân quyền).

``User`` là lớp trừu tượng; ``Admin`` và ``Receptionist`` ghi đè
``permissions()`` để có tập quyền khác nhau (đa hình).
Mật khẩu được băm SHA-256 kèm salt ngẫu nhiên, không lưu dạng chữ thường.
"""

import hashlib
import hmac
import secrets
from abc import ABC, abstractmethod
from typing import Any

from hotel.models.enums import Permission, Role
from hotel.utils.exceptions import ValidationError
from hotel.utils.validators import validate_name, validate_password, validate_username


class User(ABC):
    """Lớp cha trừu tượng cho tài khoản người dùng."""

    ROLE: Role

    def __init__(self, username: str, full_name: str, password_hash: str, salt: str) -> None:
        self.__username = validate_username(username)
        self.__full_name = validate_name(full_name)
        self.__password_hash = password_hash
        self.__salt = salt

    # ------------------------------------------------------------ properties
    @property
    def username(self) -> str:
        return self.__username

    @property
    def full_name(self) -> str:
        return self.__full_name

    @property
    def role(self) -> Role:
        return self.ROLE

    # -------------------------------------------------------------- mật khẩu
    @staticmethod
    def _hash(password: str, salt: str) -> str:
        return hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()

    @classmethod
    def create(cls, username: str, password: str, full_name: str) -> "User":
        """Tạo tài khoản mới từ mật khẩu dạng chữ thường (sẽ được băm)."""
        validate_password(password)
        salt = secrets.token_hex(8)
        return cls(username, full_name, cls._hash(password, salt), salt)

    def check_password(self, password: str) -> bool:
        """So khớp mật khẩu (so sánh an toàn thời gian)."""
        return hmac.compare_digest(self._hash(password, self.__salt), self.__password_hash)

    def set_password(self, new_password: str) -> None:
        """Đổi mật khẩu (tạo salt mới)."""
        validate_password(new_password)
        self.__salt = secrets.token_hex(8)
        self.__password_hash = self._hash(new_password, self.__salt)

    # -------------------------------------------------------------- phân quyền
    @abstractmethod
    def permissions(self) -> frozenset[Permission]:
        """Tập quyền của loại người dùng (đa hình)."""

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions()

    # ------------------------------------------------------ chuyển đổi dữ liệu
    def to_dict(self) -> dict[str, Any]:
        return {"username": self.username, "full_name": self.full_name,
                "role": self.role.value, "password_hash": self.__password_hash,
                "salt": self.__salt}

    def to_row(self) -> list:
        return [self.username, self.full_name, self.role.label]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.username}) - {self.role.label}"


class Admin(User):
    """Quản trị viên: toàn quyền."""

    ROLE = Role.ADMIN

    def permissions(self) -> frozenset[Permission]:
        return frozenset(Permission)


class Receptionist(User):
    """Lễ tân: phục vụ khách, không được sửa danh mục phòng/dịch vụ, tài khoản, xuất CSV."""

    ROLE = Role.RECEPTIONIST

    _PERMISSIONS = frozenset({
        Permission.VIEW_ROOMS, Permission.MANAGE_GUESTS, Permission.MANAGE_BOOKINGS,
        Permission.VIEW_SERVICES, Permission.VIEW_REPORTS,
    })

    def permissions(self) -> frozenset[Permission]:
        return self._PERMISSIONS


class UserFactory:
    """Tạo đối tượng người dùng đúng lớp con theo vai trò."""

    _REGISTRY: dict[Role, type[User]] = {Role.ADMIN: Admin, Role.RECEPTIONIST: Receptionist}

    @classmethod
    def user_class(cls, role: Role | str) -> type[User]:
        return cls._REGISTRY[Role.parse(role)]

    @classmethod
    def create(cls, role: Role | str, username: str, password: str, full_name: str) -> User:
        return cls.user_class(role).create(username, password, full_name)

    @classmethod
    def from_dict(cls, data: dict) -> User:
        try:
            return cls.user_class(data["role"])(data["username"], data["full_name"],
                                                data["password_hash"], data["salt"])
        except KeyError as exc:
            raise ValidationError(f"Thiếu trường dữ liệu tài khoản: {exc}.") from None
