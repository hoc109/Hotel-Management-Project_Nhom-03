"""Quản lý danh sách phòng: thêm, sửa, tìm kiếm, sắp xếp."""

from hotel.managers.base_manager import BaseManager
from hotel.models.enums import RoomStatus
from hotel.models.room import Room, RoomFactory
from hotel.utils.exceptions import DuplicateIdError


class RoomManager(BaseManager[Room]):
    """Quản lý các đối tượng ``Room`` (mọi loại phòng)."""

    ID_PREFIX = "R"

    @property
    def entity_name(self) -> str:
        return "phòng"

    def get_id(self, item: Room) -> str:
        return item.room_id

    def create_from_dict(self, data: dict) -> Room:
        return RoomFactory.from_dict(data)

    def _validate_unique(self, item: Room, exclude_id: str | None = None) -> None:
        """Số phòng cũng phải là duy nhất."""
        for room in self._items.values():
            if room.room_id != exclude_id and room.room_number == item.room_number:
                raise DuplicateIdError(
                    f"Số phòng '{item.room_number}' đã được dùng cho phòng {room.room_id}.")

    # ---------------------------------------------------------- tìm kiếm
    def search_by_type(self, room_type: str) -> list[Room]:
        """Lọc theo loại phòng (standard/deluxe/suite) – so khớp chính xác lớp."""
        return self.filter(lambda r: r.ROOM_TYPE == room_type)

    def search_by_price(self, min_price: float, max_price: float) -> list[Room]:
        """Lọc phòng có giá/đêm trong khoảng [min_price, max_price]."""
        low, high = sorted((min_price, max_price))
        return self.filter(lambda r: low <= r.price_per_night <= high)

    def search_by_status(self, status: RoomStatus) -> list[Room]:
        return self.filter(lambda r: r.status == status)

    def search_by_number(self, keyword: str) -> list[Room]:
        """Tìm gần đúng theo số phòng (chứa chuỗi), vd '0' -> 101, 102, 201..."""
        keyword = keyword.strip()
        return self.filter(lambda r: keyword in r.room_number)

    def find_by_number(self, room_number: str) -> Room | None:
        return next((r for r in self._items.values() if r.room_number == room_number), None)

    # ---------------------------------------------------------- sắp xếp
    SORT_KEYS = {
        "price": ("Giá/đêm", lambda r: (r.price_per_night, int(r.room_number))),
        "number": ("Số phòng", lambda r: int(r.room_number)),
        "type": ("Loại phòng", lambda r: (r.get_room_type(), int(r.room_number))),
    }

    def sort_rooms(self, criterion: str, reverse: bool = False,
                   rooms: list[Room] | None = None) -> list[Room]:
        """Sắp xếp theo 'price' | 'number' | 'type'."""
        _, key = self.SORT_KEYS[criterion]
        return self.sort_by(key, reverse, rooms)
