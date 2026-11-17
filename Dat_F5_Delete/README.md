# Module F5: Chức năng Xóa (Delete) – Phần của Đạt

Thư mục này được tách **độc lập hoàn toàn** khỏi dự án `Hotel-Management-Project_Nhom-03` để thực hiện riêng chức năng **F5: Chức năng Xóa (Delete)** theo bảng phân công:

> **F5: Chức năng Xóa (Delete)** – Tìm theo mã, xác nhận trước khi xóa, kiểm tra ràng buộc liên quan (không xóa phòng đang booked) – **Đạt**.

## Cấu trúc thư mục

- [entities.py](entities.py): Các thực thể tối giản (`Room`, `Guest`, `Service`, `Booking`, `User`), enum trạng thái và exception riêng (`NotFoundError`, `BusinessRuleError`, `DeletionCancelled`).
- [delete_manager.py](delete_manager.py): **Class riêng `DeleteManager`** xử lý toàn bộ nghiệp vụ xóa:
  - Tìm kiếm chính xác theo mã (chuẩn hóa bỏ khoảng trắng, không phân biệt hoa/thường).
  - Kiểm tra ràng buộc liên quan trước khi xóa:
    - **Phòng**: chặn xóa nếu còn đặt phòng ở trạng thái `Đã đặt` (`BOOKED`) hoặc `Đang ở` (`CHECKED_IN`).
    - **Khách hàng**: chặn xóa nếu khách còn đặt phòng còn hiệu lực (`BOOKED` / `CHECKED_IN`).
    - **Dịch vụ**: cho phép xóa khỏi danh mục.
    - **Tài khoản**: không xóa tài khoản đang đăng nhập và không xóa tài khoản `Admin` cuối cùng.
  - Xác nhận trước khi xóa (`confirm_fn` / `confirmed`).
  - Tự lưu/đọc JSON trong thư mục `data/` riêng của module (không chung đụng với dự án gốc).
- [main.py](main.py): Chương trình console độc lập để chạy thử và demo F5.
- [test_delete_manager.py](test_delete_manager.py): Bộ unit test bằng `unittest` (chỉ dùng thư viện chuẩn Python).

## Cách chạy

```powershell
cd F:\BTL-PYTHON\Dat_F5_Delete
python main.py
```

Chạy kiểm thử tự động:

```powershell
cd F:\BTL-PYTHON\Dat_F5_Delete
python -m unittest test_delete_manager.py -v
```
