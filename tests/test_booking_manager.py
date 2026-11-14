"""Kiểm thử nghiệp vụ đặt phòng: chống trùng lịch, nhận/trả phòng, dịch vụ, giảm giá."""

import unittest

from tests.helpers import HotelTestCase

from hotel.models import BookingStatus, RoomStatus
from hotel.utils.exceptions import (BusinessRuleError, DuplicateIdError, NotFoundError,
                                    ValidationError)


class BookingManagerTests(HotelTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.add_basic_data()

    def test_create_valid_booking(self):
        """TC30 – Đặt phòng hợp lệ, tạm tính đúng tiền."""
        b = self.hotel.create_booking("B001", "G001", "R002", self.d(0), self.d(2))
        self.assertEqual(b.status, BookingStatus.BOOKED)
        self.assertEqual((b.nights, b.room_cost, b.discount_rate), (2, 2_400_000, 0))
        self.assertEqual(self.hotel.rooms.get("R002").status, RoomStatus.AVAILABLE)

    def test_duplicate_booking_id(self):
        self.hotel.create_booking("B001", "G001", "R001", self.d(0), self.d(1))
        with self.assertRaises(DuplicateIdError):
            self.hotel.create_booking("B001", "G002", "R002", self.d(0), self.d(1))

    def test_overlapping_booking_rejected(self):
        """TC13 – Không đặt trùng phòng trong cùng khoảng thời gian."""
        self.hotel.create_booking("B001", "G001", "R001", self.d(1), self.d(4))
        with self.assertRaises(BusinessRuleError):
            self.hotel.create_booking("B002", "G002", "R001", self.d(3), self.d(5))
        with self.assertRaises(BusinessRuleError):
            self.hotel.create_booking("B002", "G002", "R001", self.d(2), self.d(2))

    def test_adjacent_booking_allowed(self):
        """TC16 – Biên: nhận phòng đúng ngày khách trước trả."""
        self.hotel.create_booking("B001", "G001", "R001", self.d(1), self.d(4))
        b = self.hotel.create_booking("B002", "G002", "R001", self.d(4), self.d(6))
        self.assertEqual(b.check_in, self.d(4))

    def test_cancelled_booking_frees_room(self):
        self.hotel.create_booking("B001", "G001", "R001", self.d(1), self.d(4))
        self.hotel.cancel_booking("B001")
        self.hotel.create_booking("B002", "G002", "R001", self.d(1), self.d(4))

    def test_same_day_booking_one_night(self):
        """TC17 – Nhận/trả cùng ngày tính 1 đêm."""
        b = self.hotel.create_booking("B001", "G001", "R001", self.d(0), self.d(0))
        self.assertEqual((b.nights, b.room_cost), (1, 500_000))
        self.hotel.create_booking("B002", "G002", "R001", self.d(1), self.d(2))  # hôm sau trống

    def test_invalid_dates(self):
        """TC07 – Ngày quá khứ, ngày trả trước ngày nhận."""
        with self.assertRaises(BusinessRuleError):
            self.hotel.create_booking("B001", "G001", "R001", self.d(-1), self.d(2))
        with self.assertRaises(ValidationError):
            self.hotel.create_booking("B001", "G001", "R001", self.d(3), self.d(2))

    def test_maintenance_room_rejected(self):
        """TC21 – Không đặt được phòng đang bảo trì."""
        with self.assertRaises(BusinessRuleError):
            self.hotel.create_booking("B001", "G001", "R004", self.d(0), self.d(1))

    def test_unknown_guest_or_room(self):
        with self.assertRaises(NotFoundError):
            self.hotel.create_booking("B001", "G999", "R001", self.d(0), self.d(1))
        with self.assertRaises(NotFoundError):
            self.hotel.create_booking("B001", "G001", "R999", self.d(0), self.d(1))

    def test_available_rooms(self):
        self.hotel.create_booking("B001", "G001", "R001", self.d(0), self.d(3))
        free = {r.room_id for r in self.hotel.bookings.available_rooms(self.d(1), self.d(2))}
        self.assertEqual(free, {"R002", "R003"})

    def test_full_stay_flow(self):
        """TC22 – Đặt → nhận → dịch vụ → trả phòng, hóa đơn đúng và được lưu."""
        h = self.hotel
        h.create_booking("B001", "G001", "R003", self.d(0), self.d(3))
        with self.assertRaises(BusinessRuleError):        # chưa nhận phòng
            h.add_service_to_booking("B001", "S001", 1)
        h.check_in("B001")
        self.assertEqual(h.rooms.get("R003").status, RoomStatus.OCCUPIED)
        h.add_service_to_booking("B001", "S001", 3)
        self.today = self.d(3)
        booking, invoice, path = h.check_out("B001")
        # Suite 3 đêm = (2.000.000 + 300.000) × 3 + 500.000 = 7.400.000; giảm 5% = 370.000
        self.assertEqual(booking.room_cost, 7_400_000)
        self.assertEqual(booking.discount_amount, 370_000)
        self.assertEqual(booking.amount_due, 7_400_000 - 370_000 + 150_000)
        self.assertEqual(booking.status, BookingStatus.CHECKED_OUT)
        self.assertEqual(h.rooms.get("R003").status, RoomStatus.AVAILABLE)
        self.assertTrue(path.is_file())
        self.assertIn("TỔNG THANH TOÁN", invoice.render())

    def test_check_in_rules(self):
        h = self.hotel
        h.create_booking("B001", "G001", "R001", self.d(2), self.d(4))
        with self.assertRaises(BusinessRuleError):        # chưa tới ngày
            h.check_in("B001")
        self.today = self.d(2)
        h.check_in("B001")
        with self.assertRaises(BusinessRuleError):        # nhận phòng lần 2
            h.check_in("B001")

    def test_cancel_after_check_in_rejected(self):
        """TC23 – Không hủy được đặt phòng đã nhận phòng."""
        self.hotel.create_booking("B001", "G001", "R001", self.d(0), self.d(1))
        self.hotel.check_in("B001")
        with self.assertRaises(BusinessRuleError):
            self.hotel.cancel_booking("B001")

    def test_check_out_requires_check_in(self):
        self.hotel.create_booking("B001", "G001", "R001", self.d(0), self.d(1))
        with self.assertRaises(BusinessRuleError):
            self.hotel.check_out("B001")

    def test_update_booking(self):
        h = self.hotel
        h.create_booking("B001", "G001", "R001", self.d(1), self.d(3))
        h.create_booking("B002", "G002", "R002", self.d(1), self.d(3))
        with self.assertRaises(BusinessRuleError):        # đổi sang phòng đã có người đặt
            h.update_booking("B001", room_id="R002")
        b = h.update_booking("B001", room_id="R003", check_out=self.d(4))
        self.assertEqual((b.room_id, b.room_number, b.nights), ("R003", "301", 3))
        self.assertEqual(b.room_cost, 7_400_000)
        h.update_booking("B002", check_in=self.d(2))      # sửa chính nó không bị coi là trùng

    def test_loyalty_discount_after_three_stays(self):
        h = self.hotel
        for i in range(3):
            self.today = self.d(i * 2)
            h.create_booking(f"B00{i + 1}", "G001", "R001", self.today, self.today)
            h.check_in(f"B00{i + 1}")
            h.check_out(f"B00{i + 1}")
        self.today = self.TODAY
        b = h.create_booking("B010", "G001", "R002", self.d(10), self.d(13))
        self.assertEqual(b.discount_rate, 0.10)          # 5% dài ngày + 5% thân thiết
        self.assertEqual(h.bookings.completed_stays("G001"), 3)

    def test_search_and_sort(self):
        h = self.hotel
        h.create_booking("B001", "G001", "R001", self.d(2), self.d(3))
        h.create_booking("B002", "G002", "R003", self.d(0), self.d(1))
        bm = h.bookings
        self.assertEqual([b.booking_id for b in bm.search_by_guest("binh")], ["B002"])
        self.assertEqual([b.booking_id for b in bm.search_by_guest("g001")], ["B001"])
        self.assertEqual([b.booking_id for b in bm.sort_bookings("check_in")], ["B002", "B001"])
        self.assertEqual([b.booking_id for b in bm.sort_bookings("amount", True)], ["B002", "B001"])
        self.assertEqual([b.booking_id for b in bm.bookings_on(self.d(2))], ["B001"])
        self.assertEqual([b.booking_id for b in bm.bookings_on(self.d(0), "check_in")], ["B002"])


if __name__ == "__main__":
    unittest.main()
