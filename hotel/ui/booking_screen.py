"""Màn hình Đặt phòng & lưu trú: đặt, sửa, hủy, nhận phòng, dịch vụ, trả phòng."""

from datetime import timedelta

from hotel.models.booking import Booking
from hotel.models.enums import BookingStatus, Permission
from hotel.ui.base_screen import BaseScreen
from hotel.ui.menu import MenuItem
from hotel.ui.views import show_booking_detail, show_bookings, show_rooms, show_services
from hotel.utils.exceptions import BusinessRuleError, ValidationError
from hotel.utils.formatter import (format_date, format_money, format_percent, print_info,
                                   print_success, print_table, print_warning)
from hotel.utils.input_helper import (ask, ask_choice, ask_date, ask_int, ask_sort_order,
                                      confirm)
from hotel.utils.validators import validate_id


class BookingScreen(BaseScreen):
    """Các nghiệp vụ đặt phòng, nhận phòng, trả phòng."""

    TITLE = "Đặt phòng & lưu trú"

    def menu_items(self) -> list[MenuItem]:
        p = Permission.MANAGE_BOOKINGS
        return [
            MenuItem("1", "Tạo đặt phòng", self.create_booking, p),
            MenuItem("2", "Cập nhật đặt phòng (đổi ngày / đổi phòng)", self.update_booking, p),
            MenuItem("3", "Hủy đặt phòng", self.cancel_booking, p),
            MenuItem("4", "Nhận phòng (check-in)", self.check_in, p),
            MenuItem("5", "Thêm dịch vụ phát sinh", self.add_service, p),
            MenuItem("6", "Trả phòng (check-out) + xuất hóa đơn", self.check_out, p),
            MenuItem("7", "Hiển thị danh sách đặt phòng", self.list_bookings, p),
            MenuItem("8", "Xem chi tiết / hóa đơn tạm tính", self.view_detail, p),
            MenuItem("9", "Tìm kiếm đặt phòng", self.search_bookings, p),
            MenuItem("10", "Sắp xếp đặt phòng", self.sort_bookings, p),
        ]

    # --------------------------------------------------------------- tiện ích
    def _ask_booking(self, prompt: str, *allowed: BookingStatus) -> Booking:
        """Nhập mã đặt phòng, chỉ chấp nhận các trạng thái cho phép."""
        def condition(b: Booking) -> str | None:
            if allowed and b.status not in allowed:
                names = ", ".join(s.label for s in allowed)
                return f"Đặt phòng {b.booking_id} đang '{b.status.label}' (yêu cầu: {names})."
            return None
        return self.ask_existing(self._hotel.bookings, prompt, condition)

    def _show_quote(self, room, guest_id: str, check_in, check_out,
                    exclude: str | None = None) -> None:
        nights = Booking.count_nights(check_in, check_out)
        cost, rate = self._hotel.bookings.quote(room, guest_id, check_in, check_out, exclude)
        rows = [[label, format_money(amount)] for label, amount in room.cost_breakdown(nights)]
        rows.append(["Cộng tiền phòng", format_money(cost)])
        stays = self._hotel.bookings.completed_stays(guest_id, exclude)
        for name, r in self._hotel.bookings.discount_calculator.details(nights, stays):
            rows.append([f"  {name}", format_percent(r)])
        rows.append([f"Giảm giá ({format_percent(rate)}, tối đa 15%)",
                     f"-{format_money(round(cost * rate))}" if rate else format_money(0)])
        rows.append(["TẠM TÍNH (chưa gồm dịch vụ)", format_money(cost - round(cost * rate))])
        print_table(["Khoản mục", "Số tiền"], rows,
                    title=f"BÁO GIÁ: phòng {room.room_number} – {nights} đêm", show_count=False)

    def _ask_available_room(self, check_in, check_out, exclude: str | None = None,
                            default: str | None = None):
        bookings = self._hotel.bookings
        free = [r for r in self._hotel.rooms.sort_rooms("number")
                if r.is_bookable() and bookings.is_room_free(r.room_id, check_in, check_out,
                                                             exclude)]
        show_rooms(free, title=f"Phòng còn trống {format_date(check_in)} → "
                               f"{format_date(check_out)}",
                   empty="Không còn phòng trống trong thời gian này.")
        if not free:
            raise BusinessRuleError("Không có phòng phù hợp, hãy chọn khoảng thời gian khác.")
        free_ids = {r.room_id for r in free}

        def condition(room) -> str | None:
            if room.room_id in free_ids:
                return None
            if not room.is_bookable():
                return f"Phòng {room.room_number} đang bảo trì, không thể đặt."
            # Phòng đã có người đặt: nói rõ trùng với đơn nào, vào những ngày nào
            clashes = bookings.conflicts(room.room_id, check_in, check_out, exclude)
            detail = "; ".join(f"{b.booking_id} ({format_date(b.check_in)} → "
                               f"{format_date(b.check_out)})" for b in clashes)
            return f"Phòng {room.room_number} bị TRÙNG LỊCH với đơn {detail}."
        if default and default in free_ids:
            return ask("Mã phòng", default=self._hotel.rooms.get(default),
                       show_default=default,
                       validator=lambda raw: self._room_validator(raw, condition))
        return self.ask_existing(self._hotel.rooms, "Chọn mã phòng", condition)

    def _room_validator(self, raw: str, condition):
        room = self._hotel.rooms.find(raw)
        if room is None:
            raise ValidationError(f"Không tìm thấy phòng có mã '{raw}'.")
        error = condition(room)
        if error:
            raise ValidationError(error)
        return room

    def _ask_dates(self, default_in=None, default_out=None):
        """Nhập ngày nhận/trả; nhập lại nếu ngày nhận ở quá khứ hoặc ngày trả trước ngày nhận."""
        today = self._hotel.today()
        in_default = default_in if default_in and default_in >= today else today
        while True:
            check_in = ask_date("Ngày nhận phòng", default=in_default)
            if check_in >= today:
                break
            print_warning(f"Ngày nhận phòng không được ở quá khứ (hôm nay {format_date(today)}). "
                          "Vui lòng nhập lại.")
        out_default = default_out if default_out and default_out >= check_in \
            else check_in + timedelta(days=1)
        while True:
            check_out = ask_date("Ngày trả phòng (trùng ngày nhận = 1 đêm)", default=out_default)
            if check_out >= check_in:
                return check_in, check_out
            print_warning("Ngày trả phòng không được trước ngày nhận phòng. Vui lòng nhập lại.")

    # ---------------------------------------------------------- 1. Tạo mới
    def create_booking(self) -> None:
        print_info("Tạo đặt phòng mới (gõ 'q' để hủy).")
        guest = self.ask_existing(self._hotel.guests, "Mã khách hàng")
        print_info(f"Khách: {guest}")
        check_in, check_out = self._ask_dates()
        room = self._ask_available_room(check_in, check_out)
        self._show_quote(room, guest.guest_id, check_in, check_out)
        booking_id = self.ask_new_id(self._hotel.bookings, "Mã đặt phòng", "B",
                                     lambda s: validate_id(s, "Mã đặt phòng"))
        if not confirm("Xác nhận đặt phòng?"):
            print_warning("Đã hủy đặt phòng.")
            return
        booking = self._hotel.create_booking(booking_id, guest.guest_id, room.room_id,
                                             check_in, check_out)
        print_success(f"Đặt phòng thành công: {self._hotel.describe_stay(booking)}.")
        show_bookings(self._hotel, [booking], title="Đặt phòng vừa tạo")

    # ---------------------------------------------------------- 2. Cập nhật
    def update_booking(self) -> None:
        booking = self._ask_booking("Mã đặt phòng cần sửa", BookingStatus.BOOKED)
        show_bookings(self._hotel, [booking], title="Thông tin hiện tại")
        print_info("Nhấn Enter để giữ nguyên giá trị trong [ ]; gõ 'q' để hủy.")
        check_in, check_out = self._ask_dates(booking.check_in, booking.check_out)
        room = self._ask_available_room(check_in, check_out, exclude=booking.booking_id,
                                        default=booking.room_id)
        if (check_in, check_out, room.room_id) == (booking.check_in, booking.check_out,
                                                   booking.room_id):
            print_warning("Không có thay đổi nào.")
            return
        self._show_quote(room, booking.guest_id, check_in, check_out, booking.booking_id)
        if not confirm("Lưu thay đổi?"):
            print_warning("Đã hủy cập nhật.")
            return
        updated = self._hotel.update_booking(booking.booking_id, room_id=room.room_id,
                                             check_in=check_in, check_out=check_out)
        print_success(f"Đã cập nhật: {self._hotel.describe_stay(updated)}.")
        show_bookings(self._hotel, [updated], title="Sau khi cập nhật")

    # -------------------------------------------------------------- 3. Hủy
    def cancel_booking(self) -> None:
        booking = self._ask_booking("Mã đặt phòng cần hủy", BookingStatus.BOOKED)
        show_bookings(self._hotel, [booking], title="Đặt phòng sẽ bị hủy")
        if not confirm("Bạn chắc chắn muốn hủy đặt phòng này?"):
            print_warning("Giữ nguyên đặt phòng.")
            return
        self._hotel.cancel_booking(booking.booking_id)
        print_success(f"Đã hủy đặt phòng {booking.booking_id}.")

    # ---------------------------------------------------------- 4. Nhận phòng
    def check_in(self) -> None:
        today = self._hotel.today()
        ready = [b for b in self._hotel.bookings.search_by_status(BookingStatus.BOOKED)
                 if b.covers(today)]
        show_bookings(self._hotel, ready, title=f"Đặt phòng có thể nhận hôm nay "
                                                f"({format_date(today)})",
                      empty="Hôm nay không có đặt phòng nào chờ nhận.")
        booking = self._ask_booking("Mã đặt phòng nhận phòng", BookingStatus.BOOKED)
        self._hotel.check_in(booking.booking_id)
        print_success(f"Nhận phòng thành công: {self._hotel.describe_stay(booking)}. "
                      f"Phòng {booking.room_number} chuyển sang 'Đang ở'.")

    # ------------------------------------------------------------ 5. Dịch vụ
    def add_service(self) -> None:
        staying = self._hotel.bookings.search_by_status(BookingStatus.CHECKED_IN)
        show_bookings(self._hotel, staying, title="Khách đang lưu trú",
                      empty="Hiện không có khách nào đang ở.")
        if not staying:
            return
        booking = self._ask_booking("Mã đặt phòng", BookingStatus.CHECKED_IN)
        show_services(self._hotel.services.list_all())
        service = self.ask_existing(self._hotel.services, "Mã dịch vụ")
        quantity = ask_int(f"Số lượng ({service.unit})", min_value=1, max_value=1000)
        usage = self._hotel.add_service_to_booking(booking.booking_id, service.service_id,
                                                   quantity)
        print_success(f"Đã thêm: {usage} vào đặt phòng {booking.booking_id}. "
                      f"Tổng dịch vụ hiện tại: {format_money(booking.service_total)}.")

    # ----------------------------------------------------------- 6. Trả phòng
    def check_out(self) -> None:
        staying = self._hotel.bookings.search_by_status(BookingStatus.CHECKED_IN)
        show_bookings(self._hotel, staying, title="Khách đang lưu trú",
                      empty="Hiện không có khách nào đang ở.")
        if not staying:
            return
        booking = self._ask_booking("Mã đặt phòng trả phòng", BookingStatus.CHECKED_IN)
        if self._hotel.today() < booking.check_out:
            print_warning("Khách trả phòng sớm – vẫn tính đủ số đêm đã đặt.")
        if not confirm(f"Xác nhận trả phòng {booking.room_number} cho đặt phòng "
                       f"{booking.booking_id}?"):
            print_warning("Đã hủy trả phòng.")
            return
        _, invoice, path = self._hotel.check_out(booking.booking_id)
        print(invoice.render())
        print_success(f"Trả phòng thành công. Hóa đơn đã lưu tại: {path}")

    # ---------------------------------------------------------- 7. Hiển thị
    def list_bookings(self) -> None:
        show_bookings(self._hotel, self._hotel.bookings.sort_bookings("check_in"),
                      empty="Chưa có đặt phòng nào trong hệ thống.")

    # ------------------------------------------------------------ 8. Chi tiết
    def view_detail(self) -> None:
        booking = self._ask_booking("Mã đặt phòng")
        show_booking_detail(self._hotel, booking)
        if booking.status != BookingStatus.CANCELLED and confirm("Xem hóa đơn?"):
            print(self._hotel.build_invoice(booking.booking_id).render())

    # ----------------------------------------------------------- 9. Tìm kiếm
    def search_bookings(self) -> None:
        bookings = self._hotel.bookings
        choice = ask_choice("Tìm theo", {
            "1": "Mã đặt phòng (chính xác)", "2": "Khách hàng (mã hoặc tên gần đúng)",
            "3": "Trạng thái", "4": "Ngày lưu trú (khách đang ở vào ngày)",
            "5": "Mã phòng"})
        if choice == "1":
            booking_id = ask("Nhập mã đặt phòng")
            found = bookings.find(booking_id)
            show_bookings(self._hotel, [found] if found else [],
                          title=f"Kết quả tìm mã '{booking_id.upper()}'",
                          empty=f"Không tìm thấy đặt phòng có mã '{booking_id.upper()}'.")
        elif choice == "2":
            keyword = ask("Nhập mã hoặc tên khách")
            show_bookings(self._hotel, bookings.sort_bookings(
                "check_in", bookings=bookings.search_by_guest(keyword)),
                title=f"Đặt phòng của khách '{keyword}'", empty="Không tìm thấy đặt phòng phù hợp.")
        elif choice == "3":
            options = {str(i): s.label for i, s in enumerate(BookingStatus, start=1)}
            status = list(BookingStatus)[int(ask_choice("Trạng thái", options)) - 1]
            show_bookings(self._hotel, bookings.sort_bookings(
                "check_in", bookings=bookings.search_by_status(status)),
                title=f"Đặt phòng '{status.label}'", empty="Không có đặt phòng ở trạng thái này.")
        elif choice == "4":
            day = ask_date("Ngày", default=self._hotel.today())
            show_bookings(self._hotel, bookings.bookings_on(day),
                          title=f"Khách lưu trú ngày {format_date(day)}",
                          empty="Không có khách lưu trú vào ngày này.")
        else:
            room_id = ask("Nhập mã phòng")
            show_bookings(self._hotel, bookings.sort_bookings(
                "check_in", bookings=bookings.search_by_room(room_id)),
                title=f"Đặt phòng của phòng {room_id.upper()}",
                empty="Phòng này chưa có đặt phòng nào.")

    # ----------------------------------------------------------- 10. Sắp xếp
    def sort_bookings(self) -> None:
        bookings = self._hotel.bookings
        keys = list(bookings.SORT_KEYS)
        options = {str(i): bookings.SORT_KEYS[k][0] for i, k in enumerate(keys, start=1)}
        criterion = keys[int(ask_choice("Sắp xếp theo", options)) - 1]
        reverse = ask_sort_order()
        show_bookings(self._hotel, bookings.sort_bookings(criterion, reverse),
                      title=f"Đặt phòng sắp xếp theo {bookings.SORT_KEYS[criterion][0].lower()} "
                            f"({'giảm dần' if reverse else 'tăng dần'})",
                      empty="Chưa có đặt phòng nào để sắp xếp.")
