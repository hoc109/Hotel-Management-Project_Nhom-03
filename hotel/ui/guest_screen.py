"""Màn hình Quản lý khách hàng."""

from hotel.models.enums import BookingStatus, Permission
from hotel.models.guest import Guest
from hotel.ui.base_screen import BaseScreen
from hotel.ui.menu import MenuItem
from hotel.ui.views import show_bookings, show_guests
from hotel.utils.exceptions import ValidationError
from hotel.utils.formatter import format_money, print_info, print_success, print_warning
from hotel.utils.input_helper import ask, ask_choice, ask_sort_order, confirm
from hotel.utils.validators import validate_id, validate_id_card, validate_name, validate_phone


class GuestScreen(BaseScreen):
    """Thêm, cập nhật, xóa, hiển thị, tìm kiếm, sắp xếp khách hàng."""

    TITLE = "Quản lý khách hàng"

    def menu_items(self) -> list[MenuItem]:
        p = Permission.MANAGE_GUESTS
        return [
            MenuItem("1", "Thêm khách hàng", self.add_guest, p),
            MenuItem("2", "Cập nhật khách hàng", self.update_guest, p),
            MenuItem("3", "Xóa khách hàng", self.delete_guest, p),
            MenuItem("4", "Hiển thị danh sách khách hàng", self.list_guests, p),
            MenuItem("5", "Tìm kiếm khách hàng", self.search_guests, p),
            MenuItem("6", "Sắp xếp khách hàng", self.sort_guests, p),
            MenuItem("7", "Lịch sử lưu trú của khách", self.guest_history, p),
        ]

    def _unique_id_card(self, exclude_id: str | None = None):
        guests = self._hotel.guests

        def validator(raw: str) -> str:
            card = validate_id_card(raw)
            for g in guests.list_all():
                if card and g.id_card == card and g.guest_id != exclude_id:
                    raise ValidationError(f"CCCD/Hộ chiếu đã thuộc về khách {g.guest_id}.")
            return card
        return validator

    def add_guest(self) -> None:
        print_info("Thêm khách hàng mới (gõ 'q' để hủy).")
        guest_id = self.ask_new_id(self._hotel.guests, "Mã khách hàng", "G",
                                   lambda s: validate_id(s, "Mã khách hàng"))
        name = ask("Họ tên", validator=validate_name)
        phone = ask("Số điện thoại (10 số, bắt đầu bằng 0)", validator=validate_phone)
        card = ask("CCCD/Hộ chiếu (Enter để bỏ qua)", required=False,
                   validator=self._unique_id_card())
        guest = self._hotel.add_guest(Guest(guest_id, name, phone, card))
        print_success(f"Đã thêm khách hàng {guest.full_name} ({guest.guest_id}).")
        show_guests([guest], title="Khách hàng vừa thêm")

    def update_guest(self) -> None:
        guest = self.ask_existing(self._hotel.guests, "Nhập mã khách hàng cần cập nhật")
        show_guests([guest], title="Thông tin hiện tại")
        print_info("Nhấn Enter để giữ nguyên giá trị trong [ ]; gõ 'q' để hủy.")
        changes = {}
        name = ask("Họ tên", default=guest.full_name, validator=validate_name)
        if name != guest.full_name:
            changes["full_name"] = name
        phone = ask("Số điện thoại", default=guest.phone, validator=validate_phone)
        if phone != guest.phone:
            changes["phone"] = phone
        card = ask("CCCD/Hộ chiếu", default=guest.id_card, show_default=guest.id_card or "trống",
                   validator=self._unique_id_card(guest.guest_id))
        if card != guest.id_card:
            changes["id_card"] = card
        if not changes:
            print_warning("Không có thay đổi nào.")
            return
        updated = self._hotel.update_guest(guest.guest_id, **changes)
        print_success(f"Đã cập nhật khách hàng {updated.guest_id}.")
        show_guests([updated], title="Thông tin sau khi cập nhật")

    def delete_guest(self) -> None:
        guest = self.ask_existing(self._hotel.guests, "Nhập mã khách hàng cần xóa")
        show_guests([guest], title="Khách hàng sẽ bị xóa")
        if self._hotel.bookings.active_for_guest(guest.guest_id):
            print_warning("Khách còn đặt phòng hiệu lực – hệ thống sẽ từ chối xóa.")
        if not confirm(f"Bạn chắc chắn muốn xóa khách {guest.full_name}?"):
            print_warning("Đã hủy xóa.")
            return
        self._hotel.delete_guest(guest.guest_id)
        print_success(f"Đã xóa khách hàng {guest.full_name} ({guest.guest_id}).")

    def list_guests(self) -> None:
        show_guests(self._hotel.guests.sort_guests("id"),
                    empty="Chưa có khách hàng nào trong hệ thống.")

    def search_guests(self) -> None:
        guests = self._hotel.guests
        choice = ask_choice("Tìm theo", {"1": "Mã khách hàng (chính xác)",
                                          "2": "Họ tên (gần đúng, không dấu cũng được)",
                                          "3": "Số điện thoại (gần đúng)"})
        if choice == "1":
            guest_id = ask("Nhập mã khách hàng")
            guest = guests.find(guest_id)
            show_guests([guest] if guest else [], title=f"Kết quả tìm mã '{guest_id.upper()}'",
                        empty=f"Không tìm thấy khách hàng có mã '{guest_id.upper()}'.")
        elif choice == "2":
            keyword = ask("Nhập một phần họ tên")
            show_guests(guests.search_by_name(keyword), title=f"Khách có tên chứa '{keyword}'",
                        empty="Không tìm thấy khách hàng phù hợp.")
        else:
            keyword = ask("Nhập một phần số điện thoại")
            show_guests(guests.search_by_phone(keyword), title=f"Khách có SĐT chứa '{keyword}'",
                        empty="Không tìm thấy khách hàng phù hợp.")

    def sort_guests(self) -> None:
        guests = self._hotel.guests
        keys = list(guests.SORT_KEYS)
        options = {str(i): guests.SORT_KEYS[k][0] for i, k in enumerate(keys, start=1)}
        criterion = keys[int(ask_choice("Sắp xếp theo", options)) - 1]
        reverse = ask_sort_order()
        show_guests(guests.sort_guests(criterion, reverse),
                    title=f"Khách hàng sắp xếp theo {guests.SORT_KEYS[criterion][0].lower()} "
                          f"({'giảm dần' if reverse else 'tăng dần'})",
                    empty="Chưa có khách hàng nào để sắp xếp.")

    def guest_history(self) -> None:
        guest = self.ask_existing(self._hotel.guests, "Nhập mã khách hàng")
        history = self._hotel.bookings.history_of_guest(guest.guest_id)
        show_bookings(self._hotel, history, title=f"LỊCH SỬ LƯU TRÚ – {guest.full_name}",
                      empty="Khách chưa có lượt đặt phòng nào.")
        done = [b for b in history if b.status == BookingStatus.CHECKED_OUT]
        print(f"Số lượt đã trả phòng: {len(done)} – Tổng chi tiêu: "
              f"{format_money(sum(b.amount_due for b in done))}")
        if len(done) >= 3:
            print_success("Khách thân thiết: được giảm thêm 5% tiền phòng cho lượt tiếp theo.")
