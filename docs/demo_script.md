# Kịch bản demo – chụp màn hình minh họa

**Chuẩn bị:** xóa thư mục `data/` (nếu có) để chương trình tạo lại dữ liệu mẫu theo ngày hiện tại, rồi chạy `python main.py`. Nên mở **Windows Terminal** và phóng to cửa sổ để bảng hiển thị đầy đủ.

Ký hiệu: `↵` = nhấn Enter (giữ giá trị mặc định trong `[ ]`); "HN" = ngày hôm nay. Dữ liệu mẫu có:

- 8 phòng: R001–R003 Tiêu chuẩn, R004–R006 Cao cấp (R006 đang **bảo trì**), R007–R008 Suite.
- 6 khách: G001–G006 (G001 đã ở 3 lượt → khách thân thiết).
- 10 đặt phòng:

  | Mã | Phòng | Thời gian | Trạng thái |
  |---|---|---|---|
  | B006 | 103 | HN−1 → HN+2 | Đang ở |
  | B007 | 202 | HN → HN+3 | Đã đặt (nhận phòng hôm nay) |
  | B008 | 302 | HN+5 → HN+8 | Đã đặt (khách thân thiết G001) |
  | B010 | 201 | HN+1, nhận/trả cùng ngày | Đã đặt (tính 1 đêm) |
  | B001–B005 | – | trong quá khứ | Đã trả |
  | B009 | – | – | Đã hủy |

| # | Ảnh cần chụp | Thao tác nhập | Kết quả mong đợi trên màn hình |
|---|---|---|---|
| 1 | Đăng nhập sai | `admin` / `123` | Thông báo "Sai tên đăng nhập hoặc mật khẩu. Còn 2 lần thử." |
| 2 | Màn hình khởi động và đăng nhập đúng | `admin` / `admin123` | Banner, thông báo tạo dữ liệu mẫu, lời chào "Quản trị viên", MENU CHÍNH |
| 3 | Menu sai lựa chọn | Ở menu chính gõ `9` | Thông báo "Lựa chọn '9' không hợp lệ…" và hiện lại menu |
| 4 | **Hiển thị** phòng | `1` → `4` | Bảng 8 phòng theo cột, có trạng thái Trống / Đang ở / Bảo trì |
| 5 | **Thêm** phòng hợp lệ | `1` → `1` → `3` (Suite) → `↵` (R009) → `401` → `3500000` → `↵` → `500000` → `800000` | "Đã thêm phòng 401 (R009)" + bảng phòng vừa thêm |
| 6 | Thêm phòng **không hợp lệ / trùng** | `1` → `1` → `1` → `R001` (trùng mã) → `R010` → `101` (trùng số) → `105` → `-5` (giá âm) → `abc` → `450000` → `↵` → `↵` | Mỗi lần nhập sai đều báo lỗi đỏ và cho nhập lại trường đó |
| 7 | **Cập nhật** phòng | `1` → `2` → `R004` → `↵` → `1300000` → `↵` → `250000` | Bảng trước và sau khi cập nhật, giá mới 1.300.000 đ |
| 8 | **Xóa** bị chặn (ràng buộc) | `1` → `3` → `R003` → `y` | Cảnh báo vàng + lỗi "Không thể xóa phòng 103: còn đặt phòng hiệu lực B006 (Đang ở)" |
| 9 | **Xóa** thành công | `1` → `3` → `R009` → `y` | "Đã xóa phòng 401 (R009)" |
| 10 | **Tìm kiếm** theo khoảng giá | `1` → `5` → `3` → `500000` → `1500000` | Danh sách phòng có giá từ 500.000 đến 1.500.000 đ |
| 11 | **Tìm kiếm** theo loại / trạng thái | `1` → `5` → `2` → `3` (Suite); sau đó `1` → `5` → `4` → `3` (Bảo trì) | Danh sách phòng Suite; phòng 203 đang bảo trì |
| 12 | **Sắp xếp** theo giá giảm dần | `1` → `6` → `1` → `2` | Phòng 302 đứng đầu, phòng 101 đứng cuối |
| 13 | **Sắp xếp** theo số phòng tăng dần | `1` → `6` → `2` → `1` | 101, 102, 103, 201… |
| 14 | **Đa hình** | `1` → `8` → `3` | Cột "Lớp Python" (StandardRoom / DeluxeRoom / SuiteRoom) và `calculate_cost(3)` khác nhau cho từng loại |
| 15 | Đa hình – tối thiểu 1 đêm | `1` → `8` → `0` | Mọi phòng đều tính "× 1 đêm" |
| 16 | Tìm khách gần đúng **không dấu** | `0` → `2` → `5` → `2` → `nguyen` | Tìm ra "Nguyễn Văn An" |
| 17 | Lịch sử khách thân thiết | `2` → `7` → `G001` | 4 lượt đặt; "Khách thân thiết: được giảm thêm 5%…" |
| 18 | **Đặt phòng** và báo giá | `0` → `3` → `1` → `G001` → `↵` (HN) → nhập ngày HN+3 → `R007` → `↵` → `y` | Bảng phòng trống, báo giá có "Ưu đãi lưu trú dài ngày 5%" và "Ưu đãi khách thân thiết 5%", đặt phòng thành công |
| 19 | **Chống đặt trùng** | `3` → `1` → `G002` → `↵` → `↵` → nhập `R007` | "Phòng 301 không trống trong thời gian này…", cho nhập lại (gõ `q` để hủy) |
| 20 | Đặt phòng bảo trì | Trong bước chọn phòng nhập `R006` | Bị từ chối vì phòng không nằm trong danh sách trống |
| 21 | Nhận / trả cùng ngày = 1 đêm | `3` → `1` → `G002` → `↵` → `↵` → nhập lại ngày HN → `R001` → `↵` → `y` | Báo giá "× 1 đêm" |
| 22 | **Nhận phòng** | `3` → `4` → `B007` | Danh sách chờ nhận hôm nay; "Nhận phòng thành công… Phòng 202 chuyển sang 'Đang ở'" |
| 23 | **Dịch vụ phát sinh** | `3` → `5` → `B007` → `S003` → `2` | "Đã thêm: Ăn sáng buffet × 2 = 300.000 đ…" |
| 24 | **Trả phòng + hóa đơn** | `3` → `6` → `B006` → `y` | Cảnh báo trả sớm, hóa đơn đầy đủ (tiền phòng, giảm giá, dịch vụ, tổng) và đường dẫn file `invoices/INV-B006.txt` |
| 25 | Hủy bị chặn | `3` → `3` → `B007` | "Đặt phòng B007 đang 'Đang ở' (yêu cầu: Đã đặt)" – cho nhập lại, gõ `q` để thoát |
| 26 | Sắp xếp đặt phòng theo tổng tiền giảm dần | `3` → `10` → `2` → `2` | Danh sách sắp xếp theo cột Tổng tiền |
| 27 | **Thống kê doanh thu** | `0` → `5` → `1` | Bảng các lượt đã trả + bảng TỔNG HỢP |
| 28 | Doanh thu theo loại phòng / theo tháng | `5` → `3`; `5` → `4` → `↵` | Bảng tỷ trọng theo loại; bảng theo tháng |
| 29 | **Tỷ lệ phòng đang sử dụng** | `5` → `5` | Số phòng đang ở / trống / bảo trì, 2 tỷ lệ % và bảng theo loại phòng |
| 30 | **Đặt phòng theo ngày** | `5` → `6` → `↵` → `1` | Danh sách khách lưu trú hôm nay |
| 31 | Xuất CSV | `5` → `7` → `4` (Tất cả) | 3 đường dẫn file trong `exports/` (mở bằng Excel không lỗi font) |
| 32 | **Phân quyền** | `0` → `7` (đăng xuất) → `letan` / `letan123` → `1` | Các mục Thêm / Sửa / Xóa phòng bị đánh dấu `[Khóa - chỉ Admin]` |
| 33 | Lễ tân bị từ chối | Chọn `1` | "Bạn không có quyền sử dụng chức năng 'Thêm phòng'." |
| 34 | Danh sách rỗng | Tìm phòng theo số `999`: `5` → `5` → `999` | "⚠ Không tìm thấy phòng phù hợp." |
| 35 | Hủy thao tác bằng `q` | Bất kỳ ô nhập nào gõ `q` | "⚠ Đã hủy thao tác." |
| 36 | **Thoát an toàn** | `0` → `0` → `y` | "Đã lưu dữ liệu." + lời chào tạm biệt |

> [!TIP]
> Muốn quay về dữ liệu mẫu ban đầu thì thoát chương trình, xóa thư mục `data/` rồi chạy lại.
