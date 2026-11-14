# Bảng kiểm thử – Hệ thống Quản lý Khách sạn

- **Ngày cố định trong test tự động:** 10/01/2026 (giả lập "hôm nay" để kết quả luôn ổn định).
- **Dữ liệu nền** (`tests/helpers.py`):
  - Phòng: R001 – Tiêu chuẩn 101, 500.000 đ; R002 – Cao cấp 201, 1.000.000 đ + phụ phí 200.000 đ/đêm; R003 – Suite 301, 2.000.000 đ + phụ phí 300.000 đ/đêm + quản gia 500.000 đ; R004 – Tiêu chuẩn 102, đang **bảo trì**.
  - Khách: G001 Nguyễn Văn An, G002 Trần Thị Bình. Dịch vụ: S001 Minibar 50.000 đ.
- **Chạy toàn bộ:** `python -m unittest discover -s tests -t . -v` → **77 test, tất cả ĐẠT**.

| Mã TC | Nhóm | Chức năng | Dữ liệu vào / Thao tác | Kết quả mong đợi | Kết quả thực tế | Đánh giá | Unit test |
|---|---|---|---|---|---|---|---|
| TC01 | Hợp lệ | Thêm phòng | Deluxe `r005`, số 202, giá 1.300.000, phụ phí 200.000 | Thêm thành công, mã tự viết hoa `R005`, tổng 5 phòng | Như mong đợi | ✅ Đạt | `test_add_valid_room` |
| TC02 | Hợp lệ / Không hợp lệ | Cập nhật khách | G002: SĐT `0999999999`, sau đó SĐT `abc` | Lần 1 cập nhật thành công; lần 2 báo lỗi SĐT | Như mong đợi | ✅ Đạt | `test_update_guest` |
| TC03 | Không hợp lệ | Cập nhật phòng | R002: số phòng 250 + giá −1 | Báo lỗi giá; **không trường nào bị đổi** (cập nhật nguyên tử) | Số phòng vẫn 201, giá vẫn 1.000.000 | ✅ Đạt | `test_update_is_atomic` |
| TC04 | Ràng buộc | Xóa khách | Xóa G002 đang có đặt phòng; xóa G003 không có đặt phòng | G002 bị từ chối; G003 xóa được | Như mong đợi | ✅ Đạt | `test_delete_guest` |
| TC05 | Không hợp lệ | Thêm phòng | Giá 0, −100, `abc`; số phòng `1A`; phụ phí −1 | Báo `ValidationError`, giữ giá trị cũ | Như mong đợi | ✅ Đạt | `test_invalid_values_rejected` |
| TC06 | Không hợp lệ | Thêm khách | SĐT `123` hoặc `1901234567`; tên `An 123`; tên rỗng; CCCD `12345` | Báo lỗi đúng trường | Như mong đợi | ✅ Đạt | `test_invalid_guest_fields` |
| TC07 | Không hợp lệ | Đặt phòng | Ngày nhận = hôm qua; ngày trả trước ngày nhận | Từ chối với thông báo rõ ràng | Như mong đợi | ✅ Đạt | `test_invalid_dates`, `test_check_out_before_check_in_rejected` |
| TC08 | Trùng mã | Thêm phòng | Mã `R001` đã tồn tại | `DuplicateIdError` | Như mong đợi | ✅ Đạt | `test_duplicate_room_id` |
| TC09 | Trùng mã | Thêm phòng | Mã mới nhưng số phòng `101` đã dùng | `DuplicateIdError` | Như mong đợi | ✅ Đạt | `test_duplicate_room_number` |
| TC10 | Trùng mã | Thêm khách | Mã `G001` đã tồn tại; CCCD trùng | `DuplicateIdError` | Như mong đợi | ✅ Đạt | `test_duplicate_guest_id`, `test_duplicate_id_card` |
| TC11 | Danh sách rỗng | Hiển thị / tìm / sắp xếp / báo cáo | Hệ thống chưa có dữ liệu | Trả về danh sách rỗng, doanh thu 0, tỷ lệ 0%, không lỗi chia cho 0 | Như mong đợi | ✅ Đạt | `test_empty_operations` |
| TC12 | Ràng buộc | Xóa phòng | Xóa R001 khi đang có đặt phòng; hủy đặt phòng rồi xóa lại | Lần 1 từ chối; lần 2 xóa được | Như mong đợi | ✅ Đạt | `test_delete_room_with_active_booking` |
| TC13 | Ràng buộc | Chống trùng lịch | R001 đã đặt 11–14/01; đặt thêm 13–15/01 và một lượt trong ngày 12/01 | Cả hai bị từ chối | Như mong đợi | ✅ Đạt | `test_overlapping_booking_rejected` |
| TC14 | Hợp lệ | Tìm kiếm | Phòng theo mã, loại, khoảng giá (tự hoán đổi min/max), trạng thái, số gần đúng; khách theo tên **không dấu** `nguyen`, theo SĐT | Đúng tập kết quả | Như mong đợi | ✅ Đạt | `test_search`, `test_fuzzy_search` |
| TC15 | Hợp lệ | Sắp xếp | Phòng theo giá và số phòng, tăng và giảm | Đúng thứ tự | Như mong đợi | ✅ Đạt | `test_sort` |
| TC16 | Biên | Đặt phòng liền kề | Lượt 11–14/01 và lượt 14–16/01 cùng phòng | **Được phép** (nhận đúng ngày khách cũ trả) | Như mong đợi | ✅ Đạt | `test_adjacent_booking_allowed` |
| TC17 | Biên | Số đêm tối thiểu | Nhận và trả cùng ngày; `calculate_cost(0)` | Tính 1 đêm (500.000 đ); hôm sau phòng vẫn trống | Như mong đợi | ✅ Đạt | `test_same_day_booking_one_night`, `test_zero_nights_is_charged_as_one` |
| TC18 | Biên | Giảm giá dài ngày | 1, 2, 3, 6, 7, 30 đêm | 0%, 0%, 5%, 5%, 10%, 10% | Như mong đợi | ✅ Đạt | `test_long_stay_tiers` |
| TC19 | Biên | Trần giảm giá | 7 đêm + khách thân thiết; chính sách tự tạo cộng 22% | Tối đa 15% | Như mong đợi | ✅ Đạt | `test_combined_and_capped` |
| TC20 | Đa hình | `calculate_cost(3)` | 3 loại phòng ở TC trên | 1.500.000 / 3.600.000 / 7.400.000 đ | Như mong đợi | ✅ Đạt | `test_polymorphic_calculate_cost` |
| TC21 | Ràng buộc | Đặt phòng bảo trì | Đặt R004 | Từ chối | Như mong đợi | ✅ Đạt | `test_maintenance_room_rejected` |
| TC22 | Hợp lệ | Toàn bộ lượt ở | Đặt Suite 3 đêm → thêm dịch vụ trước khi nhận phòng (bị từ chối) → nhận phòng → Minibar × 3 → trả phòng | Tiền phòng 7.400.000; giảm 5% = 370.000; dịch vụ 150.000; **tổng 7.180.000 đ**; phòng về Trống; có file hóa đơn | Như mong đợi | ✅ Đạt | `test_full_stay_flow` |
| TC23 | Ràng buộc | Hủy đặt phòng | Hủy lượt đã nhận phòng | Từ chối | Như mong đợi | ✅ Đạt | `test_cancel_after_check_in_rejected` |
| TC24 | Hợp lệ | Doanh thu | 1 lượt đã trả, 1 lượt đang ở | Chỉ tính lượt đã trả (1.200.000 đ); xem theo loại phòng và theo tháng | Như mong đợi | ✅ Đạt | `test_revenue` |
| TC25 | Hợp lệ | Tỷ lệ sử dụng | 4 phòng: 1 đang ở, 1 bảo trì | 25% trên tổng; 33,3% trên phòng đang kinh doanh | Như mong đợi | ✅ Đạt | `test_occupancy` |
| TC26 | Phân quyền | Lễ tân thêm phòng / xuất CSV | Đăng nhập `letan` | `PermissionDeniedError`; vẫn được quản lý khách | Như mong đợi | ✅ Đạt | `test_receptionist_cannot_manage_rooms` |
| TC27 | Lưu trữ | Lưu và nạp lại JSON | Tạo dữ liệu → nạp lại bằng một HotelManager mới | Dữ liệu giống hệt, trạng thái phòng giữ nguyên | Như mong đợi | ✅ Đạt | `test_persistence_round_trip` |
| TC28 | Menu / nhập liệu | Nhập lại khi sai | Nhập rỗng → `123` → `0901234567` | Báo lỗi 2 lần rồi nhận giá trị đúng; gõ `q` để hủy | Như mong đợi | ✅ Đạt | `test_ask_reprompts_until_valid`, `test_cancel_with_q` |
| TC29 | Menu | Lựa chọn sai / không đủ quyền | Chọn `9`, `abc`, mục bị khóa, rồi `0` | Báo lỗi, không thoát chương trình; `0` quay lại | Như mong đợi | ✅ Đạt | `test_menu_invalid_choice_then_back` |
| TC30 | Hợp lệ | Đặt phòng | Deluxe 2 đêm | Trạng thái "Đã đặt"; tạm tính 2.400.000 đ; phòng vẫn "Trống" | Như mong đợi | ✅ Đạt | `test_create_valid_booking` |

## Test bổ sung (không đánh mã TC)

Các test sau cũng nằm trong 77 test tự động:

- **Kế thừa và trừu tượng:** chuỗi kế thừa `SuiteRoom → DeluxeRoom → Room`; không tạo được đối tượng từ lớp trừu tượng `Room`.
- **Đóng gói:** không gán lại được mã phòng (chỉ đọc).
- **Lưu trữ:** chuyển đổi `to_dict` / `from_dict` không mất dữ liệu; file JSON hỏng được đổi tên thành `.bak` và có cảnh báo; lần chạy đầu tự tạo dữ liệu mẫu.
- **Tài khoản:** mật khẩu được băm (không lưu dạng chữ thường); không xóa được tài khoản đang đăng nhập; đổi mật khẩu.
- **Xuất CSV:** file có BOM UTF-8 để Excel mở đúng tiếng Việt.
- **Đặt phòng:** sửa đặt phòng (đổi phòng, đổi ngày); áp dụng ưu đãi khách thân thiết sau 3 lượt; quy tắc nhận phòng; tìm kiếm và sắp xếp đặt phòng.
