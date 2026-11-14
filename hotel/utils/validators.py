"""Các hàm kiểm tra (validate) dữ liệu đầu vào.

Mỗi hàm nhận giá trị thô, trả về giá trị đã chuẩn hóa nếu hợp lệ,
ngược lại ném ``ValidationError`` kèm thông báo tiếng Việt.
"""

import re
from datetime import date, datetime

from hotel.utils.exceptions import ValidationError
from hotel.utils.text_utils import normalize_spaces

DATE_FORMAT = "%d/%m/%Y"

_ID_PATTERN = re.compile(r"^[A-Z0-9]{2,10}$")
_PHONE_PATTERN = re.compile(r"^0\d{9}$")
_ROOM_NUMBER_PATTERN = re.compile(r"^\d{3,4}$")
_ID_CARD_PATTERN = re.compile(r"^(\d{9}|\d{12}|[A-Z]\d{7,8})$")
_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


def validate_required(value, field: str, max_length: int = 100) -> str:
    """Trường bắt buộc: không rỗng và không vượt quá ``max_length`` ký tự."""
    text = normalize_spaces(str(value)) if value is not None else ""
    if not text:
        raise ValidationError(f"{field} không được để trống.")
    if len(text) > max_length:
        raise ValidationError(f"{field} tối đa {max_length} ký tự.")
    return text


def validate_id(value, field: str = "Mã") -> str:
    """Mã định danh: 2–10 ký tự chữ/số, tự động viết hoa (vd: R001)."""
    text = validate_required(value, field).upper().replace(" ", "")
    if not _ID_PATTERN.match(text):
        raise ValidationError(
            f"{field} chỉ gồm 2–10 ký tự chữ cái không dấu hoặc chữ số (vd: R001)."
        )
    return text


def validate_name(value, field: str = "Họ tên") -> str:
    """Họ tên: 2–50 ký tự, chỉ chứa chữ cái (có dấu) và khoảng trắng."""
    text = validate_required(value, field, max_length=50)
    if len(text) < 2:
        raise ValidationError(f"{field} phải có ít nhất 2 ký tự.")
    if not all(ch.isalpha() or ch == " " for ch in text):
        raise ValidationError(f"{field} chỉ được chứa chữ cái và khoảng trắng.")
    return text.title()


def validate_phone(value) -> str:
    """Số điện thoại Việt Nam: bắt đầu bằng 0, đủ 10 chữ số."""
    text = validate_required(value, "Số điện thoại").replace(" ", "")
    if not _PHONE_PATTERN.match(text):
        raise ValidationError("Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0.")
    return text


def validate_id_card(value) -> str:
    """CCCD (12 số), CMND (9 số) hoặc hộ chiếu (1 chữ + 7–8 số). Có thể để trống."""
    text = (str(value) if value is not None else "").strip().upper()
    if not text:
        return ""
    if not _ID_CARD_PATTERN.match(text):
        raise ValidationError(
            "CCCD/CMND/Hộ chiếu không hợp lệ (12 số, 9 số hoặc 1 chữ + 7–8 số)."
        )
    return text


def validate_room_number(value) -> str:
    """Số phòng: 3–4 chữ số (vd: 101, 1205)."""
    text = validate_required(value, "Số phòng").replace(" ", "")
    if not _ROOM_NUMBER_PATTERN.match(text):
        raise ValidationError("Số phòng phải gồm 3–4 chữ số (vd: 101).")
    return text


def validate_number(value, field: str, *, min_value: float = 0,
                    allow_equal_min: bool = False, max_value: float | None = None) -> float:
    """Kiểm tra số thực, mặc định phải lớn hơn 0."""
    if isinstance(value, bool):
        raise ValidationError(f"{field} phải là số.")
    try:
        number = float(str(value).replace(",", "").replace("_", "").strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{field} phải là số.") from None
    if number != number or number in (float("inf"), float("-inf")):
        raise ValidationError(f"{field} phải là số hữu hạn.")
    if allow_equal_min:
        if number < min_value:
            raise ValidationError(f"{field} phải lớn hơn hoặc bằng {min_value:g}.")
    elif number <= min_value:
        raise ValidationError(f"{field} phải lớn hơn {min_value:g}.")
    if max_value is not None and number > max_value:
        raise ValidationError(f"{field} không được vượt quá {max_value:,.0f}.")
    return number


def validate_positive_money(value, field: str) -> float:
    """Số tiền > 0, tối đa 1 tỷ."""
    return validate_number(value, field, min_value=0, max_value=1_000_000_000)


def validate_non_negative_money(value, field: str) -> float:
    """Số tiền >= 0, tối đa 1 tỷ."""
    return validate_number(value, field, min_value=0, allow_equal_min=True,
                           max_value=1_000_000_000)


def validate_int(value, field: str, *, min_value: int | None = None,
                 max_value: int | None = None) -> int:
    """Kiểm tra số nguyên trong khoảng [min_value, max_value]."""
    if isinstance(value, bool):
        raise ValidationError(f"{field} phải là số nguyên.")
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{field} phải là số nguyên.") from None
    if min_value is not None and number < min_value:
        raise ValidationError(f"{field} phải lớn hơn hoặc bằng {min_value}.")
    if max_value is not None and number > max_value:
        raise ValidationError(f"{field} phải nhỏ hơn hoặc bằng {max_value}.")
    return number


def parse_date(value, field: str = "Ngày") -> date:
    """Chuyển chuỗi ``dd/mm/yyyy`` (hoặc ISO ``yyyy-mm-dd``) thành ``date``."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = validate_required(value, field)
    for fmt in (DATE_FORMAT, "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValidationError(f"{field} không hợp lệ, hãy nhập theo dạng dd/mm/yyyy.")


def validate_date_range(check_in: date, check_out: date) -> None:
    """Ngày trả phòng không được trước ngày nhận phòng.

    Cho phép nhận và trả trong cùng một ngày (khi đó tính tối thiểu 1 đêm).
    """
    if check_out < check_in:
        raise ValidationError("Ngày trả phòng không được trước ngày nhận phòng.")


def validate_username(value) -> str:
    """Tên đăng nhập: 3–20 ký tự chữ, số hoặc dấu gạch dưới."""
    text = validate_required(value, "Tên đăng nhập").lower()
    if not _USERNAME_PATTERN.match(text):
        raise ValidationError("Tên đăng nhập gồm 3–20 ký tự chữ, số hoặc '_'.")
    return text


def validate_password(value) -> str:
    """Mật khẩu: tối thiểu 6 ký tự, không chứa khoảng trắng."""
    text = "" if value is None else str(value)
    if len(text) < 6:
        raise ValidationError("Mật khẩu phải có ít nhất 6 ký tự.")
    if any(ch.isspace() for ch in text):
        raise ValidationError("Mật khẩu không được chứa khoảng trắng.")
    return text
