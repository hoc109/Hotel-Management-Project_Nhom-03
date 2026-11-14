"""Màn hình Thống kê & báo cáo."""

from hotel.models.enums import Permission
from hotel.ui.base_screen import BaseScreen
from hotel.ui.menu import MenuItem
from hotel.ui.views import show_bookings
from hotel.utils.formatter import (format_date, format_money, format_percent, print_success,
                                   print_table, print_warning)
from hotel.utils.input_helper import ask, ask_choice, ask_date
from hotel.utils.validators import validate_int


class ReportScreen(BaseScreen):
    """Doanh thu, tỷ lệ phòng đang sử dụng, đặt phòng theo ngày, xuất CSV."""

    TITLE = "Thống kê & báo cáo"

    def menu_items(self) -> list[MenuItem]:
        view = Permission.VIEW_REPORTS
        return [
            MenuItem("1", "Doanh thu tổng (toàn thời gian)", self.revenue_total, view),
            MenuItem("2", "Doanh thu theo khoảng ngày", self.revenue_range, view),
            MenuItem("3", "Doanh thu theo loại phòng", self.revenue_by_type, view),
            MenuItem("4", "Doanh thu theo tháng", self.revenue_by_month, view),
            MenuItem("5", "Tỷ lệ phòng đang sử dụng", self.occupancy, view),
            MenuItem("6", "Danh sách đặt phòng theo ngày", self.bookings_by_day, view),
            MenuItem("7", "Xuất báo cáo ra file CSV", self.export_csv, Permission.EXPORT_REPORTS),
        ]

    def _print_revenue(self, start=None, end=None, title="DOANH THU TIỀN PHÒNG") -> None:
        reports = self._hotel.reports
        summary = reports.total_revenue(start, end)
        if summary["count"] == 0:
            print_warning("Chưa có lượt trả phòng nào trong khoảng thời gian này – doanh thu = 0 đ.")
            return
        rows = []
        for b in reports.completed_bookings(start, end):
            guest = self._hotel.guests.find(b.guest_id)
            rows.append([format_date(b.checked_out_on or b.check_out), b.booking_id,
                         guest.full_name if guest else b.guest_id, b.room_number, b.room_type,
                         b.nights, format_money(b.room_cost), format_money(b.discount_amount),
                         format_money(b.service_total), format_money(b.amount_due)])
        print_table(["Ngày trả", "Mã ĐP", "Khách", "Phòng", "Loại", "Đêm", "Tiền phòng",
                     "Giảm giá", "Dịch vụ", "Thực thu"], rows, title=title)
        print_table(["Chỉ tiêu", "Giá trị"], [
            ["Số lượt trả phòng", summary["count"]],
            ["Tiền phòng", format_money(summary["room"])],
            ["Giảm giá", f"-{format_money(summary['discount'])}"],
            ["Tiền phòng sau giảm", format_money(summary["room"] - summary["discount"])],
            ["Dịch vụ phát sinh", format_money(summary["service"])],
            ["TỔNG DOANH THU", format_money(summary["total"])],
        ], title="TỔNG HỢP", show_count=False)

    def revenue_total(self) -> None:
        self._print_revenue()

    def revenue_range(self) -> None:
        start = ask_date("Từ ngày")
        end = ask_date("Đến ngày", default=self._hotel.today())
        if start > end:
            print_warning("Ngày bắt đầu sau ngày kết thúc – đã tự hoán đổi.")
            start, end = end, start
        self._print_revenue(start, end,
                            f"DOANH THU TỪ {format_date(start)} ĐẾN {format_date(end)}")

    def revenue_by_type(self) -> None:
        data = self._hotel.reports.revenue_by_room_type()
        total = sum(row[2] for row in data)
        rows = [[t, n, format_money(v), format_percent(v / total if total else 0)]
                for t, n, v in data]
        print_table(["Loại phòng", "Số lượt", "Doanh thu", "Tỷ trọng"], rows,
                    title="DOANH THU THEO LOẠI PHÒNG",
                    empty_message="Chưa có lượt trả phòng nào.")

    def revenue_by_month(self) -> None:
        raw = ask("Năm (Enter = tất cả)", required=False,
                  validator=lambda s: validate_int(s, "Năm", min_value=2000, max_value=2100))
        year = raw or None
        data = self._hotel.reports.revenue_by_month(year)
        print_table(["Tháng", "Số lượt", "Doanh thu"],
                    [[m, n, format_money(v)] for m, n, v in data],
                    title=f"DOANH THU THEO THÁNG{f' NĂM {year}' if year else ''}",
                    empty_message="Chưa có doanh thu.")

    def occupancy(self) -> None:
        o = self._hotel.reports.occupancy()
        if o["total"] == 0:
            print_warning("Chưa có phòng nào trong hệ thống.")
            return
        print_table(["Chỉ tiêu", "Giá trị"], [
            ["Tổng số phòng", o["total"]],
            ["Đang ở", o["occupied"]],
            ["Trống", o["available"]],
            ["Bảo trì", o["maintenance"]],
            ["Tỷ lệ sử dụng / tổng số phòng", format_percent(o["rate_total"])],
            ["Tỷ lệ sử dụng / phòng đang kinh doanh", format_percent(o["rate_operating"])],
        ], title=f"TỶ LỆ PHÒNG ĐANG SỬ DỤNG ({format_date(self._hotel.today())})", show_count=False)
        print_table(["Loại phòng", "Đang ở", "Tổng", "Tỷ lệ"],
                    [[t, occ, tot, format_percent(r)]
                     for t, occ, tot, r in self._hotel.reports.occupancy_by_type()],
                    title="Theo loại phòng")

    def bookings_by_day(self) -> None:
        day = ask_date("Ngày cần xem", default=self._hotel.today())
        mode = ask_choice("Kiểu danh sách", {"1": "Khách đang lưu trú trong ngày",
                                             "2": "Nhận phòng trong ngày",
                                             "3": "Trả phòng trong ngày"}, default="1")
        key, label = {"1": ("staying", "LƯU TRÚ"), "2": ("check_in", "NHẬN PHÒNG"),
                      "3": ("check_out", "TRẢ PHÒNG")}[mode]
        show_bookings(self._hotel, self._hotel.reports.bookings_on(day, key),
                      title=f"ĐẶT PHÒNG {label} NGÀY {format_date(day)}",
                      empty="Không có đặt phòng nào trong ngày này.")

    def export_csv(self) -> None:
        kinds = list(self._hotel.reports.EXPORT_KINDS)
        options = {str(i): self._hotel.reports.EXPORT_KINDS[k] for i, k in enumerate(kinds, 1)}
        options[str(len(kinds) + 1)] = "Tất cả"
        choice = int(ask_choice("Chọn báo cáo", options))
        selected = kinds if choice == len(kinds) + 1 else [kinds[choice - 1]]
        for kind in selected:
            path = self._hotel.export_csv(kind)
            print_success(f"Đã xuất {self._hotel.reports.EXPORT_KINDS[kind]}: {path}")
