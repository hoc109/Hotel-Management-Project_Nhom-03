"""Dữ liệu mẫu tạo khi chạy chương trình lần đầu.

Các ngày được tính tương đối theo "hôm nay" để luôn có đủ tình huống demo:
đặt phòng đã trả (có doanh thu), đang ở, nhận phòng hôm nay, đặt trước,
đã hủy, lượt ở trong ngày (tính 1 đêm) và khách thân thiết.
"""

from datetime import timedelta
from typing import TYPE_CHECKING

from hotel.models.booking import Booking
from hotel.models.enums import BookingStatus, RoomStatus
from hotel.models.guest import Guest
from hotel.models.room import DeluxeRoom, StandardRoom, SuiteRoom
from hotel.models.service import Service, ServiceUsage

if TYPE_CHECKING:
    from hotel.managers.hotel_manager import HotelManager


def _rooms() -> list:
    return [
        StandardRoom("R001", "101", 500_000),
        StandardRoom("R002", "102", 550_000, basic_service="Wifi, nước suối, trà"),
        StandardRoom("R003", "103", 600_000),
        DeluxeRoom("R004", "201", 1_200_000, extra_service_fee=200_000),
        DeluxeRoom("R005", "202", 1_300_000, extra_service_fee=200_000),
        DeluxeRoom("R006", "203", 1_500_000, RoomStatus.MAINTENANCE, extra_service_fee=250_000),
        SuiteRoom("R007", "301", 2_500_000, extra_service_fee=300_000, butler_fee=500_000),
        SuiteRoom("R008", "302", 3_000_000, extra_service_fee=400_000, butler_fee=500_000),
    ]


def _guests() -> list[Guest]:
    return [
        Guest("G001", "Nguyễn Văn An", "0901234567", "001090012345"),
        Guest("G002", "Trần Thị Bình", "0912345678", "079185001234"),
        Guest("G003", "Lê Hoàng Cường", "0987654321"),
        Guest("G004", "Phạm Thị Dung", "0934567890", "B1234567"),
        Guest("G005", "Hoàng Minh Đức", "0978123456"),
        Guest("G006", "Võ Thị Hà", "0965432109"),
    ]


def _services() -> list[Service]:
    return [
        Service("S001", "Minibar", 50_000, "lần"),
        Service("S002", "Giặt ủi", 30_000, "kg"),
        Service("S003", "Ăn sáng buffet", 150_000, "suất"),
        Service("S004", "Đưa đón sân bay", 300_000, "lượt"),
        Service("S005", "Spa", 400_000, "lần"),
    ]


def populate(hotel: "HotelManager") -> None:
    """Đổ dữ liệu mẫu vào các manager (bỏ qua kiểm tra quyền, chỉ dùng khi khởi tạo)."""
    for room in _rooms():
        hotel.rooms.add(room)
    for guest in _guests():
        hotel.guests.add(guest)
    for service in _services():
        hotel.services.add(service)

    today = hotel.today()
    calc = hotel.bookings.discount_calculator

    def make(booking_id: str, guest_id: str, room_id: str, start: int, nights: int,
             status: BookingStatus, services: list[tuple[str, int, int]] = ()) -> None:
        """Tạo một booking mẫu: ``start`` = số ngày lệch so với hôm nay."""
        room = hotel.rooms.get(room_id)
        check_in = today + timedelta(days=start)
        check_out = check_in + timedelta(days=nights)
        real_nights = Booking.count_nights(check_in, check_out)
        rate = calc.calculate(real_nights, hotel.bookings.completed_stays(guest_id))
        usages = []
        for service_id, qty, day_offset in services:
            service = hotel.services.get(service_id)
            usages.append(ServiceUsage(service.service_id, service.name, service.price, qty,
                                       check_in + timedelta(days=day_offset)))
        stayed = status in (BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT)
        booking = Booking(
            booking_id, guest_id, room_id, check_in, check_out, status=status,
            created_on=min(check_in, today) - timedelta(days=3),
            room_number=room.room_number, room_type=room.get_room_type(),
            room_cost=room.calculate_cost(real_nights), discount_rate=rate, services=usages,
            checked_in_on=check_in if stayed else None,
            checked_out_on=check_out if status == BookingStatus.CHECKED_OUT else None)
        hotel.bookings.add(booking)
        if status == BookingStatus.CHECKED_IN:
            room.status = RoomStatus.OCCUPIED

    done, staying = BookingStatus.CHECKED_OUT, BookingStatus.CHECKED_IN
    booked, cancelled = BookingStatus.BOOKED, BookingStatus.CANCELLED
    # Lịch sử (theo thứ tự thời gian để tính đúng ưu đãi khách thân thiết)
    make("B001", "G001", "R002", -60, 2, done)
    make("B002", "G001", "R007", -45, 7, done, [("S003", 14, 0), ("S005", 2, 3)])
    make("B003", "G002", "R004", -32, 3, done, [("S004", 1, 0)])
    make("B004", "G001", "R001", -20, 3, done, [("S002", 4, 1)])
    make("B005", "G002", "R005", -12, 5, done, [("S001", 3, 1), ("S003", 4, 2)])
    # Hiện tại và tương lai
    make("B006", "G003", "R003", -1, 3, staying, [("S001", 2, 0)])
    make("B007", "G004", "R005", 0, 3, booked)            # nhận phòng hôm nay
    make("B008", "G001", "R008", 5, 3, booked)            # khách thân thiết (đã 3 lượt)
    make("B009", "G006", "R001", 2, 2, cancelled)
    make("B010", "G005", "R004", 1, 0, booked)            # nhận/trả cùng ngày → 1 đêm
