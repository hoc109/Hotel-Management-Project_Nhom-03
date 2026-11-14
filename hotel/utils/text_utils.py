"""Xử lý chuỗi tiếng Việt: bỏ dấu, chuẩn hóa để tìm kiếm gần đúng."""

import unicodedata


def remove_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt, ví dụ ``"Nguyễn Văn Đức"`` -> ``"Nguyen Van Duc"``."""
    text = text.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_search(text: str) -> str:
    """Chuẩn hóa chuỗi để so khớp: bỏ dấu, chữ thường, gộp khoảng trắng."""
    return " ".join(remove_accents(text).lower().split())


def fuzzy_contains(haystack: str, needle: str) -> bool:
    """Kiểm tra ``needle`` có xuất hiện trong ``haystack`` (không phân biệt
    hoa/thường và dấu tiếng Việt)."""
    return normalize_search(needle) in normalize_search(haystack)


def normalize_spaces(text: str) -> str:
    """Xóa khoảng trắng thừa ở đầu, cuối và giữa chuỗi."""
    return " ".join(text.split())
