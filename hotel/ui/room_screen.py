"""Màn hình Quản lý phòng."""

from datetime import timedelta

from hotel.models.booking import Booking
from hotel.models.enums import Permission, RoomStatus
from hotel.models.room import DeluxeRoom, RoomFactory, StandardRoom, SuiteRoom
from hotel.ui.base_screen import BaseScreen
from hotel.ui.menu import MenuItem
from hotel.ui.views import ROOM_HEADERS, show_rooms
from hotel.utils.exceptions import BusinessRuleError, ValidationError
from hotel.utils.formatter import (format_date, format_money, print_info, print_success,
                                   print_table, print_warning)
from hotel.utils.input_helper import (ask, ask_choice, ask_date, ask_float, ask_int,
                                      ask_sort_order, confirm)
from hotel.utils.validators import (validate_id, validate_non_negative_money,
                                    validate_positive_money, validate_required,
                                    validate_room_number)

ROOM_TYPE_OPTIONS = {"1": "standard", "2": "deluxe", "3": "suite"}
ROOM_TYPE_MENU = {"1": "Tiêu chuẩn (Standard)", "2": "Cao cấp (Deluxe)", "3": "Suite"}


class RoomScreen(BaseScreen):
    """Thêm, cập nhật, xóa, hiển thị, tìm kiếm, sắp xếp phòng."""

    TITLE = "Quản lý phòng"

    def menu_items(self) -> list[MenuItem]:
        return [
            MenuItem("1", "Thêm phòng", self.add_room, Permission.MANAGE_ROOMS),
            MenuItem("2", "Cập nhật phòng", self.update_room, Permission.MANAGE_ROOMS),
            MenuItem("3", "Xóa phòng", self.delete_room, Permission.MANAGE_ROOMS),
            MenuItem("4", "Hiển thị danh sách phòng", self.list_rooms),
            MenuItem("5", "Tìm kiếm phòng", self.search_rooms),
            MenuItem("6", "Sắp xếp phòng", self.sort_rooms),
            MenuItem("7", "Tra cứu phòng trống theo khoảng ngày", self.find_available),
            MenuItem("8", "Minh họa đa hình: tính tiền N đêm cho mọi loại phòng",
                     self.polymorphism_demo),
        ]

    # ------------------------------------------------------------------ nhập
    def _unique_number(self, exclude_id: str | None = None):
        rooms = self._hotel.rooms

        def validator(raw: str) -> str:
            number = validate_room_number(raw)
            other = rooms.find_by_number(number)
            if other and other.room_id != exclude_id:
                raise ValidationError(f"Số phòng {number} đã được dùng cho phòng {other.room_id}.")
            return number
        return validator

    # ---------------------------------------------------------------- 1. Thêm
    def add_room(self) -> None:
        print_info("Thêm phòng mới (gõ 'q' để hủy).")
        type_key = ROOM_TYPE_OPTIONS[ask_choice("Chọn loại phòng", ROOM_TYPE_MENU)]
        room_id = self.ask_new_id(self._hotel.rooms, "Mã phòng", "R",
                                  lambda s: validate_id(s, "Mã phòng"))
        number = ask("Số phòng (3–4 chữ số)", validator=self._unique_number())
        price = ask("Giá phòng/đêm (VNĐ)",
                    validator=lambda s: validate_positive_money(s, "Giá phòng/đêm"))
        status = RoomStatus.MAINTENANCE if ask_choice(
            "Trạng thái ban đầu", {"1": "Trống", "2": "Bảo trì"}, default="1") == "2" \
            else RoomStatus.AVAILABLE
        if type_key == "standard":
            service = ask("Dịch vụ cơ bản miễn phí", default=StandardRoom.DEFAULT_BASIC_SERVICE,
                          validator=lambda s: validate_required(s, "Dịch vụ cơ bản"))
            room = StandardRoom(room_id, number, price, status, service)
        else:
            fee = ask("Phụ phí dịch vụ cao cấp/đêm (VNĐ)",
                      validator=lambda s: validate_non_negative_money(s, "Phụ phí"))
            if type_key == "deluxe":
                room = DeluxeRoom(room_id, number, price, status, fee)
            else:
                butler = ask("Phí quản gia/lượt ở (VNĐ)",
                             validator=lambda s: validate_non_negative_money(s, "Phí quản gia"))
                room = SuiteRoom(room_id, number, price, status, fee, butler)
        self._hotel.add_room(room)
        print_success(f"Đã thêm phòng {room.room_number} ({room.room_id}).")
        show_rooms([room], title="Phòng vừa thêm")

    # ----------------------------------------------------------- 2. Cập nhật
    def update_room(self) -> None:
        room = self.ask_existing(self._hotel.rooms, "Nhập mã phòng cần cập nhật")
        show_rooms([room], title="Thông tin hiện tại")
        print_info("Nhấn Enter để giữ nguyên giá trị trong [ ]; gõ 'q' để hủy.")
        changes: dict = {}
        number = ask("Số phòng", default=room.room_number,
                     validator=self._unique_number(room.room_id))
        if number != room.room_number:
            changes["room_number"] = number
        price = ask("Giá phòng/đêm", default=room.price_per_night,
                    show_default=format_money(room.price_per_night),
                    validator=lambda s: validate_positive_money(s, "Giá phòng/đêm"))
        if price != room.price_per_night:
            changes["price_per_night"] = price
        if room.status == RoomStatus.OCCUPIED:
            print_warning("Phòng đang có khách nên không thể đổi trạng thái.")
        else:
            current = "2" if room.status == RoomStatus.MAINTENANCE else "1"
            status = ask_choice("Trạng thái", {"1": "Trống", "2": "Bảo trì"}, default=current)
            if status != current:
                changes["status"] = (RoomStatus.MAINTENANCE if status == "2"
                                     else RoomStatus.AVAILABLE).value
        if isinstance(room, StandardRoom):
            service = ask("Dịch vụ cơ bản", default=room.basic_service,
                          validator=lambda s: validate_required(s, "Dịch vụ cơ bản"))
            if service != room.basic_service:
                changes["basic_service"] = service
        if isinstance(room, DeluxeRoom):  # gồm cả SuiteRoom (lớp con)
            fee = ask("Phụ phí dịch vụ/đêm", default=room.extra_service_fee,
                      show_default=format_money(room.extra_service_fee),
                      validator=lambda s: validate_non_negative_money(s, "Phụ phí"))
            if fee != room.extra_service_fee:
                changes["extra_service_fee"] = fee
        if isinstance(room, SuiteRoom):
            butler = ask("Phí quản gia/lượt", default=room.butler_fee,
                         show_default=format_money(room.butler_fee),
                         validator=lambda s: validate_non_negative_money(s, "Phí quản gia"))
            if butler != room.butler_fee:
                changes["butler_fee"] = butler
        if not changes:
            print_warning("Không có thay đổi nào.")
            return
        updated, warnings = self._hotel.update_room(room.room_id, **changes)
        print_success(f"Đã cập nhật phòng {updated.room_id}.")
        for warning in warnings:
            print_warning(warning)
        show_rooms([updated], title="Thông tin sau khi cập nhật")

    # ---------------------------------------------------------------- 3. Xóa
    def delete_room(self) -> None:
        room = self.ask_existing(self._hotel.rooms, "Nhập mã phòng cần xóa")
        show_rooms([room], title="Phòng sẽ bị xóa")
        active = self._hotel.bookings.active_for_room(room.room_id)
        if active:
            print_warning(f"Phòng còn {len(active)} đặt phòng hiệu lực – hệ thống sẽ từ chối xóa.")
        if not confirm(f"Bạn chắc chắn muốn xóa phòng {room.room_number}?"):
            print_warning("Đã hủy xóa.")
            return
        self._hotel.delete_room(room.room_id)
        print_success(f"Đã xóa phòng {room.room_number} ({room.room_id}).")

    # ----------------------------------------------------------- 4. Hiển thị
    def list_rooms(self) -> None:
        show_rooms(self._hotel.rooms.sort_rooms("number"),
                   empty="Chưa có phòng nào trong hệ thống.")

    # ----------------------------------------------------------- 5. Tìm kiếm
    def search_rooms(self) -> None:
        rooms = self._hotel.rooms
        choice = ask_choice("Tìm theo", {
            "1": "Mã phòng (chính xác)", "2": "Loại phòng", "3": "Khoảng giá",
            "4": "Trạng thái", "5": "Số phòng (gần đúng)",
            "6": "Kết hợp nhiều tiêu chí cùng lúc"})
        if choice == "1":
            room_id = ask("Nhập mã phòng")
            room = rooms.find(room_id)
            show_rooms([room] if room else [], title=f"Kết quả tìm mã '{room_id.upper()}'",
                       empty=f"Không tìm thấy phòng có mã '{room_id.upper()}'.")
        elif choice == "2":
            type_key = ROOM_TYPE_OPTIONS[ask_choice("Loại phòng", ROOM_TYPE_MENU)]
            show_rooms(rooms.sort_rooms("number", rooms=rooms.search_by_type(type_key)),
                       title=f"Phòng loại {RoomFactory.type_label(type_key)}",
                       empty="Không có phòng thuộc loại này.")
        elif choice == "3":
            low = ask_float("Giá thấp nhất", min_value=0, allow_equal_min=True)
            high = ask_float("Giá cao nhất", min_value=0, allow_equal_min=True)
            if low > high:
                print_warning("Giá thấp nhất lớn hơn giá cao nhất – đã tự hoán đổi.")
            show_rooms(rooms.sort_rooms("price", rooms=rooms.search_by_price(low, high)),
                       title=f"Phòng giá từ {format_money(min(low, high))} "
                             f"đến {format_money(max(low, high))}",
                       empty="Không có phòng trong khoảng giá này.")
        elif choice == "4":
            options = {str(i): s.label for i, s in enumerate(RoomStatus, start=1)}
            status = list(RoomStatus)[int(ask_choice("Trạng thái", options)) - 1]
            show_rooms(rooms.sort_rooms("number", rooms=rooms.search_by_status(status)),
                       title=f"Phòng có trạng thái '{status.label}'",
                       empty="Không có phòng ở trạng thái này.")
        elif choice == "5":
            keyword = ask("Nhập một phần số phòng")
            show_rooms(rooms.sort_rooms("number", rooms=rooms.search_by_number(keyword)),
                       title=f"Phòng có số chứa '{keyword}'",
                       empty="Không tìm thấy phòng phù hợp.")
        else:
            self._search_combined()

    def _search_combined(self) -> None:
        """Tìm kết hợp nhiều tiêu chí: nhấn Enter để bỏ qua tiêu chí không dùng."""
        rooms = self._hotel.rooms
        print_info("Kết hợp nhiều tiêu chí – nhấn Enter để bỏ qua tiêu chí không dùng.")
        type_choice = ask_choice("Loại phòng", {"0": "Tất cả", **ROOM_TYPE_MENU}, default="0")
        room_type = None if type_choice == "0" else ROOM_TYPE_OPTIONS[type_choice]

        def ask_price(prompt: str):
            value = ask(prompt, required=False,
                        validator=lambda raw: validate_non_negative_money(raw, "Giá"))
            return None if value == "" else value
        low = ask_price("Giá thấp nhất (Enter = bỏ qua)")
        high = ask_price("Giá cao nhất (Enter = bỏ qua)")
        status_options = {"0": "Tất cả", **{str(i): s.label for i, s in enumerate(RoomStatus, start=1)}}
        status_choice = ask_choice("Trạng thái", status_options, default="0")
        status = None if status_choice == "0" else list(RoomStatus)[int(status_choice) - 1]
        keyword = ask("Số phòng chứa (Enter = bỏ qua)", required=False)
        found = rooms.search(room_type=room_type, min_price=low, max_price=high, status=status,
                             number_keyword=keyword or None)
        show_rooms(rooms.sort_rooms("number", rooms=found), title="Kết quả tìm kết hợp",
                   empty="Không có phòng nào thỏa các tiêu chí đã chọn.")

    # ----------------------------------------------------------- 6. Sắp xếp
    def sort_rooms(self) -> None:
        rooms = self._hotel.rooms
        keys = list(rooms.SORT_KEYS)
        options = {str(i): rooms.SORT_KEYS[k][0] for i, k in enumerate(keys, start=1)}
        criterion = keys[int(ask_choice("Sắp xếp theo", options)) - 1]
        reverse = ask_sort_order()
        order = "giảm dần" if reverse else "tăng dần"
        show_rooms(rooms.sort_rooms(criterion, reverse),
                   title=f"Phòng sắp xếp theo {rooms.SORT_KEYS[criterion][0].lower()} ({order})",
                   empty="Chưa có phòng nào để sắp xếp.")

    # ------------------------------------------------------ 7. Phòng trống
    def find_available(self) -> None:
        today = self._hotel.today()
        check_in = ask_date("Ngày nhận phòng", default=today)
        check_out = ask_date("Ngày trả phòng", default=check_in + timedelta(days=1))
        if check_in < today:  # giống màn Tạo đặt phòng: không tra cứu ngày nhận ở quá khứ
            raise BusinessRuleError(
                f"Ngày nhận phòng ({format_date(check_in)}) không được ở quá khứ.")
        rooms = self._hotel.bookings.available_rooms(check_in, check_out)
        nights = Booking.count_nights(check_in, check_out)
        ordered = self._hotel.rooms.sort_rooms("number", rooms=rooms)
        rows = [room.to_row() + [format_money(room.calculate_cost(nights))] for room in ordered]
        print_table(ROOM_HEADERS + [f"Tạm tính {nights} đêm"], rows,
                    title=f"Phòng có thể đặt ({nights} đêm) – tạm tính chưa gồm giảm giá và dịch vụ",
                    empty_message="Không còn phòng trống trong khoảng thời gian này.")

    # -------------------------------------------------------- 8. Đa hình
    def polymorphism_demo(self) -> None:
        """Gọi cùng một phương thức ``calculate_cost`` trên các lớp phòng khác nhau."""
        nights = ask_int("Số đêm (0 = nhận/trả trong ngày, tính 1 đêm)",
                         min_value=0, max_value=365, default=3)
        rows = []
        for room in self._hotel.rooms.sort_rooms("number"):
            formula = " + ".join(f"{label}" for label, _ in room.cost_breakdown(nights))
            rows.append([room.room_number, type(room).__name__, room.get_room_type(),
                         formula, format_money(room.calculate_cost(nights))])
        print_table(["Phòng", "Lớp Python", "Loại", "Cách tính (cost_breakdown)",
                     "calculate_cost()"], rows,
                    title=f"ĐA HÌNH: room.calculate_cost({nights}) trên từng loại phòng",
                    empty_message="Chưa có phòng nào.")
