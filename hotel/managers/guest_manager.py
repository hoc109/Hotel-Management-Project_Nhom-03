"""Quản lý khách hàng: thêm, sửa, tìm kiếm gần đúng, sắp xếp."""

from hotel.managers.base_manager import BaseManager
from hotel.models.guest import Guest
from hotel.utils.exceptions import DuplicateIdError
from hotel.utils.text_utils import fuzzy_contains, normalize_search


class GuestManager(BaseManager[Guest]):
    """Quản lý các đối tượng ``Guest``."""

    ID_PREFIX = "G"

    @property
    def entity_name(self) -> str:
        return "khách hàng"

    def get_id(self, item: Guest) -> str:
        return item.guest_id

    def create_from_dict(self, data: dict) -> Guest:
        return Guest.from_dict(data)

    def _validate_unique(self, item: Guest, exclude_id: str | None = None) -> None:
        """CCCD/hộ chiếu (nếu có) không được trùng giữa hai khách."""
        if not item.id_card:
            return
        for guest in self._items.values():
            if guest.guest_id != exclude_id and guest.id_card == item.id_card:
                raise DuplicateIdError(
                    f"CCCD/Hộ chiếu '{item.id_card}' đã thuộc về khách {guest.guest_id}.")

    def search_by_name(self, keyword: str) -> list[Guest]:
        """Tìm gần đúng theo họ tên, không phân biệt hoa/thường và dấu."""
        return self.filter(lambda g: fuzzy_contains(g.full_name, keyword))

    def search_by_phone(self, keyword: str) -> list[Guest]:
        """Tìm gần đúng theo số điện thoại (chứa chuỗi)."""
        keyword = keyword.strip()
        return self.filter(lambda g: keyword in g.phone)

    SORT_KEYS = {
        "name": ("Họ tên", lambda g: normalize_search(g.full_name)),
        "given_name": ("Tên (chữ cuối)", lambda g: (normalize_search(g.given_name),
                                                     normalize_search(g.full_name))),
        "id": ("Mã khách", lambda g: g.guest_id),
    }

    def sort_guests(self, criterion: str, reverse: bool = False,
                    guests: list[Guest] | None = None) -> list[Guest]:
        _, key = self.SORT_KEYS[criterion]
        return self.sort_by(key, reverse, guests)
