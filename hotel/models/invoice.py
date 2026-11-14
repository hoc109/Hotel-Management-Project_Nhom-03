"""Hóa đơn thanh toán khi trả phòng (chức năng mở rộng)."""

from datetime import datetime
from pathlib import Path

from hotel.models.booking import Booking
from hotel.models.guest import Guest
from hotel.models.room import Room
from hotel.utils.formatter import format_date, format_money, format_percent

HOTEL_NAME = "KHÁCH SẠN PYTHON HOTEL"
WIDTH = 64


class Invoice:
    """Tạo nội dung hóa đơn dạng văn bản và lưu ra file ``.txt``."""

    def __init__(self, booking: Booking, guest: Guest | None, room: Room | None,
                 discount_details: list[tuple[str, float]] | None = None,
                 issued_at: datetime | None = None) -> None:
        self.__booking = booking
        self.__guest = guest
        self.__room = room
        self.__discount_details = discount_details or []
        self.__issued_at = issued_at or datetime.now()

    @property
    def invoice_id(self) -> str:
        return f"INV-{self.__booking.booking_id}"

    @staticmethod
    def _line(label: str, amount: float) -> str:
        """Một dòng: nhãn bên trái, số tiền căn phải."""
        money = format_money(amount)
        return f"{label:<{WIDTH - len(money) - 1}} {money}"

    def render(self) -> str:
        """Trả về toàn bộ nội dung hóa đơn."""
        b = self.__booking
        sep, thin = "=" * WIDTH, "-" * WIDTH
        guest_name = self.__guest.full_name if self.__guest else b.guest_id
        guest_phone = self.__guest.phone if self.__guest else "-"
        lines = [
            sep,
            HOTEL_NAME.center(WIDTH),
            "HÓA ĐƠN THANH TOÁN".center(WIDTH),
            sep,
            f"Số hóa đơn : {self.invoice_id}",
            f"Ngày lập   : {self.__issued_at.strftime('%d/%m/%Y %H:%M')}",
            f"Khách hàng : {guest_name} ({b.guest_id}) - SĐT: {guest_phone}",
            f"Phòng      : {b.room_number} ({b.room_id}) - Loại: {b.room_type}",
            f"Lưu trú    : {format_date(b.check_in)} → {format_date(b.check_out)} ({b.nights} đêm)",
            thin,
            "TIỀN PHÒNG",
        ]
        # Đa hình: mỗi loại phòng tự liệt kê các khoản tiền của mình.
        # Nếu giá phòng đã đổi sau khi đặt thì chỉ in tổng tiền đã chốt.
        breakdown = self.__room.cost_breakdown(b.nights) if self.__room else []
        if abs(sum(amount for _, amount in breakdown) - b.room_cost) > 0.5:
            breakdown = [(f"Tiền phòng {b.nights} đêm (giá chốt khi đặt)", b.room_cost)]
        lines += [self._line(f"  {label}", amount) for label, amount in breakdown]
        lines.append(self._line("  Cộng tiền phòng", b.room_cost))
        if b.discount_amount > 0:
            for name, rate in self.__discount_details:
                lines.append(f"  - {name}: {format_percent(rate)}")
            lines.append(self._line(f"  Giảm giá ({format_percent(b.discount_rate)})",
                                    -b.discount_amount))
        lines += [thin, "DỊCH VỤ PHÁT SINH"]
        if b.services:
            for usage in b.services:
                label = (f"  {format_date(usage.used_on)} {usage.service_name} "
                         f"{usage.quantity} × {format_money(usage.unit_price)}")
                lines.append(self._line(label, usage.subtotal))
        else:
            lines.append("  (Không sử dụng dịch vụ)")
        lines.append(self._line("  Cộng dịch vụ", b.service_total))
        lines += [sep, self._line("TỔNG THANH TOÁN", b.amount_due), sep,
                  "Cảm ơn quý khách và hẹn gặp lại!".center(WIDTH)]
        return "\n".join(lines)

    def save(self, directory: str | Path) -> Path:
        """Lưu hóa đơn ra file ``<directory>/INV-<mã đặt phòng>.txt``."""
        folder = Path(directory)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{self.invoice_id}.txt"
        path.write_text(self.render(), encoding="utf-8")
        return path

    def __str__(self) -> str:
        return self.render()
