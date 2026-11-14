"""Các hàm hiển thị bảng dữ liệu dùng chung cho các menu."""

from typing import TYPE_CHECKING

from hotel.models.booking import Booking
from hotel.models.guest import Guest
from hotel.models.room import Room
from hotel.models.service import Service
from hotel.models.user import User
from hotel.utils.formatter import format_date, format_money, format_percent, print_table

if TYPE_CHECKING:
    from hotel.managers.hotel_manager import HotelManager

ROOM_HEADERS = ["Mã phòng", "Số phòng", "Loại", "Giá/đêm", "Trạng thái", "Tiện ích / Phụ phí"]
GUEST_HEADERS = ["Mã KH", "Họ tên", "Số điện thoại", "CCCD/Hộ chiếu"]
SERVICE_HEADERS = ["Mã DV", "Tên dịch vụ", "Đơn giá", "Đơn vị"]
BOOKING_HEADERS = ["Mã ĐP", "Khách hàng", "Phòng", "Loại", "Nhận phòng", "Trả phòng",
                   "Số đêm", "Trạng thái", "Tổng tiền"]
USER_HEADERS = ["Tên đăng nhập", "Họ tên", "Vai trò"]
USAGE_HEADERS = ["Ngày", "Dịch vụ", "SL", "Đơn giá", "Thành tiền"]


def show_rooms(rooms: list[Room], title: str = "DANH SÁCH PHÒNG",
               empty: str = "Không có phòng nào.") -> None:
    print_table(ROOM_HEADERS, [r.to_row() for r in rooms], title=title, empty_message=empty)


def show_guests(guests: list[Guest], title: str = "DANH SÁCH KHÁCH HÀNG",
                empty: str = "Không có khách hàng nào.") -> None:
    print_table(GUEST_HEADERS, [g.to_row() for g in guests], title=title, empty_message=empty)


def show_services(services: list[Service], title: str = "DANH MỤC DỊCH VỤ",
                  empty: str = "Không có dịch vụ nào.") -> None:
    print_table(SERVICE_HEADERS, [s.to_row() for s in services], title=title,
                empty_message=empty)


def show_users(users: list[User], title: str = "DANH SÁCH TÀI KHOẢN") -> None:
    print_table(USER_HEADERS, [u.to_row() for u in users], title=title,
                empty_message="Không có tài khoản nào.")


def show_bookings(hotel: "HotelManager", bookings: list[Booking],
                  title: str = "DANH SÁCH ĐẶT PHÒNG",
                  empty: str = "Không có đặt phòng nào.") -> None:
    rows = []
    for b in bookings:
        guest = hotel.guests.find(b.guest_id)
        rows.append(b.to_row(f"{guest.full_name} ({b.guest_id})" if guest else b.guest_id))
    print_table(BOOKING_HEADERS, rows, title=title, empty_message=empty)


def show_booking_detail(hotel: "HotelManager", booking: Booking) -> None:
    """Chi tiết một đặt phòng: thông tin chung, dịch vụ, các khoản tiền."""
    guest = hotel.guests.find(booking.guest_id)
    print_table(["Thông tin", "Giá trị"], [
        ["Mã đặt phòng", booking.booking_id],
        ["Khách hàng", f"{guest.full_name} - {guest.phone}" if guest else booking.guest_id],
        ["Phòng", f"{booking.room_number} ({booking.room_id}) - {booking.room_type}"],
        ["Thời gian", f"{format_date(booking.check_in)} → {format_date(booking.check_out)} "
                      f"({booking.nights} đêm)"],
        ["Trạng thái", booking.status.label],
        ["Ngày tạo", format_date(booking.created_on)],
        ["Nhận phòng thực tế", format_date(booking.checked_in_on)],
        ["Trả phòng thực tế", format_date(booking.checked_out_on)],
        ["Tiền phòng", format_money(booking.room_cost)],
        ["Giảm giá", f"{format_money(booking.discount_amount)} "
                     f"({format_percent(booking.discount_rate)})"],
        ["Dịch vụ", format_money(booking.service_total)],
        ["TỔNG", format_money(booking.amount_due)],
    ], title=f"CHI TIẾT ĐẶT PHÒNG {booking.booking_id}", show_count=False)
    print_table(USAGE_HEADERS, [u.to_row() for u in booking.services],
                title="Dịch vụ phát sinh", empty_message="Chưa sử dụng dịch vụ nào.")
