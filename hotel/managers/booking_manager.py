"""Nghiệp vụ đặt phòng: đặt, sửa, hủy, nhận phòng, dịch vụ, trả phòng.

Quy tắc chính:
* Không đặt trùng phòng trong cùng khoảng thời gian (xét lượt Đã đặt/Đang ở).
* Số đêm tối thiểu 1 (nhận/trả cùng ngày tính 1 đêm).
* Nhận phòng khi hôm nay nằm trong thời gian lưu trú và phòng đang Trống.
* Trả phòng: chốt tiền theo số đêm đã đặt, áp dụng giảm giá, phòng về Trống.
"""

from collections.abc import Callable
from datetime import date

from hotel.managers.base_manager import BaseManager
from hotel.managers.guest_manager import GuestManager
from hotel.managers.room_manager import RoomManager
from hotel.managers.service_manager import ServiceManager
from hotel.models.booking import Booking
from hotel.models.discount import DiscountCalculator
from hotel.models.enums import BookingStatus, RoomStatus
from hotel.models.room import Room
from hotel.models.service import ServiceUsage
from hotel.utils.exceptions import BusinessRuleError, DuplicateIdError
from hotel.utils.formatter import format_date
from hotel.utils.text_utils import fuzzy_contains
from hotel.utils.validators import validate_date_range, validate_int


class BookingManager(BaseManager[Booking]):
    """Quản lý ``Booking`` và các ràng buộc liên quan tới phòng, khách, dịch vụ."""

    ID_PREFIX = "B"

    def __init__(self, rooms: RoomManager, guests: GuestManager, services: ServiceManager,
                 discount: DiscountCalculator | None = None,
                 today_provider: Callable[[], date] = date.today) -> None:
        super().__init__()
        self.__rooms = rooms
        self.__guests = guests
        self.__services = services
        self.__discount = discount or DiscountCalculator()
        self.__today = today_provider

    @property
    def entity_name(self) -> str:
        return "đặt phòng"

    def get_id(self, item: Booking) -> str:
        return item.booking_id

    def create_from_dict(self, data: dict) -> Booking:
        return Booking.from_dict(data)

    @property
    def discount_calculator(self) -> DiscountCalculator:
        return self.__discount

    def today(self) -> date:
        return self.__today()

    # ----------------------------------------------------------- truy vấn phụ
    def completed_stays(self, guest_id: str, exclude_booking_id: str | None = None) -> int:
        """Số lượt khách đã trả phòng (dùng cho ưu đãi khách thân thiết)."""
        return sum(1 for b in self._items.values()
                   if b.guest_id == guest_id and b.status == BookingStatus.CHECKED_OUT
                   and b.booking_id != exclude_booking_id)

    def conflicts(self, room_id: str, check_in: date, check_out: date,
                  exclude_booking_id: str | None = None) -> list[Booking]:
        """Các lượt đặt còn hiệu lực của phòng bị trùng với khoảng thời gian cho trước."""
        return [b for b in self._items.values()
                if b.room_id == room_id and b.is_active
                and b.booking_id != exclude_booking_id and b.overlaps(check_in, check_out)]

    def is_room_free(self, room_id: str, check_in: date, check_out: date,
                     exclude_booking_id: str | None = None) -> bool:
        return not self.conflicts(room_id, check_in, check_out, exclude_booking_id)

    def available_rooms(self, check_in: date, check_out: date) -> list[Room]:
        """Phòng có thể đặt trong khoảng ngày (không bảo trì, không trùng lịch)."""
        validate_date_range(check_in, check_out)
        return [r for r in self.__rooms.list_all()
                if r.is_bookable() and self.is_room_free(r.room_id, check_in, check_out)]

    def active_for_room(self, room_id: str) -> list[Booking]:
        return [b for b in self._items.values() if b.room_id == room_id and b.is_active]

    def active_for_guest(self, guest_id: str) -> list[Booking]:
        return [b for b in self._items.values() if b.guest_id == guest_id and b.is_active]

    def history_of_guest(self, guest_id: str) -> list[Booking]:
        return self.sort_by(lambda b: b.check_in, items=self.filter(
            lambda b: b.guest_id == guest_id))

    def quote(self, room: Room, guest_id: str, check_in: date, check_out: date,
              exclude_booking_id: str | None = None) -> tuple[float, float]:
        """Tạm tính (tiền phòng, tỷ lệ giảm giá) – đa hình qua ``room.calculate_cost``."""
        nights = Booking.count_nights(check_in, check_out)
        rate = self.__discount.calculate(nights, self.completed_stays(guest_id, exclude_booking_id))
        return room.calculate_cost(nights), rate

    # ---------------------------------------------------------- kiểm tra chung
    def _check_room_for_stay(self, room: Room, check_in: date, check_out: date,
                             exclude_booking_id: str | None = None) -> None:
        validate_date_range(check_in, check_out)
        if check_in < self.today():
            raise BusinessRuleError(
                f"Ngày nhận phòng ({format_date(check_in)}) không được ở quá khứ.")
        if not room.is_bookable():
            raise BusinessRuleError(f"Phòng {room.room_number} đang bảo trì, không thể đặt.")
        clashes = self.conflicts(room.room_id, check_in, check_out, exclude_booking_id)
        if clashes:
            detail = "; ".join(f"{b.booking_id} ({format_date(b.check_in)} → "
                               f"{format_date(b.check_out)})" for b in clashes)
            raise BusinessRuleError(
                f"Phòng {room.room_number} đã có người đặt trùng thời gian: {detail}.")

    # --------------------------------------------------------------- nghiệp vụ
    def create_booking(self, booking_id: str, guest_id: str, room_id: str,
                       check_in: date, check_out: date) -> Booking:
        """Tạo đặt phòng mới (trạng thái Đã đặt)."""
        if self.exists(booking_id):
            # Kiểm tra sớm để báo lỗi trùng mã trước các lỗi khác
            raise DuplicateIdError(f"Mã đặt phòng '{self.normalize_id(booking_id)}' đã tồn tại.")
        guest = self.__guests.get(guest_id)
        room = self.__rooms.get(room_id)
        self._check_room_for_stay(room, check_in, check_out)
        cost, rate = self.quote(room, guest.guest_id, check_in, check_out)
        booking = Booking(booking_id, guest.guest_id, room.room_id, check_in, check_out,
                          created_on=self.today(), room_number=room.room_number,
                          room_type=room.get_room_type(), room_cost=cost, discount_rate=rate)
        return self.add(booking)

    def update_booking(self, booking_id: str, *, room_id: str | None = None,
                       check_in: date | None = None, check_out: date | None = None) -> Booking:
        """Sửa ngày và/hoặc đổi phòng (chỉ khi Đã đặt), vẫn kiểm tra trùng lịch."""
        booking = self.get(booking_id)
        if booking.status != BookingStatus.BOOKED:
            raise BusinessRuleError(
                f"Chỉ sửa được đặt phòng ở trạng thái 'Đã đặt' (hiện tại: {booking.status.label}).")
        new_in = check_in or booking.check_in
        new_out = check_out or booking.check_out
        room = self.__rooms.get(room_id or booking.room_id)
        self._check_room_for_stay(room, new_in, new_out, exclude_booking_id=booking.booking_id)
        booking.update_stay(new_in, new_out)
        if room.room_id != booking.room_id:
            booking.assign_room(room.room_id, room.room_number, room.get_room_type())
        cost, rate = self.quote(room, booking.guest_id, new_in, new_out, booking.booking_id)
        booking.set_pricing(cost, rate)
        return booking

    def cancel_booking(self, booking_id: str) -> Booking:
        """Hủy đặt phòng (chỉ khi chưa nhận phòng)."""
        booking = self.get(booking_id)
        booking.cancel()
        return booking

    def check_in(self, booking_id: str) -> Booking:
        """Nhận phòng: Đã đặt -> Đang ở; phòng Trống -> Đang ở."""
        booking = self.get(booking_id)
        if booking.status != BookingStatus.BOOKED:
            raise BusinessRuleError(
                f"Chỉ nhận phòng được với đặt phòng 'Đã đặt' (hiện tại: {booking.status.label}).")
        today = self.today()
        if not booking.covers(today):
            raise BusinessRuleError(
                f"Hôm nay ({format_date(today)}) không nằm trong thời gian lưu trú "
                f"{format_date(booking.check_in)} → {format_date(booking.check_out)}.")
        room = self.__rooms.get(booking.room_id)
        if room.status == RoomStatus.MAINTENANCE:
            raise BusinessRuleError(f"Phòng {room.room_number} đang bảo trì, chưa thể nhận phòng.")
        if room.status == RoomStatus.OCCUPIED:
            raise BusinessRuleError(f"Phòng {room.room_number} vẫn đang có khách ở.")
        booking.mark_checked_in(today)
        room.status = RoomStatus.OCCUPIED
        return booking

    def add_service_usage(self, booking_id: str, service_id: str, quantity: int) -> ServiceUsage:
        """Ghi nhận dịch vụ phát sinh cho khách đang ở."""
        booking = self.get(booking_id)
        service = self.__services.get(service_id)
        quantity = validate_int(quantity, "Số lượng", min_value=1, max_value=1000)
        usage = ServiceUsage(service.service_id, service.name, service.price, quantity,
                             self.today())
        booking.add_service(usage)
        return usage

    def check_out(self, booking_id: str) -> Booking:
        """Trả phòng: Đang ở -> Đã trả, phòng về Trống.

        Tiền phòng giữ nguyên mức đã chốt khi đặt (theo số đêm đã đặt, giá tại
        thời điểm đặt); tỷ lệ giảm giá được tính lại tại thời điểm trả phòng.
        """
        booking = self.get(booking_id)
        if booking.status != BookingStatus.CHECKED_IN:
            raise BusinessRuleError(
                f"Chỉ trả phòng được với đặt phòng 'Đang ở' (hiện tại: {booking.status.label}).")
        rate = self.__discount.calculate(
            booking.nights, self.completed_stays(booking.guest_id, booking.booking_id))
        booking.set_pricing(booking.room_cost, rate)
        booking.mark_checked_out(self.today())
        room = self.__rooms.find(booking.room_id)
        if room is not None:
            room.status = RoomStatus.AVAILABLE
        return booking

    def discount_details(self, booking: Booking) -> list[tuple[str, float]]:
        """Các chính sách giảm giá áp dụng cho một đặt phòng."""
        return self.__discount.details(
            booking.nights, self.completed_stays(booking.guest_id, booking.booking_id))

    # ---------------------------------------------------------- tìm kiếm
    def search_by_guest(self, keyword: str) -> list[Booking]:
        """Tìm theo mã khách (chính xác) hoặc tên khách (gần đúng)."""
        def match(b: Booking) -> bool:
            if b.guest_id == keyword.strip().upper():
                return True
            guest = self.__guests.find(b.guest_id)
            return guest is not None and fuzzy_contains(guest.full_name, keyword)
        return self.filter(match)

    def search_by_status(self, status: BookingStatus) -> list[Booking]:
        return self.filter(lambda b: b.status == status)

    def search_by_room(self, room_id: str) -> list[Booking]:
        return self.filter(lambda b: b.room_id == room_id.strip().upper())

    def bookings_on(self, day: date, mode: str = "staying") -> list[Booking]:
        """Đặt phòng theo ngày.

        mode:
            'staying'   – khách đang lưu trú vào ngày đó (không tính lượt đã hủy);
            'check_in'  – có ngày nhận phòng là ngày đó;
            'check_out' – có ngày trả phòng là ngày đó.
        """
        if mode == "check_in":
            result = self.filter(lambda b: b.check_in == day)
        elif mode == "check_out":
            result = self.filter(lambda b: b.check_out == day)
        else:
            result = self.filter(lambda b: b.status != BookingStatus.CANCELLED and b.covers(day))
        return self.sort_by(lambda b: (b.check_in, b.booking_id), items=result)

    SORT_KEYS = {
        "check_in": ("Ngày nhận phòng", lambda b: (b.check_in, b.booking_id)),
        "amount": ("Tổng tiền", lambda b: (b.amount_due, b.booking_id)),
        "id": ("Mã đặt phòng", lambda b: b.booking_id),
    }

    def sort_bookings(self, criterion: str, reverse: bool = False,
                      bookings: list[Booking] | None = None) -> list[Booking]:
        _, key = self.SORT_KEYS[criterion]
        return self.sort_by(key, reverse, bookings)
