"""Màn hình danh mục dịch vụ phát sinh (chức năng mở rộng)."""

from hotel.models.enums import Permission
from hotel.models.service import Service
from hotel.ui.base_screen import BaseScreen
from hotel.ui.menu import MenuItem
from hotel.ui.views import show_services
from hotel.utils.exceptions import ValidationError
from hotel.utils.formatter import format_money, print_info, print_success, print_warning
from hotel.utils.input_helper import ask, confirm
from hotel.utils.text_utils import normalize_search
from hotel.utils.validators import validate_id, validate_positive_money, validate_required


class ServiceScreen(BaseScreen):
    """Thêm, sửa, xóa, hiển thị, tìm dịch vụ."""

    TITLE = "Danh mục dịch vụ"

    def menu_items(self) -> list[MenuItem]:
        manage, view = Permission.MANAGE_SERVICES, Permission.VIEW_SERVICES
        return [
            MenuItem("1", "Thêm dịch vụ", self.add_service, manage),
            MenuItem("2", "Cập nhật dịch vụ", self.update_service, manage),
            MenuItem("3", "Xóa dịch vụ", self.delete_service, manage),
            MenuItem("4", "Hiển thị danh mục dịch vụ", self.list_services, view),
            MenuItem("5", "Tìm dịch vụ theo tên", self.search_services, view),
        ]

    def _unique_name(self, exclude_id: str | None = None):
        def validator(raw: str) -> str:
            name = validate_required(raw, "Tên dịch vụ", max_length=50)
            for s in self._hotel.services.list_all():
                if s.service_id != exclude_id and normalize_search(s.name) == normalize_search(name):
                    raise ValidationError(f"Tên dịch vụ đã tồn tại ({s.service_id}).")
            return name
        return validator

    def add_service(self) -> None:
        print_info("Thêm dịch vụ mới (gõ 'q' để hủy).")
        service_id = self.ask_new_id(self._hotel.services, "Mã dịch vụ", "S",
                                     lambda s: validate_id(s, "Mã dịch vụ"))
        name = ask("Tên dịch vụ", validator=self._unique_name())
        price = ask("Đơn giá (VNĐ)", validator=lambda s: validate_positive_money(s, "Đơn giá"))
        unit = ask("Đơn vị tính", default="lần",
                   validator=lambda s: validate_required(s, "Đơn vị tính", 20))
        service = self._hotel.add_service(Service(service_id, name, price, unit))
        print_success(f"Đã thêm dịch vụ {service.name} ({service.service_id}).")
        show_services([service], title="Dịch vụ vừa thêm")

    def update_service(self) -> None:
        service = self.ask_existing(self._hotel.services, "Mã dịch vụ cần cập nhật")
        show_services([service], title="Thông tin hiện tại")
        print_info("Nhấn Enter để giữ nguyên giá trị trong [ ]; gõ 'q' để hủy.")
        changes = {}
        name = ask("Tên dịch vụ", default=service.name,
                   validator=self._unique_name(service.service_id))
        if name != service.name:
            changes["name"] = name
        price = ask("Đơn giá", default=service.price, show_default=format_money(service.price),
                    validator=lambda s: validate_positive_money(s, "Đơn giá"))
        if price != service.price:
            changes["price"] = price
        unit = ask("Đơn vị tính", default=service.unit,
                   validator=lambda s: validate_required(s, "Đơn vị tính", 20))
        if unit != service.unit:
            changes["unit"] = unit
        if not changes:
            print_warning("Không có thay đổi nào.")
            return
        updated = self._hotel.update_service(service.service_id, **changes)
        print_success(f"Đã cập nhật dịch vụ {updated.service_id}.")
        show_services([updated], title="Sau khi cập nhật")

    def delete_service(self) -> None:
        service = self.ask_existing(self._hotel.services, "Mã dịch vụ cần xóa")
        show_services([service], title="Dịch vụ sẽ bị xóa")
        print_info("Các lượt đã sử dụng trước đây vẫn được giữ trong hóa đơn.")
        if not confirm(f"Bạn chắc chắn muốn xóa dịch vụ {service.name}?"):
            print_warning("Đã hủy xóa.")
            return
        self._hotel.delete_service(service.service_id)
        print_success(f"Đã xóa dịch vụ {service.name}.")

    def list_services(self) -> None:
        show_services(self._hotel.services.sort_by(lambda s: s.service_id),
                      empty="Chưa có dịch vụ nào.")

    def search_services(self) -> None:
        keyword = ask("Nhập một phần tên dịch vụ")
        show_services(self._hotel.services.search_by_name(keyword),
                      title=f"Dịch vụ có tên chứa '{keyword}'",
                      empty="Không tìm thấy dịch vụ phù hợp.")
