"""Định dạng hiển thị: tiền VNĐ, ngày tháng, bảng dữ liệu và màu chữ."""

from datetime import date

from colorama import Fore, Style
from tabulate import tabulate

from hotel.utils.validators import DATE_FORMAT

TABLE_FORMAT = "simple_outline"


def format_money(amount: float) -> str:
    """Định dạng tiền Việt Nam: ``1200000`` -> ``"1.200.000 đ"``."""
    return f"{round(amount):,}".replace(",", ".") + " đ"


def format_percent(rate: float) -> str:
    """``0.155`` -> ``"15.5%"``."""
    return f"{rate * 100:.1f}%"


def format_date(value: date | None) -> str:
    """Định dạng ngày ``dd/mm/yyyy`` (trả ``"-"`` nếu không có)."""
    return value.strftime(DATE_FORMAT) if value else "-"


def render_table(headers: list[str], rows: list[list], *,
                 numeric_align: str = "right") -> str:
    """Tạo chuỗi bảng căn theo cột bằng thư viện ``tabulate``."""
    return tabulate(rows, headers=headers, tablefmt=TABLE_FORMAT,
                    numalign=numeric_align, stralign="left", disable_numparse=True)


def print_table(headers: list[str], rows: list[list], *, title: str | None = None,
                empty_message: str = "Danh sách rỗng.", show_count: bool = True) -> None:
    """In bảng; nếu danh sách rỗng thì in thông báo thay vì bảng trống."""
    if title:
        print(color_title(title))
    if not rows:
        print(color_warning(f"⚠ {empty_message}"))
        return
    print(render_table(headers, rows))
    if show_count:
        print(f"Tổng cộng: {len(rows)} dòng.")


# ----------------------------------------------------------------- màu sắc
def color_success(text: str) -> str:
    """Chữ xanh lá cho thông báo thành công."""
    return f"{Fore.GREEN}{text}{Style.RESET_ALL}"


def color_error(text: str) -> str:
    """Chữ đỏ cho thông báo lỗi."""
    return f"{Fore.RED}{text}{Style.RESET_ALL}"


def color_warning(text: str) -> str:
    """Chữ vàng cho cảnh báo."""
    return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"


def color_title(text: str) -> str:
    """Chữ xanh dương đậm cho tiêu đề."""
    return f"{Style.BRIGHT}{Fore.CYAN}{text}{Style.RESET_ALL}"


def color_dim(text: str) -> str:
    """Chữ mờ cho mục bị khóa quyền."""
    return f"{Style.DIM}{text}{Style.RESET_ALL}"


def print_success(text: str) -> None:
    print(color_success(f"✔ {text}"))


def print_error(text: str) -> None:
    print(color_error(f"✘ {text}"))


def print_warning(text: str) -> None:
    print(color_warning(f"⚠ {text}"))


def print_info(text: str) -> None:
    print(f"ℹ {text}")
