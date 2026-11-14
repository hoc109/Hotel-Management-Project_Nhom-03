"""Thống kê, báo cáo và xuất CSV."""

import csv
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from hotel.managers.booking_manager import BookingManager
from hotel.managers.guest_manager import GuestManager
from hotel.managers.room_manager import RoomManager
from hotel.models.booking import Booking
from hotel.models.enums import BookingStatus, RoomStatus
from hotel.utils.exceptions import ValidationError
from hotel.utils.formatter import format_date


class ReportManager:
    """Tổng hợp số liệu từ các manager khác (chỉ đọc, không sửa dữ liệu)."""

    def __init__(self, rooms: RoomManager, guests: GuestManager, bookings: BookingManager,
                 today_provider: Callable[[], date] = date.today) -> None:
        self.__rooms = rooms
        self.__guests = guests
        self.__bookings = bookings
        self.__today = today_provider

    # ------------------------------------------------------------ doanh thu
    def completed_bookings(self, start: date | None = None,
                           end: date | None = None) -> list[Booking]:
        """Các lượt đã trả phòng, lọc theo ngày trả thực tế trong [start, end]."""
        if start and end and start > end:
            raise ValidationError("Ngày bắt đầu không được sau ngày kết thúc.")
        result = []
        for b in self.__bookings.search_by_status(BookingStatus.CHECKED_OUT):
            day = b.checked_out_on or b.check_out
            if (start is None or day >= start) and (end is None or day <= end):
                result.append(b)
        return sorted(result, key=lambda b: (b.checked_out_on or b.check_out, b.booking_id))

    def total_revenue(self, start: date | None = None, end: date | None = None) -> dict:
        """Doanh thu tổng: tiền phòng, giảm giá, dịch vụ, thực thu."""
        items = self.completed_bookings(start, end)
        room = sum(b.room_cost for b in items)
        discount = sum(b.discount_amount for b in items)
        service = sum(b.service_total for b in items)
        return {"count": len(items), "room": room, "discount": discount,
                "service": service, "total": room - discount + service}

    def revenue_by_room_type(self, start: date | None = None,
                             end: date | None = None) -> list[tuple[str, int, float]]:
        """Doanh thu theo loại phòng: (loại, số lượt, thực thu)."""
        groups: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
        for b in self.completed_bookings(start, end):
            groups[b.room_type][0] += 1
            groups[b.room_type][1] += b.amount_due
        return sorted(((k, int(v[0]), v[1]) for k, v in groups.items()),
                      key=lambda row: row[2], reverse=True)

    def revenue_by_month(self, year: int | None = None) -> list[tuple[str, int, float]]:
        """Doanh thu theo tháng (theo ngày trả phòng): (MM/YYYY, số lượt, thực thu)."""
        groups: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0, 0.0])
        for b in self.completed_bookings():
            day = b.checked_out_on or b.check_out
            if year is None or day.year == year:
                groups[(day.year, day.month)][0] += 1
                groups[(day.year, day.month)][1] += b.amount_due
        return [(f"{m:02d}/{y}", int(v[0]), v[1]) for (y, m), v in sorted(groups.items())]

    # ------------------------------------------------------------ công suất
    def occupancy(self) -> dict:
        """Tỷ lệ phòng đang sử dụng.

        * ``rate_total``: phòng Đang ở / tổng số phòng.
        * ``rate_operating``: phòng Đang ở / số phòng đang kinh doanh (trừ bảo trì).
        """
        rooms = self.__rooms.list_all()
        total = len(rooms)
        occupied = sum(1 for r in rooms if r.status == RoomStatus.OCCUPIED)
        maintenance = sum(1 for r in rooms if r.status == RoomStatus.MAINTENANCE)
        available = total - occupied - maintenance
        operating = total - maintenance
        return {
            "total": total, "occupied": occupied, "maintenance": maintenance,
            "available": available,
            "rate_total": occupied / total if total else 0.0,
            "rate_operating": occupied / operating if operating else 0.0,
        }

    def occupancy_by_type(self) -> list[tuple[str, int, int, float]]:
        """Tỷ lệ sử dụng theo loại phòng: (loại, đang ở, tổng, tỷ lệ)."""
        groups: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for r in self.__rooms.list_all():
            groups[r.get_room_type()][1] += 1
            if r.status == RoomStatus.OCCUPIED:
                groups[r.get_room_type()][0] += 1
        return [(k, v[0], v[1], v[0] / v[1]) for k, v in sorted(groups.items())]

    def bookings_on(self, day: date, mode: str = "staying") -> list[Booking]:
        return self.__bookings.bookings_on(day, mode)

    # -------------------------------------------------------------- xuất CSV
    EXPORT_KINDS = {
        "rooms": "Danh sách phòng",
        "bookings": "Danh sách đặt phòng",
        "revenue": "Doanh thu theo lượt trả phòng",
    }

    def export_csv(self, kind: str, directory: str | Path) -> Path:
        """Xuất CSV (UTF-8 có BOM để mở bằng Excel không lỗi font)."""
        if kind not in self.EXPORT_KINDS:
            raise ValidationError(f"Loại báo cáo '{kind}' không hợp lệ.")
        headers, rows = getattr(self, f"_csv_{kind}")()
        folder = Path(directory)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{kind}_{datetime.now():%Y%m%d_%H%M%S}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)
        return path

    def _guest_name(self, guest_id: str) -> str:
        guest = self.__guests.find(guest_id)
        return guest.full_name if guest else guest_id

    def _csv_rooms(self) -> tuple[list[str], list[list]]:
        headers = ["Mã phòng", "Số phòng", "Loại", "Giá/đêm", "Trạng thái", "Ghi chú"]
        rows = [[r.room_id, r.room_number, r.get_room_type(), round(r.price_per_night),
                 r.status.label, r.get_extra_info()]
                for r in self.__rooms.sort_rooms("number")]
        return headers, rows

    def _csv_bookings(self) -> tuple[list[str], list[list]]:
        headers = ["Mã đặt phòng", "Mã khách", "Tên khách", "Mã phòng", "Số phòng", "Loại",
                   "Ngày nhận", "Ngày trả", "Số đêm", "Trạng thái", "Tiền phòng",
                   "Giảm giá", "Dịch vụ", "Tổng tiền"]
        rows = [[b.booking_id, b.guest_id, self._guest_name(b.guest_id), b.room_id,
                 b.room_number, b.room_type, format_date(b.check_in), format_date(b.check_out),
                 b.nights, b.status.label, round(b.room_cost), round(b.discount_amount),
                 round(b.service_total), round(b.amount_due)]
                for b in self.__bookings.sort_bookings("check_in")]
        return headers, rows

    def _csv_revenue(self) -> tuple[list[str], list[list]]:
        headers = ["Ngày trả", "Mã đặt phòng", "Tên khách", "Số phòng", "Loại", "Số đêm",
                   "Tiền phòng", "Giảm giá", "Dịch vụ", "Thực thu"]
        rows = [[format_date(b.checked_out_on or b.check_out), b.booking_id,
                 self._guest_name(b.guest_id), b.room_number, b.room_type, b.nights,
                 round(b.room_cost), round(b.discount_amount), round(b.service_total),
                 round(b.amount_due)]
                for b in self.completed_bookings()]
        summary = self.total_revenue()
        rows.append(["TỔNG", "", "", "", "", "", round(summary["room"]),
                     round(summary["discount"]), round(summary["service"]),
                     round(summary["total"])])
        return headers, rows
