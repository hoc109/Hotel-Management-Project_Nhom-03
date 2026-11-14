"""Định nghĩa các ngoại lệ (exception) riêng của hệ thống.

Mọi lỗi nghiệp vụ đều kế thừa từ ``HotelError`` để tầng giao diện
chỉ cần bắt một loại ngoại lệ và hiển thị thông báo thân thiện.
"""


class HotelError(Exception):
    """Lớp cha của mọi lỗi trong hệ thống quản lý khách sạn."""


class ValidationError(HotelError):
    """Dữ liệu đầu vào không hợp lệ (sai định dạng, rỗng, âm...)."""


class DuplicateIdError(HotelError):
    """Mã định danh (hoặc giá trị duy nhất) đã tồn tại."""


class NotFoundError(HotelError):
    """Không tìm thấy đối tượng theo mã."""


class BusinessRuleError(HotelError):
    """Vi phạm ràng buộc nghiệp vụ (trùng lịch, xóa dữ liệu đang dùng...)."""


class PermissionDeniedError(HotelError):
    """Người dùng hiện tại không có quyền thực hiện thao tác."""


class AuthenticationError(HotelError):
    """Sai tên đăng nhập hoặc mật khẩu."""


class StorageError(HotelError):
    """Lỗi khi đọc/ghi dữ liệu."""


class InputCancelled(Exception):
    """Người dùng chủ động hủy thao tác nhập liệu (gõ 'q').

    Không kế thừa ``HotelError`` vì đây không phải lỗi, chỉ là tín hiệu
    để quay lại menu.
    """
