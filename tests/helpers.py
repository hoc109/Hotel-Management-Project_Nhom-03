"""Tiện ích dùng chung cho các test: tạo HotelManager trong thư mục tạm, ngày cố định."""

import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hotel.managers.hotel_manager import HotelManager  # noqa: E402
from hotel.models import DeluxeRoom, Guest, RoomStatus, Service, StandardRoom, SuiteRoom  # noqa: E402


class HotelTestCase(unittest.TestCase):
    """Mỗi test có một HotelManager riêng, dữ liệu rỗng, "hôm nay" cố định = 10/01/2026."""

    TODAY = date(2026, 1, 10)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.today = self.TODAY
        self.hotel = self.make_hotel()
        self.hotel.load(seed_if_empty=False)   # chỉ tạo tài khoản mặc định
        self.hotel.login("admin", "admin123")

    def make_hotel(self) -> HotelManager:
        return HotelManager(data_dir=self.base / "data", invoice_dir=self.base / "invoices",
                            export_dir=self.base / "exports", today_provider=lambda: self.today)

    def d(self, offset: int) -> date:
        """Ngày lệch ``offset`` ngày so với hôm nay."""
        return self.TODAY + timedelta(days=offset)

    def add_basic_data(self) -> None:
        """3 loại phòng + 1 phòng bảo trì, 2 khách, 1 dịch vụ."""
        h = self.hotel
        h.add_room(StandardRoom("R001", "101", 500_000))
        h.add_room(DeluxeRoom("R002", "201", 1_000_000, extra_service_fee=200_000))
        h.add_room(SuiteRoom("R003", "301", 2_000_000, extra_service_fee=300_000,
                             butler_fee=500_000))
        h.add_room(StandardRoom("R004", "102", 450_000, RoomStatus.MAINTENANCE))
        h.add_guest(Guest("G001", "Nguyễn Văn An", "0901234567", "001090012345"))
        h.add_guest(Guest("G002", "Trần Thị Bình", "0912345678"))
        h.add_service(Service("S001", "Minibar", 50_000))
