"""Giao diện Console chạy độc lập để demo chức năng F5: Xóa (Phần của Đạt)."""

import sys
from pathlib import Path

from delete_manager import DeleteManager
from entities import DeleteError, DeletionCancelled

BASE_DIR = Path(__file__).resolve().parent


def _ask_non_empty(prompt: str) -> str | None:
    raw = input(f"{prompt} (gõ 'q' để hủy): ").strip()
    if not raw or raw.lower() == "q":
        return None
    return raw


def _confirm(prompt: str) -> bool:
    while True:
        ans = input(f"{prompt} (y/n): ").strip().lower()
        if ans in ("y", "yes", "c", "co", "có"):
            return True
        if ans in ("n", "no", "k", "khong", "không", "q"):
            return False
        print("Vui lòng nhập 'y' (đồng ý) hoặc 'n' (không).")


def _show_overview(dm: DeleteManager) -> None:
    print("\n--- PHÒNG ---")
    for r in dm.rooms:
        print(f"  {r.room_id} | Số {r.room_number} | {r.room_type} | {r.price_per_night:,.0f} đ | {r.status.label}")
    if not dm.rooms:
        print("  (Danh sách phòng rỗng)")

    print("\n--- KHÁCH HÀNG ---")
    for g in dm.guests:
        print(f"  {g.guest_id} | {g.full_name} | SĐT: {g.phone}")
    if not dm.guests:
        print("  (Danh sách khách hàng rỗng)")

    print("\n--- ĐẶT PHÒNG (ĐỂ KIỂM TRA RÀNG BUỘC) ---")
    for b in dm.bookings:
        print(f"  {b.booking_id} | Khách: {b.guest_id} | Phòng: {b.room_id} | {b.status.label}")

    print("\n--- DỊCH VỤ ---")
    for s in dm.services:
        print(f"  {s.service_id} | {s.name} | {s.price:,.0f} đ/{s.unit}")
    if not dm.services:
        print("  (Danh mục dịch vụ rỗng)")

    print("\n--- TÀI KHOẢN ---")
    for u in dm.users:
        print(f"  {u.username} | {u.full_name} | {u.role.label}")


def _handle_delete_room(dm: DeleteManager) -> None:
    room_id = _ask_non_empty("Nhập mã phòng cần xóa (vd: R001, R005)")
    if room_id is None:
        print("Đã hủy thao tác.")
        return
    room = dm.find_room(room_id)
    print(f"Thông tin phòng: {room.room_id} - Số {room.room_number} ({room.room_type}) - {room.status.label}")
    deleted = dm.delete_room(
        room.room_id,
        confirm_fn=lambda r: _confirm(f"Bạn chắc chắn muốn xóa phòng {r.room_number} ({r.room_id})?"),
    )
    print(f"✔ Đã xóa phòng {deleted.room_number} ({deleted.room_id}).")


def _handle_delete_guest(dm: DeleteManager) -> None:
    guest_id = _ask_non_empty("Nhập mã khách hàng cần xóa (vd: G001, G003)")
    if guest_id is None:
        print("Đã hủy thao tác.")
        return
    guest = dm.find_guest(guest_id)
    print(f"Thông tin khách: {guest.guest_id} - {guest.full_name} - SĐT: {guest.phone}")
    deleted = dm.delete_guest(
        guest.guest_id,
        confirm_fn=lambda g: _confirm(f"Bạn chắc chắn muốn xóa khách {g.full_name} ({g.guest_id})?"),
    )
    print(f"✔ Đã xóa khách hàng {deleted.full_name} ({deleted.guest_id}).")


def _handle_delete_service(dm: DeleteManager) -> None:
    service_id = _ask_non_empty("Nhập mã dịch vụ cần xóa (vd: S001)")
    if service_id is None:
        print("Đã hủy thao tác.")
        return
    service = dm.find_service(service_id)
    print(f"Thông tin dịch vụ: {service.service_id} - {service.name} ({service.price:,.0f} đ/{service.unit})")
    deleted = dm.delete_service(
        service.service_id,
        confirm_fn=lambda s: _confirm(f"Bạn chắc chắn muốn xóa dịch vụ {s.name} ({s.service_id})?"),
    )
    print(f"✔ Đã xóa dịch vụ {deleted.name} ({deleted.service_id}).")


def _handle_delete_user(dm: DeleteManager) -> None:
    username = _ask_non_empty("Nhập tên đăng nhập cần xóa (vd: letan, admin2)")
    if username is None:
        print("Đã hủy thao tác.")
        return
    user = dm.find_user(username)
    print(f"Thông tin tài khoản: {user.username} - {user.full_name} ({user.role.label})")
    deleted = dm.delete_user(
        user.username,
        current_username="admin",
        confirm_fn=lambda u: _confirm(f"Bạn chắc chắn muốn xóa tài khoản {u.username}?"),
    )
    print(f"✔ Đã xóa tài khoản {deleted.username}.")


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    dm = DeleteManager(data_dir=BASE_DIR / "data")
    actions = {
        "1": lambda: _show_overview(dm),
        "2": lambda: _handle_delete_room(dm),
        "3": lambda: _handle_delete_guest(dm),
        "4": lambda: _handle_delete_service(dm),
        "5": lambda: _handle_delete_user(dm),
        "6": lambda: (dm.reset_sample_data(), print("✔ Đã khôi phục dữ liệu mẫu.")),
    }

    while True:
        print("\n============================================================")
        print("       MODULE F5: CHỨC NĂNG XÓA (DELETE) - ĐẠT")
        print("============================================================")
        print("  1. Xem toàn bộ dữ liệu hiện tại")
        print("  2. Xóa Phòng (kiểm tra ràng buộc đặt phòng)")
        print("  3. Xóa Khách hàng (kiểm tra ràng buộc đặt phòng)")
        print("  4. Xóa Dịch vụ")
        print("  5. Xóa Tài khoản (giả lập đang đăng nhập: admin)")
        print("  6. Khôi phục dữ liệu mẫu ban đầu")
        print("  0. Thoát")
        print("------------------------------------------------------------")

        choice = input("Chọn chức năng: ").strip()
        if choice == "0":
            print("Đã thoát chương trình F5.")
            break
        action = actions.get(choice)
        if action is None:
            print(f"✘ Lựa chọn '{choice}' không hợp lệ.")
            continue
        try:
            action()
        except DeletionCancelled as exc:
            print(f"⚠ {exc}")
        except DeleteError as exc:
            print(f"✘ {exc}")


if __name__ == "__main__":
    main()
