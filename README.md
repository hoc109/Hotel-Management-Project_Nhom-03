# Hệ thống Quản lý Khách sạn (Hotel Management System)

Bài tập lớn – Chủ đề 03. Ứng dụng Console viết bằng Python theo hướng đối tượng (OOP): quản lý phòng Tiêu chuẩn / Cao cấp / Suite, khách hàng, đặt phòng – nhận phòng – trả phòng, dịch vụ phát sinh, hóa đơn, thống kê và phân quyền.

## 1. Cài đặt và chạy

Yêu cầu Python 3.10 trở lên (đã kiểm thử trên Python 3.14).

```powershell
cd "c:\Project Python-QLKS"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

| Tài khoản mặc định | Mật khẩu | Vai trò |
|---|---|---|
| `admin` | `admin123` | Quản trị viên – toàn quyền |
| `letan` | `letan123` | Lễ tân – phục vụ khách, không được sửa danh mục phòng/dịch vụ, tài khoản, xuất CSV |

- Lần chạy đầu tiên, chương trình tự tạo **dữ liệu mẫu** trong `data/`, với các ngày tính theo hôm nay.
- Muốn làm lại từ đầu: xóa thư mục `data/` rồi chạy lại.
- Gõ `q` ở bất kỳ ô nhập nào để hủy thao tác; khi cập nhật, nhấn Enter để giữ giá trị cũ.
- `Ctrl+C` cũng thoát an toàn: dữ liệu vẫn được lưu trước khi thoát.

**Chạy kiểm thử tự động (77 test):**

```powershell
python -m unittest discover -s tests -t . -v
```

## 2. Cấu trúc mã nguồn

```
main.py                 Điểm khởi chạy
hotel/models/           Lớp thực thể: Room (ABC) → StandardRoom, DeluxeRoom → SuiteRoom; Guest;
                        Booking; Service, ServiceUsage; DiscountPolicy (ABC); Invoice; User (ABC) → Admin, Receptionist
hotel/managers/         Lớp quản lý: BaseManager (ABC, Generic) → Room/Guest/Service/Booking/AuthManager;
                        ReportManager; HotelManager (Facade: kiểm tra quyền, ràng buộc, tự lưu)
hotel/storage/          JsonStorage (ghi an toàn, sao lưu file hỏng), seed_data (dữ liệu mẫu)
hotel/ui/               Menu, BaseScreen và 6 màn hình con, HotelApp
hotel/utils/            Exception, validators, input_helper, formatter (tabulate, colorama), text_utils
tests/                  Unit test (unittest)
docs/                   UML, lưu đồ, bảng kiểm thử, kịch bản demo
data/ invoices/ exports/  Dữ liệu JSON, hóa đơn .txt, báo cáo .csv (sinh ra khi chạy)
```

## 3. Đối chiếu yêu cầu của đề

| Yêu cầu | Nơi thực hiện |
|---|---|
| Kế thừa, đa hình, đóng gói, ABC | `hotel/models/room.py`, `user.py`, `discount.py`, `managers/base_manager.py`. Giải thích chi tiết ở [docs/uml_class_diagram.md](docs/uml_class_diagram.md) |
| 1. Thêm (bắt buộc nhập, không trùng mã) | Menu Phòng/Khách/Dịch vụ → Thêm; gợi ý mã kế tiếp, báo trùng ngay khi nhập |
| 2. Cập nhật theo mã | Enter giữ nguyên; cập nhật nguyên tử (một trường sai thì không đổi gì) |
| 3. Xóa có xác nhận, kiểm tra dữ liệu liên quan | Không xóa phòng/khách còn đặt phòng hiệu lực; không xóa admin cuối cùng |
| 4. Hiển thị theo cột, xử lý danh sách rỗng | `tabulate`; thông báo "⚠ … rỗng" |
| 5. Sắp xếp ≥ 2 tiêu chí, tăng/giảm | Phòng: giá, số phòng, loại. Khách: họ tên, tên, mã. Đặt phòng: ngày nhận, tổng tiền, mã |
| 6. Tìm kiếm chính xác + gần đúng | Mã chính xác; tên khách không dấu; SĐT, số phòng gần đúng; khoảng giá |
| 7. Nghiệp vụ đặc thù | Đặt / sửa / hủy / nhận / trả phòng, cập nhật trạng thái phòng, **chống đặt trùng lịch** |
| 8. Tìm và sắp xếp phòng | Theo mã, loại, giá, trạng thái; sắp xếp theo giá hoặc số phòng |
| 9. Thống kê | Doanh thu (tổng, khoảng ngày, loại phòng, tháng), tỷ lệ phòng đang sử dụng, đặt phòng theo ngày |
| 10. Menu | Nhập lại khi chọn sai, thoát an toàn có xác nhận |
| Mở rộng (6 chức năng) | Dịch vụ phát sinh · Hóa đơn `.txt` · Đăng nhập phân quyền · Phòng Suite · Giảm giá · Xuất CSV |

## 4. Quy tắc nghiệp vụ chính

- **Số đêm** = `max(1, ngày trả − ngày nhận)`: nhận và trả cùng ngày vẫn tính 1 đêm.
- **Tiền phòng:**
  - Tiêu chuẩn = giá × số đêm.
  - Cao cấp = (giá + phụ phí dịch vụ) × số đêm.
  - Suite = như Cao cấp + phí quản gia (tính 1 lần).
- **Chống trùng lịch:** hai lượt đặt cùng phòng bị coi là trùng khi `nhận_A < trả_B` và `nhận_B < trả_A`. Chỉ xét các lượt "Đã đặt" và "Đang ở"; khách mới được nhận phòng đúng ngày khách cũ trả.
- **Nhận phòng:** chỉ khi hôm nay nằm trong thời gian lưu trú và phòng đang Trống.
- **Trả phòng:** tính theo số đêm đã đặt; trả sớm vẫn tính đủ, giá được chốt tại thời điểm đặt.
- **Giảm giá** (cộng dồn, tối đa 15%, chỉ áp lên tiền phòng):
  - Từ 3 đêm giảm 5%, từ 7 đêm giảm 10%.
  - Khách đã có ≥ 3 lượt trả phòng giảm thêm 5%.
- **Mật khẩu:** băm SHA-256 kèm salt.

## 5. Tài liệu

- [Sơ đồ lớp UML và giải thích quan hệ OOP](docs/uml_class_diagram.md)
- [Lưu đồ menu và nghiệp vụ](docs/flowchart_menu.md)
- [Bảng kiểm thử (30 trường hợp)](docs/test_cases.md)
- [Kịch bản demo để chụp màn hình](docs/demo_script.md)

## 6. Đề xuất chức năng mở rộng tiếp theo

Các chức năng dưới đây **chưa** được làm trong bài:

- Đặt cọc và thanh toán một phần, hỗ trợ nhiều phương thức thanh toán.
- Giá phòng theo mùa / cuối tuần (thêm một `PricingPolicy` theo mẫu Strategy).
- Lưu trữ bằng SQLite thay cho JSON khi dữ liệu lớn.
- Gửi xác nhận đặt phòng qua email/SMS.
