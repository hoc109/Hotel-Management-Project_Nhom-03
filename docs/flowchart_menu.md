# Lưu đồ hoạt động – Menu chính và các nghiệp vụ

## 1. Luồng chương trình và menu chính

```mermaid
flowchart TD
    A([Bắt đầu: python main.py]) --> B[Nạp dữ liệu JSON]
    B --> C{Lần chạy đầu?}
    C -- Có --> D[Tạo dữ liệu mẫu + tài khoản mặc định]
    C -- Không --> E
    D --> E[/Nhập tên đăng nhập, mật khẩu/]
    E --> F{Đúng?}
    F -- Sai, chưa quá 3 lần --> E
    F -- Sai 3 lần hoặc gõ q --> Z
    F -- Đúng --> G[Hiển thị MENU CHÍNH]
    G --> H[/Chọn chức năng/]
    H --> I{Lựa chọn hợp lệ?}
    I -- Không --> J[Báo lỗi] --> G
    I -- 1 --> M1[Quản lý phòng]
    I -- 2 --> M2[Quản lý khách hàng]
    I -- 3 --> M3[Đặt phòng & lưu trú]
    I -- 4 --> M4[Danh mục dịch vụ]
    I -- 5 --> M5[Thống kê & báo cáo]
    I -- 6 --> M6[Tài khoản]
    M1 & M2 & M3 & M4 & M5 & M6 --> G
    I -- 7 Đăng xuất --> E
    I -- 0 Thoát --> K{Xác nhận thoát?}
    K -- Không --> G
    K -- Có --> Z[Lưu dữ liệu JSON]
    Z --> END([Kết thúc])
    G -. Ctrl+C / EOF .-> Z
```

## 2. Xử lý một chức năng trong menu con

```mermaid
flowchart TD
    S[/Chọn chức năng trong menu con/] --> P{Đủ quyền?}
    P -- Không --> PE[Báo: không có quyền] --> W
    P -- Có --> IN[/Nhập dữ liệu từng trường/]
    IN --> V{Hợp lệ?}
    V -- Không --> VE[Báo lỗi, nhập lại trường đó] --> IN
    V -- Gõ q --> CA[Đã hủy thao tác] --> W
    V -- Có --> BR{Kiểm tra nghiệp vụ: trùng mã, ràng buộc}
    BR -- Vi phạm --> BE[Báo lỗi nghiệp vụ] --> W
    BR -- OK --> OK[Thực hiện, tự động lưu JSON, hiển thị kết quả] --> W
    W[Nhấn Enter để tiếp tục] --> BACK[Quay lại menu con]
```

## 3. Nghiệp vụ đặt phòng – nhận phòng – trả phòng

```mermaid
flowchart TD
    A[/Nhập mã khách/] --> B{Khách tồn tại?}
    B -- Không --> A
    B -- Có --> C[/Nhập ngày nhận, ngày trả/]
    C --> D{Ngày nhận không ở quá khứ<br/>và ngày trả không trước ngày nhận?}
    D -- Không --> C
    D -- Có --> E["Số đêm = max(1, ngày trả - ngày nhận)"]
    E --> F[Liệt kê phòng không bảo trì và không trùng lịch]
    F --> G[/Chọn phòng/]
    G --> H["Báo giá: room.calculate_cost(số đêm) và giảm giá"]
    H --> I{Xác nhận?}
    I -- Không --> X([Hủy])
    I -- Có --> J[Booking: ĐÃ ĐẶT]
    J --> K{Khách đến?}
    K -- Hủy trước khi đến --> L[Booking: ĐÃ HỦY]
    K -- Đến trong thời gian lưu trú --> M[Booking: ĐANG Ở<br/>Phòng: Đang ở]
    M --> N[Thêm dịch vụ phát sinh nếu có]
    N --> O[Trả phòng: tính lại giảm giá]
    O --> P[Booking: ĐÃ TRẢ<br/>Phòng: Trống]
    P --> Q[In hóa đơn và lưu invoices/INV-mã.txt]
```

## 4. Vòng đời trạng thái

```mermaid
stateDiagram-v2
    [*] --> DaDat: create_booking()
    DaDat --> DaDat: update_booking()
    DaDat --> DaHuy: cancel_booking()
    DaDat --> DangO: check_in()
    DangO --> DangO: add_service_to_booking()
    DangO --> DaTra: check_out()
    DaHuy --> [*]
    DaTra --> [*]

    state "Đã đặt" as DaDat
    state "Đang ở" as DangO
    state "Đã trả" as DaTra
    state "Đã hủy" as DaHuy
```

Trạng thái phòng: `Trống ⇄ Bảo trì` (Admin đổi thủ công). `Trống → Đang ở` chỉ xảy ra khi nhận phòng; `Đang ở → Trống` chỉ xảy ra khi trả phòng.
