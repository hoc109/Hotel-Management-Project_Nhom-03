"""Các hàm nhập liệu từ bàn phím có kiểm tra, yêu cầu nhập lại khi sai.

Quy ước chung:
* Gõ ``q`` ở bất kỳ ô nhập nào để hủy thao tác (ném ``InputCancelled``).
* Với ô có giá trị mặc định (khi cập nhật), nhấn Enter để giữ nguyên.
"""

from collections.abc import Callable
from datetime import date
from typing import Any

from hotel.utils.exceptions import InputCancelled, ValidationError
from hotel.utils.formatter import format_date, print_error
from hotel.utils.validators import parse_date, validate_int, validate_number

CANCEL_KEYWORD = "q"

_MISSING = object()


def ask(prompt: str, *, validator: Callable[[str], Any] | None = None,
        required: bool = True, default: Any = _MISSING,
        show_default: str | None = None) -> Any:
    """Nhập một giá trị, lặp lại cho tới khi hợp lệ.

    Args:
        prompt: Câu hỏi hiển thị.
        validator: Hàm kiểm tra/chuyển đổi, ném ``ValidationError`` nếu sai.
        required: Bắt buộc nhập (khi không có ``default``).
        default: Giá trị trả về khi người dùng nhấn Enter.
        show_default: Chuỗi hiển thị cho giá trị mặc định.
    """
    suffix = ""
    if default is not _MISSING:
        shown = show_default if show_default is not None else str(default)
        suffix = f" [{shown}]"
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()
        if raw.lower() == CANCEL_KEYWORD:
            raise InputCancelled()
        if not raw:
            if default is not _MISSING:
                return default
            if not required:
                return ""
            print_error("Trường này là bắt buộc. Vui lòng nhập lại.")
            continue
        if validator is None:
            return raw
        try:
            return validator(raw)
        except ValidationError as exc:
            print_error(f"{exc} Vui lòng nhập lại.")


def ask_int(prompt: str, *, min_value: int | None = None, max_value: int | None = None,
            default: Any = _MISSING) -> int:
    """Nhập số nguyên trong khoảng cho trước."""
    return ask(prompt, default=default,
               validator=lambda s: validate_int(s, "Giá trị", min_value=min_value,
                                                max_value=max_value))


def ask_float(prompt: str, *, min_value: float = 0, allow_equal_min: bool = False,
              default: Any = _MISSING, show_default: str | None = None) -> float:
    """Nhập số thực (mặc định > 0)."""
    return ask(prompt, default=default, show_default=show_default,
               validator=lambda s: validate_number(s, "Giá trị", min_value=min_value,
                                                   allow_equal_min=allow_equal_min))


def ask_date(prompt: str, *, default: Any = _MISSING) -> date:
    """Nhập ngày theo dạng dd/mm/yyyy."""
    shown = format_date(default) if isinstance(default, date) else None
    return ask(f"{prompt} (dd/mm/yyyy)", default=default, show_default=shown,
               validator=parse_date)


def ask_choice(prompt: str, options: dict[str, str], *, default: Any = _MISSING) -> str:
    """Chọn một khóa trong ``options`` (``{khóa: mô tả}``)."""
    for key, label in options.items():
        print(f"   {key}. {label}")

    def _validator(raw: str) -> str:
        if raw not in options:
            raise ValidationError(f"Chỉ được chọn: {', '.join(options)}.")
        return raw

    return ask(prompt, validator=_validator, default=default)


def confirm(prompt: str) -> bool:
    """Hỏi xác nhận y/n, lặp lại tới khi nhập đúng."""
    while True:
        raw = input(f"{prompt} (y/n): ").strip().lower()
        if raw in ("y", "yes", "c", "co", "có"):
            return True
        if raw in ("n", "no", "k", "khong", "không", CANCEL_KEYWORD):
            return False
        print_error("Vui lòng nhập 'y' (đồng ý) hoặc 'n' (không).")


def ask_sort_order() -> bool:
    """Chọn thứ tự sắp xếp. Trả về ``True`` nếu giảm dần."""
    choice = ask_choice("Thứ tự", {"1": "Tăng dần", "2": "Giảm dần"})
    return choice == "2"


def pause() -> None:
    """Dừng màn hình chờ người dùng nhấn Enter."""
    input("\nNhấn Enter để tiếp tục...")
