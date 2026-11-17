"""Quản lý danh sách phòng: thêm, sửa, tìm kiếm, sắp xếp."""

from hotel.managers.base_manager import BaseManager
from hotel.models.enums import RoomStatus
from hotel.models.room import Room, RoomFactory
from hotel.utils.exceptions import DuplicateIdError, ValidationError


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

    def search(self, *, room_type: str | None = None, min_price: float | None = None,
               max_price: float | None = None, status: RoomStatus | None = None,
               number_keyword: str | None = None) -> list[Room]:
        """Tìm kết hợp nhiều tiêu chí: phòng phải thỏa TẤT CẢ tiêu chí được đưa vào.

        Tiêu chí nào để ``None`` thì bỏ qua. Chỉ nhập một đầu của khoảng giá thì đầu kia không giới hạn;
        nhập đủ hai đầu mà ngược (min > max) thì tự hoán đổi, giống ``search_by_price``.
        """
        if room_type is not None and room_type not in RoomFactory.room_types():
            raise ValidationError(f"Loại phòng '{room_type}' không hợp lệ "
                                  f"(chỉ: {', '.join(RoomFactory.room_types())}).")
        result = self.list_all()
        if room_type is not None:
            result = self.filter(lambda r: r.ROOM_TYPE == room_type, result)
        if min_price is not None or max_price is not None:
            low = 0 if min_price is None else min_price
            high = float("inf") if max_price is None else max_price
            if min_price is not None and max_price is not None:
                low, high = sorted((low, high))
            result = self.filter(lambda r: low <= r.price_per_night <= high, result)
        if status is not None:
            result = self.filter(lambda r: r.status == status, result)
        if number_keyword is not None and number_keyword.strip():
            keyword = number_keyword.strip()
            result = self.filter(lambda r: keyword in r.room_number, result)
        return result

    def find_by_number(self, room_number: str) -> Room | None:
        return next((r for r in self._items.values() if r.room_number == room_number), None)

    # ---------------------------------------------------------- sắp xếp
    SORT_KEYS = {
        "price": ("Giá/đêm", lambda r: r.price_per_night),
        "number": ("Số phòng", lambda r: int(r.room_number)),
        "type": ("Loại phòng", lambda r: r.get_room_type()),
    }

    def sort_rooms(self, criterion: str, reverse: bool = False,
                   rooms: list[Room] | None = None) -> list[Room]:
        """Sắp xếp theo 'price' | 'number' | 'type'.

        Các phòng bằng nhau (vd đồng giá) luôn xếp theo số phòng tăng dần, kể cả khi
        sắp xếp giảm dần (``sorted`` ổn định nên giữ nguyên thứ tự của bước xếp theo số phòng).
        """
        if criterion not in self.SORT_KEYS:
            raise ValidationError(f"Chỉ hỗ trợ sắp xếp theo: {', '.join(self.SORT_KEYS)}.")
        _, key = self.SORT_KEYS[criterion]
        by_number = self.sort_by(self.SORT_KEYS["number"][1], items=rooms)  # bước 1: số phòng tăng dần
        return self.sort_by(key, reverse, by_number)                         # bước 2: tiêu chí chính
