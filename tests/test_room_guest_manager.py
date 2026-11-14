"""Kiểm thử quản lý phòng và khách hàng: thêm, sửa, xóa, tìm kiếm, sắp xếp."""

import unittest

from tests.helpers import HotelTestCase

from hotel.models import DeluxeRoom, Guest, RoomStatus, StandardRoom
from hotel.utils.exceptions import (BusinessRuleError, DuplicateIdError, NotFoundError,
                                    ValidationError)


class RoomManagerTests(HotelTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.add_basic_data()

    def test_add_valid_room(self):
        """TC01 – Thêm phòng Deluxe hợp lệ."""
        self.hotel.add_room(DeluxeRoom("r005", "202", 1_300_000, extra_service_fee=200_000))
        self.assertEqual(self.hotel.rooms.get("R005").room_number, "202")
        self.assertEqual(len(self.hotel.rooms), 5)

    def test_duplicate_room_id(self):
        """TC08 – Thêm phòng trùng mã."""
        with self.assertRaises(DuplicateIdError):
            self.hotel.add_room(StandardRoom("R001", "999", 100_000))

    def test_duplicate_room_number(self):
        """TC09 – Thêm phòng trùng số phòng."""
        with self.assertRaises(DuplicateIdError):
            self.hotel.add_room(StandardRoom("R099", "101", 100_000))

    def test_update_is_atomic(self):
        """TC03 – Cập nhật có trường sai thì không thay đổi gì."""
        with self.assertRaises(ValidationError):
            self.hotel.update_room("R002", room_number="250", price_per_night=-1)
        room = self.hotel.rooms.get("R002")
        self.assertEqual((room.room_number, room.price_per_night), ("201", 1_000_000))

    def test_update_valid(self):
        room, warnings = self.hotel.update_room("R002", price_per_night=1_100_000,
                                                extra_service_fee=150_000)
        self.assertEqual(room.calculate_cost(1), 1_250_000)
        self.assertEqual(warnings, [])

    def test_update_duplicate_number_and_id_change(self):
        with self.assertRaises(DuplicateIdError):
            self.hotel.update_room("R002", room_number="101")
        with self.assertRaises(ValidationError):
            self.hotel.rooms.update("R002", room_id="R777")

    def test_status_rules(self):
        with self.assertRaises(BusinessRuleError):
            self.hotel.update_room("R001", status="occupied")
        self.hotel.create_booking("B001", "G001", "R001", self.d(0), self.d(2))
        _, warnings = self.hotel.update_room("R001", status="maintenance")
        self.assertTrue(warnings)  # cảnh báo còn đặt phòng sắp tới

    def test_delete_room_with_active_booking(self):
        """TC12 – Không xóa phòng đang có đặt phòng hiệu lực."""
        self.hotel.create_booking("B001", "G001", "R001", self.d(1), self.d(3))
        with self.assertRaises(BusinessRuleError):
            self.hotel.delete_room("R001")
        self.hotel.cancel_booking("B001")
        self.hotel.delete_room("R001")
        self.assertFalse(self.hotel.rooms.exists("R001"))

    def test_delete_missing_room(self):
        with self.assertRaises(NotFoundError):
            self.hotel.delete_room("R999")

    def test_search(self):
        """TC14 – Tìm theo mã, loại, giá, trạng thái, số phòng gần đúng."""
        rooms = self.hotel.rooms
        self.assertEqual(rooms.find("r002").room_id, "R002")
        self.assertIsNone(rooms.find("R999"))
        self.assertEqual({r.room_id for r in rooms.search_by_type("standard")}, {"R001", "R004"})
        self.assertEqual({r.room_id for r in rooms.search_by_price(1_500_000, 400_000)},
                         {"R001", "R002", "R004"})
        self.assertEqual([r.room_id for r in rooms.search_by_status(RoomStatus.MAINTENANCE)],
                         ["R004"])
        self.assertEqual({r.room_id for r in rooms.search_by_number("10")}, {"R001", "R004"})

    def test_sort(self):
        """TC15 – Sắp xếp theo giá và số phòng, tăng/giảm."""
        rooms = self.hotel.rooms
        self.assertEqual([r.room_id for r in rooms.sort_rooms("price")],
                         ["R004", "R001", "R002", "R003"])
        self.assertEqual([r.room_id for r in rooms.sort_rooms("price", reverse=True)],
                         ["R003", "R002", "R001", "R004"])
        self.assertEqual([r.room_number for r in rooms.sort_rooms("number")],
                         ["101", "102", "201", "301"])
        self.assertEqual([r.room_number for r in rooms.sort_rooms("number", True)],
                         ["301", "201", "102", "101"])

    def test_next_id(self):
        self.assertEqual(self.hotel.rooms.next_id("R"), "R005")


class EmptyListTests(HotelTestCase):

    def test_empty_operations(self):
        """TC11 – Danh sách rỗng: hiển thị, tìm, sắp xếp, báo cáo không lỗi."""
        h = self.hotel
        self.assertEqual(h.rooms.list_all(), [])
        self.assertEqual(h.rooms.sort_rooms("price"), [])
        self.assertEqual(h.rooms.search_by_type("suite"), [])
        self.assertEqual(h.guests.search_by_name("an"), [])
        self.assertEqual(h.bookings.sort_bookings("amount"), [])
        self.assertEqual(h.reports.total_revenue()["total"], 0)
        self.assertEqual(h.reports.occupancy()["rate_total"], 0.0)
        self.assertEqual(h.rooms.next_id("R"), "R001")


class GuestManagerTests(HotelTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.add_basic_data()
        self.hotel.add_guest(Guest("G003", "Lê Văn Cường", "0987654321"))

    def test_duplicate_guest_id(self):
        """TC10 – Thêm khách trùng mã."""
        with self.assertRaises(DuplicateIdError):
            self.hotel.add_guest(Guest("G001", "Ai Đó", "0900000000"))

    def test_duplicate_id_card(self):
        with self.assertRaises(DuplicateIdError):
            self.hotel.add_guest(Guest("G009", "Ai Đó", "0900000000", "001090012345"))

    def test_fuzzy_search(self):
        """TC14 – Tìm tên gần đúng không dấu, SĐT gần đúng."""
        g = self.hotel.guests
        self.assertEqual([x.guest_id for x in g.search_by_name("nguyen")], ["G001"])
        self.assertEqual({x.guest_id for x in g.search_by_name("VĂN")}, {"G001", "G003"})
        self.assertEqual([x.guest_id for x in g.search_by_phone("0912")], ["G002"])
        self.assertEqual(g.search_by_name("không có"), [])

    def test_sort(self):
        g = self.hotel.guests
        self.assertEqual([x.guest_id for x in g.sort_guests("given_name")], ["G001", "G002", "G003"])
        self.assertEqual([x.guest_id for x in g.sort_guests("name", True)], ["G002", "G001", "G003"])

    def test_update_guest(self):
        """TC02 – Cập nhật khách hợp lệ."""
        guest = self.hotel.update_guest("G002", phone="0999999999")
        self.assertEqual(guest.phone, "0999999999")
        with self.assertRaises(ValidationError):
            self.hotel.update_guest("G002", phone="abc")

    def test_delete_guest(self):
        """TC04 – Xóa khách: chặn khi còn đặt phòng, cho phép khi không còn."""
        self.hotel.create_booking("B001", "G002", "R001", self.d(0), self.d(1))
        with self.assertRaises(BusinessRuleError):
            self.hotel.delete_guest("G002")
        self.hotel.delete_guest("G003")
        self.assertFalse(self.hotel.guests.exists("G003"))


if __name__ == "__main__":
    unittest.main()
