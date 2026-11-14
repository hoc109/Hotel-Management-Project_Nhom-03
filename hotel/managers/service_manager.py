"""Quản lý danh mục dịch vụ phát sinh."""

from hotel.managers.base_manager import BaseManager
from hotel.models.service import Service
from hotel.utils.exceptions import DuplicateIdError
from hotel.utils.text_utils import fuzzy_contains, normalize_search


class ServiceManager(BaseManager[Service]):
    """Quản lý các đối tượng ``Service``."""

    ID_PREFIX = "S"

    @property
    def entity_name(self) -> str:
        return "dịch vụ"

    def get_id(self, item: Service) -> str:
        return item.service_id

    def create_from_dict(self, data: dict) -> Service:
        return Service.from_dict(data)

    def _validate_unique(self, item: Service, exclude_id: str | None = None) -> None:
        """Tên dịch vụ không được trùng (không phân biệt hoa/thường, dấu)."""
        for service in self._items.values():
            if (service.service_id != exclude_id
                    and normalize_search(service.name) == normalize_search(item.name)):
                raise DuplicateIdError(f"Tên dịch vụ '{item.name}' đã tồn tại ({service.service_id}).")

    def search_by_name(self, keyword: str) -> list[Service]:
        return self.filter(lambda s: fuzzy_contains(s.name, keyword))
