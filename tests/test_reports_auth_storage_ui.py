"""Kiểm thử thống kê, phân quyền, lưu trữ JSON và giao diện nhập liệu/menu."""

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tests.helpers import HotelTestCase

from hotel.models import Permission, RoomStatus, StandardRoom
from hotel.ui.menu import Menu, MenuItem, MenuSignal
from hotel.utils.exceptions import (AuthenticationError, BusinessRuleError, InputCancelled,
                                    PermissionDeniedError)
from hotel.utils.input_helper import ask, ask_int, confirm
from hotel.utils.validators import validate_phone


class ReportTests(HotelTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.add_basic_data()
        h = self.hotel
        h.create_booking("B001", "G001", "R001", self.d(0), self.d(2))
        h.create_booking("B002", "G002", "R002", self.d(0), self.d(1))
        h.check_in("B001")
        h.check_in("B002")
        self.today = self.d(1)
        h.check_out("B002")

    def test_revenue(self):
        """TC24 – Doanh thu chỉ tính lượt đã trả phòng."""
        summary = self.hotel.reports.total_revenue()
        self.assertEqual((summary["count"], summary["total"]), (1, 1_200_000))
        self.assertEqual(self.hotel.reports.total_revenue(self.d(5), self.d(9))["total"], 0)
        self.assertEqual(self.hotel.reports.revenue_by_room_type(), [("Cao cấp", 1, 1_200_000)])
        self.assertEqual(self.hotel.reports.revenue_by_month(), [("01/2026", 1, 1_200_000)])

    def test_occupancy(self):
        """TC25 – Tỷ lệ phòng đang sử dụng (tổng và trừ phòng bảo trì)."""
        o = self.hotel.reports.occupancy()
        self.assertEqual((o["total"], o["occupied"], o["maintenance"]), (4, 1, 1))
        self.assertAlmostEqual(o["rate_total"], 0.25)
        self.assertAlmostEqual(o["rate_operating"], 1 / 3)

    def test_bookings_by_day(self):
        self.assertEqual([b.booking_id for b in self.hotel.reports.bookings_on(self.d(1))],
                         ["B001"])

    def test_export_csv(self):
        for kind in ("rooms", "bookings", "revenue"):
            path = self.hotel.export_csv(kind)
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))  # BOM cho Excel


class AuthTests(HotelTestCase):

    def test_wrong_password(self):
        with self.assertRaises(AuthenticationError):
            self.hotel.login("admin", "sai-mat-khau")

    def test_receptionist_cannot_manage_rooms(self):
        """TC26 – Lễ tân thêm phòng bị từ chối, nhưng được quản lý khách."""
        self.hotel.login("letan", "letan123")
        with self.assertRaises(PermissionDeniedError):
            self.hotel.add_room(StandardRoom("R001", "101", 500_000))
        with self.assertRaises(PermissionDeniedError):
            self.hotel.export_csv("rooms")
        self.assertTrue(self.hotel.can(Permission.MANAGE_GUESTS))

    def test_not_logged_in(self):
        self.hotel.logout()
        with self.assertRaises(PermissionDeniedError):
            self.hotel.add_room(StandardRoom("R001", "101", 500_000))

    def test_user_management_rules(self):
        with self.assertRaises(BusinessRuleError):
            self.hotel.delete_user("admin")              # đang đăng nhập
        self.hotel.add_user("receptionist", "nv01", "matkhau1", "Nhân Viên Một")
        self.hotel.delete_user("nv01")
        self.hotel.change_password("admin123", "newpass1")
        self.hotel.logout()
        self.hotel.login("admin", "newpass1")


class StorageTests(HotelTestCase):

    def test_persistence_round_trip(self):
        """TC27 – Dữ liệu được lưu và nạp lại đầy đủ."""
        self.add_basic_data()
        self.hotel.create_booking("B001", "G001", "R003", self.d(0), self.d(2))
        self.hotel.check_in("B001")
        reloaded = self.make_hotel()
        reloaded.load(seed_if_empty=False)
        self.assertEqual(len(reloaded.rooms), 4)
        self.assertEqual(reloaded.rooms.get("R003").to_dict(),
                         self.hotel.rooms.get("R003").to_dict())
        self.assertEqual(reloaded.bookings.get("B001").to_dict(),
                         self.hotel.bookings.get("B001").to_dict())
        self.assertEqual(reloaded.rooms.get("R003").status, RoomStatus.OCCUPIED)

    def test_corrupt_file_backed_up(self):
        (self.base / "data" / "rooms.json").write_text("{không phải json", encoding="utf-8")
        reloaded = self.make_hotel()
        warnings = reloaded.load(seed_if_empty=False)
        self.assertTrue(any("bị lỗi" in w for w in warnings))
        self.assertTrue(list((self.base / "data").glob("rooms*.bak")))

    def test_seed_on_first_run(self):
        fresh_dir = self.base / "fresh"
        from hotel.managers.hotel_manager import HotelManager
        hotel = HotelManager(fresh_dir / "data", fresh_dir / "inv", fresh_dir / "exp",
                             today_provider=lambda: self.today)
        hotel.load()
        self.assertEqual((len(hotel.rooms), len(hotel.guests), len(hotel.bookings)), (8, 6, 10))
        self.assertTrue(hotel.reports.total_revenue()["total"] > 0)
        data = json.loads((fresh_dir / "data" / "users.json").read_text(encoding="utf-8"))
        self.assertNotIn("admin123", json.dumps(data))


class InputAndMenuTests(unittest.TestCase):

    def run_quiet(self, func, inputs):
        with patch("builtins.input", side_effect=inputs), redirect_stdout(io.StringIO()) as out:
            result = func()
        return result, out.getvalue()

    def test_ask_reprompts_until_valid(self):
        """TC28 – Nhập sai thì báo lỗi và cho nhập lại."""
        value, out = self.run_quiet(lambda: ask("SĐT", validator=validate_phone),
                                    ["", "123", "0901234567"])
        self.assertEqual(value, "0901234567")
        self.assertEqual(out.count("Vui lòng nhập lại"), 2)

    def test_cancel_with_q(self):
        with self.assertRaises(InputCancelled):
            self.run_quiet(lambda: ask_int("Số"), ["q"])

    def test_default_and_confirm(self):
        self.assertEqual(self.run_quiet(lambda: ask("Tên", default="cũ"), [""])[0], "cũ")
        self.assertTrue(self.run_quiet(lambda: confirm("OK?"), ["x", "y"])[0])

    def test_menu_invalid_choice_then_back(self):
        """TC29 – Menu: lựa chọn sai, mục bị khóa quyền, rồi quay lại."""
        called = []
        menu = Menu("Thử", [MenuItem("1", "A", lambda: called.append("A")),
                            MenuItem("2", "B", lambda: called.append("B"),
                                     Permission.MANAGE_USERS)],
                    can=lambda p: False)
        signal, out = self.run_quiet(menu.run, ["9", "abc", "2", "", "1", "", "0"])
        self.assertEqual(signal, MenuSignal.BACK)
        self.assertEqual(called, ["A"])
        self.assertIn("không hợp lệ", out)
        self.assertIn("không có quyền", out)

    def test_menu_catches_business_errors(self):
        def boom():
            raise BusinessRuleError("lỗi nghiệp vụ")
        menu = Menu("Thử", [MenuItem("1", "Boom", boom)], can=lambda p: True)
        signal, out = self.run_quiet(menu.run, ["1", "", "0"])
        self.assertEqual(signal, MenuSignal.BACK)
        self.assertIn("lỗi nghiệp vụ", out)


if __name__ == "__main__":
    unittest.main()
