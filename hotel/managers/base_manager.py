"""Lớp quản lý cơ sở dùng chung cho mọi loại thực thể (Generic + ABC)."""

import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import Any, Generic, TypeVar

from hotel.utils.exceptions import DuplicateIdError, NotFoundError, ValidationError

T = TypeVar("T")


class BaseManager(ABC, Generic[T]):
    """Quản lý một tập đối tượng theo mã định danh.

    Cung cấp sẵn: thêm (chống trùng mã), lấy theo mã, cập nhật nguyên tử,
    xóa, liệt kê, lọc, sắp xếp, gợi ý mã tiếp theo, chuyển đổi dict.
    Lớp con chỉ cần khai báo tên thực thể, cách lấy mã và cách tạo từ dict.
    """

    def __init__(self) -> None:
        self._items: dict[str, T] = {}  # protected: lớp con được truy cập

    # ------------------------------------------- phương thức lớp con phải cài
    @property
    @abstractmethod
    def entity_name(self) -> str:
        """Tên thực thể dùng trong thông báo (vd: 'phòng')."""

    @abstractmethod
    def get_id(self, item: T) -> str:
        """Lấy mã định danh của đối tượng."""

    @abstractmethod
    def create_from_dict(self, data: dict) -> T:
        """Tạo đối tượng từ dict."""

    # ------------------------------------------------------------ hook kiểm tra
    def _validate_unique(self, item: T, exclude_id: str | None = None) -> None:
        """Kiểm tra các trường duy nhất khác ngoài mã (lớp con ghi đè nếu cần)."""

    @staticmethod
    def normalize_id(item_id: str) -> str:
        return str(item_id).strip().upper()

    # --------------------------------------------------------------- CRUD
    def add(self, item: T) -> T:
        """Thêm đối tượng; báo lỗi nếu trùng mã."""
        item_id = self.get_id(item)
        if item_id in self._items:
            raise DuplicateIdError(f"Mã {self.entity_name} '{item_id}' đã tồn tại.")
        self._validate_unique(item)
        self._items[item_id] = item
        return item

    def find(self, item_id: str) -> T | None:
        """Tìm theo mã chính xác, không thấy trả ``None``."""
        return self._items.get(self.normalize_id(item_id))

    def get(self, item_id: str) -> T:
        """Lấy theo mã chính xác, không thấy thì ném ``NotFoundError``."""
        item = self.find(item_id)
        if item is None:
            raise NotFoundError(f"Không tìm thấy {self.entity_name} có mã '{item_id}'.")
        return item

    def exists(self, item_id: str) -> bool:
        return self.normalize_id(item_id) in self._items

    def update(self, item_id: str, **changes: Any) -> T:
        """Cập nhật nguyên tử: dựng đối tượng mới từ dữ liệu cũ + thay đổi.

        Nếu bất kỳ trường nào không hợp lệ thì đối tượng cũ giữ nguyên.
        Không cho phép đổi mã định danh.
        """
        old = self.get(item_id)
        data = old.to_dict()
        unknown = set(changes) - set(data)
        if unknown:
            raise ValidationError(f"Không có trường: {', '.join(sorted(unknown))}.")
        id_fields = [key for key in data if key.endswith("_id") and data[key] == self.get_id(old)]
        if any(key in changes and self.normalize_id(changes[key]) != self.get_id(old)
               for key in id_fields):
            raise ValidationError(f"Không được thay đổi mã {self.entity_name}.")
        data.update(changes)
        new = self.create_from_dict(data)
        self._validate_unique(new, exclude_id=self.get_id(old))
        self._items[self.get_id(old)] = new
        return new

    def remove(self, item_id: str) -> T:
        """Xóa khỏi danh sách (kiểm tra ràng buộc thực hiện ở HotelManager)."""
        item = self.get(item_id)
        del self._items[self.get_id(item)]
        return item

    # --------------------------------------------------------- truy vấn
    def list_all(self) -> list[T]:
        return list(self._items.values())

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self.list_all())

    def filter(self, predicate: Callable[[T], bool],
               items: Iterable[T] | None = None) -> list[T]:
        """Lọc theo điều kiện."""
        source = self.list_all() if items is None else items
        return [item for item in source if predicate(item)]

    def sort_by(self, key: Callable[[T], Any], reverse: bool = False,
                items: Iterable[T] | None = None) -> list[T]:
        """Sắp xếp theo ``key`` (tăng dần hoặc giảm dần), không đổi dữ liệu gốc."""
        source = self.list_all() if items is None else list(items)
        return sorted(source, key=key, reverse=reverse)

    def next_id(self, prefix: str, width: int = 3) -> str:
        """Gợi ý mã tiếp theo, vd: R001, R002 -> R003."""
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
        numbers = [int(m.group(1)) for key in self._items if (m := pattern.match(key))]
        return f"{prefix}{(max(numbers) + 1) if numbers else 1:0{width}d}"

    # ------------------------------------------------------ chuyển đổi dữ liệu
    def load_dicts(self, records: Iterable[dict]) -> list[str]:
        """Nạp dữ liệu; bỏ qua bản ghi lỗi và trả về danh sách cảnh báo."""
        self._items.clear()
        warnings = []
        for index, record in enumerate(records, start=1):
            try:
                self.add(self.create_from_dict(record))
            except Exception as exc:  # noqa: BLE001 - gom mọi lỗi dữ liệu để báo cáo
                warnings.append(f"Bỏ qua {self.entity_name} thứ {index}: {exc}")
        return warnings

    def to_dicts(self) -> list[dict]:
        return [item.to_dict() for item in self._items.values()]

    def clear(self) -> None:
        self._items.clear()
