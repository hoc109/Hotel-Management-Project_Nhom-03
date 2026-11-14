"""Kiểm thử lớp thực thể: kế thừa, đa hình, đóng gói, kiểm tra dữ liệu."""

import unittest
from datetime import date

import tests.helpers  # noqa: F401 - thiết lập sys.path

from hotel.models import (Admin, Booking, BookingStatus, DeluxeRoom, DiscountCalculator,
                          Guest, LongStayDiscount, LoyaltyDiscount, Permission, Receptionist,
                          Room, RoomFactory, StandardRoom, SuiteRoom)
from hotel.utils.exceptions import BusinessRuleError, ValidationError


class RoomModelTests(unittest.TestCase):

    def setUp(self) -> None:
        self.std = StandardRoom("r001", "101", 500_000)
        self.dlx = DeluxeRoom("R002", "201", 1_000_000, extra_service_fee=200_000)
        self.suite = SuiteRoom("R003", "301", 2_000_000, extra_service_fee=300_000,
                               butler_fee=500_000)

    def test_polymorphic_calculate_cost(self):
        """TC20 – Cùng 3 đêm, mỗi loại phòng tính tiền khác nhau."""
        rooms: list[Room] = [self.std, self.dlx, self.suite]
        costs = [room.calculate_cost(3) for room in rooms]
        self.assertEqual(costs, [1_500_000, 3_600_000, 7_400_000])
        self.assertEqual([r.get_room_type() for r in rooms], ["Tiêu chuẩn", "Cao cấp", "Suite"])

    def test_breakdown_matches_cost(self):
        for room in (self.std, self.dlx, self.suite):
            self.assertAlmostEqual(sum(a for _, a in room.cost_breakdown(4)),
                                   room.calculate_cost(4))

    def test_zero_nights_is_charged_as_one(self):
        """TC17 – Nhận/trả cùng ngày tính tối thiểu 1 đêm."""
        self.assertEqual(self.std.calculate_cost(0), self.std.calculate_cost(1))
        self.assertEqual(self.suite.calculate_cost(0), 2_800_000)

    def test_negative_nights_rejected(self):
        with self.assertRaises(ValidationError):
            self.std.calculate_cost(-1)

    def test_room_is_abstract(self):
        with self.assertRaises(TypeError):
            Room("R009", "999", 100)  # type: ignore[abstract]

    def test_inheritance_chain(self):
        self.assertIsInstance(self.suite, DeluxeRoom)
        self.assertIsInstance(self.suite, Room)
        self.assertNotIsInstance(self.std, DeluxeRoom)

    def test_id_normalized_and_read_only(self):
        self.assertEqual(self.std.room_id, "R001")
        with self.assertRaises(AttributeError):
            self.std.room_id = "R999"  # type: ignore[misc]

    def test_invalid_values_rejected(self):
        """TC05 – Giá ≤ 0, chữ, số phòng sai, phụ phí âm đều bị từ chối."""
        for price in (0, -100, "abc"):
            with self.assertRaises(ValidationError):
                StandardRoom("R010", "110", price)
        with self.assertRaises(ValidationError):
            StandardRoom("R010", "1A", 100)
        with self.assertRaises(ValidationError):
            DeluxeRoom("R010", "110", 100, extra_service_fee=-1)
        with self.assertRaises(ValidationError):
            self.std.price_per_night = -5
        self.assertEqual(self.std.price_per_night, 500_000)  # giữ nguyên giá trị cũ

    def test_factory_round_trip(self):
        for room in (self.std, self.dlx, self.suite):
            clone = RoomFactory.from_dict(room.to_dict())
            self.assertIs(type(clone), type(room))
            self.assertEqual(clone.to_dict(), room.to_dict())

    def test_factory_unknown_type(self):
        with self.assertRaises(ValidationError):
            RoomFactory.from_dict({"type": "villa", "room_id": "R1"})

    def test_status_parse(self):
        self.std.status = "maintenance"
        self.assertFalse(self.std.is_available())
        self.assertFalse(self.std.is_bookable())
        with self.assertRaises(ValidationError):
            self.std.status = "broken"


class GuestModelTests(unittest.TestCase):

    def test_valid_guest_normalized(self):
        g = Guest("g01", "  nguyễn   văn an ", "0901234567")
        self.assertEqual((g.guest_id, g.full_name), ("G01", "Nguyễn Văn An"))
        self.assertEqual(g.given_name, "An")

    def test_invalid_guest_fields(self):
        """TC06 – SĐT sai, tên có số, tên rỗng, CCCD sai."""
        cases = [("G01", "An", "123"), ("G01", "An 123", "0901234567"),
                 ("G01", "", "0901234567"), ("G01", "Nguyễn An", "1901234567")]
        for args in cases:
            with self.assertRaises(ValidationError, msg=str(args)):
                Guest(*args)
        with self.assertRaises(ValidationError):
            Guest("G01", "Nguyễn An", "0901234567", "12345")


class BookingModelTests(unittest.TestCase):

    def make(self, start: date, end: date, **kw) -> Booking:
        return Booking("B001", "G001", "R001", start, end, **kw)

    def test_nights_minimum_one(self):
        self.assertEqual(self.make(date(2026, 1, 1), date(2026, 1, 1)).nights, 1)
        self.assertEqual(self.make(date(2026, 1, 1), date(2026, 1, 4)).nights, 3)

    def test_check_out_before_check_in_rejected(self):
        """TC07 – Ngày trả trước ngày nhận."""
        with self.assertRaises(ValidationError):
            self.make(date(2026, 1, 5), date(2026, 1, 4))

    def test_overlap_rules(self):
        b = self.make(date(2026, 1, 5), date(2026, 1, 8))
        self.assertTrue(b.overlaps(date(2026, 1, 7), date(2026, 1, 9)))
        self.assertTrue(b.overlaps(date(2026, 1, 1), date(2026, 1, 20)))
        self.assertFalse(b.overlaps(date(2026, 1, 8), date(2026, 1, 10)))  # nhận đúng ngày trả
        self.assertFalse(b.overlaps(date(2026, 1, 2), date(2026, 1, 5)))
        # lượt ở trong ngày chiếm phòng [ngày, ngày + 1)
        self.assertTrue(b.overlaps(date(2026, 1, 6), date(2026, 1, 6)))
        self.assertFalse(b.overlaps(date(2026, 1, 8), date(2026, 1, 8)))
        same_day = self.make(date(2026, 1, 5), date(2026, 1, 5))
        self.assertTrue(same_day.overlaps(date(2026, 1, 5), date(2026, 1, 6)))
        self.assertFalse(same_day.overlaps(date(2026, 1, 6), date(2026, 1, 7)))

    def test_state_machine(self):
        b = self.make(date(2026, 1, 5), date(2026, 1, 8))
        with self.assertRaises(BusinessRuleError):
            b.mark_checked_out(date(2026, 1, 8))
        b.mark_checked_in(date(2026, 1, 5))
        with self.assertRaises(BusinessRuleError):
            b.cancel()
        b.mark_checked_out(date(2026, 1, 8))
        self.assertEqual(b.status, BookingStatus.CHECKED_OUT)

    def test_amount_due(self):
        b = self.make(date(2026, 1, 5), date(2026, 1, 8), room_cost=1_000_000, discount_rate=0.1)
        self.assertEqual(b.discount_amount, 100_000)
        self.assertEqual(b.amount_due, 900_000)

    def test_round_trip(self):
        b = self.make(date(2026, 1, 5), date(2026, 1, 8), room_cost=1_000_000)
        self.assertEqual(Booking.from_dict(b.to_dict()).to_dict(), b.to_dict())


class DiscountTests(unittest.TestCase):

    def test_long_stay_tiers(self):
        """TC18 – Mốc 3 đêm (5%) và 7 đêm (10%)."""
        policy = LongStayDiscount()
        self.assertEqual([policy.rate(n, 0) for n in (1, 2, 3, 6, 7, 30)],
                         [0, 0, 0.05, 0.05, 0.10, 0.10])

    def test_loyalty(self):
        self.assertEqual(LoyaltyDiscount().rate(1, 2), 0)
        self.assertEqual(LoyaltyDiscount().rate(1, 3), 0.05)

    def test_combined_and_capped(self):
        """TC19 – Cộng dồn nhưng không vượt trần 15%."""
        calc = DiscountCalculator()
        self.assertEqual(calc.calculate(3, 3), 0.10)
        self.assertEqual(calc.calculate(7, 3), 0.15)
        greedy = DiscountCalculator([LongStayDiscount([(1, 0.12)]), LoyaltyDiscount(0, 0.1)])
        self.assertEqual(greedy.calculate(1, 0), 0.15)


class UserModelTests(unittest.TestCase):

    def test_password_is_hashed(self):
        user = Admin.create("boss", "secret123", "Ông Chủ")
        self.assertNotIn("secret123", str(user.to_dict()))
        self.assertTrue(user.check_password("secret123"))
        self.assertFalse(user.check_password("wrong"))

    def test_polymorphic_permissions(self):
        admin = Admin.create("boss", "secret123", "Ông Chủ")
        staff = Receptionist.create("staff", "secret123", "Nhân Viên")
        self.assertTrue(admin.has_permission(Permission.MANAGE_ROOMS))
        self.assertFalse(staff.has_permission(Permission.MANAGE_ROOMS))
        self.assertTrue(staff.has_permission(Permission.MANAGE_BOOKINGS))

    def test_short_password_rejected(self):
        with self.assertRaises(ValidationError):
            Admin.create("boss", "123", "Ông Chủ")


if __name__ == "__main__":
    unittest.main()
