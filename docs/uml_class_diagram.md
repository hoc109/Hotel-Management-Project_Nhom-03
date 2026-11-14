# Sơ đồ lớp UML – Hệ thống Quản lý Khách sạn

Ký hiệu phạm vi truy cập: `+` public · `-` private (`__thuoc_tinh`) · `#` protected (`_thuoc_tinh`).
Phương thức trừu tượng được đánh dấu `*`. Các thuộc tính private đều được truy cập qua `@property` (getter/setter có kiểm tra dữ liệu).

> Có thể xem sơ đồ trực tiếp trên GitHub/VS Code (Markdown Preview Mermaid), hoặc dán vào https://mermaid.live để xuất ảnh PNG/SVG.

## 1. Lớp thực thể (models)

```mermaid
classDiagram
    direction TB

    class Room {
        <<abstract>>
        +ROOM_TYPE: str
        -__room_id: str
        -__room_number: str
        #_price_per_night: float
        -__status: RoomStatus
        +room_id: str «property, chỉ đọc»
        +room_number: str «property»
        +price_per_night: float «property»
        +status: RoomStatus «property»
        +is_available() bool
        +is_bookable() bool
        #_normalize_nights(nights: int) int
        #_room_charge(nights: int) float
        +calculate_cost(nights: int) float*
        +get_room_type() str*
        +get_extra_info() str*
        +cost_breakdown(nights: int) list*
        +to_dict() dict
        +to_row() list
        +__str__() str
    }
    class StandardRoom {
        -__basic_service: str
        +calculate_cost(nights: int) float
        +get_room_type() str
        +from_dict(data: dict)$ StandardRoom
    }
    class DeluxeRoom {
        #_extra_service_fee: float
        +calculate_cost(nights: int) float
        +get_room_type() str
        +from_dict(data: dict)$ DeluxeRoom
    }
    class SuiteRoom {
        -__butler_fee: float
        +calculate_cost(nights: int) float
        +get_room_type() str
        +from_dict(data: dict)$ SuiteRoom
    }
    class RoomFactory {
        -_REGISTRY: dict
        +from_dict(data: dict)$ Room
        +room_types()$ dict
    }
    Room <|-- StandardRoom
    Room <|-- DeluxeRoom
    DeluxeRoom <|-- SuiteRoom
    RoomFactory ..> Room : tạo

    class Guest {
        -__guest_id: str
        -__full_name: str
        -__phone: str
        -__id_card: str
        +given_name: str
        +to_dict() dict
        +from_dict(data: dict)$ Guest
        +__str__() str
    }

    class Service {
        -__service_id: str
        -__name: str
        -__price: float
        -__unit: str
        +to_dict() dict
        +__str__() str
    }
    class ServiceUsage {
        -__service_id: str
        -__service_name: str
        -__unit_price: float
        -__quantity: int
        -__used_on: date
        +subtotal: float
    }

    class Booking {
        -__booking_id: str
        -__guest_id: str
        -__room_id: str
        -__check_in: date
        -__check_out: date
        -__status: BookingStatus
        -__room_cost: float
        -__discount_rate: float
        -__services: list~ServiceUsage~
        +nights: int
        +amount_due: float
        +count_nights(ci, co)$ int
        +overlaps(start, end) bool
        +covers(day) bool
        +mark_checked_in(day)
        +mark_checked_out(day)
        +cancel()
        +add_service(usage)
        +update_stay(ci, co)
        +assign_room(id, number, type)
    }
    Booking "1" *-- "0..*" ServiceUsage : gồm
    Booking "0..*" --> "1" Guest : guest_id
    Booking "0..*" --> "1" Room : room_id
    ServiceUsage ..> Service : lưu bản sao giá

    class DiscountPolicy {
        <<abstract>>
        +name: str*
        +rate(nights, completed_stays) float*
    }
    class LongStayDiscount {
        -__tiers: list
        +rate(nights, completed_stays) float
    }
    class LoyaltyDiscount {
        -__min_stays: int
        -__discount: float
        +rate(nights, completed_stays) float
    }
    class DiscountCalculator {
        -__policies: list~DiscountPolicy~
        -__max_rate: float
        +details(nights, stays) list
        +calculate(nights, stays) float
    }
    DiscountPolicy <|-- LongStayDiscount
    DiscountPolicy <|-- LoyaltyDiscount
    DiscountCalculator o-- "1..*" DiscountPolicy

    class Invoice {
        -__booking: Booking
        -__guest: Guest
        -__room: Room
        +render() str
        +save(directory) Path
    }
    Invoice --> Booking
    Invoice --> Room : cost_breakdown()

    class User {
        <<abstract>>
        -__username: str
        -__full_name: str
        -__password_hash: str
        -__salt: str
        +create(username, password, full_name)$ User
        +check_password(pw) bool
        +set_password(pw)
        +permissions() frozenset*
        +has_permission(p) bool
    }
    class Admin { +permissions() frozenset }
    class Receptionist { +permissions() frozenset }
    User <|-- Admin
    User <|-- Receptionist
```

## 2. Lớp quản lý (managers)

```mermaid
classDiagram
    direction TB
    class BaseManager~T~ {
        <<abstract>>
        #_items: dict~str, T~
        +entity_name: str*
        +get_id(item: T) str*
        +create_from_dict(data: dict) T*
        #_validate_unique(item, exclude_id)
        +add(item: T) T
        +find(id) T
        +get(id) T
        +exists(id) bool
        +update(id, **changes) T
        +remove(id) T
        +list_all() list~T~
        +filter(predicate) list~T~
        +sort_by(key, reverse) list~T~
        +next_id(prefix) str
        +load_dicts(records) list
        +to_dicts() list
    }
    class RoomManager {
        +search_by_type(type) list
        +search_by_price(min, max) list
        +search_by_status(status) list
        +search_by_number(keyword) list
        +sort_rooms(criterion, reverse) list
    }
    class GuestManager {
        +search_by_name(keyword) list
        +search_by_phone(keyword) list
        +sort_guests(criterion, reverse) list
    }
    class ServiceManager {
        +search_by_name(keyword) list
    }
    class BookingManager {
        -__rooms: RoomManager
        -__guests: GuestManager
        -__services: ServiceManager
        -__discount: DiscountCalculator
        +conflicts(room_id, ci, co) list
        +available_rooms(ci, co) list
        +create_booking(...) Booking
        +update_booking(...) Booking
        +cancel_booking(id) Booking
        +check_in(id) Booking
        +add_service_usage(id, sid, qty)
        +check_out(id) Booking
        +bookings_on(day, mode) list
        +sort_bookings(criterion, reverse) list
    }
    class AuthManager {
        -__current_user: User
        +login(username, password) User
        +logout()
        +require(permission)
        +add_user(...) User
        +delete_user(username) User
        +change_password(old, new)
    }
    class ReportManager {
        +total_revenue(start, end) dict
        +revenue_by_room_type() list
        +revenue_by_month(year) list
        +occupancy() dict
        +bookings_on(day, mode) list
        +export_csv(kind, dir) Path
    }
    class JsonStorage {
        -__data_dir: Path
        +load(name) list
        +save(name, records)
    }
    class HotelManager {
        <<Facade>>
        -__storage: JsonStorage
        +load() list
        +save()
        +login() / logout()
        +add_room() / update_room() / delete_room()
        +add_guest() / update_guest() / delete_guest()
        +add_service() / update_service() / delete_service()
        +create_booking() / update_booking() / cancel_booking()
        +check_in() / add_service_to_booking() / check_out()
        +export_csv(kind) Path
    }

    BaseManager <|-- RoomManager
    BaseManager <|-- GuestManager
    BaseManager <|-- ServiceManager
    BaseManager <|-- BookingManager
    BaseManager <|-- AuthManager
    BookingManager --> RoomManager
    BookingManager --> GuestManager
    BookingManager --> ServiceManager
    ReportManager --> BookingManager
    ReportManager --> RoomManager
    HotelManager *-- RoomManager
    HotelManager *-- GuestManager
    HotelManager *-- ServiceManager
    HotelManager *-- BookingManager
    HotelManager *-- ReportManager
    HotelManager *-- AuthManager
    HotelManager *-- JsonStorage
```

## 3. Tầng giao diện (ui)

```mermaid
classDiagram
    class Menu {
        -__title: str
        -__items: dict~str, MenuItem~
        +display()
        +run() MenuSignal
    }
    class MenuItem {
        +key: str
        +label: str
        +action: Callable
        +permission: Permission
    }
    class BaseScreen {
        <<abstract>>
        #_hotel: HotelManager
        +menu_items() list*
        +run()
        +ask_existing(manager, prompt)$
        +ask_new_id(manager, prompt, prefix)$
    }
    class HotelApp {
        -__hotel: HotelManager
        +run()
        -_login() bool
        -_main_menu() Menu
    }
    Menu o-- MenuItem
    BaseScreen <|-- RoomScreen
    BaseScreen <|-- GuestScreen
    BaseScreen <|-- BookingScreen
    BaseScreen <|-- ServiceScreen
    BaseScreen <|-- ReportScreen
    BaseScreen <|-- AccountScreen
    BaseScreen ..> Menu : tạo
    HotelApp ..> BaseScreen
    HotelApp --> HotelManager
```

## 4. Giải thích các quan hệ OOP

| Quan hệ | Ví dụ trong bài | Ý nghĩa |
|---|---|---|
| **Kế thừa** | `StandardRoom`, `DeluxeRoom` kế thừa `Room`; `SuiteRoom` kế thừa `DeluxeRoom` (nhiều cấp); `Admin`, `Receptionist` kế thừa `User`; 5 manager kế thừa `BaseManager`; 6 màn hình kế thừa `BaseScreen` | Dùng lại thuộc tính và phương thức chung, lớp con chỉ bổ sung phần riêng |
| **Đa hình (ghi đè)** | `calculate_cost()`, `get_room_type()`, `cost_breakdown()`, `__str__()` của các loại phòng; `permissions()` của các loại `User`; `rate()` của các chính sách giảm giá | Cùng một lời gọi nhưng mỗi lớp xử lý khác nhau. Ví dụ `Invoice` gọi `room.cost_breakdown()` mà không cần biết loại phòng |
| **Đóng gói** | Thuộc tính `__private` / `_protected` + `@property` có setter kiểm tra dữ liệu; `Booking` chỉ đổi trạng thái qua `mark_checked_in()`, `cancel()`… | Không thể gán dữ liệu sai hoặc nhảy cóc trạng thái |
| **Trừu tượng (ABC)** | `Room`, `User`, `DiscountPolicy`, `BaseManager`, `BaseScreen` | Bắt buộc lớp con cài đặt các phương thức trừu tượng; không tạo được đối tượng trực tiếp từ lớp trừu tượng |
| **Hợp thành** (◆ composition) | `Booking` ◆— `ServiceUsage`; `HotelManager` ◆— các manager | Thành phần tồn tại cùng vòng đời với lớp chứa nó |
| **Kết tập** (◇ aggregation) | `DiscountCalculator` ◇— `DiscountPolicy`; `Menu` ◇— `MenuItem` | Lớp chứa giữ tham chiếu tới các đối tượng có thể tồn tại độc lập |
| **Liên kết** (→ association) | `Booking` → `Guest`, `Room` (qua mã); `BookingManager` → `RoomManager` | Đối tượng này biết và dùng đối tượng kia |
| **Phụ thuộc** (⇢ dependency) | `RoomFactory` ⇢ `Room`; `ServiceUsage` ⇢ `Service` | Chỉ dùng tạm thời (tạo đối tượng, sao chép giá) |
| **Mẫu thiết kế** | Facade (`HotelManager`), Factory (`RoomFactory`, `UserFactory`), Strategy (`DiscountPolicy`), Template Method (`BaseManager.add` gọi hook `_validate_unique`) | Tách nghiệp vụ khỏi giao diện, dễ mở rộng thêm loại phòng hoặc chính sách mới |

### Vì sao điều chỉnh so với các lớp gợi ý của đề

- Bổ sung `SuiteRoom` (chức năng mở rộng), kế thừa từ `DeluxeRoom` để minh họa kế thừa nhiều cấp.
- Tách `HotelManager` thành nhiều manager chuyên trách; `HotelManager` chỉ đóng vai trò điều phối (Facade). Như vậy mỗi lớp chỉ có một nhiệm vụ.
- `Booking` lưu thêm trạng thái, tiền phòng, giảm giá và danh sách dịch vụ để phục vụ trả phòng, hóa đơn và thống kê. Đồng thời lưu số phòng và loại phòng tại thời điểm đặt, để lịch sử vẫn đúng khi phòng bị sửa hoặc xóa.
- `Guest` có thêm `id_card` (CCCD/hộ chiếu), không bắt buộc nhập nhưng phải duy nhất nếu có.
