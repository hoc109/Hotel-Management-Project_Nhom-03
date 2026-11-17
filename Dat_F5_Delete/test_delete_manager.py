"""Unit test độc lập cho class DeleteManager (F5: Chức năng Xóa - Đạt)."""

import tempfile
import unittest
from pathlib import Path

from delete_manager import DeleteManager
from entities import (
    BusinessRuleError,
    DeletionCancelled,
    NotFoundError,
)


class DeleteManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dm = DeleteManager()
        self.dm.reset_sample_data()

    # ------------------------------------------------------------ Xóa Phòng
    def test_delete_room_without_active_booking_succeeds(self) -> None:
        # R001 chỉ có B001 đã trả (CHECKED_OUT) -> được phép xóa
        deleted = self.dm.delete_room("r001", confirm_fn=lambda _r: True)
        self.assertEqual(deleted.room_id, "R001")
        with self.assertRaises(NotFoundError):
            self.dm.find_room("R001")

    def test_delete_room_cancelled_booking_succeeds(self) -> None:
        # R002 chỉ có B002 đã hủy (CANCELLED) -> được phép xóa
        deleted = self.dm.delete_room("R002", confirmed=True)
        self.assertEqual(deleted.room_id, "R002")

    def test_delete_room_with_booked_rejected(self) -> None:
        # R005 đang có B004 ở trạng thái BOOKED -> phải từ chối
        with self.assertRaises(BusinessRuleError):
            self.dm.delete_room("R005")
        self.assertEqual(self.dm.find_room("R005").room_number, "202")

    def test_delete_room_with_checked_in_rejected(self) -> None:
        # R003 đang có B003 ở trạng thái CHECKED_IN -> phải từ chối
        with self.assertRaises(BusinessRuleError):
            self.dm.delete_room("R003")

    def test_delete_room_missing_id(self) -> None:
        with self.assertRaises(NotFoundError):
            self.dm.delete_room("R999")

    def test_delete_room_cancelled_by_confirmation(self) -> None:
        with self.assertRaises(DeletionCancelled):
            self.dm.delete_room("R001", confirm_fn=lambda _r: False)
        # Dữ liệu vẫn còn nguyên khi người dùng chọn 'n'
        self.assertEqual(self.dm.find_room("R001").room_id, "R001")

    # ------------------------------------------------------------ Xóa Khách
    def test_delete_guest_without_active_booking_succeeds(self) -> None:
        deleted = self.dm.delete_guest("g001")
        self.assertEqual(deleted.guest_id, "G001")
        with self.assertRaises(NotFoundError):
            self.dm.find_guest("G001")

    def test_delete_guest_with_active_booking_rejected(self) -> None:
        with self.assertRaises(BusinessRuleError):
            self.dm.delete_guest("G003")
        with self.assertRaises(BusinessRuleError):
            self.dm.delete_guest("G004")

    # ------------------------------------------------------------ Xóa Dịch vụ
    def test_delete_service_succeeds(self) -> None:
        deleted = self.dm.delete_service("s001")
        self.assertEqual(deleted.service_id, "S001")
        with self.assertRaises(NotFoundError):
            self.dm.find_service("S001")

    # ------------------------------------------------------------ Xóa Tài khoản
    def test_delete_user_rules(self) -> None:
        # Không xóa được tài khoản đang đăng nhập
        with self.assertRaises(BusinessRuleError):
            self.dm.delete_user("admin", current_username="admin")
        # Xóa được lễ tân và admin phụ
        self.dm.delete_user("letan", current_username="admin")
        self.dm.delete_user("admin2", current_username="admin")
        # Không xóa được admin cuối cùng
        with self.assertRaises(BusinessRuleError):
            self.dm.delete_user("admin", current_username="other")

    # ------------------------------------------------------------ Lưu trữ JSON riêng
    def test_persistence_in_own_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "data"
            dm1 = DeleteManager(data_dir=data_path)
            dm1.delete_room("R001")
            dm2 = DeleteManager(data_dir=data_path)
            with self.assertRaises(NotFoundError):
                dm2.find_room("R001")
            self.assertEqual(dm2.find_room("R005").room_id, "R005")


if __name__ == "__main__":
    unittest.main(verbosity=2)
